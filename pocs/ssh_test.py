import yaml
import os
import paramiko
from coldata import ColData_User
from parsing.flat import CSVParse_User, UsrObjList
from utils import TimeUtils, SanitationUtils
from itertools import chain

srcFolder = "../source/"
in_folder = "../input/"
remoteExportFolder = "act_usr_exp/"
yamlPath = "merger_config.yaml"

import_name = TimeUtils.get_ms_timestamp()
dateStamp = TimeUtils.get_datestamp()

with open(yamlPath) as stream:
    config = yaml.load(stream)

    m_ssh_user = config.get('test_m_ssh_user')
    m_ssh_pass = config.get('test_m_ssh_pass')
    m_ssh_host = config.get('test_m_ssh_host')
    m_ssh_port = config.get('test_m_ssh_port', 22)
    m_db_host = config.get('test_m_db_host', '127.0.0.1')
    m_db_user = config.get('test_m_db_user')
    m_db_pass = config.get('test_m_db_pass')
    m_db_name = config.get('test_m_db_name')
    m_command = config.get('test_m_command')

exportFilename = "act_x_test_" + import_name + ".csv"
remoteExportPath = os.path.join(remoteExportFolder, exportFilename)
maPath = os.path.join(in_folder, exportFilename)
maEncoding = "utf-8"

paramikoSSHParams = {
    'hostname': m_ssh_host,
    'port': m_ssh_port,
    'username': m_ssh_user,
    'password': m_ssh_pass,
}

col_data = ColData_User()
actCols = col_data.get_act_cols()
fields = ";".join(actCols.keys())

command = " ".join(filter(None, [
    'cd {wd};'.format(
        wd=remoteExportFolder,
    ) if remoteExportFolder else None,
    '{cmd} "-d{db_name}" "-h{db_host}" "-u{db_user}" "-p{db_pass}"'.format(
        cmd=m_command,
        db_name=m_db_name,
        db_host=m_db_host,
        db_user=m_db_user,
        db_pass=m_db_pass,
    ),
    '-s"%s"' % "2016-03-01",
    '"-c%s"' % fields,
    ('"%s"' % exportFilename) if exportFilename else None

]))

# SanitationUtils.safe_print(command)
# exit()

sshClient = paramiko.SSHClient()
sshClient.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    sshClient.connect(**paramikoSSHParams)
    stdin, stdout, stderr = sshClient.exec_command(command)
    possible_errors = stdout.readlines()
    assert not possible_errors, "command returned errors: " + possible_errors
    try:
        sftp_client = sshClient.open_sftp()
        sftp_client.chdir(remoteExportFolder)
        fstat = sftp_client.stat(exportFilename)
        if fstat:
            sftp_client.get(exportFilename, maPath)
    except Exception as exc:
        SanitationUtils.safe_print("ERROR IN SFTP: " + str(exc))
    finally:
        sftp_client.close()

except Exception as exc:
    SanitationUtils.safe_print("ERROR IN SSH: " + str(exc))
finally:
    sshClient.close()

maParser = CSVParse_User(
    cols=col_data.get_import_cols(),
    defaults=col_data.get_defaults(),
    contact_schema='act',
)

maParser.analyse_file(maPath, maEncoding)


def print_basic_columns(users):
    # print len(users)
    usrList = UsrObjList()
    for user in users:
        usrList.append(user)
        # SanitationUtils.safe_print( "BILLING ADDRESS:", repr(user), user['First Name'], user.get('First Name'), user.name.__unicode__(out_schema="flat"))

    cols = col_data.get_basic_cols()

    SanitationUtils.safe_print(usrList.tabulate(
        cols,
        tablefmt='simple'
    ))

print_basic_columns(list(chain(*maParser.emails.values()[:100])))
