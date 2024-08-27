import datetime
import delugeonal.mediasite
import re
import requests
import xml.etree.ElementTree as ET


class MediaSite(delugeonal.mediasite.site):
    def __init__(self, config):
        super().__init__('ipt', config, name = 'IPTorrents', seedtime = 15)

    # return [{name, title, season, episode, url, codec, resolution}]
    def rss_feed(self):
        if (self.config is None):
            return []

        # TV/x265 = 99 TV/Web-DL = 22 TV/x264 = 5 TV/BD = 23
        if ('user_id' not in self.config):
            raise Exception('user_id is not defined.')
        if ('user_tp' not in self.config):
            raise Exception('user_tp is not defined.')

        url = 'https://iptorrents.com/t.rss?u=' + self.config['user_id'] + ';tp=' + self.config['user_tp'] + ';99;23;22;5;download;subscriptions'

        items = []
        r = requests.get(url)
        root = ET.fromstring(r.text)

        for item in root.findall('.//item'):
            name = item.find('title').text
            # <pubDate>Mon, 14 Mar 2022 03:02:25 +0000</pubDate>
            date = datetime.datetime.strptime(item.find('pubDate').text, '%a, %d %b %Y %H:%M:%S %z')
            # TODO: Parse size and 'category' from the description and add it to the output
            # <description>810 MB; TV/Web-DL</description>
            # description = item.find('description').text
            
            link_url = item.find('link').text
            if (name is None or name == '' or link_url is None or link_url == ''):
                continue
            # TODO: Change this so it returns a dict, rather than a tuple
            items.append({ 'name': name, 'url': link_url, 'date': date })
        return items

    def search_site(self, search_string):
        return []

    def trackers(self):
        return [ 'empirehost.me', 'stackoverflow.tech', 'bgp.technology' ]
