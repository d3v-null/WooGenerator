import yaml
import os
import paramiko
from coldata import ColData_User
from parsing.flat import CSVParse_User, UsrObjList
from utils import TimeUtils, SanitationUtils
from itertools import chain

srcFolder = "../source/"
inFolder = "../input/"
remoteExportFolder = "act_usr_exp/"
yamlPath = "merger_config.yaml"

importName = TimeUtils.get_ms_timestamp()
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

exportFilename = "act_x_test_"+importName+".csv"
remoteExportPath = os.path.join(remoteExportFolder, exportFilename)
maPath = os.path.join(inFolder, exportFilename)
maEncoding = "utf-8"

paramikoSSHParams = {
    'hostname':    m_ssh_host,
    'port':        m_ssh_port,
    'username':    m_ssh_user,
    'password':    m_ssh_pass,
}

colData = ColData_User()
actCols = colData.getACTCols()
fields = ";".join(actCols.keys())

command = " ".join(filter(None,[
    'cd {wd};'.format(
        wd      = remoteExportFolder,
    ) if remoteExportFolder else None,
    '{cmd} "-d{db_name}" "-h{db_host}" "-u{db_user}" "-p{db_pass}"'.format(
        cmd     = m_command,
        db_name = m_db_name,
        db_host = m_db_host,
        db_user = m_db_user,
        db_pass = m_db_pass,
    ),
    '-s"%s"' % "2016-03-01",
    '"-c%s"' % fields,
    ('"%s"' % exportFilename) if exportFilename else None

]))

# SanitationUtils.safePrint(command)
# exit()

sshClient = paramiko.SSHClient()
sshClient.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try: 
    sshClient.connect(**paramikoSSHParams)
    stdin, stdout, stderr = sshClient.exec_command(command)
    possible_errors = stdout.readlines()
    assert not possible_errors, "command returned errors: " + possible_errors
    try:
        sftpClient = sshClient.open_sftp()    
        sftpClient.chdir(remoteExportFolder)
        fstat = sftpClient.stat(exportFilename)
        if fstat:
            sftpClient.get(exportFilename, maPath)
    except Exception, e:
        SanitationUtils.safePrint("ERROR IN SFTP: " + str(e))
    finally:
        sftpClient.close()

except Exception, e:
    SanitationUtils.safePrint("ERROR IN SSH: " + str(e))
finally:
    sshClient.close()

maParser = CSVParse_User(
    cols = colData.getImportCols(),
    defaults = colData.getDefaults(),
    contact_schema = 'act',
)

maParser.analyseFile(maPath, maEncoding)

def printBasicColumns(users):
    # print len(users)
    usrList = UsrObjList()
    for user in users:
        usrList.append(user)
        # SanitationUtils.safePrint( "BILLING ADDRESS:", repr(user), user['First Name'], user.get('First Name'), user.name.__unicode__(out_schema="flat"))

    cols = colData.getBasicCols()

    SanitationUtils.safePrint( usrList.tabulate(
        cols,
        tablefmt = 'simple'
    ))

printBasicColumns( list(chain( *maParser.emails.values()[:100] )) )


