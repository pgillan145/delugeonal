import delugeonal.torrentclient
import os
import re
import shutil
import subprocess
import tempfile
import yaml

class TorrentClient(delugeonal.torrentclient.TorrentClient):
    def __init__(self, config):
        super().__init__(config)

    def add_torrent(self, f, path=None):
        command = 'add "{}"'.format(f)
        if (path is not None):
            command = 'add --path "{}" "{}"'.format(path, f)
        return self._do_command([command])

    def delete_torrent(self, f, remove_data=False):
        command = 'del "{}"'.format(f)
        if (remove_data is True):
            command = 'del --remove_data "{}"'.format(f)
        return self._do_command([command])

    def _do_command(self, command = []):
        if (len(command) == 0):
            return
        command.insert(0, self.config['deluge']['deluge_console'])
        #print(' '.join(command))
        proc = subprocess.Popen(command, stdout=subprocess.PIPE)
        output  = str(proc.stdout.read(), 'utf-8')
        return output

    def get_config(self):
        deluge_config = yaml.safe_load(self._do_command(['config']))
        return deluge_config

    def get_data_file(self, filename, verbose=False, config = None):
        data_file = None
        if (config is None):
            config = get_config()

        data_dir = config['download_location']
        if (config['move_completed']):
            data_dir = config['move_completed_path']

        if os.path.exists("{}/{}".format(data_dir, filename)):
            data_file = "{}/{}".format(data_dir, filename)
        return data_file

    def get_info(self, filename = None, verbose=False):
        deluge_config = self.get_config()
        state_dir = os.path.dirname(deluge_config["plugins_location"]) + "/state"
        if verbose: print("pulling deluge info for {}".format(filename))
        if (filename):
            command = ['info "{}"'.format(filename)]
        else:
            command = ['info']
        info_str = self._do_command(command)

        f = None
        info = {}
        for l in info_str.split("\n"):
            if (len(l) == 0):
                continue
            s = re.search("^Name: (\S.+)$", l)
            if (s):
                f = s.groups()[0]
                info[f] = {'name':f, 'orig_torrent_file':self.get_torrent_file(f, config=deluge_config, verbose=verbose), 'data_file':self.get_data_file(f, config=deluge_config, verbose=verbose), 'ratio':0.0, 'tracker':None, 'trackerstatus':None, 'state':None, 'size':0}

            s = re.search("^ID: (\S+)$", l)
            if (s):
                info[f]["id"] = s.groups()[0]
                info[f]["torrent_file"] = state_dir + "/" + info[f]["id"] +  ".torrent"

            s = re.search("Ratio: ([\d\.]+)", l)
            if (s):
                info[f]["ratio"] = float(s.groups()[0])

            s = re.search("^State: (\S+)", l)
            if (s):
                info[f]["state"] = s.groups()[0]

            s = re.search("Seed time: (\d+) days (\d\d):(\d\d):(\d\d) ", l)
            if (s):
                secs = int(s.groups()[0]) * 24 * 60 * 60
                secs = secs + int(s.groups()[1]) * 60 * 60
                secs = secs + int(s.groups()[2]) * 60
                secs = secs + int(s.groups()[3])
                info[f]["seedtime"] = secs

            s = re.search("Size: ([\d\.]+) (\w+)\/", l)
            if (s):
                size = 0
                if (s.groups()[1] == "GiB"):
                    size = int(float(s.groups()[0]) * 1024 * 1024)
                elif (s.groups()[1] == "MiB"):
                    size = int(float(s.groups()[0]) * 1024)
                else:
                    size = int(float(s.groups()[0]))
                info[f]["size"] = size

            s = re.search("Tracker status: ([^:]+): (.+)$", l)
            if (s):
                info[f]["tracker"] = s.groups()[0]
                info[f]["trackerstatus"] = s.groups()[1]

        if (len(info.keys()) == 0):
            exception = "no torrent info"
            if (filename is not None):
                exception = "{} for {}".format(exception, filename)
            raise Exception(exception)
        return info

    def get_torrent_file(self, filename, verbose=False, config = None):
        if(verbose):print("get_torrent_file({})".format(filename))
        torrent_file = None
        if (config is None):
            config = get_config()
        
        torrent_dir = config['torrentfiles_location']
        if os.path.exists('{}/{}.torrent'.format(torrent_dir, filename)):
            torrent_file = '{}/{}.torrent'.format(torrent_dir, filename)
        elif os.path.exists('{}/{} [IPT].torrent'.format(torrent_dir, filename)):
            torrent_file = '{}/{} [IPT].torrent'.format(torrent_dir, filename)
        elif (os.path.exists(torrent_dir + '/'+ re.sub('YTS.AM', 'YTS.MX', filename))):
            torrent_file = torrent_dir + '/' + re.sub('YTS.AM', 'YTS.MX', filename)
        else:
            if (verbose): print("searching for torrent file")
            for f in os.listdir(torrent_dir):
                if (re.search("^\.", f)):
                    continue
                tmp = re.sub(' +$','', re.sub('.torrent$','', re.sub('\[.+\]','', f)))
                if (re.search('^' + re.escape(tmp), filename, re.IGNORECASE)):
                    torrent_file = torrent_dir + '/' + f
                    break

                # Try looking at all the different parts of the filename, maybe they're just in a different
                #   order
                match = 0
                parsed = f.split(' ')
                if (verbose): print("checking " + f)
                for p in parsed:
                    if re.search(re.escape(p), filename):
                        if (verbose): print("  match: " + p)
                        match = match + 1
                if (verbose): print("  score: " + (match/len(parsed)))
                if (match/len(parsed) >= .70):
                    if (verbose): print("  match!")
                    torrent_file = torrent_dir + '/' + f
                    break
        return torrent_file

    def move_torrent(self, torrent, target):
        deluge_config = self.get_config()

        download_dir = deluge_config['download_location']
        data_dir = download_dir
        if (deluge_config['move_completed']):
            data_dir = deluge_config['move_completed_path']

        if (os.path.exists(data_dir + '/' + torrent) is False):
            raise Exception("cannot find '{}'".format(torrent))
        if (os.path.exists(target) is False):
            raise Exception("{} does not exist)".format(target))

        info = self.get_info(torrent)
        torrent_file = info[torrent]["torrent_file"]
        if (torrent_file is None or os.path.exists(torrent_file) is False):
            raise Exception("can't find torrent file for {}".format(torrent))
        test_dir = tempfile.TemporaryDirectory()
        tmp_torrent_file = test_dir.name + '/' + info[torrent]['id'] + '.torrent'
        shutil.copyfile(torrent_file, tmp_torrent_file)

        self.delete_torrent(torrent)
        shutil.move(data_dir + '/' + torrent, target + '/' + torrent)
        return self.add_torrent(tmp_torrent_file, path=target)

    def pause_all(self):
        command = 'pause *'
        return self._do_command([command])

    def resume_all(self):
        command = 'resume *'
        return self._do_command([command])
            
