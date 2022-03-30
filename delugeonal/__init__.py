import argparse
import atexit
import os.path
import pickle
import sys

__version__ = "0.0.11"

cache = {}
cache_file = None
client = None
config = {}
mediadbs = []
mserver = None
mediasites = []

def cleanup_cache():
    #print("cleanup_cache()")
    if (cache_file is not None):
        #print("cache_file:" + cache_file)
        with open(cache_file, "wb") as f:
            pickle.dump(cache, f)
atexit.register(cleanup_cache)

from . import delugeonal
def main():
    delugeonal.main()

def get_title(title, year=True, headless=True):
    return db.get_title(title, year=year, headless=headless)

def search_title(title):
    return db.search_title(title)

def transform(title, season, episode):
    return delugeonal.transform(title, season, episode)
