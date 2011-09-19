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

    try:
        com_services = bus.get_object('org.melissi.Melissi','/org/melissi/Melissi')

    except dbus.exceptions.DBusException:
        print "Cannot contact service! Is melissi desktop client running?"
        sys.exit(1)

    parser = OptionParser()
    (options, args) = parser.parse_args()

    if len(args) < 1:
        print "List of available methods:",
        print com_services.get_dbus_method('list_methods')()
        sys.exit(0)

    try:
        command = com_services.get_dbus_method(args[0])
        print command(*args[1:])

    except dbus.DBusException:
        print "Method not available or wrong arguments given!"
        print "List of available methods:",
        print com_services.get_dbus_method('list_methods')()

        sys.exit(1)

if __name__ == '__main__':
    main()
