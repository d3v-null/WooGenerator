from utils import  SanitationUtils, AddressUtils # descriptorUtils, listUtils,
from pprint import pprint
from collections import OrderedDict

DEBUG_ADDRESS = False
# DEBUG_ADDRESS = True

DEBUG_NAME = True

class ContactObject(object):
    equality_keys = []
    similarity_keys = []
    key_mappings = {}

    def __init__(self, schema=None, **kwargs):
        self.kwargs = kwargs
        self.properties = OrderedDict()
        self.valid = True
        self.problematic = False
        self.empty = False

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            # for key in ['country', 'state', 'postcode', 'city', 'thoroughfares', 'deliveries', 'names', 'buildings', 'floors', 'subunits']:
            for key in self.equality_keys:
                if getattr(self, key) != getattr(other, key):
                    return False
            return True
        else:
            return False

    def __getitem__(self, key):
        for attr, keys in self.key_mappings.items():
            if key in keys:
                return getattr(self, attr)

    def normalizeVal(self, val):
        return SanitationUtils.normalizeVal(val)

    def similar(self, other):
        if(self.empty or other.empty):
            return True if self.empty and other.empty else False
        for key in self.similarity_keys:
            # print "-> LOOKING AT KEY", key
            if getattr(self, key) and getattr(other, key):
                # print "--> self", 
                if self.normalizeVal(getattr(self, key)) != self.normalizeVal(getattr(other, key)):
                    # print "->NOT THE SAME BECAUSE OF", key
                    return False
                else:
                    pass
                    # print "->KEY IS THE SAME", key
        return True
        # print "THEY ARE SIMILAR"
        #todo: this

    def __bool__(self):
        return not self.empty
    __nonzero__=__bool__

class ContactAddress(ContactObject):
    equality_keys = ['line1', 'line2', 'line3']
    similarity_keys = ['country', 'state', 'postcode', 'city', 'thoroughfares', 'deliveries', 'names', 'buildings', 'floors', 'subunits']
    key_mappings = {
        'country':['Country', 'Home Country'],
        'state':['State', 'Home State'],
        'postcode':['Postcode', 'Home Postcode'],
        'city':['City', 'Home City'],
        'line1':['Address 1', 'Home Address 1'],
        'line2':['Address 2', 'Home Address 2']
    }

    def __init__(self, schema=None, **kwargs):
        super(ContactAddress, self).__init__(schema, **kwargs)
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
            if not schema: self.schema = self.__class__.determineSchema(**kwargs)

            lines = filter(None, map(lambda key: kwargs.get(key, ''), ['line1', 'line2']))

            wordsToRemove = []

            if('country' in kwargs.keys() and kwargs.get('country', '')):
                countrySanitized = AddressUtils.sanitizeState(kwargs['country'])
                countryIdentified = AddressUtils.identifyCountry(countrySanitized)
                # if DEBUG_ADDRESS: print "countrySanitized", countrySanitized, "countryIdentified", countryIdentified
                if countrySanitized != countryIdentified:
                    self.properties['country'] = countryIdentified
                else:
                    self.properties['country'] = countrySanitized
                # wordsToRemove.append(countrySanitized)

            if('state' in kwargs.keys() and kwargs.get('state', '')):
                stateSanitized = AddressUtils.sanitizeState(kwargs['state'])
                wordsToRemove.append(stateSanitized)
                stateIdentified = AddressUtils.identifyState(stateSanitized)
                if stateIdentified != stateSanitized:
                    wordsToRemove.append(stateIdentified)
                    self.properties['state'] = stateIdentified
                else:
                    self.properties['state'] = stateSanitized


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
                    if DEBUG_ADDRESS: print SanitationUtils.coerceBytes( u"-> token[%d]: %s" % (j, token) )
                    delivery = AddressUtils.getDelivery(token)
                    if(delivery):
                        # delivery_type, delivery_name = delivery
                        self.properties['deliveries'] += [delivery]
                        continue
                    subunit = AddressUtils.getSubunit(token)
                    if(subunit):
                        if DEBUG_ADDRESS:
                            print "FOUND SUBUNIT: ", subunit
                        subunit_type, subunit_number = subunit
                        if subunit_type in ['SHOP', 'SE', 'KSK', 'SHRM']:
                            self.isShop = True
                        self.properties['subunits'] += [subunit]
                        continue
                    floor = AddressUtils.getFloor(token)
                    if(floor):
                        if DEBUG_ADDRESS:
                            print "FOUND FLOOR: ", floor
                        # floor_type, floor_number = floor
                        self.properties['floors'] += [floor]
                        continue
                    thoroughfare = AddressUtils.getThoroughfare(token)
                    if(thoroughfare):
                        if DEBUG_ADDRESS:
                            print "FOUND THOROUGHFARE: ", thoroughfare
                            # thoroughfare_number, thoroughfare_name, thoroughfare_type, thoroughfare_suffix = thoroughfare
                        self.properties['thoroughfares'] += [thoroughfare]
                        continue
                    building = AddressUtils.getBuilding(token)
                    if(building):
                        if DEBUG_ADDRESS:
                            print "FOUND BUILDING: ", building
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

            # if(schema in ['act']):
            #     pass
            #     #TODO: THIS
            # else:
            #     pass
            #     #TODO: THIS
    
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
    def country(self):
        return self.properties.get('country') if self.valid else self.kwargs.get('country')

    @property
    def postcode(self):
        return self.properties.get('postcode') if self.valid else self.kwargs.get('country')

    @property
    def city(self):
        return self.properties.get('city') if self.valid else self.kwargs.get('city')
    

    @property
    def line1(self):
        if(self.valid):
            elements = [
                self.names,
                self.deliveries,
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
            elements = [
                self.thoroughfares
            ]
            return ", ".join( filter(None, elements)) 
        else:
            return self.kwargs.get('line2')

    @property
    def line3(self):
        return ", ".join( filter(None, [self.city, self.state, self.postcode, self.country]))

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


    def normalizeVal(self, val):
        return AddressUtils.sanitizeState(val)

    def __unicode__(self, out_schema = None):
        prefix = ""
        if DEBUG_ADDRESS:
            prefix = "VALID: " if self.valid else "INVALID: "
        delimeter = "\n"
        if out_schema == "flat":
            delimeter = ";"
        return SanitationUtils.coerceUnicode( prefix + delimeter.join(filter(None,[
            self.line1,
            self.line2,
            self.line3
        ])) ) 

    def __str__(self, out_schema=None):
        return SanitationUtils.coerceBytes(self.__unicode__(out_schema)) 



def testContactAddress():
    #GETS
    print ContactAddress(
        city = 'Jandakot',
        state = 'WA',
        country = 'Australia',
        line1 = "Unit 1\\n",
        line2 = "41 Biscayne Way",
        postcode = "6164"
    ).__str__(out_schema="flat")

    # print ContactAddress(
    #     city = 'Perth',
    #     state = 'WA',
    #     country = 'Australia',
    #     line1 = "SHOP G159 BROADMEADOWS SHOP. CENTRE",
    #     line2 = "104 PEARCEDALE PARADE"
    # ).__str__(out_schema="flat")

    # print ContactAddress(
    #     city = 'Perth',
    #     state = 'WA',
    #     country = 'Australia',
    #     line1 = "SHOP 5/562 PENNANT HILLS RD",
    # ).__str__(out_schema="flat")

    # print ContactAddress(
    #     line1 = "SH115A, FLOREAT FORUM"
    # ).__str__(out_schema="flat")

    # print ContactAddress(
    #     line1 = "A8/90 MOUNT STREET"
    # ).__str__(out_schema="flat")

    # print ContactAddress(
    #     line1 = "DANNY, SPG1 LG3 INGLE FARM SHOPPING CENTRE"
    # ).__str__(out_schema="flat")

    # print ContactAddress(
    #     line1 = "8/5-7 KILVINGTON DRIVE EAST"
    # ).__str__(out_schema="flat")

    # print ContactAddress(
    #      line1 = u'ANTONY WHITE, PO BOX 886',
    #      line2 = u'LEVEL1 468 KINGSFORD SMITH DRIVE'
    # ).__str__(out_schema="flat")
    
    # # DOESN'T GET

    # print ContactAddress(
    #     line1 = "THE VILLAGE SHOP 5"
    # ).__str__(out_schema="flat")

    # print ContactAddress(
    #     line1 = "3/3 HOWARD AVA"
    # ).__str__(out_schema="flat")

    # print ContactAddress(
    #     line1 = "6/7 118 RODWAY ARCADE"
    # ).__str__(out_schema="flat")


    # #Try see if similar works:

    # M = ContactAddress(
    #     line1 = "20 BOWERBIRD ST",
    #     city = "DEEBING HEIGHTS",
    #     state = "QLD",
    #     postcode = "4306", 
    #     country = "AU"
    # )
    # N = ContactAddress(
    #     line1 = "MAX POWER",
    #     line2 = "20 BOWERBIRD STREET",
    #     city = "DEEBING HEIGHTS",
    #     state = "QLD",
    #     postcode = "4306"
    # )
    # O = ContactAddress(
    #     line2 = "20 BOWERBIRD STREET",
    #     city = "DEEBING HEIGHTS",
    #     state = "QLD",
    #     postcode = "4306",
    #     country = "AU"
    # )

    # S = ContactAddress(
    #     line1 = "1 HARRIET CT",
    #     city = "SPRINGFIELD LAKES",
    #     state = "QLD", 
    #     postcode = "4300"
    # )
    # print M.similar(S)
    # print M.similar(N)
    # print M == O
    
class ContactName(ContactObject):
    equality_keys = ['first_name', 'middle_name']
    similarity_keys = ['first_name', 'middle_name', 'family_name', 'contact', 'company']
    key_mappings = {
        'first_name':['First Name'],
        'family_name':['Surname'],
        'middle_name':['Middle Name'],
        'name_prefix':['Name Prefix'],
        'name_suffix':['name_suffix']
    }

    def __init__(self, schema=None, **kwargs):
        self.kwargs = kwargs
        self.properties = OrderedDict()
        # self.valid = True
        self.valid = False #uncomment this once class is complete
        self.problematic = False
        self.empty = False

        if not any( filter(None, map(
            lambda key: kwargs.get(key, ''), 
            ['first_name', 'family_name', 'contact', 'company']
        ))): 
            self.empty = True
            self.valid = False 
        else:
            wordsToRemove = []

            if('country' in kwargs.keys() and kwargs.get('country', '')):
                countrySanitized = AddressUtils.sanitizeState(kwargs['country'])
                countryIdentified = AddressUtils.identifyCountry(countrySanitized)
                # if DEBUG_ADDRESS: print "countrySanitized", countrySanitized, "countryIdentified", countryIdentified
                if countrySanitized != countryIdentified:
                    self.properties['country'] = countryIdentified
                else:
                    self.properties['country'] = countrySanitized
                # wordsToRemove.append(countrySanitized)

            if('state' in kwargs.keys() and kwargs.get('state', '')):
                stateSanitized = AddressUtils.sanitizeState(kwargs['state'])
                wordsToRemove.append(stateSanitized)
                stateIdentified = AddressUtils.identifyState(stateSanitized)
                if stateIdentified != stateSanitized:
                    wordsToRemove.append(stateIdentified)
                    self.properties['state'] = stateIdentified
                else:
                    self.properties['state'] = stateSanitized


            if 'city' in kwargs.keys() and kwargs.get('city', ''):
                citySanitized = AddressUtils.sanitizeState(kwargs['city'])
                self.properties['city'] = citySanitized

    @property
    def first_name(self):
        return self.properties.get('first_name') if self.valid else self.kwargs.get('first_name') 

    @property
    def family_name(self):
        return self.properties.get('family_name') if self.valid else self.kwargs.get('family_name') 

    @property
    def middle_name(self):
        return self.properties.get('middle_name') if self.valid else self.kwargs.get('middle_name') 

    @property
    def name_prefix(self):
        return self.properties.get('name_prefix') if self.valid else self.kwargs.get('name_prefix') 

    @property
    def name_suffix(self):
        return self.properties.get('name_suffix') if self.valid else self.kwargs.get('name_suffix') 


    def __unicode__(self, out_schema=None):
        prefix = ""
        if DEBUG_NAME:
            prefix = "VALID: " if self.valid else "INVALID: "
        delimeter = " "
        return SanitationUtils.coerceUnicode( prefix + delimeter.join(filter(None,[
            self.name_prefix,
            self.first_name,
            self.middle_name,
            self.family_name,
            self.name_suffix
        ])))

    def __str__(self, out_schema = None):
        return SanitationUtils.coerceBytes(self.__unicode__(out_schema)) 

        # first_name  = self.get('First Name', ''),
        # middle_name = self.get('Middle Name', ''),
        # family_name = self.get('Surname', ''),
        # name_prefix = self.get('Name Prefix', ''),
        # name_suffix = self.get('Name Suffix', ''),
        # contact     = self.get('Contact', ''),
        # company     = self.get('Company', ''),
        # city        = self.get('City', ''),
        # country     = self.get('Country', ''),
        # state       = self.get('State', '')

if __name__ == '__main__':
    testContactAddress()
    # testContactName()

