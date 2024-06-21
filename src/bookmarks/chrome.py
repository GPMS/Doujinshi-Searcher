from chrome_bookmarks import Item, folders


def load_bookmarks_chromium(path: str, folders: list[Item]) -> tuple[list[str], bool]:
    dirs = path.split('/')
    current_folder: Item | None = None
    subfolders = folders
    for current_dir in dirs:
        for folder in subfolders:
            if folder.name == current_dir:
                current_folder = folder
                subfolders = current_folder.folders
                break
    if current_folder is None or current_folder.name != dirs[-1]:
        return [], False
    urls: list[str] = []
    for entry in current_folder.urls:
        urls.append(entry.url)
    return urls, True


def load_bookmarks(path: str):
    return load_bookmarks_chromium(path, folders)
