import json
import shutil
import os
from os.path import join as pathjoin
from twisted.internet import reactor

import util
import dbschema as db

if __debug__:
    from Print import dprint

def delete(hub, item):
    _dms = hub.database_manager.store
    function, parameters = item
    filename, watched_path = parameters
    record = _dms.find(db.File,
                       db.File.filename == filename,
                       db.WatchPath.path == watched_path,
                       db.WatchPath.id == db.File.watchpath_id
                       ).one() or False

    # helper functions start
    def success_cb(result):
        reactor.callLater(util.WORKER_RECALL, hub.worker.work)
        
    def failure_cb(error):
        if __debug__:
            dprint("An error occured while deleting ", error)
        reactor.callLater(util.WORKER_RECALL, hub.worker.work)

    # helper functions end

    if not record:
        # file not watched, ignoring
        reactor.callLater(util.WORKER_RECALL, hub.worker.work)
        return

    # delete all children
    for child in _dms.find(db.File,
                           db.File.filename.like(u'%s/%%' % record.filename),
                           db.WatchPath.path == watched_path,
                           db.WatchPath.id == db.File.watchpath_id
                           ):
        _dms.remove(child)
    # delete self
    _dms.remove(record)
    hub.database_manager.commit()

    # delete from filesystem
    # required when deleting recursivelly folders
    fullpath = pathjoin(watched_path, record.filename)
    try:
        shutil.rmtree(fullpath)
    except OSError, error_message:
        if error_message.errno == 20:
            # this is a file not a directory
            try:
                os.unlink(fullpath)
            except OSError:
                # ah, ignore
                pass
        
    # data to send
    data = {'delete': True}
    uri = '%s/file/%s' % (hub.config_manager.get_server(),
                                 record.server_id)
    uri += util.urlencode(data)
    d = hub.rest_client.delete(uri)
    d.addCallback(success_cb)
    d.addErrback(failure_cb)
