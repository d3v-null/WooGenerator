import os
import tempfile
import unittest

import mock
from tests.test_sync_client import AbstractSyncClientTestCase

from context import TESTS_DATA_DIR, woogenerator
from mock_utils import MockUtils
from woogenerator.conf.parser import ArgumentParserUser
from woogenerator.merger import (do_match, do_merge, do_report, do_report_post,
                                 do_summary, do_updates,
                                 populate_master_parsers,
                                 populate_slave_parsers)
from woogenerator.namespace.user import SettingsNamespaceUser
from woogenerator.namespace.core import (MatchNamespace, ParserNamespace,
                                         UpdateNamespace, init_dirs,
                                         init_settings)



class TestClientEmail(AbstractSyncClientTestCase):
    local_work_dir = os.path.expanduser('~/Documents/woogenerator')
    config_file = "conf_user.yaml"
    settings_namespace_class = SettingsNamespaceUser
    argument_parser_class = ArgumentParserUser
    debug = False

class TestClientEmailExchange(TestClientEmail):
    def test_email_basic(self):
        with self.settings.email_client(self.settings.email_connect_params) as email_client:
            message = email_client.compose_message(
                self.settings.mail_sender,
                'test',
                'test',
                self.settings.mail_recipients
            )
            attachment = os.path.join(TESTS_DATA_DIR, 'test.zip')
            message = email_client.attach_file(message, attachment)

class TestClientEmailExchangeDestructive(TestClientEmail):
    @unittest.skip("destructive tests skipped")
    def test_send_destructive(self):
        with self.settings.email_client(self.settings.email_connect_params) as email_client:
            message = email_client.compose_message(
                self.settings.mail_sender,
                self.settings.mail_recipients,
                'test',
                'test',
            )
            attachment = os.path.join(TESTS_DATA_DIR, 'test.zip')
            message = email_client.attach_file(message, attachment)
            email_client.send(message)

    @unittest.skip("destructive tests skipped")
    def test_send_dummy_report(self):
        self.parsers = ParserNamespace()
        self.matches = MatchNamespace()
        self.updates = UpdateNamespace()
        self.settings.local_work_dir = TESTS_DATA_DIR
        self.settings.local_live_config = None
        self.settings.master_dialect_suggestion = "ActOut"
        self.settings.download_master = False
        self.settings.download_slave = False
        self.settings.master_file = os.path.join(TESTS_DATA_DIR, "merger_master_dummy.csv")
        self.settings.slave_file = os.path.join(TESTS_DATA_DIR, "merger_slave_dummy.csv")
        self.settings.testmode = True
        self.settings.do_sync = True
        self.settings.report_duplicates = True
        self.settings.report_sanitation = True
        self.settings.report_matching = True
        # TODO: mock out update clients
        self.settings.ask_before_update = False
        self.override_args = ""

        self.parsers = populate_master_parsers(
            self.parsers, self.settings
        )
        self.parsers = populate_slave_parsers(
            self.parsers, self.settings
        )

        self.settings.local_test_config = "merger_config_test.yaml"
        self.settings = init_settings(
            settings=self.settings,
            override_args=self.override_args,
            argparser_class=ArgumentParserUser
        )
        suffix='do_summary'
        temp_working_dir = tempfile.mkdtemp(suffix + '_working')
        self.settings.local_work_dir = temp_working_dir
        init_dirs(self.settings)
        self.settings.do_mail = True

        self.matches = do_match(
            self.parsers, self.settings
        )
        self.updates = do_merge(
            self.matches, self.parsers, self.settings
        )
        self.reporters = do_report(
            self.matches, self.updates, self.parsers, self.settings
        )
        self.settings.update_master = True
        self.settings.update_slave = True
        with mock.patch(
            MockUtils.get_mock_name(self.settings.__class__, 'master_upload_client_class'),
            new_callable=mock.PropertyMock,
            return_value = self.settings.null_client_class
        ), \
        mock.patch(
            MockUtils.get_mock_name(self.settings.__class__, 'slave_upload_client_class'),
            new_callable=mock.PropertyMock,
            return_value = self.settings.null_client_class
        ):
            self.results = do_updates(
                self.updates, self.settings
            )
        do_report_post(self.reporters, self.results, self.settings)
        summary_html, summary_text = do_summary(self.settings, self.reporters, self.results, 0)
        # if self.debug:
        #     print("Summary HTML:\n%s" % summary_html)
        #     print("Summary Text:\n%s" % summary_text)
