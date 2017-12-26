"""
Utilities for time-related tasks
"""
from __future__ import absolute_import

import calendar
import datetime
import time
from copy import deepcopy
from numbers import Number

import pytz
import tzlocal
from pytz import timezone
from tzlocal import get_localzone

from .core import SanitationUtils


class TimeUtils(object):
    """
    Utilities for time-related tasks
    """
    _override_time = None
    # _wp_srv_offset = 0
    # _act_srv_offset = 0
    _wp_srv_tz = pytz.utc
    _act_srv_tz = pytz.utc
    _gdrive_tz = pytz.utc
    _xero_tz = pytz.utc
    _local_tz = get_localzone()

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
    def set_wp_srv_tz(cls, zone):
        """ Set the timezone used by the WP server. """
        cls._wp_srv_tz = timezone(zone)

    @classmethod
    def set_gdrive_tz(cls, zone):
        """ Set the timezone of times specified in the GDrive files. """
        cls._gdrive_tz = timezone(zone)

    @classmethod
    def set_xero_tz(cls, zone):
        """ Set the timezone used by the Xero API. """
        cls._xero_tz = timezone(zone)

    @classmethod
    def set_act_srv_tz(cls, zone):
        """ Set the timezone used by the Act! Database. """
        cls._act_srv_tz = timezone(zone)

    @classmethod
    def set_local_tz(cls, zone):
        """ Set the timezone of the local computer. """
        cls._local_tz = timezone(zone)

    @classmethod
    def inform_datetime(cls, dt, tz):
        """
        Inform a naiive datetime object of its' timezone without changing its' time.
        """
        assert isinstance(dt, datetime.datetime)
        assert isinstance(tz, datetime.tzinfo)
        return dt.replace(tzinfo=tz)

    @classmethod
    def localize_datetime(cls, dt, tz):
        """
        Localize an aware datetime object in a different timezone.
        """
        assert dt.tzinfo, "Requires a datetime object that is aware of its timezone."
        assert isinstance(tz, datetime.tzinfo)
        return dt.astimezone(tz)

    @classmethod
    def current_loctstruct(cls):
        """ returns the current local time as a time.struct_time in local time or the
        struct_time that was set to override the curren time """
        if cls._override_time:
            return cls._override_time
        else:
            return time.gmtime()
            #TODO: should this be localtime() ?

    @classmethod
    def current_tsecs(cls):
        """
        Return the curren time in number of seconds since the epoch or the time
        that was set to override.
        """
        if cls._override_time:
            return time.mktime(cls._override_time)
        else:
            return time.time()

    @classmethod
    def current_datetime(cls):
        """
        Return the current time as an aware datetime object.
        """
        response = datetime.datetime(*cls.current_loctstruct())
        return cls.inform_datetime(response, cls._local_tz)

    @classmethod
    def star_strp_datetime(cls, string, fmt=wp_datetime_format):
        """
        Take a string in format `fmt` and return the naiive datetime object it represents.
        """
        if string:
            if '.' in string:
                string = string.split('.')[0]
            return datetime.datetime.strptime(string, fmt)

    @classmethod
    def star_strf_datetime(cls, dt, fmt=wp_datetime_format):
        """
        Take a datetime object and return a string in format `fmt` representing the date.
        """
        if dt is not None:
            return dt.strftime(fmt)

    @classmethod
    def timestamp2datetime(cls, timestamp):
        """
        Return a timestamp's representation as a naiive datetime object.
        """
        if not timestamp:
            return
        if isinstance(timestamp, datetime.datetime):
            secs = cls.datetime2timestamp(timestamp)
        elif isinstance(timestamp, tuple):
            secs = time.mktime(timestamp)
        elif isinstance(timestamp, (Number, basestring)):
            secs = float(timestamp)
        return datetime.datetime.utcfromtimestamp(secs)

    @classmethod
    def datetime2timestamp(cls, dt):
        """
        Return a datetime's representation as a timestamp in it's timezone.
        """
        if dt:
            if dt.tzinfo:
                dt = cls.localize_datetime(dt, pytz.utc)
            dt = dt.replace(tzinfo=None)
            return int(calendar.timegm(dt.utctimetuple()))

    @classmethod
    def datetime_local2gmt(cls, dt, local_tz=None):
        """
        Return the UTC localized form of a naiive or aware local datetime object.
        """
        if local_tz is None:
            local_tz = cls._local_tz
        response = cls.inform_datetime(dt, local_tz)
        return cls.localize_datetime(response, pytz.utc)

    @classmethod
    def star_strp_mktime(cls, string, fmt=wp_datetime_format):
        # type: (basestring, basestring) -> int
        """
        Given a time string and a format, returns number of seconds since epoch
        """
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
    def normalize_iso8601(cls, string, tz=None, fmt=None):
        """
        Given `string` in iso8601 format, return the datetime object
        in timezone `tz` which it represents.
        """
        if tz is None:
            tz = pytz.utc
        if fmt is None:
            fmt = TimeUtils.iso8601_datetime_format
        if not string:
            return
        response = cls.star_strp_datetime(string, fmt)
        response = cls.inform_datetime(response, tz)
        return response

    @classmethod
    def denormalize_iso8601(cls, dt, tz=None, fmt=None):
        """
        Given datetime `dt`, return the iso8601 representation in timezone `tz`.
        """
        if tz is None:
            tz = pytz.utc
        if fmt is None:
            fmt = cls.iso8601_datetime_format
        response = cls.localize_datetime(dt, tz)
        response = cls.star_strf_datetime(response, fmt)
        return response

    @classmethod
    def normalize_iso8601_wp(cls, string):
        return cls.normalize_iso8601(string, cls._wp_srv_tz, cls.wp_datetime_format)

    @classmethod
    def normalize_iso8601_wp_t(cls, string):
        return cls.normalize_iso8601(string, cls._wp_srv_tz, cls.iso8601_datetime_format)

    @classmethod
    def normalize_iso8601_act(cls, string):
        return cls.normalize_iso8601(string, cls._act_srv_tz)

    @classmethod
    def normalize_iso8601_gdrive(cls, string):
        return cls.normalize_iso8601(string, cls._gdrive_tz, cls.gdrive_datetime_format)

    @classmethod
    def normalize_iso8601_xero(cls, string):
        return cls.normalize_iso8601(string, cls._xero_tz)

    @classmethod
    def normalize_iso8601_local(cls, string):
        return cls.normalize_iso8601(string, cls._local_tz)

    @classmethod
    def denormalize_iso8601_wp(cls, dt):
        return cls.denormalize_iso8601(dt, cls._wp_srv_tz, cls.wp_datetime_format)

    @classmethod
    def denormalize_iso8601_wp_t(cls, dt):
        return cls.denormalize_iso8601(dt, cls._wp_srv_tz, cls.iso8601_datetime_format)

    @classmethod
    def denormalize_iso8601_act(cls, dt):
        return cls.denormalize_iso8601(dt, cls._act_srv_tz)

    @classmethod
    def denormalize_iso8601_gdrive(cls, dt):
        return cls.denormalize_iso8601(dt, cls._gdrive_tz, cls.gdrive_datetime_format)

    @classmethod
    def denormalize_iso8601_xero(cls, dt):
        return cls.denormalize_iso8601(dt, cls._xero_tz)

    @classmethod
    def denormalize_iso8601_local(cls, string):
        """
        Given a string in iso8601 format and local timezone, return the
        aware datetime object it represents.
        """
        return cls.denormalize_iso8601(string, cls._local_tz)

    @classmethod
    def normalize_timestamp(cls, timestamp, tz=None, fmt=None):
        """
        Given `string` in iso8601 format, return the datetime object
        in timezone `tz` which it represents.
        """
        if timestamp is None or timestamp == '':
            return
        if tz is None:
            tz = pytz.utc
        response = cls.timestamp2datetime(timestamp)
        response = cls.inform_datetime(response, tz)
        return response

    @classmethod
    def denormalize_timestamp(cls, dt, tz=None):
        """
        Given datetime `dt`, return the timestamp representation in timezone `tz`.
        """
        if not dt:
            return
        if tz is None:
            tz = pytz.utc
        response = cls.localize_datetime(dt, tz)
        response = cls.datetime2timestamp(response)
        return response

    @classmethod
    def normalize_timestamp_utc(cls, dt):
        return cls.normalize_timestamp(dt, pytz.utc)

    @classmethod
    def denormalize_timestamp_utc(cls, dt):
        return cls.denormalize_timestamp(dt, pytz.utc)

    @classmethod
    def normalize_timestamp_wp(cls, dt):
        return cls.normalize_timestamp(dt, cls._wp_srv_tz)

    @classmethod
    def denormalize_timestamp_wp(cls, dt):
        return cls.denormalize_timestamp(dt, cls._wp_srv_tz)

    @classmethod
    def normalize_timestamp_act(cls, dt):
        return cls.normalize_timestamp(dt, cls._act_srv_tz)

    @classmethod
    def denormalize_timestamp_act(cls, dt):
        return cls.denormalize_timestamp(dt, cls._act_srv_tz)

    @classmethod
    def normalize_timestamp_gdrive(cls, dt):
        return cls.normalize_timestamp(dt, cls._gdrive_tz)

    @classmethod
    def denormalize_timestamp_gdrive(cls, dt):
        return cls.denormalize_timestamp(dt, cls._gdrive_tz)

    @classmethod
    def normalize_timestamp_xero(cls, dt):
        return cls.normalize_timestamp(dt, cls._xero_tz)

    @classmethod
    def denormalize_timestamp_xero(cls, dt):
        return cls.denormalize_timestamp(dt, cls._xero_tz)

    @classmethod
    def normalize_timestamp_local(cls, dt):
        return cls.normalize_timestamp(dt, cls._local_tz)

    @classmethod
    def denormalize_timestamp_local(cls, dt):
        return cls.denormalize_timestamp(dt, cls._local_tz)

    # @classmethod
    # def set_wp_srv_offset(cls, offset):
    #     """ changes the offset (secs) """
    #     assert isinstance(offset, (int, float)
    #                       ), "param must be a number not %s" % type(offset)
    #     cls._wp_srv_offset = offset

    # @classmethod
    # def act_strp_mktime(cls, string):
    #     """ take an act formatted date or time string (eg. "8/11/2016 1:38:51 PM"),
    #     returns number of seconds since epoch """
    #     assert isinstance(string, basestring), \
    #         "param must be a string not %s" % type(string)
    #
    #     response = None
    #     exceptions = []
    #     for fmt in [cls.act_datetime_format, cls.act_date_format]:
    #         try:
    #             response = cls.star_strp_mktime(string, fmt)
    #         except ValueError as exc:
    #             exceptions.append(exc)
    #     if response is None and exceptions:
    #         raise exceptions[0]
    #     return response

    # @classmethod
    # def wp_strp_mktime(cls, string):
    #     """ take a wp formatted time string (eg. "2015-07-13 22:33:05"),
    #     returns number of seconds since epoch """
    #
    #     response = None
    #     exceptions = []
    #     for fmt in [cls.wp_datetime_format, cls.wp_date_format]:
    #         try:
    #             response = cls.star_strp_mktime(string, fmt)
    #         except ValueError as exc:
    #             exceptions.append(exc)
    #     if response is None and exceptions:
    #         raise exceptions[0]
    #     return response
    #
    # @classmethod
    # def act_strp_mkdate(cls, string):
    #     """ take an act formatted date string (eg. "13/07/2015"),
    #     returns number of seconds since epoch """
    #     return cls.star_strp_mktime(string, cls.act_date_format)
    #
    # @classmethod
    # def g_drive_strp_mk_time(cls, string):
    #     """ take a gDrive formatted time string (eg. "2016-07-13 22:33:05"),
    #     returns number of seconds since epoch """
    #     return cls.star_strp_mktime(string, cls.gdrive_datetime_format)

    @classmethod
    def wp_time_to_string(cls, time_, fmt=None):
        """
    Convert time to formatted local time string.

        Args:
            secs (Number, basestring): The number of seconds since epoch.
            fmt (basestring): The format string.

        Returns:
            str: formatted time string
        """
        if not time_:
            return
        if not fmt:
            fmt = cls.wp_datetime_format
        if isinstance(time_, datetime.datetime):
            secs = cls.datetime2timestamp(time_)
        elif isinstance(time_, tuple):
            secs = time.mktime(time_)
        elif isinstance(time_, (Number, basestring)):
            secs = float(time_)
        return time.strftime(fmt, time.localtime(secs))

    @classmethod
    def has_happened_yet(cls, time_):
        """
        Determine if a time has happened yet according to overrides.

        Args:
            secs (Number, basestring): The number of seconds since epoch.

        Returns:
            bool: Whether the time has happened yet according to overrides.
        """
        if isinstance(time_, datetime.datetime):
            secs = cls.datetime2timestamp(time_)
        elif isinstance(time_, tuple):
            secs = time.mktime(time_)
        elif isinstance(time_, (Number, basestring)):
            secs = float(time_)
        return secs >= cls.current_tsecs()

    # @classmethod
    # def local_to_server_time(cls, time_int, timezone_offset=time.timezone):
    #     """
    #     take a time in local time (int), and an offset (int)
    #     returns the time in server time (int)
    #     """
    #     return int(time_int - timezone_offset)
    #
    # @classmethod
    # def server_to_local_time(cls, time_int, timezone_offset=time.timezone):
    #     """
    #     take a time in server time (int), and an offset (int)
    #     returns the time in local time (int)
    #     """
    #     return int(time_int + timezone_offset)
    #
    # @classmethod
    # def wp_server_to_local_time(cls, time_int):
    #     """
    #     take a time in wp server time (int),
    #     returns the time in local time (int)
    #     """
    #     return cls.server_to_local_time(time_int, cls._wp_srv_offset)
    # @classmethod
    # def wp_local_to_server_time(cls, time_int):
    #     """
    #     take a time in wp server time (int),
    #     returns the time in local time (int)
    #     """
    #     return cls.local_to_server_time(time_int, cls._wp_srv_offset)
    #
    # @classmethod
    # def act_server_to_local_time(cls, time_int):
    #     """
    #     take a time in act server time (int),
    #     returns the time in local time (int)
    #     """
    #     return cls.server_to_local_time(time_int, cls._act_srv_offset)
    #
    # @classmethod
    # def get_datestamp(cls, time_struct=None):
    #     """
    #     Get current datestamp string
    #     """
    #     if not time_struct:
    #         time_struct = cls.current_loctstruct()
    #     return time.strftime(cls.wp_date_format, time_struct)
    #
    @classmethod
    def get_ms_timestamp(cls, time_struct=None):
        """
        Get current MS friendly timestamp string
        """
        if not time_struct:
            time_struct = cls.current_loctstruct()
        return time.strftime(cls.ms_datetime_format, time_struct)
    #
    # @classmethod
    # def get_system_timezone(cls):
    #     """
    #     Get timezone offset as configured by system.
    #     """
    #     return time.strftime("%z", time.gmtime())

    @classmethod
    def get_timestamp(cls, time_struct=None):
        if not time_struct:
            time_struct = cls.current_loctstruct()
        return time.strftime(cls.wp_datetime_format, time_struct)
