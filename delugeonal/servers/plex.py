import delugeonal.mediaserver
from datetime import datetime
from dumper import dump
from fuzzywuzzy import fuzz
from plexapi.server import PlexServer
from plexapi.exceptions import NotFound
import re

class MediaServer(delugeonal.mediaserver.MediaServer):
    def __init__(self):
        super().__init__()
        self.plex = PlexServer(delugeonal.config['plex']['url'], delugeonal.config['plex']['token'])
        self.name = "Plex"

    def episodes(self, title):
        plex = self.plex

        if (title is None):
            raise Exception("title is not defined.")
        #if (title in self.cache and 'episodes' in self.cache[title]): 
        #    return self.cache[title]['episodes']
        if (title not in self.cache): self.cache[title] = {}

        show = self._show(title)
        if (show is None):
            raise Exception(f"Can't find '{title}' in {self.name}")

        episodes = []
        for episode in show.episodes():
            episodes.append({'show':show.title, 'episode':episode.index, 'season':episode.parentIndex, 'title':episode.title})

        #self.cache[title]['episodes'] = episodes
        #self.cache[title]['mod_date'] = datetime.now()
        return episodes

    def _show(self, search_string):
        """Returns the proper show name for search_string."""
        if (search_string is None):
            raise Exception("search string is empty.")
        if (search_string not in self.cache): self.cache[search_string] = {}

        show = None
        if (re.search(" \(\d\d\d\d\)$", search_string) is not None):
            test_search_string = re.sub(" \(\d\d\d\d\)$", "", search_string)
            try:
                show = self.plex.library.section('TV Shows').get(test_search_string)
                return show
            except NotFound as e:
                pass

        if (show is None):
            # Let this throw an exception if title is BS, we're all out of options.
            try:
                show = self.plex.library.section('TV Shows').get(search_string)
                return show
            except NotFound as e:
                raise e

    def show_name(self, search_string):
        show = self._show(search_string)
        if (show is None):
            raise Exception(f"Can't find '{search_string}' in {self.name}")
        return show.title

