import time
import unittest

from context import woogenerator
from woogenerator.utils import TimeUtils

class testUtilsTime(unittest.TestCase):
    def setUp(self):
        self.inTimeStr = "2016-05-06 16:07:00"
        self.inTimeStruct = time.strptime(self.inTimeStr, TimeUtils.wpTimeFormat)
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
        TimeUtils.setWpSrvOffset(self.srvOffset)
        inTimeSecsResult = TimeUtils.wpStrpMktime(self.inTimeStr)
        self.assertEqual(inTimeSecsResult, self.inTimeSecs)
        self.assertEqual(
            TimeUtils.wpTimeToString(inTimeSecsResult),
            self.inTimeStr
        )

    def test_srvOffset(self):
        self.assertEqual(
            TimeUtils.wpTimeToString(TimeUtils.wpServerToLocalTime(TimeUtils.wpStrpMktime(self.inTimeStr))),
            self.inTimeStrOffset
        )

    def test_formats(self):
        for test, expected in self.actTimeTests:
            self.assertEqual(
                TimeUtils.wpTimeToString(TimeUtils.actStrpMktime(test)),
                expected
            )
        for test in self.wpTimeTests:
            self.assertEqual(
                TimeUtils.wpTimeToString(TimeUtils.wpStrpMktime(test)),
                test
            )

        self.assertEqual(
            TimeUtils.getDateStamp(time.localtime(TimeUtils.actStrpMkdate(self.actDateStr))),
            self.wpDateStr
        )

    def test_override(self):
        TimeUtils.set_override_time(self.overrideTimeStruct)

        self.assertEqual(TimeUtils.current_tsecs(), self.overrideTimeSecs)

        self.assertFalse(TimeUtils.hasHappenedYet(self.overrideTimeSecs-1))
        self.assertTrue(TimeUtils.hasHappenedYet(self.overrideTimeSecs+1))

if __name__ == '__main__':
    unittest.main()
