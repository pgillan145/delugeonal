import delugeonal.mediasite
import re
import requests
import urllib.parse
import xml.etree.ElementTree as ET


class MediaSite(delugeonal.mediasite.site):
    def __init__(self, config):
        super().__init__('eztv', config, name = 'EZTV')

    def rss_feed(self):
        """Retrieve the rss feed for this site and return a list of torrents."""
        if (self.config is None):
            return []

        items = []
        r = requests.get('https://eztv.re/ezrss.xml')
        root = ET.fromstring(r.text)

        for item in root.findall('.//item'):
            name = item.find('title').text
            enclosure = item.find('enclosure')
            if (enclosure is not None):
                link_url = enclosure.attrib['url']
                if (name is None or name == '' or link_url is None or link_url == ''):
                    continue

                items.append({ 'name': name, 'url': link_url})
        return items

    def search_site(self, search_string):
        """Search this site and return a list of available torrents.

        Parameters
        ----------
        search_string : str
            The string to search for.

        Returns
        -------
        list
            dict
                name : str
                    The name of the torrent.
                url : str
                    The url.
        """
        if (self.config is None):
            return []
        
        # TODO: Order by seeds, and take the highest.
        search_url = 'https://eztv.re/search/'

        unsorted = []
        url = search_url + str(search_string)
        r = requests.get(url)
        #print(r.text)
        for m in re.findall(r'<a href="(https://[^\n]+?([^/]+)\.torrent)".*?<td .*?<td .*?<td .+?>([^<]+)<', r.text, flags=re.DOTALL):
            url = m[0]
            name = urllib.parse.unquote_plus(m[1])
            seeds = m[2]
            if (seeds in ('', '-', '0')): continue

            # Site returns everything if it doesn't find the string, so at the very least make sure that
            #   some of what we're looking for exists in the name before using it
            partial_match = False
            for x in name.split('.'):
                if (partial_match): break
                for y in search_string.split(' '):
                    if (x.lower() == y.lower()):
                        partial_match = True
                        break
            if (partial_match is False): continue

            unsorted.append((name, url, seeds))

        items = []
        # Return the results in order from highest seeded to lowest.
        for name, url, seeds in sorted(unsorted, key=lambda x: int(x[2]), reverse = True):
            items.append({ 'name': name, 'url': url})

        return items

    def trackers(self):
        return []
