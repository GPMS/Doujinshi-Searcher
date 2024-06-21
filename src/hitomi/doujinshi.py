from datetime import datetime
import urllib.parse

from .config import Filters
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
        desc = ""
        desc += f"{self.name}"

        dict = self.toJSON()
        for key in dict.keys():
            if key == "name":
                continue
            elif key == "exclude_reasons" and len(dict[key]) == 0:
                continue
            if not dict[key]:
                continue
            desc += f"\n\t{key}: {dict[key]}"
        return desc

    def __eq__(self, other):
        if not isinstance(other, Doujinshi):
            return NotImplemented
        return self.url == other.url

    def __ne__(self, other):
        return (not self.__eq__(other))

    def __hash__(self):
        return hash(self.url)

    def could_be_anthology(self):
        '''
        Check whether doujin could be a compilation of multiple doujin
        '''
        return len(self.artists) > 2

    def matches(self, filter: Filters) -> bool:
        '''
        Check if doujin passes all filters set by the Config
        '''
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
            t == self.type for t in filter.must_exclude_type)
        if is_forbidden_type:
            can_add = False
            self.exclude_reasons.append(f"Is of type {self.type}")

        forbidden_tags = CommonItems(self.tags, filter.must_exclude_tags)
        if len(forbidden_tags) > 0:
            can_add = False
            self.exclude_reasons.append(f"Contains tags {forbidden_tags}")

        missing_tags = MissingItems(self.tags, filter.must_include_tags)
        if len(missing_tags) > 0:
            can_add = False
            self.exclude_reasons.append(f"Doesn't contain tags {missing_tags}")

        if filter.must_include_series:
            includes_series = False
            for name in self.series:
                if name == filter.must_include_series:
                    includes_series = True
            if not includes_series:
                can_add = False
                self.exclude_reasons.append(
                    f"Doesn't contain series {filter.must_include_series}")

        missing_characters = MissingItems(
            self.characters, filter.must_include_characters)
        if len(missing_characters) > 0:
            can_add = False
            self.exclude_reasons.append(
                f"Doesn't contain characters {missing_characters}")

        if filter.max_num_artists > 0 and len(self.artists) > filter.max_num_artists:
            can_add = False
            self.exclude_reasons.append(
                f"More than {filter.max_num_artists} artists")

        return can_add

    def toJSON(self):
        # Don't modify original __dict__
        my_dict = dict(self.__dict__)

        # Remove empty entries
        my_dict = {k: v for k, v in my_dict.items() if v}

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
            data = json_data[key]
            correct_type = type(getattr(doujinshi, key))
            if correct_type == datetime:
                setattr(doujinshi, key, datetime.strptime(
                    data, '%d %b %Y, %H:%M'))
            else:
                setattr(doujinshi, key, data)
        return doujinshi
