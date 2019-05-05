class RequestPacket:
    '''
    process request packet

    Members:

        __requestLine:                              request line, first line of the header

        __filePath:                                 filePath of packet

        __headerSplitted:                           header fields of request packet, delimited by '\r\n'

        __payload:                                  raw payload

        __method:                                   stores the method of the request packet

        __connection:                               Keep-Alive or Close

    Constructors:

        default:                                    does nothing

        parsePacket(packetRaw):                     takes entire raw packet, auto separation, fix url and initialize members

    Functions:

        setHeaderSplitted(headerSplitted):          set splitted packet data (header fields only)

        setRequestLine(requestLine):                set request line data

        setPayload(payload):                        set payload data

        fixRequestLine():                           replace url with file path

        getFilePath():                              get the path of file from url eg returns '/image1.png' from 'http://www.ust.hk/image1.png'

        modifyTime(time):                           change the if-modified-since field to ${time}

        getHostName():                              returns server host name

        getMethod():                                returns method used in the request packet

        getConnection():                            returns connection info eg keep-alive, close

        getHeaderInfo(fieldName):                   param: (fieldName : string)
                                                    (update) returns value of fieldName

        getVersion():                               eg HTTP/1.1

        getPacket(option=''):                       returns reformed packet option 'DEBUG' to omit printing payload

        getPacketRaw():                             returns raw (encoded) packet data

        getRequestLine():                           returns string request line

        getHeaderSplitted():                        returns list of string header fields

        getPayload():                               returns payload

    '''
    def __init__(self):
        '''
        this should not be called directly
        instead, should use p = RequestPacket.parsePacket(packet)
        '''
        self.__requestLine = ''
        self.__filePath = ''
        self.__headerSplitted = []
        self.__payload = ''
        self.__method = ''
        self.__connection = ''
        pass

    @classmethod
    def parsePacket(cls, packetRaw):
        print('\n\n')
        rp = RequestPacket()

        packetRawSplitted = packetRaw.split(b'\r\n\r\n')

        if len(packetRawSplitted) == 1:
            headerRaw = packetRawSplitted[0]
        elif len(packetRawSplitted) == 2:
            headerRaw, payload = packetRawSplitted
            rp.setPayload(payload)
        else:
            raise Exception('RequestPacket:: strange number of values unpacket: ' + str(len(packetRawSplitted)))

        header = headerRaw.decode('ascii')
        headerSplitted = header.split('\r\n')
        rp.setRequestLine(headerSplitted[0])
        rp.setHeaderSplitted(headerSplitted[1:])

        if rp.getMethod().lower() != 'connect': # file path needs to be fixed
            requestLineSplitted = headerSplitted[0].split(' ')
            requestLineSplitted[1] = rp.getFilePath()
            s = ''
            for ss in requestLineSplitted:
                s += ss + ' '
            rp.setRequestLine(s[:-1]) # drop the last extra space character
        else:
            requestLineSplitted = headerSplitted[0].split(' ')
            filePath = requestLineSplitted[1]
            filePathSplitted = filePath.split(':')
            requestLineSplitted[1] = filePathSplitted[0]
            fixedRequestLine = ''
            for ss in requestLineSplitted:
                fixedRequestLine += ss + ' '
            rp.setRequestLine(ss[:-1])

        return rp

    def setHeaderSplitted(self, headerSplitted):
        self.__headerSplitted = headerSplitted

    def setRequestLine(self, requestLine):
        self.__requestLine = requestLine

    def setPayload(self, payload):
        self.__payload = payload

    def fixRequestLine(self):
        '''
        edit 2nd field to correct filePath
        '''
        requestLineSplitted = self.__requestLine.split(' ')
        requestLineSplitted[1] = self.getFilePath()
        s = ''
        for ss in requestLineSplitted:
            s += ss + ' '
        self.setRequestLine(s[:-1]) # drop the last extra space character

    def getFilePath(self):
        '''
        assumed incoming packet is HTTP ie 2nd field starts with http://
        '''
        if self.__filePath == '':
            requestLineSplitted = self.__requestLine.split(' ')
            url = requestLineSplitted[1]
            while url[0] != '/' or url[1] == '/':
                url = url[1:] # shift one character until '/detectportal.firefox.com/success.txt'
            url = url[1:] # shift one more time to 'detectportal.firefox.com/success.txt'
            filePath = url[len(self.getHostName()):]
            self.__filePath = filePath
            return filePath
        else:
            return self.__filePath

    def modifyTime(self, time):
        index = -1 # line index where header field key is 'if-modified-since'
        for idx in range(len(self.__headerSplitted)):
            if self.__headerSplitted[idx][0:len('if-modified-since')].lower() == 'if-modified-since':
                index = idx
                break
        if index == -1: # originally no such field, append to headerSplitted
            self.__headerSplitted.append('if-modified-since: ' + time)
        else:
            self.__headerSplitted[index] = 'if-modified-since: ' + time

    def getHostName(self):
        hostLine = ''
        for ss in self.__headerSplitted:
            if ss[0:len('Host')] == 'Host':
                hostLine = ss
                break
        hostLineSplitted = hostLine.split(' ')
        return hostLineSplitted[1]

    def getMethod(self):
        if self.__method == '':
            requestLineSplitted = self.__requestLine.split(' ')
            self.__method = requestLineSplitted[0]
        return self.__method

    def getConnection(self):
        if self.__connection == '':
            connectionLine = ''
            for ss in self.__headerSplitted:
                if ss[0:len('connection')].lower() == 'connection':
                    connectionLine = ss
                    break
            connectionLineSplitted = connectionLine.split(' ')
            self.__connection = connectionLineSplitted[1]
        return self.__connection

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

    def getVersion(self):
        requestLineSplitted = self.__requestLine.split(' ')
        for ss in requestLineSplitted:
            if ss[0:len('HTTP')].lower() == 'http':
                return ss


    def getPacket(self, option=''):
        s = ''
        s += self.__requestLine + '\r\n'
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
        # request line, header splitted, payload
        packetRaw = self.__requestLine.encode('ascii') + b'\r\n'
        for ss in self.__headerSplitted:
            packetRaw += ss.encode('ascii') + b'\r\n'
        packetRaw += b'\r\n' + self.__payload
        return packetRaw

    def getRequestLine(self):
        return self.__requestLine

    def getHeaderSplitted(self):
        return self.__headerSplitted

    def getPayload(self):
        return self.__payload
