# Contains
# DeleteObject
# DeleteDir
# DeleteFile

import shutil
import os

from actions import *

if __debug__:
    from Print import dprint

class DeleteObject(WorkerAction):
    """ lala """
    def __init__(self, hub, filename, watchpath):
        super(DeleteObject, self).__init__(hub)

        self.filename = filename
        self.watchpath = watchpath
        self._dm = self._hub.database_manager
        self._record = False

    @property
    def unique_id(self):
        if self._record:
            return self._record.id
        else:
            return False

    def exists(self):
        # return record if item exists in the database
        # else return False
        return self._dm.store.find(db.File,
                                   db.File.filename == self.filename,
                                   db.WatchPath.path == self.watchpath,
                                   db.WatchPath.id == db.File.watchpath_id
                                   ).one() or False

    def _execute(self):
        self._record = self.exists()
        if not self._record:
            # file not watched, ignoring
            # TODO maybe should look into the queue for pending actions
            # regarding this file
            return

        # delete from database
        self._delete_from_db()

        # delete from filesystem
        self._delete_from_fs()

        # notify server
        return self._post_to_server()

    def _failure(self, result):
        if __debug__:
            dprint("Failure in delete", result)

        raise RetryLater

class DeleteDir(DeleteObject):
    def __init__(self, hub, filename, watchpath):
        super(DeleteDir, self).__init__(hub, filename, watchpath)

    def _delete_from_db(self):
        # delete all children
        for entry in self._dm.store.find(db.File,
                                         db.File.filename.like(u'%s/%%' % self.filename),
                                         db.WatchPath.path == self.watchpath,
                                         db.WatchPath.id == db.File.watchpath_id
                                         ):
            entry.remove()

        # delete self
        self._dm.store.remove(self._record)

    def _delete_from_fs(self):
        # required when deleting recursivelly folders
        fullpath = pathjoin(self.watchpath, self._record.filename)
        try:
            shutil.rmtree(fullpath)
        except OSError, error_message:
            # ah, ignore
            pass

    def _post_to_server(self):
        uri = '%s/api/cell/%s/' % (self._hub.config_manager.get_server(),
                               self._record.id)
        d = self._hub.rest_client.delete(str(uri))
        d.addErrback(self._failure)

        return d

class DeleteFile(DeleteObject):
    def __init__(self, hub, filename, watchpath):
        super(DeleteFile, self).__init__(hub, filename, watchpath)

    def _delete_from_db(self):
        # delete self
        self._dm.store.remove(self._record)

    def _delete_from_fs(self):
        # required when deleting recursivelly folders
        fullpath = pathjoin(self.watchpath, self._record.filename)
        try:
            os.unlink(fullpath)
        except OSError, error_message:
            # ah, ignore
            pass

    def _post_to_server(self):
        uri = '%s/api/droplet/%s/' % (self._hub.config_manager.get_server(),
                                  self._record.id)
        d = self._hub.rest_client.delete(str(uri))
        d.addErrback(self._failure)

        return d
