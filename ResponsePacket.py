from RequestPacket import RequestPacket

class ResponsePacket:
    '''
    process response packet
    '''

    def __init__(self):
        '''
        __responseLine:     first line of response

        __headerSplitted:   entire lines of response header, delimited by '\r\n'

        __payload:          raw payload

        __responseCode:     response code of packet
        '''
        self.__responseLine = ''
        self.__headerSplitted = []
        self.__payload = b''
        self.__responseCode = ''
        pass

    @classmethod
    def parsePacket(cls, packetRaw):
        '''
        takes entire raw packet, auto separation and initialize members

        note: packetRaw can contain chunked data,
        meaning there exists 1 header, multiple payload
        mission: reform into multiple packets, return the list of ResponsePacket objects
        '''
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
            payload = b''
            for i in range(1, len(packetRawSplitted) - 1):
                payload += packetRawSplitted[i] + b'\r\n\r\n'
            payload += packetRawSplitted[-1]
            rp.setPayload(payload)
        header = headerRaw.decode('ascii')
        headerSplitted = header.split('\r\n')
        rp.setResponseLine(headerSplitted[0])
        rp.setHeaderSplitted(headerSplitted[1:])
        return rp

    @classmethod
    def emptyPacket(cls, rqp):
        '''
        creates 404 Not Found packet

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
        '''
        change the date field to ${time}
        '''
        index = -1 # line index where header field key is 'date'
        for idx in range(len(self.__headerSplitted)):
            if self.__headerSplitted[idx][0:len('date')].lower() == 'date':
                index = idx
                break
        if index == -1: # originally no such field, append to headerSplitted
            self.__headerSplitted.append('date: ' + time)
        else:
            self.__headerSplitted[index] = 'date: ' + time

    def responseCode(self):
        if self.__responseCode == '':
            responseLineSplitted = self.__responseLine.split(' ')
            self.__responseCode = responseLineSplitted[1]
        return self.__responseCode

    def isChunked(self):
        transferEncoding = self.getHeaderInfo('transfer-encoding').lower()
        transferEncodingSplitted = transferEncoding.split(',')
        for i in range(len(transferEncodingSplitted)):
            transferEncodingSplitted[i] = transferEncodingSplitted[i].strip()
        if 'chunked' in transferEncodingSplitted:
            return True
        else:
            return False

    def getKeepLive(self, option=''):
        '''
        returns keep-alive field value
        option: timeout or max
        returns corresponding value
        return 'nil' if keep-alive is not present in packet
        '''
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
                lineSplitted = line.split(',')
                if option == 'timeout':
                    if lineSplitted[0][0:len('timeout')].strip().lower() == 'timeout':
                        return lineSplitted[0].strip()[len('timeout=') : ]
                    else:
                        return lineSplitted[1].strip()[len('timeout=') : ]
                elif option == 'max':
                    if lineSplitted[0][0:len('max')].strip().lower() == 'max':
                        return lineSplitted[0].strip()[len('max=') : ]
                    else:
                        return lineSplitted[1].strip()[len('max=') : ]
                else:
                    return 'nil'

    def getHeaderInfo(self, fieldName):
        '''
        returns value of fieldName
        '''
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
