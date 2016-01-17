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
    email_regex = r"^[\w.+-]+@[\w-]+\.[\w.-]+$"
    punctuationChars = [
        '!', '"', '#', '$', '%', '&', '\'', '(', ')', '*', '+', ',', '\-', '.', '/', ':', ';', '<', '=', '>', '?', '@', '[', '\\\\', '\\]', '^', '_', '`', '{', '|', '}', '~' 
    ]
    myobid_regex = r"C\d+"

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
        str_out = re.sub(r'(\d+),(\d{3})', '\g<1>\g<2>', string)
        if DEBUG: print "removeThousandsSeparator", string.encode('ascii','backslashreplace'), str_out.encode('ascii','backslashreplace')
        return str_out

    @staticmethod
    def removeLoneWhiteSpace(string):
        str_out = re.sub(r'^\s*$','', string)    
        if DEBUG: print "removeLoneWhiteSpace", string.encode('ascii','backslashreplace'), str_out.encode('ascii','backslashreplace')
        return str_out

    @staticmethod
    def removeNULL(string):
        str_out = re.sub(r'^NULL$', '', string)
        if DEBUG: print "removeNULL", string.encode('ascii','backslashreplace'), str_out.encode('ascii','backslashreplace')
        return str_out

    @staticmethod
    def stripLeadingWhitespace(string):
        str_out = re.sub(r'^\s*', '', string)
        if DEBUG: print "stripLeadingWhitespace", string.encode('ascii','backslashreplace'), str_out.encode('ascii','backslashreplace')
        return str_out

    @staticmethod
    def stripTailingWhitespace(string):
        str_out = re.sub(r'\s*$', '', string)
        if DEBUG: print "stripTailingWhitespace", string.encode('ascii','backslashreplace'), str_out.encode('ascii','backslashreplace')
        return str_out

    @staticmethod
    def stripAllWhitespace(string):
        if DEBUG: print "stripAllWhitespace", repr(string)
        str_out = re.sub(r'\s', '', string)
        if DEBUG: print "stripAllWhitespace", string.encode('ascii','backslashreplace'), str_out.encode('ascii','backslashreplace')
        return str_out

    @staticmethod
    def stripExtraWhitespace(string):
        str_out = re.sub(r'\s{2,}', ' ', string)
        if DEBUG: print "stripExtraWhitespace", string.encode('ascii','backslashreplace'), str_out.encode('ascii','backslashreplace')
        return str_out

    @staticmethod
    def stripNonNumbers(string):
        str_out = re.sub('[^\d]', '', string)
        if DEBUG: print "stripNonNumbers", string.encode('ascii','backslashreplace'), str_out.encode('ascii','backslashreplace')
        return str_out

    @staticmethod
    def stripPunctuation(string):
        str_out = re.sub('[%s]' % ''.join(sanitationUtils.punctuationChars) , '', string)
        if DEBUG: print "stripPunctuation", string.encode('ascii', 'backslashreplace'), str_out.encode('ascii', 'backslashreplace')
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
    def toUpper(string):
        str_out = string.upper()
        if DEBUG: print "toUpper", string.encode('ascii','backslashreplace'), str_out.encode('ascii','backslashreplace')
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
    def stringContainsNumbers(string):
        if(re.search('\d', string)):
            return True
        else:
            return False

    @staticmethod
    def stringContainsNoNumbers(string):
        return not sanitationUtils.stringContainsNumbers(string)

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

    @staticmethod
    def stringCapitalized(string):
        return unicode(string) == unicode(string).upper()



def compilePartialAbbrvRegex( abbrvKey, abbrvs ):
    return "|".join(filter(None,[
        "|".join(filter(None,abbrvs)),
        abbrvKey
    ]))

def compileAbbrvRegex( abbrv ):
    return "|".join(filter(None,
        [compilePartialAbbrvRegex(abbrvKey, abbrvValue) for abbrvKey, abbrvValue in abbrv.items()]
    ))


class AddressUtils:
    subunitAbbreviations = OrderedDict([
        ('ANT',     ['ANTENNA']),
        ('APT',     ['APARTMENT']),
        ('ATM',     ['AUTOMATED TELLER MACHINE']),
        ('BBQ',     ['BARBECUE']),
        ('BTSD',    ['BOATSHED']),
        ('BLDG',    ['BUILDING']),
        ('BNGW',    ['BUNGALOW']),
        ('CAGE',    []),
        ('CARP',    ['CARPARK']),
        ('CARS',    ['CARSPACE']),
        ('CLUB',    []),
        ('COOL',    ['COOLROOM']),
        ('CTGE',    ['COTTAGE']),
        ('DUPL',    ['DUPLEX']),
        ('FCTY',    ['FACTORY', 'FY']),
        ('FLAT',    ['FLT','FL','F']),
        ('GRGE',    ['GARAGE']),
        ('HALL',    []),
        ('HSE',     ['HOUSE']),
        ('KSK',     ['KIOSK']),
        ('LSE',     ['LEASE']),
        ('LBBY',    ['LOBBY']),
        ('LOFT',    []),
        ('LOT',     []),
        ('MSNT',    ['MAISONETTE']),
        ('MBTH',    ['MARINE BERTH', 'MB']),
        ('OFFC',    ['OFFICE', 'OFF']),
        ('RESV',    ['RESERVE']),
        ('ROOM',    ['RM']),
        ('SHED',    []),
        ('SHOP',    ['SH', 'SP']),
        ('SHRM',    ['SHOWROOM']),
        ('SIGN',    []),
        ('SITE',    []),
        ('STLL',    ['STALL', 'SL']),
        ('STOR',    ['STORE']),
        ('STR',     ['STRATA UNIT']),
        ('STU',     ['STUDIO', 'STUDIO APARTMENT']),
        ('SUBS',    ['SUBSTATION']),
        ('SE',      ['SUITE']),
        ('TNCY',    ['TENANCY']),
        ('TWR',     ['TOWER']),
        ('TNHS',    ['TOWNHOUSE']),
        ('UNIT',    ['U']),
        ('VLT',     ['VAULT']),
        ('VLLA',    ['VILLA']),
        ('WARD',    []),
        ('WHSE',    ['WAREHOUSE', 'WE']),
        ('WKSH',    ['WORKSHOP'])
    ])

    stateAbbreviations = OrderedDict([
        ('WA',      ['WESTERN AUSTRALIA', 'WEST AUSTRALIA', 'WEST AUS']),
        ('ACT',     ['AUSTRALIAN CAPITAL TERRITORY', 'AUS CAPITAL TERRITORY']),
        ('NSW',     ['NEW SOUTH WALES']),
        ('NT',      ['NORTHERN TERRITORY']),
        ('QLD',     ['QUEENSLAND']),
        ('SA',      ['SOUTH AUSTRALIA']),
        ('TAS',     ['TASMAIA'])
    ])

    floorAbbreviations = OrderedDict([
        ('B',       ['BASEMENT']),
        ('G',       ['GROUND FLOOR', 'GROUND']),
        ('LG',      ['LOWER GROUND FLOOR', 'LOWER GROUND']),
        ('UG',      ['UPPER GROUND FLOOR', 'UPPER GROUND']),
        ('FL',      ['FLOOR', 'FLR']),
        ('L',       ['LEVEL', 'LVL']),
        ('M',       ['MEZZANINE', 'MEZ'])
    ])

    thoroughfareTypeAbbreviations = OrderedDict([
        ('ACCS',     ['ACCESS']),
        ('ALLY',     ['ALLEY']),
        ('ALWY',     ['ALLEYWAY']),
        ('AMBL',     ['AMBLE']),
        ('APP',      ['APPROACH']),
        ('ARC',      ['ARCADE']),
        ('ARTL',     ['ARTERIAL']),
        ('ARTY',     ['ARTERY']),
        ('AVE',      ['AVENUE','AV']),
        ('BA',       ['BANAN']),
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
        ('CIR',      ['CIRCLE']),
        ('CCT',      ['CIRCUIT']),
        ('CRCS',     ['CIRCUS']),
        ('CL',       ['CLOSE']),
        ('CON',      ['CONCOURSE']),
        ('CPS',      ['COPSE']),
        ('CNR',      ['CORNER']),
        ('CT',       ['COURT']),
        ('CTYD',     ['COURTYARD']),
        ('COVE',     []),
        ('CRES',     ['CRESCENT', 'CR']),
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
        ('GDNS',     ['GARDENS']),
        ('GTE',      ['GATE']),
        ('GLDE',     ['GLADE']),
        ('GLEN',     []),
        ('GRA',      ['GRANGE']),
        ('GRN',      ['GREEN']),
        ('GR',       ['GROVE']),
        ('HTS',      ['HEIGHTS']),
        ('HIRD',     ['HIGHROAD']),
        ('HWY',      ['HIGHWAY']),
        ('HILL',     []),
        ('INTG',     ['INTERCHANGE']),
        ('JNC',      ['JUNCTION']),
        ('KEY',      []),
        ('LANE',     []),
        ('LNWY',     ['LANEWAY']),
        ('LINE',     []),
        ('LINK',     []),
        ('LKT',      ['LOOKOUT']),
        ('LOOP',     []),
        ('MALL',     []),
        ('MNDR',     ['MEANDER']),
        ('MEWS',     []),
        ('MTWY',     ['MOTORWAY']),
        ('NOOK',     []),
        ('OTLK',     ['OUTLOOK']),
        ('PDE',      ['PARADE']),
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
        ('SHOPPING CENTRE', ["S/C", "SHOPNG CNTR", "SHOPPING CENTER", "SHOPPING CENTRE", "SHOPPING"]),
        ('PLAZA',           []),
        ('ARCADE',          []),
        ('MALL',            []),
        ('BUILDING',        ['BLDG']),
        ('FORUM',           [])
    ])

    allowedPunctuation = ['\\-', '.', '\'']
    tokenDelimeters  = [r"\s", r"\d"] + list(set(sanitationUtils.punctuationChars) - set(allowedPunctuation))
    delimeterRegex   = r"[%s]" % "".join(tokenDelimeters)
    nondelimeterRegex= r"[^%s]" % "".join(tokenDelimeters)
    clearStartRegex  = r"(?<!%s)" % nondelimeterRegex
    clearFinishRegex = r"(?!%s)" % nondelimeterRegex
    numberRangeRegex = r"(\d+) ?- ?(\d+)"
    numberAlphaRegex = r"(\d+) ?([A-Z])"
    numberSlashRegex = r"(\d+)/(\d+)"
    numberRegex      = r"(\d+)"
    nameRegex        = r"(?:%s+\s?)+" % nondelimeterRegex
    slashAbbrvRegex  = r"[A-Z]+/[A-Z]+"
    
    floorLevelRegex = r"((?P<floor_prefix>FLOOR|LEVEL|LVL) )?(?P<floor_type>%s) ?(?P<floor_number>%s)" % (
        compileAbbrvRegex(floorAbbreviations),
        numberRegex,
    )
    subunitRegex = r"(?P<subunit_type>%s) ?(?P<subunit_number>%s)" % (
        compileAbbrvRegex(subunitAbbreviations),
        "|".join([
            numberAlphaRegex,
            numberRangeRegex,
            # numberSlashRegex,
            numberRegex
        ]),
    )
    stateRegex = r"(%s)" % compileAbbrvRegex(stateAbbreviations)
    thoroughfareTypeRegex = r"(?P<thoroughfare_type>%s)" % (
        compileAbbrvRegex(thoroughfareTypeAbbreviations)
    )
    thoroughfareSuffixRegex = r"(?P<thoroughfare_suffix>%s)" % (
        compileAbbrvRegex(thoroughfareSuffixAbbreviations)
    )
    thoroughfareRegex = r"(?P<thoroughfare_number>%s)\s+(?P<thoroughfare_name>%s)\s+%s(?:\s+%s)?" % (
        "|".join([
            numberAlphaRegex,
            numberRangeRegex,
            # numberSlashRegex,
            numberRegex
        ]),
        nameRegex,
        thoroughfareTypeRegex,
        thoroughfareSuffixRegex
    )
    buildingTypeRegex = r"(?P<building_type>%s)" % (
        compileAbbrvRegex(buildingTypeAbbreviations)
    )
    buildingRegex = r"(?P<building_name>%s)\s+%s" % (
        nameRegex,
        buildingTypeRegex
    )
    weakThoroughfareTypeRegex = r"(?P<weak_thoroughfare_type>%s)" % (
        compileAbbrvRegex(thoroughfareTypeAbbreviations)
    )
    weakThoroughfareSuffixRegex = r"(?P<weak_thoroughfare_suffix>%s)" % (
        compileAbbrvRegex(thoroughfareSuffixAbbreviations)
    )
    weakThoroughfareRegex = r"(?P<weak_thoroughfare_name>%s)\s+%s(?:\s+%s)?" % (
        nameRegex,
        weakThoroughfareTypeRegex,
        weakThoroughfareSuffixRegex
    )

    addressTokenRegex = r"(%s|[^,\s\d/()-]+)" % "|".join([
        clearStartRegex + floorLevelRegex + clearFinishRegex,
        clearStartRegex + subunitRegex + clearFinishRegex,
        clearStartRegex + thoroughfareRegex + clearFinishRegex,
        clearStartRegex + buildingRegex + clearFinishRegex,
        clearStartRegex + weakThoroughfareRegex + clearFinishRegex,
        clearStartRegex + nameRegex + clearFinishRegex,
        clearStartRegex + numberRangeRegex + clearFinishRegex,
        # clearStartRegex + numberSlashRegex + clearFinishRegex,
        clearStartRegex + numberAlphaRegex + clearFinishRegex,
        clearStartRegex + numberRegex + clearFinishRegex,
        clearStartRegex + slashAbbrvRegex + clearFinishRegex,
    ])

    @staticmethod
    def wrapClearRegex(regex):
        return AddressUtils.clearStartRegex + regex + AddressUtils.clearFinishRegex

    @staticmethod
    def identifyAbbreviation(abbrvDict, string):
        for abbrvKey, abbrvs in abbrvDict.items():
            if( string in [abbrvKey] + abbrvs):
                return abbrvKey
        None

    @staticmethod
    def identifySubunit(string):
        return AddressUtils.identifyAbbreviation(AddressUtils.subunitAbbreviations, string)

    @staticmethod
    def identifyFloor(string):
        return AddressUtils.identifyAbbreviation(AddressUtils.floorAbbreviations, string)

    @staticmethod
    def getSubunit(token):
        match = re.match(
            AddressUtils.wrapClearRegex(
                AddressUtils.subunitRegex
            ),
            token
        )
        matchDict = match.groupdict() if match else None
        if(matchDict and matchDict.get('subunit_type') and matchDict.get('subunit_number')): 
            subunit_type = AddressUtils.identifySubunit(matchDict.get('subunit_type'))
            subunit_number = matchDict.get('subunit_number')
            print "FOUND SUBUNIT %s %s" % (subunit_type, subunit_number)
            return subunit_type, subunit_number
        return None

    @staticmethod
    def getFloor(token):
        match = re.match(
            AddressUtils.wrapClearRegex(
                AddressUtils.subunitRegex
            ),
            token
        )
        matchDict = match.groupdict() if match else None
        if(matchDict and matchDict.get('floor_type') and matchDict.get('floor_number') ): 
            floor_type = AddressUtils.identifyFloor(matchDict.get('floor_type'))
            floor_number = matchDict.get('floor_number')
            print "FOUND FLOOR %s %s" % (floor_type, floor_number)
            return floor_type, floor_number
        return None

    @staticmethod
    def getThoroughfare(token):
        match = re.match(
            AddressUtils.wrapClearRegex(
                AddressUtils.thoroughfareRegex
            ),
            token
        )
        matchDict = match.groupdict() if match else None
        if(matchDict and matchDict.get('thoroughfare_name') and matchDict.get('thoroughfare_type')):
            print matchDict
            thoroughfare_name = matchDict.get('thoroughfare_name')
            thoroughfare_type = matchDict.get('thoroughfare_type')
            thoroughfare_suffix = matchDict.get('thoroughfare_suffix')
            thoroughfare_number = matchDict.get('thoroughfare_number')
            print "FOUND ADDRESS (%s) %s | %s (%s)" % (
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
            AddressUtils.wrapClearRegex(
                AddressUtils.buildingRegex
            ),
            token
        )
        matchDict = match.groupdict() if match else None
        if(matchDict and matchDict.get('building_name') and matchDict.get('building_type')):
            building_name = matchDict.get('building_name')
            building_type = matchDict.get('building_type')
            print "FOUND BUILDING %s %s" % (
                building_name, 
                building_type
            )
            return building_name, building_type
        return None

    @staticmethod
    def sanitizeState(string):
        return sanitationUtils.compose(
            sanitationUtils.stripLeadingWhitespace,
            sanitationUtils.stripTailingWhitespace,
            sanitationUtils.stripExtraWhitespace,   
            sanitationUtils.stripPunctuation,
            sanitationUtils.toUpper
        )(string)

    @staticmethod
    def sanitizeAddressToken(string):
        string = sanitationUtils.stripExtraWhitespace(string)
        string = re.sub(AddressUtils.numberAlphaRegex + AddressUtils.clearStartRegex , r'\1\2', string)
        string = re.sub(AddressUtils.numberRangeRegex, r'\1-\2', string)
        if DEBUG: print "sanitizeAddressToken", sanitationUtils.makeSafeOutput( string)
        return string

    @staticmethod
    def tokenizeAddress(string):
        matches =  re.findall(
            AddressUtils.addressTokenRegex, 
            string
        )
        if DEBUG: print repr(matches)
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

class UnicodeDictWriter(UnicodeWriter):
    def __init__(self, f, fieldnames, dialect=csv.excel, encoding="utf-8", **kwds):
        UnicodeWriter.__init__(self, f, dialect, encoding, **kwds)
        self.fieldnames = fieldnames

    def writerow(self, rowDict):
        row = [unicode(rowDict.get(fieldname)) or "" for fieldname in self.fieldnames]
        UnicodeWriter.writerow(self, row)

    def writeheader(self):
        UnicodeWriter.writerow(self, self.fieldnames)

if __name__ == '__main__':
    # t1 =  TimeUtils.actStrptime("29/08/2014 9:45:08 AM")
    # t2 = TimeUtils.actStrptime("26/10/2015 11:08:31 AM")
    # t3 = TimeUtils.wpStrptime("2015-07-13 22:33:05")
    # t4 = TimeUtils.wpStrptime("2015-12-18 16:03:37")
    # print \
    #     TimeUtils.wpTimeToString(t1), \
    #     TimeUtils.wpTimeToString(t2), \
    #     TimeUtils.wpTimeToString(t3), \
    #     TimeUtils.wpTimeToString(t4)

    # n1 = u"D\u00C8RWENT"
    # n2 = u"d\u00E8rwent"
    # print sanitationUtils.unicodeToAscii(n1) , \
    #     sanitationUtils.unicodeToAscii(sanitationUtils.similarComparison(n1)), \
    #     sanitationUtils.unicodeToAscii(n2), \
    #     sanitationUtils.unicodeToAscii(sanitationUtils.similarComparison(n2))

    # p1 = "+61 04 3190 8778"
    # p2 = "04 3190 8778"
    # p3 = "+61 (08) 93848512"
    # print \
    #     sanitationUtils.similarPhoneComparison(p1), \
    #     sanitationUtils.similarPhoneComparison(p2), \
    #     sanitationUtils.similarPhoneComparison(p3)

    # print sanitationUtils.makeSafeOutput(u"asdad \u00C3 <br> \n \b")

    # tru = sanitationUtils.similarComparison(u"TRUE")

    # print \
    #     sanitationUtils.similarTruStrComparison('yes'), \
    #     sanitationUtils.similarTruStrComparison('no'), \
    #     sanitationUtils.similarTruStrComparison('TRUE'),\
    #     sanitationUtils.similarTruStrComparison('FALSE'),\
    #     sanitationUtils.similarTruStrComparison(0),\
    #     sanitationUtils.similarTruStrComparison('0'),\
    #     sanitationUtils.similarTruStrComparison(u"0")\

    # testpath = "../output/UnicodeDictWriterTest.csv"
    # with open(testpath, 'w+') as testfile:
    #     writer = UnicodeDictWriter(testfile, ['a', 'b', 'c'])
    #     writer.writeheader()
    #     writer.writerow( {'a':1, 'b':2, 'c':u"\u00C3"})

    # with open(testpath, 'r') as testfile:
    #     for line in testfile.readlines():
    #         print line[:-1]

    # print AddressUtils.addressRemoveEndWord("WEST AUSTRALIA", "WEST AUSTRALIA")

    # print AddressUtils.addressRemoveEndWord("SHOP 7 KENWICK SHOPNG CNTR BELMONT RD, KENWICK WA (", "KENWICK WA")

    print "addressTokenRegex", AddressUtils.addressTokenRegex
    print "subunitRegex", AddressUtils.subunitRegex
    print "floorLevelRegex", AddressUtils.floorLevelRegex
    print "stateRegex", AddressUtils.stateRegex
    print "delimeterRegex", AddressUtils.delimeterRegex

    print AddressUtils.getSubunit("SHOP 4 A")

    for line in [
        "8/5-7 KILVINGTON DRIVE EAST",
        "SH20 SANCTUARY LAKES SHOPPING CENTRE",
        "2 HIGH ST EAST BAYSWATER",
        "FLOREAT FORUM",
        "ANN LYONS",
        "SHOP 5, 370 VICTORIA AVE",
        "SHOP 34 ADELAIDE ARCADE",
        "SHOP 5/562 PENNANT HILLS RD",
        "MT OMMANEY SHOPPING",
        "BUCKLAND STREET",
        "6/7 118 RODWAY ARCADE",
        "INGLE FARM SHOPPING CENTRE",
        "EASTLAND SHOPPING CENTRE",
        "SHOP 3044 WESTFEILD",
        "303 HAWTHORN RD",
        "7 KALBARRI ST,  WA",
        "229 FORREST HILL CHASE",
        "THE VILLAGE SHOP 5",
        "GARDEN CITY SHOPPING CENTRE",
        "SHOP 2 EAST MALL",
        "SAMANTHA PALMER",
        "134 THE GLEN SHOPPING CENTRE",
        "SHOP 3 A, 24 TEDDER AVE",
        "SHOP 205, DANDENONG PLAZA",
        "SHOP 5 / 20 -21 OLD TOWN PLAZA",
        "18A BORONIA RD",
        "SHOP 426 LEVEL 4",
        "WATERFORD PLAZA",
        "BEAUDESERT RD",
        "173 GLENAYR AVE",
        "SHOP 14-16 ALBANY PLAZA S/C",
        "861 ALBANY HIGHWAY",
        "4/479 SYDNEY RD",
        "90 WINSTON AVE",
        "SHOP 2004 - LEVEL LG1",
        "142 THE PARADE",
        "46 MARKET STREET",
        "AUSTRALIA FAIR",
        "538 MAINS RD",
        "SHOP 28 GRENFELL ST",
        "309 MAIN ST",
        "60 TOMPSON ROAD",
        "SHOP 10 2-28 EVAN ST",
        "VENESSA MILETO",
        "BOX RD",
        "34 RAILWAY PARADE",
        "SHOP 14A WOODLAKE VILLAGE S/C",
        "17 ROKEBY RD",
        "AUSTRALIA FAIR SHOPPING",
        "SHOP 1, 18-26 ANDERSON ST",
        "INDOOROOPILLY SHOPPINGTOWN",
        "17 CASUARINA RD",
        "WHITFORDS WESTFIELD",
        "4, 175 LABOUCHERE RD",
        "2 PEEL STREET",
        "SHOP 71 THE ENTRANCE RD",
        "SHOP 2014 LEVEL 2",
        "PLAZA ARCADE",
        "SHOP 27 ADELAIDE ARCADE",
        "152 WENTWORTH RD",
        "92 PROSPECT RD",
        "31 REITA AVE",
        "33 NEW ENGLAND HWY",
        "46 HUNTER ST",
        "1/34-36 MCPHERSON ST",
        "SHOP 358",
        "147 SOUTH TCE",
        "SHOP 1003 L1",
        "357 CAMBRIDGE STREET",
        "495 BURWOOD HWY",
        "CAROUSAL MALL",
        "SHOP 22 BAYSIDE VILLAGE",
        "1/64 GYMEA BAY RD",
        "1/15 RAILWAY RD",
        "SOUTHLANDS BOULEVARD",
        "83A COMMERCIAL RD",
        u"456 ROCKY PT R\u010E",
        "95 ROCKEBY RD",
        "4/13-17 WARBURTON ST",
        "1/18 ADDISON SY",
        "SUNNYPARK",
        "SHOP 4,81 PROSPECT",
        "WESTFIELD",
        "15 - 16 KEVLAR CLOSE",
        "31",
        "3/71 DORE ST",
        "SHOP 11 RIVERSTONE PDE",
        "SOUTHERN RIVER SHOPPING CENTRE RANFORD ROAD",
        "6 RODINGA CLOSE",
        "SHOP 2013 WESTFIELDS",
        "SHOP 524 THE GLEN SHOPPING CENTRE",
        "JOONDALUP SHOPPING CENTRE",
        "48/14 JAMES PLACE",
        "3/66 TENTH AVE",
        "SHOP 23 GORDON VILLAGE ARCADE",
        "HORNSBY WESTFIELD",
        "SHOP 81",
        "215/152 BUNNERONG RD",
        "SP 1032 KNOX CITY SHOPPING CENTRE",
        "SHOP 152 RUNDLE MALL",
        "37 BURWOOD RD",
        "SHOP 52 LEVEL 3",
        "ALBANY PLAZA SHOPPING CENTRE",
        "LEVEL 3 SHOP 3094",
        "SHOP 19 B LAKE MACQUARIE",
        "18/70 HURTLE",
        "309 GEORGE ST",
        "76 EDWARDES",
        "SUNNYBANK PLAZA",
        "1/134 HIGH ST",
        "CARRUM DOWNS SHOPPING CENTER",
        "SHOP 13 1 WENTWORTH ST",
        "234 BROADWAY",
        "288 STATION ST",
        "KMART PLAZA",
        "15 FLINTLOCK CT",
        "17 O'CONNELL ST",
        "JILL STREET SHOPPING CENTRE",
        "SHOP 3, 2-10 WILLIAM THWAITES BLVD",
        "170 CLOVELLY RD",
        "SHOP 11 451 SYDNEY RD",
        "PRINCES HIGHWAY ULLADULLA",
        "WESTFIELD DONCASTER SHOPPING CENTRE",
        "153 BREBNER SR",
        "HELENSVALE TOWN CENTRE",
        "SHOP 7 A KENWICK SHOPNG CNTR 1 - 3 BELMONT RD EAST, KENWICK WA (",
        "3/3 HOWARD AVA",
        "8/2 RIDER BLVD",
        "ROBINA PARKWAY",
        "VICTORIA PT SHOPPING",
        "ROBINSON ROAD",
        "3/3 BEASLEY RD,",
        "39 HAWKESBURY RETREAT",
        "171 MORAYFIELD ROAD",
        "149 ST JOHN STREET",
        "49 GEORGE ST,  WA",
        "UNIT 1",
        "A8/90 MOUNT STREET",
        "114 / 23 CORUNNA RD",
        "43 GINGHAM STREET",
        "5 KERRY CRESCENT, WESTERN AUSTRALIA",
        "UNIT 2/33 MARTINDALE STREET",
        "207/67 WATT ST"
    ]:
        # pass
        print sanitationUtils.unicodeToAscii("%64s %64s %s" % (line, AddressUtils.tokenizeAddress(line), AddressUtils.getThoroughfare(line)))