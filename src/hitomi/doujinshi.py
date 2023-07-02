from datetime import datetime

from .config import Config
from .logger import Logger


class Doujinshi:
    def __init__(self):
        self.url = ""
        self.name = ""
        self.type = ""
        self.groups: list[str] = []
        self.artists: list[str] = []
        self.series: list[str] = []
        self.characters: list[str] = []
        self.tags: list[str] = []
        self.date = datetime(1900, 1, 1)
        self.exclude_reasons: list[str] = []

    def __str__(self):
        desc = f"""{self.name}\
            \n\tArtists:{self.artists}\
            \n\tGroups:{self.groups}\
            \n\tSeries:{self.series}\
            \n\tType:{self.type}\
            \n\tCharacters:{self.characters}\
            \n\tTags:{self.tags}]\
            \n\tDate:{self.date.strftime('%d %b %Y, %H:%M')}"""
        if len(self.exclude_reasons) > 0:
            desc += f"\n\tExclude Reason: {self.exclude_reasons}"
        return desc

    def can_add(self, config: Config) -> bool:
        def CommonItems(lst, items):
            common = []
            for item in items:
                for element in lst:
                    if item == element:
                        common.append(item)
                        break
            return common

        def MissingItems(lst, items):
            missing = []
            for item in items:
                is_included = False
                for element in lst:
                    if item == element:
                        is_included = True
                        break
                if not is_included:
                    missing.append(item)
            return missing

        can_add = True

        is_forbidden_type = any(
            t == self.type for t in config.must_exclude_type)
        if is_forbidden_type:
            can_add = False
            self.exclude_reasons.append(f"Is of type {self.type}")

        forbidden_tags = CommonItems(self.tags, config.must_exclude_tags)
        if len(forbidden_tags) > 0:
            can_add = False
            self.exclude_reasons.append(f"Contains tags {forbidden_tags}")

        missing_tags = MissingItems(self.tags, config.must_include_tags)
        if len(missing_tags) > 0:
            can_add = False
            self.exclude_reasons.append(f"Doesn't contain tags {missing_tags}")

        if config.must_include_series:
            includes_series = False
            for name in self.series:
                if name == config.must_include_series:
                    includes_series = True
            if not includes_series:
                can_add = False
                self.exclude_reasons.append(
                    f"Doesn't contain series {config.must_include_series}")

        missing_characters = MissingItems(
            self.characters, config.must_include_characters)
        if len(missing_characters) > 0:
            can_add = False
            self.exclude_reasons.append(
                f"Doesn't contain characters {missing_characters}")

        if config.max_num_artists > 0 and len(self.artists) > config.max_num_artists:
            can_add = False
            self.exclude_reasons.append(
                f"More than {config.max_num_artists} artists")

        return can_add

    def toJSON(self):
        my_dict = dict(self.__dict__)
        my_dict['date'] = self.date.strftime('%d %b %Y, %H:%M')
        return my_dict

    @classmethod
    def fromJSON(cls, json_data: dict):
        if len(json_data.keys()) == 0:
            return None

        doujinshi = Doujinshi()
        for key in json_data:
            if not hasattr(doujinshi, key):
                Logger.log_warn(
                    f"Unknown doujinshi key '{key}', skipping...\n")
                continue
            variable = getattr(doujinshi, key)
            if isinstance(variable, datetime):
                setattr(doujinshi, key, datetime.strptime(
                    json_data[key], '%d %b %Y, %H:%M'))
            else:
                setattr(doujinshi, key, json_data[key])
        return doujinshi
