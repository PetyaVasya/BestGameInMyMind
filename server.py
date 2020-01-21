# import socket
# from _thread import *
# import sys
#
# server = ""
# port = 5555
#
# s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#
# try:
#     s.bind((server, port))
# except socket.error as e:
#     print(e)
#
# s.listen(2)
# print("Waiting for a connection, server started")
#
#
# def threaded_client(conn):
#     reply = ""
#
#     while True:
#         try:
#             data = conn.recv(2048)
#             reply = data.decode("utf-8")
#
#             if not data:
#                 print("Disconnected")
#                 break
#             else:
#                 print(f"Received: {reply}")
#                 print(f"Sending: {reply}")
#             conn.sendall(str.encode(reply))
#         except Exception as e:
#             print(e)
#             break
#
# while True:
#     conn, address = s.accept()
#     print(f"Connected to: {address}")
#
#     start_new_thread(threaded_client, (conn,))


import socket
import asyncore
import select
import random
import pickle
import time

BUFFERSIZE = 512

outgoing = []


class Minion:
    def __init__(self, ownerid):
        self.x = 50
        self.y = 50
        self.ownerid = ownerid


minionmap = {}


def updateWorld(message):
    arr = pickle.loads(message)
    print(str(arr))
    playerid = arr[1]
    x = arr[2]
    y = arr[3]

    if playerid == 0: return

    minionmap[playerid].x = x
    minionmap[playerid].y = y

    remove = []

    for i in outgoing:
        update = ['player locations']

        for key, value in minionmap.items():
            update.append([value.ownerid, value.x, value.y])

        try:
            i.send(pickle.dumps(update))
        except Exception:
            remove.append(i)
            continue

        print('sent update data')

        for r in remove:
            outgoing.remove(r)


class MainServer(asyncore.dispatcher):
    def __init__(self, port):
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.bind(('', port))
        self.listen(10)

    def handle_accept(self):
        conn, addr = self.accept()
        print('Connection address:' + addr[0] + " " + str(addr[1]))
        outgoing.append(conn)
        playerid = random.randint(1000, 1000000)
        playerminion = Minion(playerid)
        minionmap[playerid] = playerminion
        conn.send(pickle.dumps(['id update', playerid]))
        SecondaryServer(conn)


class SecondaryServer(asyncore.dispatcher_with_send):
    def handle_read(self):
        recievedData = self.recv(BUFFERSIZE)
        if recievedData:
            updateWorld(recievedData)
        else:
            self.close()


MainServer(4321)
asyncore.loop()
