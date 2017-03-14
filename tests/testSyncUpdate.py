import os
from os import sys, path
from unittest import TestCase, main, skip
import unittest
import StringIO
import yaml

from context import woogenerator
from woogenerator import SyncUpdate
from woogenerator import coldata
from woogenerator.coldata import ColData_User
from woogenerator.csvparse_flat import ImportUser, CSVParse_User
from woogenerator.contact_objects import FieldGroup


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

        # FieldGroup.performPost = True
        FieldGroup.DEBUG_WARN = True
        FieldGroup.DEBUG_MESSAGE = True
        FieldGroup.DEBUG_ERROR = True
        SyncUpdate.DEBUG_WARN = True
        SyncUpdate.DEBUG_MESSAGE = True
        SyncUpdate.DEBUG_ERROR = True

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

        self.usrMD1 = ImportUser(
            {
                'MYOB Card ID': 'C00002',
                'Role': 'WN',
                'Wordpress ID': 7,
                'Wordpress Username': 'derewnt',
                'First Name': 'Abe',
                'Edited in Act': '11/11/2015 6:45:00 AM',
            },
            2,
            [],
        )

        self.usrSD1 = ImportUser(
            {
                'MYOB Card ID': 'C00002',
                'Role': 'RN',
                'Wordpress ID': 7,
                'Wordpress Username': 'derewnt',
                'First Name': 'Abe',
                'Edited in Wordpress': '2015-11-11 6:55:00',
            },
            2,
            [],
        )

        self.usrMD2 = ImportUser(
            {
                'MYOB Card ID': 'C00002',
                'Role': 'RN',
                'Wordpress ID': 7,
                'Wordpress Username': 'derewnt',
                'First Name': 'Abe',
                'Edited in Act': '11/11/2015 6:55:00 AM',
            },
            2,
            [],
        )

        self.usrSD2 = ImportUser(
            {
                'MYOB Card ID': 'C00002',
                'Role': 'WN',
                'Wordpress ID': 7,
                'Wordpress Username': 'derewnt',
                'First Name': 'Abe',
                'Edited in Wordpress': '2015-11-11 6:45:00',
            },
            2,
            [],
        )

        self.usrMD2a = ImportUser(
            {
                'MYOB Card ID': 'C000128',
                'Role': 'WN',
                'Edited in Act': '31/03/2016 12:41:43 PM',
            },
            2,
            [],
        )

        self.usrSD2a = ImportUser(
            {
                'MYOB Card ID': 'C000128',
                'Role': 'RN',
                'Wordpress ID': '3684',
            },
            2,
            [],
        )

        self.usrMD3 = ImportUser(
            {
                'MYOB Card ID': 'C00002',
                'Role': '',
                'Wordpress ID': 7,
                'Wordpress Username': 'derewnt',
                'First Name': 'Abe',
                'Edited in Act': '11/11/2015 6:55:00 AM',
            },
            2,
            [],
        )

        self.usrSD3 = ImportUser(
            {
                'MYOB Card ID': 'C00002',
                'Role': '',
                'Wordpress ID': 7,
                'Wordpress Username': 'derewnt',
                'First Name': 'Abe',
                'Edited in Wordpress': '2015-11-11 6:55:00',
            },
            2,
            [],
        )

        self.usrMD4 = ImportUser(
            {
                'MYOB Card ID': 'C00001',
                'E-mail': 'neil@technotan.com.au',
                'Wordpress ID': 1,
                'Wordpress Username': 'neil',
                'Role': 'WN',
                'Edited Name': '18/02/2016 12:13:00 PM',
                'Web Site': 'www.technotan.com.au',
                'Contact': 'NEIL',
                'First Name': '',
                'Surname': 'NEIL',
                'Edited in Act': '16/05/2016 11:20:22 AM',
            },
            2,
            [],
        )

        self.usrSD4 = ImportUser(
            {
                'MYOB Card ID': 'C00001',
                'E-mail': 'neil@technotan.com.au',
                'Wordpress ID': 1,
                'Wordpress Username': 'neil',
                'Role': 'ADMIN',
                'Edited Name': '2016-05-05 19:15:27',
                'Web Site': 'http://www.technotan.com.au',
                'Contact': 'NEIL CUNLIFFE-WILLIAMS',
                'First Name': 'NEIL',
                'Surname': 'CUNLIFFE-WILLIAMS',
                'Edited in Wordpress': '2016-05-10 16:36:30',
            },
            2,
            [],
        )

        print "set up complete"

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

    def test_mDeltas(self):
        syncUpdate = SyncUpdate(self.usrMD1, self.usrSD1)
        syncUpdate.update(ColData_User.getSyncCols())
        # syncUpdate.mDeltas(ColData_User.getDeltaCols())
        self.assertGreater(syncUpdate.sTime, syncUpdate.mTime)
        self.assertFalse(syncUpdate.sDeltas)
        self.assertTrue(syncUpdate.mDeltas)
        self.assertEqual(syncUpdate.syncWarnings.get('Role')[0].get('subject'), syncUpdate.slave_name)
        self.assertEqual(syncUpdate.newMObject.get(ColData_User.deltaCol('Role')), 'WN')

    def test_sDeltas(self):
        syncUpdate = SyncUpdate(self.usrMD2, self.usrSD2)
        syncUpdate.update(ColData_User.getSyncCols())
        # syncUpdate.sDeltas(ColData_User.getDeltaCols())
        self.assertGreater(syncUpdate.mTime, syncUpdate.sTime)
        self.assertEqual(syncUpdate.syncWarnings.get('Role')[0].get('subject'), syncUpdate.master_name)
        self.assertFalse(syncUpdate.mDeltas)
        self.assertTrue(syncUpdate.sDeltas)
        self.assertEqual(syncUpdate.newSObject.get('Role'), 'RN')
        self.assertEqual(syncUpdate.newSObject.get(ColData_User.deltaCol('Role')), 'WN')

        syncUpdate = SyncUpdate(self.usrMD2a, self.usrSD2a)
        syncUpdate.update(ColData_User.getSyncCols())
        # syncUpdate.sDeltas(ColData_User.getDeltaCols())
        self.assertGreater(syncUpdate.mTime, syncUpdate.sTime)
        self.assertEqual(syncUpdate.syncWarnings.get('Role')[0].get('subject'), syncUpdate.master_name)
        self.assertFalse(syncUpdate.mDeltas)
        self.assertTrue(syncUpdate.sDeltas)
        self.assertEqual(syncUpdate.newSObject.get('Role'), 'WN')
        self.assertEqual(syncUpdate.newSObject.get(ColData_User.deltaCol('Role')), 'RN')

    def test_mDeltasB(self):
        syncUpdate = SyncUpdate(self.usrMD3, self.usrSD2)
        syncUpdate.update(ColData_User.getSyncCols())
        # syncUpdate.sDeltas(ColData_User.getDeltaCols())
        self.assertGreater(syncUpdate.mTime, syncUpdate.sTime)
        self.assertEqual(syncUpdate.syncWarnings.get('Role')[0].get('subject'), syncUpdate.slave_name)
        self.assertFalse(syncUpdate.sDeltas)
        self.assertFalse(syncUpdate.mDeltas)
        self.assertEqual(syncUpdate.newMObject.get('Role'), 'WN')
        self.assertEqual(syncUpdate.newMObject.get(ColData_User.deltaCol('Role')), '')

    def test_sDeltasB(self):
        syncUpdate = SyncUpdate(self.usrMD1, self.usrSD3)
        syncUpdate.update(ColData_User.getSyncCols())
        # syncUpdate.sDeltas(ColData_User.getDeltaCols())
        self.assertGreater(syncUpdate.sTime, syncUpdate.mTime)
        self.assertEqual(syncUpdate.syncWarnings.get('Role')[0].get('subject'), syncUpdate.master_name)
        self.assertFalse(syncUpdate.mDeltas)
        self.assertFalse(syncUpdate.sDeltas)
        self.assertEqual(syncUpdate.newSObject.get('Role'), 'WN')
        self.assertEqual(syncUpdate.newSObject.get(ColData_User.deltaCol('Role')), '')

    def test_doubleNames(self):
        syncUpdate = SyncUpdate(self.usrMD4, self.usrSD4)
        syncUpdate.update(ColData_User.getSyncCols())
        print "master old: ", syncUpdate.oldMObject['Name'], '|', syncUpdate.oldMObject['Contact']
        print "master new: ", syncUpdate.newMObject['Name'], '|', syncUpdate.newMObject['Contact']
        print "slave old:  ", syncUpdate.oldSObject['Name'], '|', syncUpdate.oldSObject['Contact']
        print "slave new:  ", syncUpdate.newSObject['Name'], '|', syncUpdate.newSObject['Contact']
        print syncUpdate.tabulate(tablefmt='simple')

    def test_doubleNames2(self):

        inFolder = "input/"

        master_file = "act_test_dual_names.csv"
        slave_file = "wp_test_dual_names.csv"
        maPath = os.path.join(inFolder, master_file)
        saPath = os.path.join(inFolder, slave_file)

        saParser = CSVParse_User(
            cols = ColData_User.getWPImportCols(),
            defaults = ColData_User.getDefaults(),
        )

        saParser.analyseFile(saPath)

        sUsr = saParser.emails['neil@technotan.com.au'][0]

        maParser = CSVParse_User(
            cols = ColData_User.getACTImportCols(),
            defaults = ColData_User.getDefaults(),
        )

        maParser.analyseFile(maPath)

        mUsr = maParser.emails['neil@technotan.com.au'][0]

        syncUpdate = SyncUpdate(mUsr, sUsr)
        syncUpdate.update(ColData_User.getSyncCols())
        print "master old: ", syncUpdate.oldMObject['Name'], '|', syncUpdate.oldMObject['Contact']
        print "master new: ", syncUpdate.newMObject['Name'], '|', syncUpdate.newMObject['Contact']
        print "slave old:  ", syncUpdate.oldSObject['Name'], '|', syncUpdate.oldSObject['Contact']
        print "slave new:  ", syncUpdate.newSObject['Name'], '|', syncUpdate.newSObject['Contact']
        print syncUpdate.tabulate(tablefmt='simple')
        print syncUpdate.getMasterUpdates()

    def test_similarURL(self):
        syncUpdate = SyncUpdate(self.usrMD4, self.usrSD4)
        syncUpdate.update(ColData_User.getSyncCols())
        # print "master old: ", syncUpdate.oldMObject['Name'], '|', syncUpdate.oldMObject['Web Site']
        # print "master new: ", syncUpdate.newMObject['Name'], '|', syncUpdate.newMObject['Web Site']
        # print "slave old:  ", syncUpdate.oldSObject['Name'], '|', syncUpdate.oldSObject['Web Site']
        # print "slave new:  ", syncUpdate.newSObject['Name'], '|', syncUpdate.newSObject['Web Site']

        self.assertIn('Web Site', syncUpdate.syncPasses)
        # print syncUpdate.tabulate(tablefmt='simple')




if __name__ == '__main__':
    # main()
    doubleNameTestSuite = unittest.TestSuite()
    doubleNameTestSuite.addTest(testSyncUpdate('test_doubleNames2'))
    unittest.TextTestRunner().run(doubleNameTestSuite)
    # result = unittest.TestResult()
    # result = doubleNameTestSuite.run(result)
    # print repr(result)
