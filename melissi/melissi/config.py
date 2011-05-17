# standard modules
import ConfigParser
import os

# melissi modules
import dbschema as db

class ConfigManager:
    def __init__(self, hub, config_file):
        self.hub = hub
        self.config_file = config_file
        self.config = ConfigParser.SafeConfigParser()
        self.config.read(config_file)

        # check if first run
        if not self.config.sections():
            # run for the first time
            config_path = os.path.dirname(self.config_file) or "."
            try:
                import socket
                resource = socket.gethostname()
            except:
                resource = 'default'
            self.config.add_section('main')
            self.config.set('main', 'username', '')
            self.config.set('main', 'password', '')
            self.config.set('main', 'host', 'http://')
            self.config.set('main', 'database', 'sqlite:///%s/melissi.db' % config_path)
            self.config.set('main', 'socket', '%s/melissi.sock' % config_path)
            self.config.set('main', 'no-desktop', 'False')
            self.config.set('main', 'desktop-notifications', 'True')
            self.config.set('main', 'new-root-path',
                            '%s' % os.path.expanduser('~'))
            self.config.set('main', 'resource', '%s' % resource)

            self.write_config()

    @property
    def configured(self):
        return self._check_configuration()

    def _check_configuration(self):
        if (self.get_username() == '' or \
            self.get_password() == '' or \
            self.get_server() == ''):
            return False
        return True

    def write_config(self):
        try:
            os.mkdir(os.path.dirname(self.config_file))
        except OSError, error_message:
            if error_message.errno == 17:
                # exists, no worries
                pass

        with open(self.config_file, 'wb') as f:
            os.fchmod(f.fileno(), 0600)
            self.config.write(f)

    def set_desktop_notifications(self, value):
        self.config.set('main', 'desktop-notifications', value)
        self.write_config()

    def get_username(self):
        return self.config.get('main', 'username')

    def set_username(self, username):
        self.config.set('main', 'username', str(username))
        self.write_config()

    def get_password(self):
        return self.config.get('main', 'password')

    def set_password(self, password):
        self.config.set('main', 'password', str(password))
        self.write_config()

    def get_database(self):
        return self.config.get('main', 'database')

    def set_database(self, database):
        self.config.set('main', 'database', str(database))
        self.write_config()

    def get_socket(self):
        return self.config.get('main', 'socket')

    def set_socket(self, socket):
        self.config.set('main', 'socket', str(socket))
        self.write_config()

    def get_server(self):
        return self.config.get('main', 'host')

    def set_server(self, host):
        # error checking
        import re
        if not re.match(r'http(s)?://[^:/]+:\d+', host):
            return -1

        self.config.set('main', 'host', str(host))
        self.write_config()

    def get_watchlist(self):
        record = self.hub.database_manager.store.find(db.WatchPath).one() or False
        if record:
            return record.path
        else:
            return False


    def set_watchlist(self, path):
        record = self.hub.database_manager.store.find(db.WatchPath).one() or False
        path = os.path.abspath(os.path.expanduser(path))

        if record:
            record.path = path
            self.hub.database_manager.commit()
            return True
        else:
            return False

    def get_basedir(self):
        basedir = self.hub.database_manager.store.find(db.Config, db.Config.name == u'basedir').one() or False
        if basedir:
            return int(basedir.value)
        else:
            return -1

    def set_basedir(self, basedir):
        record = self.hub.database_manager.store.find(db.Config, db.Config.name == u'basedir').one() or False
        if record:
            record.value = unicode(basedir)
            self.hub.database_manager.commit()
            return True
        else:
            return False


    def set_timestamp(self, timestamp):
        record = self.hub.database_manager.store.find(db.Config, db.Config.name == u'timestamp').one() or False
        if not record:
            record = db.Config()
            record.name = u'timestamp'
            record.type = u'str'
            self.hub.database_manager.store.add(record)

        record.value = unicode(timestamp)
        self.hub.database_manager.commit()
        return True

    def get_timestamp(self):
        record = self.hub.database_manager.store.find(db.Config, db.Config.name == u'timestamp').one() or False
        if not record:
            return 0
        else:
            return str(record.value)
