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
from woogenerator.coldata import ColDataWpPost
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
    coldata_class = ColDataWpPost

    @pytest.mark.local
    def test_sql_vs_wp_api_post(self):
        self.settings.download_slave = True
        client_class = SyncClientSqlWP
        client_args = self.settings.slave_download_client_args

        with client_class(**client_args) as client:
            rows = client.get_rows(None, limit=1)
            headers = rows[0]
            first_values = rows[1]
            first_post = OrderedDict(zip(headers, first_values))
            if self.debug:
                print('rows:\n%s' % pformat(first_post.items()))
            wp_sql_first_post_normalized = self.coldata_class.normalize_data(
                first_post, 'wp-sql'
            )
            if self.debug:
                print('first_post normalized sql:\n%s' % pformat(
                    dict(wp_sql_first_post_normalized)
                ))

        client_class = SyncClientWP
        client_args = {
            'connect_params': self.settings.slave_wp_api_params
        }
        with client_class(**client_args) as client:
            client.endpoint_singular = 'post'
            first_post = client.get_first_endpoint_item()
            wp_api_first_post_normalized = self.coldata_class.translate_data_from(
                first_post, 'wp-api-v2'
            )
            if self.debug:
                print('first_post normalized api:\n%s' % pformat(
                    dict(wp_api_first_post_normalized)
                ))

        keys_wp_sql = set(wp_sql_first_post_normalized.keys())
        keys_wp_api = set(wp_api_first_post_normalized.keys())
        keys_intersect = keys_wp_sql.intersection(keys_wp_api)
        keys_difference = keys_wp_sql.difference(keys_wp_api)
        if self.debug:
            print('keys_intersect:\n%s' % pformat(keys_intersect))
            print('keys_difference:\n%s' % pformat(keys_difference))




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
