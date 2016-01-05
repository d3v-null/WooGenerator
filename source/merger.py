import csv
from collections import OrderedDict
import os
import shutil
from utils import listUtils, sanitationUtils
from csvparse_abstract import ImportObject
from csvparse_flat import CSVParse_User, UsrObjList
from coldata import ColData_User
from tabulate import tabulate
import sys

inFolder = "../input/"
outFolder = "../output/"
logFolder = "../logs/"

maPath = os.path.join(inFolder, "export-everything-dec-23.csv")
# maPath = os.path.join(inFolder, "bad act.csv")
saPath = os.path.join(inFolder, "wordpress-export.csv")

MASTER_NAME = "ACT"
SLAVE_NAME = "WORDPRESS"

# maPath = os.path.join(inFolder, "100-act-records.csv")
# maPath = os.path.join(inFolder, "200-act-records.csv")
# saPath = os.path.join(inFolder, "100-wp-records.csv")

# master_all
# slave_all
# master_changed
# slave_changed
# master_updates
# slave_updates

#########################################
# Import Info From Spreadsheets
#########################################

print "importing data"

colData = ColData_User()
maParser = CSVParse_User(
    cols = colData.getUserCols(),
    defaults = colData.getDefaults()
)

saParser = CSVParse_User(
    cols = colData.getUserCols(),
    defaults = colData.getDefaults()
)

maParser.analyseFile(maPath)

saParser.analyseFile(saPath)

#requirements for new account in wordpress:
# email valid and direct customer TechnoTan
#no requirements for new account in act, everything goes in, but probably need email

class Match(object):
    def __init__(self, mObjects = None, sObjects = None):
        self._mObjects = mObjects or [] 
        self._sObjects = sObjects or []

    @property
    def mObjects(self):
        return self._mObjects
    
    @property
    def sObjects(self):
        return self._sObjects

    @property
    def isSingular(self):
        return len(self.mObjects) <= 1 and len(self.sObjects) <= 1

    @property
    def hasNoMaster(self):
        return len(self.mObjects) == 0

    @property
    def hasNoSlave(self):
        return len(self.sObjects) == 0

    @property
    def type(self):
        if(self.isSingular):
            if(self.hasNoMaster):
                if(not self.hasNoSlave):
                    return 'masterless'
                else:
                    return 'empty'
            elif(self.hasNoSlave):
                return 'slaveless'
            else:
                return 'pure'
        else:
            return 'duplicate'
    

    def addSObject(self, sObject):
        if sObject not in self.sObjects: self.sObjects.append(sObject)

    def addMObject(self, mObject):
        if mObject not in self.mObjects: self.mObjects.append(mObject)

    def findKeyMatches(self, keyFn):
        kMatches = {}
        for sObject in self.sObjects:
            value = keyFn(sObject)
            if not value in kMatches.keys(): 
                kMatches[value] = Match()
            kMatches[value].addSObject(sObject)
            # for mObject in self.mObjects:
            #     if keyFn(mObject) == value:
            #         kMatches[value].addMObject(mObject)
        for mObject in self.mObjects:
            value = keyFn(mObject)
            if not value in kMatches.keys():
                kMatches[value] = Match()
            kMatches[value].addMObject(mObject)
        return kMatches
    
    def WooObjListRepr(self, objs):
        length = len(objs)
        return "({0}) [{1:^200s}]".format(len(objs), ",".join(map(lambda obj: obj.__repr__()[:200/length], objs)))

    def __repr__(self):
        return " | ".join( [self.WooObjListRepr(self.mObjects), self.WooObjListRepr(self.sObjects)] ) 

    def rep_str(self):
        out  = ""
        match_type = self.type
        m_len, s_len = len(self.mObjects), len(self.sObjects)
        print_headings = False
        if(match_type in ['duplicate']):
            if(m_len > 0):
                out += "The following ACT records are diplicates"
                if(s_len > 0):
                    print_headings = True
                    out += " of the following WORDPRESS records"
            else:
                assert (s_len > 0)
                out += "The following WORDPRESS records are duplicates"
        elif(match_type in ['masterless', 'slavelaveless']):
            out += "The following records do not exist in %s" % {'masterless':'ACT', 'slaveless':'WORDPRESS'}[match_type]
        out += "\n"
        users = UsrObjList()
        if(m_len > 0):
            objs = self.mObjects
            if(print_headings): 
                heading = ImportObject({}, 'ACT')
                objs = [heading] + objs
            for obj in objs :
                users.addObject(obj)
        if(s_len > 0):
            objs = self.sObjects
            if(print_headings): 
                heading = ImportObject({}, 'WORDPRESS')
                objs = [heading] + objs
            for obj in objs:
                users.addObject(obj)
        out += users.rep_str()
        return out


def findCardMatches(match):
    return match.findKeyMatches( lambda obj: obj.MYOBID or '')

def findPCodeMatches(match):
    return match.findKeyMatches( lambda obj: obj.get('Postcode') or obj.get('Home Postcode') or '')

class MatchList(list):
    def __init__(self, indexFn = None):
        if(indexFn):
            self._indexFn = indexFn
        else:
            self._indexFn = (lambda x: x.index)
        self._sIndices = []
        self._mIndices = []

    @property
    def sIndices(self):
        return self._sIndices
    
    @property
    def mIndices(self):
        return self._mIndices

    def addMatch(self, match):
        for sObject in match.sObjects:
            sIndex = self._indexFn(sObject)
            assert sIndex not in self.sIndices
            self.sIndices.append(sIndex)
        for mObject in match.mObjects:
            mIndex = self._indexFn(mObject)
            assert mIndex not in self.mIndices
            self.mIndices.append(mIndex)
        self.append(match)

    def addMatches(self, matches):
        for match in matches:
            self.addMatch(match)

    def merge(self):
        mObjects = []
        sObjects = []
        for match in self:
            for mObj in match.mObjects:
                mObjects.append(mObj)
            for sObj in match.sObjects:
                sObjects.append(sObj)

        return Match(mObjects, sObjects)


class AbstractMatcher(object):
    def __init__(self, keyFn = None):
        # print "entering AbstractMatcher __init__"
        if(keyFn):
            # print "-> keyFn"
            self.keyFn = keyFn
        else:
            # print "-> not keyFn"
            self.keyFn = (lambda x: x.index)
        self.processRegisters = self.processRegistersNonsingular
        self.retrieveObjects = self.retrieveObjectsNonsingular
        self.mFilterFn = None
        self.fFilterFn = None
        self.clear()

    def clear(self):
        self._matches = {
            'all': MatchList(),
            'pure': MatchList(),
            'slaveless': MatchList(),
            'masterless': MatchList(),
            'duplicate': MatchList()
        }

    @property
    def matches(self):
        return self._matches['all']

    @property
    def pureMatches(self):
        return self._matches['pure']

    @property
    def slavelessMatches(self):
        return self._matches['slaveless']
    
    @property
    def masterlessMatches(self):
        return self._matches['masterless']

    @property
    def duplicateMatches(self):
        return self._matches['duplicate']

    # saRegister is in nonsingular form. regkey => [slaveObjects]
    def processRegistersNonsingular(self, saRegister, maRegister):
        # print "processing nonsingular register"
        for regKey, regValue in saRegister.items():
            maObjects = self.retrieveObjects(maRegister, regKey)
            self.processMatch(maObjects, regValue)            

    # saRegister is in singular form. regIndex => slaveObject
    def processRegistersSingular(self, saRegister, maRegister):
        # print "processing singular register"
        for regKey, regValue in saRegister.items():
            maObjects = self.retrieveObjects(maRegister, self.keyFn(regValue))
            self.processMatch(maObjects, [regValue])

    def retrieveObjectsNonsingular(self, register, key):
        # print "retrieving nonsingular object"
        return register.get(key, [])

    def retrieveObjectsSingular(self, register, key):
        # print "retrieving singular object"
        regObject = register.get(key, [])
        if(regObject):
            return [regObject]
        else:
            return []

    def get_match_type(self, match):
        return match.type

    def addMatch(self, match, match_type):
        try:
            self._matches[match_type].addMatch(match)
        except Exception as e:
            print "could not add match to " + match_type + " matches ", e
        try:
            self._matches['all'].addMatch(match)
        except Exception as e:
            print "could not add match to matches ", e

    def mFilter(self, objects):
        if(self.mFilterFn):
            return filter(self.mFilterFn, objects)
        else:
            return objects

    def sFilter(self, objects):
        if(self.fFilterFn):
            return filter(self.fFilterFn, objects)
        else:
            return objects

    def processMatch(self, maObjects, saObjects):
        maObjects = self.mFilter(maObjects)
        saObjects = self.sFilter(saObjects)
        match = Match(maObjects, saObjects)
        match_type = self.get_match_type(match)
        if(match_type and match_type != 'empty'):
            self.addMatch(match, match_type)
            # print "match_type: ", match_type

    def __repr__(self):
        repr_str = ""
        repr_str += "pure matches:\n"
        for match in self.pureMatches:
             repr_str += " -> " + repr(match) + "\n"
        repr_str += "masterless matches:\n"
        for match in self.masterlessMatches:
             repr_str += " -> " + repr(match) + "\n"
        repr_str += "slaveless matches:\n"
        for match in self.slavelessMatches:
             repr_str += " -> " + repr(match) + "\n"
        repr_str += "duplicate matches:\n"
        for match in self.duplicateMatches:
             repr_str += " -> " + repr(match) + "\n"
        return repr_str

class UsernameMatcher(AbstractMatcher):
    def __init__(self):
        super(UsernameMatcher, self).__init__( lambda x: x.username )

class FilteringMatcher(AbstractMatcher):
    def __init__(self, keyFn, sMatchIndices = [], mMatchIndices = []):
        # print "entering FilteringMatcher __init__"
        super(FilteringMatcher, self).__init__( keyFn )
        self.sMatchIndices = sMatchIndices
        self.mMatchIndices = mMatchIndices
        self.mFilterFn = lambda x: x.index not in self.mMatchIndices
        self.fFilterFn = lambda x: x.index not in self.sMatchIndices

class CardMatcher(FilteringMatcher):
    def __init__(self, sMatchIndices = [], mMatchIndices = []):
        # print "entering CardMatcher __init__"
        super(CardMatcher, self).__init__( lambda x: x.MYOBID, sMatchIndices, mMatchIndices  )

class EmailMatcher(FilteringMatcher):
    def __init__(self, sMatchIndices = [], mMatchIndices = []):
        # print "entering EmailMatcher __init__"
        super(EmailMatcher, self).__init__( lambda x: x.email.lower(), sMatchIndices, mMatchIndices )
        
class NocardEmailMatcher(EmailMatcher):
    def __init__(self, sMatchIndices = [], mMatchIndices = []):
        # print "entering NocardEmailMatcher __init__"
        super(NocardEmailMatcher, self).__init__( sMatchIndices, mMatchIndices )
        self.processRegisters = self.processRegistersSingular

# get matches

globalMatches = MatchList()
anomalousMatchLists = {}
newMasters = MatchList()
newSlaves = MatchList()
anomalousParselists = {}

def denyAnomalousMatchList(matchListType, anomalousMatchList):
    try:
        assert not anomalousMatchList
    except AssertionError as e:
        # print "could not deny anomalous match list", matchListType,  e
        if(e): pass
        anomalousMatchLists[matchListType] = anomalousMatchList

def denyAnomalousParselist(parselistType, anomalousParselist):
    try:
        assert not anomalousParselist
    except AssertionError as e:
        if(e): pass
        # print "could not deny anomalous parse list", parselistType, e
        anomalousParselists[parselistType] = anomalousParselist

# for every username in slave, check that it exists in master
    
print "processing usernames"

denyAnomalousParselist( 'saParser.nousernames', saParser.nousernames )

usernameMatcher = UsernameMatcher();
usernameMatcher.processRegisters(saParser.usernames, maParser.usernames)

denyAnomalousMatchList('usernameMatcher.slavelessMatches', usernameMatcher.slavelessMatches)
denyAnomalousMatchList('usernameMatcher.duplicateMatches', usernameMatcher.duplicateMatches)
globalMatches.addMatches( usernameMatcher.pureMatches)

print "processing cards"

#for every card in slave not already matched, check that it exists in master

denyAnomalousParselist( 'maParser.nocards', maParser.nocards )

cardMatcher = CardMatcher( globalMatches.sIndices, globalMatches.mIndices )
cardMatcher.processRegisters( saParser.cards, maParser.cards )

denyAnomalousMatchList('cardMatcher.duplicateMatches', cardMatcher.duplicateMatches)
denyAnomalousMatchList('cardMatcher.masterlessMatches', cardMatcher.masterlessMatches)

globalMatches.addMatches( cardMatcher.pureMatches)

# #for every email in slave, check that it exists in master

print "processing emails"

denyAnomalousParselist( "saParser.noemails", saParser.noemails )

emailMatcher = NocardEmailMatcher( globalMatches.sIndices, globalMatches.mIndices )
emailMatcher.processRegisters( saParser.nocards, maParser.emails)

newMasters.addMatches(emailMatcher.masterlessMatches)

newSlaves.addMatches(emailMatcher.slavelessMatches)

globalMatches.addMatches(emailMatcher.pureMatches)


# TODO: further sort emailMatcher

def hashify(in_str):
    out_str = "#" * (len(in_str) + 2) + "\n"
    out_str += "# " + in_str + "\n"
    out_str += "#" * (len(in_str) + 2) + "\n"
    return out_str

print hashify( "results")

print "\n"

print hashify( "perfect matches: (%d)" % len(globalMatches))

print "\n"

if( emailMatcher.duplicateMatches ):
    print hashify("email duplicates: (%d)" % len( emailMatcher.duplicateMatches ))
    for match in emailMatcher.duplicateMatches:
        print match.rep_str()
        print "\n"
else:
    print hashify("no email duplicates")

print "\n"

print hashify("anomalous MatchLists: ")

matchListInstructions = {
    'cardMatcher.masterlessMatches': 'The following records may have been deleted from %s because their MYOB Card ID does not exist' % MASTER_NAME
}

for matchlistType, matchList in anomalousMatchLists.items():
    print " -> ", matchListInstructions.get(matchlistType, matchlistType), "(", len(matchList), ")"     
    if( 'masterless' in matchlistType or 'slaveless' in matchlistType):
        matchList = [matchList.merge()]    
        
    for match in matchList:
        print match.rep_str()
        print "\n"
    
print hashify("anomalous ParseLists: ")

parseListInstructions = {
    "saParser.noemails" : "The following %s records have invalid emails" % SLAVE_NAME,
    "maParser.noemails" : "The following %s records have invalid emails" % MASTER_NAME,
    "maParser.nocards"  : "The following %s records have no cards" % MASTER_NAME
}

for parselistType, parseList in anomalousParselists.items():
    print " -> ", parseListInstructions.get(parselistType, parselistType), "(", len(parseList), ")"  
    usrList  = UsrObjList()
    for obj in parseList.values():
        usrList.addObject(obj)
    print usrList.rep_str()
    print "\n"

# cardMatches = []
# slavelessCardMatches = []
# masterlessCardMatches = []
# cardDuplicates = []
# cardFails = []

# for card, saObjects in saParser.cards.items():
#     print "card: ", card
#     maObjects = maParser.cards.get(card) or []
#     cardMatch = Match(maObjects, saObjects)
#     if(cardMatch.isSingular):
#         print " -> is singular!"
#         if(cardMatch.hasNoMaster):
#             masterlessCardMatches.append(cardMatch)
#         elif(cardMatch.hasNoSlave):
#             slavelessCardMatches.append(cardMatch)
#         else:
#             cardMatches.append(cardMatch)
#     else:
#         print " -> not singular"
#         cardFails.append(cardMatch)
#         print repr(cardMatch)

# #for every email in slave, check that it exists in master

# emailMatches = []
# masterlessEmailMatches = []
# slavelessEmailMatches = []
# emailDuplicates = []
# emailFails = []

# for index, saObject in saParser.nocards.items():
#     saObjects =  [saObject]
#     email = saObject.email
#     print "email: ", email
#     maObjects = maParser.emails.get(email) or []
#     emailMatch = Match(maObjects, saObjects)
#     if(emailMatch.isSingular):
#         print " -> is singular!"
#         if(emailMatch.hasNoMaster):
#             masterlessEmailMatches.append(emailMatch)
#         elif(emailMatch.hasNoSlave):
#             slavelessEmailMatches.append(emailMatch)
#         else:
#             emailMatches.append(emailMatch)
#     else:       
#         print " -> not singular"
#         if len(emailMatch.sObjects) == 1 and not emailMatch.sObjects[0].MYOBID:
#             print " -> could not reconcile"
#             print repr(emailMatch)
#             emailFails.append(emailMatch) 
#             continue

#         print " -> finding card matches"
#         print " -> associated slave objects:"
#         for saObject in saObjects:
#             print " --> ", saObject.MYOBID, " | ", saObject.username 

#         if maObjects:
#             print " -> associated master objects:"
#             for maObject in maObjects:
#                 print " --> ", maObject.MYOBID, " | ", maObject.username 
#         cardMatches = findCardMatches(emailMatch)
#         for card, cardMatch in cardMatches.items():
#             print " --> card: ", card
#             print " --> slaves: ", len(cardMatch.sObjects)
#             print " --> masters: ", len(cardMatch.mObjects)
#             if cardMatch.isSingular:
#                 print " ---> is singular!"
#                 if cardMatch.hasNoSlave:
#                     print " ---> slaveless duplicate"
#                     emailDuplicates.append(cardMatch)
#                 else:
#                     emailMatches.append(cardMatch)
#             else:
#                 print " ---> is not singular"
#                 print " ---> could not reconcile"
#                 print repr(cardMatch)
#                 emailFails.append(cardMatch)