from twisted.internet import reactor
from os.path import join as pathjoin
import os
import base64
import json

import dbschema as db
import util

if __debug__:
    from Print import dprint

def modify(hub, item):
    _dms = hub.database_manager.store
    function, parameters = item

    if function.startswith('MODIFY'):
        filename, watch_path = parameters
        record = _dms.find(db.File,
                           db.File.filename == filename,
                           db.WatchPath.path == watch_path,
                           db.WatchPath.id == db.File.watchpath_id
                           ).one() or False

    elif function.startswith('CREATEDIR'):
        filename, watch_path = parameters
        record = _dms.find(db.File,
                           db.File.filename == filename,
                           db.WatchPath.path == watch_path,
                           db.WatchPath.id == db.File.watchpath_id
                           ).one() or False
        if record:
            # we already have it
            reactor.callLater(util.WORKER_RECALL, hub.worker.work)
            return

    elif function.startswith('MOVE'):
        filename, old_filename, watch_path = parameters
        record = _dms.find(db.File,
                           db.File.filename == old_filename,
                           db.WatchPath.path == watch_path,
                           db.WatchPath.id == db.File.watchpath_id
                           ).one()
        if not record:
            # we already did the move
            reactor.callLater(util.WORKER_RECALL, hub.worker.work)
            return

    fullpath = pathjoin(watch_path, filename)

    # helper functions start
    def success_cb(result, record, filename, fullpath, watch_path):
        try:
            data = json.loads(result)
        except ValueError, error_message:
            # let the errback handle it
            raise

        # generate signature
        if not data['directory']:
            file_signature = util.get_signature(fullpath)
        else:
            file_signature = None

        # create / update record
        if not record:
            record = db.File()

        # don't use server filename since it's stripped
        record.filename = filename
        record.revision = data['revision']
        record.directory = data['directory']
        record.hash = data['hash']
        record.size = data['size']
        record.signature = file_signature
        record.server_id = data['id']
        record.modified = util.parse_datetime(data['modified'])
        record.parent = _dms.find(db.File,
                                  db.File.server_id == data['parent_id']
                                  ).one()
        record.watchpath = _dms.find(db.WatchPath,
                                     db.WatchPath.path == watch_path
                                     ).one()
        _dms.add(record)
        hub.database_manager.commit()

        # notify
        # util.notify(filename, "Successfully uploaded to server", image="up")
        reactor.callLater(util.WORKER_RECALL, hub.worker.work)

    def failure_cb(error):
        if __debug__:
            dprint("Failure in modify", error)
        hub.database_manager.store.rollback()
        reactor.callLater(util.WORKER_RECALL, hub.worker.work)
    # helper functions end

    # generate hash
    if function == 'MODIFY':
        file_hash = util.get_hash(filename=fullpath)

        if record and file_hash == record.hash:
            # file not modified, ignore
            if __debug__:
                dprint("File not modified, ignoring")
            reactor.callLater(util.WORKER_RECALL, hub.worker.work)
            return

        if record:
            # we already follow this file
            delta = True
            # generate delta
            file_handler = util.get_delta(record.signature, fullpath)
        else:
            # this is a new file
            delta = False
            try:
                file_handler = open(fullpath, 'rb')
            except (OSError, IOError), error_message:
                # we cannot access the file for some reason, ignore
                if __debug__:
                    dprint("Error accessing file:", error_message, exception=1)
                hub.database_manager.store.rollback()
                reactor.callLater(util.WORKER_RECALL, hub.worker.work)
                return

            ## # create new record
            ## record = db.File()
            ## record.filename = filename
            ## record.revision = 0
            ## record.directory = False
            ## record.watchpath = _dms.find(db.WatchPath,
            ##                              db.WatchPath.path == watch_path
            ##                              ).one()

        content = True
        revision = 0
        # get size
        file_size = os.path.getsize(fullpath)
        directory = False

    elif function == 'CREATEDIR':
        # check if we
        ## record = db.File()
        ## record.filename = filename
        ## record.revision = 0
        ## record.directory = True
        ## record.watchpath = _dms.find(db.WatchPath,
        ##                              db.WatchPath.path == watch_path
        ##                              ).one()
        content = False
        delta = False
        file_hash = ''
        file_size = 0
        revision = 0
        directory = True

    else:
        # function 'MOVE'
        revision = record.revision
        content = False
        delta = False
        file_hash = record.hash
        file_size = record.size
        directory = record.directory

        # update record
        old_filename = record.filename
        old_watchpath = record.watchpath.path
        record.filename = filename
        record.watchpath = record.parent.watchpath


        # update all subdirectories and files if this is directory
        # change subfiles / subdirectories in database
        query = _dms.find(db.File,
                          db.File.filename.like(u'%s/%%' % old_filename),
                          db.WatchPath.path == old_watchpath,
                          db.WatchPath.id == db.File.watchpath_id
                          );
        for f in query:
            f.filename = f.filename.replace(old_filename, record.filename, 1)
            f.watchpath = record.watchpath

    parent_name = os.path.dirname(filename)
    parent = _dms.find(db.File,
                       db.File.filename == parent_name,
                       db.File.watchpath_id == db.WatchPath.id,
                       db.WatchPath.path == watch_path
                       ).one()

    # TODO DIRTY HACK
    # Sometimes we first process a file and then the directory
    # containing the file. This will cause record.parent to be NoneType
    # and hence and get an exception and we cannot push the
    # object to the server. If parent is None then push the file
    # back to the queue. Hopefully the directory will be created
    # well its turn comes again.
    if not parent:
        if __debug__:
            dprint("Hey there is no parent, put the item back to queue")
            dprint("parent_name ", parent_name)
            dprint("watch_path ", watch_path)
            dprint(parent)
        hub.database_manager.store.rollback()
        reactor.callLater(3, hub.worker.queue.put, (function, parameters))
        reactor.callLater(util.WORKER_RECALL, hub.worker.work)
        return

    # data to send
    data = {'filename':os.path.basename(filename),
            'revision':revision + 1,
            'data': content,
            'directory':directory,
            'delta':delta,
            'hash':file_hash,
            'size':file_size,
            'parent_id':parent.server_id
            }
    uri = '%s/file/' % hub.config_manager.get_server()
    if record:
        uri += str(record.server_id)
        # hack TODO
        del data['directory']

    uri += util.urlencode(data)
    if content:
        d = hub.rest_client.post_file(uri, file_handler)
    else:
        d = hub.rest_client.post(uri, None)
    d.addCallback(success_cb, record, filename, fullpath, watch_path)
    d.addErrback(failure_cb)
