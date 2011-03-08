# Contains
# GetUpdates
# CellUpdate
# DropletUpdate
from actions import *

class GetUpdates(WorkerAction):
    def __init__(self, hub):
        super(GetUpdates, self).__init__(hub)
        self._action_name = "GetUpdates"

    @property
    def _uri(self):
        return '%s/api/status/' % self._hub.config_manager.get_server()

    def _add_to_queue(self, item, when=0):
        reactor.callLater(when, self._hub.queue.put, item)

    def _execute(self):
        d = self._hub.rest_client.get(self._uri)
        d.addCallback(self._success)
        d.addErrback(self._failure)

        return d

    def _success(self, result):
        result = json.load(result)

        if 'error' in result.keys():
            raise Exception(result['error'])

        for droplet in result['reply']['droplets']:
            self._add_to_queue(
                DropletUpdate(hub=self._hub, **droplet)
                )

        for cell in result['reply']['cells']:
            self._add_to_queue(
                CellUpdate(hub=self._hub, **cell)
                )

        # todo
        # update timestamp
        # notifications
        self._add_to_queue(GetUpdates(hub=self._hub), when=100)

    def _failure(self, result):
        if __debug__:
            dprint("Get updates failure", result)

        raise RetryLater(2)

class CellUpdate(WorkerAction):
    def __init__(self, hub, pk, name, roots, owner, created, updated, deleted):
        assert isinstance(pk, basestring)
        assert isinstance(name, basestring)
        assert isinstance(roots, list)
        assert isinstance(owner, dict)
        assert isinstance(deleted, bool)
        assert isinstance(created, basestring)
        assert isinstance(updated, basestring)

        super(CellUpdate, self).__init__(hub)

        self._action_name = "CellUpdate"

        self.hub = hub
        self._dm = self.hub.database_manager

        self.pk = pk
        self.name = name
        self.roots = roots
        self.owner = owner
        self.deleted = deleted
        self.created = created
        self.updated = updated

    @property
    def unique_id(self):
        return self.pk

    def exists(self):
        # return record if item exists in the database
        # else return False
        return self._dm.store.find(db.File,
                                   db.File.id == self.pk
                                   ).one() or False

    def is_root(self):
        if not len(self.roots):
            return True
        else:
            return False

    def parent_exists(self):
        # return True if parent exists
        if not self.is_root():
            return self._dm.store.find(db.File,
                                       db.File.id == self.roots[0]['pk']
                                       ).one() or False
        else:
            return False

    def _create_record(self):
        record = db.File()
        record.id = self.pk
        record.hash = None
        record.revision = None
        record.size = None
        record.directory = True

        if not self.is_root():
            parent = self.parent_exists()
            record.filename = pathjoin(parent.filename, self.name)
            record.parent_id = parent.id
            record.watchpath = parent.watchpath
        else:
            record.filename = u''
            record.parent_id = None
            record.watchpath = self._watchpath

        return record

    def notify(self):
        """ Display notification """
        return

    @property
    def fullpath(self):
        return pathjoin(self._record.watchpath.path,
                        self._record.filename)

    def _execute(self):
        # if we don't know the file:
        if not self.exists():
            # if root do something
            if self.is_root():
                # new repository
                watchpath = db.WatchPath()
                watchpath.server_id = self.pk
                watchpath.path = pathjoin(os.path.abspath(u'.'), self.name)
                self._watchpath = watchpath
                self._dm.store.add(watchpath)
            else:
                # and it's already delete don't worry
                if self.deleted:
                    return True
                elif not self.parent_exists():
                    # if parent does not exist, add to queue
                    raise WaitItem(self.roots[-1]['pk'])

            self._record = self._create_record()

            # create path
            util.create_path(self.fullpath)

            # add a new watch
            self.hub.notify_manager.add_watch(self.fullpath)

        # we know the file
        else:
            if self.is_root():
                return
            elif not self.parent_exists():
                # if parent does not exist, add to queue
                raise WaitItem(self.roots[-1]['pk'])

            self._record = self.exists()

            # file was deleted
            if self.deleted:
                # remove from filesystem
                from shutil import rmtree
                try:
                    shutil.rmtree(self.fullpath)
                except (IOError, OSError), error_message:
                    if __debug__:
                        dprint("An (not important) exception occured",
                               error_message,
                               exception=1)

                # remove from database
                for child in self._dm.store.find(db.File,
                                                 db.File.filename.like(u'%s/%%' % self._record.filename),
                                                 db.WatchPath.path == self._record.watchpath.path,
                                                 db.Watchpath.id == db.File.watchpath_id
                                                 ):
                    self._dm.store.remove(child)

            # file was updated
            else:
                # check if the file was moved
                if self.roots[0]['pk'] != self._record.parent_id:
                    parent = self.parent_exists()
                    oldfilename = self._record.filename
                    oldwatchpath = self._record.watchpath.path

                    self._record.filename = parent.filename + self.name
                    self._record.watchpath = parent.watchpath

                    oldpath = pathjoin(oldwatchpath, oldfilename)

                    # move file
                    shutil.move(oldpath, self.fullpath)

                    # change subfiles / subdirectories in database
                    for child in self._dm.store.find(db.File,
                                                     db.File.filename.like(u'%s/%%' % oldfilename),
                                                     db.Watchpath.path == oldwatchpath,
                                                     db.Watchpath.id == db.File.watchpath_id
                                                     ):
                        child.filename = child.filename.replace(oldfilename, self._record.filename, 1)
                        child.watchpath = self._record.watchpath




class DropletUpdate(WorkerAction):
    def __init__(self, hub, pk, name, cell, owner, created, updated, deleted, revisions):
        assert isinstance(pk, basestring)
        assert isinstance(name, basestring)
        assert isinstance(cell, dict)
        assert isinstance(owner, dict)
        assert isinstance(deleted, bool)
        assert isinstance(created, basestring)
        assert isinstance(updated, basestring)
        assert isinstance(revisions, list)

        super(DropletUpdate, self).__init__(hub)
        self._action_name = "DropletUpdate"

        self.hub = hub
        self._dm = self.hub.database_manager

        self.pk = pk
        self.name = name
        self.cell = cell
        self.owner = owner
        self.deleted = deleted
        self.created = util.parse_datetime(created)
        self.updated = util.parse_datetime(updated)
        self.revisions = revisions

    @property
    def unique_id(self):
        return self.pk

    def exists(self):
        # return record if item exists in the database
        # else return False
        return self._dm.store.find(db.File,
                                   db.File.id == self.pk
                                   ).one() or False

    def cell_exists(self):
        # return True if parent exists
        return self._dm.store.find(db.File,
                                   db.File.id == self.cell['pk']
                                   ).one() or False

    def _create_record(self):
        record = db.File()
        record.hash = self.revisions[-1]['content_md5']
        record.revision = len(self.revisions)
        record.id = self.pk
        record.size = None
        record.directory = False
        record.modified = self.updated

        cell = self.cell_exists()
        record.watchpath = cell.watchpath
        record.parent_id = cell.id
        record.filename = pathjoin(cell.filename, self.name)

        # add to store
        self._dm.store.add(record)

        return record

    def _touch_file_datetime(self):
        """ Touch file to update time and date according to received
        data
        """
        # set last modification date to the one given by server
        # for use convenience
        # trick to calculate localtime from utctime
        # m_datetime = util.get_localtime(self.updated)
        m_datetime = self.updated
        a_datetime = datetime.now()
        os.utime(self.fullpath,
                 (int(a_datetime.strftime("%s")),
                  int(m_datetime.strftime("%s"))))

    def notify(self):
        pass

    @property
    def fullpath(self):
        if self._record:
            return pathjoin(self._record.watchpath.path,
                            self._record.filename)
        return False

    def fix_permissions(self):
        # ensure that we can read/write the file
        current_mode = os.stat(self.fullpath).st_mode
        os.chmod(self.fullpath, current_mode|256|128)

    def _generate_signarute(self):
        return util.get_signature(self.fullpath)

    def _execute(self):
        # if we don't know the file:
        if not self.exists():
             # and it's already delete don't worry
             if self.deleted:
                 return True

             # if cell does not exist, add to queue
             elif not self.cell_exists():
                 raise WaitItem(self.cell['pk'])

             self._record = self._create_record()
             cell = self.cell_exists()

             # check if for some reasy we already have the file
             if os.path.exists(self.fullpath) and \
                util.get_hash(self.fullpath) == self._record.hash:

                 # ensure that we can read/write it
                 self.fix_permissions()

                 # generate signarute
                 self._record.signature = self._generate_signarute()

             else:
                 # we need to fetch the file
                 # return deferred
                 return self._get_file()

        # we know the file
        else:
            # TODO
            pass

    def _get_file(self):
        uri = '%(server)s/api/droplet/%(droplet_id)s/revision/latest/content/' %\
              {'server': self._hub.config_manager.get_server(),
               'droplet_id': self.pk}
        d = self.hub.rest_client.get(str(uri))
        d.addCallback(self._get_file_success)
        d.addErrback(self._failure)

    def _get_patch_success(self):
        pass

    def _get_patch_error(self):
        pass

    def _get_patch(self):
        pass

    def _get_file_success(self, result):
        # result is a file handle

        # check the hash
        if not util.get_hash(f=result) == self._record.hash:
            # oups
            if __debug__:
                dprint("Hashes don't match!")
            raise ValueError("Hashes don't match!")

        # set write permissions first
        # Warning: we are actually chaning permissions on
        # user files, so we must warn them on README
        # set user read+write
        if os.path.exists(self.fullpath):
            current_mode = os.stat(self.fullpath).st_mode
            os.chmod(self.fullpath, current_mode|256|128)

        # move file
        shutil.move(result.name, self.fullpath)

        # update time
        self._touch_file_datetime()

        # update signature
        self._record.signature = self._generate_signarute()

    def _failure(self, result):
        if __debug__:
            dprint("We cannot fetch the file", result, exception=1)

        # self._tmp_file.close()
        # try:
        #     os.remove(self._tmp_file.name)
        # except OSError:
        #     pass

        raise RetryLater
