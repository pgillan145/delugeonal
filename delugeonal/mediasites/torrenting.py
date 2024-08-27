import datetime
import delugeonal.mediasite
import re
import requests
import xml.etree.ElementTree as ET


class MediaSite(delugeonal.mediasite.site):
    def __init__(self, config):
        super().__init__('torrenting', config, name = 'Torrenting', seedtime = 3)

    # return [{name, title, season, episode, url, codec, resolution}]
    def rss_feed(self):
        if (self.config is None):
            return []

        items = []
        return items

    def search_site(self, search_string):
        return []

    def trackers(self):
        return ['jumbohostpro.eu', 'connecting.center']
