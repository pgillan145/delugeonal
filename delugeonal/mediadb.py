from abc import ABC, abstractmethod
import atexit
from datetime import datetime
from dumper import dump
from fuzzywuzzy import fuzz
from . import cache, config
import os.path
import pickle
import re
import sys

class db(ABC):
    def __init__(self):
        if ('db' not in cache): cache['db'] = {}
        self.cache = cache['db']
        self.name = "media db"
        self.types = []
        atexit.register(self.cleanup)

    def cleanup(self):
        pass

    @abstractmethod
    def get_by_id(self, id):
        """Returns a dict containing the basic information about a particular `id`.

        Returns
        -------
        dict
            name : str
                The official name of this item, NOT including the year.  (i.e. "Archer", not "Archer (2009)")
            year : int
                The first year this item was produced.
            kind : str
                The kind of item this represents, 'tv' or 'movie'.
            id
                The unique id of this record.
        """ 
        pass

    def get_title(self, parsed_title, year=True, headless=True):
        title = None

        if (parsed_title in self.cache and 'title' in self.cache[parsed_title]):
            title = self.cache[parsed_title]['title']
            if (year is True): title = f"{title} ({self.cache[parsed_title]['year']})"
            return title

        titles = self.search_title(parsed_title)
        if (titles is None):
            return None

        if (parsed_title in titles):
            self.cache[parsed_title]['title'] = titles[parsed_title]['title']
            self.cache[parsed_title]['year'] = titles[parsed_title]['year']
            self.cache[parsed_title]['mod_date'] = datetime.now()
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
            #if (parsed_year and titles[t]["year"] != parsed_year): continue
            search_t = t
            if (parsed_year is None):
                search_t = re.sub(" \(\d\d\d\d\)", "", search_t)
            lev = fuzz.ratio(search_t.lower(),parsed_title.lower())
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
                if (parsed_title not in self.cache): self.cache[parsed_title] = {}
                self.cache[parsed_title]['title'] = title
                self.cache[parsed_title]['year'] = titles[title]['year']
                self.cache[parsed_title]['mod_date'] = datetime.now()
                #if (year is True): title = f"{title} ({titles[title]['year']})"
                if (year is False): title = re.sub(" \(\d\d\d\d\)$", "", title)
                return title
            elif (re.search("^\d+$", pick) and int(pick) > 99999):
                res = self.get_by_id(pick)
                if (parsed_title not in self.cache): self.cache[parsed_title] = {}
                self.cache[parsed_title]['title'] = res['title']
                self.cache[parsed_title]['year'] = res['year']
                self.cache[parsed_title]['mod_date'] = datetime.now()
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
                if (parsed_title not in self.cache): self.cache[parsed_title] = {}
                self.cache[parsed_title]['title'] = pick_title
                self.cache[parsed_title]['year'] = pick_year
                self.cache[parsed_title]['mod_date'] = datetime.now()
                if (year is not False and pick_year is not None):
                    return f'{pick_title} ({pick_year})'
                return pick_title
        return title

    def istype(self, type):
        """Returns True if `type` is in self.types."""
        if type is None:
            raise Exception(f"no type specified")
        return type in self.types

    @abstractmethod
    def search_title(self, title):
        """Returns a list of items that match `title`.

        The items in the list are the values returned from get_by_id().

        Parameters
        ----------
        title : str
            The title to search for.

        Returns
        -------
        list[ title + year : str ]
            dict
                name : str
                    The official name of this item, NOT including the year.  (i.e. "Archer", not "Archer (2009)")
                year : int
                    The first year this item was produced.
                kind : str
                    The kind of item this represents, 'tv' or 'movie'.
                id
                    The unique id of this record.
        """
        pass

    @abstractmethod
    def total_episodes(self, title):
        """Return a dict containing the number of episodes for each season.

        Returns
        -------
        dict[ season : int ] = episodes : int
             total number of episodes for `season`.
        """
        pass

