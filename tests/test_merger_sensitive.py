"""
Sensitive test cases that should not be uploaded to GitHub
"""

from __future__ import print_function

import unittest

from context import SENSITIVE_DATA_DIR, woogenerator
from test_merger import TestMergerAbstract
from test_sync_manager import AbstractSyncManagerTestCase
from utils import ConnectionUtils, MockUtils
from woogenerator.contact_objects import FieldGroup
from woogenerator.merger import (do_match, do_merge, do_report, do_report_post,
                                 do_summary, do_updates,
                                 populate_filter_settings,
                                 populate_master_parsers,
                                 populate_slave_parsers)
from woogenerator.namespace.user import SettingsNamespaceUser
from woogenerator.syncupdate import SyncUpdate
from woogenerator.utils import Registrar, TimeUtils


@unittest.skipIf(
    ConnectionUtils.check_hostname() != 'Derwents-MBP.lan',
    "Only perform these sensitive tests on my machine"
)
class TestMergerSensitiveAbstract(TestMergerAbstract):
    """
    Specific tests for merger using live data.
    """
    data_dir = SENSITIVE_DATA_DIR

@unittest.skip("Does not pass yet")
class TestMergerSensitiveC032560(TestMergerSensitiveAbstract):
    """
    The issue here is that it does a reflection and an update at the same time,
    but only performs the reflection, not the update.
    """
    master_file = "user_master-2017-09-20_16-00-01_C032560.csv"
    slave_file = "user_slave-2017-09-20_16-00-01_C032560.csv"

    def test_sync_role(self):
        self.parsers = populate_master_parsers(
            self.parsers, self.settings
        )
        self.parsers = populate_slave_parsers(
            self.parsers, self.settings
        )
        self.matches = do_match(
            self.parsers, self.settings
        )
        self.updates = do_merge(
            self.matches, self.parsers, self.settings
        )
        if self.debug:
            self.print_updates_summary(self.updates)

        updates_problematic = self.updates.problematic[:]

        sync_update = updates_problematic.pop(0)
        if self.debug:
            print("\nold_m_object:")
            self.print_user_summary(sync_update.old_m_object)
            print("\nold_s_object:")
            self.print_user_summary(sync_update.old_s_object)
            print("\nnew_m_object:")
            self.print_user_summary(sync_update.new_m_object)
            print("\nnew_s_object:")
            self.print_user_summary(sync_update.new_s_object)
        try:
            self.assertEqual(sync_update.old_m_object.MYOBID, 'C032560')
            self.assertEqual(sync_update.old_m_object.role.direct_brand, 'Mosaic Wholesale')
            self.assertEqual(sync_update.old_m_object.role.role, 'WN')
            self.assertEqual(sync_update.old_s_object.wpid, '18798')
            self.assertEqual(sync_update.old_s_object.role.direct_brand, 'Mosaic Minerals Retail')
            self.assertEqual(sync_update.old_s_object.role.role, 'WN')
            self.assertGreater(
                sync_update.get_s_col_mod_time('Role Info'),
                sync_update.get_m_col_mod_time('Role Info')
            )

            self.assertEqual(sync_update.new_m_object.role.role, 'WN')
            self.assertEqual(sync_update.new_m_object.role.direct_brand, 'Mosaic Minerals Retail')
        except AssertionError as exc:
            self.fail_syncupdate_assertion(exc, sync_update)

class TestMergerSensitiveC005188(TestMergerSensitiveAbstract):
    """
    The user is WN; TechnoTan Wholesale in Act but it shows up as RN; Pending
    """
    master_file = "user_master-2017-09-20_16-00-01_C005188.csv"
    slave_file = "user_slave-2017-09-20_16-00-01_C005188.csv"
    debug = True

    def setUp(self):
        super(TestMergerSensitiveAbstract, self).setUp()
        if self.debug:
            Registrar.DEBUG_ROLE = True
            Registrar.DEBUG_UPDATE = True

    @unittest.skip("does not handle")
    def test_sync_role(self):
        self.parsers = populate_master_parsers(
            self.parsers, self.settings
        )
        self.parsers = populate_slave_parsers(
            self.parsers, self.settings
        )

        if self.debug:
            master_list = self.parsers.master.get_obj_list()
            first_master = master_list[0]
            slave_list =  self.parsers.slave.get_obj_list()
            first_slave = slave_list[0]
            print("\nFirst Master:")
            self.print_user_summary(first_master)
            print("\nFirst Slave:")
            self.print_user_summary(first_slave)

        self.matches = do_match(
            self.parsers, self.settings
        )
        self.updates = do_merge(
            self.matches, self.parsers, self.settings
        )
        if self.debug:
            self.print_updates_summary(self.updates)

        updates_problematic = self.updates.problematic[:]

        sync_update = updates_problematic.pop(0)
        if self.debug:
            print("\nold_m_object:")
            self.print_user_summary(sync_update.old_m_object)
            print("\nold_s_object:")
            self.print_user_summary(sync_update.old_s_object)
            print("\nnew_m_object:")
            self.print_user_summary(sync_update.new_m_object)
            print("\nnew_s_object:")
            self.print_user_summary(sync_update.new_s_object)
        try:
            self.assertEqual(sync_update.old_m_object.MYOBID, 'C005188')
            self.assertEqual(sync_update.old_m_object.role.direct_brand, 'TechnoTan Wholesale')
            self.assertEqual(sync_update.old_m_object.role.role, 'WN')
            self.assertEqual(sync_update.old_s_object.wpid, '19595')
            self.assertEqual(sync_update.old_s_object.role.direct_brand, None)
            self.assertEqual(sync_update.old_s_object.role.role, 'WN')
            self.assertGreater(
                sync_update.get_s_col_mod_time('Role Info'),
                sync_update.get_m_col_mod_time('Role Info')
            )

            self.assertEqual(sync_update.new_m_object.role.role, 'WN')
            self.assertEqual(sync_update.new_m_object.role.direct_brand, 'TechnoTan Wholesale')
        except AssertionError as exc:
            self.fail_syncupdate_assertion(exc, sync_update)
