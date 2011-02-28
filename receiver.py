# code from http://github.com/mariano/pyfire/blob/master/pyfire/twistedx/receiver.py

from twisted.internet import protocol
from twisted.web import client

class StringReceiver(protocol.Protocol):
    """ String receiver protocol. To be used in combination
    with producer to upload files in a twisted python way

    """
    buffer = ""

    def __init__(self, deferred=None):
        self._deferred = deferred

    def dataReceived(self, data):
        """ Receives data. We don't expect a lot of data here
        so we store result directly into memory
        """
        self.buffer += data

    def connectionLost(self, reason):
        if self._deferred and reason.check(client.ResponseDone):
            self._deferred.callback(self.buffer)
        else:
            self._deferred.errback(self.buffer)
