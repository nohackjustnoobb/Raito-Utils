import json
import os
import sqlite3
import concurrent.futures
import threading
from time import sleep

from models.manga import *

# load the config
with open("config.json", "r") as file:
    config = json.load(file)
    proxies: tuple = config["proxies"]


# load the driver
driver = config["driver"]
exec(f"from drivers.{driver.lower()} import {driver.upper()}")
exec(f"driver = {driver.upper()}()")

# global variables
next_id = None
wait_list = []
failed = []
failed_count = {}
consecutive_failures = 0

# create data directory
if not os.path.exists("data"):
    os.makedirs("data")


json_path = f"data/{driver.identifier}.json"

# try to load previous state
if os.path.exists(json_path):
    with open(json_path, "r") as file:
        state = json.load(file)
    wait_list = state["waitList"]
    next_id = state["nextId"]
    failed = state["failed"]

# initialize state if it doesn't exist
if next_id == None:
    next_id = driver.initId


# initialize database
conn = sqlite3.connect(f"data/{driver.identifier}.sqlite3")
cursor = conn.cursor()

with open("sql/initial.sql", "r") as sql_file:
    sql_commands = sql_file.read()
    cursor.executescript(sql_commands)
    conn.commit()


# helper functions
def save_state():
    global wait_list, next_id, failed
    with open(json_path, "w") as file:
        json.dump(
            {
                "waitList": wait_list,
                "nextId": next_id,
                "failed": failed,
            },
            file,
        )


def save_manga(manga: Manga):
    global cursor, conn

    print(f"Saving: {manga.id}")

    # save the manga
    cursor.execute(
        "REPLACE INTO MANGA (ID, THUMBNAIL, TITLE, DESCRIPTION, IS_END, AUTHORS, CATEGORIES, LATEST, UPDATE_TIME) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            manga.id,
            manga.thumbnail,
            manga.title,
            manga.description,
            manga.is_end,
            "|".join(manga.authors),
            "|".join(manga.categories),
            manga.latest,
            manga.update_time,
        ),
    )

    conn.commit()

    # save the chapters
    cursor.execute(
        "REPLACE INTO CHAPTERS (MANGA_ID, EXTRA_DATA) VALUES (?, ?)",
        (manga.id, manga.chapters.extra_data),
    )
    conn.commit()

    # delete the existing chapter
    cursor.execute("DELETE FROM CHAPTER WHERE CHAPTERS_ID = ?;", (manga.id,))
    conn.commit

    # save the chapter
    cursor.executemany(
        "REPLACE INTO CHAPTER (CHAPTERS_ID, ID, IDX, TITLE, IS_EXTRA) VALUES (?, ?, ?, ?, ?)",
        list(
            map(
                lambda x: (manga.id, x[1].id, x[0], x[1].title, True),
                enumerate(reversed(manga.chapters.extra)),
            )
        ),
    )
    cursor.executemany(
        "REPLACE INTO CHAPTER (CHAPTERS_ID, ID, IDX, TITLE, IS_EXTRA) VALUES (?, ?, ?, ?, ?)",
        list(
            map(
                lambda x: (manga.id, x[1].id, x[0], x[1].title, False),
                enumerate(reversed(manga.chapters.serial)),
            )
        ),
    )
    conn.commit()


def load_next_to_wait_list():
    global wait_list, next_id
    wait_list.append(next_id)
    next_id = driver.next(next_id)


list_lock = threading.Lock()


def fetch(proxy):
    global wait_list, list_lock

    with list_lock:
        id = wait_list.pop(0)
    print(f"Fetching: {id}")

    try:
        manga = driver.get(id, proxy)
    except:
        manga = None
        error(id)

    return manga


def error(id):
    global wait_list, failed_count, failed, consecutive_failures, list_lock

    print(f"Error: {id}")
    with list_lock:
        if failed_count.get(id) == None:
            failed_count[id] = 0

        if failed_count[id] >= 5:
            print(f"Failed: {id}")
            consecutive_failures += 1
            failed.append(id)
        else:
            failed_count[id] += 1
            wait_list.insert(0, id)


# main loop
while consecutive_failures < 5:
    while len(wait_list) <= len(proxies):
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
    sleep(driver.timeout)
