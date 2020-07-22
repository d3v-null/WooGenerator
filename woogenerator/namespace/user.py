"""Provide configuration namespaces for user data."""

from __future__ import absolute_import

import os

from ..client.user import (UsrSyncClientSqlWP, UsrSyncClientSshAct,
                           UsrSyncClientWP)
from ..coldata import ColDataUser
from ..conf.core import DEFAULT_LOCAL_USER_PATH, DEFAULT_LOCAL_USER_TEST_PATH
from ..conf.parser import ArgumentParserUser
from ..contact_objects import FieldGroup
from ..parsing.user import CsvParseUser
from .core import SettingsNamespaceProto


class SettingsNamespaceUser(SettingsNamespaceProto):
    """Provide namespace for user settings."""
    argparser_class = ArgumentParserUser

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
        """Name used for main export."""
        return "%s_x%s_%s.csv" % (self.main_name, self.file_suffix,
                                  self.import_name)

    @property
    def s_x_name(self):
        """Name used for subordinate export."""
        return "%s_x%s_%s.csv" % (self.subordinate_name, self.file_suffix,
                                  self.import_name)

    @property
    def coldata_class(self):
        """Class used to obtain column metadata."""
        return ColDataUser

    @property
    def main_path(self):
        """Get path which the main data is downloaded to and read from."""
        if hasattr(self, 'main_file') and getattr(self, 'main_file'):
            return getattr(self, 'main_file')
        response = '%s%s-%s.csv' % (self.file_prefix, 'main',
                                    self.import_name)
        response = os.path.join(self.in_dir_full, response)
        return response

    @property
    def subordinate_path(self):
        """Get path which the subordinate data is downloaded to and read from."""
        if hasattr(self, 'subordinate_file') and getattr(self, 'subordinate_file'):
            return getattr(self, 'subordinate_file')
        response = '%s%s-%s.csv' % (self.file_prefix, 'subordinate',
                                    self.import_name)
        response = os.path.join(self.in_dir_full, response)
        return response

    @property
    def main_parser_class(self):
        """Class used to parse main data."""
        return CsvParseUser

    @property
    def main_parser_args(self):
        """Arguments used to create the main parser."""
        response = {
            'cols': self.coldata_class.get_act_import_cols(),
            'defaults': self.coldata_class.get_defaults(),
            'contact_schema': 'act',
            'source': self.main_name,
            # 'schema':self.schema
        }
        for key, settings_key in [
            ('filter_items', 'filter_items'),
        ]:
            if hasattr(self, settings_key):
                response[key] = getattr(self, settings_key)
        return response

    @property
    def main_download_client_class(self):
        """Get class which is used to download and parse main data."""
        response = self.local_client_class
        if self.download_main:
            response = UsrSyncClientSshAct
        return response

    @property
    def main_upload_client_class(self):
        """Get class which is used to download and parse main data."""
        response = self.local_client_class
        if self['update_main']:
            response = UsrSyncClientSshAct
        return response

    @property
    def main_connect_params(self):
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
        return ";".join(self.coldata_class.get_act_import_cols())

    @property
    def main_db_params(self):
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
    def main_download_client_args(self):
        """Return arguments used by the client to analyse main data."""
        response = {
            'encoding': self.get('main_encoding', 'utf8'),
            'dialect_suggestion': self.get('main_dialect_suggestion',
                                           'ActOut')
        }
        if self.main_download_client_class == UsrSyncClientSshAct:
            response.update({
                'connect_params': self.main_connect_params,
                'db_params': self.main_db_params,
                'fs_params': self.fs_params,
            })
        for key, settings_key in [('limit', 'main_parse_limit')]:
            if hasattr(self, settings_key):
                response[key] = getattr(self, settings_key)
        return response

    @property
    def main_upload_client_args(self):
        """Return arguments used by the client to analyse main data."""
        response = {
            'encoding': self.get('main_encoding', 'utf8'),
            'dialect_suggestion': self.get('main_dialect_suggestion',
                                           'ActOut')
        }
        if self.main_upload_client_class == UsrSyncClientSshAct:
            response.update({
                'connect_params': self.main_connect_params,
                'db_params': self.main_db_params,
                'fs_params': self.fs_params,
            })
        for key, settings_key in [('limit', 'main_parse_limit')]:
            if hasattr(self, settings_key):
                response[key] = getattr(self, settings_key)
        return response

    @property
    def subordinate_parser_class(self):
        """Class used to parse main data."""
        return CsvParseUser

    @property
    def subordinate_parser_args(self):
        response = {
            'cols': self.coldata_class.get_wp_import_cols(),
            'defaults': self.coldata_class.get_defaults(),
            'source': self.subordinate_name,
            'schema': self.schema
        }
        for key, settings_key in [
            ('filter_items', 'filter_items'),
        ]:
            if hasattr(self, settings_key):
                response[key] = getattr(self, settings_key)
        return response

    @property
    def subordinate_download_client_class(self):
        response = self.local_client_class
        if self.get('download_subordinate'):
            response = UsrSyncClientSqlWP
        return response

    @property
    def subordinate_connect_params(self):
        response = {
            'ssh_address_or_host': (self['ssh_host'], self['ssh_port']),
            'ssh_password':
            self['ssh_pass'],
            'ssh_username':
            self['ssh_user'],
            'remote_bind_address': (self['remote_bind_host'],
                                    self['remote_bind_port']),
        }
        return response

    @property
    def subordinate_db_params(self):
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
    def subordinate_download_client_args(self):
        response = {
            'encoding': self.get('subordinate_encoding', 'utf8'),
            'dialect_suggestion': self.get('subordinate_dialect_suggestion',
                                           'ActOut')
        }
        if self.get('download_subordinate'):
            response.update({
                'connect_params': self['subordinate_connect_params'],
                'db_params': self['subordinate_db_params'],
                'filter_items': self.get('filter_items')
            })
        for key, settings_key in [('limit', 'subordinate_parse_limit')]:
            if hasattr(self, settings_key):
                response[key] = getattr(self, settings_key)
        return response

    @property
    def subordinate_upload_client_class(self):
        response = self.local_client_class
        if self.get('update_subordinate'):
            response = UsrSyncClientWP
        return response

    @property
    def subordinate_upload_client_args(self):
        response = {}
        if self.get('update_subordinate'):
            response = {'connect_params': self.subordinate_wp_api_params}
        return response

    def init_settings(self, override_args=None):
        super(SettingsNamespaceUser, self).init_settings(override_args)
        FieldGroup.do_post = self.do_post

    @property
    def main_pkey(self):
        return "MYOB Card ID"

    @property
    def subordinate_pkey(self):
        return "Wordpress ID"
