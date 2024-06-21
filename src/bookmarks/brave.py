from pathlib import Path
import json
from .chrome import load_bookmarks_chromium
from datetime import datetime, timedelta, timezone


def dateFromWebkit(timestamp):
    epochStart = datetime(1601, 1, 1)
    delta = timedelta(microseconds=int(timestamp))
    return (epochStart + delta).replace(tzinfo=timezone.utc).astimezone()


class Item(dict):
    """Item class, dict based. properties: `id`, `name`, `type`, `url`, `folders`, `urls`"""

    @property
    def id(self):
        return self["id"]

    @property
    def name(self):
        return self["name"]

    @property
    def type(self):
        return self["type"]

    @property
    def url(self):
        if "url" in self:
            return self["url"]
        return ""

    @property
    def added(self):
        return dateFromWebkit(self["date_added"])

    @property
    def modified(self):
        if "date_modified" in self:
            return dateFromWebkit(self["date_modified"])

    @property
    def folders(self):
        items = []
        for children in self["children"]:
            if children["type"] == "folder":
                items.append(Item(children))
        return items

    @property
    def urls(self):
        items = []
        for children in self["children"]:
            if children["type"] == "url":
                items.append(Item(children))
        return items


class Bookmarks:
    """Bookmarks class. attrs: `path`. properties: `folders`, `urls`"""

    def __init__(self, path: Path | str):
        self.path = path
        with open(path, encoding="utf-8") as f:
            self.data = json.load(f)
        self.attrList = self.processRoots()
        self.urls = self.attrList["urls"]
        self.folders = self.attrList["folders"]

    def processRoots(self):
        attrList = {"urls": [], "folders": []}
        with open(self.path, encoding="utf-8") as f:
            roots_data = json.load(f)
        for key, value in roots_data["roots"].items():
            if "children" in value:
                self.processTree(attrList, value["children"])
        return attrList

    def processTree(self, attrList, childrenList):
        for item in childrenList:
            self.processUrls(item, attrList, childrenList)
            self.processFolders(item, attrList, childrenList)

    def processUrls(self, item, attrList, childrenList):
        if "type" in item and item["type"] == "url":
            attrList["urls"].append(Item(item))

    def processFolders(self, item, attrList, childrenList):
        if "type" in item and item["type"] == "folder":
            attrList["folders"].append(Item(item))
            if "children" in item:
                self.processTree(attrList, item["children"])


def load_bookmarks(path: str) -> tuple[list[str], bool]:
    bookmark_file_path = Path(
        "C:/Users/gabriel/AppData/Local/BraveSoftware/Brave-Browser/User Data/Default/Bookmarks")
    folders = Bookmarks(bookmark_file_path).folders
    return load_bookmarks_chromium(path, folders)
