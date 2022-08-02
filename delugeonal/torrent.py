import bencode
import dumper
import os.path
import re
from urllib.parse import urlparse

class torrent():
    def __init__(self, f):
        if (os.path.exists(f) is False):
            raise Exception("{} does not exist".format(f))
        if (re.search('.torrent$', f) is None):
            raise Exception("{} is not a .torrent file".format(f))

        self.filename = f

        m = open(self.filename, 'rb')
        torrent_data = m.read()
        self.torrent_data = bencode.decode(torrent_data)

    def size(self):
        total_size = 0
        if (self.torrent_data is None or 'info' not in self.torrent_data):
            raise Exception("can't info from {}".format(self.filename))
        if ('files' in self.torrent_data['info']):
            for torrent_file in self.torrent_data['info']['files']:
                total_size = total_size + int(torrent_file['length'])
        elif ('length' in self.torrent_data['info']):
            total_size = int(self.torrent_data['info']['length'])
        else:
            raise Exception("can't size of {}".format(self.filename))
        return total_size

    def trackers(self):
        trackers = []
        if (self.torrent_data is None or 'announce-list' not in self.torrent_data):
            raise Exception("can't gat a list of trackers from {}".format(self.filename))
        for tracker in self.torrent_data['announce-list']:
            for t in tracker:
                trackers.append(urlparse(t).hostname)
        return trackers
