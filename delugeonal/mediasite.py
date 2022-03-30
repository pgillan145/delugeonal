from abc import ABC, abstractmethod
import atexit
from datetime import datetime,timedelta
import delugeonal
from . import cache, mediadbs
from dumper import dump
import minorimpact
import os.path
import PTN
import re
import requests
import sys
from uravo import uravo

class site(ABC):
    def __init__(self, key, config, mediaserver = None, name = None):
        atexit.register(self.cleanup)
        if (name is None):
            name = key
        self.site_key = key
        self.name = name
        self.mediaserver = mediaserver

        if ('site' not in cache):
            cache['site'] = {}
        self.cache = cache['site']
        if (self.site_key is None):
            raise Exception("site key is not defined")
        if (self.site_key not in config):
            raise Exception("'{}' not in config".format(self.site_key))

        self.config = config

        self.rss_url = self.config[self.site_key]['rss_url'] if ('rss_url' in self.config[self.site_key]) else None
        self.search_url = self.config[self.site_key]['search_url'] if ('search_url' in self.config[self.site_key]) else None

    def cleanup(self):
        pass

    def download(self, downloads, args = minorimpact.default_arg_flags):
        """Download torrent files.

        Parameters
        ----------
        list
            tuple
                str
                    Name of the torrent file.
                str
                    Download url.
        """
        #print("mediasite.download()")

        if (downloads is None):
            raise Exception("downloads is not defined")

        download_log = []
        download_count = 0
        for name, url in downloads:
            parsed = PTN.parse(name)
                
            if ('codec' not in parsed):
                if (args.debug): print("couldn't parse codec from {}".format(name))
                continue
            if ('title' not in parsed or 'season' not in parsed or 'episode' not in parsed):
                if (args.debug): print("couldn't parse title, season or episode from {}".format(name))
                continue
            if ('resolution' not in parsed):
                # I have reservations about this.
                parsed['resolution'] = '480p'
            if (args.debug): print(parsed)

            item = { 'name':name, 'title':parsed['title'], 'season':parsed['season'], 'episode':parsed['episode'], 'url':url, 'codec':parsed['codec'], 'resolution':parsed['resolution']}
            if(args.debug): print(item)

            item_title = "{} ({})".format(item['title'], item['year']) if 'year' in item else item['title']
            codec =  args.codec[0] if hasattr(args, 'codec') and args.codec is not None else self.config['default']['codec'] 
            resolution =  args.resolution[0] if hasattr(args, 'resolution') and args.resolution is not None else self.config['default']['resolution'] 
            if (item['codec'] != codec):
                if (args.debug): print("invalid codec ({}!={})".format(item['codec'], codec))
                continue
            if (item['resolution'] != resolution):
                if (args.debug): print("invalid resolution ({}!={})".format(item['resolution'], resolution))
                continue

            if (args.verbose): print("processing {} S{}E{}:".format(item_title, item['season'], item['episode']))
            title = None
            for db in mediadbs:
                if (db.istype('tv')):
                    title = db.get_title(item_title, year = True, headless=args.yes)
                    if (title is not None):
                        break
                if (title is None):
                    uravo.event({'AlertGroup':'db_title', 'AlertKey':item_title, 'Severity':'yellow', 'Summary':"Can't get {} title for {}".format(db.name, item_title)})
                    if (args.verbose): print(" ... FAILED: couldn't find {} title for {}".format(db.name, item_title))
                    continue
                uravo.event({'AlertGroup':'db_title', 'AlertKey':item_title, 'Severity':'green', 'Summary':"Got {} title for {}".format(db.name, item_title)})

            # Apply transformations to the "official" name.  This is where the user gets to override the wisdom of the masses for their own
            #   nefarious ends.
            transformation = delugeonal.transform(title, item['season'], item['episode'])
            if (transformation is not None):
                if (args.verbose): print(" ... applying transformation: '{}'=>'{}', season {}=>{}, episode {}=>{}".format(title, transformation['title'], item['season'], transformation['season'], item['episode'], transformation['episode']))
                title = transformation['title']
                item['season'] = transformation['season']
                item['episode'] = transformation['episode']

            if (self.mediaserver is not None):
                exists = False
                try:
                    exists = self.mediaserver.exists(title, item['season'], item['episode'], args = args)
                    uravo.event({'AlertGroup':'server_title', 'AlertKey':title, 'Severity':'green', 'Summary':"Got {} title for '{}'".format(self.mediaserver.name, title)})
                except Exception as e:
                    if (args.verbose): print(" ... FAILED: can't get {} title for '{}'".format(self.mediaserver.name, title))
                    uravo.event({'AlertGroup':'server_title', 'AlertKey':title, 'Severity':'yellow', 'Summary':"Can't get {} title for '{}'".format(self.mediaserver.name, title)})
                    continue
                
                if (exists):
                    if (args.verbose): print(" ... {} S{}E{} already in {}".format(title, item['season'], item['episode'], self.mediaserver.name))
                    continue

            episode_key = "{}|S{}E{}".format(title, item['season'], item['episode'])
            if (episode_key in download_log):
                # Yes, download_log *is* redundant (and a shitty hack), but in the case of --dryrun I don't want to add the download to the permanent cache, 
                # but I *also* don't want to ask the user to download multiple copies of the same torrent.
                continue
            if ('downloads' not in self.cache): self.cache['downloads'] = {}
            if (episode_key not in self.cache['downloads']):
                self.cache['downloads'][episode_key] = { 'item':item }
            elif (args.force is False and 'date' in self.cache['downloads'][episode_key] and self.cache['downloads'][episode_key]['date'] > datetime.now() - timedelta(hours=1)):
                if (args.verbose): print(" ... already downloaded within the last hour")
                continue

            link_url = item['url']
            if args.debug: print("link_url:{}".format(link_url))
            if (os.path.exists(self.config['default']['download_dir']) is False):
                raise Exception(self.config['default']['download_dir'] + " does not exist.")
            torrent_filename = re.sub(" ", ".", item['name']) + ".torrent"
            c = 'y' if (args.yes) else minorimpact.getChar(default='y', end='\n', prompt="Download {} to {}? (Y/n) ".format(torrent_filename, self.config['default']['download_dir']), echo=True).lower()
            if (c == 'y'):
                if args.verbose: print(" ... downloading {} to {}".format(torrent_filename, self.config['default']['download_dir']))
                if (args.dryrun is False):
                    r = requests.get(link_url, stream=True)
                    with open(self.config['default']['download_dir'] + '/' + torrent_filename, 'wb') as f:
                       for chunk in r.iter_content(chunk_size=128):
                          f.write(chunk)
                    self.cache['downloads'][episode_key]['date'] = datetime.now()
                download_log.append(episode_key)
                download_count += 1
        return download_count
        
    def rss(self, args = minorimpact.default_arg_flags):
        if (args.debug): print("mediasite.rss()")
        if (self.rss_url is None):
            raise Exception("rss_url is not defined")
        self.download(self.rss_feed(), args = args)

    @abstractmethod
    def rss_feed(self):
        """Returns a list of dicts containing information about each torrent item available on the rss feed.

        Returns
        -------
        list
            tuple
                str
                    The name of the torrent.
                str
                    The download url.
        """
        pass

    def search(self, search_string, download = True, args = minorimpact.default_arg_flags):
        results = self.search_site(search_string)
        if (download is True):
            self.download(results, args = args)
        else:
            return results

    @abstractmethod
    def search_site(self, search_string):
        """Search this site and return a list of available torrents.

        Parameters
        ----------
        search_string : str
            The text to search for.

        Returns
        -------
        list
            tuple 
                str
                    The torrent name.
                str
                    The download url.
        """
        pass

