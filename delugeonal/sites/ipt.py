import delugeonal.mediasite
import re
import requests
import xml.etree.ElementTree as ET


class MediaSite(delugeonal.mediasite.site):
    def __init__(self):
        super().__init__('ipt', 'IPTorrents')

    # return [{name, title, season, episode, url, codec, resolution}]
    def rss_feed(self):
        items = []
        r = requests.get(self.rss_url)
        root = ET.fromstring(r.text)

        for item in root.findall('.//item'):
            name = item.find('title').text
            
            link_url = item.find('link').text
            if (name is None or name == '' or link_url is None or link_url == ''):
                continue
            if (args.verbose): print(f" ... found '{name}'")
            items.append((name, link_url))
        return items

    def search_site(self, search_string):
        return []
