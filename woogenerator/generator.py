"""Module for generating woocommerce csv import files from Google Drive Data."""
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
from bisect import insort
from collections import OrderedDict
from pprint import pformat, pprint

from exitstatus import ExitStatus
from httplib2 import ServerNotFoundError
from PIL import Image
from requests.exceptions import ConnectionError, ConnectTimeout, ReadTimeout
from tabulate import tabulate

from woogenerator.client.prod import CatSyncClientWC
from woogenerator.coldata import ColDataBase, ColDataWoo
from woogenerator.conf.namespace import (MatchNamespace, ParserNamespace,
                                         SettingsNamespaceProd,
                                         UpdateNamespace, init_settings)
from woogenerator.conf.parser import ArgumentParserProd
from woogenerator.matching import (CategoryMatcher, MatchList, ProductMatcher,
                                   VariationMatcher)
from woogenerator.metagator import MetaGator
from woogenerator.parsing.api import CsvParseWooApi
from woogenerator.parsing.dyn import CsvParseDyn
from woogenerator.parsing.myo import MYOProdList
from woogenerator.parsing.shop import ShopObjList
from woogenerator.parsing.special import CsvParseSpecial
from woogenerator.parsing.woo import (CsvParseWoo, WooCatList, WooProdList,
                                      WooVarList)
from woogenerator.syncupdate import (SyncUpdate, SyncUpdateCatWoo,
                                     SyncUpdateProdWoo, SyncUpdateVarWoo)
from woogenerator.utils import (HtmlReporter, ProgressCounter, Registrar,
                                SanitationUtils, SeqUtils, TimeUtils)


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

def populate_master_parsers(parsers, settings):
    """Create and populates the various parsers."""
    things_to_check = [
        'master_parser_args'
    ]
    if settings['download_master']:
        things_to_check.extend(['g_drive_params'])

    for thing in things_to_check:
        Registrar.register_message(
            "%s: %s" % (thing, getattr(settings, thing))
        )
        assert getattr(settings, thing), "settings must specify %s" % thing

    parsers.dyn = CsvParseDyn()
    parsers.special = CsvParseSpecial()

    if Registrar.DEBUG_GEN:
        Registrar.register_message("master_download_client_args: %s" % settings.master_download_client_args)

    with settings.master_download_client_class(**settings.master_download_client_args) as client:
        if settings.schema_is_woo:
            if settings.do_dyns:
                Registrar.register_message("analysing dprc rules")
                client.analyse_remote(
                    parsers.dyn,
                    data_path=settings.dprc_path,
                    gid=settings.dprc_gid
                )
                settings.master_parser_args['dprc_rules'] = parsers.dyn.taxos

                Registrar.register_message("analysing dprp rules")
                parsers.dyn.clear_transients()
                client.analyse_remote(
                    parsers.dyn,
                    data_path=settings.dprp_path,
                    gid=settings.dprp_gid
                )
                settings.master_parser_args['dprp_rules'] = parsers.dyn.taxos

            if settings.do_specials:
                Registrar.register_message("analysing specials")
                client.analyse_remote(
                    parsers.special,
                    data_path=settings.specials_path,
                    gid=settings.spec_gid
                )
                if Registrar.DEBUG_SPECIAL:
                    Registrar.register_message(
                        "all specials: %s" % parsers.special.tabulate()
                    )

                settings.special_rules = parsers.special.rules

                settings.current_special_groups = parsers.special.determine_current_spec_grps(
                    specials_mode=settings.specials_mode,
                    current_special=settings.current_special
                )
                if Registrar.DEBUG_SPECIAL:
                    Registrar.register_message(
                        "current_special_groups: %s" % settings.current_special_groups
                    )

        parsers.master = settings.master_parser_class(**settings.master_parser_args)

        Registrar.register_progress("analysing master product data")

        analysis_kwargs = {
            'data_path':settings.master_path,
            'gid':settings.gen_gid,
            'limit':settings['master_parse_limit']
        }
        if Registrar.DEBUG_PARSER:
            Registrar.register_message("analysis_kwargs: %s" % analysis_kwargs)

        client.analyse_remote(parsers.master, **analysis_kwargs)

        if Registrar.DEBUG_PARSER and hasattr(parsers.master, 'categories_name'):
            for category_name, category_list in getattr(parsers.master, 'categories_name').items():
                if len(category_list) < 2:
                    continue
                if SeqUtils.check_equal(
                        [category.namesum for category in category_list]):
                    continue
                Registrar.register_warning("bad category: %50s | %d | %s" % (
                    category_name[:50], len(category_list), str(category_list)
                ))

        return parsers


def process_images(settings, parsers):
    """Process the images information in from the parsers."""
    Registrar.register_progress("processing images")

    if Registrar.DEBUG_IMG:
        Registrar.register_message("Looking in dirs: %s" %
                                   settings.img_raw_dirs)

    def invalid_image(img_name, error):
        """Register error globally and attribute to image."""
        if settings.require_images:
            Registrar.register_error(error, img_name)
        else:
            Registrar.register_message(error, img_name)
        parsers.master.images[img_name].invalidate(error)

    ls_raw = {}
    for dir in settings.img_raw_dirs:
        if dir:
            ls_raw[dir] = os.listdir(dir)

    def get_raw_image(img_name):
        """
        Find the path of the image in the raw image dirs.

        Args:
            img_name (str):
                the name of the file to search for

        Returns:
            The path of the image within the raw image dirs

        Raises:
            IOError: file could not be found
        """
        for path in settings.img_raw_dirs:
            if path and img_name in ls_raw[path]:
                return os.path.join(path, img_name)
        raise IOError("no image named %s found" % str(img_name))

    if not os.path.exists(settings.img_dst):
        os.makedirs(settings.img_dst)

    # list of images in compressed directory
    ls_cmp = os.listdir(settings.img_dst)
    for fname in ls_cmp:
        if fname not in parsers.master.images.keys():
            Registrar.register_warning("DELETING FROM REFLATTENED", fname)
            if settings.do_delete_images:
                os.remove(os.path.join(settings.img_dst, fname))

    for img, data in parsers.master.images.items():
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
                        Registrar.register_message(
                            "new dest img meta: %s" % imgmeta.read_meta(),
                            img
                        )

            except IOError as exc:
                invalid_image(img, "could not resize: " + str(exc))
                continue

    # # ------
    # # RSYNC
    # # ------
    #
    # if not os.path.exists(wpai_dir):
    #     os.makedirs(wpai_dir)
    #
    # rsync.main([os.path.join(img_dst,'*'), wpai_dir])

def export_parsers(settings, parsers):
    """Export key information from the parsers to spreadsheets."""
    Registrar.register_progress("Exporting info to spreadsheets")

    product_cols = settings.col_data_class.get_product_cols()

    if settings.schema_is_myo:
        product_list = MYOProdList(parsers.master.products.values())
        product_list.export_items(settings.myo_path,
                                  ColDataBase.get_col_names(product_cols))
    elif settings.schema_is_woo:
        for col in settings['exclude_cols']:
            if col in product_cols:
                del product_cols[col]

        attribute_cols = ColDataWoo.get_attribute_cols(
            parsers.master.attributes, parsers.master.vattributes)
        product_colnames = ColDataBase.get_col_names(
            SeqUtils.combine_ordered_dicts(product_cols, attribute_cols))

        product_list = WooProdList(parsers.master.products.values())
        product_list.export_items(settings.fla_path, product_colnames)

        # variations

        variation_cols = ColDataWoo.get_variation_cols()

        attribute_meta_cols = ColDataWoo.get_attribute_meta_cols(
            parsers.master.vattributes)
        variation_col_names = ColDataBase.get_col_names(
            SeqUtils.combine_ordered_dicts(variation_cols, attribute_meta_cols))

        if parsers.master.variations:
            variation_list = WooVarList(parsers.master.variations.values())
            variation_list.export_items(settings.flv_path, variation_col_names)

        if parsers.master.categories:
            # categories
            category_cols = ColDataWoo.get_category_cols()

            category_list = WooCatList(parsers.master.categories.values())
            category_list.export_items(settings.cat_path,
                                       ColDataBase.get_col_names(category_cols))

        # specials
        if settings.do_specials:
            current_special = getattr(settings, 'current_special', None)
            if settings.current_special_groups:
                current_special = settings.current_special_groups[0].special_id
            # print "current special is %s" % current_special
            if current_special:
                special_products = parsers.master.onspecial_products.values()
                if special_products:
                    fla_name, fla_ext = os.path.splitext(settings.fla_path)
                    fls_path = os.path.join(
                        settings.out_dir_full,
                        fla_name + "-" + current_special + fla_ext)
                    special_product_list = WooProdList(special_products)
                    special_product_list.export_items(fls_path,
                                                      product_colnames)
                special_variations = parsers.master.onspecial_variations.values()
                if special_variations:
                    flv_name, flv_ext = os.path.splitext(settings.flv_path)
                    flvs_path = os.path.join(
                        settings.out_dir_full,
                        flv_name + "-" + current_special + flv_ext)

                    sp_variation_list = WooVarList(special_variations)
                    sp_variation_list.export_items(flvs_path,
                                                   variation_col_names)

        updated_products = parsers.master.updated_products.values()
        if updated_products:
            fla_name, fla_ext = os.path.splitext(settings.fla_path)
            flu_path = os.path.join(settings.out_dir_full,
                                    fla_name + "-Updated" + fla_ext)

            updated_product_list = WooProdList(updated_products)
            updated_product_list.export_items(flu_path, product_colnames)

        updated_variations = parsers.master.updated_variations.values()

        if updated_variations:
            flv_name, flv_ext = os.path.splitext(settings.flv_path)
            flvu_path = os.path.join(settings.out_dir_full,
                                     flv_name + "-Updated" + flv_ext)

            updated_variations_list = WooVarList(updated_variations)
            updated_variations_list.export_items(
                flvu_path, variation_col_names)

def main(override_args=None, settings=None):
    """Main function for generator."""
    settings = init_settings(override_args, settings, ArgumentParserProd)

    # PROCESS CONFIG

    settings.dprc_path = os.path.join(settings.in_dir_full, 'DPRC.csv')
    settings.dprp_path = os.path.join(settings.in_dir_full, 'DPRP.csv')

    settings.add_special_categories = settings.do_specials and settings['do_categories']

    # TODO: set up logging here instead of Registrar verbosity crap

    if settings['auto_create_new']:
        exc = UserWarning("auto-create not fully implemented yet")
        Registrar.register_warning(exc)
    if settings.auto_delete_old:
        raise UserWarning("auto-delete not implemented yet")

    if settings.img_raw_dir is not None:
        settings.img_raw_dirs.append(settings.img_raw_dir)
    if settings.img_raw_extra_dir is not None:
        settings.img_raw_dirs.append(settings.img_raw_extra_dir)

    TimeUtils.set_wp_srv_offset(settings.wp_srv_offset)
    SyncUpdate.set_globals(settings.master_name, settings.slave_name,
                           settings.merge_mode, settings.last_sync)

    suffix = settings.schema
    if settings.variant:
        suffix += "-" + settings.variant

    settings.fla_path = os.path.join(settings.out_dir_full,
                                     "flattened-" + suffix + ".csv")
    settings.flv_path = os.path.join(settings.out_dir_full,
                                     "flattened-variations-" + suffix + ".csv")
    settings.cat_path = os.path.join(settings.out_dir_full,
                                     "categories-" + suffix + ".csv")
    settings.myo_path = os.path.join(settings.out_dir_full,
                                     "myob-" + suffix + ".csv")
    # bun_path = os.path.join(settings.out_dir_full , "bundles-"+suffix+".csv")
    rep_name = os.path.basename(settings.rep_main_path)
    if settings.get('web_dir'):
        settings['rep_web_path'] = os.path.join(
            settings.get('web_dir'),
            rep_name
        )
        settings['rep_web_link'] = urlparse.urljoin(
            settings.get('web_address'),
            rep_name
        )

    settings['rep_delta_slave_csv_path'] = os.path.join(
        settings.out_dir_full, "delta_report_wp%s.csv" % suffix)

    settings.img_dst = os.path.join(settings.img_cmp_dir,
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

    parsers = ParserNamespace()
    parsers = populate_master_parsers(parsers, settings)

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

        parsers.slave = CsvParseWooApi(
            **settings['api_product_parser_args'])

        slave_client_class = settings.slave_download_client_class
        slave_client_args = settings.slave_download_client_args

        # with ProdSyncClientWC(settings['slave_wp_api_params']) as client:
        with slave_client_class(**slave_client_args) as client:
            # try:
            if settings['do_categories']:
                client.analyse_remote_categories(parsers.slave)

            Registrar.register_progress("analysing WC API data")

            client.analyse_remote(
                parsers.slave, limit=settings['slave_parse_limit'])

        # print parsers.slave.categories
    else:
        parsers.slave = None

    #########################################
    # Attempt Matching
    #########################################

    Registrar.register_progress("Attempting matching")

    updates = UpdateNamespace()
    variation_updates = UpdateNamespace()
    category_updates = UpdateNamespace()

    def product_index_fn(product):
        """Return the codesum of the product."""
        return product.codesum

    matches = MatchNamespace(index_fn=product_index_fn)
    variation_matches = MatchNamespace(index_fn=product_index_fn)

    def category_index_fn(category):
        """Return the title of the category."""
        return category.title

    category_matches = MatchNamespace(index_fn=category_index_fn)
    category_matches.new_slave = OrderedDict()

    if settings['do_sync']:
        if settings['do_categories']:
            if Registrar.DEBUG_CATS:
                Registrar.register_message(
                    "matching %d master categories with %d slave categories" %
                    (len(parsers.master.categories),
                     len(parsers.slave.categories)))

            category_matcher = CategoryMatcher()
            category_matcher.clear()
            category_matcher.process_registers(parsers.slave.categories,
                                               parsers.master.categories)

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

            category_matches.globals.add_matches(category_matcher.pure_matches)
            category_matches.masterless.add_matches(
                category_matcher.masterless_matches)
            category_matches.slaveless.add_matches(
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
                        insort(category_updates.problematic, sync_update)
                        continue

                    if sync_update.m_updated:
                        category_updates.master.append(sync_update)

                    if sync_update.s_updated:
                        category_updates.slave.append(sync_update)

            for update in category_updates.master:
                if Registrar.DEBUG_UPDATE:
                    Registrar.register_message(
                        "performing update < %5s | %5s > = \n%100s, %100s " %
                        (update.master_id, update.slave_id,
                         str(update.old_m_object), str(update.old_s_object)))
                if not update.master_id in parsers.master.categories:
                    exc = UserWarning(
                        "couldn't fine pkey %s in parsers.master.categories" %
                        update.master_id)
                    Registrar.register_error(exc)
                    continue
                for col, warnings in update.sync_warnings.items():
                    if not col == 'ID':
                        continue
                    for warning in warnings:
                        if not warning['subject'] == update.master_name:
                            continue

                        new_val = warning['new_value']
                        parsers.master.categories[update.master_id][
                            col] = new_val

            if Registrar.DEBUG_CATS:
                Registrar.register_message("NEW CATEGORIES: %d" %
                                           (len(category_matches.slaveless)))

            if settings['auto_create_new']:
                # create categories that do not yet exist on slave

                if Registrar.DEBUG_CATS:
                    Registrar.DEBUG_API = True

                with CatSyncClientWC(settings['slave_wp_api_params']) as client:
                    if Registrar.DEBUG_CATS:
                        Registrar.register_message("created cat client")
                    new_categories = [
                        match.m_object for match in category_matches.slaveless
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
                            parsers.slave.process_api_category(
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
                            category_parser_data = parsers.slave.translate_keys(
                                response_api_data, api_cat_translation)
                            if Registrar.DEBUG_CATS:
                                Registrar.register_message(
                                    "category being updated with parser data: %s"
                                    % category_parser_data)
                            category.update(category_parser_data)

                            # print "CATEGORY: ", category
            elif category_matches.slaveless:
                for slaveless_category_match in category_matches.slaveless:
                    exc = UserWarning("category needs to be created: %s" %
                                      slaveless_category_match.m_objects[0])
                    Registrar.register_warning(exc)

        # print parsers.master.to_str_tree()
        # if Registrar.DEBUG_CATS:
        #     print "product parser"
        #     for key, category in parsers.master.categories.items():
        #         print "%5s | %50s | %s" % (key, category.title[:50],
        #                                    category.wpid)
        # if Registrar.DEBUG_CATS:
        #     print "api product parser info"
        #     print "there are %s slave categories registered" % len(
        #         parsers.slave.categories)
        #     print "there are %s children of API root" % len(
        #         parsers.slave.root_data.children)
        #     print parsers.slave.to_str_tree()
        #     for key, category in parsers.slave.categories.items():
        #         print "%5s | %50s" % (key, category.title[:50])

        product_matcher = ProductMatcher()
        product_matcher.process_registers(parsers.slave.products,
                                          parsers.master.products)
        # print product_matcher.__repr__()

        matches.globals.add_matches(product_matcher.pure_matches)
        matches.masterless.add_matches(
            product_matcher.masterless_matches)
        matches.slaveless.add_matches(
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
                    'subject': sync_update.slave_name
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
                    # update_params['subject'] = SyncUpdate.slave_name

                    # master_categories = [category.woo_cat_name for category \
                    #                      in change_match_list.merge().m_objects]
                    # slave_categories =  [category.woo_cat_name for category \
                    # in change_match_list.merge().s_objects]

                    sync_update.loser_update(**update_params)
                    # sync_update.new_m_object['catlist'] = master_categories
                    # sync_update.new_s_object['catlist'] = master_categories

                    # update_params['old_value'] = slave_categories
                    # update_params['new_value'] = master_categories
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
                    if category_matches.delete_slave.get(s_index) is None:
                        category_matches.delete_slave[s_index] = MatchList()
                    category_matches.delete_slave[s_index].append(cat_match)
                for cat_match in category_matcher.slaveless_matches:
                    s_index = s_object.index
                    if category_matches.new_slave.get(s_index) is None:
                        category_matches.new_slave[s_index] = MatchList()
                    category_matches.new_slave[s_index].append(cat_match)

            # Assumes that GDrive is read only, doesn't care about master
            # updates
            if not sync_update.s_updated:
                continue

            if Registrar.DEBUG_UPDATE:
                Registrar.register_message("sync updates:\n%s" %
                                           sync_update.tabulate())

            if sync_update.s_updated and sync_update.s_deltas:
                insort(updates.delta_slave, sync_update)

            if not sync_update.important_static:
                insort(updates.problematic, sync_update)
                continue

            if sync_update.s_updated:
                insort(updates.slave, sync_update)

        if settings['do_variations']:

            variation_matcher = VariationMatcher()
            variation_matcher.process_registers(parsers.slave.variations,
                                                parsers.master.variations)

            if Registrar.DEBUG_VARS:
                Registrar.register_message("variation matcher:\n%s" %
                                           variation_matcher.__repr__())

            variation_matches.globals.add_matches(
                variation_matcher.pure_matches)
            variation_matches.masterless.add_matches(
                variation_matcher.masterless_matches)
            variation_matches.slaveless.add_matches(
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
                    insort(variation_updates.problematic, sync_update)
                    continue

                if sync_update.s_updated:
                    insort(variation_updates.slave, sync_update)

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
                    product_matcher.slaveless_matches
            ):
                m_object = new_prod_match.m_object
                Registrar.register_message(
                    "will create product %d: %s" % (
                        new_prod_count, m_object.identifier
                    )
                )
                api_data = m_object.to_api_data(ColDataWoo, 'wp-api')
                for key in ['id', 'slug']:
                    if key in api_data:
                        del api_data[key]
                # print "has api data: %s" % pformat(api_data)
                updates.new_slave.append(api_data)

    check_warnings()

    # except Exception, exc:
    #     Registrar.register_error(repr(exc))
    #     settings.report_and_quit = True

    #########################################
    # Write Report
    #########################################

    Registrar.register_progress("Write Report")

    with io.open(settings.rep_main_path, 'w+', encoding='utf8') as res_file:
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

        if settings['do_sync'] and (updates.delta_slave):

            delta_group = HtmlReporter.Group('deltas', 'Field Changes')

            s_delta_list = ShopObjList(
                [
                    delta_sync_update.new_s_object
                    for delta_sync_update in updates.delta_slave
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
                    settings['rep_delta_slave_csv_path'],
                    ColDataWoo.get_col_names(all_delta_cols))

        #
        report_matching = settings['do_sync']
        if report_matching:

            matching_group = HtmlReporter.Group('product_matching',
                                                'Product Matching Results')
            if matches.globals:
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
                            matches.globals.tabulate(tablefmt="html"),
                            'length':
                            len(matches.globals)
                        }))
            if matches.masterless:
                matching_group.add_section(
                    HtmlReporter.Section(
                        'matches.masterless',
                        **{
                            'title':
                            'Masterless matches',
                            'description':
                            "matches are masterless",
                            'data':
                            matches.masterless.tabulate(
                                tablefmt="html"),
                            'length':
                            len(matches.masterless)
                        }))
            if matches.slaveless:
                matching_group.add_section(
                    HtmlReporter.Section(
                        'matches.slaveless',
                        **{
                            'title':
                            'Slaveless matches',
                            'description':
                            "matches are slaveless",
                            'data':
                            matches.slaveless.tabulate(
                                tablefmt="html"),
                            'length':
                            len(matches.slaveless)
                        }))
            if matching_group.sections:
                reporter.add_group(matching_group)

            if settings['do_categories']:
                matching_group = HtmlReporter.Group(
                    'category_matching', 'Category Matching Results')
                if category_matches.globals:
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
                                category_matches.globals.tabulate(
                                    tablefmt="html"),
                                'length':
                                len(category_matches.globals)
                            }))
                if category_matches.masterless:
                    matching_group.add_section(
                        HtmlReporter.Section(
                            'category_matches.masterless',
                            **{
                                'title':
                                'Masterless matches',
                                'description':
                                "matches are masterless",
                                'data':
                                category_matches.masterless.tabulate(
                                    tablefmt="html"),
                                'length':
                                len(category_matches.masterless)
                            }))
                if category_matches.slaveless:
                    matching_group.add_section(
                        HtmlReporter.Section(
                            'category_matches.slaveless',
                            **{
                                'title':
                                'Slaveless matches',
                                'description':
                                "matches are slaveless",
                                'data':
                                category_matches.slaveless.tabulate(
                                    tablefmt="html"),
                                'length':
                                len(category_matches.slaveless)
                            }))
                if matching_group.sections:
                    reporter.add_group(matching_group)

            if settings['do_variations']:
                matching_group = HtmlReporter.Group(
                    'variation_matching', 'Variation Matching Results')
                if variation_matches.globals:
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
                                variation_matches.globals.tabulate(
                                    tablefmt="html"),
                                'length':
                                len(variation_matches.globals)
                            }))
                if variation_matches.masterless:
                    matching_group.add_section(
                        HtmlReporter.Section(
                            'variation_matches.masterless',
                            **{
                                'title':
                                'Masterless matches',
                                'description':
                                "matches are masterless",
                                'data':
                                variation_matches.masterless.tabulate(
                                    tablefmt="html"),
                                'length':
                                len(variation_matches.masterless)
                            }))
                if variation_matches.slaveless:
                    matching_group.add_section(
                        HtmlReporter.Section(
                            'variation_matches.slaveless',
                            **{
                                'title':
                                'Slaveless matches',
                                'description':
                                "matches are slaveless",
                                'data':
                                variation_matches.slaveless.tabulate(
                                    tablefmt="html"),
                                'length':
                                len(variation_matches.slaveless)
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
                        for update in updates.slave
                    ]),
                    length=len(updates.slave)))

            syncing_group.add_section(
                HtmlReporter.Section(
                    "updates.problematic",
                    description="items can't be merged because they are too dissimilar",
                    data='<hr>'.join([
                        update.tabulate(tablefmt="html")
                        for update in updates.problematic
                    ]),
                    length=len(updates.problematic)))

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
                            for update in variation_updates.slave
                        ]),
                        length=len(variation_updates.slave)))

                syncing_group.add_section(
                    HtmlReporter.Section(
                        "variation_updates.problematic",
                        description="items can't be merged because they are too dissimilar",
                        data='<hr>'.join([
                            update.tabulate(tablefmt="html")
                            for update in variation_updates.problematic
                        ]),
                        length=len(variation_updates.problematic)))

                reporter.add_group(syncing_group)

        report_cats = settings['do_sync'] and settings['do_categories']
        if report_cats:
            # "reporting cats. settings['do_sync']: %s, do_categories: %s" % (
            #     repr(settings['do_sync']), repr(settings['do_categories']))
            syncing_group = HtmlReporter.Group('cats',
                                               'Category Syncing Results')

            syncing_group.add_section(
                HtmlReporter.Section(
                    ('category_matches.delete_slave'),
                    description="%s items will leave categories" %
                    settings.slave_name,
                    data=tabulate(
                        [
                            [
                                index,
                                # parsers.slave.products[index],
                                # parsers.slave.products[index].categories,
                                # ", ".join(category.woo_cat_name \
                                # for category in matches_.merge().m_objects),
                                ", ".join([
                                    category_.woo_cat_name
                                    for category_ in matches_.merge().s_objects
                                ])
                            ] for index, matches_ in category_matches.delete_slave.items()
                        ],
                        tablefmt="html"),
                    length=len(category_matches.delete_slave)
                    # data = '<hr>'.join([
                    #         "%s<br/>%s" % (index, match.tabulate(tablefmt="html")) \
                    #         for index, match in category_matches.delete_slave.items()
                    #     ]
                    # )
                ))

            category_matches.delete_slave_ns_data = tabulate(
                [
                    [
                        index,
                        ", ".join([
                            category_.woo_cat_name
                            for category_ in matches_.merge().s_objects
                            if not re.search('Specials', category_.woo_cat_name)
                        ])
                    ] for index, matches_ in category_matches.delete_slave.items()
                ],
                tablefmt="html"
            )

            syncing_group.add_section(
                HtmlReporter.Section(
                    ('category_matches.delete_slave_not_specials'),
                    description="%s items will leave categories" %
                    settings.slave_name,
                    data=category_matches.delete_slave_ns_data,
                    length=len(category_matches.delete_slave)
                    # data = '<hr>'.join([
                    #         "%s<br/>%s" % (index, match.tabulate(tablefmt="html")) \
                    #         for index, match in category_matches.delete_slave.items()
                    #     ]
                    # )
                ))

            syncing_group.add_section(
                HtmlReporter.Section(
                    ('category_matches.new_slave'),
                    description="%s items will join categories" %
                    settings.slave_name,
                    data=tabulate(
                        [
                            [
                                index,
                                # parsers.slave.products[index],
                                # parsers.slave.products[index].categories,
                                ", ".join([
                                    category_.woo_cat_name
                                    for category_ in matches_.merge()
                                    .m_objects
                                ]),
                                # ", ".join(category_.woo_cat_name \
                                # for category_ in matches_.merge().s_objects)
                            ] for index, matches_ in category_matches.new_slave.items()
                        ],
                        tablefmt="html"),
                    length=len(category_matches.new_slave)
                    # data = '<hr>'.join([
                    #         "%s<br/>%s" % (index, match.tabulate(tablefmt="html")) \
                    #         for index, match in category_matches.delete_slave.items()
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

    all_product_updates = updates.slave
    if settings['do_variations']:
        all_product_updates += variation_updates.slave
    if settings.do_problematic:
        all_product_updates += updates.problematic
        if settings['do_variations']:
            all_product_updates += variation_updates.problematic

    # don't perform updates if limit was set
    if settings['slave_parse_limit']:
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

        slave_client_class = settings.slave_upload_client_class
        slave_client_args = settings.slave_upload_client_args

        with slave_client_class(**slave_client_args) as slave_client:
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

    if settings.do_report:
        if settings['rep_web_path']:
            shutil.copyfile(settings.rep_main_path, settings['rep_web_path'])
            if settings['web_browser']:
                os.environ['BROWSER'] = settings['web_browser']
                # print "set browser environ to %s" % repr(web_browser)
            # print "moved file from %s to %s" % (settings.rep_main_path, repWeb_path)

            webbrowser.open(settings['rep_web_link'])
    else:
        print "open this link to view report %s" % settings['rep_web_link']


def catch_main(override_args=None):
    """Run the main function within a try statement and attempt to analyse failure."""
    file_path = __file__
    cur_dir = os.getcwd() + '/'
    if file_path.startswith(cur_dir):
        file_path = file_path[len(cur_dir):]
    override_args_repr = ''
    if override_args is not None:
        override_args_repr = ' '.join(override_args)

    full_run_str = "%s %s %s" % (str(sys.executable), str(file_path), override_args_repr)

    settings = SettingsNamespaceProd()

    status = 0
    try:
        main(settings=settings, override_args=override_args)
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
            if Registrar.DEBUG_TRACE:
                import pudb; pudb.set_trace()


    with io.open(settings.log_path, 'w+', encoding='utf8') as log_file:
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
        settings.rep_fail_master_csv_path, settings.rep_fail_slave_csv_path, settings.rep_main_path
    ]

    with zipfile.ZipFile(settings.zip_path, 'w') as zip_file:
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
