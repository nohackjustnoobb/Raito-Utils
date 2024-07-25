import json
import os
import threading
import concurrent.futures
from time import sleep

from mode.init_db import init_db
from models.manga import ChapterModel, Manga, MangaModel, PreviewManga

print('Running in mode "update"')

# load the config
with open("config.json", "r") as file:
    config = json.load(file)


# load the driver
driver = config["driver"]
exec(f"from drivers.{driver.lower()} import {driver.upper()}")
exec(f"driver = {driver.upper()}()")

# load proxies
proxies = config["proxies"]
if len(proxies) == 0:
    raise Exception("No Proxies")


# create data directory
if not os.path.exists("data"):
    os.makedirs("data")

# init the database
db_config = config.get("database")
if not db_config:
    db_config = {"sql": "sqlite3"}
if not db_config.get("connection"):
    db_config["connection"] = {"path": f"./data/{driver.identifier.upper()}.sqlite3"}
db = init_db(db_config)

# global variables
waiting_list = []
failed = []
failed_count = {}
thread_lock = threading.Lock()

json_path = f"data/{driver.identifier}.json"
if os.path.exists(json_path):
    with open(json_path, "r") as file:
        state = json.load(file)
    if state["mode"] == "update":
        waiting_list = state["waitingList"]
        failed = state["failed"]


# helper functions
def save_state():
    global waiting_list
    with open(json_path, "w") as file:
        json.dump(
            {
                "mode": "update",
                "waitingList": waiting_list,
                "failed": failed,
            },
            file,
        )


def save_manga(manga: Manga):
    print(f"Saving: {manga.id}")

    with db.atomic():
        result = manga.to_model().save()
        if result == 0:
            manga.to_model().save(force_insert=True)
            ChapterModel.bulk_create(manga.to_chapter_models(), batch_size=100)
        else:
            chapter_dict = {}
            for i in [*manga.chapters.extra, *manga.chapters.serial]:
                chapter_dict[i.id] = i

            # delete removed chapters
            ChapterModel.delete().where(
                (ChapterModel.manga == manga.id)
                & (ChapterModel.id.not_in(list(chapter_dict.keys())))
            )

            # get old chapters
            chapters = ChapterModel.select().where(
                (ChapterModel.manga == manga.id)
                & (ChapterModel.id.in_(list(chapter_dict.keys())))
            )

            # update the existing chapters
            for chapter in chapters:
                if chapter.title != chapter_dict[chapter.id].title:
                    chapter.title = chapter_dict[chapter.id].title
                    chapter.save()
                del chapter_dict[chapter.id]

            # insert new chapters
            new_chapters = list(
                filter(lambda x: x.id in chapter_dict.keys(), manga.to_chapter_models())
            )
            ChapterModel.bulk_create(new_chapters, batch_size=100)


def save_chapter(manga_id, id, urls):
    print(f"Saving Chapter: {id} from {manga_id}")

    chapter = ChapterModel.get(
        (ChapterModel.manga == manga_id) & (ChapterModel.id == id)
    )
    chapter.urls = "|".join(urls)
    chapter.save()


def check(manga: PreviewManga):
    global waiting_list
    try:
        model = MangaModel.get(MangaModel.id == manga.id)
        if (
            not driver.is_same(model.latest, manga.latest)
            and manga.id not in waiting_list
        ):
            print(f"Outdated: {manga.id}")
            waiting_list.append(manga.id)
    except:
        if manga.id not in waiting_list:
            print(f"New: {manga.id}")
            waiting_list.append(manga.id)


class FetchObject:
    type: str
    id: tuple | str
    result: object = None

    def __init__(self, type, id):
        self.type = type
        self.id = id

    def save(self):
        if self.result is None:
            return

        if self.type == "manga":
            save_manga(self.result)
        else:
            save_chapter(self.id[0], self.id[1], self.result)

            key = ".".join(self.id[:-1])
            if failed_count.get(key) is not None:
                del failed_count[key]

    def fetch(self, proxy):
        if self.type == "manga":
            print(f"Fetching: {self.id}")
            self.result = driver.get(self.id, proxy)
        else:
            print(f"Fetching: {self.id[1]} from {self.id[0]}")
            self.result = driver.get_chapter(self.id[1], self.id[2], proxy)

        if self.result is None:
            raise

    def error(self):
        global thread_lock
        if self.type == "manga":
            print(f"Error: {self.id}")
            global waiting_list
            with thread_lock:
                waiting_list.append(self.id)
        else:
            print(f"Error: {self.id[1]} from {self.id[0]}")
            global failed_count
            key = ".".join(self.id[:-1])
            with thread_lock:
                if failed_count.get(key) is None:
                    failed_count[key] = 0
                failed_count[key] += 1

                if failed_count[key] >= 5:
                    del failed_count[key]
                    failed.append(self.id[:-1])


def fetch(proxy):
    global thread_lock

    fo = None
    with thread_lock:
        global waiting_list
        if len(waiting_list) != 0:
            id = waiting_list.pop(0)
            fo = FetchObject("manga", id)
        else:
            try:
                offset = 0
                while True:
                    query = (
                        ChapterModel.select()
                        .where(ChapterModel.urls.is_null())
                        .limit(1)
                        .offset(offset)
                    )
                    chapter = [i for i in query][0]

                    if not any(
                        i[0] == chapter.manga.id and i[1] == chapter.id for i in failed
                    ):
                        id = (chapter.manga.id, chapter.id, chapter.manga.extra_data)
                        fo = FetchObject("chapter", id)
                        break

                    offset += 1
            except:
                pass

    if fo is not None:
        try:
            fo.fetch(proxy)
        except:
            fo.error()

    return fo


counter = 300
while True:
    # check if 5 minutes have passed
    if counter >= 300:
        # get the updates
        print(f"Getting Updates")
        update = driver.get_update(proxies[0])
        for i in update:
            # check each manga if updated
            check(i)
        counter = 0
    else:
        with concurrent.futures.ThreadPoolExecutor(len(proxies)) as executor:
            futures = {executor.submit(fetch, proxy) for proxy in proxies}

            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                if result is not None:
                    result.save()

    save_state()
    print("sleeping...")
    sleep(driver.timeout)
    counter += driver.timeout
