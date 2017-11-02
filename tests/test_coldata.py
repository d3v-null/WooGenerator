from collections import OrderedDict
import unittest
from unittest import TestCase
import logging

from context import woogenerator
from woogenerator.coldata import ColDataUser, ColDataWoo, ColDataAbstract, ColDataMedia
from woogenerator.utils import Registrar
from pprint import pformat

class TestColData(unittest.TestCase):
    col_data_class = ColDataAbstract

    def setUp(self):
        if self.debug:
            pass
        else:
            logging.basicConfig(level=logging.DEBUG)
            Registrar.DEBUG_ERROR = False
            Registrar.DEBUG_WARN = False
            Registrar.DEBUG_MESSAGE = False

class TestColDataAbstract(TestColData):
    def test_get_target_ancestors(self):
        self.assertEqual(
            self.col_data_class.get_target_ancestors(
                self.col_data_class.targets,
                'wc-legacy-api-v2'
            ),
            ['api', 'wc-api', 'wc-legacy-api', 'wc-legacy-api-v2']
        )

    def test_get_property(self):
        self.assertEqual(
            self.col_data_class.get_handle_property('id', 'path'),
            'id'
        )
        self.assertEqual(
            self.col_data_class.get_handle_property('id', 'path', 'xero-api'),
            None
        )
        self.assertEqual(
            self.col_data_class.get_handle_property('id', 'path', 'sql'),
            'id'
        )
        self.assertEqual(
            self.col_data_class.get_handle_property('id', 'path', 'wp-sql'),
            'ID'
        )
        self.assertEqual(
            self.col_data_class.get_handle_property('id', 'path', 'wp-api'),
            'id'
        )
        self.assertEqual(
            self.col_data_class.get_handle_property('id', 'write'),
            False
        )
        self.assertEqual(
            self.col_data_class.get_handle_property('id', 'write', 'xero-api'),
            False
        )
        self.assertEqual(
            self.col_data_class.get_handle_property('id', 'write', 'sql'),
            False
        )
        self.assertEqual(
            self.col_data_class.get_handle_property('id', 'write', 'wp-sql'),
            False
        )
        self.assertEqual(
            self.col_data_class.get_handle_property('id', 'write', 'wp-api'),
            False
        )
        self.assertEqual(
            self.col_data_class.get_handle_property('id', 'write', 'wp-csv'),
            False
        )

class TestColDataImg(TestColData):
    col_data_class = ColDataMedia
    debug = True

    def test_get_property(self):
        self.assertEqual(
            self.col_data_class.get_handle_property('source_url', 'path'),
            'source_url'
        )
        self.assertEqual(
            self.col_data_class.get_handle_property('source_url', 'path', 'wp-api-v1'),
            'source'
        )
        self.assertEqual(
            self.col_data_class.get_handle_property('source_url', 'path', 'wp-api-v2'),
            'source_url'
        )

    def test_get_handles(self):
        handles_property_v2 = self.col_data_class.get_handles_property('path', 'wp-api-v2')
        if self.debug:
            print("handles_property_v2: %s" % pformat(handles_property_v2))
        self.assertEquals(
            handles_property_v2,
            OrderedDict([('attach_post_id', 'post'), ('attach_post_type', 'type'), ('attach_link', 'link')])
        )


    def test_get_path_translation(self):
        path_translation = self.col_data_class.get_path_translation('wp-api-v2')
        if self.debug:
            print("path_translation: %s" % pformat(path_translation))



class testColDataUser(TestColData):
    col_data_class = ColDataUser
    def setUp(self):
        super(testColDataUser, self).setUp()
        self.maxDiff = None

    def test_getImportCols(self):
        importCols = self.col_data_class.get_import_cols()
        for key in [
            'MYOB Card ID',
            'E-mail',
            'Wordpress Username',
            'Wordpress ID',
            # 'Role',
            'Contact',
            'First Name',
            'Surname',
            'Middle Name',
            'Name Suffix',
            'Name Prefix',
            'Memo',
            'Spouse',
            'Salutation',
            'Company',
            'Mobile Phone',
            'Phone',
            'Fax',
            'Address 1',
            'Address 2',
            'City',
            'Postcode',
            'State',
            'Country',
            'Shire',
            'Home Address 1',
            'Home Address 2',
            'Home City', 'Home Postcode', 'Home Country', 'Home State',
            'MYOB Customer Card ID', 'Client Grade',
            # 'Direct Brand',
            'Agent',
            'Web Site',
            'ABN',
            'Business Type',
            'Lead Source',
            'Referred By',
            'Personal E-mail',
            'Create Date',
            'Wordpress Start Date',
            'Edited in Act',
            'Edited in Wordpress',
            'Last Sale',
            'Facebook Username',
            'Twitter Username',
            'GooglePlus Username',
            'Instagram Username',
            'Added to mailing list',
            'Tans Per Week'
        ]:
            self.assertIn(key, importCols)

    def test_getActTrackedCols(self):
        actTrackedCols = self.col_data_class.get_act_tracked_cols()
        self.assertItemsEqual(
            actTrackedCols,
            OrderedDict([
                ('Edited E-mail', ['E-mail']),
                ('Edited Name', ['Name Prefix', 'First Name', 'Middle Name',
                                 'Surname', 'Name Suffix', 'Salutation', 'Contact']),
                ('Edited Memo', ['Memo', 'Memo']),
                ('Edited Spouse', ['Spouse', 'Spouse']),
                ('Edited Company', ['Company']),
                ('Edited Phone Numbers', ['Mobile Phone', 'Phone', 'Fax']),
                ('Edited Address', ['Address 1', 'Address 2', 'City', 'Postcode',
                                    'State', 'Country', 'Shire']),
                ('Edited Alt Address', ['Home Address 1', 'Home Address 2', 'Home City',
                                        'Home Postcode', 'Home State', 'Home Country']),
                ('Edited Personal E-mail', ['Personal E-mail']),
                ('Edited Web Site', ['Web Site']),
                ('Edited Social Media', ['Facebook Username', 'Twitter Username',
                                         'GooglePlus Username', 'Instagram Username']),
             ]))

    def test_getDeltaCols(self):
        DeltaCols = self.col_data_class.get_delta_cols()
        self.assertItemsEqual(DeltaCols, OrderedDict(
            [
                ('E-mail', 'Delta E-mail'),
                # ('Role Info', 'Delta Role Info')
            ]))

    def test_getAllWpDbCols(self):
        dbCols = self.col_data_class.get_all_wpdb_cols()
        # print "dbCols %s" % pformat(dbCols.items())
        self.assertItemsEqual(dbCols, OrderedDict([
            ('myob_card_id', 'MYOB Card ID'),
            # ('act_role', 'Role'),
            ('nickname', 'Contact'),
            ('first_name', 'First Name'),
            ('last_name', 'Surname'),
            ('middle_name', 'Middle Name'),
            ('name_suffix', 'Name Suffix'),
            ('name_prefix', 'Name Prefix'),
            ('name_notes', 'Memo'),
            ('spouse', 'Spouse'),
            # ('salutation', 'Salutation'),
            ('billing_company', 'Company'),
            ('mobile_number', 'Mobile Phone'),
            ('billing_phone', 'Phone'),
            ('fax_number', 'Fax'),
            # ('pref_mob', 'Mobile Phone Preferred'),
            # ('pref_tel', 'Phone Preferred'),
            ('billing_address_1', 'Address 1'),
            ('billing_address_2', 'Address 2'),
            ('billing_city', 'City'),
            ('billing_postcode', 'Postcode'),
            ('billing_state', 'State'),
            ('billing_country', 'Country'),
            ('shipping_address_1', 'Home Address 1'),
            ('shipping_address_2', 'Home Address 2'),
            ('shipping_city', 'Home City'),
            ('shipping_postcode', 'Home Postcode'),
            ('shipping_country', 'Home Country'),
            ('shipping_state', 'Home State'),
            ('myob_customer_card_id', 'MYOB Customer Card ID'),
            ('client_grade', 'Client Grade'),
            # ('direct_brand', 'Direct Brand'),
            ('agent', 'Agent'),
            ('abn', 'ABN'),
            ('business_type', 'Business Type'),
            ('how_hear_about', 'Lead Source'),
            ('referred_by', 'Referred By'),
            ('tans_per_wk', 'Tans Per Week'),
            ('personal_email', 'Personal E-mail'),
            ('edited_in_act', 'Edited in Act'),
            ('act_last_sale', 'Last Sale'),
            ('facebook', 'Facebook Username'),
            ('twitter', 'Twitter Username'),
            ('gplus', 'GooglePlus Username'),
            ('instagram', 'Instagram Username'),
            ('mailing_list', 'Added to mailing list'),
            ('user_email', 'E-mail'),
            ('user_login', 'Wordpress Username'),
            ('ID', 'Wordpress ID'),
            # ('display_name', 'Contact'),
            ('user_url', 'Web Site'),
            ('user_registered', 'Wordpress Start Date'),
            ('pref_method', 'Pref Method')
        ]))

    def test_getWPAPICols(self):
        api_cols = ColDataWoo.get_wpapi_cols()
        # print "test_getWPAPICols", api_cols.keys()

    def test_getWPAPIVariableCols(self):
        api_cols = ColDataWoo.get_wpapi_variable_cols()
        # print "test_getWPAPIVariableCols", api_cols.keys()

if __name__ == '__main__':
    unittest.main()

# TODO: Implement these test cases
#
# def testColDataMyo():
#     print "Testing ColDataMyo Class:"
#     col_data = ColDataMyo()
#     print col_data.get_import_cols()
#     print col_data.get_defaults()
#     print col_data.get_product_cols()
#
# def testColDataWoo():
#     print "Testing ColDataWoo class:"
#     col_data = ColDataWoo()
#     print col_data.get_import_cols()
#     print col_data.get_defaults()
#     print col_data.get_product_cols()
#
# def testColDataUser():
#     print "Testing ColDataUser class:"
#     col_data = ColDataUser()
#     # print "importCols", col_data.get_import_cols()
#     # print "userCols", col_data.get_user_cols().keys()
#     # print "report_cols", col_data.get_report_cols().keys()
#     # print "capitalCols", col_data.get_capital_cols().keys()
#     # print "sync_cols", col_data.get_sync_cols().keys()
#     print "actCols", col_data.get_act_cols().keys()
#     # print "wpcols", col_data.get_wp_cols().keys()
#     print "get_wp_tracked_cols", col_data.get_wp_tracked_cols()
#     print "get_act_tracked_cols", col_data.get_act_tracked_cols()
#     print "get_act_future_tracked_cols", col_data.get_act_future_tracked_cols()
#
# def testTansyncDefaults():
#     col_data = ColDataUser()
#     print '{'
#     for col, data in col_data.get_tansync_defaults().items():
#         print '"%s": %s,' % (col, json.dumps(data))
#     print '}'
#
# if __name__ == '__main__':
#     # testColDataMyo()
#     # testColDataWoo()
#     testColDataUser()
#     # testTansyncDefaults()
