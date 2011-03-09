# Contains
# ModifyFile
# CreateDir

from actions import *

class ModifyFile(WorkerAction):
    def __init__(self, hub, filename, watchpath):
        super(ModifyFile, self).__init__(hub)
        self._action_name = 'ModifyFile'

        self.filename = filename
        self.watchpath = watchpath

        self._dm = self._hub.database_manager


    @property
    def fullpath(self):
        return pathjoin(self.watchpath, self.filename)

    def _record_get_or_create(self):
        record = self._dm.store.find(db.File,
                                     db.File.filename == self.filename,
                                     db.WatchPath.path == self.watchpath,
                                     db.WatchPath.id == db.File.watchpath_id
                                     ).one() or False

        if not record:
            record = db.File()
            record.filename = self.filename
            record.hash = None
            record.watchpath_id = self._parent.watchpath.id
            record.directory = False
            record.revision = 0
            record.parent_id = self._parent.id
            self._dm.store.add(record)

        return record

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

    def _execute(self):
        self._parent = self._get_parent()
        self._record = self._record_get_or_create()
        self._hash = util.get_hash(filename=self.fullpath)

        if self._hash == self._record.hash:
            dprint("File not modified, ignoring")

        self._record.hash = self._hash

        if self._record.id:
            patch = True
            self._file_handler = util.get_delta(self._record.signature,
                                                self.fullpath)

        else:
            patch = False
            try:
                self._file_handler = open(self.fullpath)
            except (OSError, IOError) as error_message:
                raise RetryLater()

            if not self._record.id:
                return self._post_droplet()
            else:
                return self._put_revision()

    def _post_droplet(self):
        uri = '%s/api/droplet/' % self._hub.config_manager.get_server()
        data = {'name': os.path.basename(self.filename), 'cell': self._parent.id}
        d = self._hub.rest_client.post(str(uri), data=data)
        d.addCallback(self._success_droplet_callback)
        d.addErrback(self._failure_callback)
        return d

    def _post_revision(self):
        uri = '%s/api/droplet/%s/revision/' % (self._hub.config_manager.get_server(), self._record.id)
        data = {'md5': self._record.hash, 'number': self._record.revision}
        d = self._hub.rest_client.post(str(uri), data=data, file_handle=self._file_handler)
        d.addCallback(self._success_revision_callback)
        d.addErrback(self._failure_callback)
        return d

    def _put_revision(self):
        uri = '%s/api/droplet/%s/revision/' % (self._hub.config_manager.get_server(), self._record.id)
        data = {'md5': self._record.hash, 'number': self._record.revision}
        d = self._hub.rest_client.post(str(uri), data=data, file_handle=self._file_handler)
        d.addCallback(self._success_revision_callback)
        d.addErrback(self._failure_callback)
        return d

    def _success_droplet_callback(self, result):
        result = json.load(result)
        self._record.id = result['reply']['pk']
        return self._post_revision()

    def _success_revision_callback(self, result):
        result = json.load(result)
        self._record.signature = util.get_signature(self.fullpath)
        self._record.revision = result['reply']['number']
        self._record.modified = util.parse_datetime(result['reply']['revision']['created'])

    def _failure_callback(self, error):
        if __debug__:
            dprint("Failure in modify ", error)
        raise RetryLater

class CreateDir(WorkerAction):
    def __init__(self, hub, filename, watchpath):
        super(CreateDir, self).__init__(hub)
        self._action_name = 'CreateDir'
        self.filename = filename
        self.watchpath = watchpath

        self._dm = self._hub.database_manager

    def _exists(self):
        # return record if item exists in the database
        # else return False
        return self._dm.store.find(db.File,
                                   db.File.filename == self.filename,
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

    def _create_record(self):
        record = db.File()
        record.filename = self.filename
        record.hash = None
        record.watchpath_id = self._parent.watchpath.id
        record.directory = True
        record.revision = 0
        record.parent_id = self._parent.id

        # add to store
        self._dm.store.add(record)

        return record

    def _execute(self):
        if self._exists():
            # record already exists, do nothing
            raise DropItem("Directory record already exists")

        # get parent
        self._parent = self._get_parent()

        # create record
        self._record = self._create_record()

        uri = '%s/api/cell/' % (self._hub.config_manager.get_server())
        data = {'name': os.path.basename(self.filename),
                'parent':self._record.parent.id
                }
        d = self._hub.rest_client.post(str(uri), data=data)
        d.addCallback(self._success)
        d.addErrback(self._failure)
        return d


    def _success(self, result):
        result = json.load(result)
        self._record.id = result['reply']['pk']

    def _failure(self, error):
        if __debug__:
            dprint("Cell create failed", error)

        raise RetryLater
