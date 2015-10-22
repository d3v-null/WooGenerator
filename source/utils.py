import functools
# from itertools import chain
import re
import time
import datetime
import inspect
import json
from collections import OrderedDict

class sanitationUtils:
    email_regex = "^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"

    @staticmethod
    def compose(*functions):
        return functools.reduce(lambda f, g: lambda x: f(g(x)), functions)

    @staticmethod
    def removeLeadingDollarWhiteSpace(string):
        return re.sub('^\W*\$','', string)

    @staticmethod
    def removeLeadingPercentWhiteSpace(string):
        return re.sub('%\W*$','', string)

    @staticmethod
    def removeLoneDashes(string):
        return re.sub('^-$', '', string)

    @staticmethod
    def removeThousandsSeparator(string):
        return re.sub('(\d+),(\d{3})', '\g<1>\g<2>', string)

    @staticmethod
    def removeLoneWhiteSpace(string):
        return re.sub('^\s*$','', string)    

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
            sanitationUtils.sanitizeNewlines
        )(cell)   

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
        return re.findall("\s*\$([\d,]+\.?\d*)", instring)

    @staticmethod
    def findallPercent(instring):
        assert type(instring) == str, "param must be a string not %s"% type(instring)
        return re.findall("\s*(\d+\.?\d*)%", instring)

    @staticmethod
    def stringIsEmail(email):
        return re.match(sanitationUtils.email_regex, email)

    @staticmethod
    def datetotimestamp(datestring):
        assert type(datestring) == str, "param must be a string not %s"% type(datestring)
        return int(time.mktime(datetime.datetime.strptime(datestring, "%d/%m/%Y").timetuple()))    

    @staticmethod
    def decodeJSON(string):
        assert isinstance(string, str)
        attrs = json.loads(string)
        return attrs

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

class debugUtils:
    @staticmethod
    def getProcedure():
        return inspect.stack()[1][3]

    @staticmethod
    def getCallerProcedure():
        return inspect.stack()[2][3]        