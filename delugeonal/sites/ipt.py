import delugeonal.mediasite
from delugeonal import server
from datetime import datetime,timedelta
from dumper import dump
from fuzzywuzzy import fuzz
import imdb
import minorimpact
#import PTN
import re
import requests
import sys
from uravo import uravo
import xml.etree.ElementTree as ET


class MediaSite(delugeonal.mediasite.site):
    def __init__(self):
        self.site_key = 'ipt'
        super().__init__()
        self.name = "IPTorrents"

    # return [{name, title, season, episode, url, codec, resolution}]
    def rss_feed(self, args = minorimpact.default_arg_flags):
        items = []
        if (args.debug): print(self.rss_url)
        r = requests.get(self.rss_url)
        root = ET.fromstring(r.text)

        if (args.verbose): minorimpact.fprint(f"searching {self.name}:")
        for item in root.findall('.//item'):
            name = item.find('title').text
            
            #parsed = PTN.parse(name)
            #if ('codec' not in parsed):
            #    if (args.debug): print(f"couldn't parse codec from {name}")
            #    continue
            #if ('resolution' not in parsed):
            #    if (args.debug): print(f"couldn't parse resolution from {name}")
            #    continue
            #if ('title' not in parsed or 'season' not in parsed or 'episode' not in parsed):
            #    if (args.debug): print(f"couldn't parse title, season or episode from {name}")
            #    continue

            #if (args.debug): print(f"{parsed}")

            #parsed_title = f"{parsed['title']} ({parsed['year']})" if 'year' in parsed else parsed['title']

            link_url = item.find('link').text
            if (name is None or name == '' or link_url is None or link_url == ''):
                continue
            if (args.verbose): print(f" ... found '{name}'")
            #items.append({'name':name, 'title':parsed_title, 'season':parsed['season'], 'episode':parsed['episode'], 'url':link_url, 'codec':parsed['codec'], 'resolution':parsed['resolution']})
            items.append((name, link_url))
        return items

    def search(self, search_string, args = minorimpact.default_arg_flags):
        return []
