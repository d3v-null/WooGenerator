"""
Utilities for time-related tasks
"""
import datetime
import time
from numbers import Number

from core import SanitationUtils


class TimeUtils(object):
    """
    Utilities for time-related tasks
    """
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
    def star_strp_mktime(cls, string, fmt=wpTimeFormat):
        # type: (basestring, basestring) -> int
        """ takes a time string and a format, returns number of seconds since epoch """
        if string:
            if isinstance(string, datetime.datetime):
                # sometimes yaml does strings as datetime.datetime
                string.microsecond = 0
                string = str(string)
            string = SanitationUtils.coerce_unicode(string)
            tstruct = time.strptime(string, fmt)
            if tstruct:
                return time.mktime(tstruct)
        return 0

    @classmethod
    def set_wp_srv_offset(cls, offset):
        """ changes the offset (secs) """
        assert isinstance(offset, (int, float)
                          ), "param must be a number not %s" % type(offset)
        cls._wpSrvOffset = offset

    @classmethod
    def act_strp_mktime(cls, string):
        """ takes an act formatted time string, returns number of seconds since epoch """
        assert isinstance(
            string, basestring), "param must be a string not %s" % type(string)
        return cls.star_strp_mktime(string, cls.actTimeFormat)

    @classmethod
    def wp_strp_mktime(cls, string):
        """ takes a wp formatted time string (eg. "2015-07-13 22:33:05"),
        returns number of seconds since epoch """
        return cls.star_strp_mktime(string)

    @classmethod
    def act_strp_mkdate(cls, string):
        """ takes an act formatted date string (eg. "13/07/2015"),
        returns number of seconds since epoch """
        return cls.star_strp_mktime(string, cls.actDateFormat)

    @classmethod
    def g_drive_strp_mk_time(cls, string):
        """ takes a gDrive formatted time string (eg. "2016-07-13 22:33:05"),
        returns number of seconds since epoch """
        return cls.star_strp_mktime(string, cls.gDriveTimeFormat)

    @classmethod
    def wp_time_to_string(cls, secs, fmt=None):
        """
    Convert time to formatted local time string.

        Args:
            secs (Number, basestring): The number of seconds since epoch.
            fmt (basestring): The format string.

        Returns:
            str: formatted time string
        """

        if not fmt:
            fmt = cls.wpTimeFormat
        if secs:
            assert isinstance(secs, (Number, basestring)), \
                "param must be a number or string not %s" % type(secs)
            secs = float(secs)
            return time.strftime(fmt, time.localtime(secs))

    @classmethod
    def has_happened_yet(cls, secs):
        """
        Determine if a time has happened yet according to overrides.

        Args:
            secs (Number, basestring): The number of seconds since epoch.

        Returns:
            bool: Whether the time has happened yet according to overrides.
        """

        assert isinstance(secs, (Number, basestring)), \
            "param must be a number or string not %s" % type(secs)
        secs = float(secs)
        return secs >= cls.current_tsecs()

    @classmethod
    def local_to_server_time(cls, time_int, timezone_offset=time.timezone):
        """
        takes a time in local time (int), and an offset (int)
        returns the time in server time (int)
        """
        return int(time_int - timezone_offset)

    @classmethod
    def server_to_local_time(cls, time_int, timezone_offset=time.timezone):
        """
        takes a time in server time (int), and an offset (int)
        returns the time in local time (int)
        """
        return int(time_int + timezone_offset)

    @classmethod
    def wp_server_to_local_time(cls, time_int):
        """
        takes a time in wp server time (int),
        returns the time in local time (int)
        """
        return cls.server_to_local_time(time_int, cls._wpSrvOffset)

    @classmethod
    def act_server_to_local_time(cls, time_int):
        """
        takes a time in act server time (int),
        returns the time in local time (int)
        """
        return cls.server_to_local_time(time_int, cls.actSrvOffset)

    @classmethod
    def get_datestamp(cls, time_struct=None):
        """
        Get current datestamp string
        """
        if not time_struct:
            time_struct = cls.current_loctstruct()
        return time.strftime(cls.dateFormat, time_struct)

    @classmethod
    def get_ms_timestamp(cls, time_struct=None):
        """
        Get current MS friendly timestamp string
        """
        if not time_struct:
            time_struct = cls.current_loctstruct()
        return time.strftime(cls.msTimeFormat, time_struct)
    #
    # @classmethod
    # def get_timestamp(cls, time_struct=None):
    #     if not time_struct:
    #         time_struct = cls.current_loctstruct()
    #     return time.strftime(cls.wpTimeFormat, time_struct)
