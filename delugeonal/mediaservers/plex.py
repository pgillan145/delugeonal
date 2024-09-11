import delugeonal.mediaserver
from datetime import datetime
from dumper import dump
from fuzzywuzzy import fuzz
from plexapi.server import PlexServer
from plexapi.exceptions import NotFound
import re

class MediaServer(delugeonal.mediaserver.MediaServer):
    def __init__(self, config, cache = {}):
        super().__init__("Plex", config, cache = cache)
        self.plex = PlexServer(self.config['plex']['url'], self.config['plex']['token'])

    def episodes(self, title):
        plex = self.plex

        if (title is None):
            raise Exception("title is not defined.")
        #if (title in self.cache and 'episodes' in self.cache[title]): 
        #    return self.cache[title]['episodes']
        if (title not in self.cache): self.cache[title] = {}
        show = self._show(title)
        if (show is None):
            raise delugeonal.mediaserver.TitleNotFoundException("Can't find '{}' in {}".format(title, self.name))

        episodes = []
        for episode in show.episodes():
            #dump(episode)
            resolution = 0
            try:
                for media in episode.media:
                    r = media.videoResolution
                    if (r == '4k'): r = '2160'
                    if (r == 'sd'): r = '480'
                    r = int(r)
                    if (r > resolution):
                        resolution = r
                    #print(media.videoResolution, media.videoCodec, media.container)
                    #for part in media.parts:
                        #print(part.file, part.videoProfile)
            except Exception as e:
                pass
            episodes.append({'show':show.title, 'episode':episode.index, 'season':episode.parentIndex, 'title':episode.title, 'resolution':resolution, 'date':episode.originallyAvailableAt})

        #self.cache[title]['episodes'] = episodes
        #self.cache[title]['mod_date'] = datetime.now()
        return episodes

    def _show(self, search_string):
        """Returns the proper show name for search_string."""
        if (search_string is None):
            raise Exception("search string is empty.")
        if (search_string not in self.cache): self.cache[search_string] = {}

        test_search_string = search_string
        test_search_year = None
        if (re.search(r' \(\d\d\d\d\)$', search_string) is not None):
            m = re.search(r'(.+) \((\d\d\d\d)\)$', search_string)
            test_search_string = m.group(1)
            test_search_year = m.group(2)

        try:
            #print(f"test_search_string:'{test_search_string}'")
            #print(f"test_search_year:'{test_search_year}'")
            if (test_search_year is not None):
                shows = self.plex.library.section('TV Shows').search(title=test_search_string, year=test_search_year, maxresults=1 )
            else:
                shows = self.plex.library.section('TV Shows').search(title=test_search_string, maxresults=1 )
        except NotFound as e:
            raise delugeonal.mediaserver.TitleNotFoundException(repr(e))

        if (len(shows) > 0):
            return shows[0]
        return None

    def show_name(self, search_string):
        show = self._show(search_string)
        if (show is None):
            raise delugeonal.mediaserver.TitleNotFoundException("Can't find '{}' in {}".format(search_string, self.name))
        return show.title

