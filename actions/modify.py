# Contains
# ModifyFile
# CreateDir

from actions import *

class ModifyFile(WorkerAction):
    def __init__(self, hub, filename, watchpath):
        super(ModifyFile, self).__init__(hub)

        self.filename = filename
        self.watchpath = watchpath

    @property
    def unique_id(self):
        return self.filename

    @property
    def fullpath(self):
        return pathjoin(self.watchpath, self.filename)

    def _record_get_or_create(self):
        record = self._fetch_file_record(File__filename=self.filename,
                                         WatchPath__path=self.watchpath
                                         )

        if not record:
            record = db.File()
            record.filename = self.filename
            record.hash = None
            record.watchpath_id = self._parent.watchpath.id
            record.directory = False
            record.revision = 0
            record.parent_id = self._parent.id
            self._dms.add(record)

        return record

    def _get_parent(self):
        parent = self._fetch_file_record(File__filename=os.path.dirname(self.filename),
                                         WatchPath__path=self.watchpath
                                         )

        if not parent:
            # sadly we cannot use WaitItem because we don't know
            # cellid yet
            raise RetryLater("Parent does not exist in db [%s]" % \
                             os.path.dirname(self.filename))
        else:
            return parent

    def _execute(self):
        self._parent = self._get_parent()
        self._record = self._record_get_or_create()
        self._hash = util.get_hash(filename=self.fullpath)

        if self._hash == self._record.hash:
            dprint("File not modified, ignoring")
            raise DropItem("File not modified, ignoring")

        self._record.hash = self._hash

        if self._record.id:
            # patch = True
            # self._file_handler = util.get_delta(self._record.signature,
            #                                     self.fullpath)
            # return self._put_revision()
            try:
                self._file_handler = open(self.fullpath)
            except (OSError, IOError) as error_message:
                raise RetryLater("Erro opening file")
            return self._put_revision()

        else:
            patch = False
            try:
                self._file_handler = open(self.fullpath)
            except (OSError, IOError) as error_message:
                raise RetryLater("Error opening file")

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
        data = {'md5': self._record.hash,
                'number': self._record.revision,
                'patch': False
                }
        d = self._hub.rest_client.put(str(uri), data=data, file_handle=self._file_handler)
        d.addCallback(self._success_revision_callback)
        d.addErrback(self._failure_callback)
        return d

    def _success_droplet_callback(self, result):
        result = json.load(result.content)
        self._record.id = result['reply']['pk']
        self._record.revision = len(result['reply']['revisions'])

        return self._post_revision()

    def _success_revision_callback(self, result):
        result = json.load(result.content)
        # self._record.signature = util.get_signature(self.fullpath)
        self._record.signature = None
        self._record.revision = result['reply']['number']
        self._record.modified = util.parse_datetime(result['reply']['revision']['created'])

    def _failure_callback(self, error):
        if __debug__:
            dprint("Failure in modify ", error)
        raise RetryLater("Failure in modify")

class CreateDir(WorkerAction):
    def __init__(self, hub, filename, watchpath):
        super(CreateDir, self).__init__(hub)
        self.filename = filename
        self.watchpath = watchpath

    @property
    def unique_id(self):
        return self.filename

    def _exists(self):
        # return record if item exists in the database
        # else return False
        return self._fetch_file_record(File__filename=self.filename,
                                       WatchPath__path=self.watchpath
                                       )

    def _get_parent(self):
        parent = self._fetch_file_record(File__filename=os.path.dirname(self.filename),
                                         WatchPath__path=self.watchpath
                                         )
        if not parent:
            raise RetryLater("Parent does not exist in db [%s]" % \
                             os.path.dirname(self.filename))
        else:
            return parent

    def _create_record(self):
        record = db.File()
        record.filename = self.filename
        record.hash = None
        record.watchpath_id = self._parent.watchpath.id
        record.directory = True
        record.revision = None
        record.parent_id = self._parent.id

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
                'parent':self._parent.id
                }

        d = self._hub.rest_client.post(str(uri), data=data)
        d.addCallback(self._success)
        d.addErrback(self._failure)

        return d

    def _success(self, result):
        result = json.load(result.content)
        self._record.id = result['reply']['pk']
        self._record.revision = len(result['reply']['revisions'])
        self._record.modified = util.parse_datetime(result['reply']['created'])

        # add to store
        self._dms.add(self._record)

    def _failure(self, error):
        if __debug__:
            dprint("Cell create failed", error)

        raise RetryLater("Cell create failed [%s]" % self.unique_id)
