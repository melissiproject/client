# Contains
# MoveFile
# MoveDirectory

class MoveFile(WorkerAction):
    def __init__(self, hub, filename, watchpath):
        super(MoveFile, self).__init__(hub)
        self._action_name = "MoveFile"

        self.filename = filename
        self.watchpath = watchpath
        self._hub = hub
        self._dm = self._hub.database_manager

    def _execute(self):
        pass

class MoveDir(WorkerAction):
    def __init__(self, hub, dirname, watchpath):
        super(MoveDir, self).__init__(hub)
        self._action_name = "MoveDir"

        self.dirname = dirname
        self.watchpath = watchpath
        self._hub = hub
        self._dm = self._hub.database_manager

    def _execute(self):
        pass
