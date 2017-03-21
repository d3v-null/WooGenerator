from os import sys, path
import unittest
from unittest import TestCase, main, skip
from tabulate import tabulate
from pprint import pprint

from context import woogenerator

from testSyncClient import abstractSyncClientTestCase
from woogenerator.sync_client_user import UsrSyncClient_SQL_WP, UsrSyncClient_SSH_ACT, UsrSyncClient_WC, UsrSyncClient_WP
from woogenerator.coldata import ColData_User
from woogenerator.parsing.user import ImportUser, CSVParse_User, CSVParse_User_Api
from woogenerator.utils import TimeUtils, Registrar

@skip('no config file yet')
class testUsrSyncClient(abstractSyncClientTestCase):
    # yamlPath = "merger_config.yaml"
    optionNamePrefix = 'test_'
    # optionNamePrefix = 'dummy_'

    def __init__(self, *args, **kwargs):
        super(testUsrSyncClient, self).__init__(*args, **kwargs)
        self.SSHTunnelForwarderParams = {}
        self.PyMySqlconnect_params = {}
        self.jsonconnect_params = {}
        self.actconnect_params = {}
        self.actDbParams = {}
        self.fsParams = {}

    def processConfig(self, config):
        inFolder = "../input/"
        outFolder = "../output/"

        if 'inFolder' in config.keys():
            inFolder = config['inFolder']
        if 'outFolder' in config.keys():
            outFolder = config['outFolder']
        # if 'logFolder' in config.keys():
        #     logFolder = config['logFolder']

        ssh_user = config.get(self.optionNamePrefix+'ssh_user')
        ssh_pass = config.get(self.optionNamePrefix+'ssh_pass')
        ssh_host = config.get(self.optionNamePrefix+'ssh_host')
        ssh_port = config.get(self.optionNamePrefix+'ssh_port', 22)
        m_ssh_user = config.get(self.optionNamePrefix+'m_ssh_user')
        m_ssh_pass = config.get(self.optionNamePrefix+'m_ssh_pass')
        m_ssh_host = config.get(self.optionNamePrefix+'m_ssh_host')
        m_ssh_port = config.get(self.optionNamePrefix+'m_ssh_port', 22)
        remote_bind_host = config.get(self.optionNamePrefix+'remote_bind_host', '127.0.0.1')
        remote_bind_port = config.get(self.optionNamePrefix+'remote_bind_port', 3306)
        db_user = config.get(self.optionNamePrefix+'db_user')
        db_pass = config.get(self.optionNamePrefix+'db_pass')
        db_name = config.get(self.optionNamePrefix+'db_name')
        db_charset = config.get(self.optionNamePrefix+'db_charset', 'utf8mb4')
        wp_srv_offset = config.get(self.optionNamePrefix+'wp_srv_offset', 0)
        m_db_user = config.get(self.optionNamePrefix+'m_db_user')
        m_db_pass = config.get(self.optionNamePrefix+'m_db_pass')
        m_db_name = config.get(self.optionNamePrefix+'m_db_name')
        m_db_host = config.get(self.optionNamePrefix+'m_db_host')
        m_x_cmd = config.get(self.optionNamePrefix+'m_x_cmd')
        m_i_cmd = config.get(self.optionNamePrefix+'m_i_cmd')
        tbl_prefix = config.get(self.optionNamePrefix+'tbl_prefix', '')
        # wp_user = config.get(self.optionNamePrefix+'wp_user', '')
        # wp_pass = config.get(self.optionNamePrefix+'wp_pass', '')
        wc_api_key = config.get(self.optionNamePrefix+'wc_api_key')
        wc_api_secret = config.get(self.optionNamePrefix+'wc_api_secret')
        wp_api_key = config.get(self.optionNamePrefix+'wp_api_key')
        wp_api_secret = config.get(self.optionNamePrefix+'wp_api_secret')
        store_url = config.get(self.optionNamePrefix+'store_url', '')
        wp_user = config.get(self.optionNamePrefix+'wp_user')
        wp_pass = config.get(self.optionNamePrefix+'wp_pass')
        wp_callback = config.get(self.optionNamePrefix+'wp_callback')
        remote_export_folder = config.get(self.optionNamePrefix+'remote_export_folder', '')

        TimeUtils.set_wp_srv_offset(wp_srv_offset)

        actFields = ";".join(ColData_User.getACTImportCols())

        SSHTunnelForwarderAddress = (ssh_host, ssh_port)
        SSHTunnelForwarderBindAddress = (remote_bind_host, remote_bind_port)

        self.SSHTunnelForwarderParams = {
            'ssh_address_or_host':SSHTunnelForwarderAddress,
            'ssh_password':ssh_pass,
            'ssh_username':ssh_user,
            'remote_bind_address': SSHTunnelForwarderBindAddress,
        }

        self.PyMySqlconnect_params = {
            'host' : 'localhost',
            'user' : db_user,
            'password': db_pass,
            'db'   : db_name,
            'charset': db_charset,
            'use_unicode': True,
            'tbl_prefix': tbl_prefix,
            # 'srv_offset': wp_srv_offset,
        }

        self.wcApiParams = {
            'api_key':wc_api_key,
            'api_secret':wc_api_secret,
            'url':store_url
        }

        self.wpApiParams = {
            'api_key': wp_api_key,
            'api_secret': wp_api_secret,
            'url':store_url,
            'wp_user':wp_user,
            'wp_pass':wp_pass,
            'callback':wp_callback
        }

        # json_uri = store_url + 'wp-json/wp/v2'
        #
        # self.jsonconnect_params = {
        #     'json_uri': json_uri,
        #     'wp_user': wp_user,
        #     'wp_pass': wp_pass
        # }

        self.actconnect_params = {
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
            'importName': self.importName,
            'remote_export_folder': remote_export_folder,
            'inFolder': inFolder,
            'outFolder': outFolder
        }

    def setUp(self):
        super(testUsrSyncClient, self).setUp()

        for var in ['SSHTunnelForwarderParams', 'PyMySqlconnect_params',
                    'wcApiParams', 'actconnect_params', 'actDbParams']:
            print var, getattr(self, var)

        # Registrar.DEBUG_SHOP = True
        # Registrar.DEBUG_MRO = True
        # Registrar.DEBUG_TREE = True
        # Registrar.DEBUG_PARSER = True
        # Registrar.DEBUG_GEN = True
        # Registrar.DEBUG_ABSTRACT = True
        # Registrar.DEBUG_WOO = True
        # Registrar.DEBUG_API = True
        # Registrar.DEBUG_PARSER = True
        # Registrar.DEBUG_UTILS = True


    def test_SQLWP_Analyse(self):
        saParser = CSVParse_User(
            cols = ColData_User.getImportCols(),
            defaults = ColData_User.getDefaults()
        )

        with UsrSyncClient_SQL_WP(
            self.SSHTunnelForwarderParams,
            self.PyMySqlconnect_params
        ) as sqlClient:
            sqlClient.analyse_remote(saParser, since='2016-01-01 00:00:00')

        # CSVParse_User.printBasicColumns( list(chain( *saParser.emails.values() )) )
        self.assertIn('neil@technotan.com.au', saParser.emails)

    @skip
    def test_SSH_ACT_Upload(self):
        fields = {
            "ABN": "1",
            "MYOB Card ID": "C000001",
        }

        with UsrSyncClient_SSH_ACT(self.actconnect_params, self.actDbParams, self.fsParams) as client:
            response = client.upload_changes('C000001', fields)
        print response

    # @skip
    # def test_JSON_read(self):
    #     response = ''
    #     with UsrSyncClient_JSON(self.jsonconnect_params) as client:
    #         response = client.service.get_posts()
    #     print response
    #     self.assertTrue(response)
    #
    # @skip
    # def test_JSON_Upload_bad(self):
    #     fields = {"user_email": "neil@technotan.com.au"}
    #
    #     response = ''
    #     with UsrSyncClient_JSON(self.jsonconnect_params) as client:
    #         response = client.upload_changes(2, fields)
    #
    #     print response
    #
    # @skip
    # def test_JSON_Upload_good(self):
    #     fields = {"first_name": "neil"}
    #
    #     response = ''
    #     with UsrSyncClient_JSON(self.jsonconnect_params) as client:
    #         response = client.upload_changes(1, fields)
    #
    #     self.assertTrue(response)
    #
    # @skip
    # def test_JSON_Upload_Core_Easy(self):
    #     url = "http://www.google.com/"
    #     fields = {"user_url": url}
    #     user_id = 2508
    #
    #     response = None
    #     with UsrSyncClient_JSON(self.jsonconnect_params) as client:
    #         response = client.upload_changes(user_id, fields)
    #
    #     updated = ''
    #     with UsrSyncClient_SQL_WP(
    #         self.SSHTunnelForwarderParams,
    #         self.PyMySqlconnect_params
    #     ) as sqlClient:
    #         sqlClient.assert_connect()
    #         sqlClient.dbParams['port'] = sqlClient.service.local_bind_address[-1]
    #         cursor = pymysql.connect( **sqlClient.dbParams ).cursor()
    #
    #         sql = """
    #         SELECT user_url
    #         FROM {tbl_u}
    #         WHERE `ID` = {user_id}""".format(
    #             tbl_u = sqlClient.tbl_prefix + 'users',
    #             user_id = user_id
    #         )
    #
    #         cursor.execute(sql)
    #
    #         updated = list(list(cursor)[0])[0]
    #
    #     self.assertTrue(response)
    #     self.assertEqual(url, updated)
    #
    # @skip
    # def test_JSON_Upload_Core_Hard(self):
    #     url = "http://www.facebook.com/search/?post_form_id=474a034babb679a6e6eed34af9a686c0&q=kezzi@live.com.au&init=quick&ref=search_loaded#"
    #     fields = {"user_url": url}
    #     user_id = 2508
    #
    #     response = None
    #     with UsrSyncClient_JSON(self.jsonconnect_params) as client:
    #         response = client.upload_changes(user_id, fields)
    #
    #     updated = ''
    #     with UsrSyncClient_SQL_WP(
    #         self.SSHTunnelForwarderParams,
    #         self.PyMySqlconnect_params
    #     ) as sqlClient:
    #         sqlClient.assert_connect()
    #         sqlClient.dbParams['port'] = sqlClient.service.local_bind_address[-1]
    #         cursor = pymysql.connect( **sqlClient.dbParams ).cursor()
    #
    #         sql = """
    #         SELECT user_url
    #         FROM {tbl_u}
    #         WHERE `ID` = {user_id}""".format(
    #             tbl_u = sqlClient.tbl_prefix + 'users',
    #             user_id = user_id
    #         )
    #
    #         cursor.execute(sql)
    #
    #         updated = list(list(cursor)[0])[0]
    #
    #     self.assertTrue(response)
    #     self.assertEqual(url, updated)

    def test_WC_read(self):
        response = []
        with UsrSyncClient_WC(self.wcApiParams) as client:
            response = client.get_iterator()
        print tabulate(list(response)[:10], headers='keys')
        print list(response)
        self.assertTrue(response)

    # def test_WC_Upload_bad(self):
    #     fields = {"user_email": "neil@technotan.com.au"}
    #
    #     response = ''
    #     with UsrSyncClient_WC(self.wcApiParams) as client:
    #         response = client.upload_changes(2, fields)
    #
    #     print response
    #
    # def test_WC_Upload_good(self):
    #     fields = {"first_name": "neil"}
    #
    #     response = ''
    #     with UsrSyncClient_WC(self.wcApiParams) as client:
    #         response = client.upload_changes(1, fields)
    #
    #     self.assertTrue(response)
    #
    # def test_WC_Upload_Core_Easy(self):
    #     url = "http://www.google.com/"
    #     fields = {"user_url": url}
    #     user_id = 2508
    #
    #     response = None
    #     with UsrSyncClient_WC(self.wcApiParams) as client:
    #         response = client.upload_changes(user_id, fields)
    #
    #     updated = ''
    #     with UsrSyncClient_SQL_WP(
    #         self.SSHTunnelForwarderParams,
    #         self.PyMySqlconnect_params
    #     ) as sqlClient:
    #         sqlClient.assert_connect()
    #         sqlClient.dbParams['port'] = sqlClient.service.local_bind_address[-1]
    #         cursor = pymysql.connect( **sqlClient.dbParams ).cursor()
    #
    #         sql = """
    #         SELECT user_url
    #         FROM {tbl_u}
    #         WHERE `ID` = {user_id}""".format(
    #             tbl_u = sqlClient.tbl_prefix + 'users',
    #             user_id = user_id
    #         )
    #
    #         cursor.execute(sql)
    #
    #         updated = list(list(cursor)[0])[0]
    #
    #     self.assertTrue(response)
    #     self.assertEqual(url, updated)
    #
    # def test_WC_Upload_Core_Hard(self):
    #     url = "http://www.facebook.com/search/?post_form_id=474a034babb679a6e6eed34af9a686c0&q=kezzi@live.com.au&init=quick&ref=search_loaded#"
    #     fields = {"user_url": url}
    #     user_id = 2508
    #
    #     response = None
    #     with UsrSyncClient_WC(self.wcApiParams) as client:
    #         response = client.upload_changes(user_id, fields)
    #
    #     updated = ''
    #     with UsrSyncClient_SQL_WP(
    #         self.SSHTunnelForwarderParams,
    #         self.PyMySqlconnect_params
    #     ) as sqlClient:
    #         sqlClient.assert_connect()
    #         sqlClient.dbParams['port'] = sqlClient.service.local_bind_address[-1]
    #         cursor = pymysql.connect( **sqlClient.dbParams ).cursor()
    #
    #         sql = """
    #         SELECT user_url
    #         FROM {tbl_u}
    #         WHERE `ID` = {user_id}""".format(
    #             tbl_u = sqlClient.tbl_prefix + 'users',
    #             user_id = user_id
    #         )
    #
    #         cursor.execute(sql)
    #
    #         updated = list(list(cursor)[0])[0]
    #
    #     self.assertTrue(response)
    #     self.assertEqual(url, updated)

    def test_WP_read(self):
        response = []
        with UsrSyncClient_WP(self.wpApiParams) as client:
            response = client.get_iterator()
        print tabulate(list(response)[:10], headers='keys')
        print list(response)
        self.assertTrue(response)

    def test_WP_iterator(self):
        with UsrSyncClient_WP(self.wpApiParams) as slaveClient:
            iterator = slaveClient.get_iterator('users?context=edit')
            for page in iterator:
                pprint(page)

    def test_WP_analyse(self):
        print "API Import cols: "
        pprint(ColData_User.getWPAPIImportCols())

        saParser = CSVParse_User_Api(
            cols=ColData_User.getWPImportCols(),
            defaults=ColData_User.getDefaults()
        )

        with UsrSyncClient_WP(self.wpApiParams) as slaveClient:
            slaveClient.analyse_remote(saParser)

        print saParser.tabulate()

    # def test_SSH_download(self):
    #     with UsrSyncClient_SSH_ACT(self.actconnect_params, self.actDbParams, self.fsParams) as client:
    #         response = client.getDeleteFile('act_usr_exp/act_x_2016-05-26_15-03-07.csv', 'downloadtest.csv')

    # def test_SSH_Upload(self):
    #     fields = {
    #         "Phone": "0413 300 930",
    #         "MYOB Card ID": "C004897",
    #     }
    #
    #     response = ''
    #     with UsrSyncClient_SSH_ACT(self.actconnect_params, self.actDbParams, self.fsParams) as client:
    #         response = client.upload_changes('C004897', fields)
    #
    #     print response



if __name__ == '__main__':
    # main()
    testSuite = unittest.TestSuite()
    # testSuite.addTest(testUsrSyncClient('test_JSON_Upload_Core_Easy'))
    # testSuite.addTest(testUsrSyncClient('test_JSON_Upload_Core_Hard'))
    # testSuite.addTest(testUsrSyncClient('test_WP_read'))
    # testSuite.addTest(testUsrSyncClient('test_WC_read'))
    # testSuite.addTest(testUsrSyncClient('test_WP_iterator'))
    testSuite.addTest(testUsrSyncClient('test_WP_analyse'))
    unittest.TextTestRunner().run(testSuite)
