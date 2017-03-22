import os
import yaml
import smtplib
import zipfile
import tempfile
from email import encoders
from email.message import Message
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart


def send_file_zipped(the_file, recipients, sender='you@you.com'):
    zf = tempfile.TemporaryFile(prefix='mail', suffix='.zip')
    zip = zipfile.ZipFile(zf, 'w')
    zip.write(the_file)
    zip.close()
    zf.seek(0)

    # Create the message
    themsg = MIMEMultipart()
    themsg['Subject'] = 'File %s' % the_file
    themsg['To'] = ', '.join(recipients)
    themsg['From'] = sender
    themsg.preamble = 'I am not using a MIME-aware mail reader.\n'
    msg = MIMEBase('application', 'zip')
    msg.set_payload(zf.read())
    encoders.encode_base64(msg)
    msg.add_header('Content-Disposition', 'attachment',
                   filename=the_file + '.zip')
    themsg.attach(msg)
    themsg = themsg.as_string()

    # send the message
    smtp = smtplib.SMTP()
    smtp.connect()
    smtp.sendmail(sender, recipients, themsg)
    smtp.close()


def send_zipped_file(zipped_file, recipients, sender, connect_params):
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
    server.login('derwentx@gmail.com', 'Opensesami0114')

    server.sendmail(sender, recipients, themsg)
    server.quit()

srcFolder = "../source/"
in_folder = "../input/"
yaml_path = os.path.join(srcFolder, "merger_config.yaml")
try:
    os.stat('source')
    os.chdir('source')
except Exception as exc:
    if(exc):
        pass
    os.chdir(srcFolder)
print os.getcwd()

with open(yaml_path) as stream:
    config = yaml.load(stream)

    smtp_user = config.get('smtp_user')
    smtp_pass = config.get('smtp_pass')
    smtp_host = config.get('smtp_host')
    smtp_port = config.get('smtp_port', 25)

send_zipped_file(
    '/Users/Derwent/Desktop/test.zip',
    ['webmaster@technotan.com.au'],
    'webmaster@technotan.com.au',
    connect_params={
        'host': smtp_host,
        'port': smtp_port,
        'user': smtp_user,
        'pass': smtp_pass
    })
