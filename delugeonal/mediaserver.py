from abc import ABC, abstractmethod
import minorimpact
import re
#import importlib
#medialib = config.medialib if hasattr(config, 'medialib') and config.medialib is not None else None
#if (medialib is None):
#    sys.exit("no media library defined")
#media = importlib.import_module(medialib)
#m = media.Server()

class TitleNotFoundException(Exception):
    pass

class MediaServer(ABC):
    def __init__(self, name, config, cache = {}):
        if ('server' not in cache): cache['server'] = {}
        self.cache = cache['server']
        self.name = name
        self.config = config
        self.fuck = "FUCK"

    @abstractmethod
    def episodes(self, show):
        pass

    def exists(self, title, season, episode, resolution = None, args = minorimpact.default_arg_flags):
        if (resolution is not None and isinstance(resolution, str)):
            if (resolution == '4k'): resolution = '2160'
            if (resolution == 'sd'): resolution = '480'
            resolution = re.sub('[pi]$','', resolution) 
            resolution = int(resolution)

        for ep in self.episodes(title):
            if (ep['season'] == season and ep['episode'] == episode) and (resolution is None or (ep['resolution'] is not None and ep['resolution'] >= resolution)):
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

    @abstractmethod
    def show_name(self, search_string):
        """Returns the canonical show name for search_string."""
        pass
    
