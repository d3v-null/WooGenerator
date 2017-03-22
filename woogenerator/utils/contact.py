# -*- coding: utf-8 -*-
import functools
import itertools
# from itertools import chain
import re
import time
import sys
# import datetime
import inspect
import json
from collections import OrderedDict
import codecs
import unicodecsv
import cStringIO
# from uniqid import uniqid
from phpserialize import dumps, loads
from kitchen.text import converters
import time
import math
import random
import io
import base64
from pympler import tracker
import cgi
import os
from urlparse import urlparse, parse_qs
from core import Registrar, SanitationUtils

try:
    # Python 2.6-2.7
    from HTMLParser import HTMLParser
except ImportError:
    # Python 3
    from html.parser import HTMLParser


class NameUtils:
    ordinalNumberRegex = r"(\d+)(?:ST|ND|RD|TH)"

    # #disallowed punctuation and whitespace
    # disallowedPunctuationOrSpace = list(set(disallowedPunctuation + whitespaceChars))
    # #delimeter characters incl whitespace and disallowed punc
    # tokenDelimeters  =  list(set([ r"\d"] + disallowedPunctuation + whitespaceChars))
    # #delimeter characters including all punctuation and whitespace
    # tokenPunctuationDelimeters = list(set([r"\d"] + punctuationChars + whitespaceChars))
    # #delimeter characters excl space
    # tokenDelimetersNoSpace  = list(set(disallowedPunctuation + whitespaceChars + [r"\d"]) - set([' ']))
    # punctuationRegex = r"[%s]" % "".join(punctuationChars)
    # #delimeter characters incl space and disallowed punc
    # delimeterRegex   = r"[%s]" % "".join(tokenDelimeters)
    # #disallowed punctuation and whitespace
    # disallowed_punc_or_space_regex = r"[%s]" % "".join(disallowedPunctuationOrSpace)
    # #disallowed punctuation
    # disallowedPunctuationRegex = r"[%s]" % "".join(disallowedPunctuation)
    # #not a delimeter (no whitespace or disallowed punc)
    # nondelimeterRegex = r"[^%s]" % "".join(tokenDelimeters)
    # #not a delimeter or punctuation (no punctuation or whitespace)
    # nondelimeterPunctuationRegex = r"[^%s]" % "".join(tokenPunctuationDelimeters)
    # #not a delimeter except space (no whitespace except space, no disallowed punc)

    singleNameRegex = r"(?!{Ds}+.*)({ndp}(?:{nd}*{ndp})?|{ord})".format(
        # disallowed punctuation and whitespace
        Ds=SanitationUtils.disallowed_punc_or_space_regex,
        # not a delimeter (no whitespace or disallowed punc)
        nd=SanitationUtils.nondelimeterRegex,
        # not a delimeter or punctuation (no punctuation or whitespace)
        ndp=SanitationUtils.nondelimeterPunctuationRegex,
        ord=ordinalNumberRegex
    )

    LazyMultiNameNoOrdRegex = "(?!{Ds}+.*)(?:{nd}(?:{nds}*?{nd})?)".format(
        # disallowed punctuation and whitespace
        Ds=SanitationUtils.disallowed_punc_or_space_regex,
        # not a delimeter (no whitespace or disallowed punc)
        nd=SanitationUtils.nondelimeterRegex,
        # not a delimeter except space (no whitespace except space, no
        # disallowed punc)
        nds=SanitationUtils.nondelimeterOrSpaceRegex
    )

    greedyMultiNameNoOrdRegex = "(?!{Ds}+.*)(?:{nd}(?:{nds}*{nd})?)".format(
        Ds=SanitationUtils.disallowed_punc_or_space_regex,
        nd=SanitationUtils.nondelimeterRegex,
        nds=SanitationUtils.nondelimeterOrSpaceRegex
    )

    lazyMultiNameRegex = "((?:{ord} )?{mnr}(?: {ord}(?: {mnr})?)?)".format(
        mnr=LazyMultiNameNoOrdRegex,
        ord=ordinalNumberRegex
    )

    greedyMultiNameRegex = "((?:{ord} )?{mnr}(?: {ord}(?: {mnr})?)?)".format(
        mnr=greedyMultiNameNoOrdRegex,
        ord=ordinalNumberRegex
    )

    titleAbbreviations = OrderedDict([
        ('DR', ['DOCTOR', 'DR.']),
        ('HON', ['HONORABLE', 'HON.']),
        ('REV', ['REVEREND', 'REV.']),
        ('MR', ['MISTER', 'MR.']),
        ('MS', ['MISS', 'MISSES', 'MS.']),
        ('MRS', []),
        ('MX', []),
    ])

    positionAbbreviations = OrderedDict([
        ('OWNER', []),
        ('ACCOUNTANT', ['ACCTS']),
        ('SALES MANAGER', []),
        ('MANAGER', []),
        ('BEAUTICIAN', []),
        ('DIRECTOR', []),
        ('HAIRDRESSER', []),
        ('STYLIST', []),
        ('CEO', []),
        ('FINANCE DEPT', ['FINANCE DEPARTMENT']),
        ('RECEPTION', ['RECEPTION']),
    ])

    noteAbbreviations = OrderedDict([
        ('SPOKE WITH', ['SPIKE WITH', 'SPOKE W', "SPOKE TO"]),
        ('CLOSED', ['CLOSED DOWN', 'CLOSED BUSINESS']),
        ('PRONOUNCED', []),
        ('ARCHIVE', []),
        ('STOCK', ['STOCK ACCOUNT', 'STOCK ACCT', 'STOCK ACCNT']),
        ('ACCOUNT', []),
        ('RETAIL ACCOUNT', []),
        ('STAFF', []),
        ('FINALIST', []),
        ('BOOK A TAN CUSTOMER', []),
        ('SOLD EQUIPMENT', []),
        ("NOT THIS ONE", []),
        ("TECHNOTAN", []),
        ("TECHNICIAN", []),
        ("SPONSORSHIP", []),
        ("TRAINING", []),
        ("OPEN BY APPT ONLY", []),
        ('CUSTOMER', []),
        ('NOTE', []),
        ("N/A", []),
        ('UNSUBSCRIBED', ["UNSUBSCRIBE"]),
    ])

    noteDelimeters = OrderedDict([
        ("-", []),
        (r"&", []),
        (r"\?", []),
        (r"@", []),
        ('AND', ['&AMP']),
        ('OR', []),
    ])

    careOfAbbreviations = OrderedDict([
        ('C/O', ['C/-', 'CARE OF']),
        ('ATTN', ['ATTENTION'])
    ])

    organizationTypeAbbreviations = OrderedDict([
        ('CO', ['COMPANY']),
        ('INC', ['INCORPORATED']),
        ('LTD', ['LIMITED']),
        ('NL', ['NO LIABILITY']),
        ('PTY', ['PROPRIETARY']),
        ('PTY LTD', ['PROPRIETARY LIMITED'])
    ])

    nameSuffixAbbreviations = OrderedDict([
        ('SR', ['SENIOR', 'SR.']),
        ('JR', ['JUNIOR', 'DR.'])
    ])

    familyNamePrefixAbbreviations = OrderedDict([
        ('MC', []),
        ('MAC', []),
        ('VAN DE', []),
        ('VAN DER', []),
        ('VAN DEN', []),
        ('VAN', []),
        ('DER', []),
        ('DI', []),
        ('O', []),
        ('O', []),
    ])

    titleRegex = r"(?P<name_title>%s)\.?" % (
        SanitationUtils.compile_abbrv_regex(titleAbbreviations)
    )

    positionRegex = r"(?P<name_position>%s)\.?" % (
        SanitationUtils.compile_abbrv_regex(positionAbbreviations)
    )

    familyNamePrefixRegex = r"%s" % (
        SanitationUtils.compile_abbrv_regex(familyNamePrefixAbbreviations)
    )

    familyNameRegex = r"(?:(?P<family_name_prefix>%s) )?(?P<family_name>%s)" % (
        familyNamePrefixRegex,
        singleNameRegex
    )

    # valid notes
    # (NOTE_BEFORE names_after_note?)
    # (names_before_note_MIDDLE? NOTE_MIDDLE names_after_note_MIDDLE?)
    # (note_names_only)
    # NOTE_ONLY
    # OTHERS?
    noteRegex = (r"(?:" +
                 r"|".join([
                     r"(?P<name_before_note_paren>{name})?(?P<note_open_paren>\() ?(?:" +
                     r"|".join([
                         r"(?P<note_before>{note})\.? ?(?P<names_after_note>{names})?",
                         r"(?P<names_before_note_middle>{names})? ?(?P<note_middle>{note})\.? ?(?P<names_after_note_middle>{names})?",
                         r"(?P<note_names_only>{names})"
                     ]),
                     r") ?(?P<note_close_paren>\))",
                     r"(?P<note_only>{note})",
                     r"(?P<note_delimeter>{noted}) (?P<names_after_note_delimeter>{names})?"
                 ]) +
                 r")").format(
        note=SanitationUtils.wrap_clear_regex(
            SanitationUtils.compile_abbrv_regex(noteAbbreviations)),
        noted=SanitationUtils.wrap_clear_regex(
            SanitationUtils.compile_abbrv_regex(noteDelimeters)),
        names=lazyMultiNameRegex,
        name=singleNameRegex,
    )

    careOfRegex = r"(?P<careof>%s)[\.:]? ?(?P<careof_names>%s)" % (
        SanitationUtils.compile_abbrv_regex(careOfAbbreviations),
        greedyMultiNameRegex,
    )

    nameSuffixRegex = r"\(?(?P<name_suffix>%s)\.?\)?" % (
        SanitationUtils.compile_abbrv_regex(nameSuffixAbbreviations)
    )

    organizationRegex = r"(?P<organization_name>%s) (?P<organization_type>%s)\.?" % (
        greedyMultiNameRegex,
        SanitationUtils.compile_abbrv_regex(organizationTypeAbbreviations)
    )

    nameTokenRegex = r"(%s)" % "|".join([
        SanitationUtils.wrap_clear_regex(titleRegex),
        SanitationUtils.wrap_clear_regex(positionRegex),
        SanitationUtils.wrap_clear_regex(nameSuffixRegex),
        SanitationUtils.wrap_clear_regex(careOfRegex),
        SanitationUtils.wrap_clear_regex(organizationRegex),
        SanitationUtils.wrap_clear_regex(SanitationUtils.email_regex),
        SanitationUtils.wrap_clear_regex(noteRegex),
        SanitationUtils.wrap_clear_regex(familyNameRegex),
        SanitationUtils.wrap_clear_regex(singleNameRegex),
        SanitationUtils.wrap_clear_regex(ordinalNumberRegex),
        SanitationUtils.disallowedPunctuationRegex
    ])

    @staticmethod
    def identify_title(string):
        return SanitationUtils.identify_abbreviation(
            NameUtils.titleAbbreviations, string)

    @staticmethod
    def identify_note(string):
        return SanitationUtils.identify_abbreviation(
            NameUtils.noteAbbreviations, string)

    @staticmethod
    def identify_position(string):
        return SanitationUtils.identify_abbreviation(
            NameUtils.positionAbbreviations, string)

    @staticmethod
    def identify_name_suffix(string):
        return SanitationUtils.identify_abbreviation(
            NameUtils.nameSuffixAbbreviations, string)

    @staticmethod
    def identify_care_of(string):
        return SanitationUtils.identify_abbreviation(
            NameUtils.careOfAbbreviations, string)

    @staticmethod
    def identify_organization(string):
        return SanitationUtils.identify_abbreviation(
            NameUtils.organizationTypeAbbreviations, string)

    @staticmethod
    def sanitize_name_token(string):
        return SanitationUtils.normalize_val(string)

    @staticmethod
    def get_single_name(token):
        match = re.match(
            SanitationUtils.wrap_clear_regex(
                NameUtils.singleNameRegex
            ),
            token
        )
        match_grps = match.groups() if match else None
        if(match_grps):
            # name = " ".join(match_grps)
            name = match_grps[0]
            if Registrar.DEBUG_NAME:
                SanitationUtils.safe_print("FOUND NAME " + repr(name))
            return name

    @staticmethod
    def get_single_names(token):
        matches = re.findall(
            SanitationUtils.wrap_clear_regex(
                NameUtils.singleNameRegex
            ),
            token
        )
        names = [match[0] for match in filter(None, matches)]
        if names:
            if Registrar.DEBUG_NAME:
                SanitationUtils.safe_print("FOUND NAMES " + repr(names))
            return names

    @staticmethod
    def get_multi_name(token):
        match = re.match(
            SanitationUtils.wrap_clear_regex(
                NameUtils.greedyMultiNameRegex
            ),
            token
        )
        match_grps = match.groups() if match else None
        if(match_grps):
            # name = " ".join(match_grps)
            name = match_grps[0]
            if Registrar.DEBUG_NAME:
                SanitationUtils.safe_print("FOUND NAME " + repr(name))
            return name

    @staticmethod
    def get_email(token):
        # if Registrar.DEBUG_NAME: SanitationUtils.safe_print("checking email", token)
        match = re.match(
            SanitationUtils.wrap_clear_regex(
                "({})".format(SanitationUtils.email_regex)
            ),
            token
        )
        match_grps = match.groups() if match else None
        if(match_grps):
            # if Registrar.DEBUG_NAME: SanitationUtils.safe_print("email matches", repr(match_grps))
            # name = " ".join(match_grps)
            email = match_grps[0]
            if Registrar.DEBUG_NAME:
                SanitationUtils.safe_print("FOUND EMAIL " + repr(email))
            return email

    @staticmethod
    def get_title(token):
        match = re.match(
            SanitationUtils.wrap_clear_regex(
                NameUtils.titleRegex
            ),
            token
        )
        match_dict = match.groupdict() if match else None
        if match_dict and match_dict.get('name_title'):
            title = NameUtils.identify_title(match_dict['name_title'])
            if Registrar.DEBUG_NAME:
                print "FOUND TITLE ", repr(title)
            return title
        # match_grps = match.groups() if match else None
        # if(match_grps):
        #     # title = " ".join(match_grps)
        #     title = match_grps[0]
        #     if Registrar.DEBUG_NAME: print "FOUND TITLE ", repr(title)
        #     return title

    @staticmethod
    def get_position(token):
        match = re.match(
            SanitationUtils.wrap_clear_regex(
                NameUtils.positionRegex
            ),
            token
        )
        match_dict = match.groupdict() if match else None
        if match_dict and match_dict.get('name_position'):
            position = NameUtils.identify_position(match_dict['name_position'])
            if Registrar.DEBUG_NAME:
                print "FOUND POSITION ", repr(position)
            return position
        # match_grps = match.groups() if match else None
        # if(match_grps):
        #     # position = " ".join(match_grps)
        #     position = match_grps[0]
        #     if Registrar.DEBUG_NAME: print "FOUND POSITION ", repr(position)
        #     return position

    @staticmethod
    def get_ordinal(token):
        match = re.match(
            SanitationUtils.wrap_clear_regex(
                NameUtils.ordinalNumberRegex
            ),
            token
        )
        match_grps = match.groups() if match else None
        if match_grps:
            ordinal = match_grps[0]
            if Registrar.DEBUG_NAME:
                SanitationUtils.safe_print("FOUND ORDINAL", ordinal)
            return ordinal

    @staticmethod
    def get_name_suffix(token):
        match = re.match(
            SanitationUtils.wrap_clear_regex(
                NameUtils.nameSuffixRegex
            ),
            token
        )
        match_dict = match.groupdict() if match else None
        if match_dict and match_dict.get('name_suffix'):
            suffix = NameUtils.identify_name_suffix(match_dict['name_suffix'])
            if Registrar.DEBUG_NAME:
                print "FOUND NAME SUFFIX ", repr(suffix)
            return suffix
        # match_grps = match.groups() if match else None
        # if(match_grps):
        #     # position = " ".join(match_grps)
        #     suffix = match_grps[0]
        #     if Registrar.DEBUG_NAME: print "FOUND NAME SUFFIX ", repr(suffix)
        #     return suffix

    @staticmethod
    def get_note(token):
        match = re.match(
            SanitationUtils.wrap_clear_regex(
                NameUtils.noteRegex
            ),
            token
        )
        match_dict = match.groupdict() if match else None
        if match_dict and (match_dict.get('note_open_paren') or match_dict.get(
                'note_only') or match_dict.get('note_delimeter')):
            note_open_paren = match_dict.get('note_open_paren')
            note_close_paren = match_dict.get('note_close_paren')
            names_before_note = None
            names_after_note = None
            if note_open_paren:
                if match_dict.get('note_before'):
                    note = NameUtils.identify_note(match_dict.get('note_only'))
                    names_after_note = match_dict.get('names_after_note')
                elif match_dict.get('note_middle'):
                    names_before_note = match_dict.get(
                        'names_before_note_middle')
                    note = NameUtils.identify_note(
                        match_dict.get('note_middle'))
                    names_after_note = match_dict.get(
                        'names_after_note_middle')
                else:
                    names_before_note = match_dict.get('note_names_only')
                    note = None
                name_before_note_paren = match_dict.get(
                    'name_before_note_paren')
                if name_before_note_paren:
                    names_before_note = " ".join(
                        filter(None, [name_before_note_paren, names_before_note]))
            elif match_dict.get('note_only'):
                note = NameUtils.identify_note(match_dict.get('note_only'))
            elif match_dict.get('note_delimeter'):
                note = match_dict.get('note_delimeter')
                names_after_note = match_dict.get('names_after_note_delimeter')

            note_tuple = (note_open_paren, names_before_note,
                          note, names_after_note, note_close_paren)
            if Registrar.DEBUG_NAME:
                print "FOUND NOTE ", repr(note_tuple)
            return note_tuple
        # match_grps = match.groups() if match else None
        # if(match_grps):
        #     # note = " ".join(match_grps)
        #     note = match_grps[0]
        #     return note

    @staticmethod
    def get_family_name(token):
        match = re.match(
            SanitationUtils.wrap_clear_regex(
                NameUtils.familyNameRegex
            ),
            token
        )
        match_dict = match.groupdict() if match else None
        if match_dict and match_dict.get('family_name'):
            family_name = match_dict['family_name']
            family_name_prefix = match_dict.get('family_name_prefix')
            for component in [family_name_prefix, family_name]:
                if Registrar.DEBUG_NAME:
                    print "name component", repr(component)
            combined_family_name = " ".join(
                filter(None, [family_name_prefix, family_name]))
            if Registrar.DEBUG_NAME:
                SanitationUtils.safe_print(
                    "FOUND FAMILY NAME", combined_family_name)
            return combined_family_name

    @staticmethod
    def get_care_of(token):
        match = re.match(
            SanitationUtils.wrap_clear_regex(
                NameUtils.careOfRegex
            ),
            token
        )
        match_dict = match.groupdict() if match else None
        if match_dict and match_dict.get('careof'):
            careof = NameUtils.identify_care_of(match_dict.get('careof'))
            names = match_dict.get('careof_names')
            careof_tuple = (careof, names)
            if Registrar.DEBUG_NAME:
                print "FOUND CAREOF ", repr(careof_tuple)
            return careof_tuple
        # match_grps = match.groups() if match else None
        # if(match_grps):
        #     # note = " ".join(match_grps)
        #     careof = match_grps[0]
        #     if Registrar.DEBUG_NAME: print "FOUND CAREOF ", repr(careof)
        #     return careof

    @staticmethod
    def get_organization(token):
        match = re.match(
            SanitationUtils.wrap_clear_regex(
                NameUtils.organizationRegex
            ),
            token
        )
        match_dict = match.groupdict() if match else None
        if match_dict and (match_dict.get('organization_name')
                           and match_dict.get('organization_type')):
            organization_name = match_dict.get('organization_name')
            organization_type = match_dict.get('organization_type')
            organization = (organization_name, organization_type)
            if Registrar.DEBUG_NAME:
                print "FOUND ORGANIZATION ", repr(organization)
            return organization

    @staticmethod
    def tokenize_name(string):
        string = string.upper()
        matches = re.findall(
            NameUtils.nameTokenRegex,
            string
        )
        # if Registrar.DEBUG_NAME: print repr(matches)
        return map(
            lambda match: NameUtils.sanitize_name_token(match[0]),
            matches
        )


def test_name_utils():
    pass
    # print SanitationUtils.compile_abbrv_regex(NameUtils.noteAbbreviations)
    # print NameUtils.tokenize_name('DERWENT (ACCT)')
    # print NameUtils.get_email('KYLIESWEET@GMAIL.COM')

    # assert r'\'' in SanitationUtils.allowedPunctuation
    # assert r'\'' not in SanitationUtils.disallowedPunctuation
    # assert r'\'' not in SanitationUtils.tokenDelimeters
    #
    # print SanitationUtils.tokenDelimeters
    #
    # match = re.match(
    #     '(' + SanitationUtils.nondelimeterRegex + ')',
    #     '\''
    # )
    # if match: print "nondelimeterRegex", [match_item for match_item in match.groups()]
    #
    # match = re.match(
    #     '(' + SanitationUtils.delimeterRegex + ')',
    #     '\''
    # )
    # if match: print "delimeterRegex", [match_item for match_item in match.groups()]
    #
    # match = re.match(
    #     NameUtils.singleNameRegex,
    #     'OCAL\'LAGHAN'
    # )
    # if match: print [match_item for match_item in match.groups()]

    # print "singlename", repr( NameUtils.get_single_name('O\'CALLAGHAN' ))
    # def testNotes(line):
    #     for token in NameUtils.tokenize_name(line):
    #         print token, NameUtils.get_note(token)
    #
    # testNotes("DE-RWENT- FINALIST")
    # testNotes("JAGGERS HAIR- DO NOT WANT TO BE CALLED!!!!")


class AddressUtils:
    subunitAbbreviations = OrderedDict([
        # ('ANT',     ['ANTENNA']),
        ('APARTMENT', ['APT', 'A']),
        # ('ATM',     ['AUTOMATED TELLER MACHINE']),
        ('BBQ', ['BARBECUE']),
        # ('BTSD',    ['BOATSHED']),
        ('BUILDING', ['BLDG']),
        # ('BNGW',    ['BUNGALOW']),
        # ('CAGE',    []),
        # ('CARP',    ['CARPARK']),
        # ('CARS',    ['CARSPACE']),
        # ('CLUB',    []),
        # ('COOL',    ['COOLROOM']),
        ('COTTAGE', ['CTGE']),
        ('DUPLEX', ['DUP', 'DUPL']),
        ('FACTORY', ['FCTY', 'FY']),
        ('FLAT', ['FLT', 'FL', 'F']),
        ('GARAGE', ['GRGE']),
        ('HALL', []),
        ('HOUSE', ['HSE']),
        ('KIOSK', ['KSK']),
        ('LEASE', ['LSE']),
        ('LOBBY', ['LBBY']),
        ('LOFT', []),
        ('LOT', []),
        ('MAISONETTE', ['MSNT']),
        ('MBTH', ['MARINE BERTH', 'MB']),
        ('OFFICE', ['OFFC', 'OFF']),
        ('PENTHOUSE', ['PTHS']),
        ('REAR', ['R']),
        # ('RESV',    ['RESERVE']),
        ('ROOM', ['RM']),
        ('SHED', []),
        ('SHOP', ['SH', 'SP', 'SHP']),
        ('SHRM', ['SHOWROOM']),
        # ('SIGN',    []),
        ('SITE', []),
        ('STALL', ['STLL', 'SL']),
        ('STORE', ['STOR']),
        ('STR', ['STRATA UNIT']),
        ('STUDIO', ['STU', 'STUDIO APARTMENT']),
        ('SUBS', ['SUBSTATION']),
        ('SUITE', ['SE']),
        ('TNCY', ['TENANCY']),
        ('TWR', ['TOWER']),
        ('TOWNHOUSE', ['TNHS']),
        ('UNIT', ['U']),
        ('VLT', ['VAULT']),
        ('VILLA', ['VLLA']),
        ('WARD', []),
        ('WAREHOUSE', ['WHSE', 'WE']),
        ('WKSH', ['WORKSHOP'])
    ])

    stateAbbreviations = OrderedDict([
        ('AAT', ['AUSTRALIAN ANTARCTIC TERRITORY']),
        ('ACT', ['AUSTRALIAN CAPITAL TERRITORY', 'AUS CAPITAL TERRITORY']),
        ('NSW', ['NEW SOUTH WALES']),
        ('NT', ['NORTHERN TERRITORY']),
        ('QLD', ['QUEENSLAND']),
        ('SA', ['SOUTH AUSTRALIA']),
        ('TAS', ['TASMAIA']),
        ('VIC', ['VICTORIA']),
        ('WA', ['WESTERN AUSTRALIA', 'WEST AUSTRALIA', 'WEST AUS']),
    ])

    floorAbbreviations = OrderedDict([
        ('B', ['BASEMENT']),
        ('G', ['GROUND FLOOR', 'GROUND']),
        ('LG', ['LOWER GROUND FLOOR', 'LOWER GROUND']),
        ('UG', ['UPPER GROUND FLOOR', 'UPPER GROUND', 'UPPER LEVEL']),
        ('FL', ['FLOOR', 'FLR']),
        ('LEVEL', ['LVL', 'L']),
        ('M', ['MEZZANINE', 'MEZ'])
    ])

    thoroughfareTypeAbbreviations = OrderedDict([
        ('ACCS', ['ACCESS']),
        ('ALLY', ['ALLEY']),
        ('ALWY', ['ALLEYWAY']),
        ('AMBL', ['AMBLE']),
        ('ANCG', ['ANCHORAGE']),
        ('APP', ['APPROACH']),
        ('ARC', ['ARCADE']),
        ('ARTL', ['ARTERIAL']),
        ('ARTY', ['ARTERY', 'ART']),
        ('AVE', ['AVENUE', 'AV']),
        ('BASN', ['BASIN']),
        ('BA', ['BANAN']),
        ('BCH', ['BEACH']),
        ('BEND', []),
        ('BWLK', ['BOARDWALK']),
        ('BLVD', ['BOULEVARD', 'BLVD']),
        ('BR', ['BRACE']),
        ('BRAE', []),
        ('BRK', ['BREAK']),
        ('BROW', []),
        ('BYPA', ['BYPASS']),
        ('BYWY', ['BYWAY']),
        ('CSWY', ['CAUSEWAY']),
        ('CTR', ['CENTRE']),
        ('CH', ['CHASE']),
        ('CIR', ['CIRCLE', 'CCLE']),
        ('CCT', ['CIRCUIT']),
        ('CRCS', ['CIRCUS']),
        ('CL', ['CLOSE']),
        ('CON', ['CONCOURSE']),
        ('CPS', ['COPSE']),
        ('CNR', ['CORNER']),
        ('CT', ['COURT', 'CRT']),
        ('CTYD', ['COURTYARD']),
        ('COVE', []),
        ('CRES', ['CRESCENT', 'CR', 'CRESENT', 'CRS']),
        ('CRST', ['CREST']),
        ('CRSS', ['CROSS']),
        ('CSAC', ['CUL-DE-SAC']),
        ('CUTT', ['CUTTING']),
        ('DALE', []),
        ('DIP', []),
        ('DR', ['DRIVE']),
        ('DVWY', ['DRIVEWAY']),
        ('EDGE', []),
        ('ELB', ['ELBOW']),
        ('END', []),
        ('ENT', ['ENTRANCE']),
        ('ESP', ['ESPLANADE']),
        ('EXP', ['EXPRESSWAY']),
        ('FAWY', ['FAIRWAY']),
        ('FOLW', ['FOLLOW']),
        ('FTWY', ['FOOTWAY']),
        ('FORM', ['FORMATION']),
        ('FWY', ['FREEWAY']),
        ('FRTG', ['FRONTAGE']),
        ('GAP', []),
        ('GDNS', ['GARDENS', 'GARDEN']),
        ('GTE', ['GATE']),
        ('GLDE', ['GLADE']),
        ('GLEN', []),
        ('GRA', ['GRANGE']),
        ('GRN', ['GREEN']),
        ('GR', ['GROVE']),
        ('HTS', ['HEIGHTS']),
        ('HIRD', ['HIGHROAD']),
        ('HWY', ['HIGHWAY', 'HGWY', 'HWAY', 'H\'WAY']),
        ('HILL', []),
        ('INTG', ['INTERCHANGE']),
        ('JNC', ['JUNCTION']),
        ('KEY', []),
        ('LANE', []),
        ('LNWY', ['LANEWAY']),
        ('LINE', []),
        ('LINK', []),
        ('LKT', ['LOOKOUT', 'LOOK OUT']),
        ('LOOP', []),
        ('MALL', []),
        ('MNDR', ['MEANDER']),
        ('MEWS', []),
        ('MTWY', ['MOTORWAY']),
        ('NOOK', []),
        ('OTLK', ['OUTLOOK']),
        ('PDE', ['PARADE']),
        ('PARK', []),
        ('PWY', ['PARKWAY']),
        ('PASS', []),
        ('PSGE', ['PASSAGE']),
        ('PATH', []),
        ('PWAY', ['PATHWAY']),
        ('PIAZ', ['PIAZZA']),
        ('PL', ['PLACE', 'PLCE']),
        ('PLZA', ['PLAZA']),
        ('PKT', ['POCKET']),
        ('PNT', ['POINT']),
        ('PORT', []),
        ('PROM', ['PROMENADE']),
        ('QDRT', ['QUADRANT']),
        ('QYS', ['QUAYS']),
        ('RMBL', ['RAMBLE']),
        ('REST', []),
        ('RTT', ['RETREAT']),
        ('RDGE', ['RIDGE']),
        ('RISE', []),
        ('RD', ['ROAD']),
        ('RTY', ['ROTARY']),
        ('RTE', ['ROUTE']),
        ('ROW', []),
        ('RUE', []),
        ('SVWY', ['SERVICEWAY']),
        ('SHUN', ['SHUNT']),
        ('SPUR', []),
        ('SQ', ['SQUARE']),
        ('ST', ['STREET']),
        ('STRAIGHT', []),
        ('SBWY', ['SUBWAY']),
        ('TARN', []),
        ('TCE', ['TERRACE']),
        ('THFR', ['THOROUGHFARE']),
        ('TLWY', ['TOLLWAY']),
        ('TOP', []),
        ('TOR', []),
        ('TRK', ['TRACK']),
        ('TRL', ['TRAIL']),
        ('TURN', []),
        ('UPAS', ['UNDERPASS']),
        ('VALE', []),
        ('VIAD', ['VIADUCT']),
        ('VIEW', []),
        ('VSTA', ['VISTA']),
        ('WALK', []),
        ('WAY', ['WY']),
        ('WKWY', ['WALKWAY']),
        ('WHRF', ['WHARF']),
        ('WYND', [])
    ])

    thoroughfareSuffixAbbreviations = OrderedDict([
        ('CN', ['CENTRAL']),
        ('E', ['EAST']),
        ('EX', ['EXTENSION']),
        ('LR', ['LOWER']),
        ('N', ['NORTH']),
        ('NE', ['NORTH EAST']),
        ('NW', ['NORTH WEST']),
        ('S', ['SOUTH']),
        ('SE', ['SOUTH EAST']),
        ('SW', ['SOUTH WEST']),
        ('UP', ['UPPER']),
        ('W', ['WEST'])
    ])

    buildingTypeAbbreviations = OrderedDict([
        ('SHOPPING CENTRE', ["S/C", r"SHOP.? CENTRE", "SHOPNG CENTRE"]),
        ('SHOPPING CENTER', [r"SHOP.? CENTER", "SHOPNG CENTER"]),
        ('SHOPPING CTR', [r"SHOP.? CTR", "SHOPNG CTR"]),
        ("SHOPPING CTNR", [r"SHOP.? CTR", "SHOPNG CTNR"]),
        ('PLAZA', ['PLZA']),
        ('ARCADE', ["ARC"]),
        ('MALL', []),
        ('BUILDING', ['BLDG']),
        ('FORUM', []),
        ('HOUSE', []),
        ('CENTER', []),
        ('CENTRE', []),
        ('FORUM', []),
        ('CTR', ["CNTR"]),
    ])

    deliveryTypeAbbreviations = OrderedDict([
        ('CARE PO', []),
        ('CMA', []),
        ('CMB', []),
        ('CPA', []),
        ('GPO BOX', [r"G\.?P\.?O(\.| )BOX", "GENERAL POST OFFICE BOX"]),
        ('LOCKED BAG', []),
        ('PO BOX', [r"P\.?O\.? ?BOX"]),
        ('PO', []),
        ('RMB', []),
        ('RMS', []),
        ('MS', []),
        ('PRIVATE BAG', []),
        ('PARCEL LOCKER', []),
    ])

    countryAbbreviations = OrderedDict([
        ('AF', ['AFGHANISTAN']),
        ('AL', ['ALBANIA']),
        ('DZ', ['ALGERIA']),
        ('AS', ['AMERICAN SAMOA']),
        ('AD', ['ANDORRA']),
        ('AO', ['ANGOLA']),
        ('AI', ['ANGUILLA']),
        ('AQ', ['ANTARCTICA']),
        ('AG', ['ANTIGUA AND BARBUDA']),
        ('AR', ['ARGENTINA']),
        ('AM', ['ARMENIA']),
        ('AW', ['ARUBA']),
        ('AU', ['AUSTRALIA']),
        ('AT', ['AUSTRIA']),
        ('AZ', ['AZERBAIJAN']),
        ('BS', ['BAHAMAS']),
        ('BH', ['BAHRAIN']),
        ('BD', ['BANGLADESH']),
        ('BB', ['BARBADOS']),
        ('BY', ['BELARUS']),
        ('BE', ['BELGIUM']),
        ('BZ', ['BELIZE']),
        ('BJ', ['BENIN']),
        ('BM', ['BERMUDA']),
        ('BT', ['BHUTAN']),
        ('BO', ['BOLIVIA']),
        ('BQ', ['BONAIRE']),
        ('BA', ['BOSNIA AND HERZEGOVINA']),
        ('BW', ['BOTSWANA']),
        ('BV', ['BOUVET ISLAND']),
        ('BR', ['BRAZIL']),
        ('IO', ['BRITISH INDIAN OCEAN TERRITORY']),
        ('BN', ['BRUNEI DARUSSALAM']),
        ('BG', ['BULGARIA']),
        ('BF', ['BURKINA FASO']),
        ('BI', ['BURUNDI']),
        ('KH', ['CAMBODIA']),
        ('CM', ['CAMEROON']),
        ('CA', ['CANADA']),
        ('CV', ['CAPE VERDE']),
        ('KY', ['CAYMAN ISLANDS']),
        ('CF', ['CENTRAL AFRICAN REPUBLIC']),
        ('TD', ['CHAD']),
        ('CL', ['CHILE']),
        ('CN', ['CHINA']),
        ('CX', ['CHRISTMAS ISLAND']),
        ('CC', ['COCOS (KEELING) ISLANDS']),
        ('CO', ['COLOMBIA']),
        ('KM', ['COMOROS']),
        ('CG', ['CONGO']),
        ('CD', ['DEMOCRATIC REPUBLIC OF THE CONGO']),
        ('CK', ['COOK ISLANDS']),
        ('CR', ['COSTA RICA']),
        ('HR', ['CROATIA']),
        ('CU', ['CUBA']),
        ('CY', ['CYPRUS']),
        ('CZ', ['CZECH REPUBLIC']),
        ('DK', ['DENMARK']),
        ('DJ', ['DJIBOUTI']),
        ('DM', ['DOMINICA']),
        ('DO', ['DOMINICAN REPUBLIC']),
        ('EC', ['ECUADOR']),
        ('EG', ['EGYPT']),
        ('SV', ['EL SALVADOR']),
        ('GQ', ['EQUATORIAL GUINEA']),
        ('ER', ['ERITREA']),
        ('EE', ['ESTONIA']),
        ('ET', ['ETHIOPIA']),
        ('FK', ['FALKLAND ISLANDS (MALVINAS)']),
        ('FO', ['FAROE ISLANDS']),
        ('FJ', ['FIJI']),
        ('FI', ['FINLAND']),
        ('FR', ['FRANCE']),
        ('GF', ['FRENCH GUIANA']),
        ('PF', ['FRENCH POLYNESIA']),
        ('TF', ['FRENCH SOUTHERN TERRITORIES']),
        ('GA', ['GABON']),
        ('GM', ['GAMBIA']),
        ('GE', ['GEORGIA']),
        ('DE', ['GERMANY']),
        ('GH', ['GHANA']),
        ('GI', ['GIBRALTAR']),
        ('GR', ['GREECE']),
        ('GL', ['GREENLAND']),
        ('GD', ['GRENADA']),
        ('GP', ['GUADELOUPE']),
        ('GU', ['GUAM']),
        ('GT', ['GUATEMALA']),
        ('GG', ['GUERNSEY']),
        ('GN', ['GUINEA']),
        ('GW', ['GUINEA-BISSAU']),
        ('GY', ['GUYANA']),
        ('HT', ['HAITI']),
        ('HM', ['HEARD ISLAND AND MCDONALD MCDONALD ISLANDS']),
        ('VA', ['HOLY SEE (VATICAN CITY STATE)']),
        ('HN', ['HONDURAS']),
        ('HK', ['HONG KONG']),
        ('HU', ['HUNGARY']),
        ('IS', ['ICELAND']),
        ('IN', ['INDIA']),
        ('ID', ['INDONESIA']),
        ('IR', ['IRAN, ISLAMIC REPUBLIC OF']),
        ('IQ', ['IRAQ']),
        ('IE', ['IRELAND']),
        ('IM', ['ISLE OF MAN']),
        ('IL', ['ISRAEL']),
        ('IT', ['ITALY']),
        ('JM', ['JAMAICA']),
        ('JP', ['JAPAN']),
        ('JE', ['JERSEY']),
        ('JO', ['JORDAN']),
        ('KZ', ['KAZAKHSTAN']),
        ('KE', ['KENYA']),
        ('KI', ['KIRIBATI']),
        ('KP', ['KOREA, DEMOCRATIC PEOPLE\'S REPUBLIC OF']),
        ('KR', ['KOREA, REPUBLIC OF']),
        ('KW', ['KUWAIT']),
        ('KG', ['KYRGYZSTAN']),
        ('LA', ['LAO PEOPLE\'S DEMOCRATIC REPUBLIC']),
        ('LV', ['LATVIA']),
        ('LB', ['LEBANON']),
        ('LS', ['LESOTHO']),
        ('LR', ['LIBERIA']),
        ('LY', ['LIBYA']),
        ('LI', ['LIECHTENSTEIN']),
        ('LT', ['LITHUANIA']),
        ('LU', ['LUXEMBOURG']),
        ('MO', ['MACAO']),
        ('MK', ['MACEDONIA, THE FORMER YUGOSLAV REPUBLIC OF']),
        ('MG', ['MADAGASCAR']),
        ('MW', ['MALAWI']),
        ('MY', ['MALAYSIA']),
        ('MV', ['MALDIVES']),
        ('ML', ['MALI']),
        ('MT', ['MALTA']),
        ('MH', ['MARSHALL ISLANDS']),
        ('MQ', ['MARTINIQUE']),
        ('MR', ['MAURITANIA']),
        ('MU', ['MAURITIUS']),
        ('YT', ['MAYOTTE']),
        ('MX', ['MEXICO']),
        ('FM', ['MICRONESIA, FEDERATED STATES OF']),
        ('MD', ['MOLDOVA, REPUBLIC OF']),
        ('MC', ['MONACO']),
        ('MN', ['MONGOLIA']),
        ('ME', ['MONTENEGRO']),
        ('MS', ['MONTSERRAT']),
        ('MA', ['MOROCCO']),
        ('MZ', ['MOZAMBIQUE']),
        ('MM', ['MYANMAR']),
        ('NA', ['NAMIBIA']),
        ('NR', ['NAURU']),
        ('NP', ['NEPAL']),
        ('NL', ['NETHERLANDS']),
        ('NC', ['NEW CALEDONIA']),
        ('NZ', ['NEW ZEALAND']),
        ('NI', ['NICARAGUA']),
        ('NE', ['NIGER']),
        ('NG', ['NIGERIA']),
        ('NU', ['NIUE']),
        ('NF', ['NORFOLK ISLAND']),
        ('MP', ['NORTHERN MARIANA ISLANDS']),
        ('NO', ['NORWAY']),
        ('OM', ['OMAN']),
        ('PK', ['PAKISTAN']),
        ('PW', ['PALAU']),
        ('PS', ['PALESTINE, STATE OF']),
        ('PA', ['PANAMA']),
        ('PG', ['PAPUA NEW GUINEA']),
        ('PY', ['PARAGUAY']),
        ('PE', ['PERU']),
        ('PH', ['PHILIPPINES']),
        ('PN', ['PITCAIRN']),
        ('PL', ['POLAND']),
        ('PT', ['PORTUGAL']),
        ('PR', ['PUERTO RICO']),
        ('QA', ['QATAR']),
        ('RO', ['ROMANIA']),
        ('RU', ['RUSSIAN FEDERATION']),
        ('RW', ['RWANDA']),
        ('RE', ['REUNION']),
        ('BL', ['SAINT BARTHALEMY']),
        ('SH', ['SAINT HELENA']),
        ('KN', ['SAINT KITTS AND NEVIS']),
        ('LC', ['SAINT LUCIA']),
        ('MF', ['SAINT MARTIN (FRENCH PART)']),
        ('PM', ['SAINT PIERRE AND MIQUELON']),
        ('VC', ['SAINT VINCENT AND THE GRENADINES']),
        ('WS', ['SAMOA']),
        ('SM', ['SAN MARINO']),
        ('ST', ['SAO TOME AND PRINCIPE']),
        ('SA', ['SAUDI ARABIA']),
        ('SN', ['SENEGAL']),
        ('RS', ['SERBIA']),
        ('SC', ['SEYCHELLES']),
        ('SL', ['SIERRA LEONE']),
        ('SG', ['SINGAPORE']),
        ('SX', ['SINT MAARTEN (DUTCH PART)']),
        ('SK', ['SLOVAKIA']),
        ('SI', ['SLOVENIA']),
        ('SB', ['SOLOMON ISLANDS']),
        ('SO', ['SOMALIA']),
        ('ZA', ['SOUTH AFRICA']),
        ('GS', ['SOUTH GEORGIA AND THE SOUTH SANDWICH ISLANDS']),
        ('SS', ['SOUTH SUDAN']),
        ('ES', ['SPAIN']),
        ('LK', ['SRI LANKA']),
        ('SD', ['SUDAN']),
        ('SR', ['SURINAME']),
        ('SJ', ['SVALBARD AND JAN MAYEN']),
        ('SZ', ['SWAZILAND']),
        ('SE', ['SWEDEN']),
        ('CH', ['SWITZERLAND']),
        ('SY', ['SYRIAN ARAB REPUBLIC']),
        ('TW', ['TAIWAN, PROVINCE OF CHINA']),
        ('TJ', ['TAJIKISTAN']),
        ('TZ', ['UNITED REPUBLIC OF TANZANIA']),
        ('TH', ['THAILAND']),
        ('TL', ['TIMOR-LESTE']),
        ('TG', ['TOGO']),
        ('TK', ['TOKELAU']),
        ('TO', ['TONGA']),
        ('TT', ['TRINIDAD AND TOBAGO']),
        ('TN', ['TUNISIA']),
        ('TR', ['TURKEY']),
        ('TM', ['TURKMENISTAN']),
        ('TC', ['TURKS AND CAICOS ISLANDS']),
        ('TV', ['TUVALU']),
        ('UG', ['UGANDA']),
        ('UA', ['UKRAINE']),
        ('AE', ['UNITED ARAB EMIRATES']),
        ('GB', ['UNITED KINGDOM']),
        ('US', ['UNITED STATES']),
        ('UM', ['UNITED STATES MINOR OUTLYING ISLANDS']),
        ('UY', ['URUGUAY']),
        ('UZ', ['UZBEKISTAN']),
        ('VU', ['VANUATU']),
        ('VE', ['VENEZUELA']),
        ('VN', ['VIET NAM']),
        ('VG', ['BRITISH VIRGIN ISLANDS']),
        ('VI', ['US VIRGIN ISLANDS']),
        ('WF', ['WALLIS AND FUTUNA']),
        ('EH', ['WESTERN SAHARA']),
        ('YE', ['YEMEN']),
        ('ZM', ['ZAMBIA']),
        ('ZW', ['ZIMBABWE']),
        ('AX', ['ALAND ISLANDS'])
    ])

    numberRegex = r"(\d+(?:,\d+)*)"
    alphaRegex = r"[A-Z]"
    numberRangeRegex = r"{0} ?(?:[-&]|TO) ?{0}".format(
        numberRegex
    )
    numberAlphaRegex = r"{0} ?(?:{1})".format(
        numberRegex,
        alphaRegex
    )
    numberSlashRegex = r"{0} ?/ ?{0}".format(
        numberRegex
    )
    alphaNumberRegex = r"{1}{0}".format(
        numberRegex,
        alphaRegex
    )
    alphaNumberAlphaRegex = r"{1}{0}{1}".format(
        numberRegex,
        alphaRegex
    )
    slashAbbrvRegex = r"{0}/{0}+".format(
        alphaRegex
    )
    singleNumberRegex = r"(%s)" % "|".join([
        numberAlphaRegex,
        numberRegex
    ])
    singleAlphaNumberRegex = r"(%s)" % "|".join([
        numberAlphaRegex,
        numberRegex,
        alphaRegex
    ])
    singleAlphaNumberAlphaRegex = r"(%s)" % "|".join([
        numberAlphaRegex,
        numberRegex,
        alphaNumberAlphaRegex,
        alphaRegex
    ])
    multiNumberRegex = r"(%s)" % "|".join([
        numberAlphaRegex,
        numberRangeRegex,
        numberRegex
    ])
    multiNumberSlashRegex = r"(%s)" % "|".join([
        numberAlphaRegex,
        numberRangeRegex,
        numberSlashRegex,
        numberRegex
    ])
    multiNumberAlphaRegex = r"(%s)" % "|".join([
        numberAlphaRegex,
        numberRangeRegex,
        numberRegex,
        alphaNumberRegex,
    ])
    multiAlphaNumberAlphaRegex = r"(%s)" % "|".join([
        numberAlphaRegex,
        numberRangeRegex,
        numberRegex,
        alphaNumberRegex,
        alphaNumberAlphaRegex,
    ])
    multiNumberAllRegex = r"(%s)" % "|".join([
        numberAlphaRegex,
        numberRangeRegex,
        numberSlashRegex,
        numberRegex,
        alphaNumberRegex,
    ])

    floorLevelRegex = r"(?:(?P<floor_prefix>FLOOR|LEVEL|LVL)\.? )?(?P<floor_type>%s)\.? ?(?P<floor_number>%s)" % (
        SanitationUtils.compile_abbrv_regex(floorAbbreviations),
        singleAlphaNumberRegex,
    )
    subunitTypeRegexNamed = "(?P<subunit_type>%s)" % (
        SanitationUtils.compile_abbrv_regex(subunitAbbreviations)
    )
    subunitRegex = r"(?P<subunit_type>%s) ?(?P<subunit_number>(?:%s)/?)" % (
        SanitationUtils.compile_abbrv_regex(subunitAbbreviations),
        multiAlphaNumberAlphaRegex,
    )
    weakSubunitRegex = r"(?P<weak_subunit_type>%s) ?(?P<weak_subunit_number>(?:%s)/?)" % (
        NameUtils.singleNameRegex,
        multiAlphaNumberAlphaRegex,
    )
    stateRegex = r"(%s)" % SanitationUtils.compile_abbrv_regex(
        stateAbbreviations)
    thoroughfareNameRegex = r"%s" % (
        "|".join([
            NameUtils.greedyMultiNameRegex,
            NameUtils.ordinalNumberRegex,
        ])
    )
    thoroughfareTypeRegex = r"%s" % (
        SanitationUtils.compile_abbrv_regex(thoroughfareTypeAbbreviations)
    )
    thoroughfareTypeRegexNamed = r"(?P<thoroughfare_type>%s)" % (
        SanitationUtils.compile_abbrv_regex(thoroughfareTypeAbbreviations)
    )
    thoroughfareSuffixRegex = r"%s" % (
        SanitationUtils.compile_abbrv_regex(thoroughfareSuffixAbbreviations)
    )
    thoroughfareRegex = r"(?P<thoroughfare_number>{0})\s+(?P<thoroughfare_name>{1})\s+(?P<thoroughfare_type>{2})\.?(?:\s+(?P<thoroughfare_suffix>{3}))?".format(
        multiNumberSlashRegex,
        thoroughfareNameRegex,
        thoroughfareTypeRegex,
        thoroughfareSuffixRegex
    )
    weakThoroughfareRegex = r"(?P<weak_thoroughfare_name>{0})\s+(?P<weak_thoroughfare_type>{1})\.?(?:\s+(?P<weak_thoroughfare_suffix>{2}))?".format(
        thoroughfareNameRegex,
        thoroughfareTypeRegex,
        thoroughfareSuffixRegex
    )
    buildingTypeRegex = r"(?P<building_type>{0}(\s{0})*)".format(
        SanitationUtils.compile_abbrv_regex(buildingTypeAbbreviations)
    )
    buildingRegex = r"(?P<building_name>{0})\s+{1}".format(
        NameUtils.lazyMultiNameRegex,
        buildingTypeRegex
    )
    deliveryTypeRegex = r"(?P<delivery_type>%s)" % (
        SanitationUtils.compile_abbrv_regex(deliveryTypeAbbreviations),
    )
    deliveryRegex = r"%s(?:\s*(?P<delivery_number>%s))?" % (
        deliveryTypeRegex,
        singleNumberRegex
    )
    countryRegex = r"(%s)" % SanitationUtils.compile_abbrv_regex(
        countryAbbreviations)

# [^,\s\d/()-]+
    addressTokenRegex = r"(%s)" % "|".join([
        SanitationUtils.wrap_clear_regex(deliveryRegex),
        SanitationUtils.wrap_clear_regex(floorLevelRegex),
        SanitationUtils.wrap_clear_regex(subunitRegex),
        SanitationUtils.wrap_clear_regex(thoroughfareRegex),
        SanitationUtils.wrap_clear_regex(buildingRegex),
        SanitationUtils.wrap_clear_regex(weakThoroughfareRegex),
        SanitationUtils.wrap_clear_regex(weakSubunitRegex),
        # SanitationUtils.wrap_clear_regex( stateRegex),
        SanitationUtils.wrap_clear_regex(NameUtils.careOfRegex),
        SanitationUtils.wrap_clear_regex(NameUtils.organizationRegex),
        SanitationUtils.wrap_clear_regex(NameUtils.singleNameRegex),
        SanitationUtils.wrap_clear_regex(multiNumberAllRegex),
        SanitationUtils.wrap_clear_regex(slashAbbrvRegex),
        SanitationUtils.disallowedPunctuationRegex,

    ])

    @staticmethod
    def identify_subunit(string):
        return SanitationUtils.identify_abbreviation(
            AddressUtils.subunitAbbreviations, string)

    @staticmethod
    def identify_floor(string):
        return SanitationUtils.identify_abbreviation(
            AddressUtils.floorAbbreviations, string)

    @staticmethod
    def identify_thoroughfare_type(string):
        return SanitationUtils.identify_abbreviation(
            AddressUtils.thoroughfareTypeAbbreviations, string)

    @staticmethod
    def identify_thoroughfare_suffix(string):
        return SanitationUtils.identify_abbreviation(
            AddressUtils.thoroughfareSuffixAbbreviations, string)

    @staticmethod
    def identify_state(string):
        return SanitationUtils.identify_abbreviation(
            AddressUtils.stateAbbreviations, string)

    @staticmethod
    def identify_building_type(string):
        return SanitationUtils.identify_abbreviation(
            AddressUtils.buildingTypeAbbreviations, string)

    @staticmethod
    def identify_building_types(string):
        return SanitationUtils.identify_abbreviations(
            AddressUtils.buildingTypeAbbreviations, string)

    @staticmethod
    def identify_delivery_type(string):
        return SanitationUtils.identify_abbreviation(
            AddressUtils.deliveryTypeAbbreviations, string)

    @staticmethod
    def identify_country(string):
        return SanitationUtils.identify_abbreviation(
            AddressUtils.countryAbbreviations, string)

    @staticmethod
    def get_floor(token):
        match = re.match(
            SanitationUtils.wrap_clear_regex(
                AddressUtils.floorLevelRegex
            ),
            token
        )
        match_dict = match.groupdict() if match else None
        if(match_dict):
            floor_type = AddressUtils.identify_floor(
                match_dict.get('floor_type'))
            floor_number = match_dict.get('floor_number')
            if Registrar.DEBUG_ADDRESS:
                SanitationUtils.safe_print(
                    "FOUND FLOOR", floor_type, floor_number)
            return floor_type, floor_number
        return None

    @staticmethod
    def get_subunit_type(token):
        match = re.match(
            SanitationUtils.wrap_clear_regex(
                AddressUtils.subunitTypeTypeRegexNamed
            ),
            token
        )
        match_dict = match.groupdict() if match else None
        if match_dict and match_dict.get('subunit_type'):
            subunit_type = AddressUtils.identifySubunitType(
                match_dict.get('subunit_type')
            )
            return subunit_type

    @staticmethod
    def get_subunit(token):
        match = re.match(
            SanitationUtils.wrap_clear_regex(
                AddressUtils.subunitRegex
            ),
            token
        )
        match_dict = match.groupdict() if match else None
        if(match_dict and match_dict.get('subunit_type') and match_dict.get('subunit_number')):
            subunit_type = AddressUtils.identify_subunit(
                match_dict.get('subunit_type'))
            subunit_number = match_dict.get('subunit_number')
            subunit = (subunit_type, subunit_number)
            if Registrar.DEBUG_ADDRESS:
                SanitationUtils.safe_print("FOUND SUBUNIT", subunit)
            return subunit
        return None

    @staticmethod
    def get_weak_subunit(token):
        match = re.match(
            SanitationUtils.wrap_clear_regex(
                AddressUtils.weakSubunitRegex
            ),
            token
        )
        match_dict = match.groupdict() if match else None
        if(match_dict and match_dict.get('weak_subunit_type') and match_dict.get('weak_subunit_number')):
            subunit_type = AddressUtils.identify_subunit(
                match_dict.get('weak_subunit_type'))
            subunit_number = match_dict.get('weak_subunit_number')
            subunit = (subunit_type, subunit_number)
            if Registrar.DEBUG_ADDRESS:
                SanitationUtils.safe_print("FOUND WEAK SUBUNIT", subunit)
            return subunit
        return None

    @staticmethod
    def get_thoroughfare_type(token):
        match = re.match(
            SanitationUtils.wrap_clear_regex(
                AddressUtils.thoroughfareTypeRegexNamed
            ),
            token
        )
        match_dict = match.groupdict() if match else None
        if match_dict and match_dict.get('thoroughfare_type'):
            thoroughfare_type = AddressUtils.identify_thoroughfare_type(
                match_dict.get('thoroughfare_type')
            )
            return thoroughfare_type

    @staticmethod
    def get_thoroughfare(token):
        match = re.match(
            SanitationUtils.wrap_clear_regex(
                AddressUtils.thoroughfareRegex
            ),
            token
        )
        match_dict = match.groupdict() if match else None
        if(match_dict and match_dict.get('thoroughfare_name') and match_dict.get('thoroughfare_type')):
            thoroughfare_name = match_dict.get('thoroughfare_name')
            thoroughfare_type = AddressUtils.identify_thoroughfare_type(
                match_dict.get('thoroughfare_type')
            )
            thoroughfare_suffix = AddressUtils.identify_thoroughfare_suffix(
                match_dict.get('thoroughfare_suffix')
            )
            thoroughfare_number = match_dict.get('thoroughfare_number')
            if Registrar.DEBUG_ADDRESS:
                SanitationUtils.safe_print(
                    "FOUND THOROUGHFARE",
                    thoroughfare_number,
                    thoroughfare_name,
                    thoroughfare_type,
                    thoroughfare_suffix
                )
            return thoroughfare_number, thoroughfare_name, thoroughfare_type, thoroughfare_suffix
        return None

    @staticmethod
    def get_building(token):
        match = re.match(
            SanitationUtils.wrap_clear_regex(
                AddressUtils.buildingRegex
            ),
            token
        )
        match_dict = match.groupdict() if match else None
        if(match_dict):
            # print match_dict
            building_name = match_dict.get('building_name')
            building_type = ''.join(AddressUtils.identify_building_types(
                match_dict.get('building_type')
            ))
            if Registrar.DEBUG_ADDRESS:
                SanitationUtils.safe_print(
                    "FOUND BUILDING",
                    building_name,
                    building_type
                )
            return building_name, building_type

    @staticmethod
    def get_weak_thoroughfare(token):
        match = re.match(
            SanitationUtils.wrap_clear_regex(
                AddressUtils.weakThoroughfareRegex
            ),
            token
        )
        match_dict = match.groupdict() if match else None
        if(match_dict and match_dict.get('weak_thoroughfare_name') and match_dict.get('weak_thoroughfare_type')):
            # print match_dict
            weak_thoroughfare_name = match_dict.get('weak_thoroughfare_name')
            weak_thoroughfare_type = match_dict.get('weak_thoroughfare_type')
            # weak_thoroughfare_type = AddressUtils.identify_thoroughfare_type(
            #     match_dict.get('weak_thoroughfare_type')
            # )
            weak_thoroughfare_suffix = AddressUtils.identify_thoroughfare_suffix(
                match_dict.get('weak_thoroughfare_suffix')
            )

            if Registrar.DEBUG_ADDRESS:
                print "FOUND WEAK THOROUGHFARE %s | %s (%s)" % (
                    weak_thoroughfare_name,
                    weak_thoroughfare_type,
                    weak_thoroughfare_suffix
                )
            return weak_thoroughfare_name, weak_thoroughfare_type, weak_thoroughfare_suffix

    @staticmethod
    def get_state(token):
        match = re.match(
            SanitationUtils.wrap_clear_regex(
                AddressUtils.stateRegex
            ),
            token
        )
        match_dict = match.groupdict() if match else None
        if(match_dict and match_dict.get('state_name')):
            state_name = match_dict.get('state_name')
            if Registrar.DEBUG_ADDRESS:
                SanitationUtils.safe_print("FOUND STATE ", state_name)
            return state_name

    @staticmethod
    def get_delivery(token):
        match = re.match(
            SanitationUtils.wrap_clear_regex(
                AddressUtils.deliveryRegex
            ),
            token
        )
        match_dict = match.groupdict() if match else None
        if(match_dict):
            delivery_type = AddressUtils.identify_delivery_type(
                match_dict.get('delivery_type'))
            delivery_number = match_dict.get('delivery_number')
            if Registrar.DEBUG_ADDRESS:
                SanitationUtils.safe_print(
                    "FOUND DELIVERY ", delivery_type, delivery_number)
            return delivery_type, delivery_number

    @staticmethod
    def get_number(token):
        match = re.match(
            SanitationUtils.wrap_clear_regex(
                AddressUtils.multiNumberAllRegex
            ),
            token
        )
        match_grps = match.groups() if match else None
        if(match_grps):
            number = match_grps[0]
            if Registrar.DEBUG_ADDRESS:
                SanitationUtils.safe_print("FOUND NUMBER ", repr(number))
            number = SanitationUtils.strip_all_whitespace(number)
            return number

    @staticmethod
    def get_single_number(token):
        match = re.match(
            "(" + AddressUtils.numberRegex + ")",
            token
        )
        match_grps = match.groups() if match else None
        if(match_grps):
            number = match_grps[0]
            if Registrar.DEBUG_ADDRESS:
                SanitationUtils.safe_print(
                    "FOUND SINGLE NUMBER ", repr(number))
            number = SanitationUtils.strip_all_whitespace(number)
            return number

    @staticmethod
    def find_single_number(token):
        match = re.search(
            "(" + AddressUtils.numberRegex + ")",
            token
        )
        match_grps = match.groups() if match else None
        if(match_grps):
            number = match_grps[0]
            if Registrar.DEBUG_ADDRESS:
                SanitationUtils.safe_print(
                    "FOUND SINGLE NUMBER ", repr(number))
            number = SanitationUtils.strip_all_whitespace(number)
            return number

    @staticmethod
    def sanitize_state(string):
        return SanitationUtils.compose(
            SanitationUtils.strip_leading_whitespace,
            SanitationUtils.strip_tailing_whitespace,
            SanitationUtils.strip_extra_whitespace,
            SanitationUtils.strip_punctuation,
            SanitationUtils.to_upper
        )(string)

    @staticmethod
    def sanitize_address_token(string):
        string = SanitationUtils.strip_extra_whitespace(string)
        string = re.sub(AddressUtils.numberAlphaRegex +
                        SanitationUtils.clearStartRegex, r'\1\2', string)
        string = re.sub(AddressUtils.numberRangeRegex, r'\1-\2', string)
        if Registrar.DEBUG_UTILS:
            SanitationUtils.safe_print("sanitize_address_token", string)
        return string

    @staticmethod
    def tokenize_address(string):
        # if Registrar.DEBUG_ADDRESS:
        #     SanitationUtils.safe_print("in tokenize_address")
        matches = re.findall(
            AddressUtils.addressTokenRegex,
            string.upper()
        )
        # if Registrar.DEBUG_ADDRESS:
        #     for match in matches:
        #         print repr(match)
        return map(
            lambda match: AddressUtils.sanitize_address_token(match[0]),
            matches
        )

    @staticmethod
    def address_remove_end_word(string, word):
        string_layout = AddressUtils.tokenize_address(string)
        word_layout = AddressUtils.tokenize_address(word)
        if not(word_layout and string_layout):
            return string
        for i, word in enumerate(reversed(word_layout)):
            if(1 + i > len(word_layout)) or word != string_layout[-1 - i]:
                return string
        return " ".join(string_layout[:-len(word_layout)])

    @staticmethod
    def extract_shop(address):
        match = re.match(AddressUtils.shopRegex, address)
        match_dict = match.groupdict()
        if(match_dict):
            number = match_dict.get('number', None)
            rest = match_dict.get('rest', None)
            if(number):
                return number, rest
        return None, address

# def testAddressUtils():
#     # SanitationUtils.clearStartRegex = "<START>"
#     # SanitationUtils.clearFinishRegex = "<FINISH>"
#     # print repr(AddressUtils.addressTokenRegex)
#
#     # print AddressUtils.address_remove_end_word("WEST AUSTRALIA", "WEST AUSTRALIA")
#
#     # print AddressUtils.address_remove_end_word("SHOP 7 KENWICK SHOPNG CNTR BELMONT RD, KENWICK WA (", "KENWICK WA")
#     # print SanitationUtils.unicodeToByte(u"\u00FC ASD")
#     # print "addressTokenRegex", AddressUtils.addressTokenRegex
#     # print "thoroughfareRegex", AddressUtils.thoroughfareRegex
#     # print "subunitRegex", AddressUtils.subunitRegex
#     # print "floorLevelRegex", AddressUtils.floorLevelRegex
#     # print "stateRegex", AddressUtils.stateRegex
#     # print "delimeterRegex", AddressUtils.delimeterRegex
#
#     # print AddressUtils.get_subunit("SHOP 4 A")
#     # print AddressUtils.get_floor("LEVEL 8")
#     print AddressUtils.tokenize_address("BROADWAY FAIR SHOPPING CTR")
#     print AddressUtils.get_building("BROADWAY FAIR SHOPPING CTR")
#     print AddressUtils.get_building("BROADWAY FAIR SHOPPING")
#     print NameUtils.get_multi_name("BROADWAY")
#
