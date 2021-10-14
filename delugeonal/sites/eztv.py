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
        self.site_key = 'eztv'
        super().__init__()
        self.name = 'eztv'

    # return [{name, title, season, episode, url, codec, resolution}]
    def rss_feed(self, args = minorimpact.default_arg_flags):
        """Retrieve the rss feed for this site and return a list of torrents."""
        items = []
        if (args.debug): print(self.rss_url)
        r = requests.get(self.rss_url)
        root = ET.fromstring(r.text)

        if (args.verbose): minorimpact.fprint(f"searching {self.name}:")
        for item in root.findall('.//item'):
            name = item.find('title').text
            link_url = item.find('enclosure').attrib['url']
            if (name is None or name == '' or link_url is None or link_url == ''):
                #if (args.debug): print(f"couldn't parse link for {name}")
                continue

            #parsed = PTN.parse(name)
            #if ('codec' not in parsed or 'resolution' not in parsed):
            #    if (args.verbose): print(f"couldn't parse codec and resolution from {name}")
            #    continue
            #if ('title' not in parsed or 'season' not in parsed or 'episode' not in parsed):
            #    if (args.verbose): print(f"couldn't parse title, season and episode from {name}")
            #    continue

            if (args.verbose): print(f" ... found {name} ")
            #if (args.debug): print(f"{parsed}")

            #parsed_title = f"{parsed['title']} ({parsed['year']})" if 'year' in parsed else parsed['title']
            #items.append({'name':name, 'title':parsed_title, 'season':parsed['season'], 'episode':parsed['episode'], 'url':link_url, 'codec':parsed['codec'], 'resolution':parsed['resolution']})
            items.append((name, link_url))
        return items

    def search(self, search_string, args = minorimpact.default_arg_flags):
        """Search this site and return a list of available torrents."""
        items = []
        if (self.search_url is None):
            raise Exception("search_url is not defined")
        url = self.search_url + str(search_string)
        if (args.debug): print(f"{url}")
        r = requests.get(url)
        for m in re.findall('<a href="(https:\/\/.*?([^/]+)\.torrent)"', r.text):
            items.append((m[1], m[0]))

        return items
