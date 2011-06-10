#
#

# standard modules
import json
import tempfile
import os
import shutil
from datetime import datetime, timedelta
from os.path import join as pathjoin

# extra modules
from twisted.internet import reactor
import twisted.internet.defer as defer

# melissi modules
import melissi.dbschema as db
import melissi.util

class NotImplementedError(Exception):
    """
    Use when construting non-standalone classes. The functions that
    /need/ to be overloaded by classes that inherit should raise a
    NotImplementedError

    """
    pass

class RetryLater(Exception):
    """
    Raise when an action should be executed again.

    For example when communication with server fails due to network
    error, we need to retry later. Optional parameter `time` (default
    value: 10)

    """
    def __init__(self, error_message=None, time=10):
        self.time = time
        self.error_message = error_message

    def __str__(self):
        return str(self.error_message)

class DropItem(Exception):
    """
    Raise when an action should to be ignored.

    When an action is called but nothing needs to be done, prefer
    raising a DropItem exception instead of just returning from that
    function.

    For example when a ModifyFile action is executed which was
    triggered from a UpdateDroplet action, the first probably does not
    need to perform any action because the file is already up to
    date. In that case raise a DropItem

    """

    pass

class WaitItem(Exception):
    """
    Raise when an actions should wait for another action.

    When an actions depends on another action, raise a WaitItem with
    parameters the unique_id of the action to wait for. Your action
    will be added to the Queue.waiting_list and will be put in the
    normal queue again, when the action it wait for successfully
    finishes execution.

    For example when a DropletUpdate want to write into a Directory
    not yet created from a CellUpdate, raise a WaitItem exception with
    `id`, the id of the Cell.

    """
    def __init__(self, id):
        super(WaitItem, self).__init__()
        self.id = id

class WorkerAction(object):
    def __init__(self, hub):
        self._hub = hub
        self._dms = hub.database_manager.store

        self._action_taken = False

    @property
    def action_name(self):
        if self.unique_id:
            return '%s [%s]' % (self.__class__.__name__,
                                self.unique_id)
        else:
            return self.__class__.__name__

    @property
    def unique_id(self):
        return "'unknown' (type: %s)" % self.__class__.__name__

    def _send_notification(self):
        return

    def _write_log(self):
        return

    def _log(self, *args, **kwargs):
        # maybe called in a deffered list, with a result
        # which we can safelly ignore
        self._write_log()

        # clear entries older than a month\
        a_month_ago = datetime.now() - timedelta(days=30)
        map(lambda x: self._dms.remove(x), self._dms.find(db.LogEntry,
                                                          db.LogEntry.timestamp < a_month_ago)
            )

    def _notify(self, *args, **kwargs):
        # maybe called in a deffered list, with a result
        # which we can safelly ignore
        if self._action_taken:
            self._send_notification()

    def _fetch_file_record(self, **kwargs):
        # keys format:
        # File__filename is converted to db.File.filename
        query = self._dms.find(db.File)
        query = query.find(db.WatchPath.id == db.File.watchpath_id)

        for key, value in kwargs.iteritems():
            attr = reduce(lambda x, y: getattr(x, y),
                          [db] + key.split("__")
                          )

            query = query.find(attr == value)

        return query.one() or False

    def _wakeup_waiting(self, result):
        self._hub.queue.wake_up(self.unique_id)

    def _execute(self):
        raise NotImplementedError("WorkerAction not implemented error")

    def __call__(self):
        # TODO maybe we should handle DropItems here since we need to
        # call _wakeup_waiting as well

        d = defer.maybeDeferred(self._execute)
        d.addCallback(self._notify)
        d.addCallback(self._log)
        d.addCallback(self._wakeup_waiting)
        return d

    def __unicode__(self):
        return str(self.unique_id)

    def __str__(self):
        return str(self.unique_id)

from modify import *
from updates import *
from delete import *
from move import *
from notify import *
from share import *
from fs import *
