import json
import os
import sqlite3
from time import sleep

from models.manga import *

# load the config
with open("config.json", "r") as file:
    config = json.load(file)


# load the driver
driver = config["driver"]
exec(f"from drivers.{driver.lower()} import {driver.upper()}")
exec(f"driver = {driver.upper()}()")


# create data directory
if not os.path.exists("data"):
    os.makedirs("data")

# global variables
wait_list = []

json_path = f"data/{driver.identifier}.json"

# try to load previous state
if os.path.exists(json_path):
    with open(json_path, "r") as file:
        state = json.load(file)
    wait_list = state["waitList"]


# initialize database
conn = sqlite3.connect(f"data/{driver.identifier}.sqlite3")
cursor = conn.cursor()


# helper functions
def save_state():
    global wait_list
    with open(json_path, "w") as file:
        json.dump(
            {"waitList": wait_list},
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

    # save the chapter
    cursor.executemany(
        "REPLACE INTO CHAPTER (CHAPTERS_ID, ID, TITLE, IS_EXTRA) VALUES (?, ?, ?, ?)",
        list(map(lambda x: (manga.id, x.id, x.title, True), manga.chapters.extra)),
    )
    cursor.executemany(
        "REPLACE INTO CHAPTER (CHAPTERS_ID, ID, TITLE, IS_EXTRA) VALUES (?, ?, ?, ?)",
        list(map(lambda x: (manga.id, x.id, x.title, False), manga.chapters.serial)),
    )
    conn.commit()


def check(manga: PreviewManga):
    global wait_list

    cursor.execute("SELECT * FROM MANGA WHERE ID = ?", (manga.id,))
    row = cursor.fetchone()

    if row:
        if manga.latest not in row[-2] and manga.id not in wait_list:
            print(f"Outdated: {manga.id}")
            wait_list.append(manga.id)
    elif manga.id not in wait_list:
        print(f"New: {manga.id}")
        wait_list.append(manga.id)


counter = 300
proxy = config["proxy"]
while True:
    # check if 5 minutes have passed
    if counter >= 300:
        try:
            # get the updates
            print(f"Getting Updates")
            update = driver.update(proxy)
            for i in update:
                # check each manga if updated
                check(i)
            counter = 0
        except:
            pass
    elif wait_list:
        # update the outdated manga
        id = wait_list.pop(0)
        try:
            print(f"Fetching: {id}")
            manga = driver.get(id, proxy)
            save_manga(manga)
        except:
            print(f"Error: {id}")
            wait_list.append(id)

    save_state()
    print("sleeping...")
    sleep(driver.timeout)
    counter += driver.timeout
