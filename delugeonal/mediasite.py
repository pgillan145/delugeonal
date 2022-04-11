from abc import ABC, abstractmethod
import atexit
from datetime import datetime,timedelta
import delugeonal
from dumper import dump
import minorimpact
import os.path
import PTN
import re
import requests
import sys
from uravo import uravo

class site(ABC):
    def __init__(self, key, config, name = None):
        atexit.register(self.cleanup)
        if (name is None):
            name = key
        self.site_key = key
        self.name = name

        if (self.site_key is None):
            raise Exception("site key is not defined")
        if (self.site_key not in config):
            raise Exception("'{}' not in config".format(self.site_key))

        self.full_config = config
        self.config = config[self.site_key]

        self.rss_url = self.config['rss_url'] if ('rss_url' in self.config) else None
        self.search_url = self.config['search_url'] if ('search_url' in self.config) else None

    def cleanup(self):
        pass

    @abstractmethod
    def rss_feed(self):
        """Returns a list of dicts containing information about each torrent item available on the rss feed.

        Returns
        -------
        list
           dict
                name : str
                    The name of the torrent.
                url : str
                    The download url.
                date : datetime
                    Torrent file date.  Optional.
        """
        pass

    def search(self, search_string, download = True, args = minorimpact.default_arg_flags):
        results = self.search_site(search_string)
        if (download is True):
            self.download(results, args = args)
        else:
            return results

    @abstractmethod
    def search_site(self, search_string):
        """Search this site and return a list of available torrents.

        Parameters
        ----------
        search_string : str
            The text to search for.

        Returns
        -------
        list
           dict
                name : str
                    The name of the torrent.
                url : str
                    The download url.
                date : datetime
                    Torrent file date.  Optional.
        """
        pass

