from dataclasses import dataclass


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
    is_end: bool
    authors: list
    categories: tuple
    chapters: Chapters
    latest: str
    update_time: int
