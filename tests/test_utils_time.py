import time
import unittest
from datetime import datetime

from context import woogenerator
from woogenerator.utils import Registrar, TimeUtils


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

    def test_easy(self):
        TimeUtils.set_wp_srv_offset(self.srv_offset)
        in_time_secs_result = TimeUtils.wp_strp_mktime(self.in_time_str)
        self.assertEqual(in_time_secs_result, self.in_time_secs)
        self.assertEqual(
            TimeUtils.wp_time_to_string(in_time_secs_result),
            self.in_time_str
        )

    def test_srv_offset(self):
        self.assertEqual(
            TimeUtils.wp_time_to_string(TimeUtils.wp_server_to_local_time(
                TimeUtils.wp_strp_mktime(self.in_time_str))),
            self.in_time_str_offset
        )

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

    @unittest.skip("fix this later")
    def test_formats(self):
        for test, expected in self.act_time_tests:
            self.assertEqual(
                TimeUtils.wp_time_to_string(TimeUtils.act_strp_mktime(test)),
                expected
            )
        for test in self.wp_time_tests:
            self.assertEqual(
                TimeUtils.wp_time_to_string(TimeUtils.wp_strp_mktime(test)),
                test
            )

        self.assertEqual(
            TimeUtils.get_datestamp(time.localtime(
                TimeUtils.act_strp_mktime(self.act_date_str))),
            self.wp_date_str
        )

    def test_override(self):
        TimeUtils.set_override_time(self.override_time_struct)

        self.assertEqual(TimeUtils.current_tsecs(), self.override_time_secs)

        self.assertFalse(TimeUtils.has_happened_yet(self.override_time_secs - 1))
        self.assertTrue(TimeUtils.has_happened_yet(self.override_time_secs + 1))

if __name__ == '__main__':
    unittest.main()
