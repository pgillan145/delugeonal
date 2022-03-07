import delugeonal.torrentclient
from delugeonal import config, server
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import yaml

class TorrentClient(delugeonal.torrentclient.TorrentClient):
    def __init__(self):
        super().__init__()

    def add_torrent(self, f, path=None):
        command = [f'--add',f'{f}']
        if (path is not None):
            command = [f'--add','{f}','--download-dir',f'{path}']
        return self._do_command(command)

    def delete_torrent(self, f, remove_data=False):
        id = self.get_id(f)
        command = [f'-t{id}', '--remove']
        if (remove_data is True):
            command = [f'-t{id}', '--remove-and-delete']
        return self._do_command([command])

    def _do_command(self, command = []):
        if (len(command) == 0):
            return
        command.insert(0, config['transmission']['transmission_remote'])
        #print(' '.join(command))
        proc = subprocess.Popen(command, stdout=subprocess.PIPE)
        #time.sleep(1)
        output  = str(proc.stdout.read(), 'utf-8')
        #print(f"returncode:{proc.returncode}")
        #print(f"output:{output}")
        return output

    def get_torrent_file(self, filename, verbose=False, config = None):
        pass

    def get_config(self):
        with open('/etc/transmission-daemon/settings.json', 'r') as f:
            config = json.load(f)
        return config

    def get_id(self, filename, verbose = False):
        info = self.get_info()
        if (filename not in info):
            raise Exception(f"can't find ID for {filename}")
        return info[filename]['id']

    def get_info(self, filename = None, verbose=False):
        #deluge_config = self.get_config()
        command = ['-l']
        list_str = self._do_command(command)

        info = {}
        for t in list_str.split('\n'):
            if (len(t) == 0 or re.match('ID ', t) or re.match('Sum: ', t)):
                continue

            m = re.search('^\s*(?P<id>\d+)\s+', t)
            if (m is None): continue
            g = m.groupdict()
            id = g['id']
            info_str = self._do_command([f'-t{id}', '-i'])

            f = None
            for l in info_str.split('\n'):
                s = re.search("^  Name: (\S.+)$", l)
                if (s):
                    f = s.groups()[0]
                    #info[f] = {"name":f, "orig_torrent_file":self.get_torrent_file(f, config=deluge_config, verbose=verbose), "data_file":self.get_data_file(f, config=deluge_config, verbose=verbose), "ratio":0.0, "tracker":None, "trackerstatus":None, "state":None}
                    info[f] = {"name":f, "id":id, "ratio":0.0, "state":None}

                #s = re.search("^  Id: (\S+)$", l)
                #if (s):
                #    print(s.groups()[0])
                #    info[f]["id"] = s.groups()[0]

                s = re.search('^  Location: (.+)$', l)
                if (s):
                    info[f]["data_file"] = f'{s.groups()[0]}/{f}'

                s = re.search("^  Ratio: ([\d\.]+)", l)
                if (s):
                    info[f]["ratio"] = float(s.groups()[0])

                s = re.search("^  State: (\S+)", l)
                if (s):
                    info[f]["state"] = s.groups()[0]

                s = re.search('^  Seeding Time:\s+.*? \((\d+) seconds\)$', l)
                if (s):
                    secs = int(s.groups()[0])
                    info[f]["seedtime"] = secs

                s = re.search("^  Total size: ([\d\.]+) (\w+) ", l)
                if (s):
                    size = 0
                    if (s.groups()[1] == "GB"):
                        size = int(float(s.groups()[0]) * 1024 * 1024)
                    elif (s.groups()[1] == "MB"):
                        size = int(float(s.groups()[0]) * 1024)
                    else:
                        size = int(float(s.groups()[0]))
                    info[f]["size"] = size

            if (id and f):
                tracker_str = self._do_command([f'-t{id}','-it'])
                tracker = None
                trackers = []
                #  Tracker 2: udp://tracker.leechers-paradise.org:6969
                #  Active in tier 2
                #  Got an error "Connection failed" 21 minutes (1289 seconds) ago
                #  Asking for more peers in 38 minutes (2312 seconds)
                #  Got a scrape error "Connection failed" 12 minutes (734 seconds) ago
                #  Asking for peer counts in 1 hour, 48 minutes (6525 seconds)

                #  Tracker 3: udp://tracker.pomf.se:80
                #  Active in tier 3
                #  Got a list of 4 peers 22 minutes (1352 seconds) ago
                #  Asking for more peers in 7 minutes (473 seconds)
                #  Tracker had 2 seeders and 2 leechers 22 minutes (1352 seconds) ago
                #  Asking for peer counts in 7 minutes (455 seconds)

                line = 0
                for lt in tracker_str.split('\n'):
                    line = line + 1
                    if (len(lt) == 0): 
                        if (tracker is not None):
                            if ('status' not in tracker):
                                tracker['status'] = 'unknown'
                            trackers.append(tracker)
                        tracker = {}
                        line = 1
                        continue
                    s = re.search('^  Tracker \d+: (?P<protocol>https?|udp)://(?P<name>[^:]+):(?P<port>\d+)', lt)
                    if (s):
                        g = s.groupdict()
                        #tracker['name'] = g['names']
                        names = g['name'].split('.')
                        names = names[::-1]
                        tracker['name'] = f'{names[1]}.{names[0]}'
                        tracker['port'] = g['port']
                        tracker['protocol'] = g['protocol']

                        #info[f]['tracker'] = s.groups()[0]
                        #break
                        #info[f]["trackerstatus"] = s.groups()[1]
                    #s = re.search('^  (\S+) in tier \d', lt)
                    if (s):
                        s = re.search('^  Got a list of \d+ ', lt)
                        tracker['status'] = 'ok'
                    else:
                        s = re.search('^  Got an error ', lt)
                        if (s):
                            tracker['status'] = 'error'
                    if (line == 4):
                        tracker['statusline'] = lt
                info[f]['trackers'] = trackers
                for t in trackers:
                    info[f]['tracker'] = t['name']
                    info[f]['trackerstatus'] = t['status']
                    if t['status'] == 'ok': break

        if (len(info.keys()) == 0):
            exception = "no torrent info"
            if (filename is not None):
                exception = f"{exception} for {filename}"
            raise Exception(exception)

        if (filename):
            return {filename: info[filename]}

        return info

    def move_torrent(self, torrent, target):
        id = self.get_id(torrent)
        command = [f'-t{id}', '--move',target]
        self._do_command(command)

    def pause_all(self):
        command = ['-t', 'all', '--stop']
        return self._do_command(command)

    def resume_all(self):
        command = ['-t', 'all', '--start']
        return self._do_command(command)
            
