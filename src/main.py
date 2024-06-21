from sys import exit
from traceback import print_exception
from datetime import datetime, timedelta
from time import time
from argparse import ArgumentParser
from os import getenv
from pathlib import Path
from dotenv import load_dotenv
from urllib.parse import unquote
import shutil

import bookmarks
import serialization
import hitomi


############################## GLOBALS ##############################
# Environmental Variables
dotenv_path = Path(".", ".env")
load_dotenv(dotenv_path=dotenv_path)
BROWSER_NAME = getenv("BROWSER_NAME")
# Paths
WORKSPACE_DIR = Path(__file__).parent.parent.resolve()
OUTPUT_DIR = Path(WORKSPACE_DIR, "output")
OUTPUT_BACKUP_DIR = Path(WORKSPACE_DIR, "output-backup")
CONFIG_FILE = Path(WORKSPACE_DIR, "config")
CONFIG_BACKUP_FILE = Path(WORKSPACE_DIR, "config-backup.json")
# Services
serializer = serialization.JsonSerializer()
#####################################################################


def load_config():
    config = serializer.load_config_file(CONFIG_FILE)
    if config == None:
        hitomi.Logger.log("No config, loading default\n")
        config = hitomi.Config()
    if not config.search_is_incomplete:
        config.seen_doujinshi.clear()
    hitomi.Logger.log("Loading artists\n")
    if BROWSER_NAME:
        config.added_artists = bookmarks.load_artists(BROWSER_NAME)
    else:
        hitomi.Logger.log_warn(
            "Set variable 'BROWSER_NAME' in .env to load added_artists and read_doujinshi from your bookmarks")
    dump_config_file(config)
    hitomi.Logger.log("Config loaded\n")
    return config


def dump_config_file(config: hitomi.Config | None):
    if not config:
        return
    serializer.dump_to_file(CONFIG_FILE, config)


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


def dump_list(filename: str, data: list):
    OUTPUT_DIR.mkdir(exist_ok=True)
    path = Path(OUTPUT_DIR, f"{filename}")
    serializer.dump_to_file(path, data)


def dump_lists(lists: dict[str, list]):
    hitomi.Logger.log(
        f"TOTAL: {len(lists[f'doujin_included'])} doujinshi and {len(lists['artist_included'])} artists\n")
    hitomi.Logger.log("Dumping lists...\n")
    for dir in lists:
        if len(lists[dir]) != 0:
            lists[dir].sort(key=lambda x: x.name)
            remove_repeated_entries(lists[dir])
        dump_list(dir, lists[dir])


def load_lists(config: hitomi.Config) -> dict:
    lists = {}
    if config.search_is_incomplete:
        hitomi.Logger.log("Loading previous session\n")
        lists["doujin_included"] = serializer.load_doujinshi_list(
            OUTPUT_DIR / "doujin_included")
        lists["doujin_excluded"] = serializer.load_doujinshi_list(
            OUTPUT_DIR / "doujin_excluded")
        lists["artist_included"] = serializer.load_artist_list(
            OUTPUT_DIR / "artist_included")
        lists["artist_excluded"] = serializer.load_artist_list(
            OUTPUT_DIR / "doujin_excluded")
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
        can_add_doujin = doujin.matches(config.filters)

        # Doujin info in the normal list doesn't contain information
        # on characters and groups. If you are filtering for it then get it from
        # the specific doujin page, in which case you will need to reload
        # the web elements when you get back since you changed the page
        need_reload = False
        if can_add_doujin and (config.filters.must_include_characters != 0 or len(doujin.artists) == 0):
            iterator.get_extra_doujin_info(doujin)
            can_add_doujin = doujin.matches(config.filters)
            need_reload = True

        if can_add_doujin:
            lists["doujin_included_list"].append(doujin)
            if not doujin.could_be_anthology() and doujin.name not in seen_created_titles:
                seen_created_titles.add(doujin.name)
                hitomi.Logger.log("\t\tNew created title\n")
        else:
            lists["doujin_excluded_list"].append(doujin)

        if iterator.is_last_of_page(i):
            hitomi.Logger.log("\t\t")
        if from_homepage and len(seen_created_titles) >= config.filters.artist_minimum_doujin_count:
            can_add = True
            break
        if need_reload:
            iterator.reload_page()
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
        need_reload = False
        count += 1
        hitomi.Logger.log(f"{i} ({count}): {doujin.name}\n")

        if not config.search_all and config.filters.must_include_series != "":
            # Save date and title of the latest doujin
            if is_start:
                hitomi.Logger.log(f"\tNew stop daytime: {doujin.date}\n")
                new_stop_datetime = doujin.date
                new_stop_title = doujin.name
                is_start = False
            # Reached last updated date?
            # If so then all doujin from here on have already been seen
            if doujin.date <= config.stop_datetime:
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
        doujin_fits_filter = doujin.matches(config.filters)
        if doujin_fits_filter and (len(config.filters.must_include_characters) != 0
                                   or len(doujin.artists) == 0):
            # Can't exclude it yet? Look deeper and check again
            iterator.get_extra_doujin_info(doujin)
            need_reload = True
            doujin_fits_filter = doujin.matches(config.filters)

        if doujin_fits_filter:
            includes_series_from_filter = config.filters.must_include_series in doujin.series
            included_seen_series = [
                name for name in doujin.series if name in config.seen_series]
            is_original = (len(doujin.series) == 0) or (
                doujin.series[0] == "original") or (doujin.series[0] == "n/a")
            if is_original or includes_series_from_filter or len(included_seen_series) > 0:
                lists["doujin_included"].append(doujin)
                include_reason = ""
                if is_original:
                    include_reason = "original doujin"
                if includes_series_from_filter:
                    include_reason = "is from series {config.must_include_series}"
                if len(included_seen_series) > 0:
                    include_reason = "is from seen series: {included_seen_series}"
                hitomi.Logger.log(f"\t+ {include_reason}\n")
            else:
                unread_series = []
                for series_name in doujin.series:
                    if series_name not in config.seen_series:
                        config.unread_series.add(series_name)
                        unread_series.append(series_name)
                exclude_reason = f"Unread series: {unread_series}"
                hitomi.Logger.log(f"\t- {exclude_reason}\n")
                doujin.exclude_reasons.append(exclude_reason)
                lists["doujin_excluded"].append(doujin)
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
        # Add excluded doujin to separate list
        else:
            hitomi.Logger.log("\t- Cant add\n")
            lists["doujin_excluded"].append(doujin)

        # Finished checking doujin, add it to seen list to ignore it later if it comes again
        # Specially useful if the program crashes midway
        config.seen_doujinshi.add(doujin.url)
        if need_reload:
            iterator.reload_page()

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
        dump_config_file(config)
        hitomi.Logger.log(f"Invalid series names: {incorrect_series_names}\n")
    except Exception as e:
        hitomi.Logger.log("Caught exception, dumping lists...\n")
        dump_config_file(config)
        print_exception(e)


def search_doujin(config: hitomi.Config):
    lists = load_lists(config)
    start_time = time()
    try:
        config.search_is_incomplete = True
        search_homepage(config, lists)
        dump_lists(lists)
        bookmarks.export_lists(lists["doujin_included"],
                               lists["artist_included"],
                               config.filters.must_include_series)
        config.search_is_incomplete = False
        config.seen_doujinshi.clear()
        config.unread_series.clear()
        dump_config_file(config)
    except KeyboardInterrupt:
        hitomi.Logger.log_warn("interrupted, dumping lists...\n")
        dump_lists(lists)
        dump_config_file(config)
    except SystemExit:
        exit()
    except Exception as e:
        hitomi.Logger.log_error("Caught exception, dumping lists...\n")
        dump_lists(lists)
        dump_config_file(config)
        print_exception(e)
    elapsed_seconds = time() - start_time
    hitomi.Logger.log(
        f"Total time: {timedelta(seconds=elapsed_seconds)}\n")


def backup_files():
    if not Path.is_dir(OUTPUT_DIR):
        return
    Path("output-backup").mkdir(exist_ok=True)
    for file in OUTPUT_DIR.iterdir():
        src = file
        dst = OUTPUT_BACKUP_DIR.joinpath(file.name)
        shutil.copy(src, dst)
    shutil.copy(CONFIG_FILE, CONFIG_BACKUP_FILE)


def look_for_all_series():
    with open("check_again.txt") as f:
        series = [line.rstrip() for line in f]

    config = None
    lists = {}

    try:
        for name in series:
            hitomi.Logger.log(name)
            config = load_config()
            lists = load_lists(config)
            config.filters.must_include_series = name
            config.search_is_incomplete = True
            search_homepage(config, lists)
            dump_lists(lists)
            num_doujins = len(lists["doujin_included"])
            bookmarks.export_lists(lists["doujin_included"],
                                   lists["artist_included"])
            config.search_is_incomplete = False
            config.seen_doujinshi.clear()
            config.unread_series.clear()
            dump_config_file(config)
    except KeyboardInterrupt:
        hitomi.Logger.log_warn("interrupted, dumping lists...\n")
        dump_lists(lists)
        dump_config_file(config)
    except SystemExit:
        exit()
    except Exception as e:
        hitomi.Logger.log_error("Caught exception, dumping lists...\n")
        dump_lists(lists)
        dump_config_file(config)
        print_exception(e)


def main():
    parser = ArgumentParser(
        prog="SearchDoujinshi",
        description="Scrape doujinshi from hitomi.la")
    parser.add_argument("--logfile", action="store_true",
                        help="Print log to log file instead of terminal")
    parser.add_argument("--check", action="store_true",
                        help="check if links in seen_series are correct")
    parser.add_argument("--series",
                        help="Search only for doujinshi in the given series")
    args = parser.parse_args()
    if args.logfile:
        hitomi.Logger.start_logger()
    else:
        hitomi.Logger.use_terminal()
    if args.check:
        check_seen_series_link()
    else:
        backup_files()
        config = load_config()
        if args.series:
            config.filters.must_include_series = args.series
        search_doujin(config)
    if args.logfile:
        hitomi.Logger.stop_logger()


def get_correct_name_for_favorite_doujin():
    def dump_bookmarks(foreign_url_list: list[str], timeout_url_list: list[str], doujin_list: list[hitomi.Doujinshi]):
        hitomi.Logger.log("Dumping lists...\n")
        print("foreign:", foreign_url_list)
        print("timeout:", timeout_url_list)
        dump_list("bookmarks", doujin_list)
    # hitomi.Logger.start_logger()
    hitomi.Logger.use_terminal()
    if not BROWSER_NAME:
        return
    favorite_doujin = bookmarks.load_folder(
        "エロ/漫画/favorite-doujin-temp", BROWSER_NAME)
    if favorite_doujin == None:
        return
    count = len(favorite_doujin)
    doujin_list = serializer.load_doujinshi_list(OUTPUT_DIR / "bookmarks")
    urls = []
    for doujin in doujin_list:
        urls.append(doujin.url)
    urls = set(urls)
    foreign_url_list: list[str] = []
    timeout_url_list: list[str] = []
    navigator = hitomi.Navigator()
    for i, doujin_url in enumerate(favorite_doujin):
        try:
            if doujin_url in urls:
                continue
            urls.add(doujin_url)
            hitomi.Logger.log(
                f"{i+1}/{count} {unquote(doujin_url)}\n")
            if "hitomi.la" not in doujin_url:
                hitomi.Logger.log("\tforeign\n")
                foreign_url_list.append(doujin_url)
                continue
            doujin = hitomi.Doujinshi()
            doujin = hitomi.DoujinPage(doujin_url, navigator).load_doujin()
            doujin_list.append(doujin)
        except TimeoutError:
            hitomi.Logger.log("\tTimeout\n")
            timeout_url_list.append(doujin_url)
            continue
        except KeyboardInterrupt:
            dump_bookmarks(foreign_url_list, timeout_url_list, doujin_list)
            return
        except Exception as e:
            dump_bookmarks(foreign_url_list, timeout_url_list, doujin_list)
            print(e)
            return
    dump_bookmarks(foreign_url_list, timeout_url_list, doujin_list)
    bookmarks.export_lists(doujin_list, [], group=False)
    # hitomi.Logger.stop_logger()


def download_doujins():
    hitomi.Logger.use_terminal()
    urls = ["https://hitomi.la/manga/%E3%83%A2%E3%83%86%E3%82%8B%E7%8A%AC%E3%81%AE%E7%94%9F%E3%81%8D%E3%81%96%E3%81%BE-%E6%97%A5%E6%9C%AC%E8%AA%9E-77267-502373.html#1"]
    navigator = hitomi.Navigator(load_images=True)
    for url in urls:
        hitomi.download_doujin(url, navigator)


if __name__ == "__main__":
    # main()
    download_doujins()
    # get_correct_name_for_favorite_doujin()
