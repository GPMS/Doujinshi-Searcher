from pathlib import Path
from hitomi import Config, Doujinshi, Artist
from typing import Callable, Any


class Serializer():
    def __init__(self, loader: Callable[[Path | str], None | Any], dumper: Callable[[Path | str, Any], None]):
        self.__load = loader
        self.__dump = dumper

    def load_config_file(self, path: Path | str):
        json_data: dict | None = self.__load(path)
        if json_data == None:
            return None
        return Config.fromJSON(json_data)

    def dump_to_file(self, path, data):
        self.__dump(path, data)

    def load_list(self, path: Path | str) -> list[dict]:
        data: list[dict] | None = self.__load(path)
        if data == None:
            return []
        return data

    def load_doujinshi_list(self, path: Path | str) -> list[Doujinshi]:
        list_of_dicts = self.load_list(path)
        if len(list_of_dicts) == 0:
            return []
        doujinshi_list: list[Doujinshi] = []
        for item in list_of_dicts:
            doujinshi = Doujinshi.fromJSON(item)
            if doujinshi is not None:
                doujinshi_list.append(doujinshi)
        return doujinshi_list

    def load_artist_list(self, path: Path | str) -> list[Artist]:
        list_of_dicts = self.load_list(path)
        if len(list_of_dicts) == 0:
            return []
        artist_list: list[Artist] = []
        for item in list_of_dicts:
            artist = Artist.fromJSON(item)
            if artist != None:
                artist_list.append(artist)
        return artist_list
