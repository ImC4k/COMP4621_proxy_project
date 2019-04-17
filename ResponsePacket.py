class ResponsePacket:
    '''
    process response packet
    todo: cut by the first empty line, first half is header, the other will be data

    Members:

        __packetRaw:                            entire raw response packet data

        __headerSplitted:                       entire lines of response header, delimited by '\r\n'

        __payload:                              raw payload

        __timeout:                              integer

        __lastModified:                         time the response data is last modified

        __transferEncoding:                     content encoding type eg chunked, compress, deflate, gzip, identity

    Constructors:

        default:                                does nothing

        parsePacket(packetRaw):                 takes entire raw packet, auto separation and initialize members

    Functions:

        setPacketRaw(packetRaw):                set raw packet data

        setHeaderSplitted(headerSplitted):      set splitted packet data

        setPayload(payload):                    set payload data

        getTimeout():                           returns -1 if doesn't exist, else timeout in seconds

        getLastModified():                      returns 'nil' if doesn't exist, else last-modified string

        getTransferEncoding():                  returns 'nil' if doesn't exist, else transfer-encoding string

        getHeaderInfo(fieldName):               (update) returns value of fieldName

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

    def setPacketRaw(self, packetRaw):
        self.__packetRaw = packetRaw

    def setHeaderSplitted(self, headerSplitted):
        self.__headerSplitted = headerSplitted

    def setResponseLine(self, responseLine):
        self.__responseLine = responseLine

    def setPayload(self, payload):
        self.__payload = payload

    def getTimeout(self):
        if self.__timeout == '':
            keepAliveLine = ''
            for ss in self.__headerSplitted:
                if ss[0:len('keep-alive')].lower() == 'keep-alive':
                    keepAliveLine = ss
                    break
            if keepAliveLine == '':
                self.__timeout = -1
            else:
                keepAliveLineSplitted = keepAliveLine.split(' ')
                timeoutStr = keepAliveLineSplitted[1]
                timeoutStr = timeoutStr[len('timeout='):]
                if timeoutStr[-1] == ',':
                    timeoutStr = timeoutStr[:-1]
                self.__timeout = int(timeoutStr)
        return self.__timeout

    def getLastModified(self):
        if self.__lastModified == '':
            lastModifiedLine = ''
            for ss in self.__headerSplitted:
                if ss[0:len('last-modified')].lower() == 'last-modified':
                    lastModifiedLine = ss
                    break
            if lastModifiedLine == '':
                self.__lastModified == 'nil'
            else:
                lastModifiedLineSplitted = lastModifiedLine.split(' ')
                lastModifiedLineSplitted[1] = lastModifiedLineSplitted[1][:-1] # drop comma in 'Mon,'
                self.__lastModified = lastModifiedLineSplitted[1:-1] # drop 'last-modified' and 'GMT'
        return self.__lastModified

    def getTransferEncoding(self):
        if self.__transferEncoding == '':
            transferEncodingLine = ''
            for ss in self.__headerSplitted:
                if ss[0:len('transfer-encoding')].lower() == 'transfer-encoding':
                    transferEncodingLine = ss
                    break
            if transferEncodingLine == '':
                self.__transferEncoding = 'nil'
            else:
                transferEncodingLineSplitted = transferEncodingLine.split(' ')
                self.__transferEncoding = transferEncodingLineSplitted[1]
        return self.__transferEncoding

    def getCacheControl(self):
        if self.__cacheControl == '':
            cacheControlLine = ''
            for ss in self.__headerSplitted:
                if ss[0:len('cache-control')].lower() == 'cache-control':
                    cacheControlLine = ss
                    break
            if cacheControlLine == '':
                self.__cacheControl = 'nil'
            else:
                cacheControlLineSplitted = cacheControlLine.split(' ')
                self.__cacheControl = cacheControlLineSplitted[1]
        return self.__cacheControl

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
