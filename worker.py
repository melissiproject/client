from twisted.internet import reactor

import util
import dbschema as db
import actions.modify
import actions.delete
import actions.update
import actions.share

if __debug__:
    from Print import dprint

class Worker():
    def __init__(self, hub): 
        self.hub = hub
        self._dms = self.hub.database_manager.store
        self.queue = util.queue()
        self.processing = False

        self._actions = {'UPDATE':actions.update.update,
                         'DELETE':actions.delete.delete,
                         'MOVE':actions.modify.modify,
                         'MODIFY':actions.modify.modify,
                         'CREATEDIR':actions.modify.modify,
                         'DELETEDIR':actions.delete.delete,
                         'SHARE':actions.share.share,
                         'GETUPDATES':actions.update.get_updates
                         }
        
    def work(self):
        # TODO: find a better async way
        if self.hub.rest_client.offline:
            return

        try:
            item = self.queue.get()
        except IndexError:
            if self.processing:
                self.processing = False
                self.hub.desktop_tray.set_icon_ok()
            reactor.callLater(1, self.work)
            return
            
        # only if the item is not in the queue again
        if item not in self.queue:
            self.processing = True
            self.hub.desktop_tray.set_icon_update("Foobox Working")
            # maybe an overkill to call each item
            self.hub.desktop_tray.set_recent_updates()
            self.process_item(item)
        else:
            reactor.callLater(0, self.work)

    def process_item(self, item):
        function, parameters = item
        # notify tray and stdout
        if __debug__:
            dprint("Worker processing", item)
 
        try:
            self._actions[function](self.hub, item)
        except KeyError, error_message:
            # invalid action given, just ignore
            if __debug__:
                dprint("Invalid action '%s' given" % function)
            reactor.callLater(0, self.work)
