#
#
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
    def __init__(self, time=10):
        self.time = time

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

    @property
    def action_name(self):
        if self.unique_id:
            return '%s [%s]' % (self.__class__.__name__,
                                self.unique_id)
        else:
            return self.__class__.__name__

    @property
    def unique_id(self):
        return False

    def _wakeup_waiting(self, result):
        self._hub.queue.wake_up(self.unique_id)

    def _execute(self):
        raise NotImplementedError("WorkerAction not implemented error")

    def __call__(self):
        if __debug__:
            dprint("Executing ", self.action_name)

        # TODO maybe we should handle DropItems here since we need to
        # call _wakeup_waiting as well

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
from move import *
