# standard modules
from collections import deque
import logging
log = logging.getLogger("melissilogger")

# melissi. modules
from actions import GetUpdates, CreateDir, MoveDir

if log.level <= logging.DEBUG:
    from twisted.internet import reactor

class Queue(object):
    """ Simple Queue Service.

    Provides queues for actions to be executed asap, for actions
    waiting for other actions and for desktop notifications

    """

    def __init__(self, hub):
        self.priority_queue = deque()
        self.queue = deque()
        self._notifications = []
        self.waiting_list = {}
        self._hub = hub

        if __debug__:
            def report():
                log.log(5, "Queue size: %s queued, %s waiting" %\
                        (len(self.queue) + len(self.priority_queue),
                         len(self.waiting_list)
                         )
                        )

                reactor.callLater(3, report)

            reactor.callWhenRunning(report)

    def get(self):
        try:
            return self.priority_queue.popleft()
        except IndexError:
            return self.queue.popleft()

    def put(self, item):
        if item in self.priority_queue or item in self.queue:
            log.debug("Dropping item already in queue")
            return

        if isinstance(item, CreateDir) or \
           isinstance(item, MoveDir):
            # place in the top of the queue
            self.priority_queue.append(item)

        else:
            # allow only one GetUpdates into queue
            if isinstance(item, GetUpdates):
                for i in self.queue:
                    if isinstance(i, GetUpdates):
                        log.debug("Dropping duplicate GetUpdates")
                        return

            self.queue.append(item)

    def clear_all(self):
        self.priority_queue = deque()
        self.queue = deque()
        self._notifications = []
        self.waiting_list = {}

    def __contains__(self, item):
        if item in self.queue or item in self.priority_queue:
            return True
        else:
            return False

    def put_into_waiting_list(self, waiting_id, item):
        try:
            self.waiting_list[waiting_id].append(item)
        except KeyError:
            self.waiting_list[waiting_id] = [item]

    def wake_up(self, waiting_id):
        if waiting_id in self.waiting_list:
            for item in self.waiting_list[waiting_id]:
                log.log(5, "Waking up %s" % item)
                self.put(item)

            del(self.waiting_list[waiting_id])

    def put_into_notification_list(self, name, filepath, dirpath, owner, verb):
        """ owner is a dictionary with username, email, name """
        self._notifications.append({'name': name,
                                    'filepath': filepath,
                                    'dirpath': dirpath,
                                    'owner': owner,
                                    'verb': verb
                                    })

    def pop_notification_list(self):
        tmp = self._notifications[:]
        self._notifications = []
        return tmp
