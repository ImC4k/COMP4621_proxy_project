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
        Proxy.setFreeIndex(idx, True)
        print('ConnectionThread:: index ' + str(self.idx) + ' in Proxy class is set free')
