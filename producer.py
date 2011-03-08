# Code from http://github.com/mariano/pyfire/blob/master/pyfire/twistedx/producer.py

import urllib
import os
import random
from string import letters

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

    def __init__(self, data=None, file_handle=None, deferred=None):
        """ Initializes the producer

        files is a file descriptor
        deferred = a deferred

        The procuder performs a seek(0) to the file
        """
        self._file = file_handle
        if self._file:
            self._file_length = self._file_size(self._file)
        else:
            self._file_length = 0

        self._data = data
        self._deferred = deferred

        self.boundary = self._generate_boundary()

        self.head = self._generate_head()
        self.tail = self._generate_tail()

        self.length = self._file_length + len(self.head) + len(self.tail)
        self._sent = 0
        self._paused = False

    def _generate_boundary(self):
        boundary = "------------------------------"
        for i in range(12):
            boundary += random.choice(letters)

        return boundary

    def _generate_tail(self):
        if self.head:
            return  '\r\n--%s--\r\n' % self.boundary
        else:
            return ''

    def _generate_head(self):
        postdata = ""
        if self._data or self._file:
            postdata += '%s\r\n' % self.boundary

            for key, value in self._data.items():
                postdata += 'Content-Disposition: form-data; name="%s"\r\n\r\n' % key
                postdata += '%s\r\n' % value
                postdata += '--%s\r\n' % self.boundary

            if self._file:
                postdata += 'Content-Disposition: form-data; name="content"; filename="content"\r\n'
                postdata += 'Content-Type: application/octet-stream\r\n\r\n'
            else:
                # len('\r\n--%s\r\n' % self.boundary) == 48
                postdata = postdata[:-48]

        return postdata

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
            chunk = ''
            if self._sent < len(self.head):
                chunk = self.head[:self.CHUNK_SIZE]
                self.head = self.head[len(chunk):]

            if len(chunk) < self.CHUNK_SIZE and self._file:
                chunk += self._file.read(self.CHUNK_SIZE - len(chunk))

            if len(chunk) < self.CHUNK_SIZE:
                chunk += self.tail[:self.CHUNK_SIZE - len(chunk)]
                self.tail = self.tail[len(chunk):]

            if len(chunk) == 0:
                done = True
            else:
                self._send_to_consumer(chunk)



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
        block = str(block)

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
