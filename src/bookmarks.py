import codecs
import os
from hitomi import Artist, Doujinshi, Config, get_artist_name_from_url, Logger

import firefox
import chrome


def load_artists(config: Config,
                 browser: str):

    ARTISTS_FOLDER = os.getenv("ARTISTS_FOLDER")
    BEST_ARTISTS_FOLDER = os.getenv("BEST_ARTISTS_FOLDER")

    if ARTISTS_FOLDER:
        artists: list[str] = []
        was_found: bool = False
        if browser == 'firefox':
            artists, was_found = firefox.load_bookmarks(
                f'toolbar/{ARTISTS_FOLDER}')
        elif browser == 'chrome':
            artists, was_found = chrome.load_bookmarks(ARTISTS_FOLDER)

        if was_found:
            for artist_url in artists:
                artist_name = get_artist_name_from_url(artist_url)
                config.added_artists.add(artist_name)
    else:
        Logger.log_warn(
            "Set 'ARTIST_FOLDER' variable in .env to load the added_artists list from your bookmarks")

    if BEST_ARTISTS_FOLDER:
        best_artists: list[str] = []
        was_found = False

        if browser == 'firefox':
            best_artists, was_found = firefox.load_bookmarks(
                f'toolbar/{BEST_ARTISTS_FOLDER}')
        elif browser == 'chrome':
            best_artists, was_found = chrome.load_bookmarks(
                BEST_ARTISTS_FOLDER)

        if was_found:
            for artist_url in best_artists:
                artist_name = get_artist_name_from_url(artist_url)
                config.added_artists.add(artist_name)
    else:
        Logger.log_warn(
            "Set 'BEST_ARTIST_FOLDER' variable in .env to load the added_artists list from your bookmarks")


def export_lists(config: Config,
                 doujinshi_list: list[Doujinshi],
                 artist_list: list[Artist]):

    def add_entry(file, level: int, entry: Doujinshi | Artist):
        tabs = '\t'*level
        if isinstance(entry, Doujinshi):
            creators = ''
            if len(entry.artists) > 0:
                creators = ",".join(entry.artists)
                creators += ' | '
            elif len(entry.groups) > 0:
                creators = ",".join(entry.groups)
                creators += ' | '
            file.write(
                f'{tabs}<DT><A HREF="{entry.url}">{creators}{entry.name}</A>\n')
        elif isinstance(entry, Artist):
            file.write(f'{tabs}<DT><A HREF="{entry.url}">{entry.name}</A>\n')

    def add_folder(file, level: int, folder_name: str, contents: list):
        if len(contents) == 0:
            return
        tabs = '\t'*level
        file.write(
            f'{tabs}<DT><H3>{folder_name}</H3>\n'
            f'{tabs}<DL><p>\n'
        )
        for entry in contents:
            add_entry(file, level+1, entry)
        tabs = '\t'*level
        file.write(f'{tabs}</DL><p>\n')

    def group_by_creator(doujins: list[Doujinshi]):
        artist_doujin_count: dict[str, int] = {}
        for doujinshi in doujinshi_list:
            if len(doujinshi.artists) > 0:
                for artist in doujinshi.artists:
                    if artist not in artist_doujin_count.keys():
                        artist_doujin_count[artist] = 1
                    else:
                        artist_doujin_count[artist] += 1
            else:
                for group in doujinshi.groups:
                    if group not in artist_doujin_count.keys():
                        artist_doujin_count[group] = 1
                    else:
                        artist_doujin_count[group] += 1
        # Organize doujin by artist (if multiple use the one with most doujin)
        artist_doujin_list: dict[str, list[Doujinshi]] = {}
        for doujinshi in doujinshi_list:
            # If doujin has many artists save it as an anthology
            if len(doujinshi.artists) > 2:
                if 'new-anthologies' not in artist_doujin_list:
                    artist_doujin_list['new-anthologies'] = []
                artist_doujin_list['new-anthologies'].append(doujinshi)
            else:
                # Get artist with most doujin (most likely to be actual artist) or undefined
                artist_with_most_doujin = 'undefined'
                if len(doujinshi.artists) > 0:
                    artist_with_most_doujin = max(
                        doujinshi.artists, key=lambda k: artist_doujin_count[k])
                elif len(doujinshi.groups) > 0:
                    artist_with_most_doujin = max(
                        doujinshi.groups, key=lambda k: artist_doujin_count[k])
                if artist_with_most_doujin != 'undefined' and artist_doujin_count[artist_with_most_doujin] == 1:
                    artist_with_most_doujin = 'undefined'
                # Add doujin to artist
                if artist_with_most_doujin not in artist_doujin_list:
                    artist_doujin_list[artist_with_most_doujin] = []
                artist_doujin_list[artist_with_most_doujin].append(doujinshi)
        return artist_doujin_list

    if config.must_include_series:
        filepath = f"output/{config.must_include_series.replace(' ', '_')}.html"
    else:
        filepath = f"output/bookmarks.html"

    if len(doujinshi_list) == 0:
        Logger.log("No doujin to export\n")
    if len(artist_list) == 0:
        Logger.log("No artist to export\n")
    if len(doujinshi_list) == 0 and len(artist_list) == 0:
        Logger.log("Nothing to export\n")
        with open(filepath, "w") as f:
            f.write("")
        return
    with codecs.open(filepath, 'w', 'utf-8') as f:
        f.write(
            '<!DOCTYPE NETSCAPE-Bookmark-file-1>\n'
            '<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">\n'
            '<TITLE>Bookmarks</TITLE>\n'
            '<H1>Bookmarks</H1>\n'
            '<DL><p>\n'
        )
        if len(doujinshi_list) > 0:
            if config.must_include_series:
                # If we only have one single series use it as the name
                # for the folder
                f.write(
                    f'\t<DT><H3>{config.must_include_series}</H3>\n'
                    '\t<DL><p>\n'
                )
            else:
                f.write(
                    '\t<DT><H3>new-doujinshi</H3>\n'
                    '\t<DL><p>\n'
                )
            if len(doujinshi_list) == 1:
                add_entry(f, 2, doujinshi_list[0])
            else:
                groups = group_by_creator(doujinshi_list)
                if len(groups) == 1:
                    # No need to create folders if there's only one group
                    # Just add it in place
                    sole_creator_name = next(iter(groups))
                    sole_group = groups[sole_creator_name]
                    sole_group.sort(key=lambda d: d.name)
                    for doujin in sole_group:
                        add_entry(f, 2, doujin)
                else:
                    for creator_name in groups:
                        groups[creator_name].sort(key=lambda d: d.name)
                        add_folder(f, 2, creator_name, groups[creator_name])
            f.write(
                '\t</DL><p>\n'
            )
        add_folder(f, 1, 'new-artists', artist_list)
        f.write(
            '</DL><p>\n'
        )
