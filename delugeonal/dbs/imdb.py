import delugeonal.mediadb
from datetime import datetime
from dumper import dump
from fuzzywuzzy import fuzz
import imdb
import re
import sys


class MediaDb(delugeonal.mediadb.db):
    def __init__(self):
        super().__init__()
        self.name = "IMDb"
        self.types.append('movie')
        self.types.append('tv')

        self.ia = imdb.IMDb()
        self.results_cache = {}

    def get_by_id(self, id):
        if (id in self.results_cache):
            return self.results_cache[id]
        if (result is None):
            result = self.ia.get_movie(id)
        return self.parse_record(result)

    def parse_record(self, data):
        item = None
        if (data is not None and 'year' in data):
            kind = data['kind']
            if (kind == 'tv series'): kind = 'tv'
            if self.istype(kind):
                title = data['title']
                re.sub(' \(\d\d\d\d\)$', '', title)
                item = { 'title':title, 'kind':kind, 'year':data['year'], 'id':id }
        return item

    def search_title(self, title):
        results = []
        search_year = None
        if (title in self.results_cache):
            results = self.results_cache[title]
        else:
            search_title = title
            match = re.search(' \((\d\d\d\d)\)$', search_title)
            if (match):
                search_year = match.group(1)
                search_title = re.sub(' \(\d\d\d\d\)$', '', search_title.rstrip()).rstrip()
            
            results = self.ia.search_movie(search_title)
            # We can't use the global cache for this, because we can't pickle it.
            self.results_cache[title] = results

        titles = {}
        for result in results:
            item = self.parse_record(result)
            if (item is not None):
                if search_year is not None and int(item['year']) != int(search_year):
                    continue
                titles[f"{item['title']} ({item['year']})"] = item
        return titles

    def episode(self):
        #>>> m = ia.get_movie("0105946")
        #>>> m
        #<Movie id:0105946[http] title:_"Babylon 5" (1993)_>
        #>>> ia.update(m, 'episodes')
        #>>> m['episodes'][1][5]
        #<Movie id:0517711[http] title:_"Babylon 5 (TV Series 1993–1998) - IMDb" The Parliament of Dreams (1994)_>
        pass

    def total_episodes(self, search_title):
        """Return a dict containing the number of episodes for every season.

        Returns
        -------
        dict[season : int] = episodes : int
        """
        results = self.search_title(search_title)
        
        title = results[list(sorted(results, key = lambda x: fuzz.ratio(results[x]['title'], search_title), reverse=True))[0]]
        total_episodes = {}
        if (title is not None):
            #m = self.get_by_id(title['id'])
            m = self.ia.get_movie(title['id'])
            self.ia.update(m, 'episodes')
            for season in m['episodes']:
                total_episodes[season] = 0
                for episode in m['episodes'][season]:
                    ep = m['episodes'][season][episode]
                    date = ep['original air date']
                    if (re.search('\d\d? \w\w\w\.? \d\d\d\d', date) is None): continue
                    date = re.sub(' (\w\w\w)\. ', r' \1 ', date)
                    
                    if (date is None or datetime.strptime(date, '%d %b %Y') > datetime.now()): 
                        continue
                    total_episodes[season] = total_episodes[season] + 1
                    
        return total_episodes
