""" Boilerplate Test Cases common to merger and generator """

from __future__ import print_function

import os
import tempfile
import traceback
import unittest
from pprint import pformat

from context import TESTS_DATA_DIR, get_testdata, woogenerator
from woogenerator.namespace.core import (MatchNamespace, ParserNamespace,
                                         ResultsNamespace,
                                         SettingsNamespaceProto,
                                         UpdateNamespace)
from woogenerator.utils import Registrar, TimeUtils

from .abstract import AbstractWooGeneratorTestCase


class AbstractSyncManagerTestCase(AbstractWooGeneratorTestCase):

    def setUp(self):
        super(AbstractSyncManagerTestCase, self).setUp()
        self.matches = MatchNamespace()
        self.updates = UpdateNamespace()
        self.results = ResultsNamespace()

    @property
    def parsers(self):
        if not hasattr(self, '_parsers'):
            self._parsers = ParserNamespace()
        return self._parsers

    def print_debug_config(self):
        print("debug: %s, verbosity: %s, quiet: %s, Reg.DEBUG_MESSAGE: %s, Reg.DEBUG_WARN: %s" % (
            self.debug, self.settings.verbosity, self.settings.quiet,
            Registrar.DEBUG_MESSAGE, Registrar.DEBUG_WARN
        ))

    def print_matches_summary(self, matches):
        print("matches.globals (%d):\n%s" % (
            len(matches.globals), matches.globals.tabulate())
        )
        print("matches.masterless (%d):\n%s" % (
            len(matches.masterless), matches.masterless.tabulate())
        )
        print("matches.slaveless (%d):\n%s" % (
            len(matches.slaveless), matches.slaveless.tabulate())
        )
        if hasattr(matches, 'valid'):
            print("matches.valid (%d):\n%s" % (
                len(matches.valid), matches.valid.tabulate())
            )
        if hasattr(matches, 'invalid'):
            print("matches.invalid (%d):\n%s" % (
                len(matches.invalid), matches.invalid.tabulate())
            )
        if hasattr(matches, 'duplicate'):
            print("matches.duplicate (%d):\n%s" % (
                len(matches.duplicate), pformat(matches.duplicate.items()))
            )

    def print_updates_summary(self, updates):
        print("delta_master updates(%d):\n%s" % (
            len(updates.delta_master), map(str, updates.delta_master))
        )
        print("delta_slave updates(%d):\n%s" % (
            len(updates.delta_slave), map(str, updates.delta_slave))
        )
        print("master updates(%d):\n%s" % (
            len(updates.master), map(str, updates.master))
        )
        # print("masterless updates(%d):\n%s" % (
        #     len(updates.masterless), map(str, updates.masterless))
        # )
        # print("slaveless updates(%d):\n%s" % (
        #     len(updates.slaveless), map(str, updates.slaveless))
        # )
        print("nonstatic_master updates(%d):\n%s" % (
            len(updates.nonstatic_master), map(str, updates.nonstatic_master))
        )
        print("nonstatic_slave updates(%d):\n%s" % (
            len(updates.nonstatic_slave), map(str, updates.nonstatic_slave))
        )
        print("problematic updates(%d):\n%s" % (
            len(updates.problematic), map(str, updates.problematic))
        )
        print("slave updates(%d):\n%s" % (
            len(updates.slave), map(str, updates.slave))
        )
        print("static updates(%d):\n%s" % (
            len(updates.static), map(str, updates.static))
        )
        if hasattr(updates, 'new_slaves'):
            print("new_slave updates(%d):\n%s" % (
                len(updates.new_slaves), map(str, updates.new_slaves))
            )
        if hasattr(updates, 'new_masters'):
            print("new_master updates(%d):\n%s" % (
                len(updates.new_masters), map(str, updates.new_masters))
            )
    def fail_syncupdate_assertion(self, exc, sync_update):
        msg = "failed assertion: \nITEMS:\n%s\nUPDATE:\n%s\nTRACEBACK:\n%s" % (
            pformat(sync_update.sync_warnings.items()),
            sync_update.tabulate(tablefmt='simple'),
            traceback.format_exc(exc),
        )
        raise AssertionError(msg)

    def print_update(self, update):
        old_m_object_dict = 'EMPTY'
        old_s_object_dict = 'EMPTY'
        if getattr(update, 'old_m_object_gen', {}):
            old_m_object_dict = pformat(update.old_m_object_gen.to_dict())
        if getattr(update, 'old_s_object_gen', {}):
            old_s_object_dict = pformat(update.old_s_object_gen.to_dict())
        print(
            (
                "%s%s\n---\nM:%s\n%s\nS:%s\n%s\nwarnings"
                ":\n%s\npasses:\n%s\nprobbos:\n%s"
            ) % (
                update,
                str(type(update)),
                update.old_m_object_gen,
                old_m_object_dict,
                update.old_s_object_gen,
                old_s_object_dict,
                update.display_sync_warnings(),
                update.display_sync_passes(),
                update.display_problematic_updates(),
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
