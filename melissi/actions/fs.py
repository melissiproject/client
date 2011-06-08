# Contains
# RescanDirectories

# melissi modules
from melissi.actions import *

class RescanDirectories(WorkerAction):
    def __init__(self, hub, directories=None):
        super(RescanDirectories, self).__init__(hub)
        self._directories = directories

    @property
    def unique_id(self):
        return self._directories or "all"

    def _execute(self):
        self._hub.notify_manager.rescan_directories(self._directories)
