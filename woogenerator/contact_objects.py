"""
Container objects for storing contact data
"""

from __future__ import absolute_import

from collections import OrderedDict
from copy import copy, deepcopy
from pprint import pformat

from tabulate import tabulate

from .utils import (AddressUtils, DescriptorUtils, NameUtils, Registrar,
                    SanitationUtils, SeqUtils)

STRICT_ADDRESS = False
STRICT_ADDRESS = True

STRICT_NAME = False
STRICT_NAME = True


class FieldGroup(Registrar):
    """
    Group a series of interdependent fields together so that they are synced at the same time.
    """

    equality_keys = []
    similarity_keys = []
    mandatory_keys = []
    invincible_keys = []
    key_mappings = {}
    fieldGroupType = 'GRP'
    _supports_tablefmt = True
    perform_post = False
    enforce_mandatory_keys = True
    reprocess_kwargs = False
    similar_all_keys = False

    def __init__(self, schema=None, **kwargs):
        super(FieldGroup, self).__init__()
        self.schema = schema
        self.debug = getattr(self, 'debug', self.DEBUG_CONTACT)
        self.strict = getattr(self, 'strict', None)
        self.kwargs = kwargs
        if self.debug:
            self.register_message("kwargs: %s" % pformat(self.kwargs))
        self.valid = True
        self.problematic = False
        self.reason = ""
        self.properties = OrderedDict()
        if self.perform_post:
            self.process_kwargs()

    @property
    def empty(self):
        if self.enforce_mandatory_keys and self.mandatory_keys:
            empty_mandatory_keys = [
                key for key in self.mandatory_keys \
                if not self.kwargs.get(key)
            ]
            return any(empty_mandatory_keys)
        else:
            return not any(self.kwargs.values())


    def process_kwargs(self):
        self.init_properties()
        self.perform_post = True

    def init_properties(self):
        pass

    def reflect(self):
        reflected = copy(self)
        reflected.process_kwargs()
        return reflected

    def get_mapped_attr(self, key):
        for attr, keys in self.key_mappings.items():
            if key in keys + [attr]:
                return attr

    def update_from(self, other, cols=None):
        assert isinstance(other, type(self))
        if cols is None:
            cols = other.key_mappings.keys()
        for col in cols:
            attr = self.get_mapped_attr(col)
            val = copy(other[attr])
            self.kwargs[attr] = val
        if self.reprocess_kwargs:
            self.process_kwargs()

    @property
    def properties_override(self):
        if self.perform_post and self.valid:
            return True

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            for key in self.equality_keys:
                if getattr(self, key) != getattr(other, key):
                    return False
            return True
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __getitem__(self, key):
        if Registrar.DEBUG_CONTACT:
            Registrar.register_message(
                "getting key %s" % (key)
            )
        attr = self.get_mapped_attr(key)
        if attr:
            if self.properties_override:
                return self.properties.get(attr)
            return self.kwargs.get(attr)
        # for attr, keys in self.key_mappings.items():
        #     if key in keys or key == attr:
        #         if self.properties_override:
        #             return self.properties[attr]
        #             # return getattr(self, attr)
        #         return self.kwargs.get(attr)

    def __setitem__(self, key, val):
        if Registrar.DEBUG_CONTACT:
            Registrar.register_message(
                "setting key %s to val %s " % (key, val)
            )
        attr = self.get_mapped_attr(key)
        if attr:
            if self.properties_override:
                self.properties[attr] = val
                return
            self.kwargs[attr] = val
            return
        # for attr, keys in self.key_mappings.items():
        #     if key in keys or key == attr:
        #         if self.properties_override:
        #             self.properties[attr] = val
        #             # return setattr(self, attr, val)
        #         self.kwargs[attr] = val
        #         return

    def __contains__(self, key):
        if Registrar.DEBUG_CONTACT:
            Registrar.register_message(
                "checking key %s contained" % (key)
            )
        attr = self.get_mapped_attr(key)
        return bool(attr)
        # return member in [
        #     item for key, value in self.key_mappings.items()
        #     for item in [key] + value
        # ]


    def __copy__(self):
        # print "calling copy on ", self
        response = self.__class__(self.schema, **copy(self.kwargs))
        # print " -> response", response
        return response

    def __deepcopy__(self, memodict=None):
        # print ("calling deepcopy on ", self)
        # print ("-> kwargs ", deepcopy(self.kwargs, memodict))
        response = self.__class__(self.schema, **deepcopy(self.kwargs, memodict))
        # print (" -> response", response, response.kwargs)
        return response

    def __unicode__(self, tablefmt=None):
        raise NotImplementedError()

    def __str__(self, tablefmt=None):
        return SanitationUtils.coerce_bytes(self.__unicode__(tablefmt))

    def get_prefix(self):
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

    def invalidate(self, reason=None):
        self.valid = False
        if not self.reason:
            self.reason = reason
        self.register_error(
            "INVALID: %s" % SanitationUtils.coerce_unicode(reason))

    def enforce_strict(self, reason=None):
        self.problematic = True
        if self.strict:
            self.invalidate(reason)
            self.register_message(
                "PROBLEMATIC: %s" % SanitationUtils.coerce_unicode(reason))

    def to_dict(self, tablefmt=None):
        if not tablefmt:
            tablefmt = 'simple'
        if tablefmt == 'html':
            sanitizer = SanitationUtils.sanitize_for_xml
        else:
            sanitizer = SanitationUtils.sanitize_for_table
        if self.empty:
            reason = self.fieldGroupType + " EMPTY"
        else:
            reason = self.reason

        printable_kwargs = {}
        if self.kwargs:
            for key, arg in self.kwargs.items():
                if arg:
                    printable_kwargs[key] = [sanitizer(arg)]

        table = OrderedDict()

        table[self.fieldGroupType] = [
            sanitizer(self.__unicode__(tablefmt=tablefmt))
        ]

        if reason:
            table['REASON'] = [sanitizer(reason)]

        if printable_kwargs:
            for key, arg in printable_kwargs.items():
                table['KEY:' + key] = arg
        return table

    def tabulate(self, tablefmt=None):
        return tabulate(
            self.to_dict(tablefmt), tablefmt=tablefmt, headers='keys')

    def normalize_val(self, key, val):
        if key:
            pass
        return SanitationUtils.normalize_val(val)

    def similar(self, other):
        if not isinstance(other, FieldGroup):
            return False
        self_empty = self.empty
        other_empty = other.empty
        if self_empty or other_empty:
            return True if self_empty and other_empty else False
        for key in self.similarity_keys:
            # print "-> LOOKING AT KEY", key
            self_val = getattr(self, key)
            other_val = getattr(other, key)
            if not (self_val or other_val):
                continue
            if (self_val and other_val) or self.similar_all_keys:
                # print "--> self",
                self_normalized = self.normalize_val(key, self_val)
                other_normalized = self.normalize_val(key, other_val)
                if self_normalized != other_normalized:
                    # print "->NOT THE SAME BECAUSE OF", key
                    return False
                else:
                    pass
                    # print "->KEY IS THE SAME", key
        return True
        # print "THEY ARE SIMILAR"
        # todo: this

    def __bool__(self):
        return not self.empty

    __nonzero__ = __bool__


class ContactObject(FieldGroup):
    fieldGroupType = "CONTACTOBJ"

    class Combo(list):
        def __init__(self, *args, **kwargs):
            super(ContactObject.Combo, self).__init__(*args, **kwargs)
            self.last_index = -1

        def reset(self):
            self[:] = []
            self.last_index = -1

        def add(self, index, item):
            self.append(item)
            self.last_index = index

        def broken(self, index):
            return self and index != self.last_index + 1

        @property
        def flattened(self):
            flat = " ".join(self)
            self.reset()
            return flat

    def init_properties(self):
        super(ContactObject, self).init_properties()
        self.properties['ignores'] = []
        self.properties['unknowns'] = []
        self.properties['names'] = []
        self.properties['end_names'] = []
        self.properties['careof_names'] = []
        self.properties['organization_names'] = []
        self.properties['ambiguous_tokens'] = []
        self.properties['name_combo'] = ContactObject.Combo()
        self.properties['remove_words'] = []

    def __copy__(self):
        # print "calling copy on ", self
        response = self.__class__(self.schema, **copy(self.kwargs))
        # print " -> response", response
        return response

    def __deepcopy__(self, memodict=None):
        # print ("calling deepcopy on ", self)
        # print ("-> kwargs ", deepcopy(self.kwargs, memodict))
        response = self.__class__(
            deepcopy(self.schema, memodict), **deepcopy(self.kwargs, memodict))
        # print (" -> response", response, response.kwargs)
        return response

    # def get(self, key, default = None):
    #     for attr, keys in self.key_mappings.items():
    #         if key in keys:
    #             return getattr(self, attr)
    #     return super(ContactObject, self).get(key, default)

    def add_careof(self, careof):
        self.register_message(
            "FOUND CAREOF %s" % SanitationUtils.coerce_unicode(careof))
        if careof not in self.properties['careof_names']:
            self.properties['careof_names'] += [careof]

    def add_organization(self, organization):
        self.register_message("FOUND ORGANIZATION: %s" %
                              SanitationUtils.coerce_unicode(organization))
        if organization not in self.properties['organization_names']:
            self.properties['organization_names'] += [organization]

    def coerce_organization(self, organization_name):
        organization = NameUtils.get_organization(organization_name)
        if not organization:
            organization = (organization_name, None)
        self.add_organization(organization)

    @property
    def careof_names(self):
        if self.properties.get('careof_names'):
            return ", ".join([
                " ".join(filter(None, careof_name))
                for careof_name in self.properties['careof_names']
            ])

    @property
    def organization_names(self):
        if self.properties.get('organization_names'):
            return ", ".join([
                " ".join(filter(None, organization))
                for organization in self.properties['organization_names']
            ])

    company = DescriptorUtils.kwarg_alias_property(
        'company',
        lambda self: ", ".join(
            [" ".join(filter(None, organization))
             for organization in self.properties['organization_names']]
        )
    )

    @property
    def names(self):
        if self.properties.get('names') or self.properties.get('careof_names') \
        or self.properties.get('organization_names'):
            out = ", ".join(
                filter(None, [
                    " ".join(filter(None, names))
                    for names in [[self.careof_names], self.properties[
                        'names'], [self.organization_names]]
                ]))
            return out


class ContactAddress(ContactObject):
    fieldGroupType = "ADDRESS"
    equality_keys = ['line1', 'line2', 'line3']
    similarity_keys = [
        'country', 'state', 'postcode', 'city', 'thoroughfares', 'deliveries',
        'names', 'buildings', 'floors', 'subunits'
    ]
    mandatory_keys = ['line1', 'line2', 'city', 'postcode', 'state']
    key_mappings = {
        'country': ['Country', 'Home Country'],
        'state': ['State', 'Home State'],
        'postcode': ['Postcode', 'Home Postcode'],
        'city': ['City', 'Home City'],
        'line1': ['Address 1', 'Home Address 1'],
        'line2': ['Address 2', 'Home Address 2']
    }

    def __init__(self, schema=None, **kwargs):
        if self.DEBUG_ADDRESS:
            self.register_message("kwargs: %s" % kwargs)
        self.strict = STRICT_ADDRESS
        self.debug = self.DEBUG_ADDRESS
        super(ContactAddress, self).__init__(schema, **kwargs)

    def init_properties(self):
        super(ContactAddress, self).init_properties()
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
        self.properties['unknowns'] = []
        self.properties['number_combo'] = ContactObject.Combo()

    def process_kwargs(self):
        super(ContactAddress, self).process_kwargs()
        if self.empty:
            # if self.debug:
            #     self.register_message("not processing kwargs because empty")
            return
        # if not schema: self.schema = self.__class__.determine_source(**self.kwargs)

        lines = SeqUtils.filter_unique_true([
            SanitationUtils.normalize_val(self.kwargs.get(key, '')) \
            for key in ['line1', 'line2']
        ])

        # lines = SeqUtils.filter_unique_true(map(lambda key: SanitationUtils.normalize_val(
        #     self.kwargs.get(key, '')), ['line1', 'line2']))

        if self.kwargs.get('country', ''):
            country_sanitized = AddressUtils.sanitize_state(
                self.kwargs['country'])
            country_identified = AddressUtils.identify_country(
                country_sanitized)
            # if self.debug: print "country_sanitized", country_sanitized,
            # "country_identified", country_identified
            if country_sanitized != country_identified:
                self.properties['country'] = country_identified
            else:
                self.properties['country'] = country_sanitized
            # self.properties['remove_words'].append(country_sanitized)

        if self.kwargs.get('state', ''):
            state_sanitized = AddressUtils.sanitize_state(self.kwargs['state'])
            self.properties['remove_words'].append(state_sanitized)
            state_identified = AddressUtils.identify_state(state_sanitized)
            if state_identified != state_sanitized:
                self.properties['remove_words'].append(state_identified)
                self.properties['state'] = state_identified
            else:
                self.properties['state'] = state_sanitized

        if self.kwargs.get('city', ''):
            city_sanitized = AddressUtils.sanitize_state(self.kwargs['city'])
            self.properties['city'] = city_sanitized
            # self.properties['remove_words'].append(city_sanitized)

        if self.kwargs.get('postcode'):
            self.properties['postcode'] = self.kwargs.get('postcode')
            if SanitationUtils.string_contains_no_numbers(
                    self.kwargs.get('postcode')):
                self.invalidate("Postcode has no numbers: %s" %
                                repr(self.kwargs.get('postcode')))

        if self.kwargs.get('company'):
            company_sanitized = SanitationUtils.normalize_val(
                self.kwargs['company'])
            company_tokens = NameUtils.tokenize_name(company_sanitized)
            company_has_notes = False
            for token in company_tokens:
                note = NameUtils.get_note(token)
                if note:
                    company_has_notes = True
            if not company_has_notes:
                self.properties['remove_words'].append(company_sanitized)
                self.coerce_organization(self.kwargs.get('company'))

        for i, line in enumerate(lines):
            self.register_message("ANALYSING LINE %d: %s" % (i, repr(line)))
            tokens = AddressUtils.tokenize_address(line)
            self.register_message(u"TOKENS: %s" % repr(tokens))
            self.properties['name_combo'].reset()
            self.properties['number_combo'].reset()
            for j, token in enumerate(tokens):
                if self.properties['number_combo'].broken(j):
                    self.add_number(self.properties['number_combo'].flattened)
                if self.properties['name_combo'].broken(j):
                    self.add_name(self.properties['name_combo'].flattened)
                self.register_message(u"-> token[%d]: %s" % (j, token))
                if len(token) == 1 and SanitationUtils.string_contains_bad_punc(
                        token):
                    continue
                self.parse_token(j, token)

                # break
            if self.properties['number_combo']:
                self.register_message(
                    "CONGRUENT NUMBERS AT END OF CYCLE: %s" % SanitationUtils.
                    coerce_unicode(self.properties['number_combo']))
                self.add_number(self.properties['number_combo'].flattened)
            if self.properties['name_combo']:
                self.register_message(
                    "CONGRUENT NAMES AT END OF CYCLE:  %s" % SanitationUtils.
                    coerce_unicode(self.properties['name_combo']))
                self.add_name(self.properties['name_combo'].flattened)
            # self.register_message( "FINISHED CYCLE, NAMES: ", self.properties['names'])
            continue

        while self.properties['numbers']:
            number = self.properties['numbers'].pop()
            if self.properties['weak_thoroughfares'] and not self.properties['thoroughfares']:
                weak_thoroughfare = self.properties['weak_thoroughfares'].pop()
                self.coerce_thoroughfare(number, weak_thoroughfare)
            else:
                self.properties['unknowns'] += [number]
                self.invalidate(
                    "Too many numbers to match to thoroughfare or subunit: %s"
                    % repr(number))
                break

        while self.properties['incomplete_subunits']:
            incomplete_subunit = self.properties['incomplete_subunits'].pop()
            self.complete_subunit(incomplete_subunit)

        while self.properties['ambiguous_tokens']:
            if not self.properties['thoroughfares'] \
                    and not self.properties['weak_thoroughfares']:
                ambiguous_token = self.properties['ambiguous_tokens'].pop()
                self.add_weak_thoroughfare((ambiguous_token, None, None))
            else:
                ambiguous_token = self.properties['ambiguous_tokens']
                self.enforce_strict(
                    'There are some ambiguous tokens: %s' % SanitationUtils.
                    coerce_unicode(self.properties['ambiguous_tokens']))
                break

        all_thoroughfares = self.properties['thoroughfares'] + self.properties['weak_thoroughfares']
        if len(all_thoroughfares) > 1:
            self.enforce_strict(
                'multiple thoroughfares: %s' %
                SanitationUtils.coerce_unicode(all_thoroughfares))

        if self.properties['unknowns']:
            self.invalidate("There are some unknown tokens: %s" %
                            repr(" | ".join(self.properties['unknowns'])))

    def parse_token(self, token_index, token):
        for getter, adder in [
            (AddressUtils.get_delivery, self.add_delivery),
            (AddressUtils.get_subunit, self.add_subunit),
            (AddressUtils.get_floor, self.add_floor),
            (AddressUtils.get_thoroughfare, self.add_thoroughfare),
            (NameUtils.get_care_of, self.add_careof),
            (NameUtils.get_organization, self.add_organization),
            (AddressUtils.get_weak_subunit, self.add_weak_subunit)
        ]:
            result = getter(token)
            if result:
                adder(result)
                return

        name = NameUtils.get_multi_name(token)
        number = AddressUtils.get_number(token)
        weak_thoroughfare = AddressUtils.get_weak_thoroughfare(token)
        building = AddressUtils.get_building(token)

        if (not name) or weak_thoroughfare or building:
            if self.properties['name_combo']:
                self.add_name(self.properties['name_combo'].flattened)
        if not number:
            if self.properties['number_combo']:
                self.add_number(self.properties['number_combo'].flattened)

        if building and weak_thoroughfare:
            self.register_message("BUILDING AND WEAK THOROUGHFARE")
            self.add_name(token)
            return
        if weak_thoroughfare:
            self.add_weak_thoroughfare(weak_thoroughfare)
            return
        if building and not self.properties['buildings']:
            self.add_building(building)
            return

        if name:
            self.register_message(
                "FOUND NAME: %s" % SanitationUtils.coerce_unicode(name))
            self.properties['name_combo'].add(token_index, name)
            return

        if number:
            self.register_message(
                "FOUND NUMBER: %s" % SanitationUtils.coerce_unicode(number))
            self.properties['number_combo'].add(token_index, number)
            return

        self.register_message(
            "UNKNOWN TOKEN %s" % SanitationUtils.coerce_unicode(token))
        self.properties['unknowns'] += [token]
        self.invalidate("There are some unknown tokens: %s" %
                        repr(self.properties['unknowns']))

    # NO SUBUNUTS -> SUBUNIT W/ NO UNIT TYPE

    def add_number(self, number):
        # if self.properties['name_combo']: self.add_name(self.properties['name_combo'].flattened)
        number = AddressUtils.get_number(number)
        if not number:
            return
        if self.properties['incomplete_subunits'] and not self.properties['name_combo']:
            subunit_type, subunit_number = self.properties[
                'incomplete_subunits'].pop()
            try:
                assert not SanitationUtils.string_contains_punctuation(
                    number), "Number must be single"
                number_find = AddressUtils.get_single_number(number)
                assert number_find, "Number must be valid"
                subunit_find = AddressUtils.get_single_number(subunit_number)
                assert subunit_find, "subunit number must be singular"
                assert int(number_find) > int(
                    subunit_find), "Number must be greater than subunit number"
                subunit_number += number
                self.add_subunit((subunit_type, subunit_number))
            except Exception as exc:
                self.register_message(SanitationUtils.coerce_unicode(exc))
                self.complete_subunit((subunit_type, subunit_number))
                self.add_number(number)
        elif not self.properties['subunits']:
            self.coerce_subunit(number)
        else:
            self.properties['numbers'] += [number]

    # NUMBERS and NO THOROUGHFARES -> WEAK THOROUGHFARE
    # SUBUNIT or FLOORS or DELIVERIES -> BUILDING

    def add_name(self, name):
        # if self.properties['number_combo']:
        #    self.add_number(self.properties['number_combo'].flattened)
        # name = NameUtils.get_multi_name(name)
        if not name:
            return
        # if we haven't flushed number_combo, do it now
        # self.register_message(
        #     "PROCESSING NAME %s" % SanitationUtils.coerce_unicode(name))
        names = filter(None, NameUtils.get_single_names(name))
        # self.register_message(
        #     "SINGLE NAMES %s" % SanitationUtils.coerce_unicode(names))
        weak_thoroughfare = AddressUtils.get_weak_thoroughfare(name)
        building = AddressUtils.get_building(name)
        if building and weak_thoroughfare:
            # self.register_message(
            #     "BUILDING %s" % SanitationUtils.coerce_unicode(building))
            # self.register_message(
            #     "WEAK THOROUGHFARE:  %s" %
            #     SanitationUtils.coerce_unicode(weak_thoroughfare))
            if building[1] and weak_thoroughfare[1]:
                thoroughfare_type_len, building_type_len = [
                    len(x[1]) for x in [weak_thoroughfare, building]
                ]
                # thoroughfare_type_len, building_type_len = map(
                #     lambda x: len(x[1]), [weak_thoroughfare, building])
                if thoroughfare_type_len > building_type_len:
                    self.add_weak_thoroughfare(weak_thoroughfare)
                    return
                elif building_type_len > thoroughfare_type_len:
                    self.add_building(building)
                    return
                # else:
                #     self.register_warning(
                #         'EQUALLY VALID THOROUGHFARE AND BUILDING')

        if not (self.properties['thoroughfares'] + self.properties['weak_thoroughfares']) and \
                (self.properties['numbers'] or self.properties['coerced_subunits']):
            if not weak_thoroughfare:
                if len(names) > 1:
                    thoroughfare_name = " ".join(map(str, names[:-1]))
                    thoroughfare_type = names[-1]
                else:
                    thoroughfare_name = name
                    thoroughfare_type = None
                weak_thoroughfare = (thoroughfare_name, thoroughfare_type,
                                     None)
            self.add_weak_thoroughfare(weak_thoroughfare)
        elif not (self.properties['buildings']) \
        and (self.properties['subunits'] or self.properties['floors'] \
        or self.properties['deliveries']):
            if building:
                self.add_building(building)
            else:
                self.coerce_building(name)
        elif weak_thoroughfare \
        and not self.properties['thoroughfares'] + self.properties['weak_thoroughfares']:
            self.add_weak_thoroughfare(weak_thoroughfare)
        elif building and not self.properties['buildings']:
            self.add_building(building)
        # elif weak_thoroughfare and not building:
        #     self.add_weak_thoroughfare(weak_thoroughfare)
        elif name in self.properties['remove_words']:
            self.properties['ignores'] += [name]
        elif not self.properties['thoroughfares'] + self.properties['weak_thoroughfares']:
            self.properties['names'] += [name]
        else:
            self.properties['ambiguous_tokens'] += [name]

    def add_subunit(self, subunit):
        subunit_type, subunit_number = subunit
        if subunit_type in ['SHOP', 'SUITE', 'KIOSK', 'SHRM', 'STORE']:
            self.properties['isShop'] = True
        if subunit_number[-1] == '/':
            while self.properties['incomplete_subunits']:
                self.complete_subunit(
                    self.properties['incomplete_subunits'].pop())
            # self.register_message("ADDING INCOMPLETE SUBUNIT:  %s" %
            #                       SanitationUtils.coerce_unicode(subunit))
            self.properties['incomplete_subunits'] += [subunit]
        else:
            # self.register_message("ADDING SUBUNIT:  %s" %
            #                       SanitationUtils.coerce_unicode(subunit))
            self.properties['subunits'] += [subunit]

    def add_weak_subunit(self, weak_subunit):
        subunit_type, _ = weak_subunit
        self.enforce_strict("Unknown subunit type: %s" % subunit_type)
        self.add_subunit(weak_subunit)

    def coerce_subunit(self, number):
        subunit = (None, number)
        # self.register_message(
        #     "COERCED SUBUNIT: %s" % SanitationUtils.coerce_unicode(subunit))
        self.properties['coerced_subunits'] += [subunit]

    def complete_subunit(self, incomplete_subunit):
        subunit_type, subunit_number = incomplete_subunit
        if subunit_number[-1] == '/':
            subunit_number = subunit_number[:-1]
        complete_subunit = subunit_type, subunit_number
        self.add_subunit(complete_subunit)

    def add_building(self, building):
        all_thoroughfares = self.properties['thoroughfares'] + self.properties['weak_thoroughfares']
        if all_thoroughfares:
            self.enforce_strict(
                "Building (%s) should not come after thoroughfare (%s)" %
                (SanitationUtils.coerce_unicode(building),
                 SanitationUtils.coerce_unicode(all_thoroughfares[0])))
        # self.register_message(
        #     "ADDING BUILDING:  %s" % SanitationUtils.coerce_unicode(building))
        self.properties['buildings'] += [building]

    def coerce_building(self, token):
        building = AddressUtils.get_building(token)
        if not building:
            building = (token, None)
        # self.register_message(
        #     "COERCED BUILDING %s" % SanitationUtils.coerce_unicode(building))
        self.add_building(building)

    def add_thoroughfare(self, thoroughfare):
        # self.register_message("ADDING THOROUGHFARE %s" %
        #                       SanitationUtils.coerce_unicode(thoroughfare))
        _, thoroughfare_name, thoroughfare_type, _ = thoroughfare
        self.assert_valid_thoroughfare_type(thoroughfare_name,
                                            thoroughfare_type)
        # if legit thoroughfare is being added, remove weaklings before adding
        while self.properties['weak_thoroughfares']:
            weak_thoroughfare = self.properties['weak_thoroughfares'].pop()
            token = " ".join(filter(None, weak_thoroughfare))
            self.coerce_building(token)
        self.properties['thoroughfares'] += [thoroughfare]

    def coerce_thoroughfare(self, number, weak_thoroughfare):
        # self.register_message(
        #     "COERCING THOROUGHFARE %s %s" % (
        #         SanitationUtils.coerce_unicode(number),
        #         SanitationUtils.coerce_unicode(weak_thoroughfare)
        #     )
        # )
        thoroughfare_name, thoroughfare_type, thoroughfare_suffix = weak_thoroughfare
        thoroughfare = (number, thoroughfare_name, thoroughfare_type,
                        thoroughfare_suffix)
        # self.register_message(
        #     "COERCED THOROUGHFARE: %s" %
        #     SanitationUtils.coerce_unicode(thoroughfare)
        # )
        self.add_thoroughfare(thoroughfare)

    def add_weak_thoroughfare(self, weak_thoroughfare):
        # self.register_message(
        #     "ADDING WEAK THOROUGHFARE %s" %
        #     SanitationUtils.coerce_unicode(weak_thoroughfare)
        # )
        if \
                True or\
                not (self.properties['thoroughfares'] or self.properties['weak_thoroughfares']):
            if self.properties['numbers'] or self.properties['coerced_subunits']:
                # if self.properties['number_combo']:
                #     number = AddressUtils.get_number(self.properties['number_combo'].flattened)
                if self.properties['numbers']:
                    number = self.properties['numbers'].pop()
                elif self.properties['coerced_subunits']:
                    _, number = self.properties['coerced_subunits'].pop()

                # token = " ".join(names)
                self.coerce_thoroughfare(number, weak_thoroughfare)
                return
            # self.register_message(
            #     "ADDING WEAK THOROUGHFARE:  %s" %
            #     SanitationUtils.coerce_unicode(weak_thoroughfare))
            thoroughfare_name, thoroughfare_type, _ = weak_thoroughfare
            self.assert_valid_thoroughfare_type(thoroughfare_name,
                                                thoroughfare_type)
            self.properties['weak_thoroughfares'] += [weak_thoroughfare]
        else:
            token = " ".join(filter(None, weak_thoroughfare))
            self.coerce_building(token)

    def add_floor(self, floor):
        # self.register_message(
        #     "ADDING FLOOR:  %s" % SanitationUtils.coerce_unicode(floor))
        self.properties['floors'] += [floor]

    def add_delivery(self, delivery):
        # self.register_message(
        #     "ADDING DELIVERY:  %s" % SanitationUtils.coerce_unicode(delivery))
        self.properties['deliveries'] += [delivery]

    def assert_valid_thoroughfare_type(self, thoroughfare_name,
                                       thoroughfare_type):
        if thoroughfare_type:
            try:
                assert AddressUtils.get_thoroughfare_type(
                    thoroughfare_type
                ), "Unknown thoroughfares type: %s" % thoroughfare_type
            except Exception as exc:
                self.enforce_strict(SanitationUtils.coerce_unicode(exc))
        else:
            self.enforce_strict("No thoroughfare type: " + thoroughfare_name)

    @property
    def subunits(self):
        if self.properties.get('subunits') or self.properties.get(
                'coerced_subunits'):
            return ", ".join([
                " ".join(filter(None, subunit))
                for subunit in (self.properties['subunits'] +
                                self.properties['coerced_subunits'])
            ])

    @property
    def floors(self):
        if self.properties.get('floors'):
            return ", ".join([
                " ".join(filter(None, floor))
                for floor in self.properties['floors']
            ])

    @property
    def buildings(self):
        if self.properties.get('buildings'):
            return ", ".join([
                " ".join(filter(None, building))
                for building in self.properties['buildings']
            ])

    @property
    def deliveries(self):
        if self.properties.get('deliveries'):
            return ", ".join([
                " ".join(filter(None, delivery))
                for delivery in self.properties['deliveries']
            ])

    @property
    def thoroughfares(self):
        if self.properties.get('thoroughfares') or self.properties.get(
                'weak_thoroughfares'):
            return ", ".join([
                " ".join(filter(None, thoroughfares))
                for thoroughfares in self.properties['thoroughfares'] +
                self.properties['weak_thoroughfares']
            ])

    @property
    def end_names(self):
        if self.properties.get('end_names'):
            return ", ".join(self.properties.get('end_names'))

    state = DescriptorUtils.kwarg_alias_property(
        'state',
        lambda self: \
        self.properties.get('state')
    )

    country = DescriptorUtils.kwarg_alias_property(
        'country',
        lambda self: \
        self.properties.get('country')
    )

    postcode = DescriptorUtils.kwarg_alias_property(
        'postcode',
        lambda self: \
        self.properties.get('postcode')
    )

    city = DescriptorUtils.kwarg_alias_property(
        'city',
        lambda self: \
        self.properties.get('city')
    )

    @property
    def line1(self):
        if self.properties_override:
            elements = [
                self.names,
                self.deliveries,
                self.subunits,
                self.floors,
                self.buildings,
            ]
            out = ", ".join(filter(None, elements))
            # SanitationUtils.safe_print( "line1: ", out )
            return out
        return self.kwargs.get('line1')

    @property
    def line2(self):
        if self.properties_override:
            elements = [self.thoroughfares, self.end_names]
            return ", ".join(filter(None, elements))
        return self.kwargs.get('line2')

    @property
    def line3(self):
        return ", ".join(
            filter(None, [self.city, self.state, self.postcode, self.country]))

    @staticmethod
    def determine_source(**kwargs):
        fields = [
            kwargs.get(key) for key in ['line1', 'line2', 'city'] if key
        ]
        # fields = filter(None,
        #                 map(lambda key: kwargs.get(key, ''),
        #                     ['line1', 'line2', 'city']))
        if fields:
            act_like = all(map(SanitationUtils.string_capitalized, fields))
            if act_like:
                return 'act'
            return 'unknown'
        return None

    def normalize_val(self, key, val):
        val = super(ContactAddress, self).normalize_val(key, val)
        # if key == 'state':
        val = AddressUtils.sanitize_state(val)
        return val

    def __unicode__(self, tablefmt=None):
        prefix = self.get_prefix() if self.debug else ""
        delimeter = "; "
        if tablefmt == "html":
            delimeter = "<br/>"
        return SanitationUtils.coerce_unicode(prefix + delimeter.join(
            filter(None, [
                self.line1, self.line2, self.line3,
                (("|UNKN:" + " ".join(self.properties['unknowns']))
                 if self.debug and 'unknowns' in self.properties else "")
            ])))


class ContactName(ContactObject):
    fieldGroupType = "NAME"
    equality_keys = ['first_name', 'middle_name', 'family_name']
    similarity_keys = [
        'first_name', 'middle_name', 'family_name', 'contact', 'company'
    ]
    mandatory_keys = ['first_name', 'family_name']
    key_mappings = {
        'first_name': ['First Name'],
        'family_name': ['Surname'],
        'middle_name': ['Middle Name'],
        'name_prefix': ['Name Prefix'],
        'name_suffix': ['Name Suffix'],
        'name_notes': ['Memo'],
        'company': ['Company'],
        'contact': ['Contact']
    }

    def __init__(self, schema=None, **kwargs):
        self.debug = self.DEBUG_NAME
        self.strict = STRICT_NAME
        super(ContactName, self).__init__(schema, **kwargs)

    def init_properties(self):
        super(ContactName, self).init_properties()
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

    def process_kwargs(self):
        super(ContactName, self).process_kwargs()
        if not self.empty:
            if self.kwargs.get('country'):
                country_sanitized = AddressUtils.sanitize_state(
                    self.kwargs['country'])
                country_identified = AddressUtils.identify_country(
                    country_sanitized)
                # if self.debug: print "country_sanitized", country_sanitized,
                # "country_identified", country_identified
                if country_sanitized != country_identified:
                    self.properties['country'] = country_identified
                else:
                    self.properties['country'] = country_sanitized
                # self.properties['remove_words'].append(country_sanitized)

            if self.kwargs.get('state'):
                state_sanitized = AddressUtils.sanitize_state(
                    self.kwargs['state'])
                self.properties['remove_words'].append(state_sanitized)
                state_identified = AddressUtils.identify_state(state_sanitized)
                if state_identified != state_sanitized:
                    self.properties['remove_words'].append(state_identified)
                    self.properties['state'] = state_identified
                else:
                    self.properties['state'] = state_sanitized

            if self.kwargs.get('city'):
                city_sanitized = AddressUtils.sanitize_state(
                    self.kwargs['city'])
                self.properties['city'] = city_sanitized

            if self.kwargs.get('company'):
                company_sanitized = SanitationUtils.normalize_val(
                    self.kwargs['company'])
                company_tokens = NameUtils.tokenize_name(company_sanitized)
                company_has_notes = False
                for token in company_tokens:
                    note = NameUtils.get_note(token)
                    if note:
                        company_has_notes = True
                if not company_has_notes:
                    self.properties['remove_words'].append(company_sanitized)
                    self.coerce_organization(self.kwargs.get('company'))

            full_name_contact = SanitationUtils.normalize_val(
                self.kwargs.get('contact'))
            full_name_components = SanitationUtils.normalize_val(
                ' '.join([
                    self.kwargs.get(key) for key in [
                        'name_prefix', 'first_name', 'middle_name',
                        'family_name', 'name_suffix'
                    ] if self.kwargs.get(key)
                ])
            )
            # full_name_components = SanitationUtils.normalize_val(
            #     ' '.join(
            #         filter(None,
            #                map(lambda k: self.kwargs.get(k), ))))

            if full_name_contact and full_name_components:
                no_punctuation_contact, no_punctuation_components = map(
                    SanitationUtils.similar_no_punc_cmp,
                    [full_name_contact, full_name_components])
                if no_punctuation_contact == no_punctuation_components:
                    # The names are effectively the same, can drop one
                    full_name_components = None
                else:
                    reverse_name_components = SanitationUtils.similar_no_punc_cmp(
                        " ".join(
                            filter(None, [
                                self.kwargs.get('family_name'),
                                self.kwargs.get('first_name'),
                                self.kwargs.get('middle_name')
                            ])))
                    # print reverse_name_components, no_punctuation_contact
                    if reverse_name_components == no_punctuation_contact:
                        # self.register_message(
                        #     "DETECTED REVERSE NAME:  %s" % \
                        #     SanitationUtils.coerce_unicode(full_name_contact))
                        full_name_contact = None

            full_names = SeqUtils.filter_unique_true(
                map(SanitationUtils.normalize_val,
                    [full_name_contact, full_name_components]))

            if len(full_names) > 1:
                self.invalidate("Unable to determine which name is correct: %s"
                                % SanitationUtils.coerce_unicode(full_names))

            for i, full_name in enumerate(full_names):
                # self.register_message("ANALYSING FULL NAME %d: %s" %
                #                       (i, repr(full_name)))
                tokens = NameUtils.tokenize_name(full_name)
                # self.register_message("TOKENS: %s" % repr(tokens))
                self.properties['name_combo'].reset()
                for j, token in enumerate(tokens):
                    self.parse_token(j, token)

                if self.properties['name_combo']:
                    # self.register_message("CONGRUENT NAMES AT END OF CYCLE: %s"
                    #                       % self.properties['name_combo'])
                    self.add_name(self.properties['name_combo'].flattened)

            while self.properties['names']:
                name = self.properties['names'].pop(0)
                single_names = NameUtils.get_single_names(name)
                for single_name in single_names:
                    self.properties['single_names'] += [single_name]
                    # self.register_message(
                    #     "adding single name: %s" % single_name)

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
                    self.properties['first_names'] += [
                        self.properties['single_names'].pop(0)
                    ]

            if len(self.properties['family_names']) > 1:
                self.enforce_strict(
                    "THERE ARE MULTIPLE FAMILY NAMES: %s" % SanitationUtils.
                    coerce_bytes(' / '.join(self.properties['family_names'])))
            if len(self.properties['middle_names']) > 1:
                self.enforce_strict(
                    "THERE ARE MULTIPLE MIDDLE NAMES: %s" % SanitationUtils.
                    coerce_bytes(' / '.join(self.properties['middle_names'])))
            if len(self.properties['first_names']) > 2:
                self.enforce_strict(
                    "THERE ARE MULTIPLE FIRST NAMES: %s" % SanitationUtils.
                    coerce_bytes(' / '.join(self.properties['first_names'])))

            if not any([
                    self.properties['family_names'],
                    self.properties['middle_names'],
                    self.properties['first_names']
            ]):
                self.empty = True

            if len(self.properties['titles']) > 1:
                self.enforce_strict("THERE ARE MULTIPLE TITLES: " +
                                    SanitationUtils.coerce_bytes(
                                        ' / '.join(self.properties['titles'])))

            if len(self.properties['notes']) > 1:
                self.enforce_strict(
                    "THERE ARE MULTIPLE NOTES: " +
                    SanitationUtils.coerce_bytes(" / ".join(
                        map(self.get_note_no_paranthesis,
                            self.properties.get('notes', [])))))

            if len(self.properties['positions']) > 1:
                self.enforce_strict(
                    "THERE ARE MULTIPLE POSITIONS: " + SanitationUtils.
                    coerce_bytes(' / '.join(self.properties['positions'])))

            if self.properties['unknowns']:
                self.invalidate(
                    "There are some unknown tokens: %s" % \
                    SanitationUtils.coerce_bytes(
                        ' / '.join(self.properties['unknowns'])
                    )
                )

    def parse_token(self, token_index, token):
        if self.properties['name_combo'].broken(token_index):
            self.add_name(self.properties['name_combo'].flattened)

        title = NameUtils.get_title(token)
        if title:
            # self.register_message(
            #     "FOUND TITLE: %s" % SanitationUtils.coerce_unicode(title))
            if title not in self.properties['titles']:
                self.properties['titles'] += [title]
            return

        position = NameUtils.get_position(token)
        if position:
            # self.register_message("FOUND POSITION: %s" %
            #                       SanitationUtils.coerce_unicode(position))
            if position not in self.properties['positions']:
                self.properties['positions'] += [position]
            return

        suffix = NameUtils.get_name_suffix(token)
        if suffix:
            # self.register_message("FOUND NAME SUFFIX: %s" %
            #                       SanitationUtils.coerce_unicode(suffix))
            if suffix not in self.properties['suffixes']:
                self.properties['suffixes'] += [suffix]
            return

        email = NameUtils.get_email(token)
        if email:
            # self.register_message(
            #     "FOUND EMAIL: %s" % SanitationUtils.coerce_unicode(email))
            if email not in self.properties['emails']:
                self.properties['emails'] += [email]
            return

        note = NameUtils.get_note(token)
        if note:
            # self.register_message(
            #     "FOUND NOTE: %s" % self.get_note_no_paranthesis(note))
            if note not in self.properties['notes']:
                self.properties['notes'] += [note]
            return

        careof = NameUtils.get_care_of(token)
        if careof:
            # self.register_message(
            #     "FOUND CAREOF: %s" % SanitationUtils.coerce_unicode(careof))
            if careof not in self.properties['careof_names']:
                self.properties['careof_names'] += [careof]
            return

        organization = NameUtils.get_organization(token)
        if organization:
            # self.register_message("FOUND ORGANIZATION: %s" %
            #                       SanitationUtils.coerce_unicode(organization))
            if organization not in self.properties['organization_names']:
                self.properties['organization_names'] += [organization]
            return

        family_name = NameUtils.get_family_name(token)
        single_name = NameUtils.get_single_name(token)
        # if family_name and single_name:
        #     self.register_message(
        #         "FOUND FAMILY AND NAME: '%s' | '%s'" %
        #         (SanitationUtils.coerce_unicode(family_name),
        #          SanitationUtils.coerce_unicode(single_name)))
        if family_name:
            if not single_name or (len(family_name) > len(single_name)):
                # self.register_message(
                #     "FOUND FAMILY NAME: %s" %
                #     SanitationUtils.coerce_unicode(family_name))
                self.properties['family_names'] += [family_name]
                return

        multi_name = NameUtils.get_multi_name(token)

        if multi_name:
            # self.register_message(
            #     "FOUND NAME: %s" % SanitationUtils.coerce_unicode(multi_name))
            self.properties['name_combo'].add(token_index, multi_name)
            return

        if SanitationUtils.string_contains_bad_punc(token) and len(token) == 1:
            return

        self.properties['unknowns'] += [token]
        self.invalidate("UNKNOWN TOKEN: " + repr(token))

    def add_name(self, name):
        if name in self.properties['remove_words']:
            self.properties['ignores'] += [name]
            # self.register_message(
            #     "IGNORING WORD: %s" % SanitationUtils.coerce_unicode(name))
            return
        if name and name not in self.properties['names']:
            # self.register_message(
            #     "ADDING NAME: %s" % SanitationUtils.coerce_unicode(name))
            self.properties['names'] += [name]

    def get_note_no_paranthesis(self, note_tuple):
        _, names_before_note, note, names_after_note, _ = note_tuple
        return " ".join(
            filter(None, [names_before_note, note, names_after_note]))

    first_name = DescriptorUtils.kwarg_alias_property(
        'first_name',
        lambda self: \
        " ".join(filter(None, self.properties.get('first_names', [])))
    )

    family_name = DescriptorUtils.kwarg_alias_property(
        'family_name',
        lambda self:\
        " ".join(filter(None, self.properties.get('family_names', [])))
    )

    middle_name = DescriptorUtils.kwarg_alias_property(
        'middle_name',
        lambda self:\
        " ".join(filter(None, self.properties.get('middle_names', [])))
    )

    name_prefix = DescriptorUtils.kwarg_alias_property(
        'name_prefix',
        lambda self: \
        " ".join(filter(None, self.properties.get('titles', [])))
    )

    name_suffix = DescriptorUtils.kwarg_alias_property(
        'name_suffix',
        lambda self: \
        " ".join(filter(
            None,
            self.properties.get('positions', []) \
            + self.properties.get('suffixes', [])
        ))
    )

    contact = DescriptorUtils.kwarg_alias_property(
        'contact',
        lambda self: " ".join(filter(None, [
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
            return ', '.join(
                map(self.get_note_no_paranthesis,
                    self.properties.get('notes', [])))
        return self.kwargs.get('name_notes')

    def __unicode__(self, tablefmt=None):
        prefix = self.get_prefix() if self.debug else ""
        delimeter = " "
        return SanitationUtils.coerce_unicode(prefix + delimeter.join(filter(None, [
            (("PREF: " + self.name_prefix)
             if self.debug and self.name_prefix else self.name_prefix),
            (("FIRST: " + self.first_name)
             if self.debug and self.first_name else self.first_name),
            (("MID: " + self.middle_name)
             if self.debug and self.middle_name else self.middle_name),
            (("FAM: " + self.family_name)
             if self.debug and self.family_name else self.family_name),
            (("SUFF: " + self.name_suffix)
             if self.debug and self.name_suffix else self.name_suffix),
            (("NOTES: (%s)" % self.name_notes) if self.debug and self.name_notes else "(%s)" %
             self.name_notes if self.name_notes else None),
            (("|UNKN:" + " ".join(self.properties['unknowns']))\
                if self.debug and self.properties.get('unknowns') else "")
        ])))

    def __str__(self, tablefmt=None):
        return SanitationUtils.coerce_bytes(self.__unicode__(tablefmt))

class ContactPhones(FieldGroup):
    fieldGroupType = "PHONES"
    equality_keys = ['tel_number', 'mob_number']
    similarity_keys = equality_keys[:]
    key_mappings = {
        'mob_number': ['Mobile Phone'],
        'tel_number': ['Phone'],
        'home_number': ['Home Phone'],
        'fax_number': ['Fax'],
        'mob_pref': ['Mobile Phone Preferred'],
        'tel_pref': ['Phone Preferred'],
        'pref_method': ['Pref Method'],
    }
    reprocess_kwargs = True

    # def __init__(self, schema=None, **kwargs):
    #     super(ContactPhones, self).__init__(**kwargs)

    def is_master_schema(self, schema=None):
        if not (schema and self.properties.get('master_schema')):
            return
        return schema.lower() == self.properties.get('master_schema').lower()

    def get_pref(self, schema=None, index=None):
        pref_data = self.properties.get('pref_data')
        if not (schema and index and pref_data):
            return
        options = pref_data.get(schema.lower(), {}).get('options', [])
        if not (options and index < len(options)):
            return
        return options[index]

    def get_index(self, schema=None, pref=None):
        pref_data = self.properties.get('pref_data')
        if not (schema and pref and pref_data):
            return
        options = pref_data.get(schema.lower(), {}).get('options', [])
        if not (options and pref in options):
            return
        return options.index(pref)

    def translate_pref(self, from_schema=None, to_schema=None, pref=None):
        if not (pref and to_schema and from_schema):
            return pref
        index = self.get_index(from_schema, pref)
        if index is None:
            return pref
        return self.get_pref(to_schema, index)


    def process_kwargs(self):
        super(ContactPhones, self).process_kwargs()
        if self.empty:
            return
        for key, value in self.kwargs.items():
            if '_number' in key:
                if value is not None:
                    value = SanitationUtils.strip_non_phone_characters(value)
            self.properties[key] = value
        # process pref_method, convert to master schema
        if all(
            key in self.properties for key in \
            ['pref_method', 'master_schema', 'pref_data']
        ):
            if not self.is_master_schema(self.schema):
                pref_method = self.properties['pref_method']
                if ',' in pref_method:
                    pref_method = pref_method.split(',')[0]
                pref_method = self.translate_pref(
                    self.schema,
                    self.properties['master_schema'],
                    pref_method
                )
                self.properties['pref_method'] = pref_method


    mob_number = DescriptorUtils.kwarg_alias_property(
        'mob_number',
        lambda self:
        SanitationUtils.strip_non_numbers(self.properties.get('mob_number'))
        if 'mob_number' in self.properties else ""
    )

    tel_number = DescriptorUtils.kwarg_alias_property(
        'tel_number',
        lambda self:
        SanitationUtils.strip_non_numbers(self.properties.get('tel_number'))
        if 'tel_number' in self.properties else ""
    )

    fax_number = DescriptorUtils.kwarg_alias_property(
        'fax_number',
        lambda self:
        SanitationUtils.strip_non_numbers(self.properties.get('fax_number'))
        if 'fax_number' in self.properties else ""
    )

    # mob_pref = DescriptorUtils.kwarg_alias_property(
    #     'mob_pref', lambda self: self.properties.get('mob_pref'))
    #
    # tel_pref = DescriptorUtils.kwarg_alias_property(
    #     'tel_pref', lambda self: self.properties.get('tel_pref'))

    @property
    def pref_method(self):
        response = self['pref_method']
        if not self.is_master_schema(self.schema):
            response = self.translate_pref(
                self.properties.get('master_schema'),
                self.schema,
                response
            )
        return response


    def __unicode__(self, tablefmt=None):
        prefix = self.get_prefix() if self.debug else ""
        delimeter = "; "
        components = []
        for key in ['tel', 'mob', 'fax']:
            attr = getattr(self, '%s_number' % key)
            if attr:
                component = ""
                if self.debug:
                    component += "%s: " % key.upper()
                component += attr
                components.append(attr)
        return SanitationUtils.coerce_unicode(
            prefix + delimeter.join(components)
        )

    def __str__(self, tablefmt=None):
        return SanitationUtils.coerce_bytes(self.__unicode__(tablefmt))




class SocialMediaFields(FieldGroup):
    fieldGroupType = "SOCIALMEDIA"
    equality_keys = ['facebook', 'twitter', 'instagram', 'gplus', 'website']
    similarity_keys = equality_keys[:]
    key_mappings = {
        'facebook': ['Facebook Username'],
        'twitter': ['Twitter Username'],
        'gplus': ['GooglePlus Username'],
        'instagram': ['Instagram Username'],
        'website': ['Web Site']
    }

    # def __init__(self, schema=None, **kwargs):
    #     super(SocialMediaFields, self).__init__(**kwargs)

    def process_kwargs(self):
        super(SocialMediaFields, self).process_kwargs()
        if not self.empty:
            for key, value in self.kwargs.items():
                # if self.debug:
                #     self.register_message("kwargs[%s] = %s" % (key, value))
                self.properties[key] = value

    @property
    def facebook(self):
        if self.properties_override:
            return self.properties.get('facebook')
        return self.kwargs.get('facebook')

    @property
    def twitter(self):
        if self.properties_override:
            return self.properties.get('twitter')
        return self.kwargs.get('twitter')

    @property
    def gplus(self):
        if self.properties_override:
            return self.properties.get('gplus')
        return self.kwargs.get('gplus')

    @property
    def instagram(self):
        if self.properties_override:
            return self.properties.get('instagram')
        return self.kwargs.get('instagram')

    @property
    def website(self):
        # if self.debug:
        #     self.register_message("kwargs: %s, properties: %s" %
        #                           (pformat(self.properties.items()),
        #                            pformat(self.kwargs.items())))
        if self.properties_override:
            return self.properties.get('website')
        return self.kwargs.get('website')

    def normalize_val(self, key, val):
        val = super(SocialMediaFields, self).normalize_val(key, val)
        val = SanitationUtils.strip_url_protocol(val)
        return val

    def __unicode__(self, tablefmt=None):
        prefix = self.get_prefix() if self.debug else ""
        delimeter = "; "
        return SanitationUtils.coerce_unicode(prefix + delimeter.join(
            filter(None, [
                self.facebook,
                self.twitter,
                self.gplus,
                self.instagram,
                self.website,
            ])))

    def __str__(self, tablefmt=None):
        return SanitationUtils.coerce_bytes(self.__unicode__(tablefmt))


class RoleGroup(FieldGroup):
    """ docstring for RoleGroup. """

    fieldGroupType = "ROLE"
    equality_keys = ['direct_brand', 'role']
    key_mappings = {
        'direct_brand': ['Direct Brand'],
        'role': ['Role'],
    }
    similarity_keys = ['role', 'direct_brand']
    similar_all_keys = True
    # perform_post = True

    role_translations = [
        # unambiguous
        ('rn', 'Retail'),
        ('rn', 'Retail Normal'),
        ('rp', 'Retail Preferred'),
        ('xrn', 'Retail Export'),
        ('xrn', 'Export Retail Normal'),
        ('xrp', 'Retail Preferred Export'),
        ('xrp', 'Export Retail Preferred'),
        ('wn', 'Wholesale'),
        ('wn', 'Wholesale Normal'),
        ('wp', 'Wholesale Preferred'),
        ('xwn', 'Wholesale Export'),
        ('xwn', 'Export Wholesale'),
        ('xwn', 'Export Wholesale Normal'),
        ('xwp', 'Wholesale Preferred Export'),
        ('xwp', 'Export Wholesale Preferred'),
        ('dn', 'Distributor'),
        ('dn', 'Distributor Normal'),
        ('dp', 'Distributor Preferred'),
        ('xdn', 'Distributor Export'),
        ('xdn', 'Export Distributor'),
        ('xdn', 'Export Distributor Normal'),
        ('xdp', 'Distributor Preferred Export'),
        ('xdp', 'Export Distributor Preferred'),
        ('admin', 'Administrator'),
        # ambiguous
        ('xwn', 'Export'),
    ]

    equivalent_roles = [
        ('admin', ['admi'])
    ]

    schema_translations = [
        ('tt', 'TechnoTan'),
        ('vt', 'VuTan'),
        ('mm', 'Mosaic Minerals'),
        ('mm', 'Mosaic'),
        ('pw', 'PrintWorx'),
        ('at', 'AbsoluteTan'),
        ('hr', 'House of Rhinestones'),
        ('ma', 'Meridian Marketing'),
        ('tc', 'Tanbience'),
        ('st', 'Staff'),
        ('-', 'Pending')
    ]

    allowed_combinations = OrderedDict([
        ('tt', ['rn', 'rp', 'xrn', 'xrp', 'wn', 'wp', 'xwn', 'xwp']),
        ('vt', [
            'rn', 'rp', 'xrn', 'xrp', 'wn', 'wp', 'xwn', 'xwp', 'dn', 'dp',
            'xdn', 'xdp'
        ]),
        ('mm', [
            'rn', 'rp', 'xrn', 'xrp', 'wn', 'wp', 'xwn', 'xwp', 'dn', 'dp',
            'xdn', 'xdp'
        ]),
        ('tc', ['rn', 'rp', 'wn', 'wp', 'dn', 'dp']),
        ('st', ['admin'])
    ])

    roleless_schemas = ['-', 'st']
    default_role = 'rn'
    reprocess_kwargs = True
    admin_brand = 'st'
    admin_schema = (admin_brand, None)
    admin_role = 'admin'
    # default_schema = 'tt'

    # def __init__(self, schema=None, **kwargs):
    #     super(RoleGroup, self).__init__(**kwargs)

    def init_properties(self):
        self.properties['direct_brands'] = []
        self.properties['role'] = ''

    @classmethod
    def translate_schema(cls, schema):
        if not schema:
            return
        schema = schema.lower()
        for key, translation in cls.schema_translations:
            if key.lower() == schema:
                return translation

    @classmethod
    def get_schema(cls, brand):
        if not brand:
            return
        brand = brand.lower()
        for schema, translation in cls.schema_translations:
            if translation.lower() == brand:
                return schema.lower()

    @classmethod
    def schema_exists(cls, schema):
        if not schema:
            return
        schema = schema.lower()
        for key, _ in cls.schema_translations:
            if key.lower() == schema:
                return True

    @classmethod
    def role_exists(cls, role):
        if not role:
            return
        role = role.lower()
        for key, _ in cls.role_translations:
            if key.lower() == role:
                return True

    @classmethod
    def translate_role(cls, role):
        if not role:
            return
        role = role.lower()
        for key, translation in cls.role_translations:
            if key.lower() == role:
                return translation

    @classmethod
    def get_role(cls, role_string):
        if not role_string:
            return
        role_string = role_string.lower()
        for key, translation in cls.role_translations:
            if translation.lower() == role_string:
                return key.lower()

    @classmethod
    def tokenwise_startswith(cls, haystack_tokens, needle_tokens):
        if len(needle_tokens) > len(haystack_tokens):
            return
        for index, needle_token in enumerate(needle_tokens):
            if needle_token != haystack_tokens[index]:
                return
        return True

    @classmethod
    def parse_direct_brand(cls, direct_brand):
        parsed_schema = None
        parsed_role = None
        if direct_brand == "none":
            direct_brand = None
        if direct_brand:
            direct_brand = SanitationUtils.strip_tailing_whitespace(direct_brand)
            direct_brand = SanitationUtils.strip_leading_whitespace(direct_brand)
            if direct_brand == "pending":
                return ('-', None)
            direct_brand_tokens = direct_brand.lower().split(' ')
            # do tokenwise comparison on all possible schemes:
            # if Registrar.DEBUG_CONTACT:
            #     Registrar.register_message("direct brand tokens: %s" % direct_brand_tokens)
            for schema, brand in cls.schema_translations:
                brand_tokens = brand.lower().split(' ')
                # if Registrar.DEBUG_CONTACT:
                #     Registrar.register_message("brand tokens: %s" % brand_tokens)
                if cls.tokenwise_startswith(direct_brand_tokens, brand_tokens):
                    parsed_schema = schema
                    remaining_tokens = \
                        direct_brand_tokens[len(brand_tokens):]
                    # if Registrar.DEBUG_CONTACT:
                    #     Registrar.register_message("remaining tokens: %s" % remaining_tokens)
                    if remaining_tokens:
                        parsed_role = cls.get_role(
                            " ".join(remaining_tokens))
                        assert parsed_role, \
                            "could not parse role: %s" % " ".join(remaining_tokens)
                    break

            assert parsed_schema, \
                "unkown brand: %s" %  direct_brand
        # if Registrar.DEBUG_CONTACT:
        #     Registrar.register_message("returning schema: %s; role: %s" % (
        #         parsed_schema, parsed_role
        #     ))
        return parsed_schema, parsed_role

    @classmethod
    def parse_direct_brand_str(cls, direct_brand_str):
        parsed = []
        if direct_brand_str:
            for direct_brand in map(str.lower, str(direct_brand_str).split(';')):
                # print("looking at direct_brand: %s" % direct_brand)
                parsed_schema, parsed_role = cls.parse_direct_brand(
                    direct_brand)
                if parsed_schema:
                    parsed.append((parsed_schema, parsed_role))
        return parsed

    @classmethod
    def format_direct_brand(cls, parsed_schema, parsed_role=None):
        formatted_brand = cls.translate_schema(parsed_schema)
        assert formatted_brand, \
            "cannot format as direct brand: (%s, %s)" % (
                parsed_schema, parsed_role
            )
        if parsed_role:
            formatted_role = cls.translate_role(parsed_role)
            return " ".join([formatted_brand, formatted_role])
        return formatted_brand

    @classmethod
    def determine_role(cls, direct_brand_str, schema=None, role=None):
        """
        Determe what role should be based on direct brand, schema and (optionally) default role.
        """
        if role is None:
            role = cls.default_role
        if not schema:
            return role
        schema = schema.lower()
        assert cls.schema_exists(schema), "schema %s not recognized" % schema
        if direct_brand_str is None:
            return role
        for parsed_schema, parsed_role in cls.parse_direct_brand_str(
                direct_brand_str):
            if parsed_schema:
                if (parsed_schema, parsed_role) == cls.admin_schema:
                    return cls.admin_role
                if parsed_role and schema == parsed_schema:
                    assert \
                        cls.role_exists(parsed_role), \
                        "role %s not recognized" % parsed_role
                    return parsed_role.upper()
        return role

    def normalize_role(self, role):
        """
        Take a raw role from input and return its normalized form.
        """
        role = role.lower()
        for role_normalized, role_equivalents in self.equivalent_roles:
            if role in role_equivalents:
                role = role_normalized
        return role

    def normalize_val(self, key, val):
        val = super(RoleGroup, self).normalize_val(key, val)
        if key == 'role':
            val = self.normalize_role(val)
            if val == self.default_role:
                val = ''
        return val

    def process_kwargs(self):
        super(RoleGroup, self).process_kwargs()
        # if self.empty:
        #     return
        # No reason to return of role info is empty!

        if self.schema:
            assert \
            self.schema_exists(self.schema), \
            "schema should be valid: %s" % self.schema

        if self.kwargs.get('role'):
            self.properties['role'] = self.normalize_role(self.kwargs.get('role'))
            assert self.role_exists(self.properties['role']), \
                "act_role should exist: %s" % self.properties['role']
            if self.properties['role'] == self.admin_role:
                self.properties['direct_brands'] = [self.admin_schema]
                return

        parsed = self.parse_direct_brand_str(self.kwargs.get('direct_brand'))
        # if self.debug:
        #     self.register_message("parsed: %s" % pformat(parsed))
        for count, (parsed_schema, parsed_role) in enumerate(parsed):
            if parsed_role == self.admin_role or parsed_schema == self.admin_brand:
                self.properties['role'] = self.admin_role
                self.properties['direct_brands'] = [self.admin_schema]
                break
            if parsed_schema == '-' and (len(parsed) - count > 1):
                continue
            # if self.debug:
            #     self.register_message("analysing: %s / %s" % (
            #         parsed_schema, parsed_role
            #     ))
            if parsed_schema:
                in_schema = True
                if self.schema:
                    in_schema = (parsed_schema == self.schema.lower())
                # else:
                #     in_schema = (parsed_schema == self.default_schema.lower())
                if parsed_schema not in self.roleless_schemas:
                    # if there is competition:
                    role_competitors = [(0, self.default_role, 'default')]
                    allowed_roles = [self.default_role]
                    if parsed_schema in self.allowed_combinations:
                        allowed_roles = self.allowed_combinations[
                            parsed_schema]
                    for priority, allowed_role in enumerate(allowed_roles):
                        if allowed_role == self.properties['role'] and in_schema:
                            role_competitors.append(
                                (priority, self.properties['role'], 'act_role')
                            )
                            if self.schema:
                                break
                        if allowed_role == parsed_role:
                            role_competitors.append(
                                (priority, parsed_role, 'parsed_role')
                            )
                            if self.schema:
                                break
                    # if self.debug:
                    #     self.register_message(
                    #         "role competitors: %s" % pformat(role_competitors))
                    assert role_competitors, \
                        "cannot find a suitable role for schema %s out of %s. allowed:%s" % (
                            parsed_schema,
                            role_competitors,
                            allowed_roles
                        )
                    _, winning_role, source = max(role_competitors)
                    # if self.debug:
                    #     self.register_message(
                    #         "winner: %s, %s" % (winning_role, source)
                    #     )
                    if source != 'act_role' and in_schema:
                        # if self.debug:
                        #     self.register_message("source not act and in schema")
                        self.properties['role'] = winning_role

                    if len(allowed_roles) > 1:
                        self.properties['direct_brands'].append((parsed_schema,
                                                                 winning_role))
                        continue
                self.properties['direct_brands'].append((parsed_schema, None))

        # if self.debug:
        #     self.register_message(
        #         "direct_brands: %s, role: %s" % (
        #             self.properties['direct_brands'],
        #             self.properties['role']
        #         )
        #     )

        if not self.properties['direct_brands']:
            self.properties['direct_brands'] = [('-', None)]
        if self.properties['direct_brands'] == [('-', None)]:
            if self.properties['role'] == self.admin_role:
                self.properties['direct_brands'] = [self.admin_schema]
            else:
                self.properties['role'] = ''
        if not self.properties['role']:
            self.properties['role'] = self.default_role

    @property
    def direct_brand(self):
        return self['direct_brand']
        # if self.properties_override:
        #     if self.properties['direct_brands']:
        #         return ";".join([
        #             self.format_direct_brand(*direct_brand_out) \
        #             for direct_brand_out in self.properties['direct_brands']
        #         ])
        #     return
        # return self.kwargs.get('direct_brand')

    @property
    def role(self):
        role = self['role']
        if role:
            return role.upper()
        # if self.properties_override:
        #     if self.schema:
        #         role = self.determine_role(
        #             self.direct_brand,
        #             self.schema
        #         )
        #     else:
        #         role = self.properties.get('role')
        #     if role:
        #         return role.upper()
        #     return
        # role = self.kwargs.get('role')
        # if role:
        #     return role.upper()

    def __setitem__(self, key, val):
        # if Registrar.DEBUG_CONTACT:
        #     Registrar.register_message(
        #         "setting key %s to val %s " % (key, val)
        #     )
        if self.properties_override:
            attr = self.get_mapped_attr(key)
            if attr == 'direct_brand':
                try:
                    val = self.parse_direct_brand_str(val)
                    key = 'direct_brands'
                except Exception as exc:
                    raise ValueError("could not set direct brand because: %s" % exc)
        super(RoleGroup, self).__setitem__(key, val)

    def __getitem__(self, key):
        # if Registrar.DEBUG_CONTACT:
        #     Registrar.register_message(
        #         "getting key %s" % (key)
        #     )
        if self.properties_override:
            attr = self.get_mapped_attr(key)
            if attr == 'direct_brand':
                return ";".join([
                    self.format_direct_brand(*direct_brand_out) \
                    for direct_brand_out in self.properties.get('direct_brands', [])
                ])
            elif attr == 'role':
                if self.schema:
                    role = self.determine_role(
                        self.direct_brand,
                        self.schema
                    )
                else:
                    role = super(RoleGroup, self).__getitem__('role')
                if role:
                    return role.upper()
        return super(RoleGroup, self).__getitem__(key)

    def __unicode__(self, tablefmt=None):
        prefix = self.get_prefix() if self.debug else ""
        delimeter = "; "
        return SanitationUtils.coerce_unicode(prefix + delimeter.join(
            filter(None, [
                self.role,
                self.direct_brand,
            ])))
