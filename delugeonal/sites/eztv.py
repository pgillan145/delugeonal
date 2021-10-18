import delugeonal.mediasite
import re
import requests
import urllib.parse
import xml.etree.ElementTree as ET


class MediaSite(delugeonal.mediasite.site):
    def __init__(self):
        super().__init__('eztv', 'EZTV')

    # return [{name, title, season, episode, url, codec, resolution}]
    def rss_feed(self):
        """Retrieve the rss feed for this site and return a list of torrents."""
        items = []
        r = requests.get(self.rss_url)
        root = ET.fromstring(r.text)

        for item in root.findall('.//item'):
            name = item.find('title').text
            enclosure = item.find('enclosure')
            if (enclosure is not None):
                link_url = enclosure.attrib['url']
                if (name is None or name == '' or link_url is None or link_url == ''):
                    continue

                items.append((name, link_url))
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
            tuple
                str
                    The name of the torrent.
                str
                    The url.
        """
        
        # TODO: Order by seeds, and take the highest.
        if (self.search_url is None):
            raise Exception("search_url is not defined")

        unsorted = []
        url = self.search_url + str(search_string)
        r = requests.get(url)
        #print(r.text)
        for m in re.findall('<a href="(https:\/\/[^\n]+?([^/]+)\.torrent)".*?<td .*?<td .*?<td .+?>([^<]+)<', r.text, flags=re.DOTALL):
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
            #print(f"{seeds}, {name}")
            items.append((name,url))

        return items

