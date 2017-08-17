from __future__ import print_function
# from unittest import TestCase, main, skip, TestSuite, TextTestRunner
import os
# import sys
import tempfile
import traceback
import unittest
from pprint import pformat

from context import tests_datadir, woogenerator
from woogenerator.conf.namespace import (MatchNamespace, ParserNamespace,
                                         SettingsNamespaceUser,
                                         UpdateNamespace, init_settings)
from woogenerator.conf.parser import ArgumentParserUser
from woogenerator.contact_objects import FieldGroup
from woogenerator.merger import (do_match, do_merge, populate_master_parsers,
                                 populate_slave_parsers, do_report)
from woogenerator.syncupdate import SyncUpdate
# from woogenerator.coldata import ColDataWoo
# from woogenerator.parsing.woo import ImportWooProduct, CsvParseWoo, CsvParseTT, WooProdList
from woogenerator.utils import Registrar  # , SanitationUtils


class TestMerger(unittest.TestCase):
    def setUp(self):
        self.settings = SettingsNamespaceUser()
        self.settings.local_work_dir = tests_datadir
        self.settings.local_live_config = None
        self.settings.local_test_config = "merger_config_test.yaml"
        self.settings.master_dialect_suggestion = "ActOut"
        self.settings.download_master = False
        self.settings.master_file = os.path.join(tests_datadir, "merger_master_dummy.csv")
        self.settings.slave_file = os.path.join(tests_datadir, "merger_slave_dummy.csv")
        # self.settings.master_parse_limit = 10
        # self.settings.slave_parse_limit = 10
        self.override_args = ""
        self.parsers = ParserNamespace()

        Registrar.DEBUG_ERROR = False
        Registrar.DEBUG_WARN = False
        Registrar.DEBUG_MESSAGE = False
        Registrar.DEBUG_PROGRESS = False

        self.debug = False
        # self.debug = True
        if self.debug:
            Registrar.DEBUG_ERROR = True
            Registrar.DEBUG_WARN = True
            Registrar.DEBUG_MESSAGE = True
            Registrar.DEBUG_PROGRESS = True
            # Registrar.DEBUG_ABSTRACT = True
            # Registrar.DEBUG_PARSER = True
            Registrar.DEBUG_CONTACT = True

        self.settings = init_settings(
            settings=self.settings,
            override_args=self.override_args,
            argparser_class=ArgumentParserUser
        )

        self.matches = MatchNamespace()
        self.updates = UpdateNamespace()

    def fail_syncupdate_assertion(self, exc, sync_update):
        msg = "failed assertion: %s\n%s\n%s" % (
            pformat(sync_update.sync_warnings.items()),
            sync_update.tabulate(tablefmt='simple'),
            traceback.format_exc(exc),
        )
        raise AssertionError(msg)

    def test_init_settings(self):

        self.assertEqual(self.settings.master_name, "ACT")
        self.assertEqual(self.settings.slave_name, "WORDPRESS")
        self.assertEqual(self.settings.download_master, False)
        self.assertEqual(
            self.settings.master_download_client_args["limit"],
            self.settings.master_parse_limit
        )
        self.assertEqual(self.settings.master_download_client_args["dialect_suggestion"], "ActOut")
        self.assertFalse(FieldGroup.do_post)
        self.assertEqual(SyncUpdate.master_name, "ACT")
        self.assertEqual(SyncUpdate.slave_name, "WORDPRESS")
        self.assertEqual(self.settings.master_parser_args.get('schema'), None)
        self.assertEqual(self.settings.slave_parser_args['schema'], "TT")

    def test_populate_master_parsers(self):
        self.settings.master_parse_limit = 4

        # Registrar.DEBUG_ERROR = True
        # Registrar.DEBUG_WARN = True
        # Registrar.DEBUG_MESSAGE = True
        # Registrar.DEBUG_CONTACT = True
        # Registrar.DEBUG_ADDRESS = True
        # Registrar.DEBUG_NAME = True

        self.parsers = populate_master_parsers(
            self.parsers, self.settings
        )

        usr_list = self.parsers.master.get_obj_list()

        self.assertEqual(self.parsers.master.schema, None)

        #number of objects:
        self.assertTrue(len(usr_list))
        # print("len: %s" % len(usr_list))
        # self.assertEqual(len(usr_list), 86)

        #first user:
        first_usr = usr_list[0]
        # print("pformat@dict:\n%s" % pformat(dict(first_usr)))
        # print("pformat@dir:\n%s" % pformat(dir(first_usr)))
        # print("str@.act_modtime:\n%s" % str(first_usr.act_modtime))
        # print("str@.act_created:\n%s" % str(first_usr.act_created))
        # print("str@.wp_created:\n%s" % str(first_usr.wp_created))
        # print("str@.wp_modtime:\n%s" % str(first_usr.wp_modtime))
        # print("str@.last_sale:\n%s" % str(first_usr.last_sale))
        # print("str@.last_modtime:\n%s" % str(first_usr.last_modtime))
        # print("str@.act_last_transaction:\n%s" % str(first_usr.act_last_transaction))
        # print("pformat@.name.to_dict:\n%s" % pformat(dict(first_usr.name.to_dict())))
        # print("pformat@.shipping_address.valid:\n%s" % pformat(first_usr.shipping_address.valid))
        # print("pformat@.shipping_address.kwargs:\n%s" % \
        #       pformat(first_usr.shipping_address.kwargs))
        # print("pformat@.shipping_address.to_dict:\n%s" % \
        #       pformat(dict(first_usr.shipping_address.to_dict())))
        # print(".billing_address:\n%s" % first_usr.billing_address)
        # print("pformat@.billing_address.to_dict:\n%s" % \
        #       pformat(dict(first_usr.billing_address.to_dict())))
        # print("pformat@.phones.to_dict:\n%s" % pformat(dict(first_usr.phones.to_dict())))
        # print("pformat@.socials.to_dict:\n%s" % pformat(dict(first_usr.socials.to_dict())))

        self.assertEqual(first_usr.name.schema, None)
        self.assertEqual(first_usr.name.first_name, 'Giacobo')
        self.assertEqual(first_usr.name.family_name, 'Piolli')
        self.assertEqual(first_usr.name.company, 'Linkbridge')
        self.assertEqual(str(first_usr.name), 'Giacobo Piolli')
        self.assertEqual(first_usr.shipping_address.city, 'Congkar')
        self.assertEqual(first_usr.shipping_address.country, 'AU')
        self.assertEqual(first_usr.shipping_address.postcode, '6054')
        self.assertEqual(first_usr.shipping_address.state, 'VIC')
        self.assertEqual(
            str(first_usr.shipping_address),
            '4552 Sunfield Circle; Congkar, VIC, 6054, AU'
        )
        self.assertEqual(first_usr.billing_address.city, 'Duwaktenggi')
        self.assertEqual(first_usr.billing_address.country, 'AU')
        self.assertEqual(first_usr.billing_address.postcode, '6011')
        self.assertEqual(first_usr.billing_address.state, 'WA')
        self.assertEqual(
            str(first_usr.billing_address),
            '91 Alpine Trail; Duwaktenggi, WA, 6011, AU'
        )
        self.assertEqual(first_usr.phones.mob_number, '+614 40 564 957')
        self.assertEqual(first_usr.phones.tel_number, '02 2791 7625')
        self.assertEqual(first_usr.phones.fax_number, '07 5971 6312')
        self.assertEqual(
            str(first_usr.phones),
            "02 2791 7625 PREF; +614 40 564 957 PREF; 07 5971 6312"
        )
        self.assertEqual(first_usr.socials.twitter, "kmainstone5")
        website = ("https://wikispaces.com/vivamus/metus/arcu/adipiscing.jpg?"
                   "duis=justo" "&consequat=sollicitudin" "&dui=ut"
                   "&nec=suscipit" "&nisi=a" "&volutpat=feugiat" "&eleifend=et"
                   "&donec=eros" "&ut=vestibulum" "&dolor=ac" "&morbi=est"
                   "&vel=lacinia" "&lectus=nisi" "&in=venenatis")
        self.assertEqual(first_usr.socials.website, website)
        self.assertEqual(first_usr['Web Site'], website)

        self.assertEqual(first_usr.act_modtime, 1284447467.0)
        self.assertEqual(first_usr.act_created, 1303530357.0)
        self.assertEqual(first_usr.wp_created, 1406544037.0)
        self.assertEqual(first_usr.wp_modtime, None)
        self.assertEqual(first_usr.last_sale, 1445691600.0)
        self.assertEqual(first_usr.last_modtime, 1445691600.0)
        self.assertEqual(first_usr.act_last_transaction, 1445691600.0)
        self.assertEqual(first_usr.role.role, "RN")
        self.assertEqual(first_usr.role.direct_brand, "TechnoTan Wholesale")

        # print(SanitationUtils.coerce_bytes(usr_list.tabulate(tablefmt='simple')))

    def test_populate_slave_parsers(self):
        self.parsers = populate_slave_parsers(
            self.parsers, self.settings
        )

        self.assertEqual(self.parsers.slave.schema, 'TT')

        usr_list = self.parsers.slave.get_obj_list()

        self.assertEqual(len(usr_list), 101)

        # print(SanitationUtils.coerce_bytes(obj_list.tabulate(tablefmt='simple')))

        self.assertTrue(len(usr_list))

        first_usr = usr_list[0]
        if Registrar.DEBUG_MESSAGE:
            print("pformat@dict:\n%s" % pformat(dict(first_usr)))
            print("pformat@dir:\n%s" % pformat(dir(first_usr)))
            print("str@.act_modtime:\n%s" % str(first_usr.act_modtime))
            print("str@.act_created:\n%s" % str(first_usr.act_created))
            print("str@.wp_created:\n%s" % str(first_usr.wp_created))
            print("str@.wp_modtime:\n%s" % str(first_usr.wp_modtime))
            print("str@.last_sale:\n%s" % str(first_usr.last_sale))
            print("str@.last_modtime:\n%s" % str(first_usr.last_modtime))
            print("pformat@.name.to_dict:\n%s" % pformat(dict(first_usr.name.to_dict())))
            # print(
            #     "pformat@.shipping_address.valid:\n%s" %
            #     pformat(first_usr.shipping_address.valid)
            # )
            # print("pformat@.shipping_address.kwargs:\n%s" % \
            #       pformat(first_usr.shipping_address.kwargs))
            # print("pformat@.shipping_address.to_dict:\n%s" % \
            #       pformat(dict(first_usr.shipping_address.to_dict())))
            # print(".billing_address:\n%s" % first_usr.billing_address)
            # print("pformat@.billing_address.to_dict:\n%s" % \
            #       pformat(dict(first_usr.billing_address.to_dict())))
            # print("pformat@.phones.to_dict:\n%s" % pformat(dict(first_usr.phones.to_dict())))
            # print("pformat@.socials.to_dict:\n%s" % pformat(dict(first_usr.socials.to_dict())))
            # print("pformat@.wpid:\n%s" % pformat(first_usr.wpid))
            # print("pformat@.email:\n%s" % pformat(first_usr.email))

        self.assertEqual(first_usr.name.schema, 'TT')
        self.assertEqual(first_usr.name.first_name, 'Gustav')
        self.assertEqual(first_usr.name.family_name, 'Sample')
        self.assertEqual(first_usr.name.company, 'Thoughtstorm')
        self.assertEqual(str(first_usr.name), 'Gustav Sample')
        self.assertEqual(first_usr.shipping_address.city, 'Washington')
        self.assertEqual(first_usr.shipping_address.country, 'US')
        self.assertEqual(first_usr.shipping_address.postcode, '20260')
        self.assertEqual(first_usr.shipping_address.state, 'District of Columbia')
        self.assertEqual(
            str(first_usr.shipping_address),
            '99 Oneill Point; Washington, District of Columbia, 20260, US'
        )
        self.assertEqual(first_usr.billing_address.city, 'Boulder')
        self.assertEqual(first_usr.billing_address.country, 'US')
        self.assertEqual(first_usr.billing_address.postcode, '80305')
        self.assertEqual(first_usr.billing_address.state, 'Colorado')
        self.assertEqual(
            str(first_usr.billing_address),
            '13787 Oakridge Parkway; Boulder, Colorado, 80305, US'
        )
        self.assertEqual(first_usr.phones.mob_number, '+614 37 941 958')
        self.assertEqual(first_usr.phones.tel_number, '07 2258 3571')
        self.assertEqual(first_usr.phones.fax_number, '07 4029 1259')
        self.assertEqual(
            str(first_usr.phones),
            "07 2258 3571 PREF; +614 37 941 958 PREF; 07 4029 1259"
        )
        self.assertEqual(first_usr.socials.twitter, "bblakeway7")

        self.assertEqual(first_usr.act_modtime, None)
        self.assertEqual(first_usr.act_created, None)
        self.assertEqual(first_usr.wp_created, 1479060113.0)
        self.assertEqual(first_usr.wp_modtime, None)
        self.assertEqual(first_usr.last_sale, None)
        self.assertEqual(first_usr.last_modtime, 1479060113.0)
        self.assertEqual(first_usr.role.direct_brand, "Pending")
        self.assertEqual(first_usr.role.role, "WN")
        self.assertEqual(first_usr.wpid, '1080')
        self.assertEqual(first_usr.email, 'GSAMPLE6@FREE.FR')
        # print("pformat@.edited_email:%s" % pformat(first_usr['Edited E-mail']))
        # self.assertEqual(first_usr['Edited E-mail'], TimeUtils.)

    def test_do_match(self):
        self.parsers = populate_master_parsers(
            self.parsers, self.settings
        )
        self.parsers = populate_slave_parsers(
            self.parsers, self.settings
        )
        self.matches = do_match(
            self.matches, self.parsers, self.settings
        )
        self.assertEqual(len(self.matches.globals), 8)
        # print("global matches:\n%s" % pformat(self.matches.globals))
        # print("card duplicates:\n%s" % pformat(self.matches.duplicate['card']))
        # print("card duplicates m:\n%s" % pformat(self.matches.duplicate['card'].m_indices))
        card_duplicate_m_indices = self.matches.duplicate['card'].m_indices
        self.assertEqual(len(card_duplicate_m_indices), 4)
        # print("card duplicates s:\n%s" % pformat(self.matches.duplicate['card'].s_indices))
        card_duplicate_s_indices = self.matches.duplicate['card'].s_indices
        self.assertEqual(len(card_duplicate_s_indices), 6)
        self.assertFalse(
            set(card_duplicate_s_indices).intersection(set(card_duplicate_m_indices))
        )

    def test_do_merge_basic(self):
        if self.debug:
            Registrar.DEBUG_MESSAGE = False
            Registrar.DEBUG_WARN = False
        self.parsers = populate_master_parsers(
            self.parsers, self.settings
        )
        self.parsers = populate_slave_parsers(
            self.parsers, self.settings
        )
        self.matches = do_match(
            self.matches, self.parsers, self.settings
        )
        self.updates = do_merge(
            self.matches, self.updates, self.parsers, self.settings
        )
        # if self.debug:
        #     Registrar.DEBUG_MESSAGE = True
        #     Registrar.DEBUG_WARN = True

        # if Registrar.DEBUG_MESSAGE:
        #     print("delta_master updates:\n%s" % map(str, (self.updates.delta_master)))
        #     print("delta_slave updates:\n%s" % map(str, (self.updates.delta_slave)))
        #     print("master updates:\n%s" % map(str, (self.updates.master)))
        #     print("new_master updates:\n%s" % map(str, (self.updates.new_master)))
        #     print("new_slave updates:\n%s" % map(str, (self.updates.new_slave)))
        #     print("nonstatic_master updates:\n%s" % map(str, (self.updates.nonstatic_master)))
        #     print("nonstatic_slave updates:\n%s" % map(str, (self.updates.nonstatic_slave)))
        #     print("problematic updates:\n%s" % map(str, (self.updates.problematic)))
        #     print("slave updates:\n%s" % map(str, (self.updates.slave)))
        #     print("static updates:\n%s" % map(str, (self.updates.static)))
        #
        #     for update in self.updates.static:
        #         print(
        #             (
        #                 "%s\n---\nM:%s\n%s\nS:%s\n%s\nwarnings"
        #                 ":\n%s\npasses:\n%s\nreflections:\n%s"
        #             ) % (
        #                 update,
        #                 update.old_m_object,
        #                 pformat(dict(update.old_m_object)),
        #                 update.old_s_object,
        #                 pformat(dict(update.old_s_object)),
        #                 update.display_sync_warnings(),
        #                 update.display_sync_passes(),
        #                 update.display_sync_reflections(),
        #             )
        #         )
        #TODO: Re-enable when test below working
        # self.assertEqual(len(self.updates.delta_master), 6)
        # self.assertEqual(len(self.updates.delta_slave), 7)
        # self.assertEqual(len(self.updates.master), 7)
        # self.assertEqual(len(self.updates.new_master), 0)
        # self.assertEqual(len(self.updates.new_slave), 0)
        # self.assertEqual(len(self.updates.nonstatic_master), 0)
        # self.assertEqual(len(self.updates.nonstatic_slave), 1)
        # self.assertEqual(len(self.updates.problematic), 0)
        # self.assertEqual(len(self.updates.slave), 8)
        # self.assertEqual(len(self.updates.static), 8)

        updates_static = self.updates.static[:]

        sync_update = updates_static.pop(0)
        try:
            if self.debug:
                print(sync_update.tabulate())
            self.assertEqual(sync_update.old_m_object.MYOBID, 'C016546')
            self.assertEqual(sync_update.old_m_object.rowcount, 98)
            self.assertEqual(sync_update.old_m_object.role.direct_brand, 'VuTan')
            self.assertEqual(sync_update.old_m_object.role.role, 'WN')
            self.assertEqual(sync_update.old_m_object.name.company, None)
            self.assertEqual(sync_update.old_m_object.email.lower(), 'aleshiaw@gmail.com')
            self.assertEqual(sync_update.old_m_object.phones.mob_number, '0468300749')
            self.assertEqual(sync_update.old_m_object['Client Grade'], 'Casual')

            self.assertEqual(sync_update.old_s_object.wpid, '12260')
            self.assertEqual(sync_update.old_s_object.email.lower(), 'aleshiaw@hotmail.com')
            self.assertEqual(sync_update.old_s_object.rowcount, 102)
            self.assertEqual(sync_update.old_s_object.role.direct_brand, 'VuTan')
            self.assertEqual(sync_update.old_s_object.role.role, 'WN')
            self.assertEqual(sync_update.old_s_object['Client Grade'], 'Bronze')
            self.assertEqual(sync_update.old_s_object.phones.mob_number, '0422 781 880')

            self.assertEqual(sync_update.new_m_object.role.role, 'WN')
            self.assertEqual(sync_update.new_m_object.role.direct_brand, 'VuTan Wholesale')
            self.assertEqual(sync_update.new_m_object.email.lower(), 'aleshiaw@gmail.com')
            self.assertEqual(sync_update.new_m_object['Client Grade'], 'Casual')
            self.assertEqual(sync_update.new_m_object.phones.mob_number, '0468300749')

            self.assertEqual(sync_update.new_s_object.role.schema, 'TT')
            self.assertEqual(sync_update.new_s_object.role.direct_brand, 'VuTan Wholesale')
            self.assertEqual(sync_update.new_s_object.role.role, 'RN')
            self.assertEqual(sync_update.new_s_object.email.lower(), 'aleshiaw@gmail.com')
            self.assertEqual(sync_update.new_s_object['Client Grade'], 'Casual')
            self.assertEqual(sync_update.new_s_object.phones.mob_number, '0468300749')


            self.assertTrue(sync_update.m_deltas)
            self.assertTrue(sync_update.s_deltas)

            self.assertEqual(sync_update.get_old_s_value('Role'), 'WN')
            self.assertEqual(sync_update.get_new_s_value('Role'), 'RN')

        except AssertionError as exc:
            self.fail_syncupdate_assertion(exc, sync_update)

        # sync_update = updates_static.pop(0)
        # try:
        #     if self.debug:
        #         print(sync_update.tabulate())
        #     self.assertEqual(sync_update.old_m_object.MYOBID, 'C033433')
        #     self.assertEqual(sync_update.old_m_object.rowcount, 99)
        #     self.assertEqual(sync_update.old_m_object.role.direct_brand, 'Pending')
        #     self.assertEqual(sync_update.old_m_object.role.role, 'RN')
        #     self.assertEqual(sync_update.old_m_object.name.first_name, 'CHELSEA')
        #     self.assertEqual(sync_update.old_m_object.name.family_name, 'ROSS')
        #     self.assertEqual(sync_update.old_s_object.wpid, '19145')
        #     self.assertEqual(sync_update.old_s_object.rowcount, 103)
        #     self.assertEqual(sync_update.old_s_object.role.role, None)
        #     self.assertEqual(sync_update.old_s_object.role.direct_brand, 'Pending')
        #
        #     self.assertFalse(sync_update.new_m_object)
        #
        #     self.assertEqual(sync_update.new_s_object.role.direct_brand, 'Pending')
        #     self.assertEqual(sync_update.new_s_object.role.role, 'RN')
        #
        #     # self.assertFalse(sync_update.m_deltas)
        #     # self.assertFalse(sync_update.s_deltas)
        #     #
        #     # slave_updates = sync_update.get_slave_updates()
        #     # self.assertEqual(len(slave_updates), 0)
        #     # slave_changes_native = sync_update.get_slave_updates_native()
        #     # self.assertEqual(len(slave_changes_native), 0)
        #
        # except AssertionError as exc:
        #     self.fail_syncupdate_assertion(exc, sync_update)

        sync_update = updates_static.pop(0)
        try:
            self.assertEqual(sync_update.old_m_object.MYOBID, 'C001694')
            self.assertEqual(sync_update.old_m_object.rowcount, 45)
            self.assertEqual(sync_update.old_m_object.role.direct_brand, 'TechnoTan')
            self.assertEqual(sync_update.old_m_object.role.role, 'RN')
            self.assertEqual(sync_update.old_m_object.name.company, 'Livetube')
            self.assertEqual(sync_update.old_s_object.wpid, '1143')
            self.assertEqual(sync_update.old_s_object.rowcount, 37)
            self.assertEqual(sync_update.old_s_object.role.direct_brand, None)
            self.assertEqual(sync_update.old_s_object.role.role, 'RN')

            self.assertEqual(sync_update.new_m_object.role.role, 'RN')
            self.assertEqual(sync_update.new_m_object.role.direct_brand, 'TechnoTan Retail')
            self.assertEqual(sync_update.new_s_object.role.role, 'RN')
            self.assertEqual(sync_update.new_s_object.role.direct_brand, 'TechnoTan Retail')
            self.assertTrue(sync_update.m_deltas)
            self.assertTrue(sync_update.s_deltas)
        except AssertionError as exc:
            self.fail_syncupdate_assertion(exc, sync_update)
        sync_update = updates_static.pop(0)
        try:
            self.assertEqual(sync_update.old_m_object.MYOBID, 'C001446')
            self.assertEqual(sync_update.old_m_object.rowcount, 92)
            self.assertEqual(sync_update.old_m_object.role.direct_brand, 'TechnoTan')
            self.assertEqual(sync_update.old_m_object.role.role, 'ADMIN')
            self.assertEqual(sync_update.old_s_object.wpid, '1439')
            self.assertEqual(sync_update.old_s_object.rowcount, 13)
            self.assertEqual(sync_update.old_s_object.role.direct_brand, 'TechnoTan')
            self.assertEqual(sync_update.old_s_object.role.role, 'ADMIN')
            self.assertEqual(sync_update.new_m_object.role.direct_brand, 'Staff')
            self.assertEqual(sync_update.new_m_object.role.role, 'ADMIN')
            self.assertEqual(sync_update.new_s_object.role.direct_brand, 'Staff')
            self.assertEqual(sync_update.new_s_object.role.role, 'ADMIN')
            self.assertTrue(sync_update.m_deltas)
            self.assertTrue(sync_update.s_deltas)
        except AssertionError as exc:
            self.fail_syncupdate_assertion(exc, sync_update)
        sync_update = updates_static.pop(0)
        try:
            self.assertEqual(sync_update.old_m_object.MYOBID, 'C001280')
            self.assertEqual(sync_update.old_m_object.rowcount, 10)
            self.assertEqual(sync_update.old_m_object.role.direct_brand, 'VuTan Wholesale')
            self.assertEqual(sync_update.old_m_object.role.role, 'WN')
            self.assertEqual(sync_update.old_m_object.name.first_name, 'Lorry')
            self.assertEqual(sync_update.old_m_object.name.family_name, 'Haye')
            self.assertEqual(sync_update.old_s_object.wpid, '1983')
            self.assertEqual(sync_update.old_s_object.rowcount, 91)
            self.assertEqual(sync_update.old_s_object.role.direct_brand, None)
            self.assertEqual(sync_update.old_s_object.role.role, 'WN')
            self.assertEqual(sync_update.new_m_object.role.direct_brand, 'VuTan Wholesale')
            self.assertEqual(sync_update.new_m_object.role.role, 'WN')
            # TODO: Must respect role of slave schema
            # self.assertEqual(sync_update.new_s_object.role.direct_brand, 'VuTan Wholesale')
            # self.assertEqual(sync_update.new_s_object.role.role, 'RN') #no, really
            self.assertFalse(sync_update.m_deltas)
            self.assertTrue(sync_update.s_deltas)
        except AssertionError as exc:
            self.fail_syncupdate_assertion(exc, sync_update)
        sync_update = updates_static.pop(0)
        try:
            self.assertEqual(sync_update.old_m_object.MYOBID, 'C001794')
            self.assertEqual(sync_update.old_m_object.rowcount, 43)
            self.assertEqual(sync_update.old_m_object.role.role, 'ADMIN')
            self.assertEqual(sync_update.old_m_object.role.direct_brand, None)
            self.assertEqual(sync_update.old_m_object.name.first_name, 'Hatti')
            self.assertEqual(sync_update.old_m_object.name.family_name, 'Clarson')
            self.assertEqual(sync_update.old_s_object.wpid, '1379')
            self.assertEqual(sync_update.old_s_object.rowcount, 44)
            self.assertEqual(sync_update.old_s_object.role.role, 'WN')
            self.assertEqual(sync_update.old_s_object.role.direct_brand, None)
            self.assertEqual(sync_update.new_m_object.role.role, 'ADMIN')
            self.assertEqual(sync_update.new_m_object.role.direct_brand, 'Staff')
            self.assertEqual(sync_update.new_s_object.role.role, 'ADMIN')
            self.assertEqual(sync_update.new_s_object.role.direct_brand, 'Staff')
            self.assertTrue(sync_update.m_deltas)
            self.assertTrue(sync_update.s_deltas)
        except AssertionError as exc:
            self.fail_syncupdate_assertion(exc, sync_update)

        sync_update = updates_static.pop(0)
        try:
            self.assertEqual(sync_update.old_m_object.MYOBID, 'C001939')
            self.assertEqual(sync_update.old_m_object.rowcount, 62)
            self.assertEqual(sync_update.old_m_object.role.role, 'ADMIN')
            self.assertEqual(sync_update.old_m_object.role.direct_brand, None)
            self.assertEqual(sync_update.old_m_object.name.first_name, 'Bevvy')
            self.assertEqual(sync_update.old_m_object.name.family_name, 'Brazear')
            self.assertEqual(sync_update.old_s_object.wpid, '1172')
            self.assertEqual(sync_update.old_s_object.rowcount, 68)
            self.assertEqual(sync_update.old_s_object.role.role, 'ADMIN')
            self.assertEqual(sync_update.old_s_object.role.direct_brand, 'Pending')
            self.assertEqual(sync_update.new_m_object.role.role, 'ADMIN')
            self.assertEqual(sync_update.new_m_object.role.direct_brand, 'Staff')
            self.assertEqual(sync_update.new_s_object.role.role, 'ADMIN')
            self.assertEqual(sync_update.new_s_object.role.direct_brand, 'Staff')
            self.assertTrue(sync_update.m_deltas)
            self.assertTrue(sync_update.s_deltas)
        except AssertionError as exc:
            self.fail_syncupdate_assertion(exc, sync_update)

        sync_update = updates_static.pop(0)
        try:
            self.assertEqual(sync_update.old_m_object.MYOBID, 'C001129')
            self.assertEqual(sync_update.old_m_object.rowcount, 84)
            self.assertEqual(sync_update.old_m_object.role.direct_brand, None)
            self.assertEqual(sync_update.old_m_object.role.role, 'WN')
            self.assertEqual(sync_update.old_m_object.name.first_name, 'Darwin')
            self.assertEqual(sync_update.old_m_object.name.family_name, 'Athelstan')
            self.assertEqual(sync_update.old_s_object.wpid, '1133')
            self.assertEqual(sync_update.old_s_object.rowcount, 56)
            self.assertEqual(sync_update.old_s_object.role.direct_brand, 'Pending')
            self.assertEqual(sync_update.old_s_object.role.role, 'RN')
            # Should reflect back to ACT as RN:
            self.assertEqual(sync_update.new_m_object.role.direct_brand, 'Pending')
            self.assertEqual(sync_update.new_m_object.role.role, 'RN')
            # That reflection should also go to WP:
            self.assertEqual(sync_update.new_s_object.role.direct_brand, 'Pending')
            self.assertEqual(sync_update.new_s_object.role.role, 'RN')
            # Both should be delta
            self.assertTrue(sync_update.m_deltas)
            self.assertFalse(sync_update.s_deltas)
        except AssertionError as exc:
            self.fail_syncupdate_assertion(exc, sync_update)

    def test_do_merge_hard_1(self):
        suffix = 'hard_1'
        for source, line in [('master', 8), ('slave', 89)]:
            with open(getattr(self.settings, '%s_file' % source)) as import_file:
                import_contents = import_file.readlines()
                new_contents = [import_contents[0], import_contents[line]]
                _, new_filename = tempfile.mkstemp('%s_%s' % (source, suffix))
                # print("seting %s to %s with contents:\n%s" % (
                #     source, new_filename, pformat(new_contents)
                # ))
                with open(new_filename, 'w+') as new_file:
                    new_file.writelines(new_contents)
                setattr(self.settings, '%s_file' % source, new_filename)

        if self.debug:
            Registrar.DEBUG_MESSAGE = False
            Registrar.DEBUG_WARN = False
        # print("masters")
        self.parsers = populate_master_parsers(
            self.parsers, self.settings
        )
        # print("slaves")
        self.parsers = populate_slave_parsers(
            self.parsers, self.settings
        )
        self.matches = do_match(
            self.matches, self.parsers, self.settings
        )
        self.updates = do_merge(
            self.matches, self.updates, self.parsers, self.settings
        )
        sync_update = self.updates.static.pop()
        try:
            self.assertEqual(sync_update.old_m_object.MYOBID, 'C001280')
            self.assertEqual(sync_update.old_m_object.role.direct_brand, 'VuTan Wholesale')
            self.assertEqual(sync_update.old_m_object.role.role, 'WN')
            self.assertEqual(sync_update.old_m_object.role.schema, None)
            self.assertEqual(sync_update.old_m_object.name.first_name, 'Lorry')
            self.assertEqual(sync_update.old_m_object.name.family_name, 'Haye')
            self.assertEqual(sync_update.old_s_object.wpid, '1983')
            self.assertEqual(sync_update.old_s_object.role.direct_brand, None)
            self.assertEqual(sync_update.old_s_object.role.role, 'WN')
            self.assertEqual(sync_update.old_s_object.role.schema, 'TT')
            self.assertEqual(sync_update.new_m_object.role.direct_brand, 'VuTan Wholesale')
            self.assertEqual(sync_update.new_m_object.role.role, 'WN')
            self.assertEqual(sync_update.new_m_object.role.schema, None)
            self.assertEqual(sync_update.new_s_object.role.schema, 'TT')
            self.assertEqual(sync_update.new_s_object.role.direct_brand, 'VuTan Wholesale')
            self.assertEqual(sync_update.new_s_object.role.role, 'RN')
            self.assertEqual(str(sync_update.new_s_object.role), 'RN; VuTan Wholesale')
            self.assertFalse(sync_update.m_deltas)
        except AssertionError as exc:
            self.fail_syncupdate_assertion(exc, sync_update)

    def test_do_merge_hard_2(self):
        suffix = 'hard_2'
        for source, line in [('master', -2), ('slave', -2)]:
            with open(getattr(self.settings, '%s_file' % source)) as import_file:
                import_contents = import_file.readlines()
                new_contents = [import_contents[0], import_contents[line]]
                _, new_filename = tempfile.mkstemp('%s_%s' % (source, suffix))
                # print("seting %s to %s with contents:\n%s" % (
                #     source, new_filename, pformat(new_contents)
                # ))
                with open(new_filename, 'w+') as new_file:
                    new_file.writelines(new_contents)
                setattr(self.settings, '%s_file' % source, new_filename)
        self.parsers = populate_master_parsers(
            self.parsers, self.settings
        )
        self.parsers = populate_slave_parsers(
            self.parsers, self.settings
        )
        self.matches = do_match(
            self.matches, self.parsers, self.settings
        )
        self.updates = do_merge(
            self.matches, self.updates, self.parsers, self.settings
        )
        sync_update = self.updates.static.pop()
        try:
            self.assertEqual(sync_update.old_m_object.MYOBID, 'C016546')
            self.assertEqual(sync_update.old_m_object.role.direct_brand, 'VuTan')
            self.assertEqual(sync_update.old_m_object.role.role, 'WN')
            self.assertEqual(sync_update.old_m_object.name.company, None)
            self.assertEqual(sync_update.old_s_object.wpid, '12260')
            self.assertEqual(sync_update.old_s_object.role.direct_brand, 'VuTan')
            self.assertEqual(sync_update.old_s_object.role.role, 'WN')

            self.assertEqual(sync_update.new_m_object.role.role, 'WN')
            self.assertEqual(sync_update.new_m_object.role.direct_brand, 'VuTan Wholesale')
            self.assertEqual(sync_update.new_s_object.role.schema, 'TT')
            self.assertEqual(sync_update.new_s_object.role.direct_brand, 'VuTan Wholesale')
            self.assertEqual(sync_update.new_s_object.role.role, 'RN')
            self.assertEqual(str(sync_update.new_s_object.role), 'RN; VuTan Wholesale')

            self.assertTrue(sync_update.m_deltas)
            self.assertTrue(sync_update.s_deltas)

            self.assertEqual(sync_update.get_old_s_value('Role'), 'WN')
            self.assertEqual(sync_update.get_new_s_value('Role'), 'RN')
            # print(sync_update.display_update_list(sync_update.sync_warnings))
            # self.assertEqual(sync_update.sync_warnings['Role'][0]['old_value'], 'WN')
            # self.assertEqual(sync_update.sync_warnings['Role'][0]['new_value'], 'RN')

        except AssertionError as exc:
            self.fail_syncupdate_assertion(exc, sync_update)

    def test_do_report(self):
        suffix='do_report'
        temp_out_dir = tempfile.mkdtemp(suffix + '_out')
        if self.debug:
            print("out dir is %s" % temp_out_dir)
        self.settings.out_folder = temp_out_dir
        self.settings.do_merge = True
        self.settings.do_sync = True
        if self.debug:
            print("rep_path_full is %s" % self.settings.rep_path_full)
        # self.settings.process_duplicates = True
        self.parsers = populate_master_parsers(
            self.parsers, self.settings
        )
        self.parsers = populate_slave_parsers(
            self.parsers, self.settings
        )
        self.matches = do_match(
            self.matches, self.parsers, self.settings
        )
        self.updates = do_merge(
            self.matches, self.updates, self.parsers, self.settings
        )
        do_report(
            self.matches, self.updates, self.parsers, self.settings
        )

if __name__ == '__main__':
    unittest.main()

# just in case the files get lost
MASTER_LINK = """https://www.mockaroo.com/8b4d8950"""
MASTER_FIRST_ROWS = """
MYOB Card ID,E-mail,Personal E-mail,Wordpress Username,Wordpress ID,Role,First Name,Surname,Company,Mobile Phone,Phone,Fax,Mobile Phone Preferred,Phone Preferred,Address 1,City,Postcode,State,Country,Home Address 1,Home City,Home Postcode,Home State,Home Country,Twitter Username,Web Site,ABN,Client Grade,Direct Brand,Business Type,Referred By,Edited E-mail,Edited Name,Edited Company,Edited Phone Numbers,Edited Address,Edited Alt Address,Edited Social Media,Edited Webi Site,Edited Spouse,Edited Memo,Edited Personal E-mail,Edited Web Site,Create Date,Wordpress Start Date,Edited in Act,Last Sale,Memo,Edited Added to mailing list
C001322,gpiolli1@ezinearticles.com,kmainstone5@altervista.org,mmeddings3,1007,RN,Giacobo,Piolli,Linkbridge,+614 40 564 957,02 2791 7625,07 5971 6312,true,true,91 Alpine Trail,Duwaktenggi,6011,WA,AU,4552 Sunfield Circle,Congkar,6054,VIC,AU,kmainstone5,https://wikispaces.com/vivamus/metus/arcu/adipiscing.jpg?duis=justo&consequat=sollicitudin&dui=ut&nec=suscipit&nisi=a&volutpat=feugiat&eleifend=et&donec=eros&ut=vestibulum&dolor=ac&morbi=est&vel=lacinia&lectus=nisi&in=venenatis,57667755181,New,TechnoTan Wholesale,Internet Search,Salon Melb '14,8/11/2016 1:38:51 PM,27/11/2015 2:28:22 AM,19/09/2016 3:56:43 AM,12/11/2015 12:30:27 PM,19/05/2017 4:04:04 AM,8/08/2015 6:18:47 AM,24/11/2015 10:54:31 AM,23/04/2016 9:12:28 AM,12/12/2015 9:41:32 AM,15/09/2015 6:54:40 AM,14/02/2016 1:50:26 PM,8/02/2016 3:35:46 AM,23/04/2011 1:45:57 PM,2014-07-28 20:40:37,14/09/2010 4:57:47 PM,25/10/2015,
"""
SLAVE_FIRST_ROWS = """
MYOB Card ID,E-mail,Personal E-mail,Wordpress Username,Wordpress ID,Role,First Name,Surname,Company,Mobile Phone,Phone,Fax,Mobile Phone Preferred,Phone Preferred,Address 1,City,Postcode,State,Country,Home Address 1,Home City,Home Postcode,Home State,Home Country,Twitter Username,Web Site,ABN,Client Grade,Direct Brand,Business Type,Referred By,Edited E-mail,Edited Name,Edited Company,Edited Phone Numbers,Edited Address,Edited Alt Address,Edited Social Media,Edited Web Site,Edited Spouse,Edited Memo,Edited Personal E-mail,Edited Added to mailing list,Wordpress Start Date,Edited in Act,Last Sale,Memo
C001453,gsample6@free.fr,bblakeway7@timesonline.co.uk,gsample6,1080,WN,Gustav,Sample,Thoughtstorm,+614 37 941 958,07 2258 3571,07 4029 1259,false,false,13787 Oakridge Parkway,Boulder,80305,Colorado,US,99 Oneill Point,Washington,20260,District of Columbia,US,bblakeway7.,,97 375 915 674,Bronze,Pending,Internet Search,Salon Melb '14,2017-04-14 02:13:09,2016-08-12 10:36:16,2017-03-07 01:44:01,2016-10-09 03:31:04,2017-01-14 14:09:58,2016-07-16 09:57:20,2016-08-09 23:10:49,2016-10-05 17:20:59,2016-08-29 16:53:21,2017-04-24 16:37:41,2017-03-05 22:04:12,,2016-11-14 05:01:53,,,null
"""
SLAVE_LINK = """https://www.mockaroo.com/7ebfedb0"""
