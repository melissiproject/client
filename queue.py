if __debug__:
    from twisted.internet import reactor
    from Print import dprint
class Queue(object):
    """ Simple queue class, we don't care if it is thread safe
    since we run in single thread twisted, right? """

    def __init__(self, hub):
        from collections import deque
        self.queue = deque()
        self.waiting_list = {}
        self.hub = hub

        if __debug__:
            def report():
                print "Queue size: %s queued, %s waiting" % (len(self.queue), len(self.waiting_list))
                reactor.callLater(3, report)

            reactor.callLater(0, report)

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
        print waiting_id
        try:
            self.waiting_list[waiting_id].append(item)
        except KeyError:
            self.waiting_list[waiting_id] = [item]

    def wake_up(self, waiting_id):
        if waiting_id in self.waiting_list:
            for item in self.waiting_list[waiting_id]:
                print "Waking up ", item
                self.put(item)

            del(self.waiting_list[waiting_id])
