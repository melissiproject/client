# melissi. modules
from actions import GetUpdates
if __debug__:
    from twisted.internet import reactor
    from Print import dprint

class Queue(object):
    """ Simple Queue Service.

    Provides queues for actions to be executed asap, for actions
    waiting for other actions and for desktop notifications

    """

    def __init__(self, hub):
        from collections import deque
        self.queue = deque()
        self._notifications = []
        self.waiting_list = {}
        self._hub = hub

        if __debug__:
            def report():
                print "Queue size: %s queued, %s waiting" % (len(self.queue), len(self.waiting_list))
                reactor.callLater(3, report)

            reactor.callWhenRunning(report)

    def get(self):
        return self.queue.popleft()

    def put(self, item):
        self.queue.append(item)

    def __contains__(self, item):
        if item in self.queue:
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
                if __debug__:
                    dprint("Waking up %s" % item)
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
