# standard modules
import json
import logging
log = logging.getLogger("melissilogger")

# extra modules
from twisted.protocols.basic import LineReceiver
from twisted.internet.protocol import ServerFactory
import twisted.internet.defer  as defer

# melissi modules
import dbschema as db
from actions import NotImplementedError, Share

class CommanderAction(object):
    def __init__(self, hub, command):
        self._hub = hub
        self._command = command

    def __call__(self):
        raise NotImplementedError

class CommanderShare(CommanderAction):
    def __init__(self, hub, command, path, mode, user):
        super(CommanderShare, self).__init__(hub, command)
        self.path = path
        self.mode = mode
        self.user = user

    def __call__(self):
        # validate and build a Share WorkerAction object
        filename, watched_dir = self._hub.notify_manager.path_split(self.path)
        self._hub.queue.put(Share(self._hub, filename, watched_dir, self.mode, self.user))

class CommanderAuth(CommanderAction):
    def __init__(self, hub, command, username, password):
        super(CommanderAuth, self).__init__(hub, command)
        self.username = username
        self.password = password

    def __call__(self):
        self._hub.config_manager.set_username(self.username)
        self._hub.config_manager.set_password(self.password)
        self._hub.config_manager.write_config()
        self._hub.rest_client.disconnect()
        self._hub.rest_client.connect()

class CommanderDisconnect(CommanderAction):
    def __init__(self, hub, command):
        super(CommanderDisconnect, self).__init__(hub, command)

    def __call__(self):
        self._hub.rest_client.disconnect()

class CommanderConnect(CommanderAction):
    def __init__(self, hub, command):
        super(CommanderConnect, self).__init__(hub, command)

    def __call__(self):
        self._hub.rest_client.connect()

class CommanderCheckBusy(CommanderAction):
    def __init__(self, hub, command):
        super(CommanderCheckBusy, self).__init__(hub, command)

    def __call__(self):
        return 'Processing: %s, Queue size: %s queued, %s waiting' % (
            self._hub.worker.processing,
            len(self._hub.queue.queue),
            len(self._hub.queue.waiting_list)
            )

class CommanderRegister(CommanderAction):
    def __init__(self, hub, command, username, password, email):
        super(CommanderRegister, self).__init__(hub, command)
        self.username = username
        self.password = password
        self.email = email

    def __call__(self):
        return self._hub.rest_client.register(self.username,
                                              self.password,
                                              self.email
                                              )

class CommanderDeleteUser(CommanderAction):
    def __init__(self, hub, command):
        super(CommanderDeleteUser, self).__init__(hub, command)

    def __call__(self):
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

        d = hub.rest_client.delete('%s/user/%s' %
                                   (hub.config_manager.get_server(),
                                    hub.config_manager.get_username())
                                   )
        d.addCallback(success_cb)
        d.addErrback(failure_cb)

        return d

class CommanderSetHost(CommanderAction):
    def __init__(self, hub, command, host):
        super(CommanderSetHost, self).__init__(hub, command)
        self.host = host

    def __call__(self):
        self._hub.config_manager.set_server(self.host)
        self._hub.rest_client.disconnect()
        self._hub.rest_client.connect()


class FooboxCommandReceiverProtocol(LineReceiver):
    def lineReceived(self, line):
        # deal with the new command
        try:
            data = json.loads(line)
            cmd = data["command"]
        except (ValueError, KeyError):
            log.debug("COMMANDER: Received invalid json data '%s'" % line)
            self.sendLine("ERROR: Invalid json data")
            self.closeConnection()
            return

        try:
            reply = defer.maybeDeferred(self.factory.commands[cmd](self.factory.hub, **data))
        except KeyError:
            log.debug("COMMANDER: Received unknown command")
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
        self.commands = {'SHARE':CommanderShare,
                         'AUTH':CommanderAuth,
                         'DISCONNECT':CommanderDisconnect,
                         'CONNECT':CommanderConnect,
                         'CHECKBUSY':CommanderCheckBusy,
                         'REGISTER':CommanderRegister,
                         'SETHOST':CommanderSetHost,
                         'DELETEUSER':CommanderDeleteUser,
                         }
