from dataclasses import dataclass
from peewee import *


class MangaModel(Model):
    id = CharField(column_name="ID", primary_key=True)
    authors = CharField(column_name="AUTHORS")
    categories = CharField(column_name="CATEGORIES")
    description = TextField(column_name="DESCRIPTION")
    is_ended = BooleanField(column_name="IS_ENDED")
    latest = CharField(column_name="LATEST")
    thumbnail = CharField(column_name="THUMBNAIL")
    title = CharField(column_name="TITLE")
    update_time = IntegerField(column_name="UPDATE_TIME")
    extra_data = CharField(column_name="EXTRA_DATA")

    class Meta:
        table_name = "MANGA"


class ChapterModel(Model):
    manga = ForeignKeyField(column_name="MANGA_ID", model=MangaModel)
    id = CharField(column_name="ID")
    idx = IntegerField(column_name="IDX")
    is_extra = BooleanField(column_name="IS_EXTRA")
    title = CharField(column_name="TITLE")
    urls = TextField(column_name="URLS", null=True)

    class Meta:
        table_name = "CHAPTER"
        primary_key = CompositeKey("manga", "id")


@dataclass
class Chapter:
    title: str
    id: str


@dataclass
class Chapters:
    serial: list[Chapter]
    extra: list[Chapter]
    extra_data: str


@dataclass
class PreviewManga:
    id: str
    latest: str


@dataclass
class Manga:
    categories_list = [
        "Passionate",
        "Love",
        "Campus",
        "Yuri",
        "BL",
        "Adventure",
        "Harem",
        "SciFi",
        "War",
        "Suspense",
        "Speculation",
        "Funny",
        "Fantasy",
        "Magic",
        "Horror",
        "Ghosts",
        "History",
        "FanFi",
        "Sports",
        "Hentai",
        "Mecha",
        "Restricted",
        "Otokonoko",
    ]
    id: str
    thumbnail: str
    title: str
    description: str
    is_ended: bool
    authors: list
    categories: tuple
    chapters: Chapters
    latest: str
    update_time: int

    def to_model(self):
        model = MangaModel()

        model.id = self.id
        model.title = self.title
        model.thumbnail = self.thumbnail
        model.description = self.description
        model.is_ended = self.is_ended
        model.latest = self.latest
        model.update_time = self.update_time
        model.extra_data = self.chapters.extra_data
        model.authors = "|".join(self.authors)
        model.categories = "|".join(self.categories)

        return model

    def to_chapter_models(self):
        models = []

        for idx, i in enumerate(reversed(self.chapters.serial)):
            model = ChapterModel()
            model.title = i.title
            model.id = i.id
            model.idx = idx
            model.is_extra = False
            model.manga = self.id
            models.append(model)

        for idx, i in enumerate(reversed(self.chapters.extra)):
            model = ChapterModel()
            model.title = i.title
            model.id = i.id
            model.idx = idx
            model.is_extra = True
            model.manga = self.id
            models.append(model)

        return models
