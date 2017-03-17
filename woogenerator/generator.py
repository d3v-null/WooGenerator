"""
Module for generating woocommerce csv import files from Google Drive Data

TODO:
    reduce file length
"""

from collections import OrderedDict
import os
import shutil
import sys
import traceback
import zipfile
import io
from bisect import insort
import urlparse
import webbrowser
import re
from pprint import pformat, pprint
# import time
import argparse
import yaml
from tabulate import tabulate
from requests.exceptions import ReadTimeout, ConnectTimeout, ConnectionError
from httplib2 import ServerNotFoundError
from PIL import Image

from exitstatus import ExitStatus

from __init__ import MODULE_PATH, MODULE_LOCATION

from utils import listUtils, SanitationUtils, TimeUtils, ProgressCounter
from utils import HtmlReporter, Registrar
from metagator import MetaGator
# from parsing.api import CSVParse_Woo_Api
from coldata import ColData_Woo, ColData_MYO, ColData_Base
from sync_client import SyncClient_GDrive, SyncClient_Local
from sync_client_prod import ProdSyncClient_WC, CatSyncClient_WC
from matching import MatchList
from matching import ProductMatcher, CategoryMatcher, VariationMatcher
from SyncUpdate import SyncUpdate, SyncUpdate_Cat_Woo
from SyncUpdate import SyncUpdate_Var_Woo, SyncUpdate_Prod_Woo
from parsing.shop import ShopObjList  # ShopProdList,
from parsing.woo import CSVParse_TT, CSVParse_VT, CSVParse_Woo
from parsing.woo import WooCatList, WooProdList, WooVarList
from parsing.api import CSVParse_Woo_Api
from parsing.myo import CSVParse_MYO, MYOProdList
from parsing.dyn import CSVParse_Dyn
from parsing.special import CSVParse_Special


def check_warnings():
    """
    Check if there have been any errors or warnings registered in Registrar.

    Raise approprriate exceptions if needed
    """
    if Registrar.errors:
        print("there were some urgent errors "
              "that need to be reviewed before continuing")
        Registrar.print_message_dict(0)
        status = ExitStatus.failure
        print "\nexiting with status %s\n" % status
        sys.exit(status)
    elif Registrar.warnings:
        print "there were some warnings that should be reviewed"
        Registrar.print_message_dict(1)


def make_argparser(config):  # pylint: disable=too-many-statements
    """ creates the argument parser, using defaults from config """
    parser = argparse.ArgumentParser(
        description='Generate Import files from Google Drive')
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "-v", "--verbosity", action="count", help="increase output verbosity")
    group.add_argument("-q", "--quiet", action="store_true")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        '--testmode',
        help='Run in test mode with test servers',
        action='store_true',
        default=False)
    group.add_argument(
        '--livemode',
        help='Run the script on the live databases',
        action='store_false',
        dest='testmode')

    download_group = parser.add_argument_group('Import options')
    group = download_group.add_mutually_exclusive_group()
    group.add_argument(
        '--download-master',
        help='download the master data from google',
        action="store_true",
        default=config.get('download_master'))
    group.add_argument(
        '--skip-download-master',
        help=('use the local master file'
              'instead of downloading the master data'),
        action="store_false",
        dest='download_master')
    group = download_group.add_mutually_exclusive_group()
    group.add_argument(
        '--download-slave',
        help='download the slave data',
        action="store_true",
        default=config.get('download_slave'))
    group.add_argument(
        '--skip-download-slave',
        help='use the local slave file instead of downloading the slave data',
        action="store_false",
        dest='download_slave')
    download_group.add_argument(
        '--download-limit',
        help='global limit of objects to download (for debugging)',
        type=int)
    parser.add_argument(
        '--schema',
        help='what schema to process the files as',
        default=config.get('fallback_schema'))
    parser.add_argument(
        '--variant',
        help='what variant of schema to process the files',
        default=config.get('fallback_variant'))

    update_group = parser.add_argument_group('Update options')
    group = update_group.add_mutually_exclusive_group()
    group.add_argument(
        '--update-slave',
        help='update the slave database in WooCommerce',
        action="store_true",
        default=config.get('update_slave'))
    group.add_argument(
        '--skip-update-slave',
        help='don\'t update the slave database',
        action="store_false",
        dest='update_slave')
    group = update_group.add_mutually_exclusive_group()
    group.add_argument(
        '--do-problematic',
        help='perform problematic updates anyway',
        action="store_true",
        default=config.get('do_problematic'))
    group.add_argument(
        '--skip-problematic',
        help='protect data from problematic updates',
        action="store_false",
        dest='do_problematic')
    group = update_group.add_mutually_exclusive_group()
    group.add_argument(
        '--auto-create-new',
        help='automatically create new products if they don\'t exist yet',
        action="store_true",
        default=config.get('auto_create_new'))
    update_group.add_argument(
        '--no-create-new',
        help='do not create new items, print which need to be created',
        action="store_false",
        dest="auto_create_new")
    group = update_group.add_mutually_exclusive_group()
    group.add_argument(
        '--auto-delete-old',
        help='automatically delete old products if they don\'t exist any more',
        action="store_true",
        default=config.get('auto_delete_old'))
    group.add_argument(
        '--no-delete-old',
        help='do not delete old items, print which need to be deleted',
        action="store_false",
        dest="auto_create_new")
    update_group.add_argument(
        '--slave-timeout',
        help='timeout when using the slave api',
        default=config.get('slave_timeout'))
    update_group.add_argument(
        '--slave-limit',
        help='limit per page when using the slave api',
        default=config.get('slave_limit'))
    update_group.add_argument(
        '--slave-offset',
        help='offset when using the slave api (for debugging)',
        default=config.get('slave_offset'))
    group = update_group.add_mutually_exclusive_group()
    group.add_argument(
        '--ask-before-update',
        help="ask before updating",
        action="store_true",
        default=True)
    group.add_argument(
        '--force-update',
        help="don't ask before updating",
        action="store_false",
        dest="ask_before_update")

    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        '--do-sync',
        help='sync the databases',
        action="store_true",
        default=config.get('do_sync'))
    group.add_argument(
        '--skip-sync',
        help='don\'t sync the databases',
        action="store_false",
        dest='do_sync')

    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        '--do-categories',
        help='sync categories',
        action="store_true",
        default=config.get('do_categories'))
    group.add_argument(
        '--skip-categories',
        help='don\'t sync categories',
        action="store_false",
        dest='do_categories')

    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        '--do-variations',
        help='sync variations',
        action="store_true",
        default=config.get('do_variations'))
    group.add_argument(
        '--skip-variations',
        help='don\'t sync variations',
        action="store_false",
        dest='do_variations')

    report_group = parser.add_argument_group('Report options')
    group = report_group.add_mutually_exclusive_group()
    group.add_argument(
        '--show-report',
        help='generate report files',
        action="store_true",
        default=config.get('show_report'))
    group.add_argument(
        '--skip-report',
        help='don\'t generate report files',
        action="store_false",
        dest='show_report')
    group = report_group.add_mutually_exclusive_group()
    group.add_argument(
        '--print-report',
        help='pirnt report in terminal',
        action="store_true",
        default=config.get('show_report'))
    group.add_argument(
        '--skip-print-report',
        help='don\'t print report in terminal',
        action="store_false",
        dest='print_report')
    group = report_group.add_mutually_exclusive_group()
    group.add_argument(
        '--report-and-quit',
        help='quit after generating report',
        action="store_true",
        default=config.get('report_and_quit'))

    images_group = parser.add_argument_group('Image options')
    group = images_group.add_mutually_exclusive_group()
    group.add_argument(
        '--do-images',
        help='process images',
        action="store_true",
        default=config.get('do_images'))
    group.add_argument(
        '--skip-images',
        help='don\'t process images',
        action="store_false",
        dest='do_images')
    group = images_group.add_mutually_exclusive_group()
    group.add_argument(
        '--do-delete-images',
        help='delete extra images in compressed folder',
        action="store_true",
        default=config.get('do_delete_images'))
    group.add_argument(
        '--skip-delete-images',
        help='protect images from deletion',
        action="store_false",
        dest='do_delete_images')
    group = images_group.add_mutually_exclusive_group()
    group.add_argument(
        '--do-resize-images',
        help='resize images in compressed folder',
        action="store_true",
        default=config.get('do_resize_images'))
    group.add_argument(
        '--skip-resize-images',
        help='protect images from resizing',
        action="store_false",
        dest='do_resize_images')
    group = images_group.add_mutually_exclusive_group()
    group.add_argument(
        '--do-remeta-images',
        help='remeta images in compressed folder',
        action="store_true",
        default=config.get('do_remeta_images'))
    group.add_argument(
        '--skip-remeta-images',
        help='protect images from resizing',
        action="store_false",
        dest='do_remeta_images')
    images_group.add_argument(
        '--img-raw-folder',
        help='location of raw images',
        default=config.get('imgRawFolder'))
    images_group.add_argument(
        '--img-raw-extra-folder',
        help='location of additional raw images',
        default=config.get('imgRawExtraFolder'))
    images_group.add_argument(
        '--require-images',
        help='require that all items have images',
        default=True)

    specials_group = parser.add_argument_group('Specials options')
    group = specials_group.add_mutually_exclusive_group()
    group.add_argument(
        '--do-specials',
        help='process specials',
        action="store_true",
        default=config.get('do_specials'))
    group.add_argument(
        '--skip-specials',
        help='don\'t process specials',
        action="store_false",
        dest='do_specials')
    specials_group.add_argument(
        '--specials-mode',
        help='Select which mode to process the specials in',
        choices=['override', 'auto_next', 'all_future'],
        default='override')
    specials_group.add_argument(
        '--current-special',
        help='prefix of current special code',
        default=config.get('current_special', 'SP'))
    # specials_group.add_argument('--add-special-categories',
    #     help='add special items to special category',
    #     action="store_true",
    #     default=config.get('add_special_categories'))

    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        '--do-dyns',
        help='process dynamic pricing rules',
        action="store_true",
        default=config.get('do_dyns'))
    group.add_argument(
        '--skip-dyns',
        help='don\'t process dynamic pricing rules',
        action="store_false",
        dest='do_dyns')

    debug_group = parser.add_argument_group('Debug options')
    debug_group.add_argument(
        '--debug-abstract', action='store_true', dest='debug_abstract')
    debug_group.add_argument(
        '--debug-parser', action='store_true', dest='debug_parser')
    debug_group.add_argument(
        '--debug-flat', action='store_true', dest='debug_flat')
    debug_group.add_argument(
        '--debug-client', action='store_true', dest='debug_client')
    debug_group.add_argument(
        '--debug-utils', action='store_true', dest='debug_utils')
    debug_group.add_argument(
        '--debug-gen', action='store_true', dest='debug_gen')
    debug_group.add_argument(
        '--debug-myo', action='store_true', dest='debug_myo')
    debug_group.add_argument(
        '--debug-tree', action='store_true', dest='debug_tree')
    debug_group.add_argument(
        '--debug-woo', action='store_true', dest='debug_woo')
    debug_group.add_argument(
        '--debug-name', action='store_true', dest='debug_name')
    debug_group.add_argument(
        '--debug-img', action='store_true', dest='debug_img')
    debug_group.add_argument(
        '--debug-api', action='store_true', dest='debug_api')
    debug_group.add_argument(
        '--debug-shop', action='store_true', dest='debug_shop')
    debug_group.add_argument(
        '--debug-update', action='store_true', dest='debug_update')
    debug_group.add_argument(
        '--debug-mro', action='store_true', dest='debug_mro')
    debug_group.add_argument(
        '--debug-gdrive', action='store_true', dest='debug_gdrive')
    debug_group.add_argument(
        '--debug-special', action='store_true', dest='debug_special')
    debug_group.add_argument(
        '--debug-cats', action='store_true', dest='debug_cats')
    debug_group.add_argument(
        '--debug-vars', action='store_true', dest='debug_vars')

    return parser

def populate_parsers(settings):
    """
    Creates and populates the various parsers
    """
    for thing in [
            'g_drive_params', 'wc_api_params', 'api_product_parser_args',
            'product_parser_args'
    ]:
        Registrar.registerMessage("%s: %s" % (thing, getattr(settings, thing)))

    if settings.schema in settings.myo_schemas:
        col_data_class = ColData_MYO
    elif settings.schema in settings.woo_schemas:
        col_data_class = ColData_Woo
    else:
        col_data_class = ColData_Base
    settings.product_parser_args.update(**{
        'cols':
        col_data_class.getImportCols(),
        'defaults':
        col_data_class.getDefaults(),
    })
    if settings.schema in settings.myo_schemas:
        product_parser_class = CSVParse_MYO
    elif settings.schema in settings.woo_schemas:
        if settings.schema == "TT":
            product_parser_class = CSVParse_TT
        elif settings.schema == "VT":
            product_parser_class = CSVParse_VT
        else:
            settings.product_parser_args['schema'] = settings.schema
            product_parser_class = CSVParse_Woo

    parsers = argparse.Namespace()

    parsers.dyn = CSVParse_Dyn()
    parsers.special = CSVParse_Special()

    if settings.download_master:
        if Registrar.DEBUG_GDRIVE:
            Registrar.registerMessage("GDrive params: %s" %
                                      settings.g_drive_params)
        client_class = SyncClient_GDrive
        client_args = [settings.g_drive_params]
    else:
        client_class = SyncClient_Local
        client_args = []
    #
    with client_class(*client_args) as client:
        if settings.schema in settings.woo_schemas:
            if settings.do_dyns:
                Registrar.registerMessage("analysing dprc rules")
                client.analyseRemote(
                    parsers.dyn, settings.dprc_path, gid=settings.dprc_gid)
                settings.product_parser_args['dprcRules'] = parsers.dyn.taxos

                Registrar.registerMessage("analysing dprp rules")
                parsers.dyn.clearTransients()
                client.analyseRemote(
                    parsers.dyn, settings.dprp_path, gid=settings.dprp_gid)
                settings.product_parser_args['dprpRules'] = parsers.dyn.taxos

            if settings.do_specials:
                Registrar.registerMessage("analysing specials")
                client.analyseRemote(
                    parsers.special, settings.spec_path, gid=settings.spec_gid)
                if Registrar.DEBUG_SPECIAL:
                    Registrar.registerMessage("all specials: %s" %
                                              parsers.special.tabulate())
                settings.product_parser_args[
                    'specialRules'] = parsers.special.rules

                # all_future_groups = parsers.special.all_future()
                # print "all_future_groups: %s" % all_future_groups
                current_special_groups = parsers.special.determine_current_special_groups(
                    specials_mode=settings.specials_mode,
                    current_special=settings.current_special)
                if Registrar.DEBUG_SPECIAL:
                    Registrar.registerMessage("current_special_groups: %s" %
                                              current_special_groups)

                # print "parsers.special.DEBUG_SPECIAL: %s" % repr(parsers.special.DEBUG_SPECIAL)
                # print "Registrar.DEBUG_SPECIAL: %s" %
                # repr(Registrar.DEBUG_SPECIAL)

                if settings.do_categories:
                    # determine current specials

                    if current_special_groups:
                        settings.product_parser_args[
                            'currentSpecialGroups'] = current_special_groups
                        settings.product_parser_args[
                            'add_special_categories'] = settings.add_special_categories

        parsers.product = product_parser_class(**settings.product_parser_args)

        Registrar.registerProgress("analysing product data")

        client.analyseRemote(
            parsers.product,
            settings.gen_path,
            gid=settings.gen_gid,
            limit=settings.download_limit)

        return parsers

def main(override_args=None, settings=None):
    """ The main function for generator """
    if not settings:
        settings = argparse.Namespace()
    if not hasattr(settings, 'yaml_path'):
        settings.yaml_path = "generator_config.yaml"

    # Process YAML file for defaults

    config = {}

    with open(settings.yaml_path) as stream:
        config = yaml.load(stream)

        # overrides
        if 'inFolder' in config.keys():
            settings.in_folder = config['inFolder']
        if 'outFolder' in config.keys():
            settings.out_folder = config['outFolder']
        if 'logFolder' in config.keys():
            settings.log_folder = config['logFolder']

        # mandatory
        settings.merge_mode = config.get('merge_mode', 'sync')
        settings.master_name = config.get('master_name', 'MASTER')
        settings.slave_name = config.get('slave_name', 'SLAVE')
        settings.default_last_sync = config.get('default_last_sync')
        settings.web_folder = config.get('webFolder')
        settings.web_address = config.get('webAddress')
        settings.web_browser = config.get('webBrowser')
        settings.myo_schemas = config.get('myo_schemas')
        settings.woo_schemas = config.get('woo_schemas')
        settings.taxo_depth = config.get('taxoDepth')
        settings.item_depth = config.get('itemDepth')

        settings.img_cmp_folder = config.get('imgCmpFolder')

        settings.gdrive_scopes = config.get('gdrive_scopes')
        settings.gdrive_client_secret_file = config.get(
            'gdrive_client_secret_file')
        settings.gdrive_app_name = config.get('gdrive_app_name')
        settings.gdrive_oauth_client_id = config.get('gdrive_oauth_clientID')
        settings.gdrive_oauth_client_secret = config.get(
            'gdrive_oauth_clientSecret')
        settings.gdrive_credentials_dir = config.get('gdrive_credentials_dir')
        settings.gdrive_credentials_file = config.get(
            'gdrive_credentials_file')
        settings.gen_fid = config.get('genFID')
        settings.gen_gid = config.get('genGID')
        settings.dprc_gid = config.get('dprcGID')
        settings.dprp_gid = config.get('dprpGID')
        settings.spec_gid = config.get('specGID')

    assert all([
        settings.in_folder, settings.out_folder, settings.log_folder,
        settings.woo_schemas, settings.myo_schemas, settings.taxo_depth,
        settings.item_depth
    ])

    settings.gen_path = os.path.join(settings.in_folder, 'generator.csv')
    settings.dprc_path = os.path.join(settings.in_folder, 'DPRC.csv')
    settings.dprp_path = os.path.join(settings.in_folder, 'DPRP.csv')
    settings.spec_path = os.path.join(settings.in_folder, 'specials.csv')

    ### GET SHELL ARGS ###

    argparser = make_argparser(config)

    parser_override = []
    if override_args:
        parser_override = override_args.split(' ')
    args = argparser.parse_args(*parser_override)
    if args:
        if args.verbosity > 0:
            Registrar.DEBUG_PROGRESS = True
            Registrar.DEBUG_ERROR = True
        if args.verbosity > 1:
            Registrar.DEBUG_MESSAGE = True
            Registrar.registerMessage("raw args: %s" % pformat(vars(args)))
        if args.quiet:
            Registrar.DEBUG_PROGRESS = False
            Registrar.DEBUG_ERROR = False
            Registrar.DEBUG_MESSAGE = False

        settings.schema = args.schema
        settings.download_master = args.download_master
        settings.do_sync = args.do_sync and args.download_slave
        settings.do_categories = args.do_categories
        settings.do_dyns = args.do_dyns
        settings.do_specials = args.do_specials
        settings.do_images = args.do_images
        settings.current_special = args.current_special
        settings.add_special_categories = settings.do_specials and settings.do_categories
        settings.download_limit = args.download_limit
        settings.specials_mode = args.specials_mode

        if args.auto_create_new:
            exc = UserWarning("auto-create not fully implemented yet")
            Registrar.registerWarning(exc)
        if args.auto_delete_old:
            raise UserWarning("auto-delete not implemented yet")

        if settings.do_images and os.name == 'nt':
            raise UserWarning("Images not implemented on all platforms yet")

        settings.img_raw_folders = [args.img_raw_folder]
        if args.img_raw_extra_folder is not None:
            settings.img_raw_folders.append(args.img_raw_extra_folder)

        if args.debug_abstract is not None:
            Registrar.DEBUG_ABSTRACT = args.debug_abstract
        if args.debug_parser is not None:
            Registrar.DEBUG_PARSER = args.debug_parser
        if args.debug_flat is not None:
            Registrar.DEBUG_FLAT = args.debug_flat
        if args.debug_gen is not None:
            Registrar.DEBUG_GEN = args.debug_gen
        if args.debug_myo is not None:
            Registrar.DEBUG_MYO = args.debug_myo
        if args.debug_tree is not None:
            Registrar.DEBUG_TREE = args.debug_tree
        if args.debug_woo is not None:
            Registrar.DEBUG_WOO = args.debug_woo
        if args.debug_name is not None:
            Registrar.DEBUG_NAME = args.debug_name
        if args.debug_img is not None:
            Registrar.DEBUG_IMG = args.debug_img
        if args.debug_api is not None:
            Registrar.DEBUG_API = args.debug_api
        if args.debug_shop is not None:
            Registrar.DEBUG_SHOP = args.debug_shop
        if args.debug_update is not None:
            Registrar.DEBUG_UPDATE = args.debug_update
        if args.debug_mro is not None:
            Registrar.DEBUG_MRO = args.debug_mro
        if args.debug_gdrive is not None:
            Registrar.DEBUG_GDRIVE = args.debug_gdrive
        if args.debug_special is not None:
            Registrar.DEBUG_SPECIAL = args.debug_special
        if args.debug_cats is not None:
            Registrar.DEBUG_CATS = args.debug_cats
        if args.debug_vars is not None:
            Registrar.DEBUG_VARS = args.debug_vars

    # process YAML file after determining mode

    with open(settings.yaml_path) as stream:
        option_name_prefix = 'test_' if args.testmode else ''
        config = yaml.load(stream)
        settings.wc_api_key = config.get(option_name_prefix + 'wc_api_key')
        settings.wc_api_secret = config.get(option_name_prefix +
                                            'wc_api_secret')
        settings.wp_srv_offset = config.get(
            option_name_prefix + 'wp_srv_offset', 0)
        store_url = config.get(option_name_prefix + 'store_url', '')

    # PROCESS CONFIG

    TimeUtils.setWpSrvOffset(settings.wp_srv_offset)
    SyncUpdate.setGlobals(settings.master_name, settings.slave_name,
                          settings.merge_mode, settings.default_last_sync)

    if args.variant == "ACC":
        settings.gen_path = os.path.join(settings.in_folder,
                                         'generator-solution.csv')

    if args.variant == "SOL":
        settings.gen_path = os.path.join(settings.in_folder,
                                         'generator-accessories.csv')

    suffix = settings.schema
    if args.variant:
        suffix += "-" + args.variant

    settings.fla_path = os.path.join(settings.out_folder,
                                     "flattened-" + suffix + ".csv")
    settings.flv_path = os.path.join(settings.out_folder,
                                     "flattened-variations-" + suffix + ".csv")
    settings.cat_path = os.path.join(settings.out_folder,
                                     "categories-" + suffix + ".csv")
    settings.myo_path = os.path.join(settings.out_folder,
                                     "myob-" + suffix + ".csv")
    # bunPath = os.path.join(settings.out_folder , "bundles-"+suffix+".csv")
    settings.rep_name = "prod_sync_report%s.html" % suffix
    settings.rep_path = os.path.join(settings.out_folder, settings.rep_name)
    settings.rep_web_path = os.path.join(settings.web_folder,
                                         settings.rep_name)
    settings.rep_web_link = urlparse.urljoin(settings.web_address,
                                             settings.rep_name)

    settings.slave_delta_csv_path = os.path.join(
        settings.out_folder, "delta_report_wp%s.csv" % suffix)

    settings.img_dst = os.path.join(settings.img_cmp_folder,
                                    "images-" + settings.schema)

    if settings.do_specials:
        if settings.current_special:
            CSVParse_Woo.current_special = settings.current_special
        CSVParse_Woo.specialsCategory = "Specials"
        CSVParse_Woo.add_special_categories = settings.add_special_categories

    CSVParse_Woo.do_images = settings.do_images
    CSVParse_Woo.do_dyns = settings.do_dyns
    CSVParse_Woo.do_specials = settings.do_specials

    exclude_cols = []

    if not settings.do_images:
        exclude_cols.extend(['Images', 'imgsum'])

    if not settings.do_categories:
        exclude_cols.extend(['catsum', 'catlist'])

    if not settings.do_dyns:
        exclude_cols.extend([
            'DYNCAT', 'DYNPROD', 'spsum', 'dprclist', 'dprplist', 'dprcIDlist',
            'dprpIDlist', 'dprcsum', 'dprpsum', 'pricing_rules'
        ])

    if not settings.do_specials:
        exclude_cols.extend([
            'SCHEDULE', 'sale_price', 'sale_price_dates_from',
            'sale_price_dates_to', 'RNS', 'RNF', 'RNT', 'RPS', 'RPF', 'RPT',
            'WNS', 'WNF', 'WNT', 'WPS', 'WPF', 'WPT', 'DNS', 'DNF', 'DNT',
            'DPS', 'DPF', 'DPT'
        ])

    ########################################
    # Create Product Parser object
    ########################################

    settings.g_drive_params = {
        'scopes': settings.gdrive_scopes,
        'client_secret_file': settings.gdrive_client_secret_file,
        'app_name': settings.gdrive_app_name,
        'oauth_clientID': settings.gdrive_oauth_client_id,
        'oauth_clientSecret': settings.gdrive_oauth_client_secret,
        'credentials_dir': settings.gdrive_credentials_dir,
        'credentials_file': settings.gdrive_credentials_file,
        'genFID': settings.gen_fid,
    }

    if not settings.download_master:
        settings.g_drive_params['skip_download'] = True

    settings.wc_api_params = {
        'api_key': settings.wc_api_key,
        'api_secret': settings.wc_api_secret,
        'url': store_url,
        'timeout': args.slave_timeout,
        'offset': args.slave_offset,
        'limit': args.slave_limit
    }

    settings.api_product_parser_args = {
        'importName': settings.import_name,
        'itemDepth': settings.item_depth,
        'taxoDepth': settings.taxo_depth,
        'cols': ColData_Woo.getImportCols(),
        'defaults': ColData_Woo.getDefaults(),
    }

    settings.product_parser_args = {
        'importName': settings.import_name,
        'itemDepth': settings.item_depth,
        'taxoDepth': settings.taxo_depth,
    }

    parsers = populate_parsers(settings)

    for category_name, category_list in parsers.product.categories_name.items():
        if len(category_list) < 2:
            continue
        if listUtils.checkEqual(
                [category.namesum for category in category_list]):
            continue
        print "bad category: %50s | %d | %s" % (
            category_name[:50], len(category_list), str(category_list))

    check_warnings()

    #########################################
    # Images
    #########################################

    if settings.do_images and settings.schema in settings.woo_schemas:

        Registrar.registerProgress("processing images")

        if Registrar.DEBUG_IMG:
            Registrar.registerMessage("Looking in folders: %s" %
                                      settings.img_raw_folders)

        def invalid_image(img_name, error):
            """ Register error globally and attribute to image """
            Registrar.registerError(error, img_name)
            parsers.product.images[img_name].invalidate(error)

        ls_raw = {}
        for folder in settings.img_raw_folders:
            if folder:
                ls_raw[folder] = os.listdir(folder)

        def get_raw_image(img_name):
            """
            finds the path of the image in the raw image folders

            Args:
                img_name (str):
                    the name of the file to search for

            Returns:
                The path of the image within the raw image folders

            Raises:
                IOError: file could not be found
            """
            for path in settings.img_raw_folders:
                if path and img_name in ls_raw[path]:
                    return os.path.join(path, img_name)
            raise IOError("no image named %s found" % str(img_name))

        if not os.path.exists(settings.img_dst):
            os.makedirs(settings.img_dst)

        # list of images in compressed directory
        ls_cmp = os.listdir(settings.img_dst)
        for fname in ls_cmp:
            if fname not in parsers.product.images.keys():
                Registrar.registerWarning("DELETING FROM REFLATTENED", fname)
                if args.do_delete_images:
                    os.remove(os.path.join(settings.img_dst, fname))

        for img, data in parsers.product.images.items():
            if not data.products:
                continue
                # we only care about product images atm
            if Registrar.DEBUG_IMG:
                if data.categories:
                    Registrar.registerMessage("Associated Taxos: " + str(
                        [(taxo.rowcount, taxo.codesum)
                         for taxo in data.categories]), img)

                if data.products:
                    Registrar.registerMessage("Associated Products: " + str([
                        (item.rowcount, item.codesum) for item in data.products
                    ]), img)

            try:
                img_raw_path = get_raw_image(img)
            except IOError as exc:
                invalid_image(
                    img,
                    UserWarning("could not get raw image: %s " % repr(exc)))
                continue

            name, _ = os.path.splitext(img)
            if not name:
                invalid_image(img, UserWarning("could not extract name"))
                continue

            try:
                title, description = data.title, data.description
            except AttributeError as exc:
                invalid_image(
                    img, "could not get title or description: " + str(exc))
                continue

            if Registrar.DEBUG_IMG:
                Registrar.registerMessage("title: %s | description: %s" %
                                          (title, description), img)

            # ------
            # REMETA
            # ------

            try:
                if args.do_remeta_images:
                    metagator = MetaGator(img_raw_path)
            except Exception, exc:
                invalid_image(img, "error creating metagator: " + str(exc))
                continue

            try:
                if args.do_remeta_images:
                    metagator.update_meta({
                        'title': title,
                        'description': description
                    })
            except Exception as exc:
                invalid_image(img, "error updating meta: " + str(exc))

            # ------
            # RESIZE
            # ------

            if args.do_resize_images:
                if not os.path.isfile(img_raw_path):
                    invalid_image(img,
                                  "SOURCE FILE NOT FOUND: %s" % img_raw_path)
                    continue

                img_dst_path = os.path.join(settings.img_dst, img)
                if os.path.isfile(img_dst_path):
                    img_src_mod = max(
                        os.path.getmtime(img_raw_path),
                        os.path.getctime(img_raw_path))
                    img_dst_mod = os.path.getmtime(img_dst_path)
                    # print "image mod (src, dst): ", img_src_mod, imgdstmod
                    if img_dst_mod > img_src_mod:
                        if Registrar.DEBUG_IMG:
                            Registrar.registerMessage(
                                img,
                                "DESTINATION FILE NEWER: %s" % img_dst_path)
                        continue

                if Registrar.DEBUG_IMG:
                    Registrar.registerMessage("resizing: %s" % img)

                shutil.copy(img_raw_path, img_dst_path)

                try:
                    # imgmeta = MetaGator(img_dst_path)
                    # imgmeta.write_meta(title, description)
                    # print imgmeta.read_meta()

                    image = Image.open(img_dst_path)
                    image.thumbnail(settings.thumbsize)
                    image.save(img_dst_path)



                    if args.do_remeta_images:
                        imgmeta = MetaGator(img_dst_path)
                        imgmeta.write_meta(title, description)
                        # print imgmeta.read_meta()

                except IOError as exc:
                    invalid_image(img, "could not resize: " + str(exc))
                    continue

        # # ------
        # # RSYNC
        # # ------
        #
        # if not os.path.exists(wpaiFolder):
        #     os.makedirs(wpaiFolder)
        #
        # rsync.main([os.path.join(img_dst,'*'), wpaiFolder])

        #########################################
        # Export Info to Spreadsheets
        #########################################

    Registrar.registerProgress("Exporting info to spreadsheets")

    if settings.schema in settings.myo_schemas:
        product_cols = ColData_MYO.getProductCols()
        product_list = MYOProdList(parsers.product.products.values())
        product_list.exportItems(settings.myo_path,
                                 ColData_Base.getColNames(product_cols))
    elif settings.schema in settings.woo_schemas:
        product_cols = ColData_Woo.getProductCols()

        for col in exclude_cols:
            if col in product_cols:
                del product_cols[col]

        attribute_cols = ColData_Woo.getAttributeCols(parsers.product.attributes, parsers.product.vattributes)
        product_colnames = ColData_Base.getColNames(
            listUtils.combineOrderedDicts(product_cols, attribute_cols))

        product_list = WooProdList(parsers.product.products.values())
        product_list.exportItems(settings.fla_path, product_colnames)

        # variations

        variation_cols = ColData_Woo.getVariationCols()

        attribute_meta_cols = ColData_Woo.getAttributeMetaCols(parsers.product.vattributes)
        variation_col_names = ColData_Base.getColNames(
            listUtils.combineOrderedDicts(variation_cols, attribute_meta_cols))

        if parsers.product.variations:
            variation_list = WooVarList(parsers.product.variations.values())
            variation_list.exportItems(settings.flv_path, variation_col_names)

        if parsers.product.categories:
            # categories
            category_cols = ColData_Woo.getCategoryCols()

            category_list = WooCatList(parsers.product.categories.values())
            category_list.exportItems(settings.cat_path,
                                      ColData_Base.getColNames(category_cols))

        # specials
        if settings.do_specials:
            # current_special = settings.current_special
            current_special = None
            if parsers.product.currentSpecialGroups:
                current_special = parsers.product.currentSpecialGroups[0].ID
            if current_special:
                special_products = parsers.product.onspecial_products.values()
                if special_products:
                    fla_name, fla_ext = os.path.splitext(settings.fla_path)
                    fls_path = os.path.join(
                        settings.out_folder,
                        fla_name + "-" + current_special + fla_ext)
                    special_product_list = WooProdList(special_products)
                    special_product_list.exportItems(fls_path,
                                                     product_colnames)
                special_variations = parsers.product.onspecial_variations.values(
                )
                if special_variations:
                    flv_name, flv_ext = os.path.splitext(settings.flv_path)
                    flvs_path = os.path.join(
                        settings.out_folder,
                        flv_name + "-" + current_special + flv_ext)

                    sp_variation_list = WooVarList(special_variations)
                    sp_variation_list.exportItems(flvs_path,
                                                  variation_col_names)

        updated_products = parsers.product.updated_products.values()
        if updated_products:
            fla_name, fla_ext = os.path.splitext(settings.fla_path)
            flu_path = os.path.join(settings.out_folder,
                                    fla_name + "-Updated" + fla_ext)

            updated_product_list = WooProdList(updated_products)
            updated_product_list.exportItems(flu_path, product_colnames)

        updated_variations = parsers.product.updated_variations.values()

        if updated_variations:
            flv_name, flv_ext = os.path.splitext(settings.flv_path)
            flvu_path = os.path.join(settings.out_folder,
                                     flv_name + "-Updated" + flv_ext)

            updated_variations_list = WooVarList(updated_variations)
            updated_variations_list.exportItems(flvu_path, variation_col_names)

        #########################################
        # Attempt download API data
        #########################################

    if args.download_slave:

        api_product_parser = CSVParse_Woo_Api(
            **settings.api_product_parser_args)

        with ProdSyncClient_WC(settings.wc_api_params) as client:
            # try:
            if settings.do_categories:
                client.analyseRemoteCategories(api_product_parser)

            Registrar.registerProgress("analysing WC API data")

            client.analyseRemote(api_product_parser, limit=settings.download_limit)

        # print api_product_parser.categories
    else:
        api_product_parser = None

    #########################################
    # Attempt Matching
    #########################################

    Registrar.registerProgress("Attempting matching")

    s_delta_updates = []
    # mDeltaUpdates = []
    slave_product_updates = []
    problematic_product_updates = []
    slave_variation_updates = []
    problematic_variation_updates = []
    master_category_updates = []
    slave_category_updates = []
    problematic_category_updates = []

    slave_product_creations = []

    # product_index_fn = (lambda x: x.codesum)
    def product_index_fn(product):
        """ return the codesum of the product """
        return product.codesum

    global_product_matches = MatchList(indexFn=product_index_fn)
    masterless_product_matches = MatchList(indexFn=product_index_fn)
    slaveless_product_matches = MatchList(indexFn=product_index_fn)
    global_variation_matches = MatchList(indexFn=product_index_fn)
    masterless_variation_matches = MatchList(indexFn=product_index_fn)
    slaveless_variation_matches = MatchList(indexFn=product_index_fn)

    def category_index_fn(category):
        """ return the title of the category """
        return category.title

    # category_index_fn = (lambda x: x.title)
    global_category_matches = MatchList(indexFn=category_index_fn)
    masterless_category_matches = MatchList(indexFn=category_index_fn)
    slaveless_category_matches = MatchList(indexFn=category_index_fn)
    delete_categories = OrderedDict()
    join_categories = OrderedDict()

    if settings.do_sync:
        if settings.do_categories:
            if Registrar.DEBUG_CATS:
                Registrar.registerMessage(
                    "matching %d master categories with %d slave categories" %
                    (len(parsers.product.categories),
                     len(api_product_parser.categories)))

            category_matcher = CategoryMatcher()
            category_matcher.clear()
            category_matcher.processRegisters(api_product_parser.categories,
                                              parsers.product.categories)

            if Registrar.DEBUG_CATS:
                if category_matcher.pureMatches:
                    Registrar.registerMessage("All Category matches:\n%s" % (
                        '\n'.join(map(str, category_matcher.matches))))

            valid_category_matches = []
            valid_category_matches += category_matcher.pureMatches

            if category_matcher.duplicateMatches:

                invalid_category_matches = []
                for match in category_matcher.duplicateMatches:
                    master_taxo_sums = [cat.namesum for cat in match.mObjects]
                    if all(master_taxo_sums) \
                            and listUtils.checkEqual(master_taxo_sums) \
                            and not len(match.sObjects) > 1:
                        valid_category_matches.append(match)
                    else:
                        invalid_category_matches.append(match)
                if invalid_category_matches:
                    exc = UserWarning(
                        "categories couldn't be synchronized because of ambiguous names:\n%s"
                        % '\n'.join(map(str, invalid_category_matches)))
                    Registrar.registerError(exc)
                    raise exc

            if category_matcher.slavelessMatches and category_matcher.masterlessMatches:
                exc = UserWarning(
                    "You may want to fix up the following categories before syncing:\n%s\n%s"
                    %
                    ('\n'.join(map(str, category_matcher.slavelessMatches)),
                     '\n'.join(map(str, category_matcher.masterlessMatches))))
                Registrar.registerError(exc)
                # raise exc

            global_category_matches.addMatches(category_matcher.pureMatches)
            masterless_category_matches.addMatches(
                category_matcher.masterlessMatches)
            slaveless_category_matches.addMatches(
                category_matcher.slavelessMatches)

            sync_cols = ColData_Woo.getWPAPICategoryCols()

            # print "SYNC COLS: %s" % pformat(sync_cols.items())

            for match in enumerate(valid_category_matches):
                s_object = match.sObject
                for m_object in match.mObjects:
                    # mObject = match.mObjects[0]

                    sync_update = SyncUpdate_Cat_Woo(m_object, s_object)

                    sync_update.update(sync_cols)

                    # print sync_update.tabulate()

                    if not sync_update.importantStatic:
                        insort(problematic_category_updates, sync_update)
                        continue

                    if sync_update.mUpdated:
                        master_category_updates.append(sync_update)

                    if sync_update.sUpdated:
                        slave_category_updates.append(sync_update)

            for update in master_category_updates:
                if Registrar.DEBUG_UPDATE:
                    Registrar.registerMessage(
                        "performing update < %5s | %5s > = \n%100s, %100s " %
                        (update.MasterID, update.SlaveID,
                         str(update.oldMObject), str(update.oldSObject)))
                if not update.MasterID in parsers.product.categories:
                    exc = UserWarning(
                        "couldn't fine pkey %s in parsers.product.categories" %
                        update.MasterID)
                    Registrar.registerError(exc)
                    continue
                for col, warnings in update.syncWarnings.items():
                    if not col == 'ID':
                        continue
                    for warning in warnings:
                        if not warning['subject'] == update.opposite_src(
                                update.master_name):
                            continue

                        new_val = warning['oldWinnerValue']
                        parsers.product.categories[update.MasterID][
                            col] = new_val

            if Registrar.DEBUG_CATS:
                Registrar.registerMessage("NEW CATEGORIES: %d" %
                                          (len(slaveless_category_matches)))

            if args.auto_create_new:
                # create categories that do not yet exist on slave

                if Registrar.DEBUG_CATS:
                    Registrar.DEBUG_API = True

                with CatSyncClient_WC(settings.wc_api_params) as client:
                    if Registrar.DEBUG_CATS:
                        Registrar.registerMessage("created cat client")
                    new_categories = [
                        match.mObject for match in slaveless_category_matches
                    ]
                    if Registrar.DEBUG_CATS:
                        Registrar.registerMessage("new categories %s" %
                                                  new_categories)

                    while new_categories:
                        category = new_categories.pop(0)
                        if category.parent:
                            parent = category.parent
                            if not parent.isRoot and not parent.WPID and parent in new_categories:
                                new_categories.append(category)
                                continue

                        m_api_data = category.toApiData(ColData_Woo, 'wp-api')
                        for key in ['id', 'slug', 'sku']:
                            if key in m_api_data:
                                del m_api_data[key]
                        m_api_data['name'] = category.wooCatName
                        # print "uploading category: %s" % m_api_data
                        # pprint(m_api_data)
                        if args.update_slave:
                            response = client.createItem(m_api_data)
                            # print response
                            # print response.json()
                            response_api_data = response.json()
                            response_api_data = response_api_data.get(
                                'product_category', response_api_data)
                            api_product_parser.processApiCategory(
                                response_api_data)
                            api_cat_translation = OrderedDict()
                            for key, data in ColData_Woo.getWPAPICategoryCols(
                            ).items():
                                try:
                                    wp_api_key = data['wp-api']['key']
                                except (IndexError, TypeError):
                                    wp_api_key = key
                                api_cat_translation[wp_api_key] = key
                            # print "TRANSLATION: ", api_cat_translation
                            category_parser_data = api_product_parser.translateKeys(
                                response_api_data, api_cat_translation)
                            if Registrar.DEBUG_CATS:
                                Registrar.registerMessage(
                                    "category being updated with parser data: %s"
                                    % category_parser_data)
                            category.update(category_parser_data)

                            # print "CATEGORY: ", category
            elif slaveless_category_matches:
                for slaveless_category_match in slaveless_category_matches:
                    exc = UserWarning("category needs to be created: %s" %
                                      slaveless_category_match.mObjects[0])
                    Registrar.registerWarning(exc)

        # print parsers.product.toStrTree()
        if Registrar.DEBUG_CATS:
            print "product parser"
            for key, category in parsers.product.categories.items():
                print "%5s | %50s | %s" % (key, category.title[:50],
                                           category.WPID)
        if Registrar.DEBUG_CATS:
            print "api product parser info"
            print "there are %s slave categories registered" % len(
                api_product_parser.categories)
            print "there are %s children of API root" % len(
                api_product_parser.rootData.children)
            print api_product_parser.toStrTree()
            for key, category in api_product_parser.categories.items():
                print "%5s | %50s" % (key, category.title[:50])

        # categoryMatcher = CategoryMatcher()
        # categoryMatcher.clear()
        # categoryMatcher.processRegisters(api_product_parser.categories, parsers.product.categories)

        # print "PRINTING NEW SYNCING PROUCTS"

        # SYNC PRODUCTS

        product_matcher = ProductMatcher()
        product_matcher.processRegisters(api_product_parser.products,
                                         parsers.product.products)
        # print product_matcher.__repr__()

        global_product_matches.addMatches(product_matcher.pureMatches)
        masterless_product_matches.addMatches(product_matcher.masterlessMatches)
        slaveless_product_matches.addMatches(product_matcher.slavelessMatches)

        sync_cols = ColData_Woo.getWPAPICols()
        if Registrar.DEBUG_UPDATE:
            Registrar.registerMessage("sync_cols: %s" % repr(sync_cols))

        for col in exclude_cols:
            if col in sync_cols:
                del sync_cols[col]

        if product_matcher.duplicateMatches:
            exc = UserWarning(
                "products couldn't be synchronized because of ambiguous SKUs:%s"
                % '\n'.join(map(str, product_matcher.duplicateMatches)))
            Registrar.registerError(exc)
            raise exc

        for _, prod_match in enumerate(product_matcher.pureMatches):
            if Registrar.DEBUG_CATS or Registrar.DEBUG_VARS:
                Registrar.registerMessage("processing prod_match: %s" %
                                          prod_match.tabulate())
            m_object = prod_match.mObject
            s_object = prod_match.sObject

            sync_update = SyncUpdate_Prod_Woo(m_object, s_object)

            # , "gcs %s is not variation but object is" % repr(gcs)
            assert not m_object.isVariation
            # , "gcs %s is not variation but object is" % repr(gcs)
            assert not s_object.isVariation
            sync_update.update(sync_cols)

            # print sync_update.tabulate()

            if settings.do_categories:
                category_matcher.clear()
                category_matcher.processRegisters(s_object.categories,
                                                  m_object.categories)

                update_params = {
                    'col': 'catlist',
                    'data': {
                        # 'sync'
                    },
                    'subject': sync_update.master_name
                }

                change_match_list = category_matcher.masterlessMatches
                change_match_list.addMatches(category_matcher.slavelessMatches)

                master_categories = set([
                    master_category.WPID
                    for master_category in m_object.categories.values()
                    if master_category.WPID
                ])
                slave_categories = set([
                    slave_category.WPID
                    for slave_category in s_object.categories.values()
                    if slave_category.WPID
                ])

                if Registrar.DEBUG_CATS:
                    Registrar.registerMessage(
                        "comparing categories of %s:\n%s\n%s\n%s\n%s" %
                        (m_object.codesum, str(m_object.categories.values()),
                         str(s_object.categories.values()),
                         str(master_categories), str(slave_categories), ))

                sync_update.oldMObject['catlist'] = list(master_categories)
                sync_update.oldSObject['catlist'] = list(slave_categories)

                if change_match_list:
                    assert \
                        master_categories != slave_categories, \
                        ("if change_match_list exists, then master_categories "
                         "should not equal slave_categories.\nchange_match_list: \n%s") % \
                        "\n".join(map(pformat, change_match_list))
                    update_params['reason'] = 'updating'
                    # update_params['subject'] = SyncUpdate.master_name

                    # master_categories = [category.wooCatName for category \
                    #                      in change_match_list.merge().mObjects]
                    # slave_categories =  [category.wooCatName for category \
                    #                      in change_match_list.merge().sObjects]

                    sync_update.loserUpdate(**update_params)
                    # sync_update.newMObject['catlist'] = master_categories
                    # sync_update.newSObject['catlist'] = master_categories

                    # update_params['oldLoserValue'] = slave_categories
                    # update_params['oldWinnerValue'] = master_categories
                else:
                    assert\
                        master_categories == slave_categories, \
                        "should equal, %s | %s" % (
                            repr(master_categories),
                            repr(slave_categories)
                        )
                    update_params['reason'] = 'identical'
                    sync_update.tieUpdate(**update_params)

                if Registrar.DEBUG_CATS:
                    Registrar.registerMessage(
                        "category matches for update:\n%s" % (
                            category_matcher.__repr__()))

                for cat_match in category_matcher.masterlessMatches:
                    s_index = s_object.index
                    if delete_categories.get(s_index) is None:
                        delete_categories[s_index] = MatchList()
                    delete_categories[s_index].append(cat_match)
                for cat_match in category_matcher.slavelessMatches:
                    s_index = s_object.index
                    if join_categories.get(s_index) is None:
                        join_categories[s_index] = MatchList()
                    join_categories[s_index].append(cat_match)

            # Assumes that GDrive is read only, doesn't care about master
            # updates
            if not sync_update.sUpdated:
                continue

            if Registrar.DEBUG_UPDATE:
                Registrar.registerMessage("sync updates:\n%s" %
                                          sync_update.tabulate())

            if sync_update.sUpdated and sync_update.sDeltas:
                insort(s_delta_updates, sync_update)

            if not sync_update.importantStatic:
                insort(problematic_product_updates, sync_update)
                continue

            if sync_update.sUpdated:
                insort(slave_product_updates, sync_update)

        if args.do_variations:

            variation_matcher = VariationMatcher()
            variation_matcher.processRegisters(api_product_parser.variations,
                                               parsers.product.variations)

            if Registrar.DEBUG_VARS:
                Registrar.registerMessage("variation matcher:\n%s" %
                                          variation_matcher.__repr__())

            global_variation_matches.addMatches(variation_matcher.pureMatches)
            masterless_variation_matches.addMatches(
                variation_matcher.masterlessMatches)
            slaveless_variation_matches.addMatches(
                variation_matcher.slavelessMatches)

            var_sync_cols = ColData_Woo.getWPAPIVariableCols()
            if Registrar.DEBUG_UPDATE:
                Registrar.registerMessage("var_sync_cols: %s" %
                                          repr(var_sync_cols))

            if variation_matcher.duplicateMatches:
                exc = UserWarning(
                    "variations couldn't be synchronized because of ambiguous SKUs:%s"
                    % '\n'.join(map(str, variation_matcher.duplicateMatches)))
                Registrar.registerError(exc)
                raise exc

            for var_match_count, var_match in enumerate(
                    variation_matcher.pureMatches):
                # print "processing var_match: %s" % var_match.tabulate()
                m_object = var_match.mObject
                s_object = var_match.sObject

                sync_update = SyncUpdate_Var_Woo(m_object, s_object)

                sync_update.update(var_sync_cols)

                # Assumes that GDrive is read only, doesn't care about master
                # updates
                if not sync_update.sUpdated:
                    continue

                if Registrar.DEBUG_VARS:
                    Registrar.registerMessage("var update %d:\n%s" % (
                        var_match_count, sync_update.tabulate()))

                if not sync_update.importantStatic:
                    insort(problematic_variation_updates, sync_update)
                    continue

                if sync_update.sUpdated:
                    insort(slave_variation_updates, sync_update)

            for var_match_count, var_match in enumerate(
                    variation_matcher.slavelessMatches):
                assert var_match.hasNoSlave
                m_object = var_match.mObject

                # sync_update = SyncUpdate_Var_Woo(mObject, None)

                # sync_update.update(var_sync_cols)

                if Registrar.DEBUG_VARS:
                    Registrar.registerMessage("var create %d:\n%s" % (
                        var_match_count, m_object.identifier))

                # TODO: figure out which attribute terms to add

            for var_match_count, var_match in enumerate(
                    variation_matcher.masterlessMatches):
                assert var_match.hasNoMaster
                s_object = var_match.sObject

                # sync_update = SyncUpdate_Var_Woo(None, sObject)

                # sync_update.update(var_sync_cols)

                if Registrar.DEBUG_VARS:
                    Registrar.registerMessage("var delete: %d:\n%s" % (
                        var_match_count, s_object.identifier))

                # TODO: figure out which attribute terms to delete

        if args.auto_create_new:
            for new_prod_count, new_prod_match in enumerate(
                    product_matcher.slavelessMatches):
                m_object = new_prod_match.mObject
                print "will create product %d: %s" % (new_prod_count,
                                                      m_object.identifier)
                api_data = m_object.toApiData(ColData_Woo, 'wp-api')
                for key in ['id', 'slug']:
                    if key in api_data:
                        del api_data[key]
                print "has api data: %s" % pformat(api_data)
                slave_product_creations.append(api_data)

    check_warnings()

    # except Exception, exc:
    #     Registrar.registerError(repr(exc))
    #     args.report_and_quit = True

    #########################################
    # Write Report
    #########################################

    Registrar.registerProgress("Write Report")

    with io.open(settings.rep_path, 'w+', encoding='utf8') as res_file:
        reporter = HtmlReporter()

        # basic_cols = ColData_Woo.getBasicCols()
        # csv_colnames = ColData_Woo.getColNames(
        #     OrderedDict(basic_cols.items() + ColData_Woo.nameCols([
        #         # 'address_reason',
        #         # 'name_reason',
        #         # 'Edited Name',
        #         # 'Edited Address',
        #         # 'Edited Alt Address',
        #     ]).items()))

        # print repr(basic_colnames)
        # unicode_colnames = map(SanitationUtils.coerceUnicode, csv_colnames.values())
        # print repr(unicode_colnames)

        if settings.do_sync and (s_delta_updates):

            delta_group = HtmlReporter.Group('deltas', 'Field Changes')

            s_delta_list = ShopObjList(
                [
                    delta_sync_update.newSObject
                    for delta_sync_update in s_delta_updates \
                    if delta_sync_update.newSObject
                ]
            )

            delta_cols = ColData_Woo.getDeltaCols()

            all_delta_cols = OrderedDict(
                ColData_Woo.getBasicCols().items() + ColData_Woo.nameCols(
                    delta_cols.keys() + delta_cols.values()).items())

            if s_delta_list:
                delta_group.addSection(
                    HtmlReporter.Section(
                        's_deltas',
                        title='%s Changes List' % settings.slave_name.title(),
                        description='%s records that have changed important fields'
                        % settings.slave_name,
                        data=s_delta_list.tabulate(
                            cols=all_delta_cols, tablefmt='html'),
                        length=len(s_delta_list)))

            reporter.addGroup(delta_group)

            if s_delta_list:
                s_delta_list.exportItems(
                    settings.slave_delta_csv_path,
                    ColData_Woo.getColNames(all_delta_cols))

        #
        report_matching = settings.do_sync
        if report_matching:

            matching_group = HtmlReporter.Group('product_matching',
                                                'Product Matching Results')
            if global_product_matches:
                matching_group.addSection(
                    HtmlReporter.Section(
                        'perfect_product_matches',
                        **{
                            'title':
                            'Perfect Matches',
                            'description':
                            "%s records match well with %s" % (
                                settings.slave_name, settings.master_name),
                            'data':
                            global_product_matches.tabulate(tablefmt="html"),
                            'length':
                            len(global_product_matches)
                        }))
            if masterless_product_matches:
                matching_group.addSection(
                    HtmlReporter.Section(
                        'masterless_product_matches',
                        **{
                            'title':
                            'Masterless matches',
                            'description':
                            "matches are masterless",
                            'data':
                            masterless_product_matches.tabulate(
                                tablefmt="html"),
                            'length':
                            len(masterless_product_matches)
                        }))
            if slaveless_product_matches:
                matching_group.addSection(
                    HtmlReporter.Section(
                        'slaveless_product_matches',
                        **{
                            'title':
                            'Slaveless matches',
                            'description':
                            "matches are slaveless",
                            'data':
                            slaveless_product_matches.tabulate(
                                tablefmt="html"),
                            'length':
                            len(slaveless_product_matches)
                        }))
            if matching_group.sections:
                reporter.addGroup(matching_group)

            if settings.do_categories:
                matching_group = HtmlReporter.Group(
                    'category_matching', 'Category Matching Results')
                if global_category_matches:
                    matching_group.addSection(
                        HtmlReporter.Section(
                            'perfect_category_matches',
                            **{
                                'title':
                                'Perfect Matches',
                                'description':
                                "%s records match well with %s" % (
                                    settings.slave_name, settings.master_name),
                                'data':
                                global_category_matches.tabulate(
                                    tablefmt="html"),
                                'length':
                                len(global_category_matches)
                            }))
                if masterless_category_matches:
                    matching_group.addSection(
                        HtmlReporter.Section(
                            'masterless_category_matches',
                            **{
                                'title':
                                'Masterless matches',
                                'description':
                                "matches are masterless",
                                'data':
                                masterless_category_matches.tabulate(
                                    tablefmt="html"),
                                'length':
                                len(masterless_category_matches)
                            }))
                if slaveless_category_matches:
                    matching_group.addSection(
                        HtmlReporter.Section(
                            'slaveless_category_matches',
                            **{
                                'title':
                                'Slaveless matches',
                                'description':
                                "matches are slaveless",
                                'data':
                                slaveless_category_matches.tabulate(
                                    tablefmt="html"),
                                'length':
                                len(slaveless_category_matches)
                            }))
                if matching_group.sections:
                    reporter.addGroup(matching_group)

            if args.do_variations:
                matching_group = HtmlReporter.Group(
                    'variation_matching', 'Variation Matching Results')
                if global_variation_matches:
                    matching_group.addSection(
                        HtmlReporter.Section(
                            'perfect_variation_matches',
                            **{
                                'title':
                                'Perfect Matches',
                                'description':
                                "%s records match well with %s" % (
                                    settings.slave_name, settings.master_name),
                                'data':
                                global_variation_matches.tabulate(
                                    tablefmt="html"),
                                'length':
                                len(global_variation_matches)
                            }))
                if masterless_variation_matches:
                    matching_group.addSection(
                        HtmlReporter.Section(
                            'masterless_variation_matches',
                            **{
                                'title':
                                'Masterless matches',
                                'description':
                                "matches are masterless",
                                'data':
                                masterless_variation_matches.tabulate(
                                    tablefmt="html"),
                                'length':
                                len(masterless_variation_matches)
                            }))
                if slaveless_variation_matches:
                    matching_group.addSection(
                        HtmlReporter.Section(
                            'slaveless_variation_matches',
                            **{
                                'title':
                                'Slaveless matches',
                                'description':
                                "matches are slaveless",
                                'data':
                                slaveless_variation_matches.tabulate(
                                    tablefmt="html"),
                                'length':
                                len(slaveless_variation_matches)
                            }))
                if matching_group.sections:
                    reporter.addGroup(matching_group)

        report_sync = settings.do_sync
        if report_sync:
            syncing_group = HtmlReporter.Group('prod_sync',
                                               'Product Syncing Results')

            syncing_group.addSection(
                HtmlReporter.Section(
                    (SanitationUtils.makeSafeClass(settings.slave_name) +
                     "_product_updates"),
                    description=settings.slave_name + " items will be updated",
                    data='<hr>'.join([
                        update.tabulate(tablefmt="html")
                        for update in slave_product_updates
                    ]),
                    length=len(slave_product_updates)))

            syncing_group.addSection(
                HtmlReporter.Section(
                    "problematic_product_updates",
                    description="items can't be merged because they are too dissimilar",
                    data='<hr>'.join([
                        update.tabulate(tablefmt="html")
                        for update in problematic_product_updates
                    ]),
                    length=len(problematic_product_updates)))

            reporter.addGroup(syncing_group)

            if args.do_variations:
                syncing_group = HtmlReporter.Group('variation_sync',
                                                   'Variation Syncing Results')

                syncing_group.addSection(
                    HtmlReporter.Section(
                        (SanitationUtils.makeSafeClass(settings.slave_name) +
                         "_variation_updates"),
                        description=settings.slave_name +
                        " items will be updated",
                        data='<hr>'.join([
                            update.tabulate(tablefmt="html")
                            for update in slave_variation_updates
                        ]),
                        length=len(slave_variation_updates)))

                syncing_group.addSection(
                    HtmlReporter.Section(
                        "problematic_variation_updates",
                        description="items can't be merged because they are too dissimilar",
                        data='<hr>'.join([
                            update.tabulate(tablefmt="html")
                            for update in problematic_variation_updates
                        ]),
                        length=len(problematic_variation_updates)))

                reporter.addGroup(syncing_group)

        report_cats = settings.do_sync and settings.do_categories
        if report_cats:
            # "reporting cats. settings.do_sync: %s, do_categories: %s" % (
            #     repr(settings.do_sync), repr(settings.do_categories))
            syncing_group = HtmlReporter.Group('cats',
                                               'Category Syncing Results')

            syncing_group.addSection(
                HtmlReporter.Section(
                    ('delete_categories'),
                    description="%s items will leave categories" %
                    settings.slave_name,
                    data=tabulate(
                        [
                            [
                                index,
                                # api_product_parser.products[index],
                                # api_product_parser.products[index].categories,
                                # ", ".join(category.wooCatName \
                                #           for category in matches.merge().mObjects),
                                ", ".join(category.wooCatName
                                          for category in matches.merge()
                                          .sObjects)
                            ] for index, matches in delete_categories.items()
                        ],
                        tablefmt="html"),
                    length=len(delete_categories)
                    # data = '<hr>'.join([
                    #         "%s<br/>%s" % (index, match.tabulate(tablefmt="html")) \
                    #         for index, match in delete_categories.items()
                    #     ]
                    # )
                ))

            delete_categories_ns_data = tabulate(
                [
                    [
                        index,
                        # api_product_parser.products[index],
                        # api_product_parser.products[index].categories,
                        # ", ".join(category.wooCatName for category in matches.merge().mObjects),
                        ", ".join(category.wooCatName for category in matches.merge().sObjects\
                                  if not re.search('Specials', category.wooCatName))
                    ] for index, matches in delete_categories.items()
                ],
                tablefmt="html"
            )

            syncing_group.addSection(
                HtmlReporter.Section(
                    ('delete_categories_not_specials'),
                    description="%s items will leave categories" %
                    settings.slave_name,
                    data=delete_categories_ns_data,
                    length=len(delete_categories)
                    # data = '<hr>'.join([
                    #         "%s<br/>%s" % (index, match.tabulate(tablefmt="html")) \
                    #         for index, match in delete_categories.items()
                    #     ]
                    # )
                ))

            syncing_group.addSection(
                HtmlReporter.Section(
                    ('join_categories'),
                    description="%s items will join categories" %
                    settings.slave_name,
                    data=tabulate(
                        [
                            [
                                index,
                                # api_product_parser.products[index],
                                # api_product_parser.products[index].categories,
                                ", ".join(category.wooCatName
                                          for category in matches.merge()
                                          .mObjects),
                                # ", ".join(category.wooCatName \
                                #           for category in matches.merge().sObjects)
                            ] for index, matches in join_categories.items()
                        ],
                        tablefmt="html"),
                    length=len(join_categories)
                    # data = '<hr>'.join([
                    #         "%s<br/>%s" % (index, match.tabulate(tablefmt="html")) \
                    #         for index, match in delete_categories.items()
                    #     ]
                    # )
                ))

            reporter.addGroup(syncing_group)

        if not reporter.groups:
            empty_group = HtmlReporter.Group('empty', 'Nothing to report')
            # empty_group.addSection(
            #     HtmlReporter.Section(
            #         ('empty'),
            #         data = ''
            #
            #     )
            # )
            Registrar.registerMessage('nothing to report')
            reporter.addGroup(empty_group)

        res_file.write(reporter.getDocumentUnicode())

    if args.report_and_quit:
        sys.exit(ExitStatus.success)

    check_warnings()

    #########################################
    # Perform updates
    #########################################

    all_product_updates = slave_product_updates
    if args.do_variations:
        all_product_updates += slave_variation_updates
    if args.do_problematic:
        all_product_updates += problematic_product_updates
        if args.do_variations:
            all_product_updates += problematic_variation_updates

    # don't perform updates if limit was set
    if settings.download_limit:
        all_product_updates = []

    slave_failures = []
    if all_product_updates:
        Registrar.registerProgress("UPDATING %d RECORDS" %
                                   len(all_product_updates))

        if args.ask_before_update:
            input(
                "Please read reports and press Enter to continue or ctrl-c to stop..."
            )

        if Registrar.DEBUG_PROGRESS:
            update_progress_counter = ProgressCounter(len(all_product_updates))

        with ProdSyncClient_WC(settings.wc_api_params) as slave_client:
            for count, update in enumerate(all_product_updates):
                if Registrar.DEBUG_PROGRESS:
                    update_progress_counter.maybePrintUpdate(count)

                if args.update_slave and update.sUpdated:
                    # print "attempting update to %s " % str(update)

                    try:
                        update.updateSlave(slave_client)
                    except Exception, exc:
                        # slave_failures.append({
                        #     'update':update,
                        #     'master':SanitationUtils.coerceUnicode(update.newMObject),
                        #     'slave':SanitationUtils.coerceUnicode(update.newSObject),
                        #     'mchanges':SanitationUtils.coerceUnicode(update.getMasterUpdates()),
                        #     'schanges':SanitationUtils.coerceUnicode(update.getSlaveUpdates()),
                        #     'exception':repr(exc)
                        # })
                        SanitationUtils.safePrint(
                            "ERROR UPDATING SLAVE (%s): %s" %
                            (update.SlaveID, repr(exc)))
                        slave_failures.append(update)
                # else:
                #     print "no update made to %s " % str(update)

                #########################################
                # Display reports
                #########################################

    Registrar.registerProgress("Displaying reports")

    shutil.copyfile(settings.rep_path, settings.rep_web_path)
    if args.show_report:
        if settings.web_browser:
            os.environ['BROWSER'] = settings.web_browser
            # print "set browser environ to %s" % repr(webBrowser)
        # print "moved file from %s to %s" % (settings.rep_path, repWebPath)

        webbrowser.open(settings.rep_web_link)
    else:
        print "open this link to view report %s" % settings.rep_web_link


def catch_main():
    """
    Run the main function within a try statement and attempt to analyse failure
    """

    settings = argparse.Namespace()

    settings.in_folder = "../input/"
    settings.out_folder = "../output/"
    settings.log_folder = "../logs/"
    settings.src_folder = MODULE_LOCATION

    os.chdir(MODULE_PATH)

    settings.import_name = TimeUtils.getMsTimeStamp()
    settings.rep_path = ''
    settings.m_fail_path = os.path.join(settings.out_folder,
                                        "gdrive_fails.csv")
    settings.s_fail_path = os.path.join(settings.out_folder, "wp_fails.csv")
    settings.log_path = os.path.join(settings.log_folder,
                                     "log_%s.txt" % settings.import_name)
    settings.zip_path = os.path.join(settings.log_folder,
                                     "zip_%s.zip" % settings.import_name)

    settings.thumbsize = 1920, 1200

    status = 0
    try:
        main(settings=settings)
    except SystemExit:
        exit()
    except (ReadTimeout, ConnectionError, ConnectTimeout, ServerNotFoundError):
        status = 69  # service unavailable
        Registrar.registerError(traceback.format_exc())
    except IOError:
        status = 74
        print "cwd: %s" % os.getcwd()
        Registrar.registerError(traceback.format_exc())
    except UserWarning:
        status = 65
        Registrar.registerError(traceback.format_exc())
    except:
        status = 1
        Registrar.registerError(traceback.format_exc())

    with io.open(settings.log_path, 'w+', encoding='utf8') as log_file:
        for source, messages in Registrar.getMessageItems(1).items():
            print source
            log_file.writelines([SanitationUtils.coerceUnicode(source)])
            log_file.writelines([
                SanitationUtils.coerceUnicode(message) for message in messages
            ])
            for message in messages:
                pprint(message, indent=4, width=80, depth=2)

    #########################################
    # zip reports
    #########################################

    files_to_zip = [
        settings.m_fail_path, settings.s_fail_path, settings.rep_path
    ]

    with zipfile.ZipFile(settings.zip_path, 'w') as zip_file:
        for file_to_zip in files_to_zip:
            try:
                os.stat(file_to_zip)
                zip_file.write(file_to_zip)
            except:
                pass
        Registrar.registerMessage('wrote file %s' % settings.zip_path)

    # print "\nexiting with status %s \n" % status
    sys.exit(status)


if __name__ == '__main__':
    catch_main()
