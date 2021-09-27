import argparse
import atexit
import importlib
import minorimpact.config
import os.path
import pickle
import sys

__version__ = "0.0.1"

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

mediadblib = config['default']['mediadblib'] if 'mediadblib' in config['default'] and config['default']['mediadblib'] is not None else None
if (mediadblib is None):
    sys.exit("no media db library defined")
mediadb = importlib.import_module(mediadblib, __name__)
db = mediadb.MediaDb()

mediaserverlib = config['default']['mediaserverlib'] if 'mediaserverlib' in config['default'] and config['default']['mediaserverlib'] is not None else None
if (mediaserverlib is not None):
    mediaserver = importlib.import_module(mediaserverlib, __name__)
    server = mediaserver.MediaServer()

mediasitelib = config['default']['mediasitelib'] if 'mediasitelib' in config['default'] and config['default']['mediasitelib'] is not None else None
if (mediasitelib is not None):
    mediasite = importlib.import_module(mediasitelib, __name__)
    site = mediasite.MediaSite()

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
