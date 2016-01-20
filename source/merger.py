# import csv
from collections import OrderedDict
import os
# import shutil
from utils import listUtils, SanitationUtils, TimeUtils
from csvparse_abstract import ImportObject
from csvparse_flat import CSVParse_User, UsrObjList #, ImportUser
from contact_objects import ContactAddress
from coldata import ColData_User
from tabulate import tabulate
# from pprint import pprint
# import sys
from copy import deepcopy
# import pickle
import dill as pickle
from bisect import insort
import re

inFolder = "../input/"
outFolder = "../output/"
logFolder = "../logs/"

MASTER_NAME = "ACT"
SLAVE_NAME = "WORDPRESS"
DEFAULT_LAST_SYNC = "2015-05-29 04:33:40"

merge_mode = "sync"
merge_mode = "merge"

# maPath = os.path.join(inFolder, "export-everything-dec-23.csv")
maPath = os.path.join(inFolder, "act_cilent_export_all_2016-01-15.csv")
# maPath = os.path.join(inFolder, "bad act.csv")
# saPath = os.path.join(inFolder, "wordpress_export.csv")
saPath = os.path.join(inFolder, "wordpress_export_all_2016-01-20.csv")

testMode = False
# testMode = True
if(testMode):
    maPath = os.path.join(inFolder, "200-act-records.csv")
    saPath = os.path.join(inFolder, "100-wp-records.csv")

fileSuffix = "_test" if testMode else ""

moPath = os.path.join(outFolder, "act_import%s.csv" % fileSuffix)

resPath = os.path.join(outFolder, "sync_report%s.html" % fileSuffix)

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

pkl_path = "parser_pickle.pkl"

clear_pkl = True
try_pkl = not testMode
# clear_pkl = True

if(clear_pkl): 
    try:
        os.remove(pkl_path)
    except:
        pass

colData = ColData_User()

try:
    if try_pkl:
        pkl_file = open(pkl_path, 'rb')
        maParser = pickle.load(pkl_file)
        saParser = pickle.load(pkl_file)    
    else:
        raise Exception("not trying to load pickle")
except Exception as e:
    if(e): pass
    maParser = CSVParse_User(
        cols = colData.getImportCols(),
        defaults = colData.getDefaults(),
        contact_schema = 'act'
    )

    saParser = CSVParse_User(
        cols = colData.getImportCols(),
        defaults = colData.getDefaults()
    )

    maParser.analyseFile(maPath)
    saParser.analyseFile(saPath)

    pkl_file = open(pkl_path, 'wb')
    pickle.dump(maParser, pkl_file)
    pickle.dump(saParser, pkl_file)


#requirements for new account in wordpress:
# email valid and direct customer TechnoTan
#no requirements for new account in act, everything goes in, but probably need email

# def fieldActLike(field):
    # if(SanitationUtils.unicodeToAscii(field) == SanitationUtils.unicodeToAscii(field).upper() ):
    #     return True
    # else:
    #     return False

# def addressActLike(obj):
#     for col in ['Address 1', 'Address 2', 'City', 'Home Address 1', 'Home Address 2', 'Home City', 'Home Country']:
#         if(not SanitationUtils.fieldActLike(obj.get(col) or "")):
#             return False
#     return True

# def nameActLike(obj):
#     for col in ['First Name']:
#         if(not SanitationUtils.fieldActLike(obj.get(col)) or ""):
#             return False
#     return True

capitalCols = colData.getCapitalCols()

#assumes record has at least one of all capitalized cols
def recordActLike(obj):
    recordEmpty = True
    actLike = True
    for col in capitalCols.keys():
        val = obj.get(col) or ""
        if(val): 
            recordEmpty = False
        else:
            if(not SanitationUtils.fieldActLike(val)):
                actLike = False
    if(actLike and not recordEmpty):
        return True
    else:
        return False

def contactActLike(obj):
    recordEmpty = not any(filter(None, map(lambda key: key in obj.keys(), ['First Name', 'Surname', 'Contact', 'Middle Name'])))
    names = map( lambda key: obj.get(key) or "", ['First Name', 'Middle Name', 'Surname'])
    nameSum = " ".join(filter(None, names))
    return (not recordEmpty and nameSum.upper() == obj.get('Contact', '').upper() )



# usrList = UsrObjList()
# for email, users in maParser.emails.items()[:100]:
#     for user in users:
#         usrList.addObject(user)

# print usrList.tabulate(
#     OrderedDict([
#         ('E-mail', {}),
#         ('MYOB Card ID', {}),
#         ('Address', {}),
#         ('Home Address', {})
#     ]),
#     tablefmt = 'html'
# )


# # for email, users in maParser.emails.items():
# #     for user in users:
# #         actlike = contactActLike(user)
# #         if not actlike:
# #             print "-> ", repr(user)
# #             usrList = UsrObjList()
# #             usrList.addObject(user)
# #             print usrList.tabulate(OrderedDict([
# #                 ('First Name',{}),
# #                 ('Middle Name', {}),
# #                 ('Surname',{}),
# #                 ('Contact', {})    
# #             ]))
# quit()

class Match(object):
    def __init__(self, mObjects = None, sObjects = None):
        self._mObjects = filter(None, mObjects) or [] 
        self._sObjects = filter(None, sObjects) or []

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

    def tabulate(self, tablefmt=None):
        out  = ""
        match_type = self.type
        m_len, s_len = len(self.mObjects), len(self.sObjects)
        print_headings = False
        if(match_type in ['duplicate']):
            if(m_len > 0):
                # out += "The following ACT records are diplicates"
                if(s_len > 0):
                    print_headings = True
                    # out += " of the following WORDPRESS records"
            else:
                assert (s_len > 0)
                # out += "The following WORDPRESS records are duplicates"
        elif(match_type in ['masterless', 'slavelaveless']):
            pass
            # out += "The following records do not exist in %s" % {'masterless':'ACT', 'slaveless':'WORDPRESS'}[match_type]
        # out += "\n"
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
                # pprint(obj)
                users.addObject(obj)
        out += users.tabulate(tablefmt=tablefmt)
        return out


def findCardMatches(match):
    return match.findKeyMatches( lambda obj: obj.MYOBID or '')

def findPCodeMatches(match):
    return match.findKeyMatches( lambda obj: obj.get('Postcode') or obj.get('Home Postcode') or '')

class MatchList(list):
    def __init__(self, matches=None, indexFn = None):
        if(indexFn):
            self._indexFn = indexFn
        else:
            self._indexFn = (lambda x: x.index)
        self._sIndices = []
        self._mIndices = []
        if(matches):
            for match in matches:
                assert isinstance(match, Match)
                self.addMatch(match)

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

    def tabulate(self, tablefmt=None):
        if(self):
            prefix, suffix = "", ""
            delimeter = "\n"
            if tablefmt == 'html':
                delimeter = ''
                prefix = '<div class="matchList">'
                suffix = '</div>'
            return prefix + delimeter.join(
                [match.tabulate(tablefmt=tablefmt) for match in self if match]
            ) + suffix
        else: 
            return ""



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

class SyncUpdate(object):
    def __init__(self, oldMObject, oldSObject, lastSync = DEFAULT_LAST_SYNC):
        # print "Creating SyncUpdate: ", oldMObject.__repr__(), oldSObject.__repr__()

        self._oldMObject = oldMObject
        self._oldSObject = oldSObject
        self._tTime = TimeUtils.wpStrptime( lastSync )
        self._mTime = TimeUtils.actStrptime( self._oldMObject.get('Edited in Act'))
        self._sTime = TimeUtils.wpStrptime( self._oldSObject.get('Wordpress Updated') )
        self._bTime = TimeUtils.actStrptime( self._oldMObject.get('Last Sale'))
        self._winner = SLAVE_NAME if(self._sTime >= self._mTime) else MASTER_NAME
        
        self._newSObject = False
        self._newMObject = False
        self._static = True
        self._importantStatic = True
        self._syncWarnings = OrderedDict()
        self.updates = 0
        self.importantUpdates = 0
        # self.problematic = False

        #extra heuristics for merge mode:
        if(merge_mode == 'merge' and not self.sMod):
            might_be_sEdited = False
            if not oldSObject.addressesActLike():
                might_be_sEdited = True
            elif( oldSObject.get('Home Country') == 'AU' ):
                might_be_sEdited = True
            elif oldSObject.usernameActLike():
                might_be_sEdited = True
            if(might_be_sEdited):
                # print repr(oldSObject), "might be edited"
                self._sTime = self._tTime
                if(self.mMod):
                    self._static = False
                    # self._importantStatic = False


    @property
    def oldMObject(self):
        return self._oldMObject
    
    @property
    def oldSObject(self):
        return self._oldSObject

    @property
    def newMObject(self):
        return self._newMObject
    
    @property
    def newSObject(self):
        return self._newSObject

    @property
    def syncWarnings(self):
        return self._syncWarnings

    @property
    def sUpdated(self):
        return self._newSObject

    @property
    def mUpdated(self):
        return self._newMObject

    @property
    def static(self):
        return self._static

    @property
    def importantStatic(self):
        return self._importantStatic
          
    @property
    def mTime(self):
        return self._mTime

    @property
    def sTime(self):
        return self._sTime

    @property
    def tTime(self):
        return self._tTime

    @property
    def bTime(self):
        return self._bTime

    @property
    def lTime(self):
        return max(self.mTime, self.sTime)
    
    @property
    def mMod(self):
        return (self.mTime >= self.tTime)

    @property
    def sMod(self):
        return (self.sTime >= self.tTime)

    # @property
    # def winner(self):
    #     return self._winner
    
    # def colBlank(self, col):
    #     mValue = (mObject.get(col) or "")
    #     sValue = (sObject.get(col) or "")
    #     return (not mValue and not sValue)

    def sanitizeValue(self, col, value):
        # print "sanitizing", col, repr(value)
        if('phone' in col.lower()):
            if('preferred' in col.lower()):
                if(value and len(SanitationUtils.stripNonNumbers(value)) > 1):
                    # print "value nullified", value
                    return ""
        return value

    def getMValue(self, col):
        return self.sanitizeValue(col, self._oldMObject.get(col) or "")

    def getSValue(self, col):
        return self.sanitizeValue(col, self._oldSObject.get(col) or "")

    def colIdentical(self, col):
        mValue = self.getMValue(col)
        # print "-> mValue", mValue
        sValue = self.getSValue(col)
        # print "-> sValue", sValue
        return (mValue == sValue)

    def colSimilar(self, col):
        # print "-> comparing ", col
        mValue = self.getMValue(col)
        sValue = self.getSValue(col)
        if not (mValue or sValue):
            return True
        elif not ( mValue and sValue ):
            return False
        #check if they are similar
        if( "phone" in col.lower() ):
            if( "preferred" in col.lower() ):
                mPreferred = SanitationUtils.similarTruStrComparison(mValue)
                sPreferred = SanitationUtils.similarTruStrComparison(sValue)
                # print repr(mValue), " -> ", mPreferred
                # print repr(sValue), " -> ", sPreferred
                if(mPreferred == sPreferred):
                    return True
            else:
                mPhone = SanitationUtils.similarPhoneComparison(mValue)
                sPhone = SanitationUtils.similarPhoneComparison(sValue)
                plen = min(len(mPhone), len(sPhone))
                if(plen > 7 and mPhone[-plen] == sPhone[-plen]):
                    return True
        elif( "role" in col.lower() ):
            mRole = SanitationUtils.similarComparison(mValue)
            sRole = SanitationUtils.similarComparison(sValue)
            if (mRole == 'rn'): 
                mRole = ''
            if (sRole == 'rn'): 
                sRole = ''
            if( mRole == sRole ): 
                return True
        elif( "address" in col.lower() and isinstance(mValue, ContactAddress)):
            if( mValue != sValue ):
                pass
                # print "M: ", mValue.__str__(out_schema="flat"), "S: ", sValue.__str__(out_schema="flat")
            return mValue.similar(sValue)
        else:
            if( SanitationUtils.similarComparison(mValue) == SanitationUtils.similarComparison(sValue) ):
                return True

        return False

    def addSyncWarning(self, col, subject, reason, oldVal =  "", newVal = ""):
        if( col not in self._syncWarnings.keys()):
            self._syncWarnings[col] = []
        self._syncWarnings[col].append((subject, reason, oldVal, newVal))

    def displaySyncWarnings(self, tablefmt=None):
        if self.syncWarnings:
            header = ["Column", "Source", "Reason", "Old", "New"]
            table = [header]
            for col, warnings in self.syncWarnings.items():
                for subject, reason, oldVal, newVal in warnings:    
                    table += [map( 
                        lambda x: SanitationUtils.makeSafeOutput(x)[:64], 
                        [col, subject, reason, oldVal, newVal] 
                    )]
            return tabulate(table, headers="firstrow", tablefmt=tablefmt)
        else:
            return ""

    # def getOldLoserObject(self, winner=None):
    #     if not winner: winner = self._winner
    #     if(winner == MASTER_NAME):
    #         oldLoserObject = self._oldSObject

    def loserUpdate(self, winner, col, reason = "", data={}):
        if(winner == MASTER_NAME):
            # oldLoserObject = self._oldSObject
            oldLoserValue = self.getSValue(col)
            # oldWinnerObject = self._oldMObject
            oldWinnerValue = self.getMValue(col)
            if(not self._newSObject): self._newSObject = deepcopy(sObject)
            newLoserObject = self._newSObject
        elif(winner == SLAVE_NAME):
            # oldLoserObject = self._oldMObject
            oldLoserValue = self.getMValue(col)
            # oldWinnerObject = self._oldSObject
            oldWinnerValue = self.getSValue(col)
            if(not self._newMObject): self._newMObject = deepcopy(mObject)
            newLoserObject = self._newMObject
        # if data.get('warn'): 
        self.addSyncWarning(col, winner, reason, oldLoserValue, oldWinnerValue)
        if data.get('static'): self._static = False
        newLoserObject[col] = oldWinnerValue
        self.updates += 1
        if(reason in ['updating', 'deleting']):
            self.importantUpdates += 1
            if data.get('static'): self._importantStatic = False

    # def mUpdate(self, col, value, warn = False, reason = "", static=False):
    #     if(not self._newMObject): self._newMObject = ImportUser(mObject, mObject.rowcount, mObject.row)
    #     if static: self._static = False
    #     self._newMObject[col] = value

    # def sUpdate(self, col, value, warn = False, reason = "", static=False):
    #     if(not self._newSObject): self._newSObject = ImportUser(sObject, sObject.rowcount, sObject.row)
    #     if warn: self.addSyncWarning(col, SLAVE_NAME, reason, self._oldSObject[col], )
    #     if static: self._static = False
    #     self._newSObject[col] = value
        
    def updateCol(self, col, data={}):
        # print "sync ", col

        try:
            sync_mode = data['sync']
        except:
            return
        # sync_warn = data.get('warn')
        # sync_static = data.get('static')
        
        # if(self.colBlank(col)): continue
        if(self.colIdentical(col)): 
            # print "-> cols identical"
            return
        else:
            # print "-> cols not identical"
            pass

        mValue = self.getMValue(col)
        sValue = self.getSValue(col)

        winner = self._winner
        reason = 'updating' if mValue and sValue else 'inserting'
            
        if( 'override' in str(sync_mode).lower() ):
            # reason = 'overriding'
            if( 'master' in str(sync_mode).lower() ):
                winner = MASTER_NAME
            elif( 'slave' in str(sync_mode).lower() ):
                winner = SLAVE_NAME
        else:
            if(self.colSimilar(col)): return

            if not (mValue and sValue):
                if(merge_mode == 'merge'):
                    if(winner == SLAVE_NAME and not sValue):
                        winner = MASTER_NAME
                        reason = 'merging'
                    elif(winner == MASTER_NAME and not mValue):
                        winner = SLAVE_NAME
                        reason = 'merging'
                else:
                    if(winner == SLAVE_NAME and not sValue):
                        reason = 'deleting'
                    elif(winner == MASTER_NAME and not mValue):
                        reason = 'deleting'

        self.loserUpdate(winner, col, reason, data)

    def update(self, syncCols, merge_mode):
        for col, data in syncCols.items():
            self.updateCol(col, data)

    def tabulate(self, tablefmt=None):
        subtitle_fmt = "%s"
        info_delimeter = "\n"
        info_fmt = "%s: %s"
        if(tablefmt == "html"):
            subtitle_fmt = "<h3>%s</h3>" 
            info_delimeter = "<br/>"
            info_fmt = "<strong>%s:</strong> %s"
        out_str = subtitle_fmt % "OLD"
        oldMatch = Match([self._oldMObject], [self._oldSObject])
        out_str += oldMatch.tabulate(tablefmt)
        out_str += subtitle_fmt % "INFO"
        out_str += info_delimeter.join(filter(None,[
            (info_fmt % ("Last Sale", self._bTime)) if self.bTime else "No Last Sale",
            (info_fmt % ("%s Mod Time" % MASTER_NAME, self.mTime)) if self.mMod else "%s Not Modded" % MASTER_NAME,
            (info_fmt % ("%s Mod Time" % SLAVE_NAME, self.sTime)) if self.sMod else "%s Not Modded" % SLAVE_NAME,
            (info_fmt % ("static", "yes" if self._static else "no")),
            (info_fmt % ("importantStatic", "yes" if self.importantStatic else "no"))
        ]))
        out_str += subtitle_fmt % 'CHANGES (%d!%d)' % (self.updates, self.importantUpdates)
        out_str += self.displaySyncWarnings(tablefmt)
        newMatch = Match([self._newMObject], [self._newSObject])
        out_str += subtitle_fmt % 'NEW'
        out_str += newMatch.tabulate(tablefmt)
        return out_str

    def __cmp__(self, other):
        return -cmp(self.bTime, other.bTime)
        # -cmp((self.importantUpdates, self.updates, - self.lTime), (other.importantUpdates, other.updates, - other.lTime))


# get matches

globalMatches = MatchList()
anomalousMatchLists = {}
newMasters = MatchList()
newSlaves = MatchList()
anomalousParselists = {}
nonstaticUpdates = []
nonstaticSUpdates = []
nonstaticMUpdates = []
staticUpdates = []
staticSUpdates = []
staticMUpdates = []
problematicUpdates = []
masterUpdates = []

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
    out_str = "#" * (len(in_str) + 4) + "\n"
    out_str += "# " + in_str + " #\n"
    out_str += "#" * (len(in_str) + 4) + "\n"
    return out_str


print hashify("BEGINNING MERGE")

syncCols = colData.getSyncCols()

for match in globalMatches:
    # print hashify( "MATCH NUMBER %d" % i )

    # print "-> INITIAL VALUES:"
    # print match.tabulate()

    mObject = match.mObjects[0]
    sObject = match.sObjects[0]

    syncUpdate = SyncUpdate(mObject, sObject)
    syncUpdate.update(syncCols, merge_mode)

    if(not syncUpdate.importantStatic):
        if(syncUpdate.mUpdated and syncUpdate.sUpdated):
            if(syncUpdate.sMod):
                insort(problematicUpdates, syncUpdate)
            else:
                insort(masterUpdates, syncUpdate)
        if(syncUpdate.mUpdated and not SyncUpdate.sUpdated):
            insort(nonstaticMUpdates, syncUpdate)
            if(syncUpdate.sMod):
                insort(problematicUpdates, syncUpdate)
            else:
                insort(masterUpdates, syncUpdate)
        # if(syncUpdate.sUpdated and not syncUpdate.mUpdated):
        #     insort(nonstaticSUpdates, syncUpdate)
    else:
        if(syncUpdate.sUpdated or syncUpdate.mUpdated):
            if(syncUpdate.mUpdated and syncUpdate.sUpdated):
                insort(masterUpdates, syncUpdate)
                # insort(staticUpdates, syncUpdate)
            if(syncUpdate.mUpdated and not syncUpdate.sUpdated):
                insort(masterUpdates, syncUpdate)
                # insort(staticMUpdates, syncUpdate)
            if(syncUpdate.sUpdated and not syncUpdate.mUpdated):
                pass
                # insort(staticSUpdates, syncUpdate)
            
with open(resPath, 'w+') as resFile:
    def writeSection(title, description, data, length = 0, html_class="results_section"):
        sectionID = SanitationUtils.makeSafeClass(title)
        description = "%s %s" % (str(length) if length else "No", description)
        resFile.write('<div class="%s">'% html_class )
        resFile.write('<a data-toggle="collapse" href="#%s" aria-expanded="true" data-target="#%s" aria-controls="%s">' % (sectionID, sectionID, sectionID))
        resFile.write('<h2>%s (%d)</h2>' % (title, length))
        resFile.write('</a>')
        resFile.write('<div class="collapse" id="%s">' % sectionID)
        resFile.write('<p class="description">%s</p>' % description)
        resFile.write('<p class="data">' )
        resFile.write( re.sub("<table>","<table class=\"table table-striped\">",data) )
        resFile.write('</p>')
        resFile.write('</div>')
        resFile.write('</div>')

    resFile.write('<!DOCTYPE html>')
    resFile.write('<html lang="en">')
    resFile.write('<head>')
    resFile.write("""
<!-- Latest compiled and minified CSS -->
<link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.6/css/bootstrap.min.css" integrity="sha384-1q8mTJOASx8j1Au+a5WDVnPi2lkFfwwEAa8hDDdjZlpLegxhjVME1fgjWPGmkzs7" crossorigin="anonymous">

<!-- Optional theme -->
<link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.6/css/bootstrap-theme.min.css" integrity="sha384-fLW2N01lMqjakBkx3l/M9EahuwpSfeNvV63J5ezn3uZzapT0u7EYsXMjQV+0En5r" crossorigin="anonymous">
""")
    resFile.write('<body>')
    resFile.write('<div class="matching">')
    resFile.write('<h1>%s</h1>' % 'Matching Results')
    
    writeSection(
        "Perfect Matches", 
        "%s records match well with %s" % (SLAVE_NAME, MASTER_NAME),
        globalMatches.tabulate(tablefmt="html"),
        length = len(globalMatches)
    )

    writeSection(
        "Email Duplicates",
        "%s records match with multiple records in %s on email" % (SLAVE_NAME, MASTER_NAME),
        emailMatcher.duplicateMatches.tabulate(tablefmt="html"),
        length = len(emailMatcher.duplicateMatches)
    )

    matchListInstructions = {
        'cardMatcher.masterlessMatches': '%s records do not have a corresponding CARD ID in %s (deleted?)' % (SLAVE_NAME, MASTER_NAME),
        'cardMatcher.duplicateMatches': '%s records have multiple CARD IDs in %s' % (SLAVE_NAME, MASTER_NAME),
        'usernameMatcher.slavelessMatches': '%s records have no USERNAMEs in %s' % (MASTER_NAME, SLAVE_NAME),
        'usernameMatcher.duplicateMatches': '%s records have multiple USERNAMEs in %s' % (SLAVE_NAME, MASTER_NAME)
    }

    for matchlistType, matchList in anomalousMatchLists.items():
        if not matchList:
            continue
        description = matchListInstructions.get(matchlistType, matchlistType)
        if( 'masterless' in matchlistType or 'slaveless' in matchlistType):
            data = matchList.merge().tabulate(tablefmt="html")
        else:
            data = matchList.tabulate(tablefmt="html")
        writeSection(
            matchlistType.title(),
            description,
            data,
            length = len(matchList)
        )
            
        
    # print hashify("anomalous ParseLists: ")

    parseListInstructions = {
        "saParser.noemails" : "%s records have invalid emails" % SLAVE_NAME,
        "maParser.noemails" : "%s records have invalid emails" % MASTER_NAME,
        "maParser.nocards"  : "%s records have no cards" % MASTER_NAME,
        "saParser.nousernames": "%s records have no username" % SLAVE_NAME
    }

    for parselistType, parseList in anomalousParselists.items():
        description = matchListInstructions.get(parselistType, parselistType)
        usrList  = UsrObjList()
        for obj in parseList.values():
            usrList.addObject(obj)
        

        writeSection(
            parselistType.title(),
            description,
            usrList.tabulate(tablefmt="html"),
            length = len(parseList)
        )

    resFile.write('</div>')
    resFile.write('<div class="sync">')
    resFile.write('<h1>%s</h1>' % 'Syncing Results')

    writeSection(
        (MASTER_NAME + " Updates"),
        "these items will be updated",
        '<hr>'.join([update.tabulate(tablefmt="html") for update in masterUpdates ]),
        length = len(masterUpdates)
    )

    writeSection(
        ("Problematic Updates"),
        "These items can't be merged because they are too dissimilar",
        '<hr>'.join([update.tabulate(tablefmt="html") for update in problematicUpdates ]),
        length = len(problematicUpdates)
    )

    resFile.write('</div>')
    resFile.write("""
<script src="https://ajax.googleapis.com/ajax/libs/jquery/2.1.4/jquery.min.js"></script>
<script src="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.6/js/bootstrap.min.js" integrity="sha384-0mSbJDEHialfmuBBQP6A4Qrprq5OVfW37PRR3j5ELqxss1yVqOtnepnHVP9aJ7xS" crossorigin="anonymous"></script>
""")
    resFile.write('</body>')
    resFile.write('</html>')




#uncomment below to export

# importUsers = UsrObjList()

# for update in masterUpdates:
#     importUsers.addObject(update.newMObject)

# print hashify("IMPORT USERS (%d)" % len(importUsers))

# print importUsers.tabulate()

# importUsers.exportItems(moPath, OrderedDict((col, col) for col in colData.getUserCols().keys()))

# with open(moPath) as outFile:
#     for line in outFile.readlines():
#         print line[:-1]

