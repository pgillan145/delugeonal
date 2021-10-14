import delugeonal.mediasite
from delugeonal import server
from datetime import datetime,timedelta
from dumper import dump
from fuzzywuzzy import fuzz
import imdb
import minorimpact
import PTN
import re
import requests
import sys
from uravo import uravo
import xml.etree.ElementTree as ET


class MediaSite(delugeonal.mediasite.site):
    def __init__(self):
        self.site_key = 'tgx'
        super().__init__()
        #self.url = delugeonal.config['tgx']['rss_url']
        #self.dl_type = delugeonal.config['tgx']['dl_type']
        self.name = 'TorrentGalaxy'

    # return [{name, title, season, episode, url, codec, resolution}]
    def rss_feed(self, args = minorimpact.default_arg_flags):
        items = []
        if (args.debug): print(self.url)
        r = requests.get(self.url)
        root = ET.fromstring(r.text)

        if (args.verbose): minorimpact.fprint(f"searching {self.name}:")
        for item in root.findall('.//item'):
            name = item.find('title').text
            category = item.find('category').text
            if (re.match("TV : Episodes", category) is None):
                continue

            #parsed = PTN.parse(name)
            #if ('codec' not in parsed or 'resolution' not in parsed):
            #    if (args.verbose): print(f"couldn't parse codec and resolution from {name}")
            #    continue
            #if ('title' not in parsed or 'season' not in parsed or 'episode' not in parsed):
            #    if (args.verbose): print(f"couldn't parse title, season and episode from {name}")
            #    continue

            #if (args.debug): print(f"{parsed}")

            #parsed_title = f"{parsed['title']} ({parsed['year']})" if 'year' in parsed else parsed['title']

            link_url = item.find('link').text
            if (name is None or name == '' or link_url is None or link_url == ''):
                continue
            if (args.debug): print(f" ... found {name} ")
            items.append((name, link_url))
        return items
        
