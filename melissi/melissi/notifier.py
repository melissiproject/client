# standard modules
import os
import sys
from os.path import join as pathjoin

# extra modules
from twisted.internet import abstract, reactor
import pyinotify

# melissi modules
import util
import dbschema as db
from actions import *
if __debug__:
    from Print import dprint

class HandleEvents(pyinotify.ProcessEvent):
    def __init__(self, manager):
        pyinotify.ProcessEvent.__init__(self)
        self.manager = manager

    def checkFile(self, event):
        # TODO: check if we are the ones to open the file
        # really needed? we open read only anyway...
        filename = event.pathname

        # check if directory
        if event.dir:
            return False

        # we deleted we don't have to do further checks
        # 0x200 is pyinotify mask of deletion
        if event.mask == 0x200:
            return True

        # check if we can read the file
        if not os.access(event.pathname, os.R_OK):
            #print "Unreadable!", fullpath
            return False

        # # check if the file is hidden
        # if event.name[0] == ".":
        #     #print "Hidden", fullpath
        #     return False

        # # check if the file is a backup
        # if event.name[-1] == "~":
        #     #print "Backup", fullpath
        #     return False

        return True

    def process_IN_CREATE(self, event):
        # we *do* have to do that although we use rec=True
        if event.dir:
            try:
                path = unicode(event.pathname)
            except UnicodeDecodeError, error_message:
                if __debug__:
                    dprint("Ignore file [%s]: %s" % (event.pathname,
                                                     error_message)
                           )
                return

            f, w = self.manager.path_split(path)
            self.manager.add_to_queue(CreateDir(self.manager.hub, f, w),
                                      pathjoin(w,f)
                                      )
            self.manager.add_watch(path)

    def process_IN_OPEN(self, event):
        if self.checkFile(event):
            # add to dictionary
            self.manager.add_to_file_list(event)

    def process_IN_CLOSE_NOWRITE(self, event):
        if self.checkFile(event):
            self.manager.remove_from_file_list(event)

    def process_IN_CLOSE_WRITE(self, event):
        if self.checkFile(event):
            # remove from dictionary
            self.manager.remove_from_file_list(event)

            try:
                path = unicode(event.pathname)
            except UnicodeDecodeError, error_message:
                if __debug__:
                    dprint("Ignore file [%s]: %s" % (event.pathname,
                                                     error_message)
                           )
                return

            f, w = self.manager.path_split(path)
            self.manager.add_to_queue(ModifyFile(self.manager.hub, f, w),
                                      pathjoin(w,f)
                                      )

    def process_IN_DELETE(self, event):
        # TODO when delete dir what happens with the files?
        try:
            path = unicode(event.pathname)
        except UnicodeDecodeError, error_message:
            if __debug__:
                dprint("Ignore file [%s]: %s" % (event.pathname,
                                                 error_message)
                       )
            return

        f, w = self.manager.path_split(path)
        if event.dir:
            self.manager.add_to_queue(DeleteDir(self.manager.hub, f, w),
                                      pathjoin(w,f)
                                      )
        elif self.checkFile(event):
            self.manager.add_to_queue(DeleteFile(self.manager.hub, f, w),
                                      pathjoin(w,f)
                                      )

    def process_IN_MOVED_TO(self, event):
        try:
            path = unicode(event.pathname)
        except UnicodeDecodeError, error_message:
            if __debug__:
                dprint("Ignore file [%s]: %s" % (event.pathname,
                                                 error_message)
                       )
            return

        filename, watched_dir = self.manager.path_split(path)
        try:
            try:
                src_path = unicode(event.src_pathname)
            except UnicodeDecodeError, error_message:
                if __debug__:
                    dprint("Ignore file [%s]: %s" % (event.src_pathname,
                                                     error_message)
                           )
                return

            old_filename, _ = self.manager.path_split(src_path)
        except AttributeError, error_message:
            # if we receive error """'Event' object has no attribute 'src_pathname'"""
            # means that the file was moved into a directory that we follow
            # from a directory that we don't follow, so it's like creating a new file
            if event.dir:
                self.process_IN_CREATE(event)
            else:
                self.process_IN_CLOSE_WRITE(event)
            return

        if event.dir:
            self.manager.add_to_queue(MoveDir(self.manager.hub,
                                              filename,
                                              old_filename,
                                              watched_dir),
                                      pathjoin(watched_dir, filename)
                                      )
        else:
            self.manager.add_to_queue(MoveFile(self.manager.hub,
                                               filename,
                                               old_filename,
                                               watched_dir),
                                      pathjoin(watched_dir, filename)
                                      )
    # # for debuging proposes only
    # def process_default(self, event):
    #     print event


class NotifyManager():
    def __init__(self, hub):
        self.hub = hub
        self._dms = self.hub.database_manager.store
        self.open_files_list = {}
        self._inotify_wm = pyinotify.WatchManager()
        self._processor = HandleEvents(self)
        self._inotify_notifier = pyinotify.Notifier(self._inotify_wm, self._processor)
        self._initify_reader = self._hook_inotify_to_twisted(
                                self._inotify_wm, self._inotify_notifier)
        self.watch_list = []
        for record in self._dms.find(db.WatchPath):
            reactor.callWhenRunning(self.add_watch, record.path)



    def add_watch(self, directory):
        if __debug__:
            dprint("Adding ", directory)
            dprint("Adding expanded", os.path.abspath(os.path.expanduser(directory)))
        directory = os.path.abspath(directory)
        if self.check_valid_path(directory):
            mask = pyinotify.IN_DELETE | pyinotify.IN_OPEN | pyinotify.IN_CLOSE_WRITE | pyinotify.IN_ACCESS | pyinotify.IN_CREATE | pyinotify.IN_CLOSE_NOWRITE  # watched events
            mask = mask | pyinotify.IN_MOVED_TO | pyinotify.IN_MOVED_FROM | pyinotify.IN_MOVE_SELF
            mask = mask | pyinotify.ALL_EVENTS
            watch_list = self._inotify_wm.add_watch(directory, mask, rec=True)

            # save only dir we watch
            self.watch_list.append(directory)

            for d in watch_list:
                if watch_list[d] == -1:
                    # TODO handle better
                    if __debug__:
                        dprint("Cannot watch %s, skipping" % directory)
                else:
                    # scan for new files
                    self.scan_directory(d)


    def rescan_directories(self, directories=None):
        if not directories:
            directories = self.watch_list

        for directory in directories:
            self.scan_directory(directory)
            for _, dirs, _ in os.walk(directory):
                if dirs:
                    self.rescan_directories(dirs)


    # must check self.watch_list values for this to work now
    #def remove_watch(self, directory):
    #    print "Removing", directory
    #    try:
    #        del self.watch_list[directory]
    #    except KeyError:
    #         silentiy ignore the error
    #        pass

    def path_split(self, path):
        for d in self.watch_list:
            if path.startswith(d):
                return (path[len(d)+1:], d)

        raise KeyError, "We don't follow '%s' (%s)" % (path, self.watch_list)

    def check_valid_path(self, directory):
        # TODO check if we follow parent OR child
        """ Check if path is a directory
            Check if a directory exists
            Check if we already follow that or it's father
            """
        return True
#if directory not in self.watch_list.values() \
            #    and os.path.exists(directory) \
            #    and os.path.isdir(directory):
        #    return True

        #return False

    def scan_directory(self, directory):
        # check for creations / modifictions
        for root, dirs, files in os.walk(directory):
            # process directories
            for name in dirs:
                f, w = self.path_split(pathjoin(root, name))
                self.add_to_queue(CreateDir(self.hub, f, w),
                                  pathjoin(w, f)
                                  )
            # process files
            for name in files:
                f, w = self.path_split(pathjoin(root, name))
                self.add_to_queue(ModifyFile(self.hub, f, w),
                                  pathjoin(w, f)
                                  )

        # check for deletions
        watchpath = self._dms.find(db.WatchPath, db.WatchPath.path==directory).one()
        if watchpath:
            # only do this procedure with watchpath's
            # find file in watched path
            query = self._dms.find(db.File,
                                   db.WatchPath.id == watchpath.id,
                                   db.WatchPath.id == db.File.watchpath_id)
            for f in query:
                fullpath = pathjoin(watchpath.path, f.filename)
                if not os.path.exists(fullpath):
                    # the file got delete while we
                    # where not watching
                    if f.directory:
                        self.add_to_queue(DeleteDir(self.hub, f.filename, watchpath.path),
                                          fullpath)
                    else:
                        self.add_to_queue(DeleteFile(self.hub, f.filename, watchpath.path),
                                          fullpath)

    def add_to_queue(self, action, pathname):
        if pathname not in self.open_files_list:
            self.hub.queue.put(action)

    def add_to_file_list(self, event):
        #if self.checkFile(event):
            self.open_files_list[event.pathname] = True

    def remove_from_file_list(self, event):
        #if self.checkFile(event):
            try:
                del self.open_files_list[event.pathname]
            except KeyError:
                #print "error, not in list"
                #print event.pathname, self.open_files_list
                pass


    def _hook_inotify_to_twisted(self, wm, notifier):
        """This will hook inotify to twisted."""
        """ copied directly from event_queue.py of ubuntuone """

        class MyReader(abstract.FileDescriptor):
            """Chain between inotify and twisted."""
            # will never pass a fd to write, pylint: disable-msg=W0223

            def fileno(self):
                """Returns the fileno to select()."""
                # pylint: disable-msg=W0212
                return wm._fd

            def doRead(self):
                """Called when twisted says there's something to read."""
                notifier.read_events()
                notifier.process_events()

        reader = MyReader()
        reactor.addReader(reader)
        return reader

