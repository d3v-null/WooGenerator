import argparse

from StringIO import StringIO
from pprint import pformat

import __init__
from woogenerator.client.core import SyncClientGDrive, SyncClientLocalStream
from woogenerator.client.prod import CatSyncClientWC, ProdSyncClientWC
from woogenerator.coldata import ColDataBase, ColDataMyo, ColDataWoo
from woogenerator.conf.parser import (ArgumentParserProd,
                                      ArgumentParserProtoProd)
from woogenerator.matching import (CategoryMatcher, MatchList, ProductMatcher,
                                   VariationMatcher)
from woogenerator.metagator import MetaGator
from woogenerator.namespace.prod import SettingsNamespaceProd
from woogenerator.parsing.api import CsvParseWooApi
from woogenerator.parsing.dyn import CsvParseDyn
from woogenerator.parsing.myo import CsvParseMyo, MYOProdList
from woogenerator.parsing.special import CsvParseSpecial
from woogenerator.parsing.woo import (CsvParseTT, CsvParseVT, CsvParseWoo,
                                      WooCatList, WooProdList, WooVarList)
from woogenerator.syncupdate import (SyncUpdate, SyncUpdateCatWoo,
                                     SyncUpdateProdWoo, SyncUpdateVarWoo)
from woogenerator.utils import Registrar


# Example: BioTan Plus special SP2017-05-22-STBTP
def populate_examples(settings):
    settings.special_schedule_raw = """\
Special Group ID,Rule Code,FROM               ,TO                 ,RNS,RPS,WNS
SP2017-05-22    ,         ,2017-05-22 17:00:00,2017-05-31 23:59:59,   ,   ,
                ,STBTP    ,                   ,                   ,   ,   ,80%
                ,CT       ,                   ,                   ,70%,   ,70%
                ,TC       ,                   ,                   ,85%,   ,85%
"""
    settings.dyncat_raw = """\
ID     ,Qty. Base,Rule Mode,Roles        ,Min ( Buy ),Max ( Receive ),Discount Type,Discount,Repeating,Meaning
CATWSOL,CAT      ,BULK     ,WN|WP|XWN|XWP,           ,               ,             ,        ,         ,
       ,         ,         ,             ,4          ,7              ,PDSC         ,10      ,         ,Buy 4 or more 1 Litre Solution Items and receive 10% off 1 Litre Solution
       ,         ,         ,             ,8          ,11             ,PDSC         ,15      ,         ,Buy 8 or more 1 Litre Solution Items and receive 15% off 1 Litre Solution
       ,         ,         ,             ,12         ,23             ,PDSC         ,17.5    ,         ,Buy 12 or more 1 Litre Solution Items and receive 17.5% off 1 Litre Solution
       ,         ,         ,             ,24         ,               ,PDSC         ,20      ,         ,Buy 24 or more 1 Litre Solution Items and receive 20% off 1 Litre Solution
"""

    settings.dynprod_raw = """\
ID      ,Qty. Base,Rule Mode,Roles        ,Min ( Buy ),Max ( Receive ),Discount Type,Discount,Repeating,Meaning
PRODWTCS,PROD     ,BULK     ,WN|WP|XWN|XWP,           ,               ,             ,        ,         ,
        ,         ,         ,             ,6          ,11             ,PDSC         ,10      ,         ,Buy between 6 and11 Items and receive 10% off this item
        ,         ,         ,             ,12         ,23             ,PDSC         ,15      ,         ,Buy between 12 and 23 Items and receive 15% off this item
        ,         ,         ,             ,24         ,               ,PDSC         ,20      ,         ,Buy 24 or more and get 20% off this item
"""

    settings.affected_items = """\
Solution
    TechnoTan Solution
        BioTan Plus (2hr)
Tan Care
    TechnoTan Tan Care Kits
        Mousse and Mitt Kits
            Mocha Style Mousse and Mitt Kit
                100mL
                200mL
            Mocha Style Mousse and Deluxe Mitt Kit
                100mL
                200mL
    TechnoTan After Care
        Hydrating Cream
            Hydrating Cream - Coconut & Lime
                50ml (pump)
    TechnoTan Tan Enhancement
        Bronzing Cream
            Bronzing Cream - Tamarillo & Papaya
                50ml (airless pump)
        Shimmering Bronzer
            Shimmering Bronzer - Tamarillo & Papaya
                50ml (airless pump)
        Classic Tanning Mousse
            Mocha Style Tanning Mouse
                200ml (pump bottle)
                100ml (pump bottle)
Tanbience
    Natural Soy Wax Candles
"""

    settings.out_html_specials = """\
<ul>
    <li>Save 30% off NEW Mocha Style Tanning Mousse and Deluxe Application Mitts</li>
    <li>Save up to 36% off BioTan Plus Solution</li>
    <li>Save 30% off NEW 50ml Airless Pump Bottles</li>
    <li>Save up to 32% off Tanbience Candles & Melts</li>
</ul>
<em>Promotion ends 5pm (AWST) Wednesday 31st May 2017</em>"""

    settings.out_html_stbtp = """\
<strong>Save up to 36% off BioTan Plus Solution</strong>
<ul>
    <li>Buy 1-3 litres & receive 20% off</li>
    <li>Buy 4-7 litres & receive 28% off</li>
    <li>Buy 8-11 litres & receive 32% off</li>
    <li>Buy 12-23 litres & receive 34% off</li>
    <li>Buy 24+ litres & receive 36% off</li>
</ul>
<em>*Specials valid until 5pm (AWST) Wednesday 31st May 2017</em>"""

    settings.out_html_tc = """\
<strong>Save up to 32% off Tanbience Candels & Melts</strong>
<ul>
    <li>Buy 1-5 of a kind & receive 15% off</li>
    <li>Buy 6-11 of a kind & receive 23.5% off</li>
    <li>Buy 12-23 of a kind & receive 27.75% off</li>
    <li>Buy 24+ of a kind & receive 32% off</li>
</ul>
<em>*Specials valid until 5pm (AWST) Wednesday 31st May 2017</em>"""

    settings.out_html_ct = """\
<strong>Save 30% off</strong>
<ul>
    <li>Mocha Style Tanning Mousse</li>
    <li>Deluxe Application Mitts</li>
    <li>50ml Airless Pump Bottles</li>
</ul>
<em>*Specials valid until 5pm (AWST) Wednesday 31st May 2017</em>"""

    return settings

def populate_master_parsers(settings):
    col_data_class = ColDataWoo

    settings.product_parser_args.update(**{
        'cols':
        col_data_class.get_import_cols(),
        'defaults':
        col_data_class.get_defaults(),
    })

    product_parser_class = CsvParseTT

    parsers = argparse.Namespace()

    parsers.dyn = CsvParseDyn()
    parsers.special = CsvParseSpecial()

    client_class = SyncClientLocalStream
    client_args = []

    with client_class(*client_args) as client:
        Registrar.register_message("analysing dprc rules")
        client.analyse_remote(parsers.dyn, StringIO(settings.dyncat_raw))
        settings.product_parser_args['dprc_rules'] = parsers.dyn.taxos

        for rule in parsers.dyn.taxos:
            print "DPRC Rule:", rule

        Registrar.register_message("analysing dprp rules")
        parsers.dyn.clear_transients()
        client.analyse_remote(parsers.dyn, StringIO(settings.dynprod_raw))
        settings.product_parser_args['dprp_rules'] = parsers.dyn.taxos

        for rule in parsers.dyn.taxos:
            print "DPRP Rule:", rule

def main(override_args=None, settings=None):

    if not settings:
        settings = SettingsNamespaceProd()

    ### First round of argument parsing determines which config files to read
    ### from core config files, CLI args and env vars

    proto_argparser = ArgumentParserProtoProd()

    Registrar.register_message("proto_parser: \n%s" % pformat(proto_argparser.get_actions()))

    parser_override = {'namespace':settings}
    if override_args:
        parser_override['args'] = override_args

    settings, _ = proto_argparser.parse_known_args(**parser_override)

    Registrar.register_message("proto settings: \n%s" % pformat(vars(settings)))

    ### Second round gets all the arguments from all config files

    argparser = ArgumentParserProd()

    for conf in settings.second_stage_configs:
        print "adding conf: %s" % conf
        argparser.add_default_config_file(conf)

    if settings.help_verbose:
        if 'args' not in parser_override:
            parser_override['args'] = []
        parser_override['args'] += ['--help']

    Registrar.register_message("parser: %s " % pformat(argparser.get_actions()))

    settings = argparser.parse_args(**parser_override)

    Registrar.register_message("Raw settings: %s" % pformat(vars(settings)))

    Registrar.DEBUG_PROGRESS = True
    Registrar.DEBUG_ERROR = True
    Registrar.DEBUG_MESSAGE = True

    Registrar.DEBUG_ABSTRACT = True
    Registrar.DEBUG_PARSER = True
    # Registrar.DEBUG_UPDATE = settings.debug_update
    # Registrar.DEBUG_NAME = settings.debug_name
    # Registrar.DEBUG_ADDRESS = settings.debug_address
    # Registrar.DEBUG_CLIENT = settings.debug_client
    # Registrar.DEBUG_UTILS = settings.debug_utils
    # Registrar.DEBUG_CONTACT = settings.debug_contact
    # Registrar.DEBUG_DUPLICATES = settings.debug_duplicates

    settings = populate_examples(settings)

    settings.product_parser_args = {
        'import_name': settings.import_name,
        'item_depth': settings.item_depth,
        'taxo_depth': settings.taxo_depth,
    }

    parsers = populate_master_parsers(settings)


if __name__ == '__main__':
    main()
