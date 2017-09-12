""" Boilerplate Test Cases common to merger and generator """

import os
import traceback
import tempfile
import unittest
from pprint import pformat

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

    def fail_syncupdate_assertion(self, exc, sync_update):
        msg = "failed assertion: \nITEMS:\n%s\nUPDATE:\n%s\nTRACEBACK:\n%s" % (
            pformat(sync_update.sync_warnings.items()),
            sync_update.tabulate(tablefmt='simple'),
            traceback.format_exc(exc),
        )
        raise AssertionError(msg)

    def print_update(self, update):
        print(
            (
                "%s\n---\nM:%s\n%s\nS:%s\n%s\nwarnings"
                ":\n%s\npasses:\n%s\nreflections:\n%s"
            ) % (
                update,
                update.old_m_object,
                pformat(dict(update.old_m_object)),
                update.old_s_object,
                pformat(dict(update.old_s_object)),
                update.display_sync_warnings(),
                update.display_sync_passes(),
                update.display_sync_reflections(),
            )
        )

    def make_temp_with_lines(self, filename, lines, suffix=''):
        """ Safely create a new temp file with the contents of filename at lines. """
        source = os.path.basename(filename)
        with open(filename) as in_file:
            in_contents = in_file.readlines()
            new_contents = [
                in_contents[line] for line in lines
            ]
            _, new_filename = tempfile.mkstemp('%s_%s' % (source, suffix))
            with open(new_filename, 'w+') as new_file:
                new_file.writelines(new_contents)
            return new_filename
