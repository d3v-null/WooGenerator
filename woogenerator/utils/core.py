# -*- coding: utf-8 -*-
import functools
import itertools
# from itertools import chain
import re
import time
import sys
# import datetime
import inspect
import json
from collections import OrderedDict
import codecs
import unicodecsv
import cStringIO
# from uniqid import uniqid
from phpserialize import dumps, loads
from kitchen.text import converters
import time
import math
import random
import io
import base64
from pympler import tracker
import cgi
import os
from urlparse import urlparse, parse_qs

try:
    # Python 2.6-2.7
    from HTMLParser import HTMLParser
except ImportError:
    # Python 3
    from html.parser import HTMLParser

#

DEFAULT_ENCODING = 'utf8'


class SanitationUtils:
    email_regex = r"[\w.+-]+@[\w-]+\.[\w.-]+"
    regex_url_simple = r"https?:\/\/(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{2,256}\.[a-z]{2,6}\b(?:[-a-zA-Z0-9@:%_\+.~#?&//=]*)"
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
    disallowedPunctuationOrSpaceRegex = r"[%s]" % "".join(
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

    @classmethod
    def wrapClearRegex(cls, regex):
        return cls.clearStartRegex + regex + cls.clearFinishRegex

    @classmethod
    def identifyAbbreviation(cls, abbrvDict, string):
        for abbrv_key, abbrvs in abbrvDict.items():
            if(string in [abbrv_key] + abbrvs):
                return abbrv_key
        return string

    @classmethod
    def identifyAbbreviations(cls, abbrvDict, string):
        matches = re.findall(
            '(' + cls.compile_abbrv_regex(abbrvDict) + ')',
            string
        )

        for candidate in [match for match in filter(None, matches)]:
            identified = cls.identifyAbbreviation(abbrvDict, candidate)
            if identified:
                yield identified

    @classmethod
    def compile_partial_abbrv_regex(cls, abbrv_key, abbrvs):
        return "|".join(filter(None, [
            "|".join(filter(None, abbrvs)),
            abbrv_key
        ]))

    @classmethod
    def compile_abbrv_regex(cls, abbrv):
        return "|".join(filter(None,
                               [cls.compile_partial_abbrv_regex(
                                   abbrv_key, abbrvValue) for abbrv_key, abbrvValue in abbrv.items()]
                               ))

    @classmethod
    def compose(cls, *functions):
        return functools.reduce(lambda f, g: lambda x: f(g(x)), functions)

    # Functions for dealing with string encodings

    @classmethod
    def assert_ascii(cls, string):
        for index, char in enumerate(string):
            assert ord(char) < 128, "char %s of string %s ... is not ascii" % (
                index, (string[:index - 1]))

    @classmethod
    def unicodeToUTF8(cls, u_str):
        assert isinstance(
            u_str, unicode), "parameter should be unicode not %s" % type(u_str)
        byte_return = converters.to_bytes(u_str, "utf8")
        assert isinstance(
            byte_return, str), "something went wrong, should return str not %s" % type(byte_return)
        return byte_return

    @classmethod
    def unicodeToAscii(cls, u_str):
        assert isinstance(
            u_str, unicode), "parameter should be unicode not %s" % type(u_str)
        byte_return = converters.to_bytes(u_str, "ascii", "backslashreplace")
        assert isinstance(
            byte_return, str), "something went wrong, should return str not %s" % type(byte_return)
        return byte_return

    @classmethod
    def unicodeToXml(cls, u_str, ascii_only=False):
        assert isinstance(
            u_str, unicode), "parameter should be unicode not %s" % type(u_str)
        if ascii_only:
            byte_return = converters.unicode_to_xml(u_str, encoding="ascii")
        else:
            byte_return = converters.unicode_to_xml(u_str)
        assert isinstance(
            byte_return, str), "something went wrong, should return str not %s" % type(byte_return)
        return byte_return

    @classmethod
    def utf8ToUnicode(cls, utf8_str):
        assert isinstance(
            utf8_str, str), "parameter should be str not %s" % type(utf8_str)
        byte_return = converters.to_unicode(utf8_str, "utf8")
        assert isinstance(
            byte_return, unicode), "something went wrong, should return unicode not %s" % type(byte_return)
        return byte_return

    @classmethod
    def xmlToUnicode(cls, utf8_str):
        assert isinstance(
            utf8_str, str), "parameter should be str not %s" % type(utf8_str)
        byte_return = converters.xml_to_unicode(utf8_str)
        assert isinstance(
            byte_return, str), "something went wrong, should return str not %s" % type(byte_return)
        return byte_return

    @classmethod
    def ascii_to_unicode(cls, ascii_str):
        assert isinstance(
            ascii_str, str), "parameter should be str not %s" % type(ascii_str)
        unicode_return = converters.to_unicode(ascii_str, "ascii")
        assert isinstance(
            unicode_return, unicode), "something went wrong, should return unicode not %s" % type(unicode_return)
        return unicode_return

    @classmethod
    def coerce_unicode(cls, thing):
        if thing is None:
            unicode_return = u""
        else:
            unicode_return = converters.to_unicode(thing, encoding="utf8")
        assert isinstance(
            unicode_return, unicode), "something went wrong, should return unicode not %s" % type(unicode_return)
        return unicode_return

    @classmethod
    def coerce_bytes(cls, thing):
        byte_return = cls.compose(
            cls.unicodeToUTF8,
            cls.coerce_unicode
        )(thing)
        assert isinstance(
            byte_return, str), "something went wrong, should return str not %s" % type(byte_return)
        return byte_return

    @classmethod
    def coerce_ascii(cls, thing):
        byte_return = cls.compose(
            cls.unicodeToAscii,
            cls.coerce_unicode
        )(thing)
        assert isinstance(
            byte_return, str), "something went wrong, should return str not %s" % type(byte_return)
        return byte_return

    @classmethod
    def coerce_xml(cls, thing):
        byte_return = cls.compose(
            cls.unicodeToXml,
            cls.coerce_unicode
        )(thing)
        assert isinstance(
            byte_return, str), "something went wrong, should return str not %s" % type(byte_return)
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
        assert isinstance(
            float_return, float), "something went wrong, should return str not %s" % type(float_return)
        return float_return

    @classmethod
    def limitString(cls, length):
        return (lambda x: x[:length])

    @classmethod
    def sanitizeForTable(cls, thing, tablefmt=None):
        if hasattr(thing, '_supports_tablefmt'):
            thing = thing.__unicode__(tablefmt)
        if isinstance(thing, (str, unicode)) and tablefmt == 'simple':
            thing = thing[:64] + '...'
        unicode_return = cls.compose(
            cls.coerce_unicode,
            cls.limitString(50),
            cls.escape_newlines,
            cls.coerce_unicode
        )(thing)
        assert isinstance(
            unicode_return, unicode), "something went wrong, should return unicode not %s" % type(unicode_return)
        return unicode_return

    @classmethod
    def sanitizeForXml(cls, thing):
        unicode_return = cls.compose(
            cls.coerce_unicode,
            cls.sanitizeNewlines,
            cls.unicodeToXml,
            cls.coerce_unicode
        )(thing)
        assert isinstance(
            unicode_return, unicode), "something went wrong, should return unicode not %s" % type(unicode_return)
        return unicode_return

    @classmethod
    def safePrint(cls, *args):
        print " ".join([cls.coerce_bytes(arg) for arg in args])

    @classmethod
    def normalize_val(cls, thing):
        unicode_return = cls.compose(
            cls.coerce_unicode,
            cls.toUpper,
            cls.stripLeadingWhitespace,
            cls.stripTailingWhitespace,
            cls.stripExtraWhitespace,
            cls.coerce_unicode
        )(thing)
        assert isinstance(
            unicode_return, unicode), "something went wrong, should return unicode not %s" % type(unicode_return)
        return unicode_return

    @classmethod
    def removeLeadingDollarWhiteSpace(cls, string):
        str_out = re.sub('^\W*\$', '', string)
        if Registrar.DEBUG_UTILS:
            print "removeLeadingDollarWhiteSpace", repr(string), repr(str_out)
        return str_out

    @classmethod
    def removeLeadingPercentWhiteSpace(cls, string):
        str_out = re.sub('%\W*$', '', string)
        if Registrar.DEBUG_UTILS:
            print "removeLeadingPercentWhiteSpace", repr(string), repr(str_out)
        return str_out

    @classmethod
    def removeLoneDashes(cls, string):
        str_out = re.sub('^-$', '', string)
        if Registrar.DEBUG_UTILS:
            print "removeLoneDashes", repr(string), repr(str_out)
        return str_out

    @classmethod
    def removeThousandsSeparator(cls, string):
        str_out = re.sub(r'(\d+),(\d{3})', '\g<1>\g<2>', string)
        if Registrar.DEBUG_UTILS:
            print "removeThousandsSeparator", repr(string), repr(str_out)
        return str_out

    @classmethod
    def removeLoneWhiteSpace(cls, string):
        str_out = re.sub(r'^\s*$', '', string)
        if Registrar.DEBUG_UTILS:
            print "removeLoneWhiteSpace", repr(string), repr(str_out)
        return str_out

    @classmethod
    def removeNULL(cls, string):
        str_out = re.sub(r'^NULL$', '', string)
        if Registrar.DEBUG_UTILS:
            print "removeNULL", repr(string), repr(str_out)
        return str_out

    @classmethod
    def stripLeadingWhitespace(cls, string):
        str_out = re.sub(r'^\s*', '', string)
        if Registrar.DEBUG_UTILS:
            print "stripLeadingWhitespace", repr(string), repr(str_out)
        return str_out

    @classmethod
    def stripLeadingNewline(cls, string):
        str_out = re.sub(r'^(\\n|\n)*', '', string)
        if Registrar.DEBUG_UTILS:
            print "stripLeadingNewline", repr(string), repr(str_out)
        return str_out

    @classmethod
    def stripTailingWhitespace(cls, string):
        str_out = re.sub(r'\s*$', '', string)
        if Registrar.DEBUG_UTILS:
            print "stripTailingWhitespace", repr(string), repr(str_out)
        return str_out

    @classmethod
    def stripTailingNewline(cls, string):
        str_out = re.sub(r'(\\n|\n)*$', '', string)
        if Registrar.DEBUG_UTILS:
            print "stripTailingNewline", repr(string), repr(str_out)
        return str_out

    @classmethod
    def stripAllWhitespace(cls, string):
        str_out = re.sub(r'\s', '', string)
        if Registrar.DEBUG_UTILS:
            print "stripAllWhitespace", repr(string), repr(str_out)
        return str_out

    @classmethod
    def stripExtraWhitespace(cls, string):
        str_out = re.sub(r'\s{2,}', ' ', string)
        if Registrar.DEBUG_UTILS:
            print "stripExtraWhitespace", repr(string), repr(str_out)
        return str_out

    @classmethod
    def stripNonNumbers(cls, string):
        str_out = re.sub(r'[^\d]', '', string)
        if Registrar.DEBUG_UTILS:
            print "stripNonNumbers", repr(string), repr(str_out)
        return str_out

    @classmethod
    def stripNonPhoneCharacters(cls, string):
        str_out = re.sub(cls.disallowedPhoneCharRegex, '', string)
        return str_out

    @classmethod
    def stripPunctuation(cls, string):
        str_out = re.sub(r'[%s]' % ''.join(cls.punctuationChars), '', string)
        if Registrar.DEBUG_UTILS:
            print "stripPunctuation", repr(string), repr(str_out)
        return str_out

    @classmethod
    def stripAreaCode(cls, string):
        str_out = re.sub(r'\s*\+\d{2,3}\s*', '', string)
        if Registrar.DEBUG_UTILS:
            print "stripAreaCode", repr(string), repr(str_out)
        return str_out

    @classmethod
    def stripURLProtocol(cls, string):
        str_out = re.sub(r"^\w+://", "", string)
        if Registrar.DEBUG_UTILS:
            print "stripURLProtocol", repr(string), repr(str_out)
        return str_out

    @classmethod
    def stripPTags(cls, string):
        str_out = re.sub(r"</?p[^>]*>", "", string)
        if Registrar.DEBUG_UTILS:
            print "stripURLProtocol", repr(string), repr(str_out)
        return str_out

    @classmethod
    def stripBrTags(cls, string):
        str_out = re.sub(r"</?\s*br\s*/?>", "", string)
        if Registrar.DEBUG_UTILS:
            print "stripURLProtocol", repr(string), repr(str_out)
        return str_out

    @classmethod
    def stripURLHost(cls, url):
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
            print "stripURLHost", repr(url), repr(str_out)
        return str_out

    @classmethod
    def toLower(cls, string):
        str_out = string.lower()
        if Registrar.DEBUG_UTILS:
            print "toLower", repr(string), repr(str_out)
        return str_out

    @classmethod
    def toUpper(cls, string):
        str_out = string.upper()
        if Registrar.DEBUG_UTILS:
            print "toUpper", repr(string), repr(str_out)
        return str_out

    @classmethod
    def sanitizeNewlines(cls, string):
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
    def sanitizeCell(cls, cell):
        return cls.compose(
            cls.removeLeadingDollarWhiteSpace,
            cls.removeLeadingPercentWhiteSpace,
            cls.removeLoneDashes,
            # cls.stripExtraWhitespace,
            cls.removeThousandsSeparator,
            cls.removeLoneWhiteSpace,
            cls.stripLeadingWhitespace,
            cls.stripTailingWhitespace,
            cls.sanitizeNewlines,
            cls.stripTailingNewline,
            cls.stripLeadingNewline,
            cls.removeNULL,
            cls.coerce_unicode
        )(cell)

    @classmethod
    def sanitizeSpecialCell(cls, cell):
        return cls.compose(
            cls.removeLeadingDollarWhiteSpace,
            cls.removeLeadingPercentWhiteSpace,
            # cls.removeLoneDashes,
            # cls.stripExtraWhitespace,
            cls.removeThousandsSeparator,
            cls.removeLoneWhiteSpace,
            cls.stripLeadingWhitespace,
            cls.stripTailingWhitespace,
            cls.sanitizeNewlines,
            cls.stripTailingNewline,
            cls.stripLeadingNewline,
            cls.removeNULL,
            cls.coerce_unicode
        )(cell)

    @classmethod
    def sanitizeClass(cls, string):
        return re.sub('[^a-z]', '', string.lower())

    @classmethod
    def slugify(cls, string):
        string = re.sub('[^a-z0-9 _]', '', string.lower())
        return re.sub(' ', '_', string)

    @classmethod
    def similarComparison(cls, string):
        return cls.compose(
            cls.toLower,
            cls.stripLeadingWhitespace,
            cls.stripTailingWhitespace,
            cls.coerce_unicode
        )(string)

    @classmethod
    def similarNoPunctuationComparison(cls, string):
        return cls.compose(
            cls.normalize_val,
            cls.stripPunctuation,
        )(string)

    @classmethod
    def similarPhoneComparison(cls, string):
        return cls.compose(
            cls.stripLeadingWhitespace,
            cls.stripNonNumbers,
            cls.stripAreaCode,
            cls.stripExtraWhitespace,
            cls.stripNonPhoneCharacters,
            cls.coerce_unicode
        )(string)

    @classmethod
    def similarTruStrComparison(cls, string):
        return cls.compose(
            cls.truishStringToBool,
            cls.similarComparison
        )(string)

    @classmethod
    def similarURLComparison(cls, string):
        return cls.compose(
            cls.stripURLProtocol,
            cls.coerce_unicode
        )(string)

    @classmethod
    def similarMarkupComparison(cls, string):
        return cls.compose(
            cls.toLower,
            cls.stripLeadingWhitespace,
            cls.stripTailingWhitespace,
            cls.stripExtraWhitespace,
            cls.stripPTags,
            cls.stripBrTags,
            cls.coerce_unicode
        )(string)

    @classmethod
    def similarCurrencyComparison(cls, string):
        return cls.compose(
            cls.coerce_float,
            cls.removeLeadingDollarWhiteSpace,
            cls.coerce_unicode,
        )(string)

    @classmethod
    def makeSafeClass(cls, string):
        return cls.compose(
            cls.stripAllWhitespace,
            cls.stripPunctuation
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
        # assert isinstance(instring, (str, unicode)), "param must be a string not %s"% type(instring)
        # if not isinstance(instring, unicode):
            # instring = instring.decode('utf-8')
        instring = cls.coerce_unicode(instring)
        return re.findall(r'\s*([^.|]*\.[^.|\s]*)(?:\s*|\s*)', instring)

    @classmethod
    def find_all_tokens(cls, instring, delim="|"):
        # assert isinstance(instring, (str, unicode)), "param must be a string not %s"% type(instring)
        # if not isinstance(instring, unicode):
            # instring = instring.decode('utf-8')
        instring = cls.coerce_unicode(instring)
        return re.findall(r'\s*(\b[^\s.|]+\b)\s*', instring)

    @classmethod
    def find_all_dollars(cls, instring):
        # assert isinstance(instring, (str, unicode)), "param must be a string not %s"% type(instring)
        # if not isinstance(instring, unicode):
            # instring = instring.decode('utf-8')
        instring = cls.coerce_unicode(instring)
        return re.findall(r"\s*\$([\d,]+\.?\d*)", instring)

    @classmethod
    def find_all_percent(cls, instring):
        # assert isinstance(instring, (str, unicode)), "param must be a string not %s"% type(instring)
        # if not isinstance(instring, unicode):
            # instring = instring.decode('utf-8')
        instring = cls.coerce_unicode(instring)
        return re.findall(r"\s*(\d+\.?\d*)%", instring)

    @classmethod
    def find_all_emails(cls, instring):
        instring = cls.coerce_unicode(instring)
        return re.findall(
            cls.wrapClearRegex(cls.email_regex),
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
    def findall_wp_links(cls, string):
        # todo implement
        return []

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
    def titleSplitter(cls, instring):
        assert isinstance(instring, (str, unicode)
                          ), "param must be a string not %s" % type(instring)
        if not isinstance(instring, unicode):
            instring = instring.decode('utf-8')
        found = re.findall(r"^\s*(.*?)\s+[^\s\w&\(\)]\s+(.*?)\s*$", instring)
        if found:
            return found[0]
        else:
            return instring, ""

    @classmethod
    def stringIsEmail(cls, email):
        return re.match(cls.email_regex, email)

    @classmethod
    def stringIsMYOBID(cls, card):
        return re.match(cls.myobid_regex, card)

    @classmethod
    def stringCapitalized(cls, string):
        return unicode(string) == unicode(string).upper()

    @classmethod
    def stringContainsNumbers(cls, string):
        if(re.search('\d', string)):
            return True
        else:
            return False

    @classmethod
    def stringContainsNoNumbers(cls, string):
        return not cls.stringContainsNumbers(string)

    @classmethod
    def stringContainsDelimeters(cls, string):
        return True if(re.search(cls.delimeterRegex, string)) else False

    @classmethod
    def stringContainsDisallowedPunctuation(cls, string):
        return True if(
            re.search(cls.disallowedPunctuationRegex, string)) else False

    @classmethod
    def stringContainsPunctuation(cls, string):
        return True if(re.search(cls.punctuationRegex, string)) else False

    @classmethod
    def truishStringToBool(cls, string):
        if(not string or 'n' in string or 'false' in string or string == '0' or string == 0):
            if Registrar.DEBUG_UTILS:
                print "truishStringToBool", repr(string), 'FALSE'
            return "FALSE"
        else:
            if Registrar.DEBUG_UTILS:
                print "truishStringToBool", repr(string), 'TRUE'
            return "TRUE"

    @classmethod
    def bool_to_truish_string(cls, boolVal):
        if boolVal:
            return "TRUE"
        else:
            return "FALSE"

    @classmethod
    def datetotimestamp(cls, datestring):
        raise DeprecationWarning()
        # assert isinstance(datestring, (str,unicode)), "param must be a string not %s"% type(datestring)
        # return int(time.mktime(datetime.datetime.strptime(datestring,
        # "%d/%m/%Y").timetuple()))

    @classmethod
    def decode_json(cls, json_str):
        assert isinstance(json_str, (str, unicode))
        attrs = json.loads(json_str)
        return attrs

    @classmethod
    def encode_json(cls, obj):
        assert isinstance(obj, (dict, list))
        json_str = json.dumps(obj, encoding="utf8", ensure_ascii=False)
        return json_str

    @classmethod
    def encode_base64(cls, str):
        utf8_str = cls.coerce_bytes(str)
        return base64.standard_b64encode(utf8_str)

    @classmethod
    def decode_base64(cls, b64_str):
        return base64.standard_b64decode(b64_str)


def test_sanitation_utils():
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
    # SanitationUtils.safePrint(obj_json, repr(obj_json) )
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
    # SanitationUtils.safePrint( fields, repr(fields) )
    # fields_json = SanitationUtils.encode_json(fields)
    # SanitationUtils.safePrint( fields_json, repr(fields_json) )
    # fields_json_base64 = SanitationUtils.encode_base64( fields_json )
    # SanitationUtils.safePrint( fields_json_base64, repr(fields_json_base64) )

    # should be   eyJ1c2VyX2xvZ2luIjogImFkbWluIiwgImZpcnN0X25hbWUiOiAibm/wn5GMb2Twn5GMbGUiLCAidXNlcl91cmwiOiAiaHR0cDovL3d3dy5sYXNlcnBoaWxlLmNvbS9hc2QifQ==
    # is actually
    # eyJ1c2VyX2xvZ2luIjogImFkbWluIiwgImZpcnN0X25hbWUiOiAibm_wn5GMb2Twn5GMbGUiLCAidXNlcl91cmwiOiAiaHR0cDovL3d3dy5sYXNlcnBoaWxlLmNvbS9hc2QifQ==

    # n1 = u"D\u00C8RWENT"
    # n2 = u"d\u00E8rwent"
    # print SanitationUtils.unicodeToByte(n1) , \
    #     SanitationUtils.unicodeToByte(SanitationUtils.similarComparison(n1)), \
    #     SanitationUtils.unicodeToByte(n2), \
    #     SanitationUtils.unicodeToByte(SanitationUtils.similarComparison(n2))

    # p1 = "+61 04 3190 8778"
    # p2 = "04 3190 8778"
    # p3 = "+61 (08) 93848512"
    # print \
    #     SanitationUtils.similarPhoneComparison(p1), \
    #     SanitationUtils.similarPhoneComparison(p2), \
    #     SanitationUtils.similarPhoneComparison(p3)

    # print SanitationUtils.makeSafeOutput(u"asdad \u00C3 <br> \n \b")

    # tru = SanitationUtils.similarComparison(u"TRUE")

    # print \
    #     SanitationUtils.similarTruStrComparison('yes'), \
    #     SanitationUtils.similarTruStrComparison('no'), \
    #     SanitationUtils.similarTruStrComparison('TRUE'),\
    #     SanitationUtils.similarTruStrComparison('FALSE'),\
    #     SanitationUtils.similarTruStrComparison(0),\
    #     SanitationUtils.similarTruStrComparison('0'),\
    #     SanitationUtils.similarTruStrComparison(u"0")\
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
    # SanitationUtils.safePrint( SanitationUtils.escape_newlines(a))


class descriptorUtils:

    @staticmethod
    def safeKeyProperty(key):
        def getter(self):
            assert key in self.keys(), "{} must be set before get in {}".format(
                key, repr(type(self)))
            return self[key]

        def setter(self, value):
            assert isinstance(value, (str, unicode)), "{} must be set with string not {}".format(
                key, type(value))
            self[key] = value

        return property(getter, setter)

    @staticmethod
    def safeNormalizedKeyProperty(key):
        def getter(self):
            assert key in self.keys(), "{} must be set before get in {}".format(
                key, repr(type(self)))
            return SanitationUtils.normalize_val(self[key])

        def setter(self, value):
            assert isinstance(value, (str, unicode)), "{} must be set with string not {}".format(
                key, type(value))
            self[key] = value

        return property(getter, setter)

    @staticmethod
    def kwargAliasProperty(key, handler):
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
            self.processKwargs()

        return property(getter, setter)


class listUtils:

    @staticmethod
    def combine_lists(a, b):
        """
            Combines lists a and b uniquely, attempting to preserve order
        """
        if not a:
            return b if b else []
        if not b:
            return a
        c = []
        for element in a + b:
            if element not in c:
                c.append(element)
        return c

    @staticmethod
    def combine_ordered_dicts(a, b):
        """
            Combines OrderedDict a with b by starting with A and overwriting with items from b.
            Attempts to preserve order
        """
        if not a:
            return b if b else OrderedDict()
        if not b:
            return a
        c = OrderedDict(a.items())
        for key, value in b.items():
            c[key] = value
        return c

    @staticmethod
    def filter_unique_true(a):
        b = []
        for i in a:
            if i and i not in b:
                b.append(i)
        return b

    @staticmethod
    def get_all_keys(*args):
        return listUtils.filter_unique_true(itertools.chain(*(
            arg.keys() for arg in args if isinstance(arg, dict)
        )))

    @staticmethod
    def keysNotIn(dictionary, keys):
        assert isinstance(dictionary, dict)
        return type(dictionary)([
            (key, value) for key, value in dictionary.items()
            if key not in keys
        ])

    @staticmethod
    def check_equal(iterator):
        """Taken from SO answer http://stackoverflow.com/questions/3844801/check-if-all-elements-in-a-list-are-identical """
        iterator = iter(iterator)
        try:
            first = next(iterator)
        except StopIteration:
            return True
        return all(first == rest for rest in iterator)


class debugUtils:

    @classmethod
    def getProcedure(cls, level=1):
        try:
            procedure = inspect.stack()[level][3]
            # return procedure
            path = inspect.stack()[level][1]
            basename = 'source/' + os.path.basename(path)
            line = inspect.stack()[level][2]
            baseline = "%s:%s" % (basename, line)
            return ".".join([baseline, str(procedure)])
        except:
            return None

    @classmethod
    def get_caller_procedure(cls, level=0):
        return cls.getProcedure(3 + level)

    @classmethod
    def get_caller_procedures(cls, levels=2):
        procedures = map(cls.get_caller_procedure, range(1, levels + 1))
        return ">".join(reversed(filter(None, procedures)))

    @staticmethod
    def hashify(in_str):
        out_str = "#" * (len(in_str) + 4) + "\n"
        out_str += "# " + in_str + " #\n"
        out_str += "#" * (len(in_str) + 4) + "\n"
        return out_str


class Registrar(object):
    messages = OrderedDict()
    errors = OrderedDict()
    warnings = OrderedDict()
    objectIndexer = id
    DEBUG_ERROR = True
    DEBUG_WARN = True
    DEBUG_MESSAGE = False
    DEBUG_PROGRESS = True
    DEBUG_ABSTRACT = False
    DEBUG_PARSER = False
    DEBUG_UPDATE = False
    DEBUG_FLAT = False
    DEBUG_GEN = False
    DEBUG_MYO = False
    DEBUG_TREE = False
    DEBUG_WOO = False
    DEBUG_ADDRESS = False
    DEBUG_NAME = False
    DEBUG_UTILS = False
    DEBUG_CLIENT = False
    DEBUG_CONTACT = False
    DEBUG_IMG = False
    DEBUG_API = False
    DEBUG_SHOP = False
    DEBUG_MRO = False
    DEBUG_GDRIVE = False
    DEBUG_SPECIAL = False
    DEBUG_CATS = False
    DEBUG_VARS = False
    DEBUG_DUPLICATES = False
    DEBUG_USR = False

    # def __init__(self):
    # self.objectIndexer = id
    # self.conflict_resolver = self.passiveResolver
    # self.Registrar.DEBUG_ERROR = True
    # self.Registrar.DEBUG_WARN = False
    # self.Registrar.DEBUG_MESSAGE = False

    @classmethod
    def conflict_resolver(self, *args):
        pass

    def resolveConflict(self, new, old, index, registerName=''):
        self.registerError(
            "Object [index: %s] already exists in register %s" % (index, registerName))

    @classmethod
    def getObjectRowcount(cls, object_data):
        return object_data.rowcount

    @classmethod
    def getObjectIndex(cls, object_data):
        if hasattr(object_data, 'index'):
            return object_data.index
        else:
            raise UserWarning('object is not indexable')

    @classmethod
    def passiveResolver(cls, *args):
        pass

    @classmethod
    def exception_resolver(cls, new, old, index, registerName=''):
        raise Exception("could not register %s in %s. \nDuplicate index: %s" % (
            str(new), registerName, index))

    @classmethod
    def duplicate_object_exception_resolver(
            cls, new, old, index, registerName=''):
        assert hasattr(
            new, 'rowcount'), 'new object type: %s should have a .rowcount attr' % type(new)
        assert hasattr(
            old, 'rowcount'), 'old object type: %s should have a .rowcount attr' % type(old)
        raise Exception("could not register %s in %s. \nDuplicate index: %s appears in rowcounts %s and %s" % (
            str(new), registerName, index, new.rowcount, old.rowcount))

    def warningResolver(self, new, old, index, registerName=''):
        try:
            self.exception_resolver(new, old, index, registerName)
        except Exception as exc:
            self.registerError(exc, new)

    @classmethod
    def stringAnything(self, index, thing, delimeter='|'):
        return SanitationUtils.coerce_bytes(
            u"%50s %s %s" % (index, delimeter, thing))

    @classmethod
    def printAnything(self, index, thing, delimeter):
        print Registrar.stringAnything(index, thing, delimeter)

    @classmethod
    def registerAnything(self, thing, register, indexer=None, resolver=None,
                         singular=True, unique=True, registerName=''):
        if resolver is None:
            resolver = self.conflict_resolver
        if indexer is None:
            indexer = self.objectIndexer
        index = None
        try:
            if callable(indexer):
                if self.DEBUG_UTILS:
                    print "INDEXER IS CALLABLE"
                index = indexer(thing)
            else:
                if self.DEBUG_UTILS:
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
                    resolver(thing, register[index], index, registerName)
            else:
                if index not in register:
                    register[index] = []
                if not unique or thing not in register[index]:
                    register[index].append(thing)
        # print "registered", thing

    @classmethod
    def registerError(self, error, source=None):
        if source:
            try:
                index = source.index
                assert not callable(index)
            except:
                index = source
        else:
            index = debugUtils.get_caller_procedures()
        error_string = SanitationUtils.coerce_unicode(error)
        if self.DEBUG_ERROR:
            Registrar.printAnything(index, error_string, '!')
        self.registerAnything(
            error_string,
            Registrar.errors,
            index,
            singular=False,
            registerName='errors'
        )

    @classmethod
    def registerWarning(self, message, source=None):
        if source:
            try:
                index = source.index
                assert not callable(index)
            except:
                index = source
        else:
            index = debugUtils.get_caller_procedures()
        error_string = SanitationUtils.coerce_unicode(message)
        if self.DEBUG_WARN:
            Registrar.printAnything(index, error_string, '|')
        self.registerAnything(
            error_string,
            Registrar.warnings,
            index,
            singular=False,
            registerName='warnings'
        )

    @classmethod
    def registerMessage(self, message, source=None):
        if source is None:
            source = debugUtils.get_caller_procedures()
        if self.DEBUG_MESSAGE:
            Registrar.printAnything(source, message, '~')
        self.registerAnything(
            message,
            Registrar.messages,
            source,
            singular=False,
            registerName='messages'
        )

    @classmethod
    def registerProgress(self, message):
        if self.DEBUG_PROGRESS:
            print debugUtils.hashify(message)

    @classmethod
    def getMessageItems(self, verbosity=0):
        items = self.errors
        if verbosity > 0:
            items = listUtils.combine_ordered_dicts(items, self.warnings)
        if verbosity > 1:
            items = listUtils.combine_ordered_dicts(items, self.messages)
        return items

    @classmethod
    def print_message_dict(self, verbosity):
        items = self.getMessageItems(verbosity)
        for key, messages in items.items():
            for message in messages:
                self.printAnything(key, message, '|')


class ValidationUtils:

    @staticmethod
    def isNotNone(arg):
        return arg is not None

    @staticmethod
    def isContainedIn(l):
        return lambda v: v in l


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
    m = time.time()
    sec = math.floor(m)
    usec = math.floor(1000000 * (m - sec))
    if more_entropy:
        lcg = random.random()
        the_uniqid = "%08x%05x%.8F" % (sec, usec, lcg * 10)
    else:
        the_uniqid = '%8x%05x' % (sec, usec)

    the_uniqid = prefix + the_uniqid
    return the_uniqid


class PHPUtils:

    @staticmethod
    def uniqid(prefix="", more_entropy=False):
        # raise DeprecationWarning('uniqid deprecated')
        return uniqid(prefix, more_entropy)

    @staticmethod
    def ruleset_uniqid():
        return PHPUtils.uniqid("set_")

    @staticmethod
    def serialize(thing):
        return dumps(thing)

    @staticmethod
    def unserialize(string):
        return loads(string)


class ProgressCounter(object):

    def __init__(self, total, printThreshold=1):
        self.total = total
        self.printThreshold = printThreshold
        self.last_print = time.time()
        self.first_print = self.last_print
        self.printCount = 0
        # self.memory_tracker = tracker.SummaryTracker()

    def maybePrintUpdate(self, count):
        now = time.time()
        if now - self.last_print > self.printThreshold:
            # self.memory_tracker.print_diff()
            self.last_print = now
            percentage = 0
            if self.total > 0:
                percentage = 100 * count / self.total
            line = "(%3d%%) %10d of %10d items processed" % (
                percentage, count, self.total)
            if percentage > 1 and percentage < 100:
                time_elapsed = self.last_print - self.first_print
                ratio = (float(self.total) / (count) - 1.0)
                time_remaining = float(time_elapsed) * ratio
                # line += " | elapsesd: %3f | ratio: %3f" % (time_elapsed, ratio )
                line += " | remaining: %3d seconds" % int(time_remaining)
            if self.printCount > 0:
                line = "\r%s\r" % line
            sys.stdout.write(line)
            sys.stdout.flush()
            self.printCount += 1
        if count == self.total - 1:
            print "\n"


class UnicodeCsvDialectUtils(object):
    default_dialect = unicodecsv.excel

    class act_out(unicodecsv.Dialect):
        delimiter = ','
        quoting = unicodecsv.QUOTE_ALL
        doublequote = True
        strict = False
        quotechar = "\""
        escapechar = None
        skipinitialspace = False
        lineterminator = '\r\n'

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
            'delimeter',
            'quotechar',
            'doublequote',
            'escapechar',
            'quotechar',
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
        file_name, ext = os.path.splitext(os.path.basename(path))
        return file_name


if __name__ == '__main__':
    pass
    # test_html_reporter()
    # testTimeUtils()
    # test_sanitation_utils()
    # testUnicodeWriter()
    # testAddressUtils()
    # test_name_utils()
