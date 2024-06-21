from pathlib import Path
from typing import Any
import yaml
from hitomi import Doujinshi, Artist
from .serialization import Serializer


def loadYaml(path: Path | str):
    data = None
    with open(f"{path}.yaml", "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data


def dump_doujin(file, doujin: Doujinshi):
    data = doujin.toJSON()
    file.write(f"- name: \"{data['name']}\"\n")
    for key in data:
        if key == "name":
            continue
        if not data[key]:
            continue
        file.write(f"\t{key}:")
        if isinstance(data[key], list):
            file.write("\n")
            for entry in data[key]:
                file.write(f"\t\t- {entry}\n")
        else:
            file.write(f" {data[key]}\n")


def dump_artist(file, artist: Artist):
    file.write(f"- name: {artist.name}")
    file.write(f"\turl: {artist.url}")


def dumpYaml(path: Path | str, data: list[Artist | Doujinshi]):
    print(f"Dumping {path}.yaml")
    with open(f"{path}.yaml", "w", encoding="utf-8") as f:
        f.write("---\n")
        if isinstance(data, list):
            for entry in data:
                if isinstance(entry, Doujinshi):
                    dump_doujin(f, entry)
                elif isinstance(entry, Artist):
                    dump_artist(f, entry)


def YamlSerializer():
    return Serializer(loadYaml, dumpYaml)
