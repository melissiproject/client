from dbschema import *

class DatabaseManager():
    def __init__(self, hub, database_file):
        self.hub = hub
        self.database_file = database_file
        self.connect_db()

    def connect_db(self):
        # check if database exists
        self.database = create_database(self.database_file)
        self.store = Store(self.database)

        # if database is new, we have to create schema
        self._check_schema()

    def _check_schema(self):
        try:
            version = self.store.find(Config, Config.name == u'version').one()
            if version < SCHEMA_VERSION:
                self._upgrade_schema()
        except:
            self._create_schema()

        return SCHEMA_VERSION


    def _upgrade_schema(self):
        # TODO
        store.commit()
        return True

    def commit(self):
        self.store.commit()

    def rollback(self):
        self.store.rollback()

    def _create_schema(self):
        self.store.execute(SCHEMA_FILE)
        self.store.execute(SCHEMA_WATCHPATH)
        self.store.execute(SCHEMA_CONFIG)
        self.store.execute(SCHEMA_LOG)

        version = Config()
        version.name = u'version'
        version.type = u'int'
        version.value = u'1'
        self.store.add(version)

        # TODO debug
        ## host = Config()
        ## host.name = u'host'
        ## host.type = u'str'
        ## host.value = u'localhost'
        ## self.store.add(host)

        ## port = Config()
        ## port.name = u'port'
        ## port.type = u'int'
        ## port.value = u'8000'
        ## self.store.add(port)

        ## username = Config()
        ## username.name = u'username'
        ## username.type = u'str'
        ## username.value = u'mpetzas'
        ## self.store.add(username)

        ## password = Config()
        ## password.name = u'password'
        ## password.type = u'str'
        ## password.value = u'123'
        ## self.store.add(password)

        ## watchpath = Config()
        ## watchpath.name = u'watchpath'
        ## watchpath.type = u'str'
        ## watchpath.value = u'./foobox'
        ## self.store.add(watchpath)

        ## timestamp = Config()
        ## timestamp.name = u'timestamp'
        ## timestamp.type = u'str'
        ## timestamp.value = u'0'
        ## self.store.add(timestamp)

        ## timestamp = Config()
        ## timestamp.name = u'basedir'
        ## timestamp.type = u'str'
        ## timestamp.value = u'-1'
        ## self.store.add(timestamp)

        ## record = File()
        ## record.server_id = 1
        ## record.filename = u''
        ## record.directory = True
        ## self.store.add(record)


        self.commit()


