from twisted.internet import reactor
from os.path import join as pathjoin
import json
import tempfile
import base64
import shutil
import os
from datetime import datetime
from time import mktime

import dbschema as db
import util

if __debug__:
    from Print import dprint

def update(hub, item):
    _dms = hub.database_manager.store
    function, data = item
    

    # find file in local db
    record = _dms.find(db.File,
                       db.File.server_id == data['id'],
                       ).one() or False
    if record: 
        # We already know the file
        def success_cb(result, tmp_file, record, data):
            record.parent_id = data['parent_id']
            record.hash = data['hash']
            record.size = data['size']
            record.filename = data['filename']
            record.revision = data['revision']
            record.modified = util.parse_datetime(data['modified'])

            fullpath = pathjoin(record.watchpath.path,
                                record.parent.filename,
                                record.filename)
            util.patch_file(tmp_file.name,
                            fullpath,
                            data['hash'])

            # delete tmp_file we don't longer need it
            tmp_file.close()
            os.unlink(tmp_file.name)
            
            record.signature = util.get_signature(fullpath)
            hub.database_manager.commit()

            ## util.notify(record.filename,
            ##             "Successfully downloaded from server",
            ##             image="down")
            reactor.callLater(util.WORKER_RECALL, hub.worker.work)

        def failure_cb(result, tmp_file):
            if __debug__:
                dprint("Failed to get delta", result)
            hub.database_manager.store.rollback()

            tmp_file.close()
            os.unlink(tmp_file.name)
            reactor.callLater(util.WORKER_RECALL, hub.worker.work)

        # check if deleted
        if data['deleted']:
            # remove from filesystem and database
            fullpath = pathjoin(record.watchpath.path,
                                record.parent.filename,
                                record.filename)

            if record.directory:
                try:
                    shutil.rmtree(fullpath)
                except (IOError, OSError), error_message:
                    if __debug__:
                        dprint("An (not important) exception occured",
                               error_message,
                               exception=1)
                
                for child in _dms.find(db.File,
                                       db.File.filename.like(u'%s/%%' % record.filename),
                                       db.WatchPath.path == record.watchpath.path,
                                       db.WatchPath.id == db.File.watchpath_id                            
                                       ):
                    _dms.remove(child)
            else:
                try:
                    os.unlink(fullpath)
                except OSError, error_message:
                    # maybe the file is already deleted, don't worry
                    if __debug__:                    
                        dprint("An (not important) exception occured", error_message, exception=1)

            # delete self
            _dms.remove(record)
            hub.database_manager.commit()

            reactor.callLater(util.WORKER_RECALL, hub.worker.work)
            return

        if data['directory'] or data['hash'] == record.hash:
            # maybe moved
            filename = os.path.basename(record.filename)
            if data['revision'] != record.revision:
                dprint(data['revision'], record.revision, data['revision'] == record.revision)
                record.parent_id = data['parent_id']
                oldpath = pathjoin(record.watchpath.path, record.filename)
                record_parent = _dms.find(db.File,
                                          db.File.server_id == data['parent_id']).one()
                old_filename = record.filename
                old_watchpath = record.watchpath.path
                record.filename = pathjoin(record_parent.filename,
                                           data['filename'])
                record.watchpath = record_parent.watchpath
                fullpath = pathjoin(record_parent.watchpath.path, record.filename)
                # move file
                shutil.move(oldpath, fullpath)

                # change subfiles / subdirectories in database
                query = _dms.find(db.File,
                                  db.File.filename.like(u'%s/%%' % old_filename),
                                  db.WatchPath.path == old_watchpath,
                                  db.WatchPath.id == db.File.watchpath_id
                                  );
                for f in query:
                    f.filename = f.filename.replace(old_filename, record.filename, 1)
                    f.watchpath = record.watchpath
                
                record.revision = data['revision']
                hub.database_manager.commit()
            reactor.callLater(util.WORKER_RECALL, hub.worker.work)
        else:
            # we need to get the file
            # send our signature to receive the delta
            uri = '%s/file/%s?delta=True' % \
                  (hub.config_manager.get_server(), record.id)
            tmp_file = tempfile.NamedTemporaryFile(prefix='foobox-', suffix='.tmp', delete=False)
            d = hub.rest_client.get_file(uri, tmp_file, record.signature)
            d.addCallback(success_cb, tmp_file, record, data)
            d.addErrback(failure_cb, tmp_file)
    else:
        # we don't know the file
        def success_cb(result, record, tmp_file, data):
            # save
            # add to database

            ## # file is close by client.downloadPage so
            ## # we must reopen it
            ## tmp_file = open(tmp_file.name, 'rb')
            if util.get_hash(filename=tmp_file.name) == data['hash']:
                fullpath = pathjoin(record_parent.watchpath.path,
                                    record_parent.filename,
                                    data['filename'])
                
                # set write permissions first
                # Warning: we are actually chaning permissions on
                # user files, so we must warn them on README
                # set user read+write
                if os.path.exists(fullpath):
                    current_mode = os.stat(fullpath).st_mode
                    os.chmod(fullpath, current_mode|256|128)
                shutil.move(tmp_file.name, fullpath)

                # set last modification date to the one given by server
                # for use convenience
                # trick to calculate localtime from utctime
                m_datetime = util.get_localtime(util.parse_datetime(data['modified']))
                a_datetime = datetime.now()
                os.utime(fullpath,
                         (int(a_datetime.strftime("%s")),
                          int(m_datetime.strftime("%s"))))
                record.signature = util.get_signature(fullpath)
                
                _dms.add(record)
                hub.database_manager.commit()

                ## util.notify(data['filename'],
                ##             "Successfully downloaded from server",
                ##             image="down")
            else:
                # TODO raise error
                if __debug__:
                    dprint("Hashes don't match",
                           util.get_hash(f=tmp_file),
                           data['hash'],
                           tmp_file.name)
                raise ValueError("Hashes don't match")

            reactor.callLater(util.WORKER_RECALL, hub.worker.work)

        def failure_cb(result, tmp_file):
            if __debug__:
                dprint("We cannot fetch the file", result, exception=1)
            hub.database_manager.store.rollback()

            tmp_file.close()
            try:
                os.remove(tmp_file.name)
            except OSError:
                pass
            reactor.callLater(util.WORKER_RECALL, hub.worker.work)

        # we don't know the file and it's already deleted, don't worry
        if data['deleted']:
            reactor.callLater(util.WORKER_RECALL, hub.worker.work)
            return

        record = db.File()
        record.hash = data.get('hash', None)
        record.revision = data['revision']
        record.server_id = data['id']
        record.size = data.get('size', None)
        record.directory = data.get('directory', False)
        record.modified = util.parse_datetime(data['modified'])

        if data['parent_id']:
            record_parent = _dms.find(db.File,
                                      db.File.server_id == data['parent_id']).one()
            if not record_parent:
                # we don't have the parent dir yet.
                # do nothing for now, try to update later
                hub.database_manager.store.rollback()
                reactor.callLater(3, hub.worker.queue.put, (function, data))
                reactor.callLater(util.WORKER_RECALL, hub.worker.work)
                return

            record.filename = pathjoin(record_parent.filename,
                                       data['filename'])
            record.watchpath = record_parent.watchpath
            record.parent_id = data['parent_id']
            fullpath = pathjoin(record.watchpath.path, record.filename)
            
            if data['directory']:
                util.create_path(fullpath)
                # add watch
                hub.notify_manager.add_watch(fullpath)

                _dms.add(record)
                hub.database_manager.commit()
                reactor.callLater(util.WORKER_RECALL, hub.worker.work)
            else:
                # check if for some reason we already have the file
                # so we don't need to download it again
                if os.path.exists(fullpath) and util.get_hash(fullpath) == data['hash']:
                    # ensure that we can read/write it
                    current_mode = os.stat(fullpath).st_mode
                    os.chmod(fullpath, current_mode|256|128)
                    # create signature
                    record.signature = util.get_signature(fullpath)
                    _dms.add(record)
                    hub.database_manager.commit()
                    reactor.callLater(util.WORKER_RECALL, hub.worker.work)
                else:
                    uri = '%s/file/%s' %\
                          (hub.config_manager.get_server(), data['id'])
                    tmp_file = tempfile.NamedTemporaryFile(prefix='foobox-', suffix='.tmp', delete=False)
                    d = hub.rest_client.get_file(uri, tmp_file) 
                    d.addCallback(success_cb, record, tmp_file, data)
                    d.addErrback(failure_cb, tmp_file)
        else:
            # new repository
            fullpath = data['filename']
            record.filename = u''

            util.create_path(fullpath)
            # add watch
            hub.notify_manager.add_watch(fullpath)


            watchpath = db.WatchPath()
            watchpath.files.add(record)
            watchpath.path = pathjoin(os.path.abspath(u'.'), data['filename'])
            _dms.add(watchpath)
            reactor.callLater(util.WORKER_RECALL, hub.worker.work)


def get_updates(hub, item):
    _dms = hub.database_manager.store
    
    def success_cb(result):
        try:
            reply = json.loads(result)
        except ValueError, error_message:
            _add_get_updates_to_queue(hub, when=10)
            ## raise ValueError("Malformed request")
            return
        data = reply['data']            
        data_check = [{'name':'id', 'type':int},
                      {'name':'revision', 'type':int},
                      {'name':'filename', 'type':unicode},
                      {'name':'last_revision_by_id', 'type':int},
                      {'name':'last_revision_by_username', 'type':unicode},
                      {'name':'last_revision_by_email', 'type':unicode},
                      {'name':'owner_by_id', 'type':int},
                      {'name':'owner_by_username', 'type':unicode},
                      {'name':'owner_by_email', 'type':unicode},
                      {'name':'modified', 'type':unicode},
                      {'name':'parent_id', 'type':(int, type(None))},
                      {'name':'directory', 'type':bool},
                      {'name':'deleted', 'type':bool}
                      ]
        data_check_dir = data_check[:] + [{'name':'permission', 'type':int},
                                          {'name':'files', 'type':list}]
        data_check_file = data_check[:] + [{'name':'hash', 'type':unicode},
                                           {'name':'size', 'type':int}]
        update_notifications = 0
        for directory in data:
            if not util.check_keys_in_data(data_check_dir, directory):
                # invalid data, ignore directory and files
                if __debug__:
                    dprint("Invalid UPDATE data for directory", directory)
                continue
            
            hub.worker.queue.put(('UPDATE', (directory)))
            for file in directory['files']:
                if not util.check_keys_in_data(data_check_file, file):
                    # invalid data, ignore file
                    if __debug__:
                        dprint("Invalid UPDATE data for file", file)
                    continue
                update_notifications += 1
                filename = file['filename']
                user = file['owner_by_username']
                email = file['owner_by_email']
                hub.worker.queue.put(('UPDATE', (file)))

        # send notification if we are not owners
        if hub.config_manager.config.get('main', 'desktop-notifications') and \
               update_notifications >= 1 and \
               user != hub.config_manager.config.get('main', 'username'):
            if update_notifications == 1:
                util.desktop_update_notification(filename,
                                                 "User %s updated file %s" % (user, filename),
                                                 email
                                                 )
            elif update_notifications > 1:
                util.desktop_many_update_notifications()

        # update timestamp
        hub.config_manager.set_timestamp(reply['timestamp'])
        _add_get_updates_to_queue(hub, when=10)
        reactor.callLater(util.WORKER_RECALL, hub.worker.work)

    def failure_cb(result):
        # TODO do something here
        if __debug__:
            dprint("Get updates failure", result)
        # try again
        _add_get_updates_to_queue(hub, when=2)
        reactor.callLater(util.WORKER_RECALL, hub.worker.work)

    if __debug__:
        dprint("Getting updates")
        
    uri = '%s/repository/user' % hub.config_manager.get_server()
    timestamp = hub.config_manager.get_timestamp()
    if timestamp:
        uri += util.urlencode({'timestamp':timestamp})

    try:
        d = hub.rest_client.get(uri)
        d.addCallback(success_cb)
        d.addErrback(failure_cb)
    except AttributeError, e:
        # we get AttributeError when the client is offline
        # because we do not return a deferred
        # just ignore 
        pass


def _add_get_updates_to_queue(hub, when=False):
    """ I add a 'GETUPDATES' item in the worker's queue, if there is not
    one already

    If when is False I immediatelly add the command to workers queue,
    otherwise I use reactor.callLater to add the command in the queue
    later.
    
    """
    if 'GETUPDATES' not in hub.worker.queue:
        if isinstance(when, int):
            reactor.callLater(when, hub.worker.queue.put, ('GETUPDATES', None))
        else:
            hub.worker.queue.put(('GETUPDATES', None))
