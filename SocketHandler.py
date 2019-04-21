from socket import *
from RequestPacket import RequestPacket
from ResponsePacket import ResponsePacket
# from TimerThread import TimerThread
from CacheHandler import CacheHandler
from TimeComparator import TimeComparator



#  ██  ██      ███████  ██████   ██████ ██   ██ ███████ ████████     ██   ██  █████  ███    ██ ██████  ██      ███████ ██████
# ████████     ██      ██    ██ ██      ██  ██  ██         ██        ██   ██ ██   ██ ████   ██ ██   ██ ██      ██      ██   ██
#  ██  ██      ███████ ██    ██ ██      █████   █████      ██        ███████ ███████ ██ ██  ██ ██   ██ ██      █████   ██████
# ████████          ██ ██    ██ ██      ██  ██  ██         ██        ██   ██ ██   ██ ██  ██ ██ ██   ██ ██      ██      ██   ██
#  ██  ██      ███████  ██████   ██████ ██   ██ ███████    ██        ██   ██ ██   ██ ██   ████ ██████  ███████ ███████ ██   ██




class SocketHandler:
    '''
    responsible for
        receiving client request, sending out request to server,
        receiving server response, sending out response to client

    Members:

        BUFFER_SIZE:                    (static) maximum buffer size to receive/ send packet

        HTTPS_PORT:                     (static) port number for HTTPS protocol

        HTTP_PORT:                      (static) port number for HTTP protocol

        socket:                         socket information

        timeout:                        boolean, true if timer ends

        timeoutThreadID:                if thread with this ID timeout, close this connection

        maxTransmission:                number of transmissions this connection can handle (default 100)

        isFirstResponse:                true if first response packet, set maxTransmission, connectionType

        connectionType:                 HTTP or HTTPS, allow different logistics

    Constructor:

        __init__(socket, callback):     when handleRequest() returns (connection closes),
                                        call callback function

    Methods:

        handleRequest():                called by listen(),
                                        handle incoming client request,
                                        make request to server by requestToServer(),
                                        return response to client

        requestToServer(rqp):           param: (rqp : RequestPacket)
                                        connect to server,
                                        return response packet

        cacheResponse(responseRaw):     param: (responseRaw : bytes)
                                        cache the response to a file

    '''

    BUFFER_SIZE = 8192 # 8KB
    HTTPS_PORT = 443
    HTTP_PORT = 80

    def __init__(self, socket):
        self.__socket = socket
        self.__timeout = False
        self.__timeoutThreadID = -1
        self.__maxTransmission = 100
        self.__isFirstResponse = True
        # self.__connectionType = 'HTTP'
        print('SocketHandler:: Socket handler initialized')

    def handleRequest(self):
        while not self.__timeout and self.__maxTransmission > 0:
            requestRaw = self.__socket.recv(SocketHandler.BUFFER_SIZE)
            if requestRaw == b'':
                continue
            rqp = RequestPacket.parsePacket(requestRaw)
            print('SocketHandler:: received data: \n' + rqp.getPacket('DEBUG') + '\nrequest packet end\n')
            if rqp.getMethod().lower() == 'connect':
                print('SocketHandler:: CONNECT method detected, using HTTPS protocol')
                self.establishHTTPSConnection(rqp)
                return
            elif rqp.getMethod().lower() == 'get': # follow draft semantics
                fetchedResponse = CacheHandler.fetchResponse(rqp)
                if fetchedResponse is None: # no cache found
                    rsp = self.requestToServer(rqp)
                    print('SocketHandler:: received response: \n' + rsp.getPacket('DEBUG') + '\nresponse packet end\n')
                    if rsp.responseCode() == '200':
                        print('---------------------------------')
                        print('SocketHandler:: caching response:')
                        print('---------------------------------')
                        CacheHandler.cacheResponse(rqp, rsp) # TODO should be handled by thread
                    self.__socket.send(rsp.getPacketRaw())
                else: # cache response found
                    rqpTimeLine = rqp.getHeaderInfo('if-modified-since')
                    print(rqpTimeLine)
                    if rqpTimeLine == 'nil':
                        # forgeTime = fetchedResponse.getHeaderInfo('date')
                        rqp.modifyTime(fetchedResponse.getHeaderInfo('date'))
                        print('------------------------------------------')
                        print('SocketHandler:: check if cache is updated:')
                        print('------------------------------------------')
                        rsp = self.requestToServer(rqp)
                        if rsp.responseCode() == '200':
                            print('----------------------------------------')
                            print('SocketHandler:: new data found, caching:')
                            print('----------------------------------------')
                            CacheHandler.cacheResponse(rqp, rsp) # TODO should be handled by thread
                            self.__socket.send(rsp.getPacketRaw())
                        elif rsp.responseCode() == '304':
                            print('----------------------------')
                            print('SocketHandler:: cache is OK:')
                            print('----------------------------')
                            fetchedResponse.modifyTime(rsp.getHeaderInfo('date'))
                            self.__socket.send(fetchedResponse.getPacketRaw())
                        else:
                            print('-------------------------------------------------------')
                            print('SocketHandler:: packet is directly forwarded to client:')
                            print('-------------------------------------------------------')
                            self.__socket.send(rsp.getPacketRaw())
                    else:
                        rqpTime = TimeComparator(rqpTimeLine)
                        fetchTime = TimeComparator(fetchedResponse.getHeaderInfo('date'))
                        if rqpTime > fetchTime:
                            print('---------------------------------------------------------')
                            print('SocketHandler:: rqp > fetch, check if modified since rqp:')
                            print('---------------------------------------------------------')
                            rsp = self.requestToServer(rqp)
                            if rsp.responseCode() == '200':
                                print('----------------------------------------')
                                print('SocketHandler:: new data found, caching:')
                                print('----------------------------------------')
                                CacheHandler.cacheResponse(rqp, rsp) # TODO should be handled by thread
                            self.__socket.send(rsp.getPacketRaw())
                        else: # fetchTime > rqpTime
                            rqp.modifyTime(fetchTime)
                            print('-----------------------------------------------------------')
                            print('SocketHandler:: fetch > rqp, check if modified since fetch:')
                            print('-----------------------------------------------------------')
                            rsp = self.requestToServer(rqp)
                            if rsp.responseCode() == '200':
                                print('----------------------------------------')
                                print('SocketHandler:: new data found, caching:')
                                print('----------------------------------------')
                                CacheHandler.cacheResponse(rqp, rsp) # TODO should be handled by thread
                                self.__socket.send(rsp.getPacketRaw())
                            elif rsp.responseCode() == '304':
                                print('----------------------------------')
                                print('SocketHandler:: update cache time:')
                                print('----------------------------------')
                                fetchedResponse.modifyTime(rsp.getHeaderInfo('date'))
                                CacheHandler.cacheResponse(rqp, fetchedResponse) # TODO should be handled by thread
                                self.__socket.send(fetchedResponse)
                            elif rsp.responseCode() == '404':
                                print('-------------------------------------------')
                                print('SocketHandler:: no such file, delete cache:')
                                print('-------------------------------------------')
                                CacheHandler.deleteFromCache(rqp, rsp) # TODO should be handled by thread
                                self.__socket.send(rsp.getPacketRaw())
                            else:
                                print('-------------------------------------------------------')
                                print('SocketHandler:: packet is directly forwarded to client:')
                                print('-------------------------------------------------------')
                                self.__socket.send(rsp.getPacketRaw())

            else: # not GET nor CONNECT, request from server and reply to client, no caching required
                rsp = self.requestToServer(rqp)
                if rsp is None:
                    rsp = ResponsePacket.emptyPacket()
                self.__socket.send(rsp.getPacketRaw())


            time = rsp.getKeepLive('timeout')
            self.__timeoutThreadID += 1
            timer = TimerThread(self.__timeoutThreadID, int(time), self)
            print('SocketHandler:: timeout set for ' + time + ' seconds')
            timer.start()

            if self.__isFirstResponse:
                self.__maxTransmission = int(rsp.getKeepLive('max'))
                print('SocketHandler:: max transmission: ' + str(self.__maxTransmission))
                # if rqp.getMethod().lower() == 'connect':
                #     self.__connectionType = 'HTTPS'
                self.__isFirstResponse = False

            # if rqp.getMethod().lower() == 'get' and rsp.responseCode() == '200':
            #     CacheHandler.cacheResponse(rqp, rsp) # open thread to cache, don't spend time on connection thread

            if rqp.getConnection().lower() == 'close':
                self.__socket.close()
                print('SocketHandler:: connection to client closed\n\n')

            self.__maxTransmission -= 1
            print('SocketHandler:: transmission allowed remaining: ' + str(self.__maxTransmission))

    def requestToServer(self, rqp):
        serverAddr = gethostbyname(rqp.getHostName())

        # if rqp.getMethod().lower() == 'connect':
        #     serverPort = SocketHandler.HTTPS_PORT
        # else:
        #     serverPort = SocketHandler.HTTP_PORT
        serverPort = SocketHandler.HTTP_PORT

        serverSideSocket = socket(AF_INET, SOCK_STREAM)
        serverSideSocket.connect((serverAddr, serverPort))
        serverSideSocket.send(rqp.getPacketRaw())
        responseRaw = serverSideSocket.recv(SocketHandler.BUFFER_SIZE)
        if responseRaw is None:
            serverSideSocket.close()
            return None
        rsp = ResponsePacket.parsePacket(responseRaw)
        if rsp.getHeaderInfo('transfer-encoding').lower() == 'chunked': # TODO handle chunked data
            pass
        serverSideSocket.close()
        return rsp

    def establishHTTPSConnection(self, rqp):
        print('SocketHandler:: establishHTTPSConnection(): not build yet, returning')
        return
        serverAddr = gethostbyname(rqp.getHostName())
        serverPort = SocketHandler.HTTPS_PORT
        serverSideSocket = socket(AF_INET, SOCK_STREAM)
        serverSideSocket.connect((serverAddr, serverPort))
        serverSideSocket.send(rqp.getPacketRaw())
        responseRaw = serverSideSocket.recv(SocketHandler.BUFFER_SIZE)
        rsp = ResponsePacket.parsePacket(responseRaw)
        print('SocketHandler:: received response: \n' + rsp.getPacket('DEBUG') + '\nresponse packet end\n')

        self.__socket.send(responseRaw)
        while True: # TODO
            print('loop until end connection')
            break

    def setTimeout(self, id):
        if self.__timeoutThreadID == id:
            self.__timeout = True








#  ██  ██      ████████ ██ ███    ███ ███████     ████████ ██   ██ ██████  ███████  █████  ██████
# ████████        ██    ██ ████  ████ ██             ██    ██   ██ ██   ██ ██      ██   ██ ██   ██
#  ██  ██         ██    ██ ██ ████ ██ █████          ██    ███████ ██████  █████   ███████ ██   ██
# ████████        ██    ██ ██  ██  ██ ██             ██    ██   ██ ██   ██ ██      ██   ██ ██   ██
#  ██  ██         ██    ██ ██      ██ ███████        ██    ██   ██ ██   ██ ███████ ██   ██ ██████




import threading
from time import sleep
# no need to import SocketHandler here, otherwise it will cause a cycle

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
        print('TimeThread:: timeout for ' + str(self.__id) + ' ends')
        self.__socketHandler.setTimeout(self.__id)
