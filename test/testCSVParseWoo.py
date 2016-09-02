from os import sys, path
from time import sleep
from unittest import TestCase, main, skip, TestSuite, TextTestRunner

if __name__ == '__main__' and __package__ is None:
    sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

from source.sync_client_prod import *
from source.coldata import ColData_Woo
from source.csvparse_woo import ImportWooProduct, CSVParse_Woo, CSVParse_TT, WooProdList


class testCSVParseWoo(TestCase):

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
            optionNamePrefix = 'test_'
            optionNamePrefix = ''

            if 'inFolder' in config.keys():
                inFolder = config['inFolder']
            if 'outFolder' in config.keys():
                outFolder = config['outFolder']
            if 'logFolder' in config.keys():
                logFolder = config['logFolder']

            taxoDepth = config.get('taxoDepth')
            itemDepth = config.get('itemDepth')

        self.genPath = inFolder + "generator.csv"

        self.productParserArgs = {
            'importName': importName,
            'itemDepth': itemDepth,
            'taxoDepth': taxoDepth,
            'cols': ColData_Woo.getImportCols(),
            'defaults': ColData_Woo.getDefaults(),
        }

        for var in ['self.productParserArgs']:
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
    # main()

    testSuite = TestSuite()
    testSuite.addTest(testCSVParseWoo('testCSVParseTT'))
    TextTestRunner().run(testSuite)
