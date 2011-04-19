#!/usr/bin/env python

# melissi modules
import desktop
import dbstorm as database
import notifier
import worker
import config
import restclient
import commander
import queue
import twisted

# standard modules
from optparse import OptionParser
from twisted.internet import reactor
import os
import sys


class Hub():
    def __init__(self):
        self.database_manager = None
        self.config_manager = None
        self.desktop_tray = None
        self.worker = None
        self.notify_manager = None
        self.queue = None
        self.rest_client = None

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
    (options, _) = parser.parse_args()

    hub = Hub()
    hub.queue = queue.Queue(hub)
    hub.config_manager = config.ConfigManager(hub, os.path.expanduser(options.config_file))
    hub.database_manager = database.DatabaseManager(hub, hub.config_manager.get_database())
    hub.notify_manager = notifier.NotifyManager(hub)
    hub.desktop_tray = desktop.DesktopTray(hub,
                                           disable=hub.config_manager.config.get('main', 'no-desktop') == 'True' or options.no_desktop)
    hub.worker = worker.Worker(hub)
    hub.rest_client = restclient.RestClient(hub)

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
