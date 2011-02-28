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

modes = {'woro':1, 'wora': 2, 'wara': 3, 'wnra':4, 'remove':-1}
command_list = []

class FooboxCommanderProtocol(LineReceiver):
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

        
class FooboxCommander(ClientFactory):
    protocol = FooboxCommanderProtocol

    def __init__(self, command_list):
        self.command_list = command_list

def usage(commands):
    print "Available commands: " + ', '.join(commands)

def share(argv):
    def usage():
        print "Usage: %s share [folder] [mode] [users]" % sys.argv[0]
        
    if len(sys.argv) != 5:
        usage()
        sys.exit(1)

    folder = argv[0]
    mode = argv[1]
    users = argv[2]
    cmd = {}
    cmd["command"] = "SHARE"

    cmd["folder"] = os.path.abspath(folder)

    # check if proper mode
    if not (mode in modes.keys()):
        usage()
        sys.exit(1)
    else:
        cmd["mode"] = modes[mode]

    cmd["users"] = []
    for user in users.split(','):
        if user == '':
            continue
        cmd["users"].append(user)
    
    command_list.append(json.dumps(cmd))


def auth(argv):
    def usage():
        print "Usage: %s auth [username] [password]" % sys.argv[0]
        
    if len(argv) != 2:
        usage()
        sys.exit(1)

    username = argv[0]
    password = argv[1]
    cmd = {}
    cmd["command"] = "AUTH"
    cmd["username"] = username
    cmd["password"] = password

    command_list.append(json.dumps(cmd))

def disconnect(argv):
    cmd = {'command':'DISCONNECT'}
    command_list.append(json.dumps(cmd))

def connect(argv):
    cmd = {'command':'CONNECT'}
    command_list.append(json.dumps(cmd))

def register(argv):
    def usage():
        print "Usage: %s register [username] [password] [email]" % sys.argv[0]
        
    if len(argv) != 3:
        usage()
        sys.exit()
    username = argv[0]
    password = argv[1]
    email = argv[2]

    cmd = {'command':'REGISTER',
           'username':username,
           'password':password,
           'email':email}
    command_list.append(json.dumps(cmd))

def checkbusy(argv):
    cmd = {'command':'CHECKBUSY'}
    command_list.append(json.dumps(cmd))

def sethost(argv):
    def usage():
        print "Usage: %s sethost [host] [port]" % sys.argv[0]

    if len(sys.argv) != 4:
        usage()
        sys.exit()
    host = argv[0]
    try:
        port = int(argv[1])
    except ValueError:
        usage()
        sys.exit(1)

    cmd = {'command':'SETHOST',
           'host':host,
           'port':int(port)}
    command_list.append(json.dumps(cmd))

def deleteuser(argv):
    def usage():
        print "Usage: %s deleteuser iamsure" % sys.argv[0]

    if len(sys.argv) != 3 and \
       argv[0] != "iamsure":
        usage()
        sys.exit()

    cmd = {'command':'DELETEUSER'}
    command_list.append(json.dumps(cmd))
           
def main():
    parser = OptionParser()
    parser.add_option("--socket",
                      help="UNIX socket where foobox client listens",
                      default=os.path.expanduser("~/.foobox/foobox.sock")
                      )
    (options, args) = parser.parse_args()

    commands = {'share':share,
                'auth':auth,
                'disconnect':disconnect,
                'connect':connect,
                'register':register,
                'checkbusy':checkbusy,
                'sethost':sethost,
                'deleteuser':deleteuser
                }

    if len(args) < 1:
        usage(commands)
        sys.exit(0)

    try:
        commands[args[0]](args[1:])
    except KeyError:
        usage(commands)
        sys.exit(1)

    foobox_commander = FooboxCommander(command_list)
    reactor.connectUNIX(options.socket, foobox_commander, timeout=2)
    reactor.run()


if __name__ == '__main__':
    main()
