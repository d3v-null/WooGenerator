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

    def test_getActDeltaCols(self):
        actDeltaCols = ColData_User.getACTDeltaCols()
        self.assertDictEqual(actDeltaCols,OrderedDict([('Role', 'Delta Role')]))

if __name__ == '__main__':
    main()
