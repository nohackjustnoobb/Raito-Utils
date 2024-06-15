from peewee import *

from models.manga import ChapterModel, MangaModel


def init_db(config):
    sql = config.get("sql")

    if sql == "sqlite3":
        path = config["connection"].get("path")
        db = SqliteDatabase(path)

    db.connect()
    db.bind([MangaModel, ChapterModel])
    db.create_tables([MangaModel, ChapterModel])

    return db
