import delugeonal.mediadb
from datetime import datetime
from dumper import dump
from fuzzywuzzy import fuzz
import re
import sys
import tvdb_v4_official

THETVDB_API_KEY = '1a2a6b43-c9d2-4077-905e-af520f273dc9'

class MediaDb(delugeonal.mediadb.db):
    def __init__(self):
        super().__init__()
        self.name = "TheTVDB"
        self.results_cache = {}
        self.types.append('tv')

        self.tvdb = tvdb_v4_official.TVDB(THETVDB_API_KEY, pin=delugeonal.config['thetvdb']['api_pin'])

    def get_by_id(self, id):
        if (id in self.results_cache):
            return self.results_cache[id]

        item = self.tvdb.get_series(id)
        
        result = None
        if (item is not None and 'firstAired' in item and item['firstAired'] is not None):
            year = re.search('^(\d\d\d\d)-', item['firstAired']).group(1)
            title = re.sub(' \(\d\d\d\d\)$', '', item['name'])
            result = { 'title':title, 'kind':'tv', 'year':year, 'id':id }
            self.results_cache[id] = result
        return result

    def search_title(self, parsed_title):
        results = []
        parsed_year = None
        if (parsed_title in self.results_cache):
            results = self.results_cache[parsed_title]
        else:
            search_title = parsed_title
            try:
                results = self.tvdb.search(search_title, type = 'series', limit = 10)
                # We can't use the global cache for this, because we can't pickle it.
                self.results_cache[parsed_title] = results
            except ValueError as e:
                pass

        titles = {}
        for result in results:
            if ('year' not in result or (parsed_year is not None and result['year'] != parsed_year) or result['type'] != 'series'): continue
            item = self.get_by_id(result['tvdb_id'])
            if (item is not None):
                if parsed_year is not None and item['year'] != parsed_year: continue
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
        dict[season : int ] = episodes : int
        """
        results = self.search_title(search_title)
        
        title = results[list(sorted(results, key = lambda x: fuzz.ratio(results[x]['title'], search_title), reverse=True))[0]]
        total_episodes = {}
        if (title is not None):
            #m = self.get_by_id(title['id'])
            series = self.tvdb.get_series_extended(title['id'])
            for season in series['seasons']:
                if season['number'] == 0 or season['number'] in total_episodes: continue
                total_episodes[season['number']] = 0
                #season = self.tvdb.get_season_extended(season['id'])
                for ep in self.tvdb.get_season_extended(season['id'])['episodes']:
                    date = ep['aired']
                    if (re.search('\d\d\d\d-\d\d-\d\d', date) is None): continue
                    if (date is None or datetime.strptime(date, '%Y-%m-%d') > datetime.now()): 
                        continue
                    total_episodes[season['number']] = total_episodes[season['number']] + 1

        return total_episodes
