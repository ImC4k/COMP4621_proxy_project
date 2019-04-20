import threading
from time import sleep
# NOTE: no need to import SocketHandler here, otherwise it will cause a cycle

class TimerThread(threading.Thread):
    '''
    timer thread for proxy-to-client connection
    when timer ends, try to set timeout for the caller

    Members:

        __id:                        id this thread is assigned to

        __time:                       seconds the timer should set to

        __socketHandler:            the caller of this thread

    Constructor:

        default:                    construct superclass,
                                    initialize members

    Functions:

        run():                      start timer
                                    when finish, set connectionThread.timeout = True
    '''

    def __init__(self, id, time, socketHandler):
        threading.Thread.__init__(self)
        self.__id = id
        self.__time = time
        self.__socketHandler = socketHandler

    def run(self):
        sleep(self.__time)
        self.__socketHandler.setTimeout(self.__id)
