"""Provide configuration namespaces."""
from __future__ import absolute_import

import argparse
import os
import sys
import time
from collections import OrderedDict
from copy import copy
from pprint import pformat

from tabulate import tabulate

from ..client.core import SyncClientLocal, SyncClientNull
from ..client.email import EmailClientExchange, EmailClientSMTP
from ..coldata import ColDataBase
from ..conf.core import (DEFAULT_LOCAL_IN_DIR, DEFAULT_LOCAL_LOG_DIR,
                         DEFAULT_LOCAL_OUT_DIR, DEFAULT_LOCAL_PICKLE_DIR,
                         DEFAULT_LOCAL_WORK_DIR, DEFAULT_MASTER_NAME,
                         DEFAULT_SLAVE_NAME, DEFAULT_TESTMODE)
from ..contact_objects import FieldGroup
from ..matching import MatchList
from ..syncupdate import SyncUpdate
from ..utils import Registrar, TimeUtils


class SettingsNamespaceProto(argparse.Namespace):
    """ Provide namespace for settings in first stage, supports getitem """

    def __init__(self, *args, **kwargs):
        # This getattr stuff allows the attributes to be set in a subclass
        self.local_work_dir = getattr(self, 'local_work_dir', DEFAULT_LOCAL_WORK_DIR)
        self.local_live_config = getattr(self, 'local_live_config', None)
        self.local_test_config = getattr(self, 'local_test_config', None)
        self.testmode = getattr(self, 'testmode', DEFAULT_TESTMODE)
        self.in_dir = getattr(self, 'in_dir', DEFAULT_LOCAL_IN_DIR)
        self.out_dir = getattr(self, 'out_dir', DEFAULT_LOCAL_OUT_DIR)
        self.log_dir = getattr(self, 'log_dir', DEFAULT_LOCAL_LOG_DIR)
        self.pickle_dir = getattr(self, 'pickle_dir', DEFAULT_LOCAL_PICKLE_DIR)
        self.import_name = getattr(self, 'import_name', TimeUtils.get_ms_timestamp())
        self.master_name = getattr(self, 'master_name', DEFAULT_MASTER_NAME)
        self.slave_name = getattr(self, 'slave_name', DEFAULT_SLAVE_NAME)
        self.start_time = getattr(self, 'start_time', time.time())
        self.schema = getattr(self, 'schema', None)
        self.download_master = getattr(self, 'download_master', False)
        self.do_post = getattr(self, 'do_post', None)

        super(SettingsNamespaceProto, self).__init__(*args, **kwargs)

    def __getitem__(self, key):
        try:
            return getattr(self, key)
        except AttributeError:
            raise KeyError(key)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default


    def join_work_path(self, path):
        """ Join a given path relative to the local-work-dir in this namespace. """
        response = path
        if self.local_work_dir and path:
            response = os.path.join(self.local_work_dir, path)
        return response

    @property
    def second_stage_configs(self):
        """ Return the second stage config files according to this namespace. """
        response = []
        if self.local_live_config:
            response.append(self.local_live_config_full)
        if self.testmode and self.local_test_config:
            response.append(self.local_test_config_full)
        return response

    @property
    def local_test_config_full(self):
        if self.local_test_config:
            return self.join_work_path(self.local_test_config)

    @property
    def local_live_config_full(self):
        if self.local_live_config:
            return self.join_work_path(self.local_live_config)

    @property
    def in_dir_full(self):
        if self.in_dir:
            return self.join_work_path(self.in_dir)

    @property
    def out_dir_full(self):
        if self.out_dir:
            return self.join_work_path(self.out_dir)

    @property
    def report_dir_full(self):
        return self.out_dir_full

    @property
    def log_dir_full(self):
        if self.log_dir:
            return self.join_work_path(self.log_dir)

    @property
    def pickle_dir_full(self):
        if self.pickle_dir:
            return self.join_work_path(self.pickle_dir)

    @property
    def dirs(self):
        return [
            self.in_dir_full,
            self.out_dir_full,
            self.report_dir_full,
            self.log_dir_full,
            self.pickle_dir_full,
        ]

    @property
    def file_prefix(self):
        return ""

    @property
    def file_suffix(self):
        response = ""
        if self.testmode:
            response += "_test"
        if self.get('picklemode'):
            response += "_pickle"
        return response

    @property
    def slave_wp_api_params(self):
        response = {
            'api_key': self.get('wp_api_key'),
            'api_secret': self.get('wp_api_secret'),
            'url': self.get('store_url'),
            'wp_user': self.get('wp_user'),
            'wp_pass': self.get('wp_pass'),
            'callback': self.get('wp_callback')
        }
        if self.get('wp_api_version'):
            response['api_version'] = self.get('wp_api_version')
        return response

    @property
    def slave_wc_api_params(self):
        response = {
            'api_key': self.get('wc_api_key'),
            'api_secret': self.get('wc_api_secret'),
            'url': self.get('store_url'),
            'callback': self.get('wp_callback')
            # TODO: rename wp_callback to api_callback
        }
        if self.get('wc_api_version'):
            response['api_version'] = self.get('wc_api_version')
        return response

    @property
    def local_client_class(self):
        return SyncClientLocal

    @property
    def null_client_class(self):
        return SyncClientNull


    @property
    def col_data_class(self):
        """ Class used to obtain column metadata. """
        return ColDataBase

    @property
    def basic_cols(self):
        return self.col_data_class.get_basic_cols()

    @property
    def email_client(self):
        if self.get('mail_type') == 'exchange':
            return EmailClientExchange
        elif self.get('mail_type') == 'smtp':
            return EmailClientSMTP
        else:
            raise ValueError("No mail type specified")

    @property
    def email_connect_params(self):
        response = {}
        potential_keys = [
            ('host', 'mail_host'),
            ('user', 'mail_user'),
            ('pass', 'mail_pass'),
        ]
        client = self.email_client
        if issubclass(client, EmailClientExchange):
            potential_keys += [
                ('sender', 'mail_sender'),
            ]
        elif issubclass(client, EmailClientSMTP):
            potential_keys += [
                ('port', 'mail_port'),
            ]
        for resp_key, self_key in potential_keys:
            if hasattr(self, self_key):
                response[resp_key] = self[self_key]
        return response

    # File paths for reporting / piclking

    @property
    def pickle_path(self):
        if hasattr(self, 'pickle_file') and getattr(self, 'pickle_file'):
            return getattr(self, 'pickle_file')
        response = self.import_name
        if self.get('progress'):
            response += '_%s' % self['progress']
        response += '.pickle'
        if self.pickle_dir_full:
            response = os.path.join(self.pickle_dir_full, response)
        return response

    @property
    def rep_main_path(self):
        response = '%ssync_report%s.html' % (
            self.file_prefix, self.file_suffix
        )
        if self.report_dir_full:
            response = os.path.join(self.report_dir_full, response)
        return response

    @property
    def rep_dup_path(self):
        response = "%ssync_report_duplicate_%s.html" % (
            self.file_prefix, self.file_suffix
        )
        if self.report_dir_full:
            response = os.path.join(self.report_dir_full, response)
        return response

    @property
    def rep_san_path(self):
        response = "%ssync_report_sanitation_%s.html" % (
            self.file_prefix, self.file_suffix
        )
        if self.report_dir_full:
            response = os.path.join(self.report_dir_full, response)
        return response

    @property
    def rep_san_master_csv_path(self):
        response = "%s_bad_contact_%s_%s.csv" % (
            self.file_prefix, self.slave_name, self.file_suffix
        )
        if self.report_dir_full:
            response = os.path.join(self.report_dir_full, response)
        return response

    @property
    def rep_san_slave_csv_path(self):
        response = "%s_bad_contact_%s_%s.csv" % (
            self.file_prefix, self.slave_name, self.file_suffix
        )
        if self.report_dir_full:
            response = os.path.join(self.report_dir_full, response)
        return response

    @property
    def rep_match_path(self):
        response = "%ssync_report_matching_%s.html" % (
            self.file_prefix, self.file_suffix
        )
        if self.report_dir_full:
            response = os.path.join(self.report_dir_full, response)
        return response

    @property
    def rep_post_path(self):
        response = "%ssync_report_post_%s.html" % (
            self.file_prefix, self.file_suffix
        )
        if self.report_dir_full:
            response = os.path.join(self.report_dir_full, response)
        return response

    @property
    def rep_fail_master_csv_path(self):
        response = "%s%s_fails_%s.csv" % (
            self.file_prefix, self.master_name, self.file_suffix
        )
        if self.report_dir_full:
            response = os.path.join(self.report_dir_full, response)
        return response

    @property
    def rep_fail_slave_csv_path(self):
        response = "%s%s_fails_%s.csv" % (
            self.file_prefix, self.slave_name, self.file_suffix
        )
        if self.report_dir_full:
            response = os.path.join(self.report_dir_full, response)
        return response

    @property
    def rep_delta_master_csv_path(self):
        response = "%s%s_deltas_%s.csv" % (
            self.file_prefix, self.master_name, self.file_suffix
        )
        if self.report_dir_full:
            response = os.path.join(self.report_dir_full, response)
        return response

    @property
    def rep_delta_slave_csv_path(self):
        response = "%s%s_deltas_%s.csv" % (
            self.file_prefix, self.slave_name, self.file_suffix
        )
        if self.report_dir_full:
            response = os.path.join(self.report_dir_full, response)
        return response

    @property
    def log_path(self):
        response = '%s.log' % self.import_name
        if self.log_dir_full:
            response = os.path.join(self.log_dir_full, response)
        return response

    @property
    def zip_path(self):
        response = '%s.zip' % self.import_name
        if self.log_dir_full:
            response = os.path.join(self.log_dir_full, response)
        return response

    def init_dirs(self):
        for path in list(set(self.dirs)):
            if path and not os.path.exists(path):
                os.mkdir(path)

class ParserNamespace(argparse.Namespace):
    """ Collect parser variables into a single namespace. """

    def __init__(self, *args, **kwargs):
        super(ParserNamespace, self).__init__(*args, **kwargs)
        self.master = getattr(self, 'master', None)
        self.slave = getattr(self, 'slave', None)
        self.anomalous = {}

    def deny_anomalous(self, parselist_type, anomalous_parselist):
        """Add the parselist to the list of anomalous parse lists if it is not empty."""
        try:
            assert not anomalous_parselist
        except AssertionError:
            # print "could not deny anomalous parse list", parselist_type, exc
            self.anomalous[parselist_type] = anomalous_parselist

class MatchNamespace(argparse.Namespace):
    """ Collect variables used in matching into a single namespace. """

    def __init__(self, index_fn=None, *args, **kwargs):
        super(MatchNamespace, self).__init__(*args, **kwargs)
        self.globals = MatchList(index_fn=index_fn)
        self.new_master = MatchList(index_fn=index_fn)
        self.new_slave = MatchList(index_fn=index_fn)
        self.masterless = MatchList(index_fn=index_fn)
        self.slaveless = MatchList(index_fn=index_fn)
        self.anomalous = OrderedDict()
        self.duplicate = OrderedDict()
        self.conflict = OrderedDict()
        self.delete_slave = OrderedDict()
        self.delete_master = OrderedDict()

    def deny_anomalous(self, match_list_type, anomalous_match_list):
        """Add the matchlist to the list of anomalous match lists if it is not empty."""
        try:
            assert not anomalous_match_list
        except AssertionError:
            # print "could not deny anomalous match list", match_list_type,
            # exc
            self.anomalous[match_list_type] = anomalous_match_list

class UpdateNamespace(argparse.Namespace):
    """ Collect variables used in updates into a single namespace. """

    def __init__(self, *args, **kwargs):
        super(UpdateNamespace, self).__init__(*args, **kwargs)
        self.master = []
        self.slave = []
        self.static = []
        self.problematic = []
        self.nonstatic_master = []
        self.nonstatic_slave = []
        self.delta_master = []
        self.delta_slave = []
        self.new_master = []
        self.new_slave = []

class ResultsNamespace(argparse.Namespace):
    """ Collect information about failures into a single namespace. """

    result_attrs = ['fails_master', 'fails_slave', 'successes']

    def __init__(self, *args, **kwargs):
        super(ResultsNamespace, self).__init__(*args, **kwargs)
        self.fails_master = []
        self.fails_slave = []
        self.successes = []

    @property
    def as_dict(self):
        return dict([
            (attr, getattr(self, attr)) \
            for attr in self.result_attrs \
            if hasattr(self, attr)
        ])


    def __bool__(self):
        return bool(any(self.as_dict.values()))

def init_registrar(settings):
    # print "settings.verbosity = %s" % settings.verbosity
    # print "settings.quiet = %s" % settings.quiet
    if settings.verbosity > 0:
        Registrar.DEBUG_PROGRESS = True
        Registrar.DEBUG_ERROR = True
    if settings.verbosity > 1:
        Registrar.DEBUG_MESSAGE = True
    if settings.quiet:
        Registrar.DEBUG_PROGRESS = False
        Registrar.DEBUG_ERROR = False
        Registrar.DEBUG_MESSAGE = False

    Registrar.DEBUG_ABSTRACT = settings.debug_abstract
    Registrar.DEBUG_ADDRESS = settings.debug_address
    Registrar.DEBUG_API = settings.debug_api
    Registrar.DEBUG_CATS = settings.debug_cats
    Registrar.DEBUG_CLIENT = settings.debug_client
    Registrar.DEBUG_CONTACT = settings.debug_contact
    Registrar.DEBUG_DUPLICATES = settings.debug_duplicates
    Registrar.DEBUG_GDRIVE = settings.debug_gdrive
    Registrar.DEBUG_GEN = settings.debug_gen
    Registrar.DEBUG_IMG = settings.debug_img
    Registrar.DEBUG_MRO = settings.debug_mro
    Registrar.DEBUG_MYO = settings.debug_myo
    Registrar.DEBUG_NAME = settings.debug_name
    Registrar.DEBUG_PARSER = settings.debug_parser
    Registrar.DEBUG_SHOP = settings.debug_shop
    Registrar.DEBUG_SPECIAL = settings.debug_special
    Registrar.DEBUG_TREE = settings.debug_tree
    Registrar.DEBUG_UPDATE = settings.debug_update
    Registrar.DEBUG_UTILS = settings.debug_utils
    Registrar.DEBUG_VARS = settings.debug_vars
    Registrar.DEBUG_WOO = settings.debug_woo
    Registrar.DEBUG_TRACE = settings.debug_trace
    Registrar.DEBUG_USR = settings.debug_usr

class MetaSettings(object):
    """
    Store information about settings object as it transitions between states.
    """

    def __init__(self):
        self.states = OrderedDict()
        self.known_keys = set()
        self.override_args = None

    def set_override_args(self, override_args):
        self.override_args = override_args

    def add_state(self, name, vars_=None, configs=None):
        assert name not in self.states, "state already added"
        state_dict = {}
        if vars_:
            self.known_keys = self.known_keys | set(vars_.keys())
            state_dict["vars"] = vars_
        state_dict['configs'] = configs if configs else []
        self.states[name] = state_dict

    def set_state_vars(self, name, vars_):
        if not name in self.states:
            self.states[name] = {}
        self.states[name]['vars'] = vars_

    def tabulate(self, tablefmt=None, ignore_keys=None):
        subtitle_fmt = "*%s*"
        info_delimeter = "\n"
        info_fmt = "%s: %s"
        if tablefmt == "html":
            subtitle_fmt = "<h3>%s</h3>"
            info_delimeter = "<br/>"
            info_fmt = "<strong>%s:</strong> %s"

        info_components = []
        info_components += [subtitle_fmt % "Configs"]
        seen_configs = []
        for state_name, state in self.states.items():
            state_configs = state.get('configs', [])
            unseen_configs = [
                config for config in state_configs if config not in seen_configs
            ]
            info_components += [info_fmt % (
                state_name,
                ", ".join(unseen_configs)
            )]
            seen_configs += unseen_configs

        info_components += [subtitle_fmt % "Settings"]
        if ignore_keys is None:
            ignore_keys = []
        state_table = [['key'] + self.states.keys()]
        for key in sorted(list(self.known_keys)):
            if key in ignore_keys:
                continue
            state_table_row = [key] + [
                state.get('vars', {}).get(key) for state in self.states.values()
            ]
            state_table.append(state_table_row)
        info_components += [tabulate(state_table, tablefmt=tablefmt, headers="firstrow")]

        return info_delimeter.join(info_components)


def init_settings(override_args=None, settings=None, argparser_class=None):
    """
    Load config file and initialise settings object from given argparser class.
    """

    meta_settings = MetaSettings()

    if not settings:
        settings = argparser_class.namespace()

    meta_settings.add_state('init', copy(vars(settings)))

    ### First round of argument parsing determines which config files to read
    ### from core config files, CLI args and env vars

    proto_argparser = argparser_class.proto_argparser()

    Registrar.register_message("proto_parser: \n%s" % pformat(proto_argparser.get_actions()))

    parser_override = {'namespace':settings}
    if override_args is not None:
        parser_override['args'] = override_args
        meta_settings.set_override_args(override_args)
        settings.called_with_args = override_args
    else:
        settings.called_with_args = sys.argv

    settings, _ = proto_argparser.parse_known_args(**parser_override)

    meta_settings.add_state('proto', copy(vars(settings)))

    ### Second round gets all the arguments from all config files

    # TODO: implement "ask for password" feature
    argparser = argparser_class()

    # TODO: test set local work dir
    # TODO: test set live config
    # TODO: test set test config
    # TODO: move in, out, log dirs to full

    for conf in settings.second_stage_configs:
        # print "adding conf: %s" % conf
        argparser.add_default_config_file(conf)

    if settings.help_verbose:
        if 'args' not in parser_override:
            parser_override['args'] = []
        parser_override['args'] += ['--help']


    # defaults first
    settings = argparser.parse_args(**parser_override)

    meta_settings.add_state('main', copy(vars(settings)), argparser.default_config_files)

    init_registrar(settings)

    # Init class variables

    FieldGroup.do_post = settings.do_post
    SyncUpdate.set_globals(settings.master_name, settings.slave_name,
                           settings.merge_mode, settings.last_sync)
    TimeUtils.set_wp_srv_offset(settings.wp_srv_offset)

    Registrar.register_message(
        "meta settings:\n%s" %
        meta_settings.tabulate(ignore_keys=['called_with_args'])
    )

    return settings
