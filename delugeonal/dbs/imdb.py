import delugeonal.mediadb
from dumper import dump
from fuzzywuzzy import fuzz
import imdb
import re
import sys


class MediaDb(delugeonal.mediadb.db):
    def __init__(self):
        super().__init__()
        self.ia = imdb.IMDb()
        self.result_cache = {}
        self.name = "IMDb"

    def get_id(self, id):
        item = self.ia.get_movie(id)
        #dump(item)
        result = None
        if (item is not None and "year" in item):
            result = {"title":item['title'], "kind":item['kind'], "year":item['year']}

        return result

    def search_title(self, parsed_title):
        results = []
        if (parsed_title in self.result_cache):
            results = self.result_cache[parsed_title]
        else:
            search_title = re.sub(" \(\d\d\d\d\)$", "", parsed_title.rstrip()).rstrip()
            results = self.ia.search_movie(search_title)
            self.result_cache[parsed_title] = results

        titles = {}
        for result in results:
            #dump(result)
            if (result['kind'] not in ("tv series", "movie") or "year" not in result): continue
            titles[f"{result['title']} ({result['year']})"] = {"title":result['title'], "year":result['year'], "kind":result['kind']}
        
        return titles

    def episode(self):
        #>>> m = ia.get_movie("0105946")
        #>>> m
        #<Movie id:0105946[http] title:_"Babylon 5" (1993)_>
        #>>> ia.update(m, 'episodes')
        #>>> m['episodes'][1][5]
        #<Movie id:0517711[http] title:_"Babylon 5 (TV Series 1993–1998) - IMDb" The Parliament of Dreams (1994)_>
        pass


