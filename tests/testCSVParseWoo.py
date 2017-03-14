import os
from unittest import TestCase, main, skip, TestSuite, TextTestRunner

from context import woogenerator
from woogenerator.coldata import ColData_Woo
from woogenerator.parsing.csvparse_woo import ImportWooProduct, CSVParse_Woo, CSVParse_TT, WooProdList
from woogenerator.utils import TimeUtils, Registrar, SanitationUtils

from context import tests_datadir

class TestCSVParseWoo(TestCase):

    def setUp(self):
        importName = TimeUtils.getMsTimeStamp()

        self.genPath = os.path.join(tests_datadir, "generator_sample.csv")

        self.productParserArgs = {
            'importName': importName,
            'cols': ColData_Woo.getImportCols(),
            'defaults': ColData_Woo.getDefaults(),
        }

        for var in ['self.productParserArgs']:
            print var, eval(var)

        # Registrar.DEBUG_PROGRESS = True
        # Registrar.DEBUG_MESSAGE = True
        # Registrar.DEBUG_ERROR = True
        # Registrar.DEBUG_WARN = True
        # Registrar.DEBUG_SHOP = True
        # Registrar.DEBUG_MRO = True
        # Registrar.DEBUG_TREE = True
        # Registrar.DEBUG_PARSER = True
        # Registrar.DEBUG_GEN = True
        # Registrar.DEBUG_ABSTRACT = True
        # Registrar.DEBUG_WOO = True
        # Registrar.DEBUG_API = True
        CSVParse_TT.do_images = False
        CSVParse_TT.do_specials = False
        CSVParse_TT.do_dyns = False


    def testCSVParseTT(self):
        productParser = CSVParse_TT(
            **self.productParserArgs
        )

        productParser.analyseFile(self.genPath)

        Registrar.DEBUG_MRO = True

        print "number of objects: %s" % len(productParser.objects.values())
        print "number of items: %s" % len(productParser.items.values())
        print "number of products: %s" % len(productParser.products.values())
        prodList = WooProdList(productParser.products.values())
        print SanitationUtils.coerceBytes(prodList.tabulate(tablefmt='simple'))

        # sort_keys = lambda (ka, va), (kb, vb): cmp(ka, kb)

        # print "Categories:"
        # for key, category in sorted(WooParser.categories.items(), sort_keys):
        # print "%15s | %s" % (category.get('codesum', ''),
        # category.get('taxosum', ''))

        # print "Products:"
        # for product in WooParser.getProducts():
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
    main()

    # testSuite = TestSuite()
    # testSuite.addTest(TestCSVParseWoo('testCSVParseTT'))
    # TextTestRunner().run(testSuite)
