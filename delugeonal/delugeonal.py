import argparse
import atexit
from datetime import datetime, timedelta
import delugeonal.mediaserver
from dumper import dump
from fuzzywuzzy import fuzz
import importlib
import minorimpact
import minorimpact.config
from operator import itemgetter
import os
import os.path
import pickle
import PTN
import re
import requests
import shutil
import sys
import time
from uravo import uravo
import bencode

cache = {}
client = None
config = {}
mediadbs = []
mserver = None
mediasites = []

def main():
    setup()
    #print("cache_file:" + cache_file)

    parser = argparse.ArgumentParser(description="delugeonal")
    parser.add_argument('-f', '--force', help = "bypass built-in delays", action='store_true')
    parser.add_argument('-v', '--verbose', help = "extra loud output", action='store_true')
    parser.add_argument('-y', '--yes', help = "Always say yes.", action='store_true')
    parser.add_argument('-d', '--dryrun', help = "Don't actually make any changes", action='store_true')
    parser.add_argument('--debug', help = "extra extra loud output", action='store_true')
    parser.add_argument('--add', metavar = 'DIR',  help = "Scan DIR for torrent files, and add them to the client.", nargs=1)
    parser.add_argument('--cleanup', help = "Remove completed torrents from the client.", action = 'store_true')
    parser.add_argument('--clear_cache', help = "Empty the delugeonal cache.", action = 'store_true')
    parser.add_argument('--codec', metavar = 'CODEC',  help = "Search for torrents encoded with CODEC", nargs=1)
    parser.add_argument('--dump_cache', help = "Dump the delugeonal cache to stdout.", action = 'store_true')
    parser.add_argument('--fill', metavar = 'SHOW', help = "search media sites for missing episodes of SHOW", nargs=1)
    parser.add_argument('--move_download', metavar = ('NAME', 'TARGET_DIR'), help = "Move newly downloaded torrent NAME to TARGET_DIR", nargs=2)
    parser.add_argument('--move_media', metavar = 'DIR', help = "Move media files from the download directory (or DIR, if specified) to the appropriate media folders", nargs='?', const=config['default']['download_dir'] )
    parser.add_argument('--rss', help = "Check media site rss feeds for new downloads.", action = 'store_true')
    parser.add_argument('--search', metavar = 'SEARCH',  help = "Search media sites for SEARCH.", nargs=1)
    parser.add_argument('--torrents', help = "List active torrents.", action = 'store_true')
    parser.add_argument('--resolution', metavar = 'RES',  help = "Search for torrents with a resolution of RES", nargs=1)
    args = parser.parse_args()
    if (args.dryrun): args.verbose = True
    if (args.add is not None and len(args.add) == 1):
        add(args.add[0], args = args)
    if (args.cleanup):
        cleanup(args = args, torrent_dir = config['default']['torrent_dir'])
    if (args.clear_cache):
        clear_cache(args = args)
    if (args.dump_cache):
        dump_cache(args = args)
    if (args.fill is not None and len(args.fill) == 1):
        fill(args.fill[0], args = args)
    if (args.move_download is not None and len(args.move_download) == 2):
        move_download(args.move_download[0], args.move_download[1], args = args)
    if (args.move_media is not None):
        move_media(args = args)
    if (args.rss):
        rss(args = args)
    if (args.search is not None and len(args.search) == 1):
        search(args.search[0], args = args)
    if (args.torrents is not None and args.torrents is True):
        torrents(args = args)

def add(directory, args = minorimpact.default_arg_flags):
    if (os.path.exists(directory) is False):
        sys.exit("'{}' doesn't exist".format(directory))
    if (args.dryrun): verbose = True

    free_percent = 5
    if ('cleanup' in config and 'free_percent' in config['cleanup']):
        free_percent = int(config['cleanup']['free_percent'])
    total, used, free = shutil.disk_usage('/')
    target_free = total * (free_percent/100)

    for f in os.listdir(directory):
        data = None
        if (re.search('.torrent$', f)):
            total_size = torrent_size(directory + '/' + f)
            if (args.verbose): print("{}\nsize:{}".format(f, minorimpact.disksize(total_size, units='b')))
            if (free - total_size < target_free):
                if (args.verbose): print("not enough free space for {}".format(f))
                continue
            free = free - total_size
            data = directory + '/' + f
        elif (re.search('.magnet$', f)):
            m = open(directory + '/' + f, 'r')
            data = m.read()
            # TODO: Try to find the actual size of the magent download, rather than just rejecting them
            #   if the remaining disk space is lower than a certain percentage.  (Especially because it will
            #   essentially add all magnets, since 'free' is not adjusted down after each one is added.)
            #   Maybe use this? https://github.com/webtorrent/torrent-discovery
            if (free < target_free):
                if (args.verbose): print("not enough free space for {}".format(f))
                continue

        if (data is None):
            continue

        if (args.verbose): print("adding {}".format(f))
        if (args.dryrun is False):
            add_torrent = client.add_torrent(data)
            if (args.verbose): print(add_torrent)
            if (re.search('responded: "success"', add_torrent)):
                if (args.verbose): print("deleting {}".format(f))
                os.remove(directory + '/' + f)

def cleanup(args = minorimpact.default_arg_flags, torrent_dir = None):
    if ('cleanup' not in config):
        return

    client_config = client.get_config()

    free_percent = 5
    if ('free_percent' in config['cleanup']):
        free_percent = int(config['cleanup']['free_percent'])
    total, used, free = shutil.disk_usage('/')
    target_free = total * (free_percent/100)

    if (args.force is True):
        target_free = total
    if (args.verbose): print("free space:{}/{}".format(minorimpact.disksize(free, units='b'),minorimpact.disksize(target_free, units='b')))

    # Figure out how much space we *actually* need to free up based on what's waiting in the download queue.
    if (torrent_dir is not None):
        for f in os.listdir(torrent_dir):
            data = None
            if (re.search('.torrent$', f)):
                total_size = torrent_size(torrent_dir + '/' + f)
                if (args.verbose): print("need additional space for {}:{}".format(f, minorimpact.disksize(total_size, units='b')))
                target_free = target_free + total_size

    #delete_torrents('notracker', description = "torrents with no tracker", verbose = verbose)
    #delete_torrents('public_ratio', description = "public torrents that have exceeded the minimum ratio", verbose = verbose)
    #delete_torrents('public_seedtime', sort='seedtime', description = "public torrents that have served their time", target = target_free, verbose = verbose)
    #delete_torrents('private_low_ratio', sort = 'size', description = "private torrents that have served their time but have a low ratio", target = target_free, verbose = verbose)
    #delete_torrents('seedtime', sort='seedtime', description = "all torrents that have served their time", target = target_free, verbose = verbose)
    #delete_torrents('ratio', sort='seedtime', description = "all torrents that have served their ratio", target = target_free, verbose = verbose)
    #delete_torrents('public', sort='size', description = "public torrents that have completed", target = target_free, verbose = verbose)
    #delete_torrents('ratio1', sort='size', description = "all torrents with a ratio > 1", target = target_free, verbose = verbose)

    for criteria in [{ 'type':'notracker', 'description':"torrents with no tracker" },
                     { 'type':'done', 'description':"torrents marked 'done' by the client" },
                     { 'type':'public_ratio', 'description':"public torrents that have exceeded the minimum ratio" },
                     { 'type':'max_ratio', 'description':"any torrent that's exceeded the maximum ratio" },
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
        if (args.verbose and description is not None): print("checking for {}".format(description))
        delete = filter_torrents(criteria, args)
        for f in delete:
            ignore = []
            if ('ignore' in config['cleanup']):
                ignore = eval(config['cleanup']['ignore'])
            imatch = False
            for i in ignore:
                m = re.search(i, f)
                if (m is not None):
                    imatch = True
                    break
            if (imatch is True):
                continue
            if (args.verbose): print("{}".format(f))
            info = client.get_info(f)
            if (args.verbose): print("  ratio:{:.1f} seedtime:{:.1f} state:{} size:{}".format(info[f]['ratio'], info[f]['seedtime']/(3600*24), info[f]['state'], minorimpact.disksize(info[f]['size'])))
            if (args.verbose): print("  Tracker: {}/{}".format(info[f]['tracker'], info[f]['trackerstatus']))
            if (args.verbose): print("  file:{}".format(info[f]['data_file']))
            c = 'y' if (args.yes) else minorimpact.getChar(default='y', end='\n', prompt="delete {}? (Y/n) ".format(f), echo=True).lower()
            if (c == 'q'):
                sys.exit()
            elif (c == 'y'):
                if (args.verbose): print("deleting {}".format(f))
                if (args.dryrun is False):
                    del_torrent = client.delete_torrent(f, remove_data=True)
                    time.sleep(1)
                    if (args.verbose): print(del_torrent)
                    if (target > 0):
                        total, used, free = shutil.disk_usage('/')
                        if (free > target):
                            return

def clear_cache(args = minorimpact.default_arg_flags):
    """Remove all the values from the local persistent storage."""
    if (args.verbose): print("clearing cache")
    keys = list(cache.keys())
    [cache.pop(key) for key in keys]
    if (args.verbose): print(" ... DONE")

def download(downloads, args = minorimpact.default_arg_flags):
    """Download torrent files.

    Parameters
    ----------
    list
       dict
            name : str
                Name of the torrent file.
            url : str
                Download url.
            date : datetime
                torrent file date. Optional.
    """
    if (downloads is None):
        raise Exception("downloads is not defined")

    download_log = []
    download_count = 0
    for d in downloads:
        name = d['name']
        url = d['url']
        date = d['date'] if ('date' in d) else None
        #print(name + " (" + url + "):" + str(date))

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

        codec =  config['default']['codec']
        resolution =  config['default']['resolution']
        if ('download_overrides' in config['default']):
            overrides = eval(config['default']['download_overrides'])
            for regex in overrides.keys():
                if (re.search(regex, item_title)):
                    codec = overrides[regex]['codec']
                    resolution = overrides[regex]['resolution']
                    break

        # Command line settings trump everything else
        if hasattr(args, 'codec') and args.codec is not None: codec = args.codec[0] 
        if hasattr(args, 'resolution') and args.resolution is not None: resolution = args.resolution[0] 

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
        transformation = transform(title, item['season'], item['episode'])
        if (transformation is not None):
            if (args.verbose): print(" ... applying transformation: '{}'=>'{}', season {}=>{}, episode {}=>{}".format(title, transformation['title'], item['season'], transformation['season'], item['episode'], transformation['episode']))
            title = transformation['title']
            item['season'] = transformation['season']
            item['episode'] = transformation['episode']

        if (mserver is not None):
            exists = False
            try:
                exists = mserver.exists(title, item['season'], item['episode'], resolution = item['resolution'], args = args)
                uravo.event({'AlertGroup':'server_title', 'AlertKey':title, 'Severity':'green', 'Summary':"Got {} title for '{}'".format(mserver.name, title)})
            except delugeonal.mediaserver.TitleNotFoundException as e:
                if (args.verbose): print(" ... FAILED: can't get {} title for '{}'".format(mserver.name, title))
                # Make an exception and allow the download of a show that's not in the media server *if* it's the first episode
                #   of a season.
                if (item['episode'] != 1):
                    uravo.event({'AlertGroup':'server_title', 'AlertKey':title, 'Severity':'yellow', 'Summary':repr(e)})
                    continue
            except Exception as e:
                if (args.verbose): print(" ... FAILED: {}".format(repr(e)))
                uravo.event({'AlertGroup':'server_title', 'AlertKey':title, 'Severity':'yellow', 'Summary':repr(e)})
                continue

            if (exists):
                if (args.verbose): print(" ... {} S{}E{} already in {}".format(title, item['season'], item['episode'], mserver.name))
                continue

        episode_key = "{}|S{}E{}".format(title, item['season'], item['episode'])
        if (episode_key in download_log):
            # Yes, download_log *is* redundant (and a shitty hack), but in the case of --dryrun I don't want to add the download to the permanent cache, 
            # but I *also* don't want to ask the user to download multiple copies of the same torrent.
            continue
        if ('downloads' not in cache): cache['downloads'] = {}
        if (episode_key not in cache['downloads']):
            cache['downloads'][episode_key] = { 'item':item }
        elif (args.force is False and 'date' in cache['downloads'][episode_key] and cache['downloads'][episode_key]['date'] > datetime.now() - timedelta(hours=1)):
            if (args.verbose): print(" ... already downloaded within the last hour")
            continue

        link_url = item['url']
        if args.debug: print("link_url:{}".format(link_url))
        if (os.path.exists(config['default']['download_dir']) is False):
            raise Exception(config['default']['download_dir'] + " does not exist.")
        torrent_filename = re.sub(" ", ".", item['name']) + ".torrent"
        c = 'y' if (args.yes) else minorimpact.getChar(default='y', end='\n', prompt="Download {} to {}? (Y/n) ".format(torrent_filename, config['default']['download_dir']), echo=True).lower()
        if (c == 'y'):
            if args.verbose: print(" ... downloading {} to {}".format(torrent_filename, config['default']['download_dir']))
            if (args.dryrun is False):
                r = requests.get(link_url, stream=True)
                with open(config['default']['download_dir'] + '/' + torrent_filename, 'wb') as f:
                   for chunk in r.iter_content(chunk_size=128):
                      f.write(chunk)
                cache['downloads'][episode_key]['date'] = datetime.now()
            download_log.append(episode_key)
            download_count += 1
    return download_count

def dump_cache(args = minorimpact.default_arg_flags):
    dump(cache)

def fill(search_string, args = minorimpact.default_arg_flags):
    """Find all missing episodes for `search_string`.

    Parameters
    ----------
    str
        The name of the show for which to find missing episodes.
    """
    if (args.debug): print("delugeonal.fill()")
    show = mserver.show_name(search_string)
    if (show is None):
        raise Exception ("Can't get show for '{}'".format(search_string))

    if (args.debug): print("'{}' => '{}'".format(search_string, show))
    episodes = mserver.episodes(show)
    total_episodes = None
    mediadb = None
    for db in mediadbs:
        if (db.istype('tv')):
            total_episodes = db.total_episodes(show)
            mediadb = db
            break

    if (mediadb is None or total_episodes is None):
        raise Exception("Can't get season/episode count")

    missing = []
    last_season = 0
    last_episode = 0
    # Sort all of the episodes by episode, then by 
    #for episode in sorted(sorted(episodes, key=lambda x: x['episode']), key=lambda x: x['season']):
    for episode in sorted(episodes, key=itemgetter('season', 'episode')):
        # These are specials, I have no personal interest in collecting all of these -- though it might be
        #   a nice option in the future.
        if (episode['season'] == 0): continue

        # Seasons change
        if (episode['season'] == last_season + 1):
            # We've gone from one season to the next.
            if (last_season > 0 and last_episode < total_episodes[last_season]):
                while (last_episode < total_episodes[last_season]):
                    last_episode += 1
                    missing.append({'season':last_season, 'episode':last_episode})
            last_episode = 0
        elif (episode['season'] > last_season + 1):
            # We've apparently skipped an entire season
            while (episode['season'] > last_season+1):
                last_season += 1
                for i in range(1, total_episodes[last_season] + 1):
                    missing.append({'season':last_season, 'episode':i})

        # Having an episode
        if (episode['episode'] > last_episode+1):
            while (episode['episode'] > last_episode+1):
                last_episode += 1
                missing.append({'season':episode['season'], 'episode':last_episode})
        last_episode = episode['episode']
        last_season = episode['season']

    # Last call
    if (last_season < len(total_episodes) or (last_season == len(total_episodes) and last_episode < total_episodes[last_season])):
        # There are seasons and/or episodes beyond what we've got
        while (last_season <= len(total_episodes)):
            while(last_episode < total_episodes[last_season]):
                last_episode += 1
                missing.append({'season':last_season, 'episode':last_episode})
            last_episode = 0
            last_season += 1

    if (len(missing) == 0):
        print("No missing episodes found for {}".format(show))
        return

    print("Found {} missing episode(s) for {}".format(len(missing), show))
    for m in missing:
        season = str(m['season'])
        episode = str(m['episode'])
        season = '0' + season if int(season) < 10 else season
        episode = '0' + episode if int(episode) < 10 else episode

        search_string = re.sub(' \(\d\d\d\d\)$', '', show)
        search_string = '{} S{}E{}'.format(search_string, season, episode)
        if (args.verbose): print("searching for '{}'".format(search_string))
        for site in (mediasites):
            results = site.search(search_string, download = False, args = args)
            if (results is not None and len(results) > 0):
                if (download(results, args = args) > 0):
                    break

def filter_torrents(criteria, args = minorimpact.default_arg_flags):
    """Return a list of torrents from the client matching the values in criteria.

    Parameters
    ----------
    criteria : dict
            'type': One of a set of predefined searches
            'description': a human readable summary of what this search does (TODO: Move this into the actual search, since all the other
                info is there aleady.)
            'sort': sort torrents by this field, and process them in reverse order.
            'target': The desired amount of free disk space on the system.  If target is greater than 0, filter torrents will stop analyzing
                once this value is reached.

    Returns
    -------
    list
        A list of torrent titles that fit criteria.
    """
    client_config = client.get_config()
    if 'download_location' in client_config: 
        download_location = client_config['download_location']
    elif 'download-dir' in client_config:
        download_location = client_config['download-dir']

    if 'move_completed' in client_config and client_config['move_completed']:
        download_location = client_config['move_completed_path']
    #elif 'incomplete-dir-enabled' in client_config and client_config['incomplete-dir-enabled'] == 'true':
    #    download_location = client_config['incomplete-dir']

    cleanup_ratio = eval(config['cleanup']['ratio'])
    cleanup_seedtime = eval(config['cleanup']['seedtime'])
    type = criteria['type']
    sort = criteria['sort'] if 'sort' in criteria else 'name'
    delete = []
    info = client.get_info()
    for f in sorted(info.keys(), key=lambda x: info[x][sort], reverse=True):
        if config['cleanup']['wait_for_file_move'] and info[f]['data_file'] is not None and re.match(download_location, info[f]['data_file']):
            continue
        if (info[f]['state'] == 'Downloading' or info[f]['state'] == 'Checking'):
            continue

        tracker = info[f]['tracker']
        ratio = info[f]['ratio']
        seedtime = info[f]['seedtime']

        if type == 'done':
            #if (args.verbose): print("torrents marked 'done' by the client")
            state = info[f]['state'].lower()
            if (state is None or state in ('finished', 'done')):
                delete.append(f)
                continue
        elif type == 'notracker':
            #if (args.verbose): print("checking for torrents with no tracker")
            trackerstatus = info[f]['trackerstatus']
            if tracker is None or trackerstatus == "Error: unregistered torrent" or trackerstatus == 'error':
                delete.append(f)
        elif type == 'max_ratio':
            if ('max_ratio' not in config['cleanup']):
                continue
            max_ratio = config['cleanup']['max_ratio'] 

            if (len(max_ratio) > 0 and re.search('[^0-9\.]', max_ratio) is None and float(max_ratio) > 0 and ratio >= float(max_ratio)):
                delete.append(f)
                continue
        elif type == 'private_low_ratio':
            #if (args.verbose): print("private torrents that have served their time but have a low ratio")
            if tracker not in cleanup_seedtime: continue
            test_seedtime = cleanup_seedtime[tracker]
            test_seedtime = test_seedtime * 60 * 60 * 24
            #print("{}({}):{} {} {}".format(f, tracker, seedtime, ratio, test_seedtime))
            if (seedtime > test_seedtime and ratio < float(config['cleanup']['min_keep_ratio'])):
                delete.append(f)
        elif type == 'public':
            #if (args.verbose): print("public torrents that have completed")
            if tracker in cleanup_ratio or tracker in cleanup_seedtime: continue
            delete.append(f)
        elif type == 'public_ratio':
            #if (args.verbose): print("public torrents that have exceeded the minimum ratio")
            #print(info[f])
            #print(cleanup_ratio)
            if tracker in cleanup_ratio: continue
            test_ratio = cleanup_ratio['default'] if ('default' in cleanup_ratio) else 1.0
            if (ratio >= test_ratio):
                delete.append(f)
        elif type == 'public_seedtime':
            #if (args.verbose): print("public torrents that have served their time")
            if tracker in cleanup_seedtime: continue
            test_seedtime = cleanup_seedtime['default'] if ('default' in cleanup_seedtime) else 1
            test_seedtime = test_seedtime * 60 * 60 * 24
            if (seedtime > test_seedtime):
                delete.append(f)
        elif type == 'ratio':
            #if (args.verbose): print("all torrents that have served their ratio")
            test_ratio = cleanup_ratio['default'] if ('default' in cleanup_ratio) else 1.0
            if (tracker in cleanup_ratio): test_ratio = cleanup_ratio[tracker]
            if (ratio >= test_ratio):
                delete.append(f)
        elif type == "ratio1":
            #if (args.verbose): print("all torrents with a ratio > 1")
            test_ratio = 1
            if (ratio >= test_ratio):
                delete.append(f)
        elif type == "seedtime":
            #if (args.verbose): print("all torrents that have served their time")
            test_seedtime = cleanup_seedtime['default'] if ('default' in cleanup_seedtime) else 1
            if (tracker in cleanup_seedtime): test_seedtime = cleanup_seedtime[tracker]
            test_seedtime = test_seedtime * 60 * 60 * 24
            #print("{}({}):{} {}".format(f, tracker, seedtime, test_seedtime))
            if (seedtime >= test_seedtime):
                delete.append(f)
    return delete


def load_libraries():
    setup()

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
    meta_info = re.sub(delim + '$', '', meta_info)
    return meta_info

def move_download(name, target, args = minorimpact.default_arg_flags):
    if (args.verbose): print("moving {} to {}".format(name, target))
    if (args.dryrun is False):
        try:
            client.move_torrent(name, target)
        except Exception as e:
            print("ERROR: {}".format(e))
    return

def move_media(args = minorimpact.default_arg_flags):
    #download_dir =  config['default']['download_dir']
    download_dir = args.move_media
    files = {}
    churn = 1
    while churn > 0:
        churn = 0
        for f in os.listdir(download_dir):
            if (re.match('\.', f)): continue
            size = minorimpact.dirsize(download_dir + '/' + f)
            mtime = os.path.getmtime(download_dir + '/' + f)
            if (f in files):
                if (size == files[f]['size'] and files[f]['mtime'] == mtime):
                    if (files[f]['state'] != 'done'):
                        process_media_dir(download_dir + '/' + f, args = args)
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
        time.sleep(1)
    return

def process_media_dir(filename, args = minorimpact.default_arg_flags):
    import rarfile

    media_dirs = eval(config['default']['media_dirs'])
    search_history = {}
    video_formats = ['mp4', 'mkv', 'avi', 'mpg', 'mpeg', 'm4v']
    video_regex = '|'.join(video_formats)

    if (os.path.isdir(filename)):
        for f in os.listdir(filename):
            if (re.match('\.', f) or re.match('Sample', f)): continue
            if (re.search('\.(' + video_regex + '|rar)$', f)):
                process_media_dir(filename + '/' + f, args = args)
        return

    if (args.verbose): print("processing {}".format(filename))
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
                if (args.verbose):print("extracting {}.{}".format(basename, extension))
                if (args.dryrun is False):
                    try:
                        rf.extractall(path=dirname)
                    except Exception as e:
                        print("failed to extract {}.{}\n{}".format(basename, extension, e))
                        uravo.alert(AlertGroup="move_media", AlertKey=filename, Severity=3, Summary="failed to extract {}.{}".format(basename, extension))
                        return
                    shutil.move(filename, filename + ".done")
                    process_media_dir(dirname + "/" + new_file, args = args)
            else:
                print("{}.{} is weird".format(basename, extension))
                uravo.alert(AlertGroup="move_media", AlertKey=filename, Severity=3, Summary="{}.{} is weird".format(basename, extension))
        return

    if (extension not in video_formats): return
    parsed = PTN.parse(basename + "." + extension)
    if ('codec' in parsed and parsed['codec'] == 'H.265'): parsed['codec'] = 'HEVC.x265'
    if ('codec' in parsed and parsed['codec'] == 'H.264'): parsed['codec'] = 'x264'
    if ('resolution' not in parsed):  parsed['resolution'] = '480p'

    if (args.debug): print("{}:{}".format(basename, parsed))
    parsed_title = '{} ({})'.format(parsed['title'], parsed['year']) if 'year' in parsed else parsed['title']

    if ('season' in parsed):
        mediadb = None
        title = None
        tv_dir = None

        for media_dir in media_dirs:
            if (os.path.exists(media_dir + '/' + config['default']['tv_dir'] + '/' + parsed_title)):
                tv_dir = media_dir + '/' + config['default']['tv_dir'] + '/' + parsed_title
                title = parsed_title
                break

        # This isn't just a copy of mediadb.get_title() -- I want to scan through the results of a search and see if any of them match the
        #   directories we already have, which might save us from having to ask the user for a match later. 
        if (title is None):
            titles = {}
            for db in mediadbs:
                if (db != mediadb and db.istype('tv')):
                    titles = db.search_title(parsed_title)
                    if (len(titles.keys()) > 0):
                        mediadb = db
                        break

            if (len(titles.keys()) > 0):
                min_lev = 75
                for t in titles:
                    lev = fuzz.ratio(t,parsed_title)
                    if (lev >= min_lev):
                        title = t
                        if (args.debug): print("{} (match:{})".format(t, lev))
                        for media_dir in media_dirs:
                            if (os.path.exists(media_dir + '/' + config['default']['tv_dir'] + '/' + title)):
                                if (args.debug): print("found {}/{}/{}".format(media_dir, config['default']['tv_dir'], title))
                                tv_dir = media_dir + '/' + config['default']['tv_dir'] + '/' + title
                    if (tv_dir is not None): 
                        mediadb.match_log(os.path.basename(filename), parsed_title, titles[t]['title'], titles[t]['year'])
                        break

        # We didn't find a close match in any of the existing directories, so let let mediadb do whatever it needs to do to find
        #   a match.
        if (title is None):
            if mediadb is None:
                raise Exception("Can't find a mediadb object.")
            title = mediadb.get_title(parsed_title, year=True, headless = args.yes)
            if (title is not None):
                for media_dir in media_dirs:
                    if (os.path.exists(media_dir + '/' + config['default']['tv_dir'] + '/' + title)):
                        tv_dir = media_dir + '/' + config['default']['tv_dir'] + '/' + title

        if (tv_dir is None and title is None):
            print("Can't find a valid title for {}".format(filename))
            uravo.alert(AlertGroup='move_media', AlertKey=filename, Severity=3, Summary="Can't find a valid title for {}".format(filename))
            return
        uravo.alert(AlertGroup='move_media', AlertKey=filename, Severity=0, Summary="Found a valid title for {}:{}".format(filename, title))

        if (tv_dir is None and title is not None):
            tv_dir = media_dirs[0] + '/' + config['default']['tv_dir'] + '/' + title

        new_basename = basename
        transformation = transform(title, parsed['season'], parsed['episode'])
        if (transformation is not None):
            season = transformation['season']
            episode = transformation['episode']
            if (int(episode) < 10): episode = '0' + str(int(episode))
            new_basename = "{}.S{}E{}".format(title, season, episode)
            meta = meta_info(parsed, ['quality','resolution', 'codec', 'encoder'])
            if (len(meta) > 0):
                new_basename = new_basename + '.' + meta
            if (args.debug): print(new_basename)

        if (os.path.exists(tv_dir + "/" + new_basename + "." + extension) and args.yes):
            uravo.alert(AlertGroup="move_media_overwrite", AlertKey=filename, Severity=3, Summary="{}/{}.{} already exists.".format(tv_dir, new_basename, extension))
            if (args.verbose): print("{}/{}.{} already exists.".format(tv_dir, new_basename, extension))
            return
        uravo.alert(AlertGroup="move_media_overwrite", AlertKey=filename, Severity=0, Summary="{}/{}.{} doesn't exist.".format(tv_dir, new_basename, extension))

        # Get user confimation before we move/delete anything.
        c = 'y' if (args.yes) else minorimpact.getChar(default='y', end='\n', prompt="move {}.{} to {}/{}.{}? (Y/n) ".format(basename, extension, tv_dir, new_basename, extension), echo=True).lower()
        if (c == 'y'):
            if (args.verbose): print("moving {}.{} to {}/{}.{}".format(basename, extension, tv_dir, new_basename, extension))
            if (args.dryrun is False):
                if (os.path.exists(tv_dir) is False):
                    if (args.verbose): print("creating {}".format(tv_dir))
                    os.mkdir(tv_dir)
            if (os.path.exists(tv_dir + '/' + new_basename + '.' + extension)):
                c = minorimpact.getChar(default='n', end='\n', prompt="overwrite {}/{}.{}? (y/N) ".format(tv_dir, new_basename, extension), echo=True).lower()
                if (c == 'n'):
                    return

            if (args.dryrun is False):
                shutil.move(filename, tv_dir + '/' + new_basename + '.' + extension)
                uravo.alert(AlertGroup='move_media', AlertKey=filename, Severity=0, Summary="moved {}.{} to {}".format(basename, extension, tv_dir))
            if (os.path.exists(dirname + '/' + basename + '.srt')):
                if (args.verbose): print("moving {}.srt to {}/{}.en.srt".format(basename, tv_dir, new_basename))
                if (args.dryrun is False):
                    shutil.move(dirname + '/' + basename + '.srt', tv_dir + '/' + new_basename + '.en.srt')

            if (dirname != config['default']['download_dir'] and media_files(dirname, video_formats = video_formats) == 0):
                c = 'y' if (args.yes) else minorimpact.getChar(default='y', end='\n', prompt="delete {}? (Y/n) ".format(dirname), echo=True).lower()
                if (c == 'y'):
                    if (args.verbose): print("deleting {}".format(dirname))
                    if (args.dryrun == False): shutil.rmtree(dirname)
        elif (c == 'q'):
            sys.exit()
    else:
        title = None
        movie_dir = None
        mediadb = None
        for db in mediadbs:
            if (db.istype('movie')): mediadb = db

        if mediadb is None:
            raise Exception("Can't find a mediadb object.")

        for media_dir in media_dirs:
            if (os.path.exists(media_dir + '/' + config['default']['movie_dir'] + '/' + parsed_title)):
                title = parsed_title
                movie_dir = media_dir + '/' + config['default']['movie_dir'] + '/' + parsed_title
                mediadb.match_log(filename, parsed_title, title, None)

        if (title is None):
            title = mediadb.get_title(parsed_title, year=True, headless = args.yes)
            if (args.debug):print("got {} from {}".format(title, parsed_title))
            if (title is not None):
                for media_dir in media_dirs:
                    if (os.path.exists(media_dir + '/' + config['default']['movie_dir'] + '/' + title)):
                        movie_dir = media_dir + '/' + config['default']['movie_dir'] + '/' + title

        if (title is None):
            uravo.alert(AlertGroup='move_media', AlertKey=filename, Severity='yellow', Summary="Can't find a title for {}".format(filename))
            return
        uravo.alert(AlertGroup='move_media', AlertKey=filename, Severity='green', Summary="Found '{}' for {}".format(title, filename))

        if (movie_dir is None):
            movie_dir = media_dirs[0] + '/' + config['default']['movie_dir'] + '/' + title

        new_basename = title
        meta = meta_info(parsed, ['resolution'])
        if (len(meta) > 0):
            new_basename = new_basename + ' - ' + meta

        if (os.path.exists(movie_dir + '/' + new_basename + '.' + extension) and args.yes):
            uravo.alert(AlertGroup='move_media_overwrite', AlertKey=filename, Severity=3, Summary="{}/{}.{} already exists.".format(movie_dir, new_basename, extension))
            if (args.verbose): print("{}/{}.{} already exists.".format(movie_dir, new_basename, extension));
            return
        uravo.alert(AlertGroup='move_media_overwrite', AlertKey=filename, Severity=0, Summary="{}/{}.{} doesn't exist.".format(movie_dir, new_basename, extension))

        # Move and delete the file.
        c = 'y' if (args.yes) else minorimpact.getChar(default='y', end='\n', prompt="move {}.{} to {}/{}.{}? (Y/n) ".format(basename, extension, movie_dir, new_basename, extension), echo=True).lower()
        if (c == 'y'):
            if (args.dryrun is False and os.path.exists(movie_dir) is False):
                if (args.verbose): print("making {}".format(movie_dir))
                os.mkdir(movie_dir)
            if (os.path.exists(movie_dir + '/' + new_basename + '.' + extension)):
                c = minorimpact.getChar(default='n', end='\n', prompt="overwrite {}/{}.{}? (y/N) ".format(movie_dir, new_basename, extension), echo=True).lower()
                if (c == 'n'):
                    return
            if (args.verbose): print("moving {}.{} to {}.{}".format(basename, extension, new_basename, extension))
            if (args.dryrun == False):
                    shutil.move(filename, movie_dir + '/' + new_basename + '.' + extension)
                    uravo.alert(AlertGroup='move_media', AlertKey=filename, Severity=0, Summary="moved {}.{} to {}/{}.{}".format(basename, extension, movie_dir, new_basename, extension))
            if (os.path.exists(dirname + '/' + basename + '.srt')):
                if (args.verbose): print("moving {}.srt to {}/{}.en.srt".format(basename, movie_dir, new_basename))
                if (args.dryrun is False): shutil.move(dirname + '/' + basename + '.srt', movie_dir + '/' + new_basename + '.en.srt')

            if (dirname != config['default']['download_dir'] and media_files(dirname, video_formats = video_formats) == 0):
                c = 'y' if (args.yes) else minorimpact.getChar(default='y', end='\n', prompt="delete {}? (Y/n) ".format(dirname), echo=True).lower()
                if (c == 'y'):
                    if (args.verbose): print("deleting {}".format(dirname))
                    if (args.dryrun == False): shutil.rmtree(dirname)
    return

def rss(args = minorimpact.default_arg_flags):
    if (args.debug): print("delugeonal.rss()")
    for site in (mediasites):
        try:
            download(site.rss_feed(), args = args)
        except Exception as e:
            print(e)

def search(search_string, args = minorimpact.default_arg_flags):
    if (args.verbose): print("searching for '{}'".format(search_string))
    results = []
    for site in (mediasites):
        site.search(search_string, args = args)

def setup():
    global cache, client, config, mediadbs, mserver, mediasites

    config = minorimpact.config.getConfig(script_name='delugeonal')
    if ('cache_file' in config['default']):
        cache_file = config['default']['cache_file']
        if (os.path.exists(cache_file)):
            with open(cache_file, "rb") as f:
                cache = pickle.load(f)

    mediadblibs = eval(config['default']['mediadblibs']) if 'mediadblibs' in config['default'] and config['default']['mediadblibs'] is not None else None
    if (mediadblibs is not None and len(mediadblibs)>0):
        for mediadblib in (mediadblibs):
       	    db = importlib.import_module(mediadblib, 'delugeonal')
            try:
                mediadbs.append(db.MediaDb(config, cache = cache))
            except Exception as e:
                print(e)

    mediaserverlib = config['default']['mediaserverlib'] if 'mediaserverlib' in config['default'] and config['default']['mediaserverlib'] is not None else None
    if (mediaserverlib is not None):
        server = importlib.import_module(mediaserverlib, 'delugeonal')
        mserver = server.MediaServer(config, cache = cache)

    # TODO: Make this load everything in the 'sites' directory.
    # TODO: Add a user configurable 'sites' directory for custom modules.
    mediasitelibs = [ '.sites.eztv', '.sites.ipt', '.sites.tgx', '.sites.torrenting' ]
    if (mediasitelibs is not None and len(mediasitelibs) > 0):
        for mediasitelib in (mediasitelibs):
            site = importlib.import_module(mediasitelib, 'delugeonal')
            try:
                mediasites.append(site.MediaSite(config))
            except Exception as e:
                print(e)

    torrentclientlib = config['default']['torrentclientlib'] if 'torrentclientlib' in config['default'] and config['default']['torrentclientlib'] is not None else None
    if (torrentclientlib is not None):
        torrentclient = importlib.import_module(torrentclientlib, 'delugeonal')
        client = torrentclient.TorrentClient(config)

def torrent_size(f):
    total_size = 0
    m = open(f, 'rb')
    torrent_data = m.read()
    t = bencode.decode(torrent_data)
    if (t is None or 'info' not in t):
        raise Exception("can't get info from {}".format(f))
    if ('files' not in t['info']):
        total_size = int(t['info']['length'])
    else:
        for torrent_file in t['info']['files']:
            total_size = total_size + int(torrent_file['length'])
    return total_size

def torrents(args = minorimpact.default_arg_flags):
    info = client.get_info(verbose = args.verbose)
    for f in info:
        print("{}: ratio:{}, size:{}, seedtime:{}, tracker:{}({})".format(f, info[f]['ratio'], info[f]['size'], info[f]['seedtime'], info[f]['tracker'], info[f]['trackerstatus']))

def trackers():
    trackers = []
    setup()
    for site in mediasites:
        for tracker in site.trackers():
            trackers.append(tracker)
    return trackers

def transform(title, season, episode):
    transforms = eval(config['default']['transforms'])

    if title in transforms:
        for transform in transforms[title]:
            criteria = []
            action = []
            for c in transform['criteria'].split(','):
                match = re.search('^([a-z]+)([=<>]+)([0-9]+)$', c)
                if (match):
                    criteria.append({"field":match.group(1), "cmp":match.group(2), "value":match.group(3)})

            for a in transform['action'].split(','):
                match = re.search('^([a-z]+)([+-=])(.+)$', a)
                if (match):
                    value = match.group(3)
                    if re.search('^[0-9]+$', value):
                        foo = {"field":match.group(1), "action":match.group(2), "value":value}
                    else:
                        foo = {"field":match.group(1), "action":match.group(2), "value":'"{}"'.format(value)}
                    action.append(foo)

            if (criteria and action):
                transformation = {'title': title, 'season': season, 'episode':episode}
                criteria_string = ''
                for c in criteria:
                    criteria_string = '{} and {}{}{}'.format(criteria_string, c["field"], c["cmp"], c["value"])
                criteria_string = re.sub('^ and ', '', criteria_string)
                if (eval(criteria_string, {}, transformation)):
                    for a in action:
                        if (a['action'] == '='):
                            s = "{} = {}".format(a['field'], a['value'])
                            exec(s, {}, transformation)
                        else:
                            s = "{} = {} {} {}".format(a['field'], a['field'], a['action'], a['value'])
                            exec(s, {}, transformation)

                return transformation

    return None

def write_cache():
    if (config is not None and 'default' in config and 'cache_file' in config['default']):
        cache_file = config['default']['cache_file']
        #print("write_cache(): cache_file = '" + cache_file + "'")
        if (os.path.exists(cache_file)):
            #print("writing cache_file:" + cache_file)
            with open(cache_file, "wb") as f:
                pickle.dump(cache, f)

atexit.register(write_cache)

