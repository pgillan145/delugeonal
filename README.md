# delugeonal

A set of scripts and libraries for controlling and organizing a torrent/media infrastructure.

Current (barely) supported software:  
- Media Servers: Plex
- Media Databases: IMDb
- Torrent Clients: Deluge 1.3.15
- Media Sites: [IPTorrents](https://iptorrents.com)

## Usage
Add torrent files from a particular directory to your torrent client:
```
    $ delugeonal --add $HOME/Downloads
```
Check for torrents that can/should be removed from your torrent client:
```
    $ delugeonal --cleanup --verbose
```
Scan the rss feed for your configured torrent site and download torrents for any files that aren't present on your media server:
```
    $ delugeonal --rss
```
Move downloaded media files from the default download directory and add them to the proper media server directory:
```
    $ delugeonal --move_media
```

Note that not all services need to be running on the same machine.  Your torrent client may be running on one machine, your media server may be running on a seperate on another, where you may  may also search for and download torrent/magent files.

## Installation
```
    $ pip3 install delugeonal
```

## Configuration

Copy [sample-config](https://github.com/pgillan145/delugeonal/blob/master/sample-config) to one of these three locations:
```
    $HOME/delugeonal.conf
    $HONE/.config/delugeonal/delugeonal.conf
    /etc/delugeonal.conf
```
 ... or set the $DELUGEONAL\_CONF environment variable:
```
    $ export DELUGEONAL_CONF=/place/i/put/the/configuration.file
```
