import traceback
import unittest
from pprint import pformat

from context import get_testdata, TESTS_DATA_DIR, woogenerator
from woogenerator.namespace.core import (MatchNamespace, ParserNamespace,
                                         SettingsNamespaceProto,
                                         UpdateNamespace)
from woogenerator.conf.parser import ArgumentParserCommon
from woogenerator.utils import Registrar, TimeUtils


class TestSyncUpdateAbstract(unittest.TestCase):
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

        self.settings.init_settings(self.override_args)

        # with open(yaml_path) as stream:
        #     config = yaml.load(stream)
        #     merge_mode = config.get('merge-mode', 'sync')
        #     main_name = config.get('main-name', 'MASTER')
        #     subordinate_name = config.get('subordinate-name', 'SLAVE')
        #     default_last_sync = config.get('default-last-sync')
        #
        # SyncUpdateUsr.set_globals(
        #     main_name, subordinate_name, merge_mode, default_last_sync)

        Registrar.DEBUG_ERROR = False
        Registrar.DEBUG_WARN = False
        Registrar.DEBUG_MESSAGE = False
        Registrar.DEBUG_PROGRESS = False

        if self.debug:
            # FieldGroup.perform_post = True
            # FieldGroup.DEBUG_WARN = True
            # FieldGroup.DEBUG_MESSAGE = True
            # FieldGroup.DEBUG_ERROR = True
            # SyncUpdateUsr.DEBUG_WARN = True
            # SyncUpdateUsr.DEBUG_MESSAGE = True
            # SyncUpdateUsr.DEBUG_ERROR = True
            Registrar.DEBUG_ERROR = True
            Registrar.DEBUG_WARN = True
            Registrar.DEBUG_MESSAGE = True
            Registrar.DEBUG_PROGRESS = True
            Registrar.DEBUG_UPDATE = True
            # Registrar.DEBUG_USR = True
            # Registrar.DEBUG_CONTACT = True
            # Registrar.DEBUG_NAME = True
            # FieldGroup.DEBUG_CONTACT = True
            # FieldGroup.enforce_mandatory_keys = False

    def fail_syncupdate_assertion(self, exc, sync_update):
        msg = "failed assertion: %s\n%s\n%s" % (
            pformat(sync_update.sync_warnings.items()),
            sync_update.tabulate(tablefmt='simple'),
            traceback.format_exc(exc),
        )
        raise AssertionError(msg)
