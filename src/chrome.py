from chrome_bookmarks import Item, folders


def load_bookmarks(path: str) -> tuple[list[str], bool]:
    dirs = path.split('/')
    current_folder: Item | None = None
    subfolders: list[Item] = folders
    for current_dir in dirs:
        for folder in subfolders:
            if folder.name == current_dir:
                current_folder = folder
                subfolders = current_folder.folders
                break
    found = current_folder is not None and current_folder.name == dirs[-1]
    urls = []
    for entry in current_folder.urls:
        urls.append(entry.url)
    return urls, found
