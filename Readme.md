# Doujinshi Searcher

Web scrapper for doujinshi and authors using hitomi.la

For now it only search for doujinshi in Japanese.

## How to use

Install requirements in `requirements.txt` and the [Chrome Web Driver](https://chromedriver.chromium.org/downloads), then run without arguments to search for recent doujinshi and authors that fit the user's preferences inside `config.json`:
```console
> run.bat
```

Use `--series <series-name>` to search for a specific series.

The program takes a long time to run. You can follow the progress with the log file inside the `logs` folder.

After it's finished it will generate the files inside the `output` folder. The `.json` files are for debug purposes, but they contain all artists/doujinshi that were found in the search divided by whether they were included or excluded based on the user's preference. You are advised to instead import the `bookmarks.html` file using your browser of preference.

Use the following command to load the backup files if needed:
```console
> doReset.bat
```

## Config.json

File containing the user's preferences. It gets automatically generated with default values when the program is first run if it doesn't exist already. It can then be manually edited to fit each user's needs.

### Options

Options available to set in `config.json`:
- **must_exclude_type:** exclude doujinshi that are of any of the given types.
- **must_include_tags:** exclude doujinshi that don't contain all the given tags.
- **must_exclude_tags:** exclude doujinshi that contain any of the given tags.
- **must_include_characters:** exclude doujinshi that don't contain all the given characters.
- **must_include_series:** exclude doujinshi that aren't of the given series. Can be set using `--series`.https://chromedriver.chromium.org/downloads
- **artist_minimum_doujin_count:** minimum number of doujin an artist must have that fit the user's preferences.
- **max_num_artists:** max number of artists a doujin can have (or 0 for any number).
- **seen_series:** all series to search for, aside from the one in `must_include_series`. All others are ignored.
- **unread_series:** Series found during search that are not in `seen_series`. Serves as suggestions to search in the future using `must_include_series`.
- **added_artists:** All artists that are favorited by the user. Not included in the artist list at the end, but all new doujinshi by these artists are included, if they fit the user's preference.
- **seen_doujinshi:** all doujinshi found during search. This gets reset every new search, but allows to skip already seen doujinshi if a search gets interrupted.
- **stop_datetime:** the datetime of the last doujinshi of the last search. This will be the stop point of future searches.
- **stop_title:** the tile of the last doujinshi of the last search. Used for debug purposes.
- **incomplete:** whether the last check was interrupted or not.
- **check_artist:** whether to search for new artists as well or only doujinshi. Can speed up search if set to `false`.
