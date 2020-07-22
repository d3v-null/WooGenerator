# from __future__ import print_function
#
# import os
# import tempfile
# import unittest
# from pprint import pformat
#
# import mock
# import pytest
#
# from context import TESTS_DATA_DIR, woogenerator
# from test_sync_manager import AbstractSyncManagerTestCase
# from utils import MockUtils
# from woogenerator.coldata import ColDataUser
# from woogenerator.contact_objects import FieldGroup
# from woogenerator.merger import (do_match, do_merge, do_report, do_report_post,
#                                  do_summary, do_updates,
#                                  populate_filter_settings,
#                                  populate_main_parsers,
#                                  populate_subordinate_parsers)
# from woogenerator.namespace.user import SettingsNamespaceUser
# from woogenerator.syncupdate import SyncUpdate
# from woogenerator.utils import TimeUtils, Registrar
#
# @pytest.mark.skip
# class TestMergerAbstract(AbstractSyncManagerTestCase):
#     """
#     Abstract utilities for testing merger.
#     """
#
#     settings_namespace_class = SettingsNamespaceUser
#     config_file = "merger_config_test.yaml"
#     data_dir = TESTS_DATA_DIR
#     main_file = "merger_main_dummy.csv"
#     subordinate_file = "merger_subordinate_dummy.csv"
#
#     def setUp(self):
#         super(TestMergerAbstract, self).setUp()
#         self.settings.main_dialect_suggestion = "ActOut"
#         self.settings.download_main = False
#         self.settings.download_subordinate = False
#         self.settings.main_file = os.path.join(self.data_dir, self.main_file)
#         self.settings.subordinate_file = os.path.join(self.data_dir, self.subordinate_file)
#         self.settings.testmode = True
#         self.settings.do_sync = True
#         self.settings.report_duplicates = True
#         self.settings.report_sanitation = True
#         self.settings.report_matching = True
#         self.settings.update_main = False
#         self.settings.update_subordinate = False
#         self.settings.ask_before_update = False
#         self.settings.init_settings(self.override_args)
#
#     def print_user_summary(self, user):
#         if user is None:
#             print(user)
#             return
#         print("pformat@dict:\n%s" % pformat(dict(user)))
#         # print("pformat@dir:\n%s" % pformat(dir(user)))
#         print("str@.act_modtime:\n%s" % str(user.act_modtime))
#         print("str@.act_created:\n%s" % str(user.act_created))
#         print("str@.wp_created:\n%s" % str(user.wp_created))
#         print("str@.wp_modtime:\n%s" % str(user.wp_modtime))
#         print("str@.last_sale:\n%s" % str(user.last_sale))
#         print("str@.last_modtime:\n%s" % str(user.last_modtime))
#         print("pformat@.name.to_dict:\n%s" % pformat(dict(user.name.to_dict())))
#         # print("pformat@.phones.to_dict:\n%s" % pformat(dict(user.phones.to_dict())))
#         # print(
#         #     "pformat@.shipping_address.valid:\n%s" %
#         #     pformat(user.shipping_address.valid)
#         # )
#         # print("pformat@.shipping_address.kwargs:\n%s" % \
#         #       pformat(user.shipping_address.kwargs))
#         # print("pformat@.shipping_address.to_dict:\n%s" % \
#         #       pformat(dict(user.shipping_address.to_dict())))
#         # print(".billing_address:\n%s" % user.billing_address)
#         # print("pformat@.billing_address.to_dict:\n%s" % \
#         #       pformat(dict(user.billing_address.to_dict())))
#         # print("pformat@.phones.to_dict:\n%s" % pformat(dict(user.phones.to_dict())))
#         print("pformat@.role.to_dict:\n%s" % pformat(dict(user.role.to_dict())))
#         # print("pformat@.socials.to_dict:\n%s" % pformat(dict(user.socials.to_dict())))
#         # print("pformat@.wpid:\n%s" % pformat(user.wpid))
#         # print("pformat@.email:\n%s" % pformat(user.email))
#         # print("pformat@.edited_email:%s" % pformat(first_usr['Edited E-mail']))
# @pytest.mark.skip
# class TestMergerSafe(TestMergerAbstract):
#     """
#     Safe tests for merger using randomized data
#     """
#     def test_init_settings(self):
#
#         self.assertEqual(self.settings.main_name, "ACT")
#         self.assertEqual(self.settings.subordinate_name, "WORDPRESS")
#         self.assertEqual(self.settings.download_main, False)
#         self.assertEqual(
#             self.settings.main_download_client_args["limit"],
#             self.settings.main_parse_limit
#         )
#         self.assertEqual(self.settings.main_download_client_args["dialect_suggestion"], "ActOut")
#         self.assertFalse(FieldGroup.do_post)
#         self.assertEqual(SyncUpdate.main_name, "ACT")
#         self.assertEqual(SyncUpdate.subordinate_name, "WORDPRESS")
#         self.assertEqual(self.settings.main_parser_args.get('schema'), None)
#         self.assertEqual(self.settings.subordinate_parser_args['schema'], "TT")
#
#     def test_populate_main_parsers(self):
#         self.settings.main_parse_limit = 4
#
#         populate_main_parsers(
#             self.parsers, self.settings
#         )
#
#         usr_list = self.parsers.main.get_obj_list()
#
#         self.assertEqual(self.parsers.main.schema, None)
#
#         #number of objects:
#         self.assertTrue(len(usr_list))
#         # print("len: %s" % len(usr_list))
#         # self.assertEqual(len(usr_list), 86)
#
#         #first user:
#         first_usr = usr_list[0]
#         # self.print_user_summary(first_usr)
#
#         self.assertEqual(first_usr.name.schema, None)
#         self.assertEqual(first_usr.name.first_name, 'Giacobo')
#         self.assertEqual(first_usr.name.family_name, 'Piolli')
#         self.assertEqual(first_usr.name.company, 'Linkbridge')
#         self.assertEqual(str(first_usr.name), 'Giacobo Piolli')
#         self.assertEqual(first_usr.shipping_address.city, 'Congkar')
#         self.assertEqual(first_usr.shipping_address.country, 'AU')
#         self.assertEqual(first_usr.shipping_address.postcode, '6054')
#         self.assertEqual(first_usr.shipping_address.state, 'VIC')
#         self.assertEqual(
#             str(first_usr.shipping_address),
#             '4552 Sunfield Circle; Congkar, VIC, 6054, AU'
#         )
#         self.assertEqual(first_usr.billing_address.city, 'Duwaktenggi')
#         self.assertEqual(first_usr.billing_address.country, 'AU')
#         self.assertEqual(first_usr.billing_address.postcode, '6011')
#         self.assertEqual(first_usr.billing_address.state, 'WA')
#         self.assertEqual(
#             str(first_usr.billing_address),
#             '91 Alpine Trail; Duwaktenggi, WA, 6011, AU'
#         )
#         self.assertEqual(first_usr.phones.mob_number, '+614 40 564 957')
#         self.assertEqual(first_usr.phones.tel_number, '02 2791 7625')
#         self.assertEqual(first_usr.phones.fax_number, '07 5971 6312')
#         self.assertEqual(first_usr.socials.twitter, "kmainstone5")
#         website = ("https://wikispaces.com/vivamus/metus/arcu/adipiscing.jpg?"
#                    "duis=justo" "&consequat=sollicitudin" "&dui=ut"
#                    "&nec=suscipit" "&nisi=a" "&volutpat=feugiat" "&eleifend=et"
#                    "&donec=eros" "&ut=vestibulum" "&dolor=ac" "&morbi=est"
#                    "&vel=lacinia" "&lectus=nisi" "&in=venenatis")
#         self.assertEqual(first_usr.socials.website, website)
#         self.assertEqual(first_usr['Web Site'], website)
#
#         if 'Role' in ColDataUser.data:
#             self.assertEqual(first_usr.role.role, "RN")
#             self.assertEqual(first_usr.role.direct_brand, "TechnoTan Wholesale")
#
#         # print(SanitationUtils.coerce_bytes(usr_list.tabulate(tablefmt='simple')))
#
#     @unittest.skipIf(
#         TimeUtils.get_system_timezone != '+1000',
#         'Tests calibrated for AEST'
#     )
#     def test_populate_main_parsers_time(self):
#         """check main time is parsed correctly (skip tests if not local)"""
#         self.settings.main_parse_limit = 4
#         populate_main_parsers(
#             self.parsers, self.settings
#         )
#         usr_list = self.parsers.main.get_obj_list()
#         self.assertTrue(len(usr_list))
#         first_usr = usr_list[0]
#
#         self.assertEqual(first_usr.act_modtime, 1284447467.0)
#         self.assertEqual(first_usr.act_created, 1303530357.0)
#         self.assertEqual(first_usr.wp_created, 1406544037.0)
#         self.assertEqual(first_usr.wp_modtime, None)
#         self.assertEqual(first_usr.last_sale, 1445691600.0)
#         self.assertEqual(first_usr.last_modtime, 1445691600.0)
#         self.assertEqual(first_usr.act_last_transaction, 1445691600.0)
#
#
#     def test_populate_subordinate_parsers(self):
#         populate_subordinate_parsers(
#             self.parsers, self.settings
#         )
#
#         self.assertEqual(self.parsers.subordinate.schema, 'TT')
#
#         usr_list = self.parsers.subordinate.get_obj_list()
#
#         self.assertEqual(len(usr_list), 101)
#
#         # print(SanitationUtils.coerce_bytes(obj_list.tabulate(tablefmt='simple')))
#
#         self.assertTrue(len(usr_list))
#
#         first_usr = usr_list[0]
#         if self.debug:
#             self.print_user_summary(first_usr)
#
#         self.assertEqual(first_usr.name.schema, 'TT')
#         self.assertEqual(first_usr.name.first_name, 'Gustav')
#         self.assertEqual(first_usr.name.family_name, 'Sample')
#         self.assertEqual(first_usr.name.company, 'Thoughtstorm')
#         self.assertEqual(str(first_usr.name), 'Gustav Sample')
#         self.assertEqual(first_usr.shipping_address.city, 'Washington')
#         self.assertEqual(first_usr.shipping_address.country, 'US')
#         self.assertEqual(first_usr.shipping_address.postcode, '20260')
#         self.assertEqual(first_usr.shipping_address.state, 'District of Columbia')
#         self.assertEqual(
#             str(first_usr.shipping_address),
#             '99 Oneill Point; Washington, District of Columbia, 20260, US'
#         )
#         self.assertEqual(first_usr.billing_address.city, 'Boulder')
#         self.assertEqual(first_usr.billing_address.country, 'US')
#         self.assertEqual(first_usr.billing_address.postcode, '80305')
#         self.assertEqual(first_usr.billing_address.state, 'Colorado')
#         self.assertEqual(
#             str(first_usr.billing_address),
#             '13787 Oakridge Parkway; Boulder, Colorado, 80305, US'
#         )
#         self.assertEqual(first_usr.phones.mob_number, '+614 37 941 958')
#         self.assertEqual(first_usr.phones.tel_number, '07 2258 3571')
#         self.assertEqual(first_usr.phones.fax_number, '07 4029 1259')
#         self.assertEqual(first_usr.socials.twitter, "bblakeway7")
#
#         self.assertEqual(first_usr.wpid, '1080')
#         self.assertEqual(first_usr.email, 'GSAMPLE6@FREE.FR')
#         # self.assertEqual(first_usr['Edited E-mail'], TimeUtils.)
#
#         if 'Role' in ColDataUser.data:
#             self.assertEqual(first_usr.role.direct_brand, "Pending")
#             self.assertEqual(first_usr.role.role, "WN")
#
#     @unittest.skipIf(
#         TimeUtils.get_system_timezone not in ['+1000', '+1100'],
#         'Tests calibrated for AEST'
#     )
#     def test_populate_subordinate_parsers_time(self):
#         populate_subordinate_parsers(
#             self.parsers, self.settings
#         )
#         usr_list = self.parsers.subordinate.get_obj_list()
#         self.assertTrue(len(usr_list))
#         first_usr = usr_list[0]
#         self.assertEqual(first_usr.act_modtime, None)
#         self.assertEqual(first_usr.act_created, None)
#         self.assertEqual(first_usr.wp_created, 1479060113.0)
#         self.assertEqual(first_usr.wp_modtime, None)
#         self.assertEqual(first_usr.last_sale, None)
#         self.assertEqual(first_usr.last_modtime, 1479060113.0)
#
#     def test_do_match(self):
#         populate_main_parsers(
#             self.parsers, self.settings
#         )
#         populate_subordinate_parsers(
#             self.parsers, self.settings
#         )
#         self.matches = do_match(
#             self.parsers, self.settings
#         )
#         self.assertEqual(len(self.matches.globals), 8)
#         # print("global matches:\n%s" % pformat(self.matches.globals))
#         # print("card duplicates:\n%s" % pformat(self.matches.duplicate['card']))
#         # print("card duplicates m:\n%s" % pformat(self.matches.duplicate['card'].m_indices))
#         card_duplicate_m_indices = self.matches.duplicate['card'].m_indices
#         self.assertEqual(len(card_duplicate_m_indices), 4)
#         # print("card duplicates s:\n%s" % pformat(self.matches.duplicate['card'].s_indices))
#         card_duplicate_s_indices = self.matches.duplicate['card'].s_indices
#         self.assertEqual(len(card_duplicate_s_indices), 6)
#         self.assertFalse(
#             set(card_duplicate_s_indices).intersection(set(card_duplicate_m_indices))
#         )
#
#     @unittest.skipIf(
#         'Role' in ColDataUser.data,
#         "Tests assume role not being synced"
#     )
#     def test_do_merge_basic_no_role(self):
#         populate_main_parsers(
#             self.parsers, self.settings
#         )
#         populate_subordinate_parsers(
#             self.parsers, self.settings
#         )
#         self.matches = do_match(
#             self.parsers, self.settings
#         )
#         self.updates = do_merge(
#             self.matches, self.parsers, self.settings
#         )
#         if self.debug:
#             self.print_updates_summary(self.updates)
#
#         self.assertEqual(len(self.updates.delta_main), 3)
#         self.assertEqual(len(self.updates.delta_subordinate), 4)
#         self.assertEqual(len(self.updates.main), 6)
#         self.assertEqual(len(self.updates.mainless), 0)
#         self.assertEqual(len(self.updates.subordinateless), 0)
#         self.assertEqual(len(self.updates.nonstatic_main), 0)
#         self.assertEqual(len(self.updates.nonstatic_subordinate), 1)
#         self.assertEqual(len(self.updates.problematic), 0)
#         self.assertEqual(len(self.updates.subordinate), 7)
#         self.assertEqual(len(self.updates.static), 7)
#
#         updates_static = self.updates.static[:]
#
#         sync_update = updates_static.pop(0)
#         # This is tested in test_do_merge_hard_2
#
#         sync_update = updates_static.pop(0)
#         try:
#             self.assertEqual(sync_update.old_m_object.MYOBID, 'C001694')
#             self.assertEqual(sync_update.old_m_object.rowcount, 45)
#             self.assertEqual(sync_update.old_m_object.name.company, 'Livetube')
#             self.assertEqual(sync_update.old_m_object.get('Business Type'), 'Worked for Business using TT')
#             self.assertEqual(sync_update.old_s_object.wpid, '1143')
#             self.assertEqual(sync_update.old_s_object.rowcount, 37)
#             self.assertEqual(sync_update.old_s_object.get('Business Type'), None)
#
#             self.assertEqual(sync_update.new_m_object.get('Business Type'), 'Worked for Business using TT')
#             self.assertEqual(sync_update.new_s_object.get('Business Type'), 'Worked for Business using TT')
#             self.assertFalse(sync_update.m_deltas)
#             self.assertTrue(sync_update.s_deltas)
#         except AssertionError as exc:
#             self.fail_syncupdate_assertion(exc, sync_update)
#         sync_update = updates_static.pop(0)
#         try:
#             self.assertEqual(sync_update.old_m_object.MYOBID, 'C001446')
#             self.assertEqual(sync_update.old_m_object.rowcount, 92)
#             self.assertEqual(sync_update.old_m_object.get('Business Type'), "Event")
#             self.assertEqual(sync_update.old_s_object.wpid, '1439')
#             self.assertEqual(sync_update.old_s_object.rowcount, 13)
#             self.assertEqual(sync_update.old_s_object.get('Business Type'), "Worked for Business using TT")
#             self.assertTrue(sync_update.m_deltas)
#             self.assertFalse(sync_update.s_deltas)
#         except AssertionError as exc:
#             self.fail_syncupdate_assertion(exc, sync_update)
#         sync_update = updates_static.pop(0)
#         # This is tested in test_do_merge_hard_1
#
#         sync_update = updates_static.pop(0)
#         try:
#             self.assertEqual(sync_update.old_m_object.MYOBID, 'C001794')
#             self.assertEqual(sync_update.old_m_object.rowcount, 43)
#             self.assertEqual(sync_update.old_m_object.name.first_name, 'Hatti')
#             self.assertEqual(sync_update.old_m_object.name.family_name, 'Clarson')
#             self.assertEqual(sync_update.old_s_object.wpid, '1379')
#             self.assertEqual(sync_update.old_s_object.rowcount, 44)
#             self.assertFalse(sync_update.m_deltas)
#             self.assertTrue(sync_update.s_deltas)
#         except AssertionError as exc:
#             self.fail_syncupdate_assertion(exc, sync_update)
#
#         sync_update = updates_static.pop(0)
#
#         try:
#             self.assertEqual(sync_update.old_m_object.MYOBID, 'C001939')
#             self.assertEqual(sync_update.old_m_object.rowcount, 62)
#             self.assertEqual(sync_update.old_m_object.name.first_name, 'Bevvy')
#             self.assertEqual(sync_update.old_m_object.name.family_name, 'Brazear')
#             self.assertEqual(sync_update.old_m_object.get('Business Type'), None)
#             self.assertEqual(sync_update.old_s_object.wpid, '1172')
#             self.assertEqual(sync_update.old_s_object.rowcount, 68)
#             self.assertEqual(sync_update.new_m_object.get('Business Type'), None)
#             self.assertTrue(sync_update.m_deltas)
#             self.assertFalse(sync_update.s_deltas)
#             main_updates = sync_update.get_main_updates()
#             self.assertFalse('Business Type' in main_updates)
#             subordinate_updates = sync_update.get_subordinate_updates()
#             self.assertFalse('Business Type' in subordinate_updates)
#
#         except AssertionError as exc:
#             self.fail_syncupdate_assertion(exc, sync_update)
#
#         sync_update = updates_static.pop(0)
#         try:
#             self.assertEqual(sync_update.old_m_object.MYOBID, 'C001129')
#             self.assertEqual(sync_update.old_m_object.rowcount, 84)
#             self.assertEqual(sync_update.old_m_object.name.first_name, 'Darwin')
#             self.assertEqual(sync_update.old_m_object.name.family_name, 'Athelstan')
#             self.assertEqual(sync_update.old_s_object.wpid, '1133')
#             self.assertEqual(sync_update.old_s_object.rowcount, 56)
#             self.assertTrue(sync_update.m_deltas)
#             self.assertFalse(sync_update.s_deltas)
#         except AssertionError as exc:
#             self.fail_syncupdate_assertion(exc, sync_update)
#
#     @unittest.skipIf(
#         "Role" not in ColDataUser.data,
#         "tests assume role being synced"
#     )
#     def test_do_merge_basic_with_role(self):
#         populate_main_parsers(
#             self.parsers, self.settings
#         )
#         populate_subordinate_parsers(
#             self.parsers, self.settings
#         )
#         self.matches = do_match(
#             self.parsers, self.settings
#         )
#         self.updates = do_merge(
#             self.matches, self.parsers, self.settings
#         )
#         if self.debug:
#             self.print_updates_summary(self.updates)
#
#         self.assertEqual(len(self.updates.delta_main), 6)
#         self.assertEqual(len(self.updates.delta_subordinate), 6)
#         self.assertEqual(len(self.updates.main), 7)
#         self.assertEqual(len(self.updates.mainless), 0)
#         self.assertEqual(len(self.updates.subordinateless), 0)
#         self.assertEqual(len(self.updates.nonstatic_main), 0)
#         self.assertEqual(len(self.updates.nonstatic_subordinate), 0)
#         self.assertEqual(len(self.updates.problematic), 0)
#         self.assertEqual(len(self.updates.subordinate), 7)
#         self.assertEqual(len(self.updates.static), 7)
#
#         updates_static = self.updates.static[:]
#
#         sync_update = updates_static.pop(0)
#         # This is tested in test_do_merge_hard_2
#
#         sync_update = updates_static.pop(0)
#         try:
#             self.assertEqual(sync_update.old_m_object.MYOBID, 'C001694')
#             self.assertEqual(sync_update.old_m_object.rowcount, 45)
#             self.assertEqual(sync_update.old_m_object.role.direct_brand, 'TechnoTan')
#             self.assertEqual(sync_update.old_m_object.role.role, 'RN')
#             self.assertEqual(sync_update.old_m_object.name.company, 'Livetube')
#             self.assertEqual(sync_update.old_m_object.get('Business Type'), 'Worked for Business using TT')
#             self.assertEqual(sync_update.old_s_object.wpid, '1143')
#             self.assertEqual(sync_update.old_s_object.rowcount, 37)
#             self.assertEqual(sync_update.old_s_object.role.direct_brand, None)
#             self.assertEqual(sync_update.old_s_object.role.role, 'RN')
#             self.assertEqual(sync_update.old_s_object.get('Business Type'), None)
#
#             self.assertEqual(sync_update.new_m_object.role.role, 'RN')
#             self.assertEqual(sync_update.new_m_object.role.direct_brand, 'TechnoTan Retail')
#             self.assertEqual(sync_update.new_m_object.get('Business Type'), 'Worked for Business using TT')
#             self.assertEqual(sync_update.new_s_object.role.role, 'RN')
#             self.assertEqual(sync_update.new_s_object.role.direct_brand, 'TechnoTan Retail')
#             self.assertEqual(sync_update.new_s_object.get('Business Type'), 'Worked for Business using TT')
#             self.assertTrue(sync_update.m_deltas)
#             self.assertTrue(sync_update.s_deltas)
#         except AssertionError as exc:
#             self.fail_syncupdate_assertion(exc, sync_update)
#         sync_update = updates_static.pop(0)
#         try:
#             self.assertEqual(sync_update.old_m_object.MYOBID, 'C001446')
#             self.assertEqual(sync_update.old_m_object.rowcount, 92)
#             self.assertEqual(sync_update.old_m_object.role.direct_brand, 'TechnoTan')
#             self.assertEqual(sync_update.old_m_object.role.role, 'ADMIN')
#             self.assertEqual(sync_update.old_m_object.get('Business Type'), "Event")
#             self.assertEqual(sync_update.old_s_object.wpid, '1439')
#             self.assertEqual(sync_update.old_s_object.rowcount, 13)
#             self.assertEqual(sync_update.old_s_object.role.direct_brand, 'TechnoTan')
#             self.assertEqual(sync_update.old_s_object.role.role, 'ADMIN')
#             self.assertEqual(sync_update.old_s_object.get('Business Type'), "Worked for Business using TT")
#             self.assertEqual(sync_update.new_m_object.role.direct_brand, 'Staff')
#             self.assertEqual(sync_update.new_m_object.role.role, 'ADMIN')
#             self.assertEqual(sync_update.new_s_object.role.direct_brand, 'Staff')
#             self.assertEqual(sync_update.new_s_object.role.role, 'ADMIN')
#             self.assertTrue(sync_update.m_deltas)
#             self.assertTrue(sync_update.s_deltas)
#         except AssertionError as exc:
#             self.fail_syncupdate_assertion(exc, sync_update)
#         sync_update = updates_static.pop(0)
#         # This is tested in test_do_merge_hard_1
#
#         sync_update = updates_static.pop(0)
#         try:
#             self.assertEqual(sync_update.old_m_object.MYOBID, 'C001794')
#             self.assertEqual(sync_update.old_m_object.rowcount, 43)
#             self.assertEqual(sync_update.old_m_object.role.role, 'ADMIN')
#             self.assertEqual(sync_update.old_m_object.role.direct_brand, None)
#             self.assertEqual(sync_update.old_m_object.name.first_name, 'Hatti')
#             self.assertEqual(sync_update.old_m_object.name.family_name, 'Clarson')
#             self.assertEqual(sync_update.old_s_object.wpid, '1379')
#             self.assertEqual(sync_update.old_s_object.rowcount, 44)
#             self.assertEqual(sync_update.old_s_object.role.role, 'WN')
#             self.assertEqual(sync_update.old_s_object.role.direct_brand, None)
#             self.assertEqual(sync_update.new_m_object.role.role, 'ADMIN')
#             self.assertEqual(sync_update.new_m_object.role.direct_brand, 'Staff')
#             self.assertEqual(sync_update.new_s_object.role.role, 'ADMIN')
#             self.assertEqual(sync_update.new_s_object.role.direct_brand, 'Staff')
#             self.assertTrue(sync_update.m_deltas)
#             self.assertTrue(sync_update.s_deltas)
#         except AssertionError as exc:
#             self.fail_syncupdate_assertion(exc, sync_update)
#
#         sync_update = updates_static.pop(0)
#
#         try:
#             self.assertEqual(sync_update.old_m_object.MYOBID, 'C001939')
#             self.assertEqual(sync_update.old_m_object.rowcount, 62)
#             self.assertEqual(sync_update.old_m_object.role.role, 'ADMIN')
#             self.assertEqual(sync_update.old_m_object.role.direct_brand, None)
#             self.assertEqual(sync_update.old_m_object.name.first_name, 'Bevvy')
#             self.assertEqual(sync_update.old_m_object.name.family_name, 'Brazear')
#             self.assertEqual(sync_update.old_m_object.get('Business Type'), None)
#             self.assertEqual(sync_update.old_s_object.wpid, '1172')
#             self.assertEqual(sync_update.old_s_object.rowcount, 68)
#             self.assertEqual(sync_update.old_s_object.role.role, 'ADMIN')
#             self.assertEqual(sync_update.old_s_object.role.direct_brand, 'Pending')
#             # self.assertEqual(sync_update.old_s_object.get('Business Type'), 'Unknown')
#             self.assertEqual(sync_update.new_m_object.role.role, 'ADMIN')
#             self.assertEqual(sync_update.new_m_object.role.direct_brand, 'Staff')
#             self.assertEqual(sync_update.new_m_object.get('Business Type'), None)
#             self.assertEqual(sync_update.new_s_object.role.role, 'ADMIN')
#             self.assertEqual(sync_update.new_s_object.role.direct_brand, 'Staff')
#             # self.assertEqual(sync_update.new_s_object.get('Business Type'), 'Unknown')
#             self.assertTrue(sync_update.m_deltas)
#             self.assertTrue(sync_update.s_deltas)
#             # TODO: uncomment these
#             main_updates = sync_update.get_main_updates()
#             self.assertFalse('Business Type' in main_updates)
#             subordinate_updates = sync_update.get_subordinate_updates()
#             self.assertFalse('Business Type' in subordinate_updates)
#
#         except AssertionError as exc:
#             self.fail_syncupdate_assertion(exc, sync_update)
#
#         sync_update = updates_static.pop(0)
#         try:
#             self.assertEqual(sync_update.old_m_object.MYOBID, 'C001129')
#             self.assertEqual(sync_update.old_m_object.rowcount, 84)
#             self.assertEqual(sync_update.old_m_object.role.direct_brand, None)
#             self.assertEqual(sync_update.old_m_object.role.role, 'WN')
#             self.assertEqual(sync_update.old_m_object.name.first_name, 'Darwin')
#             self.assertEqual(sync_update.old_m_object.name.family_name, 'Athelstan')
#             self.assertEqual(sync_update.old_s_object.wpid, '1133')
#             self.assertEqual(sync_update.old_s_object.rowcount, 56)
#             self.assertEqual(sync_update.old_s_object.role.direct_brand, 'Pending')
#             self.assertEqual(sync_update.old_s_object.role.role, 'RN')
#             # Should reflect back to ACT as RN:
#             self.assertEqual(sync_update.new_m_object.role.direct_brand, 'Pending')
#             self.assertEqual(sync_update.new_m_object.role.role, 'RN')
#             # That reflection should also go to WP:
#             self.assertEqual(sync_update.new_s_object.role.direct_brand, 'Pending')
#             self.assertEqual(sync_update.new_s_object.role.role, 'RN')
#             # Both should be delta
#             self.assertTrue(sync_update.m_deltas)
#             self.assertFalse(sync_update.s_deltas)
#         except AssertionError as exc:
#             self.fail_syncupdate_assertion(exc, sync_update)
#
#     @unittest.skipIf(
#         "Role" not in ColDataUser.data,
#         "tests assume role being synced"
#     )
#     def test_do_merge_hard_1(self):
#         suffix = 'hard_1'
#         for source, line in [('main', 8), ('subordinate', 89)]:
#             new_filename = self.make_temp_with_lines(
#                 getattr(self.settings, '%s_file' % source),
#                 [0, line],
#                 suffix
#             )
#             setattr(self.settings, '%s_file' % source, new_filename)
#
#         populate_main_parsers(
#             self.parsers, self.settings
#         )
#         populate_subordinate_parsers(
#             self.parsers, self.settings
#         )
#         self.matches = do_match(
#             self.parsers, self.settings
#         )
#         self.updates = do_merge(
#             self.matches, self.parsers, self.settings
#         )
#         sync_update = self.updates.static.pop()
#         try:
#             self.assertEqual(sync_update.old_m_object.MYOBID, 'C001280')
#             self.assertEqual(sync_update.old_m_object.role.direct_brand, 'VuTan Wholesale')
#             self.assertEqual(sync_update.old_m_object.role.role, 'WN')
#             self.assertEqual(sync_update.old_m_object.name.first_name, 'Lorry')
#             self.assertEqual(sync_update.old_m_object.name.family_name, 'Haye')
#             self.assertEqual(sync_update.old_s_object.wpid, '1983')
#             self.assertEqual(sync_update.old_s_object.role.direct_brand, None)
#             self.assertEqual(sync_update.old_s_object.role.role, 'WN')
#             self.assertEqual(sync_update.old_s_object.role.schema, 'TT')
#
#             self.assertEqual(sync_update.new_m_object.role.direct_brand, 'VuTan Wholesale')
#             self.assertEqual(sync_update.new_m_object.role.role, 'WN')
#             self.assertEqual(sync_update.new_m_object.role.schema, None)
#             self.assertEqual(sync_update.new_s_object.role.schema, 'TT')
#             self.assertEqual(sync_update.new_s_object.role.direct_brand, 'VuTan Wholesale')
#             self.assertEqual(sync_update.new_s_object.role.role, 'RN')
#             self.assertEqual(str(sync_update.new_s_object.role), 'RN; VuTan Wholesale')
#             self.assertFalse(sync_update.m_deltas)
#         except AssertionError as exc:
#             self.fail_syncupdate_assertion(exc, sync_update)
#
#     @unittest.skipIf(
#         "Role" not in ColDataUser.data,
#         "tests assume role being synced"
#     )
#     def test_do_merge_hard_2(self):
#         suffix = 'hard_2'
#         for source, line in [('main', 96), ('subordinate', 100)]:
#             new_filename = self.make_temp_with_lines(
#                 getattr(self.settings, '%s_file' % source),
#                 [0, line],
#                 suffix
#             )
#             setattr(self.settings, '%s_file' % source, new_filename)
#         populate_main_parsers(
#             self.parsers, self.settings
#         )
#         populate_subordinate_parsers(
#             self.parsers, self.settings
#         )
#         self.matches = do_match(
#             self.parsers, self.settings
#         )
#         self.updates = do_merge(
#             self.matches, self.parsers, self.settings
#         )
#         sync_update = self.updates.static.pop()
#         try:
#             self.assertEqual(sync_update.old_m_object.MYOBID, 'C016546')
#             self.assertEqual(sync_update.old_m_object.role.direct_brand, 'VuTan')
#             self.assertEqual(sync_update.old_m_object.role.role, 'WN')
#             self.assertEqual(sync_update.old_m_object.name.company, None)
#             self.assertEqual(sync_update.old_m_object.email.lower(), 'anonymised@gmail.com')
#             self.assertEqual(sync_update.old_m_object['Client Grade'], 'Casual')
#             self.assertEqual(sync_update.old_m_object.get('Business Type'), 'Personal Use Only')
#
#             self.assertEqual(sync_update.old_s_object.wpid, '12260')
#             self.assertEqual(sync_update.old_s_object.email.lower(), 'anonymised@hotmail.com')
#             self.assertEqual(sync_update.old_s_object.role.direct_brand, 'VuTan')
#             self.assertEqual(sync_update.old_s_object.role.role, 'WN')
#             self.assertEqual(sync_update.old_s_object['Client Grade'], 'Bronze')
#
#             self.assertEqual(sync_update.new_m_object.role.role, 'WN')
#             self.assertEqual(sync_update.new_m_object.role.direct_brand, 'VuTan Wholesale')
#             self.assertEqual(sync_update.new_m_object.email.lower(), 'anonymised@gmail.com')
#             self.assertEqual(sync_update.new_m_object['Client Grade'], 'Casual')
#
#             self.assertEqual(sync_update.new_s_object.role.schema, 'TT')
#             self.assertEqual(sync_update.new_s_object.role.direct_brand, 'VuTan Wholesale')
#             self.assertEqual(sync_update.new_s_object.role.role, 'RN')
#             self.assertEqual(sync_update.new_s_object.email.lower(), 'anonymised@gmail.com')
#             self.assertEqual(sync_update.new_s_object['Client Grade'], 'Casual')
#
#             self.assertTrue(sync_update.m_deltas)
#             self.assertTrue(sync_update.s_deltas)
#
#             self.assertEqual(sync_update.get_old_s_value('Role'), 'WN')
#             self.assertEqual(sync_update.get_new_s_value('Role'), 'RN')
#             # print(sync_update.display_update_list(sync_update.sync_warnings))
#             # self.assertEqual(sync_update.sync_warnings['Role'][0]['old_value'], 'WN')
#             # self.assertEqual(sync_update.sync_warnings['Role'][0]['new_value'], 'RN')
#
#         except AssertionError as exc:
#             self.fail_syncupdate_assertion(exc, sync_update)
#
#
#     def test_do_merge_false_pos(self):
#         self.settings.main_file = os.path.join(TESTS_DATA_DIR, "merger_main_false_positive.csv")
#         self.settings.subordinate_file = os.path.join(TESTS_DATA_DIR, "merger_subordinate_false_positive.csv")
#         populate_main_parsers(
#             self.parsers, self.settings
#         )
#         populate_subordinate_parsers(
#             self.parsers, self.settings
#         )
#         self.matches = do_match(
#             self.parsers, self.settings
#         )
#         self.assertTrue(self.matches)
#         self.updates = do_merge(
#             self.matches, self.parsers, self.settings
#         )
#         # self.print_updates_summary(self.updates)
#         self.assertFalse(self.updates.static)
#         self.assertFalse(self.updates.problematic)
#         # self.print_update(sync_update)
#         # try:
#         #     self.assertEqual(sync_update.old_m_object.MYOBID, 'C031472')
#         #     self.assertEqual(sync_update.old_m_object.role.direct_brand, 'VuTan Wholesale')
#         #     self.assertEqual(sync_update.old_m_object.role.role, 'WN')
#         #     self.assertEqual(sync_update.old_s_object.wpid, '17769')
#         #     self.assertEqual(sync_update.old_s_object.role.direct_brand, 'VuTan Wholesale')
#         #     self.assertEqual(sync_update.old_s_object.role.role, None)
#         #     self.assertEqual(sync_update.new_m_object, None)
#         #     self.assertEqual(sync_update.new_s_object, None)
#         #
#         #     self.assertFalse(sync_update.m_deltas)
#         #     self.assertFalse(sync_update.s_deltas)
#         #     self.assertFalse('Role Info' in sync_update.sync_warnings)
#         #     self.assertTrue('Role Info' in sync_update.sync_passes)
#         #
#         # except AssertionError as exc:
#         #     self.fail_syncupdate_assertion(exc, sync_update)
#
#     @unittest.skip("this is an exact subset of test_do_updates")
#     def test_do_report(self):
#         suffix='do_report'
#         temp_working_dir = tempfile.mkdtemp(suffix + '_working')
#         self.settings.local_work_dir = temp_working_dir
#         self.settings.init_dirs()
#         populate_main_parsers(
#             self.parsers, self.settings
#         )
#         populate_subordinate_parsers(
#             self.parsers, self.settings
#         )
#         self.matches = do_match(
#             self.parsers, self.settings
#         )
#         self.updates = do_merge(
#             self.matches, self.parsers, self.settings
#         )
#         self.reporters = do_report(
#             self.matches, self.updates, self.parsers, self.settings
#         )
#         if self.debug:
#             print("Main report text:\n%s" % self.reporters.main.get_summary_text())
#
#     def test_do_updates(self):
#         suffix='do_updates'
#         temp_working_dir = tempfile.mkdtemp(suffix + '_working')
#         self.settings.local_work_dir = temp_working_dir
#         self.settings.init_dirs()
#         populate_main_parsers(
#             self.parsers, self.settings
#         )
#         populate_subordinate_parsers(
#             self.parsers, self.settings
#         )
#         self.matches = do_match(
#             self.parsers, self.settings
#         )
#         self.updates = do_merge(
#             self.matches, self.parsers, self.settings
#         )
#         self.reporters = do_report(
#             self.matches, self.updates, self.parsers, self.settings
#         )
#         with mock.patch(
#             MockUtils.get_mock_name(self.settings.__class__, 'main_upload_client_class'),
#             new_callable=mock.PropertyMock,
#             return_value = self.settings.null_client_class
#         ), \
#         mock.patch(
#             MockUtils.get_mock_name(self.settings.__class__, 'subordinate_upload_client_class'),
#             new_callable=mock.PropertyMock,
#             return_value = self.settings.null_client_class
#         ):
#             self.results = do_updates(
#                 self.updates, self.settings
#             )
#         self.assertTrue(self.results)
#
#     def test_do_report_post(self):
#         suffix='do_summary'
#         temp_working_dir = tempfile.mkdtemp(suffix + '_working')
#         self.settings.local_work_dir = temp_working_dir
#         self.settings.init_dirs()
#         self.settings.update_main = True
#         self.settings.update_subordinate = True
#         self.settings.do_mail = False
#         populate_main_parsers(
#             self.parsers, self.settings
#         )
#         populate_subordinate_parsers(
#             self.parsers, self.settings
#         )
#         self.matches = do_match(
#             self.parsers, self.settings
#         )
#         self.updates = do_merge(
#             self.matches, self.parsers, self.settings
#         )
#         self.reporters = do_report(
#             self.matches, self.updates, self.parsers, self.settings
#         )
#
#         with mock.patch(
#             MockUtils.get_mock_name(self.settings.__class__, 'main_upload_client_class'),
#             new_callable=mock.PropertyMock,
#             return_value = self.settings.null_client_class
#         ), \
#         mock.patch(
#             MockUtils.get_mock_name(self.settings.__class__, 'subordinate_upload_client_class'),
#             new_callable=mock.PropertyMock,
#             return_value = self.settings.null_client_class
#         ):
#             self.results = do_updates(
#                 self.updates, self.settings
#             )
#
#         do_report_post(self.reporters, self.results, self.settings)
#         self.assertTrue(self.reporters.post.groups.get('fail'))
#         self.assertFalse(self.reporters.post.groups.get('success'))
#
#     def test_do_summary(self):
#         suffix='do_summary'
#         temp_working_dir = tempfile.mkdtemp(suffix + '_working')
#         self.settings.local_work_dir = temp_working_dir
#         self.settings.init_dirs()
#         self.settings.update_main = True
#         self.settings.update_subordinate = True
#         self.settings.do_mail = False
#         populate_main_parsers(
#             self.parsers, self.settings
#         )
#         populate_subordinate_parsers(
#             self.parsers, self.settings
#         )
#         self.matches = do_match(
#             self.parsers, self.settings
#         )
#         self.updates = do_merge(
#             self.matches, self.parsers, self.settings
#         )
#         self.reporters = do_report(
#             self.matches, self.updates, self.parsers, self.settings
#         )
#
#         with mock.patch(
#             MockUtils.get_mock_name(self.settings.__class__, 'main_upload_client_class'),
#             new_callable=mock.PropertyMock,
#             return_value = self.settings.null_client_class
#         ), \
#         mock.patch(
#             MockUtils.get_mock_name(self.settings.__class__, 'subordinate_upload_client_class'),
#             new_callable=mock.PropertyMock,
#             return_value = self.settings.null_client_class
#         ):
#             self.results = do_updates(
#                 self.updates, self.settings
#             )
#         do_report_post(self.reporters, self.results, self.settings)
#         summary_html, summary_text = do_summary(
#             self.settings, self.reporters, self.results, 0
#         )
#         if self.debug:
#             print("Summary HTML:\n%s" % summary_html)
#             print("Summary Text:\n%s" % summary_text)
#
#     def test_filter_ignore_cards(self):
#         self.settings.do_filter = True
#         self.settings.ignore_cards = "C001280"
#         suffix = 'filter_ignore_cards'
#         for source, lines in [('main', [0, 8, 96]), ('subordinate', [0, 89, 100])]:
#             new_filename = self.make_temp_with_lines(
#                 getattr(self.settings, '%s_file' % source),
#                 lines,
#                 suffix
#             )
#             setattr(self.settings, '%s_file' % source, new_filename)
#             if self.debug:
#                 with open(new_filename) as new_file:
#                     print(new_file.readlines())
#         populate_filter_settings(self.settings)
#         self.assertTrue(self.settings.filter_items)
#         self.assertEqual(
#             self.settings.filter_items.get('ignore_cards'),
#             self.settings.ignore_cards.split(',')
#         )
#         populate_main_parsers(
#             self.parsers, self.settings
#         )
#         populate_subordinate_parsers(
#             self.parsers, self.settings
#         )
#         # m_usr_list = self.parsers.main.get_obj_list()
#         # print("main parsers (%d): %s" % (len(m_usr_list), m_usr_list.tabulate()))
#         # s_usr_list = self.parsers.subordinate.get_obj_list()
#         # print("subordinate parsers (%d): %s" % (len(s_usr_list), s_usr_list.tabulate()))
#         # print("main parser cards: %s" % (self.parsers.main.cards.keys()))
#         self.assertTrue(
#             "C016546" in self.parsers.main.cards
#         )
#         self.assertFalse(
#             "C001280" in self.parsers.main.cards
#         )
#
#
# if __name__ == '__main__':
#     unittest.main()
#
# # just in case the files get lost
# MASTER_LINK = """https://www.mockaroo.com/8b4d8950"""
# MASTER_FIRST_ROWS = """
# MYOB Card ID,E-mail,Personal E-mail,Wordpress Username,Wordpress ID,Role,First Name,Surname,Company,Mobile Phone,Phone,Fax,Mobile Phone Preferred,Phone Preferred,Address 1,City,Postcode,State,Country,Home Address 1,Home City,Home Postcode,Home State,Home Country,Twitter Username,Web Site,ABN,Client Grade,Direct Brand,Business Type,Referred By,Edited E-mail,Edited Name,Edited Company,Edited Phone Numbers,Edited Address,Edited Alt Address,Edited Social Media,Edited Webi Site,Edited Spouse,Edited Memo,Edited Personal E-mail,Edited Web Site,Create Date,Wordpress Start Date,Edited in Act,Last Sale,Memo,Edited Added to mailing list
# C001322,gpiolli1@ezinearticles.com,kmainstone5@altervista.org,mmeddings3,1007,RN,Giacobo,Piolli,Linkbridge,+614 40 564 957,02 2791 7625,07 5971 6312,true,true,91 Alpine Trail,Duwaktenggi,6011,WA,AU,4552 Sunfield Circle,Congkar,6054,VIC,AU,kmainstone5,https://wikispaces.com/vivamus/metus/arcu/adipiscing.jpg?duis=justo&consequat=sollicitudin&dui=ut&nec=suscipit&nisi=a&volutpat=feugiat&eleifend=et&donec=eros&ut=vestibulum&dolor=ac&morbi=est&vel=lacinia&lectus=nisi&in=venenatis,57667755181,New,TechnoTan Wholesale,Internet Search,Salon Melb '14,8/11/2016 1:38:51 PM,27/11/2015 2:28:22 AM,19/09/2016 3:56:43 AM,12/11/2015 12:30:27 PM,19/05/2017 4:04:04 AM,8/08/2015 6:18:47 AM,24/11/2015 10:54:31 AM,23/04/2016 9:12:28 AM,12/12/2015 9:41:32 AM,15/09/2015 6:54:40 AM,14/02/2016 1:50:26 PM,8/02/2016 3:35:46 AM,23/04/2011 1:45:57 PM,2014-07-28 20:40:37,14/09/2010 4:57:47 PM,25/10/2015,
# """
# SLAVE_FIRST_ROWS = """
# MYOB Card ID,E-mail,Personal E-mail,Wordpress Username,Wordpress ID,Role,First Name,Surname,Company,Mobile Phone,Phone,Fax,Mobile Phone Preferred,Phone Preferred,Address 1,City,Postcode,State,Country,Home Address 1,Home City,Home Postcode,Home State,Home Country,Twitter Username,Web Site,ABN,Client Grade,Direct Brand,Business Type,Referred By,Edited E-mail,Edited Name,Edited Company,Edited Phone Numbers,Edited Address,Edited Alt Address,Edited Social Media,Edited Web Site,Edited Spouse,Edited Memo,Edited Personal E-mail,Edited Added to mailing list,Wordpress Start Date,Edited in Act,Last Sale,Memo
# C001453,gsample6@free.fr,bblakeway7@timesonline.co.uk,gsample6,1080,WN,Gustav,Sample,Thoughtstorm,+614 37 941 958,07 2258 3571,07 4029 1259,false,false,13787 Oakridge Parkway,Boulder,80305,Colorado,US,99 Oneill Point,Washington,20260,District of Columbia,US,bblakeway7.,,97 375 915 674,Bronze,Pending,Internet Search,Salon Melb '14,2017-04-14 02:13:09,2016-08-12 10:36:16,2017-03-07 01:44:01,2016-10-09 03:31:04,2017-01-14 14:09:58,2016-07-16 09:57:20,2016-08-09 23:10:49,2016-10-05 17:20:59,2016-08-29 16:53:21,2017-04-24 16:37:41,2017-03-05 22:04:12,,2016-11-14 05:01:53,,,null
# """
# SLAVE_LINK = """https://www.mockaroo.com/7ebfedb0"""
