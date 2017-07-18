import os
# from os import sys, path
from unittest import TestCase, main
import unittest
# import StringIO
import yaml
from context import woogenerator
from context import get_testdata, tests_datadir
from woogenerator import coldata
from woogenerator.syncupdate import SyncUpdateUsr
from woogenerator.utils import Registrar
from woogenerator.coldata import ColDataUser
from woogenerator.parsing.user import ImportUser, CsvParseUser
from woogenerator.contact_objects import FieldGroup


class testSyncUpdate_Usr(TestCase):

    def setUp(self):
        # yaml_path = "source/merger_config.yaml"
        yaml_path = os.path.join(tests_datadir, "generator_config_test.yaml")

        with open(yaml_path) as stream:
            config = yaml.load(stream)
            merge_mode = config.get('merge-mode', 'sync')
            master_name = config.get('master-name', 'MASTER')
            slave_name = config.get('slave-name', 'SLAVE')
            default_last_sync = config.get('default-last-sync')

        SyncUpdateUsr.set_globals(
            master_name, slave_name, merge_mode, default_last_sync)

        # FieldGroup.perform_post = True
        # FieldGroup.DEBUG_WARN = True
        # FieldGroup.DEBUG_MESSAGE = True
        # FieldGroup.DEBUG_ERROR = True
        # SyncUpdateUsr.DEBUG_WARN = True
        # SyncUpdateUsr.DEBUG_MESSAGE = True
        # SyncUpdateUsr.DEBUG_ERROR = True
        Registrar.DEBUG_WARN = False

        self.user_mn1 = ImportUser(
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

        self.usr_sn1 = ImportUser(
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

        self.user_mn2 = ImportUser(
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

        self.usr_sn2 = ImportUser(
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

        self.usr_md1 = ImportUser(
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

        self.usr_sd1 = ImportUser(
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

        self.usr_md2 = ImportUser(
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

        self.usr_sd2 = ImportUser(
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

        self.usr_md2a = ImportUser(
            {
                'MYOB Card ID': 'C000128',
                'Role': 'WN',
                'Edited in Act': '31/03/2016 12:41:43 PM',
                '_row': []
            },
            rowcount=2,
            row=[],
        )

        self.usr_sd2a = ImportUser(
            {
                'MYOB Card ID': 'C000128',
                'Role': 'RN',
                'Wordpress ID': '3684',
                '_row': []
            },
            rowcount=2,
            row=[],
        )

        self.usr_md3 = ImportUser(
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

        self.usr_sd3 = ImportUser(
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

        self.usr_md4 = ImportUser(
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

        self.usr_sd4 = ImportUser(
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

    def test_m_name_col_update(self):
        sync_update = SyncUpdateUsr(self.user_mn1, self.usr_sn1)
        sync_update.update(ColDataUser.get_sync_cols())
        self.assertGreater(sync_update.s_time, sync_update.m_time)
        self.assertGreater(
            sync_update.get_m_col_mod_time('Name'),
            sync_update.get_s_col_mod_time('Name')
        )
        try:
            self.assertIn('Name', sync_update.sync_warnings)
        except AssertionError as exc:
            raise AssertionError("failed assertion: %s\n%s\n%s" % (
                exc,
                sync_update.sync_warnings.items(),
                sync_update.tabulate(tablefmt='simple')
            ))
        self.assertEqual(
            sync_update.sync_warnings.get('Name')[0].get('subject'),
            sync_update.master_name
        )

    def test_s_name_col_update(self):
        sync_update = SyncUpdateUsr(self.user_mn2, self.usr_sn2)
        sync_update.update(ColDataUser.get_sync_cols())
        self.assertGreater(sync_update.m_time, sync_update.s_time)
        self.assertGreater(
            sync_update.get_s_col_mod_time('Name'),
            sync_update.get_m_col_mod_time('Name')
        )
        try:
            self.assertIn('Name', sync_update.sync_warnings)
        except AssertionError as exc:
            raise AssertionError("failed assertion: %s\n%s\n%s" % (
                exc,
                sync_update.sync_warnings.items(),
                sync_update.tabulate(tablefmt='simple')
            ))
        self.assertEqual(
            sync_update.sync_warnings.get('Name')[0].get('subject'),
            sync_update.slave_name
        )

    def test_m_deltas(self):
        sync_update = SyncUpdateUsr(self.usr_md1, self.usr_sd1)
        sync_update.update(ColDataUser.get_sync_cols())
        # sync_update.m_deltas(ColDataUser.get_delta_cols())
        self.assertGreater(sync_update.s_time, sync_update.m_time)
        self.assertFalse(sync_update.s_deltas)
        self.assertTrue(sync_update.m_deltas)
        self.assertIn('Role', sync_update.sync_warnings)
        self.assertEqual(
            sync_update.sync_warnings.get('Role')[0].get('subject'),
            sync_update.slave_name
        )
        self.assertEqual(sync_update.new_m_object.get(
            ColDataUser.delta_col('Role')), 'WN')

    def test_s_deltas(self):
        sync_update = SyncUpdateUsr(self.usr_md2, self.usr_sd2)
        sync_update.update(ColDataUser.get_sync_cols())
        # sync_update.s_deltas(ColDataUser.get_delta_cols())
        self.assertGreater(sync_update.m_time, sync_update.s_time)
        self.assertIn('Role', sync_update.sync_warnings)
        self.assertEqual(
            sync_update.sync_warnings.get('Role')[0].get('subject'),
            sync_update.master_name
        )
        self.assertFalse(sync_update.m_deltas)
        self.assertTrue(sync_update.s_deltas)
        self.assertEqual(sync_update.new_s_object.get('Role'), 'RN')
        self.assertEqual(sync_update.new_s_object.get(
            ColDataUser.delta_col('Role')), 'WN')

        sync_update = SyncUpdateUsr(self.usr_md2a, self.usr_sd2a)
        sync_update.update(ColDataUser.get_sync_cols())
        # sync_update.s_deltas(ColDataUser.get_delta_cols())
        self.assertGreater(sync_update.m_time, sync_update.s_time)
        self.assertIn('Role', sync_update.sync_warnings)
        self.assertEqual(
            sync_update.sync_warnings.get('Role')[0].get('subject'),
            sync_update.master_name
        )
        self.assertFalse(sync_update.m_deltas)
        self.assertTrue(sync_update.s_deltas)
        self.assertEqual(sync_update.new_s_object.get('Role'), 'WN')
        self.assertEqual(sync_update.new_s_object.get(
            ColDataUser.delta_col('Role')), 'RN')

    def test_m_deltas_b(self):
        sync_update = SyncUpdateUsr(self.usr_md3, self.usr_sd2)
        sync_update.update(ColDataUser.get_sync_cols())
        # sync_update.s_deltas(ColDataUser.get_delta_cols())
        self.assertGreater(sync_update.m_time, sync_update.s_time)
        try:
            self.assertIn('Role', sync_update.sync_warnings)
        except AssertionError as exc:
            raise AssertionError("failed assertion: %s\n%s\n%s" % (
                exc,
                sync_update.sync_warnings.items(),
                sync_update.tabulate(tablefmt='simple')
            ))
        self.assertEqual(
            sync_update.sync_warnings.get('Role')[0].get('subject'),
            sync_update.slave_name
        )
        self.assertFalse(sync_update.s_deltas)
        self.assertFalse(sync_update.m_deltas)
        self.assertEqual(sync_update.new_m_object.get('Role'), 'WN')
        self.assertEqual(sync_update.new_m_object.get(
            ColDataUser.delta_col('Role')), '')

    def test_s_deltas_b(self):
        sync_update = SyncUpdateUsr(self.usr_md1, self.usr_sd3)
        sync_update.update(ColDataUser.get_sync_cols())
        # sync_update.s_deltas(ColDataUser.get_delta_cols())
        self.assertGreater(sync_update.s_time, sync_update.m_time)
        try:
            self.assertIn('Role', sync_update.sync_warnings)
        except AssertionError as exc:
            raise AssertionError("failed assertion: %s\n%s\n%s" % (
                exc,
                sync_update.sync_passes.items(),
                sync_update.tabulate(tablefmt='simple')
            ))
        self.assertEqual(
            sync_update.sync_warnings.get('Role')[0].get('subject'),
            sync_update.master_name
        )
        self.assertFalse(sync_update.m_deltas)
        self.assertFalse(sync_update.s_deltas)
        self.assertEqual(sync_update.new_s_object.get('Role'), 'WN')
        self.assertEqual(sync_update.new_s_object.get(
            ColDataUser.delta_col('Role')), '')

    def test_similar_url(self):
        sync_update = SyncUpdateUsr(self.usr_md4, self.usr_sd4)
        sync_update.update(ColDataUser.get_sync_cols())

        try:
            self.assertIn('Web Site', sync_update.sync_passes)
        except AssertionError as exc:
            raise AssertionError("failed assertion: %s\n%s\n%s" % (
                exc,
                sync_update.sync_passes.items(),
                sync_update.tabulate(tablefmt='simple')
            ))


if __name__ == '__main__':
    main()
    # doubleNameTestSuite = unittest.TestSuite()
    # doubleNameTestSuite.addTest(testSyncUpdate_Usr('test_m_name_col_update'))
    # unittest.TextTestRunner().run(doubleNameTestSuite)
    # result = unittest.TestResult()
    # result = doubleNameTestSuite.run(result)
    # print repr(result)
