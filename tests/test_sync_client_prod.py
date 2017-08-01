import random
import unittest
from collections import OrderedDict

from context import woogenerator
from tests.test_sync_client import AbstractSyncClientTestCase
from woogenerator.client.prod import CatSyncClientWC, ProdSyncClientWC
from woogenerator.parsing.api import CsvParseWooApi
from woogenerator.parsing.shop import ShopCatList, ShopProdList
from woogenerator.utils import TimeUtils
from woogenerator.coldata import ColDataWoo


@unittest.skip("have not created config file yet")
class TestProdSyncClient(AbstractSyncClientTestCase):

    def __init__(self, *args, **kwargs):
        super(TestProdSyncClient, self).__init__(*args, **kwargs)
        self.wc_api_params = {}
        self.product_parser_args = {}

    def process_config(self, config):
        # if 'in_folder' in config.keys():
        #     in_folder = config['in_folder']
        # if 'out_folder' in config.keys():
        #     out_folder = config['out_folder']
        # if 'logFolder' in config.keys():
        #     logFolder = config['logFolder']

        wc_api_key = config.get(self.optionNamePrefix + 'wc_api_key')
        wc_api_secret = config.get(self.optionNamePrefix + 'wc_api_secret')
        wp_srv_offset = config.get(self.optionNamePrefix + 'wp_srv_offset', 0)
        store_url = config.get(self.optionNamePrefix + 'store_url', '')

        # taxo_depth = config.get('taxo_depth')
        # item_depth = config.get('item_depth')

        TimeUtils.set_wp_srv_offset(wp_srv_offset)

        # json_uri = store_url + 'wp-json/wp/v2'z

        self.wc_api_params = {
            'api_key': wc_api_key,
            'api_secret': wc_api_secret,
            'url': store_url
        }

        self.product_parser_args = {
            'import_name': self.import_name,
            # 'item_depth': item_depth,
            # 'taxo_depth': taxo_depth,
            'cols': ColDataWoo.get_import_cols(),
            'defaults': ColDataWoo.get_defaults(),
        }

    def setUp(self):
        super(TestProdSyncClient, self).setUp()

        # for var in ['wc_api_params', 'product_parser_args']:
        #     print var, getattr(self, var)

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
        CsvParseWooApi.do_images = False
        CsvParseWooApi.do_specials = False
        CsvParseWooApi.do_dyns = False

    def test_read(self):
        response = []
        with ProdSyncClientWC(self.wc_api_params) as client:
            response = client.get_iterator()
        # print tabulate(list(response)[:10], headers='keys')

        self.assertTrue(response)

    def test_analyse_remote(self):
        product_parser = CsvParseWooApi(
            **self.product_parser_args
        )

        with ProdSyncClientWC(self.wc_api_params) as client:
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
        with ProdSyncClientWC(self.wc_api_params) as client:
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
        with ProdSyncClientWC(self.wc_api_params) as client:
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
        with ProdSyncClientWC(self.wc_api_params) as client:
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
        with ProdSyncClientWC(self.wc_api_params) as client:
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
        with ProdSyncClientWC(self.wc_api_params) as client:
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
        with ProdSyncClientWC(self.wc_api_params) as client:
            response = client.upload_changes(pkey, updates)
            # print response
            # if hasattr(response, 'json'):
            #     print "test_upload_delete_var_meta", response.json()
            wn_regular_price = response.json()['product'][
                'meta'].get('lc_wn_regular_price')
            self.assertFalse(wn_regular_price)

    def test_get_single_page(self):
        with ProdSyncClientWC(self.wc_api_params) as client:
            response = client.service.get('products?page=9')
            self.assertTrue(response)
            # print response
            # if hasattr(response, 'json'):
            #     print "test_upload_changes_empty", response.json()

    def test_cat_sync_client(self):
        with CatSyncClientWC(self.wc_api_params) as client:
            for page in client.get_iterator():
                self.assertTrue(page)
                # print page

if __name__ == '__main__':
    unittest.main()

    # testSuite = TestSuite()
    # testSuite.addTest(TestProdSyncClient('test_upload_changes'))
    # testSuite.addTest(TestProdSyncClient('test_upload_changes_meta'))
    # testSuite.addTest(TestProdSyncClient('test_upload_delete_meta'))
    # testSuite.addTest(TestProdSyncClient('test_upload_changes_variation'))
    # testSuite.addTest(TestProdSyncClient('test_upload_changes_var_meta'))
    # testSuite.addTest(TestProdSyncClient('test_upload_delete_var_meta'))
    # testSuite.addTest(TestProdSyncClient('test_get_single_page'))
    # testSuite.addTest(TestProdSyncClient('test_read'))
    # testSuite.addTest(TestProdSyncClient('test_upload_changes_var_meta'))
    # TextTestRunner().run(testSuite)
