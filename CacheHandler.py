# import json
from RequestPacket import RequestPacket
from ResponsePacket import ResponsePacket
import os # remove file os.remove(filename)

class CacheHandler:
    '''
    cache handler offers only static functions
    it acts as a global singleton to handle cache for all threads

    records responses to local files,
    returns a cached response

    Members:

    Constructor:

    Functions:

        cacheResponse(rqp, rsp):        param: (rsp : ResponsePacket)
                                        handle cache request
                                        determine if the response should be cached/ updated in cache file
                                        if no, then simply return

        fetchResponse(rqp):             param: (rqp : RequestPacket)
                                        handle fetch request
    '''

    @staticmethod
    def cacheResponse(rqp, rsp):
        cacheOption = rsp.getHeaderInfo('cache-control')
        resource = rqp.getFullPath()

    @staticmethod
    def fetchResponse(rqp):
        pass
