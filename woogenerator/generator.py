"""
Module for generating woocommerce csv import files from Google Drive Data.
"""
# pylint: disable=too-many-lines
# TODO: fix too-many-lines

import io
import os
import re
import shutil
import sys
import time
import traceback
import urlparse
import webbrowser
import zipfile
import platform
from bisect import insort
from collections import OrderedDict
from pprint import pformat, pprint

import argparse
from requests.exceptions import ConnectionError, ConnectTimeout, ReadTimeout
from httplib2 import ServerNotFoundError
from PIL import Image
from tabulate import tabulate
from exitstatus import ExitStatus

import __init__
from woogenerator.coldata import ColDataBase, ColDataMyo, ColDataWoo
from woogenerator.matching import (CategoryMatcher, MatchList, ProductMatcher,
                                   VariationMatcher)
from woogenerator.metagator import MetaGator
from woogenerator.parsing.api import CsvParseWooApi
from woogenerator.parsing.dyn import CsvParseDyn
from woogenerator.parsing.myo import CsvParseMyo, MYOProdList
from woogenerator.parsing.shop import ShopObjList  # ShopProdList,
from woogenerator.parsing.special import CsvParseSpecial
from woogenerator.parsing.woo import (CsvParseTT, CsvParseVT, CsvParseWoo,
                                      WooCatList, WooProdList, WooVarList)
from woogenerator.sync_client import SyncClientGDrive, SyncClientLocal
from woogenerator.sync_client_prod import CatSyncClientWC, ProdSyncClientWC
from woogenerator.syncupdate import (SyncUpdate, SyncUpdateCatWoo,
                                     SyncUpdateProdWoo, SyncUpdateVarWoo)
from woogenerator.utils import (HtmlReporter, ProgressCounter, Registrar,
                                SanitationUtils, SeqUtils, TimeUtils)
from woogenerator.config import (ArgumentParserProd, ArgumentParserProtoProd,
                                 SettingsNamespaceProd)


def timediff(settings):
    """Return time elapsed since start."""
    return time.time() - settings.start_time


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

def populate_master_parsers(settings):  # pylint: disable=too-many-branches,too-many-statements
    """
    Create and populates the various parsers.
    """
    # TODO: fix too-many-branches,too-many-statements

    for thing in [
            'g_drive_params', 'wc_api_params', 'api_product_parser_args',
            'product_parser_args'
    ]:
        Registrar.register_message("%s: %s" %
                                   (thing, getattr(settings, thing)))

    if settings.schema_is_myo:
        col_data_class = ColDataMyo
    elif settings.schema_is_woo:
        col_data_class = ColDataWoo
    else:
        col_data_class = ColDataBase
    settings.product_parser_args.update(**{
        'cols':
        col_data_class.get_import_cols(),
        'defaults':
        col_data_class.get_defaults(),
    })
    if settings.schema_is_myo:
        product_parser_class = CsvParseMyo
    elif settings.schema_is_woo:
        if settings.schema == "TT":
            product_parser_class = CsvParseTT
        elif settings.schema == "VT":
            product_parser_class = CsvParseVT
        else:
            settings.product_parser_args['schema'] = settings.schema
            product_parser_class = CsvParseWoo

    parsers = argparse.Namespace()

    parsers.dyn = CsvParseDyn()
    parsers.special = CsvParseSpecial()

    if settings['download_master']:
        if Registrar.DEBUG_GDRIVE:
            Registrar.register_message("GDrive params: %s" %
                                       settings['g_drive_params'])
        client_class = SyncClientGDrive
        client_args = [settings['g_drive_params']]
    else:
        client_class = SyncClientLocal
        client_args = []
    #
    with client_class(*client_args) as client:
        if settings.schema_is_woo:
            if settings.do_dyns:
                Registrar.register_message("analysing dprc rules")
                client.analyse_remote(
                    parsers.dyn, settings.dprc_path, gid=settings.dprc_gid)
                settings.product_parser_args['dprc_rules'] = parsers.dyn.taxos

                Registrar.register_message("analysing dprp rules")
                parsers.dyn.clear_transients()
                client.analyse_remote(
                    parsers.dyn, settings.dprp_path, gid=settings.dprp_gid)
                settings.product_parser_args['dprp_rules'] = parsers.dyn.taxos

            if settings.do_specials:
                Registrar.register_message("analysing specials")
                client.analyse_remote(
                    parsers.special, settings.spec_path, gid=settings.spec_gid)
                if Registrar.DEBUG_SPECIAL:
                    Registrar.register_message("all specials: %s" %
                                               parsers.special.tabulate())
                settings.product_parser_args[
                    'special_rules'] = parsers.special.rules

                current_special_groups = parsers.special.determine_current_spec_grps(
                    specials_mode=settings.specials_mode,
                    current_special=settings.current_special)
                # print "current_special_groups: %s" % current_special_groups
                if Registrar.DEBUG_SPECIAL:
                    Registrar.register_message("current_special_groups: %s" %
                                               current_special_groups)

                # print "parsers.special.DEBUG_SPECIAL: %s" % repr(parsers.special.DEBUG_SPECIAL)
                # print "Registrar.DEBUG_SPECIAL: %s" % repr(Registrar.DEBUG_SPECIAL)

                settings.product_parser_args[
                    'current_special_groups'] = current_special_groups
                if settings['do_categories']:
                    if current_special_groups:
                        settings.product_parser_args[
                            'add_special_categories'] = settings.add_special_categories

        # print "calling product parser with kwargs: %s" % pformat(settings.product_parser_args)

        parsers.product = product_parser_class(**settings.product_parser_args)

        Registrar.register_progress("analysing product data")

        client.analyse_remote(
            parsers.product,
            settings.gen_path,
            gid=settings.gen_gid,
            limit=settings['download_limit'])

        return parsers


def process_images(settings, parsers):  # pylint: disable=too-many-statements,too-many-branches,too-many-locals
    """Process the images information in from the parsers."""
    # TODO: fix too-many-statements,too-many-branches,too-many-statements

    Registrar.register_progress("processing images")

    if Registrar.DEBUG_IMG:
        Registrar.register_message("Looking in folders: %s" %
                                   settings.img_raw_folders)

    def invalid_image(img_name, error):
        """Register error globally and attribute to image."""
        if settings.require_images:
            Registrar.register_error(error, img_name)
        else:
            Registrar.register_message(error, img_name)
        parsers.product.images[img_name].invalidate(error)

    ls_raw = {}
    for folder in settings.img_raw_folders:
        if folder:
            ls_raw[folder] = os.listdir(folder)

    def get_raw_image(img_name):
        """
        Find the path of the image in the raw image folders.

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
            Registrar.register_warning("DELETING FROM REFLATTENED", fname)
            if settings.do_delete_images:
                os.remove(os.path.join(settings.img_dst, fname))

    for img, data in parsers.product.images.items():
        if not data.products:
            continue
            # we only care about product images atm
        if Registrar.DEBUG_IMG:
            if data.categories:
                Registrar.register_message(
                    "Associated Taxos: " + str([(taxo.rowcount, taxo.codesum)
                                                for taxo in data.categories]),
                    img)

            if data.products:
                Registrar.register_message("Associated Products: " + str([
                    (item.rowcount, item.codesum) for item in data.products
                ]), img)

        try:
            img_raw_path = get_raw_image(img)
        except IOError as exc:
            invalid_image(
                img, UserWarning("could not get raw image: %s " % repr(exc)))
            continue

        name, _ = os.path.splitext(img)
        if not name:
            invalid_image(img, UserWarning("could not extract name"))
            continue

        try:
            title, description = data.title, data.description
        except AttributeError as exc:
            invalid_image(img,
                          "could not get title or description: " + str(exc))
            continue

        if Registrar.DEBUG_IMG:
            Registrar.register_message("title: %s | description: %s" %
                                       (title, description), img)

        # ------
        # REMETA
        # ------

        try:
            if settings.do_remeta_images:
                metagator = MetaGator(img_raw_path)
        except Exception as exc:
            invalid_image(img, "error creating metagator: " + str(exc))
            continue

        try:
            if settings.do_remeta_images:
                metagator.update_meta({
                    'title': title,
                    'description': description
                })
        except Exception as exc:
            invalid_image(img, "error updating meta: " + str(exc))
            Registrar.register_error(traceback.format_exc())

        # ------
        # RESIZE
        # ------

        if settings.do_resize_images:
            if not os.path.isfile(img_raw_path):
                invalid_image(img, "SOURCE FILE NOT FOUND: %s" % img_raw_path)
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
                        Registrar.register_message(
                            img, "DESTINATION FILE NEWER: %s" % img_dst_path)
                    continue

            if Registrar.DEBUG_IMG:
                Registrar.register_message("resizing: %s" % img)

            shutil.copy(img_raw_path, img_dst_path)

            try:
                imgmeta = MetaGator(img_dst_path)
                imgmeta.write_meta(title, description)
                if Registrar.DEBUG_IMG:
                    Registrar.register_message("old dest img meta: %s" % imgmeta.read_meta(), img)


                image = Image.open(img_dst_path)
                image.thumbnail(settings.thumbsize)
                image.save(img_dst_path)

                if settings.do_remeta_images:
                    imgmeta = MetaGator(img_dst_path)
                    imgmeta.write_meta(title, description)
                    if Registrar.DEBUG_IMG:
                        Registrar.register_message("new dest img meta: %s" % imgmeta.read_meta(), img)

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


def export_parsers(settings, parsers):  # pylint: disable=too-many-branches,too-many-statements,too-many-locals
    """Export key information from the parsers to spreadsheets."""
    # TODO: fix too-many-branches,too-many-statements,too-many-locals

    Registrar.register_progress("Exporting info to spreadsheets")

    if settings.schema_is_myo:
        product_cols = ColDataMyo.get_product_cols()
        product_list = MYOProdList(parsers.product.products.values())
        product_list.export_items(settings.myo_path,
                                  ColDataBase.get_col_names(product_cols))
    elif settings.schema_is_woo:
        product_cols = ColDataWoo.get_product_cols()

        for col in settings['exclude_cols']:
            if col in product_cols:
                del product_cols[col]

        attribute_cols = ColDataWoo.get_attribute_cols(
            parsers.product.attributes, parsers.product.vattributes)
        product_colnames = ColDataBase.get_col_names(
            SeqUtils.combine_ordered_dicts(product_cols, attribute_cols))

        product_list = WooProdList(parsers.product.products.values())
        product_list.export_items(settings.fla_path, product_colnames)

        # variations

        variation_cols = ColDataWoo.get_variation_cols()

        attribute_meta_cols = ColDataWoo.get_attribute_meta_cols(
            parsers.product.vattributes)
        variation_col_names = ColDataBase.get_col_names(
            SeqUtils.combine_ordered_dicts(variation_cols, attribute_meta_cols))

        if parsers.product.variations:
            variation_list = WooVarList(parsers.product.variations.values())
            variation_list.export_items(settings.flv_path, variation_col_names)

        if parsers.product.categories:
            # categories
            category_cols = ColDataWoo.get_category_cols()

            category_list = WooCatList(parsers.product.categories.values())
            category_list.export_items(settings.cat_path,
                                       ColDataBase.get_col_names(category_cols))

        # specials
        if settings.do_specials:
            current_special = getattr(settings, 'current_special', None)
            if parsers.product.current_special_groups:
                current_special = parsers.product.current_special_groups[0].special_id
            # print "current special is %s" % current_special
            if current_special:
                special_products = parsers.product.onspecial_products.values()
                if special_products:
                    fla_name, fla_ext = os.path.splitext(settings.fla_path)
                    fls_path = os.path.join(
                        settings.out_folder_full,
                        fla_name + "-" + current_special + fla_ext)
                    special_product_list = WooProdList(special_products)
                    special_product_list.export_items(fls_path,
                                                      product_colnames)
                special_variations = parsers.product.onspecial_variations.values()
                if special_variations:
                    flv_name, flv_ext = os.path.splitext(settings.flv_path)
                    flvs_path = os.path.join(
                        settings.out_folder_full,
                        flv_name + "-" + current_special + flv_ext)

                    sp_variation_list = WooVarList(special_variations)
                    sp_variation_list.export_items(flvs_path,
                                                   variation_col_names)

        updated_products = parsers.product.updated_products.values()
        if updated_products:
            fla_name, fla_ext = os.path.splitext(settings.fla_path)
            flu_path = os.path.join(settings.out_folder_full,
                                    fla_name + "-Updated" + fla_ext)

            updated_product_list = WooProdList(updated_products)
            updated_product_list.export_items(flu_path, product_colnames)

        updated_variations = parsers.product.updated_variations.values()

        if updated_variations:
            flv_name, flv_ext = os.path.splitext(settings.flv_path)
            flvu_path = os.path.join(settings.out_folder_full,
                                     flv_name + "-Updated" + flv_ext)

            updated_variations_list = WooVarList(updated_variations)
            updated_variations_list.export_items(
                flvu_path, variation_col_names)


def main(override_args=None, settings=None):  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
    """Main function for generator."""
    # TODO: too-many-locals,too-many-branches,too-many-statements

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

    # TODO: implement "ask for password" feature
    argparser = ArgumentParserProd()

    # TODO: test set local work dir
    # TODO: test set live config
    # TODO: test set test config
    # TODO: move in, out, log folders to full
    # TODO: move gen, dprc, dprp, spec to full calculated in settings


    for conf in settings.second_stage_configs:
        print "adding conf: %s" % conf
        argparser.add_default_config_file(conf)

    if settings.help_verbose:
        if 'args' not in parser_override:
            parser_override['args'] = []
        parser_override['args'] += ['--help']

    Registrar.register_message("parser: %s " % pformat(argparser.get_actions()))

    settings = argparser.parse_args(**parser_override)


    # PROCESS CONFIG

    Registrar.register_message("Raw settings: %s" % pformat(vars(settings)))

    settings.gen_path = os.path.join(settings.in_folder_full, 'generator.csv')
    settings.dprc_path = os.path.join(settings.in_folder_full, 'DPRC.csv')
    settings.dprp_path = os.path.join(settings.in_folder_full, 'DPRP.csv')
    settings.spec_path = os.path.join(settings.in_folder_full, 'specials.csv')

    # TODO: set up logging here instead of Registrar verbosity crap

    if settings.verbosity > 0:
        Registrar.DEBUG_PROGRESS = True
        Registrar.DEBUG_ERROR = True
    if settings.verbosity > 1:
        Registrar.DEBUG_MESSAGE = True
    if settings.quiet:
        Registrar.DEBUG_PROGRESS = False
        Registrar.DEBUG_ERROR = False
        Registrar.DEBUG_MESSAGE = False

    settings.add_special_categories = settings.do_specials and settings['do_categories']

    if settings['auto_create_new']:
        exc = UserWarning("auto-create not fully implemented yet")
        Registrar.register_warning(exc)
    if settings.auto_delete_old:
        raise UserWarning("auto-delete not implemented yet")
    # if settings.do_images and platform.system() != 'Darwin':
    #     exc = UserWarning("Images not implemented on all platforms yet")
    #     Registrar.register_warning(exc)


    if settings.img_raw_folder is not None:
        settings.img_raw_folders.append(settings.img_raw_folder)
    if settings.img_raw_extra_folder is not None:
        settings.img_raw_folders.append(settings.img_raw_extra_folder)

    Registrar.DEBUG_ABSTRACT = settings.debug_abstract
    Registrar.DEBUG_PARSER = settings.debug_parser
    Registrar.DEBUG_FLAT = settings.debug_flat
    Registrar.DEBUG_GEN = settings.debug_gen
    Registrar.DEBUG_MYO = settings.debug_myo
    Registrar.DEBUG_TREE = settings.debug_tree
    Registrar.DEBUG_WOO = settings.debug_woo
    Registrar.DEBUG_NAME = settings.debug_name
    Registrar.DEBUG_IMG = settings.debug_img
    Registrar.DEBUG_API = settings.debug_api
    Registrar.DEBUG_SHOP = settings.debug_shop
    Registrar.DEBUG_UPDATE = settings.debug_update
    Registrar.DEBUG_MRO = settings.debug_mro
    Registrar.DEBUG_GDRIVE = settings.debug_gdrive
    Registrar.DEBUG_SPECIAL = settings.debug_special
    Registrar.DEBUG_CATS = settings.debug_cats
    Registrar.DEBUG_VARS = settings.debug_vars

    TimeUtils.set_wp_srv_offset(settings.wp_srv_offset)
    SyncUpdate.set_globals(settings.master_name, settings.slave_name,
                           settings.merge_mode, settings.last_sync)

    if settings.variant == "ACC":
        settings.gen_path = os.path.join(settings.in_folder_full,
                                         'generator-solution.csv')

    if settings.variant == "SOL":
        settings.gen_path = os.path.join(settings.in_folder_full,
                                         'generator-accessories.csv')

    suffix = settings.schema
    if settings.variant:
        suffix += "-" + settings.variant

    settings.fla_path = os.path.join(settings.out_folder_full,
                                     "flattened-" + suffix + ".csv")
    settings.flv_path = os.path.join(settings.out_folder_full,
                                     "flattened-variations-" + suffix + ".csv")
    settings.cat_path = os.path.join(settings.out_folder_full,
                                     "categories-" + suffix + ".csv")
    settings.myo_path = os.path.join(settings.out_folder_full,
                                     "myob-" + suffix + ".csv")
    # bunPath = os.path.join(settings.out_folder_full , "bundles-"+suffix+".csv")
    if settings.get('web_folder'):
        settings['rep_web_path'] = os.path.join(
            settings.get('web_folder'),
            settings.rep_name
        )
        settings['rep_web_link'] = urlparse.urljoin(
            settings.get('web_address'),
            settings.rep_name
        )

    settings['slave_delta_csv_path'] = os.path.join(
        settings.out_folder_full, "delta_report_wp%s.csv" % suffix)

    settings.img_dst = os.path.join(settings.img_cmp_folder,
                                    "images-" + settings.schema)

    if settings.do_specials:
        if settings['current_special']:
            CsvParseWoo.current_special = settings['current_special']
        CsvParseWoo.specialsCategory = "Specials"
        CsvParseWoo.add_special_categories = settings['add_special_categories']

    CsvParseWoo.do_images = settings.do_images
    CsvParseWoo.do_dyns = settings.do_dyns
    CsvParseWoo.do_specials = settings.do_specials

    if not settings.get('exclude_cols'):
        settings['exclude_cols'] = []

    if not settings.do_images:
        settings['exclude_cols'].extend(['Images', 'imgsum'])

    if not settings['do_categories']:
        settings['exclude_cols'].extend(['catsum', 'catlist'])

    if not settings.do_dyns:
        settings['exclude_cols'].extend([
            'DYNCAT', 'DYNPROD', 'spsum', 'dprclist', 'dprplist', 'dprcIDlist',
            'dprpIDlist', 'dprcsum', 'dprpsum', 'pricing_rules'
        ])

    if not settings.do_specials:
        settings['exclude_cols'].extend([
            'SCHEDULE', 'sale_price', 'sale_price_dates_from',
            'sale_price_dates_to', 'RNS', 'RNF', 'RNT', 'RPS', 'RPF', 'RPT',
            'WNS', 'WNF', 'WNT', 'WPS', 'WPF', 'WPT', 'DNS', 'DNF', 'DNT',
            'DPS', 'DPF', 'DPT'
        ])

    ########################################
    # Create Product Parser object
    ########################################

    settings['g_drive_params'] = {
        'scopes': settings.gdrive_scopes,
        'client_secret_file': settings.gdrive_client_secret_file,
        'app_name': settings.gdrive_app_name,
        'oauth_client_id': settings.gdrive_oauth_client_id,
        'oauth_client_secret': settings.gdrive_oauth_client_secret,
        'credentials_dir': settings.gdrive_credentials_dir,
        'credentials_file': settings.gdrive_credentials_file,
        'gen_fid': settings.gen_fid,
    }

    if not settings['download_master']:
        settings['g_drive_params']['skip_download'] = True

    settings['wc_api_params'] = {
        'api_key': settings.wc_api_key,
        'api_secret': settings.wc_api_secret,
        'url': settings.store_url,
        'timeout': settings.slave_timeout,
        'offset': settings.slave_offset,
        'limit': settings.slave_limit
    }

    settings['api_product_parser_args'] = {
        'import_name': settings.import_name,
        'item_depth': settings.item_depth,
        'taxo_depth': settings.taxo_depth,
        'cols': ColDataWoo.get_import_cols(),
        'defaults': ColDataWoo.get_defaults(),
    }

    settings.product_parser_args = {
        'import_name': settings.import_name,
        'item_depth': settings.item_depth,
        'taxo_depth': settings.taxo_depth,
    }

    parsers = populate_master_parsers(settings)

    for category_name, category_list in parsers.product.categories_name.items():
        if len(category_list) < 2:
            continue
        if SeqUtils.check_equal(
                [category.namesum for category in category_list]):
            continue
        print "bad category: %50s | %d | %s" % (
            category_name[:50], len(category_list), str(category_list))

    check_warnings()

    #########################################
    # Images
    #########################################

    if settings.do_images and settings.schema_is_woo:
        process_images(settings, parsers)

    #########################################
    # Export Info to Spreadsheets
    #########################################

    export_parsers(settings, parsers)

    #########################################
    # Attempt download API data
    #########################################

    if settings['download_slave']:

        api_product_parser = CsvParseWooApi(
            **settings['api_product_parser_args'])

        with ProdSyncClientWC(settings['wc_api_params']) as client:
            # try:
            if settings['do_categories']:
                client.analyse_remote_categories(api_product_parser)

            Registrar.register_progress("analysing WC API data")

            client.analyse_remote(
                api_product_parser, limit=settings['download_limit'])

        # print api_product_parser.categories
    else:
        api_product_parser = None

    #########################################
    # Attempt Matching
    #########################################

    Registrar.register_progress("Attempting matching")

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
        """Return the codesum of the product."""
        return product.codesum

    global_product_matches = MatchList(index_fn=product_index_fn)
    masterless_product_matches = MatchList(index_fn=product_index_fn)
    slaveless_product_matches = MatchList(index_fn=product_index_fn)
    global_variation_matches = MatchList(index_fn=product_index_fn)
    masterless_variation_matches = MatchList(index_fn=product_index_fn)
    slaveless_variation_matches = MatchList(index_fn=product_index_fn)

    def category_index_fn(category):
        """Return the title of the category."""
        return category.title

    # category_index_fn = (lambda x: x.title)
    global_category_matches = MatchList(index_fn=category_index_fn)
    masterless_category_matches = MatchList(index_fn=category_index_fn)
    slaveless_category_matches = MatchList(index_fn=category_index_fn)
    delete_categories = OrderedDict()
    join_categories = OrderedDict()

    if settings['do_sync']:  # pylint: disable=too-many-nested-blocks
        # TODO: fix too-many-nested-blocks
        if settings['do_categories']:
            if Registrar.DEBUG_CATS:
                Registrar.register_message(
                    "matching %d master categories with %d slave categories" %
                    (len(parsers.product.categories),
                     len(api_product_parser.categories)))

            category_matcher = CategoryMatcher()
            category_matcher.clear()
            category_matcher.process_registers(api_product_parser.categories,
                                               parsers.product.categories)

            if Registrar.DEBUG_CATS:
                if category_matcher.pure_matches:
                    Registrar.register_message("All Category matches:\n%s" % (
                        '\n'.join(map(str, category_matcher.matches))))

            valid_category_matches = []
            valid_category_matches += category_matcher.pure_matches

            if category_matcher.duplicate_matches:

                invalid_category_matches = []
                for match in category_matcher.duplicate_matches:
                    master_taxo_sums = [cat.namesum for cat in match.m_objects]
                    if all(master_taxo_sums) \
                            and SeqUtils.check_equal(master_taxo_sums) \
                            and not len(match.s_objects) > 1:
                        valid_category_matches.append(match)
                    else:
                        invalid_category_matches.append(match)
                if invalid_category_matches:
                    exc = UserWarning(
                        "categories couldn't be synchronized because of ambiguous names:\n%s"
                        % '\n'.join(map(str, invalid_category_matches)))
                    Registrar.register_error(exc)
                    raise exc

            if category_matcher.slaveless_matches and category_matcher.masterless_matches:
                exc = UserWarning(
                    "You may want to fix up the following categories before syncing:\n%s\n%s"
                    %
                    ('\n'.join(map(str, category_matcher.slaveless_matches)),
                     '\n'.join(map(str, category_matcher.masterless_matches))))
                Registrar.register_error(exc)
                # raise exc

            global_category_matches.add_matches(category_matcher.pure_matches)
            masterless_category_matches.add_matches(
                category_matcher.masterless_matches)
            slaveless_category_matches.add_matches(
                category_matcher.slaveless_matches)

            sync_cols = ColDataWoo.get_wpapi_category_cols()

            # print "SYNC COLS: %s" % pformat(sync_cols.items())

            for match in enumerate(valid_category_matches):
                s_object = match.s_object
                for m_object in match.m_objects:
                    # m_object = match.m_objects[0]

                    sync_update = SyncUpdateCatWoo(m_object, s_object)

                    sync_update.update(sync_cols)

                    # print sync_update.tabulate()

                    if not sync_update.important_static:
                        insort(problematic_category_updates, sync_update)
                        continue

                    if sync_update.m_updated:
                        master_category_updates.append(sync_update)

                    if sync_update.s_updated:
                        slave_category_updates.append(sync_update)

            for update in master_category_updates:
                if Registrar.DEBUG_UPDATE:
                    Registrar.register_message(
                        "performing update < %5s | %5s > = \n%100s, %100s " %
                        (update.master_id, update.slave_id,
                         str(update.old_m_object), str(update.old_s_object)))
                if not update.master_id in parsers.product.categories:
                    exc = UserWarning(
                        "couldn't fine pkey %s in parsers.product.categories" %
                        update.master_id)
                    Registrar.register_error(exc)
                    continue
                for col, warnings in update.sync_warnings.items():
                    if not col == 'ID':
                        continue
                    for warning in warnings:
                        if not warning['subject'] == update.opposite_src(
                                update.master_name):
                            continue

                        new_val = warning['oldWinnerValue']
                        parsers.product.categories[update.master_id][
                            col] = new_val

            if Registrar.DEBUG_CATS:
                Registrar.register_message("NEW CATEGORIES: %d" %
                                           (len(slaveless_category_matches)))

            if settings['auto_create_new']:
                # create categories that do not yet exist on slave

                if Registrar.DEBUG_CATS:
                    Registrar.DEBUG_API = True

                with CatSyncClientWC(settings['wc_api_params']) as client:
                    if Registrar.DEBUG_CATS:
                        Registrar.register_message("created cat client")
                    new_categories = [
                        match.m_object for match in slaveless_category_matches
                    ]
                    if Registrar.DEBUG_CATS:
                        Registrar.register_message("new categories %s" %
                                                   new_categories)

                    while new_categories:
                        category = new_categories.pop(0)
                        if category.parent:
                            parent = category.parent
                            if not parent.isRoot and not parent.wpid and parent in new_categories:
                                new_categories.append(category)
                                continue

                        m_api_data = category.to_api_data(
                            ColDataWoo, 'wp-api')
                        for key in ['id', 'slug', 'sku']:
                            if key in m_api_data:
                                del m_api_data[key]
                        m_api_data['name'] = category.woo_cat_name
                        # print "uploading category: %s" % m_api_data
                        # pprint(m_api_data)
                        if settings['update_slave']:
                            response = client.create_item(m_api_data)
                            # print response
                            # print response.json()
                            response_api_data = response.json()
                            response_api_data = response_api_data.get(
                                'product_category', response_api_data)
                            api_product_parser.process_api_category(
                                response_api_data)
                            api_cat_translation = OrderedDict()
                            for key, data in ColDataWoo.get_wpapi_category_cols(
                            ).items():
                                try:
                                    wp_api_key = data['wp-api']['key']
                                except (IndexError, TypeError):
                                    wp_api_key = key
                                api_cat_translation[wp_api_key] = key
                            # print "TRANSLATION: ", api_cat_translation
                            category_parser_data = api_product_parser.translate_keys(
                                response_api_data, api_cat_translation)
                            if Registrar.DEBUG_CATS:
                                Registrar.register_message(
                                    "category being updated with parser data: %s"
                                    % category_parser_data)
                            category.update(category_parser_data)

                            # print "CATEGORY: ", category
            elif slaveless_category_matches:
                for slaveless_category_match in slaveless_category_matches:
                    exc = UserWarning("category needs to be created: %s" %
                                      slaveless_category_match.m_objects[0])
                    Registrar.register_warning(exc)

        # print parsers.product.to_str_tree()
        if Registrar.DEBUG_CATS:
            print "product parser"
            for key, category in parsers.product.categories.items():
                print "%5s | %50s | %s" % (key, category.title[:50],
                                           category.wpid)
        if Registrar.DEBUG_CATS:
            print "api product parser info"
            print "there are %s slave categories registered" % len(
                api_product_parser.categories)
            print "there are %s children of API root" % len(
                api_product_parser.root_data.children)
            print api_product_parser.to_str_tree()
            for key, category in api_product_parser.categories.items():
                print "%5s | %50s" % (key, category.title[:50])

        product_matcher = ProductMatcher()
        product_matcher.process_registers(api_product_parser.products,
                                          parsers.product.products)
        # print product_matcher.__repr__()

        global_product_matches.add_matches(product_matcher.pure_matches)
        masterless_product_matches.add_matches(
            product_matcher.masterless_matches)
        slaveless_product_matches.add_matches(
            product_matcher.slaveless_matches)

        sync_cols = ColDataWoo.get_wpapi_cols()
        if Registrar.DEBUG_UPDATE:
            Registrar.register_message("sync_cols: %s" % repr(sync_cols))

        for col in settings['exclude_cols']:
            if col in sync_cols:
                del sync_cols[col]

        if product_matcher.duplicate_matches:
            exc = UserWarning(
                "products couldn't be synchronized because of ambiguous SKUs:%s"
                % '\n'.join(map(str, product_matcher.duplicate_matches)))
            Registrar.register_error(exc)
            raise exc

        for _, prod_match in enumerate(product_matcher.pure_matches):
            if Registrar.DEBUG_CATS or Registrar.DEBUG_VARS:
                Registrar.register_message("processing prod_match: %s" %
                                           prod_match.tabulate())
            m_object = prod_match.m_object
            s_object = prod_match.s_object

            sync_update = SyncUpdateProdWoo(m_object, s_object)

            # , "gcs %s is not variation but object is" % repr(gcs)
            assert not m_object.isVariation
            # , "gcs %s is not variation but object is" % repr(gcs)
            assert not s_object.isVariation
            sync_update.update(sync_cols)

            # print sync_update.tabulate()

            if settings['do_categories']:
                category_matcher.clear()
                category_matcher.process_registers(s_object.categories,
                                                   m_object.categories)

                update_params = {
                    'col': 'catlist',
                    'data': {
                        # 'sync'
                    },
                    'subject': sync_update.master_name
                }

                change_match_list = category_matcher.masterless_matches
                change_match_list.add_matches(
                    category_matcher.slaveless_matches)

                master_categories = set([
                    master_category.wpid
                    for master_category in m_object.categories.values()
                    if master_category.wpid
                ])
                slave_categories = set([
                    slave_category.wpid
                    for slave_category in s_object.categories.values()
                    if slave_category.wpid
                ])

                if Registrar.DEBUG_CATS:
                    Registrar.register_message(
                        "comparing categories of %s:\n%s\n%s\n%s\n%s" %
                        (m_object.codesum, str(m_object.categories.values()),
                         str(s_object.categories.values()),
                         str(master_categories), str(slave_categories), ))

                sync_update.old_m_object['catlist'] = list(master_categories)
                sync_update.old_s_object['catlist'] = list(slave_categories)

                if change_match_list:
                    assert \
                        master_categories != slave_categories, \
                        ("if change_match_list exists, then master_categories "
                         "should not equal slave_categories.\nchange_match_list: \n%s") % \
                        "\n".join(map(pformat, change_match_list))
                    update_params['reason'] = 'updating'
                    # update_params['subject'] = SyncUpdate.master_name

                    # master_categories = [category.woo_cat_name for category \
                    #                      in change_match_list.merge().m_objects]
                    # slave_categories =  [category.woo_cat_name for category \
                    # in change_match_list.merge().s_objects]

                    sync_update.loser_update(**update_params)
                    # sync_update.new_m_object['catlist'] = master_categories
                    # sync_update.new_s_object['catlist'] = master_categories

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
                    sync_update.tie_update(**update_params)

                if Registrar.DEBUG_CATS:
                    Registrar.register_message(
                        "category matches for update:\n%s" % (
                            category_matcher.__repr__()))

                for cat_match in category_matcher.masterless_matches:
                    s_index = s_object.index
                    if delete_categories.get(s_index) is None:
                        delete_categories[s_index] = MatchList()
                    delete_categories[s_index].append(cat_match)
                for cat_match in category_matcher.slaveless_matches:
                    s_index = s_object.index
                    if join_categories.get(s_index) is None:
                        join_categories[s_index] = MatchList()
                    join_categories[s_index].append(cat_match)

            # Assumes that GDrive is read only, doesn't care about master
            # updates
            if not sync_update.s_updated:
                continue

            if Registrar.DEBUG_UPDATE:
                Registrar.register_message("sync updates:\n%s" %
                                           sync_update.tabulate())

            if sync_update.s_updated and sync_update.s_deltas:
                insort(s_delta_updates, sync_update)

            if not sync_update.important_static:
                insort(problematic_product_updates, sync_update)
                continue

            if sync_update.s_updated:
                insort(slave_product_updates, sync_update)

        if settings['do_variations']:

            variation_matcher = VariationMatcher()
            variation_matcher.process_registers(api_product_parser.variations,
                                                parsers.product.variations)

            if Registrar.DEBUG_VARS:
                Registrar.register_message("variation matcher:\n%s" %
                                           variation_matcher.__repr__())

            global_variation_matches.add_matches(
                variation_matcher.pure_matches)
            masterless_variation_matches.add_matches(
                variation_matcher.masterless_matches)
            slaveless_variation_matches.add_matches(
                variation_matcher.slaveless_matches)

            var_sync_cols = ColDataWoo.get_wpapi_variable_cols()
            if Registrar.DEBUG_UPDATE:
                Registrar.register_message("var_sync_cols: %s" %
                                           repr(var_sync_cols))

            if variation_matcher.duplicate_matches:
                exc = UserWarning(
                    "variations couldn't be synchronized because of ambiguous SKUs:%s"
                    % '\n'.join(map(str, variation_matcher.duplicate_matches)))
                Registrar.register_error(exc)
                raise exc

            for var_match_count, var_match in enumerate(
                    variation_matcher.pure_matches):
                # print "processing var_match: %s" % var_match.tabulate()
                m_object = var_match.m_object
                s_object = var_match.s_object

                sync_update = SyncUpdateVarWoo(m_object, s_object)

                sync_update.update(var_sync_cols)

                # Assumes that GDrive is read only, doesn't care about master
                # updates
                if not sync_update.s_updated:
                    continue

                if Registrar.DEBUG_VARS:
                    Registrar.register_message("var update %d:\n%s" % (
                        var_match_count, sync_update.tabulate()))

                if not sync_update.important_static:
                    insort(problematic_variation_updates, sync_update)
                    continue

                if sync_update.s_updated:
                    insort(slave_variation_updates, sync_update)

            for var_match_count, var_match in enumerate(
                    variation_matcher.slaveless_matches):
                assert var_match.has_no_slave
                m_object = var_match.m_object

                # sync_update = SyncUpdateVarWoo(m_object, None)

                # sync_update.update(var_sync_cols)

                if Registrar.DEBUG_VARS:
                    Registrar.register_message("var create %d:\n%s" % (
                        var_match_count, m_object.identifier))

                # TODO: figure out which attribute terms to add

            for var_match_count, var_match in enumerate(
                    variation_matcher.masterless_matches):
                assert var_match.has_no_master
                s_object = var_match.s_object

                # sync_update = SyncUpdateVarWoo(None, s_object)

                # sync_update.update(var_sync_cols)

                if Registrar.DEBUG_VARS:
                    Registrar.register_message("var delete: %d:\n%s" % (
                        var_match_count, s_object.identifier))

                # TODO: figure out which attribute terms to delete

        if settings['auto_create_new']:
            for new_prod_count, new_prod_match in enumerate(
                    product_matcher.slaveless_matches):
                m_object = new_prod_match.m_object
                print "will create product %d: %s" % (new_prod_count,
                                                      m_object.identifier)
                api_data = m_object.to_api_data(ColDataWoo, 'wp-api')
                for key in ['id', 'slug']:
                    if key in api_data:
                        del api_data[key]
                print "has api data: %s" % pformat(api_data)
                slave_product_creations.append(api_data)

    check_warnings()

    # except Exception, exc:
    #     Registrar.register_error(repr(exc))
    #     settings.report_and_quit = True

    #########################################
    # Write Report
    #########################################

    Registrar.register_progress("Write Report")

    with io.open(settings.rep_path_full, 'w+', encoding='utf8') as res_file:
        reporter = HtmlReporter()

        # basic_cols = ColDataWoo.get_basic_cols()
        # csv_colnames = ColDataWoo.get_col_names(
        #     OrderedDict(basic_cols.items() + ColDataWoo.name_cols([
        #         # 'address_reason',
        #         # 'name_reason',
        #         # 'Edited Name',
        #         # 'Edited Address',
        #         # 'Edited Alt Address',
        #     ]).items()))

        # print repr(basic_colnames)
        # unicode_colnames = map(SanitationUtils.coerce_unicode, csv_colnames.values())
        # print repr(unicode_colnames)

        if settings['do_sync'] and (s_delta_updates):

            delta_group = HtmlReporter.Group('deltas', 'Field Changes')

            s_delta_list = ShopObjList(
                [
                    delta_sync_update.new_s_object
                    for delta_sync_update in s_delta_updates
                    if delta_sync_update.new_s_object
                ]
            )

            delta_cols = ColDataWoo.get_delta_cols()

            all_delta_cols = OrderedDict(
                ColDataWoo.get_basic_cols().items() + ColDataWoo.name_cols(
                    delta_cols.keys() + delta_cols.values()).items())

            if s_delta_list:
                delta_group.add_section(
                    HtmlReporter.Section(
                        's_deltas',
                        title='%s Changes List' % settings.slave_name.title(),
                        description='%s records that have changed important fields'
                        % settings.slave_name,
                        data=s_delta_list.tabulate(
                            cols=all_delta_cols, tablefmt='html'),
                        length=len(s_delta_list)))

            reporter.add_group(delta_group)

            if s_delta_list:
                s_delta_list.export_items(
                    settings['slave_delta_csv_path'],
                    ColDataWoo.get_col_names(all_delta_cols))

        #
        report_matching = settings['do_sync']
        if report_matching:

            matching_group = HtmlReporter.Group('product_matching',
                                                'Product Matching Results')
            if global_product_matches:
                matching_group.add_section(
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
                matching_group.add_section(
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
                matching_group.add_section(
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
                reporter.add_group(matching_group)

            if settings['do_categories']:
                matching_group = HtmlReporter.Group(
                    'category_matching', 'Category Matching Results')
                if global_category_matches:
                    matching_group.add_section(
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
                    matching_group.add_section(
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
                    matching_group.add_section(
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
                    reporter.add_group(matching_group)

            if settings['do_variations']:
                matching_group = HtmlReporter.Group(
                    'variation_matching', 'Variation Matching Results')
                if global_variation_matches:
                    matching_group.add_section(
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
                    matching_group.add_section(
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
                    matching_group.add_section(
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
                    reporter.add_group(matching_group)

        report_sync = settings['do_sync']
        if report_sync:
            syncing_group = HtmlReporter.Group('prod_sync',
                                               'Product Syncing Results')

            syncing_group.add_section(
                HtmlReporter.Section(
                    (SanitationUtils.make_safe_class(settings.slave_name) +
                     "_product_updates"),
                    description=settings.slave_name + " items will be updated",
                    data='<hr>'.join([
                        update.tabulate(tablefmt="html")
                        for update in slave_product_updates
                    ]),
                    length=len(slave_product_updates)))

            syncing_group.add_section(
                HtmlReporter.Section(
                    "problematic_product_updates",
                    description="items can't be merged because they are too dissimilar",
                    data='<hr>'.join([
                        update.tabulate(tablefmt="html")
                        for update in problematic_product_updates
                    ]),
                    length=len(problematic_product_updates)))

            reporter.add_group(syncing_group)

            if settings['do_variations']:
                syncing_group = HtmlReporter.Group('variation_sync',
                                                   'Variation Syncing Results')

                syncing_group.add_section(
                    HtmlReporter.Section(
                        (SanitationUtils.make_safe_class(settings.slave_name) +
                         "_variation_updates"),
                        description=settings.slave_name +
                        " items will be updated",
                        data='<hr>'.join([
                            update.tabulate(tablefmt="html")
                            for update in slave_variation_updates
                        ]),
                        length=len(slave_variation_updates)))

                syncing_group.add_section(
                    HtmlReporter.Section(
                        "problematic_variation_updates",
                        description="items can't be merged because they are too dissimilar",
                        data='<hr>'.join([
                            update.tabulate(tablefmt="html")
                            for update in problematic_variation_updates
                        ]),
                        length=len(problematic_variation_updates)))

                reporter.add_group(syncing_group)

        report_cats = settings['do_sync'] and settings['do_categories']
        if report_cats:
            # "reporting cats. settings['do_sync']: %s, do_categories: %s" % (
            #     repr(settings['do_sync']), repr(settings['do_categories']))
            syncing_group = HtmlReporter.Group('cats',
                                               'Category Syncing Results')

            syncing_group.add_section(
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
                                # ", ".join(category.woo_cat_name \
                                # for category in matches.merge().m_objects),
                                ", ".join(category.woo_cat_name
                                          for category in matches.merge()
                                          .s_objects)
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
                        ", ".join(category.woo_cat_name for category in matches.merge().s_objects\
                                  if not re.search('Specials', category.woo_cat_name))
                    ] for index, matches in delete_categories.items()
                ],
                tablefmt="html"
            )

            syncing_group.add_section(
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

            syncing_group.add_section(
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
                                ", ".join(category.woo_cat_name
                                          for category in matches.merge()
                                          .m_objects),
                                # ", ".join(category.woo_cat_name \
                                # for category in matches.merge().s_objects)
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

            reporter.add_group(syncing_group)

        if not reporter.groups:
            empty_group = HtmlReporter.Group('empty', 'Nothing to report')
            # empty_group.add_section(
            #     HtmlReporter.Section(
            #         ('empty'),
            #         data = ''
            #
            #     )
            # )
            Registrar.register_message('nothing to report')
            reporter.add_group(empty_group)

        res_file.write(reporter.get_document_unicode())

    if settings.report_and_quit:
        sys.exit(ExitStatus.success)

    check_warnings()

    #########################################
    # Perform updates
    #########################################

    all_product_updates = slave_product_updates
    if settings['do_variations']:
        all_product_updates += slave_variation_updates
    if settings.do_problematic:
        all_product_updates += problematic_product_updates
        if settings['do_variations']:
            all_product_updates += problematic_variation_updates

    # don't perform updates if limit was set
    if settings['download_limit']:
        all_product_updates = []

    slave_failures = []
    if all_product_updates:
        Registrar.register_progress("UPDATING %d RECORDS" %
                                    len(all_product_updates))

        if settings['ask_before_update']:
            input(
                "Please read reports and press Enter to continue or ctrl-c to stop..."
            )

        if Registrar.DEBUG_PROGRESS:
            update_progress_counter = ProgressCounter(len(all_product_updates))

        with ProdSyncClientWC(settings['wc_api_params']) as slave_client:
            for count, update in enumerate(all_product_updates):
                if Registrar.DEBUG_PROGRESS:
                    update_progress_counter.maybe_print_update(count)

                if settings['update_slave'] and update.s_updated:
                    # print "attempting update to %s " % str(update)

                    try:
                        update.update_slave(slave_client)
                    except Exception as exc:
                        # slave_failures.append({
                        #     'update':update,
                        #     'master':SanitationUtils.coerce_unicode(update.new_m_object),
                        #     'slave':SanitationUtils.coerce_unicode(update.new_s_object),
                            # 'mchanges':SanitationUtils.coerce_unicode(
                            #         update.get_master_updates()
                            # ),
                        #     'schanges':SanitationUtils.coerce_unicode(update.get_slave_updates()),
                        #     'exception':repr(exc)
                        # })
                        SanitationUtils.safe_print(
                            "ERROR UPDATING SLAVE (%s): %s" %
                            (update.slave_id, repr(exc)))
                        slave_failures.append(update)
                # else:
                #     print "no update made to %s " % str(update)

                #########################################
                # Display reports
                #########################################

    Registrar.register_progress("Displaying reports")

    if settings.show_report:
        if settings['rep_web_path']:
            shutil.copyfile(settings.rep_path_full, settings['rep_web_path'])
            if settings['web_browser']:
                os.environ['BROWSER'] = settings['web_browser']
                # print "set browser environ to %s" % repr(web_browser)
            # print "moved file from %s to %s" % (settings.rep_path_full, repWebPath)

            webbrowser.open(settings['rep_web_link'])
    else:
        print "open this link to view report %s" % settings['rep_web_link']


def catch_main(override_args=[]):  # pylint: disable=too-many-statements,too-many-branches
    # TODO: fix too-many-statements,too-many-branches
    """Run the main function within a try statement and attempt to analyse failure."""

    file_path = __file__
    cur_dir = os.getcwd() + '/'
    if file_path.startswith(cur_dir):
        file_path = file_path[len(cur_dir):]

    full_run_str = "%s %s %s" % (str(sys.executable), str(file_path), ' '.join(override_args))

    settings = SettingsNamespaceProd()

    status = 0
    try:
        main(settings=settings, override_args=override_args)
    except SystemExit:
        exit()
    except (ReadTimeout, ConnectionError, ConnectTimeout, ServerNotFoundError):
        status = 69  # service unavailable
    except IOError:
        status = 74
        print "cwd: %s" % os.getcwd()
    except UserWarning:
        status = 65
    except SystemExit:
        status = ExitStatus.failure
    except:
        status = 1
    finally:
        if status:
            Registrar.register_error(traceback.format_exc())


    with io.open(settings.log_path_full, 'w+', encoding='utf8') as log_file:
        for source, messages in Registrar.get_message_items(1).items():
            print source
            log_file.writelines([SanitationUtils.coerce_unicode(source)])
            log_file.writelines([
                SanitationUtils.coerce_unicode(message) for message in messages
            ])
            for message in messages:
                pprint(message, indent=4, width=80, depth=2)

    #########################################
    # zip reports
    #########################################

    files_to_zip = [
        settings.m_fail_path_full, settings.s_fail_path_full, settings.rep_path_full
    ]

    with zipfile.ZipFile(settings.zip_path_full, 'w') as zip_file:
        for file_to_zip in files_to_zip:
            try:
                os.stat(file_to_zip)
                zip_file.write(file_to_zip)
            except:
                pass
        Registrar.register_message('wrote file %s' % zip_file.filename)

    # print "\nexiting with status %s \n" % status
    if status:
        print "re-run with: \n%s" % full_run_str
    else:
        Registrar.register_message("re-run with:\n%s" % full_run_str)

    sys.exit(status)


if __name__ == '__main__':
    catch_main()
