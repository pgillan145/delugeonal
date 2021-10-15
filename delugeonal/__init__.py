import argparse
import atexit
import importlib
import minorimpact.config
import os.path
import pickle
import sys

__version__ = "0.0.3"

config = minorimpact.config.getConfig(script_name='delugeonal')
cache = {}
cache_file = None
if ('cache_file' in config['default']):
    cache_file = config['default']['cache_file']
    if (os.path.exists(cache_file)):
        with open(cache_file, "rb") as f:
            cache = pickle.load(f)

def cleanup_cache():
    if (cache_file is not None):
        with open(cache_file, "wb") as f:
            pickle.dump(cache, f)
atexit.register(cleanup_cache)

mediadbs = []
mediadblibs = eval(config['default']['mediadblibs']) if 'mediadblibs' in config['default'] and config['default']['mediadblibs'] is not None else None
if (mediadblibs is not None and len(mediadblibs)>0):
    for mediadblib in (mediadblibs):
        db = importlib.import_module(mediadblib, __name__)
        mediadbs.append(db.MediaDb())
else:
    sys.exit("no media db libraries defined")

mediaserverlib = config['default']['mediaserverlib'] if 'mediaserverlib' in config['default'] and config['default']['mediaserverlib'] is not None else None
if (mediaserverlib is not None):
    mediaserver = importlib.import_module(mediaserverlib, __name__)
    server = mediaserver.MediaServer()
else:
    sys.exit("no media server library defined")

mediasites = []
mediasitelibs = eval(config['default']['mediasitelibs']) if 'mediasitelibs' in config['default'] and config['default']['mediasitelibs'] is not None else None
if (mediasitelibs is not None and len(mediasitelibs) > 0):
    for mediasitelib in (mediasitelibs):
        site = importlib.import_module(mediasitelib, __name__)
        mediasites.append(site.MediaSite())

torrentclientlib = config['default']['torrentclientlib'] if 'torrentclientlib' in config['default'] and config['default']['torrentclientlib'] is not None else None
if (torrentclientlib is not None):
    torrentclient = importlib.import_module(torrentclientlib, __name__)
    client = torrentclient.TorrentClient()

from . import delugeonal
def main():
    delugeonal.main()

def get_title(title, year=True, headless=True):
    return db.get_title(title, year=year, headless=headless)

def search_title(title):
    return db.search_title(title)

def transform(title, season, episode):
    return delugeonal.transform(title, season, episode)
