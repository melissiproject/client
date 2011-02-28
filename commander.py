from twisted.protocols.basic import LineReceiver
from twisted.internet.protocol import ServerFactory
import twisted.internet.defer  as defer
import json

import dbschema as db

def share(hub, data):
    folder = data["folder"]
    mode = data["mode"]
    users = data["users"]

    # add to queue
    hub.worker.queue.put(('SHARE', (folder, mode,users)))

def auth(hub, data):
    username = data["username"]
    password = data["password"]

    hub.config_manager.set_username(username)
    hub.config_manager.set_password(password)
    hub.rest_client.disconnect()
    hub.rest_client.auth()

def disconnect(hub, data):
    hub.rest_client.disconnect()

def connect(hub, data):
    hub.rest_client.auth()

def check_busy(hub, data):
    return hub.worker.processing

def register(hub, data):
    return hub.rest_client.register(data['username'],
                                    data['email'],
                                    data['password'])

def deleteuser(hub, data):
    def success_cb(result):
        hub.rest_client.disconnect()

        hub.config_manager.set_username('')
        hub.config_manager.set_password('')

        # we should be able to do just a
        # store.remove(db.File)
        try:
            for entry in hub.database_manager.store.find(db.File):
                hub.database_manager.store.remove(entry)
            for entry in hub.database_manager.store.find(db.WatchPath):
                hub.database_manager.store.remove(entry)
            hub.database_manager.store.commit()
        except:
            raise    
                

        return "User deleted"

    def failure_cb(error):
        return "Delete failed with error:", error
        
    d = hub.rest_client.delete('%s/user/%s?delete=yes' %
                               (hub.config_manager.get_server(),
                                hub.config_manager.get_username())
                               )
    d.addCallback(success_cb)
    d.addErrback(failure_cb)
    return d

def sethost(hub, data):
    host = data["host"]
    port = data["port"]

    hub.config_manager.set_server(host, port)
    hub.rest_client.disconnect()
    hub.rest_client.auth()

class FooboxCommandReceiverProtocol(LineReceiver):
    def lineReceived(self, line):
        # deal with the new command
        try:
            data = json.loads(line)
            cmd = data["command"]
        except (ValueError, KeyError):
            if __debug__:
                dprint("COMMANDER: Received invalid json data '%s'" % line)
            self.sendLine("ERROR: Invalid json data")
            self.closeConnection()
            return

        try:
            reply = defer.maybeDeferred(self.factory.commands[cmd], self.factory.hub, data)
        except KeyError:
            if __debug__:
                dprint("COMMANDER: Received unknown command")
            reply = "ERROR: Unknown command"

        def send_result(result):
            if result:
                self.sendLine(str(result))
            self.closeConnection()
        # send_result to be used for both callbacks and errbacks
        reply.addBoth(send_result)

    def closeConnection(self):
        self.transport.doWrite()
        self.transport.loseConnection()
        

class FooboxCommandReceiver(ServerFactory):
    protocol = FooboxCommandReceiverProtocol

    def __init__(self, hub):
        self.hub = hub
        self.commands = {'SHARE':share,
                         'AUTH':auth,
                         'DISCONNECT':disconnect,
                         'CONNECT':connect,
                         'CHECKBUSY':check_busy,
                         'REGISTER':register,
                         'SETHOST':sethost,
                         'DELETEUSER':deleteuser
                         }
