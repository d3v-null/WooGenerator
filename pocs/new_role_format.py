# pylint: disable=too-many-lines
"""Module for testing the latest role format."""

from __future__ import print_function
import io
import os
import sys
# import re
# import time
import traceback
# import zipfile
# from bisect import insort
from collections import OrderedDict, Counter
from pprint import pprint, pformat
import argparse
import unicodecsv

from tabulate import tabulate
# import unicodecsv
# from sshtunnel import check_address
from requests.exceptions import ConnectionError, ConnectTimeout, ReadTimeout
from httplib2 import ServerNotFoundError

import __init__
# from woogenerator.coldata import ColDataUser
# from woogenerator.contact_objects import FieldGroup
# from woogenerator.duplicates import Duplicates
# from woogenerator.matching import (CardMatcher, ConflictingMatchList,
#                                    EmailMatcher, Match, MatchList,
#                                    NocardEmailMatcher, UsernameMatcher)
# from woogenerator.parsing.user import CsvParseUser, UsrObjList
# from woogenerator.sync_client_user import (UsrSyncClientSqlWP,
#                                            UsrSyncClientSshAct,
#                                            UsrSyncClientWP)
# from woogenerator.syncupdate import SyncUpdate, SyncUpdateUsrApi
from woogenerator.utils import (HtmlReporter, ProgressCounter, Registrar,
                                SanitationUtils, TimeUtils, DebugUtils)
from woogenerator.config import (ArgumentParserUser, ArgumentParserProtoUser,
                                 SettingsNamespaceUser)
from woogenerator.merger import populate_master_parsers, init_settings, init_registrar

ROLES = Counter()
BRANDS = Counter()

def determine_role(direct_brands, schema=None, role=None):
    """
    Determe what role should be based on direct brand, schema and (optionally) default role.
    """
    if role is None:
        role = "RN"
    if schema is None:
        schema = "TT"
    schema = schema.lower()
    if direct_brands is None:
        return role
    schema_translations = OrderedDict([
        ('tt', 'technotan'),
        ('vt', 'vutan'),
        ('mm', 'mosaic minerals'),
        ('pw', 'printworx'),
        ('hr', 'house of rhinestones'),
        ('ma', 'meridian marketing'),
    ])
    assert schema in schema_translations, "schema %s not recognized" % schema
    role_translations = {
        'rn':'retail',
        'wn':'wholesale',
        'dn':'distributor'
    }
    for direct_brand in map(str.lower, str(direct_brands).split(';')):
        # print("looking at direct_brand: %s" % direct_brand)
        if direct_brand == 'pending':
            continue
        parsed_brand = None
        parsed_role = None
        for brand in schema_translations.values():
            if direct_brand.startswith(brand):
                print("direct_brand startswith %s" % brand)
                parsed_brand = brand
                direct_brand = direct_brand[len(brand)+1:]
                if direct_brand:
                    parsed_role = direct_brand
                break
        if parsed_brand is None:
            tokens = direct_brand.split(' ')
            assert len(tokens) <= 2, "unable to parse direct brand: %s" % direct_brand
            if len(tokens) <= 1:
                parsed_brand = tokens[0]
                continue
            if len(tokens) == 1:
                parsed_brand = tokens[0]
                parsed_role = " ".join(tokens[1:])
        print("parsed_brand is: %s, parsed_role is %s, schema role is %s" % (
            repr(parsed_brand),
            repr(parsed_role),
            repr(schema_translations[schema])
        ))
        if parsed_brand and parsed_role and schema_translations[schema] == parsed_brand:
            assert parsed_role in role_translations.values(), "role %s not recognized" % parsed_role
            ROLES.update({parsed_role:1})
            BRANDS.update({parsed_brand:1})
            for role_key, role_value in role_translations.items():
                if role_value == parsed_role:
                    print("returning role from direct brans %s" % parsed_role)
                    return role_key.upper()
    return role

def main(override_args=None, settings=None):  # pylint: disable=too-many-branches,too-many-locals
    """
    Use settings object to load config file and detect changes in wordpress.
    """
    # TODO: fix too-many-branches,too-many-locals
    # DONE: implement override_args

    settings = init_settings(override_args, settings)

    init_registrar(settings)

    # PROCESS CONFIG

    assert settings['master_file'], "master file must be provided if not download_master"
    settings.ma_path = os.path.join(
        settings.in_folder_full, settings['master_file'])
    settings.ma_encoding = "utf8"

    settings.filter_items = None

    parsers = argparse.Namespace()
    parsers = populate_master_parsers(parsers, settings)

    ma_parser_objectlist = parsers.ma.get_obj_list()
    direct_brands = Counter()
    delta_table = [['name', 'card_id', 'direct_brand', 'role', 'expected_role']]
    for master_object in ma_parser_objectlist:
        card_id = master_object.MYOBID
        name = str(master_object.name)
        direct_brand = str(master_object.get('Direct Brand'))
        role = str(master_object.get('Role'))
        expected_role = determine_role(direct_brand, settings.schema)
        row = (
            name,
            card_id,
            direct_brand,
            role,
            expected_role
        )
        direct_brands.update({direct_brand: 1})
        if expected_role != role:
            print("for %50s (%10s), direct brand is: %50s, role is %5s, expected_role is %5s" % row)
            delta_table.append(row)

    print(tabulate(delta_table, headers='firstrow'))

    with open("results.csv", "w+") as csvfile:
        csvwriter = unicodecsv.writer(csvfile)
        csvwriter.writerows(delta_table)

    print("all direct_brands: \n%s" % pformat(direct_brands))
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
    #     "master parser: \n%s" % \
    #     SanitationUtils.coerce_unicode(ma_parser_objectlist.tabulate(cols=parser_cols))
    # )

if __name__ == '__main__':
    main()
