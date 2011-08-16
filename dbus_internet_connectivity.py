import dbus

#status signals from network manager
#0 - status unknown
#1 - status asleep
#2 - status connecting
#3 - status connected
#4 - status disconnected

#define newtork manager stages
NM_STATE_UNKNOWN = 0
NM_STATE_ASLEEP = 1
NM_STATE_CONNECTING = 2
NM_STATE_CONNECTED = 3
NM_STATE_DISCONNECTED = 4

bus = dbus.SystemBus()
nm = bus.get_object('org.freedesktop.NetworkManager',
		'/org/freedesktop/NetworkManager')

if nm.state() == NM_STATE_CONNECTED:
	print "We'r in businness"
