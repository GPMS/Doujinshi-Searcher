import json
from pathlib import Path
from typing import Any
from .serialization import Serializer
from hitomi import Config, Doujinshi, Artist


class MyJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Doujinshi) or isinstance(obj, Artist) or isinstance(obj, Config):
            return obj.toJSON()
        return json.dumps(obj, ensure_ascii=False, indent=4)


def loadJson(path: Path | str):
    try:
        data = None
        with open(f"{path}.json", "r", encoding="utf-8") as f:
            data = json.loads(f.read())
        return data
    except FileNotFoundError:
        return None


def dumpJson(path: Path | str, data: Any):
    with open(f"{path}.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, cls=MyJsonEncoder, indent=4)


def JsonSerializer():
    return Serializer(loadJson, dumpJson)
