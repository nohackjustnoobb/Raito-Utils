import json
import os
import threading
import concurrent.futures
from time import sleep

from mode.init_db import init_db
from models.manga import ChapterModel, Manga, MangaModel

print('Running in mode "all"')

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
next_id = None
waiting_list = []
failed = []
failed_count = {}
consecutive_failures = 0
thread_lock = threading.Lock()

# load previous data
json_path = f"data/{driver.identifier}.json"
if os.path.exists(json_path):
    with open(json_path, "r") as file:
        state = json.load(file)
    if state["mode"] == "all":
        waiting_list = state["waitingList"]
        next_id = state["nextId"]
        failed = state["failed"]

# initialize state if it doesn't exist
if next_id == None:
    next_id = driver.initId


# helper functions
def save_state():
    global waiting_list, next_id, failed
    with open(json_path, "w") as file:
        json.dump(
            {
                "mode": "all",
                "waitingList": waiting_list,
                "nextId": next_id,
                "failed": failed,
            },
            file,
        )


def save_manga(manga: Manga):
    print(f"Saving: {manga.id}")

    with db.atomic():
        manga.to_model().save(force_insert=True)
        ChapterModel.bulk_create(manga.to_chapter_models(), batch_size=100)


def fetch(proxy):
    global waiting_list, thread_lock

    with thread_lock:
        id = waiting_list.pop(0)
    print(f"Fetching: {id}")

    manga = None
    try:
        manga = driver.get(id, proxy)
    except:
        error(id)

    return manga


def error(id):
    global waiting_list, failed_count, failed, consecutive_failures, thread_lock

    print(f"Error: {id}")
    with thread_lock:
        if failed_count.get(id) == None:
            failed_count[id] = 0

        if failed_count[id] >= 5:
            print(f"Failed: {id}")
            consecutive_failures += 1
            failed.append(id)
        else:
            failed_count[id] += 1
            waiting_list.insert(0, id)


def load_next_to_wait_list():
    global waiting_list, next_id
    waiting_list.append(next_id)
    next_id = driver.next(next_id)


# main loop
while consecutive_failures < 5:
    while len(waiting_list) <= len(proxies):
        load_next_to_wait_list()

    with concurrent.futures.ThreadPoolExecutor(len(proxies)) as executor:
        futures = {executor.submit(fetch, proxy) for proxy in proxies}

        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            try:
                if result != None:
                    save_manga(result)
                    consecutive_failures = 0
            except IndexError:
                error(result.id)

    save_state()
    print("sleeping...")
    sleep(driver.timeout)
