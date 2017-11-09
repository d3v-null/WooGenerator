from context import TESTS_DATA_DIR, get_testdata, woogenerator

import unittest
# import argparse
import pytest
import logging
from woogenerator.namespace.core import (
    MatchNamespace, ParserNamespace, SettingsNamespaceProto, UpdateNamespace
)
from woogenerator.conf.parser import ArgumentParserCommon, ArgumentParserProd
from woogenerator.utils import Registrar, TimeUtils


@pytest.mark.usefixtures("debug")
class AbstractWooGeneratorTestCase(unittest.TestCase):
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
        if self.debug:
            self.settings.verbosity = 3
            self.settings.quiet = False
            logging.basicConfig(level=logging.DEBUG)
        else:
            self.settings.verbosity = 0
            self.settings.quiet = True
            logging.basicConfig(level=logging.WARN)
            Registrar.DEBUG_MESSAGE = False
            Registrar.DEBUG_PROGRESS = False
            Registrar.DEBUG_TRACE = False
