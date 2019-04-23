from socket import *


#  ██  ██      ██████  ██████   ██████  ██   ██ ██    ██
# ████████     ██   ██ ██   ██ ██    ██  ██ ██   ██  ██
#  ██  ██      ██████  ██████  ██    ██   ███     ████
# ████████     ██      ██   ██ ██    ██  ██ ██     ██
#  ██  ██      ██      ██   ██  ██████  ██   ██    ██


class Proxy:
    '''
    provide proxy functions
    open welcoming socket
    allocate and return socket
    create thread connections

    Members:

        MAX_CONNECTION:                 (static) number of simultaneous connections supported

        freeIndexArr:                   (static) array of flags marking which index position of connectionThreads are available

        connectionThreads:              (static) array storing the connection threads

        proxyAddr:                      address of this proxy server

        proxyPort:                      port number of this proxy server

        welcomeSocket:                  welcoming socket object

    Constructor:

        __init__(port=6298):            init members, defualt port is 6298

    Functions:

        getFreeIndex():                 loop through freeIndexArr to get a free spot for next client connection

        setFreeIndex(idx, flag):        param: (idx : uint, flag : bool)
                                        set freeIndexArr[idx] to flag

        listenConnection:               start listening to proxyPort, accept connections

    '''

    MAX_CONNECTION = 100 # number of simultaneous connections supported
    freeIndexArr = []
    connectionThreads = []

    def __init__(self, port=6298):
        self.proxyAddr = '127.0.0.1'
        self.proxyPort = port
        self.welcomeSocket = socket(AF_INET, SOCK_STREAM)
        self.welcomeSocket.bind((self.proxyAddr, self.proxyPort))
        self.welcomeSocket.listen(Proxy.MAX_CONNECTION)
        for i in range(Proxy.MAX_CONNECTION):
            Proxy.freeIndexArr.append(True)
            Proxy.connectionThreads.append([])
        print('Proxy:: server starts')

    def getFreeIndex(self):
        for i in range(Proxy.MAX_CONNECTION):
            if Proxy.freeIndexArr[i] == True:
                print('Proxy:: getFreeIndex: index ' + str(i) + ' is free')
                return i
        return -1

    @staticmethod
    def setFreeIndex(idx, flag):
        Proxy.freeIndexArr[idx] = flag

    def listenConnection(self):
        while True:
            try:
                idx = Proxy.getFreeIndex(self)
                if idx != -1:
                    clientSideSocket, addr = self.welcomeSocket.accept()
                    clientThread = ConnectionThread(clientSideSocket, idx)
                    clientThread.start()
                    Proxy.connectionThreads[idx] = clientThread
                    Proxy.setFreeIndex(idx, False)

                    print('Proxy:: connection to client established')
            except KeyboardInterrupt:
                print('Proxy:: closing proxy')
                break









#  ██  ██       ██████  ██████  ███    ██ ███    ██ ███████  ██████ ████████ ██  ██████  ███    ██     ████████ ██   ██ ██████  ███████  █████  ██████
# ████████     ██      ██    ██ ████   ██ ████   ██ ██      ██         ██    ██ ██    ██ ████   ██        ██    ██   ██ ██   ██ ██      ██   ██ ██   ██
#  ██  ██      ██      ██    ██ ██ ██  ██ ██ ██  ██ █████   ██         ██    ██ ██    ██ ██ ██  ██        ██    ███████ ██████  █████   ███████ ██   ██
# ████████     ██      ██    ██ ██  ██ ██ ██  ██ ██ ██      ██         ██    ██ ██    ██ ██  ██ ██        ██    ██   ██ ██   ██ ██      ██   ██ ██   ██
#  ██  ██       ██████  ██████  ██   ████ ██   ████ ███████  ██████    ██    ██  ██████  ██   ████        ██    ██   ██ ██   ██ ███████ ██   ██ ██████




import threading
from SocketHandler import SocketHandler

class ConnectionThread(threading.Thread):
    '''
    this class must be imported by Proxy module
    thread object for clients to make connections

    Members:

        socketHandler:              socketHandler object for the client

        idx:                        index this thread is assigned to, in Proxy.connectionThreads

    Constructor:

        default:                    construct superclass,
                                    initialize members

    Functions:

        run():                      start socketHandler
                                    when finish, set Proxy.freeIndexArr[idx] to be free (True)
    '''

    def __init__(self, socket, idx):
        threading.Thread.__init__(self)
        self.socketHandler = SocketHandler(socket)
        self.idx = idx

    def run(self):
        print('ConnectionThread:: thread at ' + str(self.idx) + ' starting')
        self.socketHandler.handleRequest()
        print('ConnectionThread:: thread at ' + str(self.idx) + ' ending')
        Proxy.setFreeIndex(self.idx, True)
        print('ConnectionThread:: index ' + str(self.idx) + ' in Proxy class is set free')
