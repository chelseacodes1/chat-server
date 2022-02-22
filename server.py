#!/bin/python
###########
# IMPORTS #
###########
import signal
import os
import sys
import socket
import select
import hashlib


####################
# GLOBAL VARIABLES #
####################
daemon_quit = False         # Use this variable for main loop
clients = dict()            # key: username, value: hashed password
channel_map = dict()        # key: channel name, value: channel object
connections = []


###########
# CLASSES #
###########
class Channel:
    def __init__(self, name: str):
        self.members_ls = []   # stores conn.username -> username of connections 
        self.name = name

# Class to store client username and socket 
class Connection:
    def __init__(self, sock):
        self.connected = False
        self.logged_in = False
        self.username = None
        self.sock = sock


####################
# HELPER FUNCTIONS #
####################  
def quit_gracefully(signum, frame):     #Do not modify or remove this handler
    global daemon_quit
    daemon_quit = True


def lookup_connection(socket, connections):
    # iterate through connections 
    for conn in connections:
        if conn.sock == socket:
            return conn
    return None


def get_hash(password):
    hashGen = hashlib.sha512()
    hashGen.update(password.encode('utf-8'))
    hash_password = hashGen.hexdigest()
    return hash_password 


def register_client(message):
    tokens = message.split()
    if len(tokens) < 3:
        return "RESULT REGISTER 0\n"

    username = tokens[1]
    password = tokens[2]
    hash_password = get_hash(password)

    if username not in clients:
        # add to new client to clients dictionary - key: username, value: hashed password 
        clients[username] = hash_password 
        return "RESULT REGISTER 1\n"
    else:
        return "RESULT REGISTER 0\n"


def login_client(message, conn: Connection):
    tokens = message.split()
    
    if len(tokens) < 3:
        return "RESULT LOGIN 0\n"

    username = tokens[1]
    password = tokens[2]
    hash_password = get_hash(password)

    if (username, hash_password) in clients.items():
        # client already logged in 
        if conn.logged_in: 
            return "RESULT LOGIN 0\n"
        else:
            conn.logged_in = True
            conn.username = username
            return "RESULT LOGIN 1\n"
    else:
        return "RESULT LOGIN 0\n"
    

def create_channel(message, conn: Connection):
    tokens = message.split()

    if len(tokens) < 2:
        return "Error: Invalid use of CREATE command\n" 
    
    channel = tokens[1:]
    channel_name = " ".join(channel)

    # User not logged in 
    if not conn.logged_in:
        return "Error: User not logged in, cannot create channel\n" 
    
    # Creating a new channel 
    if channel_name not in channel_map:
        new_channel = Channel(channel_name)
        channel_map[channel_name] = new_channel
        return "RESULT CREATE {} 1\n".format(channel_name)
    else:
        return "RESULT CREATE {} 0\n".format(channel_name)


def join_channel(message, conn: Connection):
    tokens = message.split()
    
    if len(tokens) < 2:
        return "Error: Invalid use of JOIN command\n" 
    
    channel = tokens[1:]
    channel_name = " ".join(channel)
    if not conn.logged_in:
        return "RESULT JOIN {} 0\n".format(channel_name)
    
    # Channel exists
    if channel_name in channel_map:
        c = channel_map[channel_name]

        # client has not joined channel yet, add to members list 
        if conn.username not in c.members_ls:
            c.members_ls.append(conn.username)
            return "RESULT JOIN {} 1\n".format(channel_name)
        # client already joined channel, in members list 
        else:
            return "RESULT JOIN {} 0\n".format(channel_name)
    
    # Channel doesn't exist 
    else:
        return "RESULT JOIN {} 0\n".format(channel_name)


def get_list_channels():
    if len(channel_map) == 0:
        return "RESULT CHANNELS \n"

    sorted_channel_ls = sorted(channel_map.keys())
    return ("RESULT CHANNELS " + ", ".join(sorted_channel_ls) + "\n")


def send_message(message, conn: Connection):
    tokens = message.split()

    if len(tokens) < 3:
        return "Error: Invalid use of SAY command\n" 

    channel_name = tokens[1]
    msg_ls = tokens[2:]
    msg_str = " ".join(msg_ls)
    user = conn.username
    global connections 

    # check whether the user has logged in
    if not conn.logged_in:
        return "Error: user not logged in, cannot send message\n"

    # check if channel exists
    if channel_name in channel_map:
        # c: Channel object 
        c = channel_map[channel_name]

        # check if user is in channel 
        if user in c.members_ls:
            return "RECV {} {} {}\n".format(user, channel_name, msg_str)
        else:
            return "Error: user has not joined channel, cannot send message\n"
            
    else: 
        return "Error: channel does not exist\n"

##########
# DRIVER #
##########
def run():
    #Do not modify or remove this function call
    signal.signal(signal.SIGINT, quit_gracefully)
    
    if len(sys.argv) < 2:
        print("Error: no port number specified")
        return 

    # Create and start server 
    SERVER_PORT = int(sys.argv[1]) 
    server_address = ("127.0.0.1", SERVER_PORT)
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(server_address)

    # set server to non-blocking 
    server.setblocking(False) 
    server.listen()
    
    sockets = [server]
    global connections

    # Main loop 
    while not daemon_quit:
        readable, writable, errors = select.select(sockets, [], [], 0.5)
         
        for r in readable:
            # a new connection request received
            if r == server:
                client, address = r.accept()
                client.setblocking(False)
                conn = Connection(client)
                connections.append(conn)
                sockets.append(client)
            
            # a message/ data received from client, not a new connection
            else:
                try: # receiving data from the socket
                    data = r.recv(1024).decode('utf-8')
                except ConnectionResetError:
                    continue

                if data: # there is something in the socket
                    if "REGISTER" in data:
                        response = register_client(data).encode('utf-8')
                        client.send(response)
                    
                    # client doesn't need to be logged in to access channels 
                    elif "CHANNELS" in data:
                        response = get_list_channels().encode('utf-8')
                        client.send(response)

                    else:
                        conn = lookup_connection(r, connections)
                        if "LOGIN" in data:
                            response = login_client(data, conn).encode('utf-8')
                            client.send(response)
                        elif "CREATE" in data:
                            response = create_channel(data, conn).encode('utf-8')
                            client.send(response)
                        elif "JOIN" in data:
                            response = join_channel(data, conn).encode('utf-8')
                            client.send(response)
                        elif "SAY" in data:
                            response = send_message(data, conn).encode('utf-8')
                            #client.send(response)
                            for c in connections:
                               c.sock.send(response)
                        else: 
                            response = "Error: Invalid command\n".encode('utf-8')
                            client.send(response)
    server.close()

if __name__ == '__main__':
    run()