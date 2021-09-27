from abc import ABC, abstractmethod
#from . import config
#import importlib
#medialib = config.medialib if hasattr(config, 'medialib') and config.medialib is not None else None
#if (medialib is None):
#    sys.exit("no media library defined")
#media = importlib.import_module(medialib)
#m = media.Server()

class MediaServer(ABC):
    def __init__(self):
        self.name = "media server"

    @abstractmethod
    def episodes(self, show):
        pass

    def exists(self, show, season, episode):
        for ep in self.episodes(show):
            if (ep['season'] == season and ep['episode'] == episode):
                return True
        return False

    def latest_episode(self, title):
        e = None
        for ep in self.episodes(title):
            season = ep['season']
            episode = ep['episode']
            if (e is not None and "season" in e and season > e['season']):
                e = { 'season':season, 'episode':episode}
            elif (e is not None and "season" in e and season == e['season'] and episode in e and episode > e['episode']):
                e['episode'] = episode
            else:
                e = { 'season':season, 'episode':episode}
        return e

