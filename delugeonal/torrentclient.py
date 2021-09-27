from abc import ABC, abstractmethod

class TorrentClient(ABC):

    @abstractmethod
    def add_torrent(self, torrent):
        pass

    @abstractmethod
    def delete_torrent(self, torrent, remove_data = False):
        pass

    @abstractmethod
    def get_config(self):
        pass

    @abstractmethod
    def get_info(self, filename = None, verbose=False):
        pass

    @abstractmethod
    def get_torrent_file(self, filename, verbose=False, config = None):
        pass

    @abstractmethod
    def move_torrent(self, torrent, target):
        pass

    @abstractmethod
    def pause_all(self):
        pass

    @abstractmethod
    def resume_all(self):
        pass

