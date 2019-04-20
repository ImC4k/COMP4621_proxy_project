from RequestPacket import RequestPacket

class ResponsePacket:
    '''
    process response packet

    Members:

        __packetRaw:                            entire raw response packet data

        __headerSplitted:                       entire lines of response header, delimited by '\r\n'

        __payload:                              raw payload

        __timeout:                              integer

        __lastModified:                         time the response data is last modified

        __transferEncoding:                     content encoding type eg chunked, compress, deflate, gzip, identity

    Constructors:

        default:                                does nothing

        parsePacket(packetRaw):                 param: (packetRaw : bytes)
                                                takes entire raw packet, auto separation and initialize members

    Functions:

        setPacketRaw(packetRaw):                set raw packet data

        setHeaderSplitted(headerSplitted):      set splitted packet data

        setPayload(payload):                    set payload data

        modifyTime(time):                       change the date field to ${time}

        responseCode():                         returns string response code

        getKeepLive(option=''):                 returns keep-alive field value
                                                option: timeout or max
                                                returns corresponding value
                                                return 'nil' if keep-alive is not present in packet

        getHeaderInfo(fieldName):               param: (fieldName : string)
                                                (update) returns value of fieldName

        getPacket():                            returns string packet

        getPacketRaw():                         returns raw (encoded) packet data

        getResponseLine():                      returns string response line

        getHeader():                            returns list of string header fields

        getPayload():                           returns raw payload (no header)
    '''

    def __init__(self):
        '''
        this should not be called directly
        instead, should use p = ResponsePacket.parsePacket(packet)
        '''
        self.__packetRaw = ''
        self.__responseLine = ''
        self.__headerSplitted = []
        self.__payload = ''
        self.__responseCode = ''
        self.__timeout = ''
        self.__lastModified = ''
        self.__transferEncoding = ''
        self.__cacheControl = ''
        pass

    @classmethod
    def parsePacket(cls, packetRaw):
        rp = ResponsePacket()
        headerRaw, payload = packetRaw.split(b'\r\n\r\n')
        header = headerRaw.decode('ascii')
        headerSplitted = header.split('\r\n')
        rp.setResponseLine(headerSplitted[0])
        rp.setHeaderSplitted(headerSplitted[1:])
        rp.setPayload(payload)
        rp.setPacketRaw(packetRaw)
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
        rp = ResponsePacket()


    def setPacketRaw(self, packetRaw):
        self.__packetRaw = packetRaw

    def setHeaderSplitted(self, headerSplitted):
        self.__headerSplitted = headerSplitted

    def setResponseLine(self, responseLine):
        self.__responseLine = responseLine

    def setPayload(self, payload):
        self.__payload = payload

    def modifyTime(self, time):
        index = -1 # line index where header field key is 'date'
        for idx in len(self.__headerSplitted):
            if self.__headerSplitted[idx][0:len('date')].lower() == 'date':
                index = idx
                break
        if index == -1: # originally no such field, append to headerSplitted
            self.__headerSplitted.append('date: ' + time)
        else:
            self.__headerSplitted[index] = 'date: ' + time
        self.setPacketRaw(self.getPacket().encode('ascii'))

    def responseCode(self):
        if self.__responseCode == '':
            responseLineSplitted = self.__responseLine.split(' ')
            self.__responseCode = responseLineSplitted[1]
        return self.__responseCode

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
                    return 'invalid'

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
        else:
            s += self.__payload
        return s

    def getPacketRaw(self):
        return self.__packetRaw

    def getResponseLine(self):
        return self.__responseLine

    def getHeaderSplitted(self):
        return self.__headerSplitted

    def getPayload(self):
        return self.__payload
