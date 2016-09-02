from os import sys, path
import unittest
from unittest import TestCase, main, skip

if __name__ == '__main__' and __package__ is None:
    sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

from source.sync_client import *
from source.sync_client_prod import *
from source.coldata import ColData_User, ColData_Woo
from source.csvparse_flat import ImportUser

class testSyncClient(TestCase):
    def setUp(self):
        try:
            os.stat('source')
            os.chdir('source')
        except:
            pass

        yamlPath = "generator_config.yaml"

        importName = TimeUtils.getMsTimeStamp()

        with open(yamlPath) as stream:
            config = yaml.load(stream)
            optionNamePrefix = 'test_'
            optionNamePrefix = ''

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

            wc_api_key = config.get(optionNamePrefix+'wc_api_key')
            wc_api_secret = config.get(optionNamePrefix+'wc_api_secret')
            wp_srv_offset = config.get(optionNamePrefix+'wp_srv_offset', 0)
            store_url = config.get(optionNamePrefix+'store_url', '')

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

        self.wcApiParams = {
            'api_key':wc_api_key,
            'api_secret':wc_api_secret,
            'url':store_url,
            'version':'wc/v1'
        }

        self.productParserArgs = {
            'importName': importName,
            # 'itemDepth': itemDepth,
            # 'taxoDepth': taxoDepth,
            'cols': ColData_Woo.getImportCols(),
            'defaults': ColData_Woo.getDefaults(),
        }

    def test_GDrive_Read(self):
        with SyncClient_GDrive(self.gDriveParams) as client:
            print client.drive_file
            print client.get_gm_modtime(self.gDriveParams['genGID'])

    def test_WC_API_Read(self):
        with ProdSyncClient_WC(self.wcApiParams) as api:
            for page in api.ApiIterator(api.client, 'products'):
                if 'products' in page:
                    for page_product in page.get('products'):
                        print page_product
                        break
                break




if __name__ == '__main__':
    # main()
    testSuite = unittest.TestSuite()
    testSuite.addTest(testSyncClient('test_WC_API_Read'))
    unittest.TextTestRunner().run(testSuite)
