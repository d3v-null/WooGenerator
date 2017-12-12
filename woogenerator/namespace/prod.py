""" Provide configuration namespaces for GDrive <-> WC product sync. """

from __future__ import absolute_import

import os
import urlparse

from ..client.core import SyncClientGDrive, SyncClientNull
from ..client.img import ImgSyncClientWP
from ..client.prod import (CatSyncClientWC, CatSyncClientWCLegacy,
                           ProdSyncClientWC, ProdSyncClientWCLegacy,
                           ProdSyncClientXero)
from ..coldata import (ColDataAttachment, ColDataProductMeridian,
                       ColDataProductVariationMeridian, ColDataWcProdCategory)
from ..conf.core import DEFAULT_LOCAL_PROD_PATH, DEFAULT_LOCAL_PROD_TEST_PATH
from ..conf.parser import ArgumentParserProd
from ..parsing.api import ApiParseWoo, ApiParseWooLegacy
from ..parsing.myo import CsvParseMyo
from ..parsing.woo import CsvParseTT, CsvParseVT, CsvParseWoo
from ..parsing.xero import ApiParseXero, CsvParseXero
from ..syncupdate import (SyncUpdateCatWoo, SyncUpdateImgWoo, SyncUpdateProd,
                          SyncUpdateProdWoo, SyncUpdateProdXero,
                          SyncUpdateVarWoo)
from ..utils import Registrar
from .core import SettingsNamespaceProto


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
    def img_raw_dir_contents(self):
        if not '_img_raw_dir_contents' in self:
            self._img_raw_dir_contents = {}
            for dir_ in self.img_raw_dirs:
                if dir_ and os.path.isdir(dir_):
                    self._img_raw_dir_contents[dir_] = os.listdir(dir_)
        return self._img_raw_dir_contents

    @property
    def coldata_class(self):
        """ Class used to obtain column metadata. """
        return ColDataProductMeridian

    @property
    def coldata_class_img(self):
        return ColDataAttachment

    @property
    def coldata_class_cat(self):
        return ColDataWcProdCategory

    @property
    def coldata_class_var(self):
        return ColDataProductVariationMeridian

    @property
    def coldata_img_target(self):
        return 'wp-api-v2'

    @property
    def coldata_img_target_write(self):
        return 'wp-api-v2-edit'

    @property
    def coldata_cat_target(self):
        return 'wc-wp-api-v2'

    @property
    def coldata_cat_target_write(self):
        return 'wc-wp-api-v2-edit'

    @property
    def coldata_gen_target(self):
        return 'gen-csv'

    @property
    def coldata_gen_target_write(self):
        return 'gen-api'

    @property
    def coldata_target(self):
        response = None
        if self.schema_is_woo:
            response = 'wc-wp-api-v2'
        elif self.schema_is_xero:
            response = 'xero-api'
        return response

    @property
    def coldata_target_write(self):
        response = None
        if self.schema_is_woo:
            response = 'wc-wp-api-v2-edit'
        elif self.schema_is_xero:
            response = 'xero-api'
        return response

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
        if self.schema_is_woo:
            response += '_woo_api'
            if self.get('wc_api_namespace'):
                response += '_' + self.get('wc_api_namespace')
        if self.schema_is_xero:
            response += '_xero_api'
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
    def myo_path(self):
        """ The path which the master myob csv data is stored. """
        response = "%s%s-%s.csv" % (
            self.file_prefix, 'myob', self.import_name
        )
        return os.path.join(self.out_dir_full, response)

    @property
    def xero_path(self):
        """ The path which the flattened master xero csv data is stored. """
        response = "%s%s-%s.csv" % (
            self.file_prefix, 'master_xero', self.import_name
        )
        return os.path.join(self.out_dir_full, response)

    @property
    def fla_path(self):
        """ The path which the flattened master csv data is stored. """
        if self.schema_is_myo:
            return self.myo_path
        if self.schema_is_xero:
            return self.xero_path
        response = "%s%s-%s.csv" % (
            self.file_prefix, 'flattened', self.import_name
        )
        return os.path.join(self.out_dir_full, response)

    @property
    def flv_path(self):
        """ The path which the flattened master variation csv data is stored. """
        response = "%s%s-%s.csv" % (
            self.file_prefix, 'flattened-variations', self.import_name
        )
        return os.path.join(self.out_dir_full, response)

    @property
    def flu_path(self):
        """ The path which the flattened master updated csv data is stored. """
        response = "%s%s-%s.csv" % (
            self.file_prefix, 'flattened-updated', self.import_name
        )
        return os.path.join(self.out_dir_full, response)

    @property
    def flvu_path(self):
        """ The path which the flattened master updated variations csv data is stored. """
        response = "%s%s-%s.csv" % (
            self.file_prefix, 'flattened-variations-updated', self.import_name
        )
        return os.path.join(self.out_dir_full, response)

    @property
    def fls_path(self):
        """ The path which the flattened master specials csv data is stored. """
        # don't need import name
        response = "%s%s-%s.csv" % (
            self.file_prefix, 'flattened', self.current_special_id
        )
        return os.path.join(self.out_dir_full, response)

    @property
    def flvs_path(self):
        """ The path which the flattened master specials variations csv data is stored. """
        # don't need import name
        response = "%s%s-%s.csv" % (
            self.file_prefix, 'flattened-variations', self.current_special_id
        )
        return os.path.join(self.out_dir_full, response)

    @property
    def cat_path(self):
        """ The path which the flattened master categories csv data is stored. """
        response = "%s%s-%s.csv" % (
            self.file_prefix, 'categories', self.import_name
        )
        return os.path.join(self.out_dir_full, response)

    @property
    def slave_cat_path(self):
        """ The path which the slave woo api category json data is cached. """
        if hasattr(self, 'slave_cat_file') and getattr(self, 'slave_cat_file'):
            return getattr(self, 'slave_cat_file')
        response = '%s%s' % (self.file_prefix, 'slave_cat')
        if self.schema_is_woo:
            response += '_woo_api'
            if self.get('wc_api_namespace'):
                response += '_' + self.get('wc_api_namespace')
        if self.variant:
            response = "-".join([response, self.variant])
        response += "-" + self.import_name + '.json'
        return os.path.join(self.in_dir_full, response)

    @property
    def slave_img_path(self):
        """ The path which the slave wp api image json data is cached. """
        if hasattr(self, 'slave_img_file') and getattr(self, 'slave_img_file'):
            return getattr(self, 'slave_img_file')
        response = '%s%s' % (self.file_prefix, 'slave_img')
        if self.variant:
            response = "-".join([response, self.variant])
        response += "-" + self.import_name + '.json'
        return os.path.join(self.in_dir_full, response)

    @property
    def rep_delta_slave_csv_path(self):
        """ The path which the delta slave csv report is stored. """
        response = "%s%s_%s-%s.csv" % (
            self.file_prefix, 'delta_report', self.slave_name, self.import_name
        )
        return os.path.join(self.out_dir_full, response)

    @property
    def rep_img_path(self):
        response = '%ssync_report_img%s.html' % (
            self.file_prefix, self.file_suffix
        )
        if self.report_dir_full:
            response = os.path.join(self.report_dir_full, response)
        return response

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
        if self.get('img_cmp_dir'):
            response = os.path.join(self.img_cmp_dir, response)
        return response

    @property
    def sync_handles_prod(self):
        response = self.coldata_class.get_sync_handles(
            self.coldata_gen_target_write, self.coldata_target_write
        )
        # TODO: exclude_cols are in gen format
        for handle in self.exclude_cols:
            if handle in response:
                del response[handle]
        return response

    @property
    def sync_handles_var(self):
        response = self.coldata_class_var.get_sync_handles(
            self.coldata_gen_target_write, self.coldata_target_write
        )
        # TODO: exclude_cols are in gen format
        for handle in self.exclude_cols:
            if handle in response:
                del response[handle]
        return response

    @property
    def sync_handles_img(self):
        response = self.coldata_class_img.get_sync_handles(
            self.coldata_gen_target_write, self.coldata_img_target_write
        )
        # for handle in ['post_status', 'file_path']:
        for handle in ['post_status']:
            if handle in response:
                del response[handle]
        return response

    @property
    def sync_handles_cat(self):
        response = self.coldata_class_cat.get_sync_handles(
            self.coldata_gen_target_write, self.coldata_cat_target_write
        )
        for handle in self.exclude_cols_cat:
            if handle in response:
                del response[handle]
        return response

    @property
    def exclude_cols(self):
        # TODO: convert these to their handles
        response = []
        if not self.do_images:
            response.extend(['Images', 'imgsum', 'image'])
        if not self.do_categories:
            response.extend(['catsum', 'catlist', 'categories'])
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
    def exclude_cols_cat(self):
        # TODO: convert these to their handles
        response = ['post_status']
        if not self.do_images:
            response.extend(['image'])
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
            'cols': self.coldata_class.get_col_data_native('read').keys(),
            'defaults': self.coldata_class.get_col_values_native('default'),
            'schema': self.schema,
        }
        for key, settings_key in [
                ('item_depth', 'item_depth'),
                ('taxo_depth', 'taxo_depth'),
                ('special_rules', 'special_rules'),
                ('dprp_rules', 'dprp_rules'),
                ('dprc_rules', 'dprc_rules'),
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
        if self.schema_is_xero:
            response = ApiParseXero
        elif self.wc_api_is_legacy:
            response = ApiParseWooLegacy
        else:
            response = ApiParseWoo
        return response

    @property
    def slave_parser_args(self):
        response = {
            'cols': self.coldata_class.get_col_data_native('read').keys(),
            'defaults': self.coldata_class.get_col_values_native('default'),
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
                if self.wc_api_is_legacy:
                    response = ProdSyncClientWCLegacy
                else:
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
            if self.wc_api_is_legacy:
                response = ProdSyncClientWCLegacy
            else:
                response = ProdSyncClientWC
        return response

    @property
    def slave_upload_client_args(self):
        response = {
            'connect_params': self.slave_wc_api_params
        }
        return response

    @property
    def slave_cat_sync_client_class(self):
        response = self.local_client_class
        if self.download_slave:
            if self.wc_api_is_legacy:
                response = CatSyncClientWCLegacy
            else:
                response = CatSyncClientWC
        return response

    @property
    def slave_cat_sync_client_args(self):
        return {
            'connect_params': self.slave_wc_api_params
        }

    @property
    def slave_img_sync_client_class(self):
        response = self.local_client_class
        if self.download_slave:
            response = ImgSyncClientWP
        return response

    @property
    def slave_img_sync_client_args(self):
        return {
            'connect_params': self.slave_wp_api_params
        }


    @property
    def syncupdate_class_prod(self):
        response = SyncUpdateProd
        if self.schema_is_woo:
            response = SyncUpdateProdWoo
        if self.schema_is_xero:
            response = SyncUpdateProdXero
        return response

    @property
    def syncupdate_class_cat(self):
        return SyncUpdateCatWoo

    @property
    def syncupdate_class_img(self):
        return SyncUpdateImgWoo

    @property
    def syncupdate_class_var(self):
        return SyncUpdateVarWoo

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
        if self.get('skip_special_categories'):
            return not self.skip_special_categories
        return self.do_specials and self.do_categories

    def init_settings(self, override_args=None):
        super(SettingsNamespaceProd, self).init_settings(override_args)

        if self['auto_create_new']:
            exc = UserWarning("auto-create not fully implemented yet")
            Registrar.register_warning(exc)
        if self.auto_delete_old:
            raise UserWarning("auto-delete not implemented yet")
        if self.do_remeta_images:
            raise UserWarning("remeta deprecated")
        if self.do_attributes:
            raise UserWarning("Automatic attribute sync not implemented yet.")

        if self.do_specials:
            if self['specials_mode'] == 'all_future':
                exc = UserWarning(
                    "all_future specials mode not implemented yet. "
                    "will behave like auto_next, use override to set other specials"
                )
                Registrar.register_warning(exc)
            if self['current_special']:
                CsvParseWoo.current_special = self['current_special']
            CsvParseWoo.specials_category_name = "Specials"
            CsvParseWoo.add_special_categories = self['add_special_categories']

        CsvParseWoo.do_images = self.do_images
        CsvParseWoo.do_dyns = self.do_dyns
        CsvParseWoo.do_specials = self.do_specials


    @property
    def master_pkey(self):
        return "rowcount"

    @property
    def slave_pkey(self):
        response = "Wordpress ID"
        if self.schema_is_myo:
            response = 'codesum'
        if self.schema_is_xero:
            response = 'item_id'
        return response
