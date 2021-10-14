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
        self.match_log_file = None

    def __del__(self):
        if (self.match_log_file is not None):
            self.match_log_file.close()

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

    def get_title(self, name, year=True, headless=True):
        title = None
        title_year = None

        if (name in self.cache and 'title' in self.cache[name]):
            title = self.cache[name]['title']
            title_year = self.cache[name]['year']
        else:
            titles = self.search_title(name)
            if (titles is not None and len(titles) > 0):
                if (name in titles):
                    # Exact match, we got lucky
                    title = titles[name]['title']
                    title_year = titles[name]['year']
                else:
                    parsed_year = None
                    match = re.search(' \((\d\d\d\d)\)$', name)
                    if (match):
                        # Our title came in with a year -- use it
                        parsed_year = match.group(1)

                    # See if what we got is within 15% of perfect.  If so, let's use it.
                    max_lev = 85
                    for t in titles:
                        if (parsed_year and titles[t]['year'] != parsed_year): continue
                        search_t = t
                        if (parsed_year is None):
                            search_t = re.sub(' \(\d\d\d\d\)', '', search_t)
                        lev = fuzz.ratio(search_t.lower(),name.lower())
                        if (lev > max_lev):
                            title = titles[t]['title']
                            title_year = titles[t]['year']
                            max_lev = lev

                    # Nothing was a great match, so if we're not in cron mode, ask a grown-up for help.
                    if (title is None and headless is False):
                        search_title = re.sub(' \(\d\d\d\d\)$', '', name)
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
                            pick_title = items[int(pick) - 1]
                            match = re.search(" \((\d\d\d\d)\)$", pick_title)
                            if (match):
                                pick_year = match.group(1)
                                pick_title = re.sub(' \(\d\d\d\d\)$', '', pick_title)
                            title = pick_title
                            title_year = pick_year
                        elif (re.search("^\d+$", pick) and int(pick) > 99999):
                            # TODO: This may only be true for imdb.
                            res = self.get_by_id(pick)
                            title = res['title']
                            title_year = res['year']
                        elif (len(pick) > 5):
                            pick_year = None
                            pick_title = pick
                            match = re.search(" \((\d\d\d\d)\)$", pick_title)
                            if (match):
                                pick_year = match.group(1)
                                pick_title = re.sub(" \(\d\d\d\d\)$", "", pick_title)
                            title = pick_title
                            title_year = pick_year

        if (title is not None):
            if (name not in self.cache):
                self.cache[name] = {}
            self.cache[name]['title'] = title
            self.cache[name]['year'] = title_year
            self.cache[name]['mod_date'] = datetime.now()
            self.match_log(None, name,title, title_year)
            if (year is True and title_year is not None): title = f"{title} ({title_year})"
        return title

    def istype(self, type):
        """Returns True if `type` is in self.types."""
        if type is None:
            raise Exception(f"no type specified")
        return type in self.types

    def match_log(self, filename, name, title, year):
        """Writes data to 'match_debug_file', if defined in the config file.

        No user servicable parts inside.  This is a debugging method meant to keep a laundry list of every attempted match so we can 
        either debug existing code or confirm future changes still produce the same results.

        Parameters
        ---------
        filename : str
            The original file or source, if known.
        name : str
            The parsed name of the torrent.
        title : str
            The 'title' result of the match attempt.
        year
            The 'year' result of the match attempt
        """
        if (self.match_log_file is None and 'match_debug_log' in config['default'] and config['default']['match_debug_log']):
            try:
                self.match_log_file = open(config['default']['match_debug_log'], 'a')
            except Exception as e:
                if (args.verbose): print(f"Can't write match log: {e}")
                return

        if (self.match_log_file is not None):
            self.match_log_file.write(f'"{self.name}","{filename}","{name}","{title}","{year}"\n')

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

