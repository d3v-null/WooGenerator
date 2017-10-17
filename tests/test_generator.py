from __future__ import print_function

import os
import unittest
from pprint import pformat

from tabulate import tabulate

from context import TESTS_DATA_DIR, woogenerator
from test_sync_manager import AbstractSyncManagerTestCase
from woogenerator.generator import populate_master_parsers, populate_slave_parsers
from woogenerator.namespace.prod import SettingsNamespaceProd
from woogenerator.parsing.special import SpecialGruopList
from woogenerator.parsing.woo import WooProdList
from woogenerator.parsing.xero import XeroProdList, ApiParseXero
from woogenerator.parsing.tree import ItemList
from woogenerator.utils import Registrar, SanitationUtils

# import argparse




class TestGeneratorDummySpecials(AbstractSyncManagerTestCase):
    settings_namespace_class = SettingsNamespaceProd
    config_file = "generator_config_test.yaml"

    def setUp(self):
        super(TestGeneratorDummySpecials, self).setUp()
        self.settings.master_dialect_suggestion = "SublimeCsvTable"
        self.settings.download_master = False
        self.settings.master_file = os.path.join(
            TESTS_DATA_DIR, "generator_master_dummy.csv"
        )
        self.settings.specials_file = os.path.join(
            TESTS_DATA_DIR, "generator_specials_dummy.csv"
        )
        self.settings.do_specials = True
        self.settings.init_settings(self.override_args)

    def test_init_settings(self):

        self.assertEqual(self.settings.master_name, "GDrive")
        self.assertEqual(self.settings.slave_name, "WooCommerce")
        self.assertEqual(self.settings.merge_mode, "sync")
        self.assertEqual(self.settings.schema, "CA")
        self.assertEqual(self.settings.download_master, False)
        self.assertEqual(
            self.settings.master_download_client_args["dialect_suggestion"],
            "SublimeCsvTable")
        self.assertEqual(self.settings.spec_gid, None)
        # print("MPA: %s" % self.settings.master_parser_args)
        # self.settings.master_parser_args = {
        #     'taxo_depth': 3,
        #     'cols': [
        #         'WNR', 'RNR', 'DNR', 'weight', 'length', 'width', 'height',
        #         'HTML Description', 'PA', 'VA', 'D', 'E', 'DYNCAT', 'DYNPROD',
        #         'VISIBILITY', 'SCHEDULE', 'RPR', 'WPR', 'DPR', 'CVC', 'stock',
        #         'stock_status', 'Images', 'Updated', 'post_status'
        #     ],
        #     'defaults': {
        #         'SCHEDULE': '',
        #         'post_status': 'publish',
        #         'manage_stock': 'no',
        #         'catalog_visibility': 'visible',
        #         'Images': '',
        #         'CVC': 0
        #     },
        #     'import_name':'2017-07-21_09-14-23',
        #     'item_depth':2,
        #     'schema':'CA'
        # }


    def test_populate_master_parsers(self):
        # self.test_init_settings()
        # self.settings.product_parser_args = {
        #     'import_name': self.settings.import_name,
        #     'item_depth': self.settings.item_depth,
        #     'taxo_depth': self.settings.taxo_depth,
        # }

        self.parsers = populate_master_parsers(self.parsers, self.settings)

        #number of objects:
        self.assertEqual(len(self.parsers.master.objects.values()), 163)
        self.assertEqual(len(self.parsers.master.items.values()), 144)

        prod_list = WooProdList(self.parsers.master.products.values())
        self.assertEqual(len(prod_list), 48)
        first_prod = prod_list[0]
        self.assertEqual(first_prod.codesum, "ACARA-CAL")
        self.assertEqual(first_prod.parent.codesum, "ACARA-CA")
        self.assertEqual(first_prod.specials,
                         ['SP2016-08-12-ACA', 'EOFY2016-ACA'])
        self.assertEqual(first_prod.product_type, "simple")
        self.assertEqual(first_prod.depth, 4)
        self.assertTrue(first_prod.is_item)
        self.assertTrue(first_prod.is_product)
        self.assertFalse(first_prod.is_category)
        self.assertFalse(first_prod.is_root)
        self.assertFalse(first_prod.is_taxo)
        self.assertFalse(first_prod.is_variable)
        self.assertFalse(first_prod.is_variation)
        for key, value in {
                'DNR': u'59.97',
                'DPR': u'57.47',
                'RNR': u'',
                'RPR': u'',
                'WNR': u'99.95',
                'WPR': u'84.96',
                'height': u'235',
                'length': u'85',
                'price': u'',
                'weight': u'1.08',
                'width': u'85'
        }.items():
            self.assertEqual(first_prod[key], value)
        # print("pformat:\n%s" % pformat(dict(first_prod)))
        # print("dir:")
        # print(pformat(dir(first_prod)))
        # print("vars")
        # print(pformat(vars(first_prod)))
        # for attr in ["depth"]:
        # print("first_prod.%s: %s" % (attr, pformat(getattr(first_prod, attr))))
        # print(SanitationUtils.coerce_bytes(prod_list.tabulate(tablefmt='simple')))

        spec_list = SpecialGruopList(self.parsers.special.rule_groups.values())
        if Registrar.DEBUG_MESSAGE:
            Registrar.register_message(
                SanitationUtils.coerce_bytes(
                    spec_list.tabulate(tablefmt='simple')))
        first_group = spec_list[0]
        if Registrar.DEBUG_MESSAGE:
            Registrar.register_message(
                "first group:\n%s\npformat@dict:\n%s\npformat@dir:\n%s\n" %
                (SanitationUtils.coerce_bytes(
                    tabulate(first_group.children, tablefmt='simple')),
                 pformat(dict(first_group)), pformat(dir(first_group))))

    def test_populate_slave_parsers(self):
        self.parsers = populate_master_parsers(self.parsers, self.settings)
        # TODO: finish this
        # self.parsers = populate_slave_parsers(self.parsers, self.settings)

class TestGeneratorXeroDummy(AbstractSyncManagerTestCase):
    settings_namespace_class = SettingsNamespaceProd
    config_file = "generator_config_test.yaml"

    # debug = True

    def setUp(self):
        super(TestGeneratorXeroDummy, self).setUp()
        self.settings.download_master = False
        self.settings.init_settings(self.override_args)
        self.settings.schema = "XERO"
        self.settings.slave_name = "Xero"
        self.settings.do_categories = False
        self.settings.master_file = os.path.join(
            TESTS_DATA_DIR, "generator_master_dummy_xero.csv"
        )
        self.settings.master_dialect_suggestion = "SublimeCsvTable"
        self.settings.slave_file = os.path.join(
            TESTS_DATA_DIR, "xero_demo_data.json"
        )
        if self.debug:
            # Registrar.DEBUG_SHOP = True
            # ApiParseXero.DEBUG_PARSER = True
            # Registrar.DEBUG_ABSTRACT = True
            # Registrar.DEBUG_GEN = True
            # Registrar.DEBUG_TREE = True
            # Registrar.DEBUG_TRACE = True
            # ApiParseXero.DEBUG_API = True
            ApiParseXero.product_resolver = Registrar.exception_resolver

    def test_populate_master_parsers(self):
        # if self.debug:
        #     import pudb; pudb.set_trace()
        self.parsers = populate_master_parsers(self.parsers, self.settings)
        if self.debug:
            print("master objects: %s" % len(self.parsers.master.objects.values()))
            print("master items: %s" % len(self.parsers.master.items.values()))
            print("master products: %s" % len(self.parsers.master.products.values()))

        self.assertEqual(len(self.parsers.master.objects.values()), 29)
        self.assertEqual(len(self.parsers.master.items.values()), 20)

        prod_list = XeroProdList(self.parsers.master.products.values())
        if self.debug:
            print("prod list:\n%s" % prod_list.tabulate())
            item_list = ItemList(self.parsers.master.items.values())
            print("item list:\n%s" % item_list.tabulate())
            print("prod_keys: %s" % self.parsers.master.products.keys())

        self.assertEqual(len(prod_list), 15)
        first_prod = prod_list[0]
        self.assertEqual(first_prod.codesum, "GB1-White")
        self.assertEqual(first_prod.parent.codesum, "GB")
        self.assertTrue(first_prod.is_product)
        self.assertFalse(first_prod.is_category)
        self.assertFalse(first_prod.is_root)
        self.assertFalse(first_prod.is_taxo)
        self.assertFalse(first_prod.is_variable)
        self.assertFalse(first_prod.is_variation)
        for key, value in {
                'RNR': u'5.60',
        }.items():
            self.assertEqual(first_prod[key], value)

    def test_populate_slave_parsers(self):
        # self.parsers = populate_master_parsers(self.parsers, self.settings)
        self.parsers = populate_slave_parsers(self.parsers, self.settings)

        if self.debug:
            print("slave objects: %s" % len(self.parsers.slave.objects.values()))
            print("slave items: %s" % len(self.parsers.slave.items.values()))
            print("slave products: %s" % len(self.parsers.slave.products.values()))

        self.assertEqual(len(self.parsers.slave.objects.values()), 10)
        self.assertEqual(len(self.parsers.slave.items.values()), 10)

        prod_list = XeroProdList(self.parsers.slave.products.values())
        if self.debug:
            print("prod list:\n%s" % prod_list.tabulate())
            item_list = ItemList(self.parsers.slave.items.values())
            print("item list:\n%s" % item_list.tabulate())
            print("prod_keys: %s" % self.parsers.slave.products.keys())

        self.assertEqual(len(prod_list), 10)
        first_prod = prod_list[0]
        self.assertEqual(first_prod.codesum, "DevD")
        self.assertTrue(first_prod.is_product)
        self.assertFalse(first_prod.is_category)
        self.assertFalse(first_prod.is_root)
        self.assertFalse(first_prod.is_taxo)
        self.assertFalse(first_prod.is_variable)
        self.assertFalse(first_prod.is_variation)

if __name__ == '__main__':
    unittest.main()
