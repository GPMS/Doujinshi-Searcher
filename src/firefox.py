import sqlite3

import hitomi


def get_potential_bookmark_paths(conn, bookmark_path_parts):
    # Get all matching bookmarks for last part of the bookmark path
    cursor = conn.execute(
        f"SELECT * FROM moz_bookmarks\
                            WHERE title = '{bookmark_path_parts[-1]}'"
    )
    matching_places = cursor.fetchall()

    potential_paths = []

    # Iterate thought all potential matches to find unique matches
    for match in matching_places:
        # Set second to last part of the bookmark path as starting point
        part_index = len(bookmark_path_parts) - 2
        parent_id = match[3]

        # Follow the bookmark path and try to find matches to required path until
        # root bookmark is reached or when path has been found
        while part_index >= 0:
            current_part = bookmark_path_parts[part_index]
            cursor = conn.execute(
                f"SELECT * FROM moz_bookmarks WHERE id = {parent_id}\
                                    AND title = '{current_part}'"
            )
            parent = cursor.fetchone()

            if parent is None:
                break

            parent_id = parent[3]

            if parent_id == 1:
                potential_paths.append(match[0])
                break

            part_index -= 1

    return potential_paths


def get_urls(conn, bookmark_directory_id):
    cursor = conn.execute(
        f"SELECT bm.id, bm.type, url FROM moz_bookmarks as bm\
                            LEFT JOIN moz_places as p ON bm.fk = p.id\
                            WHERE parent = {bookmark_directory_id}"
    )

    urls = []

    for row in cursor.fetchall():
        bookmark_id = row[0]
        bookmark_type = row[1]
        bookmark_url = row[2]

        # Parse directories (type 2) recursively if needed
        if bookmark_type == 2:
            urls.extend(get_urls(conn, bookmark_id))
            continue

        urls.append(bookmark_url)

    return urls


def load_bookmarks(path: str) -> tuple[list[str], bool]:
    FIREFOX_PROFILE_PATH = "C:/Users/gabriel/AppData/Roaming/Mozilla/Firefox/Profiles/7aaicssr.default-1664887030248"

    try:
        database_path = f"{FIREFOX_PROFILE_PATH}/places.sqlite"
        conn = sqlite3.connect(database_path)

        bookmark_path_parts = path.split("/")
        potential_paths = get_potential_bookmark_paths(
            conn, bookmark_path_parts)

        if len(potential_paths) > 1:
            hitomi.Logger.log_error(
                "Bookmark path is not unique! Make sure there is not two paths named same way.\n")

        if len(potential_paths) == 0:
            hitomi.Logger.log_error("No matching bookmark path found!\n")
            return [], False

        urls = get_urls(conn, potential_paths[0])
        return urls, True
    except Exception as e:
        hitomi.Logger.log_error(f"Failed to load firefox bookmarks: {e}\n")
        return [], False
