from os import sys, path
if __name__ == '__main__' and __package__ is None:
    sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

from unittest import TestCase, main, skip
from source.coldata import *

class testColData(TestCase):
    def setUp(self):
        pass

class testColDataUser(testColData):
    def setUp(self):
        super(testColData, self).setUp()

    def test_getImportCols(self):
        importCols = ColData_User.getImportCols()
        self.assertItemsEqual(importCols,
                         ['MYOB Card ID', 'E-mail', 'Wordpress Username',
                         'Wordpress ID', 'Role', 'Contact', 'First Name', 'Surname',
                         'Middle Name', 'Name Suffix', 'Name Prefix', 'Memo',
                         'Spouse', 'Salutation', 'Company', 'Mobile Phone', 'Phone',
                         'Fax', 'Mobile Phone Preferred', 'Phone Preferred',
                         'Address 1', 'Address 2', 'City', 'Postcode', 'State',
                         'Country', 'Shire', 'Home Address 1', 'Home Address 2',
                         'Home City','Home Postcode','Home Country','Home State',
                         'MYOB Customer Card ID','Client Grade','Direct Brand','Agent',
                         'Web Site', 'ABN', 'Business Type', 'Lead Source',
                         'Referred By', 'Personal E-mail', 'Create Date', 'Wordpress Start Date',
                         'Edited in Act', 'Edited in Wordpress', 'Last Sale', 'Facebook Username',
                         'Twitter Username', 'GooglePlus Username', 'Instagram Username',
                         'Added to mailing list'])

    def test_getActTrackedCols(self):
        actTrackedCols = ColData_User.getACTTrackedCols()
        self.assertDictEqual(actTrackedCols,
                              OrderedDict(
                                  [('Edited E-mail', ['E-mail']),
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
                                   ('Edited Web Site', ['Web Site']),
                                   ('Edited Personal E-mail', ['Personal E-mail']),
                                   ('Edited Social Media', ['Facebook Username', 'Twitter Username',
                                                            'GooglePlus Username', 'Instagram Username'])]))

    def test_getDeltaCols(self):
        DeltaCols = ColData_User.getDeltaCols()
        self.assertDictEqual(DeltaCols,OrderedDict([('Role', 'Delta Role')]))

    def test_getAllWpDbCols(self):
        dbCols = ColData_User.getAllWPDBCols()
        self.assertItemsEqual(dbCols, OrderedDict([('myob_card_id', 'MYOB Card ID'), ('act_role', 'Role'), ('nickname', 'Contact'), ('first_name', 'First Name'), ('last_name', 'Surname'), ('middle_name', 'Middle Name'), ('name_suffix', 'Name Suffix'), ('name_prefix', 'Name Prefix'), ('name_notes', 'Memo'), ('spouse', 'Spouse'), ('salutation', 'Salutation'), ('billing_company', 'Company'), ('mobile_number', 'Mobile Phone'), ('billing_phone', 'Phone'), ('fax_number', 'Fax'), ('pref_mob', 'Mobile Phone Preferred'), ('pref_tel', 'Phone Preferred'), ('billing_address_1', 'Address 1'), ('billing_address_2', 'Address 2'), ('billing_city', 'City'), ('billing_postcode', 'Postcode'), ('billing_state', 'State'), ('billing_country', 'Country'), ('shipping_address_1', 'Home Address 1'), ('shipping_address_2', 'Home Address 2'), ('shipping_city', 'Home City'), ('shipping_postcode', 'Home Postcode'), ('shipping_country', 'Home Country'), ('shipping_state', 'Home State'), ('myob_customer_card_id', 'MYOB Customer Card ID'), ('client_grade', 'Client Grade'), ('direct_brand', 'Direct Brand'), ('agent', 'Agent'), ('abn', 'ABN'), ('business_type', 'Business Type'), ('how_hear_about', 'Lead Source'), ('referred_by', 'Referred By'), ('personal_email', 'Personal E-mail'), ('edited_in_act', 'Edited in Act'), ('act_last_sale', 'Last Sale'), ('facebook', 'Facebook Username'), ('twitter', 'Twitter Username'), ('gplus', 'GooglePlus Username'), ('instagram', 'Instagram Username'), ('mailing_list', 'Added to mailing list'), ('user_email', 'E-mail'), ('user_login', 'Wordpress Username'), ('ID', 'Wordpress ID'), ('user_url', 'Web Site'), ('user_registered', 'Wordpress Start Date')]))

    def test_getWPAPICols(self):
        api_cols = ColData_Woo.getWPAPICols()
        print "test_getWPAPICols", api_cols.keys()

    def test_getWPAPIVariableCols(self):
        api_cols = ColData_Woo.getWPAPIVariableCols()
        print "test_getWPAPIVariableCols", api_cols.keys()

if __name__ == '__main__':
    main()
