# import unittest
import unittest
# from tabulate import tabulate
from os import path, sys

from context import woogenerator
from test_sync_client import AbstractSyncClientTestCase
from test_syncupdate import TestSyncUpdateAbstract
from woogenerator.coldata import ColDataUser
from woogenerator.conf.namespace import SettingsNamespaceUser
from woogenerator.conf.parser import ArgumentParserUser
from woogenerator.contact_objects import SocialMediaFields
from woogenerator.matching import MatchList, UsernameMatcher
from woogenerator.parsing.user import CsvParseUser, CsvParseUserApi, ImportUser
from woogenerator.syncupdate import SyncUpdateUsr, SyncUpdateUsrApi
from woogenerator.utils import Registrar, SanitationUtils, TimeUtils

if __name__ == '__main__' and __package__ is None:
    sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))


class TestSyncUpdateUserAbstract(TestSyncUpdateAbstract):
    config_file = "merger_config_test.yaml"
    settings_namespace_class = SettingsNamespaceUser
    argument_parser_class = ArgumentParserUser

class TestSyncUpdateUser(TestSyncUpdateUserAbstract):
    def setUp(self):
        super(TestSyncUpdateUser, self).setUp()

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
                'Direct Brand': 'TechnoTan Wholesale',
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
                'Direct Brand': 'TechnoTan Retail',
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
                'Direct Brand': 'TechnoTan Wholesale',
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
                'Phone': '0422 781 880',
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
                'Phone': "0468300749",
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
        master_object = self.user_mn1
        self.assertEqual(
            str(master_object.name), 'Derwent Smith'
        )
        slave_object = self.usr_sn1
        self.assertEqual(
            str(slave_object.name), 'Abe Jackson'
        )
        sync_update = SyncUpdateUsr(master_object, slave_object)
        sync_update.update(ColDataUser.get_sync_cols())
        self.assertFalse(
            sync_update.values_similar(
                'Name', master_object.name, slave_object.name
            )
        )
        self.assertGreater(sync_update.s_time, sync_update.m_time)
        self.assertGreater(
            sync_update.get_m_col_mod_time('Name'),
            sync_update.get_s_col_mod_time('Name')
        )
        self.assertIn('Name', sync_update.sync_warnings)
        name_sync_params = sync_update.sync_warnings.get('Name')[0]

        try:
            self.assertEqual(
                str(name_sync_params.get('new_value')), 'Derwent Smith'
            )
            self.assertEqual(
                str(name_sync_params.get('old_value')), 'Abe Jackson'
            )
            self.assertEqual(
                name_sync_params.get('subject'),
                sync_update.slave_name
            )
        except AssertionError as exc:
            self.fail_syncupdate_assertion(exc, sync_update)

    def test_s_name_col_update(self):
        master_object = self.user_mn2
        self.assertEqual(
            str(master_object.name), 'Derwent Smith'
        )
        slave_object = self.usr_sn2
        self.assertEqual(
            str(slave_object.name), 'Abe Jackson'
        )
        sync_update = SyncUpdateUsr(master_object, slave_object)
        sync_update.update(ColDataUser.get_sync_cols())
        self.assertGreater(sync_update.m_time, sync_update.s_time)
        self.assertGreater(
            sync_update.get_s_col_mod_time('Name'),
            sync_update.get_m_col_mod_time('Name')
        )
        self.assertIn('Name', sync_update.sync_warnings)
        name_sync_params = sync_update.sync_warnings.get('Name')[0]

        try:
            self.assertEqual(
                str(name_sync_params.get('new_value')), 'Abe Jackson'
            )
            self.assertEqual(
                str(name_sync_params.get('old_value')), 'Derwent Smith'
            )
            self.assertEqual(
                name_sync_params.get('subject'), sync_update.master_name
            )
        except AssertionError as exc:
            self.fail_syncupdate_assertion(exc, sync_update)

    def test_m_deltas(self):
        master_object = self.usr_md1
        self.assertEqual(
            master_object.role.role, 'WN'
        )
        slave_object = self.usr_sd1
        self.assertEqual(
            slave_object.role.role, 'RN'
        )
        sync_update = SyncUpdateUsr(master_object, slave_object)
        sync_update.update(ColDataUser.get_sync_cols())
        # sync_update.m_deltas(ColDataUser.get_delta_cols())
        try:
            self.assertGreater(sync_update.s_time, sync_update.m_time)
            self.assertFalse(sync_update.s_deltas)
            self.assertTrue(sync_update.m_deltas)
            master_updates = sync_update.get_master_updates()
            self.assertIn('Role', master_updates)
            self.assertEqual(master_updates['Role'], 'RN')
            self.assertEqual(
                sync_update.new_m_object.get(ColDataUser.delta_col('Role Info')).role,
                'WN'
            )
        except AssertionError as exc:
            self.fail_syncupdate_assertion(exc, sync_update)

    def test_s_deltas(self):
        master_object = self.usr_md2
        slave_object = self.usr_sd2
        self.assertEqual(master_object.role.role, 'RN')
        self.assertEqual(slave_object.role.role, 'WN')

        # Registrar.DEBUG_MESSAGE = True
        # Registrar.DEBUG_UPDATE = True

        sync_update = SyncUpdateUsr(master_object, slave_object)
        sync_update.update(ColDataUser.get_sync_cols())

        # sync_update.s_deltas(ColDataUser.get_delta_cols())
        try:
            self.assertGreater(sync_update.m_time, sync_update.s_time)
            slave_updates = sync_update.get_slave_updates()
            self.assertIn('Role', slave_updates)
            self.assertEqual(slave_updates['Role'], 'RN')
            self.assertFalse(sync_update.m_deltas)
            self.assertTrue(sync_update.s_deltas)
            self.assertEqual(sync_update.new_s_object.get('Role'), 'RN')
            self.assertEqual(
                sync_update.new_s_object.get(ColDataUser.delta_col('Role Info')).role,
                'WN'
            )
        except AssertionError as exc:
            self.fail_syncupdate_assertion(exc, sync_update)

        master_object = self.usr_md2a
        self.assertEqual(
            master_object.role.role, 'WN'
        )
        slave_object = self.usr_sd2a
        self.assertEqual(
            slave_object.role.role, 'RN'
        )
        sync_update = SyncUpdateUsr(master_object, slave_object)
        sync_update.update(ColDataUser.get_sync_cols())
        try:
            # sync_update.s_deltas(ColDataUser.get_delta_cols())
            self.assertGreater(sync_update.m_time, sync_update.s_time)
            slave_updates = sync_update.get_slave_updates()
            self.assertIn('Role', slave_updates)
            self.assertEqual(slave_updates['Role'], 'WN')

            self.assertFalse(sync_update.m_deltas)
            self.assertTrue(sync_update.s_deltas)
            self.assertEqual(sync_update.new_s_object.get('Role'), 'WN')
            self.assertEqual(
                sync_update.new_s_object.get(ColDataUser.delta_col('Role Info')).role,
                'RN'
            )
        except AssertionError as exc:
            self.fail_syncupdate_assertion(exc, sync_update)

    @unittest.skip("no longer deletes slave roles since master will always reflect")
    def test_m_deltas_b(self):
        master_object = self.usr_md3
        slave_object = self.usr_sd2
        self.assertEqual(master_object.role.role, None)
        self.assertEqual(slave_object.role.role, 'WN')
        self.assertEqual(
            type(master_object['Social Media']),
            SocialMediaFields
        )
        sync_update = SyncUpdateUsr(master_object, slave_object)
        sync_update.update(ColDataUser.get_sync_cols())
        # sync_update.s_deltas(ColDataUser.get_delta_cols())
        try:
            self.assertGreater(sync_update.m_time, sync_update.s_time)
            slave_updates = sync_update.get_slave_updates()
            self.assertIn('Role', slave_updates)
            self.assertEqual(slave_updates['Role'], None)
            self.assertFalse(sync_update.m_deltas)
            self.assertTrue(sync_update.s_deltas)
            # self.assertFalse(sync_update.new_m_object) # no longer true with reflection
            self.assertEqual(sync_update.new_s_object.role.role, '')
        except AssertionError as exc:
            self.fail_syncupdate_assertion(exc, sync_update)

    def test_s_deltas_b(self):
        master_object = self.usr_md1
        slave_object = self.usr_sd3
        self.assertEqual(master_object.role.role, 'WN')
        self.assertEqual(master_object.role.direct_brand, 'TechnoTan Wholesale')
        self.assertEqual(slave_object.role.role, None)
        self.assertEqual(slave_object.role.direct_brand, None)
        sync_update = SyncUpdateUsr(master_object, slave_object)
        sync_update.update(ColDataUser.get_sync_cols())
        # sync_update.s_deltas(ColDataUser.get_delta_cols())
        try:
            self.assertGreater(sync_update.s_time, sync_update.m_time)
            # Registrar.DEBUG_TRACE = True
            master_updates = sync_update.get_master_updates()

            self.assertIn('Role', master_updates)
            self.assertEqual(master_updates['Role'], 'RN')
            self.assertEqual(
                sync_update.new_m_object.get(ColDataUser.delta_col('Role Info')).role,
                'WN'
            )
            self.assertEqual(
                sync_update.new_m_object.role.role, 'RN'
            )
            # slave_updates = sync_update.get_slave_updates()
            # self.assertIn('Role', slave_updates)
            # self.assertEqual(slave_updates['Role'], 'RN')
            # self.assertEqual(
            #     sync_update.new_s_object.get(ColDataUser.delta_col('Role Info')).role,
            #     ''
            # )
            # self.assertEqual(
            #     sync_update.new_s_object.role.role, 'RN'
            # )
            self.assertTrue(sync_update.m_deltas)
            self.assertFalse(sync_update.s_deltas)

        except AssertionError as exc:
            self.fail_syncupdate_assertion(exc, sync_update)

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
            self.fail_syncupdate_assertion(exc, sync_update)

    def test_similar_phone(self):
        sync_update = SyncUpdateUsr(self.usr_md4, self.usr_sd4)
        sync_update.update(ColDataUser.get_sync_cols())

        try:
            self.assertNotIn('Phone', sync_update.sync_passes)
        except AssertionError as exc:
            self.fail_syncupdate_assertion(exc, sync_update)

    def test_parse_time(self):
        parsed_m_time = SyncUpdateUsr.parse_m_time("8/11/2016 1:38:51 PM")
        # print("parsed_m_time: %s" % pformat(parsed_m_time))
        self.assertEqual(parsed_m_time, 1478572731)
        parsed_s_time = SyncUpdateUsr.parse_s_time("2017-04-14 02:13:09")
        # print("parsed_s_time: %s" % pformat(parsed_s_time))
        self.assertEqual(parsed_s_time, 1492099989)

class TestSyncUpdateUserInvincible(TestSyncUpdateUserAbstract):
    def test_sync_name_invincible(self):
        usr_m = ImportUser(
            {
                'E-mail': 'donnag04@hotmail.com',
                'First Name': u'DONNA',
                'Surname': u'MOORE',
                'Edited Name': '27/08/2015 11:18:00 AM',
                'Edited Phone Numbers': '29/06/2016 11:48:14 AM',
                'Edited in Act': '15/08/2016 5:33:41 PM',
                'Edited in Wordpress': u'False',
                'MYOB Card ID': 'C000598',
                '_row': []
            },
            rowcount=2,
            row=[],
        )

        usr_s = ImportUser(
            {
                'Contact': u'Donna Moore',
                'E-mail': u'donnag04@hotmail.com',
                'Edited Name': u'2015-11-08 17:35:12',
                'Edited Phone Numbers': u'2015-11-08 17:35:12',
                'Edited in Wordpress': u'2016-11-08 17:35:12',
                'First Name': u'Donna',
                'Surname': u'Moore',
                'Wordpress ID': u'16458',
                'Wordpress Username': 'donnag04@hotmail.com',
                '_row': []
            },
            rowcount=2,
            row=[],
        )

        sync_update = SyncUpdateUsrApi(usr_m, usr_s)
        sync_update.update(ColDataUser.get_sync_cols())

        self.assertGreater(sync_update.s_time, sync_update.m_time)

class TestSyncUpdateUserApi(TestSyncUpdateUserAbstract):
    def test_sync_phone(self):
        usr_m = ImportUser(
            {
                'E-mail': 'donnag04@hotmail.com',
                'Contact': u'DONNA MOORE',
                'Edited Name': '27/08/2015 11:18:00 AM',
                'Edited Phone Numbers': '29/06/2016 11:48:14 AM',
                'Edited in Act': '15/08/2017 5:33:41 PM',
                'Edited in Wordpress': u'False',
                'MYOB Card ID': 'C000598',
                'Mobile Phone': u'0414298163',
                'First Name': u'DONNA',
                'Phone': u'0410695383',
                'Surname': u'MOORE',
                'Role': 'WN',
                'Wordpress Username': 'donnag04@hotmail.com',
                '_row': []
            },
            rowcount=2,
            row=[],
        )

        usr_s = ImportUser(
            {
                'Contact': u'Donna Moore',
                'E-mail': u'donnag04@hotmail.com',
                'Edited Name': u'2015-11-08 17:35:12',
                'Edited Phone Numbers': u'2015-11-08 17:35:12',
                'Edited in Wordpress': u'2015-11-08 17:35:12',
                'MYOB Card ID': u'C000598',
                'First Name': u'Donna',
                'Surname': u'Moore',
                'Role': 'WN',
                'Wordpress ID': u'16458',
                'Wordpress Username': 'donnag04@hotmail.com',
                '_row': []
            },
            rowcount=2,
            row=[],
        )

        sync_update = SyncUpdateUsrApi(usr_m, usr_s)
        sync_update.update(ColDataUser.get_sync_cols())
        # print sync_update.tabulate()

        self.assertEqual(sync_update.new_s_object.phones.mob_number, '0414298163')
        self.assertEqual(sync_update.new_s_object.phones.tel_number, '0410695383')

        # Registrar.DEBUG_TRACE = True
        # Registrar.DEBUG_UPDATE = True
        # Registrar.DEBUG_MESSAGE = True
        slave_updates_native = sync_update.get_slave_updates_native()
        slave_meta_updates = slave_updates_native.get('meta', {})
        self.assertEqual(slave_meta_updates.get('mobile_number'), '0414298163')
        self.assertEqual(slave_meta_updates.get('billing_phone'), '0410695383')

    def test_sync_email_native(self):
        usr_m = ImportUser(
            {
                'Contact': u'DONNA MOORE',
                'Edited Name': '27/08/2015 11:18:00 AM',
                'Edited E-Mail': '27/08/2017 11:18:00 AM',
                'Edited Phone Numbers': '29/06/2016 11:48:14 AM',
                'Edited in Act': '15/08/2017 5:33:41 PM',
                'Edited in Wordpress': u'False',
                'MYOB Card ID': 'C000598',
                'Mobile Phone': u'0414298163',
                'First Name': u'DONNA',
                'Phone': u'0410695383',
                'Surname': u'MOORE',
                'Role': 'WN',
                'Wordpress Username': 'donnag04@hotmail.com',
                '_row': []
            },
            rowcount=2,
            row=[],
        )

        usr_s = ImportUser(
            {
                'Contact': u'Donna Moore',
                'E-mail': u'donnag04@hotmail.com',
                'Edited Name': u'2015-11-08 17:35:12',
                'Edited E-Mail': u'2015-11-08 17:35:12',
                'Edited Phone Numbers': u'2015-11-08 17:35:12',
                'Edited in Wordpress': u'2015-11-08 17:35:12',
                'MYOB Card ID': u'C000598',
                'First Name': u'Donna',
                'Surname': u'Moore',
                'Role': 'WN',
                'Wordpress ID': u'16458',
                'Wordpress Username': 'donnag04@hotmail.com',
                '_row': []
            },
            rowcount=2,
            row=[],
        )

        sync_update = SyncUpdateUsrApi(usr_m, usr_s)
        sync_update.update(ColDataUser.get_sync_cols())

        self.assertEqual(sync_update.new_s_object.email, '')

        native_updates = sync_update.get_slave_updates_native()

        self.assertFalse('email' in native_updates)

        # from pprint import pprint
        # pprint(native_updates)


if __name__ == '__main__':
    unittest.main()
    # doubleNameTestSuite = unittest.TestSuite()
    # doubleNameTestSuite.addTest(TestSyncUpdateUser('test_m_name_col_update'))
    # unittest.TextTestRunner().run(doubleNameTestSuite)
    # result = unittest.TestResult()
    # result = doubleNameTestSuite.run(result)
    # print repr(result)


if __name__ == '__main__':
    unittest.main()
