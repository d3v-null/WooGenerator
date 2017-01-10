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
import time, math, random
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

DEFAULT_ENCODING = 'utf8'

class SanitationUtils:
    email_regex = r"[\w.+-]+@[\w-]+\.[\w.-]+"
    regex_url_simple = r"https?:\/\/(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{2,256}\.[a-z]{2,6}\b(?:[-a-zA-Z0-9@:%_\+.~#?&//=]*)"
    regex_url = \
        ur'(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)'+\
        ur'(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+'+\
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
    disallowedPunctuation = list(set(punctuationChars) - set(allowedPunctuation))
    whitespaceChars = [ r' ', r'\t', r'\r', r'\n', 'r\f']
    #disallowed punctuation and whitespace
    disallowedPunctuationOrSpace = list(set(disallowedPunctuation + whitespaceChars))
    #delimeter characters incl whitespace and disallowed punc
    tokenDelimeters  =  list(set([ r"\d"] + disallowedPunctuation + whitespaceChars))
    #delimeter characters including all punctuation and whitespace
    tokenPunctuationDelimeters = list(set([r"\d"] + punctuationChars + whitespaceChars))
    #delimeter characters excl space
    tokenDelimetersNoSpace  = list(set(disallowedPunctuation + whitespaceChars + [r"\d"]) - set([' ']))
    punctuationRegex = r"[%s]" % "".join(punctuationChars)
    #delimeter characters incl space and disallowed punc
    delimeterRegex   = r"[%s]" % "".join(tokenDelimeters)
    #disallowed punctuation and whitespace
    disallowedPunctuationOrSpaceRegex = r"[%s]" % "".join(disallowedPunctuationOrSpace)
    #disallowed punctuation
    disallowedPunctuationRegex = r"[%s]" % "".join(disallowedPunctuation)
    #not a delimeter (no whitespace or disallowed punc)
    nondelimeterRegex = r"[^%s]" % "".join(tokenDelimeters)
    #not a delimeter or punctuation (no punctuation or whitespace)
    nondelimeterPunctuationRegex = r"[^%s]" % "".join(tokenPunctuationDelimeters)
    #not a delimeter except space (no whitespace except space, no disallowed punc)
    nondelimeterOrSpaceRegex = r"[^%s]" % "".join(tokenDelimetersNoSpace)
    disallowedPhoneCharRegex = r"[^%s]" % "".join(allowedPhonePunctuation + [r'\d', r' '])
    clearStartRegex  = r"(?<!%s)" % nondelimeterRegex
    clearFinishRegex = r"(?!%s)" % nondelimeterRegex

    @classmethod
    def wrapClearRegex(cls, regex):
        return cls.clearStartRegex + regex + cls.clearFinishRegex

    @classmethod
    def identifyAbbreviation(cls, abbrvDict, string):
        for abbrvKey, abbrvs in abbrvDict.items():
            if( string in [abbrvKey] + abbrvs):
                return abbrvKey
        return string

    @classmethod
    def identifyAbbreviations(cls, abbrvDict, string):
        matches = re.findall(
            '('+cls.compileAbbrvRegex(abbrvDict)+')',
            string
        )

        for candidate in [match for match in filter(None, matches)]:
            identified = cls.identifyAbbreviation(abbrvDict, candidate)
            if identified: yield identified

    @classmethod
    def compilePartialAbbrvRegex(cls,  abbrvKey, abbrvs ):
        return "|".join(filter(None,[
            "|".join(filter(None,abbrvs)),
            abbrvKey
        ]))

    @classmethod
    def compileAbbrvRegex(cls,  abbrv ):
        return "|".join(filter(None,
            [cls.compilePartialAbbrvRegex(abbrvKey, abbrvValue) for abbrvKey, abbrvValue in abbrv.items()]
        ))

    @classmethod
    def compose(cls, *functions):
        return functools.reduce(lambda f, g: lambda x: f(g(x)), functions)

    # Functions for dealing with string encodings

    @classmethod
    def assertAscii(cls, string):
        for index, char in enumerate(string):
            assert ord(char) < 128, "char %s of string %s ... is not ascii" % (index, (string[:index-1]))

    @classmethod
    def unicodeToUTF8(cls, u_str):
        assert isinstance(u_str, unicode), "parameter should be unicode not %s" % type(u_str)
        byte_return = converters.to_bytes(u_str, "utf8")
        assert isinstance(byte_return, str), "something went wrong, should return str not %s" % type(byte_return)
        return byte_return

    @classmethod
    def unicodeToAscii(cls, u_str):
        assert isinstance(u_str, unicode), "parameter should be unicode not %s" % type(u_str)
        byte_return = converters.to_bytes(u_str, "ascii", "backslashreplace")
        assert isinstance(byte_return, str), "something went wrong, should return str not %s" % type(byte_return)
        return byte_return

    @classmethod
    def unicodeToXml(cls, u_str, ascii_only = False):
        assert isinstance(u_str, unicode), "parameter should be unicode not %s" % type(u_str)
        if ascii_only:
            byte_return = converters.unicode_to_xml(u_str, encoding="ascii")
        else:
            byte_return = converters.unicode_to_xml(u_str)
        assert isinstance(byte_return, str), "something went wrong, should return str not %s" % type(byte_return)
        return byte_return

    @classmethod
    def utf8ToUnicode(cls, utf8_str):
        assert isinstance(utf8_str, str), "parameter should be str not %s" % type(utf8_str)
        byte_return = converters.to_unicode(utf8_str, "utf8")
        assert isinstance(byte_return, unicode), "something went wrong, should return unicode not %s" % type(byte_return)
        return byte_return

    @classmethod
    def xmlToUnicode(cls, utf8_str):
        assert isinstance(utf8_str, str), "parameter should be str not %s" % type(utf8_str)
        byte_return = converters.xml_to_unicode(utf8_str)
        assert isinstance(byte_return, str), "something went wrong, should return str not %s" % type(byte_return)
        return byte_return

    @classmethod
    def asciiToUnicode(cls, ascii_str):
        assert isinstance(ascii_str, str), "parameter should be str not %s" % type(ascii_str)
        unicode_return = converters.to_unicode(ascii_str, "ascii")
        assert isinstance(unicode_return, unicode), "something went wrong, should return unicode not %s" % type(unicode_return)
        return unicode_return

    @classmethod
    def coerceUnicode(cls, thing):
        if thing is None:
            unicode_return = u""
        else:
            unicode_return = converters.to_unicode(thing, encoding="utf8")
        assert isinstance(unicode_return, unicode), "something went wrong, should return unicode not %s" % type(unicode_return)
        return unicode_return

    @classmethod
    def coerceBytes(cls, thing):
        byte_return = cls.compose(
            cls.unicodeToUTF8,
            cls.coerceUnicode
        )(thing)
        assert isinstance(byte_return, str), "something went wrong, should return str not %s" % type(byte_return)
        return byte_return

    @classmethod
    def coerceAscii(cls, thing):
        byte_return = cls.compose(
            cls.unicodeToAscii,
            cls.coerceUnicode
        )(thing)
        assert isinstance(byte_return, str), "something went wrong, should return str not %s" % type(byte_return)
        return byte_return

    @classmethod
    def coerceXML(cls, thing):
        byte_return = cls.compose(
            cls.unicodeToXml,
            cls.coerceUnicode
        )(thing)
        assert isinstance(byte_return, str), "something went wrong, should return str not %s" % type(byte_return)
        return byte_return

    @classmethod
    def coerceFloat(cls, thing):
        unicode_thing = cls.compose(
            cls.coerceUnicode
        )(thing)
        try:
            float_return = float(unicode_thing)
        except ValueError:
            float_return = 0.0
        assert isinstance(float_return, float), "something went wrong, should return str not %s" % type(float_return)
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
            cls.coerceUnicode,
            cls.limitString(50),
            cls.escapeNewlines,
            cls.coerceUnicode
        )(thing)
        assert isinstance(unicode_return, unicode), "something went wrong, should return unicode not %s" % type(unicode_return)
        return unicode_return

    @classmethod
    def sanitizeForXml(cls, thing):
        unicode_return = cls.compose(
            cls.coerceUnicode,
            cls.sanitizeNewlines,
            cls.unicodeToXml,
            cls.coerceUnicode
        )(thing)
        assert isinstance(unicode_return, unicode), "something went wrong, should return unicode not %s" % type(unicode_return)
        return unicode_return

    @classmethod
    def safePrint(cls, *args):
        print " ".join([cls.coerceBytes(arg) for arg in args ])

    @classmethod
    def normalizeVal(cls, thing):
        unicode_return = cls.compose(
            cls.coerceUnicode,
            cls.toUpper,
            cls.stripLeadingWhitespace,
            cls.stripTailingWhitespace,
            cls.stripExtraWhitespace,
            cls.coerceUnicode
        )(thing)
        assert isinstance(unicode_return, unicode), "something went wrong, should return unicode not %s" % type(unicode_return)
        return unicode_return

    @classmethod
    def removeLeadingDollarWhiteSpace(cls, string):
        str_out = re.sub('^\W*\$','', string)
        if Registrar.DEBUG_UTILS: print "removeLeadingDollarWhiteSpace", repr(string), repr(str_out)
        return str_out

    @classmethod
    def removeLeadingPercentWhiteSpace(cls, string):
        str_out = re.sub('%\W*$','', string)
        if Registrar.DEBUG_UTILS: print "removeLeadingPercentWhiteSpace", repr(string), repr(str_out)
        return str_out

    @classmethod
    def removeLoneDashes(cls, string):
        str_out = re.sub('^-$', '', string)
        if Registrar.DEBUG_UTILS: print "removeLoneDashes", repr(string), repr(str_out)
        return str_out

    @classmethod
    def removeThousandsSeparator(cls, string):
        str_out = re.sub(r'(\d+),(\d{3})', '\g<1>\g<2>', string)
        if Registrar.DEBUG_UTILS: print "removeThousandsSeparator", repr(string), repr(str_out)
        return str_out

    @classmethod
    def removeLoneWhiteSpace(cls, string):
        str_out = re.sub(r'^\s*$','', string)
        if Registrar.DEBUG_UTILS: print "removeLoneWhiteSpace", repr(string), repr(str_out)
        return str_out

    @classmethod
    def removeNULL(cls, string):
        str_out = re.sub(r'^NULL$', '', string)
        if Registrar.DEBUG_UTILS: print "removeNULL", repr(string), repr(str_out)
        return str_out

    @classmethod
    def stripLeadingWhitespace(cls, string):
        str_out = re.sub(r'^\s*', '', string)
        if Registrar.DEBUG_UTILS: print "stripLeadingWhitespace", repr(string), repr(str_out)
        return str_out

    @classmethod
    def stripLeadingNewline(cls, string):
        str_out = re.sub(r'^(\\n|\n)*', '', string)
        if Registrar.DEBUG_UTILS: print "stripLeadingNewline", repr(string), repr(str_out)
        return str_out

    @classmethod
    def stripTailingWhitespace(cls, string):
        str_out = re.sub(r'\s*$', '', string)
        if Registrar.DEBUG_UTILS: print "stripTailingWhitespace", repr(string), repr(str_out)
        return str_out

    @classmethod
    def stripTailingNewline(cls, string):
        str_out = re.sub(r'(\\n|\n)*$', '', string)
        if Registrar.DEBUG_UTILS: print "stripTailingNewline", repr(string), repr(str_out)
        return str_out

    @classmethod
    def stripAllWhitespace(cls, string):
        str_out = re.sub(r'\s', '', string)
        if Registrar.DEBUG_UTILS: print "stripAllWhitespace", repr(string), repr(str_out)
        return str_out

    @classmethod
    def stripExtraWhitespace(cls, string):
        str_out = re.sub(r'\s{2,}', ' ', string)
        if Registrar.DEBUG_UTILS: print "stripExtraWhitespace", repr(string), repr(str_out)
        return str_out

    @classmethod
    def stripNonNumbers(cls, string):
        str_out = re.sub(r'[^\d]', '', string)
        if Registrar.DEBUG_UTILS: print "stripNonNumbers", repr(string), repr(str_out)
        return str_out

    @classmethod
    def stripNonPhoneCharacters(cls, string):
        str_out = re.sub(cls.disallowedPhoneCharRegex, '', string)
        return str_out

    @classmethod
    def stripPunctuation(cls, string):
        str_out = re.sub(r'[%s]' % ''.join(cls.punctuationChars) , '', string)
        if Registrar.DEBUG_UTILS: print "stripPunctuation", repr(string), repr(str_out)
        return str_out

    @classmethod
    def stripAreaCode(cls, string):
        str_out = re.sub(r'\s*\+\d{2,3}\s*','', string)
        if Registrar.DEBUG_UTILS: print "stripAreaCode", repr(string), repr(str_out)
        return str_out

    @classmethod
    def stripURLProtocol(cls, string):
        str_out = re.sub(r"^\w+://", "", string)
        if Registrar.DEBUG_UTILS: print "stripURLProtocol", repr(string), repr(str_out)
        return str_out

    @classmethod
    def stripPTags(cls, string):
        str_out = re.sub(r"</?p[^>]*>", "", string)
        if Registrar.DEBUG_UTILS: print "stripURLProtocol", repr(string), repr(str_out)
        return str_out

    @classmethod
    def stripBrTags(cls, string):
        str_out = re.sub(r"</?\s*br\s*/?>", "", string)
        if Registrar.DEBUG_UTILS: print "stripURLProtocol", repr(string), repr(str_out)
        return str_out

    @classmethod
    def stripURLHost(cls, url):
        str_out = url
        result = urlparse(url)
        if result:
            if result.scheme:
                remove_str = '%s:' % result.scheme
                if str_out.startswith( remove_str ):
                    str_out = str_out[len(remove_str):]
            if result.netloc:
                remove_str = '//%s' % result.netloc
                if str_out.startswith(remove_str):
                    str_out = str_out[len(remove_str):]

        if Registrar.DEBUG_UTILS: print "stripURLHost", repr(url), repr(str_out)
        return str_out

    @classmethod
    def toLower(cls, string):
        str_out = string.lower()
        if Registrar.DEBUG_UTILS: print "toLower", repr(string), repr(str_out)
        return str_out

    @classmethod
    def toUpper(cls, string):
        str_out = string.upper()
        if Registrar.DEBUG_UTILS: print "toUpper", repr(string), repr(str_out)
        return str_out

    @classmethod
    def sanitizeNewlines(cls, string):
        return re.sub('\n','</br>', string)

    @classmethod
    def escapeNewlines(cls, string):
        return re.sub('\n',r'\\n', string)

    @classmethod
    def compileRegex(cls, subs):
        if subs:
            return re.compile( "(%s)" % '|'.join(filter(None, map(re.escape, subs))) )
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
            cls.coerceUnicode
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
            cls.coerceUnicode
        )(string)

    @classmethod
    def similarNoPunctuationComparison(cls, string):
        return cls.compose(
            cls.normalizeVal,
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
            cls.coerceUnicode
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
            cls.coerceUnicode
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
            cls.coerceUnicode
        )(string)

    @classmethod
    def similarCurrencyComparison(cls, string):
        return cls.compose(
            cls.coerceFloat,
            cls.removeLeadingDollarWhiteSpace,
            cls.coerceUnicode,
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
            return cls.html_unescape(cls.coerceUnicode(things))
        else:
            return things

    @classmethod
    def findAllImages(cls, instring):
        # assert isinstance(instring, (str, unicode)), "param must be a string not %s"% type(instring)
        # if not isinstance(instring, unicode):
            # instring = instring.decode('utf-8')
        instring = cls.coerceUnicode(instring)
        return re.findall(r'\s*([^.|]*\.[^.|\s]*)(?:\s*|\s*)',instring)

    @classmethod
    def findAllTokens(cls, instring, delim = "|"):
        # assert isinstance(instring, (str, unicode)), "param must be a string not %s"% type(instring)
        # if not isinstance(instring, unicode):
            # instring = instring.decode('utf-8')
        instring = cls.coerceUnicode(instring)
        return re.findall(r'\s*(\b[^\s.|]+\b)\s*', instring )

    @classmethod
    def findallDollars(cls, instring):
        # assert isinstance(instring, (str, unicode)), "param must be a string not %s"% type(instring)
        # if not isinstance(instring, unicode):
            # instring = instring.decode('utf-8')
        instring = cls.coerceUnicode(instring)
        return re.findall(r"\s*\$([\d,]+\.?\d*)", instring)

    @classmethod
    def findallPercent(cls, instring):
        # assert isinstance(instring, (str, unicode)), "param must be a string not %s"% type(instring)
        # if not isinstance(instring, unicode):
            # instring = instring.decode('utf-8')
        instring = cls.coerceUnicode(instring)
        return re.findall(r"\s*(\d+\.?\d*)%", instring)

    @classmethod
    def findallEmails(cls, instring):
        instring = cls.coerceUnicode(instring)
        return re.findall(
            cls.wrapClearRegex( cls.email_regex ),
            instring
        )

    @classmethod
    def findallURLs(cls, instring):
        instring = cls.coerceUnicode(instring)
        instring = cls.html_unescape(instring)
        return re.findall(
            '(' + cls.regex_url_simple + ')',
            instring
        )

    @classmethod
    def findall_wp_links(cls, string):
        #todo implement
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
        assert isinstance(instring, (str, unicode)), "param must be a string not %s"% type(instring)
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
        return True if(re.search(cls.disallowedPunctuationRegex, string)) else False

    @classmethod
    def stringContainsPunctuation(cls, string):
        return True if(re.search(cls.punctuationRegex, string)) else False

    @classmethod
    def truishStringToBool(cls, string):
        if( not string or 'n' in string or 'false' in string or string == '0' or string == 0):
            if Registrar.DEBUG_UTILS: print "truishStringToBool", repr(string), 'FALSE'
            return "FALSE"
        else:
            if Registrar.DEBUG_UTILS: print "truishStringToBool", repr(string), 'TRUE'
            return "TRUE"

    @classmethod
    def boolToTruishString(cls, boolVal):
        if boolVal:
            return "TRUE"
        else:
            return "FALSE"

    @classmethod
    def datetotimestamp(cls, datestring):
        raise DeprecationWarning()
        # assert isinstance(datestring, (str,unicode)), "param must be a string not %s"% type(datestring)
        # return int(time.mktime(datetime.datetime.strptime(datestring, "%d/%m/%Y").timetuple()))

    @classmethod
    def decodeJSON(cls, json_str):
        assert isinstance(json_str, (str, unicode))
        attrs = json.loads(json_str)
        return attrs

    @classmethod
    def encodeJSON(cls, obj):
        assert isinstance(obj, (dict, list))
        json_str = json.dumps(obj, encoding="utf8", ensure_ascii=False)
        return json_str

    @classmethod
    def encodeBase64(cls, str):
        utf8_str = cls.coerceBytes(str)
        return base64.standard_b64encode(utf8_str)

    @classmethod
    def decodeBase64(cls, b64_str):
        return base64.standard_b64decode(b64_str)

def testSanitationUtils():
    # pass

    # obj = {
    #     'key': SanitationUtils.coerceBytes(" 👌 ashdfk"),
    #     'list': [
    #         "🐸",
    #         u"\u2014"
    #     ]
    # }
    # print obj, repr(obj)
    # obj_json = SanitationUtils.encodeJSON(obj)
    # SanitationUtils.safePrint(obj_json, repr(obj_json) )
    # obj_json_base64 = SanitationUtils.encodeBase64(obj_json)
    # print obj_json_base64
    # obj_json_decoded = SanitationUtils.decodeBase64(obj_json_base64)
    # print obj_json_decoded
    # obj_decoded = SanitationUtils.decodeJSON(obj_json_decoded)
    # print obj_decoded

    fields = {
        u'first_name':  SanitationUtils.coerceBytes(u'no👌od👌le'),
        'user_url': "http://www.laserphile.com/asd",
        'first_name': 'noo-dle',
        'user_login': "admin"
    }

    SanitationUtils.safePrint( fields, repr(fields) )
    fields_json = SanitationUtils.encodeJSON(fields)
    SanitationUtils.safePrint( fields_json, repr(fields_json) )
    fields_json_base64 = SanitationUtils.encodeBase64( fields_json )
    SanitationUtils.safePrint( fields_json_base64, repr(fields_json_base64) )


    # should be   eyJ1c2VyX2xvZ2luIjogImFkbWluIiwgImZpcnN0X25hbWUiOiAibm/wn5GMb2Twn5GMbGUiLCAidXNlcl91cmwiOiAiaHR0cDovL3d3dy5sYXNlcnBoaWxlLmNvbS9hc2QifQ==
    # is actually eyJ1c2VyX2xvZ2luIjogImFkbWluIiwgImZpcnN0X25hbWUiOiAibm_wn5GMb2Twn5GMbGUiLCAidXNlcl91cmwiOiAiaHR0cDovL3d3dy5sYXNlcnBoaWxlLmNvbS9hc2QifQ==

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
    # SanitationUtils.safePrint( SanitationUtils.escapeNewlines(a))

class NameUtils:
    ordinalNumberRegex = r"(\d+)(?:ST|ND|RD|TH)"

    # #disallowed punctuation and whitespace
    # disallowedPunctuationOrSpace = list(set(disallowedPunctuation + whitespaceChars))
    # #delimeter characters incl whitespace and disallowed punc
    # tokenDelimeters  =  list(set([ r"\d"] + disallowedPunctuation + whitespaceChars))
    # #delimeter characters including all punctuation and whitespace
    # tokenPunctuationDelimeters = list(set([r"\d"] + punctuationChars + whitespaceChars))
    # #delimeter characters excl space
    # tokenDelimetersNoSpace  = list(set(disallowedPunctuation + whitespaceChars + [r"\d"]) - set([' ']))
    # punctuationRegex = r"[%s]" % "".join(punctuationChars)
    # #delimeter characters incl space and disallowed punc
    # delimeterRegex   = r"[%s]" % "".join(tokenDelimeters)
    # #disallowed punctuation and whitespace
    # disallowedPunctuationOrSpaceRegex = r"[%s]" % "".join(disallowedPunctuationOrSpace)
    # #disallowed punctuation
    # disallowedPunctuationRegex = r"[%s]" % "".join(disallowedPunctuation)
    # #not a delimeter (no whitespace or disallowed punc)
    # nondelimeterRegex = r"[^%s]" % "".join(tokenDelimeters)
    # #not a delimeter or punctuation (no punctuation or whitespace)
    # nondelimeterPunctuationRegex = r"[^%s]" % "".join(tokenPunctuationDelimeters)
    # #not a delimeter except space (no whitespace except space, no disallowed punc)

    singleNameRegex       = r"(?!{Ds}+.*)({ndp}(?:{nd}*{ndp})?|{ord})".format(
        #disallowed punctuation and whitespace
        Ds = SanitationUtils.disallowedPunctuationOrSpaceRegex,
        #not a delimeter (no whitespace or disallowed punc)
        nd = SanitationUtils.nondelimeterRegex,
        #not a delimeter or punctuation (no punctuation or whitespace)
        ndp = SanitationUtils.nondelimeterPunctuationRegex,
        ord = ordinalNumberRegex
    )

    LazyMultiNameNoOrdRegex = "(?!{Ds}+.*)(?:{nd}(?:{nds}*?{nd})?)".format(
        #disallowed punctuation and whitespace
        Ds = SanitationUtils.disallowedPunctuationOrSpaceRegex,
        #not a delimeter (no whitespace or disallowed punc)
        nd = SanitationUtils.nondelimeterRegex,
        #not a delimeter except space (no whitespace except space, no disallowed punc)
        nds = SanitationUtils.nondelimeterOrSpaceRegex
    )

    greedyMultiNameNoOrdRegex = "(?!{Ds}+.*)(?:{nd}(?:{nds}*{nd})?)".format(
        Ds = SanitationUtils.disallowedPunctuationOrSpaceRegex,
        nd = SanitationUtils.nondelimeterRegex,
        nds = SanitationUtils.nondelimeterOrSpaceRegex
    )

    lazyMultiNameRegex  = "((?:{ord} )?{mnr}(?: {ord}(?: {mnr})?)?)".format(
        mnr = LazyMultiNameNoOrdRegex,
        ord = ordinalNumberRegex
    )

    greedyMultiNameRegex = "((?:{ord} )?{mnr}(?: {ord}(?: {mnr})?)?)".format(
        mnr = greedyMultiNameNoOrdRegex,
        ord = ordinalNumberRegex
    )

    titleAbbreviations = OrderedDict([
        ('DR', ['DOCTOR', 'DR.']),
        ('HON', ['HONORABLE', 'HON.']),
        ('REV', ['REVEREND', 'REV.']),
        ('MR', ['MISTER', 'MR.']),
        ('MS', ['MISS', 'MISSES', 'MS.']),
        ('MRS', []),
        ('MX', []),
    ])

    positionAbbreviations = OrderedDict([
        ('OWNER', []),
        ('ACCOUNTANT', ['ACCTS']),
        ('SALES MANAGER', []),
        ('MANAGER', []),
        ('BEAUTICIAN', []),
        ('DIRECTOR', []),
        ('HAIRDRESSER', []),
        ('STYLIST', []),
        ('CEO',     []),
        ('FINANCE DEPT', ['FINANCE DEPARTMENT']),
        ('RECEPTION', ['RECEPTION']),
    ])

    noteAbbreviations = OrderedDict([
        ('SPOKE WITH', ['SPIKE WITH', 'SPOKE W', "SPOKE TO"]),
        ('CLOSED', ['CLOSED DOWN', 'CLOSED BUSINESS']),
        ('PRONOUNCED', []),
        ('ARCHIVE', []),
        ('STOCK', ['STOCK ACCOUNT', 'STOCK ACCT', 'STOCK ACCNT']),
        ('ACCOUNT', []),
        ('RETAIL ACCOUNT', []),
        ('STAFF', []),
        ('FINALIST', []),
        ('BOOK A TAN CUSTOMER', []),
        ('SOLD EQUIPMENT', []),
        ("NOT THIS ONE", []),
        ("TECHNOTAN", []),
        ("TECHNICIAN", []),
        ("SPONSORSHIP", []),
        ("TRAINING", []),
        ("OPEN BY APPT ONLY", []),
        ('CUSTOMER', []),
        ('NOTE', []),
        ("N/A", []),
        ('UNSUBSCRIBED', ["UNSUBSCRIBE"]),
    ])

    noteDelimeters = OrderedDict([
        ("-", []),
        (r"&", []),
        (r"\?",   []),
        (r"@",     []),
        ('AND', ['&AMP']),
        ('OR', []),
    ])

    careOfAbbreviations = OrderedDict([
        ('C/O',     ['C/-', 'CARE OF']),
        ('ATTN',   ['ATTENTION'])
    ])

    organizationTypeAbbreviations = OrderedDict([
        ('CO',      ['COMPANY']),
        ('INC',     ['INCORPORATED']),
        ('LTD',     ['LIMITED']),
        ('NL',      ['NO LIABILITY']),
        ('PTY',     ['PROPRIETARY']),
        ('PTY LTD', ['PROPRIETARY LIMITED'])
    ])

    nameSuffixAbbreviations = OrderedDict([
        ('SR', ['SENIOR', 'SR.']),
        ('JR', ['JUNIOR', 'DR.'])
    ])

    familyNamePrefixAbbreviations = OrderedDict([
        ('MC',      []),
        ('MAC',     []),
        ('VAN DE', []),
        ('VAN DER', []),
        ('VAN DEN', []),
        ('VAN',     []),
        ('DER',     []),
        ('DI',      []),
        ('O',       []),
        ('O',       []),
    ])

    titleRegex = r"(?P<name_title>%s)\.?" % (
        SanitationUtils.compileAbbrvRegex(titleAbbreviations)
    )

    positionRegex = r"(?P<name_position>%s)\.?" % (
        SanitationUtils.compileAbbrvRegex(positionAbbreviations)
    )

    familyNamePrefixRegex = r"%s" % (
        SanitationUtils.compileAbbrvRegex(familyNamePrefixAbbreviations)
    )

    familyNameRegex = r"(?:(?P<family_name_prefix>%s) )?(?P<family_name>%s)" % (
        familyNamePrefixRegex,
        singleNameRegex
    )


    # valid notes
    # (NOTE_BEFORE names_after_note?)
    # (names_before_note_MIDDLE? NOTE_MIDDLE names_after_note_MIDDLE?)
    # (note_names_only)
    # NOTE_ONLY
    # OTHERS?
    noteRegex = (r"(?:"+\
                    r"|".join([
                        r"(?P<name_before_note_paren>{name})?(?P<note_open_paren>\() ?(?:"+ \
                        r"|".join([
                            r"(?P<note_before>{note})\.? ?(?P<names_after_note>{names})?",
                            r"(?P<names_before_note_middle>{names})? ?(?P<note_middle>{note})\.? ?(?P<names_after_note_middle>{names})?",
                            r"(?P<note_names_only>{names})"
                        ]),
                        r") ?(?P<note_close_paren>\))",
                        r"(?P<note_only>{note})",
                        r"(?P<note_delimeter>{noted}) (?P<names_after_note_delimeter>{names})?"
                    ]) +\
                r")").format(
        note=SanitationUtils.wrapClearRegex(SanitationUtils.compileAbbrvRegex(noteAbbreviations)),
        noted = SanitationUtils.wrapClearRegex(SanitationUtils.compileAbbrvRegex(noteDelimeters)),
        names=lazyMultiNameRegex,
        name=singleNameRegex,
    )

    careOfRegex = r"(?P<careof>%s)[\.:]? ?(?P<careof_names>%s)" % (
        SanitationUtils.compileAbbrvRegex(careOfAbbreviations),
        greedyMultiNameRegex,
    )

    nameSuffixRegex = r"\(?(?P<name_suffix>%s)\.?\)?" % (
        SanitationUtils.compileAbbrvRegex(nameSuffixAbbreviations)
    )

    organizationRegex = r"(?P<organization_name>%s) (?P<organization_type>%s)\.?" % (
        greedyMultiNameRegex,
        SanitationUtils.compileAbbrvRegex(organizationTypeAbbreviations)
    )

    nameTokenRegex = r"(%s)" % "|".join([
        SanitationUtils.wrapClearRegex( titleRegex),
        SanitationUtils.wrapClearRegex( positionRegex),
        SanitationUtils.wrapClearRegex( nameSuffixRegex),
        SanitationUtils.wrapClearRegex( careOfRegex),
        SanitationUtils.wrapClearRegex( organizationRegex),
        SanitationUtils.wrapClearRegex( SanitationUtils.email_regex ),
        SanitationUtils.wrapClearRegex( noteRegex),
        SanitationUtils.wrapClearRegex( familyNameRegex),
        SanitationUtils.wrapClearRegex( singleNameRegex ),
        SanitationUtils.wrapClearRegex( ordinalNumberRegex),
        SanitationUtils.disallowedPunctuationRegex
    ])

    @staticmethod
    def identifyTitle(string):
        return SanitationUtils.identifyAbbreviation(NameUtils.titleAbbreviations, string)

    @staticmethod
    def identifyNote(string):
        return SanitationUtils.identifyAbbreviation(NameUtils.noteAbbreviations, string)

    @staticmethod
    def identifyPosition(string):
        return SanitationUtils.identifyAbbreviation(NameUtils.positionAbbreviations, string)

    @staticmethod
    def identifyNameSuffix(string):
        return SanitationUtils.identifyAbbreviation(NameUtils.nameSuffixAbbreviations, string)

    @staticmethod
    def identifyCareOf(string):
        return SanitationUtils.identifyAbbreviation(NameUtils.careOfAbbreviations, string)

    @staticmethod
    def identifyOrganization(string):
        return SanitationUtils.identifyAbbreviation(NameUtils.organizationTypeAbbreviations, string)

    @staticmethod
    def sanitizeNameToken(string):
        return SanitationUtils.normalizeVal(string)

    @staticmethod
    def getSingleName(token):
        match = re.match(
            SanitationUtils.wrapClearRegex(
                NameUtils.singleNameRegex
            ),
            token
        )
        matchGrps = match.groups() if match else None
        if(matchGrps):
            # name = " ".join(matchGrps)
            name = matchGrps[0]
            if Registrar.DEBUG_NAME: SanitationUtils.safePrint( "FOUND NAME " + repr(name))
            return name

    @staticmethod
    def getSingleNames(token):
        matches = re.findall(
            SanitationUtils.wrapClearRegex(
                NameUtils.singleNameRegex
            ),
            token
        )
        names = [match[0] for match in filter(None, matches)]
        if names:
            if Registrar.DEBUG_NAME: SanitationUtils.safePrint( "FOUND NAMES " + repr(names))
            return names

    @staticmethod
    def getMultiName(token):
        match = re.match(
            SanitationUtils.wrapClearRegex(
                NameUtils.greedyMultiNameRegex
            ),
            token
        )
        matchGrps = match.groups() if match else None
        if(matchGrps):
            # name = " ".join(matchGrps)
            name = matchGrps[0]
            if Registrar.DEBUG_NAME: SanitationUtils.safePrint( "FOUND NAME " + repr(name))
            return name

    @staticmethod
    def getEmail(token):
        # if Registrar.DEBUG_NAME: SanitationUtils.safePrint("checking email", token)
        match = re.match(
            SanitationUtils.wrapClearRegex(
                "({})".format(SanitationUtils.email_regex)
            ),
            token
        )
        matchGrps = match.groups() if match else None
        if(matchGrps):
            # if Registrar.DEBUG_NAME: SanitationUtils.safePrint("email matches", repr(matchGrps))
            # name = " ".join(matchGrps)
            email = matchGrps[0]
            if Registrar.DEBUG_NAME: SanitationUtils.safePrint( "FOUND EMAIL " + repr(email))
            return email

    @staticmethod
    def getTitle(token):
        match = re.match(
            SanitationUtils.wrapClearRegex(
                NameUtils.titleRegex
            ),
            token
        )
        matchDict = match.groupdict() if match else None
        if matchDict and matchDict.get('name_title'):
            title = NameUtils.identifyTitle(matchDict['name_title'])
            if Registrar.DEBUG_NAME: print "FOUND TITLE ", repr(title)
            return title
        # matchGrps = match.groups() if match else None
        # if(matchGrps):
        #     # title = " ".join(matchGrps)
        #     title = matchGrps[0]
        #     if Registrar.DEBUG_NAME: print "FOUND TITLE ", repr(title)
        #     return title

    @staticmethod
    def getPosition(token):
        match = re.match(
            SanitationUtils.wrapClearRegex(
                NameUtils.positionRegex
            ),
            token
        )
        matchDict = match.groupdict() if match else None
        if matchDict and matchDict.get('name_position'):
            position = NameUtils.identifyPosition(matchDict['name_position'])
            if Registrar.DEBUG_NAME: print "FOUND POSITION ", repr(position)
            return position
        # matchGrps = match.groups() if match else None
        # if(matchGrps):
        #     # position = " ".join(matchGrps)
        #     position = matchGrps[0]
        #     if Registrar.DEBUG_NAME: print "FOUND POSITION ", repr(position)
        #     return position

    @staticmethod
    def getOrdinal(token):
        match = re.match(
            SanitationUtils.wrapClearRegex(
                NameUtils.ordinalNumberRegex
            ),
            token
        )
        matchGrps = match.groups() if match else None
        if matchGrps:
            ordinal = matchGrps[0]
            if Registrar.DEBUG_NAME: SanitationUtils.safePrint("FOUND ORDINAL", ordinal)
            return ordinal

    @staticmethod
    def getNameSuffix(token):
        match = re.match(
            SanitationUtils.wrapClearRegex(
                NameUtils.nameSuffixRegex
            ),
            token
        )
        matchDict = match.groupdict() if match else None
        if matchDict and matchDict.get('name_suffix'):
            suffix = NameUtils.identifyNameSuffix(matchDict['name_suffix'])
            if Registrar.DEBUG_NAME: print "FOUND NAME SUFFIX ", repr(suffix)
            return suffix
        # matchGrps = match.groups() if match else None
        # if(matchGrps):
        #     # position = " ".join(matchGrps)
        #     suffix = matchGrps[0]
        #     if Registrar.DEBUG_NAME: print "FOUND NAME SUFFIX ", repr(suffix)
        #     return suffix

    @staticmethod
    def getNote(token):
        match = re.match(
            SanitationUtils.wrapClearRegex(
                NameUtils.noteRegex
            ),
            token
        )
        matchDict = match.groupdict() if match else None
        if matchDict and (matchDict.get('note_open_paren') or matchDict.get('note_only') or matchDict.get('note_delimeter')):
            note_open_paren = matchDict.get('note_open_paren')
            note_close_paren = matchDict.get('note_close_paren')
            names_before_note = None
            names_after_note = None
            if note_open_paren:
                if matchDict.get('note_before'):
                    note = NameUtils.identifyNote(matchDict.get('note_only'))
                    names_after_note = matchDict.get('names_after_note')
                elif matchDict.get('note_middle'):
                    names_before_note = matchDict.get('names_before_note_middle')
                    note = NameUtils.identifyNote(matchDict.get('note_middle'))
                    names_after_note = matchDict.get('names_after_note_middle')
                else:
                    names_before_note = matchDict.get('note_names_only')
                    note = None
                name_before_note_paren = matchDict.get('name_before_note_paren')
                if name_before_note_paren:
                    names_before_note = " ".join(filter(None, [name_before_note_paren, names_before_note]))
            elif matchDict.get('note_only'):
                note = NameUtils.identifyNote(matchDict.get('note_only'))
            elif matchDict.get('note_delimeter'):
                note = matchDict.get('note_delimeter')
                names_after_note = matchDict.get('names_after_note_delimeter')

            note_tuple = (note_open_paren, names_before_note, note, names_after_note, note_close_paren)
            if Registrar.DEBUG_NAME: print "FOUND NOTE ", repr(note_tuple)
            return note_tuple
        # matchGrps = match.groups() if match else None
        # if(matchGrps):
        #     # note = " ".join(matchGrps)
        #     note = matchGrps[0]
        #     return note

    @staticmethod
    def getFamilyName(token):
        match = re.match(
            SanitationUtils.wrapClearRegex(
                NameUtils.familyNameRegex
            ),
            token
        )
        matchDict = match.groupdict() if match else None
        if matchDict and matchDict.get('family_name'):
            family_name = matchDict['family_name']
            family_name_prefix = matchDict.get('family_name_prefix')
            for component in [family_name_prefix, family_name]:
                if Registrar.DEBUG_NAME: print "name component", repr(component)
            combined_family_name = " ".join(filter(None, [family_name_prefix, family_name]))
            if Registrar.DEBUG_NAME: SanitationUtils.safePrint("FOUND FAMILY NAME", combined_family_name)
            return combined_family_name


    @staticmethod
    def getCareOf(token):
        match = re.match(
            SanitationUtils.wrapClearRegex(
                NameUtils.careOfRegex
            ),
            token
        )
        matchDict = match.groupdict() if match else None
        if matchDict and matchDict.get('careof'):
            careof = NameUtils.identifyCareOf(matchDict.get('careof'))
            names = matchDict.get('careof_names')
            careof_tuple = (careof, names)
            if Registrar.DEBUG_NAME: print "FOUND CAREOF ", repr(careof_tuple)
            return careof_tuple
        # matchGrps = match.groups() if match else None
        # if(matchGrps):
        #     # note = " ".join(matchGrps)
        #     careof = matchGrps[0]
        #     if Registrar.DEBUG_NAME: print "FOUND CAREOF ", repr(careof)
        #     return careof

    @staticmethod
    def getOrganization (token):
        match = re.match(
            SanitationUtils.wrapClearRegex(
                NameUtils.organizationRegex
            ),
            token
        )
        matchDict = match.groupdict() if match else None
        if matchDict and (matchDict.get('organization_name') and matchDict.get('organization_type')):
            organization_name = matchDict.get('organization_name')
            organization_type = matchDict.get('organization_type')
            organization = (organization_name, organization_type)
            if Registrar.DEBUG_NAME: print "FOUND ORGANIZATION ", repr(organization)
            return organization

    @staticmethod
    def tokenizeName(string):
        string = string.upper()
        matches =  re.findall(
            NameUtils.nameTokenRegex,
            string
        )
        # if Registrar.DEBUG_NAME: print repr(matches)
        return map(
            lambda match: NameUtils.sanitizeNameToken(match[0]),
            matches
        )

def testNameUtils():
    pass
    # print SanitationUtils.compileAbbrvRegex(NameUtils.noteAbbreviations)
    # print NameUtils.tokenizeName('DERWENT (ACCT)')
    # print NameUtils.getEmail('KYLIESWEET@GMAIL.COM')

    # assert r'\'' in SanitationUtils.allowedPunctuation
    # assert r'\'' not in SanitationUtils.disallowedPunctuation
    # assert r'\'' not in SanitationUtils.tokenDelimeters
    #
    # print SanitationUtils.tokenDelimeters
    #
    # match = re.match(
    #     '(' + SanitationUtils.nondelimeterRegex + ')',
    #     '\''
    # )
    # if match: print "nondelimeterRegex", [match_item for match_item in match.groups()]
    #
    # match = re.match(
    #     '(' + SanitationUtils.delimeterRegex + ')',
    #     '\''
    # )
    # if match: print "delimeterRegex", [match_item for match_item in match.groups()]
    #
    # match = re.match(
    #     NameUtils.singleNameRegex,
    #     'OCAL\'LAGHAN'
    # )
    # if match: print [match_item for match_item in match.groups()]

    # print "singlename", repr( NameUtils.getSingleName('O\'CALLAGHAN' ))
    # def testNotes(line):
    #     for token in NameUtils.tokenizeName(line):
    #         print token, NameUtils.getNote(token)
    #
    # testNotes("DE-RWENT- FINALIST")
    # testNotes("JAGGERS HAIR- DO NOT WANT TO BE CALLED!!!!")



class AddressUtils:
    subunitAbbreviations = OrderedDict([
        # ('ANT',     ['ANTENNA']),
        ('APARTMENT',     ['APT', 'A']),
        # ('ATM',     ['AUTOMATED TELLER MACHINE']),
        ('BBQ',     ['BARBECUE']),
        # ('BTSD',    ['BOATSHED']),
        ('BUILDING', ['BLDG']),
        # ('BNGW',    ['BUNGALOW']),
        # ('CAGE',    []),
        # ('CARP',    ['CARPARK']),
        # ('CARS',    ['CARSPACE']),
        # ('CLUB',    []),
        # ('COOL',    ['COOLROOM']),
        ('COTTAGE',    ['CTGE']),
        ('DUPLEX',     ['DUP', 'DUPL']),
        ('FACTORY', ['FCTY', 'FY']),
        ('FLAT',    ['FLT','FL','F']),
        ('GARAGE',    ['GRGE']),
        ('HALL',    []),
        ('HOUSE',     ['HSE']),
        ('KIOSK',     ['KSK']),
        ('LEASE',     ['LSE']),
        ('LOBBY',    ['LBBY']),
        ('LOFT',    []),
        ('LOT',     []),
        ('MAISONETTE',    ['MSNT']),
        ('MBTH',    ['MARINE BERTH', 'MB']),
        ('OFFICE',    ['OFFC', 'OFF']),
        ('PENTHOUSE',  ['PTHS']),
        ('REAR',       ['R']),
        # ('RESV',    ['RESERVE']),
        ('ROOM',    ['RM']),
        ('SHED',    []),
        ('SHOP',    ['SH', 'SP', 'SHP']),
        ('SHRM',    ['SHOWROOM']),
        # ('SIGN',    []),
        ('SITE',    []),
        ('STALL',    ['STLL', 'SL']),
        ('STORE',    ['STOR']),
        ('STR',     ['STRATA UNIT']),
        ('STUDIO',     ['STU', 'STUDIO APARTMENT']),
        ('SUBS',    ['SUBSTATION']),
        ('SUITE',      ['SE']),
        ('TNCY',    ['TENANCY']),
        ('TWR',     ['TOWER']),
        ('TOWNHOUSE',    ['TNHS']),
        ('UNIT',    ['U']),
        ('VLT',     ['VAULT']),
        ('VILLA',    ['VLLA']),
        ('WARD',    []),
        ('WAREHOUSE',    ['WHSE', 'WE']),
        ('WKSH',    ['WORKSHOP'])
    ])

    stateAbbreviations = OrderedDict([
        ('AAT',     ['AUSTRALIAN ANTARCTIC TERRITORY']),
        ('ACT',     ['AUSTRALIAN CAPITAL TERRITORY', 'AUS CAPITAL TERRITORY']),
        ('NSW',     ['NEW SOUTH WALES']),
        ('NT',      ['NORTHERN TERRITORY']),
        ('QLD',     ['QUEENSLAND']),
        ('SA',      ['SOUTH AUSTRALIA']),
        ('TAS',     ['TASMAIA']),
        ('VIC',     ['VICTORIA']),
        ('WA',      ['WESTERN AUSTRALIA', 'WEST AUSTRALIA', 'WEST AUS']),
    ])

    floorAbbreviations = OrderedDict([
        ('B',       ['BASEMENT']),
        ('G',       ['GROUND FLOOR', 'GROUND']),
        ('LG',      ['LOWER GROUND FLOOR', 'LOWER GROUND']),
        ('UG',      ['UPPER GROUND FLOOR', 'UPPER GROUND', 'UPPER LEVEL']),
        ('FL',      ['FLOOR', 'FLR']),
        ('LEVEL',   ['LVL', 'L']),
        ('M',       ['MEZZANINE', 'MEZ'])
    ])

    thoroughfareTypeAbbreviations = OrderedDict([
        ('ACCS',     ['ACCESS']),
        ('ALLY',     ['ALLEY']),
        ('ALWY',     ['ALLEYWAY']),
        ('AMBL',     ['AMBLE']),
        ('ANCG',     ['ANCHORAGE']),
        ('APP',      ['APPROACH']),
        ('ARC',      ['ARCADE']),
        ('ARTL',     ['ARTERIAL']),
        ('ARTY',     ['ARTERY', 'ART']),
        ('AVE',      ['AVENUE','AV']),
        ('BASN',     ['BASIN']),
        ('BA',       ['BANAN']),
        ('BCH',      ['BEACH']),
        ('BEND',     []),
        ('BWLK',     ['BOARDWALK']),
        ('BLVD',      ['BOULEVARD', 'BLVD']),
        ('BR',       ['BRACE']),
        ('BRAE',     []),
        ('BRK',      ['BREAK']),
        ('BROW',     []),
        ('BYPA',     ['BYPASS']),
        ('BYWY',     ['BYWAY']),
        ('CSWY',     ['CAUSEWAY']),
        ('CTR',      ['CENTRE']),
        ('CH',       ['CHASE']),
        ('CIR',      ['CIRCLE', 'CCLE']),
        ('CCT',      ['CIRCUIT']),
        ('CRCS',     ['CIRCUS']),
        ('CL',       ['CLOSE']),
        ('CON',      ['CONCOURSE']),
        ('CPS',      ['COPSE']),
        ('CNR',      ['CORNER']),
        ('CT',       ['COURT', 'CRT']),
        ('CTYD',     ['COURTYARD']),
        ('COVE',     []),
        ('CRES',     ['CRESCENT', 'CR', 'CRESENT', 'CRS']),
        ('CRST',     ['CREST']),
        ('CRSS',     ['CROSS']),
        ('CSAC',     ['CUL-DE-SAC']),
        ('CUTT',     ['CUTTING']),
        ('DALE',     []),
        ('DIP',      []),
        ('DR',       ['DRIVE']),
        ('DVWY',     ['DRIVEWAY']),
        ('EDGE',     []),
        ('ELB',      ['ELBOW']),
        ('END',      []),
        ('ENT',      ['ENTRANCE']),
        ('ESP',      ['ESPLANADE']),
        ('EXP',      ['EXPRESSWAY']),
        ('FAWY',     ['FAIRWAY']),
        ('FOLW',     ['FOLLOW']),
        ('FTWY',     ['FOOTWAY']),
        ('FORM',     ['FORMATION']),
        ('FWY',      ['FREEWAY']),
        ('FRTG',     ['FRONTAGE']),
        ('GAP',      []),
        ('GDNS',     ['GARDENS', 'GARDEN']),
        ('GTE',      ['GATE']),
        ('GLDE',     ['GLADE']),
        ('GLEN',     []),
        ('GRA',      ['GRANGE']),
        ('GRN',      ['GREEN']),
        ('GR',       ['GROVE']),
        ('HTS',      ['HEIGHTS']),
        ('HIRD',     ['HIGHROAD']),
        ('HWY',      ['HIGHWAY', 'HGWY', 'HWAY', 'H\'WAY']),
        ('HILL',     []),
        ('INTG',     ['INTERCHANGE']),
        ('JNC',      ['JUNCTION']),
        ('KEY',      []),
        ('LANE',     []),
        ('LNWY',     ['LANEWAY']),
        ('LINE',     []),
        ('LINK',     []),
        ('LKT',      ['LOOKOUT', 'LOOK OUT']),
        ('LOOP',     []),
        ('MALL',     []),
        ('MNDR',     ['MEANDER']),
        ('MEWS',     []),
        ('MTWY',     ['MOTORWAY']),
        ('NOOK',     []),
        ('OTLK',     ['OUTLOOK']),
        ('PDE',      ['PARADE']),
        ('PARK',     []),
        ('PWY',      ['PARKWAY']),
        ('PASS',     []),
        ('PSGE',     ['PASSAGE']),
        ('PATH',     []),
        ('PWAY',     ['PATHWAY']),
        ('PIAZ',     ['PIAZZA']),
        ('PL',       ['PLACE', 'PLCE']),
        ('PLZA',     ['PLAZA']),
        ('PKT',      ['POCKET']),
        ('PNT',      ['POINT']),
        ('PORT',     []),
        ('PROM',     ['PROMENADE']),
        ('QDRT',     ['QUADRANT']),
        ('QYS',      ['QUAYS']),
        ('RMBL',     ['RAMBLE']),
        ('REST',     []),
        ('RTT',      ['RETREAT']),
        ('RDGE',     ['RIDGE']),
        ('RISE',     []),
        ('RD',       ['ROAD']),
        ('RTY',      ['ROTARY']),
        ('RTE',      ['ROUTE']),
        ('ROW',      []),
        ('RUE',      []),
        ('SVWY',     ['SERVICEWAY']),
        ('SHUN',     ['SHUNT']),
        ('SPUR',     []),
        ('SQ',       ['SQUARE']),
        ('ST',       ['STREET']),
        ('STRAIGHT', []),
        ('SBWY',     ['SUBWAY']),
        ('TARN',     []),
        ('TCE',      ['TERRACE']),
        ('THFR',     ['THOROUGHFARE']),
        ('TLWY',     ['TOLLWAY']),
        ('TOP',      []),
        ('TOR',      []),
        ('TRK',      ['TRACK']),
        ('TRL',      ['TRAIL']),
        ('TURN',     []),
        ('UPAS',     ['UNDERPASS']),
        ('VALE',     []),
        ('VIAD',     ['VIADUCT']),
        ('VIEW',     []),
        ('VSTA',     ['VISTA']),
        ('WALK',     []),
        ('WAY',      ['WY']),
        ('WKWY',     ['WALKWAY']),
        ('WHRF',     ['WHARF']),
        ('WYND',     [])
    ])

    thoroughfareSuffixAbbreviations = OrderedDict([
        ('CN',  ['CENTRAL']),
        ('E',   ['EAST']),
        ('EX',  ['EXTENSION']),
        ('LR',  ['LOWER']),
        ('N',   ['NORTH']),
        ('NE',  ['NORTH EAST']),
        ('NW',  ['NORTH WEST']),
        ('S',   ['SOUTH']),
        ('SE',  ['SOUTH EAST']),
        ('SW',  ['SOUTH WEST']),
        ('UP',  ['UPPER']),
        ('W',   ['WEST'])
    ])

    buildingTypeAbbreviations = OrderedDict([
        ('SHOPPING CENTRE', ["S/C", r"SHOP.? CENTRE", "SHOPNG CENTRE" ]),
        ('SHOPPING CENTER', [r"SHOP.? CENTER", "SHOPNG CENTER"  ]),
        ('SHOPPING CTR',    [r"SHOP.? CTR", "SHOPNG CTR" ]),
        ("SHOPPING CTNR",   [r"SHOP.? CTR", "SHOPNG CTNR" ]),
        ('PLAZA',           ['PLZA']),
        ('ARCADE',          ["ARC"]),
        ('MALL',            []),
        ('BUILDING',        ['BLDG']),
        ('FORUM',           []),
        ('HOUSE',           []),
        ('CENTER',          []),
        ('CENTRE',          []),
        ('FORUM',           []),
        ('CTR',             ["CNTR"]),
    ])

    deliveryTypeAbbreviations = OrderedDict([
        ('CARE PO',     []),
        ('CMA',         []),
        ('CMB',         []),
        ('CPA',         []),
        ('GPO BOX',     [r"G\.?P\.?O(\.| )BOX", "GENERAL POST OFFICE BOX"]),
        ('LOCKED BAG',  []),
        ('PO BOX',      [r"P\.?O\.? ?BOX"]),
        ('PO',          []),
        ('RMB',         []),
        ('RMS',         []),
        ('MS',          []),
        ('PRIVATE BAG', []),
        ('PARCEL LOCKER',[]),
    ])

    countryAbbreviations = OrderedDict([
        ('AF', ['AFGHANISTAN']),
        ('AL', ['ALBANIA']),
        ('DZ', ['ALGERIA']),
        ('AS', ['AMERICAN SAMOA']),
        ('AD', ['ANDORRA']),
        ('AO', ['ANGOLA']),
        ('AI', ['ANGUILLA']),
        ('AQ', ['ANTARCTICA']),
        ('AG', ['ANTIGUA AND BARBUDA']),
        ('AR', ['ARGENTINA']),
        ('AM', ['ARMENIA']),
        ('AW', ['ARUBA']),
        ('AU', ['AUSTRALIA']),
        ('AT', ['AUSTRIA']),
        ('AZ', ['AZERBAIJAN']),
        ('BS', ['BAHAMAS']),
        ('BH', ['BAHRAIN']),
        ('BD', ['BANGLADESH']),
        ('BB', ['BARBADOS']),
        ('BY', ['BELARUS']),
        ('BE', ['BELGIUM']),
        ('BZ', ['BELIZE']),
        ('BJ', ['BENIN']),
        ('BM', ['BERMUDA']),
        ('BT', ['BHUTAN']),
        ('BO', ['BOLIVIA']),
        ('BQ', ['BONAIRE']),
        ('BA', ['BOSNIA AND HERZEGOVINA']),
        ('BW', ['BOTSWANA']),
        ('BV', ['BOUVET ISLAND']),
        ('BR', ['BRAZIL']),
        ('IO', ['BRITISH INDIAN OCEAN TERRITORY']),
        ('BN', ['BRUNEI DARUSSALAM']),
        ('BG', ['BULGARIA']),
        ('BF', ['BURKINA FASO']),
        ('BI', ['BURUNDI']),
        ('KH', ['CAMBODIA']),
        ('CM', ['CAMEROON']),
        ('CA', ['CANADA']),
        ('CV', ['CAPE VERDE']),
        ('KY', ['CAYMAN ISLANDS']),
        ('CF', ['CENTRAL AFRICAN REPUBLIC']),
        ('TD', ['CHAD']),
        ('CL', ['CHILE']),
        ('CN', ['CHINA']),
        ('CX', ['CHRISTMAS ISLAND']),
        ('CC', ['COCOS (KEELING) ISLANDS']),
        ('CO', ['COLOMBIA']),
        ('KM', ['COMOROS']),
        ('CG', ['CONGO']),
        ('CD', ['DEMOCRATIC REPUBLIC OF THE CONGO']),
        ('CK', ['COOK ISLANDS']),
        ('CR', ['COSTA RICA']),
        ('HR', ['CROATIA']),
        ('CU', ['CUBA']),
        ('CY', ['CYPRUS']),
        ('CZ', ['CZECH REPUBLIC']),
        ('DK', ['DENMARK']),
        ('DJ', ['DJIBOUTI']),
        ('DM', ['DOMINICA']),
        ('DO', ['DOMINICAN REPUBLIC']),
        ('EC', ['ECUADOR']),
        ('EG', ['EGYPT']),
        ('SV', ['EL SALVADOR']),
        ('GQ', ['EQUATORIAL GUINEA']),
        ('ER', ['ERITREA']),
        ('EE', ['ESTONIA']),
        ('ET', ['ETHIOPIA']),
        ('FK', ['FALKLAND ISLANDS (MALVINAS)']),
        ('FO', ['FAROE ISLANDS']),
        ('FJ', ['FIJI']),
        ('FI', ['FINLAND']),
        ('FR', ['FRANCE']),
        ('GF', ['FRENCH GUIANA']),
        ('PF', ['FRENCH POLYNESIA']),
        ('TF', ['FRENCH SOUTHERN TERRITORIES']),
        ('GA', ['GABON']),
        ('GM', ['GAMBIA']),
        ('GE', ['GEORGIA']),
        ('DE', ['GERMANY']),
        ('GH', ['GHANA']),
        ('GI', ['GIBRALTAR']),
        ('GR', ['GREECE']),
        ('GL', ['GREENLAND']),
        ('GD', ['GRENADA']),
        ('GP', ['GUADELOUPE']),
        ('GU', ['GUAM']),
        ('GT', ['GUATEMALA']),
        ('GG', ['GUERNSEY']),
        ('GN', ['GUINEA']),
        ('GW', ['GUINEA-BISSAU']),
        ('GY', ['GUYANA']),
        ('HT', ['HAITI']),
        ('HM', ['HEARD ISLAND AND MCDONALD MCDONALD ISLANDS']),
        ('VA', ['HOLY SEE (VATICAN CITY STATE)']),
        ('HN', ['HONDURAS']),
        ('HK', ['HONG KONG']),
        ('HU', ['HUNGARY']),
        ('IS', ['ICELAND']),
        ('IN', ['INDIA']),
        ('ID', ['INDONESIA']),
        ('IR', ['IRAN, ISLAMIC REPUBLIC OF']),
        ('IQ', ['IRAQ']),
        ('IE', ['IRELAND']),
        ('IM', ['ISLE OF MAN']),
        ('IL', ['ISRAEL']),
        ('IT', ['ITALY']),
        ('JM', ['JAMAICA']),
        ('JP', ['JAPAN']),
        ('JE', ['JERSEY']),
        ('JO', ['JORDAN']),
        ('KZ', ['KAZAKHSTAN']),
        ('KE', ['KENYA']),
        ('KI', ['KIRIBATI']),
        ('KP', ['KOREA, DEMOCRATIC PEOPLE\'S REPUBLIC OF']),
        ('KR', ['KOREA, REPUBLIC OF']),
        ('KW', ['KUWAIT']),
        ('KG', ['KYRGYZSTAN']),
        ('LA', ['LAO PEOPLE\'S DEMOCRATIC REPUBLIC']),
        ('LV', ['LATVIA']),
        ('LB', ['LEBANON']),
        ('LS', ['LESOTHO']),
        ('LR', ['LIBERIA']),
        ('LY', ['LIBYA']),
        ('LI', ['LIECHTENSTEIN']),
        ('LT', ['LITHUANIA']),
        ('LU', ['LUXEMBOURG']),
        ('MO', ['MACAO']),
        ('MK', ['MACEDONIA, THE FORMER YUGOSLAV REPUBLIC OF']),
        ('MG', ['MADAGASCAR']),
        ('MW', ['MALAWI']),
        ('MY', ['MALAYSIA']),
        ('MV', ['MALDIVES']),
        ('ML', ['MALI']),
        ('MT', ['MALTA']),
        ('MH', ['MARSHALL ISLANDS']),
        ('MQ', ['MARTINIQUE']),
        ('MR', ['MAURITANIA']),
        ('MU', ['MAURITIUS']),
        ('YT', ['MAYOTTE']),
        ('MX', ['MEXICO']),
        ('FM', ['MICRONESIA, FEDERATED STATES OF']),
        ('MD', ['MOLDOVA, REPUBLIC OF']),
        ('MC', ['MONACO']),
        ('MN', ['MONGOLIA']),
        ('ME', ['MONTENEGRO']),
        ('MS', ['MONTSERRAT']),
        ('MA', ['MOROCCO']),
        ('MZ', ['MOZAMBIQUE']),
        ('MM', ['MYANMAR']),
        ('NA', ['NAMIBIA']),
        ('NR', ['NAURU']),
        ('NP', ['NEPAL']),
        ('NL', ['NETHERLANDS']),
        ('NC', ['NEW CALEDONIA']),
        ('NZ', ['NEW ZEALAND']),
        ('NI', ['NICARAGUA']),
        ('NE', ['NIGER']),
        ('NG', ['NIGERIA']),
        ('NU', ['NIUE']),
        ('NF', ['NORFOLK ISLAND']),
        ('MP', ['NORTHERN MARIANA ISLANDS']),
        ('NO', ['NORWAY']),
        ('OM', ['OMAN']),
        ('PK', ['PAKISTAN']),
        ('PW', ['PALAU']),
        ('PS', ['PALESTINE, STATE OF']),
        ('PA', ['PANAMA']),
        ('PG', ['PAPUA NEW GUINEA']),
        ('PY', ['PARAGUAY']),
        ('PE', ['PERU']),
        ('PH', ['PHILIPPINES']),
        ('PN', ['PITCAIRN']),
        ('PL', ['POLAND']),
        ('PT', ['PORTUGAL']),
        ('PR', ['PUERTO RICO']),
        ('QA', ['QATAR']),
        ('RO', ['ROMANIA']),
        ('RU', ['RUSSIAN FEDERATION']),
        ('RW', ['RWANDA']),
        ('RE', ['REUNION']),
        ('BL', ['SAINT BARTHALEMY']),
        ('SH', ['SAINT HELENA']),
        ('KN', ['SAINT KITTS AND NEVIS']),
        ('LC', ['SAINT LUCIA']),
        ('MF', ['SAINT MARTIN (FRENCH PART)']),
        ('PM', ['SAINT PIERRE AND MIQUELON']),
        ('VC', ['SAINT VINCENT AND THE GRENADINES']),
        ('WS', ['SAMOA']),
        ('SM', ['SAN MARINO']),
        ('ST', ['SAO TOME AND PRINCIPE']),
        ('SA', ['SAUDI ARABIA']),
        ('SN', ['SENEGAL']),
        ('RS', ['SERBIA']),
        ('SC', ['SEYCHELLES']),
        ('SL', ['SIERRA LEONE']),
        ('SG', ['SINGAPORE']),
        ('SX', ['SINT MAARTEN (DUTCH PART)']),
        ('SK', ['SLOVAKIA']),
        ('SI', ['SLOVENIA']),
        ('SB', ['SOLOMON ISLANDS']),
        ('SO', ['SOMALIA']),
        ('ZA', ['SOUTH AFRICA']),
        ('GS', ['SOUTH GEORGIA AND THE SOUTH SANDWICH ISLANDS']),
        ('SS', ['SOUTH SUDAN']),
        ('ES', ['SPAIN']),
        ('LK', ['SRI LANKA']),
        ('SD', ['SUDAN']),
        ('SR', ['SURINAME']),
        ('SJ', ['SVALBARD AND JAN MAYEN']),
        ('SZ', ['SWAZILAND']),
        ('SE', ['SWEDEN']),
        ('CH', ['SWITZERLAND']),
        ('SY', ['SYRIAN ARAB REPUBLIC']),
        ('TW', ['TAIWAN, PROVINCE OF CHINA']),
        ('TJ', ['TAJIKISTAN']),
        ('TZ', ['UNITED REPUBLIC OF TANZANIA']),
        ('TH', ['THAILAND']),
        ('TL', ['TIMOR-LESTE']),
        ('TG', ['TOGO']),
        ('TK', ['TOKELAU']),
        ('TO', ['TONGA']),
        ('TT', ['TRINIDAD AND TOBAGO']),
        ('TN', ['TUNISIA']),
        ('TR', ['TURKEY']),
        ('TM', ['TURKMENISTAN']),
        ('TC', ['TURKS AND CAICOS ISLANDS']),
        ('TV', ['TUVALU']),
        ('UG', ['UGANDA']),
        ('UA', ['UKRAINE']),
        ('AE', ['UNITED ARAB EMIRATES']),
        ('GB', ['UNITED KINGDOM']),
        ('US', ['UNITED STATES']),
        ('UM', ['UNITED STATES MINOR OUTLYING ISLANDS']),
        ('UY', ['URUGUAY']),
        ('UZ', ['UZBEKISTAN']),
        ('VU', ['VANUATU']),
        ('VE', ['VENEZUELA']),
        ('VN', ['VIET NAM']),
        ('VG', ['BRITISH VIRGIN ISLANDS']),
        ('VI', ['US VIRGIN ISLANDS']),
        ('WF', ['WALLIS AND FUTUNA']),
        ('EH', ['WESTERN SAHARA']),
        ('YE', ['YEMEN']),
        ('ZM', ['ZAMBIA']),
        ('ZW', ['ZIMBABWE']),
        ('AX', ['ALAND ISLANDS'])
    ])

    numberRegex      = r"(\d+(?:,\d+)*)"
    alphaRegex       = r"[A-Z]"
    numberRangeRegex = r"{0} ?(?:[-&]|TO) ?{0}".format(
        numberRegex
    )
    numberAlphaRegex = r"{0} ?(?:{1})".format(
        numberRegex,
        alphaRegex
    )
    numberSlashRegex = r"{0} ?/ ?{0}".format(
        numberRegex
    )
    alphaNumberRegex = r"{1}{0}".format(
        numberRegex,
        alphaRegex
    )
    alphaNumberAlphaRegex = r"{1}{0}{1}".format(
        numberRegex,
        alphaRegex
    )
    slashAbbrvRegex  = r"{0}/{0}+".format(
        alphaRegex
    )
    singleNumberRegex= r"(%s)" % "|".join([
        numberAlphaRegex,
        numberRegex
    ])
    singleAlphaNumberRegex = r"(%s)" % "|".join([
        numberAlphaRegex,
        numberRegex,
        alphaRegex
    ])
    singleAlphaNumberAlphaRegex = r"(%s)" % "|".join([
        numberAlphaRegex,
        numberRegex,
        alphaNumberAlphaRegex,
        alphaRegex
    ])
    multiNumberRegex = r"(%s)" % "|".join([
        numberAlphaRegex,
        numberRangeRegex,
        numberRegex
    ])
    multiNumberSlashRegex = r"(%s)" % "|".join([
        numberAlphaRegex,
        numberRangeRegex,
        numberSlashRegex,
        numberRegex
    ])
    multiNumberAlphaRegex = r"(%s)" % "|".join([
        numberAlphaRegex,
        numberRangeRegex,
        numberRegex,
        alphaNumberRegex,
    ])
    multiAlphaNumberAlphaRegex = r"(%s)" % "|".join([
        numberAlphaRegex,
        numberRangeRegex,
        numberRegex,
        alphaNumberRegex,
        alphaNumberAlphaRegex,
    ])
    multiNumberAllRegex = r"(%s)" % "|".join([
        numberAlphaRegex,
        numberRangeRegex,
        numberSlashRegex,
        numberRegex,
        alphaNumberRegex,
    ])

    floorLevelRegex = r"(?:(?P<floor_prefix>FLOOR|LEVEL|LVL)\.? )?(?P<floor_type>%s)\.? ?(?P<floor_number>%s)" % (
        SanitationUtils.compileAbbrvRegex(floorAbbreviations),
        singleAlphaNumberRegex,
    )
    subunitTypeRegexNamed = "(?P<subunit_type>%s)" % (
        SanitationUtils.compileAbbrvRegex(subunitAbbreviations)
    )
    subunitRegex = r"(?P<subunit_type>%s) ?(?P<subunit_number>(?:%s)/?)" % (
        SanitationUtils.compileAbbrvRegex(subunitAbbreviations),
        multiAlphaNumberAlphaRegex,
    )
    weakSubunitRegex = r"(?P<weak_subunit_type>%s) ?(?P<weak_subunit_number>(?:%s)/?)" % (
        NameUtils.singleNameRegex,
        multiAlphaNumberAlphaRegex,
    )
    stateRegex = r"(%s)" % SanitationUtils.compileAbbrvRegex(stateAbbreviations)
    thoroughfareNameRegex = r"%s" % (
        "|".join([
            NameUtils.greedyMultiNameRegex,
            NameUtils.ordinalNumberRegex,
        ])
    )
    thoroughfareTypeRegex = r"%s" % (
        SanitationUtils.compileAbbrvRegex(thoroughfareTypeAbbreviations)
    )
    thoroughfareTypeRegexNamed = r"(?P<thoroughfare_type>%s)" % (
        SanitationUtils.compileAbbrvRegex(thoroughfareTypeAbbreviations)
    )
    thoroughfareSuffixRegex = r"%s" % (
        SanitationUtils.compileAbbrvRegex(thoroughfareSuffixAbbreviations)
    )
    thoroughfareRegex = r"(?P<thoroughfare_number>{0})\s+(?P<thoroughfare_name>{1})\s+(?P<thoroughfare_type>{2})\.?(?:\s+(?P<thoroughfare_suffix>{3}))?".format(
        multiNumberSlashRegex,
        thoroughfareNameRegex,
        thoroughfareTypeRegex,
        thoroughfareSuffixRegex
    )
    weakThoroughfareRegex = r"(?P<weak_thoroughfare_name>{0})\s+(?P<weak_thoroughfare_type>{1})\.?(?:\s+(?P<weak_thoroughfare_suffix>{2}))?".format(
        thoroughfareNameRegex,
        thoroughfareTypeRegex,
        thoroughfareSuffixRegex
    )
    buildingTypeRegex = r"(?P<building_type>{0}(\s{0})*)".format(
        SanitationUtils.compileAbbrvRegex(buildingTypeAbbreviations)
    )
    buildingRegex = r"(?P<building_name>{0})\s+{1}".format(
        NameUtils.lazyMultiNameRegex,
        buildingTypeRegex
    )
    deliveryTypeRegex = r"(?P<delivery_type>%s)" % (
        SanitationUtils.compileAbbrvRegex(deliveryTypeAbbreviations),
    )
    deliveryRegex = r"%s(?:\s*(?P<delivery_number>%s))?" % (
        deliveryTypeRegex,
        singleNumberRegex
    )
    countryRegex = r"(%s)" % SanitationUtils.compileAbbrvRegex(countryAbbreviations)

# [^,\s\d/()-]+
    addressTokenRegex = r"(%s)" % "|".join([
        SanitationUtils.wrapClearRegex( deliveryRegex),
        SanitationUtils.wrapClearRegex( floorLevelRegex),
        SanitationUtils.wrapClearRegex( subunitRegex),
        SanitationUtils.wrapClearRegex( thoroughfareRegex),
        SanitationUtils.wrapClearRegex( buildingRegex),
        SanitationUtils.wrapClearRegex( weakThoroughfareRegex),
        SanitationUtils.wrapClearRegex( weakSubunitRegex),
        # SanitationUtils.wrapClearRegex( stateRegex),
        SanitationUtils.wrapClearRegex( NameUtils.careOfRegex ),
        SanitationUtils.wrapClearRegex( NameUtils.organizationRegex ),
        SanitationUtils.wrapClearRegex( NameUtils.singleNameRegex),
        SanitationUtils.wrapClearRegex( multiNumberAllRegex),
        SanitationUtils.wrapClearRegex( slashAbbrvRegex),
        SanitationUtils.disallowedPunctuationRegex,

    ])

    @staticmethod
    def identifySubunit(string):
        return SanitationUtils.identifyAbbreviation(AddressUtils.subunitAbbreviations, string)

    @staticmethod
    def identifyFloor(string):
        return SanitationUtils.identifyAbbreviation(AddressUtils.floorAbbreviations, string)

    @staticmethod
    def identifyThoroughfareType(string):
        return SanitationUtils.identifyAbbreviation(AddressUtils.thoroughfareTypeAbbreviations, string)

    @staticmethod
    def identifyThoroughfareSuffix(string):
        return SanitationUtils.identifyAbbreviation(AddressUtils.thoroughfareSuffixAbbreviations, string)

    @staticmethod
    def identifyState(string):
        return SanitationUtils.identifyAbbreviation(AddressUtils.stateAbbreviations, string)

    @staticmethod
    def identifyBuildingType(string):
        return SanitationUtils.identifyAbbreviation(AddressUtils.buildingTypeAbbreviations, string)

    @staticmethod
    def identifyBuildingTypes(string):
        return SanitationUtils.identifyAbbreviations(AddressUtils.buildingTypeAbbreviations, string)

    @staticmethod
    def identifyDeliveryType(string):
        return SanitationUtils.identifyAbbreviation(AddressUtils.deliveryTypeAbbreviations, string)

    @staticmethod
    def identifyCountry(string):
        return SanitationUtils.identifyAbbreviation(AddressUtils.countryAbbreviations, string)

    @staticmethod
    def getFloor(token):
        match = re.match(
            SanitationUtils.wrapClearRegex(
                AddressUtils.floorLevelRegex
            ),
            token
        )
        matchDict = match.groupdict() if match else None
        if(matchDict):
            floor_type = AddressUtils.identifyFloor(matchDict.get('floor_type'))
            floor_number = matchDict.get('floor_number')
            if Registrar.DEBUG_ADDRESS: SanitationUtils.safePrint( "FOUND FLOOR", floor_type, floor_number)
            return floor_type, floor_number
        return None

    @staticmethod
    def getSubunitType(token):
        match = re.match(
            SanitationUtils.wrapClearRegex(
                AddressUtils.subunitTypeTypeRegexNamed
            ),
            token
        )
        matchDict = match.groupdict() if match else None
        if matchDict and matchDict.get('subunit_type'):
            subunit_type = AddressUtils.identifySubunitType(
                matchDict.get('subunit_type')
            )
            return subunit_type

    @staticmethod
    def getSubunit(token):
        match = re.match(
            SanitationUtils.wrapClearRegex(
                AddressUtils.subunitRegex
            ),
            token
        )
        matchDict = match.groupdict() if match else None
        if(matchDict and matchDict.get('subunit_type') and matchDict.get('subunit_number')):
            subunit_type = AddressUtils.identifySubunit(matchDict.get('subunit_type'))
            subunit_number = matchDict.get('subunit_number')
            subunit = (subunit_type, subunit_number)
            if Registrar.DEBUG_ADDRESS:  SanitationUtils.safePrint("FOUND SUBUNIT", subunit)
            return subunit
        return None

    @staticmethod
    def getWeakSubunit(token):
        match = re.match(
            SanitationUtils.wrapClearRegex(
                AddressUtils.weakSubunitRegex
            ),
            token
        )
        matchDict = match.groupdict() if match else None
        if(matchDict and matchDict.get('weak_subunit_type') and matchDict.get('weak_subunit_number')):
            subunit_type = AddressUtils.identifySubunit(matchDict.get('weak_subunit_type'))
            subunit_number = matchDict.get('weak_subunit_number')
            subunit = (subunit_type, subunit_number)
            if Registrar.DEBUG_ADDRESS:  SanitationUtils.safePrint("FOUND WEAK SUBUNIT", subunit)
            return subunit
        return None

    @staticmethod
    def getThoroughfareType(token):
        match = re.match(
            SanitationUtils.wrapClearRegex(
                AddressUtils.thoroughfareTypeRegexNamed
            ),
            token
        )
        matchDict = match.groupdict() if match else None
        if matchDict and matchDict.get('thoroughfare_type'):
            thoroughfare_type = AddressUtils.identifyThoroughfareType(
                matchDict.get('thoroughfare_type')
            )
            return thoroughfare_type

    @staticmethod
    def getThoroughfare(token):
        match = re.match(
            SanitationUtils.wrapClearRegex(
                AddressUtils.thoroughfareRegex
            ),
            token
        )
        matchDict = match.groupdict() if match else None
        if(matchDict and matchDict.get('thoroughfare_name') and matchDict.get('thoroughfare_type')):
            thoroughfare_name = matchDict.get('thoroughfare_name')
            thoroughfare_type = AddressUtils.identifyThoroughfareType(
                matchDict.get('thoroughfare_type')
            )
            thoroughfare_suffix = AddressUtils.identifyThoroughfareSuffix(
                matchDict.get('thoroughfare_suffix')
            )
            thoroughfare_number = matchDict.get('thoroughfare_number')
            if Registrar.DEBUG_ADDRESS: SanitationUtils.safePrint(
                "FOUND THOROUGHFARE",
                thoroughfare_number,
                thoroughfare_name,
                thoroughfare_type,
                thoroughfare_suffix
            )
            return thoroughfare_number, thoroughfare_name, thoroughfare_type, thoroughfare_suffix
        return None

    @staticmethod
    def getBuilding(token):
        match = re.match(
            SanitationUtils.wrapClearRegex(
                AddressUtils.buildingRegex
            ),
            token
        )
        matchDict = match.groupdict() if match else None
        if(matchDict):
            # print matchDict
            building_name = matchDict.get('building_name')
            building_type = ''.join(AddressUtils.identifyBuildingTypes(
                matchDict.get('building_type')
            ))
            if Registrar.DEBUG_ADDRESS: SanitationUtils.safePrint(
                "FOUND BUILDING",
                building_name,
                building_type
            )
            return building_name, building_type

    @staticmethod
    def getWeakThoroughfare(token):
        match = re.match(
            SanitationUtils.wrapClearRegex(
                AddressUtils.weakThoroughfareRegex
            ),
            token
        )
        matchDict = match.groupdict() if match else None
        if(matchDict and matchDict.get('weak_thoroughfare_name') and matchDict.get('weak_thoroughfare_type')):
            # print matchDict
            weak_thoroughfare_name = matchDict.get('weak_thoroughfare_name')
            weak_thoroughfare_type = matchDict.get('weak_thoroughfare_type')
            # weak_thoroughfare_type = AddressUtils.identifyThoroughfareType(
            #     matchDict.get('weak_thoroughfare_type')
            # )
            weak_thoroughfare_suffix = AddressUtils.identifyThoroughfareSuffix(
                matchDict.get('weak_thoroughfare_suffix')
            )

            if Registrar.DEBUG_ADDRESS: print "FOUND WEAK THOROUGHFARE %s | %s (%s)" % (
                weak_thoroughfare_name,
                weak_thoroughfare_type,
                weak_thoroughfare_suffix
            )
            return weak_thoroughfare_name, weak_thoroughfare_type, weak_thoroughfare_suffix

    @staticmethod
    def getState(token):
        match = re.match(
            SanitationUtils.wrapClearRegex(
                AddressUtils.stateRegex
            ),
            token
        )
        matchDict = match.groupdict() if match else None
        if(matchDict and matchDict.get('state_name')):
            state_name = matchDict.get('state_name')
            if Registrar.DEBUG_ADDRESS: SanitationUtils.safePrint( "FOUND STATE ", state_name)
            return state_name

    @staticmethod
    def getDelivery(token):
        match = re.match(
            SanitationUtils.wrapClearRegex(
                AddressUtils.deliveryRegex
            ),
            token
        )
        matchDict = match.groupdict() if match else None
        if(matchDict):
            delivery_type = AddressUtils.identifyDeliveryType(matchDict.get('delivery_type'))
            delivery_number = matchDict.get('delivery_number')
            if Registrar.DEBUG_ADDRESS: SanitationUtils.safePrint( "FOUND DELIVERY ", delivery_type, delivery_number)
            return delivery_type, delivery_number

    @staticmethod
    def getNumber(token):
        match = re.match(
            SanitationUtils.wrapClearRegex(
                AddressUtils.multiNumberAllRegex
            ),
            token
        )
        matchGrps = match.groups() if match else None
        if(matchGrps):
            number = matchGrps[0]
            if Registrar.DEBUG_ADDRESS: SanitationUtils.safePrint( "FOUND NUMBER ", repr(number))
            number = SanitationUtils.stripAllWhitespace( number )
            return number

    @staticmethod
    def getSingleNumber(token):
        match = re.match(
                "(" + AddressUtils.numberRegex + ")"
            ,
            token
        )
        matchGrps = match.groups() if match else None
        if(matchGrps):
            number = matchGrps[0]
            if Registrar.DEBUG_ADDRESS: SanitationUtils.safePrint( "FOUND SINGLE NUMBER ", repr(number))
            number = SanitationUtils.stripAllWhitespace( number )
            return number

    @staticmethod
    def findSingleNumber(token):
        match = re.search(
                "(" + AddressUtils.numberRegex + ")"
            ,
            token
        )
        matchGrps = match.groups() if match else None
        if(matchGrps):
            number = matchGrps[0]
            if Registrar.DEBUG_ADDRESS: SanitationUtils.safePrint( "FOUND SINGLE NUMBER ", repr(number))
            number = SanitationUtils.stripAllWhitespace( number )
            return number

    @staticmethod
    def sanitizeState(string):
        return SanitationUtils.compose(
            SanitationUtils.stripLeadingWhitespace,
            SanitationUtils.stripTailingWhitespace,
            SanitationUtils.stripExtraWhitespace,
            SanitationUtils.stripPunctuation,
            SanitationUtils.toUpper
        )(string)

    @staticmethod
    def sanitizeAddressToken(string):
        string = SanitationUtils.stripExtraWhitespace(string)
        string = re.sub(AddressUtils.numberAlphaRegex + SanitationUtils.clearStartRegex , r'\1\2', string)
        string = re.sub(AddressUtils.numberRangeRegex, r'\1-\2', string)
        if Registrar.DEBUG_UTILS: SanitationUtils.safePrint( "sanitizeAddressToken", string)
        return string

    @staticmethod
    def tokenizeAddress(string):
        # if Registrar.DEBUG_ADDRESS:
        #     SanitationUtils.safePrint("in tokenizeAddress")
        matches =  re.findall(
            AddressUtils.addressTokenRegex,
            string.upper()
        )
        # if Registrar.DEBUG_ADDRESS:
        #     for match in matches:
        #         print repr(match)
        return map(
            lambda match: AddressUtils.sanitizeAddressToken(match[0]),
            matches
        )

    @staticmethod
    def addressRemoveEndWord(string, word):
        string_layout = AddressUtils.tokenizeAddress(string)
        word_layout = AddressUtils.tokenizeAddress(word)
        if not(word_layout and string_layout): return string
        for i, word in enumerate(reversed(word_layout)):
            if( 1 + i > len(word_layout)) or word != string_layout[-1-i]:
                return string
        return " ".join(string_layout[:-len(word_layout)])

    @staticmethod
    def extractShop(address):
        match = re.match(AddressUtils.shopRegex, address)
        matchDict = match.groupdict()
        if(matchDict):
            number = matchDict.get('number', None)
            rest = matchDict.get('rest', None)
            if(number):
                return number, rest
        return None, address

def testAddressUtils():
    # SanitationUtils.clearStartRegex = "<START>"
    # SanitationUtils.clearFinishRegex = "<FINISH>"
    # print repr(AddressUtils.addressTokenRegex)

    # print AddressUtils.addressRemoveEndWord("WEST AUSTRALIA", "WEST AUSTRALIA")

    # print AddressUtils.addressRemoveEndWord("SHOP 7 KENWICK SHOPNG CNTR BELMONT RD, KENWICK WA (", "KENWICK WA")
    # print SanitationUtils.unicodeToByte(u"\u00FC ASD")
    # print "addressTokenRegex", AddressUtils.addressTokenRegex
    # print "thoroughfareRegex", AddressUtils.thoroughfareRegex
    # print "subunitRegex", AddressUtils.subunitRegex
    # print "floorLevelRegex", AddressUtils.floorLevelRegex
    # print "stateRegex", AddressUtils.stateRegex
    # print "delimeterRegex", AddressUtils.delimeterRegex

    # print AddressUtils.getSubunit("SHOP 4 A")
    # print AddressUtils.getFloor("LEVEL 8")
    print AddressUtils.tokenizeAddress("BROADWAY FAIR SHOPPING CTR")
    print AddressUtils.getBuilding("BROADWAY FAIR SHOPPING CTR")
    print AddressUtils.getBuilding("BROADWAY FAIR SHOPPING")
    print NameUtils.getMultiName("BROADWAY")




class TimeUtils:
    wpSrvOffset = 0
    actSrvOffset = 0

    dateFormat = "%Y-%m-%d"
    wpTimeFormat = "%Y-%m-%d %H:%M:%S"
    msTimeFormat = "%Y-%m-%d_%H-%M-%S"
    actTimeFormat = "%d/%m/%Y %I:%M:%S %p"
    gDriveTimeFormat = "%Y-%m-%d %H:%M:%S"

    @staticmethod
    def starStrptime(string, fmt = wpTimeFormat ):
        string = SanitationUtils.coerceUnicode(string)
        if(string):
            try:
                tstruct = time.strptime(string, fmt)
                if(tstruct):
                    return time.mktime(tstruct)
            except:
                pass
        return 0

    @classmethod
    def setWpSrvOffset(_class, offset):
        _class.wpSrvOffset = offset

    @staticmethod
    def actStrptime(string):
        return TimeUtils.starStrptime(string, TimeUtils.actTimeFormat)

    # 2015-07-13 22:33:05
    @staticmethod
    def wpStrptime(string):
        return TimeUtils.starStrptime(string)

    @staticmethod
    def gDriveStrpTime(string):
        return TimeUtils.starStrptime(string, TimeUtils.gDriveTimeFormat)

    @staticmethod
    def wpTimeToString(t, fmt = wpTimeFormat):
        return time.strftime(fmt, time.localtime(t))

    @staticmethod
    def hasHappenedYet(t):
        assert isinstance(t, (int, float)), "param must be an int not %s"% type(t)
        return t >= time.time()

    @staticmethod
    def localToServerTime(t, timezoneOffset = time.timezone):
        return int(t - timezoneOffset)

    @staticmethod
    def serverToLocalTime(t, timezoneOffset = time.timezone):
        return int(t + timezoneOffset)

    @staticmethod
    def wpServerToLocalTime(t):
        return TimeUtils.serverToLocalTime(t, TimeUtils.wpSrvOffset)

    @staticmethod
    def actServerToLocalTime(t):
        return TimeUtils.serverToLocalTime(t, TimeUtils.actSrvOffset)

    @staticmethod
    def getDateStamp():
        return time.strftime(TimeUtils.dateFormat)

    @staticmethod
    def getMsTimeStamp():
        return time.strftime(TimeUtils.msTimeFormat)

    @staticmethod
    def getTimeStamp():
        return time.strftime(TimeUtils.wpTimeFormat)



def testTimeUtils():
    TimeUtils.setWpSrvOffset(-7200)
    inTime = "2016-05-06 16:07:00"
    print TimeUtils.wpStrptime(inTime)
    print TimeUtils.wpTimeToString(TimeUtils.wpStrptime(inTime))
    print TimeUtils.wpTimeToString(TimeUtils.wpServerToLocalTime(TimeUtils.wpStrptime(inTime)))

    # gTime = TimeUtils.gDriveStrpTime("14/02/2016")
    # print "gTime", gTime
    # sTime = TimeUtils.localToServerTime(gTime)
    # print "sTime", sTime

    # print TimeUtils.wpTimeToString(1455379200)

    # t1 = TimeUtils.actStrptime("29/08/2014 9:45:08 AM")
    # t2 = TimeUtils.actStrptime("26/10/2015 11:08:31 AM")
    # t3 = TimeUtils.wpStrptime("2015-07-13 22:33:05")
    # t4 = TimeUtils.wpStrptime("2015-12-18 16:03:37")
    # print [
    #     (t1, TimeUtils.wpTimeToString(t1)),
    #     (t2, TimeUtils.wpTimeToString(t2)),
    #     (t3, TimeUtils.wpTimeToString(t3)),
    #     (t4, TimeUtils.wpTimeToString(t4))
    # ]

class HtmlReporter(object):
    """docstring for htmlReporter"""

    class Section:
        data_heading_fmt = "<h3>%s</h3>"
        data_separater = "<hr>"

        def __init__(self, classname, title = None, description = "", data = "", length = None):
            if title is None: title = classname.title()
            self.title = title
            self.description = description
            self.data = data
            self.length = length
            self.classname = classname

        def toHtml(self):
            sectionID = SanitationUtils.makeSafeClass(self.classname)
            out  = '<div class="section">'
            out += '<a data-toggle="collapse" href="#{0}" aria-expanded="true" data-target="#{0}" aria-controls="{0}">'.format(sectionID)
            out += '<h2>' + self.title + (' ({})'.format(self.length) if self.length else '') + '</h2>'
            out += '</a>'
            out += '<div class="collapse" id="' + sectionID + '">'
            out += '<p class="description">' + (str(self.length) if self.length else "No") + ' ' + self.description + '</p>'
            out += '<p class="data">'
            out += re.sub("<table>","<table class=\"table table-striped\">",SanitationUtils.coerceUnicode(self.data))
            out += '</p>'
            out += '</div>'
            out = SanitationUtils.coerceUnicode( out )
            return out


    class Group:
        def __init__(self, classname, title = None, sections = None):
            if title is None: title = classname.title()
            if sections is None: sections = OrderedDict()
            self.title = title
            self.sections = sections
            self.classname = classname

        def addSection(self, section):
            self.sections[section.classname] = section

        def toHtml(self):
            out  = '<div class="group">'
            out += '<h1>' + self.title + '</h1>'
            for section in self.sections.values():
                out += section.toHtml()
            out += '</div>'
            out = SanitationUtils.coerceUnicode( out )
            return out

    groups = OrderedDict()

    def __init__(self):
        pass

    def addGroup( self, group):
        self.groups[group.classname] = group

    def getHead(self):
        return """\
<head>
    <meta charset="UTF-8">
    <!-- Latest compiled and minified CSS -->
    <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.6/css/bootstrap.min.css" integrity="sha384-1q8mTJOASx8j1Au+a5WDVnPi2lkFfwwEAa8hDDdjZlpLegxhjVME1fgjWPGmkzs7" crossorigin="anonymous">

    <!-- Optional theme -->
    <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.6/css/bootstrap-theme.min.css" integrity="sha384-fLW2N01lMqjakBkx3l/M9EahuwpSfeNvV63J5ezn3uZzapT0u7EYsXMjQV+0En5r" crossorigin="anonymous">
</head>
"""

    def getBody(self):
        content = "<br/>".join(
            group.toHtml() for group in self.groups.values()
        )
        out = """
<body>
""" + content + """
    <script src="https://ajax.googleapis.com/ajax/libs/jquery/2.1.4/jquery.min.js"></script>
    <script src="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.6/js/bootstrap.min.js" integrity="sha384-0mSbJDEHialfmuBBQP6A4Qrprq5OVfW37PRR3j5ELqxss1yVqOtnepnHVP9aJ7xS" crossorigin="anonymous"></script>
</body>
"""
        out = SanitationUtils.coerceUnicode( out )
        return out

    def getDocument(self):
        head = self.getHead()
        body = self.getBody()
        out = """\
<!DOCTYPE html>
<html lang="en">
""" + head + """"
""" + body + """
</html>
"""
        out = SanitationUtils.coerceUnicode( out )
        return out

    def getDocumentUnicode(self):
        return SanitationUtils.coerceUnicode( self.getDocument() )

def testHTMLReporter():
    with\
             open('../output/htmlReporterTest.html', 'w+') as resFile,\
             io.open('../output/htmlReporterTestU.html', 'w+', encoding="utf8") as uresFile :
        reporter = HtmlReporter()

        matchingGroup = HtmlReporter.Group('matching', 'Matching Results')

        matchingGroup.addSection(
            HtmlReporter.Section(
                'perfect_matches',
                **{
                    'title': 'Perfect Matches',
                    'description': "%s records match well with %s" % ("WP", "ACT"),
                    'data': u"<\U0001F44C'&>",
                    'length': 3
                }
            )
        )

        reporter.addGroup(matchingGroup)

        document = reporter.getDocument()
        # SanitationUtils.safePrint( document)
        uresFile.write( SanitationUtils.coerceUnicode(document))
        resFile.write( SanitationUtils.coerceAscii(document) )


class descriptorUtils:
    @staticmethod
    def safeKeyProperty(key):
        def getter(self):
            assert key in self.keys(), "{} must be set before get in {}".format(key, repr(type(self)))
            return self[key]

        def setter(self, value):
            assert isinstance(value, (str, unicode)), "{} must be set with string not {}".format(key, type(value))
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

class InheritenceUtils:
    @classmethod
    def gcs(cls, *instances):
        """
        Taken from http://stackoverflow.com/questions/25786566/greatest-common-superclass
        """
        # try:
        if len(instances) > 1:
            class_sets = [set([type(instance)]) for instance in instances]
            while not set.intersection(*class_sets):
                set_lengths = map(len, class_sets)
                for i in range(len(class_sets)):
                    additions = []
                    for _class in class_sets[i]:
                        additions.extend(_class.__bases__)
                    # Registrar.registerMessage("additions: %s" % additions)
                    if additions:
                        class_sets[i].update(set(additions))
                if set_lengths == map(len, class_sets):
                    return None
            return list(set.intersection(*class_sets))[0]
            # classes = [type(x).mro() for x in instances]
            # if classes:
            #     for x in classes.pop():
            #         if x == object:
            #             continue
            #         if all(x in mro for mro in classes):
            #             return x
            # assert False, "no common match found for %s" % str([type(x) for x in instances])
        elif len(instances) == 1:
            return type(instances[0])
        else:
            return None
        # except AssertionError, e:
        #     Registrar.registerError(e)
        #     raise e
        #     return None



class listUtils:
    @staticmethod
    def combineLists(a, b):
        """
            Combines lists a and b uniquely, attempting to preserve order
        """
        if not a:
            return b if b else []
        if not b: return a
        c = []
        for element in a + b:
            if element not in c:
                c.append(element)
        return c

    @staticmethod
    def combineOrderedDicts(a, b):
        """
            Combines OrderedDict a with b by starting with A and overwriting with items from b.
            Attempts to preserve order
        """
        if not a:
            return b if b else OrderedDict()
        if not b: return a
        c = OrderedDict(a.items())
        for key, value in b.items():
            c[key] = value
        return c

    @staticmethod
    def filterUniqueTrue(a):
        b = []
        for i in a:
            if i and i not in b:
                b.append(i)
        return b

    @staticmethod
    def getAllkeys(*args):
        return listUtils.filterUniqueTrue(itertools.chain( *(
            arg.keys() for arg in args if isinstance(arg, dict)
        )))

    @staticmethod
    def keysNotIn(dictionary, keys):
        assert isinstance(dictionary, dict)
        return type(dictionary)([ \
            (key, value) for key, value in dictionary.items()\
            if key not in keys
        ])

    @staticmethod
    def checkEqual(iterator):
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
            basename = 'source/'+os.path.basename(path)
            line = inspect.stack()[level][2]
            baseline = "%s:%s" % (basename, line)
            return ".".join([baseline,str(procedure)])
        except:
            return None

    @classmethod
    def getCallerProcedure(cls, level=0):
        return cls.getProcedure(3+level)

    @classmethod
    def getCallerProcedures(cls, levels=2):
        procedures = map(cls.getCallerProcedure, range(1,levels+1))
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

    # def __init__(self):
        # self.objectIndexer = id
        # self.conflictResolver = self.passiveResolver
        # self.Registrar.DEBUG_ERROR = True
        # self.Registrar.DEBUG_WARN = False
        # self.Registrar.DEBUG_MESSAGE = False

    @classmethod
    def conflictResolver(self, *args):
        pass

    def resolveConflict(self, new, old, index, registerName = ''):
        self.registerError("Object [index: %s] already exists in register %s"%(index, registerName))

    @classmethod
    def getObjectRowcount(cls, objectData):
        return objectData.rowcount

    @classmethod
    def getObjectIndex(cls, objectData):
        if hasattr(objectData, 'index'):
            return objectData.index
        else:
            raise UserWarning('object is not indexable')

    @classmethod
    def passiveResolver(cls, *args):
        pass

    @classmethod
    def exceptionResolver(cls, new, old, index, registerName = ''):
        raise Exception("could not register %s in %s. \nDuplicate index: %s" % (str(new), registerName, index) )

    @classmethod
    def duplicateObjectExceptionResolver(cls, new, old, index, registerName=''):
        assert hasattr(new, 'rowcount'), 'new object type: %s should have a .rowcount attr' % type(new)
        assert hasattr(old, 'rowcount'), 'old object type: %s should have a .rowcount attr' % type(old)
        raise Exception("could not register %s in %s. \nDuplicate index: %s appears in rowcounts %s and %s" % (str(new), registerName, index, new.rowcount, old.rowcount) )


    def warningResolver(self, new, old, index, registerName = ''):
        try:
            self.exceptionResolver(new, old, index, registerName)
        except Exception as e:
            self.registerError(e, new )

    @classmethod
    def stringAnything(self, index, thing, delimeter='|'):
        return SanitationUtils.coerceBytes( u"%50s %s %s" % (index, delimeter, thing) )

    @classmethod
    def printAnything(self, index, thing, delimeter):
        print Registrar.stringAnything(index, thing, delimeter)

    @classmethod
    def registerAnything(self, thing, register, indexer = None, resolver = None, \
                         singular = True, unique=True, registerName = ''):
        if resolver is None: resolver = self.conflictResolver
        if indexer is None: indexer = self.objectIndexer
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
        except AssertionError as e:
            name = thing.__name__ if hasattr(thing, '__name__') else repr(indexer)
            raise Exception("Indexer [%s] produced invalid index: %s | %s" % (name, repr(index), str(e)))
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
            index = debugUtils.getCallerProcedures()
        error_string = SanitationUtils.coerceUnicode(error)
        if self.DEBUG_ERROR: Registrar.printAnything(index, error_string, '!')
        self.registerAnything(
            error_string,
            Registrar.errors,
            index,
            singular = False,
            registerName = 'errors'
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
            index = debugUtils.getCallerProcedures()
        error_string = SanitationUtils.coerceUnicode(message)
        if self.DEBUG_WARN: Registrar.printAnything(index, error_string, '|')
        self.registerAnything(
            error_string,
            Registrar.warnings,
            index,
            singular = False,
            registerName = 'warnings'
        )

    @classmethod
    def registerMessage(self, message, source=None):
        if source is None:
            source = debugUtils.getCallerProcedures()
        if self.DEBUG_MESSAGE: Registrar.printAnything(source, message, '~')
        self.registerAnything(
            message,
            Registrar.messages,
            source,
            singular = False,
            registerName = 'messages'
        )

    @classmethod
    def registerProgress(self, message):
        if self.DEBUG_PROGRESS:
            print debugUtils.hashify(message)

    @classmethod
    def getMessageItems(self, verbosity=0):
        items = self.errors
        if verbosity > 0:
            items = listUtils.combineOrderedDicts(items, self.warnings)
        if verbosity > 1:
            items = listUtils.combineOrderedDicts(items, self.messages)
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
            line = "(%3d%%) %10d of %10d items processed" % (percentage, count, self.total)
            if percentage > 1 and percentage < 100:
                time_elapsed = self.last_print - self.first_print
                ratio = (float(self.total) / (count) - 1.0)
                time_remaining = float(time_elapsed) * ratio
                # line += " | elapsesd: %3f | ratio: %3f" % (time_elapsed, ratio )
                line += " | remaining: %3d seconds" % int(time_remaining)
            if self.printCount > 0:
                line = "\r%s\r" % line
            sys.stdout.write( line )
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

class FileUtils(object):
    @classmethod
    def getFileName(cls, path):
        fileName, ext = os.path.splitext(os.path.basename(path))
        return fileName


if __name__ == '__main__':
    pass
    # testHTMLReporter()
    # testTimeUtils()
    # testSanitationUtils()
    # testUnicodeWriter()
    # testAddressUtils()
    # testNameUtils()
