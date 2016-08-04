from os import sys, path
import unittest
from unittest import TestCase, main, skip

if __name__ == '__main__' and __package__ is None:
    sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

from source.sync_client import *
from source.coldata import ColData_User
from source.csvparse_flat import ImportUser

class testSyncClient(TestCase):
    def setUp(self):
        os.chdir('source')

        yamlPath = "generator_config.yaml"

        importName = TimeUtils.getMsTimeStamp()

        with open(yamlPath) as stream:
            config = yaml.load(stream)

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


    def test_GDrive_Read(self):
        with SyncClient_GDrive(self.gDriveParams) as client:
            print client.drive_file
            print client.get_gm_modtime(self.gDriveParams['genGID'])



if __name__ == '__main__':
    # main()
    testSuite = unittest.TestSuite()
    testSuite.addTest(testSyncClient('test_GDrive_Read'))
    unittest.TextTestRunner().run(testSuite)
