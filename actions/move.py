# Contains
# MoveFile
# MoveDirectory
from actions import *

class MoveObject(WorkerAction):
    def __init__(self, hub, filename, old_filename, watchpath):
        super(MoveObject, self).__init__(hub)

        self.filename = filename
        self.old_filename = old_filename
        self.watchpath = watchpath

        self._dm = self._hub.database_manager

    @property
    def unique_id(self):
        return 'Move %s' % pathjoin(self.watchpath, self.filename)

    def _exists(self):
        # return record if item exists in the database
        # else return False
        return self._dm.store.find(db.File,
                                   db.File.filename == self.old_filename,
                                   db.WatchPath.path == self.watchpath,
                                   db.WatchPath.id == db.File.watchpath_id
                                   ).one() or False

    def _get_parent(self):
        parent = self._dm.store.find(db.File,
                                     db.File.filename == os.path.dirname(self.filename),
                                     db.File.watchpath_id == db.WatchPath.id,
                                     db.WatchPath.path == self.watchpath
                                     ).one()
        if not parent:
            raise RetryLater
        else:
            return parent

    def _get_uri(self):
        raise NotImplementedError

    def _get_data(self):
        raise NotImplementedError

    def _update_children(self):
        # update all subdirectories and files if this is directory
        # change subfiles / subdirectories in database
        query = self._dm.store.find(db.File,
                                    db.File.filename.like(u'%s/%%' % self.old_filename),
                                    db.WatchPath.path == self._record.watchpath.path,
                                    db.WatchPath.id == db.File.watchpath_id
                                    )
        for f in query:
            f.filename = f.filename.replace(self.old_filename, self.filename, 1)
            f.watchpath = self._parent.watchpath

    def _execute(self):
        self._record = self._exists()

        if not self._record:
            raise DropItem("We already did the move")

        self._parent = self._get_parent()

        uri = self._get_uri()
        data = self._get_data()

        d = self._hub.rest_client.put(str(uri), data=data)
        d.addCallback(self._success)
        d.addErrback(self._failure)
        return d

    def _success(self, result):
        raise NotImplementedError

    def _failure(self, error):
        raise NotImplementedError

class MoveFile(MoveObject):
    def __init__(self, hub, filename, old_filename, watchpath):
        super(MoveFile, self).__init__(hub, filename, old_filename, watchpath)

    def _get_data(self):
        return {'name': os.path.basename(self.filename),
                'cell':self._parent.id
                }

    def _get_uri(self):
        return '%s/api/droplet/%s/' % (self._hub.config_manager.get_server(),
                                       self._record.id)


    def _success(self, result):
        result = json.load(result)
        self._record.parent_id = result['reply']['cell']['pk']
        self._record.watchpath = self._parent.watchpath
        self._record.filename = pathjoin(self._parent.filename,
                                         result['reply']['name']
                                         )
        self._record.modified = util.parse_datetime(result['reply']['updated'])

        self._update_children()

    def _failure(self, error):
        if __debug__:
            dprint("File move failed", error)

        raise RetryLater

class MoveDir(MoveObject):
    def __init__(self, hub, filename, old_filename, watchpath):
        super(MoveDir, self).__init__(hub, filename, old_filename, watchpath)

    def _get_data(self):
        return {'name': os.path.basename(self.filename),
                'parent':self._parent.id
                }

    def _get_uri(self):
        return '%s/api/cell/%s/' % (self._hub.config_manager.get_server(),
                                       self._record.id)

    def _success(self, result):
        result = json.load(result)
        self._record.parent_id = result['reply']['roots'][0]['pk']
        self._record.watchpath = self._parent.watchpath
        self._record.filename = pathjoin(self._parent.filename,
                                         result['reply']['name']
                                         )
        self._record.modified = util.parse_datetime(result['reply']['updated'])
        self._update_children()

    def _failure(self, error):
        if __debug__:
            dprint("Directory move failed", error)

        raise RetryLater
