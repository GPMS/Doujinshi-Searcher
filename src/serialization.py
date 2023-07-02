import json
import os
import pathlib
from hitomi import Config, Doujinshi, Artist

WORKSPACE_DIR = pathlib.Path(__file__).parent.parent.resolve()
OUTPUT_DIR = os.path.join(WORKSPACE_DIR, "output")
OUTPUT_BACKUP_DIR = os.path.join(WORKSPACE_DIR, "output-backup")
CONFIG_FILE = os.path.join(WORKSPACE_DIR, "config.json")
CONFIG_BACKUP_FILE = os.path.join(WORKSPACE_DIR, "config-backup.json")
CONFIG_PATH = os.path.join("h:", os.sep, "doujinshi")


class MyJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Doujinshi) or isinstance(obj, Artist) or isinstance(obj, Config):
            return obj.toJSON()
        return super(MyJsonEncoder, self).dumps(obj, ensure_ascii=False, indent=4)


def dump_config_file(config: Config | None, write_back: bool = False):
    if not config:
        return
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, cls=MyJsonEncoder, indent=4)
    if write_back:
        stop_file_path = os.path.join(CONFIG_PATH, "stop.txt")
        with open(stop_file_path, "w", encoding="utf-8") as f:
            f.write(
                f"{config.stop_datetime.strftime('%d/%m/%Y %H:%M')}\n{config.stop_title}")
        finished_file_path = os.path.join(CONFIG_PATH, "finished.txt")
        with open(finished_file_path, "w") as f:
            for series_name in sorted(config.seen_series):
                f.write(f"{series_name}\n")


def load_config_file() -> Config | None:
    json_data = {}
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        json_data = json.loads(f.read())
    config: Config | None = Config.fromJSON(json_data)
    return config


def create_necessary_folders():
    try:
        os.makedirs(OUTPUT_DIR)
    except FileExistsError:
        pass


def dump_list(filename: str, data: list):
    create_necessary_folders()
    file_path = os.path.join(OUTPUT_DIR, f"{filename}.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, cls=MyJsonEncoder, indent=4)


def load_doujinshi_list(filename: str) -> list[Doujinshi]:
    doujinshi_list: list[Doujinshi] = []
    create_necessary_folders()
    try:
        json_list = []
        file_path = os.path.join(OUTPUT_DIR, f"{filename}.json")
        with open(file_path, "r", encoding="utf-8") as f:
            json_list = json.loads(f.read())
    except FileNotFoundError:
        return []
    for item in json_list:
        doujinshi = Doujinshi.fromJSON(item)
        if doujinshi != None:
            doujinshi_list.append(doujinshi)
    return doujinshi_list


def load_artist_list(filename: str) -> list[Artist]:
    artist_list: list[Artist] = []
    create_necessary_folders()
    try:
        json_list = []
        file_path = os.path.join(OUTPUT_DIR, f"{filename}.json")
        with open(file_path, "r", encoding="utf-8") as f:
            json_list = json.loads(f.read())
    except FileNotFoundError:
        return []
    for item in json_list:
        artist = Artist.fromJSON(item)
        if artist != None:
            artist_list.append(artist)

    return artist_list
