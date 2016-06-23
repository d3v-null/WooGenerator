from os import sys, path
import unittest
from unittest import TestCase, main, skip

if __name__ == '__main__' and __package__ is None:
    sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

from source.sync_client_user import *
from source.coldata import ColData_User
from source.csvparse_flat import ImportUser

class testUsrSyncClient(TestCase):
    def setUp(self):
        os.chdir('source')

        yamlPath = "merger_config.yaml"

        importName = TimeUtils.getMsTimeStamp()
        inFolder = "../input/"
        outFolder = "../output/"
        remoteExportFolder = "act_usr_exp"

        with open(yamlPath) as stream:
            config = yaml.load(stream)
            optionNamePrefix = 'test_'
            optionNamePrefix = ''

            if 'inFolder' in config.keys():
                inFolder = config['inFolder']
            if 'outFolder' in config.keys():
                outFolder = config['outFolder']
            if 'logFolder' in config.keys():
                logFolder = config['logFolder']

            ssh_user = config.get(optionNamePrefix+'ssh_user')
            ssh_pass = config.get(optionNamePrefix+'ssh_pass')
            ssh_host = config.get(optionNamePrefix+'ssh_host')
            ssh_port = config.get(optionNamePrefix+'ssh_port', 22)
            m_ssh_user = config.get(optionNamePrefix+'m_ssh_user')
            m_ssh_pass = config.get(optionNamePrefix+'m_ssh_pass')
            m_ssh_host = config.get(optionNamePrefix+'m_ssh_host')
            m_ssh_port = config.get(optionNamePrefix+'m_ssh_port', 22)
            remote_bind_host = config.get(optionNamePrefix+'remote_bind_host', '127.0.0.1')
            remote_bind_port = config.get(optionNamePrefix+'remote_bind_port', 3306)
            db_user = config.get(optionNamePrefix+'db_user')
            db_pass = config.get(optionNamePrefix+'db_pass')
            db_name = config.get(optionNamePrefix+'db_name')
            db_charset = config.get(optionNamePrefix+'db_charset', 'utf8mb4')
            wp_srv_offset = config.get(optionNamePrefix+'wp_srv_offset', 0)
            m_db_user = config.get(optionNamePrefix+'m_db_user')
            m_db_pass = config.get(optionNamePrefix+'m_db_pass')
            m_db_name = config.get(optionNamePrefix+'m_db_name')
            m_db_host = config.get(optionNamePrefix+'m_db_host')
            m_x_cmd = config.get(optionNamePrefix+'m_x_cmd')
            m_i_cmd = config.get(optionNamePrefix+'m_i_cmd')
            tbl_prefix = config.get(optionNamePrefix+'tbl_prefix', '')
            wp_user = config.get(optionNamePrefix+'wp_user', '')
            wp_pass = config.get(optionNamePrefix+'wp_pass', '')
            store_url = config.get(optionNamePrefix+'store_url', '')

        TimeUtils.setWpSrvOffset(wp_srv_offset)

        actFields = ";".join(ColData_User.getACTImportCols())

        SSHTunnelForwarderAddress = (ssh_host, ssh_port)
        SSHTunnelForwarderBindAddress = (remote_bind_host, remote_bind_port)

        self.SSHTunnelForwarderParams = {
            'ssh_address_or_host':SSHTunnelForwarderAddress,
            'ssh_password':ssh_pass,
            'ssh_username':ssh_user,
            'remote_bind_address': SSHTunnelForwarderBindAddress,
        }

        self.PyMySqlConnectParams = {
            'host' : 'localhost',
            'user' : db_user,
            'password': db_pass,
            'db'   : db_name,
            'charset': db_charset,
            'use_unicode': True,
            'tbl_prefix': tbl_prefix,
            # 'srv_offset': wp_srv_offset,
        }

        json_uri = store_url + 'wp-json/wp/v2'

        self.jsonConnectParams = {
            'json_uri': json_uri,
            'wp_user': wp_user,
            'wp_pass': wp_pass
        }

        self.actConnectParams = {
            'hostname':    m_ssh_host,
            'port':        m_ssh_port,
            'username':    m_ssh_user,
            'password':    m_ssh_pass,
        }

        self.actDbParams = {
            'db_x_exe':m_x_cmd,
            'db_i_exe':m_i_cmd,
            'db_name': m_db_name,
            'db_host': m_db_host,
            'db_user': m_db_user,
            'db_pass': m_db_pass,
            'fields' : actFields,
        }

        self.fsParams = {
            'importName': importName,
            'remoteExportFolder': remoteExportFolder,
            'inFolder': inFolder,
            'outFolder': outFolder
        }

        for var in ['self.SSHTunnelForwarderParams', 'self.PyMySqlConnectParams',
                    'self.jsonConnectParams', 'self.actConnectParams', 'self.actDbParams']:
            print var, eval(var)

    def test_SQLWP_Analyse(self):
        saParser = CSVParse_User(
            cols = ColData_User.getImportCols(),
            defaults = ColData_User.getDefaults()
        )

        with UsrSyncClient_SQL_WP(
            self.SSHTunnelForwarderParams,
            self.PyMySqlConnectParams
        ) as sqlClient:
            sqlClient.analyseRemote(saParser, since='2016-01-01 00:00:00')

        # CSVParse_User.printBasicColumns( list(chain( *saParser.emails.values() )) )
        self.assertIn('neil@technotan.com.au', saParser.emails)

    def test_JSON_read(self):
        response = ''
        with UsrSyncClient_JSON(self.jsonConnectParams) as client:
            response = client.client.get_posts()
        print response
        self.assertTrue(response)

    def test_JSON_Upload_bad(self):
        fields = {"user_email": "neil@technotan.com.au"}

        response = ''
        with UsrSyncClient_JSON(self.jsonConnectParams) as client:
            response = client.uploadChanges(2, fields)

        print response

    def test_JSON_Upload_good(self):
        fields = {"first_name": "neil"}

        response = ''
        with UsrSyncClient_JSON(self.jsonConnectParams) as client:
            response = client.uploadChanges(1, fields)

        print response

    def test_SSH_download(self):
        with UsrSyncClient_SSH_ACT(self.actConnectParams, self.actDbParams, self.fsParams) as client:
            response = client.getDeleteFile('act_usr_exp/act_x_2016-05-26_15-03-07.csv', 'downloadtest.csv')

    def test_SSH_Upload(self):
        fields = {
            "Phone": "0413 300 930",
            "MYOB Card ID": "C004897",
        }

        response = ''
        with UsrSyncClient_SSH_ACT(self.actConnectParams, self.actDbParams, self.fsParams) as client:
            response = client.uploadChanges('C004897', fields)

        print response



if __name__ == '__main__':
    # main()
    sshTestSuite = unittest.TestSuite()
    sshTestSuite.addTest(testUsrSyncClient('test_JSON_Upload_good'))
    unittest.TextTestRunner().run(sshTestSuite)
