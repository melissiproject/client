#!/usr/bin/env python

# Melissi command line tool
#
# Yeah ;)

# standard modules
import sys
import os
import dbus
from optparse import OptionParser

def main():
    bus = dbus.SessionBus()
    com_services = bus.get_object('org.melissi.Melissi','/org/melissi/Melissi')

    parser = OptionParser()
#    parser.add_option("--socket",
#                      help="UNIX socket where melissi client listens",
#                      default=os.path.expanduser("~/.config/melisi/melisi.sock")
#                      )
    (options, args) = parser.parse_args()


    if len(args) < 1:
        usage(commands)
        sys.exit(0)

    try:
        command = com_services.get_dbus_method(args[0],'org.melissi.Melissi')
        command(*args[1:])
    except dbus.DBusException:
        #TODO fix the exception
        sys.exit(1)


if __name__ == '__main__':
    main()
