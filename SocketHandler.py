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
        self.__timerThreadRunning = threading.Event()
        self.__timerThreadRunning.set()
        print('SocketHandler:: Socket handler initialized')

    def handleRequest(self):
        serverSideSocket = None
        while not self.__timeout and self.__maxTransmission > 0:
            try:
                requestRaw = self.__socket.recv(SocketHandler.BUFFER_SIZE) #, MSG_DONTWAIT
            except error as e:
                if e == errno.EAGAIN:
                    continue
                else:
                    # raise e
                    print(e)
                    self.__socket.close()
                    print('SocketHandler:: connection to client closed\n\n')
                    if serverSideSocket is not None:
                        serverSideSocket.close()
                        print('SocketHandler:: connection to server closed\n\n')
                    break

            except Exception as e: # EAGAIN, no data received
                raise e
            if requestRaw == b'': # data received is empty
                continue
            rqp = RequestPacket.parsePacket(requestRaw)
            # print('SocketHandler:: received data: \n' + rqp.getPacket('DEBUG') + '\nrequest packet end\n')

            if self.onBlackList(rqp):
                print('SocketHandler:: client attempted to access banned site: ' + rqp.getHostName())
                self.__socket.send(ResponsePacket.emptyPacket(rqp).getPacketRaw())
                self.__socket.close()
                print('SocketHandler:: connection to client closed\n\n')
                if serverSideSocket is not None:
                    serverSideSocket.close()
                    print('SocketHandler:: connection to server closed\n\n')
                return
            else:
                print('SocketHandler:: client access ok: ' + rqp.getHostName())

            if rqp.getMethod().lower() == 'connect':
                print('SocketHandler:: CONNECT method detected, using HTTPS protocol')
                print('--------------')
                print('| PATH HTTPS |')
                print('--------------')
                self.establishHTTPSConnection(rqp)
                return
            elif rqp.getMethod().lower() == 'get':
                fetchedResponses = CacheHandler.fetchResponses(rqp)
                if fetchedResponses is None: # no cache found
                    try:
                        rsps, serverSideSocket = self.requestToServer(rqp)
                    except ValueError as e:
                        self.__socket.close()
                        print('SocketHandler:: connection to client closed\n\n')
                        break
                    if rsps == []:
                        print('SocketHandler:: cannot receive response, forged a packet')
                        rsps.append(ResponsePacket.emptyPacket())
                    print('SocketHandler:: received response 1: \n' + rsps[0].getPacket('DEBUG') + '\nresponse packet end\n')
                    if rsps[0].responseCode() == '200':
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
                    self.__respondToClient(rsps, serverSideSocket)

                else: # cache response found
                    rqpTimeLine = rqp.getHeaderInfo('if-modified-since')
                    if rqpTimeLine == 'nil':
                        rqp.modifyTime(fetchedResponses[0].getHeaderInfo('date'))
                        print('------------------------------------------')
                        print('SocketHandler:: check if cache is updated:')
                        print('------------------------------------------')
                        try:
                            rsps, serverSideSocket = self.requestToServer(rqp)
                        except ValueError as e:
                            self.__socket.close()
                            print('SocketHandler:: connection to client closed\n\n')
                            break
                        if rsps == []:
                            print('SocketHandler:: cannot receive response, forged a packet')
                            rsps.append(ResponsePacket.emptyPacket())
                        if rsps[0].responseCode() == '200':
                            print('----------------------------------------')
                            print('SocketHandler:: new data found, caching:')
                            print('----------------------------------------')
                            ct = CacheThread('ADD', rqp, rsps)
                            ct.start()
                            print('------------')
                            print('| PATH BAA |')
                            print('------------')
                            self.__respondToClient(rsps, serverSideSocket)

                        elif rsps[0].responseCode() == '304':
                            print('----------------------------')
                            print('SocketHandler:: cache is OK:')
                            print('----------------------------')
                            if fetchedResponses[0].responseCode() != '206': # only the first element is a ResponsePacket object
                                fetchedResponses[0].modifyTime(rsps[0].getHeaderInfo('date'))
                            else:
                                for fetchedResponse in fetchedResponses: # change time for all packets
                                    fetchedResponse.modifyTime(rsps[0].getHeaderInfo('date'))
                            ct = CacheThread(rqp, fetchedResponses, 'ADD')
                            ct.start()
                            print('------------')
                            print('| PATH BAB |')
                            print('------------')
                            self.__respondToClient(fetchedResponses, serverSideSocket)

                        elif rsps[0].responseCode() == '404':
                            print('-------------------------------------------')
                            print('SocketHandler:: no such file, delete cache:')
                            print('-------------------------------------------')
                            ct = CacheThread('DEL', rqp, rsps)
                            ct.start()
                            print('------------')
                            print('| PATH BAC |')
                            print('------------')
                            self.__respondToClient(rsps, serverSideSocket)

                        else:
                            print('---------------------------------------------------------')
                            print('SocketHandler:: packets are directly forwarded to client:')
                            print('---------------------------------------------------------')
                            print('------------')
                            print('| PATH BAD |')
                            print('------------')
                            self.__respondToClient(rsps, serverSideSocket)

                    else:
                        rqpTime = TimeComparator(rqpTimeLine)
                        fetchTime = TimeComparator(fetchedResponses[0].getHeaderInfo('date'))
                        if rqpTime > fetchTime:
                            print('---------------------------------------------------------')
                            print('SocketHandler:: rqp > fetch, check if modified since rqp:')
                            print('---------------------------------------------------------')
                            try:
                                rsps, serverSideSocket = self.requestToServer(rqp)
                            except ValueError as e:
                                self.__socket.close()
                                print('SocketHandler:: connection to client closed\n\n')
                                break
                            if rsps == []:
                                print('SocketHandler:: cannot receive response, forged a packet')
                                rsps.append(ResponsePacket.emptyPacket())
                            if rsps[0].responseCode() == '200':
                                print('----------------------------------------')
                                print('SocketHandler:: new data found, caching:')
                                print('----------------------------------------')
                                ct = CacheThread('ADD', rqp, rsps)
                                ct.start()
                                print('-------------')
                                print('| PATH BBBA |')
                                print('-------------')
                                self.__respondToClient(rsps, serverSideSocket)

                            elif rsps[0].responseCode() == '304':
                                print('----------------------------------')
                                print('SocketHandler:: update cache time:')
                                print('----------------------------------')
                                for fetchedResponse in fetchedResponses:
                                    try:
                                        fetchedResponse.modifyTime(rsps[0].getHeaderInfo('date'))
                                    except AttributeError as e:
                                        continue
                                ct = CacheThread('ADD', rqp, rsps)
                                ct.start()
                                print('-------------')
                                print('| PATH BBBB |')
                                print('-------------')
                                self.__respondToClient(fetchedResponses, serverSideSocket)

                            elif rsps[0].responseCode() == '404':
                                print('-------------------------------------------')
                                print('SocketHandler:: no such file, delete cache:')
                                print('-------------------------------------------')
                                ct = CacheThread('DEL', rqp, rsps)
                                ct.start()
                                print('-------------')
                                print('| PATH BBBC |')
                                print('-------------')
                                self.__respondToClient(rsps, serverSideSocket)

                            else:
                                print('-------------------------------------------------------')
                                print('SocketHandler:: packet is directly forwarded to client:')
                                print('-------------------------------------------------------')
                                print('-------------')
                                print('| PATH BBBD |')
                                print('-------------')
                                self.__respondToClient(rsps, serverSideSocket)

                        else: # fetchTime > rqpTime
                            rqp.modifyTime(fetchTime)
                            print('-----------------------------------------------------------')
                            print('SocketHandler:: fetch > rqp, check if modified since fetch:')
                            print('-----------------------------------------------------------')
                            try:
                                rsps, serverSideSocket = self.requestToServer(rqp)
                            except ValueError as e:
                                self.__socket.close()
                                print('SocketHandler:: connection to client closed\n\n')
                                break

                            if rsps == []:
                                print('SocketHandler:: cannot receive response, forged a packet')
                                rsps.append(ResponsePacket.emptyPacket())
                            if rsps[0].responseCode() == '200':
                                print('----------------------------------------')
                                print('SocketHandler:: new data found, caching:')
                                print('----------------------------------------')
                                ct = CacheThread('ADD', rqp, rsps)
                                ct.start()
                                print('-------------')
                                print('| PATH BBAA |')
                                print('-------------')
                                self.__respondToClient(rsps, serverSideSocket)

                            elif rsps[0].responseCode() == '304':
                                print('----------------------------------')
                                print('SocketHandler:: update cache time:')
                                print('----------------------------------')
                                for fetchedResponse in fetchedResponses:
                                    try:
                                        fetchedResponse.modifyTime(rsps[0].getHeaderInfo('date'))
                                    except AttributeError as e:
                                        continue
                                ct = CacheThread('ADD', rqp, rsps)
                                ct.start()
                                print('-------------')
                                print('| PATH BBAB |')
                                print('-------------')
                                self.__respondToClient(fetchedResponses, serverSideSocket)

                            elif rsps[0].responseCode() == '404':
                                print('------------------------------------------------')
                                print('SocketHandler:: no such file, delete from cache:')
                                print('------------------------------------------------')
                                ct = CacheThread('DEL', rqp, rsps)
                                ct.start()
                                print('-------------')
                                print('| PATH BBAC |')
                                print('-------------')
                                self.__respondToClient(rsps, serverSideSocket)

                            else:
                                print('-------------------------------------------------------')
                                print('SocketHandler:: packet is directly forwarded to client:')
                                print('-------------------------------------------------------')
                                print('-------------')
                                print('| PATH BBAD |')
                                print('-------------')
                                self.__respondToClient(rsps, serverSideSocket)

            else: # not GET nor CONNECT, request from server and reply to client, no caching required
                try:
                    rsps, serverSideSocket = self.requestToServer(rqp)
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
                self.__respondToClient(rsps, serverSideSocket)

            print('----------------------------------------------')
            print('SocketHandler:: packet is forwarded to client:')
            print('----------------------------------------------')
            time = rsps[0].getKeepLive('timeout')
            if time == 'nil': # default timeout 100s
                time = '20'
            self.__timeoutThreadID += 1
            timer = TimerThread(self.__timeoutThreadID, int(time), self, self.__timerThreadRunning)
            print('SocketHandler:: timeout set for ' + time + ' seconds')
            timer.start()

            if self.__isFirstResponse:
                maxTransmission = rsps[0].getKeepLive('max')
                if maxTransmission == 'nil':
                    self.__maxTransmission = 100
                else:
                    self.__maxTransmission = int(maxTransmission)
                print('SocketHandler:: max transmission: ' + str(self.__maxTransmission))
                self.__isFirstResponse = False

            if rqp.getConnection().lower() == 'close': # close if close connection is detected
                self.__socket.close()
                print('SocketHandler:: connection to client closed\n\n')
                serverSideSocket.close()
                print('SocketHandler:: connection to server closed\n\n')
                break

            self.__maxTransmission -= 1
            print('SocketHandler:: transmission allowed remaining: ' + str(self.__maxTransmission))
        # loop end, close sockets
        self.__socket.close()
        print('SocketHandler:: connection to client closed\n\n')
        if serverSideSocket is not None:
            serverSideSocket.close()
            print('SocketHandler:: connection to server closed\n\n')
        print('SocketHandler:: stopping')

    def requestToServer(self, rqp, serverSideSocket = ''):
        rsps = [] # responses to be returned
        if serverSideSocket == '':
            try:
                serverAddr = gethostbyname(rqp.getHostName())
            except Exception as e:
                print('SocketHandler:: requestToServer: failed to obtain ip for host server')
                print('closing this connection')
                self.__socket.close()
                print('SocketHandler:: connection to client closed\n\n')
                return []

            serverPort = SocketHandler.HTTP_PORT

            serverSideSocket = socket(AF_INET, SOCK_STREAM)
            try:
                serverSideSocket.connect((serverAddr, serverPort))
            except TimeoutError as e:
                print('SocketHandler:: requestToServer: server side socket timeout')
                return []
        serverSideSocket.send(rqp.getPacketRaw())
        responseRaw = serverSideSocket.recv(SocketHandler.BUFFER_SIZE) # blocking, should receive data
        if responseRaw is None:
            return []

        rsp = ResponsePacket.parsePacket(responseRaw)
        rsps.append(rsp)

        expectedLength = rsp.getHeaderInfo('content-length')
        receivedLength = len(rsp.getPayload())
        if expectedLength == 'nil': # not specified
            receivedLength = 'nil'  # don't use as condition
        else:
            expectedLength = int(expectedLength)

        if (rsp.isChunked() or expectedLength != receivedLength) or rsp.responseCode() != '206': # handle continuous chunked data (1 header)
            sleepCount = 0
            while responseRaw[-len(b'0\r\n\r\n'):] != b'0\r\n\r\n':
                try:
                    responseRaw = serverSideSocket.recv(SocketHandler.BUFFER_SIZE, MSG_DONTWAIT)
                except Exception as e: # EAGAIN, no data received
                    sleep(1)
                    sleepCount += 1
                    print('SocketHandler:: requestToServer(): sleep count: ' + str(sleepCount))
                    if sleepCount == 2:
                        print('SocketHandler:: requestToServer(): Timeout')
                        break
                    continue
                if responseRaw  == b'': # same as not receiving anything, sleep and continue
                    sleep(1)
                    sleepCount += 1
                    if sleepCount == 2:
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
        return rsps, serverSideSocket

    def __respondToClient(self, rsps, serverSideSocket):
        for rsp in rsps:
            try:
                self.__socket.send(rsp.getPacketRaw())
            except BrokenPipeError as e:
                serverSideSocket.close()
                print('SocketHandler:: connection to server closed\n\n')
            except AttributeError as e:
                try:
                    self.__socket.send(rsp)
                except BrokenPipeError as e:
                    serverSideSocket.close()
                    print('SocketHandler:: connection to server closed\n\n')
                except Exception as e:
                    raise e
            except Exception as e:
                raise e

    def establishHTTPSConnection(self, rqp):

        serverAddr = gethostbyname(rqp.getHostName())
        serverPort = SocketHandler.HTTPS_PORT
        serverSideSocket = socket(AF_INET, SOCK_STREAM)
        try:
            serverSideSocket.connect((serverAddr, serverPort))
        except Exception as e:
            print('SocketHandler:: establish HTTPS connection to server failed')
            raise e
        self.__socket.send(b'HTTP/1.1 200 Connection Established\r\n\r\n')

        while True and not self.__timeout:
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

    def onBlackList(self, rqp):
        if SocketHandler.BANNED_SITES is None:
            with open('banned_sites', 'r') as banned_sites_file:
                SocketHandler.BANNED_SITES = banned_sites_file.read().split('\n')
        for site in SocketHandler.BANNED_SITES:
            if site == '***': # put *** as last line of black list file
                break
            s = site.lower()
            rq = rqp.getHostName().lower().split(':')[0]
            try:
                if s == rq or gethostbyname(s) == gethostbyname(rq):
                    return True
            except Exception as e:
                pass
        return False

    def setTimeout(self, id):
        if self.__timeoutThreadID == id:
            self.__timeout = True

    def closeConnection(self):
        self.__timerThreadRunning.clear()
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
