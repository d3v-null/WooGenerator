import unittest
import os

from tests.test_sync_client import AbstractSyncClientTestCase

from context import TESTS_DATA_DIR, woogenerator
from woogenerator.conf.namespace import (SettingsNamespaceUser)
from woogenerator.conf.parser import ArgumentParserUser

class TestClientEmail(AbstractSyncClientTestCase):
    local_work_dir = '/Users/Derwent/Documents/woogenerator'
    config_file = "conf_user.yaml"
    settings_namespace_class = SettingsNamespaceUser
    argument_parser_class = ArgumentParserUser

class TestClientEmailExchange(TestClientEmail):
    def test_send_basic(self):
        with self.settings.email_client(self.settings.email_connect_params) as email_client:
            message = email_client.compose_message(
                self.settings.mail_sender,
                'test',
                'test',
                self.settings.mail_recipients
            )
            attachment = os.path.join(TESTS_DATA_DIR, 'test.zip')
            message = email_client.attach_file(message, attachment)

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
