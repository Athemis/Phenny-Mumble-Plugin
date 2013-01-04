#!/usr/bin/env python
"""
mumble.py - Phenny Mumble Module
Copyright 2012, Steven Humphrey
Licensed under the Eiffel Forum License 2.

To get this to work, please add 4 keys to the config:
mumble_ip, mumble_port, mumble_slice, mumble_secret.
mumble_slice should be the path to the Murmur.ice file.

http://mumble.sourceforge.net/Ice
"""

import Ice
import threading, time

def setup(self):
    """Sets up ICE"""
    slicefile = self.config.mumble_slice
    icesecret = self.config.mumble_secret

    Ice.loadSlice('', ['-I' + Ice.getSliceDir(), slicefile ] )
    prop = Ice.createProperties([])
    prop.setProperty("Ice.ImplicitContext", "Shared")
    prop.setProperty("Ice.MessageSizeMax",  "65535")

    idd = Ice.InitializationData()
    idd.properties = prop
    global ice
    ice = Ice.initialize(idd)
    ice.getImplicitContext().put("secret", icesecret)
    global Murmur
    import Murmur
    ## Set up threaded checker
    t = threading.Timer(20.0, mumble_auto_loop, [self])
    t.start()
    
setup.thread = False


def mumble_auto_loop(phenny):
    server = get_server(phenny)
    users = get_users(server)
    usernames = []
    for uk in users:
        usernames.append(users[uk].name)
    recip = phenny.config.mumble_channels
    for r in recip:
        phenny.msg(r, ", ".join(usernames))

    while(True):
        time.sleep(phenny.config.mumble_check_interval)
        server = get_server(phenny)
        users = server.getUsers()
        currentusers = []
        for uk in users:
            currentusers.append(users[uk].name)
        for name in currentusers:
            try:
                usernames.index(name)
            except:
                for r in recip:
                    phenny.msg(r, "{} has joined mumble".format(name))
                usernames.append(name)
        for name in usernames:
            try:
                currentusers.index(name)
            except:
                for r in recip:
                    phenny.msg(r, "{} has left mumble".format(name))
                usernames.remove(name)
                
mumble_auto_loop.thread = False

def get_server(phenny):
    """Returns the mumble server"""
    try:
        mumble_ip     = phenny.config.mumble_ip
    except:
        mumble_ip     = "127.0.0.1"
    try:
        mumble_port   = phenny.config.mumble_port
    except:
        mumble_port   = "6502"

    if not mumble_ip:
        phenny.say("mumble is not configured")
        return
        
    connstring = "Meta:tcp -h %s -p %s" % (mumble_ip, mumble_port)

    global ice
    proxy = ice.stringToProxy( connstring )

    global Murmur
    meta = Murmur.MetaPrx.checkedCast(proxy)
    server = meta.getServer(1)
    return server


def get_channels(server):
    """Obtain a list of channels"""
    tmp = server.getChannels()
    channels = {}
    for key in tmp:
        c = tmp[key]

        channels[str(c.id)] =  {"id"         : str(c.id),
                                "name"       : str(c.name),
                                "parent"     : str(c.parent),
                                "description": str(c.description),
                                "temporary"  : bool(c.temporary),
                                "links"      : c.links,
                                "position"   : int(c.position)}
    return channels

def get_channels_id_name(server):
    channels = get_channels(server)

    id_name = []

    for id, c in channels.items():
        id_name.append( (c['id'], c['name'].lower()) )

    return id_name

def get_channels_hirarchy(server):

    channels = get_channels(server)

    for id, c in channels.items():
        
        c['children'] = []

    for id, c in channels.items():
       
        if c['parent'] and c['parent'] != '-1':
            channels[c['parent']]['children'].append(c)

    channels_tree = dict(channels)

    for k in channels.keys():
        if channels[k]['parent'] != '-1':
            del channels_tree[k]
            
    return channels_tree
  
def get_users(server):
    users = server.getUsers()
    #if len(users) == 0:
        #phenny.say("no users connected")
        #return
    #for key in users:
        #name = users[key].name
        #users.append(name)
    return users

def mumble_send(phenny, input):
    """Sends a message to mumble server"""
    server = get_server(phenny)
    try:
        message = input.groups()[1].split('|')[0].strip()
    except:
        message = None
    try:
        receiver = input.groups()[1].split('|')[1].strip().lower()
    except:
        receiver = None
    try:
        tree = bool(input.groups()[1].split('|')[2].strip())
    except:
        tree = False
    if message and not receiver:
        server.sendMessageChannel(0, True, message)
        phenny.say("Message sent to first channel tree")
    elif message and receiver:
        id_name = get_channels_id_name(server)
        sent = False
        for id, name in id_name:
            if receiver == id or receiver == name:
                server.sendMessageChannel(int(id), tree, message)
                phenny.say("Message sent to mumble channel '{}'".format(name))
                sent = True
                break
        if not sent:
            users = get_users(server)
            
            for key in users:
                name = users[key].name.lower()
                session = users[key].session
                
                if receiver == name:
                    server.sendMessage(session, message)
                    sent = True
            
        if not sent:
            phenny.say("Unknown mumble channel/user '{}'".format(channel))
    else:
        phenny.say("usage:")
        phenny.say("global message                    : .mumble_send <text>")
        phenny.say("message to channel                : .mumble_send <text>|<channel id/name>")
        phenny.say("message to channel and subchannels: .mumble_send <text>|<channel id/name>|1")

mumble_send.commands = ['mumble_send']
mumble_send.priority = 'medium'
mumble_send.example = '.mumble_send Hello World'

def mumble_users(phenny, input): 
    """Shows the users connected to mumble."""
    server = get_server(phenny)
    users = get_users(server)
    names = []
    
    if len(users) == 0:
        phenny.say("no users connected")
        return
    
    for key in users:
        name = users[key].name
        names.append(name)

    phenny.say(", ".join(names))

mumble_users.commands = ['mumble_user']
mumble_users.priority = 'medium'
mumble_users.example = '.mumble_user'


def mumble_status(phenny):
    """Shows the server's status"""
    server = get_server(phenny)

    if server.isRunning():
        status = "online"
    else:
        status = "offline"

    phenny.say("The mumble server is {}".format(status))

mumble_status.commands = ['mumblestatus']
mumble_status.priority = 'low'
mumble_status.example = '.mumblestatus'

if __name__ == '__main__': 
   print(__doc__.strip())
