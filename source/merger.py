from pprint import pprint
from collections import OrderedDict
import os
import unicodecsv
import argparse
# import shutil
from utils import SanitationUtils, TimeUtils, HtmlReporter, listUtils
from utils import Registrar, debugUtils, ProgressCounter
from matching import Match, MatchList, UsernameMatcher, CardMatcher, NocardEmailMatcher
from csvparse_flat import CSVParse_User, UsrObjList #, ImportUser
# from contact_objects import ContactAddress
from coldata import ColData_User
# from tabulate import tabulate
from itertools import chain
# from pprint import pprint
# import sys
# from copy import deepcopy
# import unicodecsv
# import pickle
# import dill as pickle
from bisect import insort
import re
import time
import yaml
# import MySQLdb
# import pymysql
# import paramiko
from sshtunnel import SSHTunnelForwarder, check_address
import io
# import wordpress_xmlrpc
from UsrSyncClient import UsrSyncClient_SSH_ACT, UsrSyncClient_JSON, UsrSyncClient_SQL_WP
from SyncUpdate import SyncUpdate
from contact_objects import FieldGroup

importName = TimeUtils.getMsTimeStamp()
start_time = time.time()

def timediff():
    return time.time() - start_time

DEBUG = False
DEBUG_PROGRESS = True
testMode = False
testMode = True

# download_slave = False
# download_master = False
# update_slave = False
# update_master = False
# download_slave = True
# download_master = True
# update_slave = True
# update_master = True
# do_problematic = False
# do_problematic = True
# do_filter = False
# do_filter = True
# FieldGroup.do_post = False
# FieldGroup.DEBUG_WARN = True
# FieldGroup.DEBUG_MESSAGE = True
# FieldGroup.DEBUG_ERROR = True


### DEFAULT CONFIG ###

inFolder = "../input/"
outFolder = "../output/"
logFolder = "../logs/"
srcFolder = "../source/"
pklFolder = "../pickles/"
remoteExportFolder = "act_usr_exp"

#TODO: if last dir is not source and source is in cwd then chdir
os.chdir('source')

yamlPath = "merger_config.yaml"

userFile = cardFile = emailFile = sinceM = sinceS = False

### OVERRIDE CONFIG WITH YAML FILE ###

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
    m_ssh_user = config.get(optionNamePrefix+'m_ssh_user')
    m_ssh_pass = config.get(optionNamePrefix+'m_ssh_pass')
    m_ssh_host = config.get(optionNamePrefix+'m_ssh_host')
    m_ssh_port = config.get(optionNamePrefix+'m_ssh_port', 22)
    remote_bind_host = config.get(optionNamePrefix+'remote_bind_host', '127.0.0.1')
    remote_bind_port = config.get(optionNamePrefix+'remote_bind_port', 3306)
    db_user = config.get(optionNamePrefix+'db_user')
    db_pass = config.get(optionNamePrefix+'db_pass')
    db_name = config.get(optionNamePrefix+'db_name')
    db_charset = config.get(optionNamePrefix+'db_charset', 'utf8mb4')
    wp_srv_offset = config.get(optionNamePrefix+'wp_srv_offset', 0)
    m_db_user = config.get(optionNamePrefix+'m_db_user')
    m_db_pass = config.get(optionNamePrefix+'m_db_pass')
    m_db_name = config.get(optionNamePrefix+'m_db_name')
    m_db_host = config.get(optionNamePrefix+'m_db_host')
    m_x_cmd = config.get(optionNamePrefix+'m_x_cmd')
    m_i_cmd = config.get(optionNamePrefix+'m_i_cmd')
    tbl_prefix = config.get(optionNamePrefix+'tbl_prefix', '')
    wp_user = config.get(optionNamePrefix+'wp_user', '')
    wp_pass = config.get(optionNamePrefix+'wp_pass', '')
    store_url = config.get(optionNamePrefix+'store_url', '')
    master_file = config.get('master_file', '')
    slave_file = config.get('slave_file', '')
    userFile = config.get('userFile')
    cardFile = config.get('cardFile')
    emailFile = config.get('emailFile')
    sinceM = config.get('sinceM')
    sinceS = config.get('sinceS')
    download_slave = config.get('download_slave')
    download_master = config.get('download_master')
    update_slave = config.get('update_slave')
    update_master = config.get('update_master')
    do_filter = config.get('do_filter')
    do_problematic = config.get('do_problematic')
    do_post = config.get('do_post')
    do_sync = config.get('do_sync')

### OVERRIDE CONFIG WITH ARGPARSE ###

parser = argparse.ArgumentParser(description = 'Merge contact records between two databases')
group = parser.add_mutually_exclusive_group()
group.add_argument("-v", "--verbosity", action="count",
                    help="increase output verbosity")
group.add_argument("-q", "--quiet", action="store_true")
parser.add_argument('--testmode', help='Run in test mode with test servers',
                    action='store_true')
group = parser.add_mutually_exclusive_group()
group.add_argument('--download-master', help='download the master data',
                   action="store_true", default=None)
group.add_argument('--skip-download-master', help='use the local master file instead\
    of downloading the master data', action="store_false", dest='download_master')
group = parser.add_mutually_exclusive_group()
group.add_argument('--download-slave', help='download the slave data',
                   action="store_true", default=None)
group.add_argument('--skip-download-slave', help='use the local slave file instead\
    of downloading the slave data', action="store_false", dest='download_slave')
group = parser.add_mutually_exclusive_group()
group.add_argument('--update-master', help='update the master database',
                   action="store_true", default=None)
group.add_argument('--skip-update-master', help='don\'t update the master database',
                   action="store_false", dest='update_master')
group = parser.add_mutually_exclusive_group()
group.add_argument('--update-slave', help='update the slave database',
                   action="store_true", default=None)
group.add_argument('--skip-update-slave', help='don\'t update the slave database',
                   action="store_false", dest='update_slave')
group = parser.add_mutually_exclusive_group()
group.add_argument('--do-filter', help='filter the databases',
                   action="store_true", default=None)
group.add_argument('--skip-filter', help='don\'t filter the databases',
                   action="store_false", dest='do_filter')
group = parser.add_mutually_exclusive_group()
group.add_argument('--do-sync', help='sync the databases',
                   action="store_true", default=None)
group.add_argument('--skip-sync', help='don\'t sync the databases',
                   action="store_false", dest='do_sync')
group = parser.add_mutually_exclusive_group()
group.add_argument('--do-post', help='post process the contacts',
                   action="store_true", default=None)
group.add_argument('--skip-post', help='don\'t post process the contacts',
                   action="store_false", dest='do_post')

parser.add_argument('--m-ssh-host', help='location of master ssh server')
parser.add_argument('--m-ssh-port', type=int, help='location of master ssh port')
parser.add_argument('--limit', type=int, help='global limit of objects to process')
args = parser.parse_args()
if args:
    print args
    if args.verbosity > 0:
        DEBUG_PROGRESS = True
        DEBUG_ERROR = True
    if args.verbosity > 1:
        DEBUG = True
    if args.testmode is not None:
        testMode = args.testmode
    if args.download_slave is not None:
        download_slave = args.download_slave
    if args.download_master is not None:
        download_master = args.download_master
    if args.update_slave is not None:
        update_slave = args.update_slave
    if args.update_master is not None:
        update_master = args.update_master
    if args.do_filter is not None:
        do_filter = args.do_filter
    if args.do_sync is not None:
        do_sync = args.do_sync
    if args.do_post is not None:
        do_post = args.do_post
    if args.m_ssh_port:
        m_ssh_port = args.m_ssh_port
    if args.m_ssh_host:
        m_ssh_host = args.m_ssh_host
    global_limit = args.limit



### DISPLAY CONFIG ###
if DEBUG:
    if testMode:
        print "testMode enabled"
    if not download_slave:
        print "no download_slave"
    if not download_master:
        print "no download_master"
    if not update_master:
        print "not updating maseter"
    if not update_slave:
        print "not updating slave"
    if not do_filter:
        print "not doing filter"
    if not do_sync:
        print "not doing sync"
    if not do_post:
        print "not doing post"
    print "master ssh host", m_ssh_host
    print "master ssh port", m_ssh_port

### PROCESS CLASS PARAMS ###

FieldGroup.do_post = do_post
SyncUpdate.setGlobals( MASTER_NAME, SLAVE_NAME, merge_mode, DEFAULT_LAST_SYNC)
TimeUtils.setWpSrvOffset(wp_srv_offset)

### SET UP DIRECTORIES ###

for path in (inFolder, outFolder, logFolder, srcFolder, pklFolder):
    if not os.path.exists(path):
        os.mkdir(path)

fileSuffix = "_test" if testMode else ""
fileSuffix += "_filter" if do_filter else ""
m_x_filename = "act_x"+fileSuffix+"_"+importName+".csv"
m_i_filename = "act_i"+fileSuffix+"_"+importName+".csv"
s_x_filename = "wp_x"+fileSuffix+"_"+importName+".csv"
remoteExportPath = os.path.join(remoteExportFolder, m_x_filename)
maPath = os.path.join(inFolder, m_x_filename)
maEncoding = "utf-8"

saPath = os.path.join(inFolder, s_x_filename)
saEncoding = "utf8"

if not download_master:
    # maPath = os.path.join(inFolder, "act_x_test_2016-05-03_23-01-48.csv")
    maPath = os.path.join(inFolder, master_file)
    # maPath = os.path.join(inFolder, "500-act-records-edited.csv")
    # maPath = os.path.join(inFolder, "500-act-records.csv")
    maEncoding = "utf8"
if not download_slave:
    saPath = os.path.join(inFolder, slave_file)
    # saPath = os.path.join(inFolder, "500-wp-records-edited.csv")
    saEncoding = "utf8"

moPath = os.path.join(outFolder, m_i_filename)
resPath = os.path.join(outFolder, "sync_report%s.html" % fileSuffix)
WPresCsvPath = os.path.join(outFolder, "sync_report_wp%s.csv" % fileSuffix)
ACTresCsvPath = os.path.join(outFolder, "sync_report_act%s.csv" % fileSuffix)
ACTDeltaCsvPath = os.path.join(outFolder, "delta_report_act%s.csv" % fileSuffix)
WPDeltaCsvPath = os.path.join(outFolder, "delta_report_wp%s.csv" % fileSuffix)
mFailPath = os.path.join(outFolder, "act_fails%s.csv" % fileSuffix)
sFailPath = os.path.join(outFolder, "wp_fails%s.csv" % fileSuffix)
sqlPath = os.path.join(srcFolder, "select_userdata_modtime.sql")
# pklPath = os.path.join(pklFolder, "parser_pickle.pkl" )
pklPath = os.path.join(pklFolder, "parser_pickle%s.pkl" % fileSuffix )
logPath = os.path.join(logFolder, "log_%s.txt" % importName)

### PROCESS OTHER CONFIG ###

assert store_url, "store url must not be blank"
xmlrpc_uri = store_url + 'xmlrpc.php'
json_uri = store_url + 'wp-json/wp/v2'

actFields = ";".join(ColData_User.getACTImportCols())

jsonConnectParams = {
    'json_uri': json_uri,
    'wp_user': wp_user,
    'wp_pass': wp_pass
}

sqlConnectParams = {

}

actConnectParams = {
    'hostname':    m_ssh_host,
    'port':        m_ssh_port,
    'username':    m_ssh_user,
    'password':    m_ssh_pass,
}

actDbParams = {
    'db_x_exe':m_x_cmd,
    'db_i_exe':m_i_cmd,
    'db_name': m_db_name,
    'db_host': m_db_host,
    'db_user': m_db_user,
    'db_pass': m_db_pass,
    'fields' : actFields,
}
if sinceM: actDbParams['since'] = sinceM

fsParams = {
    'importName': importName,
    'remoteExportFolder': remoteExportFolder,
    'inFolder': inFolder,
    'outFolder': outFolder
}

#########################################
# Prepare Filter Data
#########################################

print debugUtils.hashify("PREPARE FILTER DATA"), timediff()

if do_filter:
    filterFiles = {
        'users': userFile,
        'emails': emailFile,
        'cards': cardFile,
    }
    filterItems = {}
    if any(filterFiles) :
        for key, filterFile in filterFiles.items():
            try:
                with open(os.path.join(inFolder,filterFile) ) as filterFileObj:
                    filterItems[key] = [\
                        re.sub(r'\s*([^\s].*[^\s])\s*(?:\n)', r'\1', line)\
                        for line in filterFileObj\
                    ]
            except IOError, e:
                SanitationUtils.safePrint("could not open %s file [%s] from %s" % (
                    key,
                    filterFile,
                    unicode(os.getcwd())
                ))
                raise e
    if sinceM:
        filterItems['sinceM'] = TimeUtils.wpStrptime(sinceM)
    if sinceS:
        filterItems['sinceS'] = TimeUtils.wpStrptime(sinceS)
else:
    filterItems = None

#########################################
# Download / Generate Slave Parser Object
#########################################

print debugUtils.hashify("Download / Generate Slave Parser Object"), timediff()

saParser = CSVParse_User(
    cols = ColData_User.getWPImportCols(),
    defaults = ColData_User.getDefaults(),
    filterItems = filterItems,
    limit = global_limit
)
if download_slave:
    SSHTunnelForwarderAddress = (ssh_host, ssh_port)
    SSHTunnelForwarderBindAddress = (remote_bind_host, remote_bind_port)
    for host in ['SSHTunnelForwarderAddress', 'SSHTunnelForwarderBindAddress']:
        try:
            check_address(eval(host))
        except Exception, e:
            assert not e, "Host must be valid: %s [%s = %s]" % (str(e), host, repr(eval(host)))
    SSHTunnelForwarderParams = {
        'ssh_address_or_host':SSHTunnelForwarderAddress,
        'ssh_password':ssh_pass,
        'ssh_username':ssh_user,
        'remote_bind_address': SSHTunnelForwarderBindAddress,
    }
    PyMySqlConnectParams = {
        'host' : 'localhost',
        'user' : db_user,
        'password': db_pass,
        'db'   : db_name,
        'charset': db_charset,
        'use_unicode': True,
        'tbl_prefix': tbl_prefix,
    }
    with UsrSyncClient_SQL_WP(SSHTunnelForwarderParams, PyMySqlConnectParams) as client:
        client.analyseRemote(saParser)
        #
        # if testMode:
        #     client.analyseRemote(saParser, limit=1000)
        # else:
        #     client.analyseRemote(saParser)

        saParser.getObjList().exportItems(os.path.join(inFolder, s_x_filename),
                                          ColData_User.getWPImportColNames())

else:
    saParser.analyseFile(saPath, saEncoding)


# CSVParse_User.printBasicColumns( list(chain( *saParser.emails.values() )) )

#########################################
# Generate and Analyse ACT CSV files using shell
#########################################

maParser = CSVParse_User(
    cols = ColData_User.getACTImportCols(),
    defaults = ColData_User.getDefaults(),
    contact_schema = 'act',
    filterItems = filterItems,
    limit = global_limit
)

print debugUtils.hashify("Generate and Analyse ACT data"), timediff()

if download_master:

    for thing in ['m_x_cmd', 'm_i_cmd', 'remoteExportFolder', 'actFields']:
        assert eval(thing), "missing mandatory command component '%s'" % thing

    with UsrSyncClient_SSH_ACT(actConnectParams, actDbParams, fsParams) as masterClient:
        masterClient.analyseRemote(maParser)
else:
    maParser.analyseFile(maPath)

# CSVParse_User.printBasicColumns( list(chain( *maParser.emails.values()[:100] )) )

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
# staticSUpdates = []
# staticMUpdates = []
problematicUpdates = []
masterUpdates = []
slaveUpdates = []
mDeltaUpdates = []
sDeltaUpdates = []
emailConflictMatches = MatchList()

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


if do_sync:
    # for every username in slave, check that it exists in master
    print "processing usernames"
    denyAnomalousParselist( 'saParser.nousernames', saParser.nousernames )

    usernameMatcher = UsernameMatcher()
    usernameMatcher.processRegisters(saParser.usernames, maParser.usernames)

    denyAnomalousMatchList('usernameMatcher.slavelessMatches', usernameMatcher.slavelessMatches)
    denyAnomalousMatchList('usernameMatcher.duplicateMatches', usernameMatcher.duplicateMatches)
    globalMatches.addMatches( usernameMatcher.pureMatches)

    # debug stuff
    # if(DEBUG):
    #     print "all username matches"
    #     print usernameMatcher.matasdadches.tabulate(tablefmt="simple");

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

    denyAnomalousParselist("saParser.noemails", saParser.noemails)

    emailMatcher = NocardEmailMatcher(globalMatches.sIndices, globalMatches.mIndices)
    emailMatcher.processRegisters(saParser.nocards, maParser.emails)

    newMasters.addMatches(emailMatcher.masterlessMatches)

    newSlaves.addMatches(emailMatcher.slavelessMatches)

    globalMatches.addMatches(emailMatcher.pureMatches)


    # TODO: further sort emailMatcher

    print debugUtils.hashify("BEGINNING MERGE (%d)" % len(globalMatches))
    print timediff()


    syncCols = ColData_User.getSyncCols()

    if DEBUG_PROGRESS:
        syncProgressCounter = ProgressCounter(len(globalMatches))

    for count, match in enumerate(globalMatches):
        if DEBUG_PROGRESS:
            syncProgressCounter.maybePrintUpdate(count)

        mObject = match.mObjects[0]
        sObject = match.sObjects[0]

        syncUpdate = SyncUpdate(mObject, sObject)
        syncUpdate.update(syncCols)

        # SanitationUtils.safePrint( syncUpdate.tabulate(tablefmt = 'simple'))

        # if syncUpdate.mUpdated and syncUpdate.mDeltas:
        #     insort(mDeltaUpdates, syncUpdate)
        #
        # if syncUpdate.sUpdated and syncUpdate.sDeltas:
        #     insort(sDeltaUpdates, syncUpdate)

        if not syncUpdate:
            continue

        if syncUpdate.MYOBID == 'C000007':
            print "found C000007", syncUpdate.tabulate()

        if syncUpdate.sUpdated:
            syncSlaveUpdates = syncUpdate.getSlaveUpdates()
            if syncUpdate.MYOBID == 'C000007':
                print syncSlaveUpdates
            if 'E-mail' in syncSlaveUpdates:
                newEmail = syncSlaveUpdates['E-mail']
                print "updating slave email: ", newEmail
                if newEmail in saParser.emails:
                    mObjects = [mObject]
                    sObjects = [sObject] + saParser.emails[newEmail]
                    print "duplicate emails", mObjects, sObjects
                    emailConflictMatches.addMatch(Match(mObjects, sObjects))


        if(not syncUpdate.importantStatic):
            if(syncUpdate.mUpdated and syncUpdate.sUpdated):
                if(syncUpdate.sMod):
                    insort(problematicUpdates, syncUpdate)
                    continue
            elif(syncUpdate.mUpdated and not SyncUpdate.sUpdated):
                insort(nonstaticMUpdates, syncUpdate)
                if(syncUpdate.sMod):
                    insort(problematicUpdates, syncUpdate)
                    continue
            elif(syncUpdate.sUpdated and not syncUpdate.mUpdated):
                insort(nonstaticSUpdates, syncUpdate)
                if(syncUpdate.sMod):
                    insort(problematicUpdates, syncUpdate)
                    continue

        if(syncUpdate.sUpdated or syncUpdate.mUpdated):
            insort(staticUpdates, syncUpdate)
            if(syncUpdate.mUpdated and syncUpdate.sUpdated):
                insort(masterUpdates, syncUpdate)
                insort(slaveUpdates, syncUpdate)
            if(syncUpdate.mUpdated and not syncUpdate.sUpdated):
                insort(masterUpdates, syncUpdate)
            if(syncUpdate.sUpdated and not syncUpdate.mUpdated):
                insort(slaveUpdates, syncUpdate)

    print debugUtils.hashify("COMPLETED MERGE")
    print timediff()

#########################################
# Write Report
#########################################

print debugUtils.hashify("Write Report")
print timediff()

with io.open(resPath, 'w+', encoding='utf8') as resFile:
    reporter = HtmlReporter()

    basic_cols = ColData_User.getBasicCols()
    address_cols = OrderedDict(basic_cols.items() + [
        ('address_reason', {}),
        ('Edited Address', {}),
        ('Edited Alt Address', {}),
    ])
    name_cols = OrderedDict(basic_cols.items() + [
        ('name_reason', {}),
        ('Edited Name', {}),
    ])
    csv_colnames = ColData_User.getColNames(
        OrderedDict(basic_cols.items() + ColData_User.nameCols([
            'address_reason',
            'name_reason',
            'Edited Name',
            'Edited Address',
            'Edited Alt Address',
        ]).items()))
    # csv_colnames = colData.getColNames(OrderedDict(basic_cols.items() + [
    #     ('address_reason', {}),
    #     ('name_reason', {}),
    #     ('Edited Name', {}),
    #     ('Edited Address', {}),
    #     ('Edited Alt Address', {}),
    # ]))
    # print repr(basic_colnames)
    unicode_colnames = map(SanitationUtils.coerceUnicode, csv_colnames.values())
    # print repr(unicode_colnames)
    # WPCsvWriter = DictWriter(WPresCsvFile, fieldnames = unicode_colnames, extrasaction = 'ignore' )
    # WPCsvWriter.writeheader()
    # ACTCsvWriter = DictWriter(ACTresCsvFile, fieldnames = unicode_colnames, extrasaction = 'ignore' )
    # ACTCsvWriter.writeheader()

    sanitizingGroup = HtmlReporter.Group('sanitizing', 'Sanitizing Results')

    # s_bad_addresses_usrlist = UsrObjList(saParser.badAddress.values())

    # for user in saParser.badAddress.values():
    #     # user['address_reason'] = ''.join([address.reason for address in addresses])
    #     s_bad_addresses_usrlist.addObject(user)

    sanitizingGroup.addSection(
        HtmlReporter.Section(
            's_bad_addresses_list',
            title = 'Bad %s Address List' % SLAVE_NAME.title(),
            description = '%s records that have badly formatted addresses' % SLAVE_NAME,
            data = UsrObjList(saParser.badAddress.values()).tabulate(
                cols = address_cols,
                tablefmt='html',
            ),
            length = len(saParser.badAddress)
        )
    )

    # for row in saParser.badAddress.values():
    #     WPCsvWriter.writerow(OrderedDict(map(SanitationUtils.coerceUnicode, (key, value))  for key, value in row.items()))

    sanitizingGroup.addSection(
        HtmlReporter.Section(
            's_bad_names_list',
            title = 'Bad %s Names List' % SLAVE_NAME.title(),
            description = '%s records that have badly formatted names' % SLAVE_NAME,
            data = UsrObjList(saParser.badName.values()).tabulate(
                cols = name_cols,
                tablefmt='html',
            ),
            length = len(saParser.badName)
        )
    )
    if saParser.badName or saParser.badAddress:
        UsrObjList(saParser.badName.values() + maParser.badAddress.values()).exportItems(WPresCsvPath, csv_colnames)

    # for row in saParser.badName.values():
    #     WPCsvWriter.writerow(OrderedDict(map(SanitationUtils.coerceUnicode, (key, value))  for key, value in row.items()))

    sanitizingGroup.addSection(
        HtmlReporter.Section(
            'm_bad_addresses_list',
            title = 'Bad %s Address List' % MASTER_NAME.title(),
            description = '%s records that have badly formatted addresses' % MASTER_NAME,
            data = UsrObjList(maParser.badAddress.values()).tabulate(
                cols = address_cols,
                tablefmt='html',
            ),
            length = len(maParser.badAddress)
        )
    )

    # for row in maParser.badAddress.values():
    #     ACTCsvWriter.writerow(OrderedDict(map(SanitationUtils.coerceUnicode, (key, value))  for key, value in row.items()))

    sanitizingGroup.addSection(
        HtmlReporter.Section(
            'm_bad_names_list',
            title = 'Bad %s Names List' % MASTER_NAME.title(),
            description = '%s records that have badly formatted names' % MASTER_NAME,
            data = UsrObjList(maParser.badName.values()).tabulate(
                cols = name_cols,
                tablefmt='html',
            ),
            length = len(maParser.badName)
        )
    )

    # for row in maParser.badName.values():
    #     ACTCsvWriter.writerow(OrderedDict(map(SanitationUtils.coerceUnicode, (key, value))  for key, value in row.items()))
    if maParser.badName or maParser.badAddress:
        UsrObjList(maParser.badName.values() + maParser.badAddress.values())\
            .exportItems(ACTresCsvPath, csv_colnames)

    reporter.addGroup(sanitizingGroup)

    report_deltas = do_sync
    if report_deltas:

        deltaGroup = HtmlReporter.Group('deltas', 'Field Changes')

        mDeltaList = UsrObjList(filter(None,
                            [syncUpdate.newMObject for syncUpdate in mDeltaUpdates]))

        sDeltaList = UsrObjList(filter(None,
                            [syncUpdate.newSObject for syncUpdate in sDeltaUpdates]))

        deltaCols = ColData_User.getDeltaCols()

        allDeltaCols = OrderedDict(
            ColData_User.getBasicCols().items() +
            ColData_User.nameCols(deltaCols.keys()+deltaCols.values()).items()
        )

        deltaGroup.addSection(
            HtmlReporter.Section(
                'm_deltas',
                title = '%s Changes List' % MASTER_NAME.title(),
                description = '%s records that have changed important fields' % MASTER_NAME,
                data = mDeltaList.tabulate(
                    cols=allDeltaCols,
                    tablefmt='html'),
                length = len(mDeltaList)
            )
        )

        deltaGroup.addSection(
            HtmlReporter.Section(
                's_deltas',
                title = '%s Changes List' % SLAVE_NAME.title(),
                description = '%s records that have changed important fields' % SLAVE_NAME,
                data = sDeltaList.tabulate(
                    cols=allDeltaCols,
                    tablefmt='html'),
                length = len(sDeltaList)
            )
        )

        reporter.addGroup(deltaGroup)
        if mDeltaList:
            mDeltaList.exportItems(ACTDeltaCsvPath, ColData_User.getColNames(allDeltaCols))
        if sDeltaList:
            sDeltaList.exportItems(WPDeltaCsvPath, ColData_User.getColNames(allDeltaCols))


    report_matching = do_sync
    if report_matching:

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

        data = emailConflictMatches.tabulate(tablefmt="html")
        matchingGroup.addSection(
            HtmlReporter.Section(
                "email conflicts",
                **{
                    # 'title': matchlistType.title(),
                    'description': "email conflicts",
                    'data': data,
                    'length': len(emailConflictMatches)
                }
            )
        )

        # print debugUtils.hashify("anomalous ParseLists: ")

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

    report_sync = do_sync
    if report_sync:
        syncingGroup = HtmlReporter.Group('sync', 'Syncing Results')

        syncingGroup.addSection(
            HtmlReporter.Section(
                (MASTER_NAME + "_updates"),
                description = MASTER_NAME + " items will be updated",
                data = '<hr>'.join([update.tabulate(tablefmt="html") for update in masterUpdates ]),
                length = len(masterUpdates)
            )
        )

        syncingGroup.addSection(
            HtmlReporter.Section(
                (SLAVE_NAME + "_updates"),
                description = SLAVE_NAME + " items will be updated",
                data = '<hr>'.join([update.tabulate(tablefmt="html") for update in slaveUpdates ]),
                length = len(slaveUpdates)
            )
        )

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

#########################################
# Update databases
#########################################

allUpdates = staticUpdates
if do_problematic:
    allUpdates += problematicUpdates

print debugUtils.hashify("Update databases (%d)" % len(allUpdates))
print timediff()

masterFailures = []
slaveFailures = []

if allUpdates:
    if DEBUG_PROGRESS:
        updateProgressCounter = ProgressCounter(len(allUpdates))

    with \
        UsrSyncClient_SSH_ACT(actConnectParams, actDbParams, fsParams) as masterClient, \
        UsrSyncClient_JSON(jsonConnectParams) as slaveClient:

        for count, update in enumerate(allUpdates):
            if DEBUG_PROGRESS:
                updateProgressCounter.maybePrintUpdate(count)
            if update.WPID == '1':
                print repr(update.WPID)
                continue
            if update_master and update.mUpdated :
                try:
                    update.updateMaster(masterClient)
                except Exception, e:
                    masterFailures.append({
                        'update':update,
                        'master':SanitationUtils.coerceUnicode(update.newMObject),
                        'slave':SanitationUtils.coerceUnicode(update.newSObject),
                        'mchanges':SanitationUtils.coerceUnicode(update.getMasterUpdates()),
                        'schanges':SanitationUtils.coerceUnicode(update.getSlaveUpdates()),
                        'exception':repr(e)
                    })
                    SanitationUtils.safePrint("ERROR UPDATING MASTER (%s): %s" % (update.MYOBID, repr(e) ) )
                    # continue
            if update_slave and update.sUpdated :
                try:
                    update.updateSlave(slaveClient)
                except Exception, e:
                    slaveFailures.append({
                        'update':update,
                        'master':SanitationUtils.coerceUnicode(update.newMObject),
                        'slave':SanitationUtils.coerceUnicode(update.newSObject),
                        'mchanges':SanitationUtils.coerceUnicode(update.getMasterUpdates()),
                        'schanges':SanitationUtils.coerceUnicode(update.getSlaveUpdates()),
                        'exception':repr(e)
                    })
                    SanitationUtils.safePrint("ERROR UPDATING SLAVE (%s): %s" % (update.WPID, repr(e) ) )

def outputFailures(failures, filePath):
    with open(filePath, 'w+') as outFile:
        for failure in failures:
            Registrar.registerError(failure)
        dictwriter = unicodecsv.DictWriter(
            outFile,
            fieldnames = ['update', 'master', 'slave', 'mchanges', 'schanges', 'exception'],
            extrasaction = 'ignore',
        )
        dictwriter.writerows(failures)
        print "WROTE FILE: ", filePath

outputFailures(masterFailures, mFailPath)
outputFailures(slaveFailures, sFailPath)

# Registrar.registerError('testing errors')

with io.open(logPath, 'w+', encoding='utf8') as logFile:
    for source, messages in Registrar.getMessageItems(None, 1).items():
        print source
        logFile.writelines([SanitationUtils.coerceUnicode(source)])
        logFile.writelines(
            [SanitationUtils.coerceUnicode(message) for message in messages]
        )
        for message in messages:
            pprint( message, indent=4, width=80, depth=2)

# if __name__ == '__main__':
#     main()

#
