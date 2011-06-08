# melissi modules
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

    def clear_all(self):
        self.store.execute("DELETE FROM file")

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

        self.commit()


