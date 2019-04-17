from socket import *
from RequestPacket import RequestPacket
from ResponsePacket import ResponsePacket

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

    Constructor:

        __init__(socket, callback):     when handleRequest() returns (connection closes),
                                        call callback function

    Methods:

        handleRequest(packet):          called by listen(),
                                        handle incoming client request,
                                        make request to server by requestToServer(),
                                        return response to client

        requestToServer():              connect to server,
                                        return response packet

        cacheResponse(responseRaw):     cache the response to a file

    '''

    BUFFER_SIZE = 8192
    HTTPS_PORT = 443
    HTTP_PORT = 80

    def __init__(self, socket):
        self.socket = socket
        self.timeout = False
        print('SocketHandler:: Socket handler initialized')

    def handleRequest(self):
        while not self.timeout:
            requestRaw = self.socket.recv(SocketHandler.BUFFER_SIZE)
            if requestRaw == b'':
                continue
            rqp = RequestPacket.parsePacket(requestRaw)
            print('SocketHandler:: received data: \n' + rqp.getPacket('DEBUG') + '\nrequest packet end\n') #DEBUG
            rsp = self.requestToServer(rqp)
            print('SocketHandler:: received response: \n' + rsp.getPacket('DEBUG') + '\nresponse packet end\n')
            self.socket.send(rsp.getPacketRaw())
            print('printing headers:')
            print(str(rqp.getHeaderSplitted()))
            print('print header splitted end')
            if rqp.getMethod().lower() == 'get':
                print('caching response')
                self.cacheResponse(rsp)

            if rqp.getConnection().lower() == 'close':
                self.socket.close()
                print('SocketHandler:: connection to client closed\n\n')

    def requestToServer(self, rqp):
        #todo handle chunked packets
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
        serverSideSocket.close()
        return rsp

    def cacheResponse(self, responseRaw):
        print('SocketHandler:: should cache the file')
        pass
