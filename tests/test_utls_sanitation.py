import unittest

from context import woogenerator
from woogenerator.utils import Registrar, SanitationUtils


class TestSanitationUtils(unittest.TestCase):
    def setUp(self):
        Registrar.DEBUG_ERROR = False
        Registrar.DEBUG_WARN = False
        Registrar.DEBUG_MESSAGE = False
        Registrar.DEBUG_PROGRESS = False

    def test_similar_url(self):
        url1 = 'http://www.technotan.com.au'
        url2 = 'www.technotan.com.au'
        self.assertEqual(SanitationUtils.similar_url_comparison(url1), url2)
        self.assertEqual(SanitationUtils.similar_url_comparison(url2), url2)

    def test_findall_emails(self):
        email1 = "derwentx@gmail.com archive"
        self.assertItemsEqual(SanitationUtils.find_all_emails(email1),
                              [u'derwentx@gmail.com'])
        email2 = "derwentx@gmail.com derwent@laserphile.com"
        self.assertItemsEqual(SanitationUtils.find_all_emails(email2),
                              [u'derwentx@gmail.com', 'derwent@laserphile.com'])

    def test_find_url(self):
        url1 = "http://www.laserphile.com/ lol"
        self.assertItemsEqual(
            SanitationUtils.find_all_urls(url1),
            ['http://www.laserphile.com/'])

    def test_find_url_hard(self):
        url = 'http://www.facebook.com/search/?flt=1&amp;q=amber+melrose&amp;o=2048&amp;s=0#'
        self.assertItemsEqual(
            SanitationUtils.find_all_urls(url),
            ['http://www.facebook.com/search/?flt=1&q=amber+melrose&o=2048&s=0#']
        )

    def test_sanitize_cell(self):
        url = 'http://www.facebook.com/search/?flt=1&amp;q=amber+melrose&amp;o=2048&amp;s=0#'
        self.assertItemsEqual(url, SanitationUtils.sanitize_cell(url))

    def test_similar_comparison(self):
        url = 'http://www.facebook.com/search/?flt=1&amp;q=amber+melrose&amp;o=2048&amp;s=0#'
        self.assertItemsEqual(url, SanitationUtils.similar_comparison(url))

    def test_similar_markup_comparison(self):
        markup1 = ('Complete A Frame Assembly  (No Insert) - '
                   'A-Frame Sign Parts - A-Frame Signs - Generic Signage')
        markup2 = ('<p>Complete A Frame Assembly (No Insert) - '
                   'A-Frame Sign Parts - A-Frame Signs - Generic Signage</p>\n')
        self.assertEqual(
            SanitationUtils.similar_markup_comparison(markup1),
            SanitationUtils.similar_markup_comparison(markup2)
        )

if __name__ == '__main__':
    unittest.main()
    # doubleNameTestSuite = unittest.TestSuite()
    # doubleNameTestSuite.addTest(
    #     TestSanitationUtils('test_similarMarkupComparison'))
    # unittest.TextTestRunner().run(doubleNameTestSuite)
