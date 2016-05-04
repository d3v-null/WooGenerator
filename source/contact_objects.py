from utils import  SanitationUtils, AddressUtils, NameUtils, listUtils # descriptorUtils, listUtils,
from pprint import pprint
from collections import OrderedDict
from tabulate import tabulate

DEBUG_ADDRESS = False
# DEBUG_ADDRESS = True
STRICT_ADDRESS = False
STRICT_ADDRESS = True

DEBUG_NAME = False
# DEBUG_NAME = True
STRICT_NAME = False
STRICT_NAME = True

class ContactObject(object):
    equality_keys = []
    similarity_keys = []
    key_mappings = {}
    ContactObjectType = "CONTACTOBJ"

    class Combo(list):
        def __init__(self, *args, **kwargs):
            super(ContactObject.Combo, self).__init__(*args, **kwargs)
            self.lastIndex = -1

        def reset(self):
            self[:] = []
            self.lastIndex = -1

        def add(self, index, item):
            self.append(item)
            self.lastIndex = index

        def broken(self, index):
            return self and index != self.lastIndex + 1

        @property
        def flattened(self):
            flat = " ".join(self)
            self.reset()
            return flat


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
        self.properties['ambiguous_tokens'] = []
        self.wordsToRemove = []
        self.nameCombo = ContactObject.Combo()

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
        elif self.problematic:
            prefix = "PROBLEMATIC"
        elif self.valid:
            prefix = "VALID"  
        else:
            prefix = "INVALID"
        prefix += ": "
        return prefix


    # def get(self, key, default = None):
    #     for attr, keys in self.key_mappings.items():
    #         if key in keys:
    #             return getattr(self, attr)
    #     return super(ContactObject, self).get(key, default)


    def addCareof(self, careof):
        if self.debug: SanitationUtils.safePrint( "FOUND CAREOF ",  careof ) 
        if careof not in self.properties['careof_names']:
            self.properties['careof_names'] += [careof]

    def addOrganization(self, organization):
        if self.debug: SanitationUtils.safePrint( "FOUND ORGANIZATION: ",  organization ) 
        if organization not in self.properties['organization_names']:
            self.properties['organization_names'] += [organization]

    def coerceOrganization(self, organization_name):
        organization = NameUtils.getOrganization(organization_name)
        if not organization:
            organization = (organization_name, None)
        self.addOrganization(organization)

    @property
    def careof_names(self):
        if self.properties['careof_names']:
            return ", ".join(
                [" ".join(filter(None,careof_name)) for careof_name in self.properties['careof_names']]
            )

    @property
    def organization_names(self):
        if self.properties['organization_names']:
            return ", ".join(
                [" ".join(filter(None,organization)) for organization in self.properties['organization_names']]
            )
    
    @property
    def names(self):
        if self.properties['names'] or self.properties['careof_names'] or self.properties['organization_names']:
            out = ", ".join(filter(None,
                [
                    " ".join(filter(None, names)) for names in \
                        [
                            [self.careof_names] ,
                            self.properties['names'],
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
        if not self.reason:
            self.reason = reason
        if self.debug: 
            SanitationUtils.safePrint( "INVALID: ", reason )

    def enforceStrict(self, reason = None):
        self.problematic = True
        if self.strict:
            self.invalidate(reason)
        elif self.debug:
            SanitationUtils.safePrint( "PROBLEMATIC: ", reason)

    def tabulate(self, tablefmt = None):
        if not tablefmt:
            tablefmt = 'simple'
        if tablefmt == 'html':
            sanitizer = SanitationUtils.sanitizeForXml
        else:
            sanitizer = SanitationUtils.sanitizeForTable
        if self.empty:
            reason = self.ContactObjectType + " EMPTY"
        else:
            reason = self.reason

        printable_kwargs = {}
        if self.kwargs:
            for key, arg in self.kwargs.items():
                if arg: printable_kwargs[key] = [sanitizer(arg)]

        table = OrderedDict()

        table[self.ContactObjectType] = [sanitizer(self.__unicode__(tablefmt=tablefmt) )]

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
        self.numberCombo = ContactObject.Combo()
        self.strict = STRICT_ADDRESS
        self.debug = DEBUG_ADDRESS

        if not any( filter(None, map(
            lambda key: kwargs.get(key, ''), 
            ['line1', 'line2', 'city', 'postcode', 'state']
        ))): 
            self.schema = None
        else:
            self.empty = False
            if DEBUG_ADDRESS: pprint(kwargs)
            if not schema: self.schema = self.__class__.determineSchema(**kwargs)

            lines = listUtils.filterUniqueTrue(map(lambda key: SanitationUtils.normalizeVal(kwargs.get(key, '')), ['line1', 'line2']))

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

            if kwargs.get('company'):
                companySanitized = SanitationUtils.normalizeVal(kwargs['company'])
                company_tokens = NameUtils.tokenizeName(companySanitized)
                company_has_notes = False
                for token in company_tokens:
                    note = NameUtils.getNote(token)
                    if note:
                        company_has_notes = True
                        # self.enforceStrict("Company name contains notes: " + self.getNoteNoParanthesis(note))
                if not company_has_notes:
                    self.wordsToRemove.append(companySanitized)
                    self.coerceOrganization(kwargs.get('company'))

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
                self.nameCombo.reset()
                self.numberCombo.reset()
                for j, token in enumerate(tokens):
                    if self.numberCombo.broken(j): self.addNumber(self.numberCombo.flattened)
                    if self.nameCombo.broken(j): self.addName(self.nameCombo.flattened)
                    if DEBUG_ADDRESS: SanitationUtils.safePrint( u"-> token[%d]: %s" % (j, token) )
                    if len(token) == 1 and SanitationUtils.stringContainsDisallowedPunctuation(token):
                        continue
                    self.parseToken(j, token)

                    # break
                if self.numberCombo:
                    if DEBUG_ADDRESS: SanitationUtils.safePrint( "CONGRUENT NUMBERS AT END OF CYCLE:", self.numberCombo)
                    self.addNumber(self.numberCombo.flattened)
                if self.nameCombo:
                    if DEBUG_ADDRESS: SanitationUtils.safePrint( "CONGRUENT NAMES AT END OF CYCLE:", self.nameCombo)
                    self.addName(self.nameCombo.flattened)
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

            while self.properties['incomplete_subunits']:
                incomplete_subunit = self.properties['incomplete_subunits'].pop()
                self.completeSubunit(incomplete_subunit)

            while self.properties['ambiguous_tokens']:
                ambiguous_token = self.properties['ambiguous_tokens']
                self.addWeakThoroughfare(ambiguous_token)

            if self.properties['unknowns']:
                self.invalidate("There are some unknown tokens: %s" % repr( " | ".join( self.properties['unknowns'])))
                
            #if any unknowns match number, then add them as a blank subunit

            # if(schema in ['act']):
            #     pass
            #     #TODO: THIS
            # else:
            #     pass
            #     #TODO: THIS

    def parseToken(self, tokenIndex, token):
        for getter, adder in [
            (AddressUtils.getDelivery, self.addDelivery),
            (AddressUtils.getSubunit, self.addSubunit),
            (AddressUtils.getFloor, self.addFloor),
            (AddressUtils.getThoroughfare, self.addThoroughfare),
            (NameUtils.getCareOf, self.addCareof),
            (NameUtils.getOrganization, self.addOrganization),
            (AddressUtils.getWeakSubunit, self.addWeakSubunit)
        ]:
            result = getter(token)
            if result: 
                adder(result)
                return

        name = NameUtils.getMultiName(token)
        number = AddressUtils.getNumber(token)
        weak_thoroughfare = AddressUtils.getWeakThoroughfare(token)
        building = AddressUtils.getBuilding(token)

        if (not name) or weak_thoroughfare or building: 
            if self.nameCombo: self.addName(self.nameCombo.flattened)
        if not number:
             if self.numberCombo: self.addNumber(self.numberCombo.flattened)

        if(building and weak_thoroughfare):
            if DEBUG_ADDRESS: SanitationUtils.safePrint( "BUILDING AND WEAK THOROUGHFARE" )
            self.addName(token)
            return
            # self.invalidate("Ambiguous thoroughfare or building (multiple buildings detected): %s" % repr(token))
        if(weak_thoroughfare):
            self.addWeakThoroughfare(weak_thoroughfare)
            return
        if(building and self.properties['buildings']):
            self.addBuilding(building)
            return
        #ignore if unknown is city or state
        # if token in self.wordsToRemove:
        #     self.properties['ignores'] += [token]
        #     if DEBUG_ADDRESS: SanitationUtils.safePrint( "IGNORING WORD ", token)
        #     return

        # state = AddressUtils.getState(token)
        # if(state and not self.properties['state']):
        #     #this might be the state but can't rule it out being something else
        #     self.properties['possible_states'] = list( 
        #         set( self.properties['possible_states'] ) + set([token])
        #     )
        #     if DEBUG_ADDRESS: SanitationUtils.safePrint( "IGNORING STATE ", state)
        #     return


        if name:
            if DEBUG_ADDRESS:
                SanitationUtils.safePrint( "FOUND NAME:", name)
            self.nameCombo.add(tokenIndex, name)
            return

        if(number):
            if DEBUG_ADDRESS:
                SanitationUtils.safePrint( "FOUND NUMBER:", number)
            self.numberCombo.add(tokenIndex, number)
            return

        if DEBUG_ADDRESS: SanitationUtils.safePrint( "UNKNOWN TOKEN", token)
        self.properties['unknowns'] += [token]
        self.invalidate("There are some unknown tokens: %s" % repr(self.properties['unknowns']))    

    # NO SUBUNUTS -> SUBUNIT W/ NO UNIT TYPE

    def addNumber(self, number):
        # if self.nameCombo: self.addName(self.nameCombo.flattened)
        number = AddressUtils.getNumber(number)
        if not number:
            return
        if self.properties['incomplete_subunits'] and not self.nameCombo:
            subunit_type, subunit_number = self.properties['incomplete_subunits'].pop()
            try:
                assert not SanitationUtils.stringContainsPunctuation(number), "Number must be single"
                number_find = AddressUtils.getSingleNumber(number)
                assert number_find, "Number must be valid"
                subunit_find = AddressUtils.getSingleNumber(subunit_number) 
                assert subunit_find, "subunit number must be singular"
                assert int(number_find) > int(subunit_find), "Number must be greater than subunit number"
                subunit_number += number
                self.addSubunit( (subunit_type, subunit_number) )
            except Exception, e:
                if DEBUG_ADDRESS: SanitationUtils.safePrint(e)
                self.completeSubunit( (subunit_type, subunit_number) )
                self.addNumber( number )
        elif not self.properties['subunits']:
            self.coerceSubunit(number)
        else:
            self.properties['numbers'] += [number]

    # NUMBERS and NO THOROUGHFARES -> WEAK THOROUGHFARE
    # SUBUNIT or FLOORS or DELIVERIES -> BUILDING 

    def addName(self, name):
        # if self.numberCombo: self.addNumber(self.numberCombo.flattened)
        # name = NameUtils.getMultiName(name)
        if not name:
            return
        # if we haven't flushed numberCombo, do it now
        if DEBUG_ADDRESS: SanitationUtils.safePrint( "PROCESSING NAME", name)
        names = filter(None, NameUtils.getSingleNames(name))
        if DEBUG_ADDRESS: SanitationUtils.safePrint( "SINGLE NAMES", names)
        #TODO: Which one goes to which?
        if not (self.properties['thoroughfares'] + self.properties['weak_thoroughfares']) and \
        (self.properties['numbers'] or self.properties['coerced_subunits']):
            weak_thoroughfare = AddressUtils.getWeakThoroughfare(name)
            if not weak_thoroughfare:
                if len(names) > 1:
                    thoroughfare_name = " ".join(map(str, names[:-1]))
                    thoroughfare_type = names[-1]
                else:
                    thoroughfare_name = name
                    thoroughfare_type = None
                weak_thoroughfare = (thoroughfare_name, thoroughfare_type, None)
            self.addWeakThoroughfare(weak_thoroughfare)
        elif not (self.properties['buildings']) and \
        (self.properties['subunits'] or self.properties['floors'] or self.properties['deliveries']):
            building = AddressUtils.getBuilding(name)
            if building:
                self.addBuilding(building)
            else:
                self.coerceBuilding(name)
        elif name in self.wordsToRemove:
            self.properties['ignores'] += [name]
        else:
            self.properties['names'] += [name]

    def addSubunit(self, subunit):
        subunit_type, subunit_number = subunit
        if subunit_type in ['SHOP', 'SUITE', 'KIOSK', 'SHRM', 'STORE']:
            self.isShop = True
        if subunit_number[-1] == '/':
            while self.properties['incomplete_subunits']:
                self.completeSubunit(self.properties['incomplete_subunits'].pop())
            if DEBUG_ADDRESS: SanitationUtils.safePrint( "ADDING INCOMPLETE SUBUNIT: ", subunit)
            self.properties['incomplete_subunits'] += [subunit]
        else:
            if DEBUG_ADDRESS: SanitationUtils.safePrint( "ADDING SUBUNIT: ", subunit)
            self.properties['subunits'] += [subunit]

    def addWeakSubunit(self, weak_subunit):
        subunit_type, subunit_number = weak_subunit
        if DEBUG_ADDRESS:
            self.enforceStrict("Unknown subunit type: %s" % subunit_type)
        self.addSubunit(weak_subunit)

    def coerceSubunit(self, number):
        subunit = (None, number)
        if DEBUG_ADDRESS:  SanitationUtils.safePrint("COERCED SUBUNIT:", subunit)
        self.properties['coerced_subunits'] += [subunit]

    def completeSubunit(self, incomplete_subunit):
        subunit_type, subunit_number = incomplete_subunit
        if subunit_number[-1] == '/':
            subunit_number = subunit_number[:-1]
        complete_subunit = subunit_type, subunit_number
        self.addSubunit( complete_subunit )

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
        thoroughfare_number, thoroughfare_name, thoroughfare_type, thoroughfare_suffix = thoroughfare
        self.assertValidThoroughfareType(thoroughfare_name, thoroughfare_type)
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

    def addWeakThoroughfare( self, weak_thoroughfare):
        if not (self.properties['thoroughfares'] or self.properties['weak_thoroughfares']):
            if self.properties['numbers'] or self.properties['coerced_subunits']:
                # if self.numberCombo:
                #     number = AddressUtils.getNumber(self.numberCombo.flattened)
                if self.properties['numbers']:
                    number = self.properties['numbers'].pop()
                elif self.properties['coerced_subunits']:
                    subunit_type, number = self.properties['coerced_subunits'].pop()

                # token = " ".join(names)
                self.coerceThoroughfare(number, weak_thoroughfare)
                return
            if DEBUG_ADDRESS: SanitationUtils.safePrint( "ADDING WEAK THOROUGHFARE: ", weak_thoroughfare)
            thoroughfare_name, thoroughfare_type, thoroughfare_suffix = weak_thoroughfare
            self.assertValidThoroughfareType(thoroughfare_name, thoroughfare_type)
            self.properties['weak_thoroughfares'] += [weak_thoroughfare]
        else:
            token = " ".join(filter(None, weak_thoroughfare))
            self.coerceBuilding(token)

    def addFloor(self, floor):
        if DEBUG_ADDRESS: SanitationUtils.safePrint( "ADDING FLOOR: ", floor)
        self.properties['floors'] += [floor]


    def addDelivery(self, delivery):
        if DEBUG_ADDRESS: SanitationUtils.safePrint( "ADDING DELIVERY: ", delivery)
        self.properties['deliveries'] += [delivery]

    def assertValidThoroughfareType(self, thoroughfare_name, thoroughfare_type):
        if thoroughfare_type:
            try:
                assert AddressUtils.identifyThoroughfareType(thoroughfare_type), "Unknown thoroughfares type: %s" % thoroughfare_type
            except Exception, e:
                self.enforceStrict(e)
        else:
            self.enforceStrict("No thoroughfare type: " + thoroughfare_name)

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

    def __unicode__(self, tablefmt = None):
        prefix = self.getPrefix() if DEBUG_ADDRESS else ""
        delimeter = "; "
        if tablefmt == "html":
            delimeter = "<br/>"
        return SanitationUtils.coerceUnicode( prefix + delimeter.join(filter(None,[
            self.line1,
            self.line2,
            self.line3,
            (("|UNKN:" + " ".join(self.properties['unknowns'])) \
                if DEBUG_ADDRESS and self.properties['unknowns'] else "")
        ])) ) 

    def __str__(self, tablefmt=None):
        return SanitationUtils.coerceBytes(self.__unicode__(tablefmt)) 

def testContactAddress():
    # DOESN'T GET

    print ContactAddress(
        line1 = 'LEVEL 2, SHOP 202 / 8B "WAX IT"',
        line2 = "ROBINA TOWN CENTRE"
    ).__str__(tablefmt="flat")
    
    print ContactAddress(
        line1 = 'BROADWAY FAIR SHOPPING CTR',
        line2 = 'SHOP 16, 88 BROADWAY'
    ).__str__(tablefmt="flat")

    print ContactAddress(
        line1 = "Factory 5/ inglewood s/c Shop 7/ 12 15th crs")

    print ContactAddress(
        line1 = "SHOP 9 PASPALIS CENTREPOINT",
        line2 = "SMITH STREET MALL"
    ).__str__(tablefmt="flat")

    print ContactAddress(
        **{'city': u'TEA TREE GULLY',
         'country': u'AUSTRALIA',
         'line1': u'SHOP 238/976',
         'line2': u'TEA TREE PLAZA',
         'postcode': u'5092',
         'state': u'SA'}
    ).__str__(tablefmt="flat")

    # return
    #GETS

    print ContactAddress(
        line1 = "SHOP 10, 575/577",
        line2 = "CANNING HIGHWAY"
    ).__str__(tablefmt="flat")

    SanitationUtils.safePrint(
        ContactAddress(
            line1 = "UNIT 9/42 EXERSOR ST"
        ).tabulate(tablefmt="simple")
    )

    print ContactAddress(
        line1 = 'SHOP 3 81-83',
    ).__str__(tablefmt="flat")

    SanitationUtils.safePrint(
        ContactAddress(
            line1 = "SHOP  2052 LEVEL 1 WESTFIELD"
        ).tabulate(tablefmt="simple")
    )

    print ContactAddress(
        line1 = 'SUIT 1 1 MAIN STREET',
    ).__str__(tablefmt="flat")


    print ContactAddress(
        line1 = 'SAHOP 5, 7-13 BEACH ROAD',
    ).__str__(tablefmt="flat")


    print ContactAddress(
        line1 = 'THE OFFICE OF SENATOR DAVID BUSHBY',
        line2 = 'LEVE 2, 18 ROSSE AVE'
    ).__str__(tablefmt="flat")

    print ContactAddress(
        line1 = 'SUITE 3/ LEVEL 8',
        line2 = '187 MACQUARIE STREET'
    ).__str__(tablefmt="flat")

    print ContactAddress(
        line1 = 'LEVEL 1, 407 LOGAN ROAD',
    ).__str__(tablefmt="flat")
    print ContactAddress(
        line1 = 'P.O.BOX 3385',
    ).__str__(tablefmt="flat")

    print ContactAddress(
        line1 = 'UNIT 6/7, 38 GRAND BOULEVARD',
    ).__str__(tablefmt="flat")

    print ContactAddress(
        line1 = 'SHOP 2/3 103 MARINE TERRACE',
    ).__str__(tablefmt="flat")

    print ContactAddress(
        line1 = 'UNIT 4/ 12-14 COMENARA CRS',
    ).__str__(tablefmt="flat")

    print ContactAddress(
        line1 = 'UNIT 25/39 ASTLEY CRS',
    ).__str__(tablefmt="flat")


    print ContactAddress(
        line1 = 'SHOP 6-7, 13-15 KINGSWAY',
    ).__str__(tablefmt="flat")
    
    print ContactAddress(
        line1 = 'SHOP 1, 292 MAITLAND'
    ).__str__(tablefmt="flat")

    print ContactAddress(
        line1 = 'TOWNHOUSE 4/115 - 121',
        line2 = 'CARINGBAH ROAD'
    ).__str__(tablefmt="flat")

    print ContactAddress(
        line1 = "Midvale Shopping Centre, Shop 9, 1174 Geelong Road"
    ).__str__(tablefmt="flat")

    print ContactAddress(
        line1 = "SHOP 5&6, 39 MURRAY ST"
    ).__str__(tablefmt="flat")

    print ContactAddress(
        line1 = "C/O COCO BEACH",
        line2 = "SHOP 3, 17/21 PROGRESS RD"
    ).__str__(tablefmt="flat")

    print ContactAddress(
        line1 = "6/208 MCDONALD STREET",
        line2 = "6/208 MCDONALD STREET",
    ).__str__(tablefmt="flat")

    print ContactAddress(
        line1 = "UNIT 4 / 24"
    ).__str__(tablefmt="flat")

    print ContactAddress(
        line1 = "6/7 118 RODWAY ARCADE"
    ).__str__(tablefmt="flat")    

    print ContactAddress(
        line1 = "PO 5217 MACKAY MAIL CENTRE"
    ).__str__(tablefmt="flat")

    print ContactAddress(
        line1 = "73 NORTH PARK AVENUE",
        line2 = "ROCKVILLE CENTRE"
    ).__str__(tablefmt="flat")

    print ContactAddress(
         line1 = u'ANTONY WHITE, PO BOX 886',
         line2 = u'LEVEL1 468 KINGSFORD SMITH DRIVE'
    ).__str__(tablefmt="flat")

    print ContactAddress(
        line1 = "TAN IT UP",
        line2 = "73 WOODROSE ROAD"
    ).__str__(tablefmt="flat")

    print ContactAddress(
        line1 = "DANNY, SPG1 LG3 INGLE FARM SHOPPING CENTRE"
    ).__str__(tablefmt="flat")

    print ContactAddress(
        line1 = "3/3 HOWARD AVA"
    ).__str__(tablefmt="flat")

    print ContactAddress(
        line1 = "G.P.O BOX 440",
        line2 = "CANBERRA CITY",
    ).__str__(tablefmt="flat")

    print ContactAddress(
        line1 = "SHOP 29 STIRLING CENTRAL",
        line2 = "478 WANNEROO RD",
    ).__str__(tablefmt="flat")

    print ContactAddress(
        city = 'ROSSMORE',
        state = 'NSW',
        line1 = "700 15TH AVE",
        line2 = "LANDSBOROUGH PARADE",
        postcode = "2557"
    ).__str__(tablefmt="flat")

    print ContactAddress(
        line1 = "LEVEL A",
        line2 = "MYER CENTRE",
    ).__str__(tablefmt="flat")

    print ContactAddress(
        city = 'GOLDEN BEACH',
        state = 'QLD',
        country = 'Australia',
        line1 = "C/- PAMPERED LADY - GOLDEN BEACH SHOPPING CENTRE",
        line2 = "LANDSBOROUGH PARADE",
        postcode = "4551"
    ).__str__(tablefmt="flat")

    print ContactAddress(
        city = 'CHATSWOOD',
        state = 'NSW',
        country = 'Australia',
        line1 = "SHOP 330 A VICTORIA AVE",
        postcode = "2067"
    ).__str__(tablefmt="flat")

    print ContactAddress(
        city = 'Perth',
        state = 'WA',
        country = 'Australia',
        line1 = "SHOP 5/562 PENNANT HILLS RD",
    ).__str__(tablefmt="flat")

    print ContactAddress(
        city = 'Perth',
        state = 'WA',
        country = 'Australia',
        line1 = "SHOP G159 BROADMEADOWS SHOP. CENTRE",
        line2 = "104 PEARCEDALE PARADE"
    ).__str__(tablefmt="flat")

    print ContactAddress(
        city = 'Jandakot',
        state = 'WA',
        country = 'Australia',
        line1 = "Unit 1\\n",
        line2 = "41 Biscayne Way",
        postcode = "6164"
    ).__str__(tablefmt="flat")

    print ContactAddress(
        line1 = "SH115A, FLOREAT FORUM"
    ).__str__(tablefmt="flat")

    print ContactAddress(
        line1 = "A8/90 MOUNT STREET"
    ).__str__(tablefmt="flat")

    print ContactAddress(
        line1 = "8/5-7 KILVINGTON DRIVE EAST"
    ).__str__(tablefmt="flat")

    print ContactAddress(
        line1 = "THE VILLAGE SHOP 5"
    ).__str__(tablefmt="flat")


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
        'name_suffix':['Name Suffix'],
        'organization_names':['Company']
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
        self.properties['emails'] = []
        self.properties['family_names'] = []
        self.strict = STRICT_NAME
        self.debug = DEBUG_NAME


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
                company_tokens = NameUtils.tokenizeName(companySanitized)
                company_has_notes = False
                for token in company_tokens:
                    note = NameUtils.getNote(token)
                    if note:
                        company_has_notes = True
                        # self.enforceStrict("Company name contains notes: " + self.getNoteNoParanthesis(note))
                if not company_has_notes:
                    self.wordsToRemove.append(companySanitized)
                    self.coerceOrganization(kwargs.get('company'))

            full_name_contact = SanitationUtils.normalizeVal(kwargs.get('contact'))
            full_name_components = SanitationUtils.normalizeVal(' '.join(filter(None, map(
                lambda k: kwargs.get(k),
                ['name_prefix', 'first_name', 'middle_name', 'family_name', 'name_suffix']
            ))))

            if full_name_contact and full_name_components:
                no_punctuation_contact, no_punctuation_components = map(SanitationUtils.similarNoPunctuationComparison, [full_name_contact, full_name_components])
                if no_punctuation_contact == no_punctuation_components:
                    # The names are effectively the same, can drop one
                    full_name_components = None
                else:
                    reverse_name_components = SanitationUtils.similarNoPunctuationComparison(" ".join(filter(None,[kwargs.get('family_name'), kwargs.get('first_name'), kwargs.get('middle_name')])))
                    # print reverse_name_components, no_punctuation_contact
                    if reverse_name_components == no_punctuation_contact:
                        if DEBUG_NAME: SanitationUtils.safePrint("DETECTED REVERSE NAME: ", full_name_contact)
                        # self.enforceStrict("Ambiguous if format is family_name, first_name middle_name or just stray comma")
                        full_name_contact = None

            full_names = listUtils.filterUniqueTrue(map(SanitationUtils.normalizeVal, [full_name_contact, full_name_components]))

            if len(full_names) > 1:
                self.invalidate("Unable to determine which name is correct: %s" % " / ".join(full_names))

            for i, full_name in enumerate(full_names):
                if DEBUG_NAME: SanitationUtils.safePrint( "ANALYSING NAME %d: %s" % (i, repr(full_name)) ) 
                tokens = NameUtils.tokenizeName(full_name)
                if DEBUG_NAME: SanitationUtils.safePrint( "TOKENS:", repr(tokens) )
                self.nameCombo.reset()
                # SanitationUtils.safePrint(u"TOKENS {} FOR {} ARE {}".format(len(tokens), full_name, tokens))
                for j, token in enumerate(tokens):
                    if self.nameCombo.broken(j): self.addName(self.nameCombo.flattened)

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

                    email = NameUtils.getEmail(token)
                    if email:
                        if DEBUG_NAME: SanitationUtils.safePrint("FOUND EMAIL:", email)
                        if email not in self.properties['emails']:
                            self.properties['emails'] += [email]
                        continue

                    note = NameUtils.getNote(token)
                    if note:
                        if DEBUG_NAME:
                            SanitationUtils.safePrint( "FOUND NOTE:", self.getNoteNoParanthesis( note) )
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
                        self.properties['family_names'] += [family_name]
                        continue

                    name = NameUtils.getMultiName(token)
                    if name:
                        if DEBUG_NAME:
                            SanitationUtils.safePrint( "FOUND NAME: %s" % name )
                        self.nameCombo.add(j, name)
                        continue

                    if SanitationUtils.stringContainsDisallowedPunctuation(token) and len(token) == 1:
                        continue

                    self.properties['unknowns'] += [token]
                    self.invalidate("UNKNOWN TOKEN: " + repr(token))

                if self.nameCombo:
                    if DEBUG_ADDRESS: SanitationUtils.safePrint( "CONGRUENT NAMES AT END OF CYCLE:", self.nameCombo)
                    self.addName(self.nameCombo.flattened)


            if len(self.properties['names'] ) > 1:
                self.enforceStrict("THERE ARE MULTIPLE NAMES: " + SanitationUtils.coerceBytes(' / '.join(self.properties['names'])))
            elif len(self.properties['names']) == 0:
                self.empty = True
                # self.problematic = True
                # SanitationUtils.safePrint("THERE ARE NO NAMES: " + repr(kwargs))

            if len(self.properties['titles'] ) > 1:
                self.enforceStrict("THERE ARE MULTIPLE TITLES: " + SanitationUtils.coerceBytes(' / '.join(self.properties['titles'])))

            if len(self.properties['notes'] ) > 1:
                self.enforceStrict("THERE ARE MULTIPLE NOTES: " + SanitationUtils.coerceBytes(" / ".join(map(self.getNoteNoParanthesis, self.properties.get('notes', []))) ))

            if len(self.properties['positions'] ) > 1:
                self.enforceStrict("THERE ARE MULTIPLE POSITIONS: " + SanitationUtils.coerceBytes(' / '.join(self.properties['positions'])))

            if self.properties['unknowns']:
                self.invalidate("There are some unknown tokens: %s" % SanitationUtils.coerceBytes(' / '.join(self.properties['unknowns'])))

    def addName(self, name):
        if name in self.wordsToRemove:
            self.properties['ignores'] += [name]
            if DEBUG_NAME: 
                SanitationUtils.safePrint( "IGNORING WORD:", name )
            return
        if name and name not in self.properties['names']:
            if DEBUG_NAME: SanitationUtils.safePrint( "ADDING NAME: %s" % name )
            self.properties['names'] += [name]

    def getNoteNoParanthesis(self, note_tuple):
        note_open_paren, names_before_note, note, names_after_note, note_close_paren = note_tuple
        return " ".join(filter(None, [names_before_note, note, names_after_note]))


    @property
    def first_name(self):
        if self.valid:
            if len(self.properties.get('names', [])) > 0 :
                return self.properties.get('names')[0] 
            else:
                return ""
        else :
            return self.kwargs.get('first_name') 

    @property
    def family_name(self):
        if self.valid:
            if len(self.properties.get('family_names', [])) > 1:
                return self.properties.get('family_names')[-1]
            elif len(self.properties.get('names', [])) > 1:
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
            return self.kwargs.get('middle_name') 

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
            positions_suffixes = self.properties.get('positions', []) + self.properties.get('suffixes', [])
            if len(positions_suffixes) > 0:
                return " ".join(positions_suffixes) 
            else:
                return ""
        else:
            return self.kwargs.get('name_suffix') 

    @property
    def name_notes(self):
        if self.valid:
            return ', '.join(map(self.getNoteNoParanthesis, self.properties.get('notes', []) )) 
        else:
            return self.kwargs.get('name_notes')  
    

    def __unicode__(self, tablefmt=None):
        prefix = self.getPrefix() if DEBUG_NAME else ""
        delimeter = " "
        return SanitationUtils.coerceUnicode( prefix + delimeter.join(filter(None,[
            (("PREF: "+ self.name_prefix) if DEBUG_NAME and self.name_prefix else self.name_prefix),
            (("FIRST: " + self.first_name) if DEBUG_NAME and self.first_name else self.first_name),
            (("MID: " + self.middle_name) if DEBUG_NAME and self.middle_name else self.middle_name),
            (("FAM: " + self.family_name) if DEBUG_NAME and self.family_name else self.family_name),
            (("SUFF: " + self.name_suffix) if DEBUG_NAME and self.name_suffix else self.name_suffix),
            (("NOTES: (%s)" % self.name_notes) if DEBUG_NAME and self.name_notes else "(%s)" % self.name_notes if self.name_notes else None),
            (("|UNKN:" + " ".join(self.properties['unknowns'])) \
                if DEBUG_NAME and self.properties['unknowns'] else "")
        ])))

    def __str__(self, tablefmt = None):
        return SanitationUtils.coerceBytes(self.__unicode__(tablefmt)) 

def testContactName():
    SanitationUtils.safePrint( 
        ContactName(
            contact = "C ARCHIVE STEPHANIDIS"
        ).tabulate(tablefmt="simple")
    )

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
            contact = "SPOKE WITH MICHELLE (RECEPTION)",
        ).tabulate(tablefmt="simple")
    )

    SanitationUtils.safePrint( 
        ContactName(
            contact = "SMITH, DERWENT",
            first_name = "DERWENT",
            family_name = "SMITH"
        ).tabulate(tablefmt="simple")
    )

    SanitationUtils.safePrint( 
        ContactName(
            contact = "KYLIESSWEET@GMAIL.COM",
        ).tabulate(tablefmt="simple")
    )

    #gets

    # return

    SanitationUtils.safePrint( 
        ContactName(
            contact = "CILLA (SILL-A) OWNER OR HAYLEE",
        ).tabulate(tablefmt="simple")
    )

    SanitationUtils.safePrint( 
        ContactName(
            contact = "NICOLA FAIRHEAD(MORTON)",
        ).tabulate(tablefmt="simple")
    )

    SanitationUtils.safePrint( 
        ContactName(
            first_name = 'SHANNON',
            family_name = 'AMBLER (ACCT)',
            contact = "SHANNON AMBLER (ACCT)",
        ).tabulate(tablefmt="simple")
    )

    SanitationUtils.safePrint( 
        ContactName(
            contact = "KAITLYN - FINALIST",
            first_name = "KAITLYN",
            family_name = "FINALIST"
        ).tabulate(tablefmt="simple")
    )

    SanitationUtils.safePrint( 
        ContactName(
            contact = "JESSICA (THITIRAT) PHUSOMSAI",
            first_name = "JESSICA",
            family_name = "(THITIRAT) PHUSOMSAI"

        ).tabulate(tablefmt="simple")
    )

if __name__ == '__main__':
    # testContactAddress()
    testContactName()
