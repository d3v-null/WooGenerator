"""
Utilities for time-related tasks
"""
from __future__ import absolute_import

import datetime
import time
import calendar
from numbers import Number

from .core import SanitationUtils


class TimeUtils(object):
    """
    Utilities for time-related tasks
    """
    _override_time = None
    _wpSrvOffset = 0
    actSrvOffset = 0

    wp_date_format = "%Y-%m-%d"
    act_date_format = "%d/%m/%Y"
    iso8601_datetime_format = "%Y-%m-%dT%H:%M:%S"
    wp_datetime_format = "%Y-%m-%d %H:%M:%S"
    gdrive_datetime_format = wp_datetime_format
    ms_datetime_format = "%Y-%m-%d_%H-%M-%S"
    act_datetime_format = "%d/%m/%Y %I:%M:%S %p"


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
    def star_strp_datetime(cls, string, fmt=wp_datetime_format):
        return datetime.datetime.strptime(string, fmt)

    @classmethod
    def star_strf_datetime(cls, datetime_, fmt=wp_datetime_format):
        return datetime_.strftime(fmt)

    @classmethod
    def timestamp2datetime(cls, timestamp):
        if timestamp:
            return datetime.datetime.utcfromtimestamp(float(timestamp))

    @classmethod
    def datetime2timestamp(cls, datetime_):
        if datetime_:
            return int(calendar.timegm(datetime_.utctimetuple()))

    @classmethod
    def star_strp_mktime(cls, string, fmt=wp_datetime_format):
        # type: (basestring, basestring) -> int
        """ take a time string and a format, returns number of seconds since epoch """
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
        """ take an act formatted date or time string (eg. "8/11/2016 1:38:51 PM"),
        returns number of seconds since epoch """
        assert isinstance(string, basestring), \
            "param must be a string not %s" % type(string)

        response = None
        exceptions = []
        for fmt in [cls.act_datetime_format, cls.act_date_format]:
            try:
                response = cls.star_strp_mktime(string, fmt)
            except ValueError as exc:
                exceptions.append(exc)
        if response is None and exceptions:
            raise exceptions[0]
        return response

    @classmethod
    def wp_strp_mktime(cls, string):
        """ take a wp formatted time string (eg. "2015-07-13 22:33:05"),
        returns number of seconds since epoch """

        response = None
        exceptions = []
        for fmt in [cls.wp_datetime_format, cls.wp_date_format]:
            try:
                response = cls.star_strp_mktime(string, fmt)
            except ValueError as exc:
                exceptions.append(exc)
        if response is None and exceptions:
            raise exceptions[0]
        return response

    @classmethod
    def act_strp_mkdate(cls, string):
        """ take an act formatted date string (eg. "13/07/2015"),
        returns number of seconds since epoch """
        return cls.star_strp_mktime(string, cls.act_date_format)

    @classmethod
    def g_drive_strp_mk_time(cls, string):
        """ take a gDrive formatted time string (eg. "2016-07-13 22:33:05"),
        returns number of seconds since epoch """
        return cls.star_strp_mktime(string, cls.gdrive_datetime_format)

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
            fmt = cls.wp_datetime_format
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
        take a time in local time (int), and an offset (int)
        returns the time in server time (int)
        """
        return int(time_int - timezone_offset)

    @classmethod
    def server_to_local_time(cls, time_int, timezone_offset=time.timezone):
        """
        take a time in server time (int), and an offset (int)
        returns the time in local time (int)
        """
        return int(time_int + timezone_offset)

    @classmethod
    def wp_server_to_local_time(cls, time_int):
        """
        take a time in wp server time (int),
        returns the time in local time (int)
        """
        return cls.server_to_local_time(time_int, cls._wpSrvOffset)

    @classmethod
    def act_server_to_local_time(cls, time_int):
        """
        take a time in act server time (int),
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
        return time.strftime(cls.wp_date_format, time_struct)

    @classmethod
    def get_ms_timestamp(cls, time_struct=None):
        """
        Get current MS friendly timestamp string
        """
        if not time_struct:
            time_struct = cls.current_loctstruct()
        return time.strftime(cls.ms_datetime_format, time_struct)

    @classmethod
    def get_system_timezone(cls):
        """
        Get timezone offset as configured by system.
        """
        return time.strftime("%z", time.gmtime())
    #
    # @classmethod
    # def get_timestamp(cls, time_struct=None):
    #     if not time_struct:
    #         time_struct = cls.current_loctstruct()
    #     return time.strftime(cls.wp_datetime_format, time_struct)
