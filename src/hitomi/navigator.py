from os import getenv
from pathlib import Path
import sys
from datetime import datetime
from typing import Callable
import urllib
import time

import selenium.common.exceptions as WebException
from selenium import webdriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.select import Select

from .doujinshi import Doujinshi
from .logger import Logger
from .config import Config


def generate_url(config: Config):
    def tag_to_search_param(tag: str, exclude: bool):
        string = ""
        if "♀" in tag:
            string = f"female%3A{tag.replace(' ♀', '')}"
        elif "♂" in tag:
            string = f"male%3A{tag.replace(' ♂', '')}"
        else:
            string = f"tag%3A{tag}"
        return f"%20{'-' if exclude else ''}{string.replace(' ', '_')}"

    search_params = ""
    if config.must_include_series:
        search_params += f"series%3A{config.must_include_series.replace(' ', '_')}"
    if config.language:
        search_params += f"language%3A{config.language[1]}"
    for type in config.must_exclude_type:
        search_params += f"%20-type%3A{type.replace(' ', '')}"
    for include_tag in config.must_include_tags:
        search_params += tag_to_search_param(include_tag, False)
    for exclude_tag in config.must_exclude_tags:
        search_params += tag_to_search_param(exclude_tag, True)

    base_url = "https://hitomi.la"

    if len(search_params) > 0:
        return f"{base_url}/search.html?{search_params}"
    else:
        return base_url


class Navigator:

    def __init__(self, load_images=False):
        options = Options()
        ADDBLOCK_PATH = getenv("ADDBLOCK_PATH")
        if ADDBLOCK_PATH and Path(ADDBLOCK_PATH).exists():
            options.add_argument(f"load-extension={ADDBLOCK_PATH}")
        else:
            Logger.log_warn("Set 'ADDBLOCK_PATH' path in .env\n")
        WINDOW_SIZE = "1920,1080"
        options.add_argument("--lang=en-GB")
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--remote-debugging-port=9222")
        if not load_images:
            options.add_argument("--blink-settings=imagesEnabled=false")
            options.add_argument("--disable-gpu")
        options.add_argument("--allow-insecure-localhost")
        options.add_argument("log-level=3")
        options.add_argument(f"--window-size={WINDOW_SIZE}")
        if getenv("BROWSER_NAME") == "brave":
            options.binary_location = str(
                Path("C:/Program Files/BraveSoftware/Brave-Browser/Application/brave.exe"))
        self.browser: webdriver.Chrome | None = None
        try:
            self.browser = webdriver.Chrome(service=ChromeService(
                ChromeDriverManager().install()), options=options)
            Logger.log("Open browser\n")
        except Exception as e:
            try:
                Logger.log_warn(
                    "ChromeDriverManager failed, trying local version...\n")
                self.browser = webdriver.Chrome(service=ChromeService(
                    "H:/chromedriver_win32/chromedriver.exe"), options=options)
                Logger.log("Open browser\n")
            except Exception as e:
                Logger.log_warn(f"Could not open browser: {e}\n")
                sys.exit()
        self.browser.create_options()
        self.wait = WebDriverWait(self.browser, 30)
        Logger.log("Created browser\n")

    def __del__(self):
        if self.browser:
            Logger.log("Close browser\n")
            self.browser.quit()

    def get_current_url(self):
        assert (self.browser != None)
        return self.browser.current_url

    def load(self, url: str):
        assert (self.browser != None)
        self.browser.get(url)

    def refresh(self):
        assert (self.browser != None)
        self.browser.refresh()

    def find(self, selector: str, type=By.CSS_SELECTOR, wait=False):
        assert (self.browser != None)
        if wait:
            return self.wait.until(EC.visibility_of_element_located((type, selector)))
        return self.browser.find_element(type, selector)

    def find_all(self, xpath: str, type=By.CSS_SELECTOR, wait=False):
        assert (self.browser != None)
        if wait:
            return self.wait.until(EC.presence_of_all_elements_located((type, xpath)))
        return self.browser.find_elements(type, xpath)

    def __get_current_tab_index(self) -> int:
        assert (self.browser != None)
        for i, handle in enumerate(self.browser.window_handles):
            if handle == self.browser.current_window_handle:
                return i
        raise (Exception("No current window handle"))

    def get_current_handle(self) -> str:
        assert (self.browser != None)
        return self.browser.current_window_handle

    def open_new_tab(self):
        assert (self.browser != None)
        self.browser.switch_to.new_window("tab")

    def close_tab(self):
        assert (self.browser != None)
        current_tab_index = self.__get_current_tab_index()
        self.browser.close()
        current_tab_index = current_tab_index-1
        self.browser.switch_to.window(
            self.browser.window_handles[current_tab_index])

    def can_load_url(self, url: str):
        assert (self.browser != None)
        self.browser.get(url)
        try:
            titles = self.wait.until(EC.presence_of_all_elements_located(
                (By.XPATH, "//h1[@class='lillie']/a")))
            return True
        except WebException.TimeoutException:
            return False


def wait_for_loaded_image(driver, timeout_seconds=30):
    seconds_awaited = 0
    img_path = driver.execute_script(
        "return document.querySelector('img.lillie').src;")
    all_images: list[WebElement] = driver.execute_script(
        "return document.images;")
    img_idx = -1
    for idx, image in enumerate(all_images):
        if image.get_attribute('src') == img_path:
            img_idx = idx
    if img_idx == -1:
        exit(1)
    while not driver.execute_script(f"return document.images[{img_idx}].complete;"):
        time.sleep(1)
        seconds_awaited += 1
        if seconds_awaited > timeout_seconds:
            raise (TimeoutError)


def download_doujin(url: str, navigator: Navigator | None = None, pages_interval: list[tuple[int, int]] = []) -> Doujinshi | None:
    try:
        if navigator is None:
            navigator = Navigator(load_images=True)
        assert (navigator.browser != None)
        navigator.load(url)
        doujin = Doujinshi()
        doujin.url = url
        doujin.name = navigator.find("#gallery-brand a", wait=True).text
        Logger.log(f"Downloading {doujin.name}\n")
        doujin.type = navigator.find("#type a").text
        doujin.artists.extend([l.text.lower()
                              for l in navigator.find_all("#artists a")])
        doujin.groups.extend([l.text.lower()
                              for l in navigator.find_all("#groups a")])
        doujin.series.extend([l.text.lower()
                              for l in navigator.find_all("#series a")])
        doujin.characters.extend([l.text.lower()
                                  for l in navigator.find_all("#characters a")])
        doujin.tags.extend([l.text.lower()
                           for l in navigator.find_all("#tags a")])
        navigator.find(".simplePagerPage1 a", wait=True).click()
        page_selector = Select(navigator.find(
            "#single-page-select", wait=True))
        all_pages = page_selector.options
        last_page = int(all_pages[-1].text.split(" ")[-1])
        for (start, end) in pages_interval:
            if start > last_page or end > last_page:
                Logger.log_error(f"Invalid interval {start}-{end}")
                return
        current_page = 1
        output_dir = Path(f"output/downloaded/{doujin.name}")
        output_dir.mkdir(parents=True, exist_ok=True)
        Path(output_dir, "pages").mkdir(exist_ok=True)
        current_interval = 0
        while current_page <= last_page:
            if len(pages_interval) > 0:
                if current_interval == len(pages_interval):
                    # No more intervals
                    break
                (start, end) = pages_interval[current_interval]
                if current_page < start:
                    # Jump to start
                    page_selector.select_by_index(start-1)
                    current_page = start
                    continue
                if current_page == end:
                    # Finished interval, prepare next
                    current_interval += 1
            Logger.log(f"\tPage {current_page}\n")
            wait_for_loaded_image(navigator.browser)
            with Path(output_dir, f"pages/{current_page}.png").open('wb') as file:
                file.write(navigator.find(".lillie").screenshot_as_png)
            navigator.find("#nextPanel", wait=True).click()
            current_page += 1
    except Exception as e:
        Logger.log_error(f"Could not download images from {url}: {e}\n")
        return None
    with Path(output_dir, "info.yaml").open("w", encoding="utf8") as f:
        dict = doujin.toJSON()
        f.write(f"name: {doujin.name}\n")
        f.write(f"url: {doujin.url}\n")
        f.write(f"type: {doujin.type}\n")
        if 'groups' in dict:
            f.write(f"group: {dict['groups'][0]}\n")
        if 'artists' in dict:
            f.write(f"artists: {dict['artists']}\n")
        if 'series' in dict:
            f.write(f"series: {dict['series']}\n")
        if 'characters' in dict:
            f.write(f"characters: {dict['characters']}\n")
        if 'tags' in dict:
            f.write(f"tags: {dict['tags']}\n")
    return doujin


def ConvertDatetime(original_dt: str):
    # This site uses multiple date formats
    # 2017-09-30 23:14:00-06
    try:
        return datetime.strptime(original_dt[:-4], "%Y-%m-%d %H:%M:%S")
    except:
        pass
    # 30 Sept 2017, 23:14
    try:
        weirdDate = original_dt.split(" ")
        monthName = weirdDate[1]
        if monthName == "Sept":
            monthName = "Sep"
        correctDate = f"{weirdDate[0]} {monthName} {weirdDate[2]} {weirdDate[3]}"
        return datetime.strptime(correctDate, "%d %b %Y, %H:%M")
    except IndexError:
        print(
            f"ConvertDatetime: Index Error\n original:{original_dt}\n weirdDate:{weirdDate}")
        raise (IndexError)


class DoujinPage():
    def __init__(self, url: str, navigator: Navigator):
        self.url = url
        self.navigator = navigator
        self.doujin: Doujinshi | None = None
        self.navigator.load(url)
        # Wait until elements are loaded
        try:
            self.name = self.navigator.find("#gallery-brand", wait=True).text
        except WebException.TimeoutException:
            raise TimeoutError("Timeout loading doujin page")

    def load_name(self):
        return self.name

    def load_type(self):
        return self.navigator.find("#type").text.lower()

    def _load_children_link_text(self, parent_id: str, blank_value: str):
        """
        Return the text of all links that are children to
        the element with CSS id `parent_id`
        """
        children_text: list[str] = []
        parent = self.navigator.find(parent_id, By.ID)
        if parent.text == blank_value:
            return children_text
        for child in parent.find_elements(By.TAG_NAME, "a"):
            children_text.append(child.text.lower())
        return children_text

    def load_series(self):
        return self._load_children_link_text("series", "N/A")

    def load_artists(self):
        return self._load_children_link_text("artists", "N/A")

    def load_groups(self):
        return self._load_children_link_text("groups", "N/A")

    def load_characters(self):
        return self._load_children_link_text("characters", "")

    def load_tags(self):
        return self._load_children_link_text("tags", "")

    def load_date(self):
        raw_date: str = self.navigator.find(".date").text
        return ConvertDatetime(raw_date)

    def load_doujin(self):
        doujin = Doujinshi()
        doujin.url = self.url
        doujin.type = self.load_type()
        doujin.series = self.load_series()
        doujin.name = self.load_name()
        doujin.artists = self.load_artists()
        doujin.groups = self.load_groups()
        doujin.characters = self.load_characters()
        doujin.tags = self.load_tags()
        doujin.date = self.load_date()
        return doujin


class DoujinListPage():
    def __init__(self, navigator: Navigator, url: str):
        self.navigator = navigator
        self.url = url
        self.doujin_list: list[Doujinshi] = []
        self.pages = []

    def try_loading(self, max_tries=3):
        tries = 1
        while tries <= max_tries:
            try:
                self.navigator.load(self.url)
                self.doujin_list = self.load_doujin_list()
                self.pages = self.load_pages_link()
            except WebException.TimeoutException:
                Logger.log_warn("timeout, trying again\n")
                tries += 1
                self.navigator.refresh()
                continue
        raise Exception(f"Failed to load {self.navigator.get_current_url()}")

    def load_pages_link(self) -> list[WebElement]:
        pages = self.navigator.find_all('.page-container li')
        return pages

    def load_doujin_list(self) -> list[Doujinshi]:
        def get_children_link_text(parent: WebElement):
            children = []
            try:
                for child in parent.find_elements(By.TAG_NAME, "a"):
                    text = child.get_attribute("textContent")
                    if text != "...":
                        children.append(text.lower())
            except Exception as e:
                Logger.log_warn(f"get_children exception: {e}\n")
            return children

        titles = self.navigator.find_all(".lillie a", wait=True)
        series = self.navigator.find_all(
            "//table[@class='dj-desc']/tbody/tr[1]/td[2]", By.XPATH)
        types = self.navigator.find_all(
            "//table[@class='dj-desc']/tbody/tr[2]/td[2]", By.XPATH)
        artists = self.navigator.find_all(".artist-list")
        tags = self.navigator.find_all(".relatedtags")
        dates = self.navigator.find_all(".date")

        same_len = len(titles) == len(series) == len(
            types) == len(artists) == len(tags) == len(dates)
        error_message = f"titles:{len(titles)} series:{len(series)} types:{len(types)} artists:{len(artists)} tags:{len(tags)} dates:{len(dates)}"
        assert same_len, error_message

        doujin_list = []
        for i, _ in enumerate(titles):
            doujin = Doujinshi()
            doujin.name = titles[i].text
            try:
                doujin.url = titles[i].get_attribute("href")
            except Exception as e:
                Logger.log_warn(f"url exception: {e}\n")
            doujin.type = types[i].text.lower()
            doujin.artists = get_children_link_text(artists[i])
            doujin.series = get_children_link_text(series[i])
            doujin.tags = get_children_link_text(tags[i])
            doujin.date = ConvertDatetime(dates[i].text)
            doujin_list.append(doujin)
        return doujin_list

    def get_next_page(self):
        current_page: int = sys.maxsize
        next_page_url = None
        pages_str = "| "
        for page in self.pages:
            if page.text == "...":
                pages_str += "... "
                continue
            try:
                a_tag = page.find_element(By.TAG_NAME, "a")
                page_num = int(a_tag.text)
                if next_page_url is None and page_num > current_page:
                    pages_str += f"[{page_num}] "
                    current_page = page_num
                    next_page_url = a_tag.get_attribute("href")
                else:
                    pages_str += f"{page_num} "
            except WebException.NoSuchElementException:
                pages_str += f"{page.text} "
                current_page = int(page.text)
            except Exception as e:
                Logger.log_warn(f"Next page exception: {e}\n")
                pass
        pages_str += "|"
        if next_page_url == None:
            return None
        Logger.log(f"{pages_str}\n")
        return DoujinListPage(self.navigator, next_page_url)


class DoujinIterator():
    def __init__(self, navigator: Navigator, url: str):
        navigator.load(url)
        self.navigator = navigator
        self.url = url
        self.current_page = DoujinListPage(self.navigator, self.url)

    def get_extra_doujin_info(self, doujin: Doujinshi):
        self.navigator.open_new_tab()
        doujin_page = DoujinPage(doujin.url, self.navigator)
        try:
            doujin.groups.extend(doujin_page.load_groups())
            doujin.characters.extend(doujin_page.load_characters())
        except Exception as e:
            Logger.log_warn(f"doujin info exception: {e}\n")
        self.navigator.close_tab()

    def next(self):
        while self.current_page:
            self.current_page.try_loading()
            for i, doujin in enumerate(self.current_page.doujin_list):
                if i == 0:
                    Logger.log(f"{doujin.date}\n")
                yield (i, doujin)
            self.current_page = self.current_page.get_next_page()

    def reload_page(self):
        if self.current_page == None:
            return
        self.current_page.try_loading()

    def is_last_of_page(self, i: int) -> bool:
        if self.current_page == None:
            return False
        return i == len(self.current_page.doujin_list) - 1
