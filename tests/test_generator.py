from __future__ import print_function

import os
import shutil
import tempfile
import unittest
from datetime import datetime
from pprint import pformat, pprint

import mock
import pytest
import pytz
from tabulate import tabulate

from context import TESTS_DATA_DIR, woogenerator
from test_sync_manager import AbstractSyncManagerTestCase
from utils import MockUtils
from woogenerator.coldata import (ColDataAttachment, ColDataProductMeridian,
                                  ColDataWcProdCategory)
from woogenerator.generator import (do_match_categories, do_match_images,
                                    do_match_prod, do_merge_categories,
                                    do_merge_images, do_merge_prod, do_report,
                                    do_report_categories, do_report_images,
                                    do_updates_categories_master,
                                    do_updates_categories_slave,
                                    do_updates_images_master,
                                    do_updates_images_slave,
                                    export_master_parser,
                                    populate_master_parsers,
                                    populate_slave_parsers)
from woogenerator.images import process_images
from woogenerator.matching import ProductMatcher
from woogenerator.namespace.core import MatchNamespace, UpdateNamespace
from woogenerator.namespace.prod import SettingsNamespaceProd
from woogenerator.parsing.api import ApiParseWoo
from woogenerator.parsing.special import SpecialGruopList, CsvParseSpecial
from woogenerator.parsing.tree import ItemList
from woogenerator.parsing.woo import CsvParseWoo, WooProdList
from woogenerator.parsing.xero import ApiParseXero
from woogenerator.utils import FileUtils, Registrar, SanitationUtils, TimeUtils
from woogenerator.utils.reporter import ReporterNamespace

from .abstract import AbstractWooGeneratorTestCase


class TestGeneratorDummySpecials(AbstractSyncManagerTestCase):
    settings_namespace_class = SettingsNamespaceProd
    config_file = "generator_config_test.yaml"

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
        self.settings.wp_srv_offset = 7200
        self.settings.skip_special_categories = False
        self.settings.do_sync = True
        self.settings.do_categories = True
        self.settings.do_images = True
        self.settings.report_matching = True
        self.settings.auto_create_new = True
        self.settings.update_slave = False
        self.settings.do_problematic = True
        self.settings.do_report = True
        self.settings.do_remeta_images = False
        self.settings.do_resize_images = True
        self.settings.do_delete_images = False
        self.settings.schema = "CA"
        self.settings.ask_before_update = False
        self.settings.skip_unattached_images = True
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
            Registrar.DEBUG_TRACE = True
            Registrar.DEBUG_CATS = True
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

    @pytest.mark.first
    def test_dummy_init_settings(self):
        self.assertTrue(self.settings.do_specials)
        self.assertTrue(self.settings.do_sync)
        self.assertTrue(self.settings.do_categories)
        self.assertTrue(self.settings.do_images)
        self.assertTrue(self.settings.do_resize_images)
        self.assertFalse(self.settings.do_remeta_images)
        self.assertTrue(self.settings.skip_unattached_images)
        self.assertTrue(self.settings.do_problematic)
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

    @pytest.mark.first
    def test_dummy_settings_namespace(self):
        self.assertNotIn(
            'rowcount',
            self.settings.sync_handles_cat
        )

        self.settings.do_categories = False
        self.settings.do_images = True
        self.settings.do_specials = True
        self.settings.do_dyns = True
        exclude_handles = self.settings.exclude_handles

        for handle in [
            'product_categories',
            'product_category_list'
        ]:
            self.assertIn(
                handle,
                exclude_handles
            )

        self.settings.do_categories = True
        self.settings.do_images = False
        self.settings.do_specials = True
        self.settings.do_dyns = True
        exclude_handles = self.settings.exclude_handles

        for handle in ['attachment_objects']:
            self.assertIn(
                handle,
                exclude_handles
            )
        self.settings.do_categories = True
        self.settings.do_images = True
        self.settings.do_specials = False
        self.settings.do_dyns = True
        exclude_handles = self.settings.exclude_handles

        for handle in [
            'lc_dp_sale_price', 'lc_rn_sale_price_dates_to', 'lc_dn_sale_price_dates_to', 'lc_wp_sale_price_dates_from',
            'lc_wn_sale_price_dates_from', 'sale_price_dates_to_gmt', 'lc_rn_sale_price', 'sale_price_dates_from_gmt',
            'specials_schedule', 'lc_rp_sale_price_dates_from', 'sale_price_dates_from', 'lc_rp_sale_price', 'lc_wn_sale_price',
            'lc_dn_sale_price_dates_from', 'lc_rn_sale_price_dates_from', 'sale_price_dates_to', 'lc_wp_sale_price',
            'lc_wp_sale_price_dates_to', 'lc_dp_sale_price_dates_to', 'lc_dp_sale_price_dates_from', 'sale_price',
            'lc_wn_sale_price_dates_to', 'lc_rp_sale_price_dates_to', 'lc_dn_sale_price'
        ]:
            self.assertIn(
                handle,
                exclude_handles
            )

        self.settings.do_categories = True
        self.settings.do_images = True
        self.settings.do_specials = True
        self.settings.do_dyns = False
        exclude_handles = self.settings.exclude_handles

        for handle in [
            'dynamic_category_rulesets',
            'dynamic_product_rulesets'
        ]:
            self.assertIn(
                handle,
                exclude_handles
            )

    @pytest.mark.first
    def test_dummy_populate_master_parsers(self):
        self.populate_master_parsers()

        #number of objects:
        self.assertEqual(len(self.parsers.master.objects.values()), 165)
        self.assertEqual(len(self.parsers.master.items.values()), 144)

        prod_container = self.parsers.master.product_container.container
        prod_list = prod_container(self.parsers.master.products.values())
        if self.debug:
            print("%d products:" % len(prod_list))
            print(SanitationUtils.coerce_bytes(prod_list.tabulate(tablefmt='simple')))
        self.assertEqual(len(prod_list), 48)
        first_prod = prod_list[0]
        if self.debug:
            print("pformat@first_prod:\n%s" % pformat(first_prod.to_dict()))
            print("first_prod.categories: %s" % pformat(first_prod.categories))
            print("first_prod.to_dict().get('attachment_objects'): %s" % pformat(first_prod.to_dict().get('attachment_objects')))
        self.assertEqual(first_prod.codesum, "ACARA-CAL")
        self.assertEqual(first_prod.parent.codesum, "ACARA-CA")
        first_prod_specials = first_prod.specials
        self.assertEqual(first_prod_specials,
                         ['SP2016-08-12-ACA', 'EOFY2016-ACA'])
        self.assertEqual(
            set([attachment.file_name for attachment in first_prod.to_dict().get('attachment_objects')]),
            set(["ACARA-CAL.png"])
        )
        self.assertEqual(first_prod.depth, 4)
        self.assertTrue(first_prod.is_item)
        self.assertTrue(first_prod.is_product)
        self.assertFalse(first_prod.is_category)
        self.assertFalse(first_prod.is_root)
        self.assertFalse(first_prod.is_taxo)
        self.assertFalse(first_prod.is_variable)
        self.assertFalse(first_prod.is_variation)
        test_dict = {
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
            'width': u'85',
            'rowcount': 10,
            'title': u'Range A - Style 1 - 1Litre',
            'HTML Description': u'',
            'Images': u'ACARA-CAL.png',
            'CA': u'S',
            'Updated': u'',

            # TODO: the rest of the meta keys
        }
        if self.settings.do_specials:
            timezone = TimeUtils._gdrive_tz
            test_dict.update({
                'WNS': u'74.9625',
                'WNF': timezone.localize(datetime(2016, 8, 12, 0)),
                'WNT': timezone.localize(datetime(3000, 9, 1, 0, 0)),
                # 'WNF': 1470960000,
                # 'WNT': 32524675200,
            })
        for key, value in test_dict.items():
            self.assertEqual(unicode(first_prod[key]), unicode(value))

        if self.debug:
            print("pformat@to_dict@first_prod:\n%s" % pformat(first_prod.to_dict()))
            print("dir@first_prod:\n%s" % dir(first_prod))
            print("vars@first_prod:\n%s" % vars(first_prod))
            for attr in ["depth"]:
                print("first_prod.%s: %s" % (attr, pformat(getattr(first_prod, attr))))

        third_prod = prod_list[2]
        if self.debug:
            print("pformat@third_prod:\n%s" % pformat(third_prod.to_dict()))
            print("third_prod.to_dict().get('attachment_objects'): %s" % pformat(third_prod.to_dict().get('attachment_objects')))
        self.assertEqual(
            set([attachment.file_name for attachment in third_prod.to_dict().get('attachment_objects')]),
            set(["ACARA-S.png"])
        )

        sixth_prod = prod_list[5]
        if self.debug:
            print("pformat@sixth_prod:\n%s" % pformat(sixth_prod.to_dict()))
            print("sixth_prod.to_dict().get('attachment_objects'): %s" % pformat(sixth_prod.to_dict().get('attachment_objects')))

        self.assertEqual(
            set([attachment.file_name for attachment in sixth_prod.to_dict().get('attachment_objects')]),
            set(["ACARA-S.png"])
        )

        # Test the products which have the same attachment use different attachment objects
        self.assertNotEqual(
            set([id(attachment) for attachment in third_prod.to_dict().get('attachment_objects')]),
            set([id(attachment) for attachment in sixth_prod.to_dict().get('attachment_objects')])
        )


        expected_categories = set([
            u'Product A',
            u'Company A Product A',
            u'Range A',
            u'1 Litre Company A Product A Items',
        ])
        if self.settings.add_special_categories:
            expected_categories.update([
                u'Specials',
                u'Product A Specials',
            ])

        self.assertEquals(
            set([
                cat.title for cat in first_prod.categories.values()
            ]),
            expected_categories
        )

        if self.debug:
            print("parser tree:\n%s" % self.parsers.master.to_str_tree())

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
        if self.debug:
            print("pformat@first_cat:\n%s" % pformat(first_cat.to_dict()))
            print("first_cat.to_dict().get('attachment_object'): %s" % pformat(first_cat.to_dict().get('attachment_object')))

        self.assertEqual(first_cat.codesum, 'A')
        self.assertEqual(first_cat.title, 'Product A')
        self.assertEqual(first_cat.depth, 0)
        self.assertEqual(
            first_cat.to_dict().get('attachment_object'),
            None
        )

        second_cat = cat_list[1]
        if self.debug:
            print("pformat@second_cat:\n%s" % pformat(second_cat.to_dict()))
            print("second_cat.to_dict().get('attachment_object'): %s" % pformat(second_cat.to_dict().get('attachment_object')))

        self.assertEqual(second_cat.codesum, 'ACA')
        self.assertEqual(second_cat.depth, 1)
        self.assertEqual(second_cat.parent.codesum, 'A')
        self.assertEqual(
            second_cat.to_dict().get('attachment_object').file_name,
            "ACA.jpg"
        )
        second_cat_attachment_id = id(second_cat.to_dict().get('attachment_object'))

        last_cat = cat_list[-1]
        if self.debug:
            print("pformat@last_cat:\n%s" % pformat(last_cat.to_dict()))
            print("last_cat.to_dict().get('attachment_object'): %s" % pformat(last_cat.to_dict().get('attachment_object')))

        self.assertEqual(last_cat.codesum, 'SPA')
        self.assertEqual(last_cat.depth, 1)
        self.assertEqual(last_cat.parent.codesum, 'SP')
        self.assertEqual(
            last_cat.to_dict().get('attachment_object').get('file_name'),
            "ACA.jpg"
        )
        last_cat_attachment_id = id(last_cat.to_dict().get('attachment_object'))

        # This tests that categories which have the same attachment use the same attachment object

        self.assertEqual(
            second_cat_attachment_id,
            last_cat_attachment_id
        )

        prod_a_spec_cat = self.parsers.master.find_category({
            self.parsers.master.category_container.title_key: 'Product A Specials'
        })
        self.assertEqual(
            prod_a_spec_cat[self.parsers.master.category_container.codesum_key],
            'SPA'
        )

        spec_list = SpecialGruopList(self.parsers.special.rule_groups.values())
        if self.debug:
            print(SanitationUtils.coerce_bytes(
                    spec_list.tabulate(tablefmt='simple')
            ))
        first_group = spec_list[0]
        if self.debug:
            print(
                "first group:\n%s\npformat@dict:\n%s\npformat@dir:\n%s\n" %
                (
                    SanitationUtils.coerce_bytes(
                        tabulate(first_group.children, tablefmt='simple')
                    ),
                    pformat(dict(first_group)),
                    pformat(dir(first_group))
                )
            )

    def test_dummy_export_master_parsers(self):
        self.populate_master_parsers()
        export_master_parser(self.settings, self.parsers)

    @pytest.mark.first
    def test_dummy_populate_slave_parsers(self):
        # self.populate_master_parsers()
        self.populate_slave_parsers()
        if self.debug:
            print("slave objects: %s" % len(self.parsers.slave.objects.values()))
            print("slave items: %s" % len(self.parsers.slave.items.values()))
            print("slave products: %s" % len(self.parsers.slave.products.values()))
            print("slave categories: %s" % len(self.parsers.slave.categories.values()))

        if self.debug:
            print("parser tree:\n%s" % self.parsers.slave.to_str_tree())

        self.assertEqual(len(self.parsers.slave.products), 48)
        prod_container = self.parsers.slave.product_container.container
        prod_list = prod_container(self.parsers.slave.products.values())
        first_prod = prod_list[0]
        if self.debug:
            print("first_prod.dict %s" % pformat(dict(first_prod)))
            print("first_prod.categories: %s" % pformat(first_prod.categories))
            print("first_prod.to_dict().get('attachment_objects'): %s" % pformat(first_prod.to_dict().get('attachment_objects')))

        self.assertEqual(first_prod.codesum, "ACARF-CRS")
        # self.assertEqual(first_prod.parent.codesum, "ACARF-CR")

        self.assertEqual(first_prod.product_type, "simple")
        self.assertTrue(first_prod.is_item)
        self.assertTrue(first_prod.is_product)
        self.assertFalse(first_prod.is_category)
        self.assertFalse(first_prod.is_root)
        self.assertFalse(first_prod.is_taxo)
        self.assertFalse(first_prod.is_variable)
        self.assertFalse(first_prod.is_variation)
        test_dict = {
                'height': u'120',
                'length': u'40',
                'weight': u'0.12',
                'width': u'40',
                'DNR': u'8.45',
                'DPR': u'7.75',
                'WNR': u'12.95',
                'WPR': u'11.00',
        }
        if self.settings.do_specials:
            test_dict.update({
                'WNF': u'1465837200',
                'WNT': u'32519314800',
                'WNS': u'10.36',
            })
        for key, value in test_dict.items():
            self.assertEqual(unicode(first_prod[key]), unicode(value))

        # Remember the test data is deliberately modified to remove one of the categories

        self.assertEquals(
            set([
                category.title \
                for category in first_prod.categories.values()
            ]),
            set([
                '100ml Company A Product A Samples',
                'Company A Product A',
                'Product A'
            ])
        )

        self.assertEquals(
            set([
                image.file_name \
                for image in first_prod.to_dict().get('attachment_objects')
            ]),
            set([
                'ACARF-CRS.png'
            ])
        )

        cat_container = self.parsers.slave.category_container.container
        cat_list = cat_container(self.parsers.slave.categories.values())
        if self.debug:
            print(SanitationUtils.coerce_bytes(
                cat_list.tabulate(tablefmt='simple')
            ))
        self.assertEqual(len(cat_list), 9)
        first_cat = cat_list[0]
        if self.debug:
            print("pformat@first_cat:\n%s" % pformat(first_cat.to_dict()))
            print("first_cat.to_dict().get('attachment_object'): %s" % pformat(first_cat.to_dict().get('attachment_object')))

        self.assertEqual(first_cat.slug, 'product-a')
        self.assertEqual(first_cat.title, 'Product A')
        self.assertEqual(first_cat.api_id, 315)
        self.assertEqual(
            first_cat.to_dict().get('attachment_object').file_name,
            "ACA.jpg"
        )

        second_cat = cat_list[1]
        if self.debug:
            print("pformat@second_cat:\n%s" % pformat(second_cat.to_dict()))
            print("second_cat.to_dict().get('attachment_object'): %s" % pformat(second_cat.to_dict().get('attachment_object')))

        self.assertEqual(second_cat.slug, 'product-a-company-a-product-a')
        self.assertEqual(second_cat.title, 'Company A Product A')
        self.assertEqual(second_cat.api_id, 316)
        self.assertEqual(
            second_cat.to_dict().get('attachment_object').file_name,
            "ACA.jpg"
        )

        img_container = self.parsers.slave.attachment_container.container
        img_list = img_container(self.parsers.slave.attachments.values())
        if self.debug:
            print(SanitationUtils.coerce_bytes(
                img_list.tabulate(tablefmt='simple')
            ))

        # first_img = img_list[0]
        first_img = img_list.get_by_index('ACARF.jpg')

        if self.debug:
            print(SanitationUtils.coerce_bytes(
                pformat(first_img.items())
            ))

        self.assertEqual(first_img.file_name, 'ACARF.jpg')
        self.assertEqual(first_img.wpid, 24885)
        self.assertEqual(
            first_img['caption'],
            ('With the choice of four, stunning golden brown shades that '
             'develop over 6-8 hours, TechnoTan Classic Tan is the ultimate '
             'Spray on Tan.')
        )
        self.assertEqual(
            first_img['title'],
            'Solution > TechnoTan Solution > Classic Tan (6hr)'
        )

        # last_img = img_list[-1]
        last_img = img_list.get_by_index('ACARA-CAL.png')

        if self.debug:
            print(SanitationUtils.coerce_bytes(
                pformat(last_img.items())
            ))

        self.assertEqual(last_img.file_name, 'ACARA-CAL.png')
        self.assertEqual(last_img.wpid, 24772)
        self.assertEqual(last_img['title'], 'Range A - Style 1 - 1Litre 1')
        self.assertEqual(last_img['slug'], 'range-a-style-1-1litre-1')
        self.assertEqual(last_img['width'], 1200)
        self.assertEqual(last_img['height'], 1200)

    def print_images_summary(self, attachments):
        img_cols = ColDataAttachment.get_col_data_native('report')
        img_table = [img_cols.keys()] + [
            [img_data.get(key) for key in img_cols.keys()]
            for img_data in attachments
        ]
        print(tabulate(img_table))

    def setup_temp_img_dir(self):
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

    # @unittest.skip("takes too long")
    @pytest.mark.slow
    def test_dummy_process_images_master(self):
        self.setup_temp_img_dir()
        self.populate_master_parsers()
        if self.settings.do_images:
            process_images(self.settings, self.parsers)
        self.populate_slave_parsers()

        if self.debug:
            self.print_images_summary(self.parsers.master.attachments.values())

        # test resizing
        prod_container = self.parsers.master.product_container.container
        prod_list = prod_container(self.parsers.master.products.values())
        resized_images = 0
        for prod in prod_list:
            for img_data in prod.to_dict().get('attachment_objects'):
                if self.settings.img_cmp_dir in img_data.get('file_path', ''):
                    resized_images += 1
                    self.assertTrue(img_data['width'] <= self.settings.thumbsize_x)
                    self.assertTrue(img_data['height'] <= self.settings.thumbsize_y)

        self.assertTrue(resized_images)

    @pytest.mark.slow
    def test_dummy_images_slave(self):
        self.settings.do_remeta_images = False
        self.settings.do_resize_images = False
        self.populate_master_parsers()
        self.populate_slave_parsers()

        if self.debug:
            self.print_images_summary(self.parsers.slave.attachments.values())
            for img_data in self.parsers.slave.attachments.values():
                print(
                    img_data.file_name,
                    [attach.index for attach in img_data.attaches.objects]
                )

    @pytest.mark.slow
    def test_dummy_do_match_images(self):
        self.populate_master_parsers()
        self.populate_slave_parsers()
        if self.settings.do_images:
            self.setup_temp_img_dir()
            process_images(self.settings, self.parsers)
            if self.debug:
                Registrar.DEBUG_IMG = True
            do_match_images(
                self.parsers, self.matches, self.settings
            )

        if self.debug:
            # self.matches.image.globals.tabulate()
            self.print_matches_summary(self.matches.image)

        self.assertEqual(len(self.matches.image.valid), 51)
        first_match = self.matches.image.valid[0]
        first_master = first_match.m_object
        first_slave = first_match.s_object
        if self.debug:
            print('pformat@first_master:\n%s' % pformat(first_master.to_dict()))
            print('pformat@first_slave:\n%s' % pformat(first_slave.to_dict()))
            master_keys = set(dict(first_master).keys())
            slave_keys = set(dict(first_slave).keys())
            intersect_keys = master_keys.intersection(slave_keys)
            print("intersect_keys:\n")
            for key in intersect_keys:
                out = ("%20s | %50s | %50s" % (
                    SanitationUtils.coerce_ascii(key),
                    SanitationUtils.coerce_ascii(first_master[key])[:50],
                    SanitationUtils.coerce_ascii(first_slave[key])[:50]
                ))
                print(SanitationUtils.coerce_ascii(out))

        for attr, value in {
            'file_name': 'ACA.jpg',
            'title': 'Product A > Company A Product A',
        }.items():
            self.assertEqual(getattr(first_master, attr), value)
        for attr, value in {
            'file_name': 'ACA.jpg',
            'title': 'Solution > TechnoTan Solution',
            'slug': 'solution-technotan-solution',
            'api_id': 24879
        }.items():
            self.assertEqual(getattr(first_slave, attr), value)

        # last_match = self.matches.image.valid[-1]
        # last_master = last_match.m_object
        # last_slave = last_match.s_object
        # if self.debug:
        #     print('pformat@last_master:\n%s' % pformat(last_master.to_dict()))
        #     print('pformat@last_slave:\n%s' % pformat(last_slave.to_dict()))
        #     master_keys = set(dict(last_master).keys())
        #     slave_keys = set(dict(last_slave).keys())
        #     intersect_keys = master_keys.intersection(slave_keys)
        #     print("intersect_keys:\n")
        #     for key in intersect_keys:
        #         out = ("%20s | %50s | %50s" % (
        #             SanitationUtils.coerce_ascii(key),
        #             SanitationUtils.coerce_ascii(last_master[key])[:50],
        #             SanitationUtils.coerce_ascii(last_slave[key])[:50]
        #         ))
        #         print(SanitationUtils.coerce_ascii(out))
        #
        # for match in self.matches.image.valid:
        #     self.assertEqual(
        #         match.m_object.normalized_filename,
        #         match.s_object.normalized_filename
        #     )
        #
        # for attr, value in {
        #     'file_name': 'ACARB-S.jpg',
        #     'title': 'Range B - Extra Dark - 100ml Sample',
        # }.items():
        #     self.assertEqual(getattr(last_master, attr), value)
        # for attr, value in {
        #     'file_name': 'ACARB-S.jpg',
        #     'title': 'Range B - Extra Dark - 100ml Sample 1',
        #     'slug': 'range-b-extra-dark-100ml-sample-1',
        #     'api_id': 24817
        # }.items():
        #     self.assertEqual(getattr(last_slave, attr), value)


    @pytest.mark.slow
    def test_dummy_do_match_cat_img(self):
        self.setup_temp_img_dir()
        self.populate_master_parsers()
        self.populate_slave_parsers()

        if self.settings.do_images:
            process_images(self.settings, self.parsers)
            do_match_images(
                self.parsers, self.matches, self.settings
            )
            do_merge_images(
                self.matches, self.parsers, self.updates, self.settings
            )
            do_updates_images_master(
                self.updates, self.parsers, self.results, self.settings
            )
            self.do_updates_images_slave_mocked()

        if self.settings.do_categories:
            do_match_categories(
                self.parsers, self.matches, self.settings
            )

        if self.debug:
            self.matches.category.globals.tabulate()
            self.print_matches_summary(self.matches.category)

        self.assertEqual(len(self.matches.category.globals), 9)
        first_match = self.matches.category.valid[2]
        first_master = first_match.m_object
        first_slave = first_match.s_object
        if self.debug:
            print('pformat@first_master:\n%s' % pformat(first_master.to_dict()))
            print('pformat@first_slave:\n%s' % pformat(first_slave.to_dict()))
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

        last_slaveless_match = self.matches.category.slaveless[-1]
        last_slaveless_master = last_slaveless_match.m_object
        if self.debug:
            print(
                'pformat@last_slaveless_master.to_dict:\n%s' % \
                pformat(last_slaveless_master.to_dict())
            )
        # This ensures that specials categories correctly match with existing
        self.assertTrue(
            last_slaveless_master.row
        )
        self.assertEqual(
            last_slaveless_master.to_dict().get('attachment_object').file_name,
            'ACA.jpg'
        )




    @pytest.mark.slow
    def test_dummy_do_merge_images_only(self):
        """
        Assume image files are newer than example json image mod times
        """
        self.settings.do_resize_images = True
        self.settings.do_remeta_images = False
        self.setup_temp_img_dir()
        self.populate_master_parsers()
        self.populate_slave_parsers()

        if self.settings.do_images:
            process_images(self.settings, self.parsers)
            do_match_images(
                self.parsers, self.matches, self.settings
            )
            do_merge_images(
                self.matches, self.parsers, self.updates, self.settings
            )

        if self.debug:
            print("img sync handles: %s" % self.settings.sync_handles_img)
            self.print_updates_summary(self.updates.image)
            for update in self.updates.image.slave:
                print(update.tabulate())
        self.assertEqual(len(self.updates.image.slave), 51)
        self.assertEqual(len(self.updates.image.problematic), 0)
        if self.debug:
            print("slave updates:")
            for sync_update in self.updates.image.slave:
                print(sync_update.tabulate())
        # sync_update = self.updates.image.problematic[0]
        # try:
        #     if self.debug:
        #         self.print_update(sync_update)
        #     # TODO: test this?
        # except AssertionError as exc:
        #     self.fail_syncupdate_assertion(exc, sync_update)

        sync_update = self.updates.image.slave.get_by_ids("-1|ACA.jpg", 24879)
        try:
            if self.debug:
                self.print_update(sync_update)
            master_desc = (
                "Company A have developed a range of unique blends in 16 "
                "shades to suit all use cases. All Company A's products "
                "are created using the finest naturally derived botanical "
                "and certified organic ingredients."
            )
            slave_desc = (
                "TechnoTan have developed a range of unique blends in 16 "
                "shades to suit all skin types. All TechnoTan's tanning solutions "
                "are created using the finest naturally derived botanical "
                "and certified organic ingredients."
            )
            master_title = 'Product A > Company A Product A'
            slave_title = 'Solution > TechnoTan Solution'

            self.assertEqual(
                sync_update.old_m_object_core['title'],
                master_title
            )
            self.assertEqual(
                sync_update.old_s_object_core['title'],
                slave_title
            )
            self.assertEqual(
                sync_update.new_s_object_core['title'],
                master_title
            )
            self.assertEqual(
                sync_update.old_m_object_core['post_excerpt'],
                master_desc
            )
            self.assertEqual(
                SanitationUtils.normalize_unicode(sync_update.old_s_object_core['post_excerpt']),
                slave_desc
            )
            self.assertEqual(
                sync_update.new_s_object_core['post_excerpt'],
                master_desc
            )
            self.assertFalse(sync_update.old_s_object_core['alt_text'])
            self.assertEqual(
                sync_update.new_s_object_core['alt_text'],
                master_title
            )
            self.assertFalse(sync_update.old_s_object_core['post_content'])
            self.assertEqual(
                sync_update.new_s_object_core['post_content'],
                master_desc
            )
            self.assertTrue(
                sync_update.m_time
            )
            self.assertTrue(
                sync_update.s_time
            )
        except AssertionError as exc:
            self.fail_syncupdate_assertion(exc, sync_update)
        self.assertEqual(len(self.updates.image.master), 51)
        if self.debug:
            print("master updates:")
            for sync_update in self.updates.image.master:
                print(sync_update.tabulate())
        # sync_update = self.updates.image.master[0]
        sync_update = self.updates.image.master.get_by_ids("-1|ACA.jpg", 24879)
        try:
            if self.debug:
                self.print_update(sync_update)
            master_slug = ''
            slave_slug = 'solution-technotan-solution'
            self.assertEqual(
                sync_update.old_m_object_core['slug'],
                master_slug
            )
            self.assertEqual(
                sync_update.old_s_object_core['slug'],
                slave_slug
            )
            self.assertEqual(
                sync_update.new_m_object_core['slug'],
                slave_slug
            )
        except AssertionError as exc:
            self.fail_syncupdate_assertion(exc, sync_update)

        if self.debug:
            print("slaveless objects")
            for update in self.updates.image.new_slaves:
                slave_gen_object = update.old_m_object_gen
                print(slave_gen_object)

        self.assertEqual(len(self.updates.image.new_slaves), 2)
        # sync_update = self.updates.image.new_slaves[0]
        sync_update = self.updates.image.new_slaves.get_by_ids("14|ACARA-CCL.png", "")
        try:
            if self.debug:
                self.print_update(sync_update)
            slave_gen_object = sync_update.old_m_object_gen
            title = 'Range A - Style 2 - 1Litre'
            content = (
                "Company A have developed a range of unique blends in 16 shades to "
                "suit all use cases. All Company A's products are created using the "
                "finest naturally derived botanical and certified organic ingredients."
            )
            self.assertEqual(
                self.parsers.master.attachment_container.get_title(slave_gen_object),
                title
            )
            self.assertEqual(
                self.parsers.master.attachment_container.get_alt_text(slave_gen_object),
                title
            )
            self.assertEqual(
                self.parsers.master.attachment_container.get_description(slave_gen_object),
                content
            )
            self.assertEqual(
                self.parsers.master.attachment_container.get_caption(slave_gen_object),
                content
            )
            self.assertEqual(
                FileUtils.get_path_basename(
                    self.parsers.master.attachment_container.get_file_path(slave_gen_object),
                ),
                "ACARA-CCL.png"
            )
            self.assertTrue(
                sync_update.m_time
            )
        except AssertionError as exc:
            self.fail_syncupdate_assertion(exc, sync_update)

    def do_updates_images_slave_mocked(self):
        with mock.patch(
            MockUtils.get_mock_name(
                self.settings.__class__,
                'slave_img_sync_client_class'
            ),
            new_callable=mock.PropertyMock,
            return_value=self.settings.null_client_class
        ), \
        mock.patch(
            MockUtils.get_mock_name(
                self.settings.null_client_class,
                'coldata_class'
            ),
            new_callable=mock.PropertyMock,
            return_value=ColDataAttachment
        ), \
        mock.patch(
            MockUtils.get_mock_name(
                self.settings.null_client_class,
                'coldata_target'
            ),
            new_callable=mock.PropertyMock,
            return_value=self.settings.coldata_img_target
        ), \
        mock.patch(
            MockUtils.get_mock_name(
                self.settings.null_client_class,
                'coldata_target_write'
            ),
            new_callable=mock.PropertyMock,
            return_value=self.settings.coldata_img_target_write
        ), \
        mock.patch(
            MockUtils.get_mock_name(
                self.settings.null_client_class,
                'endpoint_plural'
            ),
            new_callable=mock.PropertyMock,
            return_value='media'
        ), \
        mock.patch(
            MockUtils.get_mock_name(
                self.settings.null_client_class,
                'endpoint_singular'
            ),
            new_callable=mock.PropertyMock,
            return_value='media'
        ), \
        mock.patch(
            MockUtils.get_mock_name(
                self.settings.null_client_class,
                'file_path_handle'
            ),
            new_callable=mock.PropertyMock,
            return_value='file_path'
        ), \
        mock.patch(
            MockUtils.get_mock_name(
                self.settings.null_client_class,
                'source_url_handle'
            ),
            new_callable=mock.PropertyMock,
            return_value='source_url'
        ), \
        mock.patch(
            MockUtils.get_mock_name(
                self.settings.null_client_class,
                'primary_key_handle'
            ),
            new_callable=mock.PropertyMock,
            return_value='id'
        ):
            self.settings.update_slave = True
            do_updates_images_slave(
                self.updates, self.parsers, self.results, self.settings
            )
            self.settings.update_slave = False

    @pytest.mark.slow
    def test_dummy_do_updates_images_slave(self):
        self.setup_temp_img_dir()
        self.populate_master_parsers()
        self.populate_slave_parsers()

        if self.settings.do_images:
            process_images(self.settings, self.parsers)
            do_match_images(
                self.parsers, self.matches, self.settings
            )
            do_merge_images(
                self.matches, self.parsers, self.updates, self.settings
            )
            do_updates_images_master(
                self.updates, self.parsers, self.results, self.settings
            )
            self.do_updates_images_slave_mocked()

        if self.debug:
            print('image update results: %s' % self.results.image)

        self.assertEqual(len(self.results.image.new.successes), 2)

        sync_update = self.results.image.new.successes[0]
        # sync_update = self.results.image.new.successes.get_by_ids("14|ACARA-CCL.png", 100000)
        try:
            if self.debug:
                self.print_update(sync_update)
            self.assertEqual(
                sync_update.new_s_object_core['id'],
                100000
            )
            self.assertEqual(
                sync_update.old_m_object_gen['ID'],
                100000
            )
        except AssertionError as exc:
            self.fail_syncupdate_assertion(exc, sync_update)
        sync_update = self.results.image.new.successes[-1]
        # sync_update = self.results.image.new.successes.get_by_ids("48|ACARC-CL.jpg", 100001)
        try:
            if self.debug:
                self.print_update(sync_update)
            self.assertEqual(
                sync_update.new_s_object_core['id'],
                100001
            )
            self.assertEqual(
                sync_update.old_m_object_gen['ID'],
                100001
            )
        except AssertionError as exc:
            self.fail_syncupdate_assertion(exc, sync_update)

        self.assertEqual(
            len(self.results.image.successes),
            51
        )
        sync_update = self.results.image.successes[0]
        # sync_update = self.results.image.successes.get_by_ids("-1|ACA.jpg", 100002)
        try:
            if self.debug:
                self.print_update(sync_update)
            self.assertEqual(
                sync_update.new_s_object_core['id'],
                100002
            )
            self.assertEqual(
                sync_update.old_m_object_gen['ID'],
                100002
            )
        except AssertionError as exc:
            self.fail_syncupdate_assertion(exc, sync_update)

        sync_update = self.results.image.successes[-1]
        # sync_update = self.results.image.successes.get_by_ids("41|ACARB-S.jpg", 100052)
        try:
            if self.debug:
                self.print_update(sync_update)
            self.assertEqual(
                sync_update.new_s_object_core['id'],
                100052
            )
            self.assertEqual(
                sync_update.old_m_object_gen['ID'],
                100052
            )
        except AssertionError as exc:
            self.fail_syncupdate_assertion(exc, sync_update)

    @pytest.mark.first
    def test_dummy_do_merge_categories_only(self):
        self.settings.do_images = False
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
        # sync_update = self.updates.category.master[1]
        sync_update = self.updates.category.master.get_by_ids(4, 316)
        try:
            if self.debug:
                self.print_update(sync_update)

            updates_native = sync_update.get_slave_updates_native()

            master_desc = (
                "Company A have developed a range of unique blends in 16 "
                "shades to suit all use cases. All Company A's products "
                "are created using the finest naturally derived botanical "
                "and certified organic ingredients."
            )
            slave_desc = "Company A have developed stuff"
            self.assertEqual(
                sync_update.old_m_object['descsum'],
                master_desc
            )
            self.assertEqual(
                sync_update.old_s_object['descsum'],
                slave_desc
            )
            self.assertEqual(
                sync_update.new_s_object['descsum'],
                master_desc
            )
            self.assertIn(
                ('description', master_desc),
                updates_native.items()
            )

            master_title = "Company A Product A"
            self.assertEqual(
                sync_update.old_m_object['title'],
                master_title
            )
            self.assertEqual(
                sync_update.old_s_object['title'],
                master_title
            )
            self.assertNotIn(
                'name',
                updates_native
            )
        except AssertionError as exc:
            self.fail_syncupdate_assertion(exc, sync_update)

        if self.debug:
            print("slaveless objects")
            for update in self.updates.category.new_slaves:
                slave_gen_object = update.old_m_object_gen
                print(slave_gen_object)

        self.assertEqual(
            set([
                self.parsers.slave.category_container.get_title(gen_data.old_m_object_gen)
                for gen_data in self.updates.category.new_slaves
            ]),
            set(['Specials', 'Product A Specials'])
        )

        # sync_update = self.updates.category.new_slaves[-1]
        sync_update = self.updates.category.new_slaves.get_by_ids(167, '')
        try:
            if self.debug:
                self.print_update(sync_update)
            master_title = "Product A Specials"
            master_desc = master_title
            self.assertEqual(
                sync_update.old_m_object_core['title'],
                master_title
            )
            self.assertEqual(
                sync_update.new_s_object_core['title'],
                master_title
            )
            self.assertEqual(
                sync_update.old_m_object_core['description'],
                master_desc
            )
            self.assertEqual(
                sync_update.new_s_object_core['description'],
                master_desc
            )
            self.assertEqual(
                bool(self.settings.do_images),
                'image' in sync_update.new_s_object_core,
                "images should be excluded from new slave objects if do_images disabled, contrapositive is true"
            )
        except AssertionError as exc:
            self.fail_syncupdate_assertion(exc, sync_update)

    def do_updates_categories_slave_mocked(self):
        with mock.patch(
            MockUtils.get_mock_name(
                self.settings.__class__,
                'slave_cat_sync_client_class'
            ),
            new_callable=mock.PropertyMock,
            return_value=self.settings.null_client_class
        ), \
        mock.patch(
            MockUtils.get_mock_name(
                self.settings.null_client_class,
                'coldata_class'
            ),
            new_callable=mock.PropertyMock,
            return_value=ColDataWcProdCategory
        ), \
        mock.patch(
            MockUtils.get_mock_name(
                self.settings.null_client_class,
                'coldata_target'
            ),
            new_callable=mock.PropertyMock,
            return_value=self.settings.coldata_cat_target
        ), \
        mock.patch(
            MockUtils.get_mock_name(
                self.settings.null_client_class,
                'coldata_target_write'
            ),
            new_callable=mock.PropertyMock,
            return_value=self.settings.coldata_cat_target_write
        ), \
        mock.patch(
            MockUtils.get_mock_name(
                self.settings.null_client_class,
                'endpoint_plural'
            ),
            new_callable=mock.PropertyMock,
            return_value='categories'
        ), \
        mock.patch(
            MockUtils.get_mock_name(
                self.settings.null_client_class,
                'endpoint_singular'
            ),
            new_callable=mock.PropertyMock,
            return_value='category'
        ), \
        mock.patch(
            MockUtils.get_mock_name(
                self.settings.null_client_class,
                'primary_key_handle'
            ),
            new_callable=mock.PropertyMock,
            return_value='term_id'
        ):
            self.settings.update_slave = True
            do_updates_categories_slave(
                self.updates, self.parsers, self.results, self.settings
            )
            self.settings.update_slave = False

    @pytest.mark.last
    def test_dummy_do_updates_categories_slave_only(self):
        self.settings.do_images = False
        self.populate_master_parsers()
        self.populate_slave_parsers()
        if self.settings.do_categories:
            do_match_categories(
                self.parsers, self.matches, self.settings
            )
            do_merge_categories(
                self.matches, self.parsers, self.updates, self.settings
            )
            do_updates_categories_master(
                self.updates, self.parsers, self.results, self.settings
            )
            self.do_updates_categories_slave_mocked()

        if self.debug:
            print('category update results: %s' % self.results.category)

        self.assertEqual(
            len(self.results.category.successes),
            9
        )

        self.assertEqual(
            len(self.results.category.new.successes),
            2
        )
        index_fn = self.parsers.master.category_indexer
        sync_update = self.results.category.new.successes.pop(0)
        # sync_update = self.results.category.new.successes.get_by_ids(166, 100000)
        try:
            if self.debug:
                self.print_update(sync_update)
            new_s_object_gen = sync_update.new_s_object
            if self.debug:
                pprint(new_s_object_gen.to_dict())
            self.assertEqual(
                new_s_object_gen.title,
                'Specials',
            )
            self.assertEqual(
                new_s_object_gen.wpid,
                100000
            )
            master_index = index_fn(sync_update.old_m_object)
            original_master = self.parsers.master.categories[master_index]
            self.assertEqual(
                original_master.wpid,
                100000
            )
        except AssertionError as exc:
            self.fail_syncupdate_assertion(exc, sync_update)

        sync_update = self.results.category.new.successes.pop(0)
        # sync_update = self.results.category.new.successes.get_by_ids(167, 100001)
        try:
            if self.debug:
                self.print_update(sync_update)
            new_s_object_gen = sync_update.new_s_object
            if self.debug:
                pprint(new_s_object_gen.items())
            self.assertEqual(
                new_s_object_gen.title,
                'Product A Specials',
            )
            self.assertEqual(
                new_s_object_gen.wpid,
                100001
            )
            master_index = index_fn(sync_update.old_m_object)
            original_master = self.parsers.master.categories[master_index]
            self.assertEqual(
                original_master.wpid,
                100001
            )
            self.assertEqual(
                original_master.parent.wpid,
                100000
            )
        except AssertionError as exc:
            self.fail_syncupdate_assertion(exc, sync_update)

    @pytest.mark.slow
    def test_dummy_do_merge_cat_img(self):
        self.setup_temp_img_dir()
        self.populate_master_parsers()
        self.populate_slave_parsers()

        if self.settings.do_images:
            process_images(self.settings, self.parsers)
            do_match_images(
                self.parsers, self.matches, self.settings
            )
            do_merge_images(
                self.matches, self.parsers, self.updates, self.settings
            )
            do_updates_images_master(
                self.updates, self.parsers, self.results, self.settings
            )
            self.do_updates_images_slave_mocked()

        if self.settings.do_categories:
            do_match_categories(
                self.parsers, self.matches, self.settings
            )
            do_merge_categories(
                self.matches, self.parsers, self.updates, self.settings
            )

        if self.debug:
            self.print_updates_summary(self.updates.category)

        expected_sub_img_handles = ['source_url', 'title', 'id']
        unexpected_sub_img_handles = ['modified_gmt', 'created_gmt']
        expected_sub_img_cols = ['src', 'title', 'id']
        def sync_update_cat_rudiments_test(sync_update):
            if getattr(sync_update, 'new_s_object_core') \
            and sync_update.new_s_object_core.get('image'):
                new_s_core_img = sync_update.new_s_object_core['image']
                for key in expected_sub_img_handles:
                    self.assertIn(
                        key,
                        new_s_core_img
                    )
                for key in unexpected_sub_img_handles:
                    self.assertNotIn(
                        key,
                        new_s_core_img
                    )
            if sync_update.get_slave_updates().get('image'):
                slave_updates_core_img = sync_update.get_slave_updates().get('image')
                for key in expected_sub_img_handles:
                    self.assertIn(
                        key,
                        slave_updates_core_img
                    )
                for key in unexpected_sub_img_handles:
                    self.assertNotIn(
                        key,
                        slave_updates_core_img
                    )
                slave_updates_native_img = sync_update.get_slave_updates_native().get('image')
                for key in expected_sub_img_cols:
                    self.assertIn(
                        key,
                        slave_updates_native_img
                    )

        self.assertEqual(len(self.updates.category.master), 9)

        for sync_update in self.updates.category.master:
            try:
                sync_update_cat_rudiments_test(sync_update)
            except AssertionError as exc:
                self.fail_syncupdate_assertion(exc, sync_update)

        """
update <       4 |     316 ><class 'woogenerator.syncupdate.SyncUpdateCatWoo'>
---
M:ACA|r:4|w:|Company A Product A <ImportWooCategory>
{'CA': u'',
 'CVC': u'',
 'D': u'',
 'DNR': u'',
 'DPR': u'',
 'DYNCAT': u'',
 'DYNPROD': u'',
 'E': u'',
 'HTML Description': u"Company A have developed a range of unique blends in 16 shades to suit all use cases. All Company A's products are created using the finest naturally derived botanical and certified organic ingredients.",
 'ID': '',
 'Images': u'ACA.jpg',
 'PA': u'{"pa_brand":"Company A"}',
 'RNR': u'',
 'RPR': u'',
 'SCHEDULE': u'EOFY2016-ACA',
 'Updated': u'',
 'VA': u'',
 'VISIBILITY': u'local',
 'WNR': u'',
 'WPR': u'',
 'Xero Description': u'',
 '_row': [],
 'attachment_object': -1|ACA.jpg <ImportWooImg>,
 'attachment_objects': OrderedDict([(u'-1|ACA.jpg', -1|ACA.jpg <ImportWooImg>)]),
 'backorders': 'no',
 'catalog_visibility': 'visible',
 'code': u'CA',
 'codesum': u'ACA',
 'descsum': u"Company A have developed a range of unique blends in 16 shades to suit all use cases. All Company A's products are created using the finest naturally derived botanical and certified organic ingredients.",
 'download_expiry': -1,
 'download_limit': -1,
 'featured': 'no',
 'fullname': u'Company A Product A',
 'fullnamesum': u'Product A > Company A Product A',
 'height': u'',
 'imgsum': u'ACA.jpg',
 'is_purchased': u'',
 'is_sold': u'',
 'itemsum': '',
 'length': u'',
 'modified_gmt': datetime.datetime(2017, 12, 5, 16, 56, 30, tzinfo=<UTC>),
 'modified_local': datetime.datetime(2017, 12, 6, 2, 36, 30),
 'name': u'Company A Product A',
 'post_status': u'',
 'prod_type': 'simple',
 'rowcount': 4,
 'slug': '',
 'stock': u'',
 'stock_status': u'',
 'tax_status': 'taxable',
 'taxosum': u'Product A > Company A Product A',
 'title': u'Company A Product A',
 'weight': u'',
 'width': u''}
S:r:2|a:316|Company A Product A <ImportWooApiCategory>
{'HTML Description': u'Company A have developed stuff',
 'ID': 316,
 '_row': [],
 'api_data': {u'_links': {u'collection': [{u'href': u'http://localhost:18080/wptest/wp-json/wc/v2/products/categories'}],
                          u'self': [{u'href': u'http://localhost:18080/wptest/wp-json/wc/v2/products/categories/316'}],
                          u'up': [{u'href': u'http://localhost:18080/wptest/wp-json/wc/v2/products/categories/315'}]},
              u'count': 48,
              u'description': u'Company A have developed stuff',
              u'display': u'default',
              u'id': 316,
              u'image': {u'alt': u'',
                         u'date_created': u'2017-11-08T20:55:43',
                         u'date_created_gmt': u'2017-11-08T20:55:43',
                         u'date_modified': u'2017-11-08T20:55:43',
                         u'date_modified_gmt': u'2017-11-08T20:55:43',
                         u'id': 24879,
                         u'src': u'http://localhost:18080/wptest/wp-content/uploads/2017/11/ACA.jpg',
                         u'title': u'Solution &gt; TechnoTan Solution'},
              u'menu_order': 0,
              u'name': u'Company A Product A',
              u'parent': 315,
              u'slug': u'product-a-company-a-product-a',
              u'type': u'category'},
 'attachment_object': 100002|ACA.jpg <ImportWooApiImg>,
 'attachment_objects': OrderedDict([(24879, 100002|ACA.jpg <ImportWooApiImg>)]),
 'codesum': u'product-a-company-a-product-a',
 'descsum': u'Company A have developed stuff',
 'display': u'default',
 'parent_id': 315,
 'rowcount': 2,
 'slug': u'product-a-company-a-product-a',
 'source': 'woocommerce-test',
 'title': 'Company A Product A',
 'type': 'category'}
warnings:
-
Column       Reason    Subject           Old                                                 New                                                   M TIME    S TIME  EXTRA
-----------  --------  ----------------  --------------------------------------------------  --------------------------------------------------  --------  --------  -------
description  updating  woocommerce-test  Company A have developed stuff                      Company A have developed a range of unique blends          0         0
menu_order   updating  woocommerce-test  2                                                   4                                                          0         0
image        updating  woocommerce-test  OrderedDict([('modified_gmt', datetime.datetime(20  OrderedDict([('modified_gmt', datetime.datetime(20         0         0
-
Column          Reason        Subject      Old    New                              M TIME    S TIME  EXTRA
--------------  ------------  -----------  -----  -----------------------------  --------  --------  -------
term_parent_id  merging-read  gdrive-test         315                                   0         0
term_id         merging       gdrive-test         316                                   0         0
slug            merging       gdrive-test         product-a-company-a-product-a         0         0
display         merging       gdrive-test         default                               0         0
passes:
-
Column    Reason     Master               Slave                  M TIME    S TIME  EXTRA
--------  ---------  -------------------  -------------------  --------  --------  -------
title     identical  Company A Product A  Company A Product A         0         0
probbos:

        """
        sync_update = self.updates.category.master.get_by_ids(4, 316)

        try:
            if self.debug:
                self.print_update(sync_update)
            m_attachment = sync_update.old_m_object_gen.to_dict()['attachment_object']
            self.assertEqual(
                m_attachment.get('file_name'),
                'ACA.jpg'
            )
            self.assertEqual(
                m_attachment.get('ID'),
                100002
            )
            s_attachment = sync_update.old_s_object_gen.to_dict()['attachment_object']
            self.assertEqual(
                s_attachment.get('file_name'),
                'ACA.jpg'
            )
            self.assertEqual(
                s_attachment.get('ID'),
                24879
            )
            self.assertEqual(
                sync_update.old_m_object_core['image']['id'],
                100002
            )
            self.assertEqual(
                sync_update.old_s_object_core['image']['id'],
                24879
            )
            self.assertEqual(
                sync_update.new_s_object_core['image']['id'],
                100002
            )
            if self.debug:
                print(
                    "sync warnings core img:\n%s" % \
                    pformat(sync_update.sync_warnings_core.items())
                )
                print(
                    "slave img updates native: \n%s" % \
                    pformat(sync_update.get_slave_updates_native())
                )
            self.assertTrue(
                sync_update.sync_warnings_core.get('image')
            )
            self.assertTrue(
                sync_update.get_slave_updates_native().get('image')
            )
            self.assertTrue(
                sync_update.get_slave_updates_native().get('image').get('id'),
                100002
            )

        except AssertionError as exc:
            self.fail_syncupdate_assertion(exc, sync_update)

        # TODO: this
        if self.debug:
            import pudb; pudb.set_trace()
        self.assertEqual(len(self.updates.category.slave), 9)
        for sync_update in self.updates.category.slave:
            try:
                sync_update_cat_rudiments_test(sync_update)
            except AssertionError as exc:
                self.fail_syncupdate_assertion(exc, sync_update)
        """
update <       8 |     317 >OLD
taxos                 descsum                                            title    parent_id    ID    slug
--------------------  -------------------------------------------------  -------  -----------  ----  -------------------------------------
ACARA|r:8|w:|Range A  Company A have developed a range of unique blends  Range A
r:3|a:317|Range A                                                        Range A  316          317   product-a-company-a-product-a-range-a
CHANGES (6!1)
-
Column       Reason     Subject           Old                                                 New                                                   M TIME    S TIME  EXTRA
-----------  ---------  ----------------  --------------------------------------------------  --------------------------------------------------  --------  --------  -------
description  inserting  woocommerce-test                                                      Company A have developed a range of unique blends          0         0
image        updating   woocommerce-test  {'source_url': u'http://localhost:18080/wptest/wp-  {'source_url': u'/var/folders/sx/43gc_nmj43dcwbw15         0         0
-
Column          Reason        Subject      Old    New                                      M TIME    S TIME  EXTRA
--------------  ------------  -----------  -----  -------------------------------------  --------  --------  -------
term_parent_id  merging-read  gdrive-test         316                                           0         0
term_id         merging       gdrive-test         317                                           0         0
slug            merging       gdrive-test         product-a-company-a-product-a-range-a         0         0
display         merging       gdrive-test         default                                       0         0
gdrive-test CHANGES
  ID    term_parent_id    term_id  slug                                   display
----  ----------------  ---------  -------------------------------------  ---------
   8               316        317  product-a-company-a-product-a-range-a  default
woocommerce-test CHANGES
  ID  description                                                                                                                                                                                                 image
----  ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------  -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
 317  Company A have developed a range of unique blends in 16 shades to suit all use cases. All Company A's products are created using the finest naturally derived botanical and certified organic ingredients.  OrderedDict([('src', u'/var/folders/sx/43gc_nmj43dcwbw15n3pwm440000gn/T/tmpGiIcYKgenerator_dummy_process_images_img/imgs_cmp/images-CA/ACARA.jpg'), ('id', 100003), ('title', u'Product A > Company A Product A > Range A')])
PASSES (1)
-
Column    Reason     Master    Slave      M TIME    S TIME  EXTRA
--------  ---------  --------  -------  --------  --------  -------
title     identical  Range A   Range A         0         0

NEW
taxos                              descsum                                            title      parent_id    ID  slug
---------------------------------  -------------------------------------------------  -------  -----------  ----  -------------------------------------
ACA|r:8|w:317|Company A Product A  Company A have developed a range of unique blends  Range A          316   317  product-a-company-a-product-a-range-a
r:3|a:317|Range A                  Company A have developed a range of unique blends  Range A          316   317  product-a-company-a-product-a-range-a
        """
        sync_update = self.updates.category.slave.get_by_ids(8,317)
        try:
            if self.debug:
                self.print_update(sync_update)

            m_attachment = sync_update.old_m_object_gen.to_dict()['attachment_object']
            self.assertEqual(
                m_attachment.get('file_name'),
                'ACARA.jpg'
            )
            self.assertEqual(
                m_attachment.get('ID'),
                100003
            )
            s_attachment = sync_update.old_s_object_gen.to_dict()['attachment_object']
            self.assertEqual(
                s_attachment.get('file_name'),
                'ACARA.jpg'
            )
            self.assertEqual(
                s_attachment.get('ID'),
                24880
            )

            self.assertTrue(
                sync_update.sync_warnings_core.get('image')
            )
            self.assertTrue(
                sync_update.get_slave_updates_native().get('image')
            )
            self.assertTrue(
                sync_update.get_slave_updates_native().get('image').get('id'),
                100003
            )

        except AssertionError as exc:
            self.fail_syncupdate_assertion(exc, sync_update)

        self.assertEqual(len(self.updates.category.new_slaves), 2)

        for sync_update in self.updates.category.new_slaves:
            try:
                sync_update_cat_rudiments_test(sync_update)
            except AssertionError as exc:
                self.fail_syncupdate_assertion(exc, sync_update)


        """
update <     167 |         ><class 'woogenerator.syncupdate.SyncUpdateCatWoo'>
---
M:SPA|r:167|w:|Product A Specials <ImportWooCategory>
{'CA': u'',
 'CVC': u'',
 'D': u'',
 'DNR': u'',
 'DPR': u'',
 'DYNCAT': u'',
 'DYNPROD': u'',
 'E': u'',
 'HTML Description': u'',
 'ID': '',
 'Images': u'ACA.jpg',
 'PA': u'',
 'RNR': u'',
 'RPR': u'',
 'SCHEDULE': u'',
 'Updated': u'',
 'VA': u'',
 'VISIBILITY': u'wholesale | local',
 'WNR': u'',
 'WPR': u'',
 'Xero Description': u'',
 '_row': [],
 'attachment_object': -1|ACA.jpg <ImportWooImg>,
 'backorders': 'no',
 'catalog_visibility': 'visible',
 'code': u'A',
 'codesum': u'SPA',
 'descsum': u'Product A Specials',
 'download_expiry': -1,
 'download_limit': -1,
 'featured': 'no',
 'fullname': u'Product A Specials',
 'fullnamesum': u'Specials > Product A Specials',
 'height': u'',
 'imgsum': u'ACA.jpg',
 'is_purchased': u'',
 'is_sold': u'',
 'itemsum': '',
 'length': u'',
 'modified_gmt': datetime.datetime(2017, 12, 5, 16, 56, 30, tzinfo=<UTC>),
 'modified_local': datetime.datetime(2017, 12, 6, 2, 36, 30),
 'name': u'Product A Specials',
 'post_status': u'',
 'prod_type': 'simple',
 'rowcount': 167,
 'slug': '',
 'stock': u'',
 'stock_status': u'',
 'tax_status': 'taxable',
 'taxosum': u'Specials > Product A Specials',
 'title': u'Product A Specials',
 'weight': u'',
 'width': u''}
S:{}
EMPTY
warnings:
-
Column       Reason     Subject           Old    New                                                   M TIME    S TIME  EXTRA
-----------  ---------  ----------------  -----  --------------------------------------------------  --------  --------  -------
description  inserting  woocommerce-test         Product A Specials                                         0         0
title        inserting  woocommerce-test         Product A Specials                                         0         0
menu_order   inserting  woocommerce-test         167                                                        0         0
image        inserting  woocommerce-test         OrderedDict([('modified_gmt', datetime.datetime(20         0         0
passes:
-
Column          Reason     Master    Slave      M TIME    S TIME  EXTRA
--------------  ---------  --------  -------  --------  --------  -------
term_parent_id  identical                            0         0
term_id         identical                            0         0
slug            identical                            0         0
display         identical                            0         0
probbos:

        """
        sync_update = self.updates.category.new_slaves.get_by_ids(167, '')

        try:
            if self.debug:
                self.print_update(sync_update)
            m_attachment = sync_update.old_m_object_gen.to_dict()['attachment_object']
            self.assertEqual(
                m_attachment.get('file_name'),
                'ACA.jpg'
            )
            self.assertEqual(
                m_attachment.get('ID'),
                100002
            )
        except AssertionError as exc:
            self.fail_syncupdate_assertion(exc, sync_update)

# equivalent to:
    """
python -m woogenerator.generator \
      --schema=CA --local-work-dir 'tests/sample_data' --local-test-config 'generator_config_test.yaml' \
      --skip-download-master --master-file "tests/sample_data/generator_master_dummy.csv" \
      --master-dialect-suggestion "SublimeCsvTable" \
      --download-slave --schema "CA" \
      --do-specials --specials-file 'tests/sample_data/generator_specials_dummy.csv' \
      --do-sync --update-slave --do-problematic --auto-create-new \
      --do-categories --skip-variations --skip-attributes \
      --do-images --do-resize-images --skip-delete-images --skip-remeta-images --img-raw-dir "tests/sample_data/imgs_raw" \
      --wp-srv-offset 36000 \
      -vvv --debug-trace --force-update
    """

    @pytest.mark.slow
    def test_dummy_do_match_prod_cat_img(self):
        self.setup_temp_img_dir()
        self.populate_master_parsers()
        self.populate_slave_parsers()

        if self.settings.do_images:
            process_images(self.settings, self.parsers)
            do_match_images(
                self.parsers, self.matches, self.settings
            )
            do_merge_images(
                self.matches, self.parsers, self.updates, self.settings
            )
            do_updates_images_master(
                self.updates, self.parsers, self.results, self.settings
            )
            self.do_updates_images_slave_mocked()

        if self.settings.do_categories:
            do_match_categories(
                self.parsers, self.matches, self.settings
            )
            do_merge_categories(
                self.matches, self.parsers, self.updates, self.settings
            )
            do_updates_categories_master(
                self.updates, self.parsers, self.results, self.settings
            )
            self.do_updates_categories_slave_mocked()
        do_match_prod(self.parsers, self.matches, self.settings)

        if self.debug:
            self.matches.globals.tabulate()
            self.print_matches_summary(self.matches)

        self.assertEqual(len(self.matches.globals), 48)
        if self.debug:
            for index, matches in self.matches.sub_category.items():
                print("prod_matches: %s" % index)
                self.print_matches_summary(matches)

        # TODO: more tests

    @pytest.mark.slow
    def test_dummy_do_merge_prod_cat_img(self):
        self.setup_temp_img_dir()
        self.populate_master_parsers()
        self.populate_slave_parsers()

        if self.settings.do_images:
            process_images(self.settings, self.parsers)
            do_match_images(
                self.parsers, self.matches, self.settings
            )
            do_merge_images(
                self.matches, self.parsers, self.updates, self.settings
            )
            do_updates_images_master(
                self.updates, self.parsers, self.results, self.settings
            )
            self.do_updates_images_slave_mocked()

        if self.settings.do_categories:
            do_match_categories(self.parsers, self.matches, self.settings)

            do_merge_categories(
                self.matches, self.parsers, self.updates, self.settings
            )
            do_updates_categories_master(
                self.updates, self.parsers, self.results, self.settings
            )
            self.do_updates_categories_slave_mocked()

        if self.debug:
            report_cols = ColDataProductMeridian.get_col_values_native('path', target='gen-api')
            # report_cols['WNR'] = 'WNR'
            # report_cols['WNF'] = 'WNF'
            # report_cols['WNT'] = 'WNT'
            # report_cols['WNS'] = 'WNS'
            # report_cols['category_objects'] = 'category_objects'
            master_container = self.parsers.master.product_container.container
            master_products = master_container(self.parsers.master.products.values())
            slave_container = self.parsers.slave.product_container.container
            slave_products = slave_container(self.parsers.slave.products.values())
            print("matser_products:\n", master_products.tabulate(cols=report_cols))
            print("slave_products:\n", slave_products.tabulate(cols=report_cols))

        do_match_prod(self.parsers, self.matches, self.settings)
        do_merge_prod(self.matches, self.parsers, self.updates, self.settings)


        expected_sub_img_handles = ['source_url', 'title', 'id', 'position']
        unexpected_sub_img_handles = ['modified_gmt', 'created_gmt']
        expected_sub_img_cols = ['src', 'name', 'id', 'position']
        def sync_update_prod_rudiments_test(sync_update):
            if getattr(sync_update, 'new_s_object_core') \
            and sync_update.new_s_object_core.get('attachment_objects'):
                new_s_core_imgs = sync_update.new_s_object_core['attachment_objects']
                for new_s_core_img in new_s_core_imgs:
                    for key in expected_sub_img_handles:
                        self.assertIn(
                            key,
                            new_s_core_img
                        )
                    for key in unexpected_sub_img_handles:
                        self.assertNotIn(
                            key,
                            new_s_core_img
                        )
            if sync_update.get_slave_updates().get('attachment_objects'):
                slave_updates_core_imgs = sync_update.get_slave_updates().get('attachment_objects')
                for slave_updates_core_img in slave_updates_core_imgs:
                    for key in expected_sub_img_handles:
                        self.assertIn(
                            key,
                            slave_updates_core_img
                        )
                    for key in unexpected_sub_img_handles:
                        self.assertNotIn(
                            key,
                            slave_updates_core_img
                        )
                slave_updates_native_imgs = sync_update.get_slave_updates_native().get('images')
                for slave_updates_native_img in slave_updates_native_imgs:
                    for key in expected_sub_img_cols:
                        self.assertIn(
                            key,
                            slave_updates_native_img
                        )


        if self.debug:
            self.print_updates_summary(self.updates)
        self.assertTrue(self.updates.slave)
        self.assertEqual(len(self.updates.slave), 48)

        for sync_update in self.updates.slave:
            try:
                sync_update_prod_rudiments_test(sync_update)
            except AssertionError as exc:
                self.fail_syncupdate_assertion(exc, sync_update)

        sync_update = self.updates.slave.get_by_ids(10, 24863)

        """
update <      10 |   24863 ><class 'woogenerator.syncupdate.SyncUpdateProdWoo'>
---
M:                                         ACARF-CRS ====> <ImportWooProductSimple> <ImportWooProductSimple>
{'CA': u'S',
 'CVC': u'0.20',
 'D': u'',
 'DNR': u'8.45',
 'DPR': u'7.75',
 'DYNCAT': u'',
 'DYNPROD': u'',
 'E': u'E',
 'HTML Description': u'',
 'ID': '',
 'Images': u'ACARF-CRS.png',
 'PA': u'',
 'RNR': u'',
 'RPR': u'',
 'SCHEDULE': u'',
 'Updated': u'',
 'VA': u'',
 'VISIBILITY': u'local',
 'WNF': 1465801200,
 'WNR': u'12.95',
 'WNS': 10.36,
 'WNT': 32519278800,
 'WPR': u'11.00',
 'Xero Description': u'',
 '_row': [],
 'attachment_objects': [93|ACARF-CRS.png <ImportWooImg>],
 'attribute:pa_brand': 'Company A',
 'attribute:pa_colour': 'Style 14',
 'attribute_data:pa_brand': '0|1|0',
 'attribute_data:pa_colour': '0|1|0',
 'attribute_default:pa_brand': '',
 'attribute_default:pa_colour': '',
 'backorders': 'no',
 'catalog_visibility': 'visible',
 'category_objects': [A|r:3|w:315|Product A <ImportWooCategory>,
                      ACA|r:4|w:316|Company A Product A <ImportWooCategory>,
                      ACARF|r:77|w:323|Range F <ImportWooCategory>,
                      ACAS|r:12|w:320|100ml Company A Product A Samples <ImportWooCategory>,
                      specials|r:166|w:100000|Specials <ImportWooCategory>,
                      product_a_specials|r:167|w:100001|Product A Specials <ImportWooCategory>],
 'catsum': u'Product A|Product A > Company A Product A|Product A > Company A Product A > Range F|Product A > Company A Product A > 100ml Company A Product A Samples|Specials|Specials > Product A Specials',
 'code': u'S',
 'codesum': u'ACARF-CRS',
 'descsum': u"Company A have developed a range of unique blends in 16 shades to suit all use cases. All Company A's products are created using the finest naturally derived botanical and certified organic ingredients.",
 'download_expiry': -1,
 'download_limit': -1,
 'featured': 'no',
 'fullname': u'100ml Sample',
 'fullnamesum': u'Range F - Style 14 - 100ml Sample',
 'height': u'120',
 'imgsum': u'ACARF-CRS.png',
 'is_purchased': u'',
 'is_sold': u'',
 'itemsum': u'Range F - Style 14 - 100ml Sample',
 'length': u'40',
 'modified_gmt': datetime.datetime(2017, 12, 5, 16, 56, 30, tzinfo=<UTC>),
 'modified_local': datetime.datetime(2017, 12, 6, 2, 36, 30),
 'name': u'100ml Sample',
 'post_status': u'',
 'price': u'',
 'prod_type': 'simple',
 'rowcount': 93,
 'slug': '',
 'spsum': 'EOFY2016-ACA',
 'stock': u'',
 'stock_status': 'instock',
 'tax_status': 'taxable',
 'title': u'Range F - Style 14 - 100ml Sample',
 'title_1': u'Range F',
 'title_2': u'Style 14 - 100ml Sample',
 'weight': u'0.12',
 'width': u'40'}
S:r:10|a:24863|ACARF-CRS <ImportWooApiProductSimple>
{'CVC': 0.2,
 'D': u'',
 'DNF': None,
 'DNR': '8.45',
 'DNS': '0.00',
 'DNT': None,
 'DPF': None,
 'DPR': '7.75',
 'DPS': '0.00',
 'DPT': None,
 'HTML Description': "Company A have developed a range of unique blends in 16 shades to suit all use cases. All Company A's products are created using the finest naturally derived botanical and certified organic ingredients.",
 'ID': 24863,
 'RNF': None,
 'RNR': '0.00',
 'RNS': '0.00',
 'RNT': None,
 'RPF': None,
 'RPR': '0.00',
 'RPS': '0.00',
 'RPT': None,
 'WNF': 1465837200,
 'WNR': '12.95',
 'WNS': '10.36',
 'WNT': 32519314800,
 'WPF': None,
 'WPR': '11.00',
 'WPS': '0.00',
 'WPT': None,
 '_row': [],
 'api_data': {u'_links': {u'collection': [{u'href': u'http://localhost:18080/wptest/wp-json/wc/v2/products'}],
                          u'self': [{u'href': u'http://localhost:18080/wptest/wp-json/wc/v2/products/24863'}]},
              u'attributes': [{u'id': 2,
                               u'name': None,
                               u'options': [],
                               u'position': 0,
                               u'variation': False,
                               u'visible': True},
                              {u'id': 1,
                               u'name': None,
                               u'options': [u'Company A'],
                               u'position': 0,
                               u'variation': False,
                               u'visible': True},
                              {u'id': 3,
                               u'name': None,
                               u'options': [u'Style 14'],
                               u'position': 0,
                               u'variation': False,
                               u'visible': True}],
              u'average_rating': u'0.00',
              u'backordered': False,
              u'backorders': u'no',
              u'backorders_allowed': False,
              u'button_text': u'',
              u'catalog_visibility': u'visible',
              u'categories': [{u'id': 320,
                               u'name': u'100ml Company A Product A Samples',
                               u'slug': u'product-a-company-a-product-a-100ml-company-a-product-a-samples'},
                              {u'id': 316,
                               u'name': u'Company A Product A',
                               u'slug': u'product-a-company-a-product-a'},
                              {u'id': 315,
                               u'name': u'Product A',
                               u'slug': u'product-a'}],
              u'cross_sell_ids': [],
              u'date_created': u'2017-11-08T06:50:45',
              u'date_created_gmt': u'2017-11-08T06:50:45',
              u'date_modified': u'2017-11-08T08:55:06',
              u'date_modified_gmt': u'2017-11-08T08:55:06',
              u'date_on_sale_from': None,
              u'date_on_sale_from_gmt': None,
              u'date_on_sale_to': None,
              u'date_on_sale_to_gmt': None,
              u'default_attributes': [],
              u'description': u"<p>Company A have developed a range of unique blends in 16 shades to suit all use cases. All Company A's products are created using the finest naturally derived botanical and certified organic ingredients.</p>\n",
              u'dimensions': {u'height': u'120',
                              u'length': u'40',
                              u'width': u'40'},
              u'download_expiry': -1,
              u'download_limit': -1,
              u'downloadable': False,
              u'downloads': [],
              u'external_url': u'',
              u'featured': False,
              u'grouped_products': [],
              u'id': 24863,
              u'images': [{u'alt': u'Range F - Style 14 - 100ml Sample',
                           u'date_created': u'2017-11-08T06:50:45',
                           u'date_created_gmt': u'2017-11-08T06:50:45',
                           u'date_modified': u'2017-11-08T06:50:45',
                           u'date_modified_gmt': u'2017-11-08T06:50:45',
                           u'id': 24864,
                           u'name': u'Range F &#8211; Style 14 &#8211; 100ml Sample 1',
                           u'position': 0,
                           u'src': u'http://localhost:18080/wptest/wp-content/uploads/2017/11/ACARF-CRS.png'}],
              u'in_stock': True,
              u'manage_stock': False,
              u'menu_order': 93,
              u'meta_data': [{u'id': 88322,
                              u'key': u'_upsell_skus',
                              u'value': []},
                             {u'id': 88323,
                              u'key': u'_crosssell_skus',
                              u'value': []},
                             {u'id': 88333,
                              u'key': u'_file_path',
                              u'value': u''},
                             {u'id': 88337,
                              u'key': u'_product_url',
                              u'value': u''},
                             {u'id': 88338,
                              u'key': u'_button_text',
                              u'value': u''},
                             {u'id': 93993,
                              u'key': u'_max_variation_sale_price',
                              u'value': u''},
                             {u'id': 93994,
                              u'key': u'_min_variation_sale_price',
                              u'value': u''},
                             {u'id': 93995,
                              u'key': u'_max_variation_regular_price',
                              u'value': u''},
                             {u'id': 93996,
                              u'key': u'_min_variation_regular_price',
                              u'value': u''},
                             {u'id': 93997,
                              u'key': u'_max_variation_price',
                              u'value': u''},
                             {u'id': 93998,
                              u'key': u'_min_variation_price',
                              u'value': u''},
                             {u'id': 93999,
                              u'key': u'title_1',
                              u'value': u'Range F'},
                             {u'id': 94000,
                              u'key': u'title_2',
                              u'value': u'Style 14 - 100ml Sample'},
                             {u'id': 94001,
                              u'key': u'wootan_danger',
                              u'value': u''},
                             {u'id': 94002,
                              u'key': u'lc_rn_regular_price',
                              u'value': u''},
                             {u'id': 94003,
                              u'key': u'lc_rn_sale_price',
                              u'value': u''},
                             {u'id': 94004,
                              u'key': u'lc_rn_sale_price_dates_from',
                              u'value': u''},
                             {u'id': 94005,
                              u'key': u'lc_rn_sale_price_dates_to',
                              u'value': u''},
                             {u'id': 94006,
                              u'key': u'lc_rp_regular_price',
                              u'value': u''},
                             {u'id': 94007,
                              u'key': u'lc_rp_sale_price',
                              u'value': u''},
                             {u'id': 94008,
                              u'key': u'lc_rp_sale_price_dates_from',
                              u'value': u''},
                             {u'id': 94009,
                              u'key': u'lc_rp_sale_price_dates_to',
                              u'value': u''},
                             {u'id': 94010,
                              u'key': u'lc_wn_regular_price',
                              u'value': u'12.95'},
                             {u'id': 94011,
                              u'key': u'lc_wn_sale_price',
                              u'value': u'10.36'},
                             {u'id': 94012,
                              u'key': u'lc_wn_sale_price_dates_from',
                              u'value': u'1465837200'},
                             {u'id': 94013,
                              u'key': u'lc_wn_sale_price_dates_to',
                              u'value': u'32519314800'},
                             {u'id': 94014,
                              u'key': u'lc_wp_regular_price',
                              u'value': u'11.00'},
                             {u'id': 94015,
                              u'key': u'lc_wp_sale_price',
                              u'value': u''},
                             {u'id': 94016,
                              u'key': u'lc_wp_sale_price_dates_from',
                              u'value': u''},
                             {u'id': 94017,
                              u'key': u'lc_wp_sale_price_dates_to',
                              u'value': u''},
                             {u'id': 94018,
                              u'key': u'lc_dn_regular_price',
                              u'value': u'8.45'},
                             {u'id': 94019,
                              u'key': u'lc_dn_sale_price',
                              u'value': u''},
                             {u'id': 94020,
                              u'key': u'lc_dn_sale_price_dates_from',
                              u'value': u''},
                             {u'id': 94021,
                              u'key': u'lc_dn_sale_price_dates_to',
                              u'value': u''},
                             {u'id': 94022,
                              u'key': u'lc_dp_regular_price',
                              u'value': u'7.75'},
                             {u'id': 94023,
                              u'key': u'lc_dp_sale_price',
                              u'value': u''},
                             {u'id': 94024,
                              u'key': u'lc_dp_sale_price_dates_from',
                              u'value': u''},
                             {u'id': 94025,
                              u'key': u'lc_dp_sale_price_dates_to',
                              u'value': u''},
                             {u'id': 94026,
                              u'key': u'commissionable_value',
                              u'value': u'0.20'},
                             {u'id': 94027,
                              u'key': u'last_import',
                              u'value': u''}],
              u'name': u'Range F - Style 14 - 100ml Sample',
              u'on_sale': False,
              u'parent_id': 0,
              u'permalink': u'http://localhost:18080/wptest/product/range-f-style-14-100ml-sample/',
              u'price': u'0',
              u'price_html': u'<span class="woocommerce-Price-amount amount"><span class="woocommerce-Price-currencySymbol">$</span>0.00</span>',
              u'purchasable': True,
              u'purchase_note': u'',
              u'rating_count': 0,
              u'regular_price': u'',
              u'related_ids': [24802, 24808, 24778, 24788, 24804],
              u'reviews_allowed': True,
              u'sale_price': u'',
              u'shipping_class': u'',
              u'shipping_class_id': 0,
              u'shipping_required': True,
              u'shipping_taxable': True,
              u'short_description': u'',
              u'sku': u'ACARF-CRS',
              u'slug': u'range-f-style-14-100ml-sample',
              u'sold_individually': False,
              u'status': u'publish',
              u'stock_quantity': None,
              u'tags': [],
              u'tax_class': u'',
              u'tax_status': u'taxable',
              u'total_sales': 0,
              u'type': u'simple',
              u'upsell_ids': [],
              u'variations': [],
              u'virtual': False,
              u'weight': u'0.12'},
 'attachment_objects': [24864|ACARF-CRS.png <ImportWooApiImg>],
 'attribute_objects': [OrderedDict([('title', ''), ('ID', 2)]),
                       OrderedDict([('title', ''), ('ID', 1)]),
                       OrderedDict([('title', ''), ('ID', 3)])],
 'backorders': u'no',
 'button_text': u'',
 'catalog_visibility': u'visible',
 'category_objects': [r:8|a:320|100ml Company A Product A Samples <ImportWooApiCategory>,
                      r:2|a:316|Company A Product A <ImportWooApiCategory>,
                      r:1|a:315|Product A <ImportWooApiCategory>],
 'codesum': u'ACARF-CRS',
 'created_gmt': datetime.datetime(2017, 11, 8, 6, 50, 45),
 'cross_sell_ids': [],
 'descsum': "Company A have developed a range of unique blends in 16 shades to suit all use cases. All Company A's products are created using the finest naturally derived botanical and certified organic ingredients.",
 'download_expiry': -1,
 'download_limit': -1,
 'downloadable': False,
 'external_url': u'',
 'featured': 'no',
 'height': u'120',
 'length': u'40',
 'meta': OrderedDict([(u'lc_dp_sale_price', u''), (u'_file_path', u''), (u'_crosssell_skus', []), (u'lc_dn_sale_price_dates_to', u''), (u'lc_rp_regular_price', u''), (u'lc_wp_sale_price_dates_from', u''), (u'lc_wn_sale_price_dates_from', u'1465837200'), (u'_max_variation_sale_price', u''), (u'_min_variation_sale_price', u''), (u'lc_rn_regular_price', u''), (u'lc_rn_sale_price_dates_to', u''), (u'lc_rp_sale_price', u''), (u'lc_wp_regular_price', u'11.00'), (u'_product_url', u''), (u'lc_rn_sale_price_dates_from', u''), (u'lc_wp_sale_price', u''), (u'lc_wp_sale_price_dates_to', u''), (u'lc_dp_sale_price_dates_to', u''), (u'lc_wn_sale_price_dates_to', u'32519314800'), (u'lc_dn_sale_price', u''), (u'commissionable_value', u'0.20'), (u'_upsell_skus', []), (u'lc_rn_sale_price', u''), (u'lc_rp_sale_price_dates_from', u''), (u'_max_variation_price', u''), (u'lc_wn_regular_price', u'12.95'), (u'title_1', u'Range F'), (u'title_2', u'Style 14 - 100ml Sample'), (u'_min_variation_price', u''), (u'lc_wn_sale_price', u'10.36'), (u'wootan_danger', u''), (u'lc_dn_regular_price', u'8.45'), (u'_button_text', u''), (u'lc_dp_regular_price', u'7.75'), (u'lc_dp_sale_price_dates_from', u''), (u'_min_variation_regular_price', u''), (u'_max_variation_regular_price', u''), (u'lc_rp_sale_price_dates_to', u''), (u'lc_dn_sale_price_dates_from', u''), (u'last_import', u'')]),
 'modified_gmt': datetime.datetime(2017, 11, 8, 8, 55, 6),
 'modified_local': datetime.datetime(2017, 11, 8, 8, 55, 6),
 'parent_id': 0,
 'post_status': u'publish',
 'price': '0.00',
 'prod_type': u'simple',
 'regular_price': '0.00',
 'rowcount': 10,
 'sale_price': '0.00',
 'sale_price_dates_from': None,
 'sale_price_dates_to': None,
 'slug': u'range-f-style-14-100ml-sample',
 'sold_individually': 'no',
 'source': 'woocommerce-test',
 'stock': u'',
 'stock_status': 'instock',
 'tax_status': u'taxable',
 'title': u'Range F - Style 14 - 100ml Sample',
 'type': u'simple',
 'upsell_ids': [],
 'virtual': False,
 'weight': u'0.12',
 'width': u'40'}
warnings:
-
Column            Reason        Subject      Old    New                                                 M TIME               S TIME               EXTRA
----------------  ------------  -----------  -----  --------------------------------------------------  -------------------  -------------------  -------
post_status       merging       gdrive-test         publish                                             2017-12-06 03:56:30  2017-11-08 19:55:06
slug              merging-read  gdrive-test         range-f-style-14-100ml-sample                       2017-12-06 03:56:30  2017-11-08 19:55:06
meta              merging-read  gdrive-test         {u'lc_dp_sale_price': OrderedDict([('meta_value',   2017-12-06 03:56:30  2017-11-08 19:55:06
menu_order        merging-read  gdrive-test  93     10                                                  2017-12-06 03:56:30  2017-11-08 19:55:06
regular_price     merging-read  gdrive-test         0.00                                                2017-12-06 03:56:30  2017-11-08 19:55:06
upsell_ids        merging-read  gdrive-test         []                                                  2017-12-06 03:56:30  2017-11-08 19:55:06
sale_price        merging-read  gdrive-test         0.00                                                2017-12-06 03:56:30  2017-11-08 19:55:06
cross_sell_ids    merging-read  gdrive-test         []                                                  2017-12-06 03:56:30  2017-11-08 19:55:06
attributes        merging       gdrive-test         [OrderedDict([('title', ''), ('term_id', 2)]), Ord  2017-12-06 03:56:30  2017-11-08 19:55:06
lc_rn_sale_price  merging       gdrive-test         0.00                                                2017-12-06 03:56:30  2017-11-08 19:55:06
lc_rp_sale_price  merging       gdrive-test         0.00                                                2017-12-06 03:56:30  2017-11-08 19:55:06
lc_wp_sale_price  merging       gdrive-test         0.00                                                2017-12-06 03:56:30  2017-11-08 19:55:06
lc_dn_sale_price  merging       gdrive-test         0.00                                                2017-12-06 03:56:30  2017-11-08 19:55:06
lc_dp_sale_price  merging       gdrive-test         0.00                                                2017-12-06 03:56:30  2017-11-08 19:55:06
-
Column                       Reason     Subject           Old                                                 New                                                 M TIME               S TIME               EXTRA
---------------------------  ---------  ----------------  --------------------------------------------------  --------------------------------------------------  -------------------  -------------------  -------
product_categories           updating   woocommerce-test  [{'term_id': 320}, {'term_id': 316}, {'term_id': 3  [{'term_id': 315}, {'term_id': 316}, {'term_id': 3  2017-12-06 03:56:30  2017-11-08 19:55:06
attachment_objects           updating   woocommerce-test  [{'id': 24864}]                                     [{'id': 100044}]                                    2017-12-06 03:56:30  2017-11-08 19:55:06
lc_wn_sale_price_dates_from  updating   woocommerce-test  2016-06-13 17:00:00                                 2016-06-13 07:00:00                                 2017-12-06 03:56:30  2017-11-08 19:55:06
lc_wn_sale_price_dates_to    updating   woocommerce-test  3000-06-30 23:00:00                                 3000-06-30 13:00:00                                 2017-12-06 03:56:30  2017-11-08 19:55:06
passes:
-
Column                       Reason     Master                                             Slave                                              M TIME               S TIME               EXTRA
---------------------------  ---------  -------------------------------------------------  -------------------------------------------------  -------------------  -------------------  -------
title                        identical  Range F - Style 14 - 100ml Sample                  Range F - Style 14 - 100ml Sample                  2017-12-06 03:56:30  2017-11-08 19:55:06
post_content                 identical  Company A have developed a range of unique blends  Company A have developed a range of unique blends  2017-12-06 03:56:30  2017-11-08 19:55:06
sold_individually            similar                                                       False                                              2017-12-06 03:56:30  2017-11-08 19:55:06
height                       identical  120                                                120                                                2017-12-06 03:56:30  2017-11-08 19:55:06
featured                     identical  False                                              False                                              2017-12-06 03:56:30  2017-11-08 19:55:06
sku                          identical  ACARF-CRS                                          ACARF-CRS                                          2017-12-06 03:56:30  2017-11-08 19:55:06
download_limit               identical  -1                                                 -1                                                 2017-12-06 03:56:30  2017-11-08 19:55:06
width                        identical  40                                                 40                                                 2017-12-06 03:56:30  2017-11-08 19:55:06
catalog_visibility           identical  visible                                            visible                                            2017-12-06 03:56:30  2017-11-08 19:55:06
downloadable                 similar                                                       False                                              2017-12-06 03:56:30  2017-11-08 19:55:06
download_expiry              identical  -1                                                 -1                                                 2017-12-06 03:56:30  2017-11-08 19:55:06
button_text                  identical                                                                                                        2017-12-06 03:56:30  2017-11-08 19:55:06
in_stock                     identical  True                                               True                                               2017-12-06 03:56:30  2017-11-08 19:55:06
external_url                 identical                                                                                                        2017-12-06 03:56:30  2017-11-08 19:55:06
weight                       identical  0.12                                               0.12                                               2017-12-06 03:56:30  2017-11-08 19:55:06
tax_status                   identical  taxable                                            taxable                                            2017-12-06 03:56:30  2017-11-08 19:55:06
virtual                      similar                                                       False                                              2017-12-06 03:56:30  2017-11-08 19:55:06
stock_quantity               identical                                                                                                        2017-12-06 03:56:30  2017-11-08 19:55:06
backorders                   identical  no                                                 no                                                 2017-12-06 03:56:30  2017-11-08 19:55:06
sale_price_dates_from        identical                                                                                                        2017-12-06 03:56:30  2017-11-08 19:55:06
product_type                 identical  simple                                             simple                                             2017-12-06 03:56:30  2017-11-08 19:55:06
sale_price_dates_to          identical                                                                                                        2017-12-06 03:56:30  2017-11-08 19:55:06
length                       identical  40                                                 40                                                 2017-12-06 03:56:30  2017-11-08 19:55:06
commissionable_value         identical  0.2                                                0.2                                                2017-12-06 03:56:30  2017-11-08 19:55:06
wootan_danger                identical                                                                                                        2017-12-06 03:56:30  2017-11-08 19:55:06
lc_rn_regular_price          identical  0.00                                               0.00                                               2017-12-06 03:56:30  2017-11-08 19:55:06
lc_rn_sale_price_dates_from  identical                                                                                                        2017-12-06 03:56:30  2017-11-08 19:55:06
lc_rn_sale_price_dates_to    identical                                                                                                        2017-12-06 03:56:30  2017-11-08 19:55:06
lc_rp_regular_price          identical  0.00                                               0.00                                               2017-12-06 03:56:30  2017-11-08 19:55:06
lc_rp_sale_price_dates_from  identical                                                                                                        2017-12-06 03:56:30  2017-11-08 19:55:06
lc_rp_sale_price_dates_to    identical                                                                                                        2017-12-06 03:56:30  2017-11-08 19:55:06
lc_wn_regular_price          identical  12.95                                              12.95                                              2017-12-06 03:56:30  2017-11-08 19:55:06
lc_wn_sale_price             identical  10.36                                              10.36                                              2017-12-06 03:56:30  2017-11-08 19:55:06
lc_wp_regular_price          identical  11.00                                              11.00                                              2017-12-06 03:56:30  2017-11-08 19:55:06
lc_wp_sale_price_dates_from  identical                                                                                                        2017-12-06 03:56:30  2017-11-08 19:55:06
lc_wp_sale_price_dates_to    identical                                                                                                        2017-12-06 03:56:30  2017-11-08 19:55:06
lc_dn_regular_price          identical  8.45                                               8.45                                               2017-12-06 03:56:30  2017-11-08 19:55:06
lc_dn_sale_price_dates_from  identical                                                                                                        2017-12-06 03:56:30  2017-11-08 19:55:06
lc_dn_sale_price_dates_to    identical                                                                                                        2017-12-06 03:56:30  2017-11-08 19:55:06
lc_dp_regular_price          identical  7.75                                               7.75                                               2017-12-06 03:56:30  2017-11-08 19:55:06
lc_dp_sale_price_dates_from  identical                                                                                                        2017-12-06 03:56:30  2017-11-08 19:55:06
lc_dp_sale_price_dates_to    identical                                                                                                        2017-12-06 03:56:30  2017-11-08 19:55:06
        """
        """
slave_updates_native:
[('status', u'publish'),
 ('slug', u'range-f-style-14-100ml-sample'),
 ('meta_data',
  [OrderedDict([('value', '0.00'), ('key', u'lc_dp_sale_price')]),
   OrderedDict([('value', u''), ('key', u'_file_path')]),
   OrderedDict([('value', []), ('key', u'_crosssell_skus')]),
   OrderedDict([('value', u''), ('key', u'lc_dn_sale_price_dates_to')]),
   OrderedDict([('value', u''), ('key', u'lc_rp_regular_price')]),
   OrderedDict([('value', u''), ('key', u'lc_wp_sale_price_dates_from')]),
   OrderedDict([('value', 1465801200), ('key', u'lc_wn_sale_price_dates_from')]),
   OrderedDict([('value', u''), ('key', u'_max_variation_sale_price')]),
   OrderedDict([('value', u''), ('key', u'_min_variation_sale_price')]),
   OrderedDict([('value', u''), ('key', u'lc_rn_regular_price')]),
   OrderedDict([('value', u''), ('key', u'lc_rn_sale_price_dates_to')]),
   OrderedDict([('value', '0.00'), ('key', u'lc_rp_sale_price')]),
   OrderedDict([('value', u'11.00'), ('key', u'lc_wp_regular_price')]),
   OrderedDict([('value', u''), ('key', u'_product_url')]),
   OrderedDict([('value', u''), ('key', u'lc_rn_sale_price_dates_from')]),
   OrderedDict([('value', '0.00'), ('key', u'lc_wp_sale_price')]),
   OrderedDict([('value', u''), ('key', u'lc_wp_sale_price_dates_to')]),
   OrderedDict([('value', u''), ('key', u'lc_dp_sale_price_dates_to')]),
   OrderedDict([('value', 32519278800), ('key', u'lc_wn_sale_price_dates_to')]),
   OrderedDict([('value', '0.00'), ('key', u'lc_dn_sale_price')]),
   OrderedDict([('value', u'0.20'), ('key', u'commissionable_value')]),
   OrderedDict([('value', []), ('key', u'_upsell_skus')]),
   OrderedDict([('value', '0.00'), ('key', u'lc_rn_sale_price')]),
   OrderedDict([('value', u''), ('key', u'lc_rp_sale_price_dates_from')]),
   OrderedDict([('value', u''), ('key', u'_max_variation_price')]),
   OrderedDict([('value', u'12.95'), ('key', u'lc_wn_regular_price')]),
   OrderedDict([('value', u'Range F'), ('key', u'title_1')]),
   OrderedDict([('value', u'Style 14 - 100ml Sample'), ('key', u'title_2')]),
   OrderedDict([('value', u''), ('key', u'_min_variation_price')]),
   OrderedDict([('value', u'10.36'), ('key', u'lc_wn_sale_price')]),
   OrderedDict([('value', u''), ('key', u'wootan_danger')]),
   OrderedDict([('value', u'8.45'), ('key', u'lc_dn_regular_price')]),
   OrderedDict([('value', u''), ('key', u'_button_text')]),
   OrderedDict([('value', u'7.75'), ('key', u'lc_dp_regular_price')]),
   OrderedDict([('value', u''), ('key', u'lc_dp_sale_price_dates_from')]),
   OrderedDict([('value', u''), ('key', u'_min_variation_regular_price')]),
   OrderedDict([('value', u''), ('key', u'_max_variation_regular_price')]),
   OrderedDict([('value', u''), ('key', u'lc_rp_sale_price_dates_to')]),
   OrderedDict([('value', u''), ('key', u'lc_dn_sale_price_dates_from')]),
   OrderedDict([('value', u''), ('key', u'last_import')])]),
 ('menu_order', 10),
 ('regular_price', '0.00'),
 ('categories',
  [OrderedDict([('id', 315)]),
   OrderedDict([('id', 316)]),
   OrderedDict([('id', 323)]),
   OrderedDict([('id', 320)]),
   OrderedDict([('id', 100000)]),
   OrderedDict([('id', 100001)])]),
 ('upsell_ids', u'[]'),
 ('images', [OrderedDict([('id', 100044)])]),
 ('sale_price', '0.00'),
 ('cross_sell_ids', u'[]'),
 ('attributes',
  [OrderedDict([('name', ''), ('id', 2)]),
   OrderedDict([('name', ''), ('id', 1)]),
   OrderedDict([('name', ''), ('id', 3)])])]
slave_updates_core:
[('post_status', u'publish'),
 ('slug', u'range-f-style-14-100ml-sample'),
 ('meta',
  {u'_button_text': OrderedDict([('meta_value', u''), ('meta_key', u'_button_text')]),
   u'_crosssell_skus': OrderedDict([('meta_value', []), ('meta_key', u'_crosssell_skus')]),
   u'_file_path': OrderedDict([('meta_value', u''), ('meta_key', u'_file_path')]),
   u'_max_variation_price': OrderedDict([('meta_value', u''), ('meta_key', u'_max_variation_price')]),
   u'_max_variation_regular_price': OrderedDict([('meta_value', u''), ('meta_key', u'_max_variation_regular_price')]),
   u'_max_variation_sale_price': OrderedDict([('meta_value', u''), ('meta_key', u'_max_variation_sale_price')]),
   u'_min_variation_price': OrderedDict([('meta_value', u''), ('meta_key', u'_min_variation_price')]),
   u'_min_variation_regular_price': OrderedDict([('meta_value', u''), ('meta_key', u'_min_variation_regular_price')]),
   u'_min_variation_sale_price': OrderedDict([('meta_value', u''), ('meta_key', u'_min_variation_sale_price')]),
   u'_product_url': OrderedDict([('meta_value', u''), ('meta_key', u'_product_url')]),
   u'_upsell_skus': OrderedDict([('meta_value', []), ('meta_key', u'_upsell_skus')]),
   u'commissionable_value': OrderedDict([('meta_value', u'0.20'), ('meta_key', u'commissionable_value')]),
   u'last_import': OrderedDict([('meta_value', u''), ('meta_key', u'last_import')]),
   u'lc_dn_regular_price': OrderedDict([('meta_value', u'8.45'), ('meta_key', u'lc_dn_regular_price')]),
   u'lc_dn_sale_price': OrderedDict([('meta_value', u''), ('meta_key', u'lc_dn_sale_price')]),
   u'lc_dn_sale_price_dates_from': OrderedDict([('meta_value', u''), ('meta_key', u'lc_dn_sale_price_dates_from')]),
   u'lc_dn_sale_price_dates_to': OrderedDict([('meta_value', u''), ('meta_key', u'lc_dn_sale_price_dates_to')]),
   u'lc_dp_regular_price': OrderedDict([('meta_value', u'7.75'), ('meta_key', u'lc_dp_regular_price')]),
   u'lc_dp_sale_price': OrderedDict([('meta_value', u''), ('meta_key', u'lc_dp_sale_price')]),
   u'lc_dp_sale_price_dates_from': OrderedDict([('meta_value', u''), ('meta_key', u'lc_dp_sale_price_dates_from')]),
   u'lc_dp_sale_price_dates_to': OrderedDict([('meta_value', u''), ('meta_key', u'lc_dp_sale_price_dates_to')]),
   u'lc_rn_regular_price': OrderedDict([('meta_value', u''), ('meta_key', u'lc_rn_regular_price')]),
   u'lc_rn_sale_price': OrderedDict([('meta_value', u''), ('meta_key', u'lc_rn_sale_price')]),
   u'lc_rn_sale_price_dates_from': OrderedDict([('meta_value', u''), ('meta_key', u'lc_rn_sale_price_dates_from')]),
   u'lc_rn_sale_price_dates_to': OrderedDict([('meta_value', u''), ('meta_key', u'lc_rn_sale_price_dates_to')]),
   u'lc_rp_regular_price': OrderedDict([('meta_value', u''), ('meta_key', u'lc_rp_regular_price')]),
   u'lc_rp_sale_price': OrderedDict([('meta_value', u''), ('meta_key', u'lc_rp_sale_price')]),
   u'lc_rp_sale_price_dates_from': OrderedDict([('meta_value', u''), ('meta_key', u'lc_rp_sale_price_dates_from')]),
   u'lc_rp_sale_price_dates_to': OrderedDict([('meta_value', u''), ('meta_key', u'lc_rp_sale_price_dates_to')]),
   u'lc_wn_regular_price': OrderedDict([('meta_value', u'12.95'), ('meta_key', u'lc_wn_regular_price')]),
   u'lc_wn_sale_price': OrderedDict([('meta_value', u'10.36'), ('meta_key', u'lc_wn_sale_price')]),
   u'lc_wn_sale_price_dates_from': OrderedDict([('meta_value', u'1465837200'), ('meta_key', u'lc_wn_sale_price_dates_from')]),
   u'lc_wn_sale_price_dates_to': OrderedDict([('meta_value', u'32519314800'), ('meta_key', u'lc_wn_sale_price_dates_to')]),
   u'lc_wp_regular_price': OrderedDict([('meta_value', u'11.00'), ('meta_key', u'lc_wp_regular_price')]),
   u'lc_wp_sale_price': OrderedDict([('meta_value', u''), ('meta_key', u'lc_wp_sale_price')]),
   u'lc_wp_sale_price_dates_from': OrderedDict([('meta_value', u''), ('meta_key', u'lc_wp_sale_price_dates_from')]),
   u'lc_wp_sale_price_dates_to': OrderedDict([('meta_value', u''), ('meta_key', u'lc_wp_sale_price_dates_to')]),
   u'title_1': OrderedDict([('meta_value', u'Range F'), ('meta_key', u'title_1')]),
   u'title_2': OrderedDict([('meta_value', u'Style 14 - 100ml Sample'), ('meta_key', u'title_2')]),
   u'wootan_danger': OrderedDict([('meta_value', u''), ('meta_key', u'wootan_danger')])}),
 ('menu_order', 10),
 ('regular_price', '0.00'),
 ('product_categories',
  [{'term_id': 315},
   {'term_id': 316},
   {'term_id': 323},
   {'term_id': 320},
   {'term_id': 100000},
   {'term_id': 100001}]),
 ('upsell_ids', u'[]'),
 ('attachment_objects', [{'id': 100044}]),
 ('sale_price', '0.00'),
 ('cross_sell_ids', u'[]'),
 ('attributes',
  [OrderedDict([('title', ''), ('term_id', 2)]),
   OrderedDict([('title', ''), ('term_id', 1)]),
   OrderedDict([('title', ''), ('term_id', 3)])]),
 ('lc_rn_sale_price', '0.00'),
 ('lc_rp_sale_price', '0.00'),
 ('lc_wn_sale_price_dates_from', datetime.datetime(2016, 6, 13, 7, 0)),
 ('lc_wn_sale_price_dates_to', datetime.datetime(3000, 6, 30, 13, 0)),
 ('lc_wp_sale_price', '0.00'),
 ('lc_dn_sale_price', '0.00'),
 ('lc_dp_sale_price', '0.00')]
        """

        try:
            if self.debug:
                self.print_update(sync_update)
            expected_sku = "ACARF-CRS"

            self.assertEquals(
                sync_update.old_m_object_core['sku'],
                expected_sku
            )
            self.assertEquals(
                sync_update.old_s_object_core['sku'],
                expected_sku
            )
            self.assertEquals(
                sync_update.new_s_object_core['sku'],
                expected_sku
            )

            if self.settings.do_categories:
                expected_master_categories = set([320, 323, 315, 316])
                if not self.settings.skip_special_categories:
                    expected_master_categories.update([100000, 100001])
                expected_slave_categories = set([320, 315, 316])

                old_m_core_cat_ids = [
                    cat.get('term_id') for cat in \
                    sync_update.old_m_object_core['product_categories']
                ]
                self.assertEquals(
                    set(old_m_core_cat_ids),
                    expected_master_categories
                )
                old_s_core_cat_ids = [
                    cat.get('term_id') for cat in \
                    sync_update.old_s_object_core['product_categories']
                ]
                self.assertEquals(
                    set(old_s_core_cat_ids),
                    expected_slave_categories
                )
                new_s_core_cat_ids = [
                    cat.get('term_id') for cat in \
                    sync_update.new_s_object_core['product_categories']
                ]
                self.assertEquals(
                    set(new_s_core_cat_ids),
                    expected_master_categories
                )

            if self.settings.do_images:
                expected_master_images = set([100044])
                expected_slave_images = set([24864])

                old_m_core_img_ids = [
                    img.get('id') for img in \
                    sync_update.old_m_object_core['attachment_objects']
                ]
                self.assertEqual(
                    set(old_m_core_img_ids),
                    expected_master_images
                )
                old_s_core_img_ids = [
                    img.get('id') for img in \
                    sync_update.old_s_object_core['attachment_objects']
                ]
                self.assertEqual(
                    set(old_s_core_img_ids),
                    expected_slave_images
                )
                new_s_core_img_ids = [
                    img.get('id') for img in \
                    sync_update.new_s_object_core['attachment_objects']
                ]
                self.assertEqual(
                    set(new_s_core_img_ids),
                    expected_master_images
                )

            # TODO: test exact contents of get_slave_updates_native()
            # Specifically make sure that sale_price_dates_(to|from) are not datetime

            slave_updates_core = sync_update.get_slave_updates()
            slave_updates_native = sync_update.get_slave_updates_native()
            if self.debug:
                print("slave_updates_native:\n%s" % pformat(slave_updates_native.items()))
                print("slave_updates_core:\n%s" % pformat(slave_updates_core.items()))

            expected_dict = {
                # 'lc_wn_sale_price_dates_from': datetime(
                #     2016, 6, 13, 7, 0, 0, tzinfo=pytz.utc
                # ),
                'lc_wn_sale_price_dates_to': TimeUtils._gdrive_tz.localize(datetime(
                    3000, 7, 1, 0, 0, 0
                ))
            }
            for key, value in expected_dict.items():
                expected_value = value
                actual_value = slave_updates_core[key]
                if isinstance(actual_value, dict):
                    actual_value = set(actual_value.items())
                    expected_value = set(expected_value.items())
                elif isinstance(actual_value, list):
                    actual_value = set([
                        unicode(item) for item in actual_value
                    ])
                    expected_value = set([
                        unicode(item) for item in expected_value
                    ])
                else:
                    actual_value = unicode(actual_value)
                    expected_value = unicode(expected_value)

                self.assertEquals(
                    actual_value,
                    expected_value
                )
            expected_categories = set([315, 316, 323, 320, 100000, 100001])
            actual_categories = set([
                cat.get('term_id') for cat in slave_updates_core['product_categories']
            ])
            self.assertEqual(
                expected_categories,
                actual_categories
            )
            expected_attachments = set([100044])
            actual_attachments = set([
                img.get('id') for img in slave_updates_core['attachment_objects']
            ])
            self.assertEqual(
                expected_attachments,
                actual_attachments
            )

            for meta_object in slave_updates_native['meta_data']:
                if meta_object['key'] == 'lc_wn_sale_price_dates_to':
                    self.assertEqual(
                        meta_object['value'],
                        32519318400
                    )
        except AssertionError as exc:
            self.fail_syncupdate_assertion(exc, sync_update)

    @pytest.mark.slow
    def test_reporting_imgs_only(self):
        self.setup_temp_img_dir()
        self.populate_master_parsers()
        self.populate_slave_parsers()

        if self.settings.do_images:
            process_images(self.settings, self.parsers)
            do_match_images(
                self.parsers, self.matches, self.settings
            )
            do_merge_images(
                self.matches, self.parsers, self.updates, self.settings
            )
            do_report_images(
                self.reporters, self.matches, self.updates, self.parsers, self.settings
            )

        self.assertTrue(
            self.reporters.img
        )

        if self.debug:
            print(
                "img pre-sync summary: \n%s" % \
                self.reporters.img.get_summary_text()
            )

    def test_reporting_cat_only(self):
        self.settings.do_images = False
        self.populate_master_parsers()
        self.populate_slave_parsers()
        if self.settings.do_categories:
            do_match_categories(
                self.parsers, self.matches, self.settings
            )
            do_merge_categories(
                self.matches, self.parsers, self.updates, self.settings
            )
            do_report_categories(
                self.reporters, self.matches, self.updates, self.parsers, self.settings
            )

        self.assertTrue(
            self.reporters.cat
        )

        if self.debug:
            print(
                "cat pre-sync summary: \n%s" % \
                self.reporters.cat.get_summary_text()
            )

    @pytest.mark.slow
    def test_reporting_cat_img(self):
        self.setup_temp_img_dir()
        self.populate_master_parsers()
        self.populate_slave_parsers()

        if self.settings.do_images:
            process_images(self.settings, self.parsers)
            do_match_images(
                self.parsers, self.matches, self.settings
            )
            do_merge_images(
                self.matches, self.parsers, self.updates, self.settings
            )
            do_updates_images_master(
                self.updates, self.parsers, self.results, self.settings
            )
            self.do_updates_images_slave_mocked()

        if self.settings.do_categories:
            do_match_categories(
                self.parsers, self.matches, self.settings
            )
            do_merge_categories(
                self.matches, self.parsers, self.updates, self.settings
            )
            do_report_categories(
                self.reporters, self.matches, self.updates, self.parsers, self.settings
            )

        self.assertTrue(
            self.reporters.cat
        )

        if self.debug:
            print(
                "cat pre-sync summary: \n%s" % \
                self.reporters.cat.get_summary_text()
            )

class TestGeneratorSuperDummy(AbstractSyncManagerTestCase):
    """
    Stuff missing from original dummy:
     - variations
     - attributes
     - collapsable categories (e.g. Product A > Company A Product A => Company A Product A)
    """
    settings_namespace_class = SettingsNamespaceProd
    config_file = "generator_config_test.yaml"

    def setUp(self):
        super(TestGeneratorSuperDummy, self).setUp()
        self.settings.master_dialect_suggestion = "SublimeCsvTable"
        self.settings.download_master = False
        self.settings.master_file = os.path.join(
            TESTS_DATA_DIR, "generator_master_super_dummy.csv"
        )
        self.settings.master_and_quit = True
        self.settings.do_specials = False
        self.settings.do_categories = True
        self.settings.do_images = True
        self.settings.report_matching = True
        self.settings.auto_create_new = True
        self.settings.update_slave = False
        self.settings.do_problematic = True
        self.settings.do_report = True
        self.settings.do_remeta_images = False
        self.settings.do_resize_images = True
        self.settings.do_delete_images = False
        self.settings.schema = "CA"
        self.settings.skip_unattached_images = True
        self.settings.init_settings(self.override_args)

    def populate_master_parsers(self):
        if self.parsers.master:
            return
        if self.debug:
            print("regenerating master")
        populate_master_parsers(self.parsers, self.settings)

    @pytest.mark.first
    def test_super_dummy_populate_master_parsers(self):
        self.populate_master_parsers()

        prod_container = self.parsers.master.product_container.container
        prod_list = prod_container(self.parsers.master.products.values())
        if self.debug:
            print(
                (
                    "%d objects\n"
                    "%d items\n"
                    "%d products:\n"
                ) % (
                    len(self.parsers.master.objects.values()),
                    len(self.parsers.master.items.values()),
                    len(prod_list)
                )
            )
            print(SanitationUtils.coerce_bytes(prod_list.tabulate(tablefmt='simple')))

        self.assertEqual(len(self.parsers.master.objects.values()), 8)
        self.assertEqual(len(self.parsers.master.items.values()), 5)
        self.assertEqual(len(prod_list), 1)

        first_prod = prod_list[0]
        if self.debug:
            print("pformat@first_prod:\n%s" % pformat(first_prod.to_dict()))
            print("first_prod.categories: %s" % pformat(first_prod.categories))
            print("first_prod.to_dict().get('attachment_objects'): %s" % pformat(first_prod.to_dict().get('attachment_objects')))
        self.assertEqual(first_prod.codesum, "AGL-CP5")
        self.assertEqual(first_prod.parent.codesum, "AGL")
        self.assertEqual(
            set([attachment.file_name for attachment in first_prod.to_dict().get('attachment_objects')]),
            set(["AGL-CP5.png"])
        )
        self.assertEqual(first_prod.depth, 3)
        self.assertTrue(first_prod.is_item)
        self.assertTrue(first_prod.is_product)
        self.assertFalse(first_prod.is_category)
        self.assertFalse(first_prod.is_root)
        self.assertFalse(first_prod.is_taxo)
        self.assertTrue(first_prod.is_variable)
        self.assertFalse(first_prod.is_variation)

        test_dict = {
            'attribute:pa_material': 'Cotton',
            'attribute:quantity': '5',
            'attribute:size': 'Small|Medium|Large|XLarge',
            'attribute_data:pa_material': '0|1|0',
            'attribute_data:quantity': '0|1|0',
            'attribute_data:size': '0|1|1',
            'attribute_default:pa_material': '',
            'attribute_default:quantity': '',
            'attribute_default:size': u'Small',
            'title': u'Cotton Glove Pack x5 Pairs',
            'CA': u'V',
        }

        for key, value in test_dict.items():
            self.assertEqual(unicode(first_prod[key]), unicode(value))

        self.assertEqual(
            set([variation.codesum for variation in first_prod.variations.values()]),
            set([
                "AGL-CP5S",
                "AGL-CP5M",
                "AGL-CP5L",
                "AGL-CP5XL",
            ])
        )

        first_variation = first_prod.variations.values()[0]

        test_dict = {
            'DNR': u'3.85',
            'DPR': u'3.85',
            'RNR': u'',
            'RPR': u'',
            'WNR': u'5.50',
            'WPR': u'4.95',
            'height': u'25',
            'length': u'100',
            'width': u'250',
            'weight': u'0.10',
            'attribute:pa_material': 'Cotton',
            'attribute:quantity': '5',
            'attribute:size': 'Small',
            'meta:attribute_size': 'Small',
            'CA': u'I',
        }

        for key, value in test_dict.items():
            self.assertEqual(unicode(first_variation[key]), unicode(value))

    def test_super_dummy_to_target_type(self):
        """
        test the to_target_type functionality of master objects.
        """

        self.populate_master_parsers()

        prod_container = self.parsers.master.product_container.container
        prod_list = prod_container(self.parsers.master.products.values())

        first_prod = prod_list[0]
        first_variation = first_prod.variations.values()[0]
        coldata_target = 'wc-csv'
        coldata_class = ColDataProductMeridian


        first_prod_csv = first_prod.to_target_type_with_attributes(
            coldata_class=coldata_class,
            coldata_target=coldata_target
        )

        test_dict = {
            'attribute:pa_material': 'Cotton',
            'attribute:quantity': '5',
            'attribute:size': 'Small|Medium|Large|XLarge',
            'attribute_data:pa_material': '0|1|0',
            'attribute_data:quantity': '0|1|0',
            'attribute_data:size': '0|1|1',
            'attribute_default:pa_material': '',
            'attribute_default:quantity': '',
            'attribute_default:size': u'Small',
            'post_title': u'Cotton Glove Pack x5 Pairs',
        }

        for key, value in test_dict.items():
            self.assertEqual(unicode(first_prod_csv[key]), unicode(value))

        first_variation_csv = first_variation.to_target_type_with_attributes(
            coldata_class=coldata_class,
            coldata_target=coldata_target
        )

        test_dict = {
            'meta:lc_dn_regular_price': u'3.85',
            'meta:lc_dp_regular_price': u'3.85',
            'meta:lc_rn_regular_price': u'',
            'meta:lc_rp_regular_price': u'',
            'meta:lc_wn_regular_price': u'5.50',
            'meta:lc_wp_regular_price': u'4.95',
            'height': u'25',
            'length': u'100',
            'width': u'250',
            'weight': u'0.10',
            'attribute:pa_material': 'Cotton',
            'attribute:quantity': '5',
            'attribute:size': 'Small',
        }

        for key, value in test_dict.items():
            self.assertEqual(unicode(first_variation_csv[key]), unicode(value))




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
        do_match_prod(self.parsers, self.matches, self.settings)

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
        do_match_prod(self.parsers, self.matches, self.settings)
        self.updates = UpdateNamespace()
        do_merge_prod(self.matches, self.parsers, self.updates, self.settings)

        if self.debug:
            self.print_updates_summary(self.updates)

        if self.debug:
            for sync_update in self.updates.slave:
                self.print_update(sync_update)

        self.assertEqual(len(self.updates.delta_master), 0)
        self.assertEqual(len(self.updates.delta_slave), 1)
        self.assertEqual(len(self.updates.master), 0)
        self.assertEqual(len(self.updates.new_masters), 0)
        self.assertEqual(len(self.updates.new_slaves), 0)
        self.assertEqual(len(self.updates.nonstatic_slave), 0)
        self.assertEqual(len(self.updates.nonstatic_master), 0)
        self.assertEqual(len(self.updates.problematic), 0)
        self.assertEqual(len(self.updates.slave), 1)

        # sync_update = self.updates.delta_slave[0]
        sync_update = self.updates.delta_slave.get_by_ids(19, 'c27221d7-8290-4204-9f3d-0cfb7c5a3d6f')
        try:
            if self.debug:
                self.print_update(sync_update)
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
        do_match_prod(self.parsers, self.matches, self.settings)
        self.updates = UpdateNamespace()
        do_merge_prod(self.matches, self.parsers, self.updates, self.settings)
        self.reporters = ReporterNamespace()
        do_report(
            self.reporters, self.matches, self.updates, self.parsers, self.settings
        )


if __name__ == '__main__':
    unittest.main()
