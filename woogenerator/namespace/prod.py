""" Provide configuration namespaces for GDrive <-> WC product sync. """

from __future__ import absolute_import

import os
import urlparse

from ..client.core import SyncClientGDrive, SyncClientNull
from ..client.prod import ProdSyncClientWC, ProdSyncClientXero
from ..coldata import ColDataBase, ColDataMyo, ColDataWoo, ColDataXero
from ..conf.core import DEFAULT_LOCAL_PROD_PATH, DEFAULT_LOCAL_PROD_TEST_PATH
from ..conf.parser import ArgumentParserProd
from ..parsing.api import ApiParseWoo
from ..parsing.myo import CsvParseMyo
from ..parsing.xero import CsvParseXero, ApiParseXero
from ..parsing.woo import CsvParseTT, CsvParseVT, CsvParseWoo
from .core import SettingsNamespaceProto
from ..utils import Registrar


class SettingsNamespaceProd(SettingsNamespaceProto):
    """ Provide namespace for product settings. """

    argparser_class = ArgumentParserProd

    def __init__(self, *args, **kwargs):
        self.local_live_config = getattr(self, 'local_live_config',
                                         DEFAULT_LOCAL_PROD_PATH)
        self.local_test_config = getattr(self, 'local_test_config',
                                         DEFAULT_LOCAL_PROD_TEST_PATH)
        self.variant = getattr(self, 'variant', None)
        self.woo_schemas = getattr(self, 'woo_schemas', [])
        self.myo_schemas = getattr(self, 'myo_schemas', [])
        self.xero_schemas = getattr(self, 'xero_schemas', [])
        self.taxo_depth = getattr(self, 'taxo_depth', None)
        self.item_depth = getattr(self, 'item_depth', None)
        self.thumbsize_x = getattr(self, 'thumbsize_x', None)
        self.thumbsize_y = getattr(self, 'thumbsize_y', None)
        self.img_raw_dir = getattr(self, 'img_raw_dir', None)
        self.img_raw_extra_dir = getattr(self, 'img_raw_extra_dir', None)
        self.img_cmp_dir = getattr(self, 'img_cmp_dir', None)
        super(SettingsNamespaceProd, self).__init__(*args, **kwargs)

    @property
    def schema_is_woo(self):
        return self.schema in self.woo_schemas

    @property
    def schema_is_myo(self):
        return self.schema in self.myo_schemas

    @property
    def schema_is_xero(self):
        return self.schema in self.xero_schemas

    @property
    def thumbsize(self):
        if self.thumbsize_x and self.thumbsize_y:
            return (self.thumbsize_x, self.thumbsize_y)

    @property
    def file_prefix(self):
        return "prod_"

    @property
    def file_suffix(self):
        response = ''
        if self.schema:
            response = self.schema
        if self.variant:
            response = "-".join([response, self.variant])
        return response

    @property
    def img_raw_dirs(self):
        response = []
        if self.img_raw_dir:
            response.append(self.img_raw_dir)
        if self.img_raw_extra_dir:
            response.append(self.img_raw_extra_dir)
        return response

    @property
    def col_data_class(self):
        """ Class used to obtain column metadata. """
        if self.schema_is_myo:
            return ColDataMyo
        elif self.schema_is_xero:
            return ColDataXero
        elif self.schema_is_woo:
            return ColDataWoo
        return ColDataBase

    @property
    def master_path(self):
        """ The path which the master data is downloaded to and read from. """
        if hasattr(self, 'master_file') and getattr(self, 'master_file'):
            return getattr(self, 'master_file')
        response = '%s%s' % (self.file_prefix, 'master')
        if self.variant:
            response = "-".join([response, self.variant])
        response += "-" + self.import_name + '.csv'
        response = os.path.join(self.in_dir_full, response)
        return response

    @property
    def slave_path(self):
        """ The path which the master data is downloaded to and read from. """
        if hasattr(self, 'slave_file') and getattr(self, 'slave_file'):
            return getattr(self, 'slave_file')
        response = '%s%s' % (self.file_prefix, 'slave')
        if self.variant:
            response = "-".join([response, self.variant])
        response += "-" + self.import_name + '.json'
        response = os.path.join(self.in_dir_full, response)
        return response

    @property
    def specials_path(self):
        """ The path which the specials data is downloaded to and read from. """
        if hasattr(self, 'specials_file') and getattr(self, 'specials_file'):
            return getattr(self, 'specials_file')
        response = '%s%s-%s.csv' % (
            self.file_prefix, 'specials', self.import_name
        )
        return os.path.join(self.in_dir_full, response)

    @property
    def dprc_path(self):
        """ The path which the dynamic pricing category data is stored. """
        if hasattr(self, 'dprc_file') and getattr(self, 'dprc_file'):
            return getattr(self, 'dprc_file')
        response = '%s%s-%s.csv' % (self.file_prefix, 'dprc', self.import_name)
        return os.path.join(self.in_dir_full, response)

    @property
    def dprp_path(self):
        """ The path which the dynamic pricing product data is stored. """
        if hasattr(self, 'dprp_file') and getattr(self, 'dprp_file'):
            return getattr(self, 'dprp_file')
        response = '%s%s-%s.csv' % (self.file_prefix, 'dprp', self.import_name)
        return os.path.join(self.in_dir_full, response)

    @property
    def fla_path(self):
        """ The path which the flattened csv file is stored. """
        response = "%s%s-%s.csv" % (
            self.file_prefix, 'flattened', self.import_name
        )
        return os.path.join(self.out_dir_full, response)

    @property
    def flv_path(self):
        """ The path which the flattened variation csv file is stored. """
        response = "%s%s-%s.csv" % (
            self.file_prefix, 'flattened-variations', self.import_name
        )
        return os.path.join(self.out_dir_full, response)

    @property
    def flu_path(self):
        """ The path which the flattened updated csv file is stored. """
        response = "%s%s-%s.csv" % (
            self.file_prefix, 'flattened-updated', self.import_name
        )
        return os.path.join(self.out_dir_full, response)

    @property
    def flvu_path(self):
        """ The path which the flattened updated variations csv file is stored. """
        response = "%s%s-%s.csv" % (
            self.file_prefix, 'flattened-variations-updated', self.import_name
        )
        return os.path.join(self.out_dir_full, response)

    @property
    def fls_path(self):
        """ The path which the flattened specials csv file is stored. """
        response = "%s%s-%s-%s.csv" % (
            self.file_prefix, 'flattened', self.current_special_id, self.import_name
        )
        return os.path.join(self.out_dir_full, response)

    @property
    def flvs_path(self):
        """ The path which the flattened specials variations csv file is stored. """
        response = "%s%s-%s-%s.csv" % (
            self.file_prefix, 'flattened-variations', self.current_special_id, self.import_name
        )
        return os.path.join(self.out_dir_full, response)

    @property
    def cat_path(self):
        """ The path which the categories csv file is stored. """
        response = "%s%s-%s.csv" % (
            self.file_prefix, 'categories', self.import_name
        )
        return os.path.join(self.out_dir_full, response)

    @property
    def myo_path(self):
        """ The path which the myob csv file is stored. """
        response = "%s%s-%s.csv" % (
            self.file_prefix, 'myob', self.import_name
        )
        return os.path.join(self.out_dir_full, response)

    @property
    def rep_delta_slave_csv_path(self):
        """ The path which the delta slave csv report is stored. """
        response = "%s%s_%s-%s.csv" % (
            self.file_prefix, 'delta_report', self.slave_name, self.import_name
        )
        return os.path.join(self.out_dir_full, response)

    @property
    def rep_cat_path(self):
        response = '%ssync_report_cat%s.html' % (
            self.file_prefix, self.file_suffix
        )
        if self.report_dir_full:
            response = os.path.join(self.report_dir_full, response)
        return response

    @property
    def rep_web_path(self):
        response = os.path.basename(self.rep_main_path)
        if self.get('web_dir'):
            response = os.path.join(self.web_dir, response)
        return response

    @property
    def rep_web_link(self):
        response = os.path.basename(self.rep_main_path)
        if self.get('web_address'):
            response = urlparse.urljoin(
                self.web_address, response
            )
        return response

    @property
    def img_dst(self):
        response = 'images'
        if self.schema:
            response += '-' + self.schema
        if self.get('img_cmd_dir'):
            response = os.path.join(self.img_cmd_dir, response)
        return response

    @property
    def exclude_cols(self):
        response = []
        if not self.do_images:
            response.extend(['Images', 'imgsum'])
        if not self.do_categories:
            response.extend(['catsum', 'catlist'])
        if not self.do_dyns:
            response.extend([
                'DYNCAT', 'DYNPROD', 'spsum', 'dprclist', 'dprplist', 'dprcIDlist',
                'dprpIDlist', 'dprcsum', 'dprpsum', 'pricing_rules'
            ])
        if not self.do_specials:
            response.extend([
                'SCHEDULE', 'sale_price', 'sale_price_dates_from',
                'sale_price_dates_to', 'RNS', 'RNF', 'RNT', 'RPS', 'RPF', 'RPT',
                'WNS', 'WNF', 'WNT', 'WPS', 'WPF', 'WPT', 'DNS', 'DNF', 'DNT',
                'DPS', 'DPF', 'DPT'
            ])
        return response

    @property
    def master_parser_class(self):
        """ Class used to parse master data """
        if self.schema_is_myo:
            return CsvParseMyo
        if self.schema_is_xero:
            return CsvParseXero
        if self.schema_is_woo:
            if self.schema == CsvParseTT.target_schema:
                return CsvParseTT
            if self.schema == CsvParseVT.target_schema:
                return CsvParseVT
            return CsvParseWoo

    @property
    def master_parser_args(self):
        """ Arguments used to create the master parser. """

        response = {
            'import_name': self.import_name,
            'cols': self.col_data_class.get_import_cols(),
            'defaults': self.col_data_class.get_defaults(),
            'schema': self.schema,
        }
        for key, settings_key in [
                ('item_depth', 'item_depth'),
                ('taxo_depth', 'taxo_depth'),
                ('special_rules', 'special_rules'),
                ('current_special_groups', 'current_special_groups'),
        ]:
            if hasattr(self, settings_key):
                response[key] = getattr(self, settings_key)
        if getattr(self, 'do_categories', None) and getattr(
                self, 'current_special_groups', None):
            response['add_special_categories'] = getattr(
                self, 'add_special_categories', None)
        return response

    @property
    def master_download_client_class(self):
        """ The class which is used to download and parse master data. """
        response = self.local_client_class
        if self.download_master:
            response = SyncClientGDrive
        return response

    @property
    def master_upload_client_class(self):
        """ The class which is used to download and parse master data. """
        response = self.local_client_class
        if self['update_master']:
            response = SyncClientGDrive
        return response

    @property
    def g_drive_params(self):
        response = {}
        for key, settings_key in [
                ('scopes', 'gdrive_scopes'),
                ('client_secret_file', 'gdrive_client_secret_file'),
                ('app_name', 'gdrive_app_name'),
                ('oauth_client_id', 'gdrive_oauth_client_id'),
                ('oauth_client_secret', 'gdrive_oauth_client_secret'),
                ('credentials_dir', 'gdrive_credentials_dir'),
                ('credentials_file', 'gdrive_credentials_file'),
                ('gen_fid', 'gen_fid')
        ]:
            if hasattr(self, settings_key):
                response[key] = getattr(self, settings_key)
        if not self.download_master:
            response['skip_download'] = True
        return response

    @property
    def master_download_client_args(self):
        """ Return the arguments which are used by the client to analyse master data. """

        response = {}
        if self.master_download_client_class == SyncClientGDrive:
            response.update({
                'gdrive_params': self.g_drive_params
            })
        else:
            response.update({
                'encoding': self.get('master_encoding', 'utf8')
            })
        for key, settings_key in [
                ('dialect_suggestion', 'master_dialect_suggestion'),
                ('limit', 'master_parse_limit'),
        ]:
            if hasattr(self, settings_key):
                response[key] = getattr(self, settings_key)
        return response

    @property
    def slave_parser_class(self):
        response = ApiParseWoo
        if self.schema_is_xero:
            response = ApiParseXero
        return response

    @property
    def slave_parser_args(self):
        response = {
            'cols': self.col_data_class.get_import_cols(),
            'defaults': self.col_data_class.get_defaults(),
            'source': self.slave_name,
            'schema': self.schema,
            'import_name': self.import_name,
            'item_depth': self.item_depth,
            'taxo_depth': self.taxo_depth,
            'limit': self.slave_parse_limit,
        }
        return response

    @property
    def slave_download_client_class(self):
        response = self.local_client_class
        if self['download_slave']:
            if self.schema_is_woo:
                response = ProdSyncClientWC
            elif self.schema_is_xero:
                response = ProdSyncClientXero
        return response

    @property
    def slave_download_client_args(self):
        response = {}
        if self['download_slave']:
            if self.schema_is_woo:
                response['connect_params'] = self.slave_wc_api_params
            elif self.schema_is_xero:
                response['connect_params'] = self.slave_xero_api_params
        return response

    @property
    def slave_upload_client_class(self):
        response = self.local_client_class
        if self['update_slave']:
            response = ProdSyncClientWC
        return response

    @property
    def slave_upload_client_args(self):
        response = {
            'connect_params': self.slave_wc_api_params
        }
        return response

    @property
    def dirs(self):
        response = super(SettingsNamespaceProd, self).dirs or []
        if self.get('img_raw_dirs'):
            response.extend(self.img_raw_dirs)
        if self.get('img_cmp_dir'):
            response.append(self.img_cmp_dir)
        if self.get('web_dir'):
            response.append(self.web_dir)
        return response

    @property
    def current_special_id(self):
        response = self.get('current_special')
        if self.get('current_special_groups'):
            response = self.current_special_groups[0].special_id
        return response

    @property
    def add_special_categories(self):
        return self.do_specials and self.do_categories

    def init_settings(self, override_args=None):
        super(SettingsNamespaceProd, self).init_settings(override_args)

        if self['auto_create_new']:
            exc = UserWarning("auto-create not fully implemented yet")
            Registrar.register_warning(exc)
        if self.auto_delete_old:
            raise UserWarning("auto-delete not implemented yet")

        if self.do_specials:
            if self['current_special']:
                CsvParseWoo.current_special = self['current_special']
            CsvParseWoo.specialsCategory = "Specials"
            CsvParseWoo.add_special_categories = self['add_special_categories']

        CsvParseWoo.do_images = self.do_images
        CsvParseWoo.do_dyns = self.do_dyns
        CsvParseWoo.do_specials = self.do_specials
