"""Provide configuration namespaces for user data."""

from __future__ import absolute_import

import os

from ..client.user import (UsrSyncClientSqlWP, UsrSyncClientSshAct,
                           UsrSyncClientWP)
from ..coldata import ColDataUser
from ..conf.core import DEFAULT_LOCAL_USER_PATH, DEFAULT_LOCAL_USER_TEST_PATH
from ..conf.parser import ArgumentParserUser
from ..parsing.user import CsvParseUser
from .core import SettingsNamespaceProto


class SettingsNamespaceUser(SettingsNamespaceProto):
    """ Provide namespace for user settings. """
    argparser_class=ArgumentParserUser


    def __init__(self, *args, **kwargs):
        self.local_live_config = \
            getattr(self, 'local_live_config', DEFAULT_LOCAL_USER_PATH)
        self.local_test_config = \
            getattr(self, 'local_test_config', DEFAULT_LOCAL_USER_TEST_PATH)
        self.do_filter = getattr(self, 'do_filter', None)
        super(SettingsNamespaceUser, self).__init__(*args, **kwargs)
        # assert \
        # RoleGroup.schema_exists(self.schema), \
        # "Invalid schema: %s" % self.schema

    @property
    def file_prefix(self):
        return "user_"

    @property
    def file_suffix(self):
        response = ""
        if self.schema:
            response = self.schema
        if self.testmode:
            response += "_test"
        if self.do_filter:
            response += "_filter"
        return response

    @property
    def m_x_name(self):
        """ Name used for master export. """
        return "%s_x%s_%s.csv" % (self.master_name, self.file_suffix, self.import_name)

    @property
    def s_x_name(self):
        """ Name used for slave export. """
        return "%s_x%s_%s.csv" % (self.slave_name, self.file_suffix, self.import_name)

    @property
    def col_data_class(self):
        """ Class used to obtain column metadata. """
        return ColDataUser

    @property
    def master_path(self):
        """ The path which the master data is downloaded to and read from. """
        if hasattr(self, 'master_file') and getattr(self, 'master_file'):
            return getattr(self, 'master_file')
        response = '%s%s-%s.csv' % (self.file_prefix, 'master', self.import_name)
        response = os.path.join(self.in_dir_full, response)
        return response

    @property
    def slave_path(self):
        """ The path which the slave data is downloaded to and read from. """
        if hasattr(self, 'slave_file') and getattr(self, 'slave_file'):
            return getattr(self, 'slave_file')
        response = '%s%s-%s.csv' % (self.file_prefix, 'slave', self.import_name)
        response = os.path.join(self.in_dir_full, response)
        return response

    @property
    def master_parser_class(self):
        """ Class used to parse master data """
        return CsvParseUser

    @property
    def master_parser_args(self):
        """ Arguments used to create the master parser. """
        response = {
            'cols':self.col_data_class.get_act_import_cols(),
            'defaults':self.col_data_class.get_defaults(),
            'contact_schema':'act',
            'source':self.master_name,
            # 'schema':self.schema
        }
        for key, settings_key in [
                ('filter_items', 'filter_items'),
        ]:
            if hasattr(self, settings_key):
                response[key] = getattr(self, settings_key)
        return response

    @property
    def master_download_client_class(self):
        """ The class which is used to download and parse master data. """

        response = self.local_client_class
        if self.download_master:
            response = UsrSyncClientSshAct
        return response

    @property
    def master_upload_client_class(self):
        """ The class which is used to download and parse master data. """

        response = self.local_client_class
        if self['update_master']:
            response = UsrSyncClientSshAct
        return response

    @property
    def master_connect_params(self):
        response = {}
        for key, settings_key in [
                ('hostname', 'm_ssh_host'),
                ('port', 'm_ssh_port'),
                ('username', 'm_ssh_user'),
                ('password', 'm_ssh_pass'),
        ]:
            if hasattr(self, settings_key):
                response[key] = getattr(self, settings_key)
        return response

    @property
    def act_fields(self):
        return ";".join(self.col_data_class.get_act_import_cols())

    @property
    def master_db_params(self):
        response = {
            'fields': self.act_fields,
        }
        for key, settings_key in [
                ('db_x_exe', 'm_x_cmd'),
                ('db_i_exe', 'm_i_cmd'),
                ('db_name', 'm_db_name'),
                ('db_host', 'm_db_host'),
                ('db_user', 'm_db_user'),
                ('db_pass', 'm_db_pass'),
                ('since', 'since_m'),
        ]:
            if hasattr(self, settings_key):
                response[key] = getattr(self, settings_key)
        return response

    @property
    def fs_params(self):
        response = {
            'import_name': self.import_name,
            'remote_export_dir': self['remote_export_dir'],
            'in_dir': self.in_dir_full,
            'out_dir': self.out_dir_full
        }
        return response

    @property
    def master_download_client_args(self):
        """ Return the arguments which are used by the client to analyse master data. """

        response = {
            'encoding': self.get('master_encoding', 'utf8'),
            'dialect_suggestion': self.get('master_dialect_suggestion', 'ActOut')
        }
        if self.master_download_client_class == UsrSyncClientSshAct:
            response.update({
                'connect_params':self.master_connect_params,
                'db_params':self.master_db_params,
                'fs_params':self.fs_params,
            })
        for key, settings_key in [
                ('limit', 'master_parse_limit')
        ]:
            if hasattr(self, settings_key):
                response[key] = getattr(self, settings_key)
        return response

    @property
    def master_upload_client_args(self):
        """ Return the arguments which are used by the client to analyse master data. """

        response = {
            'encoding': self.get('master_encoding', 'utf8'),
            'dialect_suggestion': self.get('master_dialect_suggestion', 'ActOut')
        }
        if self.master_upload_client_class == UsrSyncClientSshAct:
            response.update({
                'connect_params':self.master_connect_params,
                'db_params':self.master_db_params,
                'fs_params':self.fs_params,
            })
        for key, settings_key in [
                ('limit', 'master_parse_limit')
        ]:
            if hasattr(self, settings_key):
                response[key] = getattr(self, settings_key)
        return response


    @property
    def slave_parser_class(self):
        """ Class used to parse master data """
        return CsvParseUser

    @property
    def slave_parser_args(self):
        response = {
            'cols':self.col_data_class.get_wp_import_cols(),
            'defaults':self.col_data_class.get_defaults(),
            'source':self.slave_name,
            'schema':self.schema
        }
        for key, settings_key in [
                ('filter_items', 'filter_items'),
        ]:
            if hasattr(self, settings_key):
                response[key] = getattr(self, settings_key)
        return response

    @property
    def slave_download_client_class(self):
        response = self.local_client_class
        if self.get('download_slave'):
            response = UsrSyncClientSqlWP
        return response

    @property
    def slave_connect_params(self):
        response = {
            'ssh_address_or_host': (self['ssh_host'], self['ssh_port']),
            'ssh_password': self['ssh_pass'],
            'ssh_username': self['ssh_user'],
            'remote_bind_address': (self['remote_bind_host'], self['remote_bind_port']),
        }
        return response

    @property
    def slave_db_params(self):
        response = {
            'host': self['db_host'],
            'user': self['db_user'],
            'password': self['db_pass'],
            'db': self['db_name'],
            'charset': self['db_charset'],
            'use_unicode': True,
            'tbl_prefix': self['tbl_prefix'],
        }
        return response

    @property
    def slave_download_client_args(self):
        response = {
            'encoding': self.get('slave_encoding', 'utf8'),
            'dialect_suggestion': self.get('slave_dialect_suggestion', 'ActOut')
        }
        if self.get('download_slave'):
            response.update({
                'connect_params':self['slave_connect_params'],
                'db_params':self['slave_db_params'],
                'filter_items':self.get('filter_items')
            })
        for key, settings_key in [
                ('limit', 'slave_parse_limit')
        ]:
            if hasattr(self, settings_key):
                response[key] = getattr(self, settings_key)
        return response

    @property
    def slave_upload_client_class(self):
        response = self.local_client_class
        if self.get('update_slave'):
            response = UsrSyncClientWP
        return response

    @property
    def slave_upload_client_args(self):
        response = {
        }
        if self.get('update_slave'):
            response = {
                'connect_params':self.slave_wp_api_params
            }
        return response


    @property
    def init_settings(self, override_args=None):
        super(SettingsNamespaceUser, self).init_settings(override_args)
        FieldGroup.do_post = self.do_post
