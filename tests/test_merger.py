from __future__ import print_function
import os
import sys
from unittest import TestCase, main, skip, TestSuite, TextTestRunner
import argparse

from context import woogenerator
from woogenerator.coldata import ColDataWoo
from woogenerator.parsing.woo import ImportWooProduct, CsvParseWoo, CsvParseTT, WooProdList
from woogenerator.utils import Registrar, SanitationUtils
from woogenerator.conf.parser import ArgumentParserUser
from woogenerator.conf.namespace import init_settings, ParsersNamespace, SettingsNamespaceUser
from woogenerator.merger import populate_master_parsers, populate_slave_parsers

from context import tests_datadir

class TestGenerator(TestCase):
    def setUp(self):

        self.settings = SettingsNamespaceUser()
        self.settings.local_work_dir = tests_datadir
        self.settings.local_live_config = None
        self.settings.local_test_config = "merger_config_test.yaml"
        self.settings.master_dialect_suggestion = "ActOut"
        self.settings.download_master = False
        self.settings.master_file = os.path.join(tests_datadir, "merger_master_sample.csv")
        self.settings.slave_file = os.path.join(tests_datadir, "merger_slave_sample.csv")
        # self.settings.master_parse_limit = 10
        # self.settings.slave_parse_limit = 10
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

        self.parsers = populate_master_parsers(
            self.parsers, self.settings
        )

        obj_list = self.parsers.master.get_obj_list()

        #number of objects:
        self.assertEqual(len(obj_list), 99)

        print(SanitationUtils.coerce_bytes(obj_list.tabulate(tablefmt='simple')))

    def test_populate_slave_parsers(self):
        self.test_init_settings()

        self.parsers = populate_slave_parsers(
            self.parsers, self.settings
        )

        obj_list = self.parsers.slave.get_obj_list()

        self.assertEqual(len(obj_list), 98)

        print(SanitationUtils.coerce_bytes(obj_list.tabulate(tablefmt='simple')))

        self.assertTrue(len(obj_list))

if __name__ == '__main__':
    main()
