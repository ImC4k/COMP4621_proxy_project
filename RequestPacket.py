class RequestPacket:
    '''
    process request packet
    todo: cut by the first empty line, first half is header, the other will be data

    Members:

        __packetRaw:                                raw request packet data

        __requestLine:                              request line, first line of the header

        __headerSplitted:                           header fields of request packet, delimited by '\r\n'

        __payload:                                  raw payload

        __method:                                   stores the method of the request packet

        __connection:                               Keep-Alive or Close

    Constructors:

        default:                                    does nothing

        parsePacket(packet):                        takes entire raw packet, auto separation, fix url and initialize members

    Functions:

        setPacketRaw(packetRaw):                    set raw packet data

        setHeaderSplitted(headerSplitted):          set splitted packet data (header fields only)

        setRequestLine(requestLine):                set request line data

        setPayload(payload):                        set payload data

        fixRequestLine():                           replace url with file path

        getFilePath(url):                           get the path of file from url eg returns '/image1.png' from 'http://www.ust.hk/image1.png'

        getLastModifiedRequestPacket():             returns the packet that check last modified time

        getHostName():                              returns server host name

        getMethod():                                returns method used in the request packet

        getConnection():                            returns connection info eg keep-alive, close

        getHeaderInfo(fieldName):                   (update) returns value of fieldName

        getPacket():                                returns reformed packet

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
        # print('enter default constructor')
        self.__packetRaw = ''
        self.__requestLine = ''
        self.__headerSplitted = []
        self.__payload = ''
        self.__method = ''
        self.__connection = ''
        pass

    @classmethod
    def parsePacket(cls, packetRaw):
        rp = RequestPacket()
        headerRaw, payload = packetRaw.split(b'\r\n\r\n')
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
            rp.setPacketRaw(rp.getPacket().encode('ascii'))
        else:
            rp.setPacketRaw(packetRaw)

        return rp

    def setPacketRaw(self, packetRaw):
        self.__packetRaw = packetRaw

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
        requestLineSplitted = self.__requestLine.split(' ')
        url = requestLineSplitted[1]
        while url[0] != '/' or url[1] == '/':
            url = url[1:] # shift one character until '/detectportal.firefox.com/success.txt'
        url = url[1:] # shift one more time to 'detectportal.firefox.com/success.txt'
        filePath = url[len(self.getHostName()):]
        print('RequestPacket:: filePath requested is: ' + filePath) # '/success.txt'
        return filePath

    def getLastModifiedRequestPacket(self):
        pass

    def getHostName(self):
        # hostLineSplitted = self.__headerSplitted[1].split(' ') # assumed host must be the second line
        hostLine = ''
        for ss in self.__headerSplitted:
            if ss[0:len('Host')] == 'Host':
                hostLine = ss
                break
        hostLineSplitted = hostLine.split(' ')
        if self.getMethod() == 'CONNECT':
            print('RequestPacket:: host is ' + hostLineSplitted[1][:-len(':443')])
            return hostLineSplitted[1][:-len(':443')]
        else:
            print('RequestPacket:: host is ' + hostLineSplitted[1])
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
                # print('DEBUG: ' + ss[0:len('Connection')])
                if ss[0:len('Connection')].lower() == 'connection':
                    connectionLine = ss
                    break
            connectionLineSplitted = connectionLine.split(' ')
            print('RequestPacket:: connectionLineSplitted: ' + str(connectionLineSplitted))
            self.__connection = connectionLineSplitted[1]
        return self.__connection


    def getPacket(self, option=''):
        s = ''
        s += self.__requestLine + '\r\n'
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

    def getRequestLine(self):
        return self.__requestLine

    def getHeaderSplitted(self):
        return self.__headerSplitted

    def getPayload(self):
        return self.__payload
