from socket import *
from ConnectionThread import ConnectionThread

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

        setFreeIndex(idx, flag):        set freeIndexArr[idx] to flag

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

    def setFreeIndex(self, idx, flag):
        Proxy.freeIndexArr[idx] = flag

    def listenConnection(self):
        while True:
            idx = Proxy.getFreeIndex(self)
            if idx != -1:
                clientSideSocket, addr = self.welcomeSocket.accept()
                clientThread = ConnectionThread(clientSideSocket, idx)
                clientThread.start()
                Proxy.connectionThreads[idx] = clientThread
                Proxy.setFreeIndex(self, idx, False)

                print('Proxy:: connection to client established')
