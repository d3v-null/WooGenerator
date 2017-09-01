from __future__ import print_function
import os
# import sys
from pprint import pformat
import unittest
from unittest import TestCase
from tabulate import tabulate
# import argparse

from context import woogenerator
from woogenerator.parsing.woo import WooProdList
from woogenerator.parsing.special import SpecialGruopList
from woogenerator.utils import Registrar, SanitationUtils
from woogenerator.conf.parser import ArgumentParserProd
from woogenerator.conf.namespace import SettingsNamespaceProd, init_settings, ParserNamespace
from woogenerator.generator import populate_master_parsers

from context import TESTS_DATA_DIR


class TestGenerator(TestCase):
    def setUp(self):

        self.settings = SettingsNamespaceProd()
        self.settings.local_work_dir = TESTS_DATA_DIR
        self.settings.local_live_config = None
        self.settings.local_test_config = "generator_config_test.yaml"
        self.settings.master_dialect_suggestion = "SublimeCsvTable"
        self.settings.download_master = False
        self.settings.master_file = os.path.join(TESTS_DATA_DIR,
                                                 "generator_master_dummy.csv")
        self.settings.specials_file = os.path.join(
            TESTS_DATA_DIR, "generator_specials_dummy.csv")
        self.settings.do_specials = True
        # self.settings.master_limit = 10
        self.override_args = ""
        self.parsers = ParserNamespace()

        Registrar.DEBUG_ERROR = False
        Registrar.DEBUG_WARN = False
        Registrar.DEBUG_MESSAGE = False
        Registrar.DEBUG_PROGRESS = False

        # Registrar.DEBUG_MESSAGE = True
        # Registrar.DEBUG_ERROR = True
        # Registrar.DEBUG_ABSTRACT = True
        # Registrar.DEBUG_PARSER = True
        # Registrar.DEBUG_WARN = False
        # Registrar.DEBUG_PROGRESS = False

        self.settings = init_settings(
            settings=self.settings,
            override_args=self.override_args,
            argparser_class=ArgumentParserProd)

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
        self.assertTrue(first_prod.isItem)
        self.assertTrue(first_prod.isProduct)
        self.assertFalse(first_prod.isCategory)
        self.assertFalse(first_prod.isRoot)
        self.assertFalse(first_prod.isTaxo)
        self.assertFalse(first_prod.isVariable)
        self.assertFalse(first_prod.isVariation)
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


if __name__ == '__main__':
    unittest.main()
