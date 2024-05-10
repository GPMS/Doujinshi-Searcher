from datetime import datetime

from .logger import Logger


class Config():
    def __init__(self):
        self.language = ["日本語", "japanese"]
        # Types a doujin must not contain (doujinshi, original, game cg, etc)
        self.must_exclude_type = set()
        # Tags a doujin must have
        self.must_include_tags = set()
        # Tags a doujin must not have
        self.must_exclude_tags = set()
        # Characters that must be present in the doujin for it to be included
        self.must_include_characters = set()
        # Only doujin that included this series are included.
        # Leave it blank for all series
        self.must_include_series = ""
        # Minimum number of doujin that fit the user's preference a author must have to be included
        # Use 0 to disable
        self.artist_minimum_doujin_count = 2
        # Max number of artist/authors a doujin can have to be included
        # Use 0 to disable
        self.max_num_artists = 2
        # Series which the user has already seen, thus wishes to include
        self.seen_series: set[str] = set()
        # Series found in the current search that are not included in the 'seen_series'
        self.unread_series: set[str] = set()
        # All the artist an user has favorited, taken from the browser's bookmarks
        self.added_artists: set[str] = set()
        # All doujin titles seen in the currect search
        self.seen_doujinshi: set[str] = set()
        # Datetime of the latest doujin where the last search ended on
        self.stop_datetime: datetime = datetime(1999, 1, 1)
        # Title of the latest doujin where the last search ended on
        self.stop_title = ""
        # Whether the last search was incomplete, if true the search will resume
        self.incomplete = False
        # Whether to search for artists that fit the user's preferences as well as doujin
        # Set to false to speed up doujin search
        self.check_artist = True

    def toJSON(self):
        my_dict = dict(self.__dict__)
        for attrib_name in self.__dict__:
            attrib = getattr(self, attrib_name)
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
            if not hasattr(config, key):
                Logger.log_warn(f"Unknown config key '{key}', skipping...\n")
                continue
            attrib = getattr(config, key)
            if isinstance(attrib, datetime):
                setattr(config, key, datetime.strptime(
                    json_data[key], '%d/%m/%Y %H:%M'))
            elif isinstance(attrib, set):
                setattr(config, key, set(json_data[key]))
            elif isinstance(attrib, int) and not isinstance(attrib, bool):
                setattr(config, key, int(json_data[key]))
            else:
                setattr(config, key, json_data[key])
        return config
