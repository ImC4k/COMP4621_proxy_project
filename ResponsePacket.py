class ResponsePacket:
    '''
    process response packet
    todo: cut by the first empty line, first half is header, the other will be data

    Members:

        __packetRaw:                            raw response packet data

        __packetSplitted:                       lines of response packet, delimited by '\r\n'

        __timeout:                              integer

        __lastModified:                         time the response data is last modified

        __transferEncoding:                     content encoding type eg chunked, compress, deflate, gzip, identity

    Constructors:

        default:                                does nothing

        parsePacket(packetRaw):                 takes entire raw packet, auto separation and initialize members

    Functions:

        setPacketRaw(packetRaw):                set raw packet data

        setPacketSplitted(packetSplitted):      set splitted packet data

        getTimeout():                           returns -1 if doesn't exist, else timeout in seconds

        getLastModified():                      returns 'nil' if doesn't exist, else last-modified string

        getTransferEncoding():                  returns 'nil' if doesn't exist, else transfer-encoding string

        getPacket():                            returns reformed packet

        getPacketRaw():                         returns raw (encoded) packet data

        getData():                              returns only the payload (strip header)

    '''

    def __init__(self):
        '''
        this should not be called directly
        instead, should use p = ResponsePacket.parsePacket(packet)
        '''
        self.__packetRaw = ''
        self.__packetSplitted = []
        self.__timeout = ''
        self.__lastModified = ''
        self.__transferEncoding = ''
        self.__cacheControl = ''
        pass

    @classmethod
    def parsePacket(cls, packetRaw):
        rp = ResponsePacket()
        packet = packetRaw.decode()
        packetSplitted = packet.split('\r\n')
        packetSplitted = packetSplitted[:-1]
        rp.setPacketSplitted(packetSplitted)
        rp.setPacketRaw(packetRaw)
        return rp

    def setPacketRaw(self, packetRaw):
        self.__packetRaw = packetRaw

    def setPacketSplitted(self, packetSplitted):
        self.__packetSplitted = packetSplitted

    def getTimeout(self):
        if self.__timeout == '':
            keepAliveLine = ''
            for ss in self.__packetSplitted:
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
            for ss in self.__packetSplitted:
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
            for ss in self.__packetSplitted:
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
            for ss in self.__packetSplitted:
                if ss[0:len('cache-control')].lower() == 'cache-control':
                    cacheControlLine = ss
                    break
            if cacheControlLine == '':
                self.__cacheControl = 'nil'
            else:
                cacheControlLineSplitted = cacheControlLine.split(' ')
                self.__cacheControl = cacheControlLineSplitted[1]
        return self.__cacheControl

    def getPacket(self):
        s = ''
        for ss in self.__packetSplitted:
            s += ss + '\r\n'
        s += '\r\n'
        return s

    def getPacketRaw(self):
        return self.__packetRaw

    def getData(self):
        pass
