# import csv
from collections import OrderedDict
import os
# import shutil
from utils import SanitationUtils, TimeUtils, HtmlReporter, listUtils
from matching import Match, MatchList, UsernameMatcher, CardMatcher, NocardEmailMatcher
from csvparse_flat import CSVParse_User, UsrObjList #, ImportUser
from contact_objects import ContactAddress
from coldata import ColData_User
from tabulate import tabulate
from itertools import chain
# from pprint import pprint
# import sys
from copy import deepcopy
# import pickle
import dill as pickle
from bisect import insort
import re
import time
import yaml
import MySQLdb
from sshtunnel import SSHTunnelForwarder
import io

importName = time.strftime("%Y-%m-%d %H:%M:%S")
start_time = time.time()
def timediff():
    return time.time() - start_time

DEBUG = True
testMode = False
testMode = True

### DEFAULT CONFIG ###

inFolder = "../input/"
outFolder = "../output/"
logFolder = "../logs/"
srcFolder = "../source/"
pklFolder = "../pickles/"

yamlPath = "merger_config.yaml"

userFile = cardFile = emailFile = sinceM = sinceS = False

with open(yamlPath) as stream:
    optionNamePrefix = 'test_' if testMode else ''

    config = yaml.load(stream)

    if 'inFolder' in config.keys():
        inFolder = config['inFolder']
    if 'outFolder' in config.keys():
        outFolder = config['outFolder']
    if 'logFolder' in config.keys():
        logFolder = config['logFolder']

    #mandatory
    merge_mode = config.get('merge_mode', 'sync')
    MASTER_NAME = config.get('master_name', 'MASTER')
    SLAVE_NAME = config.get('slave_name', 'SLAVE')
    DEFAULT_LAST_SYNC = config.get('default_last_sync')
    ssh_user = config.get(optionNamePrefix+'ssh_user')
    ssh_pass = config.get(optionNamePrefix+'ssh_pass')
    ssh_host = config.get(optionNamePrefix+'ssh_host')
    ssh_port = config.get(optionNamePrefix+'ssh_port', 22)
    remote_bind_host = config.get(optionNamePrefix+'remote_bind_host', '127.0.0.1')
    remote_bind_port = config.get(optionNamePrefix+'remote_bind_port', 3306)
    db_user = config.get(optionNamePrefix+'db_user')
    db_pass = config.get(optionNamePrefix+'db_pass')
    db_name = config.get(optionNamePrefix+'db_name')
    tbl_prefix = config.get(optionNamePrefix+'tbl_prefix', '')

    if 'userFile' in config.keys():
        userFile = config.get('userFile')
    if 'cardFile' in config.keys():
        cardFile = config.get('cardFile')
    if 'emailFile' in config.keys():
        emailFile = config.get('emailFile')
    if 'sinceM' in config.keys():
        sinceM = config.get('sinceM')
    if 'sinceS' in config.keys():
        sinceS = config.get('sinceS')


#########################################
# Set up directories
#########################################

for path in (inFolder, outFolder, logFolder, srcFolder, pklFolder):
    if not os.path.exists(path):
        os.mkdir(path)

# maPath = os.path.join(inFolder, "actdata_all_2016-03-11.csv")
maPath = os.path.join(inFolder, "ACT Report_Entire Database_06.04.16.csv")
saPath = os.path.join(inFolder, "wordpress_export_users_all_2016-03-11.csv")

if(testMode):
    maPath = os.path.join(inFolder, "500-act-records.csv")
    saPath = os.path.join(inFolder, "500-wp-records.csv")

fileSuffix = "_test" if testMode else ""

moPath = os.path.join(outFolder, "act_import%s.csv" % fileSuffix)
resPath = os.path.join(outFolder, "sync_report%s.html" % fileSuffix)
sqlPath = os.path.join(srcFolder, "select_userdata_modtime.sql")
pklPath = os.path.join(pklFolder, "parser_pickle%s.pkl" % fileSuffix)

#########################################
# Prepare Filter Data
#########################################

filterFiles = {
    'users': userFile, 
    'emails': emailFile, 
    'cards': cardFile,
}
filterItems = {}
if any(filterFiles) :
    for key, filterFile in filterFiles.items():
        if filterFile:
            with open(os.path.join(inFolder,filterFile) ) as filterFileObj:
                filterItems[key] = [\
                    re.sub(r'\s*([^\s].*[^\s])\s*(?:\n)', r'\1', line)\
                    for line in filterFileObj\
                ]

                # print "filterItems[%s] = %s" % (key, filterItems[key])
if sinceM:
    filterItems['sinceM'] = TimeUtils.wpStrptime(sinceM)
if sinceS:
    filterItems['sinceS'] = TimeUtils.wpStrptime(sinceS)

# filterItems = None

#########################################
# Download / Generate Slave Parser Object
#########################################

colData = ColData_User()

saRows = []

sql_run = True
sql_run = not testMode
# sql_run = False

SSHTunnelForwarderParams = {
    'ssh_address_or_host':(ssh_host, ssh_port),
    'ssh_password':ssh_pass,
    'ssh_username':ssh_user,
    'remote_bind_address':(remote_bind_host, remote_bind_port)
}
MySQLdbConnectParams = {
    'host':'127.0.0.1',
    'user':db_user,
    'passwd':db_pass,
    'db':db_name
}

if sql_run: 
    with \
        SSHTunnelForwarder(**SSHTunnelForwarderParams) as server, \
        open(sqlPath) as sqlFile:
        # server.start()
        print server.local_bind_address

        MySQLdbConnectParams['port'] = server.local_bind_port
        conn = MySQLdb.connect( **MySQLdbConnectParams )

        wpCols = colData.getWPCols()

        assert all([
            'Wordpress ID' in wpCols.keys(),
            wpCols['Wordpress ID'].get('wp', {}).get('key') == 'ID',
            wpCols['Wordpress ID'].get('wp', {}).get('final')
        ]), 'ColData should be configured correctly'
        userdata_select = ",\n\t\t\t".join([
            ("MAX(CASE WHEN um.meta_key = '%s' THEN um.meta_value ELSE \"\" END) as `%s`" if data['wp']['meta'] else "u.%s as `%s`") % (data['wp']['key'], col)\
            for col, data in wpCols.items()
        ])


        print sqlFile.read() % (userdata_select, '%susers'%tbl_prefix,'%susermeta'%tbl_prefix,'%stansync_updates'%tbl_prefix)
        sqlFile.seek(0)

        cursor = conn.cursor()
        cursor.execute(sqlFile.read() % (userdata_select, '%susers'%tbl_prefix,'%susermeta'%tbl_prefix,'%stansync_updates'%tbl_prefix))
        # headers = colData.getWPCols().keys() + ['ID', 'user_id', 'updated']
        headers = [i[0] for i in cursor.description]
        # print headers
        if testMode:
            saRows = [headers] + list(cursor.fetchall())[:100]
        else:
            saRows = [headers] + list(cursor.fetchall())

# print tabulate(saRows, tablefmt="simple")

saParser = CSVParse_User(
    cols = colData.getImportCols(),
    defaults = colData.getDefaults(),
    filterItems = filterItems
)
if saRows:
    saParser.analyseRows(saRows)
else:
    print "generating slave", timediff()
    saParser.analyseFile(saPath)
print "analysed %d slave objects" % len(saParser.objects), timediff()

#########################################
# Generate ACT CSV files using shell
#########################################

# TODO: This

#########################################
# Import Master Info From Spreadsheets
#########################################


print "importing data"



clear_pkl = False
try_pkl = not testMode
# try_pkl = False
# clear_pkl = True

if(clear_pkl): 
    try:
        os.remove(pklPath)
    except:
        pass

try:
    if try_pkl:
        pkl_file = open(pklPath, 'rb')
        maParser = pickle.load(pkl_file)
        print "loaded pickle", timediff()
    else:
        raise Exception("not trying to load pickle")
except Exception as e:
    if(e): pass
    maParser = CSVParse_User(
        cols = colData.getImportCols(),
        defaults = colData.getDefaults(),
        contact_schema = 'act',
        filterItems = filterItems
    )

    maParser.analyseFile(maPath)
    print "imported %d master objects" % len(maParser.objects), timediff()


    if try_pkl:
        pkl_file = open(pklPath, 'wb')
        print "dumping pickle", timediff()
        pickle.dump(maParser, pkl_file)

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

def printBasicColumns(users):
    usrList = UsrObjList()
    for user in users:
        usrList.addObject(user)
    print usrList.tabulate(
        OrderedDict([
            ('E-mail', {}),
            ('MYOB Card ID', {}),
            ('Address', {}),
            ('Home Address', {}),
            ('Edited in Wordpress', {})
        ]),
        tablefmt = 'html'
    )

# printBasicColumns( list(chain( *maParser.emails.values() ))[:100] )
printBasicColumns( list(chain( *saParser.emails.values() ))[:2] )

first = list(chain(*saParser.emails.values()))[0]
print first.__repr__()
print first['Edited in Wordpress']
print TimeUtils.wpStrptime(first['Edited in Wordpress'])
print first.wp_modtime

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

class SyncUpdate(object):
    def __init__(self, oldMObject, oldSObject, lastSync = DEFAULT_LAST_SYNC):
        # print "Creating SyncUpdate: ", oldMObject.__repr__(), oldSObject.__repr__()

        self.oldMObject = oldMObject
        self.oldSObject = oldSObject
        self.tTime = TimeUtils.wpStrptime( lastSync )
        self.mTime = self.oldMObject.act_modtime
        self.sTime = self.oldSObject.wp_modtime
        self.bTime = self.oldMObject.last_sale

#         print """\
# creating SyncUpdate object
#  -> %s
#  -> %s
#  -> %s
#  -> %s""" % (
#     oldMObject.__repr__(),
#     oldSObject.__repr__(),
#     self.mTime,
#     self.sTime
# )

        self._winner = SLAVE_NAME if(self.sTime >= self.mTime) else MASTER_NAME
        
        self.newSObject = False
        self.newMObject = False
        self.static = True
        self.importantStatic = True
        self.syncWarnings = OrderedDict()
        self.syncPasses = OrderedDict()
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
                self.sTime = self.tTime
                if(self.mMod):
                    self.static = False
                    # self.importantStatic = False
# 
    @property
    def sUpdated(self): return self.newSObject
    @property
    def mUpdated(self): return self.newMObject
    @property
    def lTime(self): return max(self.mTime, self.sTime)
    @property
    def mMod(self): return (self.mTime >= self.tTime)
    @property
    def sMod(self): return (self.sTime >= self.tTime)



    @property
    def winnerWPID(self):
        return self.getWinnerKey("Wordpress ID")
    # @property
    # def winner(self): return self._winner
    
    # def colBlank(self, col):
    #     mValue = (mObject.get(col) or "")
    #     sValue = (sObject.get(col) or "")
    #     return (not mValue and not sValue)

    def getWinnerKey(self, key):
        if self.syncWarnings and key in self.syncWarnings.keys():
            (subject, reason, oldVal, newVal, data) = self.syncWarnings[key]
            return newVal
        if self.syncPasses and key in self.syncPasses.keys():
            (reason, val, data) = self.syncPasses[key]
            return val
        else:
            if newSObject or newMObject:
                try:
                    vals = filter(None, [newMObject.get(key), newSObject.get(key)])
                    if any(vals):
                        return vals[0]
                except:
                    pass
            if oldSObject or oldMObject:
                try:
                    vals = filter(None, [oldMObject.get(key), oldSObject.get(key)])
                    if any(vals):
                        return vals[0]
                except:
                    pass

        return None

            

    def sanitizeValue(self, col, value):
        # print "sanitizing", col, repr(value)
        if('phone' in col.lower()):
            if('preferred' in col.lower()):
                if(value and len(SanitationUtils.stripNonNumbers(value)) > 1):
                    # print "value nullified", value
                    return ""
        return value

    def getMValue(self, col):
        return self.sanitizeValue(col, self.oldMObject.get(col) or "")

    def getSValue(self, col):
        return self.sanitizeValue(col, self.oldSObject.get(col) or "")

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

    def addSyncWarning(self, col, subject, reason, oldVal =  "", newVal = "", data = {}):
        if( col not in self.syncWarnings.keys()):
            self.syncWarnings[col] = []
        self.syncWarnings[col].append((subject, reason, oldVal, newVal, data))

    def addSyncPass(self, col, reason, val="", data={}):
        if( col not in self.syncPasses.keys()):
            self.syncPasses[col] = []
        self.syncPasses[col].append((reason, val, data))

    def displaySyncWarnings(self, tablefmt=None):
        if self.syncWarnings:
            delimeter = "<br/>" if tablefmt=="html" else "\n"
            subject_fmt = "<h4>%s</h4>" if tablefmt=="html" else "%s"
            header = ["Column", "Reason", "Old", "New"]
            subjects = {}
            for col, warnings in self.syncWarnings.items():
                for subject, reason, oldVal, newVal, data in warnings:    
                    if subject not in subjects.keys():
                        subjects[subject] = []
                    subjects[subject] += [map( 
                        lambda x: SanitationUtils.coerceBytes(x)[:64], 
                        [col, reason, oldVal, newVal] 
                    )]
            tables = []
            for subject, subjList in subjects.items():
                tables += [delimeter.join([(subject_fmt % self.opposite_src(subject)), tabulate(subjList, headers=header, tablefmt=tablefmt)])]
            return delimeter.join(tables)
        else:
            return ""

    # def getOldLoserObject(self, winner=None):
    #     if not winner: winner = self._winner
    #     if(winner == MASTER_NAME):
    #         oldLoserObject = self.oldSObject

    def opposite_src(self, subject):
        if subject == MASTER_NAME:
            return SLAVE_NAME
        else:
            return MASTER_NAME

    def loserUpdate(self, winner, col, reason = "", data={}):
        if(winner == MASTER_NAME):
            # oldLoserObject = self.oldSObject
            oldLoserValue = self.getSValue(col)
            # oldWinnerObject = self.oldMObject
            oldWinnerValue = self.getMValue(col)
            if(not self.newSObject): self.newSObject = deepcopy(sObject)
            newLoserObject = self.newSObject
        elif(winner == SLAVE_NAME):
            # oldLoserObject = self.oldMObject
            oldLoserValue = self.getMValue(col)
            # oldWinnerObject = self.oldSObject
            oldWinnerValue = self.getSValue(col)
            if(not self.newMObject): self.newMObject = deepcopy(mObject)
            newLoserObject = self.newMObject
        # if data.get('warn'): 
        self.addSyncWarning(col, winner, reason, oldLoserValue, oldWinnerValue, data)
        newLoserObject[col] = oldWinnerValue
        self.updates += 1
        if data.get('static'): 
            self.static = False
        if(reason in ['updating', 'deleting']):
            self.importantUpdates += 1
            if data.get('static'): self.importantStatic = False

    # def mUpdate(self, col, value, warn = False, reason = "", static=False):
    #     if(not self.newMObject): self.newMObject = ImportUser(mObject, mObject.rowcount, mObject.row)
    #     if static: self.static = False
    #     self.newMObject[col] = value

    # def sUpdate(self, col, value, warn = False, reason = "", static=False):
    #     if(not self.newSObject): self.newSObject = ImportUser(sObject, sObject.rowcount, sObject.row)
    #     if warn: self.addSyncWarning(col, SLAVE_NAME, reason, self.oldSObject[col], )
    #     if static: self.static = False
    #     self.newSObject[col] = value
        
    def updateCol(self, col, data={}):
        # print "sync ", col

        try:
            sync_mode = data['sync']
        except:
            return
        # sync_warn = data.get('warn')
        # syncstatic = data.get('static')
        
        # if(self.colBlank(col)): continue
        if(self.colIdentical(col)): 
            # print "-> cols identical"
            self.addSyncPass(col, "identical", self.newSObject.get(col))
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
            if(self.colSimilar(col)): 
                self.addSyncPass(col, "similar", self.newSObject.get(col))

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
        oldMatch = Match([self.oldMObject], [self.oldSObject])
        out_str += oldMatch.tabulate(tablefmt)
        out_str += subtitle_fmt % "INFO"
        out_str += info_delimeter.join(filter(None,[
            (info_fmt % ("Last Sale", TimeUtils.wpTimeToString(self.bTime))) if self.bTime else "No Last Sale",
            (info_fmt % ("%s Mod Time" % MASTER_NAME, TimeUtils.wpTimeToString(self.mTime))) if self.mMod else "%s Not Modded" % MASTER_NAME,
            (info_fmt % ("%s Mod Time" % SLAVE_NAME, TimeUtils.wpTimeToString(self.sTime))) if self.sMod else "%s Not Modded" % SLAVE_NAME,
            (info_fmt % ("static", "yes" if self.static else "no")),
            (info_fmt % ("importantStatic", "yes" if self.importantStatic else "no"))
        ]))
        out_str += subtitle_fmt % 'CHANGES (%d!%d)' % (self.updates, self.importantUpdates)
        out_str += self.displaySyncWarnings(tablefmt)
        out_str += subtitle_fmt % 'XMLRPC CHANGES'
        out_str += self.changesForXMLRPC(tablefmt)
        newMatch = Match([self.newMObject], [self.newSObject])
        out_str += subtitle_fmt % 'NEW'
        out_str += newMatch.tabulate(tablefmt)
        return out_str

    def changesForXMLRPC(self, tablefmt=None):
        if self.syncWarnings:
            info_delimeter = "\n"
            subtitle_fmt = "%s"
            if(tablefmt == "html"):
                info_delimeter = "<br/>"
                subtitle_fmt = "<h4>%s</h4>" 

            user_updates = {}
            meta_updates = {}
            for col, warnings in self.syncWarnings.items():
                for subject, reason, oldVal, newVal, data in warnings:  
                    if subject == 'ACT' and data.get('wp'):
                        data_wp = data.get('wp',{})
                        if data_wp.get('meta'):
                            meta_updates[data_wp.get('key')] = [newVal]
                        elif not data_wp.get('final'):
                            user_updates[data_wp.get('key')] = [newVal]

            #generate user_sql
            print_elements = [
                subtitle_fmt % "usermeta updates" + tabulate(meta_updates, headers="keys", tablefmt=tablefmt),
                subtitle_fmt % "user updates" + tabulate(user_updates, headers="keys", tablefmt=tablefmt)
            ]
            try:
                user_pkey = self.winnerWPID
            except :
                user_pkey = None
            if user_pkey:
                if user_updates or meta_updates :
                    all_updates = listUtils.combineOrderedDicts(user_updates , meta_updates )
                    #all_updates is in table format: k => [v]. change to k => v
                    for key, value in all_updates.items():
                        all_updates[key] = value[0]
                    all_updates_json_base64 = SanitationUtils.encodeBase64(SanitationUtils.encodeJSON(all_updates))
                    print_elements.append(all_updates_json_base64)
                    # return (user_pkey, all_updates_json_base64)
                else:
                    print_elements.append("NO XMLRPC CHANGES: no user_updates or meta_updates")    
            else:
                print_elements.append("NO XMLRPC CHANGES: must have a primary key to update user data: "+repr(user_pkey))    
            return info_delimeter.join(print_elements)
        return ""

    def __cmp__(self, other):
        return -cmp(self.bTime, other.bTime)
        # return -cmp((self.importantUpdates, self.updates, - self.lTime), (other.importantUpdates, other.updates, - other.lTime))


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
slaveUpdates = []

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

# debug stuff
# if(DEBUG):
#     print "all username matches"
#     print usernameMatcher.matches.tabulate(tablefmt="simple");

print "processing cards"

#for every card in slave not already matched, check that it exists in master

denyAnomalousParselist( 'maParser.nocards', maParser.nocards )

cardMatcher = CardMatcher( globalMatches.sIndices, globalMatches.mIndices )
cardMatcher.processRegisters( saParser.cards, maParser.cards )

denyAnomalousMatchList('cardMatcher.duplicateMatches', cardMatcher.duplicateMatches)
denyAnomalousMatchList('cardMatcher.masterlessMatches', cardMatcher.masterlessMatches)

globalMatches.addMatches( cardMatcher.pureMatches)

# if(DEBUG):
#     print "all card matches"
#     print cardMatcher.matches.tabulate(tablefmt="simple");

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
print timediff()


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
                insort(slaveUpdates, syncUpdate)

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
                insort(slaveUpdates, syncUpdate)
                # insort(staticUpdates, syncUpdate)
            if(syncUpdate.mUpdated and not syncUpdate.sUpdated):
                insort(masterUpdates, syncUpdate)
                # insort(staticMUpdates, syncUpdate)
            if(syncUpdate.sUpdated and not syncUpdate.mUpdated):
                insort(slaveUpdates, syncUpdate)
                # insort(staticSUpdates, syncUpdate)
    
print hashify("COMPLETED MERGE")
print timediff()

with io.open(resPath, 'w+', encoding='utf8') as resFile:
    reporter = HtmlReporter()

    matchingGroup = HtmlReporter.Group('matching', 'Matching Results')
    matchingGroup.addSection(
        HtmlReporter.Section(
            'perfect_matches', 
            **{
                'title': 'Perfect Matches',
                'description': "%s records match well with %s" % (SLAVE_NAME, MASTER_NAME),
                'data': globalMatches.tabulate(tablefmt="html"),
                'length': len(globalMatches)
            }
        )
    )
    matchingGroup.addSection(
        HtmlReporter.Section(
            'email_duplicates', 
            **{
                'title': 'Email Duplicates',
                'description': "%s records match with multiple records in %s on email" % (SLAVE_NAME, MASTER_NAME),
                'data': emailMatcher.duplicateMatches.tabulate(tablefmt="html"),
                'length': len(emailMatcher.duplicateMatches)
            }
        )
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
        matchingGroup.addSection(
            HtmlReporter.Section(
                matchlistType,
                **{
                    # 'title': matchlistType.title(),
                    'description': description,
                    'data': data,
                    'length': len(matchList)
                }
            )   
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

        data = usrList.tabulate(tablefmt="html")
        
        matchingGroup.addSection(
            HtmlReporter.Section(
                parselistType,
                **{
                    # 'title': matchlistType.title(),
                    'description': description,
                    'data': data,
                    'length': len(parseList)
                }
            )
        )

    reporter.addGroup(matchingGroup)

    syncingGroup = HtmlReporter.Group('sync', 'Syncing Results')

    # syncingGroup.addSection(
    #     HtmlReporter.Section(
    #         (MASTER_NAME + "_updates"),
    #         description = MASTER_NAME + " items will be updated",
    #         data = '<hr>'.join([update.tabulate(tablefmt="html") for update in masterUpdates ]),
    #         length = len(masterUpdates)
    #     )
    # )

    # syncingGroup.addSection(
    #     HtmlReporter.Section(
    #         (SLAVE_NAME + "_updates"),
    #         description = SLAVE_NAME + " items will be updated",
    #         data = '<hr>'.join([update.tabulate(tablefmt="html") for update in slaveUpdates ]),
    #         length = len(masterUpdates)
    #     )
    # )

    syncingGroup.addSection(
        HtmlReporter.Section(
            "problematic_updates",
            description = "items can't be merged because they are too dissimilar",
            data = '<hr>'.join([update.tabulate(tablefmt="html") for update in problematicUpdates ]),
            length = len(problematicUpdates)
        )
    )

    reporter.addGroup(syncingGroup)

    resFile.write( reporter.getDocumentUnicode() )


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

