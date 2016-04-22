from utils import  SanitationUtils, AddressUtils, NameUtils, listUtils # descriptorUtils, listUtils,
from pprint import pprint
from collections import OrderedDict
from tabulate import tabulate

DEBUG_ADDRESS = False
DEBUG_ADDRESS = True
STRICT_ADDRESS = True

DEBUG_NAME = False
DEBUG_NAME = True
STRICT_NAME = True

class ContactObject(object):
    equality_keys = []
    similarity_keys = []
    key_mappings = {}
    ContactObjectType = "CONTACTOBJ"

    def __init__(self, schema=None, **kwargs):
        self.valid = True
        self.empty = True
        self.reason = ""
        self.properties = OrderedDict()
        self.kwargs = kwargs
        self.problematic = False
        self.properties['ignores'] = []
        self.properties['unknowns'] = []
        self.properties['names'] = []
        self.properties['careof_names'] = []
        self.properties['organization_names'] = []

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

    def getPrefix(self):
        if self.empty:
            prefix = "EMPTY"
        elif self.valid:
            prefix = "VALID"  
        else:
            prefix = "INVALID"
            # if self.reason:
            #     prefix += "(" + self.reason + ")"
        prefix += ": "
        return prefix


    # def get(self, key, default = None):
    #     for attr, keys in self.key_mappings.items():
    #         if key in keys:
    #             return getattr(self, attr)
    #     return super(ContactObject, self).get(key, default)

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

    def tabulate(self, tablefmt = None):
        if not tablefmt:
            tablefmt = 'simple'
        if tablefmt == 'html':
            sanitizer = SanitationUtils.sanitizeForXml
            out_schema = None
        else:
            sanitizer = SanitationUtils.sanitizeForTable
            out_schema = 'flat'
        if self.empty:
            reason = self.ContactObjectType + " EMPTY"
        else:
            reason = self.reason

        printable_kwargs = {}
        if self.kwargs:
            for key, arg in self.kwargs.items():
                if arg: printable_kwargs[key] = [sanitizer(arg)]

        table = OrderedDict()

        table[self.ContactObjectType] = [sanitizer(self.__unicode__(out_schema=out_schema) )]

        if reason:
            table['REASON'] = [sanitizer(reason)]

        if printable_kwargs:
            for key, arg in printable_kwargs.items():
                table['KEY:'+key] = arg

        return tabulate(
            table,
            tablefmt = tablefmt,
            headers= 'keys'
        )


    def __bool__(self):
        return not self.empty
    __nonzero__=__bool__

class ContactAddress(ContactObject):
    ContactObjectType = "ADDRESS"
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
        self.properties['numbers'] = []

        if not any( filter(None, map(
            lambda key: kwargs.get(key, ''), 
            ['line1', 'line2', 'city', 'postcode', 'state']
        ))): 
            self.schema = None
        else:
            self.empty = False
            if DEBUG_ADDRESS: pprint(kwargs)
            if not schema: self.schema = self.__class__.determineSchema(**kwargs)

            lines = filter(None, map(lambda key: kwargs.get(key, ''), ['line1', 'line2']))

            wordsToRemove = []

            if kwargs.get('country', ''):
                countrySanitized = AddressUtils.sanitizeState(kwargs['country'])
                countryIdentified = AddressUtils.identifyCountry(countrySanitized)
                # if DEBUG_ADDRESS: print "countrySanitized", countrySanitized, "countryIdentified", countryIdentified
                if countrySanitized != countryIdentified:
                    self.properties['country'] = countryIdentified
                else:
                    self.properties['country'] = countrySanitized
                # wordsToRemove.append(countrySanitized)

            if kwargs.get('state', ''):
                stateSanitized = AddressUtils.sanitizeState(kwargs['state'])
                wordsToRemove.append(stateSanitized)
                stateIdentified = AddressUtils.identifyState(stateSanitized)
                if stateIdentified != stateSanitized:
                    wordsToRemove.append(stateIdentified)
                    self.properties['state'] = stateIdentified
                else:
                    self.properties['state'] = stateSanitized


            if kwargs.get('city', ''):
                citySanitized = AddressUtils.sanitizeState(kwargs['city'])
                self.properties['city'] = citySanitized
                # wordsToRemove.append(citySanitized)

            if kwargs.get('postcode'):
                self.properties['postcode'] = kwargs.get('postcode')
                if SanitationUtils.stringContainsNoNumbers( kwargs.get('postcode')) :
                    self.valid = False
                    self.reason = "Invalid postcode"

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
                    self.properties['names'] += [numberlessLines]
                else:
                    self.valid = False
                    self.reason = "More than one numberless line: " + repr(numberlessLines)

            # Extract subunit numbers and floor level


            for i, line in enumerate(numberLines):
                if DEBUG_ADDRESS: SanitationUtils.safePrint( "ANALYSING LINE %d: %s" % (i, repr(line)) ) 
                tokens = AddressUtils.tokenizeAddress(line)
                if DEBUG_ADDRESS: SanitationUtils.safePrint( u"TOKENS: %s" % repr(tokens) )
                congruentNames = []
                lastNameToken = -1
                for j, token in enumerate(tokens):
                    if DEBUG_ADDRESS: SanitationUtils.safePrint( u"-> token[%d]: %s" % (j, token) )
                    delivery = AddressUtils.getDelivery(token)
                    if(delivery):
                        # delivery_type, delivery_name = delivery
                        self.properties['deliveries'] += [delivery]
                        if DEBUG_ADDRESS:
                            SanitationUtils.safePrint( "FOUND DELIVERY: " + SanitationUtils.coerceUnicode(delivery))
                        continue
                    subunit = AddressUtils.getSubunit(token)
                    if(subunit):
                        if DEBUG_ADDRESS:
                            SanitationUtils.safePrint( "FOUND SUBUNIT: " + SanitationUtils.coerceUnicode(subunit))
                        subunit_type, subunit_number = subunit
                        if subunit_type in ['SHOP', 'SE', 'KSK', 'SHRM']:
                            self.isShop = True
                        self.properties['subunits'] += [subunit]
                        continue
                    floor = AddressUtils.getFloor(token)
                    if(floor):
                        if DEBUG_ADDRESS:
                            SanitationUtils.safePrint( "FOUND FLOOR: " + SanitationUtils.coerceUnicode(floor))
                        # floor_type, floor_number = floor
                        self.properties['floors'] += [floor]
                        continue
                    thoroughfare = AddressUtils.getThoroughfare(token)
                    if(thoroughfare):
                        if DEBUG_ADDRESS:
                            SanitationUtils.safePrint( "FOUND THOROUGHFARE: " + SanitationUtils.coerceUnicode(thoroughfare))
                            # thoroughfare_number, thoroughfare_name, thoroughfare_type, thoroughfare_suffix = thoroughfare
                        self.properties['thoroughfares'] += [thoroughfare]
                        continue
                    building = AddressUtils.getBuilding(token)
                    if(building):
                        if DEBUG_ADDRESS:
                            SanitationUtils.safePrint( "FOUND BUILDING: " + SanitationUtils.coerceUnicode(building))
                        # building_name, building_type = building
                        self.properties['buildings'] += [building]
                        continue
                    weak_thoroughfare = AddressUtils.getWeakThoroughfare(token)
                    if(weak_thoroughfare):
                        # weak_thoroughfare_name, weak_thoroughfare_type, weak_thoroughfare_suffix = weak_thoroughfare
                        self.properties['weak_thoroughfares'] += [weak_thoroughfare]
                        if DEBUG_ADDRESS:
                            SanitationUtils.safePrint( "FOUND WEAK THOROUGHFARE: " + SanitationUtils.coerceUnicode(weak_thoroughfare))
                        continue
                    #ignore if unknown is city or state
                    if token in wordsToRemove:
                        self.properties['ignores'] += [token]
                        if DEBUG_ADDRESS: 
                            SanitationUtils.safePrint( "IGNORING WORD " + SanitationUtils.coerceUnicode(token))
                        continue

                    state = AddressUtils.getState(token)
                    if(state and not self.properties['state']):
                        #this might be the state but can't rule it out being something else
                        self.properties['possible_states'] = list( 
                            set( self.properties['possible_states'] ) + set([token])
                        )
                        if DEBUG_ADDRESS: 
                            SanitationUtils.safePrint( "IGNORING STATE " + SanitationUtils.coerceUnicode(state))
                        continue

                    careof = NameUtils.getCareOf(token)
                    if careof:
                        if DEBUG_NAME:
                            SanitationUtils.safePrint( "FOUND CAREOF: %s" % careof )
                        if careof not in self.properties['careof_names']:
                            self.properties['careof_names'] += [careof]
                        continue

                    organization = NameUtils.getOrganization(token)
                    if organization:
                        if DEBUG_NAME:
                            SanitationUtils.safePrint( "FOUND ORGANIZATION: %s" % organization )
                        if organization not in self.properties['organization_names']:
                            self.properties['organization_names'] += [organization]
                        continue

                    name = NameUtils.getSingleName(token)
                    if(name and not self.properties['names']):
                        if DEBUG_ADDRESS:
                            SanitationUtils.safePrint( "FOUND NAME " + SanitationUtils.coerceUnicode(name))
                        if j == lastNameToken + 1:
                            congruentNames += [name]
                            lastNameToken = j
                        else:
                            self.properties['names'] += [" ".join(congruentNames)]
                            congruentNames = [name]
                        continue

                    number = AddressUtils.getNumber(token)
                    #there can only be one number
                    if(number and not self.properties['numbers']):
                        self.properties['numbers'] += [number]
                        continue
                    self.properties['unknowns'] += [token]
                    self.valid = False
                    self.reason = "There are some unknown tokens: " + repr(self.properties['unknowns'])
                    # break
                if congruentNames:
                    self.properties['names'] += [" ".join(congruentNames)]
                if DEBUG_ADDRESS:
                    SanitationUtils.safePrint( "FINISHED CYCLE ")
                continue

            while self.properties['numbers'] :
                number  = self.properties['numbers'][-1]
                if self.properties['weak_thoroughfares'] and not self.properties['thoroughfares']:
                    weak_thoroughfare = self.properties['weak_thoroughfares'][0]
                    new_thoroughfare = ( number, weak_thoroughfare[0], weak_thoroughfare[1], weak_thoroughfare[2] )
                    self.properties['thoroughfares'] += [new_thoroughfare]
                elif not self.properties['subunits']:
                    self.properties['subunits'] += [(None, self.properties['numbers'][0])]
                    self.properties['numbers'] = self.properties['numbers'][1:]
                else:
                    self.valid = False
                    self.reason = "stray number doesn't match with thoroughfare or subunit: " + repr(self.properties['numbers'])
                    break
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
        if self.properties['names'] or self.properties['careof_names'] or self.properties['organization_names']:
            return ", ".join(
                [" ".join(filter(None, names)) for names in \
                    self.properties['names'] + self.properties['careof_names'] + self.properties['organization_names']]
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
                [" ".join(filter(None, thoroughfares)) for thoroughfares in \
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
        return self.properties.get('postcode') if self.valid else self.kwargs.get('postcode')

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
        prefix = self.getPrefix() if DEBUG_ADDRESS else ""
        delimeter = "\n"
        if out_schema == "flat":
            delimeter = ";"
        return SanitationUtils.coerceUnicode( prefix + delimeter.join(filter(None,[
            self.line1,
            self.line2,
            self.line3,
            (("|UNKN:" + " ".join(self.properties['unknowns'])) \
                if DEBUG_ADDRESS and self.properties['unknowns'] else "")
        ])) ) 

    def __str__(self, out_schema=None):
        return SanitationUtils.coerceBytes(self.__unicode__(out_schema)) 

def testContactAddress():
    
    # DOESN'T GET

    print ContactAddress(
        **{'city': u'TEA TREE GULLY',
         'country': u'AUSTRALIA',
         'line1': u'SHOP 238/976',
         'line2': u'TEA TREE PLAZA',
         'postcode': u'5092',
         'state': u'SA'}
    ).__str__(out_schema="flat")

    print ContactAddress(
        line1 = "3/3 HOWARD AVA"
    ).__str__(out_schema="flat")

    print ContactAddress(
        line1 = "6/7 118 RODWAY ARCADE"
    ).__str__(out_schema="flat")

    print ContactAddress(
        city = 'GOLDEN BEACH',
        state = 'QLD',
        country = 'Australia',
        line1 = "C/- PAMPERED LADY - GOLDEN BEACH SHOPPING CENTRE",
        line2 = "LANDSBOROUGH PARADE",
        postcode = "4551"
    ).__str__(out_schema="flat")

    return
    #GETS

    print ContactAddress(
        city = 'CHATSWOOD',
        state = 'NSW',
        country = 'Australia',
        line1 = "SHOP 330 A VICTORIA AVE",
        postcode = "2067"
    ).__str__(out_schema="flat")

    print ContactAddress(
        city = 'Perth',
        state = 'WA',
        country = 'Australia',
        line1 = "SHOP 5/562 PENNANT HILLS RD",
    ).__str__(out_schema="flat")

    print ContactAddress(
        city = 'Perth',
        state = 'WA',
        country = 'Australia',
        line1 = "SHOP G159 BROADMEADOWS SHOP. CENTRE",
        line2 = "104 PEARCEDALE PARADE"
    ).__str__(out_schema="flat")

    print ContactAddress(
        city = 'Jandakot',
        state = 'WA',
        country = 'Australia',
        line1 = "Unit 1\\n",
        line2 = "41 Biscayne Way",
        postcode = "6164"
    ).__str__(out_schema="flat")

    print ContactAddress(
        line1 = "SH115A, FLOREAT FORUM"
    ).__str__(out_schema="flat")

    print ContactAddress(
        line1 = "A8/90 MOUNT STREET"
    ).__str__(out_schema="flat")

    print ContactAddress(
        line1 = "DANNY, SPG1 LG3 INGLE FARM SHOPPING CENTRE"
    ).__str__(out_schema="flat")

    print ContactAddress(
        line1 = "8/5-7 KILVINGTON DRIVE EAST"
    ).__str__(out_schema="flat")

    print ContactAddress(
         line1 = u'ANTONY WHITE, PO BOX 886',
         line2 = u'LEVEL1 468 KINGSFORD SMITH DRIVE'
    ).__str__(out_schema="flat")

    print ContactAddress(
        line1 = "THE VILLAGE SHOP 5"
    ).__str__(out_schema="flat")


    #Try see if similar works:

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
    ContactObjectType = "NAME"
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
        super(ContactName, self).__init__(schema, **kwargs)
        self.kwargs = kwargs
        # self.valid = False 
        self.problematic = False
        self.properties['titles'] = []
        self.properties['names'] = []
        self.properties['suffixes'] = []
        self.properties['positions'] = []
        self.properties['notes'] = []


        if not any( filter(None, map(
            lambda key: kwargs.get(key, ''), 
            ['first_name', 'family_name', 'contact', 'company']
        ))): 
            self.schema = None
        else:
            self.empty = False
            wordsToRemove = []

            if kwargs.get('country'):
                countrySanitized = AddressUtils.sanitizeState(kwargs['country'])
                countryIdentified = AddressUtils.identifyCountry(countrySanitized)
                # if DEBUG_ADDRESS: print "countrySanitized", countrySanitized, "countryIdentified", countryIdentified
                if countrySanitized != countryIdentified:
                    self.properties['country'] = countryIdentified
                else:
                    self.properties['country'] = countrySanitized
                # wordsToRemove.append(countrySanitized)

            if kwargs.get('state'):
                stateSanitized = AddressUtils.sanitizeState(kwargs['state'])
                wordsToRemove.append(stateSanitized)
                stateIdentified = AddressUtils.identifyState(stateSanitized)
                if stateIdentified != stateSanitized:
                    wordsToRemove.append(stateIdentified)
                    self.properties['state'] = stateIdentified
                else:
                    self.properties['state'] = stateSanitized


            if kwargs.get('city'):
                citySanitized = AddressUtils.sanitizeState(kwargs['city'])
                self.properties['city'] = citySanitized

            if kwargs.get('company'):
                companySanitized = SanitationUtils.normalizeVal(kwargs['company'])
                wordsToRemove.append(companySanitized)

            full_name_contact = SanitationUtils.normalizeVal(kwargs.get('contact'))
            full_name_components = SanitationUtils.normalizeVal(' '.join(filter(None, map(
                lambda k: kwargs.get(k),
                ['name_prefix', 'first_name', 'middle_name', 'family_name', 'name_suffix']
            ))))

            full_names = listUtils.filterUniqueTrue([full_name_components, full_name_contact])

            if len(full_names) > 1:
                self.problematic = True
                if STRICT_NAME:
                    self.valid = False
                    self.reason = "THERE ARE MORE THAN 1 FULLNAMES: " + repr(full_names)
                    if DEBUG_NAME:
                        SanitationUtils.safePrint(self.reason)

            for i, full_name in enumerate(full_names):
                if DEBUG_NAME: SanitationUtils.safePrint( "ANALYSING NAME %d: %s" % (i, repr(full_name)) ) 
                tokens = NameUtils.tokenizeName(full_name)
                if DEBUG_NAME: SanitationUtils.safePrint( u"TOKENS: %s" % repr(tokens) )
                congruentNames = []
                lastNameToken = -1
                # SanitationUtils.safePrint(u"TOKENS {} FOR {} ARE {}".format(len(tokens), full_name, tokens))
                for j, token in enumerate(tokens):
                    # SanitationUtils.safePrint( "CONGRUENTNAMES: %s" % congruentNames )
                    if token in wordsToRemove:
                        self.properties['ignores'] += [token]
                        if DEBUG_NAME: 
                            SanitationUtils.safePrint( "IGNORING WORD: %s" % token )
                        continue

                    title = NameUtils.getTitle(token)
                    if title:
                        if DEBUG_NAME:
                            SanitationUtils.safePrint( "FOUND TITLE: %s" % title )
                        if title not in self.properties['titles']:
                            self.properties['titles'] += [title]
                        continue

                    position = NameUtils.getPosition(token)
                    if position:
                        if DEBUG_NAME:
                            SanitationUtils.safePrint( "FOUND POSITION: %s" % position )
                        if position not in self.properties['positions']:
                            self.properties['positions'] += [position]
                        continue

                    suffix = NameUtils.getNameSuffix(token)
                    if suffix:
                        if DEBUG_NAME:
                            SanitationUtils.safePrint( "FOUND NAME SUFFIX: %s" % suffix )
                        if suffix not in self.properties['suffixes']:
                            self.properties['suffixes'] += [suffix]
                        continue

                    note = NameUtils.getNote(token)
                    if note:
                        if DEBUG_NAME:
                            SanitationUtils.safePrint( "FOUND NOTE: %s" % note )
                        if note not in self.properties['notes']:
                            self.properties['notes'] += [note]
                        continue

                    careof = NameUtils.getCareOf(token)
                    if careof:
                        if DEBUG_NAME:
                            SanitationUtils.safePrint( "FOUND CAREOF: %s" % careof )
                        if careof not in self.properties['careof_names']:
                            self.properties['careof_names'] += [careof]
                        continue

                    organization = NameUtils.getOrganization(token)
                    if organization:
                        if DEBUG_NAME:
                            SanitationUtils.safePrint( "FOUND ORGANIZATION: %s" % organization )
                        if organization not in self.properties['organization_names']:
                            self.properties['organization_names'] += [organization]
                        continue

                    name = NameUtils.getSingleName(token)
                    if name:
                        if DEBUG_NAME:
                            SanitationUtils.safePrint( "FOUND NAME: %s" % name )
                        if j == lastNameToken + 1:
                            congruentNames += [name]
                        else:
                            names = " ".join(congruentNames)
                            if names and names not in self.properties['names']:
                                if DEBUG_NAME: SanitationUtils.safePrint( "ADDING NAME: %s" % names )
                                self.properties['names'] += [names]
                            congruentNames = [name]
                        lastNameToken = j
                        continue

                    self.properties['unknowns'] += [token]
                    self.valid = False
                    self.reason = "UNKNOWN TOKEN: " + repr(token)
                    if DEBUG_NAME:
                        SanitationUtils.safePrint(self.reason)

                names = " ".join(congruentNames)
                if names and names not in self.properties['names']:
                    if DEBUG_NAME:
                        SanitationUtils.safePrint( "ADDING NAME: %s" % names )
                    self.properties['names'] += [names]

            if len(self.properties['names'] ) > 1:
                self.problematic = True
                if STRICT_NAME:
                    self.valid = False
                    self.reason = "THERE ARE MORE THAN 1 NAMES: " + repr(self.properties['names'])
                    if DEBUG_NAME:
                        SanitationUtils.safePrint(self.reason )
            elif len(self.properties['names']) == 0:
                self.empty = True
                # self.problematic = True
                # SanitationUtils.safePrint("THERE ARE NO NAMES: " + repr(kwargs))

            if len(self.properties['titles'] ) > 1:
                self.problematic = True
                if STRICT_NAME:
                    self.valid = False
                    self.reason = "THERE MULTIPLE TITLES: " + repr(self.properties['titles'])
                    if DEBUG_NAME:
                        SanitationUtils.safePrint(self.reason)

            if len(self.properties['notes'] ) > 1:
                self.problematic = True
                if STRICT_NAME:
                    self.valid = False
                    self.reason = "THERE MULTIPLE NOTES: " + repr(self.properties['notes'])           
                    if DEBUG_NAME:
                        SanitationUtils.safePrint(self.reason)

            if len(self.properties['positions'] ) > 1:
                self.problematic = True
                if STRICT_NAME:
                    self.valid = False
                    self.reason = "THERE MULTIPLE POSITIONS"                
                    if DEBUG_NAME:
                        SanitationUtils.safePrint(self.reason + ": " + repr(self.properties['positions']))


    @property
    def first_name(self):
        if self.valid:
            if len(self.properties.get('names', [])) > 0 :
                return self.properties.get('names')[0] 
            else:
                return ""
        else :
            self.kwargs.get('first_name') 

    @property
    def family_name(self):
        if self.valid:
            if len(self.properties.get('names', [])) > 1:
                return self.properties.get('names')[-1] 
            else:
                return ""
        else:
            return self.kwargs.get('family_name') 

    @property
    def middle_name(self):
        if self.valid:
            if len(self.properties.get('names', [])) > 2 :
                return " ".join(self.properties.get('names')[1:-1]) 
            else:
                return ""
        else :
            self.kwargs.get('middle_name') 

    @property
    def name_prefix(self):
        if self.valid:
            if len(self.properties.get('titles', [])) > 0:
                return " ".join(self.properties.get('titles')) 
            else:
                return ""
        else:
            return self.kwargs.get('name_prefix') 

    @property
    def name_suffix(self):
        if self.valid:
            if len(self.properties.get('positions', [])) > 0:
                return " ".join(self.properties.get('positions')) 
            else:
                return ""
        else:
            return self.kwargs.get('name_suffix') 

    def __unicode__(self, out_schema=None):
        prefix = self.getPrefix() if DEBUG_NAME else ""
        delimeter = " "
        return SanitationUtils.coerceUnicode( prefix + delimeter.join(filter(None,[
            (("PREF: "+ self.name_prefix) if DEBUG_NAME and self.name_prefix else self.name_prefix),
            (("FIRST: " + self.first_name) if DEBUG_NAME and self.first_name else self.first_name),
            (("MID: " + self.middle_name) if DEBUG_NAME and self.middle_name else self.middle_name),
            (("FAM: " + self.family_name) if DEBUG_NAME and self.family_name else self.family_name),
            ((", " + self.name_suffix) if self.name_suffix else ""),
            (("|UNKN:" + " ".join(self.properties['unknowns'])) \
                if DEBUG_NAME and self.properties['unknowns'] else "")
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

def testContactName():
    SanitationUtils.safePrint( 
        ContactName(
            city = 'Jandakot',
            state = 'WA',
            country = 'Australia',
            first_name = 'Dr. Neil',
            family_name = 'Cunliffe-Williams (ACCOUNTANT)',
            contact = "NEIL CUNLIFFE-WILLIAMS",
        ).tabulate(tablefmt="simple")
    )

if __name__ == '__main__':
    testContactAddress()
    testContactName()
