import functools
import itertools
# from itertools import chain
import re
import time
import datetime
import inspect
import json
from collections import OrderedDict
import codecs
import csv
import cStringIO

DEFAULT_ENCODING = 'utf8'

DEBUG = False

class sanitationUtils:
    email_regex = "^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    myobid_regex = "C\d+"

    @staticmethod
    def compose(*functions):
        return functools.reduce(lambda f, g: lambda x: f(g(x)), functions)

    @staticmethod
    def stringToUnicode(string):
        if(not isinstance(string, unicode)):
            string = str(string).decode(DEFAULT_ENCODING)
        return string

    @staticmethod
    def unicodeToAscii(string):
        str_out = sanitationUtils.stringToUnicode(string)
        return str_out.encode('ascii', 'backslashreplace')

    @staticmethod
    def removeLeadingDollarWhiteSpace(string):
        str_out = re.sub('^\W*\$','', string)
        if DEBUG: print "removeLeadingDollarWhiteSpace", string.encode('ascii','backslashreplace'), str_out.encode('ascii','backslashreplace')
        return str_out

    @staticmethod
    def removeLeadingPercentWhiteSpace(string):
        str_out = re.sub('%\W*$','', string)
        if DEBUG: print "removeLeadingPercentWhiteSpace", string.encode('ascii','backslashreplace'), str_out.encode('ascii','backslashreplace')
        return str_out

    @staticmethod
    def removeLoneDashes(string):
        str_out = re.sub('^-$', '', string)
        if DEBUG: print "removeLoneDashes", str_out
        return str_out

    @staticmethod
    def removeThousandsSeparator(string):
        str_out = re.sub('(\d+),(\d{3})', '\g<1>\g<2>', string)
        if DEBUG: print "removeThousandsSeparator", string.encode('ascii','backslashreplace'), str_out.encode('ascii','backslashreplace')
        return str_out

    @staticmethod
    def removeLoneWhiteSpace(string):
        str_out = re.sub('^\s*$','', string)    
        if DEBUG: print "removeLoneWhiteSpace", string.encode('ascii','backslashreplace'), str_out.encode('ascii','backslashreplace')
        return str_out

    @staticmethod
    def removeNULL(string):
        str_out = re.sub('^NULL$', '', string)
        if DEBUG: print "removeNULL", string.encode('ascii','backslashreplace'), str_out.encode('ascii','backslashreplace')
        return str_out

    @staticmethod
    def stripLeadingWhitespace(string):
        str_out = re.sub('^\s*', '', string)
        if DEBUG: print "stripLeadingWhitespace", string.encode('ascii','backslashreplace'), str_out.encode('ascii','backslashreplace')
        return str_out

    @staticmethod
    def stripTailingWhitespace(string):
        str_out = re.sub('\s*$', '', string)
        if DEBUG: print "stripTailingWhitespace", string.encode('ascii','backslashreplace'), str_out.encode('ascii','backslashreplace')
        return str_out

    @staticmethod
    def stripAllWhitespace(string):
        str_out = re.sub('\s', '', string)
        if DEBUG: print "stripAllWhitespace", string.encode('ascii','backslashreplace'), str_out.encode('ascii','backslashreplace')
        return str_out

    @staticmethod
    def stripNonNumbers(string):
        str_out = re.sub('[^\d]', '', string)
        if DEBUG: print "stripNonNumbers", string.encode('ascii','backslashreplace'), str_out.encode('ascii','backslashreplace')
        return str_out

    @staticmethod
    def stripAreaCode(string):
        str_out = re.sub('\s*\+\d{2,3}\s*','', string)
        if DEBUG: print "stripAreaCode", string.encode('ascii','backslashreplace'), str_out.encode('ascii','backslashreplace')
        return str_out

    @staticmethod
    def toLower(string):
        str_out = string.lower()
        if DEBUG: print "toLower", string.encode('ascii','backslashreplace'), str_out.encode('ascii','backslashreplace')
        return str_out

    @staticmethod
    def sanitizeNewlines(string):
        if '\n' in string: 
            print "!!! found newline in string"
        return re.sub('\\n','</br>', string)

    @staticmethod
    def compileRegex(subs):
        if subs:
            return re.compile( "(%s)" % '|'.join(filter(None, map(re.escape, subs))) )
        else:
            return None

    @staticmethod
    def sanitizeCell(cell):
        return sanitationUtils.compose(
            sanitationUtils.removeLeadingDollarWhiteSpace,
            sanitationUtils.removeLeadingPercentWhiteSpace,
            sanitationUtils.removeLoneDashes,
            sanitationUtils.removeThousandsSeparator,
            sanitationUtils.removeLoneWhiteSpace,
            sanitationUtils.stripLeadingWhitespace,
            sanitationUtils.stripTailingWhitespace,            
            sanitationUtils.sanitizeNewlines,
            sanitationUtils.removeNULL,
            sanitationUtils.stringToUnicode
        )(cell)   

    @staticmethod
    def similarComparison(string):
        return sanitationUtils.compose(
            sanitationUtils.toLower,
            sanitationUtils.stripLeadingWhitespace,
            sanitationUtils.stripTailingWhitespace,
            sanitationUtils.stringToUnicode
        )(string)

    @staticmethod
    def similarPhoneComparison(string):
        return sanitationUtils.compose(
            sanitationUtils.stripNonNumbers,
            sanitationUtils.stripAreaCode,
            sanitationUtils.stringToUnicode
        )(string)

    @staticmethod
    def makeSafeOutput(string):
        return sanitationUtils.compose(
            sanitationUtils.sanitizeNewlines,
            sanitationUtils.unicodeToAscii
        )(string)

    @staticmethod
    def similarTruStrComparison(string):
        return sanitationUtils.compose(
            sanitationUtils.truishStringToBool,
            sanitationUtils.similarComparison
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
    def findAllImages(imgString):
        assert type(imgString) == str, "param must be a string not %s"% type(imgString)
        return re.findall(r'\s*([^.|]*\.[^.|\s]*)(?:\s*|\s*)',imgString)

    @staticmethod
    def findAllTokens(tokenString, delim = "|"):
        assert type(tokenString) == str, "param must be a string not %s"% type(tokenString)
        return re.findall(r'\s*(\b[^\s.|]+\b)\s*', tokenString )

    @staticmethod
    def findallDollars(instring):
        assert type(instring) == str, "param must be a string not %s"% type(instring)
        return re.findall(r"\s*\$([\d,]+\.?\d*)", instring)

    @staticmethod
    def findallPercent(instring):
        assert type(instring) == str, "param must be a string not %s"% type(instring)
        return re.findall(r"\s*(\d+\.?\d*)%", instring)

    @staticmethod
    def titleSplitter(instring):
        assert type(instring) == str, "param must be a string not %s"% type(instring)
        instring = instring.decode('utf-8')
        found = re.findall(r"^\s*(.*?)\s+[^\s\w&\(\)]\s+(.*?)\s*$", instring)
        if found:
            return found[0]
        else:
            return instring, ""


    @staticmethod
    def stringIsEmail(email):
        return re.match(sanitationUtils.email_regex, email)

    @staticmethod
    def stringIsMYOBID(card):
        return re.match(sanitationUtils.myobid_regex, card)

    @staticmethod
    def truishStringToBool(string):
        if( not string or 'n' in string or 'false' in string or string == '0' or string == 0):
            if DEBUG: print "truishStringToBool", repr(string).encode('ascii','backslashreplace'), 'FALSE'
            return "FALSE"
        else:
            if DEBUG: print "truishStringToBool", repr(string).encode('ascii','backslashreplace'), 'TRUE'
            return "TRUE"

    @staticmethod
    def datetotimestamp(datestring):
        assert type(datestring) == str, "param must be a string not %s"% type(datestring)
        return int(time.mktime(datetime.datetime.strptime(datestring, "%d/%m/%Y").timetuple()))    

    @staticmethod
    def decodeJSON(string):
        assert isinstance(string, str)
        attrs = json.loads(string)
        return attrs

    @staticmethod
    def cleanBackslashString(string):
        if string is None:
            return None
        elif isinstance(string, unicode):
            unicode_content = string
        else:
            unicode_content = str(string).decode('utf-8', 'ignore')
            assert isinstance(unicode_content, unicode)
        backslashed = unicode_content.encode('ascii', 'backslashreplace')
        # print "backslashed: ", backslashed
        return backslashed

    @staticmethod
    def cleanXMLString(string):
        # print "cleaning string ", string
        if string is None:
            return None
        elif isinstance(string, unicode):
            unicode_content = string
        else:
            unicode_content = str(string).decode('utf-8', 'ignore')
            assert isinstance(unicode_content, unicode)
        # print "unicode_content: ", unicode_content
        xml_content = unicode_content.encode('ascii', 'xmlcharrefreplace')
        # print "xml_content: ", xml_content
        return xml_content

class TimeUtils:

    wpTimeFormat = "%Y-%m-%d %H:%M:%S"
    actTimeFormat = "%d/%m/%Y %I:%M:%S %p"

    @staticmethod
    def starStrptime(string, fmt = wpTimeFormat ):
        string = sanitationUtils.stringToUnicode(string)
        if(string):
            try:
                tstruct = time.strptime(string, fmt)
                if(tstruct):
                    return time.mktime(tstruct)
            except:
                pass
        return 0        

    @staticmethod
    def actStrptime(string):
        return TimeUtils.starStrptime(string, TimeUtils.actTimeFormat)

    # 2015-07-13 22:33:05
    @staticmethod
    def wpStrptime(string):
        return TimeUtils.starStrptime(string)

    @staticmethod
    def wpTimeToString(t, fmt = wpTimeFormat):
        return time.strftime(fmt, time.localtime(t))

class descriptorUtils:
    @staticmethod
    def safeKeyProperty(key):
        def getter(self):
            assert key in self.keys(), "{} must be set before get".format(key)
            return self[key]

        def setter(self, value):
            assert isinstance(value, str), "{} must be set with string not {}".format(key, type(value))
            self[key] = value

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
        c = OrderedDict(b.items())
        for key, value in a.items():
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

class UTF8Recoder:
    """
    Iterator that reads an encoded stream and reencodes the input to UTF-8
    """
    def __init__(self, f, encoding):
        try:
            bom = codecs.BOM_UTF8
            # print "bom: ", repr(bom)
            bomtest = f.read(len(bom))
            # print "bomtest: ", repr(bomtest)
            if(bomtest == bom):
                pass
                # print "starts with BOM_UTF8"
            else:
                raise Exception("does not start w/ BOM_UTF8")
        except Exception as e:
            if(e): pass
            # print "could not remove bom, ",e
            f.seek(0)
        self.reader = codecs.getreader(encoding)(f)

    def __iter__(self):
        return self

    def next(self):
        return self.reader.next().encode("utf-8")

class UnicodeReader:
    """
    A CSV reader which will iterate over lines in the CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        f = UTF8Recoder(f, encoding)
        self.reader = csv.reader(f, dialect=dialect, **kwds)

    def next(self):
        row = self.reader.next()
        return [unicode(s, "utf-8") for s in row]

    def __iter__(self):
        return self

class UnicodeWriter:
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.queue = cStringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def writerow(self, row):
        self.writer.writerow([s.encode("utf-8") for s in row])
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)

if __name__ == '__main__':
    t1 =  TimeUtils.actStrptime("29/08/2014 9:45:08 AM")
    t2 = TimeUtils.actStrptime("26/10/2015 11:08:31 AM")
    t3 = TimeUtils.wpStrptime("2015-07-13 22:33:05")
    t4 = TimeUtils.wpStrptime("2015-12-18 16:03:37")
    print \
        TimeUtils.wpTimeToString(t1), \
        TimeUtils.wpTimeToString(t2), \
        TimeUtils.wpTimeToString(t3), \
        TimeUtils.wpTimeToString(t4)

    n1 = u"D\u00C8RWENT"
    n2 = u"d\u00E8rwent"
    print sanitationUtils.unicodeToAscii(n1) , \
        sanitationUtils.unicodeToAscii(sanitationUtils.similarComparison(n1)), \
        sanitationUtils.unicodeToAscii(n2), \
        sanitationUtils.unicodeToAscii(sanitationUtils.similarComparison(n2))

    p1 = "+61 04 3190 8778"
    p2 = "04 3190 8778"
    p3 = "+61 (08) 93848512"
    print \
        sanitationUtils.similarPhoneComparison(p1), \
        sanitationUtils.similarPhoneComparison(p2), \
        sanitationUtils.similarPhoneComparison(p3)

    print sanitationUtils.makeSafeOutput(u"asdad \u00C3 <br> \n \b")

    tru = sanitationUtils.similarComparison(u"TRUE")

    print \
        sanitationUtils.similarTruStrComparison('yes'), \
        sanitationUtils.similarTruStrComparison('no'), \
        sanitationUtils.similarTruStrComparison('TRUE'),\
        sanitationUtils.similarTruStrComparison('FALSE'),\
        sanitationUtils.similarTruStrComparison(0),\
        sanitationUtils.similarTruStrComparison('0'),\
        sanitationUtils.similarTruStrComparison(u"0")\