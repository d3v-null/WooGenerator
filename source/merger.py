# import csv
from collections import OrderedDict
import os
# import shutil
from utils import SanitationUtils, TimeUtils #listUtils, 
from matching import Match, MatchList, UsernameMatcher, CardMatcher, NocardEmailMatcher
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
import time
import yaml
import MySQLdb
from sshtunnel import SSHTunnelForwarder

importName = time.strftime("%Y-%m-%d %H:%M:%S")
start_time = time.time()
def timediff():
    return time.time() - start_time

### DEFAULT CONFIG ###

inFolder = "../input/"
outFolder = "../output/"
logFolder = "../logs/"
srcFolder = "../source/"
pklFolder = "../pickles/"

yamlPath = "merger_config.yaml"

with open(yamlPath) as stream:
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
    ssh_user = config.get('ssh_user')
    ssh_pass = config.get('ssh_pass')
    ssh_host = config.get('ssh_host')
    ssh_port = config.get('ssh_port', 22)
    remote_bind_host = config.get('remote_bind_host', '127.0.0.1')
    remote_bind_port = config.get('remote_bind_port', 3306)
    db_user = config.get('db_user')
    db_pass = config.get('db_pass')
    db_name = config.get('db_name')
    tbl_prefix = config.get('tbl_prefix', '')

#########################################
# Set up directories
#########################################

for path in (inFolder, outFolder, logFolder, srcFolder, pklFolder):
    if not os.path.exists(path):
        os.mkdir(path)

maPath = os.path.join(inFolder, "actdata_all_2016-03-11.csv")
saPath = os.path.join(inFolder, "wordpress_export_users_all_2016-03-11.csv")

testMode = False
# testMode = True
if(testMode):
    maPath = os.path.join(inFolder, "500-act-records.csv")
    saPath = os.path.join(inFolder, "500-wp-records.csv")

fileSuffix = "_test" if testMode else ""

moPath = os.path.join(outFolder, "act_import%s.csv" % fileSuffix)
resPath = os.path.join(outFolder, "sync_report%s.html" % fileSuffix)
sqlPath = os.path.join(srcFolder, "select_userdata_modtime.sql")
pklPath = os.path.join(pklFolder, "parser_pickle%s.pkl" % fileSuffix)

#########################################
# Download / Generate Slave Parser Object
#########################################

colData = ColData_User()

saRows = []

sql_run = not testMode
sql_run = False

if sql_run: 
    with \
        SSHTunnelForwarder(
            (ssh_host, ssh_port),
            ssh_password=ssh_pass,
            ssh_username=ssh_user,
            remote_bind_address=(remote_bind_host, remote_bind_port)
        ) as server, \
        open(sqlPath) as sqlFile:
        # server.start()
        print server.local_bind_address
        conn = MySQLdb.connect(
            host='127.0.0.1',
            port=server.local_bind_port,
            user=db_user,
            passwd=db_pass,
            db=db_name)

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
        saRows = [headers] + list(cursor.fetchall())

saParser = CSVParse_User(
    cols = colData.getImportCols(),
    defaults = colData.getDefaults()
)
if saRows:
    saParser.analyseRows(saRows)
else:
    print "generating slave", timediff()
    saParser.analyseFile(saPath)
print "generated slave", timediff()

#########################################
# Generate ACT CSV files
#########################################

# TODO: This

#########################################
# Import Master Info From Spreadsheets
#########################################


print "importing data"



clear_pkl = False
try_pkl = not testMode
try_pkl = False
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
        contact_schema = 'act'
    )

    maParser.analyseFile(maPath)
    print "imported master", timediff()

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
    def oldMObject(self): return self._oldMObject
    @property
    def oldSObject(self): return self._oldSObject
    @property
    def newMObject(self): return self._newMObject
    @property
    def newSObject(self): return self._newSObject
    @property
    def syncWarnings(self): return self._syncWarnings
    @property
    def sUpdated(self): return self._newSObject
    @property
    def mUpdated(self): return self._newMObject
    @property
    def static(self): return self._static
    @property
    def importantStatic(self): return self._importantStatic
    @property
    def mTime(self): return self._mTime
    @property
    def sTime(self): return self._sTime
    @property
    def tTime(self): return self._tTime
    @property
    def bTime(self): return self._bTime
    @property
    def lTime(self): return max(self.mTime, self.sTime)
    @property
    def mMod(self): return (self.mTime >= self.tTime)
    @property
    def sMod(self): return (self.sTime >= self.tTime)
    # @property
    # def winner(self): return self._winner
    
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
            delimeter = "<br/>" if tablefmt=="html" else "\n"
            subject_fmt = "<h4>%s</h4>" if tablefmt=="html" else "%s"
            header = ["Column", "Reason", "Old", "New"]
            subjects = {}
            for col, warnings in self.syncWarnings.items():
                for subject, reason, oldVal, newVal in warnings:    
                    if subject not in subjects.keys():
                        subjects[subject] = []
                    subjects[subject] += [map( 
                        lambda x: SanitationUtils.makeSafeOutput(x)[:64], 
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
    #         oldLoserObject = self._oldSObject

    def opposite_src(self, subject):
        if subject == MASTER_NAME:
            return SLAVE_NAME
        else:
            return MASTER_NAME

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
            (info_fmt % ("Last Sale", TimeUtils.wpTimeToString(self._bTime))) if self.bTime else "No Last Sale",
            (info_fmt % ("%s Mod Time" % MASTER_NAME, TimeUtils.wpTimeToString(self.mTime))) if self.mMod else "%s Not Modded" % MASTER_NAME,
            (info_fmt % ("%s Mod Time" % SLAVE_NAME, TimeUtils.wpTimeToString(self.sTime))) if self.sMod else "%s Not Modded" % SLAVE_NAME,
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
    
print hashify("COMPLETED MERGE")
print timediff()

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

