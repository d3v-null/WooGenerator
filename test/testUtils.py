from os import sys, path
from time import sleep
from unittest import TestCase, main, skip, TestSuite, TextTestRunner

if __name__ == '__main__' and __package__ is None:
    sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

from source.utils import *


class testProgressCounter(TestCase):
    def setUp(self):
        self.progressCounter = ProgressCounter(100, 1)

    def test_carriageReturn(self):
        self.progressCounter.maybePrintUpdate(1)
        sleep(1)
        self.progressCounter.maybePrintUpdate(2)
        sleep(1)
        self.progressCounter.maybePrintUpdate(50)
        sleep(1)
        self.progressCounter.maybePrintUpdate(99)

if __name__ == '__main__':
    # main()

    testSuite = TestSuite()
    testSuite.addTest(testProgressCounter('test_carriageReturn'))
    TextTestRunner().run(testSuite)
