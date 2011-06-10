# stardard modules
import logging
log = logging.getLogger("melissilogger")

# extra modules
from twisted.internet import reactor
from twisted.internet.task import LoopingCall

# melissi modules
from actions.updates import GetUpdates, RescanDirectories

class WatchDog(object):
    """

    I make sure that everything is synchronized. If there is objects
    in the waiting queue for too long, I rescan the watched
    directories and fetch a full update

    """

    def __init__(self, hub):
        self._hub = hub
        self._trigger = 0
        self._threshold = 3
        if __debug__:
            self._check_every_seconds = 5
        else:
            self._check_every_seconds = 20

        self._looping_call = LoopingCall(self._watch)
        self._looping_call.start(self._check_every_seconds)

    def set_threshold(self, value, force=False):
        if self._threshold < value:
            self._threshold = value

        return self._threshold

    def _watch(self):
        if not len(self._hub.queue.queue) and len(self._hub.queue.waiting_list):
            if self._trigger < self._threshold:
                self._trigger += 1
                log.log(5, "Watchdog: increasing trigger to %s" % self._trigger)

            elif self._trigger < self._threshold + 1:
                # force rescan directories
                log.debug("Forcing a rescan, due to waiting objects")
                self._trigger += 1
                self._hub.queue.put(RescanDirectories(self._hub))

            elif self._trigger < self._threshold + 2:
                # trigger full update
                log.debug("Forcing a full update, due to waiting objects")
                self._trigger += 1
                self._hub.queue.put(GetUpdates(self._hub, full=True))

            elif self._trigger == self._threshold + 2:
                # failed :(
                #
                # notify user, to clean database and restart,
                # something is really wrong
                log.debug("Failed to solve dependency problem")
                reactor.stop()

        else:
            self._trigger = 0

        log.log(5, "Trigger %s" % self._trigger)
