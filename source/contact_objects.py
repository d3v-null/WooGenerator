# from __future__ import absolute_import
from utils import SanitationUtils, AddressUtils, NameUtils, listUtils
from utils import descriptorUtils, Registrar
from pprint import pprint
from collections import OrderedDict
from tabulate import tabulate
from copy import deepcopy


STRICT_ADDRESS = False
STRICT_ADDRESS = True

STRICT_NAME = False
STRICT_NAME = True

DEBUG_ADDRESS = False
# DEBUG_ADDRESS = True

DEBUG_NAME = False
# DEBUG_NAME = True

class FieldGroup(Registrar):
    """Groups a series of fields together so that they are synced at the same
    time"""
    equality_keys = []
    similarity_keys = []
    mandatory_keys = []
    key_mappings = {}
    fieldGroupType = 'GRP'
    _supports_tablefmt = True
    performPost = False

    def __init__(self, **kwargs):
        super(FieldGroup, self).__init__()
        self.kwargs = kwargs
        self.empty = self.mandatory_keys and not any( filter(None, map(
            lambda key: self.kwargs.get(key),
            self.mandatory_keys
        )))
        self.valid = True
        self.properties = OrderedDict()
        self.problematic = False
        self.reason = ""
        self.debug = False

    @property
    def properties_override(self):
        if self.performPost and self.valid:
            return True

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
                if self.properties_override:
                    return getattr(self, attr)
                else:
                    return self.kwargs.get(attr)

    def __setitem__(self, key, val):
        # print "setting cont %s to %s " % (key, val)
        for attr, keys in self.key_mappings.items():
            if key in keys:
                if self.properties_override:
                    return setattr(self, attr, val)
                else:
                    self.kwargs[attr] = val
                    return


    def __copy__(self):
        # print "calling copy on ", self
        retval = self.__class__(**self.kwargs[:])
        # print " -> retval", retval
        return retval

    def __deepcopy__(self, memodict=None):
        # print ("calling deepcopy on ", self)
        # print ("-> kwargs ", deepcopy(self.kwargs, memodict))
        retval = self.__class__(**deepcopy(self.kwargs, memodict))
        # print (" -> retval", retval, retval.kwargs)
        return retval

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

    def invalidate(self, reason = None):
        self.valid = False
        if not self.reason:
            self.reason = reason
        self.registerError( "INVALID: %s" % SanitationUtils.coerceUnicode(reason) )

    def enforceStrict(self, reason = None):
        self.problematic = True
        if self.strict:
            self.invalidate(reason)
            self.registerMessage( "PROBLEMATIC: %s"  % SanitationUtils.coerceUnicode(reason))

    def tabulate(self, tablefmt = None):
        if not tablefmt:
            tablefmt = 'simple'
        if tablefmt == 'html':
            sanitizer = SanitationUtils.sanitizeForXml
        else:
            sanitizer = SanitationUtils.sanitizeForTable
        if self.empty:
            reason = self.fieldGroupType + " EMPTY"
        else:
            reason = self.reason

        printable_kwargs = {}
        if self.kwargs:
            for key, arg in self.kwargs.items():
                if arg: printable_kwargs[key] = [sanitizer(arg)]

        table = OrderedDict()

        table[self.fieldGroupType] = [sanitizer(self.__unicode__(tablefmt=tablefmt) )]

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

class ContactObject(FieldGroup):
    fieldGroupType = "CONTACTOBJ"

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
        super(ContactObject, self).__init__(**kwargs)
        self.schema = schema
        if self.performPost:
            self.properties['ignores'] = []
            self.properties['unknowns'] = []
            self.properties['names'] = []
            self.properties['end_names'] = []
            self.properties['careof_names'] = []
            self.properties['organization_names'] = []
            self.properties['ambiguous_tokens'] = []
            self.wordsToRemove = []
            self.nameCombo = ContactObject.Combo()

    def __copy__(self):
        # print "calling copy on ", self
        retval = self.__class__(self.schema, **self.kwargs[:])
        # print " -> retval", retval
        return retval

    def __deepcopy__(self, memodict=None):
        # print ("calling deepcopy on ", self)
        # print ("-> kwargs ", deepcopy(self.kwargs, memodict))
        retval = self.__class__(deepcopy(self.schema,memodict), **deepcopy(self.kwargs, memodict))
        # print (" -> retval", retval, retval.kwargs)
        return retval

    # def get(self, key, default = None):
    #     for attr, keys in self.key_mappings.items():
    #         if key in keys:
    #             return getattr(self, attr)
    #     return super(ContactObject, self).get(key, default)


    def addCareof(self, careof):
        self.registerMessage("FOUND CAREOF %s"  % SanitationUtils.coerceUnicode(careof))
        if careof not in self.properties['careof_names']:
            self.properties['careof_names'] += [careof]

    def addOrganization(self, organization):
        self.registerMessage( "FOUND ORGANIZATION: %s"  % SanitationUtils.coerceUnicode(organization))
        if organization not in self.properties['organization_names']:
            self.properties['organization_names'] += [organization]

    def coerceOrganization(self, organization_name):
        organization = NameUtils.getOrganization(organization_name)
        if not organization:
            organization = (organization_name, None)
        self.addOrganization(organization)

    @property
    def careof_names(self):
        if self.properties.get('careof_names'):
            return ", ".join(
                [" ".join(filter(None,careof_name)) for careof_name in self.properties['careof_names']]
            )

    @property
    def organization_names(self):
        if self.properties.get('organization_names'):
            return ", ".join(
                [" ".join(filter(None,organization)) for organization in self.properties['organization_names']]
            )

    company = descriptorUtils.kwargAliasProperty(
        'company',
        lambda self: ", ".join(
            [" ".join(filter(None,organization)) for organization in self.properties['organization_names']]
        )
    )

    @property
    def names(self):
        if self.properties.get('names') or self.properties.get('careof_names') or self.properties.get('organization_names'):
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

class ContactAddress(ContactObject):
    fieldGroupType = "ADDRESS"
    equality_keys = ['line1', 'line2', 'line3']
    similarity_keys = ['country', 'state', 'postcode', 'city', 'thoroughfares', 'deliveries', 'names', 'buildings', 'floors', 'subunits']
    mandatory_keys = ['line1', 'line2', 'city', 'postcode', 'state']
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
        self.strict = STRICT_ADDRESS
        self.debug = DEBUG_ADDRESS
        if self.performPost:
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
            self.numberCombo = ContactObject.Combo()
            self.processKwargs()

    def processKwargs(self):
        if not self.empty:
            # if not schema: self.schema = self.__class__.determineSchema(**self.kwargs)

            lines = listUtils.filterUniqueTrue(map(lambda key: SanitationUtils.normalizeVal(self.kwargs.get(key, '')), ['line1', 'line2']))

            if self.kwargs.get('country', ''):
                countrySanitized = AddressUtils.sanitizeState(self.kwargs['country'])
                countryIdentified = AddressUtils.identifyCountry(countrySanitized)
                # if self.debug: print "countrySanitized", countrySanitized, "countryIdentified", countryIdentified
                if countrySanitized != countryIdentified:
                    self.properties['country'] = countryIdentified
                else:
                    self.properties['country'] = countrySanitized
                # self.wordsToRemove.append(countrySanitized)

            if self.kwargs.get('state', ''):
                stateSanitized = AddressUtils.sanitizeState(self.kwargs['state'])
                self.wordsToRemove.append(stateSanitized)
                stateIdentified = AddressUtils.identifyState(stateSanitized)
                if stateIdentified != stateSanitized:
                    self.wordsToRemove.append(stateIdentified)
                    self.properties['state'] = stateIdentified
                else:
                    self.properties['state'] = stateSanitized


            if self.kwargs.get('city', ''):
                citySanitized = AddressUtils.sanitizeState(self.kwargs['city'])
                self.properties['city'] = citySanitized
                # self.wordsToRemove.append(citySanitized)

            if self.kwargs.get('postcode'):
                self.properties['postcode'] = self.kwargs.get('postcode')
                if SanitationUtils.stringContainsNoNumbers( self.kwargs.get('postcode')) :
                    self.invalidate("Postcode has no numbers: %s" % repr(self.kwargs.get('postcode')) )

            if self.kwargs.get('company'):
                companySanitized = SanitationUtils.normalizeVal(self.kwargs['company'])
                company_tokens = NameUtils.tokenizeName(companySanitized)
                company_has_notes = False
                for token in company_tokens:
                    note = NameUtils.getNote(token)
                    if note:
                        company_has_notes = True
                        # self.enforceStrict("Company name contains notes: " + self.getNoteNoParanthesis(note))
                if not company_has_notes:
                    self.wordsToRemove.append(companySanitized)
                    self.coerceOrganization(self.kwargs.get('company'))

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
                self.registerMessage( "ANALYSING LINE %d: %s" % (i, repr(line)))
                tokens = AddressUtils.tokenizeAddress(line)
                self.registerMessage( u"TOKENS: %s" % repr(tokens))
                self.nameCombo.reset()
                self.numberCombo.reset()
                for j, token in enumerate(tokens):
                    if self.numberCombo.broken(j): self.addNumber(self.numberCombo.flattened)
                    if self.nameCombo.broken(j): self.addName(self.nameCombo.flattened)
                    self.registerMessage( u"-> token[%d]: %s" % (j, token))
                    if len(token) == 1 and SanitationUtils.stringContainsDisallowedPunctuation(token):
                        continue
                    self.parseToken(j, token)

                    # break
                if self.numberCombo:
                    self.registerMessage( "CONGRUENT NUMBERS AT END OF CYCLE: %s" % SanitationUtils.coerceUnicode( self.numberCombo))
                    self.addNumber(self.numberCombo.flattened)
                if self.nameCombo:
                    self.registerMessage( "CONGRUENT NAMES AT END OF CYCLE:  %s" % SanitationUtils.coerceUnicode(self.nameCombo))
                    self.addName(self.nameCombo.flattened)
                # self.registerMessage( "FINISHED CYCLE, NAMES: ", self.properties['names'])
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
                if not self.properties['thoroughfares'] \
                and not self.properties['weak_thoroughfares']:
                    ambiguous_token = self.properties['ambiguous_tokens'].pop()
                    self.addWeakThoroughfare((ambiguous_token, None, None))
                else:
                    ambiguous_token = self.properties['ambiguous_tokens']
                    self.enforceStrict('There are some ambiguous tokens: %s' %
                                       SanitationUtils.coerceUnicode(self.properties['ambiguous_tokens']))
                    break


            # if self.properties['thoroughfares'] and self.properties['weak_thoroughfares'] and not self.properties['buildings']
            #     self.enforceStrict('multiple thoroughfares and no building')
            all_thoroughfares = self.properties['thoroughfares'] + self.properties['weak_thoroughfares']
            if len(all_thoroughfares) > 1:
                self.enforceStrict('multiple thoroughfares: %s' %
                    SanitationUtils.coerceUnicode(all_thoroughfares)
                )

            if self.properties['unknowns']:
                self.invalidate("There are some unknown tokens: %s" % repr( " | ".join( self.properties['unknowns'])))

            #if any unknowns match number, then add them as a blank subunit

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

        if building and weak_thoroughfare:
            self.registerMessage( "BUILDING AND WEAK THOROUGHFARE")
            self.addName(token)
            return
            # self.invalidate("Ambiguous thoroughfare or building (multiple buildings detected): %s" % repr(token))
        if weak_thoroughfare:
            self.addWeakThoroughfare(weak_thoroughfare)
            return
        if building and not self.properties['buildings']:
            self.addBuilding(building)
            return
        #ignore if unknown is city or state
        # if token in self.wordsToRemove:
        #     self.properties['ignores'] += [token]
        #     self.registerMessage( "IGNORING WORD ", token)
        #     return

        # state = AddressUtils.getState(token)
        # if(state and not self.properties['state']):
        #     #this might be the state but can't rule it out being something else
        #     self.properties['possible_states'] = list(
        #         set( self.properties['possible_states'] ) + set([token])
        #     )
        #     self.registerMessage( "IGNORING STATE ", state)
        #     return


        if name:
            self.registerMessage( "FOUND NAME: %s"  % SanitationUtils.coerceUnicode(name))
            self.nameCombo.add(tokenIndex, name)
            return

        if number:
            self.registerMessage( "FOUND NUMBER: %s"  % SanitationUtils.coerceUnicode(number))
            self.numberCombo.add(tokenIndex, number)
            return

        self.registerMessage( "UNKNOWN TOKEN %s"  % SanitationUtils.coerceUnicode(token))
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
                self.registerMessage(SanitationUtils.coerceUnicode(e))
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
        self.registerMessage( "PROCESSING NAME %s"  % SanitationUtils.coerceUnicode(name))
        names = filter(None, NameUtils.getSingleNames(name))
        self.registerMessage( "SINGLE NAMES %s"  % SanitationUtils.coerceUnicode(names))
        weak_thoroughfare = AddressUtils.getWeakThoroughfare(name)
        building = AddressUtils.getBuilding(name)
        if building and weak_thoroughfare:
            self.registerMessage("BUILDING %s" % SanitationUtils.coerceUnicode(building))
            self.registerMessage("WEAK THOROUGHFARE:  %s" % SanitationUtils.coerceUnicode(weak_thoroughfare))
            if building[1] and weak_thoroughfare[1]:
                thoroughfare_type_len, building_type_len = map(
                    lambda x: len(x[1]),
                    [weak_thoroughfare, building]
                )
                if thoroughfare_type_len > building_type_len:
                    self.addWeakThoroughfare(weak_thoroughfare)
                    return
                elif building_type_len > thoroughfare_type_len:
                    self.addBuilding(building)
                    return
                else:
                    self.registerWarning('EQUALLY VALID THOROUGHFARE AND BUILDING')

        if not (self.properties['thoroughfares'] + self.properties['weak_thoroughfares']) and \
        (self.properties['numbers'] or self.properties['coerced_subunits']):
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
            if building:
                self.addBuilding(building)
            else:
                self.coerceBuilding(name)
        elif weak_thoroughfare and not (self.properties['thoroughfares'] + self.properties['weak_thoroughfares']):
            self.addWeakThoroughfare(weak_thoroughfare)
        elif building and not self.properties['buildings']:
            self.addBuilding(building)
        # elif weak_thoroughfare and not building:
        #     self.addWeakThoroughfare(weak_thoroughfare)
        elif name in self.wordsToRemove:
            self.properties['ignores'] += [name]
        elif not (self.properties['thoroughfares'] + self.properties['weak_thoroughfares']):
            self.properties['names'] += [name]
        else:
            self.properties['ambiguous_tokens'] += [name]

    def addSubunit(self, subunit):
        subunit_type, subunit_number = subunit
        if subunit_type in ['SHOP', 'SUITE', 'KIOSK', 'SHRM', 'STORE']:
            self.properties['isShop'] = True
        if subunit_number[-1] == '/':
            while self.properties['incomplete_subunits']:
                self.completeSubunit(self.properties['incomplete_subunits'].pop())
            self.registerMessage( "ADDING INCOMPLETE SUBUNIT:  %s" % SanitationUtils.coerceUnicode(subunit))
            self.properties['incomplete_subunits'] += [subunit]
        else:
            self.registerMessage( "ADDING SUBUNIT:  %s" % SanitationUtils.coerceUnicode(subunit))
            self.properties['subunits'] += [subunit]

    def addWeakSubunit(self, weak_subunit):
        subunit_type, subunit_number = weak_subunit
        self.enforceStrict("Unknown subunit type: %s" % subunit_type)
        self.addSubunit(weak_subunit)

    def coerceSubunit(self, number):
        subunit = (None, number)
        self.registerMessage("COERCED SUBUNIT: %s" % SanitationUtils.coerceUnicode(subunit))
        self.properties['coerced_subunits'] += [subunit]

    def completeSubunit(self, incomplete_subunit):
        subunit_type, subunit_number = incomplete_subunit
        if subunit_number[-1] == '/':
            subunit_number = subunit_number[:-1]
        complete_subunit = subunit_type, subunit_number
        self.addSubunit( complete_subunit )

    def addBuilding(self, building):
        all_thoroughfares = self.properties['thoroughfares'] + self.properties['weak_thoroughfares']
        if all_thoroughfares:
            self.enforceStrict("Building (%s) should not come after thoroughfare (%s)" % (
                SanitationUtils.coerceUnicode(building),
                SanitationUtils.coerceUnicode(all_thoroughfares[0])
            ))
        self.registerMessage( "ADDING BUILDING:  %s" % SanitationUtils.coerceUnicode(building))
        self.properties['buildings'] += [building]

    def coerceBuilding(self, token):
        building = AddressUtils.getBuilding(token)
        if not building:
            building = (token, None)
        self.registerMessage("COERCED BUILDING %s" % SanitationUtils.coerceUnicode(building))
        self.addBuilding(building)

    def addThoroughfare(self, thoroughfare):
        self.registerMessage( "ADDING THOROUGHFARE %s" % SanitationUtils.coerceUnicode(thoroughfare))
        thoroughfare_number, thoroughfare_name, thoroughfare_type, thoroughfare_suffix = thoroughfare
        self.assertValidThoroughfareType(thoroughfare_name, thoroughfare_type)
        # if legit thoroughfare is being added, remove weaklings before adding
        while self.properties['weak_thoroughfares']:
            weak_thoroughfare = self.properties['weak_thoroughfares'].pop()
            token = " ".join(filter(None, weak_thoroughfare))
            self.coerceBuilding(token)
        self.properties['thoroughfares'] += [thoroughfare]

    def coerceThoroughfare( self, number, weak_thoroughfare):
        self.registerMessage( "COERCING THOROUGHFARE %s %s"  % (
            SanitationUtils.coerceUnicode(number),
            SanitationUtils.coerceUnicode(weak_thoroughfare),
        ))
        thoroughfare_name, thoroughfare_type, thoroughfare_suffix = weak_thoroughfare
        thoroughfare = ( number, thoroughfare_name, thoroughfare_type, thoroughfare_suffix )
        self.registerMessage( "COERCED THOROUGHFARE: %s" % SanitationUtils.coerceUnicode(thoroughfare))
        self.addThoroughfare(thoroughfare)

    def addWeakThoroughfare( self, weak_thoroughfare):
        self.registerMessage( "ADDING WEAK THOROUGHFARE %s"  % SanitationUtils.coerceUnicode(weak_thoroughfare))
        if \
          True or\
          not (self.properties['thoroughfares'] or self.properties['weak_thoroughfares']):
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
            self.registerMessage( "ADDING WEAK THOROUGHFARE:  %s" % SanitationUtils.coerceUnicode(weak_thoroughfare))
            thoroughfare_name, thoroughfare_type, thoroughfare_suffix = weak_thoroughfare
            self.assertValidThoroughfareType(thoroughfare_name, thoroughfare_type)
            self.properties['weak_thoroughfares'] += [weak_thoroughfare]
        else:
            token = " ".join(filter(None, weak_thoroughfare))
            self.coerceBuilding(token)

    def addFloor(self, floor):
        self.registerMessage( "ADDING FLOOR:  %s" % SanitationUtils.coerceUnicode(floor))
        self.properties['floors'] += [floor]


    def addDelivery(self, delivery):
        self.registerMessage( "ADDING DELIVERY:  %s" % SanitationUtils.coerceUnicode(delivery))
        self.properties['deliveries'] += [delivery]

    def assertValidThoroughfareType(self, thoroughfare_name, thoroughfare_type):
        if thoroughfare_type:
            try:
                assert AddressUtils.getThoroughfareType(thoroughfare_type), "Unknown thoroughfares type: %s" % thoroughfare_type
            except Exception, e:
                self.enforceStrict(SanitationUtils.coerceUnicode(e))
        else:
            self.enforceStrict("No thoroughfare type: " + thoroughfare_name)

    @property
    def subunits(self):
        if(self.properties.get('subunits') or self.properties.get('coerced_subunits')):
            return ", ".join(
                [" ".join(filter(None, subunit)) for subunit in (self.properties['subunits'] + self.properties['coerced_subunits'])]
            )

    @property
    def floors(self):
        if self.properties.get('floors'):
            return ", ".join(
                [" ".join(filter(None,floor)) for floor in self.properties['floors']]
            )

    @property
    def buildings(self):
        if self.properties.get('buildings'):
            return ", ".join(
                [" ".join(filter(None,building)) for building in self.properties['buildings']]
            )

    @property
    def deliveries(self):
        if self.properties.get('deliveries'):
            return ", ".join(
                [" ".join(filter(None, delivery)) for delivery in self.properties['deliveries']]
            )

    @property
    def thoroughfares(self):
        if self.properties.get('thoroughfares') or self.properties.get('weak_thoroughfares'):
            return ", ".join(
                [" ".join(filter(None, thoroughfares)) for thoroughfares in \
                    self.properties['thoroughfares'] + self.properties['weak_thoroughfares']]
            )

    @property
    def end_names(self):
        if self.properties.get('end_names'):
            return ", ".join(
                self.properties.get('end_names')
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
        if(self.properties_override):
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
        if(self.properties_override):
            elements = [
                self.thoroughfares,
                self.end_names
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
        prefix = self.getPrefix() if self.debug else ""
        delimeter = "; "
        if tablefmt == "html":
            delimeter = "<br/>"
        return SanitationUtils.coerceUnicode( prefix + delimeter.join(filter(None,[
            self.line1,
            self.line2,
            self.line3,
            (("|UNKN:" + " ".join(self.properties['unknowns'])) \
                if self.debug and self.properties['unknowns'] else "")
        ])) )

    def __str__(self, tablefmt=None):
        return SanitationUtils.coerceBytes(self.__unicode__(tablefmt))

class ContactName(ContactObject):
    fieldGroupType = "NAME"
    equality_keys = ['first_name', 'middle_name', 'family_name']
    similarity_keys = ['first_name', 'middle_name', 'family_name', 'contact', 'company']
    mandatory_keys = ['first_name', 'family_name', 'contact', 'company']
    key_mappings = {
        'first_name':['First Name'],
        'family_name':['Surname'],
        'middle_name':['Middle Name'],
        'name_prefix':['Name Prefix'],
        'name_suffix':['Name Suffix'],
        'name_notes':['Memo'],
        'company':['Company'],
        'contact':['Contact']
    }

    def __init__(self, schema=None, **kwargs):
        super(ContactName, self).__init__(schema, **kwargs)
        self.debug = DEBUG_NAME
        if self.performPost:
            # self.valid = False
            self.problematic = False
            self.properties['titles'] = []
            self.properties['names'] = []
            self.properties['suffixes'] = []
            self.properties['positions'] = []
            self.properties['notes'] = []
            self.properties['emails'] = []
            self.properties['family_names'] = []
            self.properties['middle_names'] = []
            self.properties['first_names'] = []
            self.properties['single_names'] = []
            self.strict = STRICT_NAME
            # self.kwargs = kwargs
            self.processKwargs()

    def processKwargs(self):
        if not self.empty:
            if self.kwargs.get('country'):
                countrySanitized = AddressUtils.sanitizeState(self.kwargs['country'])
                countryIdentified = AddressUtils.identifyCountry(countrySanitized)
                # if self.debug: print "countrySanitized", countrySanitized, "countryIdentified", countryIdentified
                if countrySanitized != countryIdentified:
                    self.properties['country'] = countryIdentified
                else:
                    self.properties['country'] = countrySanitized
                # self.wordsToRemove.append(countrySanitized)

            if self.kwargs.get('state'):
                stateSanitized = AddressUtils.sanitizeState(self.kwargs['state'])
                self.wordsToRemove.append(stateSanitized)
                stateIdentified = AddressUtils.identifyState(stateSanitized)
                if stateIdentified != stateSanitized:
                    self.wordsToRemove.append(stateIdentified)
                    self.properties['state'] = stateIdentified
                else:
                    self.properties['state'] = stateSanitized


            if self.kwargs.get('city'):
                citySanitized = AddressUtils.sanitizeState(self.kwargs['city'])
                self.properties['city'] = citySanitized

            if self.kwargs.get('company'):
                companySanitized = SanitationUtils.normalizeVal(self.kwargs['company'])
                company_tokens = NameUtils.tokenizeName(companySanitized)
                company_has_notes = False
                for token in company_tokens:
                    note = NameUtils.getNote(token)
                    if note:
                        company_has_notes = True
                        # self.enforceStrict("Company name contains notes: " + self.getNoteNoParanthesis(note))
                if not company_has_notes:
                    self.wordsToRemove.append(companySanitized)
                    self.coerceOrganization(self.kwargs.get('company'))

            full_name_contact = SanitationUtils.normalizeVal(self.kwargs.get('contact'))
            full_name_components = SanitationUtils.normalizeVal(' '.join(filter(None, map(
                lambda k: self.kwargs.get(k),
                ['name_prefix', 'first_name', 'middle_name', 'family_name', 'name_suffix']
            ))))

            if full_name_contact and full_name_components:
                no_punctuation_contact, no_punctuation_components = map(SanitationUtils.similarNoPunctuationComparison, [full_name_contact, full_name_components])
                if no_punctuation_contact == no_punctuation_components:
                    # The names are effectively the same, can drop one
                    full_name_components = None
                else:
                    reverse_name_components = SanitationUtils.similarNoPunctuationComparison(" ".join(filter(None,[self.kwargs.get('family_name'), self.kwargs.get('first_name'), self.kwargs.get('middle_name')])))
                    # print reverse_name_components, no_punctuation_contact
                    if reverse_name_components == no_punctuation_contact:
                        self.registerMessage("DETECTED REVERSE NAME:  %s"  % SanitationUtils.coerceUnicode(full_name_contact))
                        # self.enforceStrict("Ambiguous if format is family_name, first_name middle_name or just stray comma")
                        full_name_contact = None

            full_names = listUtils.filterUniqueTrue(map(SanitationUtils.normalizeVal, [full_name_contact, full_name_components]))

            if len(full_names) > 1:
                self.invalidate("Unable to determine which name is correct: %s" %
                                SanitationUtils.coerceUnicode(full_names))

            for i, full_name in enumerate(full_names):
                self.registerMessage( "ANALYSING NAME %d: %s" % (i, repr(full_name)))
                tokens = NameUtils.tokenizeName(full_name)
                self.registerMessage( "TOKENS: %s" % repr(tokens))
                self.nameCombo.reset()
                # SanitationUtils.safePrint(u"TOKENS {} FOR {} ARE {}".format(len(tokens), full_name, tokens))
                for j, token in enumerate(tokens):
                    self.parseToken(j, token)

                if self.nameCombo:
                    self.registerMessage( "CONGRUENT NAMES AT END OF CYCLE: %s" % self.nameCombo)
                    self.addName(self.nameCombo.flattened)


            while self.properties['names']:
                name = self.properties['names'].pop(0)
                single_names = NameUtils.getSingleNames(name)
                for single_name in single_names:
                    self.properties['single_names'] += [single_name]
                    self.registerMessage("adding single name: %s" % single_name)

            while self.properties['single_names']:
                if len(self.properties['single_names']) > 1 \
                and not self.properties['family_names']:
                    end_name = self.properties['single_names'].pop(-1)
                    self.properties['family_names'] += [end_name]
                    continue
                if len(self.properties['single_names']) > 1 \
                and not self.properties['middle_names']:
                    end_name = self.properties['single_names'].pop(-1)
                    self.properties['middle_names'] += [end_name]
                    continue
                else:
                    self.properties['first_names'] += [self.properties['single_names'].pop(0)]

            if len(self.properties['family_names'] ) > 1:
                self.enforceStrict("THERE ARE MULTIPLE FAMILY NAMES: %s" %
                                   SanitationUtils.coerceBytes(' / '.join(self.properties['family_names'])))
            if len(self.properties['middle_names'] ) > 1:
                self.enforceStrict("THERE ARE MULTIPLE MIDDLE NAMES: %s" %
                                   SanitationUtils.coerceBytes(' / '.join(self.properties['middle_names'])))
            if len(self.properties['first_names'] ) > 2:
                self.enforceStrict("THERE ARE MULTIPLE FIRST NAMES: %s" %
                                   SanitationUtils.coerceBytes(' / '.join(self.properties['first_names'])))

            if len(self.properties['family_names'] + self.properties['middle_names'] + self.properties['first_names']) == 0:
                self.empty = True

            if len(self.properties['titles'] ) > 1:
                self.enforceStrict("THERE ARE MULTIPLE TITLES: " + SanitationUtils.coerceBytes(' / '.join(self.properties['titles'])))

            if len(self.properties['notes'] ) > 1:
                self.enforceStrict("THERE ARE MULTIPLE NOTES: " + SanitationUtils.coerceBytes(" / ".join(map(self.getNoteNoParanthesis, self.properties.get('notes', []))) ))

            if len(self.properties['positions'] ) > 1:
                self.enforceStrict("THERE ARE MULTIPLE POSITIONS: " + SanitationUtils.coerceBytes(' / '.join(self.properties['positions'])))

            if self.properties['unknowns']:
                self.invalidate("There are some unknown tokens: %s" % SanitationUtils.coerceBytes(' / '.join(self.properties['unknowns'])))

    def parseToken(self, tokenIndex, token):
        if self.nameCombo.broken(tokenIndex): self.addName(self.nameCombo.flattened)

        title = NameUtils.getTitle(token)
        if title:
            self.registerMessage( "FOUND TITLE: %s"  % SanitationUtils.coerceUnicode(title))
            if title not in self.properties['titles']:
                self.properties['titles'] += [title]
            return

        position = NameUtils.getPosition(token)
        if position:
            self.registerMessage( "FOUND POSITION: %s"  % SanitationUtils.coerceUnicode(position))
            if position not in self.properties['positions']:
                self.properties['positions'] += [position]
            return

        suffix = NameUtils.getNameSuffix(token)
        if suffix:
            self.registerMessage( "FOUND NAME SUFFIX: %s"  % SanitationUtils.coerceUnicode(suffix))
            if suffix not in self.properties['suffixes']:
                self.properties['suffixes'] += [suffix]
            return

        email = NameUtils.getEmail(token)
        if email:
            self.registerMessage("FOUND EMAIL: %s"  % SanitationUtils.coerceUnicode(email))
            if email not in self.properties['emails']:
                self.properties['emails'] += [email]
            return

        note = NameUtils.getNote(token)
        if note:
            self.registerMessage( "FOUND NOTE: %s" % self.getNoteNoParanthesis( note))
            if note not in self.properties['notes']:
                self.properties['notes'] += [note]
            return

        careof = NameUtils.getCareOf(token)
        if careof:
            self.registerMessage( "FOUND CAREOF: %s"  % SanitationUtils.coerceUnicode(careof))
            if careof not in self.properties['careof_names']:
                self.properties['careof_names'] += [careof]
            return

        organization = NameUtils.getOrganization(token)
        if organization:
            self.registerMessage( "FOUND ORGANIZATION: %s"  % SanitationUtils.coerceUnicode(organization))
            if organization not in self.properties['organization_names']:
                self.properties['organization_names'] += [organization]
            return

        family_name = NameUtils.getFamilyName(token)
        single_name = NameUtils.getSingleName(token)
        if family_name and single_name:
            self.registerMessage( "FOUND FAMILY AND NAME: '%s' | '%s'"  % (
                SanitationUtils.coerceUnicode(family_name),
                SanitationUtils.coerceUnicode(single_name)))
        if family_name:
            if not single_name or (len(family_name) > len(single_name)):
                self.registerMessage( "FOUND FAMILY NAME: %s"  % SanitationUtils.coerceUnicode(family_name))
                self.properties['family_names'] += [family_name]
                return

        multiName = NameUtils.getMultiName(token)

        if multiName:
            self.registerMessage( "FOUND NAME: %s"  % SanitationUtils.coerceUnicode(multiName))
            self.nameCombo.add(tokenIndex, multiName)
            return

        if SanitationUtils.stringContainsDisallowedPunctuation(token) and len(token) == 1:
            return

        self.properties['unknowns'] += [token]
        self.invalidate("UNKNOWN TOKEN: " + repr(token))

    def addName(self, name):
        if name in self.wordsToRemove:
            self.properties['ignores'] += [name]
            self.registerMessage( "IGNORING WORD: %s"  % SanitationUtils.coerceUnicode(name))
            return
        if name and name not in self.properties['names']:
            self.registerMessage( "ADDING NAME: %s"  % SanitationUtils.coerceUnicode(name))
            self.properties['names'] += [name]

    def getNoteNoParanthesis(self, note_tuple):
        note_open_paren, names_before_note, note, names_after_note, note_close_paren = note_tuple
        return " ".join(filter(None, [names_before_note, note, names_after_note]))


    # @property
    # def first_name(self):
    #     if self.valid:
    #         if len(self.properties.get('names', [])) > 0 :
    #             return self.properties.get('names')[0]
    #         else:
    #             return ""
    #     else :
    #         return self.kwargs.get('first_name')

    first_name = descriptorUtils.kwargAliasProperty(
        'first_name',
        lambda self: \
            " ".join( filter(None, self.properties.get('first_names', []) ))
    )

    # @property
    # def family_name(self):
    #     if self.valid:
    #         if len(self.properties.get('family_names', [])) > 1:
    #             return self.properties.get('family_names')[-1]
    #         elif len(self.properties.get('names', [])) > 1:
    #             return self.properties.get('names')[-1]
    #         else:
    #             return ""
    #     else:
    #         return self.kwargs.get('family_name')

    family_name = descriptorUtils.kwargAliasProperty(
        'family_name',
        lambda self: \
            " ".join( filter(None, self.properties.get('family_names', []) ))
    )

    # @property
    # def middle_name(self):
    #     if self.valid:
    #         if len(self.properties.get('names', [])) > 2 :
    #             return " ".join(self.properties.get('names')[1:-1])
    #         else:
    #             return ""
    #     else :
    #         return self.kwargs.get('middle_name')

    middle_name = descriptorUtils.kwargAliasProperty(
        'middle_name',
        lambda self: \
            " ".join( filter(None, self.properties.get('middle_names', []) ))
    )

    # @property
    # def name_prefix(self):
    #     if self.valid:
    #         if len(self.properties.get('titles', [])) > 0:
    #             return " ".join(self.properties.get('titles'))
    #         else:
    #             return ""
    #     else:
    #         return self.kwargs.get('name_prefix')

    name_prefix = descriptorUtils.kwargAliasProperty(
        'name_prefix',
        lambda self: " ".join(filter(None,self.properties.get('titles', [])))
    )

    # @property
    # def name_suffix(self):
    #     if self.valid:
    #         positions_suffixes = self.properties.get('positions', []) + self.properties.get('suffixes', [])
    #         if len(positions_suffixes) > 0:
    #             return " ".join(positions_suffixes)
    #         else:
    #             return ""
    #     else:
    #         return self.kwargs.get('name_suffix')

    name_suffix = descriptorUtils.kwargAliasProperty(
        'name_suffix',
        lambda self: " ".join(filter(None,
            self.properties.get('positions', []) + self.properties.get('suffixes', [])
        ))
    )

    # @property
    # def contact(self):
    #     if self.valid:
    #         return " ".join(filter(None,[
    #             self.name_prefix,
    #             self.first_name,
    #             self.middle_name,
    #             self.family_name,
    #             self.name_suffix
    #         ]))
    #     else:
    #         return self.kwargs.get('contact')

    contact = descriptorUtils.kwargAliasProperty(
        'contact',
        lambda self: " ".join(filter(None,[
            self.name_prefix,
            self.first_name,
            self.middle_name,
            self.family_name,
            self.name_suffix
        ]))
    )


    @property
    def name_notes(self):
        if self.valid:
            return ', '.join(map(self.getNoteNoParanthesis, self.properties.get('notes', []) ))
        else:
            return self.kwargs.get('name_notes')


    def __unicode__(self, tablefmt=None):
        prefix = self.getPrefix() if self.debug else ""
        delimeter = " "
        return SanitationUtils.coerceUnicode( prefix + delimeter.join(filter(None,[
            (("PREF: "+ self.name_prefix) if self.debug and self.name_prefix else self.name_prefix),
            (("FIRST: " + self.first_name) if self.debug and self.first_name else self.first_name),
            (("MID: " + self.middle_name) if self.debug and self.middle_name else self.middle_name),
            (("FAM: " + self.family_name) if self.debug and self.family_name else self.family_name),
            (("SUFF: " + self.name_suffix) if self.debug and self.name_suffix else self.name_suffix),
            (("NOTES: (%s)" % self.name_notes) if self.debug and self.name_notes else "(%s)" % self.name_notes if self.name_notes else None),
            (("|UNKN:" + " ".join(self.properties['unknowns'])) \
                if self.debug and self.properties.get('unknowns') else "")
        ])))

    def __str__(self, tablefmt = None):
        return SanitationUtils.coerceBytes(self.__unicode__(tablefmt))


def testcontactNameEquality():
    M = ContactName(
        first_name= 'JESSICA',
        family_name= 'TOLHURST'
    )

    N = ContactName(
        first_name= 'JESSICA',
        family_name= 'ASDASD'
    )

    assert M is not N
    assert M != N
    assert not (M == N)
    assert not M.similar(N)

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
    name = ContactName(
        contact = 'EMILY O\'CALLAGHAN'
    )

def testRefresh():
    contact = ContactName(
        contact = "JESSICA (THITIRAT) PHUSOMSAI",
        first_name = "JESSICA",
        family_name = "(THITIRAT) PHUSOMSAI"
    )

    print contact.contact
    print contact['First Name']
    contact['First Name'] = 'DERWENT'
    contact['Contact'] = 'DERWENT (THITIRAT) PHUSOMSAI'
    print contact.contact


class ContactPhones(FieldGroup):
    fieldGroupType = "PHONES"
    equality_keys = ['tel_number', 'mob_number']
    similarity_keys = equality_keys[:]
    key_mappings = {
        'mob_number': ['Mobile Phone'],
        'tel_number': ['Phone'],
        'fax_number': ['Fax'],
        'mob_pref'  : ['Mobile Phone Preferred'],
        'tel_pref'  : ['Phone Preferred'],
    }

    #todo: test if pref number then number exist

    mob_number = descriptorUtils.kwargAliasProperty(
        'mob_number',
        lambda self: self.properties.get('mob_number')
    )

    tel_number = descriptorUtils.kwargAliasProperty(
        'tel_number',
        lambda self: self.properties.get('tel_number')
    )

    fax_number = descriptorUtils.kwargAliasProperty(
        'fax_number',
        lambda self: self.properties.get('fax_number')
    )

    mob_pref = descriptorUtils.kwargAliasProperty(
        'mob_pref',
        lambda self: self.properties.get('mob_pref')
    )

    tel_pref = descriptorUtils.kwargAliasProperty(
        'tel_pref',
        lambda self: self.properties.get('tel_pref')
    )

    def __unicode__(self, tablefmt=None):
        prefix = self.getPrefix() if self.debug else ""
        delimeter = "; "
        tel_line = (("TEL: "+ self.tel_number) if self.debug and self.tel_number else self.tel_number)
        if self.tel_pref and tel_line:
            tel_line += ' PREF'
        mob_line = (("MOB: " + self.mob_number) if self.debug and self.mob_number else self.mob_number)
        if mob_line and self.mob_pref:
            mob_line += ' PREF'
        fax_line = (("FAX: " + self.fax_number) if self.debug and self.fax_number else self.fax_number)
        return SanitationUtils.coerceUnicode( prefix + delimeter.join(filter(None,[
            tel_line,
            mob_line,
            fax_line,
        ])))

    def __str__(self, tablefmt = None):
        return SanitationUtils.coerceBytes(self.__unicode__(tablefmt))

def testContactNumber():
    numbers = ContactPhones(
        mob_number = '0416160912',
        tel_number = '93848512',
        fax_number = '0892428032',
        mob_pref = True
    )

    print numbers

# TODO: make Social media class

class SocialMediaFields(FieldGroup):
    fieldGroupType = "SOCIALMEDIA"
    equality_keys = ['facebook', 'twitter', 'instagram', 'gplus']
    similarity_keys = equality_keys[:]
    key_mappings = {
        'facebook': ['Facebook Username'],
        'twitter': ['Twitter Username'],
        'gplus': ['GooglePlus Username'],
        'instagram': ['Instagram Username']
    }

    #todo: test if pref number then number exist

    facebook = descriptorUtils.kwargAliasProperty(
        'facebook',
        lambda self: self.properties.get('facebook')
    )

    twitter = descriptorUtils.kwargAliasProperty(
        'twitter',
        lambda self: self.properties.get('twitter')
    )

    gplus = descriptorUtils.kwargAliasProperty(
        'gplus',
        lambda self: self.properties.get('gplus')
    )

    instagram = descriptorUtils.kwargAliasProperty(
        'instagram',
        lambda self: self.properties.get('instagram')
    )

    def __unicode__(self, tablefmt=None):
        prefix = self.getPrefix() if self.debug else ""
        delimeter = "; "
        return SanitationUtils.coerceUnicode( prefix + delimeter.join(filter(None,[
            self.facebook,
            self.twitter,
            self.gplus,
            self.instagram,
        ])))

    def __str__(self, tablefmt = None):
        return SanitationUtils.coerceBytes(self.__unicode__(tablefmt))


def testSocialMediaGroup():
    sm = SocialMediaFields(
        facebook = 'facebook',
        twitter = '@twitter',
        gplus = '+gplus',
        instagram = '@insta'
    )

    print sm

if __name__ == '__main__':
    FieldGroup.performPost = True
    FieldGroup.DEBUG_WARN = True
    FieldGroup.DEBUG_MESSAGE = True

    address = ContactAddress(
        line1 = "SHOP G33Q, BAYSIDE SHOPPING CENTRE"
    )

    # self.assertTrue(address.valid)

    # testContactAddress()
    # testcontactNameEquality()
    # testContactNumber()
    # testSocialMediaGroup()
    # testContactName()
    # testRefresh()
