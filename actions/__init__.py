import json
import tempfile
import os
from datetime import datetime
from os.path import join as pathjoin
import shutil

from twisted.internet import reactor
import twisted.internet.defer as defer

import dbschema as db
import util

if __debug__:
    from Print import dprint


class NotImplementedError(Exception):
    pass

class RetryLater(Exception):
    def __init__(self, time=10):
        self.time = time

class DropItem(Exception):
    pass

class WaitItem(Exception):
    def __init__(self, id):
        super(WaitItem, self).__init__()
        self.id = id

class WorkerAction(object):
    def __init__(self, hub):
        self._action_name = "Worker Action"
        self._hub = hub

    @property
    def unique_id(self):
        return False

    @property
    def action_name(self):
        if self.unique_id:
            return "%s %s" % (self._action_name, self.unique_id)
        else:
            return self._action_name

    def _wakeup_waiting(self, result):
        self._hub.queue.wake_up(self.unique_id)

    def _execute(self):
        raise NotImplementedError("foo")

    def __call__(self):
        if __debug__:
            dprint("Executing ", self.action_name)

        d = defer.maybeDeferred(self._execute)
        d.addCallback(self._wakeup_waiting)
        return d

    def __unicode__(self):
        return str(self.unique_id)

    def __str__(self):
        return str(self.unique_id)

from modify import *
from updates import *
from delete import *
