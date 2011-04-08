#!/usr/bin/env python

# Foobox command line tool
#
# Yeah ;)

# standard modules
import sys
import os
import json
from optparse import OptionParser

from twisted.internet import reactor
from twisted.protocols.basic import LineReceiver
from twisted.internet.protocol import ClientFactory

modes = ['wara', 'wnra']
command_list = []

class MelisiCommanderProtocol(LineReceiver):
    def connectionMade(self):
        for cmd in self.factory.command_list:
            # send command
            self.sendLine(cmd)

        # force writing before exiting
        self.transport.doWrite()

    def lineReceived(self, line):
        print line

    def connectionLost(self, reason):
        reactor.stop()


class MelisiCommander(ClientFactory):
    protocol = MelisiCommanderProtocol

    def __init__(self, command_list):
        self.command_list = command_list

def usage(commands):
    print "Available commands: " + ', '.join(commands)

def removeshare(args):
    pass

def addshare(args):
    def usage():
        print "Usage: %s addshare [folder] [mode] [user]" % sys.argv[0]

    if len(args) != 3:
        usage()
        sys.exit(1)

    # check if proper mode
    if not (args[1] in modes):
        usage()
        sys.exit(1)

    cmd = {}
    cmd["command"] = "SHARE"
    cmd["path"] = os.path.abspath(args[0])
    cmd["mode"] = args[1]
    cmd["user"] = args[2]


    command_list.append(json.dumps(cmd))


def auth(args):
    def usage():
        print "Usage: %s auth [username] [password]" % sys.argv[0]

    if len(args) != 2:
        usage()
        sys.exit(1)

    username = args[0]
    password = args[1]
    cmd = {}
    cmd["command"] = "AUTH"
    cmd["username"] = username
    cmd["password"] = password

    command_list.append(json.dumps(cmd))

def disconnect(args):
    cmd = {'command':'DISCONNECT'}
    command_list.append(json.dumps(cmd))

def connect(args):
    cmd = {'command':'CONNECT'}
    command_list.append(json.dumps(cmd))

def register(args):
    def usage():
        print "Usage: %s register [username] [password] [email]" % sys.argv[0]

    if len(args) != 3:
        usage()
        sys.exit()
    username = args[0]
    password = args[1]
    email = args[2]

    cmd = {'command':'REGISTER',
           'username':username,
           'password':password,
           'email':email}
    command_list.append(json.dumps(cmd))

def checkbusy(args):
    cmd = {'command':'CHECKBUSY'}
    command_list.append(json.dumps(cmd))

def sethost(args):
    def usage():
        print "Usage: %s sethost http[s]://[host]:[port]/" % sys.argv[0]

    if len(args) != 1:
        usage()
        sys.exit()

    cmd = {'command':'SETHOST',
           'host':args[0],
           }
    command_list.append(json.dumps(cmd))

def deleteuser(args):
    def usage():
        print "Usage: %s deleteuser iamsure" % sys.argv[0]

    if len(args) != 1 and args[0] != "iamsure":
        usage()
        sys.exit()

    cmd = {'command':'DELETEUSER'}
    command_list.append(json.dumps(cmd))

def main():
    parser = OptionParser()
    parser.add_option("--socket",
                      help="UNIX socket where melisis client listens",
                      default=os.path.expanduser("~/.melisi/melisi.sock")
                      )
    (options, args) = parser.parse_args()

    commands = {
        'auth':auth,
        'disconnect':disconnect,
        'connect':connect,
        'register':register,
        'checkbusy':checkbusy,
        'sethost':sethost,
        'deleteuser':deleteuser,
        'addshare':addshare,
        'removeshare':removeshare,
        }

    if len(args) < 1:
        usage(commands)
        sys.exit(0)

    try:
        commands[args[0]](args[1:])
    except KeyError:
        usage(commands)
        sys.exit(1)

    melisi_commander = MelisiCommander(command_list)
    reactor.connectUNIX(options.socket, melisi_commander, timeout=2)
    reactor.run()


if __name__ == '__main__':
    main()
