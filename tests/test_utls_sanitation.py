import os
from os import sys, path
from unittest import TestCase, main, skip
import unittest
import yaml

from context import woogenerator

from woogenerator.syncupdate import *
from woogenerator import coldata
from woogenerator.coldata import ColDataUser
from woogenerator.parsing.user import ImportUser, CsvParseUser
from woogenerator.contact_objects import FieldGroup
from woogenerator.utils import Registrar


class test_sanitation_utils(TestCase):
    def setUp(self):
        Registrar.DEBUG_ERROR = False
        Registrar.DEBUG_WARN = False
        Registrar.DEBUG_MESSAGE = False
        Registrar.DEBUG_PROGRESS = False
    #     yaml_path = "source/merger_config.yaml"
    #
    #     with open(yaml_path) as stream:
    #         config = yaml.load(stream)

    def test_similarURL(self):
        url1 = 'http://www.technotan.com.au'
        url2 = 'www.technotan.com.au'
        self.assertEqual(SanitationUtils.similar_url_comparison(url1), url2)
        self.assertEqual(SanitationUtils.similar_url_comparison(url2), url2)

    def test_findallEmails(self):
        email1 = "derwentx@gmail.com archive"
        self.assertItemsEqual(SanitationUtils.find_all_emails(email1),
                              [u'derwentx@gmail.com'])
        email2 = "derwentx@gmail.com derwent@laserphile.com"
        self.assertItemsEqual(SanitationUtils.find_all_emails(email2),
                              [u'derwentx@gmail.com', 'derwent@laserphile.com'])

    def test_findUrl(self):
        url1 = "http://www.laserphile.com/ lol"
        self.assertItemsEqual(
            SanitationUtils.find_all_urls(url1),
            ['http://www.laserphile.com/'])

    def test_findUrlHard(self):
        url = 'http://www.facebook.com/search/?flt=1&amp;q=amber+melrose&amp;o=2048&amp;s=0#'
        self.assertItemsEqual(
            SanitationUtils.find_all_urls(url),
            ['http://www.facebook.com/search/?flt=1&q=amber+melrose&o=2048&s=0#']
        )

    def test_sanitizeCell(self):
        url = 'http://www.facebook.com/search/?flt=1&amp;q=amber+melrose&amp;o=2048&amp;s=0#'
        self.assertItemsEqual(url, SanitationUtils.sanitize_cell(url))

    def test_similarComparison(self):
        url = 'http://www.facebook.com/search/?flt=1&amp;q=amber+melrose&amp;o=2048&amp;s=0#'
        self.assertItemsEqual(url, SanitationUtils.similar_comparison(url))

    def test_similarMarkupComparison(self):
        markup1 = 'Complete A Frame Assembly  (No Insert) - A-Frame Sign Parts - A-Frame Signs - Generic Signage'
        markup2 = '<p>Complete A Frame Assembly (No Insert) - A-Frame Sign Parts - A-Frame Signs - Generic Signage</p>\n'
        self.assertEqual(
            SanitationUtils.similar_markup_comparison(markup1),
            SanitationUtils.similar_markup_comparison(markup2)
        )

if __name__ == '__main__':
    # main()
    doubleNameTestSuite = unittest.TestSuite()
    doubleNameTestSuite.addTest(
        test_sanitation_utils('test_similarMarkupComparison'))
    unittest.TextTestRunner().run(doubleNameTestSuite)
