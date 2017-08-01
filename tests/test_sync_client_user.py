import unittest
from pprint import pprint

from context import woogenerator
from tests.test_sync_client import AbstractSyncClientTestCase
from woogenerator.client.user import (UsrSyncClientSqlWP, UsrSyncClientSshAct,
                                      UsrSyncClientWC, UsrSyncClientWP)
from woogenerator.coldata import ColDataUser
from woogenerator.parsing.user import CsvParseUser, CsvParseUserApi
from woogenerator.utils import TimeUtils


@unittest.skip('no config file yet')
class TestUsrSyncClient(AbstractSyncClientTestCase):
    yaml_path = "merger_config.yaml"
    optionNamePrefix = 'test_'
    # optionNamePrefix = 'dummy_'

    def __init__(self, *args, **kwargs):
        super(TestUsrSyncClient, self).__init__(*args, **kwargs)
        self.ssh_tunnel_forwarder_params = {}
        self.py_my_sqlconnect_params = {}
        self.jsonconnect_params = {}
        self.actconnect_params = {}
        self.act_db_params = {}
        self.fs_params = {}

    def process_config(self, config):
        in_folder = "../input/"
        out_folder = "../output/"

        if 'in_folder' in config.keys():
            in_folder = config['in_folder']
        if 'out_folder' in config.keys():
            out_folder = config['out_folder']
        # if 'logFolder' in config.keys():
        #     logFolder = config['logFolder']

        ssh_user = config.get(self.optionNamePrefix + 'ssh_user')
        ssh_pass = config.get(self.optionNamePrefix + 'ssh_pass')
        ssh_host = config.get(self.optionNamePrefix + 'ssh_host')
        ssh_port = config.get(self.optionNamePrefix + 'ssh_port', 22)
        m_ssh_user = config.get(self.optionNamePrefix + 'm_ssh_user')
        m_ssh_pass = config.get(self.optionNamePrefix + 'm_ssh_pass')
        m_ssh_host = config.get(self.optionNamePrefix + 'm_ssh_host')
        m_ssh_port = config.get(self.optionNamePrefix + 'm_ssh_port', 22)
        remote_bind_host = config.get(
            self.optionNamePrefix + 'remote_bind_host', '127.0.0.1')
        remote_bind_port = config.get(
            self.optionNamePrefix + 'remote_bind_port', 3306)
        db_user = config.get(self.optionNamePrefix + 'db_user')
        db_pass = config.get(self.optionNamePrefix + 'db_pass')
        db_name = config.get(self.optionNamePrefix + 'db_name')
        db_charset = config.get(
            self.optionNamePrefix + 'db_charset', 'utf8mb4')
        wp_srv_offset = config.get(self.optionNamePrefix + 'wp_srv_offset', 0)
        m_db_user = config.get(self.optionNamePrefix + 'm_db_user')
        m_db_pass = config.get(self.optionNamePrefix + 'm_db_pass')
        m_db_name = config.get(self.optionNamePrefix + 'm_db_name')
        m_db_host = config.get(self.optionNamePrefix + 'm_db_host')
        m_x_cmd = config.get(self.optionNamePrefix + 'm_x_cmd')
        m_i_cmd = config.get(self.optionNamePrefix + 'm_i_cmd')
        tbl_prefix = config.get(self.optionNamePrefix + 'tbl_prefix', '')
        # wp_user = config.get(self.optionNamePrefix+'wp_user', '')
        # wp_pass = config.get(self.optionNamePrefix+'wp_pass', '')
        wc_api_key = config.get(self.optionNamePrefix + 'wc_api_key')
        wc_api_secret = config.get(self.optionNamePrefix + 'wc_api_secret')
        wp_api_key = config.get(self.optionNamePrefix + 'wp_api_key')
        wp_api_secret = config.get(self.optionNamePrefix + 'wp_api_secret')
        store_url = config.get(self.optionNamePrefix + 'store_url', '')
        wp_user = config.get(self.optionNamePrefix + 'wp_user')
        wp_pass = config.get(self.optionNamePrefix + 'wp_pass')
        wp_callback = config.get(self.optionNamePrefix + 'wp_callback')
        remote_export_folder = config.get(
            self.optionNamePrefix + 'remote_export_folder', '')

        TimeUtils.set_wp_srv_offset(wp_srv_offset)

        act_fields = ";".join(ColDataUser.get_act_import_cols())

        ssh_tunnel_forwarder_address = (ssh_host, ssh_port)
        ssh_tunnel_forwarder_bind_addr = (remote_bind_host, remote_bind_port)

        self.ssh_tunnel_forwarder_params = {
            'ssh_address_or_host': ssh_tunnel_forwarder_address,
            'ssh_password': ssh_pass,
            'ssh_username': ssh_user,
            'remote_bind_address': ssh_tunnel_forwarder_bind_addr,
        }

        self.py_my_sqlconnect_params = {
            'host': 'localhost',
            'user': db_user,
            'password': db_pass,
            'db': db_name,
            'charset': db_charset,
            'use_unicode': True,
            'tbl_prefix': tbl_prefix,
            # 'srv_offset': wp_srv_offset,
        }

        self.wc_api_params = {
            'api_key': wc_api_key,
            'api_secret': wc_api_secret,
            'url': store_url
        }

        self.wp_api_params = {
            'api_key': wp_api_key,
            'api_secret': wp_api_secret,
            'url': store_url,
            'wp_user': wp_user,
            'wp_pass': wp_pass,
            'callback': wp_callback
        }

        # json_uri = store_url + 'wp-json/wp/v2'
        #
        # self.jsonconnect_params = {
        #     'json_uri': json_uri,
        #     'wp_user': wp_user,
        #     'wp_pass': wp_pass
        # }

        self.actconnect_params = {
            'hostname': m_ssh_host,
            'port': m_ssh_port,
            'username': m_ssh_user,
            'password': m_ssh_pass,
        }

        self.act_db_params = {
            'db_x_exe': m_x_cmd,
            'db_i_exe': m_i_cmd,
            'db_name': m_db_name,
            'db_host': m_db_host,
            'db_user': m_db_user,
            'db_pass': m_db_pass,
            'fields': act_fields,
        }

        self.fs_params = {
            'import_name': self.import_name,
            'remote_export_folder': remote_export_folder,
            'in_folder': in_folder,
            'out_folder': out_folder
        }

    def setUp(self):
        super(TestUsrSyncClient, self).setUp()

        for var in ['ssh_tunnel_forwarder_params', 'py_my_sqlconnect_params',
                    'wc_api_params', 'actconnect_params', 'act_db_params']:
            self.assertTrue(var)

            # print var, getattr(self, var)

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

    def test_sqlwp_analyse(self):
        sa_parser = CsvParseUser(
            cols=ColDataUser.get_import_cols(),
            defaults=ColDataUser.get_defaults()
        )

        with UsrSyncClientSqlWP(
            self.ssh_tunnel_forwarder_params,
            self.py_my_sqlconnect_params
        ) as sql_client:
            sql_client.analyse_remote(sa_parser, since='2016-01-01 00:00:00')

        # CsvParseUser.print_basic_columns( list(chain( *sa_parser.emails.values() )) )
        self.assertIn('neil@technotan.com.au', sa_parser.emails)

    @unittest.skip
    def test_ssh_act_upload(self):
        fields = {
            "ABN": "1",
            "MYOB Card ID": "C000001",
        }

        with UsrSyncClientSshAct(
            self.actconnect_params,
            self.act_db_params,
            self.fs_params
        ) as client:
            response = client.upload_changes('C000001', fields)
            self.assertTrue(response)
        # print response

    # @unittest.skip
    # def test_JSON_read(self):
    #     response = ''
    #     with UsrSyncClient_JSON(self.jsonconnect_params) as client:
    #         response = client.service.get_posts()
    #     print response
    #     self.assertTrue(response)
    #
    # @unittest.skip
    # def test_JSON_Upload_bad(self):
    #     fields = {"user_email": "neil@technotan.com.au"}
    #
    #     response = ''
    #     with UsrSyncClient_JSON(self.jsonconnect_params) as client:
    #         response = client.upload_changes(2, fields)
    #
    #     print response
    #
    # @unittest.skip
    # def test_JSON_Upload_good(self):
    #     fields = {"first_name": "neil"}
    #
    #     response = ''
    #     with UsrSyncClient_JSON(self.jsonconnect_params) as client:
    #         response = client.upload_changes(1, fields)
    #
    #     self.assertTrue(response)
    #
    # @unittest.skip
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
    #     with UsrSyncClientSqlWP(
    #         self.ssh_tunnel_forwarder_params,
    #         self.py_my_sqlconnect_params
    #     ) as sql_client:
    #         sql_client.assert_connect()
    #         sql_client.db_params['port'] = sql_client.service.local_bind_address[-1]
    #         cursor = pymysql.connect( **sql_client.db_params ).cursor()
    #
    #         sql = """
    #         SELECT user_url
    #         FROM {tbl_u}
    #         WHERE `ID` = {user_id}""".format(
    #             tbl_u = sql_client.tbl_prefix + 'users',
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
    # @unittest.skip
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
    #     with UsrSyncClientSqlWP(
    #         self.ssh_tunnel_forwarder_params,
    #         self.py_my_sqlconnect_params
    #     ) as sql_client:
    #         sql_client.assert_connect()
    #         sql_client.db_params['port'] = sql_client.service.local_bind_address[-1]
    #         cursor = pymysql.connect( **sql_client.db_params ).cursor()
    #
    #         sql = """
    #         SELECT user_url
    #         FROM {tbl_u}
    #         WHERE `ID` = {user_id}""".format(
    #             tbl_u = sql_client.tbl_prefix + 'users',
    #             user_id = user_id
    #         )
    #
    #         cursor.execute(sql)
    #
    #         updated = list(list(cursor)[0])[0]
    #
    #     self.assertTrue(response)
    #     self.assertEqual(url, updated)

    def test_wc_read(self):
        response = []
        with UsrSyncClientWC(self.wc_api_params) as client:
            response = client.get_iterator()
        # print tabulate(list(response)[:10], headers='keys')
        # print list(response)
        self.assertTrue(response)

    # def test_WC_Upload_bad(self):
    #     fields = {"user_email": "neil@technotan.com.au"}
    #
    #     response = ''
    #     with UsrSyncClientWC(self.wc_api_params) as client:
    #         response = client.upload_changes(2, fields)
    #
    #     print response
    #
    # def test_WC_Upload_good(self):
    #     fields = {"first_name": "neil"}
    #
    #     response = ''
    #     with UsrSyncClientWC(self.wc_api_params) as client:
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
    #     with UsrSyncClientWC(self.wc_api_params) as client:
    #         response = client.upload_changes(user_id, fields)
    #
    #     updated = ''
    #     with UsrSyncClientSqlWP(
    #         self.ssh_tunnel_forwarder_params,
    #         self.py_my_sqlconnect_params
    #     ) as sql_client:
    #         sql_client.assert_connect()
    #         sql_client.db_params['port'] = sql_client.service.local_bind_address[-1]
    #         cursor = pymysql.connect( **sql_client.db_params ).cursor()
    #
    #         sql = """
    #         SELECT user_url
    #         FROM {tbl_u}
    #         WHERE `ID` = {user_id}""".format(
    #             tbl_u = sql_client.tbl_prefix + 'users',
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
    #     with UsrSyncClientWC(self.wc_api_params) as client:
    #         response = client.upload_changes(user_id, fields)
    #
    #     updated = ''
    #     with UsrSyncClientSqlWP(
    #         self.ssh_tunnel_forwarder_params,
    #         self.py_my_sqlconnect_params
    #     ) as sql_client:
    #         sql_client.assert_connect()
    #         sql_client.db_params['port'] = sql_client.service.local_bind_address[-1]
    #         cursor = pymysql.connect( **sql_client.db_params ).cursor()
    #
    #         sql = """
    #         SELECT user_url
    #         FROM {tbl_u}
    #         WHERE `ID` = {user_id}""".format(
    #             tbl_u = sql_client.tbl_prefix + 'users',
    #             user_id = user_id
    #         )
    #
    #         cursor.execute(sql)
    #
    #         updated = list(list(cursor)[0])[0]
    #
    #     self.assertTrue(response)
    #     self.assertEqual(url, updated)

    def test_wp_read(self):
        response = []
        with UsrSyncClientWP(self.wp_api_params) as client:
            response = client.get_iterator()
        # print tabulate(list(response)[:10], headers='keys')
        # print list(response)
        self.assertTrue(response)

    def test_wp_iterator(self):
        with UsrSyncClientWP(self.wp_api_params) as slave_client:
            iterator = slave_client.get_iterator('users?context=edit')
            for page in iterator:
                pprint(page)

    def test_wp_analyse(self):
        # print "API Import cols: "
        pprint(ColDataUser.get_wpapi_import_cols())

        sa_parser = CsvParseUserApi(
            cols=ColDataUser.get_wp_import_cols(),
            defaults=ColDataUser.get_defaults()
        )

        with UsrSyncClientWP(self.wp_api_params) as slave_client:
            slave_client.analyse_remote(sa_parser)

        # print sa_parser.tabulate()

    # def test_SSH_download(self):
    #     with UsrSyncClientSshAct(self.actconnect_params, self.act_db_params, self.fs_params) as client:
    #         response = client.get_delete_file('act_usr_exp/act_x_2016-05-26_15-03-07.csv', 'downloadtest.csv')

    # def test_SSH_Upload(self):
    #     fields = {
    #         "Phone": "0413 300 930",
    #         "MYOB Card ID": "C004897",
    #     }
    #
    #     response = ''
    #     with UsrSyncClientSshAct(self.actconnect_params, self.act_db_params, self.fs_params) as client:
    #         response = client.upload_changes('C004897', fields)
    #
    #     print response


if __name__ == '__main__':
    unittest.main()
    # testSuite = unittest.TestSuite()
    # testSuite.addTest(TestUsrSyncClient('test_JSON_Upload_Core_Easy'))
    # testSuite.addTest(TestUsrSyncClient('test_JSON_Upload_Core_Hard'))
    # testSuite.addTest(TestUsrSyncClient('test_wp_read'))
    # testSuite.addTest(TestUsrSyncClient('test_wc_read'))
    # testSuite.addTest(TestUsrSyncClient('test_wp_iterator'))
    # testSuite.addTest(TestUsrSyncClient('test_wp_analyse'))
    # unittest.TextTestRunner().run(testSuite)
