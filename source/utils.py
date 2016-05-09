# -*- coding: utf-8 -*-
import functools
import itertools
# from itertools import chain
import re
import time
# import datetime
import inspect
import json
from collections import OrderedDict
import codecs
import unicodecsv
import cStringIO
from uniqid import uniqid
from phpserialize import dumps, loads
from kitchen.text import converters
import io
import base64

DEFAULT_ENCODING = 'utf8'

DEBUG = False
DEBUG_ADDRESS = False
# DEBUG_ADDRESS = True
DEBUG_MESSAGE = False
# DEBUG_MESSAGE = True
DEBUG_ERROR = False
# DEBUG_ERROR = True
DEBUG_WARN = False
# DEBUG_WARN = True
DEBUG_NAME = False
# DEBUG_NAME = True

class SanitationUtils:
    email_regex = r"[\w.+-]+@[\w-]+\.[\w.-]+"
    cell_email_regex = r"^%s$" % email_regex
    myobid_regex = r"C\d+"
    punctuationChars = [
        '!', '"', '#', '$', '%', 
        '&', '\'', '(', ')', '*', 
        '+', ',', '\-', '.', '/', 
        ':', ';', '<', '=', '>', 
        '?', '@', '[', '\\\\', '\\]', 
        '^', '_', '`', '{', '|', '}', '~'
    ]
    allowedPunctuation = [
        '\\-', '.', '\''
    ]
    disallowedPunctuation = list(set(punctuationChars) - set(allowedPunctuation))
    whitespaceChars = [ ' ', '\t', '\r', '\n', '\f']
    tokenDelimeters  =  list(set([ r"\d"] + disallowedPunctuation + whitespaceChars)) #delimeter characters incl space
    tokenPunctuationDelimeters = list(set([r"\d"] + punctuationChars + whitespaceChars))
    tokenDelimetersNoSpace  = [ r"\d"] + list(set(disallowedPunctuation + whitespaceChars) - set([' '])) #delimeter characters excl space
    punctuationRegex = r"[%s]" % "".join(punctuationChars) 
    delimeterRegex   = r"[%s]" % "".join(tokenDelimeters) 
    nondelimeterRegex = r"[^%s]" % "".join(tokenDelimeters) 
    nondelimeterPunctuationRegex = r"[^%s]" % "".join(tokenPunctuationDelimeters) 
    nondelimeterAndSpaceRegex = r"[^%s]" % "".join(tokenDelimetersNoSpace)
    disallowedPunctuationRegex = r"[%s]" % "".join(disallowedPunctuation)
    clearStartRegex  = r"(?<!%s)" % nondelimeterRegex
    clearFinishRegex = r"(?!%s)" % nondelimeterRegex

    @staticmethod
    def wrapClearRegex(regex):
        return SanitationUtils.clearStartRegex + regex + SanitationUtils.clearFinishRegex

    @staticmethod
    def identifyAbbreviation(abbrvDict, string):
        for abbrvKey, abbrvs in abbrvDict.items():
            if( string in [abbrvKey] + abbrvs):
                return abbrvKey
        return string        

    @staticmethod
    def compilePartialAbbrvRegex( abbrvKey, abbrvs ):
        return "|".join(filter(None,[
            "|".join(filter(None,abbrvs)),
            abbrvKey
        ]))

    @staticmethod
    def compileAbbrvRegex( abbrv ):
        return "|".join(filter(None,
            [SanitationUtils.compilePartialAbbrvRegex(abbrvKey, abbrvValue) for abbrvKey, abbrvValue in abbrv.items()]
        ))

    @staticmethod
    def compose(*functions):
        return functools.reduce(lambda f, g: lambda x: f(g(x)), functions)

    # Functions for dealing with string encodings

    @staticmethod
    def unicodeToUTF8(u_str):
        assert isinstance(u_str, unicode), "parameter should be unicode not %s" % type(u_str)
        byte_return = converters.to_bytes(u_str, "utf8")
        assert isinstance(byte_return, str), "something went wrong, should return str not %s" % type(byte_return)
        return byte_return

    @staticmethod
    def unicodeToAscii(u_str):
        assert isinstance(u_str, unicode), "parameter should be unicode not %s" % type(u_str)
        byte_return = converters.to_bytes(u_str, "ascii", "backslashreplace")
        assert isinstance(byte_return, str), "something went wrong, should return str not %s" % type(byte_return)
        return byte_return

    @staticmethod
    def unicodeToXml(u_str, ascii_only = False):
        assert isinstance(u_str, unicode), "parameter should be unicode not %s" % type(u_str)
        if ascii_only:
            byte_return = converters.unicode_to_xml(u_str, encoding="ascii")
        else:
            byte_return = converters.unicode_to_xml(u_str)
        assert isinstance(byte_return, str), "something went wrong, should return str not %s" % type(byte_return)
        return byte_return

    @staticmethod
    def utf8ToUnicode(utf8_str):
        assert isinstance(utf8_str, str), "parameter should be str not %s" % type(utf8_str)
        byte_return = converters.to_unicode(utf8_str, "utf8")
        assert isinstance(byte_return, unicode), "something went wrong, should return unicode not %s" % type(byte_return)
        return byte_return

    @staticmethod
    def xmlToUnicode(utf8_str):
        assert isinstance(utf8_str, str), "parameter should be str not %s" % type(utf8_str)
        byte_return = converters.xml_to_unicode(utf8_str)
        assert isinstance(byte_return, str), "something went wrong, should return str not %s" % type(byte_return)
        return byte_return

    @staticmethod
    def asciiToUnicode(ascii_str):
        assert isinstance(ascii_str, str), "parameter should be str not %s" % type(ascii_str)
        unicode_return = converters.to_unicode(ascii_str, "ascii")
        assert isinstance(unicode_return, unicode), "something went wrong, should return unicode not %s" % type(unicode_return)
        return unicode_return

    @staticmethod
    def coerceUnicode(thing):
        if thing is None:
            unicode_return = u""
        else:
            unicode_return = converters.to_unicode(thing, encoding="utf8")
        assert isinstance(unicode_return, unicode), "something went wrong, should return unicode not %s" % type(unicode_return)
        return unicode_return

    @staticmethod
    def coerceBytes(thing):
        byte_return = SanitationUtils.compose(
            SanitationUtils.unicodeToUTF8,
            SanitationUtils.coerceUnicode
        )(thing)
        assert isinstance(byte_return, str), "something went wrong, should return str not %s" % type(byte_return)
        return byte_return

    @staticmethod
    def coerceAscii(thing):
        byte_return = SanitationUtils.compose(
            SanitationUtils.unicodeToAscii,
            SanitationUtils.coerceUnicode
        )(thing)
        assert isinstance(byte_return, str), "something went wrong, should return str not %s" % type(byte_return)
        return byte_return

    @staticmethod
    def coerceXML(thing):
        byte_return = SanitationUtils.compose(
            SanitationUtils.unicodeToXml,
            SanitationUtils.coerceUnicode
        )(thing)
        assert isinstance(byte_return, str), "something went wrong, should return str not %s" % type(byte_return)
        return byte_return

    @staticmethod
    def sanitizeForTable(thing):
        unicode_return = SanitationUtils.compose(
            SanitationUtils.coerceUnicode,
            SanitationUtils.escapeNewlines,
            SanitationUtils.coerceUnicode
        )(thing)
        assert isinstance(unicode_return, unicode), "something went wrong, should return unicode not %s" % type(unicode_return)
        return unicode_return

    @staticmethod
    def sanitizeForXml(thing):
        unicode_return = SanitationUtils.compose(
            SanitationUtils.coerceUnicode,
            SanitationUtils.sanitizeNewlines,
            SanitationUtils.unicodeToXml,
            SanitationUtils.coerceUnicode
        )(thing)
        assert isinstance(unicode_return, unicode), "something went wrong, should return unicode not %s" % type(unicode_return)
        return unicode_return

    @staticmethod
    def safePrint(*args):
        print " ".join([SanitationUtils.coerceBytes(arg) for arg in args ])

    @staticmethod
    def normalizeVal(thing):
        unicode_return = SanitationUtils.compose(
            SanitationUtils.coerceUnicode,
            SanitationUtils.toUpper,
            SanitationUtils.stripLeadingWhitespace,
            SanitationUtils.stripTailingWhitespace,
            SanitationUtils.stripExtraWhitespace,
            SanitationUtils.coerceUnicode
        )(thing)
        assert isinstance(unicode_return, unicode), "something went wrong, should return unicode not %s" % type(unicode_return)
        return unicode_return

    @staticmethod
    def removeLeadingDollarWhiteSpace(string):
        str_out = re.sub('^\W*\$','', string)
        if DEBUG: print "removeLeadingDollarWhiteSpace", repr(string), repr(str_out)
        return str_out

    @staticmethod
    def removeLeadingPercentWhiteSpace(string):
        str_out = re.sub('%\W*$','', string)
        if DEBUG: print "removeLeadingPercentWhiteSpace", repr(string), repr(str_out)
        return str_out

    @staticmethod
    def removeLoneDashes(string):
        str_out = re.sub('^-$', '', string)
        if DEBUG: print "removeLoneDashes", repr(string), repr(str_out)
        return str_out

    @staticmethod
    def removeThousandsSeparator(string):
        str_out = re.sub(r'(\d+),(\d{3})', '\g<1>\g<2>', string)
        if DEBUG: print "removeThousandsSeparator", repr(string), repr(str_out)
        return str_out

    @staticmethod
    def removeLoneWhiteSpace(string):
        str_out = re.sub(r'^\s*$','', string)    
        if DEBUG: print "removeLoneWhiteSpace", repr(string), repr(str_out)
        return str_out

    @staticmethod
    def removeNULL(string):
        str_out = re.sub(r'^NULL$', '', string)
        if DEBUG: print "removeNULL", repr(string), repr(str_out)
        return str_out

    @staticmethod
    def stripLeadingWhitespace(string):
        str_out = re.sub(r'^\s*', '', string)
        if DEBUG: print "stripLeadingWhitespace", repr(string), repr(str_out)
        return str_out

    @staticmethod
    def stripTailingWhitespace(string):
        str_out = re.sub(r'\s*$', '', string)
        if DEBUG: print "stripTailingWhitespace", repr(string), repr(str_out)
        return str_out

    @staticmethod
    def stripTailingNewline(string):
        str_out = re.sub(r'(\\n|\n)$', '', string)
        if DEBUG: print "stripTailingNewline", repr(string), repr(str_out)
        return str_out

    @staticmethod
    def stripAllWhitespace(string):
        if DEBUG: print "stripAllWhitespace", repr(string)
        str_out = re.sub(r'\s', '', string)
        if DEBUG: print "stripAllWhitespace", repr(string), repr(str_out)
        return str_out

    @staticmethod
    def stripExtraWhitespace(string):
        str_out = re.sub(r'\s{2,}', ' ', string)
        if DEBUG: print "stripExtraWhitespace", repr(string), repr(str_out)
        return str_out

    @staticmethod
    def stripNonNumbers(string):
        str_out = re.sub('[^\d]', '', string)
        if DEBUG: print "stripNonNumbers", repr(string), repr(str_out)
        return str_out

    @staticmethod
    def stripPunctuation(string):
        str_out = re.sub('[%s]' % ''.join(SanitationUtils.punctuationChars) , '', string)
        if DEBUG: print "stripPunctuation", repr(string), repr(str_out)
        return str_out

    @staticmethod
    def stripAreaCode(string):
        str_out = re.sub('\s*\+\d{2,3}\s*','', string)
        if DEBUG: print "stripAreaCode", repr(string), repr(str_out)
        return str_out

    @staticmethod
    def toLower(string):
        str_out = string.lower()
        if DEBUG: print "toLower", repr(string), repr(str_out)
        return str_out

    @staticmethod
    def toUpper(string):
        str_out = string.upper()
        if DEBUG: print "toUpper", repr(string), repr(str_out)
        return str_out

    @staticmethod
    def sanitizeNewlines(string):
        return re.sub('\n','</br>', string)

    @staticmethod
    def escapeNewlines(string):
        return re.sub('\n',r'\\n', string)

    @staticmethod
    def compileRegex(subs):
        if subs:
            return re.compile( "(%s)" % '|'.join(filter(None, map(re.escape, subs))) )
        else:
            return None

    @staticmethod
    def sanitizeCell(cell):
        return SanitationUtils.compose(
            SanitationUtils.removeLeadingDollarWhiteSpace,
            SanitationUtils.removeLeadingPercentWhiteSpace,
            SanitationUtils.removeLoneDashes,
            SanitationUtils.removeThousandsSeparator,
            SanitationUtils.removeLoneWhiteSpace,
            SanitationUtils.stripLeadingWhitespace,
            SanitationUtils.stripTailingWhitespace,            
            SanitationUtils.sanitizeNewlines,
            SanitationUtils.stripTailingNewline,
            SanitationUtils.removeNULL,
            SanitationUtils.coerceUnicode
        )(cell)   

    @staticmethod
    def sanitizeClass(string):
        return re.sub('[^a-z]', '', string.lower())

    @staticmethod
    def similarComparison(string):
        return SanitationUtils.compose(
            SanitationUtils.toLower,
            SanitationUtils.stripLeadingWhitespace,
            SanitationUtils.stripTailingWhitespace,
            SanitationUtils.coerceUnicode
        )(string)

    @staticmethod
    def similarNoPunctuationComparison(string):
        return SanitationUtils.compose(
            SanitationUtils.normalizeVal,
            SanitationUtils.stripPunctuation,
        )(string)

    @staticmethod
    def similarPhoneComparison(string):
        return SanitationUtils.compose(
            SanitationUtils.stripNonNumbers,
            SanitationUtils.stripAreaCode,
            SanitationUtils.coerceUnicode
        )(string)

    @staticmethod
    def similarTruStrComparison(string):
        return SanitationUtils.compose(
            SanitationUtils.truishStringToBool,
            SanitationUtils.similarComparison
        )(string)

    @staticmethod
    def makeSafeClass(string):
        return SanitationUtils.compose(
            SanitationUtils.stripAllWhitespace,
            SanitationUtils.stripPunctuation
        )(string)

    @staticmethod
    def shorten(reg, subs, str_in):
        # if(DEBUG_GEN):
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
        # if DEBUG_GEN: 
        #     print " | str_o: ",str_out
        return str_out

    @staticmethod
    def findAllImages(instring):
        assert isinstance(instring, (str, unicode)), "param must be a string not %s"% type(instring)
        if not isinstance(instring, unicode):
            instring = instring.decode('utf-8')
        return re.findall(r'\s*([^.|]*\.[^.|\s]*)(?:\s*|\s*)',instring)

    @staticmethod
    def findAllTokens(instring, delim = "|"):
        assert isinstance(instring, (str, unicode)), "param must be a string not %s"% type(instring)
        if not isinstance(instring, unicode):
            instring = instring.decode('utf-8')
        return re.findall(r'\s*(\b[^\s.|]+\b)\s*', instring )

    @staticmethod
    def findallDollars(instring):
        assert isinstance(instring, (str, unicode)), "param must be a string not %s"% type(instring)
        if not isinstance(instring, unicode):
            instring = instring.decode('utf-8')
        return re.findall(r"\s*\$([\d,]+\.?\d*)", instring)

    @staticmethod
    def findallPercent(instring):
        assert isinstance(instring, (str, unicode)), "param must be a string not %s"% type(instring)
        if not isinstance(instring, unicode):
            instring = instring.decode('utf-8')
        return re.findall(r"\s*(\d+\.?\d*)%", instring)

    @staticmethod
    def titleSplitter(instring):
        assert isinstance(instring, (str, unicode)), "param must be a string not %s"% type(instring)
        if not isinstance(instring, unicode):
            instring = instring.decode('utf-8')
        found = re.findall(r"^\s*(.*?)\s+[^\s\w&\(\)]\s+(.*?)\s*$", instring)
        if found:
            return found[0]
        else:
            return instring, ""


    @staticmethod
    def stringIsEmail(email):
        return re.match(SanitationUtils.email_regex, email)

    @staticmethod
    def stringIsMYOBID(card):
        return re.match(SanitationUtils.myobid_regex, card)

    @staticmethod
    def stringCapitalized(string):
        return unicode(string) == unicode(string).upper()

    @staticmethod
    def stringContainsNumbers(string):
        if(re.search('\d', string)):
            return True
        else:
            return False

    @staticmethod
    def stringContainsNoNumbers(string):
        return not SanitationUtils.stringContainsNumbers(string)

    @staticmethod
    def stringContainsDelimeters(string):
        return True if(re.search(SanitationUtils.delimeterRegex, string)) else False

    @staticmethod
    def stringContainsDisallowedPunctuation(string):
        return True if(re.search(SanitationUtils.disallowedPunctuationRegex, string)) else False

    @staticmethod
    def stringContainsPunctuation(string):
        return True if(re.search(SanitationUtils.punctuationRegex, string)) else False

    @staticmethod
    def truishStringToBool(string):
        if( not string or 'n' in string or 'false' in string or string == '0' or string == 0):
            if DEBUG: print "truishStringToBool", repr(string), 'FALSE'
            return "FALSE"
        else:
            if DEBUG: print "truishStringToBool", repr(string), 'TRUE'
            return "TRUE"

    @staticmethod
    def datetotimestamp(datestring):
        raise DeprecationWarning()
        # assert isinstance(datestring, (str,unicode)), "param must be a string not %s"% type(datestring)
        # return int(time.mktime(datetime.datetime.strptime(datestring, "%d/%m/%Y").timetuple()))    

    @staticmethod
    def decodeJSON(json_str):
        assert isinstance(json_str, (str, unicode))
        attrs = json.loads(json_str)
        return attrs

    @staticmethod
    def encodeJSON(obj):
        assert isinstance(obj, (dict, list))
        json_str = json.dumps(obj, encoding="utf8", ensure_ascii=False)
        return json_str

    @staticmethod
    def encodeBase64(str):
        utf8_str = SanitationUtils.coerceBytes(str)
        return base64.standard_b64encode(utf8_str)

    @staticmethod
    def decodeBase64(b64_str):
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
        # 'first_name': 'noodle',
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
    singleNameRegex       = r"({ndp}|{nd}+{ndp}|{ord})".format(
        nd = SanitationUtils.nondelimeterRegex,
        ndp = SanitationUtils.nondelimeterPunctuationRegex,
        ord = ordinalNumberRegex
    )
    multiNameRegex  = r"({ndp}|{nd}+{ndp}|{ord})({nds}*{ord})?({nds}*{nd}{ndp})?)".format(
        nd = SanitationUtils.nondelimeterRegex,
        ndp = SanitationUtils.nondelimeterPunctuationRegex,
        nds = SanitationUtils.nondelimeterAndSpaceRegex,
        ord = ordinalNumberRegex
    )

    multiNameRegex  = r"(({2}|{0}{1}*{2})?({1}*{0})?)".format(
        SanitationUtils.nondelimeterRegex,
        SanitationUtils.nondelimeterAndSpaceRegex,
        ordinalNumberRegex
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
        names=multiNameRegex,
        name=singleNameRegex,
    )

    careOfRegex = r"(?P<careof>%s)[\.:]? ?(?P<careof_names>%s)" % (
        SanitationUtils.compileAbbrvRegex(careOfAbbreviations),
        multiNameRegex,
    )

    nameSuffixRegex = r"\(?(?P<name_suffix>%s)\.?\)?" % (
        SanitationUtils.compileAbbrvRegex(nameSuffixAbbreviations)
    )

    organizationRegex = r"(?P<organization_name>%s) (?P<organization_type>%s)\.?" % (
        multiNameRegex,
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
        SanitationUtils.wrapClearRegex( ordinalNumberRegex),
        SanitationUtils.wrapClearRegex( singleNameRegex ),
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
            if DEBUG_NAME: SanitationUtils.safePrint( "FOUND NAME " + repr(name))
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
            if DEBUG_NAME: SanitationUtils.safePrint( "FOUND NAMES " + repr(names))
            return names

    @staticmethod
    def getMultiName(token):
        match = re.match(
            SanitationUtils.wrapClearRegex(
                NameUtils.multiNameRegex
            ),
            token
        )
        matchGrps = match.groups() if match else None
        if(matchGrps):
            # name = " ".join(matchGrps)
            name = matchGrps[0]
            if DEBUG_NAME: SanitationUtils.safePrint( "FOUND NAME " + repr(name))
            return name

    @staticmethod
    def getEmail(token):
        # if DEBUG_NAME: SanitationUtils.safePrint("checking email", token)
        match = re.match(
            SanitationUtils.wrapClearRegex(
                "({})".format(SanitationUtils.email_regex)
            ),
            token
        )
        matchGrps = match.groups() if match else None
        if(matchGrps):
            # if DEBUG_NAME: SanitationUtils.safePrint("email matches", repr(matchGrps))
            # name = " ".join(matchGrps)
            email = matchGrps[0]
            if DEBUG_NAME: SanitationUtils.safePrint( "FOUND EMAIL " + repr(email))
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
            if DEBUG_NAME: print "FOUND TITLE ", repr(title)
            return title
        # matchGrps = match.groups() if match else None
        # if(matchGrps):
        #     # title = " ".join(matchGrps)
        #     title = matchGrps[0]
        #     if DEBUG_NAME: print "FOUND TITLE ", repr(title)
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
            if DEBUG_NAME: print "FOUND POSITION ", repr(position)
            return position
        # matchGrps = match.groups() if match else None
        # if(matchGrps):
        #     # position = " ".join(matchGrps)
        #     position = matchGrps[0]
        #     if DEBUG_NAME: print "FOUND POSITION ", repr(position)
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
            if DEBUG_NAME: SanitationUtils.safePrint("FOUND ORDINAL", ordinal)
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
            if DEBUG_NAME: print "FOUND NAME SUFFIX ", repr(suffix)
            return suffix
        # matchGrps = match.groups() if match else None
        # if(matchGrps):
        #     # position = " ".join(matchGrps)
        #     suffix = matchGrps[0]
        #     if DEBUG_NAME: print "FOUND NAME SUFFIX ", repr(suffix)
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
            if DEBUG_NAME: print "FOUND NOTE ", repr(note_tuple)
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
        matchGrps = match.groups() if match else None
        if matchGrps:
            family_name = matchGrps[0]
            if DEBUG_NAME: SanitationUtils.safePrint("FOUND FAMILY NAME", family_name)
            return family_name


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
            if DEBUG_NAME: print "FOUND CAREOF ", repr(careof_tuple)
            return careof_tuple
        # matchGrps = match.groups() if match else None
        # if(matchGrps):
        #     # note = " ".join(matchGrps)
        #     careof = matchGrps[0]
        #     if DEBUG_NAME: print "FOUND CAREOF ", repr(careof)
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
            if DEBUG_NAME: print "FOUND ORGANIZATION ", repr(organization)
            return organization

    @staticmethod
    def tokenizeName(string):
        string = string.upper()
        matches =  re.findall(
            NameUtils.nameTokenRegex, 
            string
        )
        # if DEBUG_NAME: print repr(matches)
        return map(
            lambda match: NameUtils.sanitizeNameToken(match[0]),
            matches    
        )

def testNameUtils():
    # print SanitationUtils.compileAbbrvRegex(NameUtils.noteAbbreviations)
    # print NameUtils.tokenizeName('DERWENT (ACCT)')
    # print NameUtils.getEmail('KYLIESWEET@GMAIL.COM')
    def testNotes(line):
        for token in NameUtils.tokenizeName(line):
            print token, NameUtils.getNote(token)

    testNotes("DERWENT - FINALIST")
    testNotes("JAGGERS HAIR - DO NOT WANT TO BE CALLED!!!!")
        


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
        ('HWY',      ['HIGHWAY', 'HGWY', 'HWAY']),
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
        ('SHOPPING CENTRE', ["S/C", "SHOPNG CNTR", "SHOPPING CENTER", "SHOPPING CENTRE", "SHOPPING CTR", "SHOPPING", "SHOP. CENTRE", ]),
        ('PLAZA',           ['PLZA']),
        ('ARCADE',          ["ARC"]),
        ('MALL',            []),
        ('BUILDING',        ['BLDG']),
        ('FORUM',           []),
        ('HOUSE',           []),
        ('CENTER',          []),
        ('CENTRE',          []),
        ('FORUM',           []),
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
    numberAlphaRegex = r"{0} ?({1})".format(
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
    slashAbbrvRegex  = r"{0}/{0}+".format(
        alphaRegex
    )
    singleNumberRegex= r"(%s)" % "|".join([
        numberAlphaRegex,
        numberRegex
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
    multiNumberAllRegex = r"(%s)" % "|".join([
        numberAlphaRegex,
        numberRangeRegex,
        numberSlashRegex,
        numberRegex,
        alphaNumberRegex,
    ])
    
    floorLevelRegex = r"(?:(?P<floor_prefix>FLOOR|LEVEL|LVL)\.? )?(?P<floor_type>%s)\.? ?(?P<floor_number>%s)" % (
        SanitationUtils.compileAbbrvRegex(floorAbbreviations),
        singleNumberRegex,
    )
    subunitRegex = r"(?P<subunit_type>%s) ?(?P<subunit_number>(?:%s)/?)" % (
        SanitationUtils.compileAbbrvRegex(subunitAbbreviations),
        multiNumberAlphaRegex,
    )
    weakSubunitRegex = r"(?P<weak_subunit_type>%s) ?(?P<weak_subunit_number>(?:%s)/?)" % (
        NameUtils.singleNameRegex,
        multiNumberAlphaRegex,
    )
    stateRegex = r"(%s)" % SanitationUtils.compileAbbrvRegex(stateAbbreviations)
    thoroughfareNameRegex = r"%s" % (
        "|".join([
            NameUtils.multiNameRegex,
            NameUtils.ordinalNumberRegex,
        ])
    )
    thoroughfareTypeRegex = r"%s" % (
        SanitationUtils.compileAbbrvRegex(thoroughfareTypeAbbreviations)
    )
    thoroughfareSuffixRegex = r"%s" % (
        SanitationUtils.compileAbbrvRegex(thoroughfareSuffixAbbreviations)
    )
    thoroughfareRegex = r"(?P<thoroughfare_number>%s)\s+(?P<thoroughfare_name>%s)\s+(?P<thoroughfare_type>%s)\.?(?:\s+(?P<thoroughfare_suffix>%s))?" % (
        multiNumberSlashRegex,
        thoroughfareNameRegex,
        thoroughfareTypeRegex,
        thoroughfareSuffixRegex
    )
    weakThoroughfareRegex = r"(?P<weak_thoroughfare_name>%s)\s+(?P<weak_thoroughfare_type>%s)\.?(?:\s+(?P<weak_thoroughfare_suffix>%s))?" % (
        thoroughfareNameRegex,
        thoroughfareTypeRegex,
        thoroughfareSuffixRegex
    )
    buildingTypeRegex = r"(?P<building_type>%s)" % (
        SanitationUtils.compileAbbrvRegex(buildingTypeAbbreviations)
    )
    buildingRegex = r"(?P<building_name>{0})\s+{1}".format(
        NameUtils.multiNameRegex,
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
            if DEBUG_ADDRESS: SanitationUtils.safePrint( "FOUND FLOOR", floor_type, floor_number)
            return floor_type, floor_number
        return None

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
            if DEBUG_ADDRESS:  SanitationUtils.safePrint("FOUND SUBUNIT", subunit)
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
            if DEBUG_ADDRESS:  SanitationUtils.safePrint("FOUND WEAK SUBUNIT", subunit)
            return subunit
        return None

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
            if DEBUG_ADDRESS: SanitationUtils.safePrint( 
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
            building_name = matchDict.get('building_name')
            building_type = AddressUtils.identifyBuildingType(
                matchDict.get('building_type')
            )
            if DEBUG_ADDRESS: SanitationUtils.safePrint(
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

            if DEBUG_ADDRESS: print "FOUND WEAK THOROUGHFARE %s | %s (%s)" % (
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
            if DEBUG_ADDRESS: SanitationUtils.safePrint( "FOUND STATE ", state_name)
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
            if DEBUG_ADDRESS: SanitationUtils.safePrint( "FOUND DELIVERY ", delivery_type, delivery_number)
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
            if DEBUG_ADDRESS: SanitationUtils.safePrint( "FOUND NUMBER ", repr(number))
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
            if DEBUG_ADDRESS: SanitationUtils.safePrint( "FOUND SINGLE NUMBER ", repr(number))
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
            if DEBUG_ADDRESS: SanitationUtils.safePrint( "FOUND SINGLE NUMBER ", repr(number))
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
        if DEBUG: SanitationUtils.safePrint( "sanitizeAddressToken", string)
        return string

    @staticmethod
    def tokenizeAddress(string):
        # if DEBUG_ADDRESS: 
        #     SanitationUtils.safePrint("in tokenizeAddress")
        matches =  re.findall(
            AddressUtils.addressTokenRegex, 
            string.upper()
        )
        # if DEBUG_ADDRESS: 
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
    SanitationUtils.clearStartRegex = "<START>"
    SanitationUtils.clearFinishRegex = "<FINISH>"
    print repr(AddressUtils.addressTokenRegex)

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

    # for line in [
    #     "8/5-7 KILVINGTON DRIVE EAST",
    #     "SH20 SANCTUARY LAKES SHOPPING CENTRE",
    #     "2 HIGH ST EAST BAYSWATER",
    #     "FLOREAT FORUM",
    #     "ANN LYONS",
    #     "SHOP 5, 370 VICTORIA AVE",
    #     "SHOP 34 ADELAIDE ARCADE",
    #     "SHOP 5/562 PENNANT HILLS RD",
    #     "MT OMMANEY SHOPPING",
    #     "BUCKLAND STREET",
    #     "6/7 118 RODWAY ARCADE",
    #     "INGLE FARM SHOPPING CENTRE",
    #     "EASTLAND SHOPPING CENTRE",
    #     "SHOP 3044 WESTFEILD",
    #     "303 HAWTHORN RD",
    #     "7 KALBARRI ST,  WA",
    #     "229 FORREST HILL CHASE",
    #     "THE VILLAGE SHOP 5",
    #     "GARDEN CITY SHOPPING CENTRE",
    #     "SHOP 2 EAST MALL",
    #     "SAMANTHA PALMER",
    #     "134 THE GLEN SHOPPING CENTRE",
    #     "SHOP 3 A, 24 TEDDER AVE",
    #     "SHOP 205, DANDENONG PLAZA",
    #     "SHOP 5 / 20 -21 OLD TOWN PLAZA",
    #     "18A BORONIA RD",
    #     "SHOP 426 LEVEL 4",
    #     "WATERFORD PLAZA",
    #     "BEAUDESERT RD",
    #     "173 GLENAYR AVE",
    #     "SHOP 14-16 ALBANY PLAZA S/C",
    #     "861 ALBANY HIGHWAY",
    #     "4/479 SYDNEY RD",
    #     "90 WINSTON AVE",
    #     "SHOP 2004 - LEVEL LG1",
    #     "142 THE PARADE",
    #     "46 MARKET STREET",
    #     "AUSTRALIA FAIR",
    #     "538 MAINS RD",
    #     "SHOP 28 GRENFELL ST",
    #     "309 MAIN ST",
    #     "60 TOMPSON ROAD",
    #     "SHOP 10 2-28 EVAN ST",
    #     "VENESSA MILETO",
    #     "BOX RD",
    #     "34 RAILWAY PARADE",
    #     "SHOP 14A WOODLAKE VILLAGE S/C",
    #     "17 ROKEBY RD",
    #     "AUSTRALIA FAIR SHOPPING",
    #     "SHOP 1, 18-26 ANDERSON ST",
    #     "INDOOROOPILLY SHOPPINGTOWN",
    #     "17 CASUARINA RD",
    #     "WHITFORDS WESTFIELD",
    #     "4, 175 LABOUCHERE RD",
    #     "2 PEEL STREET",
    #     "SHOP 71 THE ENTRANCE RD",
    #     "SHOP 2014 LEVEL 2",
    #     "PLAZA ARCADE",
    #     "SHOP 27 ADELAIDE ARCADE",
    #     "152 WENTWORTH RD",
    #     "92 PROSPECT RD",
    #     "31 REITA AVE",
    #     "33 NEW ENGLAND HWY",
    #     "46 HUNTER ST",
    #     "1/34-36 MCPHERSON ST",
    #     "SHOP 358",
    #     "147 SOUTH TCE",
    #     "SHOP 1003 L1",
    #     "357 CAMBRIDGE STREET",
    #     "495 BURWOOD HWY",
    #     "CAROUSAL MALL",
    #     "SHOP 22 BAYSIDE VILLAGE",
    #     "1/64 GYMEA BAY RD",
    #     "1/15 RAILWAY RD",
    #     "SOUTHLANDS BOULEVARD",
    #     "83A COMMERCIAL RD",
    #     u"456 ROCKY PT R\u010E",
    #     "95 ROCKEBY RD",
    #     "4/13-17 WARBURTON ST",
    #     "1/18 ADDISON SY",
    #     "SUNNYPARK",
    #     "SHOP 4,81 PROSPECT",
    #     "WESTFIELD",
    #     "15 - 16 KEVLAR CLOSE",
    #     "31",
    #     "3/71 DORE ST",
    #     "SHOP 11 RIVERSTONE PDE",
    #     "SOUTHERN RIVER SHOPPING CENTRE RANFORD ROAD",
    #     "6 RODINGA CLOSE",
    #     "SHOP 2013 WESTFIELDS",
    #     "SHOP 524 THE GLEN SHOPPING CENTRE",
    #     "JOONDALUP SHOPPING CENTRE",
    #     "48/14 JAMES PLACE",
    #     "3/66 TENTH AVE",
    #     "SHOP 23 GORDON VILLAGE ARCADE",
    #     "HORNSBY WESTFIELD",
    #     "SHOP 81",
    #     "215/152 BUNNERONG RD",
    #     "SP 1032 KNOX CITY SHOPPING CENTRE",
    #     "SHOP 152 RUNDLE MALL",
    #     "37 BURWOOD RD",
    #     "SHOP 52 LEVEL 3",
    #     "ALBANY PLAZA SHOPPING CENTRE",
    #     "LEVEL 3 SHOP 3094",
    #     "SHOP 19 B LAKE MACQUARIE",
    #     "18/70 HURTLE",
    #     "309 GEORGE ST",
    #     "76 EDWARDES",
    #     "SUNNYBANK PLAZA",
    #     "1/134 HIGH ST",
    #     "CARRUM DOWNS SHOPPING CENTER",
    #     "SHOP 13 1 WENTWORTH ST",
    #     "234 BROADWAY",
    #     "288 STATION ST",
    #     "KMART PLAZA",
    #     "15 FLINTLOCK CT",
    #     "17 O'CONNELL ST",
    #     "JILL STREET SHOPPING CENTRE",
    #     "SHOP 3, 2-10 WILLIAM THWAITES BLVD",
    #     "170 CLOVELLY RD",
    #     "SHOP 11 451 SYDNEY RD",
    #     "PRINCES HIGHWAY ULLADULLA",
    #     "WESTFIELD DONCASTER SHOPPING CENTRE",
    #     "153 BREBNER SR",
    #     "HELENSVALE TOWN CENTRE",
    #     "SHOP 7 A KENWICK SHOPNG CNTR 1 - 3 BELMONT RD EAST, KENWICK WA (",
    #     "3/3 HOWARD AVA",
    #     "8/2 RIDER BLVD",
    #     "ROBINA PARKWAY",
    #     "VICTORIA PT SHOPPING",
    #     "ROBINSON ROAD",
    #     "3/3 BEASLEY RD,",
    #     "39 HAWKESBURY RETREAT",
    #     "171 MORAYFIELD ROAD",
    #     "149 ST JOHN STREET",
    #     "49 GEORGE ST,  WA",
    #     "UNIT 1",
    #     "A8/90 MOUNT STREET",
    #     "114 / 23 CORUNNA RD",
    #     "43 GINGHAM STREET",
    #     "5 KERRY CRESCENT, WESTERN AUSTRALIA",
    #     "UNIT 2/33 MARTINDALE STREET",
    #     "207/67 WATT ST",
    #     "LEVEL 8, BLIGH"
    # ]:
    #     pass
        # print SanitationUtils.unicodeToByte("%64s %64s %s" % (line, AddressUtils.tokenizeAddress(line), AddressUtils.getThoroughfare(line)))


class TimeUtils:
    wpSrvOffset = 0

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
            assert key in self.keys(), "{} must be set before get".format(key)
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

class listUtils:
    @staticmethod
    def combineLists(a, b):
        if not a:
            return b if b else []
        if not b: return a
        return list(set(a) | set(b))

    @staticmethod
    def combineOrderedDicts(a, b):
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

class debugUtils:
    @staticmethod
    def getProcedure():
        return inspect.stack()[1][3]

    @staticmethod
    def getCallerProcedure():
        return inspect.stack()[2][3]   

    @staticmethod
    def hashify(in_str):
        out_str = "#" * (len(in_str) + 4) + "\n"
        out_str += "# " + in_str + " #\n"
        out_str += "#" * (len(in_str) + 4) + "\n"
        return out_str

class Registrar:
    messages = OrderedDict()
    errors = OrderedDict()
    warnings = OrderedDict()

    def __init__(self):
        self.objectIndexer = id
        self.conflictResolver = self.passiveResolver

    def resolveConflict(self, new, old, index, registerName = ''):
        self.registerError("Object [index: %s] already exists in register %s"%(index, registerName))

    def getObjectRowcount(self, objectData):
        return objectData.rowcount

    def getObjectIndex(self, objectData):
        return objectData.index

    def passiveResolver(*args):
        pass

    def exceptionResolver(self, new, old, index, registerName = ''):
        raise Exception("could not register %s in %s. Duplicate index: %s" % (str(new), registerName, index) )

    def warningResolver(self, new, old, index, registerName = ''):
        try:
            self.exceptionResolver(new, old, index, registerName)
        except Exception as e:
            self.registerError(e, new )

    @classmethod
    def stringAnything(self, index, thing, delimeter):
        return SanitationUtils.coerceBytes( u"%31s %s %s" % (index, delimeter, thing) )

    @classmethod
    def printAnything(self, index, thing, delimeter):
        print Registrar.stringAnything(index, thing, delimeter)

    def registerAnything(self, thing, register, indexer = None, resolver = None, singular = True, registerName = ''):
        if resolver is None: resolver = self.conflictResolver
        if indexer is None: indexer = self.Indexer
        index = None
        try:
            if callable(indexer):
                index = indexer(thing)
            else: 
                index = indexer
            assert index.__hash__, "Index must be hashable"
            assert index == index, "index must support eq"
        except AssertionError as e:
            raise Exception("Indexer [%s] produced invalid index: %s | %s" % (indexer.__name__, repr(index), str(e)))
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
                register[index].append(thing)
        # print "registered", thing

    def registerError(self, error, data = None):
        if data:
            try:
                index = data.index
            except:
                index = data
        else:
            index = debugUtils.getCallerProcedure()
        error_string = str(error)
        if DEBUG_ERROR: Registrar.printAnything(index, error, '!')
        self.registerAnything(
            error_string, 
            self.errors, 
            index, 
            singular = False,
            registerName = 'errors'
        )

    def registerWarning(self, message, source=None):
        if source is None:
            source = debugUtils.getCallerProcedure()
        if DEBUG_WARN: Registrar.printAnything(source, message, ' ')
        self.registerAnything(
            message,
            self.warnings,
            source,
            singular = False,
            registerName = 'warnings'
        )

    def registerMessage(self, message, source=None):
        if source is None:
            source = debugUtils.getCallerProcedure()
        if DEBUG_MESSAGE: Registrar.printAnything(source, message, ' ')
        self.registerAnything(
            message,
            self.messages,
            source,
            singular = False,
            registerName = 'messages'
        )


class ValidationUtils:
    @staticmethod
    def isNotNone(arg):
        return arg is not None

    @staticmethod
    def isContainedIn(l):
        return lambda v: v in l

class PHPUtils:
    @staticmethod
    def uniqid(prefix="", more_entropy=False):
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
    
if __name__ == '__main__':
    # testHTMLReporter()
    testTimeUtils()
    # testSanitationUtils()
    # testUnicodeWriter()
    # testAddressUtils()
    # testNameUtils()