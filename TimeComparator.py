import datetime

class TimeComparator:
    '''
    do time comparison of format in http(s) packets
    format: Sat, 30 Mar 2019 12:30:18 GMT
    '''

    def __init__(self, timeStr = 0, dt = 0):
        '''
        __time:     pass in a string time, will convert to datetime object
                    (note that the format is guaranteed by HTTP protocol)

        __dt:       pass in a datetime object directly
        '''
        if dt == 0:
            if timeStr == 0:
                raise Exception('TimeComparator parameter cannot be empty')
            dt = datetime.datetime.strptime(timeStr, "%a, %d %b %Y %H:%M:%S GMT")
        self.__time = dt

    @classmethod
    def currentTime(cls):
        '''
        returns an object with current time in GMT
        '''
        currTime = datetime.datetime.utcnow()
        obj = cls(dt=currTime)
        return obj

    def toString(self):
        return self.__time.strftime("%a, %d %b %Y %H:%M:%S GMT")

    def __gt__(self, other):
        return self.__time > other.__time


    def __add__(self, secondStr):
        '''
        returns a new object with time incremented by secondStr
        '''
        time = self.__time + datetime.timedelta(seconds=int(secondStr))
        obj = TimeComparator(dt=time)
        return obj
