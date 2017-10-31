from __future__ import print_function

import os
import unittest
from pprint import pformat
import tempfile

from tabulate import tabulate

from context import TESTS_DATA_DIR, woogenerator
from test_sync_manager import AbstractSyncManagerTestCase
from woogenerator.generator import (
    populate_master_parsers, populate_slave_parsers, do_match, product_index_fn,
    do_merge, do_report, do_match_categories, do_merge_categories
)
from woogenerator.namespace.core import MatchNamespace, UpdateNamespace
from woogenerator.namespace.prod import SettingsNamespaceProd
from woogenerator.parsing.special import SpecialGruopList
from woogenerator.parsing.woo import WooProdList, CsvParseWoo
from woogenerator.parsing.api import ApiParseWoo
from woogenerator.parsing.xero import ApiParseXero
from woogenerator.parsing.tree import ItemList
from woogenerator.utils import Registrar, SanitationUtils
from woogenerator.utils.reporter import ReporterNamespace

# import argparse


class TestGeneratorDummySpecials(AbstractSyncManagerTestCase):
    settings_namespace_class = SettingsNamespaceProd
    config_file = "generator_config_test.yaml"

    # debug = True

    def setUp(self):
        super(TestGeneratorDummySpecials, self).setUp()
        self.settings.master_dialect_suggestion = "SublimeCsvTable"
        self.settings.download_master = False
        self.settings.download_slave = False
        self.settings.init_settings(self.override_args)
        self.settings.master_file = os.path.join(
            TESTS_DATA_DIR, "generator_master_dummy.csv"
        )
        self.settings.specials_file = os.path.join(
            TESTS_DATA_DIR, "generator_specials_dummy.csv"
        )
        self.settings.do_specials = True
        self.settings.do_sync = True
        self.settings.do_categories = True
        self.settings.report_matching = True
        self.settings.schema = "CA"
        self.settings.init_settings(self.override_args)
        if self.settings.wc_api_is_legacy:
            self.settings.slave_file = os.path.join(
                TESTS_DATA_DIR, "prod_slave_woo_api_dummy_legacy.json"
            )
            self.settings.slave_cat_file = os.path.join(
                TESTS_DATA_DIR, "prod_slave_categories_woo_api_dummy_legacy.json"
            )
        else:
            self.settings.slave_file = os.path.join(
                TESTS_DATA_DIR, "prod_slave_woo_api_dummy_wp-json.json"
            )
            self.settings.slave_cat_file = os.path.join(
                TESTS_DATA_DIR, "prod_slave_cat_woo_api_dummy_wp-json.json"
            )

        # TODO: this
        if self.debug:
            # Registrar.DEBUG_SHOP = True
            # Registrar.DEBUG_PARSER = True
            # Registrar.DEBUG_ABSTRACT = True
            # Registrar.DEBUG_GEN = True
            # Registrar.DEBUG_TREE = True
            # Registrar.DEBUG_TRACE = True
            # Registrar.DEBUG_UPDATE = True
            # Registrar.DEBUG_ERROR = True
            # Registrar.DEBUG_WARN = True
            # Registrar.DEBUG_MESSAGE = True
            # Registrar.DEBUG_SPECIAL = True
            # Registrar.DEBUG_PARSER = True
            # Registrar.DEBUG_WOO = True
            ApiParseWoo.product_resolver = Registrar.exception_resolver
            CsvParseWoo.product_resolver = Registrar.exception_resolver

    def test_init_settings(self):

        self.assertEqual(self.settings.master_name, "gdrive-test")
        self.assertEqual(self.settings.slave_name, "woocommerce-test")
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

        prod_container = self.parsers.master.product_container.container
        prod_list = prod_container(self.parsers.master.products.values())
        self.assertEqual(len(prod_list), 48)
        first_prod = prod_list[0]
        self.assertEqual(first_prod.codesum, "ACARA-CAL")
        self.assertEqual(first_prod.parent.codesum, "ACARA-CA")
        first_prod_specials = first_prod.specials
        self.assertEqual(first_prod_specials,
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

        cat_container = self.parsers.master.category_container.container
        cat_list = cat_container(self.parsers.master.categories.values())
        if self.debug:
            print(SanitationUtils.coerce_bytes(
                cat_list.tabulate(tablefmt='simple')
            ))
        self.assertEqual(len(cat_list), 9)
        first_cat = cat_list[0]
        if self.debug:
            print("pformat@dict@first_cat:\n%s" % pformat(dict(first_cat)))
        self.assertEqual(first_cat.codesum, 'A')
        self.assertEqual(first_cat.title, 'Product A')
        self.assertEqual(first_cat.depth, 0)
        second_cat = cat_list[1]
        self.assertEqual(second_cat.codesum, 'ACA')
        self.assertEqual(second_cat.depth, 1)
        self.assertEqual(second_cat.parent.codesum, 'A')

        spec_list = SpecialGruopList(self.parsers.special.rule_groups.values())
        if self.debug:
            print(SanitationUtils.coerce_bytes(
                    spec_list.tabulate(tablefmt='simple')
            ))
        first_group = spec_list[0]
        if self.debug:
            print("first group:\n%s\npformat@dict:\n%s\npformat@dir:\n%s\n" %
                (SanitationUtils.coerce_bytes(
                    tabulate(first_group.children, tablefmt='simple')),
                 pformat(dict(first_group)), pformat(dir(first_group)))
            )

    def test_populate_slave_parsers(self):
        self.parsers = populate_master_parsers(self.parsers, self.settings)
        self.parsers = populate_slave_parsers(self.parsers, self.settings)
        # TODO: finish this
        if self.debug:
            print("slave objects: %s" % len(self.parsers.slave.objects.values()))
            print("slave items: %s" % len(self.parsers.slave.items.values()))
            print("slave products: %s" % len(self.parsers.slave.products.values()))
            print("slave categories: %s" % len(self.parsers.slave.categories.values()))

        self.assertEqual(len(self.parsers.slave.products), 48)
        prod_container = self.parsers.slave.product_container.container
        prod_list = prod_container(self.parsers.slave.products.values())
        first_prod = prod_list[0]
        if self.debug:
            print("first_prod.dict %s" % pformat(dict(first_prod)))

        self.assertEqual(first_prod.codesum, "ACARF-CRS")
        # TODO: Implement category tree in slave
        # self.assertEqual(first_prod.parent.codesum, "ACARF-CR")
        self.assertEqual(first_prod.product_type, "simple")
        self.assertTrue(first_prod.is_item)
        self.assertTrue(first_prod.is_product)
        self.assertFalse(first_prod.is_category)
        self.assertFalse(first_prod.is_root)
        self.assertFalse(first_prod.is_taxo)
        self.assertFalse(first_prod.is_variable)
        self.assertFalse(first_prod.is_variation)
        for key, value in {
                'height': u'120',
                'length': u'40',
                'weight': u'0.12',
                'width': u'40',
                'DNR': u'8.45',
                'DPR': u'7.75',
                'WNR': u'12.95',
                'WPR': u'11.00',
        }.items():
            self.assertEqual(first_prod[key], value)

        cat_container = self.parsers.slave.category_container.container
        cat_list = cat_container(self.parsers.slave.categories.values())
        if self.debug:
            print("cat_container is %s" % cat_container)
            print(SanitationUtils.coerce_bytes(
                cat_list.tabulate(tablefmt='simple')
            ))
        self.assertEqual(len(cat_list), 9)
        first_cat = cat_list[0]
        if self.debug:
            print("pformat@dict@first_cat:\n%s" % pformat(dict(first_cat)))
        self.assertEqual(first_cat.slug, 'product-a')
        self.assertEqual(first_cat.title, 'Product A')
        self.assertEqual(first_cat.api_id, 315)

    def test_do_match_categories(self):
        self.parsers = populate_master_parsers(self.parsers, self.settings)
        self.parsers = populate_slave_parsers(self.parsers, self.settings)
        if self.settings.do_categories:
            self.matches = do_match_categories(
                self.parsers, self.matches, self.settings
            )

        if self.debug:
            self.matches.category.globals.tabulate()
            self.print_matches_summary(self.matches.category)

        self.assertEqual(len(self.matches.category.globals), 9)
        first_match = self.matches.category.globals[2]
        first_master = first_match.m_object
        first_slave = first_match.s_object
        if self.debug:
            print('pformat@dict@first_master:\n%s' % pformat(dict(first_master)))
            print('pformat@dict@first_slave:\n%s' % pformat(dict(first_slave)))
            master_keys = set(dict(first_master).keys())
            slave_keys = set(dict(first_slave).keys())
            intersect_keys = master_keys.intersection(slave_keys)
            print("intersect_keys:\n")
            for key in intersect_keys:
                print("%20s | %50s | %50s" % (
                    str(key), str(first_master[key])[:50], str(first_slave[key])[:50]
                ))
        for match in self.matches.category.globals:
            self.assertEqual(match.m_object.title, match.s_object.title)

    def test_do_merge_categories(self):
        self.parsers = populate_master_parsers(self.parsers, self.settings)
        self.parsers = populate_slave_parsers(self.parsers, self.settings)
        if self.settings.do_categories:
            self.matches = do_match_categories(
                self.parsers, self.matches, self.settings
            )
            self.updates = do_merge_categories(
                self.matches, self.parsers, self.updates, self.settings
            )

        if self.debug:
            self.print_updates_summary(self.updates.category)
        self.assertEqual(len(self.updates.category.master), 9)
        sync_update = self.updates.category.master[1]
        if self.debug:
            self.print_update(sync_update)
        try:
            master_desc = (
                "Company A have developed a range of unique blends in 16 "
                "shades to suit all use cases. All Company A's products "
                "are created using the finest naturally derived botanical "
                "and certified organic ingredients."
            )
            self.assertEqual(
                sync_update.old_m_object['HTML Description'],
                master_desc
            )
            self.assertEqual(
                sync_update.old_s_object['HTML Description'],
                "Company A have developed stuff"
            )
            self.assertEqual(
                sync_update.new_s_object['HTML Description'],
                master_desc
            )
        except AssertionError as exc:
            self.fail_syncupdate_assertion(exc, sync_update)

    def test_do_match(self):
        self.parsers = populate_master_parsers(self.parsers, self.settings)
        self.parsers = populate_slave_parsers(self.parsers, self.settings)
        if self.settings.do_categories:
            self.matches = do_match_categories(
                self.parsers, self.matches, self.settings
            )
            self.updates = do_merge_categories(
                self.matches, self.parsers, self.updates, self.settings
            )
        self.matches = do_match(self.parsers, self.matches, self.settings)

        if self.debug:
            self.matches.globals.tabulate()
            self.print_matches_summary(self.matches)

        self.assertEqual(len(self.matches.globals), 48)
        if self.debug:
            for index, matches in self.matches.category.prod.items():
                print("prod_matches: %s" % index)
                self.print_matches_summary(matches)
        prod_cat_match = self.matches.category.prod['ACARF-CRS | 1961']
        self.assertEqual(len(prod_cat_match.globals), 3)
        self.assertEqual(len(prod_cat_match.slaveless), 1)

    def test_do_merge(self):
        self.parsers = populate_master_parsers(self.parsers, self.settings)
        self.parsers = populate_slave_parsers(self.parsers, self.settings)
        if self.settings.do_categories:
            self.matches = do_match_categories(
                self.parsers, self.matches, self.settings
            )
            self.updates = do_merge_categories(
                self.matches, self.parsers, self.updates, self.settings
            )
        self.matches = do_match(self.parsers, self.matches, self.settings)
        self.updates = do_merge(self.matches, self.parsers, self.updates, self.settings)

        if self.debug:
            self.print_updates_summary(self.updates)
        self.assertEqual(len(self.updates.slave), 1)
        sync_update = self.updates.slave[0]
        if self.debug:
            self.print_update(sync_update)
        try:
            self.assertEquals(sync_update.old_m_object['catlist'], [320, 323, 315, 316])
            self.assertEquals(sync_update.old_s_object['catlist'], [320, 315, 316])
            self.assertEquals(sync_update.new_s_object['catlist'], [320, 323, 315, 316])

        except AssertionError as exc:
            self.fail_syncupdate_assertion(exc, sync_update)



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
        self.settings.do_sync = True
        self.settings.do_categories = False
        self.settings.master_file = os.path.join(
            TESTS_DATA_DIR, "generator_master_dummy_xero.csv"
        )
        self.settings.master_dialect_suggestion = "SublimeCsvTable"
        self.settings.slave_file = os.path.join(
            TESTS_DATA_DIR, "xero_demo_data.json"
        )
        self.settings.report_matching = True
        if self.debug:
            # Registrar.DEBUG_SHOP = True
            # ApiParseXero.DEBUG_PARSER = True
            # Registrar.DEBUG_ABSTRACT = True
            # Registrar.DEBUG_GEN = True
            # Registrar.DEBUG_TREE = True
            # Registrar.DEBUG_TRACE = True
            # ApiParseXero.DEBUG_API = True
            Registrar.DEBUG_UPDATE = True
            ApiParseXero.product_resolver = Registrar.exception_resolver

    def test_populate_master_parsers(self):
        self.parsers = populate_master_parsers(self.parsers, self.settings)
        if self.debug:
            print("master objects: %s" % len(self.parsers.master.objects.values()))
            print("master items: %s" % len(self.parsers.master.items.values()))
            print("master products: %s" % len(self.parsers.master.products.values()))

        self.assertEqual(len(self.parsers.master.objects.values()), 29)
        self.assertEqual(len(self.parsers.master.items.values()), 20)

        prod_container = self.parsers.master.product_container.container
        prod_list = prod_container(self.parsers.master.products.values())
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
                'WNR': u'5.60',
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

        prod_container = self.parsers.slave.product_container.container
        prod_list = prod_container(self.parsers.slave.products.values())
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

    def test_do_match(self):
        self.parsers = populate_master_parsers(self.parsers, self.settings)
        self.parsers = populate_slave_parsers(self.parsers, self.settings)
        self.matches = MatchNamespace(index_fn=product_index_fn)
        self.matches = do_match(self.parsers, self.matches, self.settings)

        if self.debug:
            self.print_matches_summary(self.matches)

        self.assertEqual(len(self.matches.globals), 10)
        self.assertEqual(len(self.matches.masterless), 0)
        self.assertEqual(len(self.matches.slaveless), 5)

    def test_do_merge(self):
        self.parsers = populate_master_parsers(self.parsers, self.settings)
        self.parsers = populate_slave_parsers(self.parsers, self.settings)
        self.matches = MatchNamespace(index_fn=product_index_fn)
        self.matches = do_match(self.parsers, self.matches, self.settings)
        self.updates = UpdateNamespace()
        self.updates = do_merge(self.matches, self.parsers, self.updates, self.settings)

        if self.debug:
            self.print_updates_summary(self.updates)

        self.assertEqual(len(self.updates.delta_master), 0)
        self.assertEqual(len(self.updates.delta_slave), 1)
        self.assertEqual(len(self.updates.master), 0)
        self.assertEqual(len(self.updates.masterless), 0)
        self.assertEqual(len(self.updates.slaveless), 0)
        self.assertEqual(len(self.updates.nonstatic_slave), 0)
        self.assertEqual(len(self.updates.nonstatic_master), 0)
        self.assertEqual(len(self.updates.problematic), 0)
        self.assertEqual(len(self.updates.slave), 3)

        sync_update = self.updates.delta_slave[0]
        if self.debug:
            self.print_update(sync_update)
        try:
            self.assertEqual(sync_update.master_id, 19)
            self.assertEqual(sync_update.old_m_object.codesum, 'DevD')
            self.assertEqual(
                float(sync_update.old_m_object['WNR']),
                610.0
            )
            self.assertEqual(
                sync_update.slave_id,
                u'c27221d7-8290-4204-9f3d-0cfb7c5a3d6f'
            )
            self.assertEqual(sync_update.old_s_object.codesum, 'DevD')
            self.assertEqual(
                float(sync_update.old_s_object['WNR']),
                650.0
            )
            self.assertEqual(
                float(sync_update.new_s_object['WNR']),
                610.0
            )
        except AssertionError as exc:
            self.fail_syncupdate_assertion(exc, sync_update)

    def test_do_report(self):
        suffix='do_report'
        temp_working_dir = tempfile.mkdtemp(suffix + '_working')
        if self.debug:
            print("working dir: %s" % temp_working_dir)
        self.settings.local_work_dir = temp_working_dir
        self.settings.init_dirs()
        self.parsers = populate_master_parsers(self.parsers, self.settings)
        self.parsers = populate_slave_parsers(self.parsers, self.settings)
        self.matches = MatchNamespace(index_fn=product_index_fn)
        self.matches = do_match(self.parsers, self.matches, self.settings)
        self.updates = UpdateNamespace()
        self.updates = do_merge(self.matches, self.parsers, self.updates, self.settings)
        self.reporters = ReporterNamespace()
        self.reporters = do_report(
            self.reporters, self.matches, self.updates, self.parsers, self.settings
        )


if __name__ == '__main__':
    unittest.main()
