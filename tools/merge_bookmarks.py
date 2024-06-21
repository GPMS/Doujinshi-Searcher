from pathlib import Path
import codecs
import re

DIR = Path("check-again/groups")


def merge_bookmark(bookmark_files: list[str]):
    seen_urls = set()
    with codecs.open(str(Path(DIR, "merged.html")), 'w', 'utf-8') as output:
        # Write header
        output.write(
            '<!DOCTYPE NETSCAPE-Bookmark-file-1>\n'
            '<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">\n'
            '<TITLE>Bookmarks</TITLE>\n'
            '<H1>Bookmarks</H1>\n'
            '<DL><p>\n'
        )
        for file in bookmark_files:
            with codecs.open(str(Path(DIR, file)), 'r', 'utf-8') as input:
                for line_number, line in enumerate(input):
                    # Skip header and last closing line
                    if line_number < 5 or line == "</DL><p>\n":
                        continue
                    # Skip repeated urls
                    if line.startswith("\t\t\t<DT><A HREF="):
                        quotes_index = [m.start()
                                        for m in re.finditer('"', line)]
                        url_begin = quotes_index[0] + 1
                        url_end = quotes_index[1]
                        url = line[url_begin:url_end]
                        if url in seen_urls:
                            continue
                        seen_urls.add(url)
                    # If not skipped, keep line
                    output.write(line)
        # Write closing tag
        output.write('</DL><p>\n')


def get_index(group_name: str):
    number = ""
    for c in group_name:
        if c.isdigit():
            number += c
    return int(number)


if __name__ == "__main__":
    files: list[str] = []
    for file in DIR.iterdir():
        if not file.name.endswith(".html") or file.name == "merged.html":
            continue
        files.append(file.name)
    files.sort(key=get_index)
    merge_bookmark(files)
