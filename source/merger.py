import csv
from collections import OrderedDict
import os
import shutil
from utils import listUtils, sanitationUtils
from csvparse_flat import CSVParse_User
from coldata import ColData_User
import sys

inFolder = "../input/"
outFolder = "../output/"
logFolder = "../logs/"

maPath = os.path.join(inFolder, "act-export-all-changes.csv")
saPath = os.path.join(inFolder, "wordpress-export.csv")

# maPath = os.path.join(inFolder, "100-act-records.csv")
maPath = os.path.join(inFolder, "200-act-records.csv")
saPath = os.path.join(inFolder, "100-wp-records.csv")

# master_all
# slave_all
# master_changed
# slave_changed
# master_updates
# slave_updates

#########################################
# Import Info From Spreadsheets
#########################################

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
    
    def objListRepr(self, objs):
        length = len(objs)
        return "({0}) [{1:^200s}]".format(len(objs), ",".join(map(lambda obj: obj.__repr__()[:200/length], objs)))

    def __repr__(self):
        return " | ".join( [self.objListRepr(self.mObjects), self.objListRepr(self.sObjects)] ) 

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


class Matcher(object):
    def __init__(self, keyFn = None):
        self._matches = {
            'all': MatchList(),
            'pure': MatchList(),
            'slaveless': MatchList(),
            'masterless': MatchList(),
            'duplicate': MatchList()
        }
        if(keyFn):
            self._keyFn = keyFn
        else:
            self._keyFn = (lambda x: x.index)
        self.processRegisters = self.processRegistersNonsingular
        self.retrieveObjects = self.retrieveObjectsNonsingular

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

    def processRegistersNonsingular(self, saRegister, maRegister):
        # print "processing nonsingular register"
        for regKey, regValue in saRegister.items():
            maObjects = self.retrieveObjects(maRegister, regKey)
            self.processMatch(maObjects, regValue)            

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
        if(match.isSingular):
            if(match.hasNoMaster):
                return 'masterless'
            elif(match.hasNoSlave):
                return 'slaveless'
            else:
                return 'pure'
        else:
            return 'duplicate'

    def addMatch(self, match, match_type):
        try:
            self._matches[match_type].addMatch(match)
        except Exception as e:
            print "could not add match to " + match_type + " matches ", e
        try:
            self._matches['all'].addMatch(match)
        except Exception as e:
            print "could not add match to matches ", e

    def processMatch(self, maObjects, saObjects):
        match = Match(maObjects, saObjects)
        match_type = self.get_match_type(match)

        print "match_type: ", match_type
        self.addMatch(match, match_type)

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

# get matches

globalMatches = MatchList()

# for every username in slave, check that it exists in master

class UsernameMatches(Matcher):
    def __init__(self):
        super(UsernameMatches, self).__init__( lambda x: x.username )
    
usernameMatches = UsernameMatches();

assert not saParser.nousernames
usernameMatches.processRegisters(saParser.usernames, maParser.usernames)

assert not usernameMatches.slavelessMatches
assert not usernameMatches.duplicateMatches
for match in usernameMatches.pureMatches:
    globalMatches.addMatch(match)

#for every card in slave not already matched, check that it exists in master



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