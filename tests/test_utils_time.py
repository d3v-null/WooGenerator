import time
import unittest
from datetime import datetime

import pytz

from context import woogenerator
from woogenerator.namespace.prod import SettingsNamespaceProd
from woogenerator.utils import Registrar, TimeUtils

from .abstract import AbstractWooGeneratorTestCase


class TestUtilsTime(unittest.TestCase):
    def setUp(self):
        Registrar.DEBUG_ERROR = False
        Registrar.DEBUG_WARN = False
        Registrar.DEBUG_MESSAGE = False
        Registrar.DEBUG_PROGRESS = False

        self.in_time_str = "2016-05-06 16:07:00"
        self.in_time_struct = time.strptime(
            self.in_time_str, TimeUtils.wp_datetime_format)
        self.in_time_secs = time.mktime(self.in_time_struct)
        self.srv_offset = -7200
        self.in_time_str_offset = "2016-05-06 14:07:00"
        self.act_date_str = "14/02/2016"
        self.wp_date_str = "2016-02-14"
        self.wp_time_str_offset = "2016-05-05 22:00:00"
        self.act_time_tests = [
            ("29/08/2014 9:45:08 AM", '2014-08-29 09:45:08'),
            ("10/10/2015 11:08:31 PM", '2015-10-10 23:08:31')
        ]
        self.wp_time_tests = [
            "2015-07-13 22:33:05",
            "2015-12-18 16:03:37"
        ]
        self.override_time_struct = time.strptime(
            "2016-08-12",
            TimeUtils.wp_date_format
        )
        self.override_time_secs = time.mktime(self.override_time_struct)

    # def test_easy(self):
    #     TimeUtils.set_wp_srv_offset(self.srv_offset)
    #     in_time_secs_result = TimeUtils.wp_strp_mktime(self.in_time_str)
    #     self.assertEqual(in_time_secs_result, self.in_time_secs)
    #     self.assertEqual(
    #         TimeUtils.wp_time_to_string(in_time_secs_result),
    #         self.in_time_str
    #     )

    # def test_srv_offset(self):
    #     self.assertEqual(
    #         TimeUtils.wp_time_to_string(TimeUtils.wp_server_to_local_time(
    #             TimeUtils.wp_strp_mktime(self.in_time_str))),
    #         self.in_time_str_offset
    #     )

    def test_translate_datetime_timestamp(self):
        timestamp = 1511219002
        date_string = "2017-11-20T23:03:22"
        datetime_ = datetime(2017, 11, 20, 23, 03, 22)
        self.assertEqual(
            TimeUtils.datetime2timestamp(datetime_),
            timestamp
        )
        self.assertEqual(
            TimeUtils.timestamp2datetime(timestamp),
            datetime_
        )
        self.assertEqual(
            datetime_.isoformat('T'),
            date_string
        )

    def test_override(self):
        TimeUtils.set_override_time(self.override_time_struct)

        self.assertEqual(TimeUtils.current_tsecs(), self.override_time_secs)

        self.assertFalse(TimeUtils.has_happened_yet(self.override_time_secs - 1))
        self.assertTrue(TimeUtils.has_happened_yet(self.override_time_secs + 1))

class TestTimeUtilsNormalize(AbstractWooGeneratorTestCase):
    settings_namespace_class = SettingsNamespaceProd
    config_file = "generator_config_test.yaml"

    def setUp(self):
        super(TestTimeUtilsNormalize, self).setUp()
        # make all timezones different
        self.settings.wp_srv_tz = "Africa/Algiers"          # (+0:12)
        self.settings.act_srv_tz = "Europe/Luxembourg"      # (+0:25 / +1:25 DST, 26 Mar -> 29 Oct)
        self.settings.gdrive_tz = "Africa/Cairo"            # (+2:05)
        self.settings.xero_tz = "Asia/Amman"                # (+2:24 / +3:00 DST, 31 Mar -> 27 Oct)
        self.settings.local_tz = "Africa/Asmara"            # (+2:27)
        self.settings.init_settings(self.override_args)

    def test_normalize_init_settings(self):
        self.assertEqual(self.settings.wp_srv_tz, "Africa/Algiers")
        self.assertEqual(self.settings.act_srv_tz, "Europe/Luxembourg")
        self.assertEqual(self.settings.gdrive_tz, "Africa/Cairo")
        self.assertEqual(self.settings.xero_tz, "Asia/Amman")
        self.assertEqual(self.settings.local_tz, "Africa/Asmara")

    def test_normalize_iso8601(self):
        # DST will be active
        utc_iso8601 = '2017-02-01T00:00:00'
        wp_iso8601 = '2017-02-01 00:12:00'
        act_iso8601 = '2017-02-01T00:25:00'
        gdrive_iso8601 = '2017-02-01 02:05:00'
        xero_iso8601 = '2017-02-01T02:24:00'
        local_iso8601 = '2017-02-01T02:27:00'
        utc_dt = TimeUtils.normalize_iso8601(utc_iso8601)
        naiive_dt = utc_dt.replace(tzinfo=None)
        wp_dt = TimeUtils.normalize_iso8601_wp(wp_iso8601)
        act_dt = TimeUtils.normalize_iso8601_act(act_iso8601)
        gdrive_dt = TimeUtils.normalize_iso8601_gdrive(gdrive_iso8601)
        xero_dt = TimeUtils.normalize_iso8601_xero(xero_iso8601)
        local_dt = TimeUtils.normalize_iso8601_local(local_iso8601)

        self.assertEqual(
            TimeUtils.datetime2timestamp(naiive_dt),
            TimeUtils.datetime2timestamp(utc_dt)
        )
        self.assertEqual(
            TimeUtils.datetime2timestamp(wp_dt),
            TimeUtils.datetime2timestamp(utc_dt)
        )
        self.assertEqual(
            TimeUtils.datetime2timestamp(act_dt),
            TimeUtils.datetime2timestamp(utc_dt)
        )
        self.assertEqual(
            TimeUtils.datetime2timestamp(gdrive_dt),
            TimeUtils.datetime2timestamp(utc_dt)
        )
        self.assertEqual(
            TimeUtils.datetime2timestamp(xero_dt),
            TimeUtils.datetime2timestamp(utc_dt)
        )
        self.assertEqual(
            TimeUtils.datetime2timestamp(local_dt),
            TimeUtils.datetime2timestamp(utc_dt)
        )

        self.assertEqual(
            TimeUtils.denormalize_iso8601(utc_dt),
            utc_iso8601
        )
        with self.assertRaises(AssertionError):
            TimeUtils.denormalize_iso8601(naiive_dt)
        self.assertEqual(
            TimeUtils.denormalize_iso8601_wp(wp_dt),
            wp_iso8601
        )
        self.assertEqual(
            TimeUtils.denormalize_iso8601_act(act_dt),
            act_iso8601
        )
        self.assertEqual(
            TimeUtils.denormalize_iso8601_gdrive(gdrive_dt),
            gdrive_iso8601
        )
        self.assertEqual(
            TimeUtils.denormalize_iso8601_xero(xero_dt),
            xero_iso8601
        )

    def test_normalize_timestamp(self):
        utc_timestamp = 1485907200
        wp_timestamp = 1485907920
        act_timestamp = 1485908700
        gdrive_timestamp = 1485914700
        xero_timestamp = 1485915840
        local_timestamp = 1485916020

        utc_dt = TimeUtils.normalize_timestamp(utc_timestamp)
        naiive_dt = utc_dt.replace(tzinfo=None)
        wp_dt = TimeUtils.normalize_timestamp_wp(wp_timestamp)
        act_dt = TimeUtils.normalize_timestamp_act(act_timestamp)
        gdrive_dt = TimeUtils.normalize_timestamp_gdrive(gdrive_timestamp)
        xero_dt = TimeUtils.normalize_timestamp_xero(xero_timestamp)
        local_dt = TimeUtils.normalize_timestamp_local(local_timestamp)

        self.assertEqual(
            TimeUtils.datetime2timestamp(naiive_dt),
            utc_timestamp
        )
        self.assertEqual(
            TimeUtils.datetime2timestamp(wp_dt),
            utc_timestamp
        )
        self.assertEqual(
            TimeUtils.datetime2timestamp(act_dt),
            utc_timestamp
        )
        self.assertEqual(
            TimeUtils.datetime2timestamp(gdrive_dt),
            utc_timestamp
        )
        self.assertEqual(
            TimeUtils.datetime2timestamp(xero_dt),
            utc_timestamp
        )
        self.assertEqual(
            TimeUtils.datetime2timestamp(local_dt),
            utc_timestamp
        )

if __name__ == '__main__':
    unittest.main()
