#!/usr/bin/env python

# standard modules
from optparse import OptionParser
import os
import sys

# melissi modules
import desktop
import dbstorm as database
import notifier
import worker
import config
import restclient
import watchdog
import commander
import queue
import twisted
import logging

# extra modules
# reactor must install last
from twisted.internet import reactor

class Hub(object):
    def __init__(self):
        self.database_manager = None
        self.config_manager = None
        self.desktop_tray = None
        self.worker = None
        self.notify_manager = None
        self.queue = None
        self.rest_client = None
        self.watch_dog = None


def setup_logging(level):
    """
    Logging levels:
    5 FULLDEBUG
    10 DEBUG
    20 INFO
    >=30 WARNING, ERRORS

    Example Format of Logs
    ERROR testlogger/testlogger.py:30       f                | Something awful happened
    """
    # add level 5, fulldebug
    logging.addLevelName(5, "FDEBUG")

    x = logging.getLogger("melissilogger")
    x.setLevel(level)
    h = logging.StreamHandler()
    f = logging.Formatter(" %(levelname)-10s %(module)-10s %(filename)s:%(lineno)d \t%(funcName)-20s\t | %(message)s")
    h.setFormatter(f)
    x.addHandler(h)

def main():
    # Parse options
    parser = OptionParser()
    parser.add_option("--config-file",
                      help="Path to configuration file",
                      default=os.path.expanduser('~/.config/melissi/config')
                      )
    parser.add_option("--no-desktop",
                      help="Disable desktop",
                      action="store_true",
                      default=False
                      )
    parser.add_option("-v", "--verbosity",
                      help="Verbose debug messages. Use multiple for more verbose messages",
                      action="count",
                      dest="verbosity",
                      default=0)

    (options, _) = parser.parse_args()

    # parse verbosity level and set logging
    if options.verbosity == 0:
        setup_logging(20)
    elif options.verbosity == 1:
        setup_logging(10)
    elif options.verbosity >= 2:
        setup_logging(5)
    elif options.quiet == True:
        setup_logging(30)

    hub = Hub()
    hub.queue = queue.Queue(hub)
    hub.config_manager = config.ConfigManager(hub,
                                              os.path.expanduser(options.config_file))
    hub.database_manager = database.DatabaseManager(hub, hub.config_manager.get_database())
    hub.notify_manager = notifier.NotifyManager(hub)
    hub.desktop_tray = desktop.DesktopTray(hub,
                                           disable=hub.config_manager.config.get('main', 'no-desktop') == 'True' or options.no_desktop)
    hub.worker = worker.Worker(hub)
    hub.rest_client = restclient.RestClient(hub)
    hub.watch_dog = watchdog.WatchDog(hub)

    # enable commander
    command_receiver = commander.FooboxCommandReceiver(hub)
    socket_path = hub.config_manager.get_socket()
    if socket_path:
        try:
            reactor.listenUNIX(socket_path, command_receiver)
        except twisted.internet.error.CannotListenError, error_message:
            print "Cannot use this socket. Please specify another socket"
            sys.exit(1)

    try:
        reactor.run()
    except (SystemExit, KeyboardInterrupt):
        reactor.stop()


if __name__ == "__main__":
    main()
