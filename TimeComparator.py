class TimeComparator:
    '''
    do time comparison of format in http(s) packets
    format: Sat, 30 Mar 2019 12:30:18 GMT
    '''

    def __init__(self, time):
        months = {
            'Jan' : 1,
            'Feb' : 2,
            'Mar' : 3,
            'Apr' : 4,
            'May' : 5,
            'Jun' : 6,
            'Jul' : 7,
            'Aug' : 8,
            'Sep' : 9,
            'Oct' : 10,
            'Nov' : 11,
            'Dec' : 12
        }
        timeSplitted = time.split(' ')
        timeSplitted = timeSplitted[1:-1] # scrap week day and GMT
        self.__day = int(timeSplitted[0])
        self.__month = months[timeSplitted[1]]
        self.__year = int(timeSplitted[2])
        clockSplitted = timeSplitted[3].split(':')
        self.__hour = int(clockSplitted[0])
        self.__minute = int(clockSplitted[1])
        self.__second = int(clockSplitted[2])


    def __gr__(self, other):
        if self.__year > other.__year:
            return True
        if self.__month > other.__month:
            return True
        if self.__day > other.__day:
            return True
        if self.__hour > other.__hour:
            return True
        if self.__minute > other.__minute:
            return True
        if self.__second > other.__second:
            return True
        return False
