def get_url_from_series_name(name):
    name = name.replace(" ", "%20")
    url = f"https://hitomi.la/series/{name}-japanese.html"
    return url


def get_url_from_group_name(name):
    name = name.replace("%20", " ")
    url = f"https://hitomi.la/group/{name}-japanese.html"
    return url


def get_artist_name_from_url(url: str) -> str:
    name = url.split("-")[:-1]
    name = "-".join(name).split("/")[-1]
    name = name.replace("%20", " ")
    return name


def get_url_from_artist_name(name: str) -> str:
    url = f"https://hitomi.la/artist/{name.replace(' ','%20')}-japanese.html"
    return url


class Artist:
    def __init__(self, url: str):
        self.name = get_artist_name_from_url(url)
        self.url = url

    def __str__(self):
        return f"({self.name},{self.url})"

    def toJSON(self) -> dict:
        return {
            "name": self.name,
            "url": self.url
        }

    @classmethod
    def to_yaml(cls, dumper, data):
        if not isinstance(data, Artist):
            return
        return dumper.represent_mapping("tag:yaml.org,2002:map", data.toJSON())

    @classmethod
    def fromJSON(cls, json_data: dict):
        if len(json_data.keys()) == 0:
            return None
        artist = Artist(json_data["url"])
        return artist
