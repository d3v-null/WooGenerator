from utils import  SanitationUtils, AddressUtils, NameUtils, listUtils # descriptorUtils, listUtils,
from pprint import pprint
from collections import OrderedDict
from tabulate import tabulate

DEBUG_ADDRESS = False
# DEBUG_ADDRESS = True
STRICT_ADDRESS = True

DEBUG_NAME = False
# DEBUG_NAME = True
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
        self.wordsToRemove = []

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


    @property
    def careof_names(self):
        if self.properties['careof_names']:
            return ", ".join(
                [" ".join(filter(None,careof_name)) for careof_name in self.properties['careof_names']]
            )

    @property
    def organization_names(self):
        if self.properties['careof_names']:
            return ", ".join(
                [" ".join(filter(None,organization_name)) for organization_name in self.properties['organization_names']]
            )
    
    @property
    def names(self):
        if self.properties['names'] or self.properties['careof_names'] or self.properties['organization_names']:
            out = ", ".join(filter(None,
                [
                    " ".join(filter(None, names)) for names in \
                        [
                            self.properties['names'],
                            [self.careof_names] ,
                            [self.organization_names]
                        ]
                ]
            ))
            # SanitationUtils.safePrint("NAMES", out)
            return out

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

    def invalidate(self, reason = None):
        self.valid = False
        self.reason = reason
        if DEBUG_ADDRESS: 
            SanitationUtils.safePrint( "INVALID: ", reason )

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
        self.properties['coerced_subunits'] = []
        self.properties['incomplete_subunits'] = []
        self.properties['isShop'] = False
        self.properties['deliveries'] = []
        self.properties['floors'] = []
        self.properties['thoroughfares'] = []
        self.properties['buildings'] = []
        self.properties['weak_thoroughfares'] = []
        self.properties['numbers'] = []
        self.format = 'numbered_lines'

        if not any( filter(None, map(
            lambda key: kwargs.get(key, ''), 
            ['line1', 'line2', 'city', 'postcode', 'state']
        ))): 
            self.schema = None
        else:
            self.empty = False
            if DEBUG_ADDRESS: pprint(kwargs)
            if not schema: self.schema = self.__class__.determineSchema(**kwargs)

            lines = listUtils.filterUniqueTrue(map(lambda key: kwargs.get(key, ''), ['line1', 'line2']))

            if kwargs.get('country', ''):
                countrySanitized = AddressUtils.sanitizeState(kwargs['country'])
                countryIdentified = AddressUtils.identifyCountry(countrySanitized)
                # if DEBUG_ADDRESS: print "countrySanitized", countrySanitized, "countryIdentified", countryIdentified
                if countrySanitized != countryIdentified:
                    self.properties['country'] = countryIdentified
                else:
                    self.properties['country'] = countrySanitized
                # self.wordsToRemove.append(countrySanitized)

            if kwargs.get('state', ''):
                stateSanitized = AddressUtils.sanitizeState(kwargs['state'])
                self.wordsToRemove.append(stateSanitized)
                stateIdentified = AddressUtils.identifyState(stateSanitized)
                if stateIdentified != stateSanitized:
                    self.wordsToRemove.append(stateIdentified)
                    self.properties['state'] = stateIdentified
                else:
                    self.properties['state'] = stateSanitized


            if kwargs.get('city', ''):
                citySanitized = AddressUtils.sanitizeState(kwargs['city'])
                self.properties['city'] = citySanitized
                # self.wordsToRemove.append(citySanitized)

            if kwargs.get('postcode'):
                self.properties['postcode'] = kwargs.get('postcode')
                if SanitationUtils.stringContainsNoNumbers( kwargs.get('postcode')) :
                    self.invalidate("Postcode has no numbers: %s" % repr(kwargs.get('postcode')) )

            # numberLines = filter(
            #     SanitationUtils.stringContainsNumbers, 
            #     lines
            # )
            # numberlessLines = filter(
            #     SanitationUtils.stringContainsNoNumbers,
            #     lines
            # )
            # if(numberlessLines):
            #     self.properties['names'] += numberlessLines
            #     if len(numberlessLines) > 1:
            #         self.format = 'numberless_lines'

            # Extract subunit numbers and floor level

            for i, line in enumerate(lines):
                if DEBUG_ADDRESS: SanitationUtils.safePrint( "ANALYSING LINE %d: %s" % (i, repr(line)) ) 
                tokens = AddressUtils.tokenizeAddress(line)
                if DEBUG_ADDRESS: SanitationUtils.safePrint( u"TOKENS: %s" % repr(tokens) )
                congruentNames = []
                lastNameToken = -1
                congruentNumbers = []
                lastNumberToken = -1
                for j, token in enumerate(tokens):
                    if congruentNames and j != lastNameToken + 1:
                        self.addName(" ".join(congruentNames))
                        congruentNames = []
                    if congruentNumbers and j != lastNumberToken + 1:
                        self.addNumber(" ".join(congruentNumbers))
                        congruentNumbers = []
                    if DEBUG_ADDRESS: SanitationUtils.safePrint( u"-> token[%d]: %s" % (j, token) )
                    delivery = AddressUtils.getDelivery(token)
                    if(delivery):
                        if DEBUG_ADDRESS: SanitationUtils.safePrint( "FOUND DELIVERY: ", delivery)
                        self.properties['deliveries'] += [delivery]
                        continue
                    subunit = AddressUtils.getSubunit(token)
                    if(subunit):
                        self.addSubunit(subunit)
                        continue
                    floor = AddressUtils.getFloor(token)
                    if(floor):
                        if DEBUG_ADDRESS: SanitationUtils.safePrint( "FOUND FLOOR: ", floor)
                        self.properties['floors'] += [floor]
                        continue
                    thoroughfare = AddressUtils.getThoroughfare(token)
                    if(thoroughfare):
                        self.addThoroughfare(thoroughfare)
                        continue
                    weak_thoroughfare = AddressUtils.getWeakThoroughfare(token)
                    building = AddressUtils.getBuilding(token)
                    if(building and weak_thoroughfare):
                        #TODO: Which one goes to which?
                        # if DEBUG_ADDRESS: SanitationUtils.safePrint( "BUILDING AND WEAK THOROUGHFARE" )
                        if not (self.properties['thoroughfares'] + self.properties['weak_thoroughfares']):# and (self.properties['numbers'] or self.properties['coerced_subunits']):
                            building = None
                        elif not (self.properties['buildings']): # and (self.properties['subunits'] or self.properties['floors'] or self.properties['deliveries']):
                            weak_thoroughfare = None
                        else:
                            self.invalidate("Ambiguous thoroughfare or building: %s" % repr(token))
                    if(weak_thoroughfare and not self.properties['weak_thoroughfares']):
                        # weak_thoroughfare_name, weak_thoroughfare_type, weak_thoroughfare_suffix = weak_thoroughfare
                        if DEBUG_ADDRESS: SanitationUtils.safePrint( "FOUND WEAK THOROUGHFARE: ", weak_thoroughfare)

                        if congruentNumbers or self.properties['numbers'] or self.properties['coerced_subunits']:
                            if congruentNumbers:
                                number = AddressUtils.getNumber(" ".join(congruentNumbers))
                                congruentNumbers = []
                            elif self.properties['numbers']:
                                number = self.properties['numbers'].pop()
                            elif self.properties['coerced_subunits']:
                                subunit_type, number = self.properties['coerced_subunits'].pop()
                            # token = " ".join(names)
                            self.coerceThoroughfare(number, weak_thoroughfare)
                            continue
                        self.properties['weak_thoroughfares'] += [weak_thoroughfare]
                        continue
                    if(building and self.properties['buildings']):
                        self.addBuilding(building)
                        continue
                    #ignore if unknown is city or state
                    if token in self.wordsToRemove:
                        self.properties['ignores'] += [token]
                        if DEBUG_ADDRESS: SanitationUtils.safePrint( "IGNORING WORD ", token)
                        continue

                    state = AddressUtils.getState(token)
                    if(state and not self.properties['state']):
                        #this might be the state but can't rule it out being something else
                        self.properties['possible_states'] = list( 
                            set( self.properties['possible_states'] ) + set([token])
                        )
                        if DEBUG_ADDRESS: SanitationUtils.safePrint( "IGNORING STATE ", state)
                        continue

                    careof = NameUtils.getCareOf(token)
                    if careof:
                        if DEBUG_ADDRESS: SanitationUtils.safePrint( "FOUND CAREOF ",  careof ) 
                        if careof not in self.properties['careof_names']:
                            self.properties['careof_names'] += [careof]
                        continue

                    organization = NameUtils.getOrganization(token)
                    if organization:
                        if DEBUG_ADDRESS:
                            SanitationUtils.safePrint( "FOUND ORGANIZATION: ",  organization ) 
                        if organization not in self.properties['organization_names']:
                            self.properties['organization_names'] += [organization]
                        continue

                    name = NameUtils.getMultiName(token)
                    if name:
                        if DEBUG_ADDRESS:
                            SanitationUtils.safePrint( "FOUND NAME:", name)
                        # if j != lastNameToken + 1:
                        #     if DEBUG_ADDRESS: SanitationUtils.safePrint( "NOT CONGRUENT:", "J:", j, "lastNameToken:", lastNameToken, congruentNames)
                        #     if congruentNames:
                        #         self.addName(" ".join(congruentNames))
                        #         congruentNames = []
                        # else:
                            # pass
                            # if DEBUG_ADDRESS: SanitationUtils.safePrint( "CONGRUENT:", "J:", j, "lastNameToken:", lastNameToken, congruentNames)
                        congruentNames += [name]
                        lastNameToken = j
                        continue

                    number = AddressUtils.getNumber(token)
                    if(number):
                        if DEBUG_ADDRESS:
                            SanitationUtils.safePrint( "FOUND NUMBER:", number)
                        congruentNumbers += [number]
                        lastNumberToken = j
                        continue

                    if congruentNumbers and token == "/":
                        if DEBUG_ADDRESS:
                            SanitationUtils.safePrint( "FOUND NUMBER DELIM:", token)
                        congruentNumbers += [token]
                        lastNumberToken = j

                    if SanitationUtils.stringContainsDisallowedPunctuation(token) and len(token) == 1:
                        continue

                    if DEBUG_ADDRESS: SanitationUtils.safePrint( "UNKNOWN TOKEN", token)
                    self.properties['unknowns'] += [token]
                    self.invalidate("There are some unknown tokens: " + repr(self.properties['unknowns']))
                    # break
                if congruentNames:
                    if DEBUG_ADDRESS: SanitationUtils.safePrint( "CONGRUENT NAMES AT END OF CYCLE:", congruentNames)
                    self.addName(" ".join(congruentNames))
                if congruentNumbers:
                    if DEBUG_ADDRESS: SanitationUtils.safePrint( "CONGRUENT NUMBERS AT END OF CYCLE:", congruentNumbers)
                    self.addNumber(" ".join(congruentNumbers))
                # if DEBUG_ADDRESS: SanitationUtils.safePrint( "FINISHED CYCLE, NAMES: ", self.properties['names'])
                continue

            while self.properties['numbers'] :
                number = self.properties['numbers'].pop()
                if self.properties['weak_thoroughfares'] and not self.properties['thoroughfares']:
                    weak_thoroughfare = self.properties['weak_thoroughfares'].pop()
                    self.coerceThoroughfare(number, weak_thoroughfare)
                else:
                    self.properties['unknowns'] += [number]
                    self.invalidate("Too many numbers to match to thoroughfare or subunit: %s" % repr(number))
                    break
            #if any unknowns match number, then add them as a blank subunit

            # if(schema in ['act']):
            #     pass
            #     #TODO: THIS
            # else:
            #     pass
            #     #TODO: THIS
    

    # NO SUBUNUTS -> SUBUNIT W/ NO UNIT TYPE

    def addNumber(self, number):
        number = AddressUtils.getNumber(number)
        if not number:
            return
        if self.properties['incomplete_subunits']:
            subunit_type, subunit_number = self.properties['incomplete_subunits'].pop()
            try:
                assert int(AddressUtils.getSingleNumber(subunit_number)) > int(AddressUtils.getSingleNumber(number))
            except:
                self.invalidate("invalid number token: %s" % repr(number))
            subunit = (subunit_type, subunit_number + number)
            self.addSubunit( subunit )
        elif not self.properties['subunits']:
            self.coerceSubunit(number)
        else:
            self.properties['numbers'] += [number]
        #TODO: deal with numberSlash (e.g. 6/7)

    # NUMBERS -> WEAK THOROUGHFARE
    # SUBUNIT or FLOORS or DELIVERIES -> BUILDING 

    def addName(self, name):
        if not name:
            return
        # if DEBUG_ADDRESS: SanitationUtils.safePrint( "PROCESSING NAME", name)
        names = filter(None, NameUtils.getSingleNames(name))
        # if DEBUG_ADDRESS: SanitationUtils.safePrint( "SINGLE NAMES", names)
        if not (self.properties['thoroughfares'] + self.properties['weak_thoroughfares']) and (self.properties['numbers'] or self.properties['coerced_subunits']):
            if self.properties['numbers']:
                number = self.properties['numbers'].pop()
            elif self.properties['coerced_subunits']:
                subunit_type, number = self.properties['coerced_subunits'].pop()
            # token = " ".join(names)
            weak_thoroughfare = AddressUtils.getWeakThoroughfare(name)
            if not weak_thoroughfare:
                if len(names) > 1:
                    thoroughfare_name = " ".join(names[:-1])
                    thoroughfare_type = names[-1]
                else:
                    thoroughfare_name = " ".join(names)
                    thoroughfare_type = None
                weak_thoroughfare = (thoroughfare_name, thoroughfare_type, None)
            
            self.coerceThoroughfare(number, weak_thoroughfare)
        elif not (self.properties['buildings']) and (self.properties['subunits'] or self.properties['floors'] or self.properties['deliveries']):
            self.coerceBuilding(name)
        elif name in self.wordsToRemove:
            self.properties['ignores'] += [name]
        else:
            self.properties['names'] += [name]

    def addSubunit(self, subunit):
        if DEBUG_ADDRESS: SanitationUtils.safePrint( "ADDING SUBUNIT: ", subunit)
        subunit_type, subunit_number = subunit
        if subunit_type in ['SHOP', 'SUITE', 'KIOSK', 'SHRM', 'STORE']:
            self.isShop = True
        if subunit_number[-1] == '/':
            self.properties['incomplete_subunits'] += [subunit]
        else:
            self.properties['subunits'] += [subunit]

    def coerceSubunit(self, number):
        subunit = (None, number)
        if DEBUG_ADDRESS:  SanitationUtils.safePrint("COERCED SUBUNIT:", subunit)
        self.properties['coerced_subunits'] += [subunit]

    def addBuilding(self, building):
        if DEBUG_ADDRESS: SanitationUtils.safePrint( "ADDING BUILDING: ", building)
        self.properties['buildings'] += [building]

    def coerceBuilding(self, token):
        building = AddressUtils.getBuilding(token)
        if not building:
            building = (token, )
        if DEBUG_ADDRESS: SanitationUtils.safePrint("COERCED BUILDING", building)
        self.addBuilding(building)

    def addThoroughfare(self, thoroughfare):
        if DEBUG_ADDRESS: SanitationUtils.safePrint( "ADDING THOROUGHFARE", thoroughfare)
        self.properties['thoroughfares'] += [thoroughfare]
        # if legit thoroughfare is being added, remove weaklings
        while self.properties['weak_thoroughfares']:
            weak_thoroughfare = self.properties['weak_thoroughfares'].pop()
            token = " ".join(filter(None, weak_thoroughfare))
            self.coerceBuilding(token)

    def coerceThoroughfare( self, number, weak_thoroughfare):
        thoroughfare_name, thoroughfare_type, thoroughfare_suffix = weak_thoroughfare
        thoroughfare = ( number, thoroughfare_name, thoroughfare_type, thoroughfare_suffix )
        if DEBUG_NAME:
            SanitationUtils.safePrint( "COERCED THOROUGHFARE", SanitationUtils.coerceUnicode(thoroughfare))
        self.addThoroughfare(thoroughfare)


    @property
    def subunits(self):
        if(self.properties['subunits'] or self.properties['coerced_subunits']):
            return ", ".join(
                [" ".join(filter(None, subunit)) for subunit in (self.properties['subunits'] + self.properties['coerced_subunits'])]
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
        if(self.valid and self.format == 'numbered_lines'):
            elements = [
                self.names,
                self.deliveries,
                self.subunits,
                self.floors,
                self.buildings,
            ]
            out = ", ".join( filter(None, elements))
            # SanitationUtils.safePrint( "line1: ", out )
            return  out
        else:
            return self.kwargs.get('line1')

    @property
    def line2(self):
        if(self.valid and self.format == 'numbered_lines'):
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
        line1 = 'LEVEL 2, SHOP 202 / 8B "WAX IT"',
        line2 = "ROBINA TOWN CENTRE"
    ).__str__(out_schema="flat")

    print ContactAddress(
        line1 = "Midvale Shopping Centre, Shop 9, 1174 Geelong Road"
    ).__str__(out_schema="flat")

    print ContactAddress(
        line1 = "UNIT 6/7, 38 GRAND BOULEVARD"
    ).__str__(out_schema="flat")

    print ContactAddress(
        line1 = "SHOP 5&6, 39 MURRAY ST"
    ).__str__(out_schema="flat")

    print ContactAddress(
        line1 = "SHOP 10, 575/577",
        line2 = "CANNING HIGHWAY"
    ).__str__(out_schema="flat")


    print ContactAddress(
        line1 = "C/O COCO BEACH",
        line2 = "SHOP 3, 17/21 PROGRESS RD"
    ).__str__(out_schema="flat")



    return
    #GETS

    print ContactAddress(
        line1 = "6/208 MCDONALD STREET",
        line2 = "6/208 MCDONALD STREET",
    ).__str__(out_schema="flat")

    print ContactAddress(
        line1 = "UNIT 4 / 24"
    ).__str__(out_schema="flat")

    print ContactAddress(
        line1 = "6/7 118 RODWAY ARCADE"
    ).__str__(out_schema="flat")    

    print ContactAddress(
        line1 = "PO 5217 MACKAY MAIL CENTRE"
    ).__str__(out_schema="flat")

    print ContactAddress(
        line1 = "SHOP 9 PASPALIS CENTREPOINT",
        line2 = "SMITH STREET MALL"
    ).__str__(out_schema="flat")

    print ContactAddress(
        line1 = "73 NORTH PARK AVENUE",
        line2 = "ROCKVILLE CENTRE"
    ).__str__(out_schema="flat")

    print ContactAddress(
         line1 = u'ANTONY WHITE, PO BOX 886',
         line2 = u'LEVEL1 468 KINGSFORD SMITH DRIVE'
    ).__str__(out_schema="flat")

    print ContactAddress(
        line1 = "TAN IT UP",
        line2 = "73 WOODROSE ROAD"
    ).__str__(out_schema="flat")

    print ContactAddress(
        line1 = "DANNY, SPG1 LG3 INGLE FARM SHOPPING CENTRE"
    ).__str__(out_schema="flat")

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
        line1 = "G.P.O BOX 440",
        line2 = "CANBERRA CITY",
    ).__str__(out_schema="flat")

    print ContactAddress(
        line1 = "SHOP 29 STIRLING CENTRAL",
        line2 = "478 WANNEROO RD",
    ).__str__(out_schema="flat")

    print ContactAddress(
        city = 'ROSSMORE',
        state = 'NSW',
        line1 = "700 15TH AVE",
        line2 = "LANDSBOROUGH PARADE",
        postcode = "2557"
    ).__str__(out_schema="flat")

    print ContactAddress(
        line1 = "LEVEL A",
        line2 = "MYER CENTRE",
    ).__str__(out_schema="flat")

    print ContactAddress(
        city = 'GOLDEN BEACH',
        state = 'QLD',
        country = 'Australia',
        line1 = "C/- PAMPERED LADY - GOLDEN BEACH SHOPPING CENTRE",
        line2 = "LANDSBOROUGH PARADE",
        postcode = "4551"
    ).__str__(out_schema="flat")

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
        line1 = "8/5-7 KILVINGTON DRIVE EAST"
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

            if kwargs.get('country'):
                countrySanitized = AddressUtils.sanitizeState(kwargs['country'])
                countryIdentified = AddressUtils.identifyCountry(countrySanitized)
                # if DEBUG_ADDRESS: print "countrySanitized", countrySanitized, "countryIdentified", countryIdentified
                if countrySanitized != countryIdentified:
                    self.properties['country'] = countryIdentified
                else:
                    self.properties['country'] = countrySanitized
                # self.wordsToRemove.append(countrySanitized)

            if kwargs.get('state'):
                stateSanitized = AddressUtils.sanitizeState(kwargs['state'])
                self.wordsToRemove.append(stateSanitized)
                stateIdentified = AddressUtils.identifyState(stateSanitized)
                if stateIdentified != stateSanitized:
                    self.wordsToRemove.append(stateIdentified)
                    self.properties['state'] = stateIdentified
                else:
                    self.properties['state'] = stateSanitized


            if kwargs.get('city'):
                citySanitized = AddressUtils.sanitizeState(kwargs['city'])
                self.properties['city'] = citySanitized

            if kwargs.get('company'):
                companySanitized = SanitationUtils.normalizeVal(kwargs['company'])
                self.wordsToRemove.append(companySanitized)

            full_name_contact = SanitationUtils.normalizeVal(kwargs.get('contact'))
            full_name_components = SanitationUtils.normalizeVal(' '.join(filter(None, map(
                lambda k: kwargs.get(k),
                ['name_prefix', 'first_name', 'middle_name', 'family_name', 'name_suffix']
            ))))

            full_names = listUtils.filterUniqueTrue([full_name_components, full_name_contact])

            if len(full_names) > 1:
                self.problematic = True
                if STRICT_NAME:
                    self.invalidate("Unable to determine which name is correct: %s" % repr(full_names))

            for i, full_name in enumerate(full_names):
                if DEBUG_NAME: SanitationUtils.safePrint( "ANALYSING NAME %d: %s" % (i, repr(full_name)) ) 
                tokens = NameUtils.tokenizeName(full_name)
                if DEBUG_NAME: SanitationUtils.safePrint( "TOKENS:", repr(tokens) )
                congruentNames = []
                lastNameToken = -1
                # SanitationUtils.safePrint(u"TOKENS {} FOR {} ARE {}".format(len(tokens), full_name, tokens))
                for j, token in enumerate(tokens):
                    # SanitationUtils.safePrint( "CONGRUENTNAMES: ", congruentNames )
                    if token in self.wordsToRemove:
                        self.properties['ignores'] += [token]
                        if DEBUG_NAME: 
                            SanitationUtils.safePrint( "IGNORING WORD:", token )
                        continue

                    title = NameUtils.getTitle(token)
                    if title:
                        if DEBUG_NAME:
                            SanitationUtils.safePrint( "FOUND TITLE:", title )
                        if title not in self.properties['titles']:
                            self.properties['titles'] += [title]
                        continue

                    position = NameUtils.getPosition(token)
                    if position:
                        if DEBUG_NAME:
                            SanitationUtils.safePrint( "FOUND POSITION:", position )
                        if position not in self.properties['positions']:
                            self.properties['positions'] += [position]
                        continue

                    suffix = NameUtils.getNameSuffix(token)
                    if suffix:
                        if DEBUG_NAME:
                            SanitationUtils.safePrint( "FOUND NAME SUFFIX:", suffix )
                        if suffix not in self.properties['suffixes']:
                            self.properties['suffixes'] += [suffix]
                        continue

                    note = NameUtils.getNote(token)
                    if note:
                        if DEBUG_NAME:
                            SanitationUtils.safePrint( "FOUND NOTE:", note )
                        if note not in self.properties['notes']:
                            self.properties['notes'] += [note]
                        continue

                    careof = NameUtils.getCareOf(token)
                    if careof:
                        if DEBUG_NAME:
                            SanitationUtils.safePrint( "FOUND CAREOF:", careof )
                        if careof not in self.properties['careof_names']:
                            self.properties['careof_names'] += [careof]
                        continue

                    organization = NameUtils.getOrganization(token)
                    if organization:
                        if DEBUG_NAME:
                            SanitationUtils.safePrint( "FOUND ORGANIZATION:", organization )
                        if organization not in self.properties['organization_names']:
                            self.properties['organization_names'] += [organization]
                        continue

                    family_name = NameUtils.getFamilyName(token)
                    if family_name:
                        if DEBUG_NAME:
                            SanitationUtils.safePrint( "FOUND FAMILY NAME:", family_name)


                    name = NameUtils.getMultiName(token)
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

                    if SanitationUtils.stringContainsDisallowedPunctuation(token) and len(token) == 1:
                        continue

                    self.properties['unknowns'] += [token]
                    self.invalidate("UNKNOWN TOKEN: " + repr(token))

                names = " ".join(congruentNames)
                if names and names not in self.properties['names']:
                    if DEBUG_NAME:
                        SanitationUtils.safePrint( "ADDING NAME: %s" % names )
                    self.properties['names'] += [names]

            if len(self.properties['names'] ) > 1:
                self.problematic = True
                if STRICT_NAME:
                    self.invalidate("THERE ARE MORE THAN 1 NAMES: " + repr(self.properties['names']))
            elif len(self.properties['names']) == 0:
                self.empty = True
                # self.problematic = True
                # SanitationUtils.safePrint("THERE ARE NO NAMES: " + repr(kwargs))

            if len(self.properties['titles'] ) > 1:
                self.problematic = True
                if STRICT_NAME:
                    self.invalidate("THERE MULTIPLE TITLES: " + repr(self.properties['titles']))

            if len(self.properties['notes'] ) > 1:
                self.problematic = True
                if STRICT_NAME:
                    self.invalidate("THERE MULTIPLE NOTES: " + repr(self.properties['notes']))

            if len(self.properties['positions'] ) > 1:
                self.problematic = True
                if STRICT_NAME:
                    self.invalidate("THERE MULTIPLE POSITIONS: " + repr(self.properties['positions']))

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

    SanitationUtils.safePrint( 
        ContactName(
            first_name = 'SHANNON',
            family_name = 'AMBLER (ACCT)',
            contact = "SHANNON AMBLER (ACCT)",
        ).tabulate(tablefmt="simple")
    )

if __name__ == '__main__':
    testContactAddress()
    testContactName()
