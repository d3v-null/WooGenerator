import time
from core import SanitationUtils

class TimeUtils:
    _override_time = None
    _wpSrvOffset = 0
    actSrvOffset = 0

    dateFormat = "%Y-%m-%d"
    actDateFormat = "%d/%m/%Y"
    wpTimeFormat = "%Y-%m-%d %H:%M:%S"
    msTimeFormat = "%Y-%m-%d_%H-%M-%S"
    actTimeFormat = "%d/%m/%Y %I:%M:%S %p"
    gDriveTimeFormat = "%Y-%m-%d %H:%M:%S"


    @classmethod
    def set_override_time(cls, time_struct=None):
        """ sets the override time to a local time struct or removes override """
        if time_struct:
            assert isinstance(time_struct, time.struct_time)
        cls._override_time = time_struct

    @classmethod
    def current_loctstruct(cls):
        """ returns the current local time as a time.struct_time or the
        struct_time that was set to override the curren time """
        if cls._override_time:
            return cls._override_time
        else:
            return time.gmtime()

    @classmethod
    def current_tsecs(cls):
        """ Returns the curren time in number of seconds since the epoch or the
        time that was set to override """
        if cls._override_time:
            return time.mktime(cls._override_time)
        else:
            return time.time()

    @classmethod
    def starStrptime(cls, string, fmt = wpTimeFormat ):
        string = SanitationUtils.coerceUnicode(string)
        if(string):
            try:
                tstruct = time.strptime(string, fmt)
                if(tstruct):
                    return time.mktime(tstruct)
            except:
                pass
        return 0

    @classmethod
    def setWpSrvOffset(cls, offset):
        cls._wpSrvOffset = offset

    @classmethod
    def actStrptime(cls, string):
        return cls.starStrptime(string, cls.actTimeFormat)

    # 2015-07-13 22:33:05
    @classmethod
    def wpStrptime(cls, string):
        return cls.starStrptime(string)

    @classmethod
    def actStrpdate(cls, string):
        return cls.starStrptime(string, cls.actDateFormat)

    @classmethod
    def gDriveStrpTime(cls, string):
        return cls.starStrptime(string, cls.gDriveTimeFormat)

    @classmethod
    def wpTimeToString(t, fmt = wpTimeFormat):
        return time.strftime(fmt, time.localtime(t))

    @classmethod
    def hasHappenedYet(cls, t):
        assert isinstance(t, (int, float)), "param must be an int not %s"% type(t)
        return t >= cls.current_tsecs()

    @classmethod
    def localToServerTime(cls, t, timezoneOffset = time.timezone):
        return int(t - timezoneOffset)

    @classmethod
    def serverToLocalTime(cls, t, timezoneOffset = time.timezone):
        return int(t + timezoneOffset)

    @classmethod
    def wpServerToLocalTime(cls, t):
        return cls.serverToLocalTime(t, cls._wpSrvOffset)

    @classmethod
    def actServerToLocalTime(cls, t):
        return cls.serverToLocalTime(t, cls.actSrvOffset)

    @classmethod
    def getDateStamp(cls, t=None):
        if not t:
            t=cls.current_loctstruct()
        return time.strftime(cls.dateFormat, t)

    @classmethod
    def getMsTimeStamp(cls, t=None):
        if not t:
            t=cls.current_loctstruct()
        return time.strftime(cls.msTimeFormat, t)

    @classmethod
    def getTimeStamp(cls, t=None):
        if not t:
            t=cls.current_loctstruct()
        return time.strftime(cls.wpTimeFormat, t)
