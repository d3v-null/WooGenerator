from os import sys, path
from time import sleep
from unittest import TestCase, main, skip, TestSuite, TextTestRunner

from context import woogenerator
from woogenerator.utils import ProgressCounter, SanitationUtils, UnicodeCsvDialectUtils

class testProgressCounter(TestCase):
    def setUp(self):
        self.progressCounter = ProgressCounter(100, 1)

    def test_carriageReturn(self):
        self.progressCounter.maybePrintUpdate(1)
        sleep(1)
        self.progressCounter.maybePrintUpdate(2)
        sleep(1)
        self.progressCounter.maybePrintUpdate(3)
        sleep(1)
        print "woo something else\n"

        self.progressCounter.maybePrintUpdate(3)
        sleep(1)
        self.progressCounter.maybePrintUpdate(4)
        sleep(1)

        print "woo, another thing"

        for i in range(90, 100):
            self.progressCounter.maybePrintUpdate(i)
            sleep(1)

        print "some stuff after"

    def test_stripURLHost(self):
        test_url = 'http://localhost/woocommerce/wc-api/v3/products?oauth_consumer_key=ck_0297450a41484f27184d1a8a3275f9bab5b69143&oauth_timestamp=1473914520&oauth_nonce=c430d5c707d1c8c8ff446b380eddc3218a366d0a&oauth_signature_method=HMAC-SHA256&oauth_signature=dYXFhWavVbLHeqeDMbUhWxghrnBBwCwqFaS+wYAxcy8=&page=2'
        expected_result = '/woocommerce/wc-api/v3/products?oauth_consumer_key=ck_0297450a41484f27184d1a8a3275f9bab5b69143&oauth_timestamp=1473914520&oauth_nonce=c430d5c707d1c8c8ff446b380eddc3218a366d0a&oauth_signature_method=HMAC-SHA256&oauth_signature=dYXFhWavVbLHeqeDMbUhWxghrnBBwCwqFaS+wYAxcy8=&page=2'
        self.assertEqual(SanitationUtils.stripURLHost(test_url), expected_result)

class testUnicodeCsvDialectUtils(TestCase):
    def test_get_act_dialect(self):
        csvdialect = UnicodeCsvDialectUtils.get_dialect_from_suggestion('act_out')
        print UnicodeCsvDialectUtils.dialect_to_str(csvdialect)

class testSanitationUtils(TestCase):
    def test_slugify(self):
        result = SanitationUtils.slugify("Tanbience Specials")
        self.assertEqual(result, 'tanbience_specials')

if __name__ == '__main__':
    main()

    # testSuite = TestSuite()
    # testSuite.addTest(testSanitationUtils('test_slugify'))
    # testSuite.addTest(testProgressCounter('test_stripURLHost'))
    # TextTestRunner().run(testSuite)
