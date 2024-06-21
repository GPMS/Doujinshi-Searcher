import codecs
from os import getenv
from hitomi import Artist, Doujinshi, get_artist_name_from_url, Logger

from . import firefox
from . import chrome
from . import brave


def load_folder(path: str, browser: str):
    entries: list[str] = []
    was_found: bool = False

    if browser == "firefox":
        entries, was_found = firefox.load_bookmarks(f"toolbars/{path}")
    elif browser == "chrome":
        entries, was_found = chrome.load_bookmarks(path)
    elif browser == "brave":
        entries, was_found = brave.load_bookmarks(path)

    if not was_found:
        Logger.log_warn(f"bookmark folder '{path}' was not found")

    return entries


def load_favorite_doujin(browser: str):
    FAVORITE_DOUJIN_FOLDER = getenv("FAVORITE_DOUJIN_FOLDER")

    if not FAVORITE_DOUJIN_FOLDER:
        Logger.log_warn("Set 'FAVORITE DOUJIN FOLDER' variable in .env")
        return

    return load_folder(FAVORITE_DOUJIN_FOLDER, browser)


def load_artists(browser: str):

    ARTISTS_FOLDER = getenv("ARTISTS_FOLDER")
    BEST_ARTISTS_FOLDER = getenv("BEST_ARTISTS_FOLDER")

    artist_list: set[str] = set()

    if not ARTISTS_FOLDER:
        Logger.log_warn(
            "Set 'ARTIST_FOLDER' variable in .env to load the added_artists list from your bookmarks")
    else:
        artists: list[str] = load_folder(ARTISTS_FOLDER, browser)
        for artist_url in artists:
            artist_name = get_artist_name_from_url(artist_url)
            artist_list.add(artist_name)

    if not BEST_ARTISTS_FOLDER:
        Logger.log_warn(
            "Set 'BEST_ARTIST_FOLDER' variable in .env to load the added_artists list from your bookmarks")
    else:
        best_artists = load_folder(BEST_ARTISTS_FOLDER, browser)
        for artist_url in best_artists:
            artist_name = get_artist_name_from_url(artist_url)
            artist_list.add(artist_name)

    return artist_list


class BookmarkNode():
    def __init__(self, name: str, url=""):
        self.children: list[BookmarkNode] = []
        self.name = name
        self.url = url

    def add_folder(self, folder):
        if not isinstance(folder, BookmarkNode):
            raise (Exception("Trying to add something else as folder"))
        if folder.url or self.url:
            raise (Exception("Trying to add bookmark as folder"))
        self.children.append(folder)

    def add_url(self, name: str, url: str):
        new_node = BookmarkNode(name, url)
        self.children.append(new_node)


def get_bookmark_name(entry: Doujinshi | Artist, creator_name: str | None = None):
    safe_name = entry.name.replace('<',  '&lt;').replace('>', '&gt;')

    if isinstance(entry, Doujinshi):
        creators = None
        if len(entry.artists) > 0:
            creators = list(entry.artists)
        elif len(entry.groups) > 0:
            creators = list(entry.groups)

        if creators == None:
            return entry.name

        if creator_name != None:
            creators.remove(creator_name)
            return f"{creator_name},{','.join(creators)} | {safe_name}"
        return f"{','.join(creators)} | {safe_name}"
    else:
        return safe_name


def bookmark_tree_to_file(tree_root: BookmarkNode, file_path: str):
    def write_nodes(f, node: BookmarkNode, indentation_count=1):
        tabs = "\t" * indentation_count
        if len(node.children) > 0:
            f.write(f'{tabs}<DT><H3>{node.name}</H3>\n'
                    f'{tabs}<DL><p>\n')
            for child in node.children:
                write_nodes(f, child, indentation_count + 1)
            f.write(f'{tabs}</DL><p>\n')
        else:
            f.write(f'{tabs}<DT><A HREF="{node.url}">{node.name}</A>\n')

    with codecs.open(file_path, 'w', 'utf-8') as f:
        f.write(
            '<!DOCTYPE NETSCAPE-Bookmark-file-1>\n'
            '<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">\n'
            '<TITLE>Bookmarks</TITLE>\n'
            '<H1>Bookmarks</H1>\n'
            '<DL><p>\n'
        )
        for child in tree_root.children:
            write_nodes(f, child)
        f.write(
            '</DL><p>\n'
        )


def export_lists(doujin_list: list[Doujinshi],
                 artist_list: list[Artist],
                 must_include_series: str = "",
                 group=True):

    def group_doujin(doujin_folder: BookmarkNode, doujin_list: list[Doujinshi]):
        def add_doujin_to_creator(doujin: Doujinshi, creator_name: str):
            if creator_name not in group_list:
                group_list[creator_name] = []
            group_list[creator_name].append(doujin)

        creator_doujin_count: dict[str, int] = {}
        for doujin in doujin_list:
            creators = None
            if len(doujin.artists) > 0:
                creators = doujin.artists
            elif len(doujin.groups) > 0:
                creators = doujin.groups
            if creators is None:
                continue
            for creator in creators:
                if creator not in creator_doujin_count.keys():
                    creator_doujin_count[creator] = 0
                creator_doujin_count[creator] += 1
        # Organize doujin by creator (if multiple use the one with most doujin)
        group_list: dict[str, list[Doujinshi]] = {}
        for doujin in doujin_list:
            creators = None
            if len(doujin.artists) > 0:
                creators = doujin.artists
            elif len(doujin.groups) > 0:
                creators = doujin.groups
            if creators is None:
                add_doujin_to_creator(doujin, "undefined")
                continue
            if len(creators) == 1:
                add_doujin_to_creator(doujin, creators[0])
            elif len(creators) > 3:
                add_doujin_to_creator(doujin, "new-anthologies")
            else:
                # 2 or 3 creators: add to the one with most doujin
                creator_with_most_doujin = max(
                    creators, key=lambda k: creator_doujin_count[k])
                if creator_doujin_count[creator_with_most_doujin] == 1:
                    creator_with_most_doujin = 'undefined'
                # Add doujin to artist
                add_doujin_to_creator(doujin, creator_with_most_doujin)
        # Add folders and doujin to bookmark tree
        for creator_name in group_list:
            group_list[creator_name].sort(key=lambda d: d.name)

            location = doujin_folder  # Place where bookmark will be stored
            if creator_name in ["new-anthologies", "undefined"]:
                location = BookmarkNode(creator_name)
                doujin_folder.add_folder(location)

            for doujin in group_list[creator_name]:
                name = get_bookmark_name(doujin)
                location.add_url(name, doujin.url)

    if len(doujin_list) == 0:
        Logger.log("No doujin to export\n")

    if len(artist_list) == 0:
        Logger.log("No artist to export\n")

    if len(doujin_list) == 0 and len(artist_list) == 0:
        Logger.log("Nothing to export\n")
        return

    root = BookmarkNode("root")
    if len(doujin_list) > 0:
        folder_name = must_include_series if must_include_series else "new-doujinshi"
        doujin_folder = BookmarkNode(folder_name)
        if len(doujin_list) == 1:
            doujin = doujin_list[0]
            doujin_folder.add_url(doujin.name, doujin.url)
        else:
            if group:
                group_doujin(doujin_folder, doujin_list)
            else:
                anthologies_folder = None
                for doujin in doujin_list:
                    if len(doujin.artists) > 3:
                        if anthologies_folder is None:
                            anthologies_folder = BookmarkNode(
                                "new-anthologies")
                            doujin_folder.add_folder(anthologies_folder)
                        anthologies_folder.add_url(doujin.name, doujin.url)
                    else:
                        name = get_bookmark_name(doujin)
                        doujin_folder.add_url(name, doujin.url)
        root.add_folder(doujin_folder)
    if len(artist_list) > 0:
        artists_folder = BookmarkNode("new-artists")
        for artist in artist_list:
            artists_folder.add_url(artist.name, artist.url)
        root.add_folder(artists_folder)

    file_name = ""
    if must_include_series:
        file_name = must_include_series.replace(' ', '_')
    else:
        file_name = 'bookmarks'
    bookmark_tree_to_file(root, f"output/{file_name}.html")
