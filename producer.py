# Code from http://github.com/mariano/pyfire/blob/master/pyfire/twistedx/producer.py

import urllib
import os

from twisted.internet import defer
from twisted.protocols import basic
from twisted.web import iweb
from zope.interface import implements

import librsync

class MultiPartProducer():
    """ A producer that sends files and parameters as a multi part request

    lots of code from http://github.com/mariano/pyfire/blob/master/pyfire/twistedx/producer.py

    """
    implements(iweb.IBodyProducer)
    CHUNK_SIZE = 2**14

    def __init__(self, handle, deferred=None):
        """ Initializes the producer

        files is a file descriptor
        deferred = a deferred

        The procuder performs a seek(0) to the file
        """
        self._file = handle
        self._file_length = self._file_size(self._file)
        self._deferred = deferred
        self.length = self._file_length
        self._sent = 0
        self._paused = False

    def startProducing(self, consumer):
        """ Starts producing """
        self._consumer = consumer
        self._current_deferred = defer.Deferred()

        result = self._produce()
        if result:
            return result

        return self._current_deferred

    def resumeProducing(self):
        """ Resume producing. """
        self._paused = False
        return self._produce()

    def pauseProducing(self):
        """ Pause producing

        self._paused is used in self._produce()
        """
        self._paused = True

    def stopProducing(self):
        """ Stop producing

        Will cleanup if finish and calls an errback if we haven't finished
        sending all the data
        """
        self._finish(True)
        if self._deferred and self._sent < self.length:
            error_message = "Consumer aksed to stop procuding (%d sent out of %d)" %\
                            (self._sent, self.length)
            self._deferred.errback(Exception(error_message))

    def _produce(self):
        """ Send the files """
        if self._paused:
            return

        done = False
        while not done and not self._paused:
            self._file_sent = 0
            chunk = self._file.read(self.CHUNK_SIZE)
            if chunk:
                self._send_to_consumer(chunk)
                self._file_sent += len(chunk)

            if not chunk or self._file_sent == self._file_length:
                done = True

        if done:
            self._finish()
            return defer.succeed(None)

    def _finish(self, forced=False):
        """ Cleans up """
        if self._current_deferred:
            self._current_deferred.callback(self._sent)
            self._current_deferred = None

    def _send_to_consumer(self, block):
        """ Writes to consumer, counts bytes and calls callback """
        self._consumer.write(block)
        self._sent += len(block)

    def _file_size(self, handle):
        """ Calculates file size """

        if isinstance(handle, file):
            handle.seek(0)
            size = os.fstat(handle.fileno()).st_size
            handle.seek(0)
        elif isinstance(handle, librsync.DeltaFile):
            # TODO
            # I don't like this way of calculating.
            # there should be a more elegant one
            size = 0
            while True:
                line = handle.read(4096)
                if not line: break
                size += len(line)

            # DeltaFiles does not support seek,
            # so basically with reset() I'm creating
            # the file again. Since librsync patches
            # on the fly (?) there is practically
            # no overhead into recreating
            handle.reset()

        return size
