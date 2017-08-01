import random
# import unittest
import traceback
import unittest
# from tabulate import tabulate
from bisect import insort
from os import path, sys

from context import woogenerator
from test_sync_client import AbstractSyncClientTestCase
from woogenerator.client.user import UsrSyncClientWP
from woogenerator.coldata import ColDataUser
# , CardMatcher, NocardEmailMatcher, EmailMatcher
from woogenerator.matching import MatchList, UsernameMatcher
from woogenerator.parsing.user import (CsvParseUser,  # , ImportUser
                                       CsvParseUserApi)
from woogenerator.syncupdate import SyncUpdate, SyncUpdateUsrApi
from woogenerator.utils import Registrar, SanitationUtils, TimeUtils

if __name__ == '__main__' and __package__ is None:
    sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))



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

        self.wp_api_params = {
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

        for var in ['wp_api_params']:
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

        with UsrSyncClientWP(self.wp_api_params) as slave_client:
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

        with UsrSyncClientWP(self.wp_api_params) as slave_client:

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
