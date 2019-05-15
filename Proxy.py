from socket import *
from CacheHandler import CacheHandler


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
    '''

    MAX_CONNECTION = None # number of simultaneous connections supported
    freeIndexArr = []
    connectionThreads = []

    def __init__(self, max_connection=None, port=None):
        '''
        default max_connection: 200
        default port number: 6298

        initialize welcoming socket, freeIndexArr, connectionThreads array,
        configure CacheHandler hashed locks

        MAX_CONNECTION:         @static

        freeIndexArr:           @static
                                array of flags marking which index position of connectionThreads are available

        connectionThreads:      @static
                                array storing the connection threads

        proxyAddr:              IP reachable

        proxyPort:

        welcomingSocket:
        '''
        if max_connection is None:
            max_connection = 200
        if port is None:
            port = 6298
        print('Proxy:: config: max_connection=' + str(max_connection) + ', port=' + str(port))

        Proxy.MAX_CONNECTION = max_connection
        self.proxyAddr = '0.0.0.0' # support all IP
        self.proxyPort = port
        self.welcomeSocket = socket(AF_INET, SOCK_STREAM)
        self.welcomeSocket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        self.welcomeSocket.bind((self.proxyAddr, self.proxyPort))
        self.welcomeSocket.listen(Proxy.MAX_CONNECTION)
        for i in range(Proxy.MAX_CONNECTION):
            Proxy.freeIndexArr.append(True)
            Proxy.connectionThreads.append([])
        CacheHandler.initHashedLocks(Proxy.MAX_CONNECTION)
        print('Proxy:: server starts')

    def getFreeIndex(self):
        '''
        loop through freeIndexArr to get a free spot for next client connection
        '''
        for i in range(Proxy.MAX_CONNECTION):
            if Proxy.freeIndexArr[i] == True:
                print('Proxy:: getFreeIndex: index ' + str(i) + ' is free')
                return i
        return -1

    @staticmethod
    def setFreeIndex(idx, flag):
        '''
        set freeIndexArr[idx] to flag
        '''
        Proxy.freeIndexArr[idx] = flag
        if Proxy.freeIndexArr[idx] == True: # confirm freed
            print('Proxy:: setFreeIndex: index ' + str(idx) + ' is free')

    def listenConnection(self):
        '''
        start listening to proxyPort, accept connections
        reject connections if exceeding MAX_CONNECTION

        on key interrupt:
            close connections,
            join all threads,
            write cache lookup table to file
        '''
        while True:
            try:
                clientSideSocket, addr = self.welcomeSocket.accept()
                idx = Proxy.getFreeIndex(self)
                if idx != -1:
                    clientThread = ConnectionThread(clientSideSocket, idx)
                    clientThread.start()
                    Proxy.connectionThreads[idx] = clientThread
                    Proxy.setFreeIndex(idx, False)
                    print('Proxy:: connection to client established')
                else:
                    print('Proxy:: connection thread limit reached')
                    clientSideSocket.close()
                    print('Proxy:: connection closed')

            except KeyboardInterrupt:
                self.welcomeSocket.close()
                for i in range(Proxy.MAX_CONNECTION): # call close connection, dont wait for child processes here
                    if not Proxy.freeIndexArr[i]:
                        Proxy.connectionThreads[i].closeConnection()
                CacheHandler.writeLookupTableToFile()
                for i in range(Proxy.MAX_CONNECTION): # wait for all child processes
                    if not Proxy.freeIndexArr[i]:
                        Proxy.connectionThreads[i].join()
                CacheHandler.exitRoutine()
                print('Proxy:: closing proxy') # after joining all processes, quit function`
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
    '''

    def __init__(self, socket, idx):
        threading.Thread.__init__(self)
        self.socketHandler = SocketHandler(socket)
        self.idx = idx

    def run(self):
        '''
        start socketHandler
        when finish, set Proxy.freeIndexArr[idx] to be free (True)
        '''
        print('ConnectionThread:: thread id: ' + str(self.idx) + ' starting')
        self.socketHandler.handleRequest()
        print('ConnectionThread:: thread id: ' + str(self.idx) + ' ending')
        Proxy.setFreeIndex(self.idx, True)
        print('ConnectionThread:: thread id: ' + str(self.idx) + ' in Proxy class is set free')

    def closeConnection(self):
        self.socketHandler.closeConnection()
        print('ConnectionThread: thread id: ' + str(self.idx) + ' manual close initiated')
