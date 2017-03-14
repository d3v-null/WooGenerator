from os import sys, path
import unittest
from unittest import TestCase, main, skip

from context import woogenerator
from woogenerator.parsing.csvparse_user import ImportUser

class testUsrObj(TestCase):
    def setUp(self):
        self.usr = ImportUser(
            {
                'E-mail': 'derwentx@gmail.com invalid',
                'Personal E-mail': 'derwent@laserphile.com notes',
                'Web Site': 'http://www.laserphile.com/ blah',
                'Phone': '0416160912 bad',
                'Mobile Phone': '(+61) 433124710 derp'
            }
        )

    def test_sanitizeURL(self):
        self.assertEqual(self.usr['Web Site'], 'http://www.laserphile.com/')

    def test_sanitizeEmail(self):
        self.assertEqual(self.usr.email, 'derwentx@gmail.com')
        self.assertEqual(self.usr['Personal E-mail'], 'derwent@laserphile.com')

    def test_sanitizePhone(self):
        self.assertEqual(self.usr['Phone'], '0416160912')
        self.assertEqual(self.usr['Mobile Phone'], '(+61)433124710')


if __name__ == '__main__':
    main()

    # testSuite = unittest.TestSuite()
    # testSuite.addTest(testSocialMediaGroup('test_print'))
    # unittest.TextTestRunner().run(testSuite)
