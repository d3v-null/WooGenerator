import os
import sys
# from os import sys, path
from unittest import TestCase, main
import unittest
from pprint import pformat
# import StringIO
import yaml
import pdb
import functools
import traceback

from context import woogenerator
from context import get_testdata, tests_datadir
from woogenerator import coldata
from woogenerator.syncupdate import SyncUpdateUsr
from woogenerator.utils import Registrar
from woogenerator.coldata import ColDataUser
from woogenerator.parsing.user import ImportUser, CsvParseUser
from woogenerator.contact_objects import FieldGroup, SocialMediaFields, FieldGroup

class TestSyncUpdateUser(TestCase):
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

        Registrar.DEBUG_ERROR = False
        Registrar.DEBUG_WARN = False
        Registrar.DEBUG_MESSAGE = False
        Registrar.DEBUG_PROGRESS = False

        # FieldGroup.perform_post = True
        # FieldGroup.DEBUG_WARN = True
        # FieldGroup.DEBUG_MESSAGE = True
        # FieldGroup.DEBUG_ERROR = True
        # SyncUpdateUsr.DEBUG_WARN = True
        # SyncUpdateUsr.DEBUG_MESSAGE = True
        # SyncUpdateUsr.DEBUG_ERROR = True
        # Registrar.DEBUG_ERROR = True
        # Registrar.DEBUG_WARN = True
        # Registrar.DEBUG_MESSAGE = True
        # Registrar.DEBUG_PROGRESS = True
        # Registrar.DEBUG_UPDATE = True
        # Registrar.DEBUG_USR = True
        # Registrar.DEBUG_CONTACT = True
        # Registrar.DEBUG_NAME = True
        # FieldGroup.DEBUG_CONTACT = True
        # FieldGroup.enforce_mandatory_keys = False

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

        if ImportUser.DEBUG_CONTACT:
            Registrar.register_message("creating user_md4")

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
        if ImportUser.DEBUG_CONTACT:
            Registrar.register_message("created usr_md4. socials: %s, socials.kwargs: %s" % (
                repr(self.usr_md4.socials),
                pformat(self.usr_md4.socials.kwargs.items())
            ))

        if ImportUser.DEBUG_CONTACT:
            Registrar.register_message("creating user_sd4")

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

        if ImportUser.DEBUG_CONTACT:
            Registrar.register_message("created usr_sd4. socials: %s" % repr(self.usr_sd4.socials))

    def test_m_name_col_update(self):
        self.assertEqual(
            str(self.user_mn1.name),
            "Derwent Smith"
        )
        self.assertEqual(
            str(self.usr_sn1.name),
            "Abe Jackson"
        )
        sync_update = SyncUpdateUsr(self.user_mn1, self.usr_sn1)
        sync_update.update(ColDataUser.get_sync_cols())
        self.assertTrue(self.user_mn1.name)
        self.assertTrue(self.usr_sn1.name)
        self.assertFalse(
            sync_update.values_similar(
                'Name',
                self.user_mn1.name,
                self.usr_sn1.name
            )
        )
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
        self.assertEqual(str(self.usr_md3.role), '')
        self.assertEqual(str(self.usr_sd2.role), 'WN')
        self.assertEqual(
            type(self.usr_md3['Social Media']),
            SocialMediaFields
        )
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
        role_sync_params = sync_update.sync_warnings.get('Role')[0]

        self.assertEqual(
            role_sync_params.get('subject'),
            sync_update.master_name
        )
        self.assertEqual(
            role_sync_params.get('reason'),
            'deleting'
        )
        self.assertTrue(sync_update.s_deltas)
        self.assertFalse(sync_update.m_deltas)
        self.assertFalse(sync_update.new_m_object)
        self.assertEqual(
            str(sync_update.new_s_object.role),
            ''
        )

    def test_s_deltas_b(self):
        self.assertEqual(str(self.usr_md1.role), 'WN')
        self.assertEqual(str(self.usr_sd3.role), '')
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
        role_sync_params = sync_update.sync_warnings.get('Role')[0]
        self.assertEqual(
            role_sync_params.get('subject'),
            sync_update.slave_name
        )
        self.assertEqual(
            role_sync_params.get('reason'),
            'deleting'
        )
        self.assertTrue(sync_update.m_deltas)
        self.assertFalse(sync_update.s_deltas)
        self.assertEqual(
            sync_update.new_m_object.get(ColDataUser.delta_col('Role')),
            'WN'
        )
        self.assertEqual(
            str(sync_update.new_m_object.role),
            ''
        )

    def test_similar_url(self):
        self.assertFalse(SocialMediaFields.mandatory_keys)
        self.assertFalse(self.usr_md4.socials.empty)
        self.assertEquals(self.usr_md4.socials.kwargs['website'], 'www.technotan.com.au')
        self.assertEqual(self.usr_md4.socials.website, 'www.technotan.com.au')
        self.assertEqual(self.usr_sd4.socials.website, 'http://www.technotan.com.au')
        self.assertEqual(self.usr_md4['Web Site'], 'www.technotan.com.au')
        self.assertEqual(self.usr_sd4['Web Site'], 'http://www.technotan.com.au')

        sync_update = SyncUpdateUsr(self.usr_md4, self.usr_sd4)
        sync_update.update(ColDataUser.get_sync_cols())

        try:
            self.assertIn('Web Site', sync_update.sync_passes)
        except AssertionError as exc:
            raise AssertionError("failed assertion: %s\n%s\n%s" % (
                exc,
                pformat(sync_update.sync_passes.items()),
                sync_update.tabulate(tablefmt='simple')
            ))

    def test_parse_time(self):
        parsed_m_time = SyncUpdateUsr.parse_m_time("8/11/2016 1:38:51 PM")
        # print("parsed_m_time: %s" % pformat(parsed_m_time))
        self.assertEqual(parsed_m_time, 1478572731)
        parsed_s_time = SyncUpdateUsr.parse_s_time("2017-04-14 02:13:09")
        # print("parsed_s_time: %s" % pformat(parsed_s_time))
        self.assertEqual(parsed_s_time, 1492099989)



if __name__ == '__main__':
    main()
    # doubleNameTestSuite = unittest.TestSuite()
    # doubleNameTestSuite.addTest(TestSyncUpdateUser('test_m_name_col_update'))
    # unittest.TextTestRunner().run(doubleNameTestSuite)
    # result = unittest.TestResult()
    # result = doubleNameTestSuite.run(result)
    # print repr(result)
