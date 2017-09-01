import os
import unittest
from unittest import TestCase

from context import woogenerator
from woogenerator.coldata import ColDataWoo
from woogenerator.parsing.woo import ImportWooProduct, CsvParseWoo, CsvParseTT, WooProdList
from woogenerator.utils import TimeUtils, Registrar, SanitationUtils

from context import TESTS_DATA_DIR


# TODO: fix this skip
@unittest.skip("not sure why this doesn't work yet")
class TestCSVParseWoo(TestCase):
    def setUp(self):
        import_name = TimeUtils.get_ms_timestamp()

        self.master_parser_args = {
            'import_name': import_name,
            'cols': ColDataWoo.get_import_cols(),
            'defaults': ColDataWoo.get_defaults(),
            'taxo_depth': 3,
            'item_depth': 2,
            'schema': 'CA'
        }

        # print("PPA: %s" % self.master_parser_args)

        # self.master_parser_args = {
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
        #     'import_name': '2017-07-21_09-17-50',
        #     'item_depth': 2,
        #     'schema': 'CA'
        # }

        self.gen_path = os.path.join(
            TESTS_DATA_DIR,
            "generator_master_dummy.csv"
        )

        self.analysis_kwargs = {
            'file_name': self.gen_path,
            'encoding': 'utf8',
            'dialect_suggestion': 'SublimeCsvTable',
            'limit': 10
        }

        for var in ['self.master_parser_args']:
            pass
            # print var, eval(var)

        Registrar.DEBUG_ERROR = False
        Registrar.DEBUG_WARN = False
        Registrar.DEBUG_MESSAGE = False
        Registrar.DEBUG_PROGRESS = False

        Registrar.DEBUG_PROGRESS = True
        Registrar.DEBUG_MESSAGE = True
        Registrar.DEBUG_ERROR = True
        Registrar.DEBUG_WARN = True
        Registrar.DEBUG_SHOP = True
        # Registrar.DEBUG_MRO = True
        # Registrar.DEBUG_TREE = True
        Registrar.DEBUG_PARSER = True
        # Registrar.DEBUG_GEN = True
        # Registrar.DEBUG_ABSTRACT = True
        # Registrar.DEBUG_WOO = True
        # Registrar.DEBUG_API = True
        CsvParseTT.do_images = False
        CsvParseTT.do_specials = False
        CsvParseTT.do_dyns = False

    def test_csv_parse_tt(self):
        product_parser = CsvParseTT(**self.master_parser_args)

        product_parser.analyse_file(
            **self.analysis_kwargs
        )

        Registrar.DEBUG_MRO = True

        # print "number of objects: %s" % len(product_parser.objects.values())
        # print "number of items: %s" % len(product_parser.items.values())
        # print "number of products: %s" % len(product_parser.products.values())
        prod_list = WooProdList(product_parser.products.values())
        self.assertTrue(prod_list)
        # print SanitationUtils.coerce_bytes(prod_list.tabulate(tablefmt='simple'))

        # sort_keys = lambda (ka, va), (kb, vb): cmp(ka, kb)

        # print "Categories:"
        # for key, category in sorted(WooParser.categories.items(), sort_keys):
        # print "%15s | %s" % (category.get('codesum', ''),
        # category.get('taxosum', ''))

        # print "Products:"
        # for product in WooParser.get_products():
        # print "%15s | %s" % (product.get('codesum', ''),
        # product.get('itemsum', '')), product.get('dprplist')

        # print "Variations:"
        # for sku, variation in WooParser.variations.items():
        #     print "%15s | %s" % (sku, variation.get('itemsum', ''))

        # print "Attributes"
        # for attr, vals in WooParser.attributes.items():
        #     print "%15s | %s" % (attr[:15], "|".join(map(str,vals)))

        # for img, items in WooParser.images.items():
        #         print "%s " % img
        #         for item in items:
        # print " -> (%4d) %15s " % (item['rowcount'], item['codesum'])


if __name__ == '__main__':
    unittest.main()
