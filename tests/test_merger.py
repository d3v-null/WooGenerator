from __future__ import print_function
import os
import sys
from unittest import TestCase, main, skip, TestSuite, TextTestRunner
import argparse

from context import woogenerator
from woogenerator.coldata import ColDataWoo
from woogenerator.parsing.woo import ImportWooProduct, CsvParseWoo, CsvParseTT, WooProdList
from woogenerator.utils import TimeUtils, Registrar, SanitationUtils
from woogenerator.utils import (HtmlReporter, ProgressCounter, Registrar,
                                SanitationUtils, TimeUtils, DebugUtils)
from woogenerator.config import (ArgumentParserUser, SettingsNamespaceUser, 
                                 init_settings, ParsersNamespace)
from woogenerator.merger import populate_master_parsers

from context import tests_datadir

class TestGenerator(TestCase):
    def setUp(self):

        self.settings = SettingsNamespaceUser()
        self.settings.local_work_dir = tests_datadir
        self.settings.local_live_config = None
        self.settings.local_test_config = "merger_config_test.yaml"
        self.settings.master_dialect_suggestion = "ActOut"
        self.settings.download_master = False
        self.settings.master_file = os.path.join(tests_datadir, "100_users.csv")
        # self.settings.master_parse_limit = 10
        self.override_args = ""
        self.parsers = ParsersNamespace()

        Registrar.DEBUG_MESSAGE = True
        Registrar.DEBUG_ERROR = True
        # Registrar.DEBUG_ABSTRACT = True
        # Registrar.DEBUG_PARSER = True

    def test_init_settings(self):
        self.settings = init_settings(
            settings=self.settings,
            override_args=self.override_args,
            argparser_class=ArgumentParserUser
        )
        self.assertEqual(self.settings.master_name, "ACT")
        self.assertEqual(self.settings.slave_name, "WORDPRESS")
        self.assertEqual(self.settings.download_master, False)
        self.assertEqual(
            self.settings.master_client_args["limit"],
            self.settings.master_parse_limit
        )
        self.assertEqual(self.settings.master_client_args["dialect_suggestion"], "ActOut")

    def test_populate_master_parsers(self):
        self.test_init_settings()
        # self.settings.product_parser_args = {
        #     'import_name': self.settings.import_name,
        #     'item_depth': self.settings.item_depth,
        #     'taxo_depth': self.settings.taxo_depth,
        # }

        self.parsers = populate_master_parsers(
            self.parsers,
            self.settings
        )

        #number of objects:
        self.assertEqual(
            len(self.parsers.master.objects.values()),
            99
        )

        obj_list = self.parsers.master.get_obj_list()
        print(SanitationUtils.coerce_bytes(obj_list.tabulate(tablefmt='simple')))

if __name__ == '__main__':
    main()
