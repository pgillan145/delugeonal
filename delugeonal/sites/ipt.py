import delugeonal.mediasite
import re
import requests
import xml.etree.ElementTree as ET


class MediaSite(delugeonal.mediasite.site):
    def __init__(self, config, mediaserver = None):
        super().__init__('ipt', config, mediaserver = mediaserver, name = 'IPTorrents')

    # return [{name, title, season, episode, url, codec, resolution}]
    def rss_feed(self):
        items = []
        r = requests.get(self.rss_url)
        root = ET.fromstring(r.text)

        for item in root.findall('.//item'):
            name = item.find('title').text
            # <pubDate>Mon, 14 Mar 2022 03:02:25 +0000</pubDate>
            # date = item.find('pubDate').text
            # <description>810 MB; TV/Web-DL</description>
            # description = item.find('description').text
            
            link_url = item.find('link').text
            if (name is None or name == '' or link_url is None or link_url == ''):
                continue
            items.append((name, link_url))
        return items

    def search_site(self, search_string):
        return []
