# pylint: disable=too-many-lines
"""
Module for updating woocommerce and ACT databases from ACT import file
"""
# TODO: Fix too-many-lines

from pprint import pprint
from collections import OrderedDict
import os
import traceback
from bisect import insort
import re
import time
import zipfile
import io

import yaml
import unicodecsv
import argparse
from sshtunnel import check_address

from __init__ import MODULE_PATH, MODULE_LOCATION
from woogenerator.utils import SanitationUtils, TimeUtils, HtmlReporter
from woogenerator.utils import Registrar, debugUtils, ProgressCounter
from woogenerator.matching import Match, MatchList, ConflictingMatchList
from woogenerator.matching import UsernameMatcher, CardMatcher, NocardEmailMatcher, EmailMatcher
from woogenerator.parsing.user import CSVParse_User, UsrObjList
from woogenerator.coldata import ColData_User
from woogenerator.sync_client_user import UsrSyncClient_SSH_ACT, UsrSyncClient_SQL_WP
from woogenerator.sync_client_user import UsrSyncClient_WP
from woogenerator.syncupdate import SyncUpdate, SyncUpdate_Usr_Api
from woogenerator.contact_objects import FieldGroup
from woogenerator.duplicates import Duplicates


def timediff(settings):
    """
    return the difference in time since the start time according to settings
    """
    return time.time() - settings.start_time


def main(settings):  # pylint: disable=too-many-branches,too-many-locals
    """
    Using the settings object, attempt to perform the specified functions
    """
    # TODO: fix too-many-branches,too-many-locals

    ### OVERRIDE CONFIG WITH YAML FILE ###

    config = {}

    old_threshold = "2012-01-01 00:00:00"
    oldish_threshold = "2014-01-01 00:00:00"

    with open(settings.yaml_path) as stream:
        config = yaml.load(stream)

        if 'in_folder' in config.keys():
            settings.in_folder = config['in_folder']
        if 'out_folder' in config.keys():
            settings.out_folder = config['out_folder']
        if 'logFolder' in config.keys():
            settings.log_folder = config['logFolder']

        # mandatory
        settings.merge_mode = config.get('merge_mode', 'sync')
        settings.master_name = config.get('master_name', 'MASTER')
        settings.slave_name = config.get('slave_name', 'SLAVE')
        settings.default_last_sync = config.get('default_last_sync')
        settings.master_file = config.get('master_file', '')
        settings.slave_file = config.get('slave_file', '')
        settings.user_file = config.get('userFile')
        settings.card_file = config.get('cardFile')
        settings.email_file = config.get('emailFile')
        settings.since_m = config.get('sinceM')
        settings.since_s = config.get('sinceS')
        # download_slave = config.get('download_slave')
        # download_master = config.get('download_master')
        # update_slave = config.get('update_slave')
        # update_master = config.get('update_master')
        # do_filter = config.get('do_filter')
        # do_problematic = config.get('do_problematic')
        # do_post = config.get('do_post')
        # do_sync = config.get('do_sync'

    ### OVERRIDE CONFIG WITH ARGPARSE ###

    parser = argparse.ArgumentParser(
        description='Merge contact records between two databases')
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "-v", "--verbosity", action="count", help="increase output verbosity")
    group.add_argument("-q", "--quiet", action="store_true")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        '--testmode',
        help='Run in test mode with test databases',
        action='store_true',
        default=None)
    group.add_argument(
        '--livemode',
        help='Run the script on the live databases',
        action='store_false',
        dest='testmode')
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        '--do-sync',
        help='sync the databases',
        action="store_true",
        default=config.get('do_sync'))
    group.add_argument(
        '--skip-sync',
        help='don\'t sync the databases',
        action="store_false",
        dest='do_sync')
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        '--do-post',
        help='post process the contacts',
        action="store_true",
        default=config.get('do_post'))
    group.add_argument(
        '--skip-post',
        help='don\'t post process the contacts',
        action="store_false",
        dest='do_post')
    group.add_argument(
        '--process-duplicates',
        help="do extra processing to figure out duplicates",
        default=False,
        action="store_true")

    download_group = parser.add_argument_group('Import options')
    group = download_group.add_mutually_exclusive_group()
    group.add_argument(
        '--download-master',
        help='download the master data',
        action="store_true",
        default=config.get('download_master'))
    group.add_argument(
        '--skip-download-master',
        help='use the local master file instead\
        of downloading the master data',
        action="store_false",
        dest='download_master')
    group = download_group.add_mutually_exclusive_group()
    group.add_argument(
        '--download-slave',
        help='download the slave data',
        action="store_true",
        default=config.get('download_slave'))
    group.add_argument(
        '--skip-download-slave',
        help='use the local slave file instead\
        of downloading the slave data',
        action="store_false",
        dest='download_slave')

    update_group = parser.add_argument_group('Update options')
    group = update_group.add_mutually_exclusive_group()
    group.add_argument(
        '--update-master',
        help='update the master database',
        action="store_true",
        default=config.get('update_master'))
    group.add_argument(
        '--skip-update-master',
        help='don\'t update the master database',
        action="store_false",
        dest='update_master')
    group = update_group.add_mutually_exclusive_group()
    group.add_argument(
        '--update-slave',
        help='update the slave database',
        action="store_true",
        default=config.get('update_slave'))
    group.add_argument(
        '--skip-update-slave',
        help='don\'t update the slave database',
        action="store_false",
        dest='update_slave')
    group = update_group.add_mutually_exclusive_group()
    group.add_argument(
        '--do-problematic',
        help='make problematic updates to the databases',
        action="store_true",
        default=config.get('do_problematic'))
    group.add_argument(
        '--skip-problematic',
        help='don\'t make problematic updates to the databases',
        action="store_false",
        dest='do_problematic')
    group = update_group.add_mutually_exclusive_group()
    group.add_argument(
        '--ask-before-update',
        help="ask before updating",
        action="store_true",
        default=True)
    group.add_argument(
        '--force-update',
        help="don't ask before updating",
        action="store_false",
        dest="ask_before_update")

    filter_group = parser.add_argument_group("Filter Options")
    group = filter_group.add_mutually_exclusive_group()
    group.add_argument(
        '--do-filter',
        help='filter the databases',
        action="store_true",
        default=config.get('do_filter'))
    group.add_argument(
        '--skip-filter',
        help='don\'t filter the databases',
        action="store_false",
        dest='do_filter')
    filter_group.add_argument(
        '--limit', type=int, help='global limit of objects to process')
    filter_group.add_argument(
        '--card-file',
        help='list of cards to filter on',
        default=config.get('cardFile'))

    parser.add_argument('--m-ssh-host', help='location of master ssh server')
    parser.add_argument(
        '--m-ssh-port', type=int, help='location of master ssh port')
    parser.add_argument('--master-file', help='location of master file')
    parser.add_argument('--slave-file', help='location of slave file')

    debug_group = parser.add_argument_group("Debug options")
    debug_group.add_argument(
        '--debug-abstract', action='store_true', dest='debug_abstract')
    debug_group.add_argument(
        '--debug-parser', action='store_true', dest='debug_parser')
    debug_group.add_argument(
        '--debug-update', action='store_true', dest='debug_update')
    debug_group.add_argument(
        '--debug-flat', action='store_true', dest='debug_flat')
    debug_group.add_argument(
        '--debug-name', action='store_true', dest='debug_name')
    debug_group.add_argument(
        '--debug-address', action='store_true', dest='debug_address')
    debug_group.add_argument(
        '--debug-client', action='store_true', dest='debug_client')
    debug_group.add_argument(
        '--debug-utils', action='store_true', dest='debug_utils')
    debug_group.add_argument(
        '--debug-contact', action='store_true', dest='debug_contact')
    debug_group.add_argument(
        '--debug-duplicates', action='store_true', dest='debug_duplicates')

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
            settings.test_mode = args.testmode
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
            settings.m_ssh_port = args.m_ssh_port
        if args.m_ssh_host:
            settings.m_ssh_host = args.m_ssh_host
        if args.master_file is not None:
            # download_master = False
            settings.master_file = args.master_file
        if args.slave_file is not None:
            # download_slave = False
            settings.slave_file = args.slave_file
        if args.card_file is not None:
            settings.card_file = args.card_file
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

        settings.limit = args.limit

    # api config

    with open(settings.yaml_path) as stream:
        option_name_prefix = 'test_' if settings.test_mode else ''
        config = yaml.load(stream)
        settings.ssh_user = config.get(option_name_prefix + 'ssh_user')
        settings.ssh_pass = config.get(option_name_prefix + 'ssh_pass')
        settings.ssh_host = config.get(option_name_prefix + 'ssh_host')
        settings.ssh_port = config.get(option_name_prefix + 'ssh_port', 22)
        settings.m_ssh_user = config.get(option_name_prefix + 'm_ssh_user')
        settings.m_ssh_pass = config.get(option_name_prefix + 'm_ssh_pass')
        settings.m_ssh_host = config.get(option_name_prefix + 'm_ssh_host')
        settings.m_ssh_port = config.get(option_name_prefix + 'm_ssh_port', 22)
        settings.remote_bind_host = config.get(
            option_name_prefix + 'remote_bind_host', '127.0.0.1')
        settings.remote_bind_port = config.get(
            option_name_prefix + 'remote_bind_port', 3306)
        db_user = config.get(option_name_prefix + 'db_user')
        db_pass = config.get(option_name_prefix + 'db_pass')
        db_name = config.get(option_name_prefix + 'db_name')
        db_charset = config.get(option_name_prefix + 'db_charset', 'utf8mb4')
        wp_srv_offset = config.get(option_name_prefix + 'wp_srv_offset', 0)
        m_db_user = config.get(option_name_prefix + 'm_db_user')
        m_db_pass = config.get(option_name_prefix + 'm_db_pass')
        m_db_name = config.get(option_name_prefix + 'm_db_name')
        m_db_host = config.get(option_name_prefix + 'm_db_host')
        settings.m_x_cmd = config.get(option_name_prefix + 'm_x_cmd')
        settings.m_i_cmd = config.get(option_name_prefix + 'm_i_cmd')
        tbl_prefix = config.get(option_name_prefix + 'tbl_prefix', '')
        # wp_user = config.get(optionNamePrefix+'wp_user', '')
        # wp_pass = config.get(optionNamePrefix+'wp_pass', '')
        store_url = config.get(option_name_prefix + 'store_url', '')
        wp_user = config.get(option_name_prefix + 'wp_user')
        wp_pass = config.get(option_name_prefix + 'wp_pass')
        wp_callback = config.get(option_name_prefix + 'wp_callback')
        wp_api_key = config.get(option_name_prefix + 'wp_api_key')
        wp_api_secret = config.get(option_name_prefix + 'wp_api_secret')
        #  wc_api_key = config.get(optionNamePrefix+'wc_api_key')
        #  wc_api_secret = config.get(optionNamePrefix+'wc_api_secret')
        settings.remote_export_folder = config.get(
            option_name_prefix + 'remote_export_folder', '')

    ### DISPLAY CONFIG ###
    if Registrar.DEBUG_MESSAGE:
        if settings.test_mode:
            print "test_mode enabled"
        else:
            print "test_mode disabled"
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
    SyncUpdate.set_globals(settings.master_name, settings.slave_name,
                           settings.merge_mode, settings.default_last_sync)
    TimeUtils.set_wp_srv_offset(wp_srv_offset)

    ### SET UP DIRECTORIES ###

    for path in (settings.in_folder, settings.out_folder, settings.log_folder,
                 settings.src_folder, settings.pkl_folder):
        if not os.path.exists(path):
            os.mkdir(path)

    file_suffix = "_test" if settings.test_mode else ""
    file_suffix += "_filter" if do_filter else ""
    m_x_filename = "act_x" + file_suffix + "_" + settings.import_name + ".csv"
    # m_i_filename = "act_i"+file_suffix+"_"+import_name+".csv"
    s_x_filename = "wp_x" + file_suffix + "_" + settings.import_name + ".csv"
    # remoteExportPath = os.path.join(settings.remote_export_folder, m_x_filename)

    if download_master:
        ma_path = os.path.join(settings.in_folder, m_x_filename)
        ma_encoding = "utf-8"
    else:
        # ma_path = os.path.join(in_folder, "act_x_test_2016-05-03_23-01-48.csv")
        ma_path = os.path.join(settings.in_folder, settings.master_file)
        # ma_path = os.path.join(in_folder, "500-act-records-edited.csv")
        # ma_path = os.path.join(in_folder, "500-act-records.csv")
        ma_encoding = "utf8"
    if download_slave:
        sa_path = os.path.join(settings.in_folder, s_x_filename)
        sa_encoding = "utf8"
    else:
        sa_path = os.path.join(settings.in_folder, settings.slave_file)
        # sa_path = os.path.join(in_folder, "500-wp-records-edited.csv")
        sa_encoding = "utf8"

    # moPath = os.path.join(out_folder, m_i_filename)
    settings.rep_path = os.path.join(settings.out_folder,
                                     "usr_sync_report%s.html" % file_suffix)
    repd_path = os.path.join(settings.out_folder,
                             "usr_sync_report_duplicate%s.html" % file_suffix)
    w_pres_csv_path = os.path.join(settings.out_folder,
                                   "sync_report_wp%s.csv" % file_suffix)
    master_res_csv_path = os.path.join(settings.out_folder,
                                       "sync_report_act%s.csv" % file_suffix)
    master_delta_csv_path = os.path.join(
        settings.out_folder, "delta_report_act%s.csv" % file_suffix)
    slave_delta_csv_path = os.path.join(settings.out_folder,
                                        "delta_report_wp%s.csv" % file_suffix)
    settings.m_fail_path = os.path.join(settings.out_folder,
                                        "act_fails%s.csv" % file_suffix)
    settings.s_fail_path = os.path.join(settings.out_folder,
                                        "wp_fails%s.csv" % file_suffix)
    # sqlPath = os.path.join(srcFolder, "select_userdata_modtime.sql")
    # pklPath = os.path.join(pklFolder, "parser_pickle%s.pkl" % file_suffix )
    # settings.log_path = os.path.join(settings.log_folder, "log_%s.txt" % settings.import_name)
    # settings.zip_path = os.path.join(settings.log_folder, "zip_%s.zip" % settings.import_name)

    ### PROCESS OTHER CONFIG ###

    assert store_url, "store url must not be blank"
    # xmlrpc_uri = store_url + 'xmlrpc.php'
    # json_uri = store_url + 'wp-json/wp/v2'

    settings.act_fields = ";".join(ColData_User.get_act_import_cols())

    # jsonconnect_params = {
    #     'json_uri': json_uri,
    #     'wp_user': wp_user,
    #     'wp_pass': wp_pass
    # }

    # wcApiParams = {
    # 'api_key':wc_api_key,
    # 'api_secret':wc_api_secret,
    # 'url':store_url
    # }

    wp_api_params = {
        'api_key': wp_api_key,
        'api_secret': wp_api_secret,
        'url': store_url,
        'wp_user': wp_user,
        'wp_pass': wp_pass,
        'callback': wp_callback
    }

    act_connect_params = {
        'hostname': settings.m_ssh_host,
        'port': settings.m_ssh_port,
        'username': settings.m_ssh_user,
        'password': settings.m_ssh_pass,
    }

    act_db_params = {
        'db_x_exe': settings.m_x_cmd,
        'db_i_exe': settings.m_i_cmd,
        'db_name': m_db_name,
        'db_host': m_db_host,
        'db_user': m_db_user,
        'db_pass': m_db_pass,
        'fields': settings.act_fields,
    }
    if settings.since_m:
        act_db_params['since'] = settings.since_m

    fs_params = {
        'import_name': settings.import_name,
        'remote_export_folder': settings.remote_export_folder,
        'in_folder': settings.in_folder,
        'out_folder': settings.out_folder
    }

    #########################################
    # Prepare Filter Data
    #########################################

    print debugUtils.hashify("PREPARE FILTER DATA"), timediff(settings)

    if do_filter:
        filter_files = {
            'users': settings.user_file,
            'emails': settings.email_file,
            'cards': settings.card_file,
        }
        filter_items = {}
        for key, filter_file in filter_files.items():
            if filter_file:
                try:
                    with open(os.path.join(settings.in_folder,
                                           filter_file)) as filter_file_obj:
                        filter_items[key] = [
                            re.sub(r'\s*([^\s].*[^\s])\s*(?:\n)', r'\1', line)
                            for line in filter_file_obj
                        ]
                except IOError as exc:
                    SanitationUtils.safePrint(
                        "could not open %s file [%s] from %s" % (
                            key, filter_file, unicode(os.getcwd())))
                    raise exc
        if settings.since_m:
            filter_items['sinceM'] = TimeUtils.wp_strp_mktime(settings.since_m)
        if settings.since_s:
            filter_items['sinceS'] = TimeUtils.wp_strp_mktime(settings.since_s)
    else:
        filter_items = None

    print filter_items

    #########################################
    # Download / Generate Slave Parser Object
    #########################################

    print debugUtils.hashify(
        "Download / Generate Slave Parser Object"), timediff(settings)

    sa_parser = CSVParse_User(
        cols=ColData_User.get_wp_import_cols(),
        defaults=ColData_User.get_defaults(),
        filterItems=filter_items,
        limit=settings.limit,
        source=settings.slave_name)
    if download_slave:
        settings.ssh_tunnel_forwarder_address = (settings.ssh_host,
                                                 settings.ssh_port)
        settings.ssh_tunnel_forwarder_b_address = (settings.remote_bind_host,
                                                   settings.remote_bind_port)
        for host in [
                'ssh_tunnel_forwarder_address',
                'ssh_tunnel_forwarder_bind_address'
        ]:
            try:
                check_address(getattr(settings, host))
            except AttributeError:
                Registrar.registerError("host not specified in settings: %s" %
                                        host)
            except Exception as exc:
                raise UserWarning("Host must be valid: %s [%s = %s]" % (
                    str(exc), host, repr(getattr(settings, host))))
        ssh_tunnel_forwarder_params = {
            'ssh_address_or_host': settings.ssh_tunnel_forwarder_address,
            'ssh_password': settings.ssh_pass,
            'ssh_username': settings.ssh_user,
            'remote_bind_address': settings.ssh_tunnel_forwarder_b_address,
        }
        py_my_sql_connect_params = {
            'host': '127.0.0.1',
            'user': db_user,
            'password': db_pass,
            'db': db_name,
            'charset': db_charset,
            'use_unicode': True,
            'tbl_prefix': tbl_prefix,
        }

        print "SSHTunnelForwarderParams", ssh_tunnel_forwarder_params
        print "PyMySqlconnect_params", py_my_sql_connect_params

        with UsrSyncClient_SQL_WP(ssh_tunnel_forwarder_params,
                                  py_my_sql_connect_params) as client:
            client.analyse_remote(
                sa_parser, limit=settings.limit, filterItems=filter_items)

            sa_parser.getObjList().exportItems(
                os.path.join(settings.in_folder, s_x_filename),
                ColData_User.get_wp_import_col_names())

    else:
        sa_parser.analyseFile(sa_path, sa_encoding)

    # CSVParse_User.printBasicColumns( list(chain( *saParser.emails.values() )) )

    #########################################
    # Generate and Analyse ACT CSV files using shell
    #########################################

    ma_parser = CSVParse_User(
        cols=ColData_User.get_act_import_cols(),
        defaults=ColData_User.get_defaults(),
        contact_schema='act',
        filterItems=filter_items,
        limit=settings.limit,
        source=settings.master_name)

    print debugUtils.hashify("Generate and Analyse ACT data"), timediff(
        settings)

    if download_master:
        for thing in [
                'm_x_cmd', 'm_i_cmd', 'remote_export_folder', 'act_fields'
        ]:
            assert getattr(settings, thing), "settings must specify %s" % thing

        with UsrSyncClient_SSH_ACT(act_connect_params, act_db_params,
                                   fs_params) as master_client:
            master_client.analyse_remote(ma_parser, limit=settings.limit)
    else:
        ma_parser.analyseFile(
            ma_path, dialect_suggestion='act_out', encoding=ma_encoding)

    # CSVParse_User.printBasicColumns(  saParser.roles['WP'] )
    #
    # exit()
    # quit()

    # print "first maParser source:"
    # print maParser.objects.values()[0]['source']
    # print "first saParse source:"
    # print saParser.objects.values()[0]['source']

    # quit()

    # get matches

    global_matches = MatchList()
    anomalous_match_lists = {}
    new_masters = MatchList()
    new_slaves = MatchList()
    duplicate_matchlists = OrderedDict()
    anomalous_parselists = {}
    # nonstatic_updates = []
    nonstatic_s_updates = []
    nonstatic_m_updates = []
    static_updates = []
    # staticSUpdates = []
    # staticMUpdates = []
    problematic_updates = []
    master_updates = []
    slave_updates = []
    m_delta_updates = []
    s_delta_updates = []
    email_conflict_matches = ConflictingMatchList(
        index_fn=EmailMatcher.email_index_fn)

    def deny_anomalous_match_list(match_list_type, anomalous_match_list):
        """ add the matchlist to the list of anomalous match lists if it is not empty """
        try:
            assert not anomalous_match_list
        except AssertionError:
            # print "could not deny anomalous match list", match_list_type,
            # exc
            anomalous_match_lists[match_list_type] = anomalous_match_list

    def deny_anomalous_parselist(parselist_type, anomalous_parselist):
        """ add the parselist to the list of anomalous parse lists if it is not empty """
        try:
            assert not anomalous_parselist
        except AssertionError:
            # print "could not deny anomalous parse list", parselist_type, exc
            anomalous_parselists[parselist_type] = anomalous_parselist

    if args.do_sync:  # pylint: disable=too-many-nested-blocks
        # for every username in slave, check that it exists in master
        # TODO: fix too-many-nested-blocks

        print debugUtils.hashify("processing usernames")
        print timediff(settings)

        deny_anomalous_parselist('saParser.nousernames', sa_parser.nousernames)

        username_matcher = UsernameMatcher()
        username_matcher.process_registers(sa_parser.usernames,
                                           ma_parser.usernames)

        deny_anomalous_match_list('usernameMatcher.slaveless_matches',
                                  username_matcher.slaveless_matches)
        deny_anomalous_match_list('usernameMatcher.duplicate_matches',
                                  username_matcher.duplicate_matches)

        duplicate_matchlists['username'] = username_matcher.duplicate_matches

        global_matches.add_matches(username_matcher.pure_matches)

        if Registrar.DEBUG_MESSAGE:
            print "username matches (%d pure)" % len(
                username_matcher.pure_matches)
            # print repr(usernameMatcher)

        if Registrar.DEBUG_DUPLICATES and username_matcher.duplicate_matches:
            print("username duplicates: %s" %
                  len(username_matcher.duplicate_matches))

        print debugUtils.hashify("processing cards")
        print timediff(settings)

        # for every card in slave not already matched, check that it exists in
        # master

        deny_anomalous_parselist('maParser.nocards', ma_parser.nocards)

        card_matcher = CardMatcher(global_matches.s_indices,
                                   global_matches.m_indices)
        card_matcher.process_registers(sa_parser.cards, ma_parser.cards)

        deny_anomalous_match_list('cardMatcher.duplicate_matches',
                                  card_matcher.duplicate_matches)
        deny_anomalous_match_list('cardMatcher.masterless_matches',
                                  card_matcher.masterless_matches)

        duplicate_matchlists['card'] = card_matcher.duplicate_matches

        global_matches.add_matches(card_matcher.pure_matches)

        if Registrar.DEBUG_MESSAGE:
            print "card matches (%d pure)" % len(card_matcher.pure_matches)
            # print repr(cardMatcher)

        if Registrar.DEBUG_DUPLICATES and card_matcher.duplicate_matches:
            print "card duplicates: %s" % len(card_matcher.duplicate_matches)

        # #for every email in slave, check that it exists in master

        print debugUtils.hashify("processing emails")
        print timediff(settings)

        deny_anomalous_parselist("saParser.noemails", sa_parser.noemails)

        email_matcher = NocardEmailMatcher(global_matches.s_indices,
                                           global_matches.m_indices)

        email_matcher.process_registers(sa_parser.nocards, ma_parser.emails)

        new_masters.add_matches(email_matcher.masterless_matches)
        new_slaves.add_matches(email_matcher.slaveless_matches)
        global_matches.add_matches(email_matcher.pure_matches)
        duplicate_matchlists['email'] = email_matcher.duplicate_matches

        if Registrar.DEBUG_MESSAGE:
            print "email matches (%d pure)" % (len(email_matcher.pure_matches))
            # print repr(emailMatcher)

        if Registrar.DEBUG_DUPLICATES and email_matcher.duplicate_matches:
            print "email duplicates: %s" % len(email_matcher.duplicate_matches)

        # TODO: further sort emailMatcher

        print debugUtils.hashify("BEGINNING MERGE (%d)" % len(global_matches))
        print timediff(settings)

        sync_cols = ColData_User.get_sync_cols()

        if Registrar.DEBUG_PROGRESS:
            sync_progress_counter = ProgressCounter(len(global_matches))

        for count, match in enumerate(global_matches):
            if Registrar.DEBUG_PROGRESS:
                sync_progress_counter.maybePrintUpdate(count)
                # print "examining globalMatch %d" % count
                # # print SanitationUtils.safePrint( match.tabulate(tablefmt = 'simple'))
                # print repr(match)

            m_object = match.m_objects[0]
            s_object = match.s_objects[0]

            sync_update = SyncUpdate_Usr_Api(m_object, s_object)
            sync_update.update(sync_cols)

            # if(Registrar.DEBUG_MESSAGE):
            #     print "examining SyncUpdate"
            #     SanitationUtils.safePrint( syncUpdate.tabulate(tablefmt = 'simple'))

            if sync_update.m_updated and sync_update.m_deltas:
                insort(m_delta_updates, sync_update)

            if sync_update.s_updated and sync_update.s_deltas:
                insort(s_delta_updates, sync_update)

            if not sync_update:
                continue

            if sync_update.s_updated:
                sync_slave_updates = sync_update.getSlaveUpdates()
                if 'E-mail' in sync_slave_updates:
                    new_email = sync_slave_updates['E-mail']
                    if new_email in sa_parser.emails:
                        m_objects = [m_object]
                        s_objects = [s_object] + sa_parser.emails[new_email]
                        SanitationUtils.safePrint("duplicate emails",
                                                  m_objects, s_objects)
                        try:
                            email_conflict_matches.add_match(
                                Match(m_objects, s_objects))
                        except Exception as exc:
                            SanitationUtils.safePrint(
                                ("something happened adding an email "
                                 "conflict, new_email: %s ; exception: %s") %
                                (new_email, exc))
                        continue

            if not sync_update.important_static:
                if sync_update.m_updated and sync_update.s_updated:
                    if sync_update.s_mod:
                        insort(problematic_updates, sync_update)
                        continue
                elif sync_update.m_updated and not sync_update.s_updated:
                    insort(nonstatic_m_updates, sync_update)
                    if sync_update.s_mod:
                        insort(problematic_updates, sync_update)
                        continue
                elif sync_update.s_updated and not sync_update.m_updated:
                    insort(nonstatic_s_updates, sync_update)
                    if sync_update.s_mod:
                        insort(problematic_updates, sync_update)
                        continue

            if sync_update.s_updated or sync_update.m_updated:
                insort(static_updates, sync_update)
                if sync_update.m_updated and sync_update.s_updated:
                    insort(master_updates, sync_update)
                    insort(slave_updates, sync_update)
                if sync_update.m_updated and not sync_update.s_updated:
                    insort(master_updates, sync_update)
                if sync_update.s_updated and not sync_update.m_updated:
                    insort(slave_updates, sync_update)

        print debugUtils.hashify("COMPLETED MERGE")
        print timediff(settings)

        # TODO: process duplicates here

    #########################################
    # Write Report
    #########################################

    print debugUtils.hashify("Write Report")
    print timediff(settings)

    with io.open(settings.rep_path, 'w+', encoding='utf8') as res_file:

        repd_file = None
        if args.process_duplicates:
            repd_file = io.open(repd_path, 'w+', encoding='utf8')

        css = ""
        reporter = HtmlReporter(css=css)

        basic_cols = ColData_User.get_basic_cols()
        address_cols = OrderedDict(basic_cols.items() + [
            ('address_reason', {}),
            ('Edited Address', {}),
            ('Edited Alt Address', {}),
        ])
        name_cols = OrderedDict(basic_cols.items() + [
            ('name_reason', {}),
            ('Edited Name', {}),
        ])
        csv_colnames = ColData_User.get_col_names(
            OrderedDict(basic_cols.items() + ColData_User.name_cols([
                'address_reason',
                'name_reason',
                'Edited Name',
                'Edited Address',
                'Edited Alt Address',
            ]).items()))

        sanitizing_group = HtmlReporter.Group('sanitizing',
                                              'Sanitizing Results')

        if sa_parser.bad_address:
            sanitizing_group.addSection(
                HtmlReporter.Section(
                    's_bad_addresses_list',
                    title='Bad %s Address List' % settings.slave_name.title(),
                    description='%s records that have badly formatted addresses'
                    % settings.slave_name,
                    data=UsrObjList(sa_parser.bad_address.values()).tabulate(
                        cols=address_cols,
                        tablefmt='html', ),
                    length=len(sa_parser.bad_address)))

        if sa_parser.bad_name:
            sanitizing_group.addSection(
                HtmlReporter.Section(
                    's_bad_names_list',
                    title='Bad %s Names List' % settings.slave_name.title(),
                    description='%s records that have badly formatted names' %
                    settings.slave_name,
                    data=UsrObjList(sa_parser.bad_name.values()).tabulate(
                        cols=name_cols,
                        tablefmt='html', ),
                    length=len(sa_parser.bad_name)))
        if sa_parser.bad_name or sa_parser.bad_address:
            UsrObjList(sa_parser.bad_name.values() + ma_parser.bad_address.
                       values()).exportItems(w_pres_csv_path, csv_colnames)

        if ma_parser.bad_address:
            sanitizing_group.addSection(
                HtmlReporter.Section(
                    'm_bad_addresses_list',
                    title='Bad %s Address List' % settings.master_name.title(),
                    description='%s records that have badly formatted addresses'
                    % settings.master_name,
                    data=UsrObjList(ma_parser.bad_address.values()).tabulate(
                        cols=address_cols,
                        tablefmt='html', ),
                    length=len(ma_parser.bad_address)))

        if ma_parser.bad_name:
            sanitizing_group.addSection(
                HtmlReporter.Section(
                    'm_bad_names_list',
                    title='Bad %s Names List' % settings.master_name.title(),
                    description='%s records that have badly formatted names' %
                    settings.master_name,
                    data=UsrObjList(ma_parser.bad_name.values()).tabulate(
                        cols=name_cols,
                        tablefmt='html', ),
                    length=len(ma_parser.bad_name)))

        if ma_parser.bad_name or ma_parser.bad_address:
            UsrObjList(ma_parser.bad_name.values() + ma_parser.bad_address.values())\
                .exportItems(master_res_csv_path, csv_colnames)

        reporter.addGroup(sanitizing_group)

        if args.do_sync and (m_delta_updates + s_delta_updates):

            delta_group = HtmlReporter.Group('deltas', 'Field Changes')

            m_delta_list = UsrObjList(
                filter(None, [update.new_m_object
                              for update in m_delta_updates]))

            s_delta_list = UsrObjList(
                filter(None, [update.new_s_object
                              for update in s_delta_updates]))

            delta_cols = ColData_User.get_delta_cols()

            all_delta_cols = OrderedDict(
                ColData_User.get_basic_cols().items() + ColData_User.name_cols(
                    delta_cols.keys() + delta_cols.values()).items())

            if m_delta_list:
                delta_group.addSection(
                    HtmlReporter.Section(
                        'm_deltas',
                        title='%s Changes List' % settings.master_name.title(),
                        description='%s records that have changed important fields'
                        % settings.master_name,
                        data=m_delta_list.tabulate(
                            cols=all_delta_cols, tablefmt='html'),
                        length=len(m_delta_list)))

            if s_delta_list:
                delta_group.addSection(
                    HtmlReporter.Section(
                        's_deltas',
                        title='%s Changes List' % settings.slave_name.title(),
                        description='%s records that have changed important fields'
                        % settings.slave_name,
                        data=s_delta_list.tabulate(
                            cols=all_delta_cols, tablefmt='html'),
                        length=len(s_delta_list)))

            reporter.addGroup(delta_group)
            if m_delta_list:
                m_delta_list.exportItems(
                    master_delta_csv_path,
                    ColData_User.get_col_names(all_delta_cols))
            if s_delta_list:
                s_delta_list.exportItems(
                    slave_delta_csv_path,
                    ColData_User.get_col_names(all_delta_cols))

        report_matching = args.do_sync
        if report_matching:

            matching_group = HtmlReporter.Group('matching', 'Matching Results')
            matching_group.addSection(
                HtmlReporter.Section(
                    'perfect_matches',
                    **{
                        'title':
                        'Perfect Matches',
                        'description':
                        "%s records match well with %s" % (
                            settings.slave_name, settings.master_name),
                        'data':
                        global_matches.tabulate(tablefmt="html"),
                        'length':
                        len(global_matches)
                    }))

            match_list_instructions = {
                'cardMatcher.masterless_matches':
                '%s records do not have a corresponding CARD ID in %s (deleted?)'
                % (settings.slave_name, settings.master_name),
                'usernameMatcher.slaveless_matches':
                '%s records have no USERNAMEs in %s' %
                (settings.master_name, settings.slave_name),
            }

            for matchlist_type, match_list in anomalous_match_lists.items():
                if not match_list:
                    continue
                description = match_list_instructions.get(matchlist_type,
                                                          matchlist_type)
                if ('masterless' in matchlist_type or
                        'slaveless' in matchlist_type):
                    data = match_list.merge().tabulate(tablefmt="html")
                else:
                    data = match_list.tabulate(tablefmt="html")
                matching_group.addSection(
                    HtmlReporter.Section(
                        matchlist_type,
                        **{
                            # 'title': matchlist_type.title(),
                            'description': description,
                            'data': data,
                            'length': len(match_list)
                        }))

            # print debugUtils.hashify("anomalous ParseLists: ")

            parse_list_instructions = {
                "saParser.noemails":
                "%s records have invalid emails" % settings.slave_name,
                "maParser.noemails":
                "%s records have invalid emails" % settings.master_name,
                "maParser.nocards":
                "%s records have no cards" % settings.master_name,
                "saParser.nousernames":
                "%s records have no username" % settings.slave_name
            }

            for parselist_type, parse_list in anomalous_parselists.items():
                description = parse_list_instructions.get(parselist_type,
                                                          parselist_type)
                usr_list = UsrObjList()
                for obj in parse_list.values():
                    usr_list.append(obj)

                data = usr_list.tabulate(tablefmt="html")

                matching_group.addSection(
                    HtmlReporter.Section(
                        parselist_type,
                        **{
                            # 'title': matchlist_type.title(),
                            'description': description,
                            'data': data,
                            'length': len(parse_list)
                        }))

            reporter.addGroup(matching_group)

        report_sync = args.do_sync
        if report_sync:
            syncing_group = HtmlReporter.Group('sync', 'Syncing Results')

            syncing_group.addSection(
                HtmlReporter.Section(
                    (settings.master_name + "_updates"),
                    description=settings.master_name +
                    " items will be updated",
                    data='<hr>'.join([
                        update.tabulate(tablefmt="html")
                        for update in master_updates
                    ]),
                    length=len(master_updates)))

            syncing_group.addSection(
                HtmlReporter.Section(
                    (settings.slave_name + "_updates"),
                    description=settings.slave_name + " items will be updated",
                    data='<hr>'.join([
                        update.tabulate(tablefmt="html")
                        for update in slave_updates
                    ]),
                    length=len(slave_updates)))

            syncing_group.addSection(
                HtmlReporter.Section(
                    "problematic_updates",
                    description="items can't be merged because they are too dissimilar",
                    data='<hr>'.join([
                        update.tabulate(tablefmt="html")
                        for update in problematic_updates
                    ]),
                    length=len(problematic_updates)))

            reporter.addGroup(syncing_group)

        report_duplicates = args.process_duplicates
        if report_duplicates:

            dup_css = """
.highlight_old {color: red !important; }
.highlight_old {color: orange;}
.highlight_master {background: lightblue !important;}
.highlight_slave {background: lightpink !important;}
            """
            dup_reporter = HtmlReporter(css=dup_css)
            duplicate_group = HtmlReporter.Group('dup', 'Duplicate Results')

            basic_cols = ColData_User.get_basic_cols()
            dup_cols = OrderedDict(basic_cols.items() + [
                # ('Create Date', {}),
                # ('Last Sale', {})
            ])

            # What we're doing here is analysing the duplicates we've seen so far, and
            # creating a list of all the potential objects to delete and WHY
            # they should be deleted.

            def fn_obj_source_is(target_source):
                """
                returns a function that checks if the source of the object is equal
                to the given target source
                """

                def obj_source_is(object_data):
                    """
                    checks if the source of the object is equal to the given
                    target source
                    """

                    obj_source = object_data.get('source')
                    if obj_source and target_source == obj_source:
                        return True

                return obj_source_is

            def fn_user_older_than_wp(wp_time):
                """
                return a function that checks if the user is older than a date given
                in wp_time format
                """
                wp_time_obj = TimeUtils.wp_strp_mktime(wp_time)
                assert wp_time_obj, "should be valid time struct: %s" % wp_time

                def user_older_than(user_data):
                    """
                    determine if user is older than the time time specified in
                    fn_user_older_than_wp
                    """
                    if fn_obj_source_is(settings.master_name)(user_data):
                        assert hasattr(user_data, 'act_last_transaction'), \
                            "%s user should have act_last_transaction attr: %s, %s, source: %s" % (
                                settings.master_name,
                                type(user_data),
                                SanitationUtils.coerceAscii(user_data),
                                user_data.get('source'))
                        user_time_obj = user_data.act_last_transaction
                    else:
                        user_time_obj = user_data.last_modtime
                    return user_time_obj < wp_time_obj

                return user_older_than

            duplicates = Duplicates()

            for duplicate_type, duplicate_matchlist in duplicate_matchlists.items(
            ):
                print "checking duplicates of type %s" % duplicate_type
                print "len(duplicate_matchlist) %s" % len(duplicate_matchlist)
                for match in duplicate_matchlist:
                    if match.m_len <= 1:
                        continue
                        # only care about master duplicates at the moment
                    duplicate_objects = list(match.m_objects)
                    duplicates.add_conflictors(duplicate_objects,
                                               duplicate_type)

            address_duplicates = {}
            for address, objects in ma_parser.addresses.items():
                # print "analysing address %s " % address
                # for object_data in objects:
                # print " -> associated object: %s" % object_data
                if len(objects) > 1:
                    # if there are more than one objects associated with an address,
                    # add to the duplicate addresses report
                    address_duplicates[address] = objects
                    duplicates.add_conflictors(
                        objects, "address", weighting=0.1)

            for object_data in ma_parser.objects.values():
                if fn_user_older_than_wp(old_threshold)(object_data):
                    details = TimeUtils.wp_time_to_string(
                        object_data.act_last_transaction)
                    duplicates.add_conflictor(
                        object_data, "last_transaction_old", 0.5, details)
                elif fn_user_older_than_wp(oldish_threshold)(object_data):
                    details = TimeUtils.wp_time_to_string(
                        object_data.act_last_transaction)
                    duplicates.add_conflictor(
                        object_data, "last_transaction_oldish", 0.2, details)

            highlight_rules_master_slave = [
                ('highlight_master', fn_obj_source_is(settings.master_name)),
                ('highlight_slave', fn_obj_source_is(settings.slave_name))
            ]

            highlight_rules_old = [
                ('highlight_oldish', fn_user_older_than_wp(oldish_threshold)),
                ('highlight_old', fn_user_older_than_wp(old_threshold))
            ]

            highlight_rules_all = highlight_rules_master_slave + highlight_rules_old

            # if Registrar.DEBUG_DUPLICATES:
            # print duplicates.tabulate({}, tablefmt='plain')
            if duplicates:
                duplicate_group.addSection(
                    HtmlReporter.Section('all duplicates', **{
                        'title':
                        'All Duplicates',
                        'description':
                        "%s records are involved in duplicates" %
                        settings.master_name,
                        'data':
                        duplicates.tabulate(
                            dup_cols,
                            tablefmt='html',
                            highlight_rules=highlight_rules_all),
                        'length':
                        len(duplicates)
                    }))

            email_conflict_data = email_conflict_matches.tabulate(
                cols=dup_cols,
                tablefmt="html",
                highlight_rules=highlight_rules_all)
            duplicate_group.addSection(
                HtmlReporter.Section(
                    "email conflicts",
                    **{
                        # 'title': matchlist_type.title(),
                        'description': "email conflicts",
                        'data': email_conflict_data,
                        'length': len(email_conflict_matches)
                    }))

            email_duplicate_data = email_matcher.duplicate_matches.tabulate(
                tablefmt="html", highlight_rules=highlight_rules_all)
            if email_matcher.duplicate_matches:
                duplicate_group.addSection(
                    HtmlReporter.Section('email_duplicates', **{
                        'title':
                        'Email Duplicates',
                        'description':
                        "%s records match with multiple records in %s on email"
                        % (settings.slave_name, settings.master_name),
                        'data':
                        email_duplicate_data,
                        'length':
                        len(email_matcher.duplicate_matches)
                    }))

            match_list_instructions = {
                'cardMatcher.duplicate_matches':
                '%s records have multiple CARD IDs in %s' %
                (settings.slave_name, settings.master_name),
                'usernameMatcher.duplicate_matches':
                '%s records have multiple USERNAMEs in %s' %
                (settings.slave_name, settings.master_name)
            }

            for matchlist_type, match_list in anomalous_match_lists.items():
                if not match_list:
                    continue
                description = match_list_instructions.get(matchlist_type,
                                                          matchlist_type)
                if ('masterless' in matchlist_type or
                        'slaveless' in matchlist_type):
                    data = match_list.merge().tabulate(tablefmt="html")
                else:
                    data = match_list.tabulate(
                        tablefmt="html", highlight_rules=highlight_rules_all)
                matching_group.addSection(
                    HtmlReporter.Section(
                        matchlist_type,
                        **{
                            # 'title': matchlist_type.title(),
                            'description': description,
                            'data': data,
                            'length': len(match_list)
                        }))

            if address_duplicates:

                print "there are address duplicates"
                duplicate_group.addSection(
                    HtmlReporter.Section(
                        'address_duplicates',
                        title='Duplicate %s Addresses' %
                        settings.master_name.title(),
                        description='%s addresses that appear in multiple records'
                        % settings.master_name,
                        data="<br/>".join([
                            "<h4>%s</h4><p>%s</p>" % (address, UsrObjList(
                                objects).tabulate(
                                    cols=dup_cols,
                                    tablefmt='html',
                                    highlight_rules=highlight_rules_old))
                            for address, objects in address_duplicates.items()
                        ]),
                        length=len(address_duplicates)))
            dup_reporter.addGroup(duplicate_group)
            repd_file.write(dup_reporter.getDocumentUnicode())

        res_file.write(reporter.getDocumentUnicode())

    #########################################
    # Update databases
    #########################################

    all_updates = static_updates
    if args.do_problematic:
        all_updates += problematic_updates

    print debugUtils.hashify("Update databases (%d)" % len(all_updates))
    print timediff(settings)

    master_failures = []
    slave_failures = []

    if all_updates:
        Registrar.registerProgress("UPDATING %d RECORDS" % len(all_updates))

        if args.ask_before_update:
            try:
                input(
                    "Please read reports and press Enter to continue or ctrl-c to stop..."
                )
            except SyntaxError:
                pass

        if Registrar.DEBUG_PROGRESS:
            update_progress_counter = ProgressCounter(len(all_updates))

        with \
                UsrSyncClient_SSH_ACT(act_connect_params, act_db_params, fs_params) as master_client, \
                UsrSyncClient_WP(wp_api_params) as slave_client:
            # UsrSyncClient_JSON(jsonconnect_params) as slave_client:

            for count, update in enumerate(all_updates):
                if Registrar.DEBUG_PROGRESS:
                    update_progress_counter.maybePrintUpdate(count)
                # if update.wpid == '1':
                #     print repr(update.wpid)
                #     continue
                if update_master and update.m_updated:
                    try:
                        update.updateMaster(master_client)
                    except Exception as exc:
                        master_failures.append({
                            'update':
                            update,
                            'master':
                            SanitationUtils.coerceUnicode(update.new_m_object),
                            'slave':
                            SanitationUtils.coerceUnicode(update.new_s_object),
                            'mchanges':
                            SanitationUtils.coerceUnicode(
                                update.getMasterUpdates()),
                            'schanges':
                            SanitationUtils.coerceUnicode(
                                update.getSlaveUpdates()),
                            'exception':
                            repr(exc)
                        })
                        Registrar.registerError(
                            "ERROR UPDATING MASTER (%s): %s\n%s" %
                            (update.master_id, repr(exc),
                             traceback.format_exc()))

                        # continue
                if update_slave and update.s_updated:
                    try:
                        update.updateSlave(slave_client)
                    except Exception as exc:
                        slave_failures.append({
                            'update':
                            update,
                            'master':
                            SanitationUtils.coerceUnicode(update.new_m_object),
                            'slave':
                            SanitationUtils.coerceUnicode(update.new_s_object),
                            'mchanges':
                            SanitationUtils.coerceUnicode(
                                update.getMasterUpdates()),
                            'schanges':
                            SanitationUtils.coerceUnicode(
                                update.getSlaveUpdates()),
                            'exception':
                            repr(exc)
                        })
                        Registrar.registerError(
                            "ERROR UPDATING SLAVE (%s): %s\n%s" %
                            (update.slave_id, repr(exc),
                             traceback.format_exc()))

    def output_failures(failures, file_path):
        """
        outputs a list of lists of failures as a csv file to the path specified
        """
        with open(file_path, 'w+') as out_file:
            for failure in failures:
                Registrar.registerError(failure)
            dictwriter = unicodecsv.DictWriter(
                out_file,
                fieldnames=[
                    'update', 'master', 'slave', 'mchanges', 'schanges',
                    'exception'
                ],
                extrasaction='ignore', )
            dictwriter.writerows(failures)
            print "WROTE FILE: ", file_path

    output_failures(master_failures, settings.m_fail_path)
    output_failures(slave_failures, settings.s_fail_path)

    # Registrar.registerError('testing errors')


def catch_main():
    """
    Run the main function within a try statement and attempt to analyse failure
    """

    settings = argparse.Namespace()

    settings.in_folder = "../input/"
    settings.out_folder = "../output/"
    settings.log_folder = "../logs/"
    settings.src_folder = MODULE_LOCATION
    settings.pkl_folder = "pickles/"

    os.chdir(MODULE_PATH)

    settings.import_name = TimeUtils.get_ms_timestamp()
    settings.start_time = time.time()

    settings.test_mode = True
    settings.rep_path = ''
    settings.yaml_path = os.path.join("merger_config.yaml")
    settings.m_fail_path = os.path.join(settings.out_folder, "act_fails.csv")
    settings.s_fail_path = os.path.join(settings.out_folder, "wp_fails.csv")
    settings.log_path = os.path.join(settings.log_folder,
                                     "log_%s.txt" % settings.import_name)
    settings.zip_path = os.path.join(settings.log_folder,
                                     "zip_%s.zip" % settings.import_name)
    settings.user_file = False
    settings.card_file = False
    settings.email_file = False
    settings.since_m = False
    settings.since_s = False

    try:
        main(settings)
    except SystemExit:
        exit()
    except:
        Registrar.registerError(traceback.format_exc())

    with io.open(settings.log_path, 'w+', encoding='utf8') as log_file:
        for source, messages in Registrar.getMessageItems(1).items():
            print source
            log_file.writelines([SanitationUtils.coerceUnicode(source)])
            log_file.writelines([
                SanitationUtils.coerceUnicode(message) for message in messages
            ])
            for message in messages:
                pprint(message, indent=4, width=80, depth=2)

    #########################################
    # email reports
    #########################################

    files_to_zip = [
        settings.m_fail_path, settings.s_fail_path, settings.rep_path
    ]

    with zipfile.ZipFile(settings.zip_path, 'w') as zip_file:
        for file_to_zip in files_to_zip:
            try:
                os.stat(file_to_zip)
                zip_file.write(file_to_zip)
            except Exception as exc:
                if exc:
                    pass
        Registrar.registerMessage('wrote file %s' % settings.zip_path)


if __name__ == '__main__':
    catch_main()
