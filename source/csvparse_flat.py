from utils import descriptorUtils, listUtils, SanitationUtils, AddressUtils
from csvparse_abstract import CSVParse_Base, ImportObject, ObjList
from collections import OrderedDict
from coldata import ColData_User
import os
import csv
import time
from pprint import pprint
import operator
import re

usrs_per_file = 1000

DEBUG_FLAT = False
DEBUG_ADDRESS = False

class ImportFlat(ImportObject):
    pass

class CSVParse_Flat(CSVParse_Base):

    objectContainer = ImportFlat
    # def __init__(self, cols, defaults):
    #     super(CSVParse_Flat, self).__init__(cols, defaults)

class ImportSpecial(ImportFlat):
    def __init__(self,  data, rowcount, row):
        super(ImportSpecial, self).__init__(data, rowcount, row)
        try:
            self.ID
        except:
            raise UserWarning('ID exist for Special to be valid')

    ID = descriptorUtils.safeKeyProperty('ID')

    def getIndex(self):
        return self.ID

class CSVParse_Special(CSVParse_Flat):

    objectContainer = ImportSpecial

    def __init__(self, cols=[], defaults={}):
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

    def getObjectID(self, objectData):
        return objectData.ID     

class ContactAddress(object):
    def __init__(self, schema=None, **kwargs):
        self.kwargs = kwargs
        self.properties = OrderedDict()
        self.valid = True
        self.properties['subunits'] = []
        self.properties['isShop'] = False
        self.properties['deliveries'] = []
        self.properties['floors'] = []
        self.properties['thoroughfares'] = []
        self.properties['buildings'] = []
        self.properties['weak_thoroughfares'] = []
        self.properties['names'] = []
        self.properties['numbers'] = []
        self.properties['unknowns'] = []
        self.properties['ignores'] = []

        if not any( filter(None, map(
            lambda key: kwargs.get(key, ''), 
            ['line1', 'line2', 'city', 'postcode', 'state']
        ))): 
            self.empty = True
            self.valid = False
            self.schema = None
        else:
            if DEBUG_ADDRESS: pprint(kwargs)
            self.empty = False
            if not schema: self.schema = self.__class__.determineSchema(**kwargs)

            lines = filter(None, map(lambda key: kwargs.get(key, ''), ['line1', 'line2']))


            wordsToRemove = []

            if('country' in kwargs.keys() and kwargs.get('country', '')):
                countrySanitized = AddressUtils.sanitizeState(kwargs['country'])
                # wordsToRemove.append(countrySanitized)
                self.properties['country'] = countrySanitized

            if('state' in kwargs.keys() and kwargs.get('state', '')):
                stateSanitized = AddressUtils.sanitizeState(kwargs['state'])
                wordsToRemove.append(stateSanitized)
                stateIdentified = AddressUtils.identifyState(stateSanitized)
                if stateIdentified != stateSanitized:
                    wordsToRemove.append(stateIdentified)
                    self.properties['state'] = stateIdentified
                else:
                    self.properties['state'] = stateSanitized
                # if stateSanitized in AddressUtils.stateAbbreviations.keys():
                #     self.properties['state'] = stateSanitized
                # else:
                #     for state, abbrebiations in AddressUtils.stateAbbreviations.items():
                #         if stateSanitized in abbrebiations:
                #             self.properties['state'] = state
                #             wordsToRemove.append(state)
                #     if not self.properties.get('state'):
                #         self.properties['state'] = stateSanitized
                # for word in wordsToRemove:
                #     for i, line in enumerate(lines):
                #         if SanitationUtils.stringContainsNumbers(line):
                #             new_line = AddressUtils.addressRemoveEndWord(line, word)
                #             if(line != new_line):
                #                 print ( "removing word %s from %s -> %s" % (word,line, new_line))
                #             lines[i] = new_line
            # else:
            #     for state, abbrebiations in AddressUtils.stateAbbreviations.items():
            #         for word in [state] + abbrebiations:
            #             for i, line in enumerate(lines):
            #                 new_line = AddressUtils.addressRemoveEndWord(line, word)
            #                 if new_line != line:
            #                     lines[i] = new_line
            #                     print "found state %s in %s -> %s" % (state, line, new_line)


            if 'city' in kwargs.keys() and kwargs.get('city', ''):
                citySanitized = AddressUtils.sanitizeState(kwargs['city'])
                self.properties['city'] = citySanitized
                # wordsToRemove.append(citySanitized)

            if 'postcode' in kwargs.keys() and kwargs.get('postcode'):
                self.properties['postcode'] = kwargs.get('postcode')

            numberLines = filter(
                SanitationUtils.stringContainsNumbers, 
                lines
            )
            numberlessLines = filter(
                SanitationUtils.stringContainsNoNumbers,
                lines
            )
            if(numberlessLines):
                if len(numberlessLines) == 1:
                    self.properties['names'] += numberlessLines
                else:
                    self.valid = False

            # Extract subunit numbers and floor level


            for i, line in enumerate(numberLines):
                tokens = AddressUtils.tokenizeAddress(line)
                for j, token in enumerate(tokens):
                    if DEBUG_ADDRESS: print "-> token[%d]: " % j, SanitationUtils.makeSafeOutput(token )
                    delivery = AddressUtils.getDelivery(token)
                    if(delivery):
                        # delivery_type, delivery_name = delivery
                        self.properties['deliveries'] += [delivery]
                        continue
                    subunit = AddressUtils.getSubunit(token)
                    if(subunit):
                        subunit_type, subunit_number = subunit
                        if subunit_type in ['SHOP', 'SE', 'KSK', 'SHRM']:
                            self.isShop = True
                        self.properties['subunits'] += [subunit]
                        continue
                    floor = AddressUtils.getFloor(token)
                    if(floor):
                        # floor_type, floor_number = floor
                        self.properties['floors'] += [floor]
                        continue
                    thoroughfare = AddressUtils.getThoroughfare(token)
                    if(thoroughfare):
                        # thoroughfare_number, thoroughfare_name, thoroughfare_type, thoroughfare_suffix = thoroughfare
                        self.properties['thoroughfares'] += [thoroughfare]
                        continue
                    building = AddressUtils.getBuilding(token)
                    if(building):
                        # building_name, building_type = building
                        self.properties['buildings'] += [building]
                        continue
                    weak_thoroughfare = AddressUtils.getThoroughfare(token)
                    if(weak_thoroughfare):
                        # weak_thoroughfare_name, weak_thoroughfare_type, weak_thoroughfare_suffix = weak_thoroughfare
                        self.properties['weak_thoroughfares'] += [weak_thoroughfare]
                        continue
                    #ignore if unknown is city or state
                    if token in wordsToRemove:
                        self.properties['ignores'] += [token]
                        if DEBUG_ADDRESS: print "IGNORING WORD", token
                        continue

                    state = AddressUtils.getState(token)
                    if(state and not self.properties['state']):
                        #this might be the state but can't rule it out being something else
                        self.properties['possible_states'] = list( 
                            set( self.properties['possible_states'] ) + set([token])
                        )
                        if DEBUG_ADDRESS: print "IGNORING STATE", state
                        continue

                    name = AddressUtils.getName(token)
                    if(name and not self.properties['names']):
                        self.properties['names'] += [name]
                        continue
                    number = AddressUtils.getNumber(token)

                    #there can only be one number
                    if(number and not self.properties['numbers']):
                        self.properties['numbers'] += [number]
                        continue
                    self.properties['unknowns'] += [token]
                    self.valid = False
                    # break

            if self.properties['numbers'] :
                if not self.properties['subunits']:
                    self.properties['subunits'] += [(None, self.properties['numbers'][0])]
                else:
                    self.valid = False
            #if any unknowns match number, then add them as a blank subunit

            if(schema in ['act']):
                pass
                #TODO: THIS
            else:
                pass
                #TODO: THIS

            # print SanitationUtils.makeSafeOutput( self.__str__())
    
    @property
    def subunits(self):
        if(self.properties['subunits']):
            return ", ".join(
                [" ".join(filter(None, subunit)) for subunit in self.properties['subunits']]
            )

    @property
    def floors(self):
        if self.properties['floors']:
            return ", ".join(
                [" ".join(filter(None,floor)) for floor in self.properties['floors']]
            )

    @property
    def buildings(self):
        if self.properties['buildings']:
            return ", ".join(
                [" ".join(filter(None,building)) for building in self.properties['buildings']]
            )
    
    @property
    def names(self):
        if self.properties['names']:
            return ", ".join(
                [unicode(name) for name in self.properties['names']]
            )

    @property
    def deliveries(self):
        if self.properties['deliveries']:
            return ", ".join(
                [" ".join(filter(None, delivery)) for delivery in self.properties['deliveries']]
            )
    
    @property
    def thoroughfares(self):
        if self.properties['thoroughfares'] or self.properties['weak_thoroughfares']:
            return ", ".join(
                [" ".join(filter(None, thoroughfare)) for thoroughfare in \
                    self.properties['thoroughfares'] + self.properties['weak_thoroughfares']]
            )

    @property
    def state(self):
        return self.properties.get('state') if self.valid else self.kwargs.get('state')    


    @property
    def line1(self):
        if(self.valid):
            if not self.names and self.deliveries:
                try:
                    assert not any([self.subunits, self.floors, self.buildings]), "can't have deliveries and buildings"
                except AssertionError as e:
                    print "failed assertion", e
                    pprint (self)
                elements = [self.deliveries]
            else:
                elements = [
                    self.names,
                    self.subunits,
                    self.floors,
                    self.buildings,
                ]
            return ", ".join( filter(None, elements)) 
        else:
            return self.kwargs.get('line1')

    @property
    def line2(self):
        if(self.valid):
            if self.names and self.deliveries:
                try:
                    assert not any([self.thoroughfares]), "can't have delivery and thoroughfare"
                except AssertionError as e:
                    print "failed assertion: ", e
                    pprint (self)


                elements = [self.deliveries]
            else:
                elements = [
                    self.thoroughfares
                ]
            return ", ".join( filter(None, elements)) 
        else:
            return self.kwargs.get('line2')

    @property
    def line3(self):
        if(self.valid):
            state = self.properties.get('state')
            country = self.properties.get('country')
            city = self.properties.get('city')
            postcode = self.properties.get('postcode')
        else:
            state = self.kwargs.get('state')
            country = self.kwargs.get('country')
            city = self.kwargs.get('city')
            postcode = self.kwargs.get('postcode')
        return ", ".join( filter(None, [city, state, postcode, country]))

    @staticmethod
    def determineSchema(**kwargs):
        fields = filter(None, map(lambda key: kwargs.get(key, ''), ['line1', 'line2', 'city']))
        if(fields):
            actLike = all(map(SanitationUtils.stringCapitalized, fields))
            if(actLike):
                return 'act'
            else:
                return 'unknown'
        return None

    def __str__(self, out_schema = None):
        prefix = ""
        if DEBUG_ADDRESS:
            prefix = "VALID: " if self.valid else "INVALID: "
        return  prefix + "\n".join(filter(None,[
            self.line1,
            self.line2,
            self.line3
        ]))  

        #TODO: THIS



class ImportUser(ImportFlat):

    email = descriptorUtils.safeKeyProperty('E-mail')
    MYOBID = descriptorUtils.safeKeyProperty('MYOB Card ID')
    username = descriptorUtils.safeKeyProperty('Wordpress Username')
    role = descriptorUtils.safeKeyProperty('Role')
    contact_schema = descriptorUtils.safeKeyProperty('contact_schema')
    billing_address = descriptorUtils.safeKeyProperty('Address')
    shipping_address = descriptorUtils.safeKeyProperty('Home Address')

    def __init__(self, data, rowcount=None, row=None, **kwargs):
        super(ImportUser, self).__init__(data, rowcount, row)
        for key in ['E-mail', 'MYOB Card ID', 'Wordpress Username', 'Role', 'contact_schema']:
            val = kwargs.get(key, "")
            if(val):
                self[key] = val
            elif(not self.get(key)):
                self[key] = ""

        self['Address'] = ContactAddress(
            self.contact_schema,  
            line1       = self.get('Address 1', ''),
            line2       = self.get('Address 2', ''),
            city        = self.get('City', ''),
            postcode    = self.get('Postcode', ''),
            state       = self.get('State', ''),
            country     = self.get('Country'),
        )

        self['Home Address'] = ContactAddress(
            self.contact_schema,  
            line1       = self.get('Home Address 1', ''),
            line2       = self.get('Home Address 2', ''),
            city        = self.get('Home City', ''),
            postcode    = self.get('Home Postcode', ''),
            state       = self.get('Home State', ''),
            country     = self.get('Home Country', '')
        )

    def addressesActLike(self):
        actLike = True
        for address in filter(None, map(lambda key: self.get(key), ['Address', 'Home Address'])):
            if address.schema and address.schema != 'act':
                actLike = False
        return actLike

    def usernameActLike(self):
        return self.username == self.MYOBID

    def __repr__(self):
        return "<%s> %s | %s | %s | %s " % (self.index, self.email, self.MYOBID, self.role, self.username)

class UsrObjList(ObjList):
    def __init__(self):
        super(UsrObjList, self).__init__()
        self._objList_type = 'User'

    def getReportCols(self):
        usrData = ColData_User()
        report_cols = usrData.getReportCols()
        # for exclude_col in ['E-mail','MYOB Card ID','Wordpress Username','Role']:
        #     if exclude_col in report_cols:
        #         del report_cols[exclude_col]

        return report_cols



class CSVParse_User(CSVParse_Flat):

    objectContainer = ImportUser

    def __init__(self, cols=[], defaults = {}, contact_schema = None):
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
        super(CSVParse_User, self).__init__(cols, defaults)
        self.contact_schema = contact_schema
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

    def registerObject(self, objectData):
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

if __name__ == '__main__':
    inFolder = "../input/"
    # actPath = os.path.join(inFolder, 'partial act records.csv')
    actPath = os.path.join(inFolder, "200-act-records.csv")
    outFolder = "../output/"
    usrPath = os.path.join(outFolder, 'users.csv')

    usrData = ColData_User()

    # print "import cols", usrData.getImportCols()
    # print "defaults", usrData.getDefaults()

    usrParser = CSVParse_User(
        cols = usrData.getImportCols(),
        defaults = usrData.getDefaults()
    )

    usrParser.analyseFile(actPath)

    usrList = UsrObjList()

    from copy import deepcopy

    for usr in usrParser.objects.values()[:3]:    
        usrList.addObject(usr)
        clone = deepcopy(usr)
        usr['Wordpress Username'] = 'jonno'
        usrList.addObject(clone)
        card_id = usr.MYOBID
        edit_date = usr.get('Edit Date')
        act_date = usr.get('Edited in Act')

    print usrList.tabulate()

    # usrCols = usrData.getUserCols()

    # exportItems(
    #     usrPath,
    #     usrData.getColNames(usrCols),
    #     usrParser.objects.values()
    # )

    # for role, usrs in usrParser.roles.items():
    #     for i, u in enumerate(range(0, len(usrs), usrs_per_file)):
    #         rolPath = os.path.join(outFolder, 'users_%s_%d.csv'%(role,i))

    #         exportItems(
    #             rolPath,
    #             usrData.getColNames(usrCols),
    #             usrs.values()[u:u+usrs_per_file]
    #         )
        
