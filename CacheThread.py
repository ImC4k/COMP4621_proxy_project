import threading
from CacheHandler import CacheHandler

class CacheThread(threading.Thread):
    '''
    thread to cache the response

    Members:

        __rqp:                  request packet

        __rsp:                  response packet to be cached, regardless of cacheability

    Constructor:

        default:                set rqp, rsp

    Functions:

        run:                    call CacheHandler.cacheResponse(rqp, rsp)
    '''
    
    def __init__(self, rqp, rsp):
        threading.Thread.__init__(self)
        self.__rqp = rqp
        self.__rsp = rsp

    def run(self):
        CacheHandler.cacheResponse(self.__rqp, self.__rsp)
