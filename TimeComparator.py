import datetime

class TimeComparator:
    '''
    do time comparison of format in http(s) packets
    format: Sat, 30 Mar 2019 12:30:18 GMT

    Members:

        time:                   datetime object

    Constructor:

        default:
            time:               pass in a string time, will convert to datetime object
                                (note that the format is guaranteed by HTTP protocol)

            dt:                 pass in a datetime object directly

        currentTime:            returns an object with current time in GMT

    Methods:

        toString():             print time

        __gt__(other):          compare 2 TimeComparator object

        __add__(secondStr):     returns a new object with time incremented by secondStr

    '''

    def __init__(self, timeStr = 0, dt = 0):
        if dt == 0:
            if timeStr == 0:
                raise Exception('TimeComparator parameter cannot be empty')
            dt = datetime.datetime.strptime(timeStr, "%a, %d %b %Y %H:%M:%S GMT")
        self.__time = dt

    @classmethod
    def currentTime(cls):
        currTime = datetime.datetime.utcnow()
        obj = TimeComparator(dt=currTime)
        return obj

    def toString(self):
        return self.__time.strftime("%a, %d %b %Y %H:%M:%S GMT")

    def __gt__(self, other):
        return self.__time > other.__time


    def __add__(self, secondStr): # tc += 'time in second'
        # format: Sat, 30 Mar 2019 12:30:18 GMT
        # format: Wed, 01 May 2019 12:21:23 GMT
        return self.__time + timedelta(seconds=int(secondStr))
