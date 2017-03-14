import time
import unittest

from context import woogenerator
from woogenerator.utils import TimeUtils

class testUtilsTime(unittest.TestCase):
    def setUp(self):
        self.inTimeStr = "2016-05-06 16:07:00"
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

    def test_easy(self):
        TimeUtils.setWpSrvOffset(self.srvOffset)
        self.assertEqual(TimeUtils.wpStrptime(self.inTimeStr), 1462514820.0)
        self.assertEqual(
            TimeUtils.wpTimeToString(TimeUtils.wpStrptime(self.inTimeStr)),
            self.inTimeStr
        )

    def test_srvOffset(self):
        self.assertEqual(
            TimeUtils.wpTimeToString(TimeUtils.wpServerToLocalTime(TimeUtils.wpStrptime(self.inTimeStr))),
            self.inTimeStrOffset
        )

    def test_formats(self):
        for test, expected in self.actTimeTests:
            self.assertEqual(
                TimeUtils.wpTimeToString(TimeUtils.actStrptime(test)),
                expected
            )
        for test in self.wpTimeTests:
            self.assertEqual(
                TimeUtils.wpTimeToString(TimeUtils.wpStrptime(test)),
                test
            )

        self.assertEqual(
            TimeUtils.getDateStamp(time.localtime(TimeUtils.actStrpdate(self.actDateStr))),
            self.wpDateStr
        )

    def test_override(self):
        TimeUtils.set_override_time(time.strptime(
            "2016-08-12",
            TimeUtils.dateFormat
        ))

        self.assertEqual(TimeUtils.current_tsecs(), 1470924000.0)

if __name__ == '__main__':
    unittest.main()
