import argparse
from . import db, client, config, site
from fuzzywuzzy import fuzz
import minorimpact
import os
import os.path
import PTN
import re
import shutil
import sys
import time
from uravo import uravo
from torrentool.api import Torrent

def main():
    parser = argparse.ArgumentParser(description="delugeonal")
    parser.add_argument('--add', metavar = 'DIR',  help = "Scan DIR for torrent files, and add them to the client.", nargs=1)
    parser.add_argument('--cleanup',  help = "Remove completed torrents from the client.", action = 'store_true')
    parser.add_argument('--rss',  help = "Check media site rss feeds for new downloads.", action = 'store_true')
    parser.add_argument('--move_download', metavar = ('NAME', 'TARGET_DIR'), help = "Move newly downloaded torrent NAME to TARGET_DIR", nargs=2)
    parser.add_argument('--move_media', help = "Move media files from the download directory to the appropriate media folders", action = 'store_true')
    parser.add_argument('--dryrun', help = "Don't actually make any changes", action='store_true')
    parser.add_argument('--debug', help = "extra extra loud output", action='store_true')
    parser.add_argument('--force', help = "bypass built-in delays", action='store_true')
    parser.add_argument('-v', '--verbose', help = "extra loud output", action='store_true')
    parser.add_argument('-y', '--yes', help = "Always say yes.", action='store_true')
    args = parser.parse_args()
    if (args.dryrun): args.verbose = True
    if (args.add is not None and len(args.add) == 1):
        add(args.add[0], dryrun = args.dryrun, verbose = args.verbose)
    if (args.cleanup):
        cleanup(verbose = args.verbose, yes = args.yes, dryrun = args.dryrun)
    if (args.move_download is not None and len(args.move_download) == 2):
        move_download(args.move_download[0], args.move_download[1], verbose = args.verbose, dryrun = args.dryrun)
    if (args.move_media):
        move_media(verbose = args.verbose, dryrun = args.dryrun, debug = args.debug, yes = args.yes)
    if (args.rss):
        rss(args=args)

def add(directory, dryrun=False, verbose=False):
    if (os.path.exists(directory) is False):
        sys.exit(f"'{directory}' doesn't exist")
    if (dryrun): verbose = True

    total, used, free = shutil.disk_usage('/')
    target_free = total * .05

    for f in os.listdir(directory):
        data = None
        if (re.search('.torrent$', f)):
            data = directory + "/" + f
            t = Torrent.from_file(data)
            if (verbose): print(f"{t}\nsize:{minorimpact.disksize(t.total_size, units='b')}")
            if (free - t.total_size < target_free):
                if (verbose): print(f"not enough free space for {f}")
                continue
            free = free - t.total_size
        elif (re.search('.magnet$', f)):
            m = open(directory + '/' + f, 'r')
            data = m.read()
            # TODO: Try to find the actual size of the magent download, rather than just rejecting them
            #   if the remaining disk space is lower than a certain percentage.  (Especially because it will
            #   essentially add all magnets, since 'free' is not adjusted down after each one is added.)
            #   Maybe use this? https://github.com/webtorrent/torrent-discovery
            if (free < target_free):
                if (verbose): print(f"not enough free space for {f}")
                continue

        if (data is None):
            continue

        if (verbose): print(f"adding {f}")
        if (dryrun is False):
            add_torrent = client.add_torrent(data)
            if (verbose): print(f"{add_torrent}")
            if (re.search("Torrent added!", add_torrent)):
                if (verbose): print(f"deleting {f}")
                os.remove(directory + '/' + f)

def cleanup(verbose = False, yes = False, dryrun = False):
    client_config = client.get_config()
    download_dir = client_config['download_location']
    total, used, free = shutil.disk_usage('/')
    target_free = total * .05
    if (verbose): print(f"free space:{minorimpact.disksize(free, units='b')}/{minorimpact.disksize(target_free, units='b')}")

    # Figure out how much space we *actually* need to free up based on what's waiting in the download queue.
    for f in os.listdir(download_dir):
        data = None
        if (re.search('.torrent$', f)):
            t = Torrent.from_file(download_dir + '/' + f)
            if (verbose): print(f"need additional space for {t}:{minorimpact.disksize(t.total_size, units='b')}")
            target_free = target_free + t.total_size

    #delete_torrents('notracker', description = "torrents with no tracker", verbose = verbose)
    #delete_torrents('public_ratio', description = "public torrents that have exceeded the minimum ratio", verbose = verbose)
    #delete_torrents('public_seedtime', sort='seedtime', description = "public torrents that have served their time", target = target_free, verbose = verbose)
    #delete_torrents('private_low_ratio', sort = 'size', description = "private torrents that have served their time but have a low ratio", target = target_free, verbose = verbose)
    #delete_torrents('seedtime', sort='seedtime', description = "all torrents that have served their time", target = target_free, verbose = verbose)
    #delete_torrents('ratio', sort='seedtime', description = "all torrents that have served their ratio", target = target_free, verbose = verbose)
    #delete_torrents('public', sort='size', description = "public torrents that have completed", target = target_free, verbose = verbose)
    #delete_torrents('ratio1', sort='size', description = "all torrents with a ratio > 1", target = target_free, verbose = verbose)

    for criteria in [{ 'type':'notracker', 'description':"torrents with no tracker" },
                     { 'type':'public_ratio', 'description':"public torrents that have exceeded the minimum ratio" },
                     { 'type':'public_seedtime', 'description':"public torrents that have served their time", 'target':target_free, 'sort':'seedtime' },
                     { 'type':'public', 'description':"public torrents that have completed", 'target':target_free, 'sort':'size' },
                     { 'type':'private_low_ratio', 'description':"private torrents that have served their time but have a low ratio", 'target':target_free, 'sort':'size' },
                     { 'type':'seedtime', 'description':"all torrents that have served their time", 'target':target_free, 'sort':'seedtime' },
                     { 'type':'ratio', 'description':"all torrents that have served their ratio", 'target':target_free, 'sort':'size' },
                     { 'type':'ratio1', 'description':"all torrents with a ratio > 1", 'target':target_free, 'sort':'size' }]:
        target = criteria['target'] if 'target' in criteria else 0
        if (target > 0):
            total, used, free = shutil.disk_usage('/')
            if (free > target):
                return

        description = criteria['description'] if 'description' in criteria else None
        if (verbose and description is not None): print(f"checking for {description}")
        delete = filter_torrents(criteria)
        for f in delete:
            if (verbose): print(f"deleting {f}")
            info = client.get_info(f)
            if (verbose): print(f"  ratio:{info[f]['ratio']:.1f} seedtime:{info[f]['seedtime']/(3600*24):.1f} state:{info[f]['state']} size:{minorimpact.disksize(info[f]['size'])}")
            if (verbose): print(f"  Tracker: {info[f]['tracker']}/{info[f]['trackerstatus']}")
            if (verbose): print(f"  file:{info[f]['data_file']}")
            c = 'y' if (yes) else minorimpact.getChar(default='y', end='\n', prompt=f"delete {f}? (Y/n) ", echo=True).lower()
            if (c == 'y'):
                if (dryrun is False):
                    del_torrent = client.delete_torrent(f, remove_data=True)
                    time.sleep(1)
                    if (verbose): print(del_torrent)
                    if (target > 0):
                        total, used, free = shutil.disk_usage('/')
                        if (free > target):
                            return

def filter_torrents(criteria):
    client_config = client.get_config()
    download_location = client_config['download_location']
    if client_config['move_completed']:
        download_location = client_config['move_completed_path']

    cleanup_ratio = eval(config['cleanup']['ratio'])
    cleanup_seedtime = eval(config['cleanup']['seedtime'])

    type = criteria['type']
    sort = criteria['sort'] if 'sort' in criteria else 'name'
    delete = []
    info = client.get_info()
    for f in sorted(info.keys(), key=lambda x: info[x][sort], reverse=True):
        if config['cleanup']['wait_for_file_move'] and info[f]['data_file'] is not None and re.match(download_location, info[f]['data_file']):
            #print(f"{f} has not been moved, skipping")
            continue
        if (info[f]['state'] == 'Downloading' or info[f]['state'] == 'Checking'):
            #print(f"{f} is '{info[f]['state']}', skipping")
            continue

        tracker = info[f]['tracker']
        ratio = info[f]['ratio']
        seedtime = info[f]['seedtime']
        if type == 'notracker':
            trackerstatus = info[f]['trackerstatus']
            if tracker is None or trackerstatus == "Error: unregistered torrent":
                delete.append(f)
        elif type == 'private_low_ratio':
            if tracker not in cleanup_seedtime: continue
            test_seedtime = cleanup_seedtime[tracker]
            if (seedtime > (test_seedtime * 60 * 60 * 24) and ratio < float(config['cleanup']['min_keep_ratio'])):
                delete.append(f)
        elif type == 'public':
            if tracker in cleanup_ratio or tracker in cleanup_seedtime: continue
            delete.append(f)
        elif type == 'public_ratio':
            #print(info[f])
            #print(cleanup_ratio)
            if tracker in cleanup_ratio: continue
            test_ratio = cleanup_ratio['default'] if ('default' in cleanup_ratio) else 1.0
            if (ratio >= test_ratio):
                delete.append(f)
        elif type == 'public_seedtime':
            if tracker in cleanup_seedtime: continue
            test_seedtime = cleanup_seedtime['default'] if ('default' in cleanup_seedtime) else 1
            if (seedtime > (test_seedtime * 60 * 60 * 24)):
                delete.append(f)
        elif type == 'ratio':
            test_ratio = cleanup_ratio['default'] if ('default' in cleanup_ratio) else 1.0
            if (tracker in cleanup_ratio): test_ratio = cleanup_ratio[tracker]
            if (ratio >= test_ratio):
                delete.append(f)
        elif type == "ratio1":
            test_ratio = 1
            if (ratio >= test_ratio):
                delete.append(f)
        elif type == "seedtime":
            test_seedtime = cleanup_seedtime['default'] if ('default' in cleanup_seedtime) else 1
            if (tracker in cleanup_seedtime): test_seedtime = cleanup_seedtime[tracker]
            if (seedtime > (test_seedtime * 60 * 60 * 24)):
                delete.append(f)
    return delete

def media_files(dirname, video_formats = ['mp4', 'mkv'], count = 0):
    video_regex = '|'.join(video_formats)
    for f in os.listdir(dirname):
        if (os.path.isdir(dirname + '/' + f)):
            count = media_files(dirname + '/' + f, count=count)
            continue
        elif (re.search('\.(' + video_regex + '|rar)$', f)):
            count = count + 1
    return count

def meta_info(parsed, fields, delim='.'):
    meta_info = ''
    for field in fields:
        if (field in parsed and len(parsed[field]) > 0): meta_info = meta_info + parsed[field] + delim
    meta_info = re.sub(f'{delim}$', '', meta_info)
    return meta_info

def move_download(name, target, verbose = False, dryrun = False):
    if (verbose): print(f"moving {name} to {target}")
    if (dryrun is False):
        try:
            client.move_torrent(name, target)
        except Exception as e:
            print(f"ERROR: {e}")
    return

def move_media(verbose = False, dryrun = False, debug = False, yes = False):
    download_dir = config['default']['download_dir']
    files = {}
    churn = 1
    while churn:
        churn = 0
        for f in os.listdir(download_dir):
            if (re.match('\.', f)): continue
            size = minorimpact.dirsize(download_dir + '/' + f)
            mtime = os.path.getmtime(download_dir + '/' + f)
            if (f in files):
                if (size == files[f]['size'] and files[f]['mtime'] == mtime):
                    if (files[f]['state'] != 'done'):
                        process_media_dir(download_dir + '/' + f, verbose = verbose, dryrun = dryrun, debug = debug, yes = yes)
                        files[f]['state'] = 'done'
                else:
                    churn = churn + 1
                    files[f]['size'] = size
                    files[f]['mtime'] = mtime
            else:
                churn = churn + 1
                files[f] = {'size':size, 'mtime':mtime, 'title':None, 'type':None, 'parsed':None, 'state':'new'}

        delete = [key for key in files if files[key]['state'] == 'done']
        for f in delete:
            del files[f]
        if (churn > 10):
            return
        time.sleep(1)
    return

def process_media_dir(filename, verbose = False, dryrun = False, debug = False, yes = False):
    media_dirs = eval(config['default']['media_dirs'])
    search_history = {}
    video_formats = ['mp4', 'mkv', 'avi', 'mpg', 'mpeg', 'm4v']
    video_regex = '|'.join(video_formats)

    if (os.path.isdir(filename)):
        for f in os.listdir(filename):
            if (re.match('\.', f) or re.match('Sample', f)): continue
            if (re.search('\.(' + video_regex + '|rar)$', f)):
                process_media_dir(filename + '/' + f, verbose = verbose, dryrun = dryrun, debug = debug, yes = yes)
        return

    if (verbose): print(f"processing {filename}")
    data = {}
    basename = os.path.basename(filename)
    dirname = os.path.dirname(filename)
    basename, extension = os.path.splitext(basename)
    extension = re.sub("^\.", "", extension)
    if extension == "rar":
        with rarfile.RarFile(filename) as rf:
            namelist = rf.namelist()
            new_file = namelist[0]
            if (re.search("\.(" + video_regex + ")$", new_file) and len(namelist) == 1):
                if (verbose):print(f"extracting {basename}.{extension}")
                if (dryrun is False):
                    try:
                        rf.extractall(path=dirname)
                    except Exception as e:
                        print(f"failed to extract {basename}.{extension}\n{e}")
                        uravo.alert(AlertGroup="move_media", AlertKey=f"{filename}", Severity=3, Summary=f"failed to extract {basename}.{extension}")
                        return
                    shutil.move(filename, filename + ".done")
                    process_download(dirname + "/" + new_file)
            else:
                print(f"{basename}.{extension} is weird")
                uravo.alert(AlertGroup="move_media", AlertKey=f"{filename}", Severity=3, Summary=f"{basename}.{extension} is weird")
        return

    if (extension not in video_formats): return
    parsed = PTN.parse(basename + "." + extension)
    if ("codec" in parsed and parsed['codec'] == "H.265"): parsed['codec'] = "HEVC.x265"
    if ("codec" in parsed and parsed['codec'] == "H.264"): parsed['codec'] = "x264"

    if (debug): print(f"{basename}:{parsed}")
    # TODO: Dedup all this code to find a name in the tv and movie sections.
    parsed_title = f"{parsed['title']} ({parsed['year']})" if "year" in parsed else parsed["title"]

    if ("season" in parsed):
        tv_dir = None
        title = None
        for media_dir in media_dirs:
            if (os.path.exists(media_dir + '/' + config['default']['tv_dir'] + '/' + parsed_title)):
                tv_dir = media_dir + '/' + config['default']['tv_dir'] + '/' + parsed_title
                title = parsed_title
                break
            else:
                titles = db.search_title(parsed_title)
                min_lev = 75
                for t in titles:
                    lev = fuzz.ratio(t,parsed_title)
                    if (lev >= min_lev):
                        if (debug): print(f"{t} (match:{lev})")
                        if (os.path.exists(media_dir + '/' + config['default']['tv_dir'] + '/' + t)):
                            if (debug): print(f"found {media_dir}/{config['default']['tv_dir']}/{t}")
                            tv_dir = media_dir + '/' + config['default']['tv_dir'] + '/' + t
                            title = t

        if (title is None):
            title = db.get_title(parsed_title, year=True, headless=yes)
            if (title is not None):
                for media_dir in media_dirs:
                    if (os.path.exists(media_dir + '/' + config['default']['tv_dir'] + '/' + title)):
                        tv_dir = media_dir + '/' + config['default']['tv_dir'] + '/' + title

        if (tv_dir is None and title is None):
            print(f"Can't find a valid directory for {filename}")
            uravo.alert(AlertGroup='move_media', AlertKey=filename, Severity=3, Summary=f"Can't find a valid directory for {filename}")
            return

        if (tv_dir is None and title is not None):
            # TODO: Make the user choose which volume
            # TODO: Confirm with the user before creating this directory
            tv_dir = media_dirs[0] + '/' + config['default']['tv_dir'] + '/' + title

        new_basename = basename
        transformation = transform(title, parsed['season'], parsed['episode'])
        if (transformation is not None):
                season = transformation['season']
                episode = transformation['episode']
                if (int(episode) < 10): episode = '0' + str(int(episode))
                new_basename = f"{title}.S{season}E{episode}"
                meta = meta_info(parsed, ['quality','resolution', 'codec', 'encoder'])
                if (len(meta) > 0):
                    new_basename = new_basename + '.' + meta
                if (debug): print(f"{new_basename}")

        if (os.path.exists(tv_dir + "/" + new_basename + "." + extension) and yes):
            uravo.alert(AlertGroup="move_media_overwrite", AlertKey=filename, Severity=3, Summary=f"{tv_dir}/{new_basename}.{extension} already exists.")
            if (verbose): print(f"{tv_dir}/{new_basename}.{extension} already exists.")
            return

        uravo.alert(AlertGroup="move_media_overwrite", AlertKey=filename, Severity=0, Summary=f"{tv_dir}/{new_basename}.{extension} doesn't exist.")
        # Get user confimation before we move/delete anything.
        c = 'y' if (yes) else minorimpact.getChar(default='y', end='\n', prompt=f"move {basename}.{extension} to {tv_dir}/{new_basename}.{extension}? (Y/n) ", echo=True).lower()
        if (c == 'y'):
            if (verbose): print(f"moving {basename}.{extension} to {tv_dir}/{new_basename}.{extension}")
            if (dryrun is False):
                if (os.path.exists(tv_dir) is False):
                    if (verbose): print(f"creating {tv_dir}")
                    os.mkdir(tv_dir)
            if (os.path.exists(tv_dir + '/' + new_basename + '.' + extension)):
                c = minorimpact.getChar(default='n', end='\n', prompt=f"overwrite {tv_dir}/{new_basename}.{extension}? (y/N) ", echo=True).lower()
                if (c == 'n'):
                    return

            if (dryrun is False):
                shutil.move(filename, tv_dir + '/' + new_basename + '.' + extension)
                uravo.alert(AlertGroup='move_media', AlertKey=filename, Severity=0, Summary=f"moved {basename}.{extension} to {tv_dir}")
            if (os.path.exists(dirname + '/' + basename + '.srt')):
                if (verbose): print(f"moving {basename}.srt to {tv_dir}/{new_basename}.en.srt")
                if (dryrun is False):
                    shutil.move(dirname + '/' + basename + '.srt', tv_dir + '/' + new_basename + '.en.srt')

            if (dirname != config['default']['download_dir'] and media_files(dirname, video_formats = video_formats) == 0):
                c = 'y' if (yes) else minorimpact.getChar(default='y', end='\n', prompt=f"delete {dirname}? (Y/n) ", echo=True).lower()
                if (c == 'y'):
                    if (verbose): print(f"deleting {dirname}")
                    if (dryrun == False): shutil.rmtree(dirname)
    else:
        # TODO: This code is almost identical to the code in the tv section, I think a lot of it can be moved into a function.
        title = None
        movie_dir = None
        for media_dir in media_dirs:
            if (os.path.exists(media_dir + '/' + config['default']['movie_dir'] + '/' + parsed_title)):
                movie_dir = media_dir + '/' + config['default']['movie_dir'] + '/' + parsed_title
                title = parsed_title

        if (title is None):
            title = db.get_title(parsed_title, year=True, headless=yes)
            if (debug):print(f"got {title} from {parsed_title}")
            if (title is not None):
                for media_dir in media_dirs:
                    if (os.path.exists(media_dir + '/' + config['default']['movie_dir'] + '/' + title)):
                        movie_dir = media_dir + '/' + config['default']['movie_dir'] + '/' + title

        if (title is None):
            uravo.alert(AlertGroup='move_media', AlertKey=filename, Severity=3, Summary=f"Can't find a title for {filename}")
            return

        if (movie_dir is None):
            # TODO: make the user choose which volume to store the movie in, if there are
            #   multiple.
            movie_dir = media_dirs[0] + '/' + config['default']['movie_dir'] + '/' + title

        new_basename = title
        meta = meta_info(parsed, ['resolution'])
        if (len(meta) > 0):
            new_basename = new_basename + ' - ' + meta

        if (os.path.exists(movie_dir + '/' + new_basename + '.' + extension) and yes):
            uravo.alert(AlertGroup='move_media_overwrite', AlertKey=filename, Severity=3, Summary=f"{movie_dir}/{new_basename}.{extension} already exists.")
            if (verbose): print(f"{movie_dir}/{new_basename}.{extension} already exists.");
            return
        uravo.alert(AlertGroup='move_media_overwrite', AlertKey=filename, Severity=0, Summary=f"{movie_dir}/{new_basename}.{extension} doesn't exist.")

        # Move and delete the file.
        c = 'y' if (yes) else minorimpact.getChar(default='y', end='\n', prompt=f"move {basename}.{extension} to {movie_dir}/{new_basename}.{extension}? (Y/n) ", echo=True).lower()
        if (c == 'y'):
            if (dryrun is False and os.path.exists(movie_dir) is False):
                if (verbose): print(f"making {movie_dir}")
                os.mkdir(movie_dir)
            if (os.path.exists(movie_dir + '/' + new_basename + '.' + extension)):
                c = minorimpact.getChar(default='n', end='\n', prompt=f"overwrite {movie_dir}/{new_basename}.{extension}? (y/N) ", echo=True).lower()
                if (c == 'n'):
                    return
            if (verbose): print(f"moving {basename}.{extension} to {new_basename}.{extension}")
            if (dryrun == False):
                    shutil.move(filename, movie_dir + '/' + new_basename + '.' + extension)
                    uravo.alert(AlertGroup='move_media', AlertKey=filename, Severity=0, Summary=f"moved {basename}.{extension} to {movie_dir}/{new_basename}.{extension}")
            if (os.path.exists(dirname + '/' + basename + '.srt')):
                if (verbose): print(f"moving {basename}.srt to {movie_dir}/{new_basename}.en.srt")
                if (dryrun is False): shutil.move(dirname + '/' + basename + '.srt', movie_dir + '/' + new_basename + '.en.srt')

            if (dirname != config['default']['download_dir'] and media_files(dirname, video_formats = video_formats) == 0):
                c = 'y' if (yes) else minorimpact.getChar(default='y', end='\n', prompt=f"delete {dirname}? (Y/n) ", echo=True).lower()
                if (c == 'y'):
                    if (verbose): print(f"deleting {dirname}")
                    if (dryrun == False): shutil.rmtree(dirname)
    return

def rss(args = minorimpact.default_arg_flags):
    if (args.debug): print(f"delugeonal.rss()")
    site.rss(args)

def transform(title, season, episode):
    transforms = eval(config['default']['transforms'])
    
    if title in transforms:
        for transform in transforms[title]:
            criteria = None
            action = None
            match = re.search("^([a-z]+)([=<>]+)([0-9]+)$", transform['criteria'])
            if (match):
                criteria = {"field":match.group(1), "cmp":match.group(2), "value":match.group(3)}
                #if (debug): print(f"criteria:{criteria}")
            match = re.search("^([a-z]+)([+-])([0-9]+)$", transform['action'])
            if (match):
                action = {"field":match.group(1), "action":match.group(2), "value":match.group(3)}
                #if (debug): print(f"action:{action}")

            if (criteria and action):
                transformation = {'season': season, 'episode':episode}
                if (eval(f"{criteria['field']}{criteria['cmp']}{criteria['value']}", {}, transformation)):
                    s = f"{action['field']} = {action['field']} {action['action']} {action['value']}"
                    exec(s, {}, transformation)

                return transformation

    return None

