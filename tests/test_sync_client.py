import unittest

from context import TESTS_DATA_DIR, get_testdata, woogenerator
from woogenerator.client.core import SyncClientGDrive
from woogenerator.client.prod import ProdSyncClientWC
from woogenerator.client.user import UsrSyncClientWP
from woogenerator.conf.parser import ArgumentParserCommon, ArgumentParserProd
from woogenerator.namespace.core import SettingsNamespaceProto, init_settings
from woogenerator.namespace.prod import SettingsNamespaceProd
from woogenerator.utils import Registrar, TimeUtils


class AbstractSyncClientTestCase(unittest.TestCase):
    config_file = None
    settings_namespace_class = SettingsNamespaceProto
    argument_parser_class = ArgumentParserCommon
    local_work_dir = TESTS_DATA_DIR
    override_args = ''
    debug = False

    def setUp(self):
        self.import_name = TimeUtils.get_ms_timestamp()

        self.settings = self.settings_namespace_class()
        self.settings.local_work_dir = self.local_work_dir
        self.settings.local_live_config = None
        self.settings.local_test_config = self.config_file
        self.settings.verbosity = 0
        self.settings.quiet = True

        self.settings = init_settings(
            settings=self.settings,
            override_args=self.override_args,
            argparser_class=self.argument_parser_class
        )

        Registrar.DEBUG_ERROR = False
        Registrar.DEBUG_WARN = False
        Registrar.DEBUG_MESSAGE = False
        Registrar.DEBUG_PROGRESS = False
        if self.debug:
            Registrar.DEBUG_PROGRESS = True
            Registrar.DEBUG_MESSAGE = True
            Registrar.DEBUG_ERROR = True


@unittest.skip('Tests not mocked yet')
class TestSyncClient(AbstractSyncClientTestCase):
    config_file = 'generator_config_test.yaml'
    settings_namespace_class = SettingsNamespaceProd
    argument_parser_class = ArgumentParserProd

    def __init__(self, *args, **kwargs):
        super(TestSyncClient, self).__init__(*args, **kwargs)
        self.slave_wp_api_params = {}
        self.product_parser_args = {}

        Registrar.DEBUG_API = True

    @unittest.skip("No dummy fileID")
    def test_g_drive_read(self):
        # TODO: Mock out GDrive
        with SyncClientGDrive(self.settings.g_drive_params) as client:
            self.assertTrue(client.drive_file)
            self.assertTrue(client.get_gm_modtime(self.settings.g_drive_params['gen_gid']))
            # print "drive file:", client.drive_file
            # print "GID", client.get_gm_modtime(self.settings.g_drive_params['gen_gid'])

    def test_prod_sync_client_wc_read(self):
        api_params = self.settings.slave_wc_api_params
        api_params.update(timeout=1)
        with ProdSyncClientWC(api_params) as client:
            # print client.service.get('products').text
            pages = list(client.get_iterator('products'))
            self.assertTrue(pages)
            # for pagecount, page in enumerate(pages):
            #     # print "PAGE %d: " % pagecount
            #     if 'products' in page:
            #         for page_product in page.get('products'):
            #             if 'id' in page_product:
            #                 prod_str = page_product['id']
            #             else:
            #                 prod_str = str(page_product)[:100]
            #             self.assertTrue(prod_str)
            #             # print "-> PRODUCT: ", prod_str

    # @unittest.skip('out of scope')
    def test_usr_sync_client_wp_read(self):
        with UsrSyncClientWP(self.settings.slave_wp_api_params) as client:
            # print client.service.get('users').text
            pages = list(client.get_iterator('users'))
            self.assertTrue(pages)
            # for pagecount, page in enumerate(pages):
            #     # print "PAGE %d: " % pagecount
            #     if 'users' in page:
            #         for page_user in page.get('users'):
            #             self.assertTrue(page_user)
            #             # print "-> USER: ", str(page_user)[:50]


if __name__ == '__main__':
    unittest.main()
    # testSuite = unittest.TestSuite()
    # testSuite.addTest(TestSyncClient('test_usr_sync_client_wp_read'))
    # testSuite.addTest(TestSyncClient('test_prod_sync_client_wc_read'))
    # unittest.TextTestRunner().run(testSuite)
