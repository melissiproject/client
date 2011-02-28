import json
from twisted.internet import reactor

import util
import dbschema as db

if __debug__:
    from Print import dprint
    
def share(hub, item):
    _dms = hub.database_manager.store
    function, parameters = item
    folder, mode, users = parameters
    filename, watched_path = hub.notify_manager.path_split(folder)

    record = _dms.find(db.File,
                       db.File.filename == filename,
                       db.WatchPath.path == watched_path,
                       db.WatchPath.id == db.File.watchpath_id, 
                       db.File.directory == True
                       ).one() or False
    if record:
        def success_cb(result):
            reactor.callLater(util.WORKER_RECALL, hub.worker.work)

        def failure_cb(error):
            if __debug__:
                dprint("Error setting share: ", error)
            reactor.callLater(util.WORKER_RECALL, hub.worker.work)
            return

        try:
            if mode not in [1,2,3,4]:
                raise ValueError("Invalid mode: '%s'" % mode)
            if not isinstance(users, list):
                raise ValueError("Invalid list: '%s'" % list)
            for user in users:
                if not isinstance(user, unicode) and not isinstance(user, int):
                    raise ValueError("Invalid user '%s'" % user)
        except ValueError, error_message:
            if __debug__:
                dprint(error_message, exception=1)
            reactor.callLater(util.WORKER_RECALL, hub.worker.work)
            return
        
        data = {'mode': mode,
                'users': ','.join(users)
                }
        uri = '%s/share/%s' % (hub.config_manager.get_server(),
                               record.server_id)
        uri += util.urlencode(data)
        d = hub.rest_client.post(uri, json.dumps(data))
        d.addCallback(success_cb)
        d.addErrback(failure_cb)
    else:
        # we don't follow that file, to nothing
        if __debug__:
            dprint("Error: we cannot share a folder that we don't watch",
                   filename,
                   watched_path)
