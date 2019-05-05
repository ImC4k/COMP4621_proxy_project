from socket import *
from RequestPacket import RequestPacket
from ResponsePacket import ResponsePacket
from CacheHandler import CacheHandler, CacheThread
from TimeComparator import TimeComparator
from time import sleep
import errno
import threading



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

        timerThreadRunning:             a flag to close all timer thread attached to this socket handler

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
                                        receive response from server,
                                        append as list
                                        (will not close server side socket)
                                        return response packets list, server side socket

        establishHTTPSConnection(rqp):  param: (rqp : RequestPacket)
                                        use HTTPS connection instead of HTTP
                                        no caching, timeout etc, direct forwarding after CONNECT method

        onBlackList(rqp):               returns true is the request website is on access control (blocked by me)

        setTimeout(id):                 if id matches timeoutThreadID, set timeout be True

    '''

    BUFFER_SIZE = 8192 # 8KB
    HTTPS_PORT = 443
    HTTP_PORT = 80
    BANNED_SITES = None

    def __init__(self, socket):
        self.__socket = socket
        self.__timeout = False
        self.__timeoutThreadID = -1
        self.__maxTransmission = 100
        self.__isFirstResponse = True
        self.__threadRunning = threading.Event()
        self.__threadRunning.set()
        self.serverSideSocket = None
        self.serverAddr = None
        print('SocketHandler:: Socket handler initialized')

    def handleRequest(self):
        while not self.__timeout and self.__maxTransmission > 0:
            try:
                requestRaw = self.__socket.recv(SocketHandler.BUFFER_SIZE) #, MSG_DONTWAIT
            except error as e:
                if e == errno.EAGAIN: # no packet received, keep reaching out
                    continue
                else: # other exception
                    # raise e
                    print(e)
                    self.__socket.close()
                    print('SocketHandler:: connection to client closed\n\n')
                    if self.serverSideSocket is not None:
                        self.serverSideSocket.close()
                        print('SocketHandler:: connection to server closed\n\n')
                    break

            except Exception as e: # EAGAIN, no data received
                raise e
            if requestRaw == b'': # data received is empty
                continue
            rqp = RequestPacket.parsePacket(requestRaw)
            print('SocketHandler:: received request: \n' + rqp.getPacket('DEBUG') + '\nrequest packet end\n')

            if self.onBlackList(rqp):
                print('SocketHandler:: client attempted to access banned site: ' + rqp.getHostName())
                self.__socket.send(ResponsePacket.emptyPacket(rqp).getPacketRaw())
                self.__socket.close()
                print('SocketHandler:: connection to client closed\n\n')
                if self.serverSideSocket is not None:
                    self.serverSideSocket.close()
                    print('SocketHandler:: connection to server closed\n\n')
                return
            else:
                print('SocketHandler:: client access ok: ' + rqp.getHostName())

            if rqp.getMethod().lower() == 'connect': # PATH HTTPS
                print('SocketHandler:: CONNECT method detected, using HTTPS protocol')
                print('--------------')
                print('| PATH HTTPS |')
                print('--------------')
                self.establishHTTPSConnection(rqp)
                return
            elif rqp.getMethod().lower() == 'get':
                fetchedResponses, expiry = CacheHandler.fetchResponses(rqp)

                if fetchedResponses is None: # no cache found PATH A
                    try:
                        rsps = self.requestToServer(rqp)
                    except ValueError as e:
                        self.__socket.close()
                        print('SocketHandler:: connection to client closed\n\n')
                        break

                    if rsps == []: # TODO close connection if unable to retrive data
                        self.__socket.close()
                        print('SocketHandler:: connection to client closed\n\n')
                        if self.serverSideSocket is not None:
                            self.serverSideSocket.close()
                            print('SocketHandler:: connection to server closed\n\n')
                        return
                    else:
                        print('SocketHandler:: received response 1 of total ' + str(len(rsps)) + ': \n' + rsps[0].getPacket('DEBUG') + '\nresponse packet end\n')
                    if rsps[0].responseCode() == '200' or rsps[0].responseCode() == '206':
                        print('---------------------------------')
                        print('SocketHandler:: caching response:')
                        print('---------------------------------')
                        ct = CacheThread('ADD', rqp, rsps)
                        ct.start()
                        print('-----------')
                        print('| PATH AA |')
                        print('-----------')
                    else:
                        print('----------')
                        print('| PATH A |')
                        print('----------')

                    self.__respondToClient(rsps)

                else: # TODO cache response found PATH B
                    if rqp.getHeaderInfo('if-modified-since') != 'nil': # PATH BA
                        print('-----------')
                        print('| PATH BA |')
                        print('-----------')
                        try:
                            rsps = self.__handleRequestSubroutine(rqp)
                        except Exception as e:
                            print('SocketHandler:: handleRequest: error encountered, ending connection')
                            break
                    else: # PATH BB
                        if expiry is not None  and expiry != 'nil': # PATH BBA
                            currentTime = TimeComparator.currentTime()
                            expiryTime = TimeComparator(expiry)
                            if expiryTime > currentTime: # packet cached has not expired yet PATH BBAA
                                print('-------------')
                                print('| PATH BBAA |')
                                print('-------------')
                                self.__respondToClient(fetchedResponses)
                                rsps = fetchedResponses
                            else: # packet cached expired, request new data from server
                                print('-------------')
                                print('| PATH BBAB |')
                                print('-------------')
                                try:
                                    rsps = self.__handleRequestSubroutine(rqp)
                                except Exception as e:
                                    print('SocketHandler:: handleRequest: error encountered, ending connection')
                                    break
                        else: # must revalidate PATH BBB
                            fetchTimeStr = fetchedResponses[0].getHeaderInfo('date')
                            if fetchTimeStr != 'nil': # if previous fetch time is present, create if-modified-since line
                                fetchTime = TimeComparator(fetchTimeStr)
                                rqp.modifyTime(fetchTime.toString())
                            try:
                                rsps = self.__handleRequestSubroutine(rqp, _304responses=fetchedResponses)
                            except Exception as e:
                                print('SocketHandler:: handleRequest: error encountered, ending connection')
                                break

            else: # not GET nor CONNECT, request from server and reply to client, no caching required PATH C
                try:
                    rsps = self.requestToServer(rqp)
                except ValueError as e:
                    self.__socket.close()
                    print('SocketHandler:: connection to client closed\n\n')
                    break
                if rsps == []:
                    print('SocketHandler:: cannot receive response, forged a packet')
                    rsps.append(ResponsePacket.emptyPacket())
                    print('----------')
                    print('| PATH C |')
                    print('----------')
                self.__respondToClient(rsps)

            print('----------------------------------------------')
            print('SocketHandler:: packet is forwarded to client:')
            print('----------------------------------------------')
            time = rsps[0].getKeepLive('timeout')
            if time == 'nil': # default timeout 20s
                time = '20'
            self.__timeoutThreadID += 1
            timer = TimerThread(self.__timeoutThreadID, int(time), self, self.__threadRunning)
            print('SocketHandler:: set timeout:' + time + ' seconds')
            timer.start()

            if self.__isFirstResponse:
                maxTransmission = rsps[0].getKeepLive('max')
                if maxTransmission == 'nil':
                    self.__maxTransmission = 100
                else:
                    self.__maxTransmission = int(maxTransmission)
                print('SocketHandler:: set max transmission: ' + str(self.__maxTransmission))
                self.__isFirstResponse = False

            if rqp.getConnection().lower() == 'close': # close if close connection is detected
                self.__socket.close()
                print('SocketHandler:: connection to client closed\n\n')
                if self.serverSideSocket is not None:
                    self.serverSideSocket.close()
                print('SocketHandler:: connection to server closed\n\n')
                break

            self.__maxTransmission -= 1
            print('SocketHandler:: transmission allowed remaining: ' + str(self.__maxTransmission))

        # loop end, close sockets
        self.__socket.close()
        print('SocketHandler:: connection to client closed\n\n')
        if self.serverSideSocket is not None:
            self.serverSideSocket.close()
            print('SocketHandler:: connection to server closed\n\n')
        print('SocketHandler:: stopping')


    def __handleRequestSubroutine(self, rqp, _304responses=''):
        try:
            rsps = self.requestToServer(rqp)
        except Exception as e:
            print('SocketHandler:: __handleRequestSubroutine: error encountered\n\n')
            raise e

        if rsps == []:
            print('SocketHandler:: cannot receive response, forged a packet')
            rsps.append(ResponsePacket.emptyPacket())
        if rsps[0].responseCode() == '200':
            print('----------------------------------------')
            print('SocketHandler:: new data found, caching:')
            print('----------------------------------------')
            ct = CacheThread('ADD', rqp, rsps)
            ct.start()
            print('---------------------')
            print('| PATH SUBROUTINE A |')
            print('---------------------')
            self.__respondToClient(rsps)

        elif rsps[0].responseCode() == '304':
            if _304responses != '':
                rsps = _304responses
            print('---------------------')
            print('| PATH SUBROUTINE B |')
            print('---------------------')
            self.__respondToClient(rsps)

        elif rsps[0].responseCode() == '404':
            print('------------------------------------------------')
            print('SocketHandler:: no such file, delete from cache:')
            print('------------------------------------------------')
            ct = CacheThread('DEL', rqp, rsps)
            ct.start()
            print('---------------------')
            print('| PATH SUBROUTINE C |')
            print('---------------------')
            self.__respondToClient(rsps)

        else:
            print('-------------------------------------------------------')
            print('SocketHandler:: packet is directly forwarded to client:')
            print('-------------------------------------------------------')
            print('---------------------')
            print('| PATH SUBROUTINE D |')
            print('---------------------')
            self.__respondToClient(rsps)
        return rsps


    def requestToServer(self, rqp):
        rsps = [] # responses to be returned

        try:
            tempHost = rqp.getHostName().split(':')
            tempServerAddr = gethostbyname(tempHost[0])
        except Exception as e:
            print('SocketHandler:: requestToServer: failed to obtain ip for host server')
            return []
        if len(tempHost) == 2:
            serverPort = int(tempHost[1])
        else:
            serverPort = SocketHandler.HTTP_PORT

        if self.serverAddr is not None and self.serverAddr != tempServerAddr: # incoming request server address doesn't match previous request
            self.serverSideSocket.close()
            self.serverSideSocket = None
            self.timeoutThreadID += 1
            print('SocketHandler:: connection to previous server closed\n\n')

        if self.serverSideSocket is None:
            self.serverSideSocket = socket(AF_INET, SOCK_STREAM)
            try:
                self.serverSideSocket.connect((tempServerAddr, serverPort))
                self.serverAddr = tempServerAddr
            except TimeoutError as e:
                print('SocketHandler:: requestToServer: server side socket timeout')
                return []
            except Exception as e:
                print('SocketHandler:: establish HTTP connection to server failed')
                raise e

        self.serverSideSocket.send(rqp.getPacketRaw())
        responseRaw = self.serverSideSocket.recv(SocketHandler.BUFFER_SIZE) # blocking, should receive data
        if responseRaw is None:
            return []

        rsp = ResponsePacket.parsePacket(responseRaw) # Assumption first received packet should have a header
        rsps.append(rsp)

        expectedLength = rsp.getHeaderInfo('content-length')
        receivedLength = len(rsp.getPayload())
        if expectedLength == 'nil': # not specified
            receivedLength = 'nil'  # don't use as condition
        else:
            expectedLength = int(expectedLength)

        if (rsp.isChunked() or expectedLength != receivedLength) or rsp.responseCode() == '206': # handle continuous chunked data (1 header)
            sleepCount = 0
            while responseRaw[-len(b'0\r\n\r\n'):] != b'0\r\n\r\n':
                try:
                    responseRaw = self.serverSideSocket.recv(SocketHandler.BUFFER_SIZE, MSG_DONTWAIT)
                except Exception as e: # EAGAIN, no data received
                    sleep(1)
                    sleepCount += 1
                    print('SocketHandler:: requestToServer(): sleep count: ' + str(sleepCount))
                    if sleepCount == 3:
                        print('SocketHandler:: requestToServer(): Timeout')
                        break
                    continue
                if responseRaw  == b'': # same as not receiving anything, sleep and continue
                    sleep(1)
                    sleepCount += 1
                    if sleepCount == 3:
                        print('SocketHandler:: requestToServer(): Timeout')
                        break
                    continue
                else:
                    sleepCount = 0 # reset sleepCount if new data is received
                    print('--------------------------------------')
                    print('SocketHandler:: chunked data detected:')
                    print('--------------------------------------')
                    try:
                        rsp = ResponsePacket.parsePacket(responseRaw)
                        rsps.append(rsp)
                    except TypeError as e:
                        rsps.append(responseRaw)
            print('SocketHandler:: requestToServer(): ended loop')
        return rsps

    def __respondToClient(self, rsps):
        for rsp in rsps:
            try:
                self.__socket.send(rsp.getPacketRaw())
            except BrokenPipeError as e:
                if self.serverSideSocket is not None:
                    self.serverSideSocket.close()
                    print('SocketHandler:: connection to server closed\n\n')
            except AttributeError as e:
                try:
                    self.__socket.send(rsp)
                except BrokenPipeError as e:
                    if self.serverSideSocket is not None:
                        self.serverSideSocket.close()
                        print('SocketHandler:: connection to server closed\n\n')
                except Exception as e:
                    print('SocketHandler:: __respondToClient: rsp is')
                    print(rsp)
                    print('SocketHandler:: __respondToClient: rsp end')
                    raise e
            except Exception as e:
                raise e

    def establishHTTPSConnection(self, rqp):

        try:
            tempHost = rqp.getHostName().split(':')
            tempServerAddr = gethostbyname(tempHost[0])
        except Exception as e:
            print('SocketHandler:: requestToServer: failed to obtain ip for host server')
            return
        if len(tempHost) == 2:
            serverPort = int(tempHost[1])
        else:
            serverPort = SocketHandler.HTTPS_PORT

        if self.serverAddr is not None and self.serverAddr != tempServerAddr: # incoming request server address doesn't match previous request
            self.serverSideSocket.close()
            self.serverSideSocket = None
            self.timeoutThreadID += 1
            print('SocketHandler:: connection to previous server closed\n\n')

        if self.serverSideSocket is None:
            self.serverSideSocket = socket(AF_INET, SOCK_STREAM)
            try:
                self.serverSideSocket.connect((tempServerAddr, serverPort))
                self.serverAddr = tempServerAddr
            except TimeoutError as e:
                print('SocketHandler:: requestToServer: server side socket timeout')
                return
            except Exception as e:
                print('SocketHandler:: establish HTTPS connection to server failed')
                raise e

        self.__socket.send(b'HTTP/1.1 200 Connection Established\r\n\r\n')

        while not self.__timeout:
            try:
                requestRaw = self.__socket.recv(SocketHandler.BUFFER_SIZE, MSG_DONTWAIT)
                self.serverSideSocket.send(requestRaw)
            except BlockingIOError as e:
                pass
            except ConnectionResetError as e:
                self.__socket.close()
                print('SocketHandler:: connection to client closed\n\n')
                if self.serverSideSocket is not None:
                    self.serverSideSocket.close()
                print('SocketHandler:: connection to server closed\n\n')
                return
            except BrokenPipeError as e:
                self.__socket.close()
                print('SocketHandler:: connection to client closed\n\n')
                if self.serverSideSocket is not None:
                    self.serverSideSocket.close()
                print('SocketHandler:: connection to server closed\n\n')
                return
            except Exception as e: #EAGAIN
                raise e

            try:
                responseRaw = self.serverSideSocket.recv(SocketHandler.BUFFER_SIZE, MSG_DONTWAIT)
                self.__socket.send(responseRaw)
            except BlockingIOError as e:
                pass
            except ConnectionResetError as e:
                self.__socket.close()
                print('SocketHandler:: connection to client closed\n\n')
                if self.serverSideSocket is not None:
                    self.serverSideSocket.close()
                print('SocketHandler:: connection to server closed\n\n')
                return
            except BrokenPipeError as e:
                self.__socket.close()
                print('SocketHandler:: connection to client closed\n\n')
                if self.serverSideSocket is not None:
                    self.serverSideSocket.close()
                print('SocketHandler:: connection to server closed\n\n')
                return
            except Exception as e: #EAGAIN
                raise e

    def onBlackList(self, rqp):
        if SocketHandler.BANNED_SITES is None:
            with open('banned_sites', 'r') as banned_sites_file:
                SocketHandler.BANNED_SITES = banned_sites_file.read().split('\n')

        rq = rqp.getHostName().lower().split(':')[0]
        try:
            rqHost = gethostbyname(rq)
        except Exception as e:
            print('SocketHandler:: onBlackList: IP not found: ' + rq)
            return False
        for site in SocketHandler.BANNED_SITES:
            if site == '***': # put *** as last line of black list file
                break
            s = site.lower()
            try:
                if s == rq:
                    print('SocketHandler:: onBlackList: banned by name')
                    return True
                elif gethostbyname(s) == rqHost:
                    print('SocketHandler:: onBlackList: banned by IP')
                    return True
            except Exception as e:
                pass
        return False

    def setTimeout(self, id):
        if self.__timeoutThreadID == id:
            self.__timeout = True

    def closeConnection(self):
        self.__threadRunning.clear()
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

    def __init__(self, id, time, socketHandler, isRunning):
        threading.Thread.__init__(self)
        self.__id = id
        self.__time = time
        self.__socketHandler = socketHandler
        self.__isRunning = isRunning

    def run(self):
        # sleep(self.__time)
        sleepCount = 0
        while sleepCount != self.__time and self.__isRunning.is_set():
            sleep(1)
            sleepCount += 1
        if sleepCount == self.__time: # time out
            print('TimerThread:: timeout for ' + str(self.__id) + ' ends')
            try:
                self.__socketHandler.setTimeout(self.__id)
            except Exception as e:
                pass

        else: # manual stop running
            print('Timer cancelled')
