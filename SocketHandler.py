from socket import *
from RequestPacket import RequestPacket
from ResponsePacket import ResponsePacket
from CacheHandler import CacheHandler, CacheThread
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

        establishHTTPSConnection(rqp):  param: (rqp : RequestPacket)
                                        use HTTPS connection instead of HTTP
                                        no caching, timeout etc, direct forwarding after CONNECT method

        setTimeout(id):                 if id matches timeoutThreadID, set timeout be True

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
        print('SocketHandler:: Socket handler initialized')

    def handleRequest(self):
        while not self.__timeout and self.__maxTransmission > 0:
            try:
                requestRaw = self.__socket.recv(SocketHandler.BUFFER_SIZE, MSG_DONTWAIT)
            except Exception as e: # EAGAIN, no data received
                continue
            if requestRaw == b'': # data received is empty
                continue
            rqp = RequestPacket.parsePacket(requestRaw)
            print('SocketHandler:: received data: \n' + rqp.getPacket('DEBUG') + '\nrequest packet end\n')
            if rqp.getMethod().lower() == 'connect':
                print('SocketHandler:: CONNECT method detected, using HTTPS protocol')
                print('--------------')
                print('| PATH HTTPS |')
                print('--------------')
                self.establishHTTPSConnection(rqp)
                return
            elif rqp.getMethod().lower() == 'get':
                fetchedResponse = CacheHandler.fetchResponse(rqp)
                if fetchedResponse is None: # no cache found
                    rsp = self.requestToServer(rqp)
                    if rsp is None:
                        print('SocketHandler:: cannot receive response, forged a packet')
                        rsp = ResponsePacket.emptyPacket()
                    print('SocketHandler:: received response: \n' + rsp.getPacket('DEBUG') + '\nresponse packet end\n')
                    if rsp.responseCode() == '200':
                        print('---------------------------------')
                        print('SocketHandler:: caching response:')
                        print('---------------------------------')
                        ct = CacheThread(rqp, rsp, 'ADD')
                        ct.start()
                        print('-----------')
                        print('| PATH AA |')
                        print('-----------')
                    else:
                        print('----------')
                        print('| PATH A |')
                        print('----------')
                    self.__socket.send(rsp.getPacketRaw())
                else: # cache response found
                    rqpTimeLine = rqp.getHeaderInfo('if-modified-since')
                    if rqpTimeLine == 'nil':
                        rqp.modifyTime(fetchedResponse.getHeaderInfo('date'))
                        print('------------------------------------------')
                        print('SocketHandler:: check if cache is updated:')
                        print('------------------------------------------')
                        rsp = self.requestToServer(rqp)
                        if rsp is None:
                            print('SocketHandler:: cannot receive response, forged a packet')
                            rsp = ResponsePacket.emptyPacket()
                        if rsp.responseCode() == '200':
                            print('----------------------------------------')
                            print('SocketHandler:: new data found, caching:')
                            print('----------------------------------------')
                            ct = CacheThread(rqp, rsp, 'ADD')
                            ct.start()
                            print('------------')
                            print('| PATH BAA |')
                            print('------------')
                            self.__socket.send(rsp.getPacketRaw())
                        elif rsp.responseCode() == '304':
                            print('----------------------------')
                            print('SocketHandler:: cache is OK:')
                            print('----------------------------')
                            fetchedResponse.modifyTime(rsp.getHeaderInfo('date'))
                            ct = CacheThread(rqp, fetchedResponse, 'ADD')
                            ct.start()
                            print('------------')
                            print('| PATH BAB |')
                            print('------------')
                            self.__socket.send(fetchedResponse.getPacketRaw())
                        elif rsp.responseCode() == '404':
                            print('-------------------------------------------')
                            print('SocketHandler:: no such file, delete cache:')
                            print('-------------------------------------------')
                            ct = CacheThread(rqp, rsp, 'DEL')
                            ct.start()
                            print('------------')
                            print('| PATH BAC |')
                            print('------------')
                            self.__socket.send(rsp.getPacketRaw())
                        else:
                            print('-------------------------------------------------------')
                            print('SocketHandler:: packet is directly forwarded to client:')
                            print('-------------------------------------------------------')
                            print('------------')
                            print('| PATH BAD |')
                            print('------------')
                            self.__socket.send(rsp.getPacketRaw())
                    else:
                        rqpTime = TimeComparator(rqpTimeLine)
                        fetchTime = TimeComparator(fetchedResponse.getHeaderInfo('date'))
                        if rqpTime > fetchTime:
                            print('---------------------------------------------------------')
                            print('SocketHandler:: rqp > fetch, check if modified since rqp:')
                            print('---------------------------------------------------------')
                            rsp = self.requestToServer(rqp)
                            if rsp is None:
                                print('SocketHandler:: cannot receive response, forged a packet')
                                rsp = ResponsePacket.emptyPacket()
                            if rsp.responseCode() == '200':
                                print('----------------------------------------')
                                print('SocketHandler:: new data found, caching:')
                                print('----------------------------------------')
                                ct = CacheThread(rqp, rsp, 'ADD')
                                ct.start()
                                print('-------------')
                                print('| PATH BBBA |')
                                print('-------------')
                                self.__socket.send(rsp.getPacketRaw())
                            elif rsp.responseCode() == '304':
                                print('----------------------------------')
                                print('SocketHandler:: update cache time:')
                                print('----------------------------------')
                                fetchedResponse.modifyTime(rsp.getHeaderInfo('date'))
                                ct = CacheThread(rqp, rsp, 'ADD')
                                ct.start()
                                print('-------------')
                                print('| PATH BBBB |')
                                print('-------------')
                                self.__socket.send(fetchedResponse.getPacketRaw())
                            elif rsp.responseCode() == '404':
                                print('-------------------------------------------')
                                print('SocketHandler:: no such file, delete cache:')
                                print('-------------------------------------------')
                                ct = CacheThread(rqp, rsp, 'DEL')
                                ct.start()
                                print('-------------')
                                print('| PATH BBBC |')
                                print('-------------')
                                self.__socket.send(rsp.getPacketRaw())
                            else:
                                print('-------------------------------------------------------')
                                print('SocketHandler:: packet is directly forwarded to client:')
                                print('-------------------------------------------------------')
                                print('-------------')
                                print('| PATH BBBD |')
                                print('-------------')
                                self.__socket.send(rsp.getPacketRaw())
                        else: # fetchTime > rqpTime
                            rqp.modifyTime(fetchTime)
                            print('-----------------------------------------------------------')
                            print('SocketHandler:: fetch > rqp, check if modified since fetch:')
                            print('-----------------------------------------------------------')
                            rsp = self.requestToServer(rqp)
                            if rsp is None:
                                print('SocketHandler:: cannot receive response, forged a packet')
                                rsp = ResponsePacket.emptyPacket()
                            if rsp.responseCode() == '200':
                                print('----------------------------------------')
                                print('SocketHandler:: new data found, caching:')
                                print('----------------------------------------')
                                ct = CacheThread(rqp, rsp, 'ADD')
                                ct.start()
                                print('-------------')
                                print('| PATH BBAA |')
                                print('-------------')
                                self.__socket.send(rsp.getPacketRaw())
                            elif rsp.responseCode() == '304':
                                print('----------------------------------')
                                print('SocketHandler:: update cache time:')
                                print('----------------------------------')
                                fetchedResponse.modifyTime(rsp.getHeaderInfo('date'))
                                ct = CacheThread(rqp, rsp, 'ADD')
                                ct.start()
                                print('-------------')
                                print('| PATH BBAB |')
                                print('-------------')
                                self.__socket.send(fetchedResponse)
                            elif rsp.responseCode() == '404':
                                print('-------------------------------------------')
                                print('SocketHandler:: no such file, delete cache:')
                                print('-------------------------------------------')
                                ct = CacheThread(rqp, rsp, 'DEL')
                                ct.start()
                                print('-------------')
                                print('| PATH BBAC |')
                                print('-------------')
                                self.__socket.send(rsp.getPacketRaw())
                            else:
                                print('-------------------------------------------------------')
                                print('SocketHandler:: packet is directly forwarded to client:')
                                print('-------------------------------------------------------')
                                print('-------------')
                                print('| PATH BBAD |')
                                print('-------------')
                                self.__socket.send(rsp.getPacketRaw())

            else: # not GET nor CONNECT, request from server and reply to client, no caching required
                rsp = self.requestToServer(rqp)
                if rsp is None:
                    print('SocketHandler:: cannot receive response, forged a packet')
                    rsp = ResponsePacket.emptyPacket()
                    print('----------')
                    print('| PATH C |')
                    print('----------')
                self.__socket.send(rsp.getPacketRaw())

            # self.__socket.close() # DEBUG
            # return # DEBUG
            print('----------------------------------------------')
            print('SocketHandler:: packet is forwarded to client:')
            print('----------------------------------------------')
            time = rsp.getKeepLive('timeout')
            if time == 'nil': # default timeout 100s
                time = '100'
            self.__timeoutThreadID += 1
            timer = TimerThread(self.__timeoutThreadID, int(time), self)
            print('SocketHandler:: timeout set for ' + time + ' seconds')
            timer.start()

            if self.__isFirstResponse:
                maxTransmission = rsp.getKeepLive('max')
                if maxTransmission == 'nil':
                    self.__maxTransmission = 100
                else:
                    self.__maxTransmission = int(maxTransmission)
                print('SocketHandler:: max transmission: ' + str(self.__maxTransmission))
                self.__isFirstResponse = False

            if rqp.getVersion().lower() != 'HTTP/1.1' and rqp.getConnection().lower() == 'close':
                self.__socket.close()
                print('SocketHandler:: connection to client closed\n\n')

            self.__maxTransmission -= 1
            print('SocketHandler:: transmission allowed remaining: ' + str(self.__maxTransmission))

    def requestToServer(self, rqp):
        serverAddr = gethostbyname(rqp.getHostName())
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
            print('-----------------------------')
            print('|                           |')
            print('|                           |')
            print('|  UNHANDLED CHUNKED DATA!  |')
            print('|                           |')
            print('|                           |')
            print('-----------------------------')
            pass
        serverSideSocket.close()
        return rsp

    def establishHTTPSConnection(self, rqp):

        serverAddr = gethostbyname(rqp.getHostName())
        serverPort = SocketHandler.HTTPS_PORT # BUG
        serverSideSocket = socket(AF_INET, SOCK_STREAM)
        try:
            serverSideSocket.connect((serverAddr, serverPort))
        except Exception as e:
            print('SocketHandler:: establish HTTPS connection to server failed')
            raise e
        self.__socket.send(b'HTTP/1.1 200 Connection Established\r\n\r\n')

        while True: # TODO HTTPS connection
            try:
                requestRaw = self.__socket.recv(SocketHandler.BUFFER_SIZE, MSG_DONTWAIT)
                serverSideSocket.send(requestRaw)
            except Exception as e: #EAGAIN
                pass

            try:
                responseRaw = serverSideSocket.recv(SocketHandler.BUFFER_SIZE, MSG_DONTWAIT)
                self.__socket.send(responseRaw)
            except Exception as e: #EAGAIN
                pass


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
