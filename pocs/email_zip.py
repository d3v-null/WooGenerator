import os
import smtplib
import logging
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart

import exchangelib

from context import TESTS_DATA_DIR, woogenerator
from woogenerator.namespace.core import SettingsNamespaceUser, init_settings
from woogenerator.conf.parser import ArgumentParserUser
from woogenerator.utils import Registrar


def send_zipped_file_smtp(zipped_file, recipients, sender, connect_params):
    for param in ['host', 'port', 'user', 'pass']:
        assert param in connect_params, 'must specify mandatory parameter %s' % param

    themsg = MIMEMultipart()
    themsg['Subject'] = 'TEST: File %s' % zipped_file
    themsg['To'] = ', '.join(recipients)
    themsg['From'] = sender
    themsg.preamble = 'I am not using a MIME-aware mail reader.\n'
    with open(zipped_file, 'w+') as zf:
        # Create the message
        msg = MIMEBase('application', 'zip')
        msg.set_payload(zf.read())
        encoders.encode_base64(msg)
        msg.add_header('Content-Disposition', 'attachment',
                       filename=zipped_file)
        themsg.attach(msg)
    themsg = themsg.as_string()

    # send the message
    server = smtplib.SMTP(connect_params['host'], connect_params['port'])
    server.ehlo()
    server.starttls()
    server.login(connect_params['user'], connect_params['pass'])

    server.sendmail(sender, recipients, themsg)
    server.quit()

def send_zipped_file_exchange(zipped_file, recipients, sender, connect_params):
    for param in ['host', 'sender', 'user', 'pass']:
        assert param in connect_params, 'must specify mandatory parameter %s' % param

    credentials = exchangelib.ServiceAccount(
        username=connect_params['user'],
        password=connect_params['pass']
    )

    print("creds are:\n%s" % credentials)

    config = exchangelib.Configuration(
        server=connect_params['host'],
        credentials=credentials,
        # version=version,
        # auth_type=NTLM
    )

    print("config is:\n%s" % config)

    account = exchangelib.Account(
        primary_smtp_address=connect_params['sender'],
        credentials=credentials,
        autodiscover=False,
        config=config,
        access_type=exchangelib.DELEGATE
    )

    message = exchangelib.Message(
        account=account,
        subject='TEST: File %s' % zipped_file,
        body='',
        to_recipients=recipients
    )

    with open(zipped_file, 'w+') as zf:
        attachment = exchangelib.FileAttachment(name=zipped_file, content=zf.read())
        message.attach(attachment)

    message.send_and_save()

def main():
    logging.basicConfig(level=logging.DEBUG)

    settings = SettingsNamespaceUser()
    settings.local_work_dir = '/Users/Derwent/Documents/woogenerator'
    settings.local_live_config = None
    settings.local_test_config = "conf_user.yaml"
    Registrar.DEBUG_MESSAGE = True
    settings = init_settings(
        settings=settings,
        argparser_class=ArgumentParserUser
    )
    print("connect paarams: %s" % settings.email_connect_params)

    mail_args = [
        os.path.join(TESTS_DATA_DIR, 'test.zip'),
        settings.get('mail_recipients', []),
        settings.get('mail_sender'),
        settings.email_connect_params
    ]

    if settings.get('mail_type') == 'exchange':
        send_zipped_file_exchange(
            *mail_args
        )
    else:
        send_zipped_file_smtp(
            *mail_args
        )

if __name__ == '__main__':
    main()
