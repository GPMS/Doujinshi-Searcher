from datetime import datetime

from .logger import Logger


def set_correct_data(obj: object, key: str, data):
    """
    Set `obj.key` to `data` while converting `data` to the type of `obj.key`
    """
    if obj == None:
        return
    correct_type = type(getattr(obj, key))
    correct_data = None
    if correct_type == datetime:
        correct_data = datetime.strptime(data, '%d/%m/%Y %H:%M')
    if correct_type == set:
        correct_data = set(data)
    elif correct_type == int:
        correct_data = int(data)
    else:
        correct_data = data
    setattr(obj, key, correct_data)


class Filters():
    def __init__(self):
        # Language all doujin must be in
        # First one is used for doujin filter, second one for site filter
        self.language = ["日本語", "japanese"]
        # Types a doujin must not contain (doujinshi, original, game cg, etc)
        self.must_exclude_type = set([
            "game cg"
        ])
        # Tags a doujin must have
        self.must_include_tags = set()
        # Tags a doujin must not have
        self.must_exclude_tags = set([
            "dickgirl on dickgirl ♀",
            "beastiality",
            "farting",
            "futanari",
            "gender change",
            "guro",
            "males only",
            "mind control",
            "mmf threesome",
            "netorare ♀",
            "pegging",
            "ryona",
            "sample",
            "scat",
            "shemale",
            "yaoi"
            "ttf threesome",
        ])
        # Characters that must be present in the doujin for it to be included
        self.must_include_characters = set()
        # Only doujin that included this series are included.
        # Leave it blank for all series
        self.must_include_series = ""
        # Minimum number of doujin that fit the user's preference a author have created to be included
        # (Use 0 to disable)
        self.artist_minimum_doujin_count = 2
        # Max number of artist/authors a doujin can have to be included
        # (Use 0 to disable)
        self.max_num_artists = 2

    def toJSON(self):
        my_dict = dict(self.__dict__)
        for attrib_name in self.__dict__:
            attrib = getattr(self, attrib_name)
            if isinstance(attrib, set):
                my_dict[attrib_name] = sorted(attrib)
            else:
                my_dict[attrib_name] = attrib
        return my_dict

    @classmethod
    def fromJSON(cls, json_data: dict):
        filters = Filters()
        for key in json_data:
            if not hasattr(filters, key):
                Logger.log_warn(f"Unknown filter key '{key}', skipping...\n")
                continue
            set_correct_data(filters, key, json_data[key])


class Config():
    def __init__(self):
        self.filters = Filters()
        # Series which the user has already seen, thus wishes to include
        self.seen_series: set[str] = set()
        # Series found in the current search that are not included in the 'seen_series'
        self.unread_series: set[str] = set()
        # All the artist an user has favorited, taken from the browser's bookmarks
        self.added_artists: set[str] = set()
        # All doujin titles seen in the currect search
        self.seen_doujinshi: set[str] = set()
        # Datetime of the latest doujin in the last search
        self.stop_datetime: datetime = datetime(1999, 1, 1)
        # If true ignores the stop datetime and keeps searching everything
        self.search_all = False
        # Title of the latest doujin where the last search ended on
        self.stop_title = ""
        # Whether the last search was incomplete, if true the search will resume
        self.search_is_incomplete = False
        # Whether to search for artists that fit the user's preferences as well as doujin
        # Set to false to speed up doujin search
        self.check_artist = True

    def toJSON(self):
        my_dict = dict(self.__dict__)
        for attrib_name in self.__dict__:
            attrib = getattr(self, attrib_name)
            if isinstance(attrib, Filters):
                my_dict[attrib_name] = attrib.toJSON()
            if isinstance(attrib, datetime):
                my_dict[attrib_name] = attrib.strftime('%d/%m/%Y %H:%M')
            elif isinstance(attrib, set):
                my_dict[attrib_name] = sorted(attrib)
        return my_dict

    @classmethod
    def fromJSON(cls, json_data: dict):
        if len(json_data.keys()) == 0:
            return None
        config = Config()
        for key in json_data:
            if key == "filters":
                # print(key, json_data[key])
                data = Filters.fromJSON(json_data[key])
                if data != None:
                    config.filters = data
            elif hasattr(config.filters, key):
                # print(key, json_data[key])
                set_correct_data(config.filters, key, json_data[key])
            elif not hasattr(config, key):
                Logger.log_warn(f"Unknown config key '{key}', skipping...\n")
                continue
            else:
                set_correct_data(config, key, json_data[key])
        return config
