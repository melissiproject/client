import urllib
import json

from twisted.internet import reactor
from twisted.web import client
from twisted.web import http_headers
from twisted.internet.defer import Deferred

import producer
import receiver

if __debug__:
    from Print import dprint

class RestClient():
    def __init__(self, hub): 
        self.cookie_jar = {}
        self.offline = True 
        self.hub = hub
        reactor.callLater(0, self.auth)

    def online(self):
        return not self.offline

    def disconnect(self):
        self.cookie_jar = {}
        self.offline = True
        self.hub.desktop_tray.set_icon_offline()
        self.hub.desktop_tray.set_connect_menu()
        if __debug__:
            dprint("Disconnected")

    def auth(self):
        def success_cb(result):
            if __debug__:
                dprint('Authentication success', result)
            self.offline = False
            self.hub.desktop_tray.set_icon_ok()
            self.hub.desktop_tray.set_disconnect_menu()
            self.hub.worker.queue.put(('GETUPDATES', None))
            reactor.callLater(0, self.hub.worker.work)

        ## def failure_cb(result):
        ##     self.hub.desktop_tray.set_icon_error("Authentication Error: Check your username and password")
        ##     if __debug__:
        ##         dprint('Authentication failure', result)

        # set details
        uri = '%s/auth/login' % self.hub.config_manager.get_server()
        d = self.post_form(uri,
                           username=self.hub.config_manager.get_username(),
                           password=self.hub.config_manager.get_password()
                           )
        d.addCallback(success_cb)
        ## d.addErrback(failure_cb)
        return d

    def register(self, username, password, email):
        data = {'username':username,
                'password':password,
                'email':email}
        data = json.dumps(data)
        uri = '%s/user' % self.hub.config_manager.get_server()
        
        return self.post(uri, data, force=True)

    def get(self, uri, data=None):
        return self._sendRequest('GET', uri, data)

    def post_form(self, uri, **kwargs):
        postData = urllib.urlencode(kwargs)
        mimeType = 'application/x-www-form-urlencoded'
        return self._sendRequest('POST', uri, postData, mimeType, force=True)

    def post(self, uri, data, force=False): 
        mimeType = 'application/octet-stream'
        return self._sendRequest('POST', uri, data, mimeType, force=force)

    def post_file(self, uri, file):
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

            self.hub.database_manager.store.rollback()
            reactor.callLater(0, self.hub.worker.work)
            
        def responseDone(data):
            return data

        # receiver
        receiverDeferred = Deferred()
        receiverDeferred.addCallback(responseDone)

        # producer
        producerDeferred = Deferred()
        producerDeferred.addCallback(finished)
        producerDeferred.addErrback(failure)
        
        myProducer = producer.MultiPartProducer(file, producerDeferred)
        myReceiver = receiver.StringReceiver(receiverDeferred)
        headers = http_headers.Headers()

        cookieData = []
        for cookie, cookval in self.cookie_jar.items():
             cookieData.append('%s=%s' % (cookie, cookval))
        if cookieData:
            headers.addRawHeader('Cookie', '; '.join(cookieData))

        agent = client.Agent(reactor)
        request = agent.request('POST', uri, headers, myProducer)
        request.addErrback(self.connection_error)
        request.addCallback(lambda response: response.deliverBody(myReceiver))

        return receiverDeferred

    def put(self, uri, data):
        mimeType = 'application/octet-stream'
        return self._sendRequest('PUT', uri, data, mimeType)

    def delete(self, uri, data=None):
        return self._sendRequest('DELETE', uri, data)

    def get_file(self, uri, file, data=None):
        headers = {}

        d = client.downloadPage(uri, file, method='GET', headers=headers, postdata=data, cookies=self.cookie_jar)
        d.addErrback(self.connection_error)
        return d

    def _sendRequest(self, method, uri, data='', mimeType=None, force=False):
        if not force and self.offline:
            return None

        headers = {}
        if mimeType:
            headers['Content-Type'] = mimeType
        d = client.getPage(uri,
                           method=method,
                           postdata=data,
                           headers=headers,
                           cookies=self.cookie_jar)
        d.addErrback(self.connection_error)
        return d

    def connection_error(self, result):
        import twisted.internet.error
        import twisted.web.error
        if result.type in (twisted.internet.error.ConnectionRefusedError,
                           twisted.internet.error.ConnectionClosed,
                           twisted.internet.error.ConnectionLost,
                           twisted.internet.error.DNSLookupError,
                           twisted.internet.error.TCPTimedOutError,
                           twisted.internet.error.TimeoutError):
            self.disconnect()
            self.hub.desktop_tray.set_icon_offline("Connection error: Check your internet connection status")
            reactor.callLater(2, self.auth)
        elif result.type == twisted.web.error.Error:
            # TODO is there a way to directly see the error code
            if result.getErrorMessage().startswith("401"):
                self.disconnect()
                self.hub.desktop_tray.set_icon_error("Authendication failed: Check your username and password")
                # TODO pynotify
                if __debug__:
                    dprint("Unable to login: Unauthorized message")
        elif result.type == twisted.internet.error.SSLError:
            self.disconnect()
            self.hub.desktop_tray.set_icon_error("SSLError: You need to change your settings")
            if __debug__:
                dprint("SSL Error while connecting")

        # we don't handle this, move forward
        return result
