from os import sys, path
from time import sleep
import unittest

from context import woogenerator
from woogenerator.utils import (ProgressCounter, SanitationUtils,
                                UnicodeCsvDialectUtils, Registrar)


class testProgressCounter(unittest.TestCase):

    def setUp(self):
        self.progress_counter = ProgressCounter(100, 1)

        Registrar.DEBUG_ERROR = False
        Registrar.DEBUG_WARN = False
        Registrar.DEBUG_MESSAGE = False
        Registrar.DEBUG_PROGRESS = False

    def test_stripURLHost(self):
        test_url = 'http://localhost/woocommerce/wc-api/v3/products?oauth_consumer_key=ck_0297450a41484f27184d1a8a3275f9bab5b69143&oauth_timestamp=1473914520&oauth_nonce=c430d5c707d1c8c8ff446b380eddc3218a366d0a&oauth_signature_method=HMAC-SHA256&oauth_signature=dYXFhWavVbLHeqeDMbUhWxghrnBBwCwqFaS+wYAxcy8=&page=2'
        expected_result = '/woocommerce/wc-api/v3/products?oauth_consumer_key=ck_0297450a41484f27184d1a8a3275f9bab5b69143&oauth_timestamp=1473914520&oauth_nonce=c430d5c707d1c8c8ff446b380eddc3218a366d0a&oauth_signature_method=HMAC-SHA256&oauth_signature=dYXFhWavVbLHeqeDMbUhWxghrnBBwCwqFaS+wYAxcy8=&page=2'
        self.assertEqual(SanitationUtils.strip_url_host(
            test_url), expected_result)


class testUnicodeCsvDialectUtils(unittest.TestCase):

    def test_get_act_dialect(self):
        csvdialect = UnicodeCsvDialectUtils.get_dialect_from_suggestion(
            'ActOut')
        # print UnicodeCsvDialectUtils.dialect_to_str(csvdialect)


class test_sanitation_utils(unittest.TestCase):

    def test_slugify(self):
        result = SanitationUtils.slugify("Tanbience Specials")
        self.assertEqual(result, 'tanbience_specials')

if __name__ == '__main__':
    unittest.main()

    # testSuite = TestSuite()
    # testSuite.addTest(test_sanitation_utils('test_slugify'))
    # testSuite.addTest(testProgressCounter('test_stripURLHost'))
    # TextTestRunner().run(testSuite)
