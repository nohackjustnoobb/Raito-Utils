from models.manga import *


class Driver:
    identifier: str = None
    timeout: int = None

    def get(self, id, proxy: str) -> Manga:
        pass

    def update(self, proxy: str) -> [PreviewManga]:
        pass
