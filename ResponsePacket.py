from RequestPacket import RequestPacket

class ResponsePacket:
    '''
    process response packet

    Members:

        __responseLine:                         first line of response

        __headerSplitted:                       entire lines of response header, delimited by '\r\n'

        __payload:                              raw payload

        __responseCode:                         response code of packet

        __isLastPacket:                         specify if this packet is the last packet of the request

    Constructors:

        default:                                does nothing

        parsePacket(packetRaw):                 param: (packetRaw : bytes)
                                                takes entire raw packet, auto separation and initialize members

        emptyPacket(rqp):                       creates 404 Not Found packet

    Functions:

        setHeaderSplitted(headerSplitted):      set splitted packet data

        setResponseLine(responseLine)           set response line

        setPayload(payload):                    set payload data

        modifyTime(time):                       change the date field to ${time}

        responseCode():                         returns string response code

        isLastPacket():                         True if this is the last packet of the response

        isChunked():                            True if this packet is part of a chunked response

        getKeepLive(option=''):                 returns keep-alive field value
                                                option: timeout or max
                                                returns corresponding value
                                                return 'nil' if keep-alive is not present in packet

        getHeaderInfo(fieldName):               param: (fieldName : string)
                                                (update) returns value of fieldName

        getPacket(option=''):                   returns string packet, option'DEBUG' to omit printing payload

        getPacketRaw():                         returns raw (encoded) packet data

        getResponseLine():                      returns string response line

        getHeaderSplitted():                    returns list of string header fields

        getPayload():                           returns raw payload (no header)
    '''

    def __init__(self):
        '''
        this should not be called directly
        instead, should use p = ResponsePacket.parsePacket(packet)
        '''
        self.__responseLine = ''
        self.__headerSplitted = []
        self.__payload = ''
        self.__responseCode = ''
        self.__isLastPacket = ''
        pass

    @classmethod
    def parsePacket(cls, packetRaw):
        '''
        note: packetRaw can contain chunked data,
        meaning there exists 1 header, multiple payload
        mission: reform into multiple packets, return the list of ResponsePacket objects
        '''
        print('ResponsePacket:: received packet:')
        print(packetRaw)
        print('\n\n')
        if packetRaw[0:len(b'HTTP')].lower() != b'http': # this raw data should be payload only, don't wrap as ResponsePacket, raise TypeError exception
            raise TypeError
        rp = ResponsePacket()
        packetRawSplitted = packetRaw.split(b'\r\n\r\n')
        if len(packetRawSplitted) == 1:
            headerRaw = packetRawSplitted[0]
        elif len(packetRawSplitted) == 2:
            headerRaw, payload = packetRawSplitted
            rp.setPayload(payload)
        else: # contains chunked data
            headerRaw = packetRawSplitted[0]
            payload = packetRaw[len(headerRaw):]
            rp.setPayload(payload)
        header = headerRaw.decode('ascii')
        headerSplitted = header.split('\r\n')
        rp.setResponseLine(headerSplitted[0])
        rp.setHeaderSplitted(headerSplitted[1:])
        return rp

    @classmethod
    def emptyPacket(cls, rqp):
        '''
        format:
        HTTP/1.1 404 Not Found
        Date: Wed, 17 Apr 2019 13:31:51 GMT
        Server: Apache
        Content-Length: 209
        Keep-Alive: timeout=5, max=100
        Connection: Keep-Alive
        Content-Type: text/html; charset=iso-8859-1
        '''
        version = rqp.getVersion()
        date = rqp.getHeaderInfo('date')
        packet = version + ' 404 Not Found\r\n'
        if date != 'nil':
            packet += 'Date: ' + date + '\r\n'
        packet += '\r\n'
        packetRaw = packet.encode('ascii')
        packetRaw += b'<!DOCTYPE html><html><head><meta charset="UTF-8"><title>oops</title></head><body><h1>Oops</h1><h1>404 Not Found</h1></body></html>'
        rp = ResponsePacket.parsePacket(packetRaw)
        return rp

    def setHeaderSplitted(self, headerSplitted):
        self.__headerSplitted = headerSplitted

    def setResponseLine(self, responseLine):
        self.__responseLine = responseLine

    def setPayload(self, payload):
        self.__payload = payload

    def modifyTime(self, time):
        index = -1 # line index where header field key is 'date'
        for idx in range(len(self.__headerSplitted)):
            if self.__headerSplitted[idx][0:len('date')].lower() == 'date':
                index = idx
                break
        if index == -1: # originally no such field, append to headerSplitted
            self.__headerSplitted.append('date: ' + time)
        else:
            self.__headerSplitted[index] = 'date: ' + time
        # self.setPacketRaw(self.getPacket().encode('ascii'))

    def responseCode(self):
        if self.__responseCode == '':
            responseLineSplitted = self.__responseLine.split(' ')
            self.__responseCode = responseLineSplitted[1]
        return self.__responseCode

    def isLastPacket(self):
        if self.__isLastPacket == '':
            if self.isChunked():
                if self.__payload[-len(b'\r\n\r\n'):] == b'\r\n\r\n':
                    self.__isLastPacket = True
                else:
                    self.__isLastPacket = False
            else:
                self.__isLastPacket = True
        return self.__isLastPacket

    def isChunked(self):
        transferEncoding = self.getHeaderInfo('transfer-encoding').lower()
        transferEncodingSplitted = transferEncoding.split(', ')
        if 'chunked' in transferEncodingSplitted:
            return True
        else:
            return False

    def getKeepLive(self, option=''):
        line = ''
        for ss in self.__headerSplitted:
            if ss[0:len('keep-alive')].lower() == 'keep-alive':
                line = ss
                break
        if line == '':
            return 'nil'
        else:
            line = line[len('keep-alive') + 2 : ]
            if option == '':
                return line
            else:
                lineSplitted = line.split(', ')
                if option == 'timeout':
                    if lineSplitted[0][0:len('timeout')].lower() == 'timeout':
                        return lineSplitted[0][len('timeout') + 1 : ]
                    else:
                        return lineSplitted[1][len('timeout') + 1 : ]
                elif option == 'max':
                    if lineSplitted[0][0:len('max')].lower() == 'max':
                        return lineSplitted[0][len('max') + 1 : ]
                    else:
                        return lineSplitted[1][len('max') + 1 : ]
                else:
                    return 'nil'

    def getHeaderInfo(self, fieldName):
        line = ''
        for ss in self.__headerSplitted:
            if ss[0:len(fieldName)].lower() == fieldName:
                line = ss
                break
        if line == '':
            return 'nil'
        else:
            return line[len(fieldName) + 2 :] # strip 'fieldName: '

    def getPacket(self, option=''):
        s = ''
        s += self.__responseLine + '\r\n'
        for ss in self.__headerSplitted:
            s += ss + '\r\n'
        s += '\r\n'
        if option == 'DEBUG':
            if self.__payload != '':
                s += 'payload is not shown here'
        elif option != 'HEADER_ONLY':
            s += self.__payload
        return s

    def getPacketRaw(self):
        packetRaw = self.__responseLine.encode('ascii') + b'\r\n'
        for ss in self.__headerSplitted:
            packetRaw += ss.encode('ascii') + b'\r\n'
        packetRaw += b'\r\n' + self.__payload
        return packetRaw

    def getResponseLine(self):
        return self.__responseLine

    def getHeaderSplitted(self):
        return self.__headerSplitted

    def getPayload(self):
        return self.__payload
