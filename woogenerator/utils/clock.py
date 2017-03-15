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
    def starStrpMktime(cls, string, fmt = wpTimeFormat ):
        """ takes a time string and a format, returns number of seconds since epoch """
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
        """ changes the offset (secs) """
        assert isinstance(offset, (int, float)), "param must be a number not %s"% type(offset)
        cls._wpSrvOffset = offset

    @classmethod
    def actStrpMktime(cls, string):
        """ takes an act formatted time string, returns number of seconds since epoch """
        assert isinstance(string, (str, unicode)), "param must be a string not %s"% type(string)
        return cls.starStrpMktime(string, cls.actTimeFormat)

    @classmethod
    def wpStrpMktime(cls, string):
        """ takes a wp formatted time string (eg. "2015-07-13 22:33:05"), returns number of seconds since epoch """
        assert isinstance(string, (str, unicode)), "param must be a string not %s"% type(string)
        return cls.starStrpMktime(string)

    @classmethod
    def actStrpMkdate(cls, string):
        """ takes an act formatted date string (eg. "13/07/2015"), returns number of seconds since epoch """
        assert isinstance(string, (str, unicode)), "param must be a string not %s"% type(string)
        return cls.starStrpMktime(string, cls.actDateFormat)

    @classmethod
    def gDriveStrpTime(cls, string):
        """ takes a gDrive formatted time string (eg. "2016-07-13 22:33:05"), returns number of seconds since epoch """
        assert isinstance(string, (str, unicode)), "param must be a string not %s"% type(string)
        return cls.starStrpMktime(string, cls.gDriveTimeFormat)

    @classmethod
    def wpTimeToString(cls, secs, fmt = wpTimeFormat):
        """ takes the nubmer of seconds since epoch and converts to wp formatted local time string """
        secs = float(secs)
        assert isinstance(secs, (int, float)), "param must be a number not %s"% type(secs)
        return time.strftime(fmt, time.localtime(secs))

    @classmethod
    def hasHappenedYet(cls, secs):
        """ takes seconds since epoch, determines if has happened yet according to overrides """
        secs = float(secs)
        assert isinstance(secs, (int, float)), "param must be a number not %s"% type(secs)
        return secs >= cls.current_tsecs()

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
