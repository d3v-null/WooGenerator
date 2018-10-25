import datetime
import logging
import os
import random
import unittest
from collections import OrderedDict
from copy import deepcopy
from pprint import pformat
import functools

import pytest
from tabulate import tabulate
from tests.test_sync_client import AbstractSyncClientTestCase

from context import TESTS_DATA_DIR, woogenerator
from woogenerator.client.prod import ProdSyncClientWCLegacy
from woogenerator.coldata import ColDataAttachment
from woogenerator.conf.parser import ArgumentParserProd
from woogenerator.namespace.prod import SettingsNamespaceProd
from woogenerator.parsing.api import ApiParseWoo
from woogenerator.parsing.shop import ShopCatList, ShopProdList
from woogenerator.utils import Registrar, SanitationUtils, TimeUtils


class TestProdSyncClient(AbstractSyncClientTestCase):
    # config_file = "generator_config_test_docker.yaml"
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

    def toggle(self, sequence, element):
        sequence = sequence[:]
        if element in sequence:
            sequence.remove(element)
        else:
            sequence.append(element)
        return sequence

    @classmethod
    def get_pkey_list(cls, items, client):
        return sorted([
            item.get(client.primary_key_handle) \
            for item in items
        ])

    def sub_join_leave(
        self, client, sub_client, sub_handle
    ):
        """
        Helper method containing common functionality for testing sub-entities
        (items that are children of other items, e.g. categories, attachments)
        """

        entity_raw = client.get_first_endpoint_item()
        entity_pkey, entity_subs = tuple(self.raw_get_core_paths(
            client, entity_raw, [client.primary_key_handle, sub_handle]
        ))

        first_sub_raw = sub_client.get_first_endpoint_item()
        first_sub_pkey, = tuple(self.raw_get_core_paths(
            sub_client, first_sub_raw, [sub_client.primary_key_handle]
        ))
        self.assertFalse(first_sub_pkey is None)

        entity_sub_pkeys = self.get_pkey_list(entity_subs, sub_client)

        new_sub_pkeys = self.toggle(entity_sub_pkeys, first_sub_pkey)

        new_subs = [
            {sub_client.primary_key_handle: pkey} \
            for pkey in new_sub_pkeys
        ]

        if new_subs == []:
            raise UserWarning("undefined behaviour: removing all sub entities")

        self.check_update_target_path(
            client, entity_pkey, sub_handle, new_subs,
            comparison=functools.partial(self.get_pkey_list, client=sub_client)
        )

        self.check_update_target_path(
            client, entity_pkey, sub_handle, entity_subs,
            comparison=functools.partial(self.get_pkey_list, client=sub_client)
        )

    def extract_core(self, client, item_raw):
        return client.coldata_class.translate_data_from(
            item_raw, client.coldata_target
        )

    def response_extract_core(self, client, response):
        """
        Get the response item in core format
        """
        return self.extract_core(
            client,
            client.apply_to_data_item(response.json(), SanitationUtils.identity)
        )

    def core_get_core_paths(self, client, item_core, core_paths):
        """
        Given an item in core format, extract the values from the target at the
        given core paths.
        """
        for core_path in core_paths:
            try:
                yield client.coldata_class.get_from_path(
                    item_core, core_path
                )
            except IndexError:
                yield None

    def raw_get_core_paths(self, client, item_raw, core_paths):
        """
        Given an item in raw format, convert to core format and extract the values
        from the target at the given core paths.
        """
        return self.core_get_core_paths(
            client, self.extract_core(client, item_raw), core_paths
        )


    def check_update_target_path(self, client, pkey, core_path, value, **kwargs):
        """
        Set the value of the item represented by a given primary key to the
        given value at the core path.
        """
        updates_core = client.coldata_class.update_in_path(
            {}, core_path, value
        )
        self.assertTrue(updates_core)
        response = client.upload_changes_core(pkey, updates_core, **kwargs)
        self.assertTrue(response)
        self.assertTrue(hasattr(response, 'json'))
        response_core = self.response_extract_core(client, response)
        self.assertTrue(response_core)
        try:
            response_value = client.coldata_class.get_from_path(
                response_core, core_path
            )
        except IndexError:
            response_value = None
        if 'comparison' in kwargs and callable(kwargs['comparison']):
            value = kwargs['comparison'](value)
            response_value = kwargs['comparison'](response_value)
        self.assertEqual(response_value, value)

    def check_delete_target_path(self, client, pkey, core_path, **kwargs):
        self.check_update_target_path(client, pkey, core_path, '', **kwargs)

    def new_distinct_strint(self, old_value):
        """
        Generate a new random str float until it is different to the old value
        """
        new_value = old_value
        while new_value == old_value:
            new_value = str(float(random.randint(10, 20)))
        return new_value

# TODO: mock these tests
@pytest.mark.local
class TestProdSyncClientSimple(TestProdSyncClient):
    """
    Test cases for products, type = simple
    """
    dataset_has_variable = False
    dataset_has_img = True

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
        delta_path = 'weight'
        product_client_class = self.settings.slave_download_client_class
        product_client_args = self.settings.slave_download_client_args

        with product_client_class(**product_client_args) as client:
            first_item_raw = client.get_first_endpoint_item()
            value, pkey = tuple(self.raw_get_core_paths(
                client, first_item_raw, [delta_path, client.primary_key_handle]
            ))
            if value is None:
                value = '0.0'

            new_value = self.new_distinct_strint(value)
            self.check_update_target_path(client, pkey, delta_path, new_value)
            self.check_update_target_path(client, pkey, delta_path, value)

    def test_upload_changes_meta(self):
        """
        Test data has been compromised, Fails with

        IndexError: No key lc_wn_regular_price in data [OrderedDict([('meta_value', []), ('meta_id', 110485), ('meta_key', u'_upsell_skus')]), OrderedDict([('meta_value', []), ('meta_id', 110486), ('meta_key', u'_crosssell_skus')]), OrderedDict([('meta_value', u''), ('meta_id', 110489), ('meta_key', u'_min_variation_price')]), OrderedDict([('meta_value', u''), ('meta_id', 110490), ('meta_key', u'_max_variation_price')]), OrderedDict([('meta_value', u''), ('meta_id', 110491), ('meta_key', u'_min_variation_regular_price')]), OrderedDict([('meta_value', u''), ('meta_id', 110492), ('meta_key', u'_max_variation_regular_price')]), OrderedDict([('meta_value', u''), ('meta_id', 110493), ('meta_key', u'_min_variation_sale_price')]), OrderedDict([('meta_value', u''), ('meta_id', 110494), ('meta_key', u'_max_variation_sale_price')]), OrderedDict([('meta_value', u''), ('meta_id', 110496), ('meta_key', u'_file_path')]), OrderedDict([('meta_value', u''), ('meta_id', 110500), ('meta_key', u'_product_url')]), OrderedDict([('meta_value', u''), ('meta_id', 110501), ('meta_key', u'_button_text')]), OrderedDict([('meta_value', u'Cotton Glove Pack x5 Pairs'), ('meta_id', 110503), ('meta_key', u'title_1')]), OrderedDict([('meta_value', u'27065'), ('meta_id', 110769), ('meta_key', u'_min_price_variation_id')]), OrderedDict([('meta_value', u'27065'), ('meta_id', 110770), ('meta_key', u'_min_regular_price_variation_id')]), OrderedDict([('meta_value', u'27065'), ('meta_id', 110771), ('meta_key', u'_min_sale_price_variation_id')]), OrderedDict([('meta_value', u'27065'), ('meta_id', 110772), ('meta_key', u'_max_price_variation_id')]), OrderedDict([('meta_value', u'27065'), ('meta_id', 110773), ('meta_key', u'_max_regular_price_variation_id')]), OrderedDict([('meta_value', u'27065'), ('meta_id', 110774), ('meta_key', u'_max_sale_price_variation_id')])]
        """
        delta_path = 'meta.lc_wn_regular_price'
        product_client_class = self.settings.slave_download_client_class
        product_client_args = self.settings.slave_download_client_args

        with product_client_class(**product_client_args) as client:
            first_item_raw = client.get_first_endpoint_item()
            value, pkey = tuple(self.raw_get_core_paths(
                client, first_item_raw, [delta_path, client.primary_key_handle]
            ))
            if value is None:
                value = '0.0'

            new_value = self.new_distinct_strint(value)

            self.check_update_target_path(client, pkey, delta_path, new_value)
            self.check_update_target_path(client, pkey, delta_path, value)

    def test_upload_delete_meta(self):
        delta_path = 'meta.lc_wn_regular_price'
        product_client_class = self.settings.slave_download_client_class
        product_client_args = self.settings.slave_download_client_args

        with product_client_class(**product_client_args) as client:
            first_item_raw = client.get_first_endpoint_item()
            value, pkey = tuple(self.raw_get_core_paths(
                client, first_item_raw, [delta_path, client.primary_key_handle]
            ))
            if value is None:
                value = '0.0'

            self.check_delete_target_path(client, pkey, delta_path)
            self.check_update_target_path(client, pkey, delta_path, value)

    def test_upload_create_delete_product(self):
        product_client_class = self.settings.slave_download_client_class
        product_client_args = self.settings.slave_download_client_args

        with product_client_class(**product_client_args) as client:
            first_prod_raw = client.get_first_endpoint_item()
            first_prod_core = client.coldata_class.translate_data_from(
                first_prod_raw, client.coldata_target
            )
            first_prod_sku = client.coldata_class.get_from_path(
                first_prod_core, 'sku'
            )

            new_sku = "%s-%02x" % (first_prod_sku, random.randrange(0,255))
            first_prod_core['sku'] = new_sku

            new_prod_raw = client.coldata_class.translate_data_to(
                first_prod_core, client.coldata_target_write
            )

            # TODO: should this go in client.create_item?
            new_prod_raw = client.strip_item_readonly(new_prod_raw)

            response = client.create_item(new_prod_raw)
            response_core = self.response_extract_core(client, response)
            created_id = client.coldata_class.get_from_path(
                response_core, client.primary_key_handle
            )
            response = client.delete_item(created_id)
            self.assertTrue(response.json())


    def test_upload_product_categories_join_leave(self):
        sub_handle = 'product_categories'

        cat_client_class = self.settings.slave_cat_sync_client_class
        cat_client_args = self.settings.slave_cat_sync_client_args

        product_client_class = self.settings.slave_download_client_class
        product_client_args = self.settings.slave_download_client_args

        with cat_client_class(**cat_client_args) as sub_client, \
        product_client_class(**product_client_args) as client:
            self.sub_join_leave(
                client, sub_client, sub_handle
            )

    @pytest.mark.skip("see docstring")
    def test_upload_product_images_attach_remove(self):
        """
        Get the first image from the api and attach it to the first product.
        Remove attachment when complete.

        Only works with WPTest dataset


        # TODO :

        This is happening because placeholder has image id 0

        E       UserWarning: API call to http://derwent-mac.ddns.me:18080/wptest/wp-json/wc/v2/products/27063?oauth_consumer_key=ck_e1dd4a9c85f49b9685f7964a154eecb29af39d5a&oauth_nonce=bf02c3d2498f9a8961b0c563391d068a5a1d0750&oauth_signature=vsVQ%2BVgsEpupPZ58g6q0VHdxiAI%3D&oauth_signature_method=HMAC-SHA1&oauth_timestamp=1540435742 returned
        E       CODE: 400
        E       RESPONSE:{"code":"woocommerce_product_invalid_image_id","message":"#0 is an invalid image ID.","data":{"status":400}}
        E       HEADERS: {'Content-Length': '108', 'Expires': 'Wed, 11 Jan 1984 05:00:00 GMT', 'X-Robots-Tag': 'noindex', 'X-Content-Type-Options': 'nosniff', 'X-Powered-By': 'PHP/5.6.37', 'Set-Cookie': 'woocommerce_items_in_cart=1; path=/wptest/, woocommerce_cart_hash=66c031c3683b5154c3ee0263b866d743; path=/wptest/, wp_woocommerce_session_5a4b03a1213eec2796b60fff69c78339=1%7C%7C1540608543%7C%7C1540604943%7C%7C6f9c5165db90df40c8061625e2a67ca9; expires=Sat, 27-Oct-2018 02:49:03 GMT; Max-Age=172800; path=/wptest/', 'Access-Control-Expose-Headers': 'X-WP-Total, X-WP-TotalPages', 'Server': 'Apache/2.4.35 (Unix) PHP/5.6.37', 'Connection': 'close', 'Link': '<http://derwent-mac.ddns.me:18080/wptest/wp-json/>; rel="https://api.w.org/"', 'Allow': 'GET, POST, PUT, PATCH, DELETE', 'Cache-Control': 'no-cache, must-revalidate, max-age=0', 'Date': 'Thu, 25 Oct 2018 02:49:02 GMT', 'Access-Control-Allow-Headers': 'Authorization, Content-Type', 'Content-Type': 'application/json; charset=UTF-8'}
        E       REQ_BODY:{"images": [{"id": 0}, {"id": 27091}]}
        E       Because of woocommerce_product_invalid_image_id - #0 is an invalid image ID. - {u'status': 400}
        """

        if not self.dataset_has_img:
            return

        sub_handle = 'attachment_objects'

        img_client_class = self.settings.slave_img_sync_client_class
        img_client_args = self.settings.slave_img_sync_client_args

        product_client_class = self.settings.slave_download_client_class
        product_client_args = self.settings.slave_download_client_args

        with img_client_class(**img_client_args) as sub_client, \
        product_client_class(**product_client_args) as client:
            self.sub_join_leave(
                client, sub_client, sub_handle
            )

@pytest.mark.local
class TestProdSyncClientSimpleWC(TestProdSyncClientSimple):
    """
    Perform tests with WCTest dataset
    """
    # config_file = "generator_config_wctest.yaml"
    dataset_has_variable = True
    dataset_has_img = False

    @pytest.mark.skip("attribute sync not implemented yet")
    def test_upload_var_create_delete(self):





        # TODO: THIS ONE







        sub_handle = 'variations'

        var_client_class = self.settings.slave_var_sync_client_class
        var_client_args = self.settings.slave_var_sync_client_args

        product_client_class = self.settings.slave_download_client_class
        product_client_args = self.settings.slave_download_client_args

        with var_client_class(**var_client_args) as sub_client, \
        product_client_class(**product_client_args) as client:

            entity_core = self.extract_core(
                client, client.get_first_variable_product()
            )
            entity_pkey, entity_subs, entity_attributes = tuple(
                self.core_get_core_paths(client, entity_core, [
                    client.primary_key_handle, sub_handle, 'attributes'
                ]
            ))

            # TODO: Fails here with AssertionError: [] is not true
            self.assertTrue(entity_subs)
            self.assertTrue(entity_attributes)
            self.assertTrue(entity_attributes[0]['options'])
            self.assertFalse(entity_attributes[0]['variation'] is None)

            entity_var_attributes = [
                attribute for attribute in entity_attributes if \
                attribute.get('variation')
            ]
            self.assertTrue(entity_var_attributes)
            entity_sub_pkeys = self.get_pkey_list(entity_subs, sub_client)
            self.assertTrue(entity_sub_pkeys)

            sub_core = self.extract_core(
                sub_client, sub_client.get_first_variation(entity_pkey)
            )
            sub_pkey, sub_sku, sub_attr_instances = tuple(self.core_get_core_paths(
                sub_client, sub_core, [
                    sub_client.primary_key_handle, 'sku', 'attributes'
                ]
            ))

            self.assertTrue(sub_attr_instances)
            self.assertTrue(sub_attr_instances[0]['title'])

            perform_deletion = True
            # Delete the variation
            if perform_deletion:
                sub_client.delete_item(sub_pkey, parent_pkey=entity_pkey)

            # Check that the variation was deleted
            mod_entity_response = client.get_single_endpoint_item(
                entity_pkey
            )
            mod_entity_core = self.response_extract_core(
                client, mod_entity_response
            )
            mod_entity_subs, mod_entity_attributes = tuple(
                self.core_get_core_paths(client, mod_entity_core, [
                    sub_handle, 'attributes'
                ])
            )

            mod_var_attributes = [
                attribute for attribute in mod_entity_attributes if \
                attribute.get('variation')
            ]
            self.assertTrue(mod_var_attributes)
            mod_sub_pkeys = self.get_pkey_list(mod_entity_subs, sub_client)

            self.assertEqual(
                perform_deletion,
                bool( set(entity_sub_pkeys) - set(mod_sub_pkeys) )
            )
            # self.assertEqual(
            #     perform_deletion,
            #     bool( mod_var_attributes != entity_var_attributes )
            # )

            # Re-create the variation we deleted

            if not perform_deletion:
                new_sku = "%s-%02x" % (sub_sku, random.randrange(0,255))
                sub_core['sku'] = new_sku

            new_sub_raw = sub_client.coldata_class.translate_data_to(
                sub_core, sub_client.coldata_target_write
            )

            # TODO: should this go in sub_client.create_item?
            new_sub_raw = sub_client.strip_item_readonly(new_sub_raw)

            response = sub_client.create_item(new_sub_raw, parent_pkey=entity_pkey)

            # Verify it was created

            new_sub_core = self.response_extract_core(sub_client, response)

            new_sub_pkey, new_sub_sku, new_sub_attr_instances = tuple(self.core_get_core_paths(
                sub_client, new_sub_core, [
                    sub_client.primary_key_handle, 'sku', 'attributes'
                ]
            ))

            self.assertEqual(
                perform_deletion,
                new_sub_sku == sub_sku
            )
            self.assertNotEqual(new_sub_pkey, sub_pkey)











            # sub_pkey, = tuple(self.raw_get_core_paths(
            #     sub_client, sub_raw, [sub_client.primary_key_handle]
            # ))
            # self.assertFalse(sub_pkey is None)

            # entity_sub_pkeys = self.get_pkey_list(entity_subs, sub_client)
            #
            # new_sub_pkeys = self.toggle(entity_sub_pkeys, sub_pkey)
            #
            # new_subs = [
            #     {sub_client.primary_key_handle: pkey} \
            #     for pkey in new_sub_pkeys
            # ]
            #
            # self.check_update_target_path(
            #     client, entity_pkey, sub_handle, new_subs,
            #     comparison=functools.partial(self.get_pkey_list, client=sub_client)
            # )
            #
            # self.check_update_target_path(
            #     client, entity_pkey, sub_handle, entity_subs,
            #     comparison=functools.partial(self.get_pkey_list, client=sub_client)
            # )

@unittest.skip("legacy api not supported")
class TestProdSyncClientSimpleWCLegacy(TestProdSyncClientSimple):
    # config_file = "generator_config_wctest.yaml"
    dataset_has_variable = True
    dataset_has_img = False

    def setUp(self):
        super(TestProdSyncClientSimpleWCLegacy, self).setUp()
        self.settings.wc_api_namespace = "wc-api"
        self.settings.wc_api_version = "v3"

    @unittest.skip("legacy API does not do product category primary keys so it's too complicated")
    def test_upload_product_categories_join_leave(self):
        super(TestProdSyncClientSimpleWCLegacy, self).test_upload_product_categories_join_leave()

    def test_upload_delete_meta(self):
        """Legacy API does not do meta."""
        pass

    def test_upload_changes_meta(self):
        """Legacy API does not do meta."""
        pass




@pytest.mark.local
class TestVarSyncClientWC(TestProdSyncClient):
    """
    These tests only work on WCTest dataset because WPTest doesn't have variable
    """
    # config_file = "generator_config_wctest.yaml"
    def test_upload_changes_variation(self):
        delta_path = 'weight'

        product_client_class = self.settings.slave_download_client_class
        product_client_args = self.settings.slave_download_client_args
        with product_client_class(**product_client_args) as client:
            first_prod_raw = client.get_first_variable_product()
            parent_pkey,  = tuple(self.raw_get_core_paths(
                client, first_prod_raw, [client.primary_key_handle]
            ))

        var_client_class = self.settings.slave_var_sync_client_class
        var_client_args = self.settings.slave_var_sync_client_args
        with var_client_class(**var_client_args) as client:
            first_var_raw = client.get_first_variation(parent_pkey)
            value, var_pkey = tuple(self.raw_get_core_paths(
                client, first_var_raw, [delta_path, client.primary_key_handle]
            ))

            new_value = self.new_distinct_strint(value)

            self.check_update_target_path(
                client, var_pkey, delta_path, new_value, parent_pkey=parent_pkey
            )
            self.check_update_target_path(
                client, var_pkey, delta_path, value, parent_pkey=parent_pkey
            )

    def test_upload_changes_var_meta(self):
        """
        TODO: test data has been compromised.

        First variable product contains no variations.

        self = <woogenerator.client.prod.VarSyncClientWC object at 0x107236310>, parent_id = 1237

            def get_first_variation(self, parent_id):
        >       return self.get_variations(parent_id).next()[0]
        E       IndexError: list index out of range
        """
        delta_path = 'meta.lc_wn_regular_price'

        product_client_class = self.settings.slave_download_client_class
        product_client_args = self.settings.slave_download_client_args
        with product_client_class(**product_client_args) as client:
            first_prod_raw = client.get_first_variable_product()
            parent_pkey,  = tuple(self.raw_get_core_paths(
                client, first_prod_raw, [client.primary_key_handle]
            ))

        var_client_class = self.settings.slave_var_sync_client_class
        var_client_args = self.settings.slave_var_sync_client_args
        with var_client_class(**var_client_args) as client:

            # TODO: fails here, see docstring
            first_var_raw = client.get_first_variation(parent_pkey)
            value, var_pkey = tuple(self.raw_get_core_paths(
                client, first_var_raw, [delta_path, client.primary_key_handle]
            ))

            new_value = self.new_distinct_strint(value)

            self.check_update_target_path(
                client, var_pkey, delta_path, new_value, parent_pkey=parent_pkey
            )
            self.check_update_target_path(
                client, var_pkey, delta_path, value, parent_pkey=parent_pkey
            )

    def test_upload_delete_var_meta(self):
        delta_path = 'meta.lc_wn_regular_price'

        product_client_class = self.settings.slave_download_client_class
        product_client_args = self.settings.slave_download_client_args
        with product_client_class(**product_client_args) as client:
            first_prod_raw = client.get_first_variable_product()
            parent_pkey,  = tuple(self.raw_get_core_paths(
                client, first_prod_raw, [client.primary_key_handle]
            ))

        var_client_class = self.settings.slave_var_sync_client_class
        var_client_args = self.settings.slave_var_sync_client_args
        with var_client_class(**var_client_args) as client:
            first_var_raw = client.get_first_variation(parent_pkey)
            value, var_pkey = tuple(self.raw_get_core_paths(
                client, first_var_raw, [delta_path, client.primary_key_handle]
            ))

            self.check_delete_target_path(
                client, var_pkey, delta_path, parent_pkey=parent_pkey
            )
            self.check_update_target_path(
                client, var_pkey, delta_path, value, parent_pkey=parent_pkey
            )

@pytest.mark.local
class TestAttrSyncClientWC(TestProdSyncClient):
    def test_get_first_attr(self):
        pass

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
            self.assertIn(client.primary_key_handle, response.json())
            img_id = client.get_data_core(response.json(), client.primary_key_handle)
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
            response_core = self.response_extract_core(client, response)
            self.assertIn(client.primary_key_handle, response.json())
            img_id = client.coldata_class.get_from_path(
                response_core, client.primary_key_handle
            )
            response = client.upload_changes_core(img_id, new_img_core)
            response_core = self.response_extract_core(client, response)
            self.assertEqual(
                response_core['title'], title
            )
            self.assertEqual(
                response_core['post_excerpt'], content
            )
            self.assertEqual(
                SanitationUtils.sanitize_cell(response_core['post_content']),
                SanitationUtils.sanitize_cell(content)
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
