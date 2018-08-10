import datetime
import logging
import os
import random
import unittest
from collections import OrderedDict
from copy import deepcopy
from pprint import pformat

import pytest
from tabulate import tabulate
from tests.test_sync_client import AbstractSyncClientTestCase

from context import TESTS_DATA_DIR, woogenerator
from woogenerator.client.img import ImgSyncClientWP
from woogenerator.client.prod import CatSyncClientWC, ProdSyncClientWC
from woogenerator.coldata import ColDataAttachment
from woogenerator.conf.parser import ArgumentParserProd
from woogenerator.namespace.prod import SettingsNamespaceProd
from woogenerator.parsing.api import ApiParseWoo
from woogenerator.parsing.shop import ShopCatList, ShopProdList
from woogenerator.utils import Registrar, SanitationUtils, TimeUtils


class TestProdSyncClient(AbstractSyncClientTestCase):
    config_file = "generator_config_test.yaml"
    settings_namespace_class = SettingsNamespaceProd
    argument_parser_class = ArgumentParserProd

    # uncomment to work on local test settings
    # config_file = "conf_prod_test.yaml"
    # local_work_dir = "~/Documents/woogenerator"

    # uncomment to work on local live settings
    # config_file = "conf_prod.yaml"
    # local_work_dir = "~/Documents/woogenerator"

    def setUp(self):
        super(TestProdSyncClient, self).setUp()

        self.settings.download_slave = True
        self.settings.download_master = True

        if self.debug:
            logging.basicConfig(level=logging.DEBUG)
            Registrar.DEBUG_API = True
            # Registrar.DEBUG_SHOP = True
            # Registrar.DEBUG_MRO = True
            # Registrar.DEBUG_TREE = True
            # Registrar.DEBUG_PARSER = True
            # Registrar.DEBUG_GEN = True
            # Registrar.DEBUG_ABSTRACT = True
            # Registrar.DEBUG_WOO = True
            # Registrar.DEBUG_PARSER = True
            # Registrar.DEBUG_UTILS = True
        else:
            Registrar.DEBUG_MESSAGE = False
            Registrar.DEBUG_PROGRESS = False
            Registrar.DEBUG_WARN = False
        ApiParseWoo.do_images = False
        ApiParseWoo.do_specials = False
        ApiParseWoo.do_dyns = False

    def sub_entity_join_leave(
        self, client, sub_client, sub_entity_handle
    ):
        first_sub_raw = sub_client.get_first_endpoint_item()
        first_sub_core = sub_client.coldata_class.translate_data_from(
            first_sub_raw, sub_client.coldata_target
        )
        if self.debug:
            print("first sub core:\n%s" % pformat(first_sub_core.items()))
        first_sub_pkey = first_sub_core.get(sub_client.primary_key_handle)
        if self.debug:
            print("first sub pkey:%s" % first_sub_pkey)
        self.assertTrue(first_sub_pkey is not None)

        first_entity_raw = client.get_first_endpoint_item()
        first_entity_core = client.coldata_class.translate_data_from(
            first_entity_raw, client.coldata_target
        )
        if self.debug:
            print("first entity core:\n%s" % pformat(first_entity_core.items()))
        first_entity_pkey = first_entity_core.get(client.primary_key_handle)
        if self.debug:
            print("first entity pkey:%s" % first_entity_pkey)
        first_entity_subs = first_entity_core.get(sub_entity_handle)
        first_entity_sub_pkeys = [
            sub.get(sub_client.primary_key_handle) \
            for sub in first_entity_subs
        ]
        if self.debug:
            print("first entity sub pkeys:%s" % first_entity_sub_pkeys)

        new_entity_sub_pkeys = first_entity_sub_pkeys[:]
        if first_sub_pkey in new_entity_sub_pkeys:
            new_entity_sub_pkeys.remove(first_sub_pkey)
        else:
            new_entity_sub_pkeys.append(first_sub_pkey)
        if self.debug:
            print("new entity sub pkeys:%s" % new_entity_sub_pkeys)
        self.assertNotEqual(
            set(first_entity_sub_pkeys),
            set(new_entity_sub_pkeys)
        )

        updates_core = {
            sub_entity_handle: [
                {sub_client.primary_key_handle: pkey} \
                for pkey in new_entity_sub_pkeys
            ]
        }

        first_response_raw = client.upload_changes_core(
            first_entity_pkey,  updates_core
        ).json()
        first_response_core = client.coldata_class.translate_data_from(
            first_response_raw, client.coldata_target
        )
        if self.debug:
            print("first response core:\n%s" % pformat(first_response_core.items()))
        first_response_pkey = first_response_core.get(client.primary_key_handle)
        if self.debug:
            print("first response pkey:%s" % first_response_pkey)
        self.assertEqual(
            first_response_pkey, first_entity_pkey
        )
        first_response_subs = first_response_core.get(sub_entity_handle)
        first_response_sub_pkeys = [
            sub.get(sub_client.primary_key_handle) \
            for sub in first_response_subs
        ]
        self.assertEqual(
            set(new_entity_sub_pkeys),
            set(first_response_sub_pkeys)
        )

        updates_core = {
            sub_entity_handle: first_entity_subs
        }

        second_response_raw = client.upload_changes_core(
            first_entity_pkey,  updates_core
        ).json()
        second_response_core = client.coldata_class.translate_data_from(
            second_response_raw, client.coldata_target
        )
        if self.debug:
            print("second response core:\n%s" % pformat(second_response_core.items()))
        second_response_pkey = second_response_core.get(client.primary_key_handle)
        if self.debug:
            print("second response pkey:%s" % second_response_pkey)
        self.assertEqual(
            second_response_pkey, first_entity_pkey
        )
        second_response_subs = second_response_core.get(sub_entity_handle)
        second_response_sub_pkeys = [
            sub.get(sub_client.primary_key_handle) \
            for sub in second_response_subs
        ]
        if self.debug:
            print("second response sub pkeys:%s" % second_response_sub_pkeys)

        self.assertEqual(
            set(second_response_sub_pkeys),
            set(first_entity_sub_pkeys)
        )

# TODO: mock these tests
@pytest.mark.local
class TestProdSyncClientSimple(TestProdSyncClient):
    """
    Test cases for products, type = simple
    """
    dataset_has_variable = False

    def test_read(self):
        response = []

        product_client_class = self.settings.slave_download_client_class
        product_client_args = self.settings.slave_download_client_args

        with product_client_class(**product_client_args) as client:
            response = client.get_iterator()

            if self.debug:
                print tabulate(list(response)[:10], headers='keys')

            self.assertTrue(response)

    def test_get_first_item(self):
        # self.settings.wc_api_namespace = 'wc-api'
        # self.settings.wc_api_version = 'v3'
        product_client_class = self.settings.slave_download_client_class
        product_client_args = self.settings.slave_download_client_args

        with product_client_class(**product_client_args) as client:
            first_item = client.get_first_endpoint_item()
            self.assertTrue(first_item)
            if self.debug:
                print("fist item:\n%s" % pformat(first_item))
                first_item_json = SanitationUtils.encode_json(first_item)
                print("fist item json:\n%s" % pformat(first_item_json))


    def test_analyse_remote(self):
        product_parser_class = self.settings.slave_parser_class
        product_parser = product_parser_class(
            **self.settings.slave_parser_args
        )

        cat_client_class = self.settings.slave_cat_sync_client_class
        cat_client_args = self.settings.slave_cat_sync_client_args

        with cat_client_class(**cat_client_args) as client:
            client.analyse_remote_categories(product_parser)

        if self.debug:
            print("parser tree:\n%s" % SanitationUtils.coerce_bytes(
                product_parser.to_str_tree()
            ))

        product_client_class = self.settings.slave_download_client_class
        product_client_args = self.settings.slave_download_client_args

        with product_client_class(**product_client_args) as client:
            client.analyse_remote(product_parser, limit=20)


        prod_list = ShopProdList(product_parser.products.values())
        self.assertTrue(prod_list)
        if self.debug:
            print(SanitationUtils.coerce_bytes(
                prod_list.tabulate(tablefmt='simple')
            ))
        var_list = ShopProdList(product_parser.variations.values())

        # TODO: implement var_list?
        # if self.dataset_has_variable:
        #     self.assertTrue(var_list)
        if self.debug:
             print(SanitationUtils.coerce_bytes(
                 var_list.tabulate(tablefmt='simple')
             ))
        cat_list = ShopCatList(product_parser.categories.values())
        self.assertTrue(cat_list)
        if self.debug:
            print(SanitationUtils.coerce_bytes(
                cat_list.tabulate(tablefmt='simple')
            ))
        attr_list = product_parser.attributes.items()
        # TODO: implement and test parsing.api.ApiParseWoo.process_api_attribute_gen

        # if self.dataset_has_variable:
            # self.assertTrue(attr_list)
        if self.debug:
            print(SanitationUtils.coerce_bytes(
                tabulate(attr_list, headers='keys', tablefmt="simple")
            ))

    def test_upload_changes(self):
        target_key = 'weight'
        # target_key = 'regular_price' # this interferes with lasercommerce
        product_client_class = self.settings.slave_download_client_class
        product_client_args = self.settings.slave_download_client_args

        with product_client_class(**product_client_args) as client:
            first_item = client.get_first_endpoint_item()
            if self.debug:
                print("first prod:\n%s" % pformat(first_item))
            first_pkey = client.get_item_core(first_item, 'id')
            try:
                first_value = float(first_item[target_key])
            except ValueError:
                first_value = 0.0
            if self.debug:
                print("first_value:%s" % first_value)

            new_value = first_value
            while new_value == first_value:
                new_value = float(random.randint(10, 20))
            if self.debug:
                print("new_value:%s" % new_value)

            updates = client.set_item_core({}, target_key, str(new_value))
            if self.debug:
                print("updates:\n%s" % pformat(updates))
            response = client.upload_changes(first_pkey, updates)
            if self.debug:
                print("first response:\n%s" % pformat(response.text))
            self.assertTrue(response)
            self.assertTrue(hasattr(response, 'json'))
            response_price = client.get_data_core(response.json(), target_key)
            self.assertEqual(response_price, str(new_value))
            updates = client.set_item_core({}, target_key, str(first_value))

            response = client.upload_changes(first_pkey, updates)
            if self.debug:
                print("second response:\n%s" % pformat(response.text))
            self.assertTrue(hasattr(response, 'json'))
            response_price = client.get_data_core(response.json(), target_key)
            self.assertEqual(response_price, str(first_value))

    def test_upload_changes_meta(self):
        target_key = 'lc_wn_regular_price'
        product_client_class = self.settings.slave_download_client_class
        product_client_args = self.settings.slave_download_client_args

        with product_client_class(**product_client_args) as client:
            first_item = client.get_first_endpoint_item()
            if self.debug:
                print("first prod:\n%s" % pformat(first_item))
            first_pkey = client.get_item_core(first_item, 'id')
            try:
                first_value = float(client.get_item_meta(first_item, target_key))
            except ValueError:
                first_value = 0.0
            if self.debug:
                print("first_value:%s" % first_value)

            new_value = first_value
            while new_value == first_value:
                new_value = float(random.randint(10, 20))
            if self.debug:
                print("new_value:%s" % new_value)

            updates = client.set_item_meta({}, {target_key: str(new_value)})
            if self.debug:
                print("updates:\n%s" % pformat(updates))

            response = client.upload_changes(first_pkey, updates)
            if self.debug:
                print("first response:\n%s" % pformat(response.text))
            self.assertTrue(response)
            self.assertTrue(hasattr(response, 'json'))
            response_price = client.get_data_meta(response.json(), target_key)
            self.assertEqual(response_price, str(new_value))

            updates = client.set_item_meta({}, {target_key: str(first_value)})
            response = client.upload_changes(first_pkey, updates)
            if self.debug:
                print("second response:\n%s" % response.text)
            self.assertTrue(response)
            self.assertTrue(hasattr(response, 'json'))
            response_price = client.get_data_meta(response.json(), target_key)
            self.assertEqual(response_price, str(first_value))

    def test_upload_delete_meta(self):
        target_key = 'lc_wn_regular_price'
        product_client_class = self.settings.slave_download_client_class
        product_client_args = self.settings.slave_download_client_args

        with product_client_class(**product_client_args) as client:
            first_item = client.get_first_endpoint_item()
            if self.debug:
                print("first prod:\n%s" % pformat(first_item))
            first_pkey = client.get_item_core(first_item, 'id')
            try:
                first_value = float(client.get_item_meta(first_item, target_key))
            except ValueError:
                first_value = 0.0
            if self.debug:
                print("first_value:%s" % first_value)

            new_value = first_value
            while new_value == first_value:
                new_value = random.randint(10, 20)
            if self.debug:
                print("new_value:%s" % new_value)

            updates = client.delete_item_meta({}, target_key)

            if self.debug:
                print("updates:\n%s" % pformat(updates))

            response = client.upload_changes(first_pkey, updates)
            if self.debug:
                print("first response:\n%s" % pformat(response.text))
            self.assertTrue(response)
            self.assertTrue(hasattr(response, 'json'))
            response_price = client.get_data_meta(response.json(), target_key)
            self.assertEqual(response_price, '')

            updates = client.set_item_meta({}, {target_key: str(first_value)})
            response = client.upload_changes(first_pkey, updates)
            if self.debug:
                print("second response: %s" % response.text)
            self.assertTrue(response)
            self.assertTrue(hasattr(response, 'json'))
            response_price = client.get_data_meta(response.json(), target_key)
            self.assertEqual(response_price, str(first_value))

    def test_upload_create_delete_product(self):
        product_client_class = self.settings.slave_download_client_class
        product_client_args = self.settings.slave_download_client_args

        with product_client_class(**product_client_args) as client:
            first_prod_raw = client.get_first_endpoint_item()
            if self.debug:
                print("first prod:\n%s" % pformat(first_prod_raw))

            if self.debug:
                print("first prod raw:\n%s" % pformat(first_prod_raw.items()))
            first_prod_core = client.coldata_class.translate_data_from(
                first_prod_raw, client.coldata_target
            )
            if self.debug:
                print("first prod core:\n%s" % pformat(first_prod_core.items()))
            first_prod_sku = first_prod_core.get('sku')
            if self.debug:
                print("first prod sku:%s" % first_prod_sku)
            new_sku = "%s-%02x" % (first_prod_sku, random.randrange(0,255))
            first_prod_core['sku'] = new_sku
            new_prod_raw = client.coldata_class.translate_data_to(
                first_prod_core, client.coldata_target_write
            )

            # TODO: should this go in client.create_item?
            new_prod_raw = client.strip_item_readonly(new_prod_raw)

            response = client.create_item(new_prod_raw)

            self.assertTrue(response)
            if self.debug:
                print("response: %s" % response.text)
            self.assertTrue(hasattr(response, 'json'))
            created_id = client.get_data_core(response.json(), 'id')
            response = client.delete_item(created_id)
            if self.debug:
                print("response: %s" % response.text)
            self.assertTrue(response)
            self.assertTrue(hasattr(response, 'json'))

    def test_upload_product_categories_join_leave(self):
        sub_entity_handle = 'product_categories'

        cat_client_class = self.settings.slave_cat_sync_client_class
        cat_client_args = self.settings.slave_cat_sync_client_args

        product_client_class = self.settings.slave_download_client_class
        product_client_args = self.settings.slave_download_client_args

        with cat_client_class(**cat_client_args) as sub_client, \
        product_client_class(**product_client_args) as client:
            self.sub_entity_join_leave(
                client, sub_client, sub_entity_handle
            )


class TestProdSyncClientSimpleWP(TestProdSyncClientSimple):
    """
    Perform tests with WPTest dataset
    """
    def test_upload_product_images_attach_remove(self):
        """
        Get the first image from the api and attach it to the first product.
        Remove attachment when complete.

        Only works with WPTest dataset
        """
        #TODO: update WCTest config so this works

        sub_entity_handle = 'attachment_objects'

        cat_client_class = self.settings.slave_img_sync_client_class
        cat_client_args = self.settings.slave_img_sync_client_args

        product_client_class = self.settings.slave_download_client_class
        product_client_args = self.settings.slave_download_client_args

        with cat_client_class(**cat_client_args) as sub_client, \
        product_client_class(**product_client_args) as client:
            self.sub_entity_join_leave(
                client, sub_client, sub_entity_handle
            )

@pytest.mark.local
class TestProdSyncClientSimpleWC(TestProdSyncClientSimple):
    """
    Perform tests with WCTest dataset
    """
    config_file = "generator_config_wctest.yaml"
    dataset_has_variable = True

    @unittest.skip("not implemented yet")
    def test_upload_product_variation_attach_remove(self):
        pass

@pytest.mark.local
class TestVarSyncClientWC(TestProdSyncClient):
    """
    These tests only work on WCTest dataset
    """
    config_file = "generator_config_wctest.yaml"
    def test_upload_changes_variation(self):

        delta_handle = 'weight'
        expected_delta = str(random.randint(1, 100))
        updates_core = OrderedDict([
            (delta_handle, expected_delta)
        ])

        product_client_class = self.settings.slave_download_client_class
        product_client_args = self.settings.slave_download_client_args

        with product_client_class(**product_client_args) as client:
            first_prod_raw = client.get_first_variable_product()
            self.assertTrue(first_prod_raw)
            if self.debug:
                print("first prod raw:\n%s" % pformat(first_prod_raw.items()))
            first_prod_core = client.coldata_class.translate_data_from(
                first_prod_raw, client.coldata_target
            )
            if self.debug:
                print("first prod core:\n%s" % pformat(first_prod_core.items()))
            first_prod_pkey = first_prod_core.get(client.primary_key_handle)
            if self.debug:
                print("first prod pkey:%s" % first_prod_pkey)

        var_client_class = self.settings.slave_var_sync_client_class
        var_client_args = self.settings.slave_var_sync_client_args
        with var_client_class(**var_client_args) as client:
            first_var_raw = client.get_first_variation(first_prod_pkey)
            if self.debug:
                print("first var raw:\n%s" % pformat(first_var_raw.items()))
            first_var_core = client.coldata_class.translate_data_from(
                first_var_raw, client.coldata_target
            )
            if self.debug:
                print("first var core:\n%s" % pformat(first_var_core.items()))
            first_var_pkey = first_var_core.get(client.primary_key_handle)
            if self.debug:
                print("first var pkey:%s" % first_var_pkey)
            first_var_delta = first_var_core.get(delta_handle)

            first_response_raw = client.upload_changes_core(
                first_prod_pkey, updates_core, var_pkey=first_var_pkey
            ).json()
            if self.debug:
                print("first response raw:\n%s" % pformat(first_response_raw.items()))
            first_response_core = client.coldata_class.translate_data_from(
                first_response_raw, client.coldata_target
            )
            if self.debug:
                print("first response core:\n%s" % pformat(first_response_core.items()))
            first_response_pkey = first_response_core.get(client.primary_key_handle)
            if self.debug:
                print("first response pkey:%s" % first_response_pkey)
            first_response_delta = first_response_core.get(delta_handle)

            self.assertEqual(
                first_response_delta, expected_delta
            )

            updates_core[delta_handle] = first_var_delta

            second_response_raw = client.upload_changes_core(
                first_prod_pkey, updates_core, var_pkey=first_var_pkey
            ).json()
            if self.debug:
                print("second response raw:\n%s" % pformat(second_response_raw.items()))
            second_response_core = client.coldata_class.translate_data_from(
                second_response_raw, client.coldata_target
            )
            if self.debug:
                print("second response core:\n%s" % pformat(second_response_core.items()))
            second_response_pkey = second_response_core.get(client.primary_key_handle)
            if self.debug:
                print("second response pkey:%s" % second_response_pkey)
            second_response_delta = second_response_core.get(delta_handle)

            self.assertEqual(
                second_response_delta, first_var_delta
            )

    @unittest.skip("Destructive tests not mocked yet")
    def test_upload_changes_var_meta(self):
        pkey = 23
        expected_result = str(random.randint(1, 100))
        updates = dict([
            ('custom_meta', dict([
                ('lc_dn_regular_price', expected_result)
            ]))
        ])
        with ProdSyncClientWC(self.settings.slave_wc_api_params) as client:
            response = client.upload_changes(pkey, updates)
            # print response
            # if hasattr(response, 'json'):
            #     print "test_upload_changes_var_meta", response.json()
            # self.assertIn('meta_test_key', str(response.json()))
            self.assertIn('lc_dn_regular_price',
                          (response.json()['product']['meta']))
            wn_regular_price = response.json()['product']['meta'][
                'lc_dn_regular_price']
            self.assertEqual(wn_regular_price, expected_result)

    @unittest.skip("Destructive tests not mocked yet")
    def test_upload_delete_var_meta(self):
        pkey = 41
        updates = OrderedDict([
            ('custom_meta', OrderedDict([
                ('lc_wn_regular_price', u'')
            ]))
        ])
        with ProdSyncClientWC(self.settings.slave_wc_api_params) as client:
            response = client.upload_changes(pkey, updates)
            # print response
            # if hasattr(response, 'json'):
            #     print "test_upload_delete_var_meta", response.json()
            wn_regular_price = response.json()['product'][
                'meta'].get('lc_wn_regular_price')
            self.assertFalse(wn_regular_price)

@pytest.mark.local
class TestCatSyncClient(TestProdSyncClient):
    def test_get_first_cat(self):
        cat_client_class = self.settings.slave_cat_sync_client_class
        cat_client_args = self.settings.slave_cat_sync_client_args

        with cat_client_class(**cat_client_args) as client:
            first_item = client.get_first_endpoint_item()
            self.assertTrue(first_item)
            if self.debug:
                print("fist_cat:\n%s" % pformat(first_item))

    def test_cat_sync_client(self):
        cat_client_class = self.settings.slave_cat_sync_client_class
        cat_client_args = self.settings.slave_cat_sync_client_args

        with cat_client_class(**cat_client_args) as client:
            for page in client.get_iterator():
                self.assertTrue(page)
                # print page

    # TODO: this
    @unittest.skip("probably implemented")
    def test_upload_create_delete_cat(self):
        pass

@pytest.mark.local
class TestImgSyncClient(TestProdSyncClient):
    """
    These test cases only work on the wptest dataset
    """

    def test_get_first_img(self):
        img_client_class = self.settings.slave_img_sync_client_class
        img_client_args = self.settings.slave_img_sync_client_args

        with img_client_class(**img_client_args) as client:
            first_item = client.get_first_endpoint_item()
            self.assertTrue(first_item)
            if self.debug:
                print("fist_img:\n%s" % pformat(first_item))


    def test_upload_image_delete(self):
        """
        Only upload a raw image
        """
        if self.debug:
            Registrar.DEBUG_API = True
            logging.basicConfig(level=logging.DEBUG)
        img_client_class = self.settings.slave_img_sync_client_class
        img_client_args = self.settings.slave_img_sync_client_args

        with img_client_class(**img_client_args) as client:
            img_path = os.path.join(TESTS_DATA_DIR, 'sample_img.jpg')
            response = client.upload_image(img_path)
            if self.debug:
                print("response: %s" % pformat(response.json()))
            id_key = 'id'
            if self.settings.wp_api_version == 'wp/v1':
                id_key = 'ID'
            self.assertIn(id_key, response.json())
            img_id = client.get_data_core(response.json(), id_key)
            client.delete_item(img_id)

    def test_upload_image_changes_slave_delete(self):
        if self.debug:
            Registrar.DEBUG_API = True
            logging.basicConfig(level=logging.DEBUG)
        img_client_class = self.settings.slave_img_sync_client_class
        img_client_args = self.settings.slave_img_sync_client_args

        title = "Range A - Style 2 - 1Litre"
        content = (
            "Company A have developed a range of unique blends in 16 shades "
            "to suit all use cases. All Company A's products are created "
            "using the finest naturally derived botanical and certified "
            "organic ingredients."
        )

        new_img_core = OrderedDict([
            ('title', title),
            ('post_excerpt', content),
            ('post_content', content),
            ('menu_order', 14),
            ('alt_text', title),
            ('file_path', 'tests/sample_data/imgs_raw/ACARA-CCL.png')
        ])

        with img_client_class(**img_client_args) as client:
            img_path = new_img_core.pop('file_path')
            response = client.upload_image(img_path)
            if self.debug:
                print("upload images response: %s" % pformat(response.json()))
            response_core = client.coldata_class.translate_data_from(
                response.json(), client.coldata_target
            )
            self.assertIn(client.primary_key_handle, response.json())
            img_id = client.coldata_class.get_from_path(
                response_core, client.primary_key_handle
            )
            # if self.debug:
            #     import pudb; pudb.set_trace()
            response = client.upload_changes_core(img_id, new_img_core)
            if self.debug:
                print("upload changes response: %s" % pformat(response.json()))
            response_core = client.coldata_class.translate_data_from(
                response.json(), client.coldata_target_write
            )
            self.assertEqual(
                response_core['title'], title
            )
            self.assertEqual(
                response_core['post_excerpt'], content
            )
            self.assertEqual(
                response_core['post_content'], content
            )
            self.assertEqual(
                response_core['alt_text'], title
            )
            if self.debug:
                print("upload changes response core: %s" % pformat(response_core.items()))
            client.delete_item(img_id)

    def test_overwrite_image(self):
        """
        This might have issues with not regenrating the thumbnails correctly
        """
        if self.debug:
            Registrar.DEBUG_API = True
            logging.basicConfig(level=logging.DEBUG)
        img_client_class = self.settings.slave_img_sync_client_class
        img_client_args = self.settings.slave_img_sync_client_args

        new_img_core = OrderedDict([
            ('file_path', 'tests/sample_data/imgs_raw/ACARA-CCL.png')
        ])

        with img_client_class(**img_client_args) as client:
            first_img_raw = client.get_first_endpoint_item()
            if self.debug:
                print("first img raw:\n%s" % pformat(first_img_raw.items()))
            first_img_core = client.coldata_class.translate_data_from(
                first_img_raw, client.coldata_target_write
            )
            if self.debug:
                print("first img core:\n%s" % pformat(first_img_core.items()))
            first_img_pkey = first_img_core.get(client.primary_key_handle)
            if self.debug:
                print("first img pkey: %s" % first_img_pkey)
            self.assertTrue(first_img_pkey)

            response_img_raw = client.upload_changes_core(
                first_img_pkey, new_img_core
            ).json()
            if self.debug:
                print("response img raw:\n%s" % pformat(response_img_raw.items()))
            response_img_core = client.coldata_class.translate_data_from(
                response_img_raw, client.coldata_target_write
            )
            if self.debug:
                print("response img core:\n%s" % pformat(response_img_core.items()))
            response_img_pkey = response_img_core.get(client.primary_key_handle)
            if self.debug:
                print("response img pkey: %s" % response_img_pkey)
            self.assertTrue(response_img_pkey)

            self.assertNotEqual(first_img_pkey, response_img_pkey)

            client.delete_item(response_img_pkey)

    @unittest.skip('not implemented')
    def test_analyse_single_reomte_img(self):
        raise NotImplementedError()

@pytest.mark.local
class TestProdSyncClientConstructors(TestProdSyncClient):
    # def test_make_usr_m_up_client(self):
    #     self.settings.update_master = True
    #     master_client_args = self.settings.master_upload_client_args
    #     master_client_class = self.settings.master_upload_client_class
    #     with master_client_class(**master_client_args) as master_client:
    #         self.assertTrue(master_client)

    def test_make_prod_s_up_client(self):
        self.settings.update_slave = True
        slave_client_args = self.settings.slave_upload_client_args
        slave_client_class = self.settings.slave_upload_client_class
        with slave_client_class(**slave_client_args) as slave_client:
            self.assertTrue(slave_client)

    @unittest.skipIf(
        TestProdSyncClient.local_work_dir == TESTS_DATA_DIR,
        "won't work with dummy conf"
    )
    def test_make_prod_m_down_client(self):
        self.settings.download_master = True
        master_client_args = self.settings.master_download_client_args
        master_client_class = self.settings.master_download_client_class
        with master_client_class(**master_client_args) as master_client:
            self.assertTrue(master_client)

    def test_make_prod_s_down_client(self):
        self.settings.download_slave = True
        slave_client_args = self.settings.slave_download_client_args
        slave_client_class = self.settings.slave_download_client_class
        with slave_client_class(**slave_client_args) as slave_client:
            self.assertTrue(slave_client)

@pytest.mark.local
class TestProdSyncClientXero(TestProdSyncClient):
    # debug = True

    @unittest.skipIf(
        TestProdSyncClient.local_work_dir == TESTS_DATA_DIR,
        "won't work with dummy conf"
    )
    def test_read(self):
        self.settings.download_slave = True
        self.settings.schema = 'XERO'
        slave_client_args = self.settings.slave_download_client_args
        slave_client_class = self.settings.slave_download_client_class
        if self.debug:
            print("slave_client_args: %s" % slave_client_args)
            print("slave_client_class: %s" % slave_client_class)
        with slave_client_class(**slave_client_args) as slave_client:
            self.assertTrue(slave_client)
            if self.debug:
                print(slave_client.service.items.all()[:10])

if __name__ == '__main__':
    unittest.main()
