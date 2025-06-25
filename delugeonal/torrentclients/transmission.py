import delugeonal.torrentclient
import datetime
from dumper import dump
import json
import os
import re
import subprocess
#import time


months = {'Jan':1, 'Feb':2, 'Mar':3, 'Apr':4, 'May':5, 'Jun':6, 'Jul':7, 'Aug':8, 'Sep':9, 'Oct':10, 'Nov':11, 'Dec':12}

class TorrentClient(delugeonal.torrentclient.TorrentClient):
    def __init__(self, config):
        super().__init__(config)

    def add_torrent(self, f, path=None):
        command = ['--add',f]
        if (path is not None):
            command = ['--add',f,'--download-dir',path]
        return self._do_command(command)

    def delete_torrent(self, f, remove_data=False):
        id = self.get_id(f)
        command = ['-t{}'.format(id), '--remove']
        if (remove_data is True):
            command = ['-t{}'.format(id), '--remove-and-delete']
        return self._do_command(command)

    def _do_command(self, command = []):
        if (len(command) == 0):
            return

        #dump(self.config)
        base_command = []
        base_command.insert(0, self.config['transmission']['transmission_remote'])
        host = self.config['transmission']['host'] if 'host' in self.config['transmission'] else None
        port = self.config['transmission']['port'] if 'port' in self.config['transmission'] else None
        user = self.config['transmission']['user'] if 'user' in self.config['transmission'] else None
        password = self.config['transmission']['password'] if 'password' in self.config['transmission'] else None

        if (host is not None and port is not None):
            base_command.append(f'{host}:{port}')
        if (user is not None and password is not None):
            base_command = base_command + ['-n', f'{user}:{password}']

        full_command = base_command + command

        #dump(full_command)
        #print(' '.join(full_command))
        proc = subprocess.Popen(full_command, stdout=subprocess.PIPE)
        #time.sleep(1)
        output  = str(proc.stdout.read(), 'utf-8')
        return output

    def get_torrent_file(self, filename, verbose=False, config = None):
        pass

    def get_config(self):
        settings = self.config['transmission']['settings'] if ('settings' in self.config['transmission']) else None
        if (settings is None):
            raise Exception("no settings file configured")

        with open(settings, 'r') as f:
            config = json.load(f)
        return config

    def get_id(self, filename, verbose = False):
        info = self.get_info()
        if (filename not in info):
            raise Exception("can't find ID for {}".format(filename))
        return info[filename]['id']

    def get_info(self, filename = None, verbose=False):
        #deluge_config = self.get_config()
        command = ['-l']
        list_str = self._do_command(command)

        info = {}
        for t in list_str.split('\n'):
            if (len(t) == 0 or re.match('ID ', t) or re.match('Sum: ', t)):
                continue

            m = re.search('^\\s*(?P<id>\\d+)\\s+', t)
            if (m is None): continue
            g = m.groupdict()
            id = g['id']
            info_str = self._do_command(['-t{}'.format(id), '-i'])

            f = None
            for l in info_str.split('\n'):
                s = re.search("^  Name: (\\S.+)$", l)
                if (s):
                    f = s.groups()[0]
                    #info[f] = {"name":f, "orig_torrent_file":self.get_torrent_file(f, config=deluge_config, verbose=verbose), "data_file":self.get_data_file(f, config=deluge_config, verbose=verbose), "ratio":0.0, "tracker":None, "trackerstatus":None, "state":None}
                    info[f] = {'name':f, 'id':id, 'ratio':0.0, 'state':None, 'seedtime':0, 'size':0, 'upload_value':0.00000}

                #s = re.search("^  Id: (\S+)$", l)
                #if (s):
                #    print(s.groups()[0])
                #    info[f]["id"] = s.groups()[0]

                s = re.search('^  Location: (.+)$', l)
                if (s):
                    info[f]["data_file"] = '{}/{}'.format(s.groups()[0], f)

                s = re.search("^  Ratio: ([\\d\\.]+)", l)
                if (s):
                    info[f]["ratio"] = float(s.groups()[0])

                s = re.search("^  State: (\\S+)", l)
                if (s):
                    info[f]["state"] = s.groups()[0]

                s = re.search("^  Location: (\\S+)", l)
                if (s):
                    info[f]["location"] = s.groups()[0]

                #  Date added:       Sun Aug 11 01:28:02 2024
                s = re.search('^  Date added:\\s+... (...) (\\d\\d) (\\d\\d):(\\d\\d):(\\d\\d) (\\d\\d\\d\\d)$', l)
                if (s):
                    date_added = datetime.datetime(int(s.groups()[5]), months[s.groups()[0]], int(s.groups()[1]), int(s.groups()[2]), int(s.groups()[3]), int(s.groups()[4]))
                    info[f]['date_added'] = date_added
                    info[f]['seedtime'] = int((datetime.datetime.now() - date_added).total_seconds())

                #  Seeding Time:     19 hours (69844 seconds)
                s = re.search('^  Seeding Time:\\s+.*? \\((\\d+) seconds\\)$', l)
                if (s and 'seedtime' not in info[f]):
                    secs = int(s.groups()[0])
                    info[f]["seedtime"] = secs

                if (f in info and 'seedtime' in info[f] and info[f]['seedtime'] > 3600 and 'ratio' in info[f]):
                    upload_value = info[f]['ratio']/int(info[f]['seedtime']/3600)
                    info[f]['upload_value'] = upload_value

                s = re.search("^  Total size: ([\\d\\.]+) (\\w+) ", l)
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
                tracker_str = self._do_command(['-t{}'.format(id),'-it'])
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
                    s = re.search('^  Tracker \\d+: (?P<protocol>https?|udp)://(?P<name>[^:]+):(?P<port>\\d+)', lt)
                    if (s):
                        g = s.groupdict()
                        #tracker['name'] = g['names']
                        names = g['name'].split('.')
                        names = names[::-1]
                        tracker['name'] = '{}.{}'.format(names[1],names[0])
                        tracker['port'] = g['port']
                        tracker['protocol'] = g['protocol']
                    else:
                        #  Tracker 0: routing.bgp.technology:443
                        s = re.search('^  Tracker \\d+: (?P<name>[^:]+):(?P<port>\\d+)', lt)
                        if (s):
                            g = s.groupdict()
                            #tracker['name'] = g['names']
                            names = g['name'].split('.')
                            names = names[::-1]
                            tracker['name'] = '{}.{}'.format(names[1],names[0])
                            tracker['port'] = g['port']
                            tracker['protocol'] = ''

                    s = re.search('^  (\S+) in tier \d', lt)
                    if (s):
                        s = re.search('^  Got a list of \\d+ ', lt)
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

                location = info[f]['location']
                max_file_size = 0
                biggest_fie = None
                files_str = self._do_command(['-t{}'.format(id), '--files'])
                for file in files_str.split('\n'):
                    s = re.search(r'\s+(\d+\.\d+)\s+(M|G|k)B\s+(.+)$', file)
                    if (s):
                        val = float(s.group(1))
                        unit = s.group(2)
                        file_name = s.group(3)
                        if (unit == 'k'):
                            val = val * 1000
                        elif (unit == 'M'):
                            val = val * 1000000
                        elif (unit == 'G'):
                            val = val * 1000000000

                        if (val > max_file_size):
                            max_file_size = val
                            biggest_file = file_name

                if (biggest_file is not None):
                    info[f]['primary_file'] = location + '/' + biggest_file
                    info[f]['primary_file_links'] = os.lstat(info[f]['primary_file']).st_nlink

        if (len(info.keys()) == 0):
            exception = "no torrent info"
            if (filename is not None):
                exception = "{} for {}".format(exception, filename)
            raise Exception(exception)

        if (filename):
            return {filename: info[filename]}

        return info

    def move_torrent(self, torrent, target):
        id = self.get_id(torrent)
        command = ['-t{}'.format(id), '--move',target]
        self._do_command(command)

    def pause_all(self):
        command = ['-t', 'all', '--stop']
        return self._do_command(command)

    def resume_all(self):
        command = ['-t', 'all', '--start']
        return self._do_command(command)
            
