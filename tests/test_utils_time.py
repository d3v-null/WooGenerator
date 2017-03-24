import time
import unittest

from context import woogenerator
from woogenerator.utils import TimeUtils


class testUtilsTime(unittest.TestCase):

    def setUp(self):
        self.inTimeStr = "2016-05-06 16:07:00"
        self.inTimeStruct = time.strptime(
            self.inTimeStr, TimeUtils.wpTimeFormat)
        self.inTimeSecs = time.mktime(self.inTimeStruct)
        self.srvOffset = -7200
        self.inTimeStrOffset = "2016-05-06 14:07:00"
        self.actDateStr = "14/02/2016"
        self.wpDateStr = "2016-02-14"
        self.wpTimeStrOffset = "2016-05-05 22:00:00"
        self.actTimeTests = [
            ("29/08/2014 9:45:08 AM", '2014-08-29 09:45:08'),
            ("10/10/2015 11:08:31 PM", '2015-10-10 23:08:31')
        ]
        self.wpTimeTests = [
            "2015-07-13 22:33:05",
            "2015-12-18 16:03:37"
        ]
        self.overrideTimeStruct = time.strptime(
            "2016-08-12",
            TimeUtils.dateFormat
        )
        self.overrideTimeSecs = time.mktime(self.overrideTimeStruct)

    def test_easy(self):
        TimeUtils.set_wp_srv_offset(self.srvOffset)
        inTimeSecsResult = TimeUtils.wp_strp_mktime(self.inTimeStr)
        self.assertEqual(inTimeSecsResult, self.inTimeSecs)
        self.assertEqual(
            TimeUtils.wp_time_to_string(inTimeSecsResult),
            self.inTimeStr
        )

    def test_srvOffset(self):
        self.assertEqual(
            TimeUtils.wp_time_to_string(TimeUtils.wp_server_to_local_time(
                TimeUtils.wp_strp_mktime(self.inTimeStr))),
            self.inTimeStrOffset
        )

    def test_formats(self):
        for test, expected in self.actTimeTests:
            self.assertEqual(
                TimeUtils.wp_time_to_string(TimeUtils.act_strp_mktime(test)),
                expected
            )
        for test in self.wpTimeTests:
            self.assertEqual(
                TimeUtils.wp_time_to_string(TimeUtils.wp_strp_mktime(test)),
                test
            )

        self.assertEqual(
            TimeUtils.get_datestamp(time.localtime(
                TimeUtils.act_strp_mktime(self.actDateStr))),
            self.wpDateStr
        )

    def test_override(self):
        TimeUtils.set_override_time(self.overrideTimeStruct)

        self.assertEqual(TimeUtils.current_tsecs(), self.overrideTimeSecs)

        self.assertFalse(TimeUtils.has_happened_yet(self.overrideTimeSecs - 1))
        self.assertTrue(TimeUtils.has_happened_yet(self.overrideTimeSecs + 1))

if __name__ == '__main__':
    unittest.main()
