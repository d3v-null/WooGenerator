from os import sys, path
from time import sleep
from unittest import TestCase, main, skip, TestSuite, TextTestRunner

if __name__ == '__main__' and __package__ is None:
    sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

from source.sync_client_prod import *
from source.coldata import ColData_Woo
from source.csvparse_abstract import ObjList
# from source.csvparse_gen import ProdList
from source.csvparse_shop import ShopProdList, ShopCatList
from source.csvparse_woo import ImportWooProduct, CSVParse_Woo
from source.csvparse_api import CSVParse_Woo_Api
import random

class testProdSyncClient(TestCase):
    def setUp(self):
        try:
            os.stat('source')
            os.chdir('source')
        except:
            pass

        yamlPath = "generator_config.yaml"

        importName = TimeUtils.getMsTimeStamp()
        inFolder = "../input/"
        outFolder = "../output/"

        with open(yamlPath) as stream:
            config = yaml.load(stream)
            # optionNamePrefix = 'test_'
            # optionNamePrefix = 'dummy_'
            optionNamePrefix = ''

            if 'inFolder' in config.keys():
                inFolder = config['inFolder']
            if 'outFolder' in config.keys():
                outFolder = config['outFolder']
            # if 'logFolder' in config.keys():
            #     logFolder = config['logFolder']

            wc_api_key = config.get(optionNamePrefix+'wc_api_key')
            wc_api_secret = config.get(optionNamePrefix+'wc_api_secret')
            wp_srv_offset = config.get(optionNamePrefix+'wp_srv_offset', 0)
            store_url = config.get(optionNamePrefix+'store_url', '')

            # taxoDepth = config.get('taxoDepth')
            # itemDepth = config.get('itemDepth')

        TimeUtils.setWpSrvOffset(wp_srv_offset)

        # json_uri = store_url + 'wp-json/wp/v2'

        self.wcApiParams = {
            'api_key':wc_api_key,
            'api_secret':wc_api_secret,
            'url':store_url
        }

        self.productParserArgs = {
            'importName': importName,
            # 'itemDepth': itemDepth,
            # 'taxoDepth': taxoDepth,
            'cols': ColData_Woo.getImportCols(),
            'defaults': ColData_Woo.getDefaults(),
        }

        for var in ['self.wcApiParams', 'self.productParserArgs']:
            print var, eval(var)

        Registrar.DEBUG_PROGRESS = True
        Registrar.DEBUG_MESSAGE = True
        Registrar.DEBUG_ERROR = True
        Registrar.DEBUG_WARN = True

        # Registrar.DEBUG_SHOP = True
        # Registrar.DEBUG_MRO = True
        # Registrar.DEBUG_TREE = True
        # Registrar.DEBUG_PARSER = True
        # Registrar.DEBUG_GEN = True
        # Registrar.DEBUG_ABSTRACT = True
        # Registrar.DEBUG_WOO = True
        Registrar.DEBUG_API = True
        # Registrar.DEBUG_PARSER = True
        # Registrar.DEBUG_UTILS = True
        CSVParse_Woo_Api.do_images = False
        CSVParse_Woo_Api.do_specials = False
        CSVParse_Woo_Api.do_dyns = False

    def testAnalyseRemote(self):
        productParser = CSVParse_Woo_Api(
            **self.productParserArgs
        )

        with ProdSyncClient_WC(self.wcApiParams) as client:
            client.analyseRemote(productParser, limit=20)

        prodList = ShopProdList(productParser.products.values())
        print SanitationUtils.coerceBytes(prodList.tabulate(tablefmt='simple'))
        varList = ShopProdList(productParser.variations.values())
        print SanitationUtils.coerceBytes(varList.tabulate(tablefmt='simple'))
        catList = ShopCatList(productParser.categories.values())
        print SanitationUtils.coerceBytes(catList.tabulate(tablefmt='simple'))
        attrList = productParser.attributes.items()
        print SanitationUtils.coerceBytes(tabulate(attrList, headers='keys', tablefmt="simple"))

    def testUploadChanges(self):
        pkey = 99
        updates = {
            'regular_price': u'37.00'
        }
        with ProdSyncClient_WC(self.wcApiParams) as client:
            response = client.uploadChanges(pkey, updates)
            print response
            if hasattr(response, 'json'):
                print "testUploadChanges", response.json()

    def testUploadChangesMeta(self):
        pkey = 99
        updates = OrderedDict([
            ('custom_meta',OrderedDict([
                ('lc_wn_regular_price', u'37.00')
            ]))
        ])
        with ProdSyncClient_WC(self.wcApiParams) as client:
            response = client.uploadChanges(pkey, updates)
            wn_regular_price = response.json()['product']['meta']['lc_wn_regular_price']
            print response
            if hasattr(response, 'json'):
                print "testUploadChangesMeta", response.json()
            self.assertEqual(wn_regular_price,'37.00')

    def testUploadDeleteMeta(self):
        pkey = 99
        updates = OrderedDict([
            ('custom_meta',OrderedDict([
                ('lc_wn_regular_price', u'')
            ]))
        ])
        with ProdSyncClient_WC(self.wcApiParams) as client:
            response = client.uploadChanges(pkey, updates)
            print response
            if hasattr(response, 'json'):
                print "testUploadDeleteMeta", response.json()
            wn_regular_price = response.json()['product']['meta'].get('lc_wn_regular_price')
            self.assertEqual(wn_regular_price,'')
            # self.assertNotIn('lc_wn_regular_price', response.json()['product']['meta'])

    def testUploadChangesVariation(self):
        pkey = 41
        updates = OrderedDict([
            ('weight', u'11.0')
        ])
        with ProdSyncClient_WC(self.wcApiParams) as client:
            response = client.uploadChanges(pkey, updates)
            print response
            if hasattr(response, 'json'):
                print "testUploadChangesVariation", response.json()
            description = response.json()['product']['weight']
            self.assertEqual(description,'11.0')

    def testUploadChangesVariationMeta(self):
        pkey = 41
        expected_result = str(random.randint(1,100))
        updates = OrderedDict([
            ('custom_meta',OrderedDict([
                ('lc_dn_regular_price', expected_result)
            ]))
        ])
        with ProdSyncClient_WC(self.wcApiParams) as client:
            response = client.uploadChanges(pkey, updates)
            print response
            if hasattr(response, 'json'):
                print "testUploadChangesVariationMeta", response.json()
            # self.assertIn('meta_test_key', str(response.json()))
            self.assertIn('lc_dn_regular_price', (response.json()['product']['meta']))
            wn_regular_price = response.json()['product']['meta']['lc_dn_regular_price']
            self.assertEqual(wn_regular_price, expected_result)

    def testUploadDeleteVariationMeta(self):
        pkey = 41
        updates = OrderedDict([
            ('custom_meta',OrderedDict([
                ('lc_wn_regular_price', u'')
            ]))
        ])
        with ProdSyncClient_WC(self.wcApiParams) as client:
            response = client.uploadChanges(pkey, updates)
            print response
            if hasattr(response, 'json'):
                print "testUploadDeleteVariationMeta", response.json()
            wn_regular_price = response.json()['product']['meta'].get('lc_wn_regular_price')
            self.assertFalse(wn_regular_price)

    def testGetSinglePage(self):
        with ProdSyncClient_WC(self.wcApiParams) as client:
            response = client.client.get('products?page=9')
            print response
            if hasattr(response, 'json'):
                print "testUploadChangesEmpty", response.json()

if __name__ == '__main__':
    # main()

    testSuite = TestSuite()
    # testSuite.addTest(testProdSyncClient('testUploadChanges'))
    # testSuite.addTest(testProdSyncClient('testUploadChangesMeta'))
    # testSuite.addTest(testProdSyncClient('testUploadDeleteMeta'))
    # testSuite.addTest(testProdSyncClient('testUploadChangesVariation'))
    # testSuite.addTest(testProdSyncClient('testUploadChangesVariationMeta'))
    # testSuite.addTest(testProdSyncClient('testUploadDeleteVariationMeta'))
    testSuite.addTest(testProdSyncClient('testGetSinglePage'))
    TextTestRunner().run(testSuite)
