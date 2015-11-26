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


#for every email in slave, check that it exists in master

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
    
    def objListRepr(self, objs):
        length = len(objs)
        return "({0}) [{1:^200s}]".format(len(objs), ",".join(map(lambda obj: obj.__repr__()[:200/length], objs)))

    def __repr__(self):
        return " | ".join( [self.objListRepr(self.mObjects), self.objListRepr(self.sObjects)] ) 

def findKeyMatches(match, keyFn):
    kMatches = {}
    for sObject in match.sObjects:
        value = keyFn(sObject)
        if not value in kMatches.keys(): kMatches[value] = Match()
        kMatches[value].addSObject(sObject)
        for mObject in match.mObjects:
            if keyFn(mObject) == value:
                kMatches[value].addMObject(mObject)
    for mObject in match.mObjects:
        value = keyFn(mObject)
        if not value in kMatches.keys():
            kMatches[value] = Match()
            kMatches[value].addMObject(mObject)
    return kMatches

def findCardMatches(match):
    return findKeyMatches(match, lambda obj: obj.MYOBID or '')

def findPCodeMatches(match):
    return findKeyMatches(match, lambda obj: obj.get('Postcode') or obj.get('Home Postcode') or '')


cardMatches = []
slavelessCardMatches = []
masterlessCardMatches = []
cardDuplicates = []
cardFails = []

for card, saObjects in saParser.cards.items():
    maObjects = maParser.cards.get(card) or []
    cardMatch = Match(maObjects, saObjects)
    if(cardMatch.isSingular):
        print " -> is singular!"
        if(cardMatch.hasNoMaster):
            masterlessCardMatches.append(cardMatch)
        elif(cardMatch.hasNoSlave):
            slavelessCardMatches.append(cardMatch)
        else:
            cardMatches.append(cardMatch)
    else:
        print " -> not singular"
        cardFails.append(cardMatch)
        print repr(cardMatch)

print "matches:"
for match in cardMatches:
    print repr(match)

print "slaveless matches:"
for match in slavelessCardMatches:
    print repr(match)    

print "masterless matches:"
for match in masterlessCardMatches:
    print repr(match)

print "failures:"
for match in cardFails:
    print repr(match)

print "duplicates:"
for match in cardDuplicates:
    print repr(match)    

# matches = []
# duplicates = []
# fails = []

# for email, saObjects in saParser.emails.items():
#     print "email: ", email
#     maObjects = maParser.emails.get(email) or []
#     emailMatch = Match(maObjects, saObjects)
#     if(emailMatch.isSingular):
#         print " -> is singular!"
#         matches.append(emailMatch)
#     else:       
#         print " -> not singular"
#         if len(emailMatch.sObjects) == 1 and not emailMatch.sObjects[0].MYOBID:
#             print " -> could not reconcile"
#             print repr(emailMatch)
#             fails.append(emailMatch) 
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
#                     duplicates.append(cardMatch)
#                 else:
#                     matches.append(cardMatch)
#             else:
#                 print " ---> is not singular"
#                 print " ---> could not reconcile"
#                 print repr(cardMatch)
#                 fails.append(cardMatch)

# print "matches:"
# for match in matches:
#     print repr(match)

# print "failures:"
# for match in fails:
#     print repr(match)

# print "duplicates:"
# for match in duplicates:
#     print repr(match)













