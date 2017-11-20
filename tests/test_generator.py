from __future__ import print_function

import os
import shutil
import tempfile
import unittest
import pytest
from pprint import pformat

from tabulate import tabulate

from context import TESTS_DATA_DIR, woogenerator
from test_sync_manager import AbstractSyncManagerTestCase
from woogenerator.coldata import ColDataMedia, ColDataProduct
from woogenerator.generator import (do_match, do_match_categories,
                                    do_match_images, do_merge, do_merge_images,
                                    do_merge_categories, do_report,
                                    populate_master_parsers,
                                    populate_slave_parsers)
from woogenerator.images import process_images
from woogenerator.matching import ProductMatcher
from woogenerator.namespace.core import MatchNamespace, UpdateNamespace
from woogenerator.namespace.prod import SettingsNamespaceProd
from woogenerator.parsing.api import ApiParseWoo
from woogenerator.parsing.special import SpecialGruopList
from woogenerator.parsing.tree import ItemList
from woogenerator.parsing.woo import CsvParseWoo, WooProdList
from woogenerator.parsing.xero import ApiParseXero
from woogenerator.utils import Registrar, SanitationUtils
from woogenerator.utils.reporter import ReporterNamespace
from .abstract import AbstractWooGeneratorTestCase



class TestGeneratorDummySpecials(AbstractSyncManagerTestCase):
    settings_namespace_class = SettingsNamespaceProd
    config_file = "generator_config_test.yaml"

    # debug = True

    def setUp(self):
        super(TestGeneratorDummySpecials, self).setUp()
        self.settings.master_dialect_suggestion = "SublimeCsvTable"
        self.settings.download_master = False
        self.settings.download_slave = False
        self.settings.master_file = os.path.join(
            TESTS_DATA_DIR, "generator_master_dummy.csv"
        )
        self.settings.specials_file = os.path.join(
            TESTS_DATA_DIR, "generator_specials_dummy.csv"
        )
        self.settings.do_specials = True
        self.settings.specials_mode = 'all_future'
        # self.settings.specials_mode = 'auto_next'
        # TODO: make this work with create special categories
        self.settings.skip_special_categories = True
        self.settings.do_sync = True
        self.settings.do_categories = True
        self.settings.do_images = True
        self.settings.do_resize_images = False
        self.settings.do_remeta_images = False
        self.settings.report_matching = True
        self.settings.schema = "CA"
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
            self.settings.slave_img_file = os.path.join(
                TESTS_DATA_DIR, "prod_slave_img_woo_api_dummy_wp-json.json"
            )
        self.settings.img_raw_dir = os.path.join(
            TESTS_DATA_DIR, 'imgs_raw'
        )
        self.settings.init_settings(self.override_args)

        # TODO: this
        if self.debug:
            # Registrar.strict = True
            # Registrar.DEBUG_ABSTRACT = True
            # Registrar.DEBUG_PARSER = True
            # Registrar.DEBUG_TREE = True
            # Registrar.DEBUG_GEN = True
            # Registrar.DEBUG_SHOP = True
            # Registrar.DEBUG_WOO = True
            # Registrar.DEBUG_TRACE = True
            # Registrar.DEBUG_UPDATE = True
            Registrar.DEBUG_ERROR = True
            Registrar.DEBUG_WARN = True
            Registrar.DEBUG_MESSAGE = True
            # Registrar.DEBUG_IMG = True
            # Registrar.DEBUG_SPECIAL = True
            # Registrar.strict = True
            ApiParseWoo.product_resolver = Registrar.exception_resolver
            CsvParseWoo.product_resolver = Registrar.exception_resolver
        else:
            Registrar.strict = False

    def populate_master_parsers(self):
        if self.parsers.master:
            return
        if self.debug:
            print("regenerating master")
        populate_master_parsers(self.parsers, self.settings)

    def populate_slave_parsers(self):
        if self.parsers.slave:
            return
        if self.debug:
            print("regenerating slave")
        populate_slave_parsers(self.parsers, self.settings)

    def test_dummy_init_settings(self):
        self.assertTrue(self.settings.do_specials)
        self.assertTrue(self.settings.do_sync)
        self.assertTrue(self.settings.do_categories)
        self.assertTrue(self.settings.do_images)
        self.assertFalse(self.settings.do_resize_images)
        self.assertFalse(self.settings.do_remeta_images)
        self.assertFalse(self.settings.download_master)
        self.assertFalse(self.settings.download_slave)
        self.assertEqual(self.settings.master_name, "gdrive-test")
        self.assertEqual(self.settings.slave_name, "woocommerce-test")
        self.assertEqual(self.settings.merge_mode, "sync")
        self.assertEqual(self.settings.specials_mode, "all_future")
        self.assertEqual(self.settings.schema, "CA")
        self.assertEqual(self.settings.download_master, False)
        self.assertEqual(
            self.settings.master_download_client_args["dialect_suggestion"],
            "SublimeCsvTable")
        self.assertEqual(self.settings.spec_gid, None)

    def test_dummy_populate_master_parsers(self):
        self.populate_master_parsers()

        #number of objects:
        self.assertEqual(len(self.parsers.master.objects.values()), 163)
        self.assertEqual(len(self.parsers.master.items.values()), 144)

        prod_container = self.parsers.master.product_container.container
        prod_list = prod_container(self.parsers.master.products.values())
        self.assertEqual(len(prod_list), 48)
        first_prod = prod_list[0]
        if self.debug:
            print("pformat@dict@first_prod:\n%s" % pformat(dict(first_prod)))
            print("first_prod.categories: %s" % pformat(first_prod.categories))
            print("first_prod.images: %s" % pformat(first_prod.images))
        self.assertEqual(first_prod.codesum, "ACARA-CAL")
        self.assertEqual(first_prod.parent.codesum, "ACARA-CA")
        first_prod_specials = first_prod.specials
        self.assertEqual(first_prod_specials,
                         ['SP2016-08-12-ACA', 'EOFY2016-ACA'])
        self.assertEqual(first_prod.images.keys(), ["ACARA-CAL.png"])
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
                # TODO: the rest of the meta keys
        }.items():
            self.assertEqual(first_prod[key], value)
        # import pudb; pudb.set_trace()
        # print("pformat:\n%s" % pformat(dict(first_prod)))
        # print("dir:")
        # print(pformat(dir(first_prod)))
        # print("vars")
        # print(pformat(vars(first_prod)))
        # for attr in ["depth"]:
        # print("first_prod.%s: %s" % (attr, pformat(getattr(first_prod, attr))))
        # print(SanitationUtils.coerce_bytes(prod_list.tabulate(tablefmt='simple')))

        self.assertEquals(
            [cat.title for cat in first_prod.categories.values()],
            [
                u'Product A',
                u'Company A Product A',
                u'Range A',
                u'1 Litre Company A Product A Items',
            ]
        )

        cat_container = self.parsers.master.category_container.container
        cat_list = cat_container(self.parsers.master.categories.values())

        if self.debug:
            print(SanitationUtils.coerce_bytes(
                cat_list.tabulate(tablefmt='simple')
            ))
        if self.settings.add_special_categories:
            self.assertEqual(len(cat_list), 11)
        else:
            self.assertEqual(len(cat_list), 9)
        first_cat = cat_list[0]
        second_cat = cat_list[1]
        if self.debug:
            print("pformat@dict@first_cat:\n%s" % pformat(dict(first_cat)))
            print("pformat@dict@second_cat:\n%s" % pformat(dict(second_cat)))
            print("first_cat.images: %s" % pformat(first_cat.images))
            print("second_cat.images: %s" % pformat(second_cat.images))

        self.assertEqual(first_cat.codesum, 'A')
        self.assertEqual(first_cat.title, 'Product A')
        self.assertEqual(first_cat.depth, 0)
        self.assertEqual(second_cat.codesum, 'ACA')
        self.assertEqual(second_cat.depth, 1)
        self.assertEqual(second_cat.parent.codesum, 'A')
        self.assertEqual(second_cat.images.keys(), ["ACA.jpg"])

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

        if self.debug:
            print("parser tree:\n%s" % self.parsers.master.to_str_tree())

    def test_dummy_populate_slave_parsers(self):
        # self.populate_master_parsers()
        self.populate_slave_parsers()
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
            print("first_prod.categories: %s" % pformat(first_prod.categories))
            print("first_prod.images: %s" % pformat(first_prod.images))

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
                'WNF': u'1465837200',
                'WNT': u'32519314800',
        }.items():
            self.assertEqual(unicode(first_prod[key]), value)

        # Remember the test data is deliberately modified to remove one of the categories
        self.assertEquals(
            first_prod.categories.keys(),
            [
                '100ml Company A Product A Samples',
                'Company A Product A',
                'Product A'
            ]
        )

        self.assertEquals(
            first_prod.images.keys(),
            [
                'ACARF-CRS.png'
            ]
        )

        cat_container = self.parsers.slave.category_container.container
        cat_list = cat_container(self.parsers.slave.categories.values())
        if self.debug:
            print(SanitationUtils.coerce_bytes(
                cat_list.tabulate(tablefmt='simple')
            ))
        self.assertEqual(len(cat_list), 9)
        first_cat = cat_list[0]
        second_cat = cat_list[1]
        if self.debug:
            print("pformat@dict@first_cat:\n%s" % pformat(dict(first_cat)))
            print("pformat@dict@second_cat:\n%s" % pformat(dict(second_cat)))
            print("first_cat.images: %s" % pformat(first_cat.images))
            print("second_cat.images: %s" % pformat(second_cat.images))

        self.assertEqual(first_cat.slug, 'product-a')
        self.assertEqual(first_cat.title, 'Product A')
        self.assertEqual(first_cat.api_id, 315)
        self.assertEqual(second_cat.images.keys(), ["ACA.jpg"])

        img_container = self.parsers.slave.image_container.container
        img_list = img_container(self.parsers.slave.images.values())
        if self.debug:
            print(SanitationUtils.coerce_bytes(
                img_list.tabulate(tablefmt='simple')
            ))

        if self.debug:
            print("parser tree:\n%s" % self.parsers.slave.to_str_tree())
            print("Registrar.stack_counts:")
            print(Registrar.display_stack_counts())

    def print_images_summary(self, images):
        img_cols = ColDataMedia.get_report_cols_gen()
        img_table = [img_cols.keys()] + [
            [img_data.get(key) for key in img_cols.keys()]
            for img_data in images
        ]
        print(tabulate(img_table))

    @unittest.skip("takes too long")
    @pytest.mark.slow
    def test_dummy_process_images_master(self):
        self.settings.do_resize_images = True
        self.settings.do_remeta_images = True
        self.settings.thumbsize_x = 1024
        self.settings.thumbsize_y = 768
        suffix='generator_dummy_process_images'
        temp_img_dir = tempfile.mkdtemp(suffix + '_img')
        if self.debug:
            print("working dir: %s" % temp_img_dir)
        self.settings.img_raw_dir = os.path.join(
            temp_img_dir, "imgs_raw"
        )
        shutil.copytree(
            os.path.join(
                TESTS_DATA_DIR, 'imgs_raw'
            ),
            self.settings.img_raw_dir
        )
        self.settings.img_cmp_dir = os.path.join(
            temp_img_dir, "imgs_cmp"
        )

        self.populate_master_parsers()
        self.populate_slave_parsers()
        process_images(self.settings, self.parsers)

        if self.debug:
            self.print_images_summary(self.parsers.master.images.values())

        # test resizing
        prod_container = self.parsers.master.product_container.container
        prod_list = prod_container(self.parsers.master.products.values())
        resized_images = 0
        for prod in prod_list:
            for img_data in prod.images.values():
                if self.settings.img_cmp_dir in img_data.get('file_path', ''):
                    resized_images += 1
                    self.assertTrue(img_data['width'] <= self.settings.thumbsize_x)
                    self.assertTrue(img_data['height'] <= self.settings.thumbsize_y)

        self.assertTrue(resized_images)

    @pytest.mark.last
    def test_dummy_images_slave(self):
        self.populate_master_parsers()
        self.populate_slave_parsers()

        if self.debug:
            self.print_images_summary(self.parsers.slave.images.values())
            for img_data in self.parsers.slave.images.values():
                print(
                    img_data.file_name,
                    [attachment.index for attachment in img_data.attachments.objects]
                )

    @pytest.mark.last
    def test_dummy_do_match_images(self):
        self.populate_master_parsers()
        self.populate_slave_parsers()
        if self.settings.do_images:
            process_images(self.settings, self.parsers)
            do_match_images(
                self.parsers, self.matches, self.settings
            )

        if self.debug:
            self.matches.image.globals.tabulate()
            self.print_matches_summary(self.matches.image)

        self.assertEqual(len(self.matches.image.globals), 45)
        first_match = self.matches.image.globals[0]
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
        for match in self.matches.image.globals:
            self.assertEqual(match.m_object.file_name, match.s_object.file_name)

    @pytest.mark.last
    def test_dummy_do_match_categories(self):
        self.populate_master_parsers()
        self.populate_slave_parsers()
        if self.settings.do_categories:
            do_match_categories(
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

    @pytest.mark.last
    def test_dummy_do_merge_images(self):
        self.settings.do_remeta_images = False
        self.settings.do_resize_images = False
        self.populate_master_parsers()
        process_images(self.settings, self.parsers)
        self.populate_slave_parsers()

        if self.settings.do_images:
            do_match_images(
                self.parsers, self.matches, self.settings
            )
            # if self.debug:
            #     import pudb; pudb.set_trace()
            do_merge_images(
                self.matches, self.parsers, self.updates, self.settings
            )

        if self.debug:
            print("img sync cols: %s" % self.settings.sync_cols_img)
            self.print_updates_summary(self.updates.image)
            for update in self.updates.image.slave:
                print(update.tabulate())
        # self.assertEqual(len(self.updates.category.master), 9)
        # sync_update = self.updates.category.master[1]
        # if self.debug:
        #     self.print_update(sync_update)
        # try:
        #     master_desc = (
        #         "Company A have developed a range of unique blends in 16 "
        #         "shades to suit all use cases. All Company A's products "
        #         "are created using the finest naturally derived botanical "
        #         "and certified organic ingredients."
        #     )
        #     self.assertEqual(
        #         sync_update.old_m_object['HTML Description'],
        #         master_desc
        #     )
        #     self.assertEqual(
        #         sync_update.old_s_object['HTML Description'],
        #         "Company A have developed stuff"
        #     )
        #     self.assertEqual(
        #         sync_update.new_s_object['HTML Description'],
        #         master_desc
        #     )
        # except AssertionError as exc:
        #     self.fail_syncupdate_assertion(exc, sync_update)

    @pytest.mark.last
    def test_dummy_do_merge_categories(self):
        self.populate_master_parsers()
        self.populate_slave_parsers()
        if self.settings.do_categories:
            do_match_categories(
                self.parsers, self.matches, self.settings
            )
            do_merge_categories(
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
                sync_update.old_m_object['descsum'],
                master_desc
            )
            self.assertEqual(
                sync_update.old_s_object['descsum'],
                "Company A have developed stuff"
            )
            self.assertEqual(
                sync_update.new_s_object['descsum'],
                master_desc
            )
        except AssertionError as exc:
            self.fail_syncupdate_assertion(exc, sync_update)

    @pytest.mark.last
    def test_dummy_do_match(self):
        self.populate_master_parsers()
        self.populate_slave_parsers()
        if self.settings.do_categories:
            do_match_categories(
                self.parsers, self.matches, self.settings
            )
            do_merge_categories(
                self.matches, self.parsers, self.updates, self.settings
            )
        do_match(self.parsers, self.matches, self.settings)

        if self.debug:
            self.matches.globals.tabulate()
            self.print_matches_summary(self.matches)

        self.assertEqual(len(self.matches.globals), 48)
        if self.debug:
            for index, matches in self.matches.category.prod.items():
                print("prod_matches: %s" % index)
                self.print_matches_summary(matches)
        prod_cat_match = self.matches.category.prod['ACARF-CRS | 24863']
        self.assertEqual(len(prod_cat_match.globals), 3)
        if self.settings.add_special_categories:
            self.assertEqual(len(prod_cat_match.slaveless), 3)
        else:
            self.assertEqual(len(prod_cat_match.slaveless), 1)

    @pytest.mark.last
    def test_dummy_do_merge_products(self):
        self.populate_master_parsers()
        self.populate_slave_parsers()
        if self.debug:
            report_cols = ColDataProduct.get_report_cols_gen('gen-api')
            report_cols['WNR'] = 'WNR'
            report_cols['WNF'] = 'WNF'
            report_cols['WNT'] = 'WNT'
            report_cols['WNS'] = 'WNS'
            report_cols['category_objects'] = 'category_objects'
            master_container = self.parsers.master.product_container.container
            master_products = master_container(self.parsers.master.products.values())
            slave_container = self.parsers.slave.product_container.container
            slave_products = slave_container(self.parsers.slave.products.values())
            print("matser_products:\n", master_products.tabulate(cols=report_cols))
            print("slave_products:\n", slave_products.tabulate(cols=report_cols))
        if self.settings.do_categories:
            do_match_categories(self.parsers, self.matches, self.settings)
            do_merge_categories(
                self.matches, self.parsers, self.updates, self.settings
            )
        do_match(self.parsers, self.matches, self.settings)
        do_merge(self.matches, self.parsers, self.updates, self.settings)

        if self.debug:
            self.print_updates_summary(self.updates)
        self.assertTrue(self.updates.slave)
        sync_update = self.updates.slave[-1]
        if self.debug:
            self.print_update(sync_update)
        self.assertEqual(len(self.updates.slave), 48)
        try:
            self.assertEquals(
                sync_update.old_m_object_core['sku'],
                "ACARF-CRS"
            )
            self.assertEquals(
                set(sync_update.old_m_object_core['category_ids']),
                set([320, 323, 315, 316])
            )
            self.assertEquals(
                set(sync_update.old_s_object_core['category_ids']),
                set([320, 315, 316])
            )
            self.assertEquals(
                set(sync_update.new_s_object_core['category_ids']),
                set([320, 323, 315, 316])
            )

        except AssertionError as exc:
            self.fail_syncupdate_assertion(exc, sync_update)



class TestGeneratorXeroDummy(AbstractSyncManagerTestCase):
    settings_namespace_class = SettingsNamespaceProd
    config_file = "generator_config_test.yaml"

    # debug = True

    def setUp(self):
        super(TestGeneratorXeroDummy, self).setUp()
        self.settings.download_master = False
        self.settings.do_categories = False
        self.settings.do_specials = False
        if self.debug:
            # self.settings.debug_shop = True
            # self.settings.debug_parser = True
            # self.settings.debug_abstract = True
            # self.settings.debug_gen = True
            # self.settings.debug_tree = True
            # self.settings.debug_update = True
            self.settings.verbosity = 3
            self.settings.quiet = False
        self.settings.init_settings(self.override_args)
        self.settings.schema = "XERO"
        self.settings.slave_name = "Xero"
        self.settings.do_sync = True
        self.settings.master_file = os.path.join(
            TESTS_DATA_DIR, "generator_master_dummy_xero.csv"
        )
        self.settings.master_dialect_suggestion = "SublimeCsvTable"
        self.settings.slave_file = os.path.join(
            TESTS_DATA_DIR, "xero_demo_data.json"
        )
        self.settings.report_matching = True
        self.matches = MatchNamespace(
            index_fn=ProductMatcher.product_index_fn
        )
        if self.debug:
            # Registrar.DEBUG_WARN = True
            # Registrar.DEBUG_MESSAGE = True
            # Registrar.DEBUG_ERROR = True
            # Registrar.DEBUG_SHOP = True
            # Registrar.DEBUG_PARSER = True
            # Registrar.DEBUG_ABSTRACT = True
            # Registrar.DEBUG_GEN = True
            # Registrar.DEBUG_TREE = True
            # Registrar.DEBUG_TRACE = True
            # ApiParseXero.DEBUG_API = True
            # Registrar.strict = True
            ApiParseXero.product_resolver = Registrar.exception_resolver
        else:
            Registrar.strict = False

    def test_xero_init_settings(self):
        self.assertFalse(self.settings.download_master)
        self.assertFalse(self.settings.do_specials)
        self.assertTrue(self.settings.do_sync)
        self.assertFalse(self.settings.do_categories)
        self.assertFalse(self.settings.do_delete_images)
        self.assertFalse(self.settings.do_dyns)
        self.assertFalse(self.settings.do_images)
        self.assertFalse(self.settings.do_mail)
        self.assertFalse(self.settings.do_post)
        self.assertFalse(self.settings.do_problematic)
        self.assertFalse(self.settings.do_remeta_images)
        self.assertFalse(self.settings.do_resize_images)
        self.assertFalse(self.settings.do_variations)
        self.assertFalse(self.settings.do_specials)
        self.assertTrue(self.settings.do_report)

    def test_xero_populate_master_parsers(self):
        if self.debug:
            # print(pformat(vars(self.settings)))
            registrar_vars = dict(vars(Registrar).items())
            print(pformat(registrar_vars.items()))
            del(registrar_vars['messages'])
            print(pformat(registrar_vars.items()))
        populate_master_parsers(self.parsers, self.settings)
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

    def test_xero_populate_slave_parsers(self):
        # self.parsers = populate_master_parsers(self.parsers, self.settings)
        populate_slave_parsers(self.parsers, self.settings)

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

    @pytest.mark.last
    def test_xero_do_match(self):
        populate_master_parsers(self.parsers, self.settings)
        populate_slave_parsers(self.parsers, self.settings)
        do_match(self.parsers, self.matches, self.settings)

        if self.debug:
            print('match summary')
            self.print_matches_summary(self.matches)

        self.assertEqual(len(self.matches.globals), 10)
        self.assertEqual(len(self.matches.masterless), 0)
        self.assertEqual(len(self.matches.slaveless), 5)

    @pytest.mark.last
    def test_xero_do_merge(self):
        populate_master_parsers(self.parsers, self.settings)
        populate_slave_parsers(self.parsers, self.settings)
        do_match(self.parsers, self.matches, self.settings)
        self.updates = UpdateNamespace()
        do_merge(self.matches, self.parsers, self.updates, self.settings)

        if self.debug:
            self.print_updates_summary(self.updates)

        if self.debug:
            for sync_update in self.updates.slave:
                self.print_update(sync_update)

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

    @pytest.mark.last
    def test_xero_do_report(self):
        suffix='geenrator_xero_do_report'
        temp_working_dir = tempfile.mkdtemp(suffix + '_working')
        if self.debug:
            print("working dir: %s" % temp_working_dir)
        self.settings.local_work_dir = temp_working_dir
        self.settings.init_dirs()
        populate_master_parsers(self.parsers, self.settings)
        populate_slave_parsers(self.parsers, self.settings)
        do_match(self.parsers, self.matches, self.settings)
        self.updates = UpdateNamespace()
        do_merge(self.matches, self.parsers, self.updates, self.settings)
        self.reporters = ReporterNamespace()
        do_report(
            self.reporters, self.matches, self.updates, self.parsers, self.settings
        )


if __name__ == '__main__':
    unittest.main()
