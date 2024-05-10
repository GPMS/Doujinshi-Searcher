import sys
import traceback
import datetime
import time
import argparse
import os
import shutil
from pathlib import Path
from dotenv import load_dotenv

import bookmarks
import serialization
import hitomi

dotenv_path = Path(".", ".env")
load_dotenv(dotenv_path=dotenv_path)
BROWSER_NAME = os.getenv("BROWSER_NAME")


def load_config():
    try:
        config = serialization.load_config_file()
        if config == None:
            raise Exception("Empty config")
        if not config.incomplete:
            config.seen_doujinshi.clear()
        hitomi.Logger.log("Config loaded\n")
    except FileNotFoundError:
        hitomi.Logger.log("No config, loading default\n")
        config = hitomi.Config()
        config.max_num_artists = 0
        config.must_exclude_type = set([
            "game cg"
        ])
        config.must_exclude_tags = set([
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
        finished_file_path = f"{serialization.CONFIG_PATH}/finished.txt"
        stop_file_path = f"{serialization.CONFIG_PATH}/stop.txt"
        with open(finished_file_path) as f:
            lines = f.read().splitlines()
            for line in lines:
                config.seen_series.add(line.lower())
        with open(stop_file_path, encoding="utf8") as f:
            lines = f.read().splitlines()
            config.stop_datetime = datetime.datetime.strptime(
                lines[0], "%d/%m/%Y %H:%M")
            config.stop_title = lines[1]

    hitomi.Logger.log("Loading artists\n")
    if BROWSER_NAME:
        bookmarks.load_artists(config, BROWSER_NAME)
    else:
        hitomi.Logger.log_warn(
            "Set variable 'BROWSER_NAME' in .env to load added_artists and read_doujinshi from your bookmarks")

    serialization.dump_config_file(config)
    return config


def remove_repeated_entries(data_list):
    if len(data_list) <= 1:
        return data_list
    unique_list = []
    seen_url = set()
    for data in data_list:
        if data.url in seen_url:
            hitomi.Logger.log(f"Repeated {data.url}\n")
        else:
            seen_url.add(data.url)
            unique_list.append(data)
    data_list = unique_list


def dump_lists(lists: dict[str, list]):
    hitomi.Logger.log(
        f"TOTAL: {len(lists[f'doujin_included'])} doujinshi and {len(lists['artist_included'])} artists\n")
    hitomi.Logger.log("Dumping lists...\n")
    for dir in lists:
        if len(lists[dir]) != 0:
            lists[dir].sort(key=lambda x: x.name)
            remove_repeated_entries(lists[dir])
        serialization.dump_list(dir, lists[dir])


def load_lists(config: hitomi.Config) -> dict:
    lists = {}
    if config.incomplete:
        hitomi.Logger.log("Loading previous session\n")
        lists["doujin_included"] = serialization.load_doujinshi_list(
            "doujin_included")
        lists["doujin_excluded"] = serialization.load_doujinshi_list(
            "doujin_excluded")
        lists["artist_included"] = serialization.load_artist_list(
            "artist_included")
        lists["artist_excluded"] = serialization.load_artist_list(
            "doujin_excluded")
        hitomi.Logger.log(f"{len(config.seen_doujinshi)} seen doujin\n")
        hitomi.Logger.log(f'\tincluded: {len(lists["doujin_included"])}\n')
        hitomi.Logger.log(f'\texcluded: {len(lists["doujin_excluded"])}\n')
        hitomi.Logger.log("artists\n")
        hitomi.Logger.log(f'\tincluded: {len(lists["artist_included"])}\n')
        hitomi.Logger.log(f'\texcluded: {len(lists["artist_excluded"])}\n')
    else:
        lists["doujin_included"] = []
        lists["doujin_excluded"] = []
        lists["artist_included"] = []
        lists["artist_excluded"] = []
    return lists


def search_artist_page(config: hitomi.Config,
                       url: str,
                       lists: dict = {},
                       from_homepage=False,
                       navigator: hitomi.Navigator | None = None) -> bool:
    artist = hitomi.Artist(url)
    config = config
    if not lists:
        lists["doujin_included_list"] = []
        lists["doujin_excluded_list"] = []
    seen_created_titles = set()
    can_add = False
    hitomi.Logger.log(f"\tSearching artist page: {url}\n")
    hitomi.Logger.log("\t\t")
    if navigator is None:
        navigator = hitomi.Navigator()
    iterator = hitomi.DoujinIterator(navigator, url)
    for i, doujin in iterator.next():
        need_reload = False
        can_add_doujin = doujin.can_add(config)
        # Deep search
        if can_add_doujin and (config.must_include_characters != 0 or len(doujin.artists) == 0):
            iterator.get_extra_doujin_info(doujin)
            can_add_doujin = doujin.can_add(config)
            need_reload = True
        is_creator = (len(doujin.artists) in [1, 2] or
                      (len(doujin.artists) == 0 and len(doujin.groups) == 1))
        if can_add_doujin:
            lists["doujin_included_list"].append(doujin)
            if is_creator and doujin.name not in seen_created_titles:
                seen_created_titles.add(doujin.name)
                hitomi.Logger.log("\t\tNew created title\n")
        else:
            lists["doujin_excluded_list"].append(doujin)
        if iterator.is_last_of_page(i):
            hitomi.Logger.log("\t\t")
        if from_homepage and len(seen_created_titles) >= config.artist_minimum_doujin_count:
            can_add = True
            break
        if need_reload:
            iterator.load_web_elements()
    return can_add


def search_homepage(config: hitomi.Config,
                    lists: dict[str, list]):
    def check_artist_or_group(url: str):
        # previous_url = hitomi.Navigator.get_current_url()
        navigator.open_new_tab()

        can_add = search_artist_page(
            config, url, from_homepage=True, navigator=navigator)
        artist = hitomi.Artist(url)

        # hitomi.Navigator.load(previous_url)
        navigator.close_tab()

        type = "group" if "group" in url else "artist"
        if can_add:
            hitomi.Logger.log(f"\t\t+ {type}\n")
            lists["artist_included"].append(artist)
        else:
            hitomi.Logger.log(f"\t\t- {type}\n")
            lists["artist_excluded"].append(artist)

        seen_artists.add(artist.name)

    navigator = hitomi.Navigator()

    url = hitomi.generate_url(config)
    hitomi.Logger.log(f"Searching page: {url}\n")

    count = 0
    lists = lists
    config = config
    is_start = True
    new_stop_datetime = config.stop_datetime
    new_stop_title = str(config.stop_title)
    seen_artists = set(config.added_artists)

    iterator = hitomi.DoujinIterator(navigator, url)
    for i, doujin in iterator.next():
        is_searching_specific_series = config.must_include_series != ""
        need_reload = False
        count += 1
        hitomi.Logger.log(f"{i} ({count}): {doujin.name}\n")

        # Save date and title of the latest doujin
        if is_start and not is_searching_specific_series:
            hitomi.Logger.log(f"\tNew stop daytime: {doujin.date}\n")
            new_stop_datetime = doujin.date
            new_stop_title = doujin.name
            is_start = False

        # Reached last updated date?
        # If so then all doujin from here on have already been seen
        # If searching for specific series, ignore and keep going
        if doujin.date <= config.stop_datetime and not is_searching_specific_series:
            # Update date and exit
            hitomi.Logger.log(f"\tStop at {doujin.date} {doujin.name}\n")
            config.stop_datetime = new_stop_datetime
            config.stop_title = new_stop_title
            break

        # Ignore doujin that have already been checked
        if doujin.url in config.seen_doujinshi:
            hitomi.Logger.log("\tskipped\n")
            continue

        # See if can exclude doujin
        can_add = doujin.can_add(config)
        if can_add and (len(config.must_include_characters) != 0
                        or len(doujin.artists) == 0):
            # Can't exclude it yet? Look deeper and check again
            iterator.get_extra_doujin_info(doujin)
            need_reload = True
            can_add = doujin.can_add(config)

        if can_add:
            # Check if is read series and add if so add it
            is_read_series = False
            includes_series = False
            if config.must_include_series:
                for name in doujin.series:
                    if name == config.must_include_series:
                        includes_series = True
            included_seen_series = [
                s for s in doujin.series if s in config.seen_series]
            if includes_series or len(included_seen_series) > 0:
                lists["doujin_included"].append(doujin)
                is_read_series = True
                if includes_series:
                    hitomi.Logger.log(
                        f"\t+ is from series {config.must_include_series}\n")
                if len(included_seen_series) > 0:
                    hitomi.Logger.log(
                        f"\t+ is from seen series: {included_seen_series}\n")
            # Check artist/group
            is_original = (len(doujin.series) == 0) or (
                doujin.series[0] == "original") or (doujin.series[0] == "n/a")
            if is_original or is_read_series:
                # Check artist
                if config.check_artist:
                    if len(doujin.artists) > 0:
                        for artist_name in doujin.artists:
                            if artist_name in seen_artists:
                                if artist_name == "hase yuu":
                                    hitomi.Logger.log(
                                        f"\t+ hase yuu doujin: {doujin.name}\n")
                                    lists["doujin_included"].append(doujin)
                                hitomi.Logger.log(
                                    f"\tArtist seen already: {artist_name}\n")
                                continue
                            artist_url = hitomi.get_url_from_artist_name(
                                artist_name)
                            check_artist_or_group(artist_url)
                    # No artist, check group instead
                    elif len(doujin.groups) > 0:
                        for group_name in doujin.groups:
                            if group_name in seen_artists:
                                hitomi.Logger.log(
                                    f"\tGroup seen already: {group_name}\n")
                                continue
                            group_url = hitomi.get_url_from_group_name(
                                group_name)
                            check_artist_or_group(group_url)
                # Original doujin with neither artist nor group, add
                elif not is_read_series:
                    hitomi.Logger.log(f"\t+ no artist or group\n")
                    lists["doujin_included"].append(doujin)
            # Ignore unread series
            else:
                hitomi.Logger.log(f"\t- Unread series: {doujin.series}\n")
                unread_series = []
                for series_name in doujin.series:
                    if series_name not in config.seen_series:
                        config.unread_series.add(series_name)
                        unread_series.append(series_name)
                doujin.exclude_reasons.append(f"Unread series {unread_series}")
                lists["doujin_excluded"].append(doujin)
        # Add excluded doujin to separate list
        else:
            hitomi.Logger.log("\t- Cant add\n")
            lists["doujin_excluded"].append(doujin)

        # Finished checking doujin, add it to seen list to ignore it later if it comes again
        # Specially useful if the program crashes midway
        config.seen_doujinshi.add(doujin.url)
        if need_reload:
            iterator.load_web_elements()

    if len(config.unread_series) != 0:
        going_to_read = []
        with open("later.txt") as f:
            going_to_read = [line.rstrip() for line in f]
        going_to_read = set(going_to_read)
        if len(going_to_read) == 0:
            hitomi.Logger.log(f"Unread Series:{config.unread_series}\n")
        else:
            hitomi.Logger.log(
                f"Unread Series:{config.unread_series.difference(going_to_read)}\n")


def check_seen_series_link():
    config = load_config()
    try:
        navigator = hitomi.Navigator()
        correct_series_names = set()
        incorrect_series_names = []
        num_series = len(config.seen_series)
        current_index = 0
        for series_name in config.seen_series:
            current_index += 1
            hitomi.Logger.log(f"{current_index}/{num_series}\n")
            series_url = hitomi.get_url_from_series_name(series_name)
            if navigator.can_load_url(series_url):
                correct_series_names.add(series_name)
            else:
                incorrect_series_names.append(series_name)
        config.seen_series = correct_series_names
        serialization.dump_config_file(config)
        hitomi.Logger.log(f"Invalid series names: {incorrect_series_names}\n")
    except Exception as e:
        hitomi.Logger.log("Caught exception, dumping lists...\n")
        serialization.dump_config_file(config)
        traceback.print_exception(e)


def search_doujin(config: hitomi.Config):
    lists = load_lists(config)
    start_time = time.time()
    try:
        config.incomplete = True
        search_homepage(config, lists)
        dump_lists(lists)
        bookmarks.export_lists(config,
                               lists["doujin_included"],
                               lists["artist_included"])
        config.incomplete = False
        config.seen_doujinshi.clear()
        config.unread_series.clear()
        serialization.dump_config_file(config, True)
    except KeyboardInterrupt:
        hitomi.Logger.log_warn("interrupted, dumping lists...\n")
        dump_lists(lists)
        serialization.dump_config_file(config)
    except SystemExit:
        sys.exit()
    except Exception as e:
        hitomi.Logger.log_error("Caught exception, dumping lists...\n")
        dump_lists(lists)
        serialization.dump_config_file(config)
        traceback.print_exception(e)
    elapsed_seconds = time.time() - start_time
    hitomi.Logger.log(
        f"Total time: {datetime.timedelta(seconds=elapsed_seconds)}\n")


def backup_files():
    if not os.path.isdir(serialization.OUTPUT_DIR):
        return
    try:
        os.mkdir("output-backup")
    except FileExistsError:
        pass
    for file in os.listdir(serialization.OUTPUT_DIR):
        src = os.path.join(serialization.OUTPUT_DIR, file)
        dst = os.path.join(serialization.OUTPUT_BACKUP_DIR, file)
        shutil.copy(src, dst)
    shutil.copy(serialization.CONFIG_FILE, serialization.CONFIG_BACKUP_FILE)


def look_for_all_series():
    with open("check_again.txt") as f:
        series = [line.rstrip() for line in f]

    config = None
    lists = {}

    use_terminal = False
    if use_terminal:
        hitomi.Logger.use_terminal()

    try:
        for name in series:
            hitomi.Logger.log(name)
            if not use_terminal:
                hitomi.Logger.start_logger(f"log-{name.replace(' ', '_')}.txt")
            config = load_config()
            lists = load_lists(config)
            config.must_include_series = name
            config.incomplete = True
            search_homepage(config, lists)
            dump_lists(lists)
            num_doujins = len(lists["doujin_included"])
            bookmarks.export_lists(config,
                                   lists["doujin_included"],
                                   lists["artist_included"])
            config.incomplete = False
            config.seen_doujinshi.clear()
            config.unread_series.clear()
            serialization.dump_config_file(config, True)
    except KeyboardInterrupt:
        hitomi.Logger.log_warn("interrupted, dumping lists...\n")
        dump_lists(lists)
        serialization.dump_config_file(config)
    except SystemExit:
        sys.exit()
    except Exception as e:
        hitomi.Logger.log_error("Caught exception, dumping lists...\n")
        dump_lists(lists)
        serialization.dump_config_file(config)
        traceback.print_exception(e)
    finally:
        if not use_terminal:
            hitomi.Logger.stop_logger()


def main():
    dotenv_path = Path("../.env")
    load_dotenv(dotenv_path=dotenv_path)

    parser = argparse.ArgumentParser(
        prog="SearchDoujinshi",
        description="Scrape doujinshi from hitomi.la")
    parser.add_argument("--term", action="store_false",
                        help="Print log to terminal instead to a log file")
    parser.add_argument("--check", action="store_true",
                        help="check if links in seen_series are correct")
    parser.add_argument("--series",
                        help="Search only for doujinshi in the given series")
    args = parser.parse_args()
    if args.term:
        hitomi.Logger.use_terminal()
    else:
        hitomi.Logger.start_logger()
    if args.check:
        check_seen_series_link()
    else:
        backup_files()
        config = load_config()
        if args.series:
            config.must_include_series = args.series
        search_doujin(config)
    if not args.term:
        hitomi.Logger.stop_logger()


if __name__ == "__main__":
    main()
