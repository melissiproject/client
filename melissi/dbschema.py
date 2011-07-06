# extra modules
from storm.locals import *

# melissi modules
SCHEMA_FILE = '''CREATE TABLE file (id INTEGER PRIMARY KEY,
                                    filename TEXT,
                                    hash TEXT,
                                    revision INTERGER,
                                    parent_id INTERGER,
                                    modified DATETIME,
                                    directory BOOL,
                                    watchpath_id INTEGER,
                                    signature BLOB
                                    );'''
SCHEMA_WATCHPATH = '''CREATE TABLE watchpath (id INTEGER PRIMARY KEY,
                                              path TEXT
                                              );'''
SCHEMA_CONFIG = '''CREATE TABLE config (name TEXT PRIMARY KEY,
                                        type INTEGER,
                                        value TEXT
                                        );'''

SCHEMA_LOG = '''CREATE TABLE log (id INTEGER PRIMARY KEY,
                                  timestamp DATETIME,
                                  first_name TEXT,
                                  last_name TEXT,
                                  username TEXT,
                                  email TEXT,
                                  action TEXT,
                                  extra TEXT,
                                  file_id INTEGER
                                  );'''

SCHEMA_VERSION = 1

class File(object):
    __storm_table__ = "file"
    id = Int(primary=True)
    filename = Unicode()
    hash = Unicode()
    revision = Int()
    parent_id = Int()
    parent = Reference(parent_id, id)
    modified = DateTime()
    directory = Bool(default=False)
    watchpath_id = Int()
    signature = Pickle()

class WatchPath(object):
    __storm_table__ = "watchpath"
    id = Int(primary=True)
    path = Unicode()
    files = ReferenceSet(id, File.watchpath_id)

class Config(object):
    __storm_table__ = "config"
    name = Unicode(primary = True)
    type = Unicode()
    value = Unicode()

    def __repr__(self):
        return self.value

class LogEntry(object):
    __storm_table__ = "log"
    id = Int(primary=True)
    timestamp = DateTime()
    first_name = Unicode()
    last_name = Unicode()
    username = Unicode()
    email = Unicode()
    action = Unicode()
    extra = Unicode()
    file_id = Int()
    file = Reference(file_id, File.id)

File.watchpath = Reference(File.watchpath_id, WatchPath.id)
