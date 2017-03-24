import os
from os import sys, path
from unittest import TestCase, main, skip
import unittest
import StringIO
import yaml

from context import woogenerator
from context import get_testdata, tests_datadir
from woogenerator.syncupdate import SyncUpdateUsr
from woogenerator import coldata
from woogenerator.coldata import ColDataUser
from woogenerator.parsing.user import ImportUser, CsvParseUser
from woogenerator.contact_objects import FieldGroup


class testSyncUpdate_Usr(TestCase):

    def setUp(self):
        # yaml_path = "source/merger_config.yaml"
        yaml_path = os.path.join(tests_datadir, "generator_config_test.yaml")

        with open(yaml_path) as stream:
            config = yaml.load(stream)
            merge_mode = config.get('merge_mode', 'sync')
            master_name = config.get('master_name', 'MASTER')
            slave_name = config.get('slave_name', 'SLAVE')
            default_last_sync = config.get('default_last_sync')

        SyncUpdateUsr.set_globals(
            master_name, slave_name, merge_mode, default_last_sync)

        # FieldGroup.performPost = True
        # FieldGroup.DEBUG_WARN = True
        # FieldGroup.DEBUG_MESSAGE = True
        # FieldGroup.DEBUG_ERROR = True
        # SyncUpdateUsr.DEBUG_WARN = True
        # SyncUpdateUsr.DEBUG_MESSAGE = True
        # SyncUpdateUsr.DEBUG_ERROR = True

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
            row=[],
            rowcount=1
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
                '_row': []
            },
            rowcount=2,
            row=[],
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
                '_row': []
            },
            rowcount=1,
            row=[],
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
                '_row': []
            },
            rowcount=2,
            row=[],
        )

        self.usrMD1 = ImportUser(
            {
                'MYOB Card ID': 'C00002',
                'Role': 'WN',
                'Wordpress ID': 7,
                'Wordpress Username': 'derewnt',
                'First Name': 'Abe',
                'Edited in Act': '11/11/2015 6:45:00 AM',
                '_row': []
            },
            rowcount=2,
            row=[],
        )

        self.usrSD1 = ImportUser(
            {
                'MYOB Card ID': 'C00002',
                'Role': 'RN',
                'Wordpress ID': 7,
                'Wordpress Username': 'derewnt',
                'First Name': 'Abe',
                'Edited in Wordpress': '2015-11-11 6:55:00',
                '_row': []
            },
            rowcount=2,
            row=[],
        )

        self.usrMD2 = ImportUser(
            {
                'MYOB Card ID': 'C00002',
                'Role': 'RN',
                'Wordpress ID': 7,
                'Wordpress Username': 'derewnt',
                'First Name': 'Abe',
                'Edited in Act': '11/11/2015 6:55:00 AM',
                '_row': []
            },
            rowcount=2,
            row=[],
        )

        self.usrSD2 = ImportUser(
            {
                'MYOB Card ID': 'C00002',
                'Role': 'WN',
                'Wordpress ID': 7,
                'Wordpress Username': 'derewnt',
                'First Name': 'Abe',
                'Edited in Wordpress': '2015-11-11 6:45:00',
                '_row': []
            },
            rowcount=2,
            row=[],
        )

        self.usrMD2a = ImportUser(
            {
                'MYOB Card ID': 'C000128',
                'Role': 'WN',
                'Edited in Act': '31/03/2016 12:41:43 PM',
                '_row': []
            },
            rowcount=2,
            row=[],
        )

        self.usrSD2a = ImportUser(
            {
                'MYOB Card ID': 'C000128',
                'Role': 'RN',
                'Wordpress ID': '3684',
                '_row': []
            },
            rowcount=2,
            row=[],
        )

        self.usrMD3 = ImportUser(
            {
                'MYOB Card ID': 'C00002',
                'Role': '',
                'Wordpress ID': 7,
                'Wordpress Username': 'derewnt',
                'First Name': 'Abe',
                'Edited in Act': '11/11/2015 6:55:00 AM',
                '_row': []
            },
            rowcount=2,
            row=[],
        )

        self.usrSD3 = ImportUser(
            {
                'MYOB Card ID': 'C00002',
                'Role': '',
                'Wordpress ID': 7,
                'Wordpress Username': 'derewnt',
                'First Name': 'Abe',
                'Edited in Wordpress': '2015-11-11 6:55:00',
                '_row': []
            },
            rowcount=2,
            row=[],
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
                '_row': []
            },
            rowcount=2,
            row=[],
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
                '_row': []
            },
            rowcount=2,
            row=[],
        )

        print "set up complete"

    def test_mNameColUpdate(self):
        syncUpdate = SyncUpdateUsr(self.usrMN1, self.usrSN1)
        syncUpdate.update(ColDataUser.get_sync_cols())
        self.assertGreater(syncUpdate.s_time, syncUpdate.m_time)
        self.assertEqual(syncUpdate.sync_warnings.get('Name')[
                         0].get('subject'), syncUpdate.master_name)

    def test_sNameColUpdate(self):
        syncUpdate = SyncUpdateUsr(self.usrMN2, self.usrSN2)
        syncUpdate.update(ColDataUser.get_sync_cols())
        self.assertGreater(syncUpdate.m_time, syncUpdate.s_time)
        self.assertEqual(syncUpdate.sync_warnings.get('Name')[
                         0].get('subject'), syncUpdate.slave_name)

    def test_mDeltas(self):
        syncUpdate = SyncUpdateUsr(self.usrMD1, self.usrSD1)
        syncUpdate.update(ColDataUser.get_sync_cols())
        # syncUpdate.m_deltas(ColDataUser.get_delta_cols())
        self.assertGreater(syncUpdate.s_time, syncUpdate.m_time)
        self.assertFalse(syncUpdate.s_deltas)
        self.assertTrue(syncUpdate.m_deltas)
        self.assertEqual(syncUpdate.sync_warnings.get('Role')[
                         0].get('subject'), syncUpdate.slave_name)
        self.assertEqual(syncUpdate.new_m_object.get(
            ColDataUser.delta_col('Role')), 'WN')

    def test_sDeltas(self):
        syncUpdate = SyncUpdateUsr(self.usrMD2, self.usrSD2)
        syncUpdate.update(ColDataUser.get_sync_cols())
        # syncUpdate.s_deltas(ColDataUser.get_delta_cols())
        self.assertGreater(syncUpdate.m_time, syncUpdate.s_time)
        self.assertEqual(syncUpdate.sync_warnings.get('Role')[
                         0].get('subject'), syncUpdate.master_name)
        self.assertFalse(syncUpdate.m_deltas)
        self.assertTrue(syncUpdate.s_deltas)
        self.assertEqual(syncUpdate.new_s_object.get('Role'), 'RN')
        self.assertEqual(syncUpdate.new_s_object.get(
            ColDataUser.delta_col('Role')), 'WN')

        syncUpdate = SyncUpdateUsr(self.usrMD2a, self.usrSD2a)
        syncUpdate.update(ColDataUser.get_sync_cols())
        # syncUpdate.s_deltas(ColDataUser.get_delta_cols())
        self.assertGreater(syncUpdate.m_time, syncUpdate.s_time)
        self.assertEqual(syncUpdate.sync_warnings.get('Role')[
                         0].get('subject'), syncUpdate.master_name)
        self.assertFalse(syncUpdate.m_deltas)
        self.assertTrue(syncUpdate.s_deltas)
        self.assertEqual(syncUpdate.new_s_object.get('Role'), 'WN')
        self.assertEqual(syncUpdate.new_s_object.get(
            ColDataUser.delta_col('Role')), 'RN')

    def test_mDeltasB(self):
        syncUpdate = SyncUpdateUsr(self.usrMD3, self.usrSD2)
        syncUpdate.update(ColDataUser.get_sync_cols())
        # syncUpdate.s_deltas(ColDataUser.get_delta_cols())
        self.assertGreater(syncUpdate.m_time, syncUpdate.s_time)
        self.assertEqual(syncUpdate.sync_warnings.get('Role')[
                         0].get('subject'), syncUpdate.slave_name)
        self.assertFalse(syncUpdate.s_deltas)
        self.assertFalse(syncUpdate.m_deltas)
        self.assertEqual(syncUpdate.new_m_object.get('Role'), 'WN')
        self.assertEqual(syncUpdate.new_m_object.get(
            ColDataUser.delta_col('Role')), '')

    def test_sDeltasB(self):
        syncUpdate = SyncUpdateUsr(self.usrMD1, self.usrSD3)
        syncUpdate.update(ColDataUser.get_sync_cols())
        # syncUpdate.s_deltas(ColDataUser.get_delta_cols())
        self.assertGreater(syncUpdate.s_time, syncUpdate.m_time)
        self.assertEqual(syncUpdate.sync_warnings.get('Role')[
                         0].get('subject'), syncUpdate.master_name)
        self.assertFalse(syncUpdate.m_deltas)
        self.assertFalse(syncUpdate.s_deltas)
        self.assertEqual(syncUpdate.new_s_object.get('Role'), 'WN')
        self.assertEqual(syncUpdate.new_s_object.get(
            ColDataUser.delta_col('Role')), '')

    def test_doubleNames(self):
        syncUpdate = SyncUpdateUsr(self.usrMD4, self.usrSD4)
        syncUpdate.update(ColDataUser.get_sync_cols())
        print "master old: ", syncUpdate.old_m_object['Name'], '|', syncUpdate.old_m_object['Contact']
        print "master new: ", syncUpdate.new_m_object['Name'], '|', syncUpdate.new_m_object['Contact']
        print "slave old:  ", syncUpdate.old_s_object['Name'], '|', syncUpdate.old_s_object['Contact']
        print "slave new:  ", syncUpdate.new_s_object['Name'], '|', syncUpdate.new_s_object['Contact']
        print syncUpdate.tabulate(tablefmt='simple')

    def test_doubleNames2(self):

        in_folder = "input/"

        master_file = "act_test_dual_names.csv"
        slave_file = "wp_test_dual_names.csv"
        maPath = os.path.join(in_folder, master_file)
        saPath = os.path.join(in_folder, slave_file)

        saParser = CsvParseUser(
            cols=ColDataUser.get_wp_import_cols(),
            defaults=ColDataUser.get_defaults(),
        )

        saParser.analyse_file(saPath)

        sUsr = saParser.emails['neil@technotan.com.au'][0]

        maParser = CsvParseUser(
            cols=ColDataUser.get_act_import_cols(),
            defaults=ColDataUser.get_defaults(),
        )

        maParser.analyse_file(maPath)

        mUsr = maParser.emails['neil@technotan.com.au'][0]

        syncUpdate = SyncUpdateUsr(mUsr, sUsr)
        syncUpdate.update(ColDataUser.get_sync_cols())
        print "master old: ", syncUpdate.old_m_object['Name'], '|', syncUpdate.old_m_object['Contact']
        print "master new: ", syncUpdate.new_m_object['Name'], '|', syncUpdate.new_m_object['Contact']
        print "slave old:  ", syncUpdate.old_s_object['Name'], '|', syncUpdate.old_s_object['Contact']
        print "slave new:  ", syncUpdate.new_s_object['Name'], '|', syncUpdate.new_s_object['Contact']
        print syncUpdate.tabulate(tablefmt='simple')
        print syncUpdate.get_master_updates()

    def test_similarURL(self):
        syncUpdate = SyncUpdateUsr(self.usrMD4, self.usrSD4)
        syncUpdate.update(ColDataUser.get_sync_cols())
        # print "master old: ", syncUpdate.old_m_object['Name'], '|', syncUpdate.old_m_object['Web Site']
        # print "master new: ", syncUpdate.new_m_object['Name'], '|', syncUpdate.new_m_object['Web Site']
        # print "slave old:  ", syncUpdate.old_s_object['Name'], '|', syncUpdate.old_s_object['Web Site']
        # print "slave new:  ", syncUpdate.new_s_object['Name'], '|',
        # syncUpdate.new_s_object['Web Site']

        self.assertIn('Web Site', syncUpdate.sync_passes)
        # print syncUpdate.tabulate(tablefmt='simple')


if __name__ == '__main__':
    main()
    # doubleNameTestSuite = unittest.TestSuite()
    # doubleNameTestSuite.addTest(testSyncUpdate_Usr('test_mNameColUpdate'))
    # unittest.TextTestRunner().run(doubleNameTestSuite)
    # result = unittest.TestResult()
    # result = doubleNameTestSuite.run(result)
    # print repr(result)
