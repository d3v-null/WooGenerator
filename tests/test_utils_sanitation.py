# coding=utf-8

import unittest
from unittest import TestCase

from context import woogenerator
from woogenerator.utils import Registrar, SanitationUtils

class TestSanitationUtils(TestCase):
    def setUp(self):
        Registrar.DEBUG_ERROR = False
        Registrar.DEBUG_WARN = False
        Registrar.DEBUG_MESSAGE = False
        Registrar.DEBUG_PROGRESS = False

        # Registrar.DEBUG_ERROR = True
        # Registrar.DEBUG_WARN = True
        # Registrar.DEBUG_MESSAGE = True
        # Registrar.DEBUG_PROGRESS = True

    def test_find_all_urls(self):
        self.assertEqual(
            SanitationUtils.find_all_urls("http://www.technotan.com.au/"),
            [u'http://www.technotan.com.au/']
        )
        self.assertEqual(
            SanitationUtils.find_all_urls("http://www.technotan.com.au/?p=1"),
            [u'http://www.technotan.com.au/?p=1']
        )
        self.assertEqual(
            SanitationUtils.find_all_urls("www.technotan.com.au"),
            []
        )

    def test_find_all_domains(self):
        self.assertEqual(
            SanitationUtils.find_all_domains("http://www.technotan.com.au/"),
            [u'www.technotan.com.au']
        )
        self.assertEqual(
            SanitationUtils.find_all_domains("http://www.technotan.com.au/?p=1"),
            [u'www.technotan.com.au']
        )
        self.assertEqual(
            SanitationUtils.find_all_domains("www.technotan.com.au"),
            [u'www.technotan.com.au']
        )

    # def test_strip_scheme(self):
    #     self.assertEqual(
    #         'www.google.com/',
    #         SanitationUtils.strip_url_scheme('http://www.google.com/')
    #     )

    def test_strip_protocol(self):
        self.assertEqual(
            'www.google.com/',
            SanitationUtils.strip_url_protocol('http://www.google.com/')
        )

    def test_encode_json(self):
        pass

        # obj = {
        #     'key': SanitationUtils.coerce_bytes(" 👌 ashdfk"),
        #     'list': [
        #         "🐸",
        #         u"\u2014"
        #     ]
        # }
        # print obj, repr(obj)
        # obj_json = SanitationUtils.encode_json(obj)
        # SanitationUtils.safe_print(obj_json, repr(obj_json) )
        # obj_json_base64 = SanitationUtils.encode_base64(obj_json)
        # print obj_json_base64
        # obj_json_decoded = SanitationUtils.decode_base64(obj_json_base64)
        # print obj_json_decoded
        # obj_decoded = SanitationUtils.decode_json(obj_json_decoded)
        # print obj_decoded

        # fields = {
        #     u'first_name':  SanitationUtils.coerce_bytes(u'no👌od👌le'),
        #     'user_url': "http://www.laserphile.com/asd",
        #     'first_name': 'noo-dle',
        #     'user_login': "admin"
        # }
        #
        # SanitationUtils.safe_print( fields, repr(fields) )
        # fields_json = SanitationUtils.encode_json(fields)
        # SanitationUtils.safe_print( fields_json, repr(fields_json) )
        # fields_json_base64 = SanitationUtils.encode_base64( fields_json )
        # SanitationUtils.safe_print( fields_json_base64, repr(fields_json_base64) )

        # should be   eyJ1c2VyX2xvZ2luIjogImFkbWluIiwgImZpcnN0X25hbWUiOiAibm/wn5GMb2Twn5GMbGUiLCAidXNlcl91cmwiOiAiaHR0cDovL3d3dy5sYXNlcnBoaWxlLmNvbS9hc2QifQ==
        # is actually
        # eyJ1c2VyX2xvZ2luIjogImFkbWluIiwgImZpcnN0X25hbWUiOiAibm_wn5GMb2Twn5GMbGUiLCAidXNlcl91cmwiOiAiaHR0cDovL3d3dy5sYXNlcnBoaWxlLmNvbS9hc2QifQ==

    def test_similar_phone_comparison(self):
        pass
        # n1 = u"D\u00C8RWENT"
        # n2 = u"d\u00E8rwent"
        # print SanitationUtils.unicodeToByte(n1) , \
        #     SanitationUtils.unicodeToByte(SanitationUtils.similar_comparison(n1)), \
        #     SanitationUtils.unicodeToByte(n2), \
        #     SanitationUtils.unicodeToByte(SanitationUtils.similar_comparison(n2))

        # p1 = "+61 04 3190 8778"
        # p2 = "04 3190 8778"
        # p3 = "+61 (08) 93848512"
        # print \
        #     SanitationUtils.similar_phone_comparison(p1), \
        #     SanitationUtils.similar_phone_comparison(p2), \
        #     SanitationUtils.similar_phone_comparison(p3)

    def test_make_safe_output(self):
        pass
        # print SanitationUtils.makeSafeOutput(u"asdad \u00C3 <br> \n \b")

    def test_similar_comparison(self):
        pass

        # tru = SanitationUtils.similar_comparison(u"TRUE")

        # print \
        #     SanitationUtils.similar_tru_str_comparison('yes'), \
        #     SanitationUtils.similar_tru_str_comparison('no'), \
        #     SanitationUtils.similar_tru_str_comparison('TRUE'),\
        #     SanitationUtils.similar_tru_str_comparison('FALSE'),\
        #     SanitationUtils.similar_tru_str_comparison(0),\
        #     SanitationUtils.similar_tru_str_comparison('0'),\
        #     SanitationUtils.similar_tru_str_comparison(u"0")\

    def test_make_safe_html_output(self):
        pass
        # a = u'TechnoTan Roll Up Banner Insert \u2014 Non personalised - Style D'
        # print 'a', repr(a)
        # b = SanitationUtils.makeSafeOutput(a)
        # print 'b', repr(b)
        # b = SanitationUtils.makeSafeHTMLOutput(u"T\u00C8A GRAHAM\nYEAH")
        # print 'b', b, repr(b)
        # c = SanitationUtils.makeSafeHTMLOutput(None)
        # print 'c', c, repr(c)
        # print SanitationUtils.makeSafeOutput(None)
        # c = SanitationUtils.decodeSafeOutput(b)
        # print 'c', repr(c)
        # a = u'TechnoTan Roll Up Banner Insert \u2014 Non per\nsonalised - Style D'
        # SanitationUtils.safe_print( SanitationUtils.escape_newlines(a))
