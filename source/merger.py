from collections import OrderedDict
import os
# import shutil
from utils import SanitationUtils, TimeUtils, HtmlReporter, listUtils, Registrar, debugUtils
from matching import Match, MatchList, UsernameMatcher, CardMatcher, NocardEmailMatcher
from csvparse_flat import CSVParse_User, UsrObjList #, ImportUser
from contact_objects import ContactAddress
from coldata import ColData_User
from tabulate import tabulate
from itertools import chain
# from pprint import pprint
# import sys
from copy import deepcopy
import unicodecsv
# import pickle
import dill as pickle
from bisect import insort
import re
import time
import yaml
import MySQLdb
import pymysql
import paramiko
from sshtunnel import SSHTunnelForwarder, check_address
import io
import wordpress_xmlrpc
from UsrSyncClient import UsrSyncClient_XMLRPC, UsrSyncClient_SSH_ACT, UsrSyncClient_JSON, UsrSyncClient_SQL_WP
from SyncUpdate import SyncUpdate

importName = TimeUtils.getMsTimeStamp()
start_time = time.time()


def timediff():
    return time.time() - start_time

DEBUG = False
testMode = False
testMode = True
skip_sync = False

sql_run = False
sftp_run = False
update_slave = False
update_master = False
sql_run = True
sftp_run = True
update_slave = True
# update_master = True
do_problematic = True
do_filter = False
do_filter = True

### DEFAULT CONFIG ###

inFolder = "../input/"
outFolder = "../output/"
logFolder = "../logs/"
srcFolder = "../source/"
pklFolder = "../pickles/"
remoteExportFolder = "act_usr_exp"

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

SyncUpdate.setGlobals( MASTER_NAME, SLAVE_NAME, merge_mode, DEFAULT_LAST_SYNC)

#########################################
# Set up directories
#########################################

for path in (inFolder, outFolder, logFolder, srcFolder, pklFolder):
    if not os.path.exists(path):
        os.mkdir(path)

fileSuffix = "_test" if testMode else ""
fileSuffix += "_filter" if do_filter else ""
m_x_filename = "act_x"+fileSuffix+"_"+importName+".csv"
m_i_filename = "act_i"+fileSuffix+"_"+importName+".csv"
remoteExportPath = os.path.join(remoteExportFolder, m_x_filename)
maPath = os.path.join(inFolder, m_x_filename)
maEncoding = "utf-8"

saPath = os.path.join(inFolder, "wordpress_export_users_all_2016-03-11.csv")
saEncoding = "utf8"

if not sftp_run:
    maPath = os.path.join(inFolder, "act_x_test_2016-05-03_23-01-48.csv")
    # maPath = os.path.join(inFolder, "500-act-records.csv")
    maEncoding = "utf8"
if not sql_run:
    saPath = os.path.join(inFolder, "500-wp-records.csv")
    saEncoding = "utf8"

assert store_url, "store url must not be blank"
xmlrpc_uri = store_url + 'xmlrpc.php'
json_uri = store_url + 'wp-json/wp/v2'

TimeUtils.setWpSrvOffset(wp_srv_offset)

moPath = os.path.join(outFolder, m_i_filename)
resPath = os.path.join(outFolder, "sync_report%s.html" % fileSuffix)
WPresCsvPath = os.path.join(outFolder, "sync_report_wp%s.csv" % fileSuffix)
ACTresCsvPath = os.path.join(outFolder, "sync_report_act%s.csv" % fileSuffix)
sqlPath = os.path.join(srcFolder, "select_userdata_modtime.sql")
# pklPath = os.path.join(pklFolder, "parser_pickle.pkl" )
pklPath = os.path.join(pklFolder, "parser_pickle%s.pkl" % fileSuffix )

colData = ColData_User()

actCols = colData.getACTCols()
actFields = ";".join(actCols.keys())

xmlConnectParams = {
    'xmlrpc_uri': xmlrpc_uri,
    'wp_user': wp_user,
    'wp_pass': wp_pass
}

jsonConnectParams = {
    'json_uri': json_uri,
    'wp_user': wp_user,
    'wp_pass': wp_pass
}

sqlConnectParams = {
    
}

#########################################
# Prepare Filter Data
#########################################

print debugUtils.hashify("PREPARE FILTER DATA"), timediff()

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

if not do_filter:
    filterItems = None

#########################################
# Download / Generate Slave Parser Object
#########################################

print debugUtils.hashify("Download / Generate Slave Parser Object"), timediff()

saParser = CSVParse_User(
    cols = colData.getWPImportCols(),
    defaults = colData.getDefaults(),
    filterItems = filterItems
)
if sql_run:
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
        if testMode:
            client.analyseRemote(saParser, limit=1000)
        else:
            client.analyseRemote(saParser)

else:
    saParser.analyseFile(saPath, saEncoding)

# saRows = []

# if sql_run: 
#     SSHTunnelForwarderAddress = (ssh_host, ssh_port)
#     SSHTunnelForwarderBindAddress = (remote_bind_host, remote_bind_port)
#     # SSHTunnelForwarderBindAddress = (remote_bind_host, remote_bind_port)
#     for host in ['SSHTunnelForwarderAddress', 'SSHTunnelForwarderBindAddress']:
#         try:
#             check_address(eval(host))
#         except Exception, e:
#             assert not e, "Host must be valid: %s [%s = %s]" % (str(e), host, repr(eval(host)))
#     SSHTunnelForwarderParams = {
#         'ssh_address_or_host':SSHTunnelForwarderAddress,
#         'ssh_password':ssh_pass,
#         'ssh_username':ssh_user,
#         'remote_bind_address': SSHTunnelForwarderBindAddress,
#     }

#     print SSHTunnelForwarderParams

#     MySQLdbConnectParams = {
#         'host':'127.0.0.1',
#         'user':db_user,
#         'passwd':db_pass,
#         'db':db_name
#     }

#     PyMySqlConnectParams = {
#         'host' : 'localhost',
#         'user' : db_user,
#         'password': db_pass,
#         'db'   : db_name,
#         'charset': db_charset,
#         'use_unicode': True
#     }


#     with \
#       SSHTunnelForwarder(**SSHTunnelForwarderParams) as server, \
#       open(sqlPath) as sqlFile:
#         # server.start()
#         print server.local_bind_address

#         MySQLdbConnectParams['port'] = server.local_bind_port
#         PyMySqlConnectParams['port'] = server.local_bind_port
#         print PyMySqlConnectParams
#         # conn = MySQLdb.connect( **MySQLdbConnectParams )
#         conn = pymysql.connect( **PyMySqlConnectParams )

#         wpCols = OrderedDict(filter( lambda (k, v): not v.get('wp',{}).get('generated'), colData.getWPCols().items()))

#         assert all([
#             'Wordpress ID' in wpCols.keys(),
#             wpCols['Wordpress ID'].get('wp', {}).get('key') == 'ID',
#             wpCols['Wordpress ID'].get('wp', {}).get('final')
#         ]), 'ColData should be configured correctly'
#         userdata_select = ",\n\t\t\t".join(filter(None,[
#             ("MAX(CASE WHEN um.meta_key = '%s' THEN um.meta_value ELSE \"\" END) as `%s`" if data['wp'].get('meta') else "u.%s as `%s`") % (data['wp']['key'], col)\
#             for col, data in wpCols.items()
#         ]))

#         print sqlFile.read() % (userdata_select, '%susers'%tbl_prefix,'%susermeta'%tbl_prefix,'%stansync_updates'%tbl_prefix)
#         sqlFile.seek(0)

#         cursor = conn.cursor()
#         cursor.execute(sqlFile.read() % (userdata_select, '%susers'%tbl_prefix,'%susermeta'%tbl_prefix,'%stansync_updates'%tbl_prefix))
#         # headers = colData.getWPCols().keys() + ['ID', 'user_id', 'updated']
#         headers = [SanitationUtils.coerceUnicode(i[0]) for i in cursor.description]
#         # print headers
#         saRows = [headers]
        
#         for i, row in enumerate(cursor):
#             if testMode and i>500: 
#                 break
#             saRows += [map(SanitationUtils.coerceUnicode, row)]

# #########################################
# # Import Slave Info From Spreadsheets
# #########################################

# print debugUtils.hashify("Import Slave Info From Spreadsheets"), timediff()

# saParser = CSVParse_User(
#     cols = colData.getImportCols(),
#     defaults = colData.getDefaults(),
#     filterItems = filterItems
# )
# if saRows:
#     print "analysing slave rows", timediff()
#     saParser.analyseRows(saRows)
# else:
#     print "generating slave", timediff()
#     saParser.analyseFile(saPath, saEncoding)
# print "analysed %d slave objects" % len(saParser.objects), timediff()

# def printBasicColumns(users):
#     # print len(users)
#     usrList = UsrObjList()
#     for user in users:
#         usrList.addObject(user)
#         # SanitationUtils.safePrint( "BILLING ADDRESS:", repr(user), user['First Name'], user.get('First Name'), user.name.__unicode__(out_schema="flat"))

#     cols = colData.getBasicCols()

#     SanitationUtils.safePrint( usrList.tabulate(
#         cols,
#         tablefmt = 'simple'
#     ))

CSVParse_User.printBasicColumns( list(chain( *saParser.emails.values() )) )

#########################################
# Generate and Analyse ACT CSV files using shell
#########################################


maParser = CSVParse_User(
    cols = colData.getImportCols(),
    defaults = colData.getDefaults(),
    contact_schema = 'act',
    filterItems = filterItems
)

print debugUtils.hashify("Generate and Analyse ACT data"), timediff()

if sftp_run:
    actConnectParams = {
        'hostname':    m_ssh_host,
        'port':        m_ssh_port,
        'username':    m_ssh_user,
        'password':    m_ssh_pass,
    }

    for thing in ['m_x_cmd', 'm_i_cmd', 'remoteExportFolder', 'actFields']:
        assert eval(thing), "missing mandatory command component '%s'" % thing 

    actDbParams = {
        'db_x_exe':m_x_cmd,
        'db_i_exe':m_i_cmd,
        'db_name': m_db_name,
        'db_host': m_db_host,
        'db_user': m_db_user,
        'db_pass': m_db_pass,
        'fields' : actFields
    }

    fsParams = {
        'importName': importName,
        'remoteExportFolder': remoteExportFolder,
        'inFolder': inFolder,
        'outFolder': outFolder
    }
    with UsrSyncClient_SSH_ACT(actConnectParams, actDbParams, fsParams) as masterClient:
        masterClient.analyseRemote(maParser)
else:
    maParser.analyseFile(maPath)

CSVParse_User.printBasicColumns( list(chain( *maParser.emails.values()[:100] )) )

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

    
if not skip_sync:
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

    denyAnomalousParselist( "saParser.noemails", saParser.noemails )

    emailMatcher = NocardEmailMatcher( globalMatches.sIndices, globalMatches.mIndices )
    emailMatcher.processRegisters( saParser.nocards, maParser.emails)

    newMasters.addMatches(emailMatcher.masterlessMatches)

    newSlaves.addMatches(emailMatcher.slavelessMatches)

    globalMatches.addMatches(emailMatcher.pureMatches)


    # TODO: further sort emailMatcher

    print debugUtils.hashify("BEGINNING MERGE (%d)" % len(globalMatches))
    print timediff()


    syncCols = colData.getSyncCols()

    for match in globalMatches:
        # print debugUtils.hashify( "MATCH NUMBER %d" % i )

        # print "-> INITIAL VALUES:"
        # print match.tabulate()

        mObject = match.mObjects[0]
        sObject = match.sObjects[0]

        syncUpdate = SyncUpdate(mObject, sObject)
        syncUpdate.update(syncCols)

        SanitationUtils.safePrint( syncUpdate.tabulate(tablefmt = 'simple'))

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

    basic_cols = colData.getBasicCols()
    address_cols = OrderedDict(basic_cols.items() + [('address_reason', {})])
    name_cols = OrderedDict(basic_cols.items() + [('name_reason', {})])
    csv_colnames = colData.getColNames(OrderedDict(basic_cols.items() + [('address_reason', {}), ('name_reason', {})]) )
    # print repr(basic_colnames)
    unicode_colnames = map(SanitationUtils.coerceUnicode, csv_colnames.values() )
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
        UsrObjList(maParser.badName.values() + maParser.badAddress.values()).exportItems(ACTresCsvPath, csv_colnames)

    reporter.addGroup(sanitizingGroup)

    report_matching = not skip_sync
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

    report_sync = not skip_sync
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

if allUpdates:

    with \
        UsrSyncClient_SSH_ACT(actConnectParams, actDbParams, fsParams) as masterClient, \
        UsrSyncClient_JSON(jsonConnectParams) as slaveClient:

        for update in allUpdates:
            if update_master and update.mUpdated :
                try:
                    update.updateMaster(masterClient)
                except Exception, e:
                    raise Exception("ERROR UPDATING MASTER (%s): %s" % (update.MYOBID, repr(e) ) )
            if update_slave and update.sUpdated :
                try:
                    update.updateSlave(slaveClient)
                except Exception, e:
                    raise Exception("ERROR UPDATING SLAVE (%s): %s" % (update.WPID, repr(e) ) )
