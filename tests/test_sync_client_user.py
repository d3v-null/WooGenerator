import random
import traceback
import unittest
from bisect import insort
from pprint import pformat

from tests.test_sync_client import AbstractSyncClientTestCase

from context import tests_datadir, woogenerator
from woogenerator.client.user import (UsrSyncClientSqlWP, UsrSyncClientSshAct,
                                      UsrSyncClientWC, UsrSyncClientWP)
from woogenerator.coldata import ColDataUser
from woogenerator.conf.namespace import (MatchNamespace, ParserNamespace,
                                         SettingsNamespaceUser,
                                         UpdateNamespace, init_settings)
from woogenerator.conf.parser import ArgumentParserUser
from woogenerator.matching import MatchList, UsernameMatcher
from woogenerator.merger import (do_match, do_merge, populate_master_parsers,
                                 populate_slave_parsers)
from woogenerator.parsing.user import CsvParseUser, CsvParseUserApi
from woogenerator.syncupdate import SyncUpdate, SyncUpdateUsrApi
# from woogenerator.coldata import ColDataWoo
# from woogenerator.parsing.woo import ImportWooProduct, CsvParseWoo, CsvParseTT, WooProdList
from woogenerator.utils import Registrar, SanitationUtils, TimeUtils


class TestUsrSyncClient(AbstractSyncClientTestCase):
    config_file = "merger_config_test.yaml"
    settings_namespace_class = SettingsNamespaceUser
    argument_parser_class = ArgumentParserUser

    # Uncomment to test on live settings
    # config_file = "conf_user.yaml"
    # local_work_dir = "~/Documents/woogenerator/"

    # Uncomment to test on staging settings
    # config_file = "conf_user_test.yaml"
    # local_work_dir = "~/Documents/woogenerator"

    # def setUp(self):
    #     super(TestUsrSyncClient, self).setUp()

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
@unittest.skipIf(
    TestUsrSyncClient.config_file == "merger_config_test.yaml",
    "dummy config won't work"
)
class TestUsrSyncClientHardDestructive(TestUsrSyncClient):
    def test_s_up_read_write_meta(self):
        self.settings.update_slave = True
        slave_client_args = self.settings.slave_upload_client_args
        slave_client_class = self.settings.slave_upload_client_class

        with slave_client_class(**slave_client_args) as slave_client:
            page_iterator = slave_client.get_iterator('users?context=edit')
            first_page = next(page_iterator)
            first_usr = first_page[0]
            print("first_usr is \n%s" % pformat(first_usr))
            first_usr_id = first_usr['id']
            first_usr_grade = first_usr.get('meta',{}).get('client_grade')
            new_grade = TimeUtils.get_ms_timestamp()
            print("new_grade is %s" % pformat(new_grade))
            slave_client.upload_changes(
                first_usr_id, {'meta':{'client_grade':new_grade}}
            )

            response = slave_client.service.get('users/%s?context=edit' % first_usr_id)
            self.assertTrue(response)
            self.assertTrue(response.json())
            print("updated usr is \n%s" % pformat(response.json()))

            self.assertEqual(
                new_grade,
                response.json().get('meta',{}).get('client_grade')
            )

            slave_client.upload_changes(
                first_usr_id, {'meta':{'client_grade':first_usr_grade}}
            )

            response = slave_client.service.get('users/%s?context=edit' % first_usr_id)
            self.assertTrue(response)
            self.assertTrue(response.json())
            print("finally, usr is \n%s" % pformat(response.json()))

    def test_s_up_delete_meta(self):
        self.settings.update_slave = True
        slave_client_args = self.settings.slave_upload_client_args
        slave_client_class = self.settings.slave_upload_client_class

        with slave_client_class(**slave_client_args) as slave_client:
            page_iterator = slave_client.get_iterator('users?context=edit')
            first_page = next(page_iterator)
            first_usr = first_page[0]
            print("first_usr is \n%s" % pformat(first_usr))
            first_usr_id = first_usr['id']
            first_usr_grade = first_usr.get('meta',{}).get('client_grade')
            new_grade = None
            print("new_grade is %s" % pformat(new_grade))
            slave_client.upload_changes(
                first_usr_id, {'meta':{'client_grade':new_grade}}
            )

            response = slave_client.service.get('users/%s?context=edit' % first_usr_id)
            self.assertTrue(response)
            self.assertTrue(response.json())
            print("updated usr is \n%s" % pformat(response.json()))

            self.assertEqual(
                new_grade,
                response.json().get('meta',{}).get('client_grade')
            )

            slave_client.upload_changes(
                first_usr_id, {'meta':{'client_grade':first_usr_grade}}
            )

            response = slave_client.service.get('users/%s?context=edit' % first_usr_id)
            self.assertTrue(response)
            self.assertTrue(response.json())
            print("finally, usr is \n%s" % pformat(response.json()))

    def test_s_up_ead_write(self):
        self.settings.update_slave = True
        slave_client_args = self.settings.slave_upload_client_args
        slave_client_class = self.settings.slave_upload_client_class

        with slave_client_class(**slave_client_args) as slave_client:
            page_iterator = slave_client.get_iterator('users?context=edit')
            first_page = next(page_iterator)
            first_usr = first_page[0]
            first_usr_id = first_usr['id']
            first_usr_description = first_usr['description']
            new_description = TimeUtils.get_ms_timestamp()
            slave_client.upload_changes(
                first_usr_id, {'description':new_description}
            )

            response = slave_client.service.get('users/%s' % first_usr_id)
            self.assertTrue(response)
            self.assertTrue(response.json())

            self.assertEqual(
                new_description,
                response.json().get('description')
            )

            slave_client.upload_changes(
                first_usr_id, {'description':first_usr_description}
            )




@unittest.skip("Desctructive tests not mocked yet")
class TestUsrSyncClientDestructive(TestUsrSyncClient):
    def test_sqlwp_analyse(self):
        # TODO: Mock out SSH component
        self.settings.download_slave = True

        sa_parser = CsvParseUser(
            cols=ColDataUser.get_import_cols(),
            defaults=ColDataUser.get_defaults()
        )

        with UsrSyncClientSqlWP(
            **self.settings.slave_download_client_args
        ) as sql_client:
            sql_client.analyse_remote(sa_parser, since='2016-01-01 00:00:00')

        # CsvParseUser.print_basic_columns( list(chain( *sa_parser.emails.values() )) )
        self.assertIn('neil@technotan.com.au', sa_parser.emails)

    def test_ssh_act_upload(self):
        self.settings.download_master = True

        fields = {
            "ABN": "1",
            "MYOB Card ID": "C000001",
        }

        master_download_client_args = self.settings.master_download_client_args
        # print "master_download_client_args: %s" % repr(master_download_client_args)

        with UsrSyncClientSshAct(**master_download_client_args) as client:
            response = client.upload_changes('C000001', fields)
            self.assertTrue(response)
        # print response

    def test_wc_read(self):
        response = []
        with UsrSyncClientWC(self.settings.slave_wc_api_params) as client:
            response = client.get_iterator()
        # print tabulate(list(response)[:10], headers='keys')
        # print list(response)
        self.assertTrue(response)

    # def test_WC_Upload_bad(self):
    #     fields = {"user_email": "neil@technotan.com.au"}
    #
    #     response = ''
    #     with UsrSyncClientWC(self.settings.slave_wc_api_params) as client:
    #         response = client.upload_changes(2, fields)
    #
    #     print response
    #
    # def test_WC_Upload_good(self):
    #     fields = {"first_name": "neil"}
    #
    #     response = ''
    #     with UsrSyncClientWC(self.settings.slave_wc_api_params) as client:
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
    #     with UsrSyncClientWC(self.settings.slave_wc_api_params) as client:
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
    #     with UsrSyncClientWC(self.settings.slave_wc_api_params) as client:
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
        with UsrSyncClientWP(self.settings.slave_wp_api_params) as client:
            response = client.get_iterator()
        # print tabulate(list(response)[:10], headers='keys')
        # print list(response)
        self.assertTrue(response)

    def test_wp_iterator(self):
        with UsrSyncClientWP(self.settings.slave_wp_api_params) as slave_client:
            iterator = slave_client.get_iterator('users?context=edit')
            self.assertTrue(next(iterator))

    @unittest.skip("takes too long")
    def test_wp_analyse(self):
        #TODO: mock this out

        # print "API Import cols: "
        api_import_cols = ColDataUser.get_wpapi_import_cols()
        self.assertTrue(api_import_cols)

        sa_parser = CsvParseUserApi(
            cols=ColDataUser.get_wp_import_cols(),
            defaults=ColDataUser.get_defaults()
        )

        with UsrSyncClientWP(self.settings.slave_wp_api_params) as slave_client:
            slave_client.analyse_remote(sa_parser)

        self.assertTrue(sa_parser.objects)
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
@unittest.skipIf(
    TestUsrSyncClient.config_file == "merger_config_test.yaml",
    "dummy config won't work"
)
class TestUsrSyncClientConstructors(TestUsrSyncClient):

    def test_make_usr_m_up_client(self):
        self.settings.update_master = True
        master_client_args = self.settings.master_upload_client_args
        master_client_class = self.settings.master_upload_client_class
        with master_client_class(**master_client_args) as master_client:
            self.assertTrue(master_client)

    def test_make_usr_s_up_client(self):
        self.settings.update_slave = True
        slave_client_args = self.settings.slave_upload_client_args
        self.assertTrue(slave_client_args['connect_params']['api_key'])
        slave_client_class = self.settings.slave_upload_client_class
        with slave_client_class(**slave_client_args) as slave_client:
            self.assertTrue(slave_client)

    def test_make_usr_m_down_client(self):
        self.settings.download_master = True
        master_client_args = self.settings.master_download_client_args
        master_client_class = self.settings.master_download_client_class
        with master_client_class(**master_client_args) as master_client:
            self.assertTrue(master_client)

    def test_make_usr_s_down_client(self):
        self.settings.download_slave = True
        slave_client_args = self.settings.slave_download_client_args
        self.assertTrue(slave_client_args['connect_params']['remote_bind_address'][0])
        self.assertTrue(slave_client_args['connect_params']['remote_bind_address'][1])
        slave_client_class = self.settings.slave_download_client_class
        with slave_client_class(**slave_client_args) as slave_client:
            self.assertTrue(slave_client)

@unittest.skip("no config file yet")
class TestSyncUpdateUsr(AbstractSyncClientTestCase):
    # yaml_path = "merger_config.yaml"
    optionNamePrefix = 'test_'

    def __init__(self, *args, **kwargs):
        super(TestSyncUpdateUsr, self).__init__(*args, **kwargs)

    def process_config(self, config):
        wp_srv_offset = config.get(self.optionNamePrefix + 'wp_srv_offset', 0)
        wp_api_key = config.get(self.optionNamePrefix + 'wp_api_key')
        wp_api_secret = config.get(self.optionNamePrefix + 'wp_api_secret')
        store_url = config.get(self.optionNamePrefix + 'store_url', '')
        wp_user = config.get(self.optionNamePrefix + 'wp_user')
        wp_pass = config.get(self.optionNamePrefix + 'wp_pass')
        wp_callback = config.get(self.optionNamePrefix + 'wp_callback')
        merge_mode = config.get('merge_mode', 'sync')
        master_name = config.get('master_name', 'MASTER')
        slave_name = config.get('slave_name', 'SLAVE')
        default_last_sync = config.get('default_last_sync')

        TimeUtils.set_wp_srv_offset(wp_srv_offset)
        SyncUpdate.set_globals(master_name, slave_name, merge_mode,
                               default_last_sync)

        self.slave_wp_api_params = {
            'api_key': wp_api_key,
            'api_secret': wp_api_secret,
            'url': store_url,
            'wp_user': wp_user,
            'wp_pass': wp_pass,
            'callback': wp_callback
        }

        # Registrar.DEBUG_UPDATE = True

    def setUp(self):
        super(TestSyncUpdateUsr, self).setUp()

        for var in ['slave_wp_api_params']:
            self.assertTrue(getattr(self, var))
            # print var, getattr(self, var)

        # Registrar.DEBUG_API = True

    def test_upload_slave_changes(self):

        ma_parser = CsvParseUser(
            cols=ColDataUser.get_act_import_cols(),
            defaults=ColDataUser.get_defaults())

        master_bus_type = "Salon"
        master_client_grade = str(random.random())
        master_uname = "neil"

        master_data = [
            map(unicode, row)
            for row in [[
                "E-mail", "Role", "First Name", "Surname", "Nick Name",
                "Contact", "Client Grade", "Direct Brand", "Agent",
                "Birth Date", "Mobile Phone", "Fax", "Company", "Address 1",
                "Address 2", "City", "Postcode", "State", "Country", "Phone",
                "Home Address 1", "Home Address 2", "Home City",
                "Home Postcode", "Home Country", "Home State", "MYOB Card ID",
                "MYOB Customer Card ID", "Web Site", "ABN", "Business Type",
                "Referred By", "Lead Source", "Mobile Phone Preferred",
                "Phone Preferred", "Personal E-mail", "Edited in Act",
                "Wordpress Username", "display_name", "ID", "updated"
            ], [
                "neil@technotan.com.au", "ADMIN", "Neil", "Cunliffe-Williams",
                "Neil Cunliffe-Williams", "", master_client_grade, "TT", "",
                "", +61416160912, "", "Laserphile", "7 Grosvenor Road", "",
                "Bayswater", 6053, "WA", "AU", "0416160912",
                "7 Grosvenor Road", "", "Bayswater", 6053, "AU", "WA", "", "",
                "http://technotan.com.au", 32, master_bus_type, "", "", "", "",
                "", "", master_uname, "Neil", 1, "2015-07-13 22:33:05"
            ]]
        ]

        ma_parser.analyse_rows(master_data)

        # print "MASTER RECORDS: \n", ma_parser.tabulate()

        sa_parser = CsvParseUserApi(
            cols=ColDataUser.get_wp_import_cols(),
            defaults=ColDataUser.get_defaults())

        with UsrSyncClientWP(self.slave_wp_api_params) as slave_client:
            slave_client.analyse_remote(sa_parser, search=master_uname)

        # print "SLAVE RECORDS: \n", sa_parser.tabulate()

        updates = []
        global_matches = MatchList()

        # Matching
        username_matcher = UsernameMatcher()
        username_matcher.process_registers(sa_parser.usernames,
                                           ma_parser.usernames)
        global_matches.add_matches(username_matcher.pure_matches)

        # print "username matches (%d pure)" % len(username_matcher.pure_matches)

        sync_cols = ColDataUser.get_sync_cols()

        for count, match in enumerate(global_matches):
            m_object = match.m_objects[0]
            s_object = match.s_objects[0]

            sync_update = SyncUpdateUsrApi(m_object, s_object)
            sync_update.update(sync_cols)

            # print "SyncUpdate: ", sync_update.tabulate()

            if not sync_update:
                continue

            if sync_update.s_updated:
                insort(updates, sync_update)

        slave_failures = []

        #
        response_json = {}

        with UsrSyncClientWP(self.slave_wp_api_params) as slave_client:

            for count, update in enumerate(updates):
                try:
                    response = update.update_slave(slave_client)
                    # print "response (code) is %s" % response
                    assert \
                        response, \
                        "response should exist because update should not be empty. update: %s" % \
                            update.tabulate(tablefmt="html")
                    if response:
                        # print "response text: %s" % response.text
                        response_json = response.json()

                except Exception as exc:
                    slave_failures.append({
                        'update':
                        update,
                        'master':
                        SanitationUtils.coerce_unicode(update.new_m_object),
                        'slave':
                        SanitationUtils.coerce_unicode(update.new_s_object),
                        'mchanges':
                        SanitationUtils.coerce_unicode(
                            update.get_master_updates()),
                        'schanges':
                        SanitationUtils.coerce_unicode(
                            update.get_slave_updates()),
                        'exception':
                        repr(exc)
                    })
                    Registrar.register_error(
                        "ERROR UPDATING SLAVE (%s): %s\n%s" %
                        (update.slave_id, repr(exc), traceback.format_exc()))

        self.assertTrue(response_json.get('meta'))
        self.assertEqual(
            response_json.get('meta', {}).get('business_type'),
            master_bus_type)
        self.assertEqual(
            response_json.get('meta', {}).get('client_grade'),
            master_client_grade)

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
