import os
import sys
from datetime import datetime
from typing import Callable
import urllib
import time

import selenium.common.exceptions as WebException
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.keys import Keys

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
        ADDBLOCK_PATH = os.getenv("ADDBLOK_PATH")
        if ADDBLOCK_PATH and os.path.exists(ADDBLOCK_PATH):
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
        try:
            self.browser = webdriver.Chrome(service=ChromeService(
                ChromeDriverManager().install()), options=options)
            Logger.log("Open browser\n")
        except Exception as e:
            Logger.log_warn(f"{e}\n")
            sys.exit()
        self.browser.create_options()
        self.wait = WebDriverWait(self.browser, 30)
        Logger.log("Created browser\n")

    def __del__(self):
        if self.browser:
            Logger.log("Close browser\n")
            self.browser.quit()

    def get_current_url(self):
        return self.browser.current_url

    def load(self, url: str):
        self.browser.get(url)

    def refresh(self):
        self.browser.refresh()

    def find(self, selector: str, type=By.CSS_SELECTOR, wait=False):
        if wait:
            return self.wait.until(EC.visibility_of_element_located((type, selector)))
        return self.browser.find_element(type, selector)

    def find_all(self, xpath: str, type=By.CSS_SELECTOR, wait=False):
        if wait:
            return self.wait.until(EC.presence_of_all_elements_located((type, xpath)))
        return self.browser.find_elements(type, xpath)

    def __get_current_tab_index(self) -> int:
        for i, handle in enumerate(self.browser.window_handles):
            if handle == self.browser.current_window_handle:
                return i
        raise (Exception("No current window handle"))

    def get_current_handle(self) -> str:
        return self.browser.current_window_handle

    def open_new_tab(self):
        self.browser.switch_to.new_window("tab")

    def close_tab(self):
        current_tab_index = self.__get_current_tab_index()
        self.browser.close()
        current_tab_index = current_tab_index-1
        self.browser.switch_to.window(
            self.browser.window_handles[current_tab_index])

    def can_load_url(self, url: str):
        self.browser.get(url)
        try:
            titles = self.wait.until(EC.presence_of_all_elements_located(
                (By.XPATH, "//h1[@class='lillie']/a")))
            return True
        except WebException.TimeoutException:
            return False


def wait_for_loaded_image(driver, timeout_seconds=30):
    seconds_awaited = 0
    while not driver.execute_script("return document.images[6].complete;"):
        time.sleep(1)
        seconds_awaited += 1
        if seconds_awaited > timeout_seconds:
            raise (TimeoutError)


def download_doujin(url: str, doujin: Doujinshi | None = None):
    navigator = Navigator(load_images=True)
    navigator.load(url)
    doujin = Doujinshi()
    doujin.url = url
    doujin.name = navigator.find("#gallery-brand a", wait=True).text
    doujin.type = navigator.find("#type a").text
    doujin.groups.extend([l.text.lower()
                         for l in navigator.find_all("#groups a")])
    doujin.series.extend([l.text.lower()
                          for l in navigator.find_all("#series a")])
    doujin.characters.extend([l.text.lower()
                              for l in navigator.find_all("#characters a")])
    doujin.tags.extend([l.text.lower() for l in navigator.find_all("#tags a")])
    navigator.find(".simplePagerPage1 a", wait=True).click()
    all_pages = Select(navigator.find(
        "#single-page-select", wait=True)).options
    last_page = int(all_pages[-1].text.split(" ")[-1])
    current_page = 1
    try:
        os.mkdir(doujin.name)
    except FileExistsError:
        pass
    while current_page <= last_page:
        Logger.log(f"Page {current_page}")
        wait_for_loaded_image(navigator.browser)
        with open(f"{doujin.name}/{current_page}.png", 'wb') as file:
            file.write(navigator.find(".lillie").screenshot_as_png)
        navigator.find("#nextPanel").click()
        current_page += 1


class DoujinIterator():
    def __init__(self, navigator: Navigator, url: str):
        navigator.load(url)
        self.navigator = navigator
        self.url = url

    def load_web_elements(self) -> None:
        tries = 1
        while tries <= 3:
            try:
                titles = self.navigator.find_all(".lillie a", wait=True)
                series = self.navigator.find_all(
                    "//table[@class='dj-desc']/tbody/tr[1]/td[2]", By.XPATH)
                types = self.navigator.find_all(
                    "//table[@class='dj-desc']/tbody/tr[2]/td[2]", By.XPATH)
                artists = self.navigator.find_all(".artist-list")
                tags = self.navigator.find_all(".relatedtags")
                dates = self.navigator.find_all(".date")
                pages = self.navigator.find_all('.page-container li')

                same_len = len(titles) == len(series) == len(
                    types) == len(artists) == len(tags) == len(dates)
                error_message = f"titles:{len(titles)} series:{len(series)} types:{len(types)} artists:{len(artists)} tags:{len(tags)} dates:{len(dates)}"
                assert same_len, error_message
                self.titles = titles
                self.series = series
                self.types = types
                self.artists = artists
                self.tags = tags
                self.dates = dates
                self.pages = pages
                return
            except WebException.TimeoutException:
                Logger.log_warn("timeout, trying again\n")
                tries += 1
                self.navigator.refresh()
        raise Exception(f"Failed to load {self.navigator.get_current_url()}")

    def get_extra_doujin_info(self, doujin: Doujinshi):
        self.navigator.open_new_tab()
        self.navigator.load(doujin.url)
        try:
            doujin.groups.extend([l.text.lower()
                                  for l in self.navigator.find_all("#groups a")])
            doujin.characters.extend([l.text.lower()
                                      for l in self.navigator.find_all("#characters a")])
        except Exception as e:
            Logger.log_warn(f"doujin info exception: {e}\n")
        self.navigator.close_tab()

    def get_doujin(self, i: int) -> Doujinshi:
        def ConvertDatetime(original_dt: str):
            weirdDate = original_dt.split(" ")
            try:
                monthName = weirdDate[1]
            except IndexError:
                print(
                    f"ConvertDatetime: Index Error\n original:{original_dt}\n weirdDate:{weirdDate}")
                raise (IndexError)
            if monthName == "Sept":
                monthName = "Sep"
            correctDate = f"{weirdDate[0]} {monthName} {weirdDate[2]} {weirdDate[3]}"
            return datetime.strptime(correctDate, "%d %b %Y, %H:%M")

        if self.navigator.get_current_url() != self.url:
            raise (Exception("Invalid URL: Don't go to another page while iterating"))

        title = self.titles[i]
        artists = self.artists[i]
        type = self.types[i]
        series = self.series[i]
        tags = self.tags[i]
        date = self.dates[i].text

        doujin = Doujinshi()
        doujin.type = type.text.lower()
        try:
            doujin.url = title.get_attribute("href")
        except Exception as e:
            Logger.log_warn(f"url exception: {e}\n")
        doujin.name = title.text
        try:
            for artist in artists.find_elements(By.TAG_NAME, "a"):
                text = artist.get_attribute("textContent")
                if text != "...":
                    doujin.artists.append(text.lower())
        except Exception as e:
            Logger.log_warn(f"artist exception: {e}\n")
        try:
            for series_name in series.find_elements(By.TAG_NAME, "a"):
                text = series_name.get_attribute("textContent")
                if text != "...":
                    doujin.series.append(text.lower())
        except Exception as e:
            Logger.log_warn(f"series exception: {e}\n")
        try:
            for tag in tags.find_elements(By.TAG_NAME, "a"):
                text = tag.get_attribute("textContent")
                if text != "...":
                    doujin.tags.append(text.lower())
        except Exception as e:
            Logger.log_warn(f"tag exception: {e}\n")
        doujin.date = ConvertDatetime(date)
        return doujin

    def next_page(self) -> tuple[int, bool]:
        is_done = True
        current_page: int = sys.maxsize
        next_page_url = None
        pages_str = "| "
        for page in self.pages:
            if page.text != "...":
                try:
                    a_tag = page.find_element(By.TAG_NAME, "a")
                    page_num = int(a_tag.text)
                    if next_page_url is None and page_num > current_page:
                        pages_str += f"[{page_num}] "
                        current_page = page_num
                        next_page_url = a_tag.get_attribute("href")
                        is_done = False
                    else:
                        pages_str += f"{page_num} "
                except WebException.NoSuchElementException:
                    pages_str += f"{page.text} "
                    current_page = int(page.text)
                except Exception as e:
                    Logger.log_warn(f"Next page exception: {e}\n")
                    pass
            else:
                pages_str += "... "
        pages_str += "|"
        if next_page_url is not None:
            Logger.log(f"{pages_str}\n")
            self.navigator.load(next_page_url)
            self.url = next_page_url
            self.load_web_elements()
        return current_page, is_done

    def next(self):
        self.load_web_elements()
        is_done = False
        while not is_done:
            doujinCount = len(self.titles)
            for i in range(doujinCount):
                doujin = self.get_doujin(i)
                yield (i, doujin)
            _, is_done = self.next_page()

    def is_last_of_page(self, i: int) -> bool:
        return i == len(self.titles) - 1
