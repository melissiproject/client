# Contains
# Share

# standard modules
import logging
log = logging.getLogger("melissilogger")

# melissi modules
from melissi.actions import *


class Share(WorkerAction):
    def __init__(self, hub, filename, watchpath, mode, user):
        super(Share, self).__init__(hub)

        self.filename = filename
        self.watchpath = watchpath
        self.mode = mode
        self.user = user

    @property
    def unique_id(self):
        return self.filename

    def _exists(self):
        # return record if item exists in the database else return
        # False
        return self._fetch_file_record(File__filename=self.filename,
                                       File__directory=True
                                       )

    def _execute(self):
        self._record = self._exists()
        if not self._record:
            # we don't follow the file, thus we cannot share it
            raise DropItem("You cannot share a folder I don't follow")

        data = {'mode': self.mode,
                'user': self.user
                }
        uri = '%s/api/cell/%s/share/' % (self._hub.config_manager.get_server(),
                                         self._record.id)
        # uri = '%s/api/cell/%s/share/' % ("http://localhost:8888",
        #                         self._record.id)

        d = self._hub.rest_client.post(str(uri), data=data)
        d.addErrback(self._failure)

    def _failure(self, error):
        log.debug("Error setting share: %s" % error)

        return DropItem("Failed to set share")
