# standard modules
import json
import inspect
import logging
log = logging.getLogger("melissilogger")

# extra modules
import twisted.internet.defer  as defer

import dbus
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop
DBusGMainLoop(set_as_default=True)

# melissi modules
import dbschema as db
from actions import NotImplementedError, Share


class MelissiService(dbus.service.Object):
    def __init__(self, hub):
        self._hub = hub
        object_path = '/org/melissi/Melissi'
        bus_name = dbus.service.BusName('org.melissi.Melissi', bus=dbus.SessionBus())
        dbus.service.Object.__init__(self, bus_name, object_path)

    @dbus.service.method('org.melissi.Melissi')
    def connect(self):
        self._hub.rest_client.connect()


    @dbus.service.method('org.melissi.Melissi')
    def disconnect(self):
        self._hub.rest_client.disconnect()

    @dbus.service.method('org.melissi.Melissi')
    def check_busy(self):
        return 'Processing: %s, Queue size: %s queued, %s waiting' % (
            self._hub.worker.processing,
            len(self._hub.queue.queue),
            len(self._hub.queue.waiting_list)
            )

    @dbus.service.method('org.melissi.Melissi')
    def register(self, username, password, email):
        return self._hub.rest_client.register(username, password, email)

    @dbus.service.method('org.melissi.Melissi')
    def auth(self, username, password):
        self._hub.config_manager.set_username(username)
        self._hub.config_manager.set_password(password)
        self._hub.config_manager.write_config()
        self._hub.rest_client.disconnect()
        self._hub.rest_client.connect()

    @dbus.service.method('org.melissi.Melissi')
    def add_share(self, path, mode, user):
        # validate and build a Share WorkerAction object
        filename, watched_dir = self._hub.notify_manager.path_split(path)
        self._hub.queue.put(Share(self._hub, filename, watched_dir, mode, user))

    @dbus.service.method('org.melissi.Melissi')
    def delete_user(self):
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

    @dbus.service.method('org.melissi.Melissi')
    def set_host(self, host):
        self._hub.config_manager.set_server(host)
        self._hub.rest_client.disconnect()
        self._hub.rest_client.connect()


    @dbus.service.method('org.melissi.Melissi')
    def list_methods(self):
        methods = []

        for method in dir(self):
            if method[0] == '_':
                # ignore 'hidden' methods
                continue

            elif method in ['Introspect', 'remove_from_connection'] :
                continue

            if inspect.ismethod(self.__getattribute__(method)):
                methods.append(method)

        return ', '.join(methods)
