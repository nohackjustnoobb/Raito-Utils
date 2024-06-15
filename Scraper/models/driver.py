from models.manga import Manga, PreviewManga


class Driver:
    identifier: str = None
    timeout: int = None
    initId = None

    def get(self, id, proxy) -> Manga:
        pass

    def get_chapter(self, id, extra_data, proxy) -> list[str]:
        pass

    def get_update(self, proxy) -> list[PreviewManga]:
        pass

    def is_same(self, val1, val2) -> bool:
        return val1 == val2

    def next(self, id):
        pass
