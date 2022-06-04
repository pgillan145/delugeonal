import delugeonal.mediasite
import re
import requests
import urllib.parse
import xml.etree.ElementTree as ET

class MediaSite(delugeonal.mediasite.site):
    def __init__(self, config):
        super().__init__('tgx', config, name = 'TorrentGalaxy')

    def rss_feed(self):
        """Returns a list of dicts containing information about each torrent item available on the rss feed.

        Returns
        -------
        list
            dict
                name : str
                    The name of the torrent.
                url : str
                    The download url.
        """
        if (self.config is None):
            return []

        items = []
        rss_url = 'https://torrentgalaxy.to/rss'
        r = requests.get(rss_url)
        root = ET.fromstring(r.text)

        for item in root.findall('.//item'):
            name = item.find('title').text
            category = item.find('category').text
            if (re.match("TV : Episodes", category) is None):
                continue

            link_url = item.find('link').text
            if (name is None or name == '' or link_url is None or link_url == ''):
                continue
            items.append({ 'name': name, 'url': link_url})
        return items

    def search_site(self, search_string):
        """Search this site and return a list of available torrents.

        Parameters
        ----------
        search_string : str
            The string for which to search.

        Returns
        -------
        list
            dict
                name : str
                    The name of the torrent.
                url : str
                    The download url.
        """
        if (self.config is None):
            return []

        if (search_string is None):
            raise Exception("Invalid search string")

        search_url = 'https://torrentgalaxy.to/torrents.php?search/' + str(search_string)
        r = requests.get(search_url)
        unsorted = []
        for m in re.findall("<a href='(https://[^/]+/get/[a-f0-9]{40}/([^/']+))'.*<span title='Seeders.*?<b>(.+?)</b>", r.text):
            url = m[0]
            name = urllib.parse.unquote_plus(m[1])
            seeds = m[2]
            if (seeds in ('', '-', '0')): continue
            unsorted.append((name, url, seeds))

        items = []
        # Return the results in order from highest seeded to lowest.
        for name, url, seeds in sorted(unsorted, key=lambda x: int(x[2]), reverse = True):
            items.append({ 'name': name, 'url': url})

        return items

    def trackers(self):
        return []
        
