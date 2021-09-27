from abc import ABC, abstractmethod
import atexit
from datetime import datetime,timedelta
import delugeonal
from . import db, cache, config, server
from dumper import dump
from fuzzywuzzy import fuzz
import minorimpact
import os.path
import pickle
import re
import requests
import sys
from uravo import uravo

class site(ABC):
    def __init__(self):
        atexit.register(self.cleanup)
        self.cache = cache
        self.name = "media site"
        
        if ('site' not in self.cache): self.cache['site'] = {}

    def cleanup(self):
        pass

    def rss(self, args = minorimpact.default_arg_flags):
        if (args.debug): print("site.rss()")
        for item in self.rss_feed(args):
            if(args.debug): print(f"{item}")
            item_title = f"{item['title']} ({item['year']})" if 'year' in item else item['title']
            if (args.debug): print(f"{item_title}")
            if (item['codec'] != config['default']['codec'] or item['resolution'] != config['default']['resolution']):
                if (args.debug): print(f"invalid codec ({item['codec']}!={config['default']['codec']}) or resolution ({item['resolution']}!={config['default']['resolution']})")
                continue

            if (args.verbose): print(f"processing {item_title} S{item['season']}E{item['episode']}:")
            title = db.get_title(item_title, year = True, headless=args.yes)
            if (title is None):
                uravo.event({'AlertGroup':'db_title', 'AlertKey':item_title, 'Severity':'yellow', 'Summary':f"Can't get {db.name} title for {item_title}"})
                print(f" ... FAILED: couldn't find {db.name} title for {item_title}")
                continue
            uravo.event({'AlertGroup':'db_title', 'AlertKey':item_title, 'Severity':'green', 'Summary':f"Can't get {db.name} title for {item_title}"})

            transformation = delugeonal.transform(title, item['season'], item['episode'])
            if (transformation is not None):
                if (args.verbose): print(f" ... applying transformation: season {item['season']}=>{transformation['season']}, episode {item['episode']}=>{transformation['episode']}")
                item['season'] = transformation['season']
                item['episode'] = transformation['episode']

            exists = False
            try:
                exists = server.exists(title, item['season'], item['episode'])
                uravo.event({"AlertGroup":"server_title", "AlertKey":title, "Severity":"green", "Summary":f"Got {server.name} title for {title}"})
            except:
                print(f" ... can't get {server.name} title for '{title}'")
                uravo.event({"AlertGroup":"server_title", "AlertKey":title, "Severity":"yellow", "Summary":f"Can't get {server.name} title for {title}"})
                #continue

            if (exists):
                if (args.verbose): print(f" ... {title} S{item['season']}E{item['episode']} already in {server.name}")
                continue

            episode_key = f"{title}|S{item['season']}E{item['episode']}"
            if ('downloads' not in self.cache['site']): self.cache['site']['downloads'] = {}
            if (episode_key not in self.cache['site']['downloads']):
                self.cache['site']['downloads'][episode_key] = { 'item':item }
            elif (args.force is False and 'date' in self.cache['site']['downloads'][episode_key] and self.cache['site']['downloads'][episode_key]['date'] > datetime.now() - timedelta(hours=1)):
                if (args.verbose): print(f" ... already downloaded within the last hour")
                continue

            link_url = item['url']
            if args.debug: print(f"link_url:{link_url}")
            if (os.path.exists(config['default']['download_dir']) is False):
                raise Exception(f"{config['default']['download_dir']} does not exist.")
            torrent_filename = re.sub(" ", ".", item['name']) + ".torrent"
            if args.verbose: print(f" ... downloading {torrent_filename} to {config['default']['download_dir']}")
            if (args.dryrun is False):
                r = requests.get(link_url, stream=True)
                with open(f"{config['default']['download_dir']}/{torrent_filename}", "wb") as f:
                   for chunk in r.iter_content(chunk_size=128):
                      f.write(chunk)
                self.cache['site']['downloads'][episode_key]['date'] = datetime.now()

    # return [{name, title, season, episode, url}, ...]
    @abstractmethod
    def rss_feed(self, args=minorimpact.default_arg_flags):
        pass

