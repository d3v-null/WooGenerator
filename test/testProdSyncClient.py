from os import sys, path
from time import sleep
from unittest import TestCase, main, skip, TestSuite, TextTestRunner

if __name__ == '__main__' and __package__ is None:
    sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

from source.sync_client_prod import *
from source.coldata import ColData_Woo
from source.csvparse_abstract import ObjList
from source.CSVParse_Gen_Tree import ProdList
from source.csvparse_woo import ImportWooProduct, CSVParse_Woo, CSVParse_Woo_Api

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
            optionNamePrefix = 'test_'
            optionNamePrefix = ''

            if 'inFolder' in config.keys():
                inFolder = config['inFolder']
            if 'outFolder' in config.keys():
                outFolder = config['outFolder']
            if 'logFolder' in config.keys():
                logFolder = config['logFolder']

            wc_api_key = config.get(optionNamePrefix+'wc_api_key')
            wc_api_secret = config.get(optionNamePrefix+'wc_api_secret')
            wp_srv_offset = config.get(optionNamePrefix+'wp_srv_offset', 0)
            store_url = config.get(optionNamePrefix+'store_url', '')

            taxoDepth = config.get('taxoDepth')
            itemDepth = config.get('itemDepth')

        TimeUtils.setWpSrvOffset(wp_srv_offset)

        json_uri = store_url + 'wp-json/wp/v2'

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
        Registrar.DEBUG_API = True
        Registrar.DEBUG_ABSTRACT = True
        Registrar.DEBUG_WOO = True

    def testAnalyseRemote(self):
        productParser = CSVParse_Woo_Api(
            **self.productParserArgs
        )

        with ProdSyncClient_WC(self.wcApiParams) as client:
            client.analyseRemote(productParser, limit=11)

        prodList = ProdList(productParser.products.values())
        print SanitationUtils.coerceBytes(prodList.tabulate(tablefmt='simple'))


if __name__ == '__main__':
    # main()

    testSuite = TestSuite()
    testSuite.addTest(testProdSyncClient('testAnalyseRemote'))
    TextTestRunner().run(testSuite)
