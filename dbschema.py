from storm.locals import *

if __debug__:
    from Print import dprint

SCHEMA_FILE = '''CREATE TABLE file (id TEXT PRIMARY KEY,
                                    filename TEXT,
                                    hash TEXT,
                                    revision INTERGER,
                                    parent_id TEXT,
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

SCHEMA_VERSION = 1

class File(object):
    __storm_table__ = "file"
    id = Unicode(primary=True)
    filename = Unicode()
    hash = Unicode()
    revision = Int()
    parent_id = Unicode()
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

File.watchpath = Reference(File.watchpath_id, WatchPath.id)
