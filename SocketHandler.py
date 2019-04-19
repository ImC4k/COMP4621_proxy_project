from socket import *
from RequestPacket import RequestPacket
from ResponsePacket import ResponsePacket
from TimerThread import TimerThread
from CacheHandler import CacheHandler

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
        self.__connectionType = 'HTTP'
        print('SocketHandler:: Socket handler initialized')

    def handleRequest(self):
        while not self.__timeout and self.__maxTransmission > 0:
            requestRaw = self.__socket.recv(SocketHandler.BUFFER_SIZE)
            if requestRaw == b'':
                continue
            rqp = RequestPacket.parsePacket(requestRaw)
            print('SocketHandler:: received data: \n' + rqp.getPacket('DEBUG') + '\nrequest packet end\n')
            rsp = CacheHandler.fetchResponse(rqp)
            if rsp is None:
                rsp = self.requestToServer(rqp)
                print('SocketHandler:: received response: \n' + rsp.getPacket('DEBUG') + '\nresponse packet end\n')
                if rsp is None:
                    pass # TODO custom error response
            elif rsp == 'cache-return':
                pass # TODO custom error response
            self.__socket.send(rsp.getPacketRaw())
            print('printing headers:')
            print(str(rqp.getHeaderSplitted()))
            print('print header splitted end')


            time = rsp.getTimeout()
            self.__timeoutThreadID += 1
            timer = TimerThread(self.__timeoutThreadID, time, self)

            if self.__isFirstResponse:
                self.__maxTransmission = rsp.getKeepLive('max') - 1
                if rqp.getMethod().lower() == 'connect':
                    self.__connectionType = 'HTTPS'
                self.__isFirstResponse = False

            if rqp.getMethod().lower() == 'get' and rsp.responseCode() == '200':
                CacheHandler.cacheResponse(rqp, rsp) # TODO open thread to cache, don't spend time on connection thread

            if rqp.getConnection().lower() == 'close':
                self.__socket.close()
                print('SocketHandler:: connection to client closed\n\n')

    def requestToServer(self, rqp):
        #TODO handle chunked packets
        serverAddr = gethostbyname(rqp.getHostName())

        if rqp.getMethod().lower() == 'connect':
            serverPort = SocketHandler.HTTPS_PORT
        else:
            serverPort = SocketHandler.HTTP_PORT

        serverSideSocket = socket(AF_INET, SOCK_STREAM)
        serverSideSocket.connect((serverAddr, serverPort))
        serverSideSocket.send(rqp.getPacketRaw())
        responseRaw = serverSideSocket.recv(SocketHandler.BUFFER_SIZE) # default buffer size is 8KB
        rsp = ResponsePacket.parsePacket(responseRaw)
        # if rsp.getHeaderInfo('transfer-encoding') # TODO handle chunked data
        serverSideSocket.close()
        return rsp

    def setTimeout(self, id):
        if self.__timeoutThreadID == id:
            self.__timeout = True
