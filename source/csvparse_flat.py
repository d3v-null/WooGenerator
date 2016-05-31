# from csvparse_woo import ImportWooProduct
from copy import deepcopy
from collections import OrderedDict
from coldata import ColData_User, ColData_Woo
from contact_objects import ContactAddress, ContactName, ContactPhones, SocialMediaFields
from csvparse_abstract import CSVParse_Base, ImportObject, ObjList
from utils import descriptorUtils, listUtils, SanitationUtils, TimeUtils
import os
# import time
# from pprint import pprint
# import operator
# import re

usrs_per_file = 1000

DEBUG_FLAT = False
# DEBUG_FLAT = True

class ImportFlat(ImportObject):
    pass

class CSVParse_Flat(CSVParse_Base):

    objectContainer = ImportFlat
    # def __init__(self, cols, defaults):
    #     super(CSVParse_Flat, self).__init__(cols, defaults)

class ImportSpecial(ImportFlat):

    ID = descriptorUtils.safeKeyProperty('ID')
    start_time = descriptorUtils.safeKeyProperty('start_time')
    end_time = descriptorUtils.safeKeyProperty('end_time')

    # @property
    # def start_time_iso(self): return TimeUtils.isoTimeToString(self.start_time)

    # @property
    # def end_time_iso(self): return TimeUtils.isoTimeToString(self.end_time)

    def __init__(self, data, rowcount, row):
        super(ImportSpecial, self).__init__(data, rowcount, row)
        try:
            self.ID
        except:
            raise UserWarning('ID exist for Special to be valid')

        self['start_time'] = TimeUtils.gDriveStrpTime(self['FROM'])
        self['end_time'] = TimeUtils.gDriveStrpTime(self['TO'])

    def getIndex(self):
        return self.ID

class CSVParse_Special(CSVParse_Flat):

    objectContainer = ImportSpecial

    def __init__(self, cols=None, defaults=None):
        if cols is None:
            cols = []
        if defaults is None:
            defaults = {}
        extra_cols = [
            "ID",
            "FROM",
            "TO",
            "RNS",
            "RPS",
            "WNS",
            "WPS",
            "XRNS",
            "XRPS",
            "XWNS",
            "XWPS"
        ]
        cols = listUtils.combineLists(cols, extra_cols)

        super(CSVParse_Special, self).__init__(cols, defaults)
        self.objectIndexer = self.getObjectID

    @classmethod
    def getObjectID(self, objectData):
        return objectData.ID

class ImportUser(ImportFlat):

    WPID = descriptorUtils.safeKeyProperty('Wordpress ID')
    email = descriptorUtils.safeKeyProperty('E-mail')
    # emails = descriptorUtils.safeKeyProperty('E-mails')
    MYOBID = descriptorUtils.safeKeyProperty('MYOB Card ID')
    username = descriptorUtils.safeKeyProperty('Wordpress Username')
    role = descriptorUtils.safeKeyProperty('Role')
    # contact_schema = descriptorUtils.safeKeyProperty('contact_schema')
    billing_address = descriptorUtils.safeKeyProperty('Address')
    shipping_address = descriptorUtils.safeKeyProperty('Home Address')
    name = descriptorUtils.safeKeyProperty('Name')

    aliasMapping = {
        'Address': ['Address 1', 'Address 2', 'City', 'Postcode', 'State',
                    'Country'],
        'Home Address': ['Home Address 1', 'Home Address 2', 'Home City',
                         'Home Postcode', 'Home State', 'Home Country'],
        'Name': ['Name Prefix', 'First Name', 'Middle Name', 'Surname',
                 'Name Suffix', 'Company', 'Memo', 'Contact'],
        'Phone Numbers': ['Phone', 'Mobile Phone', 'Fax'],
        'Social Media': ['Facebook Username', 'Twitter Username',
                         'GooglePlus Username', 'Instagram Username',
                         ],
                        #  'Web Site'],
        # 'E-mails': ['E-mail', 'Personal E-mail']
    }

    @property
    def index(self): return "%s | %s" % (self.WPID, self.MYOBID)

    @property
    def act_modtime(self):
        return TimeUtils.actStrptime(self.get('Edited in Act', 0))

    @property
    def wp_modtime(self):
        return TimeUtils.wpServerToLocalTime(TimeUtils.wpStrptime(self.get('Edited in Wordpress', 0) ))

    @property
    def last_sale(self):
        return TimeUtils.actStrptime(self.get('Last Sale', 0))

    @property
    def last_modtime(self):
        times = [self.act_modtime, self.wp_modtime]
        return max(times)

    def __init__(self, data, rowcount=None, row=None, **kwargs):
        super(ImportUser, self).__init__(data, rowcount, row)
        for key in ['E-mail', 'MYOB Card ID', 'Wordpress Username', 'Role', 'contact_schema', 'Wordpress ID']:
            val = kwargs.get(key, "")
            if(val):
                self[key] = val
            elif(not self.get(key)):
                self[key] = ""
            if(DEBUG_FLAT): self.registerMessage("key: {key}, value: {val}".format(key=key, val=self[key]))
        if(DEBUG_FLAT): self.registerMessage("data:" + repr(data))
        self.initContactObjects(data)

    def initContactObjects(self, data):
        # emails_kwargs = OrderedDict(filter(None, [\
        #     ((key, data.get(value)) if data.get(value) else None) for key, value in\
        #     {
        #         'email'         : 'E-mail',
        #         'personal_email': 'Personal E-mail',
        #     }.items()
        # ]))
        #
        # self['E-mails'] = EmailFields(
        #     **emails_kwargs
        # )

        name_kwargs = OrderedDict(filter(None, [\
            ((key, data.get(value)) if data.get(value) else None) for key, value in\
            {
                'first_name'    : 'First Name',
                'middle_name'   : 'Middle Name',
                'family_name'   : 'Surname',
                'name_prefix'   : 'Name Prefix',
                'name_suffix'   : 'Name Suffix',
                'contact'       : 'Contact',
                'company'       : 'Company',
                'city'          : 'City',
                'country'       : 'Country',
                'state'         : 'State',
            }.items()
        ]))

        self['Name'] = ContactName(
            **name_kwargs
        )

        assert self['Name'] is not None, \
               'contact is missing mandatory fields: something went wrong'

        address_kwargs = OrderedDict(filter(None, [\
            ((key, data.get(value)) if data.get(value) else None) \
            for key, value in\
            {
                'line1'     : 'Address 1',
                'line2'     : 'Address 2',
                'city'      : 'City',
                'postcode'  : 'Postcode',
                'state'     : 'State',
                'country'   : 'Country',
                'company'       : 'Company',
            }.items()
        ]))

        self['Address'] = ContactAddress(
            **address_kwargs
        )

        # print "ADDRESS: ", self['Address']

        alt_address_kwargs = OrderedDict(filter(None, [\
            ((key, data.get(value)) if data.get(value) else None) for key, value in\
            {
                'line1'     : 'Home Address 1',
                'line2'     : 'Home Address 2',
                'city'      : 'Home City',
                'postcode'  : 'Home Postcode',
                'state'     : 'Home State',
                'country'   : 'Home Country',
                'company'   : 'Company',
            }.items()
        ]))

        self['Home Address'] = ContactAddress(
            **alt_address_kwargs
        )

        # print "HOME ADDRESS: ", self['Home Address']

        phone_kwargs = OrderedDict(filter(None, [\
            ((key, data.get(value)) if data.get(value) else None) for key, value in\
            {
                'mob_number': 'Mobile Phone',
                'tel_number': 'Phone',
                'fax_number': 'Fax',
                'mob_pref'  : 'Mobile Phone Preferred',
                'tel_pref'  : 'Phone Preferred',
            }.items()
        ]))

        self['Phone Numbers'] = ContactPhones(
            **phone_kwargs
        )

        social_media_kwargs = OrderedDict(filter(None, [\
            ((key, data.get(value)) if data.get(value) else None) for key, value in\
            {
                'facebook': 'Facebook Username',
                'twitter': 'Twitter Username',
                'gplus': 'GooglePlus Username',
                'instagram': 'Instagram Username',
                'website': 'Web Site',
            }.items()
        ]))

        self['Social Media'] = SocialMediaFields(
            **social_media_kwargs
        )

        emails = []
        if data.get('E-mail'):
            emails = listUtils.combineLists(emails, SanitationUtils.findallEmails(data['E-mail']))
        if data.get('Personal E-mail'):
            emails = listUtils.combineLists(emails, SanitationUtils.findAllImages(data.get('Personal E-mail')))
        self['E-mail'] = emails.pop(0) if emails else None
        self['Personal E-mail'] = ', '.join(emails)

        urls = []
        if data.get('Web Site'):
            urls = SanitationUtils.combineLists(urls,
                                                SanitationUtils.findallURLs(data['Web Site']))
        self['Web Site'] = urls.pop(0) if urls else None

        # if not self['Emails'].valid:
        #     self['emails_reason'] = '\n'.join(filter(None, [
        #         self['Emails'].reason,
        #     ]))

        if not self['Address'].valid or not self['Home Address'].valid:
            self['address_reason'] = '\n'.join(filter(None, [
                'ADDRESS: ' + self['Address'].reason if not self['Address'].valid else None,
                'HOME ADDRESS: ' + self['Home Address'].reason if not self['Home Address'].valid else None
            ]))

        if not self['Name'].valid:
            self['name_reason'] = '\n'.join(filter(None, [
                self['Name'].reason,
            ]))

        if not self['Phone Numbers'].valid:
            self['phone_reason'] = '\n'.join(filter(None, [
                self['Phone Numbers'].reason,
            ]))

        if not self['Social Media'].valid:
            self['social_reason'] = '\n'.join(filter(None, [
                self['Social Media'].reason,
            ]))

    def refreshContactObjects(self):
        pass
        # self.initContactObjects(self.__getstate__())

    def __getitem__(self, key):
        for alias, keys in self.aliasMapping.items():
            if key in keys and alias in self:
                return self[alias][key]
        return super(ImportUser, self).__getitem__(key)

    def __setitem__(self, key, val):
        # print "setting obj %s to %s " % (key, repr(val))
        for alias, keys in self.aliasMapping.items():
            if key in keys and alias in self:
                self[alias][key] = val
                return
        # if key is 'Name': print "setting Name to ", val
        super(ImportUser, self).__setitem__(key, val)
        # if key is 'Name':
            # print self.__getitem__(key)

    def get(self, key, default = None):
        for alias, keys in self.aliasMapping.items():
            if key in keys and self[alias]:
                return self[alias][key]
        try:
            return super(ImportUser, self).get(key, default)
        except:
            return None

    @staticmethod
    def getContainer():
        return UsrObjList

    def addressesActLike(self):
        actLike = True
        for address in filter(None, map(lambda key: self.get(key), ['Address', 'Home Address'])):
            if address.schema and address.schema != 'act':
                actLike = False
        return actLike

    def usernameActLike(self):
        return self.username == self.MYOBID

    def __repr__(self):
        return "<%s> %s | %s | %s | %s | %s" % (self.index, self.email, self.MYOBID, self.role, self.username, self.WPID)

class UsrObjList(ObjList):
    def __init__(self, objects=None, indexer=None):
        super(UsrObjList, self).__init__(objects, indexer=None)
        self._objList_type = 'User'

    def getSanitizer(self, tablefmt=None):
        if tablefmt is 'html':
            return SanitationUtils.sanitizeForXml
        elif tablefmt is 'simple':
            return SanitationUtils.sanitizeForTable
        else:
            return super(UsrObjList, self).getSanitizer(tablefmt)


    def getReportCols(self):
        usrData = ColData_User()
        report_cols = usrData.getReportCols()
        # for exclude_col in ['E-mail','MYOB Card ID','Wordpress Username','Role']:
        #     if exclude_col in report_cols:
        #         del report_cols[exclude_col]

        return report_cols



class CSVParse_User(CSVParse_Flat):

    objectContainer = ImportUser

    def __init__(self, cols=[], defaults = {}, contact_schema = None, filterItems = None, limit=None):
        extra_cols = [
            # 'ABN', 'Added to mailing list', 'Address 1', 'Address 2', 'Agent', 'Birth Date',
            # 'book_spray_tan', 'Book-a-Tan Expiry', 'Business Type', 'Canvasser', ''
            # 'post_status'
        ]
        extra_defaults =  OrderedDict([
            # ('post_status', 'publish'),
            # ('last_import', importName),
        ])
        cols = listUtils.combineLists( cols, extra_cols )
        defaults = listUtils.combineOrderedDicts( defaults, extra_defaults )
        super(CSVParse_User, self).__init__(cols, defaults, limit)
        self.contact_schema = contact_schema
        self.filterItems = filterItems
        # self.itemIndexer = self.getUsername

    # def getKwargs(self, allData, container, **kwargs):
    #     kwargs = super(CSVParse_User, self).getKwargs(allData, container, **kwargs)
    #     for key in ['E-mail', 'MYOB Card ID', 'username', 'Role']:
    #         assert kwargs[key] is not None
    #     return kwargs

    # def newObject(self, rowcount, row, **kwargs):
    #     for key in ['E-mail', 'MYOB Card ID', 'username', 'Role']:
    #         try:
    #             assert kwargs[key]
    #         except:
    #             kwargs[key] = self.retrieveColFromRow

    def clearTransients(self):
        super(CSVParse_User, self).clearTransients()
        self.roles = OrderedDict()
        self.noroles = OrderedDict()
        self.emails = OrderedDict()
        self.noemails = OrderedDict()
        self.cards = OrderedDict()
        self.nocards = OrderedDict()
        self.usernames = OrderedDict()
        self.nousernames = OrderedDict()
        # self.companies = OrderedDict()
        self.filtered = OrderedDict()
        self.badName = OrderedDict()
        self.badAddress = OrderedDict()
        # self.badEmail = OrderedDict()

    def sanitizeCell(self, cell):
        return SanitationUtils.sanitizeCell(cell)

    def registerEmail(self, objectData, email):
        self.registerAnything(
            objectData,
            self.emails,
            email,
            singular = False,
            registerName = 'emails'
        )

    def registerNoEmail(self, objectData):
        self.registerAnything(
            objectData,
            self.noemails,
            objectData.index,
            singular = True,
            registerName = 'noemails'
        )

    def registerRole(self, objectData, role):
        self.registerAnything(
            objectData,
            self.roles,
            role,
            singular = False,
            registerName = 'roles'
        )

    def registerNoRole(self, objectData):
        self.registerAnything(
            objectData,
            self.noroles,
            objectData.index,
            singular = True,
            registerName = 'noroles'
        )

    def registerCard(self, objectData, card):
        self.registerAnything(
            objectData,
            self.cards,
            card,
            singular = False,
            registerName = 'cards'
        )

    def registerNoCard(self, objectData):
        self.registerAnything(
            objectData,
            self.nocards,
            objectData.index,
            singular = True,
            registerName = 'nocards'
        )

    def registerUsername(self, objectData, username):
        self.registerAnything(
            objectData,
            self.usernames,
            username,
            singular = False,
            registerName = 'usernames'
        )

    def registerNoUsername(self, objectData):
        self.registerAnything(
            objectData,
            self.nousernames,
            objectData.index,
            singular = True,
            registerName = 'nousernames'
        )

    # def registerCompany(self, objectData, company):
    #     self.registerAnything(
    #         objectData,
    #         self.companies,
    #         company,
    #         singular = False,
    #         registerName = 'companies'
    #     )

    def registerFiltered(self, objectData):
        self.registerAnything(
            objectData,
            self.filtered,
            objectData.index,
            singular = True,
            registerName = 'filtered'
        )

    def registerBadAddress(self, objectData, address):
        self.registerAnything(
            objectData,
            self.badAddress,
            objectData.index,
            singular = True,
            registerName = 'badaddress'
        )

    def registerBadName(self, objectData, name):
        self.registerAnything(
            objectData,
            self.badName,
            objectData.index,
            singular = True,
            registerName = 'badname'
        )

    def registerBadEmail(self, objectData, name):
        self.registerAnything(
            objectData,
            self.badEmail,
            objectData.index,
            singular = True,
            registerName = 'bademail'
        )

    def validateFilters(self, objectData):
        if self.filterItems:
            if 'roles' in self.filterItems.keys() and objectData.role not in self.filterItems['roles']:
                self.registerMessage("could not register object %s because did not match role" % objectData.__repr__() )
                return False
            if 'sinceM' in self.filterItems.keys() and objectData.act_modtime < self.filterItems['sinceM']:
                self.registerMessage("could not register object %s because did not meet sinceM condition" % objectData.__repr__() )
                return False
            if 'sinceS' in self.filterItems.keys() and objectData.wp_modtime < self.filterItems['sinceS']:
                self.registerMessage("could not register object %s because did not meet sinceS condition" % objectData.__repr__() )
                return False
            if objectData.username in self.filterItems.get('users', []): return True
            if objectData.MYOBID in self.filterItems.get('cards', []): return True
            if objectData.email in self.filterItems.get('emails', []): return True
            self.registerMessage("could not register object %s because did not meet users, cards or emails conditions" % objectData.__repr__() )
            return False
        else:
            return True


    def registerObject(self, objectData):
        if not self.validateFilters(objectData):
            self.registerFiltered(objectData)
            return

        email = objectData.email
        if email and SanitationUtils.stringIsEmail(email) :
            self.registerEmail(objectData, email)
        else:
            if(DEBUG_FLAT): self.registerWarning("invalid email address: %s"%email)
            self.registerNoEmail(objectData)

        role = objectData.role
        if role:
            self.registerRole(objectData, role)
        else:
            # self.registerWarning("invalid role: %s"%role)
            self.registerNoRole(objectData)

        card = objectData.MYOBID
        if card and SanitationUtils.stringIsMYOBID(card):
            self.registerCard(objectData, card)
        else:
            self.registerNoCard(objectData)

        username = objectData.username
        if username:
            self.registerUsername(objectData, username)
        else:
            if(DEBUG_FLAT): self.registerWarning("invalid username: %s"%username)
            self.registerNoUsername(objectData)

        # company = objectData['Company']
        # # if DEBUG_FLAT: SanitationUtils.safePrint(repr(objectData), company)
        # if company:
        #     self.registerCompany(objectData, company)

        addresses = [objectData.billing_address, objectData.shipping_address]
        for address in filter(None, addresses):
            if not address.valid:
                reason = address.reason
                assert reason, "there must be a reason that this address is invalid: " + address
                self.registerBadAddress(objectData, address)

        name = objectData.name
        # print "NAME OF %s IS %s" % (repr(objectData), name.__str__(out_schema="flat"))
        if not name.valid:
            reason = name.reason
            assert reason, "there must be a reason that this name is invalid: " + name
            # print "registering bad name: ", SanitationUtils.coerceBytes(name)
            self.registerBadName(objectData, name)

        # emails = objectData.emails
        # if not emails.valid:
        #     reason = emails.reason
        #     self.registerBadEmail(objectData, emails)

        super(CSVParse_User, self).registerObject(objectData)

    def getKwargs(self, allData, container, **kwargs):
        kwargs = super(CSVParse_User, self).getKwargs(allData, container, **kwargs)
        if not 'contact_schema' in kwargs.keys():
            kwargs['contact_schema'] = self.contact_schema
        return kwargs

    # def processRoles(self, objectData):
    #     role = objectData.role
    #     if not self.roles.get(role): self.roles[role] = OrderedDict()
    #     self.registerAnything(
    #         objectData,
    #         self.roles[role],
    #         self.getUsername,
    #         singular = True,
    #         registerName = 'roles'
    #     )

    # def processObject(self, objectData):
    #     # objectData.username = self.getMYOBID(objectData)
    #     super(CSVParse_Flat, self).processObject(objectData)
    #     self.processRoles(objectData)

    # def analyzeRow(self, row, objectData):
    #     objectData = super(CSVParse_Flat, self).analyseRow(row, objectData)
    #     return objectData

    @staticmethod
    def printBasicColumns(users):
        usrList = UsrObjList()
        for user in users:
            usrList.addObject(user)

        cols = ColData_User.getBasicCols()

        SanitationUtils.safePrint( usrList.tabulate(
            cols,
            tablefmt = 'simple'
        ))


class ImportSqlProduct(ImportFlat):
    ID          = descriptorUtils.safeKeyProperty('ID')
    codesum     = descriptorUtils.safeKeyProperty('codesum')
    itemsum     = descriptorUtils.safeKeyProperty('itemsum')

    @property
    def index(self):
        return self.codesum

class CSVParse_WPSQLProd(CSVParse_Flat):

    objectContainer = ImportSqlProduct

    """docstring for CSVParse_WPSQLProd"""
    # def __init__(self, arg):
        # super(CSVParse_WPSQLProd, self).__init__()

# def testSqlParser(inFolder, outFolder):
#     prodData = ColData_Woo()
#
#     sqlRows = [
#         ['ID', 'codesum', 'itemsum', 'title_1', 'title_2', 'pricing_rules', 'price', 'sale_price', 'sale_price_dates_from', 'sale_price_dates_to', 'RNR', 'RNS', 'RNF', 'RNT', 'RPR', 'RPS', 'RPF', 'RPT', 'WNR', 'WNS', 'WNF', 'WNT', 'WPR', 'WPS', 'WPF', 'WPT', 'DNR', 'DNS', 'DNF', 'DNT', 'DPR', 'DPS', 'DPF', 'DPT', 'CVC', 'weight', 'length', 'width', 'height', 'stock', 'stock_status', 'manage_stock'],
#         (4481L, 'CTMITT-REM', 'Tan Removal Mitt', 'Tan Removal Mitt', '', 'Tan Removal Mitt', '14.90', '11.175', '', '', '14.90', '11.175', '1479744000', '1482336000', '12.90', '', '', '', '8.90', '6.675000000000001', '1479744000', '1482336000', '8.01', '', '', '', '5.34', '', '', '', '5.12', '', '', '', '1', '0.04', '147', '6', '232', '', 'instock', 'no'), (4482L, 'CTMITT-APP', 'Tan Application Mitt', 'Tan Application Mitt', '', 'Tan Application Mitt', '9.90', '7.425000000000001', '', '', '9.90', '7.425000000000001', '1479744000', '1482336000', '8.40', '', '', '', '5.90', '4.425000000000001', '1479744000', '1482336000', '5.31', '', '', '', '3.54', '', '', '', '3.39', '', '', '', '1', '0.04', '147', '3', '232', '', 'instock', 'no'),
#         (4498L, 'CTTC-250', 'Tan in a Can - 250ml', 'Tan in a Can', '250ml', 'Tan in a Can - 250ml', '39.90', '29.924999999999997', '', '', '39.90', '29.924999999999997', '1479744000', '1482336000', '35.90', '', '', '', '24.90', '18.674999999999997', '1479744000', '1482336000', '22.41', '', '', '', '17.43', '', '', '', '16.18', '', '', '', '1', '0.33', '50', '50', '210', '', 'instock', 'no'),
#         (4506L, 'ACS-FBLK', 'Female C-String \xe2\x80\x94 Black', '', '', 'Female C-String \xe2\x80\x94 Black', '8.4', '', '', '', '9.9', '7.425000000000001', '1440000000', '1440950400', '8.4', '', '', '', '5.4', '4.050000000000001', '1440000000', '1440950400', '4.59', '', '', '', '3.27', '', '', '', '3.11', '', '', '', '1', '0.01', '80', '120', '75', '', 'instock', 'no'),
#         (4507L, 'ACS-FLEP', 'Female C-String \xe2\x80\x94 Leopard Print', '', '', 'Female C-String \xe2\x80\x94 Leopard Print', '8.4', '', '', '', '9.9', '7.425000000000001', '1440000000', '1440950400', '8.4', '', '', '', '5.4', '4.050000000000001', '1440000000', '1440950400', '4.59', '', '', '', '3.27', '', '', '', '3.11', '', '', '', '1', '0.01', '80', '120', '75', '', 'instock', 'no'),
#         (4508L, 'ACS-MBLK', 'Male C-String \xe2\x80\x94 Black', '', '', 'Male C-String \xe2\x80\x94 Black', '9.9', '', '', '', '11.9', '8.925', '1440000000', '1440950400', '9.9', '', '', '', '6.4', '4.800000000000001', '1440000000', '1440950400', '5.44', '', '', '', '3.84', '', '', '', '3.68', '', '', '', '1', '0.02', '170', '100', '90', '', 'instock', 'no'),
#         (4509L, 'ACS-WBF', 'C-String Wash Bag \xe2\x80\x94 Female', '', '', 'C-String Wash Bag \xe2\x80\x94 Female', '3.4', '', '', '', '3.9', '2.925', '1440000000', '1440950400', '3.4', '', '', '', '2.4', '1.7999999999999998', '1440000000', '1440950400', '2.04', '', '', '', '1.44', '', '', '', '1.38', '', '', '', '0.5', '0.01', '220', '150', '2', '', 'instock', 'no'),
#         (4510L, 'ACS-WBM', 'C-String Wash Bag \xe2\x80\x94 Male', '', '', 'C-String Wash Bag \xe2\x80\x94 Male', '3.4', '', '', '', '3.9', '2.925', '1440000000', '1440950400', '3.4', '', '', '', '2.4', '1.7999999999999998', '1440000000', '1440950400', '2.04', '', '', '', '1.44', '', '', '', '1.38', '', '', '', '0.5', '0.01', '220', '150', '2', '', 'instock', 'no'),
#         (4511L, 'ATOW-BLKL', 'Black Towel (No logo) \xe2\x80\x94 Large (560 x 1150mm)', '', '', 'Black Towel (No logo) \xe2\x80\x94 Large (560 x 1150mm)', '', '', '', '', '', '', '', '', '', '', '', '', '11.9', '8.925', '1440000000', '1440950400', '10.71', '', '', '', '8.33', '', '', '', '8.33', '', '', '', '0.75', '0.41', '230', '310', '30', '', 'instock', 'no'),
#         (4512L, 'ATOW-GRYS', 'Grey Towel (No logo) \xe2\x80\x94 Small (400 x 570mm)', '', '', 'Grey Towel (No logo) \xe2\x80\x94 Small (400 x 570mm)', '', '', '', '', '', '', '', '', '', '', '', '', '9.9', '7.425000000000001', '1440000000', '1440950400', '8.91', '', '', '', '6.93', '', '', '', '6.93', '', '', '', '0.75', '0.16', '200', '200', '18', '', 'instock', 'no'),
#         (4513L, 'AGL-CP5', 'Cotton Glove Pack x5 Pairs', '', '', 'Cotton Glove Pack x5 Pairs', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '0', '', '', '', '', '', 'instock', 'no'),
#         (4515L, 'ATBCS', 'TechnoTan Brush Cleaning Solution', '', '', 'TechnoTan Brush Cleaning Solution', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '0', '', '', '', '', '', 'instock', 'no'),
#         (4516L, 'ATTOW-BLKXL', 'Black Towel (TT logo) \xe2\x80\x94 Extra Large (750mm X 1440mm)', '', '', 'Black Towel (TT logo) \xe2\x80\x94 Extra Large (750mm X 1440mm)', '', '', '', '', '', '', '', '', '', '', '', '', '14.9', '11.175', '1440000000', '1440950400', '13.41', '', '', '', '10.43', '', '', '', '10.43', '', '', '', '0.8', '0.66', '260', '380', '50', '', 'instock', 'no'),
#         (4517L, 'ATTOW-BLKL', 'Black Towel (TT logo) \xe2\x80\x94 Large  (560mm X 1150mm)', '', '', 'Black Towel (TT logo) \xe2\x80\x94 Large  (560mm X 1150mm)', '', '', '', '', '', '', '', '', '', '', '', '', '12.9', '9.675', '1440000000', '1440950400', '11.61', '', '', '', '9.03', '', '', '', '9.03', '', '', '', '0.8', '0.41', '230', '310', '30', '', 'outofstock', 'no'),
#         (4518L, 'ATTOW-GRYS', 'Grey Towel (TT logo) \xe2\x80\x94 Small  (400mm X 570mm)', '', '', 'Grey Towel (TT logo) \xe2\x80\x94 Small  (400mm X 570mm)', '', '', '', '', '', '', '', '', '', '', '', '', '10.9', '8.175', '1440000000', '1440950400', '9.81', '', '', '', '7.63', '', '', '', '7.63', '', '', '', '0.8', '0.16', '200', '200', '18', '', 'instock', 'no'),
#         (4519L, 'ATUMB-L', 'Large Umbrella (TT logo)', '', '', 'Large Umbrella (TT logo)', '15.9', '', '', '', '17.9', '13.424999999999999', '1440000000', '1440950400', '15.9', '', '', '', '11.9', '8.925', '1440000000', '1440950400', '10.71', '', '', '', '8.33', '', '', '', '8.33', '', '', '', '1', '0.35', '115', '830', '115', '', 'instock', 'no'),
#         (4520L, 'ATCB-MINBLK', 'Mini TechnoTan Cooler Bag \xe2\x80\x94 Black', '', '', 'Mini TechnoTan Cooler Bag \xe2\x80\x94 Black', '8.9', '', '', '', '9.9', '7.425000000000001', '1440000000', '1440950400', '8.9', '', '', '', '6.9', '5.175000000000001', '1440000000', '1440950400', '6.21', '', '', '', '4.83', '', '', '', '4.83', '', '', '', '0.75', '0.21', '370', '165', '25', '', 'instock', 'no'),
#         (4521L, 'ATCB-LRGBLK', 'Insulated TechnoTan Cooler Bag \xe2\x80\x94 Black', '', '', 'Insulated TechnoTan Cooler Bag \xe2\x80\x94 Black', '67.5', '', '', '', '75', '56.25', '1440000000', '1440950400', '67.5', '', '', '', '50', '37.5', '1440000000', '1440950400', '45', '', '', '', '35', '', '', '', '35', '', '', '', '0.75', '2.54', '285', '500', '100', '', 'instock', 'no'),
#         (4522L, 'ATCB-LRGPNK', 'Insulated TechnoTan Cooler Bag \xe2\x80\x94 Pink', '', '', 'Insulated TechnoTan Cooler Bag \xe2\x80\x94 Pink', '67.5', '', '', '', '75', '56.25', '1440000000', '1440950400', '67.5', '', '', '', '50', '37.5', '1440000000', '1440950400', '45', '', '', '', '35', '', '', '', '35', '', '', '', '0.75', '2.54', '285', '500', '100', '', 'instock', 'no'),
#         (4523L, 'ATCB-LRGBLU', 'Insulated TechnoTan Cooler Bag \xe2\x80\x94 Blue', '', '', 'Insulated TechnoTan Cooler Bag \xe2\x80\x94 Blue', '67.5', '', '', '', '75', '56.25', '1440000000', '1440950400', '67.5', '', '', '', '50', '37.5', '1440000000', '1440950400', '45', '', '', '', '35', '', '', '', '35', '', '', '', '0.75', '2.54', '285', '500', '100', '', 'instock', 'no'),
#         (4525L, 'ATBAG-PLA50', 'Plastic Carry Bag \xe2\x80\x94 Pack / 50', '', '', 'Plastic Carry Bag \xe2\x80\x94 Pack / 50', '', '', '', '', '', '', '', '', '', '', '', '', '10', '7.5', '1440000000', '1440950400', '9', '', '', '', '6', '', '', '', '5.75', '', '', '', '0.5', '0.51', '402', '258', '10', '', 'instock', 'no'),
#         (4526L, 'ATBAG-GIF10', 'Gloss Gift Bag,  \xe2\x80\x94 Pack / 10', '', '', 'Gloss Gift Bag,  \xe2\x80\x94 Pack / 10', '', '', '', '', '12.25', '', '', '', '10.4', '', '', '', '7', '5.25', '1440000000', '1440950400', '6.3', '', '', '', '4.2', '', '', '', '4.03', '', '', '', '0.5', '0.84', '275', '280', '70', '', 'instock', 'no'),
#         (4527L, 'ATBAG-ECO10', 'Eco Carry Bag \xe2\x80\x94 Pack / 10', '', '', 'Eco Carry Bag \xe2\x80\x94 Pack / 10', '', '', '', '', '', '', '', '', '', '', '', '', '6', '4.5', '1440000000', '1440950400', '5.4', '', '', '', '3.6', '', '', '', '3.45', '', '', '', '0.5', '0.49', '275', '280', '70', '', 'instock', 'no'),
#         (4528L, 'ATBAG-DEL5', 'Deluxe Eco Carry Bag \xe2\x80\x94 Pack / 5', '', '', 'Deluxe Eco Carry Bag \xe2\x80\x94 Pack / 5', '', '', '', '', '8.75', '', '', '', '7.4', '', '', '', '5', '3.75', '1440000000', '1440950400', '4.5', '', '', '', '3', '', '', '', '2.88', '', '', '', '0.5', '0.45', '400', '300', '30', '', 'instock', 'no'),
#         (4529L, 'ATFS-BLK', 'TechnoTan Floor Sheet \xe2\x80\x94 Black', '', '', 'TechnoTan Floor Sheet \xe2\x80\x94 Black', '', '', '', '', '', '', '', '', '', '', '', '', '35', '26.25', '1440000000', '1440950400', '31.5', '', '', '', '21', '', '', '', '20.13', '', '', '', '1', '0.4', '250', '220', '15', '', 'instock', 'no'),
#         (4530L, 'ATFS-BLU', 'TechnoTan Floor Sheet \xe2\x80\x94 Blue', '', '', 'TechnoTan Floor Sheet \xe2\x80\x94 Blue', '', '', '', '', '', '', '', '', '', '', '', '', '35', '26.25', '1440000000', '1440950400', '31.5', '', '', '', '21', '', '', '', '20.13', '', '', '', '1', '0.4', '250', '220', '15', '', 'instock', 'no'),
#         (4531L, 'SQMITT-APP', 'Tan Application Mitt', '', '', 'Tan Application Mitt', '12.9', '', '', '', '14.9', '11.175', '1440000000', '1440950400', '12.9', '', '', '', '8.9', '6.675000000000001', '1440000000', '1440950400', '7.57', '', '', '', '5.34', '', '', '', '5.12', '', '', '', '1', '0.04', '147', '3', '232', '', 'instock', 'no'),
#         (4532L, 'SQMITT-REM', 'Tan Removal Mitt', '', '', 'Tan Removal Mitt', '8.4', '', '', '', '9.9', '7.425000000000001', '1440000000', '1440950400', '8.4', '', '', '', '5.9', '4.425000000000001', '1440000000', '1440950400', '5.02', '', '', '', '3.54', '', '', '', '3.39', '', '', '', '1', '0.04', '147', '3', '232', '', 'instock', 'no'),
#         (4533L, 'SQEX-MITT', 'Massage Mitt', '', '', 'Massage Mitt', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '0', '', '', '', '', '', 'instock', 'no'),
#         (4534L, 'SQEX-SPO', 'Exfoliating Massage Sponge', '', '', 'Exfoliating Massage Sponge', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '0', '', '', '', '', '', 'instock', 'no'),
#         (4535L, 'SQEX-BS', 'Exfoliating Back Strap', '', '', 'Exfoliating Back Strap', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '0', '', '', '', '', '', 'instock', 'no'),
#         (4536L, 'SQEX-BG', 'Exfoliating Body Gloves', '', '', 'Exfoliating Body Gloves', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '0', '', '', '', '', '', 'instock', 'no'),
#         (4541L, 'SQMBP-BLU', 'Light Blue Polisher Cloth', '', '', 'Light Blue Polisher Cloth', '5.9', '', '', '', '6.9', '5.175000000000001', '1440000000', '1440950400', '5.9', '', '', '', '4', '3.0', '1440000000', '1440950400', '3.4', '', '', '', '2.4', '', '', '', '2.3', '', '', '', '1', '0.03', '200', '150', '2', '', 'instock', 'no'),
#         (4542L, 'SQMBP-PNK', 'Pink Polisher Cloth', '', '', 'Pink Polisher Cloth', '5.9', '', '', '', '6.9', '5.175000000000001', '1440000000', '1440950400', '5.9', '', '', '', '4', '3.0', '1440000000', '1440950400', '3.4', '', '', '', '2.4', '', '', '', '2.3', '', '', '', '1', '0.03', '200', '150', '2', '', 'instock', 'no'),
#         (4543L, 'SQHN-P50BLU', 'Disposable Hair Nets, Pack / 50 \xe2\x80\x94 Blue', '', '', 'Disposable Hair Nets, Pack / 50 \xe2\x80\x94 Blue', '11.9', '', '', '', '13.9', '10.425', '1440000000', '1440950400', '11.9', '', '', '', '7.9', '5.925000000000001', '1440000000', '1440950400', '6.72', '', '', '', '4.77', '', '', '', '4.54', '', '', '', '1', '0.13', '150', '90', '80', '', 'instock', 'no'),
#         (4544L, 'SQHN-P50BLK', 'Disposable Hair Nets, Pack / 50 \xe2\x80\x94 Black', '', '', 'Disposable Hair Nets, Pack / 50 \xe2\x80\x94 Black', '11.9', '', '', '', '13.9', '10.425', '1440000000', '1440950400', '11.9', '', '', '', '7.9', '5.925000000000001', '1440000000', '1440950400', '6.72', '', '', '', '4.77', '', '', '', '4.54', '', '', '', '1', '0.13', '150', '90', '80', '', 'instock', 'no'),
#         (4545L, 'SQHN-P50PNK', 'Disposable Hair Nets, Pack / 50 \xe2\x80\x94 Pink', '', '', 'Disposable Hair Nets, Pack / 50 \xe2\x80\x94 Pink', '11.9', '', '', '', '13.9', '10.425', '1440000000', '1440950400', '11.9', '', '', '', '7.9', '5.925000000000001', '1440000000', '1440950400', '6.72', '', '', '', '4.77', '', '', '', '4.54', '', '', '', '1', '0.13', '150', '90', '80', '', 'instock', 'no'),
#         (4546L, 'SQHN-P50WHI', 'Disposable Hair Nets, Pack / 50 \xe2\x80\x94 White', '', '', 'Disposable Hair Nets, Pack / 50 \xe2\x80\x94 White', '11.9', '', '', '', '13.9', '10.425', '1440000000', '1440950400', '11.9', '', '', '', '7.9', '5.925000000000001', '1440000000', '1440950400', '6.72', '', '', '', '4.77', '', '', '', '4.54', '', '', '', '1', '0.13', '150', '90', '80', '', 'instock', 'no'),
#         (4547L, 'SQGS-P50BLK', 'G Strings, Pack / 50 \xe2\x80\x94 Black', '', '', 'G Strings, Pack / 50 \xe2\x80\x94 Black', '16.9', '', '', '', '19.9', '14.924999999999999', '1440000000', '1440950400', '16.9', '', '', '', '11.9', '8.925', '1440000000', '1440950400', '10.12', '', '', '', '7.14', '', '', '', '6.84', '', '', '', '1', '0.19', '200', '170', '25', '', 'instock', 'no'),
#         (4548L, 'SQGS-P50WHI', 'G Strings, Pack / 50 \xe2\x80\x94 White', '', '', 'G Strings, Pack / 50 \xe2\x80\x94 White', '16.9', '', '', '', '19.9', '14.924999999999999', '1440000000', '1440950400', '16.9', '', '', '', '11.9', '8.925', '1440000000', '1440950400', '10.12', '', '', '', '7.14', '', '', '', '6.84', '', '', '', '1', '0.19', '200', '170', '25', '', 'instock', 'no'),
#         (4549L, 'SQGS-P50BLU', 'G Strings, Pack / 50 \xe2\x80\x94 Blue', '', '', 'G Strings, Pack / 50 \xe2\x80\x94 Blue', '16.9', '', '', '', '19.9', '14.924999999999999', '1440000000', '1440950400', '16.9', '', '', '', '11.9', '8.925', '1440000000', '1440950400', '10.12', '', '', '', '7.14', '', '', '', '6.84', '', '', '', '1', '0.19', '200', '170', '25', '', 'outofstock', 'no')
#     ]
#     sqlRows = [map(SanitationUtils.coerceUnicode, row) for row in sqlRows]
#     sqlParser = CSVParse_WPSQLProd(
#         cols = prodData.getWPCols(),
#         defaults = prodData.getDefaults()
#     )
#
#     sqlParser.analyseRows(sqlRows)
#
#     print sqlParser.objects
#
#
# def testUsrParser(inFolder, outFolder):
#     actPath = os.path.join(inFolder, "200-act-records.csv")
#     # usrPath = os.path.join(outFolder, 'users.csv')
#     # actPath = os.path.join(inFolder, 'partial act records.csv')
#
#     usrData = ColData_User()
#
#     # print "import cols", usrData.getImportCols()
#     # print "defaults", usrData.getDefaults()
#
#     usrParser = CSVParse_User(
#         cols = usrData.getImportCols(),
#         defaults = usrData.getDefaults()
#     )
#
#     usrParser.analyseFile(actPath)
#
#     usrList = UsrObjList()
#
#     for usr in usrParser.objects.values()[:3]:
#         usrList.addObject(usr)
#         clone = deepcopy(usr)
#         usr['Wordpress Username'] = 'jonno'
#         usrList.addObject(clone)
#         # card_id = usr.MYOBID
#         # edit_date = usr.get('Edit Date')
#         # act_date = usr.get('Edited in Act')
#
#     print usrList.tabulate()
#
#     # usrCols = usrData.getUserCols()
#
#     # exportItems(
#     #     usrPath,
#     #     usrData.getColNames(usrCols),
#     #     usrParser.objects.values()
#     # )
#
#     # for role, usrs in usrParser.roles.items():
#     #     for i, u in enumerate(range(0, len(usrs), usrs_per_file)):
#     #         rolPath = os.path.join(outFolder, 'users_%s_%d.csv'%(role,i))
#
#     #         exportItems(
#     #             rolPath,
#     #             usrData.getColNames(usrCols),
#     #             usrs.values()[u:u+usrs_per_file]
#     #         )
#
# def testRefreshUsrContactObj():
#     usr1 = ImportUser(
#         {
#             'First Name': 'Derwent',
#             'Surname': 'Smith',
#             'Name Modified': '2015-11-11 12:55:00'
#         },
#         0,
#         [],
#     )
#
#     print usr1['Name']
#
#     usr2 = ImportUser(
#         {
#             'First Name': 'Abe',
#             'Surname': 'Jackson',
#             'Name Modified': '2015-11-11 12:45:03'
#         },
#         0,
#         [],
#     )
#     print usr2['Name']
#
#     usr1['Name'] = usr2['Name']
#
#     print usr1['Name']
#
# def testCopyUsrContactObj():
#     usr1 = ImportUser(
#         {
#             'First Name': 'Derwent',
#             'Surname': 'Smith'
#         },
#         0,
#         [],
#     )
#
#
#     usr2 = deepcopy(usr1)
#
#     print ("USR1: ",usr1.name, usr1.name.kwargs)
#     print ("USR2: ",usr2.name, usr2.name.kwargs)
#
#     usr2['First Name'] = 'Johnny'
#
#     print ("USR1: ",usr1.name, usr1.name.kwargs)
#     print ("USR2: ",usr2.name, usr2.name.kwargs)
#
#     name2 = usr2['Name']
#
#     print('NAME2:', name2, repr(name2))
#
#     usr1['Name'] = name2
#
#     print ("USR1: ",usr1.name, usr1.name.kwargs)
#     print ("USR2: ",usr2.name, usr2.name.kwargs)
#
#
# if __name__ == '__main__':
#     inFolder = "../input/"
#
#     outFolder = "../output/"
#
#     # testRefreshUsrContactObj()
#     testCopyUsrContactObj()
#
#     # testUsrParser(inFolder, outFolder)
#     # testSqlParser(inFolder, outFolder)
