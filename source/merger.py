from pprint import pprint
from collections import OrderedDict
import os
import sys
import unicodecsv
import argparse
import traceback
# import shutil
from utils import SanitationUtils, TimeUtils, HtmlReporter #,listUtils
from utils import Registrar, debugUtils, ProgressCounter
from matching import Match, MatchList, ConflictingMatchList
from matching import UsernameMatcher, CardMatcher, NocardEmailMatcher, EmailMatcher
from csvparse_user import CSVParse_User, UsrObjList #, ImportUser
# from contact_objects import ContactAddress
from coldata import ColData_User
# from tabulate import tabulate
# from itertools import chain
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
# import smtplib
import zipfile
# import tempfile
# from email import encoders
# from email.message import Message
# from email.mime.base import MIMEBase
# from email.mime.multipart import MIMEMultipart
# import MySQLdb
# import pymysql
# import paramiko
from sshtunnel import check_address
import io
# import wordpress_xmlrpc
from sync_client_user import UsrSyncClient_SSH_ACT, UsrSyncClient_SQL_WP
from sync_client_user import UsrSyncClient_WP #, UsrSyncClient_WC, UsrSyncClient_JSON
from SyncUpdate import SyncUpdate, SyncUpdate_Usr_Api
from contact_objects import FieldGroup
from duplicates import Duplicates, object_glb_index_fn


importName = TimeUtils.getMsTimeStamp()
start_time = time.time()

def timediff():
    return time.time() - start_time

# testMode = False
testMode = True

# good testing command: python source/merger.py -vv --skip-download-master --skip-download-slave --skip-update-master --skip-update-slave --skip-filter --do-sync --skip-post --testmode --limit=9000 --master-file=act_x_2017-01-10_16-42-53.csv --slave-file=wp_x_test_2017-01-10_16-42-53.csv

### DEFAULT CONFIG ###

# paths are relative to source file

# things that need global scope

os.chdir(os.path.dirname(sys.argv[0]))

inFolder = "../input/"
outFolder = "../output/"
logFolder = "../logs/"
srcFolder = "../source/"
pklFolder = "../pickles/"

yamlPath = "merger_config.yaml"

repPath = ''
mFailPath = os.path.join(outFolder, "act_fails.csv")
sFailPath = os.path.join(outFolder, "wp_fails.csv" )
logPath = os.path.join(logFolder, "log_%s.txt" % importName)
zipPath = os.path.join(logFolder, "zip_%s.zip" % importName)

def main():
    global testMode, inFolder, outFolder, logFolder, srcFolder, pklFolder, \
        yamlPath, repPath, mFailPath, sFailPath, logPath, zipPath

    userFile = cardFile = emailFile = sinceM = sinceS = False

    ### OVERRIDE CONFIG WITH YAML FILE ###

    config = {}

    OLD_THRESHOLD = "2014-01-01 00:00:00"

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
        master_file = config.get('master_file', '')
        slave_file = config.get('slave_file', '')
        userFile = config.get('userFile')
        cardFile = config.get('cardFile')
        emailFile = config.get('emailFile')
        sinceM = config.get('sinceM')
        sinceS = config.get('sinceS')
        # download_slave = config.get('download_slave')
        # download_master = config.get('download_master')
        # update_slave = config.get('update_slave')
        # update_master = config.get('update_master')
        # do_filter = config.get('do_filter')
        # do_problematic = config.get('do_problematic')
        # do_post = config.get('do_post')
        # do_sync = config.get('do_sync'

    ### OVERRIDE CONFIG WITH ARGPARSE ###

    parser = argparse.ArgumentParser(description = 'Merge contact records between two databases')
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-v", "--verbosity", action="count",
                        help="increase output verbosity")
    group.add_argument("-q", "--quiet", action="store_true")
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--testmode', help='Run in test mode with test databases',
                        action='store_true', default=None)
    group.add_argument('--livemode', help='Run the script on the live databases',
                        action='store_false', dest='testmode')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--do-sync', help='sync the databases',
                       action="store_true", default=config.get('do_sync'))
    group.add_argument('--skip-sync', help='don\'t sync the databases',
                       action="store_false", dest='do_sync')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--do-post', help='post process the contacts',
                       action="store_true", default=config.get('do_post'))
    group.add_argument('--skip-post', help='don\'t post process the contacts',
                       action="store_false", dest='do_post')
    group.add_argument('--process-duplicates', help="do extra processing to figure out duplicates",
                       default=False, action="store_true")

    download_group = parser.add_argument_group('Import options')
    group = download_group.add_mutually_exclusive_group()
    group.add_argument('--download-master', help='download the master data',
                       action="store_true", default=config.get('download_master'))
    group.add_argument('--skip-download-master', help='use the local master file instead\
        of downloading the master data', action="store_false", dest='download_master')
    group = download_group.add_mutually_exclusive_group()
    group.add_argument('--download-slave', help='download the slave data',
                       action="store_true", default=config.get('download_slave'))
    group.add_argument('--skip-download-slave', help='use the local slave file instead\
        of downloading the slave data', action="store_false", dest='download_slave')

    update_group = parser.add_argument_group('Update options')
    group = update_group.add_mutually_exclusive_group()
    group.add_argument('--update-master', help='update the master database',
                       action="store_true", default=config.get('update_master'))
    group.add_argument('--skip-update-master', help='don\'t update the master database',
                       action="store_false", dest='update_master')
    group = update_group.add_mutually_exclusive_group()
    group.add_argument('--update-slave', help='update the slave database',
                       action="store_true", default=config.get('update_slave'))
    group.add_argument('--skip-update-slave', help='don\'t update the slave database',
                       action="store_false", dest='update_slave')
    group = update_group.add_mutually_exclusive_group()
    group.add_argument('--do-problematic', help='make problematic updates to the databases',
                       action="store_true", default=config.get('do_problematic'))
    group.add_argument('--skip-problematic', help='don\'t make problematic updates to the databases',
                       action="store_false", dest='do_problematic')
    group = update_group.add_mutually_exclusive_group()
    group.add_argument('--ask-before-update', help="ask before updating",
                       action="store_true", default=True)
    group.add_argument('--force-update', help="don't ask before updating",
                       action="store_false", dest="ask_before_update")



    filter_group = parser.add_argument_group("Filter Options")
    group = filter_group.add_mutually_exclusive_group()
    group.add_argument('--do-filter', help='filter the databases',
                       action="store_true", default=config.get('do_filter'))
    group.add_argument('--skip-filter', help='don\'t filter the databases',
                       action="store_false", dest='do_filter')
    filter_group.add_argument('--limit', type=int, help='global limit of objects to process')
    filter_group.add_argument(
        '--card-file',
        help='list of cards to filter on',
        default=config.get('cardFile')
    )

    parser.add_argument('--m-ssh-host', help='location of master ssh server')
    parser.add_argument('--m-ssh-port', type=int, help='location of master ssh port')
    parser.add_argument('--master-file', help='location of master file')
    parser.add_argument('--slave-file', help='location of slave file')

    debug_group = parser.add_argument_group("Debug options")
    debug_group.add_argument('--debug-abstract', action='store_true', dest='debug_abstract')
    debug_group.add_argument('--debug-parser', action='store_true', dest='debug_parser')
    debug_group.add_argument('--debug-update', action='store_true', dest='debug_update')
    debug_group.add_argument('--debug-flat', action='store_true', dest='debug_flat')
    debug_group.add_argument('--debug-name', action='store_true', dest='debug_name')
    debug_group.add_argument('--debug-address', action='store_true', dest='debug_address')
    debug_group.add_argument('--debug-client', action='store_true', dest='debug_client')
    debug_group.add_argument('--debug-utils', action='store_true', dest='debug_utils')
    debug_group.add_argument('--debug-contact', action='store_true', dest='debug_contact')
    debug_group.add_argument('--debug-duplicates', action='store_true', dest='debug_duplicates')

    args = parser.parse_args()

    if args:
        print args
        if args.verbosity > 0:
            Registrar.DEBUG_PROGRESS = True
            Registrar.DEBUG_ERROR = True
        if args.verbosity > 1:
            Registrar.DEBUG_MESSAGE = True
        if args.quiet:
            Registrar.DEBUG_PROGRESS = False
            Registrar.DEBUG_ERROR = False
            Registrar.DEBUG_MESSAGE = False
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
        # if args.do_sync is not None:
        #     do_sync = args.do_sync
        # if args.do_problematic is not None:
        #     do_problematic = args.do_problematic
        # if args.do_post is not None:
        #     do_post = args.do_post
        if args.m_ssh_port:
            m_ssh_port = args.m_ssh_port
        if args.m_ssh_host:
            m_ssh_host = args.m_ssh_host
        if args.master_file is not None:
            # download_master = False
            master_file = args.master_file
        if args.slave_file is not None:
            # download_slave = False
            slave_file = args.slave_file
        if args.card_file is not None:
            cardFile = args.card_file
            # do_filter = True

        if args.debug_abstract is not None:
            Registrar.DEBUG_ABSTRACT = args.debug_abstract
        if args.debug_parser is not None:
            Registrar.DEBUG_PARSER = args.debug_parser
        if args.debug_update is not None:
            Registrar.DEBUG_UPDATE = args.debug_update
        if args.debug_flat is not None:
            Registrar.DEBUG_FLAT = args.debug_flat
        if args.debug_name is not None:
            Registrar.DEBUG_NAME = args.debug_name
        if args.debug_address is not None:
            Registrar.DEBUG_ADDRESS = args.debug_address
        if args.debug_client is not None:
            Registrar.DEBUG_CLIENT = args.debug_client
        if args.debug_utils is not None:
            Registrar.DEBUG_UTILS = args.debug_utils
        if args.debug_contact is not None:
            Registrar.DEBUG_CONTACT = args.debug_contact
        if args.debug_duplicates is not None:
            Registrar.DEBUG_DUPLICATES = args.debug_duplicates

        global_limit = args.limit

    # api config

    with open(yamlPath) as stream:
        optionNamePrefix = 'test_' if testMode else ''
        config = yaml.load(stream)
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
        # wp_user = config.get(optionNamePrefix+'wp_user', '')
        # wp_pass = config.get(optionNamePrefix+'wp_pass', '')
        store_url = config.get(optionNamePrefix+'store_url', '')
        wp_user = config.get(optionNamePrefix+'wp_user')
        wp_pass = config.get(optionNamePrefix+'wp_pass')
        wp_callback = config.get(optionNamePrefix+'wp_callback')
        wp_api_key = config.get(optionNamePrefix+'wp_api_key')
        wp_api_secret = config.get(optionNamePrefix+'wp_api_secret')
       #  wc_api_key = config.get(optionNamePrefix+'wc_api_key')
       #  wc_api_secret = config.get(optionNamePrefix+'wc_api_secret')
        remote_export_folder = config.get(optionNamePrefix+'remote_export_folder', '')


    ### DISPLAY CONFIG ###
    if Registrar.DEBUG_MESSAGE:
        if testMode:
            print "testMode enabled"
        else:
            print "testMode disabled"
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
        if not args.do_sync:
            print "not doing sync"
        if not args.do_post:
            print "not doing post"

    ### PROCESS CLASS PARAMS ###

    FieldGroup.do_post = args.do_post
    SyncUpdate.setGlobals( MASTER_NAME, SLAVE_NAME, merge_mode, DEFAULT_LAST_SYNC)
    TimeUtils.setWpSrvOffset(wp_srv_offset)

    ### SET UP DIRECTORIES ###

    for path in (inFolder, outFolder, logFolder, srcFolder, pklFolder):
        if not os.path.exists(path):
            os.mkdir(path)

    fileSuffix = "_test" if testMode else ""
    fileSuffix += "_filter" if do_filter else ""
    m_x_filename = "act_x"+fileSuffix+"_"+importName+".csv"
    # m_i_filename = "act_i"+fileSuffix+"_"+importName+".csv"
    s_x_filename = "wp_x"+fileSuffix+"_"+importName+".csv"
    # remoteExportPath = os.path.join(remote_export_folder, m_x_filename)

    if download_master:
        maPath = os.path.join(inFolder, m_x_filename)
        maEncoding = "utf-8"
    else:
        # maPath = os.path.join(inFolder, "act_x_test_2016-05-03_23-01-48.csv")
        maPath = os.path.join(inFolder, master_file)
        # maPath = os.path.join(inFolder, "500-act-records-edited.csv")
        # maPath = os.path.join(inFolder, "500-act-records.csv")
        maEncoding = "utf8"
    if download_slave:
        saPath = os.path.join(inFolder, s_x_filename)
        saEncoding = "utf8"
    else:
        saPath = os.path.join(inFolder, slave_file)
        # saPath = os.path.join(inFolder, "500-wp-records-edited.csv")
        saEncoding = "utf8"

    # moPath = os.path.join(outFolder, m_i_filename)
    repPath = os.path.join(outFolder, "usr_sync_report%s.html" % fileSuffix)
    repdPath = os.path.join(outFolder, "usr_sync_report_duplicate%s.html" % fileSuffix)
    WPresCsvPath = os.path.join(outFolder, "sync_report_wp%s.csv" % fileSuffix)
    masterResCsvPath = os.path.join(outFolder, "sync_report_act%s.csv" % fileSuffix)
    masterDeltaCsvPath = os.path.join(outFolder, "delta_report_act%s.csv" % fileSuffix)
    slaveDeltaCsvPath = os.path.join(outFolder, "delta_report_wp%s.csv" % fileSuffix)
    mFailPath = os.path.join(outFolder, "act_fails%s.csv" % fileSuffix)
    sFailPath = os.path.join(outFolder, "wp_fails%s.csv" % fileSuffix)
    # sqlPath = os.path.join(srcFolder, "select_userdata_modtime.sql")
    # pklPath = os.path.join(pklFolder, "parser_pickle%s.pkl" % fileSuffix )
    logPath = os.path.join(logFolder, "log_%s.txt" % importName)
    zipPath = os.path.join(logFolder, "zip_%s.zip" % importName)

    ### PROCESS OTHER CONFIG ###

    assert store_url, "store url must not be blank"
    # xmlrpc_uri = store_url + 'xmlrpc.php'
    # json_uri = store_url + 'wp-json/wp/v2'

    actFields = ";".join(ColData_User.getACTImportCols())

    # jsonConnectParams = {
    #     'json_uri': json_uri,
    #     'wp_user': wp_user,
    #     'wp_pass': wp_pass
    # }

    # wcApiParams = {
        # 'api_key':wc_api_key,
        # 'api_secret':wc_api_secret,
        # 'url':store_url
    # }

    wpApiParams = {
        'api_key': wp_api_key,
        'api_secret': wp_api_secret,
        'url':store_url,
        'wp_user':wp_user,
        'wp_pass':wp_pass,
        'callback':wp_callback
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
        'remote_export_folder': remote_export_folder,
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
        for key, filterFile in filterFiles.items():
            if filterFile:
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

    print filterItems

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
            'host' : '127.0.0.1',
            'user' : db_user,
            'password': db_pass,
            'db'   : db_name,
            'charset': db_charset,
            'use_unicode': True,
            'tbl_prefix': tbl_prefix,
        }

        print "SSHTunnelForwarderParams", SSHTunnelForwarderParams
        print "PyMySqlConnectParams", PyMySqlConnectParams

        with UsrSyncClient_SQL_WP(SSHTunnelForwarderParams, PyMySqlConnectParams) as client:
            client.analyseRemote(saParser, limit=global_limit, filterItems=filterItems)

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
        for thing in ['m_x_cmd', 'm_i_cmd', 'remote_export_folder', 'actFields']:
            assert eval(thing), "missing mandatory command component '%s'" % thing

        with UsrSyncClient_SSH_ACT(actConnectParams, actDbParams, fsParams) as masterClient:
            masterClient.analyseRemote(maParser, limit=global_limit)
    else:
        maParser.analyseFile(maPath, dialect_suggestion='act_out', encoding=maEncoding)

    # CSVParse_User.printBasicColumns(  saParser.roles['WP'] )
    #
    # exit()
    # quit()


    # get matches

    globalMatches = MatchList()
    anomalousMatchLists = {}
    newMasters = MatchList()
    newSlaves = MatchList()
    duplicateMatchlists = OrderedDict()
    anomalousParselists = {}
    # nonstaticUpdates = []
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
    emailConflictMatches = ConflictingMatchList(indexFn=EmailMatcher.emailIndexFn)

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


    if args.do_sync:
        # for every username in slave, check that it exists in master
        print debugUtils.hashify("processing usernames")
        print timediff()

        denyAnomalousParselist( 'saParser.nousernames', saParser.nousernames )

        usernameMatcher = UsernameMatcher()
        usernameMatcher.processRegisters(saParser.usernames, maParser.usernames)

        denyAnomalousMatchList('usernameMatcher.slavelessMatches', usernameMatcher.slavelessMatches)
        denyAnomalousMatchList('usernameMatcher.duplicateMatches', usernameMatcher.duplicateMatches)

        duplicateMatchlists['username'] = usernameMatcher.duplicateMatches

        globalMatches.addMatches( usernameMatcher.pureMatches)

        if(Registrar.DEBUG_MESSAGE):
            print "username matches (%d pure)" % len(usernameMatcher.pureMatches)
            # print repr(usernameMatcher)

        if Registrar.DEBUG_DUPLICATES and usernameMatcher.duplicateMatches:
            print("username duplicates: %s" % len(usernameMatcher.duplicateMatches))

        print debugUtils.hashify("processing cards")
        print timediff()

        #for every card in slave not already matched, check that it exists in master

        denyAnomalousParselist( 'maParser.nocards', maParser.nocards )

        cardMatcher = CardMatcher( globalMatches.sIndices, globalMatches.mIndices )
        cardMatcher.processRegisters( saParser.cards, maParser.cards )

        denyAnomalousMatchList('cardMatcher.duplicateMatches', cardMatcher.duplicateMatches)
        denyAnomalousMatchList('cardMatcher.masterlessMatches', cardMatcher.masterlessMatches)

        duplicateMatchlists['card'] = cardMatcher.duplicateMatches

        globalMatches.addMatches( cardMatcher.pureMatches)

        if(Registrar.DEBUG_MESSAGE):
            print "card matches (%d pure)" % len(cardMatcher.pureMatches)
            # print repr(cardMatcher)

        if Registrar.DEBUG_DUPLICATES and cardMatcher.duplicateMatches:
            print("card duplicates: %s" % len(cardMatcher.duplicateMatches))

        # #for every email in slave, check that it exists in master

        print debugUtils.hashify("processing emails")
        print timediff()

        denyAnomalousParselist("saParser.noemails", saParser.noemails)

        emailMatcher = NocardEmailMatcher(globalMatches.sIndices, globalMatches.mIndices)

        emailMatcher.processRegisters(saParser.nocards, maParser.emails)

        newMasters.addMatches(emailMatcher.masterlessMatches)
        newSlaves.addMatches(emailMatcher.slavelessMatches)
        globalMatches.addMatches(emailMatcher.pureMatches)
        duplicateMatchlists['email'] = emailMatcher.duplicateMatches

        if(Registrar.DEBUG_MESSAGE):
            print "email matches (%d pure)" % (len(emailMatcher.pureMatches))
            # print repr(emailMatcher)

        if Registrar.DEBUG_DUPLICATES and emailMatcher.duplicateMatches:
            print("email duplicates: %s" % len(emailMatcher.duplicateMatches))        

        # TODO: further sort emailMatcher

        print debugUtils.hashify("BEGINNING MERGE (%d)" % len(globalMatches))
        print timediff()

        syncCols = ColData_User.getSyncCols()

        if Registrar.DEBUG_PROGRESS:
            syncProgressCounter = ProgressCounter(len(globalMatches))

        for count, match in enumerate(globalMatches):
            if Registrar.DEBUG_PROGRESS:
                syncProgressCounter.maybePrintUpdate(count)
                # print "examining globalMatch %d" % count
                # # print SanitationUtils.safePrint( match.tabulate(tablefmt = 'simple'))
                # print repr(match)

            mObject = match.mObjects[0]
            sObject = match.sObjects[0]

            syncUpdate = SyncUpdate_Usr_Api(mObject, sObject)
            syncUpdate.update(syncCols)

            # if(Registrar.DEBUG_MESSAGE):
            #     print "examining SyncUpdate"
            #     SanitationUtils.safePrint( syncUpdate.tabulate(tablefmt = 'simple'))

            if syncUpdate.mUpdated and syncUpdate.mDeltas:
                insort(mDeltaUpdates, syncUpdate)

            if syncUpdate.sUpdated and syncUpdate.sDeltas:
                insort(sDeltaUpdates, syncUpdate)

            if not syncUpdate:
                continue

            if syncUpdate.sUpdated:
                syncSlaveUpdates = syncUpdate.getSlaveUpdates()
                if 'E-mail' in syncSlaveUpdates:
                    newEmail = syncSlaveUpdates['E-mail']
                    if newEmail in saParser.emails:
                        mObjects = [mObject]
                        sObjects = [sObject] + saParser.emails[newEmail]
                        SanitationUtils.safePrint("duplicate emails", mObjects, sObjects)
                        try:
                            emailConflictMatches.addMatch(Match(mObjects, sObjects))
                        except Exception, e:
                            SanitationUtils.safePrint(
                                "something happened adding an email conflict, newEmail: %s ; exception: %s" % (
                                    newEmail,
                                    e
                                )
                            )
                        continue

            if(not syncUpdate.importantStatic):
                if(syncUpdate.mUpdated and syncUpdate.sUpdated):
                    if(syncUpdate.sMod):
                        insort(problematicUpdates, syncUpdate)
                        continue
                elif(syncUpdate.mUpdated and not syncUpdate.sUpdated):
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

        # todo: process duplicates here

    #########################################
    # Write Report
    #########################################

    print debugUtils.hashify("Write Report")
    print timediff()

    with io.open(repPath, 'w+', encoding='utf8') as resFile:

        repdFile = None
        if args.process_duplicates:
            repdFile = io.open(repdPath, 'w+', encoding='utf8')

        css = ""
        reporter = HtmlReporter(css=css)

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
        # unicode_colnames = map(SanitationUtils.coerceUnicode, csv_colnames.values())
        # print repr(unicode_colnames)
        # WPCsvWriter = DictWriter(WPresCsvFile, fieldnames = unicode_colnames, extrasaction = 'ignore' )
        # WPCsvWriter.writeheader()
        # ACTCsvWriter = DictWriter(ACTresCsvFile, fieldnames = unicode_colnames, extrasaction = 'ignore' )
        # ACTCsvWriter.writeheader()

        sanitizingGroup = HtmlReporter.Group('sanitizing', 'Sanitizing Results')

        # s_bad_addresses_usrlist = UsrObjList(saParser.badAddress.values())

        # for user in saParser.badAddress.values():
        #     # user['address_reason'] = ''.join([address.reason for address in addresses])
        #     s_bad_addresses_usrlist.append(user)

        if saParser.badAddress:
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

        if saParser.badName:
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

        if maParser.badAddress:
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

        if maParser.badName:
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
                .exportItems(masterResCsvPath, csv_colnames)

        reporter.addGroup(sanitizingGroup)

        if args.do_sync and (mDeltaUpdates + sDeltaUpdates):

            deltaGroup = HtmlReporter.Group('deltas', 'Field Changes')

            mDeltaList = UsrObjList(filter(None,
                                [update.newMObject for update in mDeltaUpdates]))

            sDeltaList = UsrObjList(filter(None,
                                [update.newSObject for update in sDeltaUpdates]))

            deltaCols = ColData_User.getDeltaCols()

            allDeltaCols = OrderedDict(
                ColData_User.getBasicCols().items() +
                ColData_User.nameCols(deltaCols.keys()+deltaCols.values()).items()
            )

            if mDeltaList:
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

            if sDeltaList:
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
                mDeltaList.exportItems(masterDeltaCsvPath, ColData_User.getColNames(allDeltaCols))
            if sDeltaList:
                sDeltaList.exportItems(slaveDeltaCsvPath, ColData_User.getColNames(allDeltaCols))


        report_matching = args.do_sync
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

            matchListInstructions = {
                'cardMatcher.masterlessMatches': '%s records do not have a corresponding CARD ID in %s (deleted?)' % (SLAVE_NAME, MASTER_NAME),
                # 'cardMatcher.duplicateMatches': '%s records have multiple CARD IDs in %s' % (SLAVE_NAME, MASTER_NAME),
                'usernameMatcher.slavelessMatches': '%s records have no USERNAMEs in %s' % (MASTER_NAME, SLAVE_NAME),
                # 'usernameMatcher.duplicateMatches': '%s records have multiple USERNAMEs in %s' % (SLAVE_NAME, MASTER_NAME)
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
                description = parseListInstructions.get(parselistType, parselistType)
                usrList  = UsrObjList()
                for obj in parseList.values():
                    usrList.append(obj)

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

        report_sync = args.do_sync
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

        report_duplicates = args.process_duplicates
        if report_duplicates:

            dupCss = ".highlight_old {color: red;}"
            dupReporter = HtmlReporter(css=dupCss)
            duplicateGroup = HtmlReporter.Group('dup', 'Duplicate Results')

            dup_cols = OrderedDict(basic_cols.items() + [
                ('Create Date', {})
            ])

            # What we're doing here is analysing the duplicates we've seen so far, and 
            # creating a list of all the potential objects to delete and WHY they should be deleted.

            duplicates = Duplicates()

            for duplicateType, duplicateMatchlist in duplicateMatchlists.items():
                print "checking duplicates of type %s" % duplicateType
                print "len(duplicateMatchlist) %s" % len(duplicateMatchlist)
                for match in duplicateMatchlist:
                    if match.mLen <= 1:
                        continue
                        # only care about master duplicates at the moment
                    duplicateObjects = list(match.mObjects)
                    duplicates.add_conflictors(duplicateObjects, duplicateType)

            address_duplicates = {}
            for address, objects in maParser.addresses.items():
                # print "analysing address %s " % address
                # for objectData in objects:
                    # print " -> associated object: %s" % objectData
                if len(objects) > 1:
                    # if there are more than one objects associated with an address, add to the duplicate addresses report
                    address_duplicates[address] = objects
                    duplicates.add_conflictors(objects, "address")

            if Registrar.DEBUG_DUPLICATES:
                print duplicates.tabulate({}, tablefmt='plain')
            if duplicates:
                duplicateGroup.addSection(
                    HtmlReporter.Section(
                        'all duplicates',
                        **{
                            'title': 'All Duplicates',
                            'description': "%s records are involved in duplicates" % (MASTER_NAME),
                            'data': duplicates.tabulate(dup_cols, tablefmt='html'),
                            'length': len(duplicates)
                        }
                    )
                )

            if emailMatcher.duplicateMatches:
                duplicateGroup.addSection(
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
                # 'cardMatcher.masterlessMatches': '%s records do not have a corresponding CARD ID in %s (deleted?)' % (SLAVE_NAME, MASTER_NAME),
                'cardMatcher.duplicateMatches': '%s records have multiple CARD IDs in %s' % (SLAVE_NAME, MASTER_NAME),
                # 'usernameMatcher.slavelessMatches': '%s records have no USERNAMEs in %s' % (MASTER_NAME, SLAVE_NAME),
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

            if address_duplicates:
                def fn_user_older_than_wp(wp_time):
                    """ returns a function that checks if the user is older than a date given in wp_time format """
                    wp_time_obj = TimeUtils.wpStrptime(wp_time)
                    assert wp_time_obj, "should be valid time struct: %s" % wp_time
                    def user_older_than(userData):
                        assert hasattr(userData, 'act_last_transation'), \
                            "user should have act_last_transaction attr"
                        user_time_obj = userData.act_last_transation
                        return user_time_obj < wp_time_obj
                    return user_older_than

                print "there are address duplicates"
                duplicateGroup.addSection(
                    HtmlReporter.Section(
                        'address_duplicates',
                        title='Duplicate %s Addresses' % MASTER_NAME.title(),
                        description='%s addresses that appear in multiple records' % MASTER_NAME,
                        data="<br/>".join([
                            "<h4>%s</h4><p>%s</p>" % (
                                address,
                                UsrObjList(objects).tabulate(
                                    cols=dup_cols,
                                    tablefmt='html',
                                    highlight_rules=[('highlight_old', fn_user_older_than_wp(OLD_THRESHOLD))]
                                )
                            ) for address, objects in address_duplicates.items()
                        ]),
                        length=len(address_duplicates)
                    )
                )
            dupReporter.addGroup(duplicateGroup)
            repdFile.write(dupReporter.getDocumentUnicode() )

        resFile.write( reporter.getDocumentUnicode() )

    #########################################
    # Update databases
    #########################################

    allUpdates = staticUpdates
    if args.do_problematic:
        allUpdates += problematicUpdates

    print debugUtils.hashify("Update databases (%d)" % len(allUpdates))
    print timediff()

    masterFailures = []
    slaveFailures = []

    if allUpdates:
        Registrar.registerProgress("UPDATING %d RECORDS" % len(allUpdates))

        if args.ask_before_update:
            try:
                input("Please read reports and press Enter to continue or ctrl-c to stop...")
            except SyntaxError:
                pass

        if Registrar.DEBUG_PROGRESS:
            updateProgressCounter = ProgressCounter(len(allUpdates))

        with \
            UsrSyncClient_SSH_ACT(actConnectParams, actDbParams, fsParams) as masterClient, \
            UsrSyncClient_WP(wpApiParams) as slaveClient:
            # UsrSyncClient_JSON(jsonConnectParams) as slaveClient:

            for count, update in enumerate(allUpdates):
                if Registrar.DEBUG_PROGRESS:
                    updateProgressCounter.maybePrintUpdate(count)
                # if update.WPID == '1':
                #     print repr(update.WPID)
                #     continue
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
                        Registrar.registerError("ERROR UPDATING MASTER (%s): %s\n%s" % (
                            update.MasterID,
                            repr(e),
                            traceback.format_exc()
                        ) )

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
                        Registrar.registerError("ERROR UPDATING SLAVE (%s): %s\n%s" % (
                            update.SlaveID,
                            repr(e),
                            traceback.format_exc()
                        ) )

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

if __name__ == '__main__':
    try:
        main()
    except SystemExit:
        exit()
    except:
        Registrar.registerError(traceback.format_exc())

    with io.open(logPath, 'w+', encoding='utf8') as logFile:
        for source, messages in Registrar.getMessageItems(1).items():
            print source
            logFile.writelines([SanitationUtils.coerceUnicode(source)])
            logFile.writelines(
                [SanitationUtils.coerceUnicode(message) for message in messages]
            )
            for message in messages:
                pprint( message, indent=4, width=80, depth=2)



    #########################################
    # email reports
    #########################################

    files_to_zip = [mFailPath, sFailPath, repPath]

    with zipfile.ZipFile(zipPath, 'w') as zipFile:
        for file_to_zip in files_to_zip:
            try:
                os.stat(file_to_zip)
                zipFile.write(file_to_zip)
            except Exception as e:
                if(e):
                    pass
        Registrar.registerMessage('wrote file %s' % zipPath)
