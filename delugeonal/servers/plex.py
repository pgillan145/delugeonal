import delugeonal.mediaserver
from dumper import dump
from fuzzywuzzy import fuzz
from plexapi.server import PlexServer
from plexapi.exceptions import NotFound
import re

class MediaServer(delugeonal.mediaserver.MediaServer):
    def __init__(self):
        super().__init__()
        self.plex = None
        self.name = "plex"

    def episodes(self, title):
        plex = self.plex

        if (plex is None):
            plex = PlexServer(delugeonal.config['plex']['url'], delugeonal.config['plex']['token'])

        show = None
        if (show is None and re.search(" \(\d\d\d\d\)$", title)):
            test_title = re.sub(" \(\d\d\d\d\)$", "", title)
            try:
                show = plex.library.section('TV Shows').get(test_title)
                title = test_title
            except NotFound as e:
                pass

        if (show is None):
            show = plex.library.section('TV Shows').get(title)

        episodes = []
        for episode in show.episodes():
            episodes.append({'show':show.title, 'episode':episode.index, 'season':episode.parentIndex, 'title':episode.title})

        return episodes

