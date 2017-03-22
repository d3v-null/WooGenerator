import os
from os import sys, path
import unittest
import yaml
from unittest import TestCase  # , main, skip

from context import woogenerator
from context import get_testdata, tests_datadir
from woogenerator.sync_client import SyncClientGDrive
from woogenerator.sync_client_prod import ProdSyncClient_WC
from woogenerator.sync_client_user import UsrSyncClient_WP
from woogenerator.coldata import ColData_User, ColData_Woo
from woogenerator.parsing.user import ImportUser
from woogenerator.utils import Registrar, TimeUtils


class abstractSyncClientTestCase(TestCase):
    # yaml_path = "generator_config.yaml"
    yaml_path = os.path.join(tests_datadir, 'generator_config_test.yaml')
    optionNamePrefix = 'test_'
    # optionNamePrefix = ''

    def processConfig(self, config): raise NotImplementedError()

    def setUp(self):
        self.import_name = TimeUtils.get_ms_timestamp()

        with open(self.yaml_path) as stream:
            config = yaml.load(stream)
            self.processConfig(config)

        # Registrar.DEBUG_PROGRESS = True
        # Registrar.DEBUG_MESSAGE = True
        # Registrar.DEBUG_ERROR = True
        # Registrar.DEBUG_WARN = True


@unittest.skip('have not created config file yet')
class testSyncClient(abstractSyncClientTestCase):
    # optionNamePrefix = 'dummy_'
    optionNamePrefix = ''

    def __init__(self, *args, **kwargs):
        super(testSyncClient, self).__init__(*args, **kwargs)
        self.gDriveParams = {}
        self.wcApiParams = {}
        self.productParserArgs = {}

        Registrar.DEBUG_API = True

    def processConfig(self, config):
        gdrive_scopes = config.get('gdrive_scopes')
        gdrive_client_secret_file = config.get('gdrive_client_secret_file')
        gdrive_app_name = config.get('gdrive_app_name')
        gdrive_oauth_clientID = config.get('gdrive_oauth_clientID')
        gdrive_oauth_clientSecret = config.get('gdrive_oauth_clientSecret')
        gdrive_credentials_dir = config.get('gdrive_credentials_dir')
        gdrive_credentials_file = config.get('gdrive_credentials_file')
        genFID = config.get('genFID')
        genGID = config.get('genGID')
        dprcGID = config.get('dprcGID')
        dprpGID = config.get('dprpGID')
        specGID = config.get('specGID')
        usGID = config.get('usGID')
        xsGID = config.get('xsGID')

        wc_api_key = config.get(self.optionNamePrefix + 'wc_api_key')
        wc_api_secret = config.get(self.optionNamePrefix + 'wc_api_secret')
        wp_api_key = config.get(self.optionNamePrefix + 'wp_api_key')
        wp_api_secret = config.get(self.optionNamePrefix + 'wp_api_secret')
        wp_user = config.get(self.optionNamePrefix + 'wp_user')
        wp_pass = config.get(self.optionNamePrefix + 'wp_pass')
        wp_callback = config.get(self.optionNamePrefix + 'wp_callback')

        # wp_srv_offset = config.get(self.optionNamePrefix+'wp_srv_offset', 0)
        store_url = config.get(self.optionNamePrefix + 'store_url', '')

        self.gDriveParams = {
            'scopes': gdrive_scopes,
            'client_secret_file': gdrive_client_secret_file,
            'app_name': gdrive_app_name,
            'oauth_clientID': gdrive_oauth_clientID,
            'oauth_clientSecret': gdrive_oauth_clientSecret,
            'credentials_dir': gdrive_credentials_dir,
            'credentials_file': gdrive_credentials_file,
            'genFID': genFID,
            'genGID': genGID,
            'dprcGID': dprcGID,
            'dprpGID': dprpGID,
            'specGID': specGID,
            'usGID': usGID,
            'xsGID': xsGID,
        }

        print "gDriveParams", self.gDriveParams

        self.wcApiParams = {
            'api_key': wc_api_key,
            'api_secret': wc_api_secret,
            'url': store_url,
            'limit': 6
            # 'version':'wc/v1'
        }

        print "wcApiParams", self.wcApiParams

        self.wpApiParams = {
            'api_key': wp_api_key,
            'api_secret': wp_api_secret,
            'wp_user': wp_user,
            'wp_pass': wp_pass,
            'url': store_url,
            'callback': wp_callback
        }

        print "wpApiParams", self.wpApiParams

        self.productParserArgs = {
            'self.import_name': self.import_name,
            # 'itemDepth': itemDepth,
            # 'taxoDepth': taxoDepth,
            'cols': ColData_Woo.get_import_cols(),
            'defaults': ColData_Woo.get_defaults(),
        }

        print "productParserArgs", self.productParserArgs

    def test_GDrive_Read(self):
        with SyncClientGDrive(self.gDriveParams) as client:
            print "drive file:", client.drive_file
            print "GID", client.get_gm_modtime(self.gDriveParams['genGID'])

    def test_ProdSyncClient_WC_Read(self):
        self.wcApiParams.update(timeout=1)
        with ProdSyncClient_WC(self.wcApiParams) as client:
            # print client.service.get('products').text
            for pagecount, page in enumerate(client.get_iterator('products')):
                print "PAGE %d: " % pagecount
                if 'products' in page:
                    for page_product in page.get('products'):
                        if 'id' in page_product:
                            prod_str = page_product['id']
                        else:
                            prod_str = str(page_product)[:100]
                        print "-> PRODUCT: ", prod_str

    @unittest.skip('out of scope')
    def test_UsrSyncClient_WP_Read(self):
        with UsrSyncClient_WP(self.wpApiParams) as client:
            print client.service.get('users').text
            for pagecount, page in enumerate(client.get_iterator('users')):
                print "PAGE %d: " % pagecount
                if 'users' in page:
                    for page_user in page.get('users'):
                        print "-> USER: ", str(page_user)[:50]


if __name__ == '__main__':
    unittest.main()
    # testSuite = unittest.TestSuite()
    # testSuite.addTest(testSyncClient('test_UsrSyncClient_WP_Read'))
    # testSuite.addTest(testSyncClient('test_ProdSyncClient_WC_Read'))
    # unittest.TextTestRunner().run(testSuite)
