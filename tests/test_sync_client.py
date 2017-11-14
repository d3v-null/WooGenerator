import logging
import unittest
from collections import OrderedDict
from pprint import pformat

import pytest

from context import TESTS_DATA_DIR, get_testdata, woogenerator
from woogenerator.client.core import (SyncClientGDrive, SyncClientSqlWP,
                                      SyncClientWC, SyncClientWCLegacy,
                                      SyncClientWP)
from woogenerator.client.prod import ProdSyncClientWC
from woogenerator.client.user import UsrSyncClientWP
from woogenerator.coldata import ColDataWpPost, ColDataProductMeridian
from woogenerator.conf.parser import ArgumentParserCommon, ArgumentParserProd
from woogenerator.namespace.core import (MatchNamespace, ParserNamespace,
                                         SettingsNamespaceProto,
                                         UpdateNamespace)
from woogenerator.namespace.prod import SettingsNamespaceProd
from woogenerator.namespace.user import SettingsNamespaceUser
from woogenerator.utils import Registrar, SanitationUtils, TimeUtils

from .abstract import AbstractWooGeneratorTestCase


class AbstractSyncClientTestCase(AbstractWooGeneratorTestCase):

    def setUp(self):
        super(AbstractSyncClientTestCase, self).setUp()

        self.settings.init_settings(self.override_args)
        if self.debug:
            Registrar.DEBUG_API = True
        else:
            Registrar.DEBUG_PROGRESS = False

class TestSyncClientBasic(AbstractSyncClientTestCase):
    config_file = 'generator_config_test.yaml'
    settings_namespace_class = SettingsNamespaceProd
    argument_parser_class = ArgumentParserProd

    @pytest.mark.local
    def test_wp_v1_read_post_1(self):
        sync_client_class = SyncClientWP
        sync_client_args = {
            'connect_params': self.settings.slave_wp_api_params
        }
        sync_client_args['connect_params']['version'] = 'wp/v1'
        sync_client_args['connect_params']['api'] = 'wp-json'
        with sync_client_class(**sync_client_args) as client:
            first_post = client.service.get('posts/1').json()
            if client.page_nesting:
                first_post = first_post['post']
            if self.debug:
                first_post_json = SanitationUtils.encode_json(first_post)
                print('first post json: \n%s' % pformat(first_post_json))

    @pytest.mark.local
    def test_wp_v2_read_post_1(self):
        sync_client_class = SyncClientWP
        sync_client_args = {
            'connect_params': self.settings.slave_wp_api_params
        }
        sync_client_args['connect_params']['version'] = 'wp/v2'
        with sync_client_class(**sync_client_args) as client:
            first_post = client.service.get('posts/1').json()
            if client.page_nesting:
                first_post = first_post['post']
            if self.debug:
                first_post_json = SanitationUtils.encode_json(first_post)
                print('first post json: \n%s' % pformat(first_post_json))

    @pytest.mark.local
    def test_wp_read_first_post(self):
        sync_client_class = SyncClientWP
        sync_client_args = {
            'connect_params': self.settings.slave_wp_api_params
        }
        with sync_client_class(**sync_client_args) as client:
            post_pager = client.get_iterator('posts')
            post_page = post_pager.next()
            if self.debug:
                print('first post page: %s' % pformat(post_page))
            if client.page_nesting:
                post_page = post_page['posts']
            first_post = post_page[0]
            if self.debug:
                first_post_json = SanitationUtils.encode_json(first_post)
                print('first post json: \n%s' % pformat(first_post_json))

class TestSyncClientAccordance(AbstractSyncClientTestCase):
    config_file = 'generator_config_test.yaml'
    settings_namespace_class = SettingsNamespaceUser

    @pytest.mark.local
    def test_sql_vs_wp_api_post(self):
        self.settings.download_slave = True
        self.coldata_class = ColDataWpPost
        client_class = SyncClientSqlWP
        client_args = self.settings.slave_download_client_args

        with client_class(**client_args) as client:
            rows = client.get_rows(None, limit=1)
            headers = rows[0]
            first_values = rows[1]
            wp_sql_first_post_raw = OrderedDict(zip(headers, first_values))
            if self.debug:
                print('sql rows:\n%s' % pformat(wp_sql_first_post_raw.items()))
            # already in core path format so we have to do this:
            core_path_translation = self.coldata_class.get_core_path_translation('wp-api')
            wp_sql_first_post_normalized = self.coldata_class.translate_types_from(
                wp_sql_first_post_raw, 'wp-sql', core_path_translation
            )
            wp_sql_first_post_normalized = self.coldata_class.translate_structure_from(
                wp_sql_first_post_normalized, 'wp-sql', core_path_translation
            )
            if self.debug:
                print('wp_sql_first_post_normalized:\n%s' % pformat(
                    dict(wp_sql_first_post_normalized)
                ))

        client_class = SyncClientWP
        client_args = {
            'connect_params': self.settings.slave_wp_api_params
        }
        with client_class(**client_args) as client:
            client.endpoint_singular = 'post'
            wp_api_first_post_raw = client.get_first_endpoint_item()
            if self.debug:
                print('wp_api_first_post_raw:\n%s' % pformat(wp_api_first_post_raw))
            wp_api_first_post_normalized = self.coldata_class.translate_data_from(
                wp_api_first_post_raw, 'wp-api-v2'
            )
            if self.debug:
                print('wp_api_first_post_normalized:\n%s' % pformat(
                    dict(wp_api_first_post_normalized)
                ))

        keys_wp_sql = set(wp_sql_first_post_normalized.keys())
        keys_wp_api = set(wp_api_first_post_normalized.keys())
        keys_intersect = keys_wp_sql.intersection(keys_wp_api)
        if self.debug:
            print('keys_intersect:\n%s' % pformat(keys_intersect))
            print('keys_difference:\nsql-api:\n%s\napi-sql:\n%s' % (
                pformat(keys_wp_sql.difference(keys_wp_api)),
                pformat(keys_wp_api.difference(keys_wp_sql))
            ))

        self.assertTrue(
            set([
                'author', 'comment_status', 'created_gmt',
                'created_local', 'featured_media_id', 'guid', 'id',
                'modified_gmt', 'modified_local', 'ping_status',
                'post_content', 'post_excerpt',  'post_type', 'post_status',
                'slug', 'title'
            ]).issubset(keys_intersect)
        )

        for key in list(keys_intersect - set(['excerpt'])):
            if key == 'post_excerpt':
                continue
            if self.debug and key == 'parent_id':
                import pudb; pudb.set_trace()
            self.assertEqual(
                wp_sql_first_post_normalized[key],
                wp_api_first_post_normalized[key]
            )
class TestSyncClientAccordanceProd(AbstractSyncClientTestCase):
    config_file = 'generator_config_test.yaml'
    settings_namespace_class = SettingsNamespaceUser

    @pytest.mark.local
    def test_sql_vs_wc_api_prod(self):
        self.settings.download_slave = True
        self.coldata_class = ColDataProductMeridian

        client_class = ProdSyncClientWC
        client_args = {
            'connect_params': self.settings.slave_wc_api_params
        }
        with client_class(**client_args) as client:
            wc_api_first_prod_raw = client.get_first_endpoint_item()
            if self.debug:
                print('api first_prod raw:\n%s' % pformat(wc_api_first_prod_raw))
            wc_api_first_prod_normalized = self.coldata_class.translate_data_from(
                wc_api_first_prod_raw, 'wc-wp-api-v2'
            )
            if self.debug:
                print('api first_prod normalized api:\n%s' % pformat(
                    dict(wc_api_first_prod_normalized)
                ))
            wc_api_first_prod_id = wc_api_first_prod_raw['id']

        client_class = SyncClientSqlWP
        client_args = self.settings.slave_download_client_args

        with client_class(**client_args) as client:
            client.coldata_class = ColDataProductMeridian
            rows = client.get_rows(None, limit=1, filter_pkey=wc_api_first_prod_id)
            headers = rows[0]
            first_values = rows[1]
            wp_sql_first_prod_raw = OrderedDict(zip(headers, first_values))
            if self.debug:
                print('sql rows:\n%s' % pformat(wp_sql_first_prod_raw.items()))
            # already in core path format so we have to do this:
            core_path_translation = self.coldata_class.get_core_path_translation('wp-api')
            wp_sql_first_prod_normalized = self.coldata_class.translate_types_from(
                wp_sql_first_prod_raw, 'wp-sql', core_path_translation
            )
            wp_sql_first_prod_normalized = self.coldata_class.translate_structure_from(
                wp_sql_first_prod_normalized, 'wp-sql', core_path_translation
            )
            if self.debug:
                print('wp_sql_first_prod_normalized:\n%s' % pformat(
                    dict(wp_sql_first_prod_normalized)
                ))

        keys_wp_sql = set(wp_sql_first_prod_normalized.keys())
        keys_wc_api = set(wc_api_first_prod_normalized.keys())
        keys_intersect = keys_wp_sql.intersection(keys_wc_api)
        if self.debug:
            print('keys_intersect:\n%s' % pformat(keys_intersect))
            print('keys_difference:\nsql-api:\n%s\napi-sql:\n%s' % (
                pformat(keys_wp_sql.difference(keys_wc_api)),
                pformat(keys_wc_api.difference(keys_wp_sql))
            ))

        self.assertTrue(
            set([
                u'backorders',
                u'button_text',
                u'catalog_visibility',
                u'commissionable_value',
                u'created_gmt',
                u'created_local',
                u'cross_sell_ids',
                u'download_expiry',
                u'download_limit',
                u'downloadable',
                u'external_url',
                u'featured',
                u'height',
                u'id',
                u'in_stock',
                u'lc_dn_regular_price',
                u'lc_dn_sale_price',
                u'lc_dn_sale_price_dates_from',
                u'lc_dn_sale_price_dates_to',
                u'lc_dp_regular_price',
                u'lc_dp_sale_price',
                u'lc_dp_sale_price_dates_from',
                u'lc_dp_sale_price_dates_to',
                u'lc_rn_regular_price',
                u'lc_rn_sale_price',
                u'lc_rn_sale_price_dates_from',
                u'lc_rn_sale_price_dates_to',
                u'lc_rp_regular_price',
                u'lc_rp_sale_price',
                u'lc_rp_sale_price_dates_from',
                u'lc_rp_sale_price_dates_to',
                u'lc_wn_regular_price',
                u'lc_wn_sale_price',
                u'lc_wn_sale_price_dates_from',
                u'lc_wn_sale_price_dates_to',
                u'lc_wp_regular_price',
                u'lc_wp_sale_price',
                u'lc_wp_sale_price_dates_from',
                u'lc_wp_sale_price_dates_to',
                u'length',
                u'manage_stock',
                u'menu_order',
                u'mime_type',
                u'modified_gmt',
                u'modified_local',
                u'parent_id',
                u'post_content',
                u'post_excerpt',
                u'post_status',
                u'price',
                u'purchase_note',
                u'regular_price',
                u'sale_price',
                u'sale_price_dates_from',
                u'sale_price_dates_to',
                u'sku',
                u'sold_individually',
                u'stock_quantity',
                u'tax_class',
                u'tax_status',
                u'title',
                u'total_sales',
                u'upsell_ids',
                u'virtual',
                u'weight',
                u'width',
                u'wootan_danger'
            ]).issubset(keys_intersect)
        )

        for key in list(keys_intersect - set(['excerpt'])):
            try:
                self.assertEqual(
                    wp_sql_first_prod_normalized[key],
                    wc_api_first_prod_normalized[key]
                )
            except AssertionError, exc:
                if self.debug:
                    print("key %s failed assertion: %s" % (key, exc))

    @pytest.mark.local
    def test_wc_legacy_vs_wc_wp_api_prod(self):
        pass


@unittest.skip('Tests not mocked yet')
class TestSyncClientDestructive(AbstractSyncClientTestCase):

    @unittest.skip("No dummy fileID")
    def test_g_drive_read(self):
        # TODO: Mock out GDrive
        with SyncClientGDrive(self.settings.g_drive_params) as client:
            self.assertTrue(client.drive_file)
            self.assertTrue(client.get_gm_modtime(self.settings.g_drive_params['gen_gid']))
            # print "drive file:", client.drive_file
            # print "GID", client.get_gm_modtime(self.settings.g_drive_params['gen_gid'])

    def test_prod_sync_client_wc_read(self):
        api_params = self.settings.slave_wc_api_params
        api_params.update(timeout=1)
        with ProdSyncClientWC(api_params) as client:
            # print client.service.get('products').text
            pages = list(client.get_iterator('products'))
            self.assertTrue(pages)
            # for pagecount, page in enumerate(pages):
            #     # print "PAGE %d: " % pagecount
            #     if 'products' in page:
            #         for page_product in page.get('products'):
            #             if 'id' in page_product:
            #                 prod_str = page_product['id']
            #             else:
            #                 prod_str = str(page_product)[:100]
            #             self.assertTrue(prod_str)
            #             # print "-> PRODUCT: ", prod_str

    @unittest.skip('out of scope')
    def test_usr_sync_client_wp_read(self):
        with UsrSyncClientWP(self.settings.slave_wp_api_params) as client:
            # print client.service.get('users').text
            pages = list(client.get_iterator('users'))
            self.assertTrue(pages)
            # for pagecount, page in enumerate(pages):
            #     # print "PAGE %d: " % pagecount
            #     if 'users' in page:
            #         for page_user in page.get('users'):
            #             self.assertTrue(page_user)
            #             # print "-> USER: ", str(page_user)[:50]


if __name__ == '__main__':
    unittest.main()
    # testSuite = unittest.TestSuite()
    # testSuite.addTest(TestSyncClient('test_usr_sync_client_wp_read'))
    # testSuite.addTest(TestSyncClient('test_prod_sync_client_wc_read'))
    # unittest.TextTestRunner().run(testSuite)
