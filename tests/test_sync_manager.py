""" Boilerplate Test Cases common to merger and generator """

import unittest

from context import TESTS_DATA_DIR, get_testdata, woogenerator
from woogenerator.namespace.core import (MatchNamespace, ParserNamespace,
                                         SettingsNamespaceProto,
                                         UpdateNamespace)
from woogenerator.utils import Registrar, TimeUtils


class AbstractSyncManagerTestCase(unittest.TestCase):
    config_file = None
    settings_namespace_class = SettingsNamespaceProto
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

        self.parsers = ParserNamespace()
        self.matches = MatchNamespace()
        self.updates = UpdateNamespace()

        Registrar.DEBUG_ERROR = False
        Registrar.DEBUG_WARN = False
        Registrar.DEBUG_MESSAGE = False
        Registrar.DEBUG_PROGRESS = False
        if self.debug:
            Registrar.DEBUG_PROGRESS = True
            Registrar.DEBUG_MESSAGE = True
            Registrar.DEBUG_ERROR = True
            Registrar.DEBUG_WARN = True
