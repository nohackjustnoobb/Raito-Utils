from models.manga import Manga


class Driver:
    identifier: str = None
    timeout: int = None
    initId = None

    def get(self, id, proxy: str) -> Manga:
        pass

    def next(self, id):
        pass
