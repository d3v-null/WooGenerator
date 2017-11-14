# -*- coding: utf-8 -*-
from __future__ import absolute_import

import base64
import cgi
import functools
import inspect
import itertools
import json
import math
import os
import random
import re
import sys
import time
import traceback
from collections import Counter, OrderedDict
from HTMLParser import HTMLParser
from urlparse import parse_qs, urlparse

import cjson
import unicodecsv
from kitchen.text import converters
import phpserialize

from jsonpath_ng import jsonpath

DEFAULT_ENCODING = 'utf8'


class SanitationUtils(object):
    email_regex = r"[\w.+-]+@[\w-]+\.[\w.-]+"
    regex_url_simple = (
        r"https?:\/\/(?:www\.)?"
        r"[-a-zA-Z0-9@:%._\+~#=]{2,256}\.[a-z]{2,6}\b(?:[-a-zA-Z0-9@:%_\+.~#?&//=]*)"
    )
    regex_domain_simple = (
        r"[-a-zA-Z0-9@:%._\+~#=]{2,256}\.[a-z]{2,6}"
    )
    regex_url = \
        ur'(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)' +\
        ur'(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+' +\
        ur'(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:\'".,<>?]))'
    regex_wc_link = ur"<(?P<url>{0})>; rel=\"(?P<rel>\w+)\"".format(regex_url)
    cell_email_regex = r"^%s$" % email_regex
    myobid_regex = r"C\d+"
    punctuationChars = [
        r'!', r'"', r'\#', r'\$', r'%',
        r'&', r'\'', r'(', r')', r'\*',
        r'\+', r',', r'\-', r'\.', r'/',
        r':', r';', r'<', r'=', r'>',
        r'\?', r'@', r'\[', r'\\', r'\]',
        r'\^', r'_', r'`', r'\{', r'\|', r'\}', r'~'
    ]
    allowedPunctuation = [
        r'\-', r'\.', r'\''
    ]
    allowedPhonePunctuation = [
        r'\-', r'\.', r'(', r')', r'\+'
    ]
    disallowedPunctuation = list(
        set(punctuationChars) - set(allowedPunctuation))
    whitespaceChars = [r' ', r'\t', r'\r', r'\n', 'r\f']
    # disallowed punctuation and whitespace
    disallowedPunctuationOrSpace = list(
        set(disallowedPunctuation + whitespaceChars))
    # delimeter characters incl whitespace and disallowed punc
    tokenDelimeters = list(
        set([r"\d"] + disallowedPunctuation + whitespaceChars))
    # delimeter characters including all punctuation and whitespace
    tokenPunctuationDelimeters = list(
        set([r"\d"] + punctuationChars + whitespaceChars))
    # delimeter characters excl space
    tokenDelimetersNoSpace = list(
        set(disallowedPunctuation + whitespaceChars + [r"\d"]) - set([' ']))
    punctuationRegex = r"[%s]" % "".join(punctuationChars)
    # delimeter characters incl space and disallowed punc
    delimeterRegex = r"[%s]" % "".join(tokenDelimeters)
    # disallowed punctuation and whitespace
    bad_punc_or_space_regex = r"[%s]" % "".join(
        disallowedPunctuationOrSpace)
    # disallowed punctuation
    disallowedPunctuationRegex = r"[%s]" % "".join(disallowedPunctuation)
    # not a delimeter (no whitespace or disallowed punc)
    nondelimeterRegex = r"[^%s]" % "".join(tokenDelimeters)
    # not a delimeter or punctuation (no punctuation or whitespace)
    nondelimeterPunctuationRegex = r"[^%s]" % "".join(
        tokenPunctuationDelimeters)
    # not a delimeter except space (no whitespace except space, no disallowed
    # punc)
    nondelimeterOrSpaceRegex = r"[^%s]" % "".join(tokenDelimetersNoSpace)
    disallowedPhoneCharRegex = r"[^%s]" % "".join(
        allowedPhonePunctuation + [r'\d', r' '])
    clearStartRegex = r"(?<!%s)" % nondelimeterRegex
    clearFinishRegex = r"(?!%s)" % nondelimeterRegex
    currency_precision = 2

    @classmethod
    def wrap_clear_regex(cls, regex):
        return cls.clearStartRegex + regex + cls.clearFinishRegex

    @classmethod
    def identify_abbreviation(cls, abbrv_dict, string):
        for abbrv_key, abbrvs in abbrv_dict.items():
            if string in abbrvs + [abbrv_key]:
                return abbrv_key
        return string

    @classmethod
    def identify_abbreviations(cls, abbrv_dict, string):
        matches = re.findall(
            '(' + cls.compile_abbrv_regex(abbrv_dict) + ')',
            string
        )

        for candidate in [match for match in filter(None, matches)]:
            identified = cls.identify_abbreviation(abbrv_dict, candidate)
            if identified:
                yield identified

    @classmethod
    def compile_partial_abbrv_regex(cls, abbrv_key, abbrvs):
        return "|".join([
            abbrv for abbrv in abbrvs + [abbrv_key] if abbrv
        ])

    @classmethod
    def compile_abbrv_regex(cls, abbrv):
        compiled_regex = [
            cls.compile_partial_abbrv_regex(abbrv_key, abbrv_value)
            for abbrv_key, abbrv_value in abbrv.items()
        ]
        return "|".join(
            [compiled for compiled in compiled_regex if compiled]
        )

    @classmethod
    def compose(cls, *functions):
        """
        Compose a list of functions into a single function.

        Stolen from: https://mathieularose.com/function-composition-in-python/
        """
        def compose2(func_f, func_g):
            return lambda x: func_f(func_g(x))
        return functools.reduce(compose2, functions)

    # Functions for dealing with string encodings

    @classmethod
    def identity(cls, thing):
        return thing

    @classmethod
    def assert_ascii(cls, string):
        for index, char in enumerate(string):
            assert ord(char) < 128, "char %s of string %s ... is not ascii" % (
                index, (string[:index - 1]))

    @classmethod
    def unicode_to_utf8(cls, u_str):
        assert isinstance(u_str, unicode),\
            "parameter should be unicode not %s" % type(u_str)
        byte_return = converters.to_bytes(u_str, "utf8")
        assert isinstance(byte_return, str),\
            "something went wrong, should return str not %s" % type(
                byte_return)
        return byte_return

    @classmethod
    def unicode_to_ascii(cls, u_str):
        assert isinstance(u_str, unicode),\
            "parameter should be unicode not %s" % type(u_str)
        byte_return = converters.to_bytes(u_str, "ascii", "backslashreplace")
        assert isinstance(byte_return, str),\
            "something went wrong, should return str not %s" % type(
                byte_return)
        return byte_return

    @classmethod
    def unicode_to_xml(cls, u_str, ascii_only=False):
        assert isinstance(u_str, unicode),\
            "parameter should be unicode not %s" % type(u_str)
        if ascii_only:
            byte_return = converters.unicode_to_xml(u_str, encoding="ascii")
        else:
            byte_return = converters.unicode_to_xml(u_str)
        return byte_return

    @classmethod
    def utf8_to_unicode(cls, utf8_str):
        assert isinstance(utf8_str, str),\
            "parameter should be str not %s" % type(utf8_str)
        byte_return = converters.to_unicode(utf8_str, "utf8")
        assert isinstance(byte_return, unicode),\
            "something went wrong, should return unicode not %s" % type(
                byte_return)
        return byte_return

    @classmethod
    def xml_to_unicode(cls, utf8_str):
        byte_return = converters.xml_to_unicode(utf8_str)
        return byte_return

    @classmethod
    def ascii_to_unicode(cls, ascii_str):
        assert isinstance(ascii_str, str),\
            "parameter should be str not %s" % type(ascii_str)
        # literal_eval("b'{}'".format(ascii_str)).decode('utf-8')
        # unicode_return = converters.to_unicode(ascii_str, "ascii")
        unicode_return = ascii_str.decode('unicode-escape')
        assert isinstance(unicode_return, unicode),\
            "something went wrong, should return unicode not %s" % type(
                unicode_return)
        return unicode_return

    @classmethod
    def coerce_unicode(cls, thing):
        if thing is None:
            unicode_return = u""
        else:
            unicode_return = converters.to_unicode(thing, encoding="utf8")
        assert isinstance(unicode_return, unicode),\
            "something went wrong, should return unicode not %s" % type(
                unicode_return)
        return unicode_return

    @classmethod
    def coerce_bytes(cls, thing):
        byte_return = cls.compose(
            cls.unicode_to_utf8,
            cls.coerce_unicode
        )(thing)
        assert isinstance(byte_return, str),\
            "something went wrong, should return str not %s" % type(
                byte_return)
        return byte_return

    @classmethod
    def coerce_ascii(cls, thing):
        byte_return = cls.compose(
            cls.unicode_to_ascii,
            cls.coerce_unicode
        )(thing)
        assert isinstance(byte_return, str),\
            "something went wrong, should return str not %s" % type(
                byte_return)
        return byte_return

    @classmethod
    def coerce_xml(cls, thing):
        byte_return = cls.compose(
            cls.unicode_to_xml,
            cls.coerce_unicode
        )(thing)
        assert isinstance(byte_return, str),\
            "something went wrong, should return str not %s" % type(
                byte_return)
        return byte_return

    @classmethod
    def coerce_float(cls, thing):
        unicode_thing = cls.compose(
            cls.coerce_unicode
        )(thing)
        try:
            float_return = float(unicode_thing)
        except ValueError:
            float_return = 0.0
        assert isinstance(float_return, float),\
            "something went wrong, should return str not %s" % type(
                float_return)
        return float_return

    @classmethod
    def coerce_int(cls, thing):
        unicode_thing = cls.compose(
            cls.coerce_unicode
        )(thing)
        try:
            int_return = int(unicode_thing)
        except ValueError:
            int_return = 0
        assert isinstance(int_return, int),\
            "something went wrong, should return str not %s" % type(
                int_return)
        return int_return

    @classmethod
    def yesno2bool(cls, string):
        return string.lower().startswith('y')

    @classmethod
    def bool2yesno(cls, bool_):
        return 'yes' if bool_ else 'no'

    @classmethod
    def stock_status2bool(cls, string):
        return string.lower() == 'instock'

    @classmethod
    def bool2stock_status(cls, bool_):
        return 'instock' if bool_ else 'outofstock'

    @classmethod
    def normalize_optional_int_minus_1(cls, thing):
        if thing:
            return int(thing)
        else:
            return -1

    @classmethod
    def normalize_optional_int_zero(cls, thing):
        if thing:
            return int(thing)
        else:
            return 0

    @classmethod
    def limit_string(cls, length):
        return lambda x: x[:length]

    @classmethod
    def sanitize_for_table(cls, thing, tablefmt=None):
        if hasattr(thing, '_supports_tablefmt'):
            thing = thing.__unicode__(tablefmt)
        if isinstance(thing, (str, unicode)) and tablefmt == 'simple':
            thing = thing[:64] + '...'
        unicode_return = cls.compose(
            cls.coerce_unicode,
            cls.limit_string(50),
            cls.escape_newlines,
            cls.coerce_unicode
        )(thing)
        assert isinstance(unicode_return, unicode),\
            "something went wrong, should return unicode not %s" % type(
                unicode_return)
        return unicode_return

    @classmethod
    def sanitize_for_xml(cls, thing):
        unicode_return = cls.compose(
            cls.coerce_unicode,
            cls.sanitize_newlines,
            cls.unicode_to_xml,
            cls.coerce_unicode
        )(thing)
        assert isinstance(unicode_return, unicode),\
            "something went wrong, should return unicode not %s" % type(
                unicode_return)
        return unicode_return

    @classmethod
    def safe_print(cls, *args):
        print " ".join([cls.coerce_bytes(arg) for arg in args])

    @classmethod
    def normalize_val(cls, thing):
        unicode_return = cls.compose(
            cls.coerce_unicode,
            cls.to_upper,
            cls.strip_leading_whitespace,
            cls.strip_tailing_whitespace,
            cls.strip_extra_whitespace,
            cls.coerce_unicode
        )(thing)
        assert isinstance(unicode_return, unicode),\
            "something went wrong, should return unicode not %s" % type(
                unicode_return)
        return unicode_return

    @classmethod
    def remove_leading_dollar_wspace(cls, string):
        str_out = re.sub(r'^\W*\$', '', string)
        if Registrar.DEBUG_UTILS:
            print "remove_leading_dollar_wspace", repr(string), repr(str_out)
        return str_out

    @classmethod
    def remove_leading_quote(cls, string):
        str_out = re.sub(r'^\'', '', string)
        if Registrar.DEBUG_UTILS:
            print "remove_leading_quote", repr(string), repr(str_out)
        return str_out

    @classmethod
    def remove_leading_percent_wspace(cls, string):
        str_out = re.sub(r'%\W*$', '', string)
        if Registrar.DEBUG_UTILS:
            print "remove_leading_percent_wspace", repr(string), repr(str_out)
        return str_out

    @classmethod
    def remove_lone_dashes(cls, string):
        str_out = re.sub(r'^-$', '', string)
        if Registrar.DEBUG_UTILS:
            print "remove_lone_dashes", repr(string), repr(str_out)
        return str_out

    @classmethod
    def remove_thousands_separator(cls, string):
        str_out = re.sub(r'(\d+),(\d{3})', r'\g<1>\g<2>', string)
        if Registrar.DEBUG_UTILS:
            print "remove_thousands_separator", repr(string), repr(str_out)
        return str_out

    @classmethod
    def remove_lone_white_space(cls, string):
        str_out = re.sub(r'^\s*$', '', string)
        if Registrar.DEBUG_UTILS:
            print "remove_lone_white_space", repr(string), repr(str_out)
        return str_out

    @classmethod
    def remove_null(cls, string):
        str_out = re.sub(r'^NULL$', '', string)
        if Registrar.DEBUG_UTILS:
            print "remove_null", repr(string), repr(str_out)
        return str_out

    @classmethod
    def strip_leading_whitespace(cls, string):
        if not isinstance(string, basestring):
            return string
        str_out = re.sub(r'^\s*', '', string)
        if Registrar.DEBUG_UTILS:
            print "strip_leading_whitespace", repr(string), repr(str_out)
        return str_out

    @classmethod
    def strip_leading_newline(cls, string):
        if not isinstance(string, basestring):
            return string
        str_out = re.sub(r'^(\\n|\n)*', '', string)
        if Registrar.DEBUG_UTILS:
            print "strip_leading_newline", repr(string), repr(str_out)
        return str_out

    @classmethod
    def strip_tailing_whitespace(cls, string):
        if not isinstance(string, basestring):
            return string
        str_out = re.sub(r'\s*$', '', string)
        if Registrar.DEBUG_UTILS:
            print "strip_tailing_whitespace", repr(string), repr(str_out)
        return str_out

    @classmethod
    def strip_tailing_newline(cls, string):
        if not isinstance(string, basestring):
            return string
        str_out = re.sub(r'(\\n|\n)*$', '', string)
        if Registrar.DEBUG_UTILS:
            print "strip_tailing_newline", repr(string), repr(str_out)
        return str_out

    @classmethod
    def strip_all_whitespace(cls, string):
        if not isinstance(string, basestring):
            return string
        str_out = re.sub(r'\s', '', string)
        if Registrar.DEBUG_UTILS:
            print "strip_all_whitespace", repr(string), repr(str_out)
        return str_out

    @classmethod
    def strip_extra_whitespace(cls, string):
        if not isinstance(string, basestring):
            return string
        str_out = re.sub(r'\s{2,}', ' ', string)
        if Registrar.DEBUG_UTILS:
            print "strip_extra_whitespace", repr(string), repr(str_out)
        return str_out

    @classmethod
    def strip_non_numbers(cls, string):
        if not isinstance(string, basestring):
            return string
        str_out = re.sub(r'[^\d]', '', string)
        if Registrar.DEBUG_UTILS:
            print "strip_non_numbers", repr(string), repr(str_out)
        return str_out

    @classmethod
    def strip_non_phone_characters(cls, string):
        if not isinstance(string, basestring):
            return string
        str_out = re.sub(cls.disallowedPhoneCharRegex, '', string)
        return str_out

    @classmethod
    def strip_punctuation(cls, string):
        if not isinstance(string, basestring):
            return string
        str_out = re.sub(r'[%s]' % ''.join(cls.punctuationChars), '', string)
        if Registrar.DEBUG_UTILS:
            print "strip_punctuation", repr(string), repr(str_out)
        return str_out

    @classmethod
    def strip_area_code(cls, string):
        if not isinstance(string, basestring):
            return string
        str_out = re.sub(r'\s*\+\d{2,3}\s*', '', string)
        if Registrar.DEBUG_UTILS:
            print "strip_area_code", repr(string), repr(str_out)
        return str_out

    @classmethod
    def strip_url_protocol(cls, string):
        if not isinstance(string, basestring):
            return string
        str_out = re.sub(r"^\w+://", "", string)
        if Registrar.DEBUG_UTILS:
            print "strip_url_protocol", repr(string), repr(str_out)
        return str_out

    @classmethod
    def strip_p_tags(cls, string):
        if not isinstance(string, basestring):
            return string
        str_out = re.sub(r"</?p[^>]*>", "", string)
        return str_out

    @classmethod
    def strip_br_tags(cls, string):
        if not isinstance(string, basestring):
            return string
        str_out = re.sub(r"</?\s*br\s*/?>", "", string)
        return str_out

    @classmethod
    def replace_br_tags(cls, string):
        if not isinstance(string, basestring):
            return string
        str_out = re.sub(r"</?\s*br\s*/?>", "\n", string)
        return str_out

    # @classmethod
    # def strip_url_scheme(cls, url):
    #     str_out = url
    #     result = urlparse(url)
    #     if result:
    #         if result.scheme:
    #             remove_str = '%s:' % result.scheme
    #             if str_out.startswith(remove_str):
    #                 str_out = str_out[len(remove_str):]
    #     if Registrar.DEBUG_UTILS:
    #         print "strip_url_scheme", repr(url), repr(str_out)
    #     return str_out

    @classmethod
    def strip_url_host(cls, url):
        str_out = url
        result = urlparse(url)
        if result:
            if result.scheme:
                remove_str = '%s:' % result.scheme
                if str_out.startswith(remove_str):
                    str_out = str_out[len(remove_str):]
            if result.netloc:
                remove_str = '//%s' % result.netloc
                if str_out.startswith(remove_str):
                    str_out = str_out[len(remove_str):]

        if Registrar.DEBUG_UTILS:
            print "strip_url_host", repr(url), repr(str_out)
        return str_out

    @classmethod
    def to_lower(cls, string):
        str_out = string.lower()
        if Registrar.DEBUG_UTILS:
            print "to_lower", repr(string), repr(str_out)
        return str_out

    @classmethod
    def to_upper(cls, string):
        str_out = string.upper()
        if Registrar.DEBUG_UTILS:
            print "to_upper", repr(string), repr(str_out)
        return str_out

    @classmethod
    def sanitize_newlines(cls, string):
        return re.sub('\n', '</br>', string)

    @classmethod
    def escape_newlines(cls, string):
        return re.sub('\n', r'\\n', string)

    @classmethod
    def compile_regex(cls, subs):
        if subs:
            return re.compile("(%s)" % '|'.join(
                filter(None, map(re.escape, subs))))
        else:
            return None

    @classmethod
    def sanitize_cell(cls, cell):
        return cls.compose(
            cls.remove_leading_dollar_wspace,
            cls.remove_leading_percent_wspace,
            cls.remove_lone_dashes,
            # cls.strip_extra_whitespace,
            # cls.strip_all_whitespace,
            cls.remove_thousands_separator,
            cls.remove_lone_white_space,
            cls.strip_leading_whitespace,
            cls.strip_tailing_whitespace,
            cls.sanitize_newlines,
            cls.strip_tailing_newline,
            cls.strip_leading_newline,
            cls.remove_null,
            cls.coerce_unicode,
        )(cell)

    @classmethod
    def sanitize_special_cell(cls, cell):
        return cls.compose(
            # cls.remove_leading_dollar_wspace,
            # cls.remove_leading_percent_wspace,
            # cls.remove_lone_dashes,
            # cls.strip_extra_whitespace,
            cls.remove_thousands_separator,
            cls.remove_lone_white_space,
            cls.strip_leading_whitespace,
            cls.strip_tailing_whitespace,
            cls.sanitize_newlines,
            cls.strip_tailing_newline,
            cls.strip_leading_newline,
            cls.remove_null,
            cls.coerce_unicode
        )(cell)

    @classmethod
    def sanitize_class(cls, string):
        return re.sub('[^a-z]', '', string.lower())

    @classmethod
    def slugify(cls, string):
        string = re.sub('[^a-z0-9 _]', '', string.lower())
        return re.sub(' ', '_', string)

    @classmethod
    def similar_comparison(cls, string):
        return cls.compose(
            cls.to_lower,
            cls.strip_leading_whitespace,
            cls.strip_tailing_whitespace,
            cls.coerce_unicode
        )(string)

    @classmethod
    def similar_no_punc_cmp(cls, string):
        return cls.compose(
            cls.normalize_val,
            cls.strip_punctuation,
        )(string)

    @classmethod
    def similar_phone_comparison(cls, string):
        return cls.compose(
            cls.coerce_unicode,
            cls.coerce_int,
            cls.strip_non_numbers,
            cls.strip_area_code,
            cls.strip_extra_whitespace,
            cls.strip_non_phone_characters,
            cls.coerce_unicode
        )(string)

    @classmethod
    def similar_tru_str_comparison(cls, string):
        return cls.compose(
            cls.truish_string_to_bool,
            cls.similar_comparison
        )(string)

    @classmethod
    def similar_url_comparison(cls, string):
        return cls.compose(
            cls.strip_url_protocol,
            cls.coerce_unicode
        )(string)

    @classmethod
    def similar_markup_comparison(cls, string):
        return cls.compose(
            cls.to_lower,
            cls.strip_leading_whitespace,
            cls.strip_tailing_whitespace,
            cls.strip_extra_whitespace,
            cls.strip_p_tags,
            cls.strip_br_tags,
            cls.coerce_unicode
        )(string)

    @classmethod
    def similar_currency_comparison(cls, string):
        return cls.compose(
            cls.round_currency,
            cls.coerce_float,
            cls.remove_leading_dollar_wspace,
            # cls.remove_leading_quote,
            cls.coerce_unicode,
        )(string)

    @classmethod
    def make_safe_class(cls, string):
        return cls.compose(
            cls.strip_all_whitespace,
            cls.strip_punctuation
        )(string)

    @classmethod
    def normalize_wp_rendered_content(cls, string):
        return cls.compose(
            # cls.strip_leading_whitespace,
            # cls.strip_tailing_whitespace,
            cls.strip_tailing_newline,
            cls.xml_to_unicode,
            cls.strip_p_tags,
            cls.replace_br_tags,
            cls.coerce_unicode
        )(string)

    @classmethod
    def shorten(cls, reg, subs, str_in):
        # if(Registrar.DEBUG_GEN):
        #     print "calling shorten"
        #     print " | reg:", reg
        #     print " | subs:", subs
            # print " | str_i: ",str_in
        if not all([reg, subs, str_in]):
            str_out = str_in
        else:
            str_out = reg.sub(
                lambda mo: subs[mo.string[mo.start():mo.end()]],
                str_in
            )
        # if Registrar.DEBUG_GEN:
        #     print " | str_o: ",str_out
        return str_out

    @classmethod
    def round_currency(cls, price):
        return round(price, cls.currency_precision)

    @classmethod
    def html_unescape(cls, string):
        return HTMLParser().unescape(string)

    @classmethod
    def html_escape(cls, string):
        return cgi.escape(string)

    @classmethod
    def html_unescape_recursive(cls, things):
        if isinstance(things, list):
            return [cls.html_unescape_recursive(thing) for thing in things]
        elif isinstance(things, (str, unicode)):
            return cls.html_unescape(cls.coerce_unicode(things))
        else:
            return things

    @classmethod
    def find_all_images(cls, instring):
        instring = cls.coerce_unicode(instring)
        return re.findall(r'\s*([^.|]*\.[^.|\s]*)(?:\s*|\s*)', instring)

    @classmethod
    def find_all_tokens(cls, instring, delim="|"):
        instring = cls.coerce_unicode(instring)
        escaped_delim = re.escape(delim)
        return re.findall(r'\s*(\b[^\s.%s]+\b)\s*' % escaped_delim, instring)

    @classmethod
    def find_all_dollars(cls, instring):
        instring = cls.coerce_unicode(instring)
        return re.findall(r"\s*\$([\d,]+\.?\d*)", instring)

    @classmethod
    def find_all_percent(cls, instring):
        instring = cls.coerce_unicode(instring)
        return re.findall(r"\s*(\d+\.?\d*)%", instring)

    @classmethod
    def find_all_emails(cls, instring):
        instring = cls.coerce_unicode(instring)
        return re.findall(
            cls.wrap_clear_regex(cls.email_regex),
            instring
        )

    @classmethod
    def find_all_urls(cls, instring):
        instring = cls.coerce_unicode(instring)
        instring = cls.html_unescape(instring)
        return re.findall(
            '(' + cls.regex_url_simple + ')',
            instring
        )

    @classmethod
    def find_all_domains(cls, instring):
        instring = cls.coerce_unicode(instring)
        instring = cls.html_unescape(instring)
        return re.findall(
            '(' + cls.regex_domain_simple + ')',
            instring
        )

    # @classmethod
    # def findall_wp_links(cls, string):
    #     # TODO: implement
    #     return []

    @classmethod
    def findall_wc_links(cls, string):
        """Finds all wc style link occurences in a given string"""
        matches = []
        lines = string.split(', ')
        print lines
        for line in lines:
            print 'processing line', line
            print 'attempting match on %s' % cls.regex_wc_link
            match = re.match(cls.regex_wc_link, line)
            print "match", match
            if match is None:
                print "match is none"
                continue
            else:
                print "match is none"
            match_dict = match.groupdict()
            if 'url' in match_dict and 'rel' in match_dict:
                matches.append(match_dict)
        print 'returning matches', matches
        return matches

    @classmethod
    def findall_url_params(cls, url):
        result = urlparse(url)
        if result and result.query:
            return parse_qs(result.query)
        else:
            return {}

    @classmethod
    def title_splitter(cls, instring):
        assert isinstance(instring, (str, unicode)), \
            "param must be a string not %s" % type(instring)
        if not isinstance(instring, unicode):
            instring = instring.decode('utf-8')
        found = re.findall(r"^\s*(.*?)\s+[^\s\w&\(\)]\s+(.*?)\s*$", instring)
        if found:
            return found[0]
        else:
            return instring, ""

    @classmethod
    def string_is_email(cls, email):
        return re.match(cls.email_regex, email)

    @classmethod
    def string_is_myobid(cls, card):
        return re.match(cls.myobid_regex, card)

    @classmethod
    def string_capitalized(cls, string):
        return unicode(string) == unicode(string).upper()

    @classmethod
    def string_contains_numbers(cls, string):
        return bool(re.search(r'\d', string))

    @classmethod
    def string_contains_no_numbers(cls, string):
        return not cls.string_contains_numbers(string)

    @classmethod
    def string_contains_delimeters(cls, string):
        return True if(re.search(cls.delimeterRegex, string)) else False

    @classmethod
    def string_contains_bad_punc(cls, string):
        return True if(
            re.search(cls.disallowedPunctuationRegex, string)) else False

    @classmethod
    def string_contains_punctuation(cls, string):
        return True if(re.search(cls.punctuationRegex, string)) else False

    @classmethod
    def truish_string_to_bool(cls, string):
        if not string or 'n' in string or 'false' in string \
                or string == '0' or string == 0:
            if Registrar.DEBUG_UTILS:
                print "truish_string_to_bool", repr(string), 'FALSE'
            return "FALSE"
        else:
            if Registrar.DEBUG_UTILS:
                print "truish_string_to_bool", repr(string), 'TRUE'
            return "TRUE"

    @classmethod
    def bool_to_truish_string(cls, bool_val):
        if bool_val:
            return "TRUE"
        else:
            return "FALSE"

    @classmethod
    def decode_json(cls, json_str, **kwargs):
        assert isinstance(json_str, (str, unicode))
        # attrs = cjson.decode(json_str, **kwargs)
        attrs = json.loads(json_str, **kwargs)
        return attrs

    @classmethod
    def encode_json(cls, obj, **kwargs):
        assert isinstance(obj, (dict, list))
        json_str = json.dumps(obj, **kwargs)
        # json_str = cjson.encode(obj, **kwargs)
        return json_str

    @classmethod
    def encode_base64(cls, string):
        utf8_str = cls.coerce_bytes(string)
        return base64.standard_b64encode(utf8_str)

    @classmethod
    def decode_base64(cls, b64_str):
        return base64.standard_b64decode(b64_str)


class DescriptorUtils(object):

    class DescriptorPropertySafe(property):
        """
        Differentiates safe properties created with DescriptorUtils from other properties.
        """
        pass

    class DescriptorPropertySafeNormalized(property):
        """
        Differentiates safe normalized properties created with DescriptorUtils from other properties.
        """
        pass

    class DescriptorPropertyKwargAlias(property):
        """
        Differentiates kwarg alias properties created with DescriptorUtils from other properties.
        """
        pass

    @classmethod
    def safe_key_property(cls, key):
        def getter(self):
            assert key in self.keys(), "{} must be set before get in {}".format(
                key, repr(type(self)))
            return self[key]

        def setter(self, value):
            assert isinstance(value, (str, unicode)), "{} must be set with string not {}".format(
                key, type(value))
            self[key] = value

        return cls.DescriptorPropertySafe(getter, setter)

    @classmethod
    def safe_normalized_key_property(cls, key):
        def getter(self):
            assert key in self.keys(), "{} must be set before get in {}".format(
                key, repr(type(self)))
            return SanitationUtils.normalize_val(self[key])

        def setter(self, value):
            assert isinstance(value, (str, unicode)), "{} must be set with string not {}".format(
                key, type(value))
            self[key] = value

        return cls.DescriptorPropertySafeNormalized(getter, setter)

    @classmethod
    def kwarg_alias_property(cls, key, handler):
        def getter(self):
            if self.properties_override:
                retval = handler(self)
            else:
                retval = self.kwargs.get(key)
            # print "getting ", key, "->", retval
            return retval

        def setter(self, value):
            # print "setting ", key, '<-', value
            self.kwargs[key] = value
            self.process_kwargs()

        return cls.DescriptorPropertyKwargAlias(getter, setter)


class SeqUtils(object):
    """
    Utilities for manipulating sequences like lists and dicts
    """
    @classmethod
    def combine_two_lists(cls, list_a, list_b):
        """
        Combine lists a and b uniquely, attempting to preserve order.
        """
        if not list_a:
            return list_b if list_b else []
        if not list_b:
            return list_a
        response = []
        for element in list_a + list_b:
            if element not in response:
                response.append(element)
        return response

    @classmethod
    def subtrace_two_lists(cls, list_a, list_b):
        """
        Return elements in list_a that are not in list_b.
        Attempt to preserve order
        """
        response = []
        for element in list_a:
            if element not in list_b:
                response.append(element)
        return response

    @classmethod
    def combine_lists(cls, *args):
        """
        Combine all argument lists uniquely, attempt to preserve order
        """
        response = []
        for arg in args:
            response = cls.combine_two_lists(response, arg)
        return response

    @classmethod
    def combine_two_ordered_dicts(cls, dict_a, dict_b):
        """
        Combine OrderedDict a with b by starting with A and overwriting with items from b.
        Attempt to preserve order
        """
        if not dict_a:
            return dict_b if dict_b else OrderedDict()
        if not dict_b:
            return dict_a
        response = OrderedDict(dict_a.items())
        for key, value in dict_b.items():
            response[key] = value
        return response

    @classmethod
    def combine_ordered_dicts(cls, *args):
        """
        Combine all dict arguments overwriting former with items from latter.
        Attempt to preserve order
        """
        response = OrderedDict()
        for arg in args:
            response = cls.combine_two_ordered_dicts(response, arg)
        return response

    @classmethod
    def filter_unique_true(cls, list_a):
        response = []
        for i in list_a:
            if i and i not in response:
                response.append(i)
        return response

    @classmethod
    def get_all_keys(cls, *args):
        return SeqUtils.filter_unique_true(itertools.chain(*(
            arg.keys() for arg in args if isinstance(arg, dict)
        )))

    @classmethod
    def keys_not_in(cls, dictionary, keys):
        assert isinstance(dictionary, dict)
        return type(dictionary)([
            (key, value) for key, value in dictionary.items()
            if key not in keys
        ])

    @classmethod
    def check_equal(cls, iterator):
        """
        Check that all items in an iterator are equal.

        Taken from SO answer:
        http://stackoverflow.com/questions/3844801/check-if-all-elements-in-a-list-are-identical
        """

        iterator = iter(iterator)
        try:
            first = next(iterator)
        except StopIteration:
            return True
        return all(first == rest for rest in iterator)

class JSONPathUtils(object):
    class NonSingularPathError(UserWarning):
        pass

    @classmethod
    def blank_get_field_datum(cls, path, datum, field):
        """
        Emulate jsonpath.Fields.get_field_datum but create the field in path
        if it does not exist.
        """
        try:
            field_value = datum.value[field]
        except (TypeError, KeyError, AttributeError):
            # differs from jsonpath.Fields.get_field_datum here:
            datum.value[field] = {}
            field_value = datum.value[field]
        return jsonpath.DatumInContext(
            value=field_value,
            path=jsonpath.Fields(field),
            context=datum
        )

    @classmethod
    def blank_reified_fields(cls, path, datum):
        """
        Emulate jsonpath.Fields.reified_fields but throw an exception if the
        path is nonsingular.
        """
        if '*' not in path.fields:
            return path.fields
        else:
            # differs from jsonpath.Fields.reified_fields here:
            raise cls.NonSingularPathError("'*' in path not supported")

    @classmethod
    def blank_find(cls, path, datum):
        """
        Emulate jsonpath.JSONPath.reified_fields but throw an exception if the
        path is nonsingular.
        """
        if isinstance(path, jsonpath.Child):
            return [
                submatch
                for subdata in cls.blank_find(path.left, datum)
                for submatch in cls.blank_find(path.right, subdata)
            ]
        if isinstance(path, jsonpath.Fields):
            datum  = jsonpath.DatumInContext.wrap(datum)

            return [
                field_datum
                for field_datum in [
                    cls.blank_get_field_datum(path, datum, field)
                    for field in cls.blank_reified_fields(path, datum)
                ]
                if field_datum is not None
            ]

    @classmethod
    def blank_update(cls, path, data, val):
        """
        Emulate JSONPath.update but create a path for the data if it doesn't
        exist and throw an exception if the path is nonsingular.
        Assume path looks somthing like this:
        c -- c -- f
          \- f \- f
        """

        if isinstance(path, jsonpath.Child):
            for datum in cls.blank_find(path.left, data):
                cls.blank_update(path.right, datum.value, val)
            return data

        if isinstance(path, jsonpath.Fields):
            for field in cls.blank_reified_fields(path, data):
                if field in data and hasattr(val, '__call__'):
                    val(data[field], data, field)
                    continue
                data[field] = val
            return data

        if isinstance(path, jsonpath.JSONPath):
            raise cls.NonSingularPathError(
                "path is not made of singular jsonpath objects"
            )

        # descendants = []
        # path_traverse = updater
        # while path_traverse:
        #     leaf = path_traverse
        #     if isinstance(path_traverse, jsonpath.Child):
        #         leaf = path_traverse.right
        #     if isinstance(leaf, jsonpath.Fields):
        #         descendants.append(leaf.fields[0])
        #     path_traverse = path_traverse.getattr('left', None)





class DebugUtils(object):

    @classmethod
    def get_procedure(cls, level=1):
        try:
            procedure = inspect.stack()[level][3]
            # return procedure
            path = inspect.stack()[level][1]
            basename = 'source/' + os.path.basename(path)
            line = inspect.stack()[level][2]
            baseline = "%s:%s" % (basename, line)
            return ".".join([baseline, str(procedure)])
        except BaseException:
            return None

    @classmethod
    def get_caller_procedure(cls, level=0):
        return cls.get_procedure(3 + level)

    @classmethod
    def get_caller_procedures(cls, levels=2):
        procedures = map(cls.get_caller_procedure, range(1, levels + 1))
        return ">".join(reversed(filter(None, procedures)))

    @classmethod
    def hashify(cls, in_str):
        out_str = "#" * (len(in_str) + 4) + "\n"
        out_str += "# " + in_str + " #\n"
        out_str += "#" * (len(in_str) + 4) + "\n"
        return out_str


class Registrar(object):
    messages = OrderedDict()
    errors = OrderedDict()
    warnings = OrderedDict()
    stack_counts = OrderedDict()
    object_indexer = id
    DEBUG_ERROR = True
    DEBUG_WARN = True
    DEBUG_MESSAGE = False
    DEBUG_PROGRESS = True
    DEBUG_ABSTRACT = False
    DEBUG_ADDRESS = False
    DEBUG_API = False
    DEBUG_CATS = False
    DEBUG_CLIENT = False
    DEBUG_CONTACT = False
    DEBUG_DUPLICATES = False
    DEBUG_GDRIVE = False
    DEBUG_GEN = False
    DEBUG_IMG = False
    DEBUG_MRO = False
    DEBUG_MYO = False
    DEBUG_NAME = False
    DEBUG_PARSER = False
    DEBUG_ROLE = False
    DEBUG_SHOP = False
    DEBUG_SPECIAL = False
    DEBUG_TRACE = False
    DEBUG_TREE = False
    DEBUG_UPDATE = False
    DEBUG_USR = False
    DEBUG_UTILS = False
    DEBUG_VARS = False
    DEBUG_WOO = False
    master_name = None
    slave_name = None
    strict = False

    @classmethod
    def conflict_resolver(cls, *_):
        pass

    def resolve_conflict(self, new, _, index, register_name=''):
        if new:
            pass
        self.register_error(
            "Object [index: %s] already exists in register %s" % (index, register_name))

    @classmethod
    def get_object_rowcount(cls, object_data):
        if hasattr(object_data, 'rowcount'):
            return object_data.rowcount
        else:
            raise UserWarning('object does not have rowcount')

    @classmethod
    def get_object_index(cls, object_data):
        if hasattr(object_data, 'index'):
            return object_data.index
        else:
            raise UserWarning('object is not indexable')

    @classmethod
    def passive_resolver(cls, *args):
        pass

    @classmethod
    def exception_resolver(cls, new, _, index, register_name=''):
        raise Exception("could not register %s in %s. \nDuplicate index: %s" % (
            str(new), register_name, index))

    @classmethod
    def duplicate_obj_exc_resolver(cls, new, old, index, register_name=''):
        assert hasattr(
            new, 'rowcount'), 'new object type: %s should have a .rowcount attr' % type(new)
        assert hasattr(
            old, 'rowcount'), 'old object type: %s should have a .rowcount attr' % type(old)
        raise Exception(
            ("could not register %s in %s. \n"
             "Duplicate index: %s appears in rowcounts %s and %s"
             ) % (
                str(new), register_name, index, new.rowcount, old.rowcount
            )
        )

    def warning_resolver(self, new, old, index, register_name=''):
        try:
            self.exception_resolver(new, old, index, register_name)
        except Exception as exc:
            self.register_error(exc, new)

    @classmethod
    def string_anything(cls, index, thing, delimeter='|'):
        return SanitationUtils.coerce_bytes(
            u"%50s %s %s" % (index, delimeter, thing))

    @classmethod
    def print_anything(cls, index, thing, delimeter):
        print Registrar.string_anything(index, thing, delimeter)

    @classmethod
    def register_anything(cls, thing, register, indexer=None, resolver=None,
                          singular=True, unique=True, register_name='', container=None):
        if resolver is None:
            resolver = cls.conflict_resolver
        if indexer is None:
            indexer = cls.object_indexer
        if container is None:
            container = list
        index = None
        try:
            if callable(indexer):
                if cls.DEBUG_UTILS:
                    print "INDEXER IS CALLABLE"
                index = indexer(thing)
            else:
                if cls.DEBUG_UTILS:
                    print "INDEXER IS NOT CALLABLE"
                index = indexer
            assert hasattr(index, '__hash__'), "Index must be hashable"
            assert index == index, "index must support eq"
        except AssertionError as exc:
            name = thing.__name__ if hasattr(
                thing, '__name__') else repr(indexer)
            raise Exception("Indexer [%s] produced invalid index: %s | %s" % (
                name, repr(index), str(exc)))
        else:
            # if not register:
            #     register = OrderedDict()
            if singular:
                if index not in register:
                    register[index] = thing
                else:
                    resolver(thing, register[index], index, register_name)
            else:
                if index not in register:
                    register[index] = container()
                if not unique or thing not in register[index]:
                    register[index].append(thing)
        # print "registered", thing

    @classmethod
    def register_error(cls, error, source=None):
        if source:
            try:
                index = source.index
                assert not callable(index)
            except BaseException:
                index = source
        else:
            index = DebugUtils.get_caller_procedures()
        error_string = SanitationUtils.coerce_unicode(error)
        if cls.DEBUG_ERROR:
            Registrar.print_anything(index, error_string, '!')
        cls.register_anything(
            error_string,
            Registrar.errors,
            index,
            singular=False,
            register_name='errors'
        )

    @classmethod
    def register_warning(cls, message, source=None):
        if source:
            try:
                index = source.index
                assert not callable(index)
            except BaseException:
                index = source
        else:
            index = DebugUtils.get_caller_procedures()
        error_string = SanitationUtils.coerce_unicode(message)
        if cls.DEBUG_WARN:
            Registrar.print_anything(index, error_string, '|')
        cls.register_anything(
            error_string,
            Registrar.warnings,
            index,
            singular=False,
            register_name='warnings'
        )

    @classmethod
    def register_message(cls, message, source=None):
        if source is None:
            source = DebugUtils.get_caller_procedures()
        if cls.DEBUG_MESSAGE:
            Registrar.print_anything(source, message, '~')
        cls.register_anything(
            message,
            Registrar.messages,
            source,
            singular=False,
            register_name='messages'
        )

    @classmethod
    def register_progress(cls, message):
        if cls.DEBUG_PROGRESS:
            print DebugUtils.hashify(message)

    @classmethod
    def get_message_items(cls, verbosity=0):
        items = cls.errors
        if verbosity > 0:
            items = SeqUtils.combine_ordered_dicts(items, cls.warnings)
        if verbosity > 1:
            items = SeqUtils.combine_ordered_dicts(items, cls.messages)
        return items

    @classmethod
    def print_message_dict(cls, verbosity):
        items = cls.get_message_items(verbosity)
        for key, messages in items.items():
            for message in messages:
                cls.print_anything(key, message, '|')

    @classmethod
    def raise_exception(cls, exc):
        if cls.DEBUG_TRACE:
            _, _, traceback_ = sys.exc_info()
            import pdb; pdb.post_mortem(traceback_)
        raise exc

    @classmethod
    def increment_stack_count(cls, name=''):
        if not name in cls.stack_counts:
            cls.stack_counts[name] = Counter()
        stack = ' -> '.join([
            line.strip().split('\n')[0] for line in list(reversed(traceback.format_stack()))[3:7]
        ])
        cls.stack_counts[name].update({stack:1})

    @classmethod
    def display_stack_counts(cls):
        response = ''
        for stack_name, stack_counts in cls.stack_counts.items():
            response += (" -> %s\n" % stack_name)
            for caller, count in sorted(
                stack_counts.items(),
                cmp=(lambda x, y: int(y[1]).__cmp__(int(x[1])))
            ):
                response += ("  -> (%3d) %s\n" % (count, caller))
        return response

class ValidationUtils(object):

    @staticmethod
    def is_not_none(arg):
        return arg is not None

    @staticmethod
    def is_contained_in(a_list):
        return lambda v: v in a_list


def uniqid(prefix='', more_entropy=False):
    """uniqid([prefix=''[, more_entropy=False]]) -> str
    Gets a prefixed unique identifier based on the current
    time in microseconds.
    prefix
        Can be useful, for instance, if you generate identifiers
        simultaneously on several hosts that might happen to generate
        the identifier at the same microsecond.
        With an empty prefix, the returned string will be 13 characters
        long. If more_entropy is True, it will be 23 characters.
    more_entropy
        If set to True, uniqid() will add additional entropy (using
        the combined linear congruential generator) at the end of
        the return value, which increases the likelihood that
        the result will be unique.
    Returns the unique identifier, as a string."""
    seed = time.time()
    sec = math.floor(seed)
    usec = math.floor(1000000 * (seed - sec))
    if more_entropy:
        lcg = random.random()
        the_uniqid = "%08x%05x%.8F" % (sec, usec, lcg * 10)
    else:
        the_uniqid = '%8x%05x' % (sec, usec)

    the_uniqid = prefix + the_uniqid
    return the_uniqid


class PHPUtils(object):

    @staticmethod
    def uniqid(prefix="", more_entropy=False):
        # raise DeprecationWarning('uniqid deprecated')
        return uniqid(prefix, more_entropy)

    @staticmethod
    def ruleset_uniqid():
        return PHPUtils.uniqid("set_")

    @staticmethod
    def serialize(thing):
        if thing:
            return phpserialize.dumps(thing)

    @staticmethod
    def unserialize(string):
        if string:
            return phpserialize.loads(string)

    @staticmethod
    def serialize_list(list_):
        if list_:
            return phpserialize.dumps(list_)

    @staticmethod
    def unserialize_list(string):
        if string:
            response = phpserialize.loads(string)
            if response:
                return response.values()
            return []

    @staticmethod
    def serialize_mapping(list_):
        if list_:
            return phpserialize.dumps(list_)

    @staticmethod
    def unserialize_mapping(string):
        if string:
            response = phpserialize.loads(string)
            if response:
                return response
            return {}

class MimeUtils(object):
    mime_data = {

        # Image formats
        'image/jpeg': {
            'extensions': ['.jpg', '.jpeg', '.jfif', '.jpe']
        },
        'image/gif': {
            'extensions': ['gif']
        },
        'image/png': {
            'extensions': ['.png', '.x-png']
        },
        'image/bmp': {
            'extensions': ['bmp']
        },
        'image/tiff': {
            'extensions': ['tif', 'tiff']
        },
        'image/ico': {
            'extensions': ['ico']
        },
        'image/jp2': {
            'extensions': ['.jp2', '.jpg2']
        },

        # Video formats
        'video/x-ms-asf': {
            'extensions': ['asf', 'asx']
        },
        'video/x-ms-wmv': {
            'extensions': ['wmv']
        },
        'video/x-ms-wmx': {
            'extensions': ['wmx']
        },
        'video/x-ms-wm': {
            'extensions': ['wm']
        },
        'video/avi': {
            'extensions': ['avi']
        },
        'video/divx': {
            'extensions': ['divx']
        },
        'video/x-flv': {
            'extensions': ['flv']
        },
        'video/quicktime': {
            'extensions': ['mov', 'qt']
        },
        'video/mpeg': {
            'extensions': ['mpeg', 'mpg', 'mpe']
        },
        'video/mp4': {
            'extensions': ['mp4', 'm4v']
        },
        'video/ogg': {
            'extensions': ['ogv']
        },
        'video/webm': {
            'extensions': ['webm']
        },
        'video/x-matroska': {
            'extensions': ['mkv']
        },

        # Text formats
        'text/plain': {
            'extensions': ['txt', 'asc', 'c', 'cc', 'h']
        },
        'text/csv': {
            'extensions': ['csv']
        },
        'text/tab-separated-values': {
            'extensions': ['tsv']
        },
        'text/calendar': {
            'extensions': ['ics']
        },
        'text/richtext': {
            'extensions': ['rtx']
        },
        'text/css': {
            'extensions': ['css']
        },
        'text/html': {
            'extensions': ['htm', 'html']
        },

        # Audio formats
        'audio/mpeg': {
            'extensions': ['mp3', 'm4a', 'm4b']
        },
        'audio/x-realaudio': {
            'extensions': ['ra', 'ram']
        },
        'audio/wav': {
            'extensions': ['wav']
        },
        'audio/ogg': {
            'extensions': ['ogg', 'oga']
        },
        'audio/midi': {
            'extensions': ['mid', 'midi']
        },
        'audio/x-ms-wma': {
            'extensions': ['wma']
        },
        'audio/x-ms-wax': {
            'extensions': ['wax']
        },
        'audio/x-matroska': {
            'extensions': ['mka']
        },

        # Misc application formats
        'application/rtf': {
            'extensions': ['rtf']
        },
        'application/javascript': {
            'extensions': ['js']
        },
        'application/pdf': {
            'extensions': ['pdf']
        },
        'application/x-shockwave-flash': {
            'extensions': ['swf']
        },
        'application/java': {
            'extensions': ['class']
        },
        'application/x-tar': {
            'extensions': ['tar']
        },
        'application/zip': {
            'extensions': ['zip']
        },
        'application/x-gzip': {
            'extensions': ['gz', 'gzip']
        },
        'application/rar': {
            'extensions': ['rar']
        },
        'application/x-7z-compressed': {
            'extensions': ['7z']
        },
        'application/x-msdownload': {
            'extensions': ['exe']
        },

        # MS Office formats
        'application/msword': {
            'extensions': ['doc']
        },
        'application/vnd.ms-powerpoint': {
            'extensions': ['pot', 'pps', 'ppt']
        },
        'application/vnd.ms-write': {
            'extensions': ['wri']
        },
        'application/vnd.ms-excel': {
            'extensions': ['xla', 'xls', 'xlt', 'xlw']
        },
        'application/vnd.ms-access': {
            'extensions': ['mdb']
        },
        'application/vnd.ms-project': {
            'extensions': ['mpp']
        },
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': {
            'extensions': ['docx']
        },
        'application/vnd.ms-word.document.macroEnabled.12': {
            'extensions': ['docm']
        },
        'application/vnd.openxmlformats-officedocument.wordprocessingml.template': {
            'extensions': ['dotx']
        },
        'application/vnd.ms-word.template.macroEnabled.12': {
            'extensions': ['dotm']
        },
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': {
            'extensions': ['xlsx']
        },
        'application/vnd.ms-excel.sheet.macroEnabled.12': {
            'extensions': ['xlsm']
        },
        'application/vnd.ms-excel.sheet.binary.macroEnabled.12': {
            'extensions': ['xlsb']
        },
        'application/vnd.openxmlformats-officedocument.spreadsheetml.template': {
            'extensions': ['xltx']
        },
        'application/vnd.ms-excel.template.macroEnabled.12': {
            'extensions': ['xltm']
        },
        'application/vnd.ms-excel.addin.macroEnabled.12': {
            'extensions': ['xlam']
        },
        'application/vnd.openxmlformats-officedocument.presentationml.presentation': {
            'extensions': ['pptx']
        },
        'application/vnd.ms-powerpoint.presentation.macroEnabled.12': {
            'extensions': ['pptm']
        },
        'application/vnd.openxmlformats-officedocument.presentationml.slideshow': {
            'extensions': ['ppsx']
        },
        'application/vnd.ms-powerpoint.slideshow.macroEnabled.12': {
            'extensions': ['ppsm']
        },
        'application/vnd.openxmlformats-officedocument.presentationml.template': {
            'extensions': ['potx']
        },
        'application/vnd.ms-powerpoint.template.macroEnabled.12': {
            'extensions': ['potm']
        },
        'application/vnd.ms-powerpoint.addin.macroEnabled.12': {
            'extensions': ['ppam']
        },
        'application/vnd.openxmlformats-officedocument.presentationml.slide': {
            'extensions': ['sldx']
        },
        'application/vnd.ms-powerpoint.slide.macroEnabled.12': {
            'extensions': ['sldm']
        },
        'application/onenote': {
            'extensions': ['onetoc', 'onetoc2', 'onetmp', 'onepkg']
        },

        # OpenOffice formats
        'application/vnd.oasis.opendocument.text': {
            'extensions': ['odt']
        },
        'application/vnd.oasis.opendocument.presentation': {
            'extensions': ['odp']
        },
        'application/vnd.oasis.opendocument.spreadsheet': {
            'extensions': ['ods']
        },
        'application/vnd.oasis.opendocument.graphics': {
            'extensions': ['odg']
        },
        'application/vnd.oasis.opendocument.chart': {
            'extensions': ['odc']
        },
        'application/vnd.oasis.opendocument.database': {
            'extensions': ['odb']
        },
        'application/vnd.oasis.opendocument.formula': {
            'extensions': ['odf']
        },

        # WordPerfect formats
        'application/wordperfect': {
            'extensions': ['wp', 'wpd']
        },

        # iWork formats
        'application/vnd.apple.keynote': {
            'extensions': ['key']
        },
        'application/vnd.apple.numbers': {
            'extensions': ['numbers']
        },
        'application/vnd.apple.pages': {
            'extensions': ['pages']
        },
    }

    @classmethod
    def validate_mime_type(cls, string):
        if not string:
            return
        if string.lower() in cls.mime_data:
            return string.lower()

    @classmethod
    def get_ext_mime_type(cls, extension):
        for mime_type, data in cls.mime_data.items():
            extensions = data.get('extensions', [])
            if extension.lower() in extensions:
                return mime_type


class ProgressCounter(object):

    def __init__(self, total, print_threshold=1):
        self.total = total
        self.print_threshold = print_threshold
        self.last_print = time.time()
        self.first_print = self.last_print
        self.print_count = 0
        # self.memory_tracker = tracker.SummaryTracker()

    def maybe_print_update(self, count):
        now = time.time()
        if now - self.last_print > self.print_threshold:
            # self.memory_tracker.print_diff()
            self.last_print = now
            percentage = 0
            if self.total > 0:
                percentage = 100 * count / self.total
            line = "(%3d%%) %10d of %10d items processed, elapsed" % (
                percentage, count, self.total)
            if percentage > 1 and percentage < 100:
                time_elapsed = self.last_print - self.first_print
                ratio = (float(self.total) / (count) - 1.0)
                time_remaining = float(time_elapsed) * ratio
                # line += " | elapsesd: %3f | ratio: %3f" % (time_elapsed, ratio )
                line += " | remaining: %3d seconds, %3d elapsed" % (
                    int(time_remaining),
                    int(time_elapsed)
                )
            if self.print_count > 0:
                line = "\r%s\r" % line
            sys.stdout.write(line)
            sys.stdout.flush()
            self.print_count += 1
        if count == self.total - 1:
            print "\n"


class UnicodeCsvDialectUtils(object):
    default_dialect = unicodecsv.excel

    class ActOut(unicodecsv.Dialect):
        delimiter = ','
        quoting = unicodecsv.QUOTE_ALL
        doublequote = True
        strict = False
        quotechar = "\""
        escapechar = None
        skipinitialspace = False
        lineterminator = '\r\n'

    class SublimeCsvTable(unicodecsv.Dialect):
        delimiter = ','
        quoting = unicodecsv.QUOTE_MINIMAL
        doublequote = True
        strict = False
        quotechar = "\""
        escapechar = None
        skipinitialspace = True
        lineterminator = '\n'

    @classmethod
    def get_dialect_from_suggestion(cls, suggestion):
        dialect = cls.default_dialect
        if hasattr(cls, suggestion):
            possible_dialect = getattr(cls, suggestion)
            if isinstance(possible_dialect, unicodecsv.Dialect):
                dialect = possible_dialect
        return dialect

    @classmethod
    def dialect_to_str(cls, dialect):
        out = "Dialect: %s" % dialect.__name__
        out += " | DEL: %s" % repr(dialect.delimiter)
        out += " | DBL: %s" % repr(dialect.doublequote)
        out += " | ESC: %s" % repr(dialect.escapechar)
        out += " | QUC: %s" % repr(dialect.quotechar)
        out += " | QUT: %s" % repr(dialect.quoting)
        out += " | SWS: %s" % repr(dialect.skipinitialspace)
        return out

    @classmethod
    def dialect_unicode_to_bytestr(cls, dialect):
        for attr in [
                'delimeter', 'quotechar', 'doublequote', 'escapechar', 'quotechar',
                'quoting',
        ]:
            if isinstance(getattr(dialect, attr), unicode):
                setattr(
                    dialect,
                    attr,
                    SanitationUtils.coerce_bytes(getattr(dialect, attr))
                )
        return dialect

    @classmethod
    def get_dialect_from_sample(cls, sample, suggestion):
        byte_sample = SanitationUtils.coerce_bytes(sample)
        csvdialect = unicodecsv.Sniffer().sniff(byte_sample)
        if not csvdialect:
            return cls.get_dialect_from_suggestion(suggestion)
        return csvdialect


class FileUtils(object):

    @classmethod
    def get_file_name(cls, path):
        file_name, _ = os.path.splitext(os.path.basename(path))
        return file_name
