import os
from os import sys, path
from unittest import TestCase, main, skip
import unittest
import StringIO
if __name__ == '__main__' and __package__ is None:
    sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

from source.SyncUpdate import *
from source import coldata
from source.coldata import ColData_User
from source.csvparse_flat import ImportUser, CSVParse_User
from source.contact_objects import FieldGroup


class testSanitationUtils(TestCase):
    def setUp(self):
        yamlPath = "source/merger_config.yaml"

        with open(yamlPath) as stream:
            config = yaml.load(stream)

    def test_similarURL(self):
        url1 = 'http://www.technotan.com.au'
        url2 = 'www.technotan.com.au'
        self.assertEqual(SanitationUtils.similarURLComparison(url1), url2)
        self.assertEqual(SanitationUtils.similarURLComparison(url2), url2)

    def test_findallEmails(self):
        email1 = "derwentx@gmail.com archive"
        self.assertItemsEqual( SanitationUtils.findallEmails(email1),
                              [u'derwentx@gmail.com'])
        email2 = "derwentx@gmail.com derwent@laserphile.com"
        self.assertItemsEqual( SanitationUtils.findallEmails(email2),
                              [u'derwentx@gmail.com', 'derwent@laserphile.com'])

    def test_findUrl(self):
        url1 = "http://www.laserphile.com/ lol"
        self.assertItemsEqual(
            SanitationUtils.findallURLs(url1),
            ['http://www.laserphile.com/'])

if __name__ == '__main__':
    main()
    # doubleNameTestSuite = unittest.TestSuite()
    # doubleNameTestSuite.addTest(testSyncUpdate('test_similarURL'))
    # unittest.TextTestRunner().run(doubleNameTestSuite)
