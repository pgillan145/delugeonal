from abc import ABC, abstractmethod
import atexit
from dumper import dump
from fuzzywuzzy import fuzz
from . import cache, config
import os.path
import pickle
import re
import sys

class db(ABC):
    def __init__(self):
        self.cache = cache
        self.name = "media db"
        atexit.register(self.cleanup)
        if ('db' not in self.cache): self.cache['db'] = {}

    def cleanup(self):
        pass

    @abstractmethod
    def get_id(self, id):
        pass

    def get_title(self, parsed_title, year=True, headless=True):
        title = None

        if (parsed_title in self.cache['db']):
            title = self.cache['db'][parsed_title]['title']
            if (year is True): title = f"{title} ({self.cache['db'][parsed_title]['year']})"
            return title

        titles = self.search_title(parsed_title)
        if (titles is None):
            return title

        if (parsed_title in titles):
            self.cache['db'][parsed_title] = titles[parsed_title]
            title = titles[parsed_title]['title']
            if (year is True): title = f"{title} ({titles[parsed_title]['year']})"
            return title

        parsed_year = None
        search_title = parsed_title
        match = re.search(" \((\d\d\d\d)\)$", parsed_title)
        if (match):
            parsed_year = match.group(1)
            search_title = re.sub(" \(\d\d\d\d\)$", "", parsed_title)

        max_lev = 85
        for t in titles:
            if (parsed_year and titles[t]["year"] != parsed_year): continue
            search_t = t
            if (parsed_year is None):
                search_t = re.sub(" \(\d\d\d\d\)", "", search_t)
            lev = fuzz.ratio(search_t.lower(),parsed_title.lower())
            #print(f"{t} ({lev})")
            if (lev > max_lev):
                title = t
                max_lev = lev

        if (title is not None):
            if (year is False): title = re.sub(" \(\d\d\d\d\)$", "", title)
            return title

        if (headless is False):
            i = 0
            items = {}
            print(f"Searching for '{search_title}':")
            for t in titles:
                items[i] = t
                i = i + 1
                output = f"{i:-2d} {t} (match:{fuzz.ratio(t.lower(),search_title.lower())})"
                print(output)
            pick = input("Choose a title/enter id/enter a name manually: ").rstrip()
            if (re.search("^\d+$", pick) and int(pick) > 0 and int(pick) <= len(titles)):
                pick = int(pick) - 1
                title = items[pick]
                self.cache['db'][parsed_title] = titles[title]
                #if (year is True): title = f"{title} ({titles[title]['year']})"
                if (year is False): title = re.sub(" \(\d\d\d\d\)$", "", title)
                return title
            elif (re.search("^\d+$", pick) and int(pick) > 99999):
                res = self.get_id(pick)
                self.cache['db'][parsed_title] = res
                title = f"{res['title']}"
                if (year is True): title = f"{title} ({res['year']})"
                return title
            elif (len(pick) > 5):
                pick_year = None
                pick_title = pick
                match = re.search(" \((\d\d\d\d)\)$", pick_title)
                if (match):
                    pick_year = match.group(1)
                    pick_title = re.sub(" \(\d\d\d\d\)$", "", pick_title)
                self.cache['db'][parsed_title] = { 'title':pick_title, 'year':pick_year }
                if (year is not False and pick_year is not None):
                    return f'{pick_title} ({pick_year})'
                return pick_title

        return title

    @abstractmethod
    def search_title(self, title):
        pass

