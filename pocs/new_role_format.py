# pylint: disable=too-many-lines
"""Module for testing the latest role format."""

from __future__ import print_function
# import io
# import os
# import sys
# import re
# import time
# import traceback
# import zipfile
# from bisect import insort
from collections import OrderedDict, Counter
from pprint import pprint, pformat
# import argparse
import unicodecsv

from tabulate import tabulate
# import unicodecsv
# from sshtunnel import check_address
# from requests.exceptions import ConnectionError, ConnectTimeout, ReadTimeout
# from httplib2 import ServerNotFoundError

import __init__
# from woogenerator.coldata import ColDataUser
# from woogenerator.contact_objects import FieldGroup
# from woogenerator.duplicates import Duplicates
# from woogenerator.matching import (CardMatcher, ConflictingMatchList,
#                                    EmailMatcher, Match, MatchList,
#                                    NocardEmailMatcher, UsernameMatcher)
# from woogenerator.parsing.user import CsvParseUser, UsrObjList
# from woogenerator.client.user import (UsrSyncClientSqlWP,
#                                            UsrSyncClientSshAct,
#                                            UsrSyncClientWP)
# from woogenerator.syncupdate import SyncUpdate, SyncUpdateUsrApi
from woogenerator.utils import (HtmlReporter, ProgressCounter, Registrar,
                                SanitationUtils, TimeUtils, DebugUtils, SeqUtils)
from woogenerator.conf.parser import ArgumentParserUser, ArgumentParserProtoUser
from woogenerator.namespace.core import ParserNamespace, MatchNamespace
from woogenerator.merger import populate_main_parsers, populate_subordinate_parsers, do_match

"""
Explanation:

Role is now the most
"""

ROLES = Counter()
BRANDS = Counter()

SCHEMA_TRANSLATIONS = [
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

def translate_schema(schema):
    if not schema:
        return
    schema = schema.lower()
    for key, translation in SCHEMA_TRANSLATIONS:
        if key.lower() == schema:
            return translation

def get_schema(brand):
    if not brand:
        return
    brand = brand.lower()
    for schema, translation in SCHEMA_TRANSLATIONS:
        if translation.lower() == brand:
            return schema.lower()

def schema_exists(schema):
    if not schema:
        return
    schema = schema.lower()
    for key, _ in SCHEMA_TRANSLATIONS:
        if key.lower() == schema:
            return True

ROLE_TRANSLATIONS = [
    # unambiguous
    ('rn',  'Retail'),
    ('rn',  'Retail Normal'),
    ('rp',  'Retail Preferred'),
    ('xrn', 'Retail Export'),
    ('xrn', 'Export Retail Normal'),
    ('xrp', 'Retail Preferred Export'),
    ('xrp', 'Export Retail Preferred'),
    ('wn',  'Wholesale'),
    ('wn',  'Wholesale Normal'),
    ('wp',  'Wholesale Preferred'),
    ('xwn', 'Wholesale Export'),
    ('xwn', 'Export Wholesale'),
    ('xwn', 'Export Wholesale Normal'),
    ('xwp', 'Wholesale Preferred Export'),
    ('xwp', 'Export Wholesale Preferred'),
    ('dn',  'Distributor'),
    ('dn',  'Distributor Normal'),
    ('dp',  'Distributor Preferred'),
    ('xdn', 'Distributor Export'),
    ('xdn', 'Export Distributor'),
    ('xdn', 'Export Distributor Normal'),
    ('xdp', 'Distributor Preferred Export'),
    ('xdp', 'Export Distributor Preferred'),
    ('admin', 'Administrator'),
    # ambiguous
    ('xwn', 'Export'),

]

def role_exists(role):
    if not role:
        return
    role = role.lower()
    for key, _ in ROLE_TRANSLATIONS:
        if key.lower() == role:
            return True

def translate_role(role):
    if not role:
        return
    role = role.lower()
    for key, translation in ROLE_TRANSLATIONS:
        if key.lower() == role:
            return translation

def get_role(role_string):
    if not role_string:
        return
    role_string = role_string.lower()
    for key, translation in ROLE_TRANSLATIONS:
        if translation.lower() == role_string:
            return key.lower()

def tokenwise_startswith(haystack_tokens, needle_tokens):
    if len(needle_tokens) > len(haystack_tokens):
        return
    for index, needle_token in enumerate(needle_tokens):
        if needle_token != haystack_tokens[index]:
            return
    return True

ALLOWED_COMBINATIONS = OrderedDict([
    ('tt', ['rn', 'rp', 'xrn', 'xrp', 'wn', 'wp', 'xwn', 'xwp']),
    ('vt', ['rn', 'rp', 'xrn', 'xrp', 'wn', 'wp', 'xwn', 'xwp', 'dn', 'dp', 'xdn', 'xdp']),
    ('mm', ['rn', 'rp', 'xrn', 'xrp', 'wn', 'wp', 'xwn', 'xwp', 'dn', 'dp', 'xdn', 'xdp']),
    ('tc', ['rn', 'rp', 'wn', 'wp', 'dn', 'dp']),
    ('st', ['admin'])
])


def parse_direct_brand(direct_brand):
    parsed_schema = None
    parsed_role = None
    if direct_brand == "none":
        direct_brand = None
    if direct_brand:
        direct_brand_tokens = direct_brand.lower().split(' ')
        # do tokenwise comparison on all possible schemes:
        for schema, brand in SCHEMA_TRANSLATIONS:
            brand_tokens = brand.lower().split(' ')

            if tokenwise_startswith(direct_brand_tokens, brand_tokens):
                parsed_schema = schema
                direct_brand_tokens = direct_brand_tokens[len(brand_tokens):]
                if direct_brand_tokens:
                    parsed_role = get_role(" ".join(direct_brand_tokens))
                    assert parsed_role, \
                        "could not parse role: %s" % " ".join(direct_brand_tokens)

        assert parsed_schema, \
            "unkown brand: %s" %  direct_brand
    return parsed_schema, parsed_role

def parse_direct_brand_str(direct_brand_str):
    parsed = []
    if direct_brand_str:
        for direct_brand in map(str.lower, str(direct_brand_str).split(';')):
            # print("looking at direct_brand: %s" % direct_brand)
            parsed_schema, parsed_role = parse_direct_brand(direct_brand)
            if parsed_schema:
                parsed.append((parsed_schema, parsed_role))
    return parsed

def format_direct_brand(parsed_schema, parsed_role=None):
    formatted_brand = translate_schema(parsed_schema)
    assert formatted_brand, \
        "cannot format as direct brand: (%s, %s)" % (
            parsed_schema, parsed_role
        )
    if parsed_role:
        formatted_role = translate_role(parsed_role)
        return " ".join([formatted_brand, formatted_role])
    return formatted_brand

def determine_role(direct_brands, schema=None, role=None):
    """
    Determe what role should be based on direct brand, schema and (optionally) default role.
    """
    schema = schema.lower()
    if direct_brands is None:
        return role
    assert schema_exists(schema), "schema %s not recognized" % schema
    for parsed_schema, parsed_role in parse_direct_brand_str(direct_brands):
        # print("parsed_schema is: %s, parsed_role is %s, schema role is %s" % (
        #     repr(translate_schema(parsed_schema)),
        #     repr(translate_role(parsed_role)),
        #     repr(translate_schema(schema))
        # ))
        if parsed_schema and parsed_role and schema == parsed_schema:
            assert role_exists(parsed_role), "role %s not recognized" % parsed_role
            ROLES.update({parsed_role:1})
            BRANDS.update({parsed_schema:1})
            return parsed_role.upper()
    return role

ROLELESS_SCHEMAS = ['-', 'st']

def jess_fix(direct_brands, act_role):
    if act_role.lower() == 'admin':
        return "Staff", "ADMIN"
    direct_brands_out = []
    if act_role:
        act_role = act_role.lower()
        assert role_exists(act_role), \
            "act_role should exist: %s" % act_role
    role_out = act_role
    parsed = parse_direct_brand_str(direct_brands)

    # if len(parsed) >= 2:
    #     schema_no_roles = [
    #         parsed_schema for parsed_schema, parsed_role in parsed \
    #         if parsed_schema and (not parsed_role) and (parsed_schema not in ROLELESS_SCHEMAS)
    #     ]
        # assert not any(schema_no_roles), \
        #     "there are too many direct brands that have no act_role. %s" % direct_brands

    # print("parsed: %s" % parsed)

    for count, (parsed_schema, parsed_role) in enumerate(parsed):
        if parsed_role == 'admin' or parsed_schema == 'st':
            role_out = "admin"
            direct_brands_out = [('-', None)]
            break
        if parsed_schema == '-' and (len(parsed) - count > 1):
            continue
        if parsed_schema:
            if parsed_schema not in ROLELESS_SCHEMAS:
                # if there is competition:
                role_competitors = [(0, 'rn', 'default')]
                allowed_roles = ['rn']
                if parsed_schema in ALLOWED_COMBINATIONS:
                    allowed_roles = ALLOWED_COMBINATIONS[parsed_schema]
                for priority, allowed_role in enumerate(allowed_roles):
                    if allowed_role == act_role:
                        role_competitors.append((priority, act_role, 'act_role'))
                    if allowed_role == parsed_role:
                        role_competitors.append((priority, parsed_role, 'parsed_role'))
                assert role_competitors, \
                    "cannot find a suitable role for schema %s out of %s. allowed:%s" % (
                        parsed_schema,
                        role_competitors,
                        allowed_roles
                    )
                _, winning_role, source = max(role_competitors)
                if source != 'act_role':
                    role_out = winning_role

                if len(allowed_roles) > 1:
                    direct_brands_out.append((parsed_schema, winning_role))
                    continue
            direct_brands_out.append((parsed_schema, None))

    # print(direct_brands_out, role_out)

    if not direct_brands_out:
        direct_brands_out = [('-', None)]
    if direct_brands_out == [('-', None)]:
        if role_out == 'admin':
            direct_brands_out = [('st', None)]
        else:
            role_out = None
    if not role_out:
        role_out = 'rn'

    direct_brand_str = ";".join([
        format_direct_brand(*direct_brand_out) for direct_brand_out in direct_brands_out
    ])
    return direct_brand_str, role_out.upper()


def main(override_args=None, settings=None):  # pylint: disable=too-many-branches,too-many-locals
    """
    Use settings object to load config file and detect changes in wordpress.
    """
    # TODO: fix too-many-branches,too-many-locals
    # DONE: implement override_args

    Registrar.DEBUG_MESSAGE = True

    override_args = [
        '--livemode',
        # '--download-main',
        '--download-subordinate',
        '--skip-download-main',
        # '--skip-download-subordinate',
        '--main-file=/Users/derwent/Documents/woogenerator/input/user_main-2017-07-12_00-41-26.csv',
        # '--main-parse-limit=5000',
        # '--subordinate-parse-limit=5000',
        '--schema=TT',
        '-vvv'
    ]

    settings.init_settings(override_args)

    assert schema_exists(settings.schema), \
        "schema %s should be in %s" % (settings.schema, SCHEMA_TRANSLATIONS)

    parsers = ParserNamespace()
    parsers = populate_subordinate_parsers(parsers, settings)
    parsers = populate_main_parsers(parsers, settings)

    matches = MatchNamespace()
    matches = do_match(matches, parsers, settings)

    if Registrar.DEBUG_PROGRESS:
        sync_progress_counter = ProgressCounter(len(matches.globals))

    direct_brand_counter = Counter()
    delta_table = [[
        'card_id',
        'name',
        'direct brand',
        '%s role' % settings.main_name,
        '%s role' % settings.subordinate_name,
        'expected role',
        'jess direct brand',
        'jess role',
        'errors'
    ]]

    for count, match in enumerate(matches.globals):
        if Registrar.DEBUG_PROGRESS:
            sync_progress_counter.maybe_print_update(count)

        main_object = match.m_objects[0]
        subordinate_object = match.s_objects[0]

        errors = ''
        card_id = main_object.MYOBID
        name = str(main_object.name)
        act_direct_brand_str = str(main_object.get('Direct Brand'))
        parsed_direct_brand_str = parse_direct_brand_str(act_direct_brand_str)
        main_role = str(main_object.get('Role'))
        subordinate_role = str(subordinate_object.get('Role'))
        try:
            expected_role = determine_role(act_direct_brand_str, settings.schema)
        except AssertionError, exc:
            expected_role = "UNKN"
            errors = str(exc)
        jess_direct_brand_str, jess_role = None, None
        try:
            jess_direct_brand_str, jess_role = jess_fix(act_direct_brand_str, main_role)
        except AssertionError, exc:
            errors = "; ".join([errors, str(exc)])
        row = (
            card_id,
            name,
            act_direct_brand_str,
            main_role,
            subordinate_role,
            expected_role,
            jess_direct_brand_str,
            jess_role,
            errors
        )
        for parsed_schema, parsed_role in parsed_direct_brand_str:
            direct_brand_counter.update({format_direct_brand(parsed_schema, parsed_role): 1})

        unique_roles = SeqUtils.filter_unique_true([main_role, subordinate_role, jess_role])
        unique_direct_brands = SeqUtils.filter_unique_true([act_direct_brand_str, jess_direct_brand_str])

        if errors or len(unique_roles) > 1 or len(unique_direct_brands) > 1:
            delta_table.append(row)

    print(tabulate(delta_table, headers='firstrow'))

    with open("results.csv", "w+") as csvfile:
        csvwriter = unicodecsv.writer(csvfile)
        csvwriter.writerows(delta_table)

    print("all direct_brands: \n%s" % pformat(direct_brand_counter))
    print("all parsed roles: \n%s" % pformat(ROLES))
    print("all parsed brands: \n%s" % pformat(BRANDS))

    # direct_brands = Counter({
    #     'Pending': 15305,
    #     'TechnoTan': 9967,
    #     'VuTan': 1806,
    #     'TechnoTan Wholesale': 719,
    #     'Technotan': 517,
    #     'Technotan Retail': 246,
    #     'VuTan Wholesale': 136,
    #     'Pending;': 126,
    #     'TechnoTan;': 120,
    #     'Mosaic Minerals': 76,
    #     'VuTan;': 38,
    #     'Mosaic Minerals;TechnoTan': 38,
    #     'PrintWorx': 8,
    #     'Mosaic Minerals;VuTan': 8,
    #     'VuTan Retail': 6,
    #     'Technotan;': 6,
    #     'None': 6,
    #     'TechnoTan;VuTan': 4,
    #     'Technotan Retail;': 4,
    #     'VuTan Distributor': 3,
    #     'Pending;VuTan Wholesale': 3,
    #     'TechnoTan;VuTan;': 2,
    #     'Pending;TechnoTan': 2,
    #     'VuTan Wholesale;': 2,
    #     'House of Rhinestones': 2,
    #     'Meridian Marketing': 2,
    #     'TechnoTan Wholesale;VuTan Wholesale': 1,
    #     'vuTan': 1,
    #     'Tanbience;TechnoTan Wholesale': 1,
    #     'TEChnoTan': 1,
    #     'TECHnoTan': 1,
    #     'Technotan Retail;VuTan Wholesale': 1,
    #     'technoTan': 1,
    #     'TechnoTan Wholesale;Mosaic Minerals': 1,
    #     'TechnoTan Wholesale;': 1,
    #     'Mosaic Minerals;': 1,
    #     'TechnoTan Distributor;': 1
    # })



    # parser_cols = ma_parser_objectlist.report_cols
    # parser_cols['Direct Brand'] = {}
    # Registrar.register_message(
    #     "main parser: \n%s" % \
    #     SanitationUtils.coerce_unicode(ma_parser_objectlist.tabulate(cols=parser_cols))
    # )

if __name__ == '__main__':
    main()
