# -*- coding: utf-8 -*-
from __future__ import absolute_import

import os
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart

import exchangelib

from .core import ClientAbstract

MAX_BODY_LEN = 1000000


class EmailClient(ClientAbstract):
    """Interface with a mail client. Boilerplate."""

    def send(self, message):
        """Send an email.message object using the mail client."""
        raise NotImplementedError()

    def compose_message(self,
                        sender,
                        recipients,
                        subject,
                        body,
                        text_body=None):
        raise NotImplementedError()

    def attach_file(self, message, filename):
        raise NotImplementedError()


class EmailClientSMTP(ClientAbstract):
    """Interface with an SMTP mail client."""
    service_builder = smtplib.SMTP

    def __exit__(self, exit_type, value, traceback):
        self.service.quit()

    def compose_message(self,
                        sender,
                        recipients,
                        subject,
                        body,
                        text_body=None):
        message = MIMEMultipart()
        message['Subject'] = subject
        message['To'] = ', '.join(recipients)
        message['From'] = sender
        message.preamble = 'I am not using a MIME-aware mail reader.\n'
        return message

    def attach_file(self, message, filename):
        with open(filename) as attachment_file:
            # Create the message
            msg = MIMEBase('application', 'zip')
            msg.set_payload(attachment_file.read())
            encoders.encode_base64(msg)
            msg.add_header(
                'Content-Disposition', 'attachment', filename=filename)
            message.attach(msg)
        return message

    def send(self, message):
        sender = message.get('From', '')
        recipients = message.get('To', '').split(', ')
        message = message.as_string()
        self.service.sendmail(sender, recipients, message)

    def attempt_connect(self):
        self.service = self.service_builder(self.connect_params['host'],
                                            self.connect_params['port'])
        self.service.ehlo()
        self.service.starttls()
        self.service.login(self.connect_params['user'],
                           self.connect_params['pass'])


class EmailClientExchange(ClientAbstract):
    """Interface with an exchange mail client."""
    service_builder = exchangelib.Account

    def __init__(self, connect_params, **kwargs):
        self.connect_params = connect_params
        self.service = None
        self.attempt_connect()

    def compose_message(self,
                        sender,
                        recipients,
                        subject,
                        body,
                        text_body=None):
        if body is None:
            body = ''
        body = body[:MAX_BODY_LEN]
        if text_body is None:
            text_body = ''
        message = exchangelib.Message(
            account=self.service,
            subject=subject,
            text_body=text_body[:MAX_BODY_LEN],
            body=exchangelib.HTMLBody(body[:MAX_BODY_LEN]),
            to_recipients=recipients)
        return message

    def attach_file(self, message, path):
        filename = os.path.basename(path)
        with open(path) as attachment_file:
            attachment = exchangelib.FileAttachment(
                name=filename, content=attachment_file.read())
            message.attach(attachment)
        return message

    def send(self, message):
        message.send_and_save()

    def attempt_connect(self):
        """
        Attempt to connect using instances `connect_params` and `service_builder`
        """
        self.credentials = exchangelib.ServiceAccount(
            username=self.connect_params['user'],
            password=self.connect_params['pass'])

        self.config = exchangelib.Configuration(
            server=self.connect_params['host'],
            credentials=self.credentials,
            # version=version,
            # auth_type=NTLM
        )

        self.service = self.service_builder(
            primary_smtp_address=self.connect_params['sender'],
            credentials=self.credentials,
            autodiscover=False,
            config=self.config,
            access_type=exchangelib.DELEGATE)
