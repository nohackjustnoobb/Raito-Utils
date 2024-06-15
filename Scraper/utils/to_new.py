import sqlite3
from peewee import *

import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.manga import ChapterModel, Manga, MangaModel, Chapters, Chapter


# initialize database
filename = input("Filename: ")
if not filename:
    filename = "MHG.sqlite3"
old = sqlite3.connect("./utils/" + filename)
cursor = old.cursor()


new = SqliteDatabase("./utils/new.sqlite3")
new.connect()
new.bind([MangaModel, ChapterModel])
new.create_tables([MangaModel, ChapterModel])


mangaDict = {}

print("Querying Manga")
cursor.execute("SELECT * FROM MANGA M JOIN CHAPTERS C ON C.MANGA_ID = M.ID")
result = cursor.fetchall()
for row in result:
    manga = Manga(
        id=row[0],
        thumbnail=row[1],
        title=row[2],
        description=row[3],
        is_ended=row[4] == 1,
        authors=row[5].split("|"),
        categories=row[6].split("|"),
        latest=row[7],
        update_time=row[8],
        chapters=Chapters(extra=[], serial=[], extra_data=row[10]),
    )
    mangaDict[manga.id] = manga

print("Querying Chapter")
cursor.execute("SELECT * FROM CHAPTER ORDER BY -IDX")
result = cursor.fetchall()
for row in result:
    if row[4] == 0:
        mangaDict[str(row[0])].chapters.serial.append(Chapter(title=row[3], id=row[1]))
    else:
        mangaDict[str(row[0])].chapters.extra.append(Chapter(title=row[3], id=row[1]))


mangas = []
chapters = []

for manga in mangaDict.values():
    mangas.append(manga.to_model())
    chapters.extend(manga.to_chapter_models())


print("Inserting Records")
with new.atomic():
    MangaModel.bulk_create(mangas, batch_size=100)
    ChapterModel.bulk_create(chapters, batch_size=100)
