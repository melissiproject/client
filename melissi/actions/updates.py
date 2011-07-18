# Contains
# GetUpdates
# CellUpdate
# DropletUpdate

# standard modules
from shutil import rmtree
import logging
log = logging.getLogger("melissilogger")

# melissi modules
import melissi.util
from melissi.actions import *

class GetUpdates(WorkerAction):
    def __init__(self, hub, full=False):
        super(GetUpdates, self).__init__(hub)
        self.full = full

    @property
    def _uri(self):
        return '%s/api/status/after/%s/' % (self._hub.config_manager.get_server(),
                                            self.timestamp
                                            )

    def _add_to_queue(self, item, when=0):
        reactor.callLater(when, self._hub.queue.put, item)

    def _execute(self):
        self.timestamp = 0 if self.full else self._hub.config_manager.get_timestamp()

        d = self._hub.rest_client.get(self._uri)
        d.addCallback(self._success)
        d.addErrback(self._failure)

        return d

    def _success(self, result):
        result = json.load(result.content)

        if 'error' in result.keys():
            raise Exception(result['error'])

        for cell in result['reply']['cells']:
            self._add_to_queue(
                CellUpdate(hub=self._hub, **cell)
                )

        for droplet in result['reply']['droplets']:
            self._add_to_queue(
                DropletUpdate(hub=self._hub, **droplet)
                )

        # update timestamp
        self._hub.config_manager.set_timestamp(result['timestamp'])

        # place a GetUpdates in queue
        self._add_to_queue(GetUpdates(hub=self._hub),
                           when=self._hub.config_manager.get_update_interval()
                           )

    def _failure(self, result):
        log.debug("Get updates failure %s" % result)

class CellUpdate(WorkerAction):
    def __init__(self, hub, id, name, pid, revisions, owner, created, updated, deleted):
        super(CellUpdate, self).__init__(hub)

        self.id = id
        self.name = name
        self.parent = pid
        self.owner = owner
        self.deleted = deleted
        self.created = melissi.util.parse_datetime(created)
        self.updated = melissi.util.parse_datetime(updated)
        self.revisions = revisions

        self._new = True

    @property
    def unique_id(self):
        return self.id

    def exists(self):
        # return record if item exists in the database
        # else return False
        return self._fetch_file_record(File__id=self.id, File__directory=True)

    def is_root(self):
        if not self.parent:
            return True
        else:
            return False

    def parent_exists(self):
        # return True if parent exists
        if not self.is_root():
            return self._fetch_file_record(File__id=self.parent,
                                           File__directory=True
                                           )

        else:
            return False

    def _create_record(self):
        record = db.File()
        record.id = self.id
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

    def _write_log(self):
        # check if entry already exists
        # and if yes, do nothing
        if self._dms.find(db.LogEntry,
                          db.LogEntry.timestamp == self.updated,
                          db.LogEntry.file_id == self.id
                          ).one():
            return

        logentry = db.LogEntry()
        logentry.timestamp = self.updated
        logentry.first_name = self.owner['first_name']
        logentry.last_name = self.owner['last_name']
        logentry.username = self.owner['username']
        logentry.email = self.owner['email']
        logentry.file = self.id
        if self.deleted:
            verb = u'deleted'
        elif self._new:
            verb = u'created'
        else:
            verb = u'edited'
        logentry.action = verb
        logentry.extra = unicode(json.dumps({'type': u'directory', 'name': self.name}))

        self._dms.add(logentry)

    def _send_notification(self):
        """ Display notification """
        if self.deleted:
            verb = u'deleted'
        elif self._new:
            verb = u'created'
        else:
            verb = u'edited'
        self._hub.queue.put_into_notification_list(self.name,
                                                   self.fullpath,
                                                   os.path.dirname(self.fullpath),
                                                   self.owner,
                                                   verb
                                                   )

    @property
    def fullpath(self):
        return pathjoin(self._record.watchpath.path,
                        self._record.filename)

    def _execute(self):
        # if we don't know the file:
        self._record = self.exists()
        if not self._record:
            self._new = True

            # if root do something
            if self.is_root():
                # new repository
                watchpath = db.WatchPath()
                watchpath.server_id = self.id
                watchpath.path = pathjoin(
                    os.path.abspath(self._hub.config_manager.config.get('main', 'new-root-path')),
                    self.name
                    )
                self._watchpath = watchpath
                self._dms.add(watchpath)
            else:
                # and it's already deleted don't worry
                if self.deleted:
                    return True
                elif not self.parent_exists():
                    # if parent does not exist, add to queue
                    raise WaitItem(self.parent)

            self._record = self._create_record()

            # create path
            melissi.util.create_path(self.fullpath)

            # add a new watch
            self._hub.notify_manager.add_watch(self.fullpath)

        # we know the file
        else:
            self._new = False

            if self.is_root():
                return
            elif not self.parent_exists():
                # if parent does not exist, add to queue
                raise WaitItem(self.parent)

            # if revision is older than our revision, do nothing
            if self.revisions < self._record.revision:
                raise DropItem("Local revision larger %s vs %s" %\
                               (self._record.revision, self.revisions)
                               )

            # file was deleted
            if self.deleted:
                # remove from filesystem
                shutil.rmtree(self.fullpath, ignore_errors=True)

                # remove children and self from database
                for child in self._dms.find(db.File,
                                            db.File.filename.like(u'%s/%%' % self._record.filename),
                                            db.WatchPath.path == self._record.watchpath.path,
                                            db.WatchPath.id == db.File.watchpath_id
                                            ):
                    self._dms.remove(child)


            # file was updated
            else:
                # check if the file was moved or renamed
                if self.parent != self._record.parent_id or\
                       self.name != os.path.basename(self._record.filename):

                    parent = self.parent_exists()
                    oldfilename = self._record.filename
                    oldwatchpath = self._record.watchpath.path

                    self._record.filename = pathjoin(parent.filename, self.name)
                    self._record.watchpath = parent.watchpath
                    self._record.parent_id = self.parent

                    oldpath = pathjoin(oldwatchpath, oldfilename)

                    # move file
                    shutil.move(oldpath, self.fullpath)

                    # change subfiles / subdirectories in database
                    for child in self._dms.find(db.File,
                                                db.File.filename.like(u'%s/%%' % oldfilename),
                                                db.WatchPath.path == oldwatchpath,
                                                db.WatchPath.id == db.File.watchpath_id
                                                ):
                        child.filename = child.filename.replace(oldfilename, self._record.filename, 1)
                        child.watchpath = self._record.watchpath

                else:
                    # nothing happened
                    return

        # update modified time
        self._record.modified = self.updated

        # update revisions
        self._record.revision = self.revisions

        # notify user
        self._action_taken = True

class DropletUpdate(WorkerAction):
    def __init__(self, hub, id, name, cell, owner, created, updated,
                 content_sha256, patch_sha256, deleted, revisions):
        super(DropletUpdate, self).__init__(hub)

        self.id = id
        self.name = name
        self.cell = cell
        self.owner = owner
        self.deleted = deleted
        self.created = melissi.util.parse_datetime(created)
        self.updated = melissi.util.parse_datetime(updated)
        self.content_sha256 = content_sha256
        self.patch_sha256 = patch_sha256
        self.revisions = revisions

        self._new = True

    @property
    def unique_id(self):
        return self.id

    def exists(self):
        # return record if item exists in the database
        # else return False
        return self._fetch_file_record(File__id=self.id, File__directory=False)

    def cell_exists(self):
        # return True if parent exists
        return self._fetch_file_record(File__id=self.cell['id'],
                                       File__directory=True,
                                       )

    def _create_record(self):
        record = db.File()
        record.hash = self.content_sha256
        record.revision = self.revisions
        record.id = self.id
        record.size = None
        record.directory = False
        record.modified = self.updated

        cell = self.cell_exists()
        record.watchpath = cell.watchpath
        record.parent_id = cell.id
        record.filename = pathjoin(cell.filename, self.name)

        # add to store
        self._dms.add(record)

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


    def _write_log(self):
        # check if entry already exists
        # and if yes, do nothing
        if self._dms.find(db.LogEntry,
                          db.LogEntry.timestamp == self.updated,
                          db.LogEntry.file_id == self.id
                          ).one():
            return

        logentry = db.LogEntry()
        logentry.timestamp = self.updated
        logentry.first_name = self.owner['first_name']
        logentry.last_name = self.owner['last_name']
        logentry.username = self.owner['username']
        logentry.email = self.owner['email']
        logentry.file = self.id

        if self.deleted:
            verb = u'deleted'
        elif self._new:
            verb = u'created'
        else:
            verb = u'edited'
        logentry.action = verb
        logentry.extra = unicode(json.dumps({'type': u'file', 'name': self.name}))

        self._dms.add(logentry)

    def _send_notification(self):
        if self.deleted:
            verb = u'deleted'
        elif self._new:
            verb = u'created'
        else:
            verb = u'edited'

        self._hub.queue.put_into_notification_list(self.name,
                                                   self.fullpath,
                                                   os.path.dirname(self.fullpath),
                                                   self.owner,
                                                   verb
                                                   )
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

    def _generate_signature(self):
        # return util.get_signature(self.fullpath)
        return ''

    def _execute(self):
        # if we don't know the file:
        self._record = self.exists()
        if not self._record:
            self._new = True

            # and it's already delete don't worry
            if self.deleted:
                return True
            # if cell does not exist, add to queue
            elif not self.cell_exists():
                raise WaitItem(self.cell['id'])

            self._record = self._create_record()
            cell = self.cell_exists()

            # check if for some reason we already have the file
            if os.path.exists(self.fullpath) and \
                   melissi.util.get_hash(self.fullpath) == self._record.hash:

                # ensure that we can read/write it
                self.fix_permissions()

                # generate signarute
                self._record.signature = self._generate_signature()

            else:
                # we need to fetch the file
                # return deferred

                # if path exists, and hash is not the same, then this
                # is a conflict
                if os.path.exists(self.fullpath):
                    log.debug("Conflict on file [%s]" % self.unique_id)

                    resource = self.revisions[-1]['resource']
                    if resource['user'] == self._hub.config_manager.get_username():
                        msg = "your copy on '%s'" % resource['name']
                    else:
                        msg = "%s's copy" % resource['user']
                    self._record.filename = melissi.util.append_to_filename(self._record.filename, msg)

                return self._get_file()

        # we know the file
        else:
            self._new = False

            # if revision is older than our revision, do nothing
            if self.revisions < self._record.revision:
                raise DropItem("Local revision larger %s vs %s" %\
                               (self._record.revision, self.revisions)
                               )

            # if deleted call a delete
            if self.deleted:
                # remove from fs
                try:
                    os.unlink(self.fullpath)
                except OSError, error_message:
                    log.debug("Error while removing file %s maybe not important" %\
                              self.fullpath, exception=1)

                # remove from db
                self._dms.remove(self._record)

                # notify user
                self._action_taken = True
                return

            parent = self._get_parent()
            if parent.id != self._record.parent_id:
                oldfilename = self._record.filename
                oldwatchpath = self._record.watchpath.path

                self._record.filename = pathjoin(parent.filename, self.name)
                self._record.watchpath = parent.watchpath
                self._record.parent = parent

                oldpath = pathjoin(oldwatchpath, oldfilename)

                print "hey"
                # move file
                shutil.move(oldpath, self.fullpath)

            # check if file content changed
            # TODO be aware of race conditions here
            if self.content_sha256 != self._record.hash and \
               self.revisions > self._record.revision:
                # yeah there is some new content, let's fetch this
                # return self._get_patch()
                return self._get_file()

            raise DropItem("Do nothing")

    def _get_parent(self):
        parent = self._fetch_file_record(File__id=self.cell['id'],
                                         File__directory=True,
                                         )

        if not parent:
            raise WaitItem(self.cell['id'])
        else:
            return parent

    def _get_file(self):
        uri = '%(server)s/api/droplet/%(droplet_id)s/revision/latest/content/' %\
              {'server': self._hub.config_manager.get_server(),
               'droplet_id': self.id}
        d = self._hub.rest_client.get(str(uri))
        d.addCallback(self._get_file_success)
        d.addErrback(self._failure)
        return d

    def _get_patch_success(self, result):
        # try patching
        melissi.util.patch_file(result, self.fullpath, self.content_sha256)

        # ok same changes in db
        self._record.signature = self._generate_signature()
        self._record.hash = self.content_sha256
        self._record.modified = self.updated
        self._record.revision = self.revisions

        # notify user
        self._action_taken = True

    def _get_patch(self):
        uri = '%(server)s/api/droplet/%(droplet_id)s/revision/latest/patch/' %\
              {'server': self._hub.config_manager.get_server(),
               'droplet_id': self.id}
        d = self._hub.rest_client.get(str(uri))
        d.addCallback(self._get_patch_success)
        d.addErrback(self._failure)

        return d

    def _get_file_success(self, result):
        # ok same changes in db
        self._record.hash = self.content_sha256
        # check the hash
        if not melissi.util.get_hash(f=result.content) == self._record.hash:
            # oups
            log.debug("Hashes don't match!")
            raise ValueError("Hashes don't match!")

        # set write permissions first
        # Warning: we are actually chaning permissions on
        # user files, so we must warn them on README
        # set user read+write
        if os.path.exists(self.fullpath):
            current_mode = os.stat(self.fullpath).st_mode
            os.chmod(self.fullpath, current_mode|256|128)

        # copy file
        shutil.copyfile(result.content.name, self.fullpath)

        # update time
        self._touch_file_datetime()

        # update signature, revision and time
        self._record.signature = self._generate_signature()
        self._record.revision = self.revisions
        self._record.modified = self.updated

        # notify user
        self._action_taken = True

    def _failure(self, result):
        log.error("We cannot fetch the file")
        log.exception(result)

        # self._tmp_file.close()
        # try:
        #     os.remove(self._tmp_file.name)
        # except OSError:
        #     pass

        raise RetryLater
