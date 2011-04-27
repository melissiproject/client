import urllib
import json
import base64

from twisted.internet import reactor
from twisted.web import client
from twisted.web import http_headers
from twisted.internet.defer import Deferred
import twisted.internet.error
import twisted.web.error

import producer
import receiver

from actions import *

if __debug__:
    from Print import dprint

class AuthenticationFailed(Exception):
    pass

class RestClient():
    def __init__(self, hub):
        self.offline = True
        self._hub = hub
        self.connect()

    def online(self):
        return not self.offline

    def disconnect(self):
        self.offline = True
        self._hub.desktop_tray.set_icon_offline()
        self._hub.desktop_tray.set_connect_menu()
        if __debug__:
            dprint("Disconnected")

    def connect(self):
        if self._check_connection():
            self.offline = False
            self._hub.desktop_tray.set_icon_ok()
            self._hub.desktop_tray.set_disconnect_menu()
            self._hub.queue.put(GetUpdates(self._hub))
            reactor.callLater(0, self._hub.worker.work)
        else:
            self.disconnect()

    def _check_connection(self):
        # TODO
        return self._hub.config_manager.configured

    def _get_basic_auth_string(self):
        username = self._hub.config_manager.get_username()
        password = self._hub.config_manager.get_password()

        return 'Basic %s' % \
               base64.encodestring(':'.join((username, password)))[:-1]

    def register(self, username, password, password2, email):
        data = {'username':username,
                'password':password,
                'password2': password2,
                'email':email}
        uri = '%s/api/user/' % self._hub.config_manager.get_server()
        return self._sendRequest('POST', uri, data, auth=False)

    def get(self, uri, data=None, file_handle=None):
        return self._sendRequest('GET', uri, data, file_handle=None)

    def post(self, uri, data=None, file_handle=None):
        return self._sendRequest('POST', uri, data, file_handle)

    def put(self, uri, data=None, file_handle=None):
        return self._sendRequest('PUT', uri, data, file_handle)

    def delete(self, uri):
        return self._sendRequest('DELETE', uri)

    def _sendRequest(self, method, uri, data=None, file_handle=None, auth=True):
        # code from http://marianoiglesias.com.ar/python/file-\
        # uploading-with-multi-part-encoding-using-twisted/
        def finished(bytes):
            if __debug__:
                dprint("Upload DONE: %d" % bytes)

        def progress(current, total):
            if __debug__:
                dprint("Upload PROGRESS: %d out of %d" % (current, total))

        def failure(error):
            if __debug__:
                dprint("Upload ERROR: %s" % error)
                dprint(error, exception=1)
            return error

        def responseDone(data):
            return data

        def responseFail(result):
            """ trap any errors from receiving """
            print "responseFail failure", result.type
            if __debug__:
                dprint(result, exception=1)

            return result

        # receiver
        receiverDeferred = Deferred()
        receiverDeferred.addCallback(responseDone)
        # receiverDeferred.addErrback(responseFail)

        # producer
        producerDeferred = Deferred()
        producerDeferred.addCallback(finished)
        producerDeferred.addErrback(failure)

        myReceiver = receiver.StringReceiver(receiverDeferred)
        headers = http_headers.Headers()
        if auth:
            headers.addRawHeader('Authorization', self._get_basic_auth_string())

        if data or file_handle:
            myProducer = producer.MultiPartProducer(data,
                                                    file_handle,
                                                    producerDeferred)
            headers.addRawHeader('Content-Type',
                                 'multipart/form-data; boundary=%s' % myProducer.boundary)
        else:
            myProducer = None

        agent = client.Agent(reactor)
        request = agent.request(method, uri, headers, myProducer)

        def request_ok(response):
            myReceiver.response.set_code(response.code)

            # workaround when sending a DELETE it seems that
            # connectionLost is never called from some reason also
            # dilverBody does not call dataReceived (because there are
            # to data). Anyway if that's the case, call connection
            # lost manually
            if response.code == 204 and response.length == 0:
                myReceiver.connectionLost(None)
            elif response.code == 401:
                raise AuthenticationFailed()
            else:
                response.deliverBody(myReceiver)

        request.addCallback(request_ok)

        # we pass receiverDeferred into addErrback so it can call its
        # errback for the error to propagate
        request.addErrback(self._connection_failure)
        request.addErrback(receiverDeferred.errback)

        return receiverDeferred

    def _connection_failure(self, failure):
        """ This is a deferred failure """
        try:
            failure.raiseException()

        except (twisted.internet.error.ConnectionRefusedError,
                twisted.internet.error.ConnectionClosed,
                twisted.internet.error.ConnectionLost,
                twisted.internet.error.DNSLookupError,
                twisted.internet.error.TCPTimedOutError,
                twisted.internet.error.TimeoutError), error:

            self.disconnect()
            self._hub.desktop_tray.set_icon_offline("Connection failed")
            reactor.callLater(2, self.connect)

        except AuthenticationFailed, error:
            # TODO is there a way to directly see the error code
            self.disconnect()
            self._hub.desktop_tray.set_icon_error("Authendication failed")
            # TODO pynotify
            if __debug__:
                dprint("Unable to login: Unauthorized message")

        except twisted.internet.error.SSLError:
            self.disconnect()
            self._hub.desktop_tray.set_icon_error("SSLError: You need to change your settings")
            if __debug__:
                dprint("SSL Error while connecting")

        except Exception, error:
            print error

        finally:
            return failure
        # finally:
        #     # call receiver with failure for the error to propagate
        #     # remember that the rest of the callbacks / errbacks are
        #     # tailed to "receiver" and not the current chain
        #     receiver.errback(failure)
