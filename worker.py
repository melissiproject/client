#
# This is documentation for worker
#
from twisted.internet import reactor
from twisted.internet import defer

import util
import dbschema as db
# import actions.modify
# import actions.delete
# import actions.update
# import actions.share
from actions import *

if __debug__:
    from Print import dprint

class Worker():
    def __init__(self, hub):
        self.hub = hub
        self._dms = self.hub.database_manager.store
        self.processing = False

    def work(self):
        # TODO: find a better async way
        if self.hub.rest_client.offline:
            return

        try:
            item = self.hub.queue.get()
        except IndexError:
            if self.processing:
                self.processing = False
                self.hub.desktop_tray.set_icon_ok()

            reactor.callLater(1, self.work)
            return

        # only if the item is not in the queue again
        if item not in self.hub.queue:
            self.processing = True
            self.hub.desktop_tray.set_icon_update("Melisi Working")
            # maybe an overkill to call each item
            self.hub.desktop_tray.set_recent_updates()
            self.process_item(item)

    def process_item(self, item):
        # notify tray and stdout
        if __debug__:
            dprint("Worker processing ", item.action_name)

        d = defer.maybeDeferred(item)
        d.addErrback(self._action_failure, item)
        d.addBoth(self._call_worker)

    def _action_failure(self, failure, item):
        # rollback database
        print "rolling back", item
        self.hub.database_manager.rollback()

        try:
            failure.raiseException()

        except WaitItem, e:
            if __debug__:
                dprint("Item %s waits for %s" % (item.pk, e.id))
            self.hub.queue.put_into_waiting_list(e.id, item)

        except RetryLater, e:
            if __debug__:
                dprint("Need to retry later")
            reactor.callLater(e.time, self.hub.queue.put, item)

        except DropItem, e:
            if __debug__:
                dprint("Drop item")
            pass

        except Exception, e:
            dprint("UNEXPECTED Exception ", e, exception=1)
            dprint("Item ", item)
            raise e


        # decide what to do based on error type
        # e.g. if we are retrying or giving up

    def _call_worker(self, result, when=0):
        self.hub.database_manager.commit()
        reactor.callLater(0, self.work)

