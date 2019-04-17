class RequestPacket:
    '''
    process request packet
    todo: cut by the first empty line, first half is header, the other will be data

    Members:

        __packetRaw:                                raw request packet data

        __packetSplitted:                           lines of request packet, delimited by '\r\n'

        __method:                                   stores the method of the request packet

        __connection:                               Keep-Alive or Close

    Constructors:

        default:                                    does nothing

        parsePacket(packet):                        takes entire raw packet, auto separation, fix url and initialize members

    Functions:

        setPacketRaw(packetRaw):                    set raw packet data

        setPacketSplitted(packetSplitted):          set splitted packet data

        fixRequestLine():                           replace url with file path

        getFilePath(url):                           get the path of file from url eg returns '/image1.png' from 'http://www.ust.hk/image1.png'

        getLastModifiedRequestPacket():             returns the packet that check last modified time

        getHostName():                              returns server host name

        getMethod():                                returns method used in the request packet

        getConnection():                            returns connection info eg keep-alive, close

        getPacket():                                returns reformed packet

        getPacketRaw():                             returns raw (encoded) packet data

    '''
    def __init__(self):
        '''
        this should not be called directly
        instead, should use p = RequestPacket.parsePacket(packet)
        '''
        # print('enter default constructor')
        self.__packetRaw = ''
        self.__packetSplitted = []
        self.__method = ''
        self.__connection = ''
        pass

    @classmethod
    def parsePacket(cls, packetRaw):
        rp = RequestPacket()
        packet = packetRaw.decode()
        packetSplitted = packet.split('\r\n')
        packetSplitted = packetSplitted[:-1]
        rp.setPacketSplitted(packetSplitted)
        if rp.getMethod().lower() != 'connect': # file path needs to be fixed
            rp.fixRequestLine()
            rp.setPacketRaw(rp.getPacket().encode())
        else:
            rp.setPacketRaw(packetRaw)

        return rp

    def setPacketRaw(self, packetRaw):
        self.__packetRaw = packetRaw

    def setPacketSplitted(self, packetSplitted):
        self.__packetSplitted = packetSplitted

    def fixRequestLine(self):
        '''
        edit 2nd field to correct filePath
        '''
        requestLineSplitted = self.__packetSplitted[0].split(' ')
        requestLineSplitted[1] = self.getFilePath(requestLineSplitted[1])
        s = ''
        for ss in requestLineSplitted:
            s += ss + ' '
        self.__packetSplitted[0] = s[:-1] # drop the last extra space character

    def getFilePath(self):
        '''
        assumed incoming packet is HTTP ie 2nd field starts with http://
        '''
        requestLineSplitted = self.__packetSplitted[0].split(' ')
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
        # hostLineSplitted = self.__packetSplitted[1].split(' ') # assumed host must be the second line
        hostLine = ''
        for ss in self.__packetSplitted:
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
            requestLineSplitted = self.__packetSplitted[0].split(' ')
            self.__method = requestLineSplitted[0]
        return self.__method

    def getConnection(self):
        if self.__connection == '':
            connectionLine = ''
            for ss in self.__packetSplitted:
                if ss[0:len('Connection')] == 'Connection':
                    hostLine = ss
                    break
            connectionLineSplitted = connectionLine.split(' ')
            self.__connection = connectionLineSplitted[1]
        return self.__connection


    def getPacket(self):
        s = ''
        for ss in self.__packetSplitted:
            s += ss + '\r\n'
        s += '\r\n'
        return s

    def getPacketRaw(self):
        return self.__packetRaw
