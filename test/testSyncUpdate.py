from os import sys, path
if __name__ == '__main__' and __package__ is None:
    sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

from unittest import TestCase, main, skip
from source.SyncUpdate import *
from source.coldata import ColData_User
from source.csvparse_flat import ImportUser

class testSyncUpdate(TestCase):
    def setUp(self):
        yamlPath = "source/merger_config.yaml"

        with open(yamlPath) as stream:
            config = yaml.load(stream)
            merge_mode = config.get('merge_mode', 'sync')
            MASTER_NAME = config.get('master_name', 'MASTER')
            SLAVE_NAME = config.get('slave_name', 'SLAVE')
            DEFAULT_LAST_SYNC = config.get('default_last_sync')

        SyncUpdate.setGlobals( MASTER_NAME, SLAVE_NAME, merge_mode, DEFAULT_LAST_SYNC)

        self.usrMN1 = ImportUser(
            {
                'MYOB Card ID': 'C00002',
                'Wordpress ID': 7,
                'Wordpress Username': 'derewnt',
                'First Name': 'Derwent',
                'Surname': 'Smith',
                'Edited Name': '10/11/2015 12:55:00 PM',
                'Edited in Act': '11/11/2015 6:45:00 AM',
            },
            1,
            [],
        )

        self.usrSN1 = ImportUser(
            {
                'MYOB Card ID': 'C00002',
                'Wordpress ID': 7,
                'Wordpress Username': 'derewnt',
                'First Name': 'Abe',
                'Surname': 'Jackson',
                'Edited Name': '2015-11-10 12:45:03',
                'Edited in Wordpress': '2015-11-11 6:55:00',
            },
            2,
            [],
        )

        self.usrMN2 = ImportUser(
            {
                'MYOB Card ID': 'C00002',
                'Wordpress ID': 7,
                'Wordpress Username': 'derewnt',
                'First Name': 'Derwent',
                'Surname': 'Smith',
                'Edited Name': '10/11/2015 12:45:00 PM',
                'Edited in Act': '11/11/2015 6:55:00 AM',
            },
            1,
            [],
        )

        self.usrSN2 = ImportUser(
            {
                'MYOB Card ID': 'C00002',
                'Wordpress ID': 7,
                'Wordpress Username': 'derewnt',
                'First Name': 'Abe',
                'Surname': 'Jackson',
                'Edited Name': '2015-11-10 12:55:03',
                'Edited in Wordpress': '2015-11-11 6:45:00',
            },
            2,
            [],
        )

        # self.usrMD1 = ImportUser(
        #
        # )

    def test_mNameColUpdate(self):
        syncUpdate = SyncUpdate(self.usrMN1, self.usrSN1)
        syncUpdate.update(ColData_User.getSyncCols())
        self.assertGreater(syncUpdate.sTime, syncUpdate.mTime)
        self.assertEqual(syncUpdate.syncWarnings.get('Name')[0].get('subject'), syncUpdate.master_name)

    def test_sNameColUpdate(self):
        syncUpdate = SyncUpdate(self.usrMN2, self.usrSN2)
        syncUpdate.update(ColData_User.getSyncCols())
        self.assertGreater(syncUpdate.mTime, syncUpdate.sTime)
        self.assertEqual(syncUpdate.syncWarnings.get('Name')[0].get('subject'), syncUpdate.slave_name)

    def test_mDeltaCols(self):




if __name__ == '__main__':
    main()
