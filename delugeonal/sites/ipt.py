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
        super().__init__()
        self.url = delugeonal.config['ipt']['rss_url']
        self.name = "IPTorrents"

    # return [{name, title, season, episode, url, codec, resolution}]
    def rss_feed(self, args = minorimpact.default_arg_flags):
        items = []
        if (args.debug): print(self.url)
        r = requests.get(self.url)
        root = ET.fromstring(r.text)

        if (args.verbose): minorimpact.fprint(f"searching {self.name}:")
        for item in root.findall('.//item'):
            name = item.find('title').text
            
            parsed = PTN.parse(name)
            if ('codec' not in parsed or 'resolution' not in parsed):
                print(f"couldn't parse codec and resolution from {name}")
                continue
            if ('title' not in parsed or 'season' not in parsed or 'episode' not in parsed):
                print(f"couldn't parse title, season and episode from {name}")
                continue

            if (args.verbose): print(f" ... found {name} ")
            if (args.debug): print(f"{parsed}")

            parsed_title = f"{parsed['title']} ({parsed['year']})" if 'year' in parsed else parsed['title']

            link_url = item.find('link').text
            if (link_url is None or link_url == ''):
                continue
            items.append({'name':name, 'title':parsed_title, 'season':parsed['season'], 'episode':parsed['episode'], 'url':link_url, 'codec':parsed['codec'], 'resolution':parsed['resolution']})
        return items
        
