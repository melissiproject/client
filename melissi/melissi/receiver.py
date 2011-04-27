# code from http://github.com/mariano/pyfire/blob/master/pyfire/twistedx/receiver.py
import tempfile

from twisted.internet import protocol
from twisted.web import client

class APIResponse(object):
    """ An API Response object. """
    def __init__(self):
        self._content = tempfile.NamedTemporaryFile(prefix='melissi-',
                                                    suffix='.tmp')
        self._code = -1

    @property
    def code(self):
        return self._code

    @property
    def content(self):
        return self._content

    def __unicode__(self):
        self._content.seek(0)
        return "Response code: %s\n%s" % (self.code, self._content.read())

    def set_code(self, code):
        self._code = code

class StringReceiver(protocol.Protocol):
    """ String receiver protocol. To be used in combination
    with producer to upload files in a twisted python way

    """
    def __init__(self, deferred=None):
        self._deferred = deferred
        self.response = APIResponse()

    def dataReceived(self, data):
        """ Receives data. We don't expect a lot of data here
        so we store result directly into memory
        """
        self.response.content.write(data)

    def connectionLost(self, reason):
        self.response.content.seek(0)

        if self.response.code >= 200 and self.response.code < 300:
            self._deferred.callback(self.response)
        else:
            self._deferred.errback(self.response)
