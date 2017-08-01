import os
import unittest
from os import path, sys

import yaml

from context import get_testdata, tests_datadir, woogenerator
from woogenerator.client.core import SyncClientGDrive
from woogenerator.client.prod import ProdSyncClientWC
from woogenerator.client.user import UsrSyncClientWP
from woogenerator.coldata import ColDataWoo
from woogenerator.utils import Registrar, TimeUtils


class AbstractSyncClientTestCase(unittest.TestCase):
    # yaml_path = "generator_config.yaml"
    yaml_path = os.path.join(tests_datadir, 'generator_config_test.yaml')
    optionNamePrefix = 'test_'
    # optionNamePrefix = ''

    def process_config(self, config):
        raise NotImplementedError()

    def setUp(self):
        self.import_name = TimeUtils.get_ms_timestamp()

        with open(self.yaml_path) as stream:
            config = yaml.load(stream)
            self.process_config(config)

        Registrar.DEBUG_ERROR = False
        Registrar.DEBUG_WARN = False
        Registrar.DEBUG_MESSAGE = False
        Registrar.DEBUG_PROGRESS = False

        # Registrar.DEBUG_PROGRESS = True
        # Registrar.DEBUG_MESSAGE = True
        # Registrar.DEBUG_ERROR = True


@unittest.skip('have not created config file yet')
class TestSyncClient(AbstractSyncClientTestCase):
    # optionNamePrefix = 'dummy_'
    optionNamePrefix = ''

    def __init__(self, *args, **kwargs):
        super(TestSyncClient, self).__init__(*args, **kwargs)
        self.g_drive_params = {}
        self.wc_api_params = {}
        self.product_parser_args = {}

        Registrar.DEBUG_API = True

    def process_config(self, config):
        gdrive_scopes = config.get('gdrive_scopes')
        gdrive_client_secret_file = config.get('gdrive_client_secret_file')
        gdrive_app_name = config.get('gdrive_app_name')
        gdrive_oauth_client_id = config.get('gdrive_oauth_client_id')
        gdrive_oauth_client_secret = config.get('gdrive_oauth_client_secret')
        gdrive_credentials_dir = config.get('gdrive_credentials_dir')
        gdrive_credentials_file = config.get('gdrive_credentials_file')
        gen_fid = config.get('gen_fid')
        gen_gid = config.get('gen_gid')
        dprc_gid = config.get('dprc_gid')
        dprp_gid = config.get('dprp_gid')
        spec_gid = config.get('spec_gid')
        us_gid = config.get('us_gid')
        xs_gid = config.get('xs_gid')

        wc_api_key = config.get(self.optionNamePrefix + 'wc_api_key')
        wc_api_secret = config.get(self.optionNamePrefix + 'wc_api_secret')
        wp_api_key = config.get(self.optionNamePrefix + 'wp_api_key')
        wp_api_secret = config.get(self.optionNamePrefix + 'wp_api_secret')
        wp_user = config.get(self.optionNamePrefix + 'wp_user')
        wp_pass = config.get(self.optionNamePrefix + 'wp_pass')
        wp_callback = config.get(self.optionNamePrefix + 'wp_callback')

        # wp_srv_offset = config.get(self.optionNamePrefix+'wp_srv_offset', 0)
        store_url = config.get(self.optionNamePrefix + 'store_url', '')

        self.g_drive_params = {
            'scopes': gdrive_scopes,
            'client_secret_file': gdrive_client_secret_file,
            'app_name': gdrive_app_name,
            'oauth_client_id': gdrive_oauth_client_id,
            'oauth_client_secret': gdrive_oauth_client_secret,
            'credentials_dir': gdrive_credentials_dir,
            'credentials_file': gdrive_credentials_file,
            'gen_fid': gen_fid,
            'gen_gid': gen_gid,
            'dprc_gid': dprc_gid,
            'dprp_gid': dprp_gid,
            'spec_gid': spec_gid,
            'us_gid': us_gid,
            'xs_gid': xs_gid,
        }

        # print "g_drive_params", self.g_drive_params

        self.wc_api_params = {
            'api_key': wc_api_key,
            'api_secret': wc_api_secret,
            'url': store_url,
            'limit': 6
            # 'version':'wc/v1'
        }

        # print "wc_api_params", self.wc_api_params

        self.wp_api_params = {
            'api_key': wp_api_key,
            'api_secret': wp_api_secret,
            'wp_user': wp_user,
            'wp_pass': wp_pass,
            'url': store_url,
            'callback': wp_callback
        }

        # print "wp_api_params", self.wp_api_params

        self.product_parser_args = {
            'self.import_name': self.import_name,
            # 'item_depth': item_depth,
            # 'taxo_depth': taxo_depth,
            'cols': ColDataWoo.get_import_cols(),
            'defaults': ColDataWoo.get_defaults(),
        }

        # print "product_parser_args", self.product_parser_args

    def test_g_drive_read(self):
        with SyncClientGDrive(self.g_drive_params) as client:
            self.assertTrue(client.drive_file)
            self.assertTrue(client.get_gm_modtime(self.g_drive_params['gen_gid']))
            # print "drive file:", client.drive_file
            # print "GID", client.get_gm_modtime(self.g_drive_params['gen_gid'])

    def test_prod_sync_client_wc_read(self):
        self.wc_api_params.update(timeout=1)
        with ProdSyncClientWC(self.wc_api_params) as client:
            # print client.service.get('products').text
            for pagecount, page in enumerate(client.get_iterator('products')):
                self.assertTrue(pagecount)
                # print "PAGE %d: " % pagecount
                if 'products' in page:
                    for page_product in page.get('products'):
                        if 'id' in page_product:
                            prod_str = page_product['id']
                        else:
                            prod_str = str(page_product)[:100]
                        self.assertTrue(prod_str)
                        # print "-> PRODUCT: ", prod_str

    @unittest.skip('out of scope')
    def test_usr_sync_client_wp_read(self):
        with UsrSyncClientWP(self.wp_api_params) as client:
            # print client.service.get('users').text
            for pagecount, page in enumerate(client.get_iterator('users')):
                self.assertTrue(pagecount)
                # print "PAGE %d: " % pagecount
                if 'users' in page:
                    for page_user in page.get('users'):
                        self.assertTrue(page_user)
                        # print "-> USER: ", str(page_user)[:50]


if __name__ == '__main__':
    unittest.main()
    # testSuite = unittest.TestSuite()
    # testSuite.addTest(TestSyncClient('test_usr_sync_client_wp_read'))
    # testSuite.addTest(TestSyncClient('test_prod_sync_client_wc_read'))
    # unittest.TextTestRunner().run(testSuite)
