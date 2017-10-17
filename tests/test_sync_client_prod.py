import random
import unittest
from collections import OrderedDict

from tests.test_sync_client import AbstractSyncClientTestCase

from context import TESTS_DATA_DIR, woogenerator
from woogenerator.client.prod import CatSyncClientWC, ProdSyncClientWC
from woogenerator.coldata import ColDataWoo
from woogenerator.conf.parser import ArgumentParserProd
from woogenerator.namespace.prod import SettingsNamespaceProd
from woogenerator.parsing.api import ApiParseWoo
from woogenerator.parsing.shop import ShopCatList, ShopProdList
from woogenerator.utils import TimeUtils


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

@unittest.skip("Destructive tests not mocked yet")
# TODO: mock these tests
class TestProdSyncClientDestructive(TestProdSyncClient):
    def setUp(self):
        super(TestProdSyncClient, self).setUp()

        # Registrar.DEBUG_SHOP = True
        # Registrar.DEBUG_MRO = True
        # Registrar.DEBUG_TREE = True
        # Registrar.DEBUG_PARSER = True
        # Registrar.DEBUG_GEN = True
        # Registrar.DEBUG_ABSTRACT = True
        # Registrar.DEBUG_WOO = True
        # Registrar.DEBUG_API = True
        # Registrar.DEBUG_PARSER = True
        # Registrar.DEBUG_UTILS = True
        ApiParseWoo.do_images = False
        ApiParseWoo.do_specials = False
        ApiParseWoo.do_dyns = False

    def test_read(self):
        response = []
        with ProdSyncClientWC(self.settings.slave_wc_api_params) as client:
            response = client.get_iterator()
        # print tabulate(list(response)[:10], headers='keys')

        self.assertTrue(response)

    def test_analyse_remote(self):
        product_parser = ApiParseWoo(
            **self.settings.master_parser_args
        )

        with ProdSyncClientWC(self.settings.slave_wc_api_params) as client:
            client.analyse_remote(product_parser, limit=20)

        prod_list = ShopProdList(product_parser.products.values())
        self.assertTrue(prod_list)
        # print
        # SanitationUtils.coerce_bytes(prod_list.tabulate(tablefmt='simple'))
        var_list = ShopProdList(product_parser.variations.values())
        self.assertTrue(var_list)
        # print
        # SanitationUtils.coerce_bytes(var_list.tabulate(tablefmt='simple'))
        cat_list = ShopCatList(product_parser.categories.values())
        self.assertTrue(cat_list)
        # print
        # SanitationUtils.coerce_bytes(cat_list.tabulate(tablefmt='simple'))
        attr_list = product_parser.attributes.items()
        self.assertTrue(attr_list)
        # print SanitationUtils.coerce_bytes(tabulate(attr_list, headers='keys',
        # tablefmt="simple"))

    def test_upload_changes(self):
        pkey = 99
        updates = {
            'regular_price': u'37.00'
        }
        with ProdSyncClientWC(self.settings.slave_wc_api_params) as client:
            response = client.upload_changes(pkey, updates)
            self.assertTrue(response)
            # print response
            # if hasattr(response, 'json'):
            #     print "test_upload_changes", response.json()

    def test_upload_changes_meta(self):
        pkey = 99
        updates = OrderedDict([
            ('custom_meta', OrderedDict([
                ('lc_wn_regular_price', u'37.00')
            ]))
        ])
        with ProdSyncClientWC(self.settings.slave_wc_api_params) as client:
            response = client.upload_changes(pkey, updates)
            wn_regular_price = response.json()['product']['meta'][
                'lc_wn_regular_price']
            # print response
            # if hasattr(response, 'json'):
            #     print "test_upload_changes_meta", response.json()
            self.assertEqual(wn_regular_price, '37.00')

    def test_upload_delete_meta(self):
        pkey = 99
        updates = OrderedDict([
            ('custom_meta', OrderedDict([
                ('lc_wn_regular_price', u'')
            ]))
        ])
        with ProdSyncClientWC(self.settings.slave_wc_api_params) as client:
            response = client.upload_changes(pkey, updates)
            # print response
            # if hasattr(response, 'json'):
            #     print "test_upload_delete_meta", response.json()
            wn_regular_price = response.json()['product'][
                'meta'].get('lc_wn_regular_price')
            self.assertEqual(wn_regular_price, '')
            # self.assertNotIn('lc_wn_regular_price', response.json()['product']['meta'])

    def test_upload_changes_variation(self):
        pkey = 41
        updates = OrderedDict([
            ('weight', u'11.0')
        ])
        with ProdSyncClientWC(self.settings.slave_wc_api_params) as client:
            response = client.upload_changes(pkey, updates)
            # print response
            # if hasattr(response, 'json'):
            #     print "test_upload_changes_variation", response.json()
            description = response.json()['product']['weight']
            self.assertEqual(description, '11.0')

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

    def test_get_single_page(self):
        with ProdSyncClientWC(self.settings.slave_wc_api_params) as client:
            response = client.service.get('products?page=9')
            self.assertTrue(response)
            # print response
            # if hasattr(response, 'json'):
            #     print "test_upload_changes_empty", response.json()

    def test_cat_sync_client(self):
        with CatSyncClientWC(self.settings.slave_wc_api_params) as client:
            for page in client.get_iterator():
                self.assertTrue(page)
                # print page

class TestProdSyncClientConstructors(TestProdSyncClient):
    # def test_make_usr_m_up_client(self):
    #     self.settings.update_master = True
    #     master_client_args = self.settings.master_upload_client_args
    #     master_client_class = self.settings.master_upload_client_class
    #     with master_client_class(**master_client_args) as master_client:
    #         self.assertTrue(master_client)

    def test_make_usr_s_up_client(self):
        self.settings.update_slave = True
        slave_client_args = self.settings.slave_upload_client_args
        # self.assertTrue(slave_client_args['connect_params']['api_key'])
        slave_client_class = self.settings.slave_upload_client_class
        with slave_client_class(**slave_client_args) as slave_client:
            self.assertTrue(slave_client)

    @unittest.skipIf(
        TestProdSyncClient.local_work_dir == TESTS_DATA_DIR,
        "won't work with dummy conf"
    )
    def test_make_usr_m_down_client(self):
        self.settings.download_master = True
        master_client_args = self.settings.master_download_client_args
        master_client_class = self.settings.master_download_client_class
        with master_client_class(**master_client_args) as master_client:
            self.assertTrue(master_client)

    def test_make_usr_s_down_client(self):
        self.settings.download_slave = True
        slave_client_args = self.settings.slave_download_client_args
        self.assertTrue(slave_client_args['connect_params']['api_key'])
        slave_client_class = self.settings.slave_download_client_class
        with slave_client_class(**slave_client_args) as slave_client:
            self.assertTrue(slave_client)

class TestProdSyncClientXero(TestProdSyncClient):
    # debug = True

    @unittest.skipIf(
        TestProdSyncClient.local_work_dir == TESTS_DATA_DIR,
        "won't work with dummy conf"
    )
    def test_read(self):
        self.settings.download_slave = True
        self.settings.schema = 'XERO'
        # if self.debug: import pudb; pudb.set_trace()
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
