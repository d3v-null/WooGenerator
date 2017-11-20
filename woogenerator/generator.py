"""Module for generating woocommerce csv import files from Google Drive Data."""

from __future__ import absolute_import

import io
import json
import os
import shutil
import sys
import time
import traceback
import webbrowser
import zipfile
from bisect import insort
from collections import OrderedDict
from pprint import pformat, pprint

from exitstatus import ExitStatus
from httplib2 import ServerNotFoundError
from PIL import Image
from requests.exceptions import ConnectionError, ConnectTimeout, ReadTimeout

from .client.prod import CatSyncClientWC
from .matching import CategoryMatcher, ProductMatcher, VariationMatcher, ImageMatcher
from .images import process_images
from .namespace.core import (MatchNamespace, ParserNamespace, ResultsNamespace,
                             UpdateNamespace)
from .namespace.prod import SettingsNamespaceProd
from .parsing.dyn import CsvParseDyn
from .parsing.myo import MYOProdList
from .parsing.shop import ShopObjList
from .parsing.special import CsvParseSpecial
from .parsing.woo import WooCatList, WooProdList, WooVarList
from .syncupdate import SyncUpdateVarWoo
from .utils import ProgressCounter, Registrar, SanitationUtils, SeqUtils
from .utils.reporter import (ReporterNamespace, do_cat_sync_gruop,
                             do_category_matches_group, do_delta_group,
                             do_duplicates_group, do_duplicates_summary_group,
                             do_failures_group, do_main_summary_group,
                             do_matches_group, do_matches_summary_group,
                             do_post_summary_group,
                             do_successes_group, do_sync_group,
                             do_variation_matches_group,
                             do_variation_sync_group)
from .parsing.api import ApiParseWoo

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
        'master_parser_args', 'master_parser_class'
    ]

    Registrar.register_message('schema: %s, woo_schemas: %s' % (
        settings.schema, settings.woo_schemas
    ))

    for thing in things_to_check:
        Registrar.register_message(
            "%s: %s" % (thing, getattr(settings, thing))
        )
        assert getattr(settings, thing), "settings must specify %s" % thing

    parsers.dyn = CsvParseDyn()
    parsers.special = CsvParseSpecial()

    if Registrar.DEBUG_GEN:
        Registrar.register_message(
            "master_download_client_args: %s" %
            settings.master_download_client_args)

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

        parsers.master = settings.master_parser_class(
            **settings.master_parser_args
        )

        Registrar.register_progress("analysing master product data")

        analysis_kwargs = {
            'data_path': settings.master_path,
            'gid': settings.gen_gid,
            'limit': settings['master_parse_limit']
        }
        if Registrar.DEBUG_PARSER:
            Registrar.register_message("analysis_kwargs: %s" % analysis_kwargs)

        client.analyse_remote(parsers.master, **analysis_kwargs)

        if Registrar.DEBUG_PARSER and hasattr(
                parsers.master, 'categories_name'):
            for category_name, category_list in getattr(
                    parsers.master, 'categories_name').items():
                if len(category_list) < 2:
                    continue
                if SeqUtils.check_equal(
                        [category.namesum for category in category_list]):
                    continue
                Registrar.register_warning("bad category: %50s | %d | %s" % (
                    category_name[:50], len(category_list), str(category_list)
                ))

        return parsers


def populate_slave_parsers(parsers, settings):
    """Populate the parsers for data from the slave database."""

    parsers.slave = settings.slave_parser_class(**settings.slave_parser_args)

    slave_client_class = settings.slave_download_client_class
    slave_client_args = settings.slave_download_client_args

    # with ProdSyncClientWC(settings['slave_wp_api_params']) as client:

    if settings.schema_is_woo and settings['do_images']:
        Registrar.register_progress("analysing API image data")
        img_client_class = settings.slave_img_sync_client_class
        img_client_args = settings.slave_img_sync_client_args

        with img_client_class(**img_client_args) as client:
            client.analyse_remote_imgs(
                parsers.slave,
                data_path=settings.slave_img_path
            )

    if settings.schema_is_woo and settings['do_categories']:
        Registrar.register_progress("analysing API category data")

        cat_upload_client_class = settings.slave_cat_sync_client_class
        cat_upload_client_args = settings.slave_cat_sync_client_args

        with cat_upload_client_class(**cat_upload_client_args) as client:
            client.analyse_remote_categories(
                parsers.slave,
                data_path=settings.slave_cat_path
            )


    with slave_client_class(**slave_client_args) as client:
        # try:

        Registrar.register_progress("analysing API data")

        # Registrar.DEBUG_ABSTRACT = True
        # Registrar.DEBUG_API = True
        # Registrar.DEBUG_GEN = True
        # Registrar.DEBUG_TREE = True
        # Registrar.DEBUG_WOO = True
        # Registrar.DEBUG_TRACE = True
        # ApiParseWoo.product_resolver = Registrar.exception_resolver
        client.analyse_remote(
            parsers.slave,
            data_path=settings.slave_path
        )

    if Registrar.DEBUG_CLIENT:
        container = settings.slave_parser_class.product_container.container
        prod_list = container(parsers.slave.products.values())
        Registrar.register_message("Products: \n%s" % prod_list.tabulate())

    return parsers

def export_master_parser(settings, parsers):
    """Export key information from master parser to csv."""
    Registrar.register_progress("Exporting Master info to disk")

    product_cols = settings.coldata_class.get_product_cols()
    product_colnames = settings.coldata_class.get_col_names(product_cols)

    for col in settings['exclude_cols']:
        if col in product_cols:
            del product_cols[col]

    if settings.schema_is_woo:
        attribute_cols = settings.coldata_class.get_attribute_cols(
            parsers.master.attributes, parsers.master.vattributes)
        product_colnames = settings.coldata_class.get_col_names(
            SeqUtils.combine_ordered_dicts(product_cols, attribute_cols))

    if Registrar.DEBUG_GEN:
        Registrar.register_message("master parser class is %s" % settings.master_parser_class)

    container = settings.master_parser_class.product_container.container

    if Registrar.DEBUG_GEN:
        Registrar.register_message("export container is %s" % container.__name__)

    product_list = container(parsers.master.products.values())
    product_list.export_items(settings.fla_path, product_colnames)

    if settings.schema_is_woo:
        # variations
        variation_container = settings.master_parser_class.variation_container.container
        variation_cols = settings.coldata_class.get_variation_cols()
        attribute_meta_cols = settings.coldata_class.get_attribute_meta_cols(
            parsers.master.vattributes)
        variation_col_names = settings.coldata_class.get_col_names(
            SeqUtils.combine_ordered_dicts(variation_cols, attribute_meta_cols))
        if settings.do_variations and parsers.master.variations:

            variation_list = variation_container(parsers.master.variations.values())
            variation_list.export_items(settings.flv_path, variation_col_names)

            updated_variations = parsers.master.updated_variations.values()

            if updated_variations:
                updated_variations_list = variation_container(updated_variations)
                updated_variations_list.export_items(
                    settings.flvu_path, variation_col_names
                )

        # categories
        if settings.do_categories and parsers.master.categories:
            category_cols = settings.coldata_class_cat.get_export_cols_gen('path')
            category_col_names = settings.coldata_class_cat.get_col_names(category_cols)
            category_container = settings.master_parser_class.category_container.container
            category_list = category_container(parsers.master.categories.values())
            category_list.export_items(settings.cat_path, category_col_names)

        # specials
        if settings.do_specials and settings.current_special_id:
            special_products = parsers.master.onspecial_products.values()
            if special_products:
                special_product_list = container(special_products)
                special_product_list.export_items(
                    settings.fls_path, product_colnames
                )
            special_variations = parsers.master.onspecial_variations.values()
            if special_variations:
                sp_variation_list = variation_container(special_variations)
                sp_variation_list.export_items(
                    settings.flvs_path, variation_col_names
                )

        updated_products = parsers.master.updated_products.values()
        if updated_products:
            updated_product_list = container(updated_products)
            updated_product_list.export_items(
                settings.flu_path, product_colnames
            )

    Registrar.register_progress("CSV Files have been created.")

def cache_api_data(settings, parsers):
    """Export key information from slave parser to csv."""
    if not settings.download_slave:
        return

    Registrar.register_progress("Exporting Slave info to disk")
    container = settings.slave_parser_class.product_container.container
    product_list = container(parsers.slave.products.values())
    product_list.export_api_data(settings.slave_path)

    if settings.do_categories and parsers.slave.categories:
        category_container = settings.slave_parser_class.category_container.container
        category_list = category_container(parsers.slave.categories.values())
        category_list.export_api_data(settings.slave_cat_path)

    if settings.do_images and parsers.slave.images:
        image_container = settings.slave_parser_class.image_container.container
        image_list = image_container(parsers.slave.images.values())
        image_list.export_api_data(settings.slave_img_path)

def do_match_images(parsers, matches, settings):
    if Registrar.DEBUG_IMG:
        Registrar.register_message(
            "matching %d master images with %d slave images" %
            (len(parsers.master.images),
             len(parsers.slave.images)))

    matches.image = MatchNamespace(
        index_fn=ImageMatcher.image_index_fn
    )

    image_matcher = ImageMatcher()
    image_matcher.clear()
    slave_imgs_attachments = OrderedDict([
        (index, image) for index, image in parsers.slave.images.items()
        if image.attachments.has_product_categories
    ])
    master_imgs_attachments = OrderedDict([
        (index, image) for index, image in parsers.master.images.items()
        if image.attachments.has_product_categories
    ])
    image_matcher.process_registers(
        slave_imgs_attachments, master_imgs_attachments
    )

    matches.image.globals.add_matches(image_matcher.pure_matches)
    matches.image.masterless.add_matches(image_matcher.masterless_matches)
    matches.image.slaveless.add_matches(image_matcher.slaveless_matches)

    if Registrar.DEBUG_IMG:
        if image_matcher.pure_matches:
            Registrar.register_message("All Image matches:\n%s" % (
                '\n'.join(map(str, image_matcher.matches))))

    matches.image.valid += image_matcher.pure_matches

    if image_matcher.duplicate_matches:
        matches.image.duplicate['title'] = image_matcher.duplicate_matches

        for match in image_matcher.duplicate_matches:
            master_filenames = [img.file_name for img in match.m_objects]
            if all(master_filenames) \
                    and SeqUtils.check_equal(master_filenames) \
                    and not len(match.s_objects) > 1:
                matches.image.valid.append(match)
            else:
                matches.image.invalid.append(match)
        if matches.image.invalid:
            exc = UserWarning(
                "images couldn't be synchronized because of ambiguous filenames:\n%s"
                % '\n'.join(map(str, matches.image.invalid)))
            Registrar.register_error(exc)
            raise exc

    return matches

def do_match_categories(parsers, matches, settings):
    if Registrar.DEBUG_CATS:
        Registrar.register_message(
            "matching %d master categories with %d slave categories" %
            (len(parsers.master.categories),
             len(parsers.slave.categories)))

    if not( parsers.master.categories and parsers.slave.categories ):
        return matches

    matches.category = MatchNamespace(
        index_fn=CategoryMatcher.category_index_fn
    )

    category_matcher = CategoryMatcher()
    category_matcher.clear()
    category_matcher.process_registers(
        parsers.slave.categories, parsers.master.categories
    )

    matches.category.globals.add_matches(category_matcher.pure_matches)
    matches.category.masterless.add_matches(
        category_matcher.masterless_matches)
    # matches.deny_anomalous(
    #     'category_matcher.masterless_matches', category_matcher.masterless_matches
    # )
    matches.category.slaveless.add_matches(category_matcher.slaveless_matches)
    # matches.deny_anomalous(
    #     'category_matcher.slaveless_matches', category_matcher.slaveless_matches
    # )

    if Registrar.DEBUG_CATS:
        if category_matcher.pure_matches:
            Registrar.register_message("All Category matches:\n%s" % (
                '\n'.join(map(str, category_matcher.matches))))

    matches.category.valid += category_matcher.pure_matches

    if category_matcher.duplicate_matches:
        matches.category.duplicate['title'] = category_matcher.duplicate_matches

        for match in category_matcher.duplicate_matches:
            master_taxo_sums = [cat.namesum for cat in match.m_objects]
            if all(master_taxo_sums) \
                    and SeqUtils.check_equal(master_taxo_sums) \
                    and not len(match.s_objects) > 1:
                matches.category.valid.append(match)
            else:
                matches.category.invalid.append(match)
        if matches.category.invalid:
            exc = UserWarning(
                "categories couldn't be synchronized because of ambiguous names:\n%s"
                % '\n'.join(map(str, matches.category.invalid)))
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

    return matches


def do_match(parsers, matches, settings):
    """For every item in slave, find its counterpart in master."""

    Registrar.register_progress("Attempting matching")

    matches.variation = MatchNamespace(
        index_fn=ProductMatcher.product_index_fn
    )

    if settings['do_categories']:
        matches.category.prod = OrderedDict()

    if not settings.do_sync:
        return matches

    product_matcher = ProductMatcher()
    product_matcher.process_registers(
        parsers.slave.products, parsers.master.products
    )
    # print product_matcher.__repr__()

    matches.globals.add_matches(product_matcher.pure_matches)
    matches.masterless.add_matches(product_matcher.masterless_matches)
    matches.deny_anomalous(
        'product_matcher.masterless_matches', product_matcher.masterless_matches
    )
    matches.slaveless.add_matches(product_matcher.slaveless_matches)
    matches.deny_anomalous(
        'product_matcher.slaveless_matches', product_matcher.slaveless_matches
    )

    try:
        matches.deny_anomalous(
            'product_matcher.duplicate_matches',
            product_matcher.duplicate_matches,
            True
        )
    except AssertionError as exc:
        exc = UserWarning(
            "products couldn't be synchronized because of ambiguous SKUs:%s"
            % '\n'.join(map(str, product_matcher.duplicate_matches)))
        Registrar.register_error(exc)
        raise exc

    if settings['do_categories']:

        category_matcher = CategoryMatcher()

        for _, prod_match in enumerate(matches.globals):
            if Registrar.DEBUG_CATS or Registrar.DEBUG_VARS:
                Registrar.register_message("processing prod_match: %s" %
                                           prod_match.tabulate())
            m_object = prod_match.m_object
            s_object = prod_match.s_object
            match_index = prod_match.singular_index

            category_matcher.clear()
            category_matcher.process_registers(
                s_object.categories, m_object.categories
            )

            matches.category.prod[match_index] = MatchNamespace(
                index_fn=CategoryMatcher.category_index_fn)

            matches.category.prod[match_index].globals.add_matches(
                category_matcher.pure_matches
            )
            matches.category.prod[match_index].masterless.add_matches(
                category_matcher.masterless_matches
            )
            matches.category.prod[match_index].slaveless.add_matches(
                category_matcher.slaveless_matches
            )

            if Registrar.DEBUG_CATS:
                Registrar.register_message(
                    "category matches for update:\n%s" % (
                        category_matcher.__repr__()))

    if settings['do_variations']:

        variation_matcher = VariationMatcher()
        variation_matcher.process_registers(
            parsers.slave.variations, parsers.master.variations
        )

        if Registrar.DEBUG_VARS:
            Registrar.register_message("variation matcher:\n%s" %
                                       variation_matcher.__repr__())

        matches.variation.globals.add_matches(variation_matcher.pure_matches)
        matches.variation.masterless.add_matches(
            variation_matcher.masterless_matches)
        matches.variation.deny_anomalous(
            'variation_matcher.masterless_matches',
            variation_matcher.masterless_matches
        )
        matches.variation.slaveless.add_matches(
            variation_matcher.slaveless_matches)
        matches.variation.deny_anomalous(
            'variation_matcher.slaveless_matches',
            variation_matcher.slaveless_matches
        )
        if variation_matcher.duplicate_matches:
            matches.variation.duplicate['index'] = variation_matcher.duplicate_matches

    return matches


def do_merge_images(matches, parsers, updates, settings):
    updates.image = UpdateNamespace()

    if not hasattr(matches, 'image'):
        return updates

    if Registrar.DEBUG_TRACE:
        print(matches.image.tabulate())

    for match in matches.image.valid:
        s_object = match.s_object
        m_object = match.m_object

        sync_update = settings.syncupdate_class_img(m_object, s_object)

        if Registrar.DEBUG_TRACE:
            print(sync_update.tabulate())
            import pudb; pudb.set_trace()

def do_merge_categories(matches, parsers, updates, settings):
    updates.category = UpdateNamespace()

    if not hasattr(matches, 'category'):
        return updates

    for match in matches.category.valid:
        s_object = match.s_object
        for m_object in match.m_objects:
            # m_object = match.m_objects[0]

            sync_update = settings.syncupdate_class_cat(m_object, s_object)

            sync_update.update()


            if not sync_update.important_static:
                insort(updates.category.problematic, sync_update)
                continue

            if sync_update.m_updated:
                updates.category.master.append(sync_update)

            if sync_update.s_updated:
                updates.category.slave.append(sync_update)

    for update in updates.category.master:
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
            for warning in warnings:
                if not warning['subject'] == update.master_name:
                    continue

                new_val = warning['new_value']
                parsers.master.categories[update.master_id][col] = new_val

    if settings['auto_create_new']:
        for match in enumerate(matches.category.slaveless):
            m_object = match.m_object
            sync_update = settings.syncupdate_class_cat(m_object)
            updates.category.slaveless.append(sync_update)

    return updates

def do_merge(matches, parsers, updates, settings):
    """For a given list of matches, return a description of updates required to merge them."""

    if settings.do_variations:
        updates.variation = UpdateNamespace()

    if not settings['do_sync']:
        return updates

    # Merge products

    sync_cols = settings.sync_cols_prod

    if Registrar.DEBUG_UPDATE:
        Registrar.register_message("sync_cols: %s" % repr(sync_cols))

    for col in settings['exclude_cols']:
        if col in sync_cols:
            del sync_cols[col]

    for _, prod_match in enumerate(matches.globals):
        if Registrar.DEBUG_CATS or Registrar.DEBUG_VARS:
            Registrar.register_message("processing prod_match: %s" %
                                       prod_match.tabulate())
        m_object = prod_match.m_object
        s_object = prod_match.s_object


        sync_update = settings.syncupdate_class_prod(m_object, s_object)

        # , "gcs %s is not variation but object is" % repr(gcs)
        assert not m_object.is_variation
        # , "gcs %s is not variation but object is" % repr(gcs)
        assert not s_object.is_variation

        sync_update.update()

        # print sync_update.tabulate()

        if settings['do_categories']:

            update_params = {
                'col': 'category_ids',
                'subject': sync_update.slave_name
            }

            master_cat_ids = set([
                master_category.wpid
                for master_category in m_object.categories.values()
                if master_category.wpid
            ])
            slave_cat_ids = set([
                slave_category.wpid
                for slave_category in s_object.categories.values()
                if slave_category.wpid
            ])

            if Registrar.DEBUG_CATS:
                Registrar.register_message(
                    "comparing categories of %s:\n%s\n%s\n%s\n%s" %
                    (m_object.codesum, str(m_object.categories.values()),
                     str(s_object.categories.values()),
                     str(master_cat_ids), str(slave_cat_ids), ))

            sync_update.old_m_object_core['category_ids'] = list(master_cat_ids)
            sync_update.old_s_object_core['category_ids'] = list(slave_cat_ids)
            update_params['new_value'] = sync_update.old_m_object_core['category_ids']
            update_params['old_value'] = sync_update.old_s_object_core['category_ids']
            # update_params['new_value'] = [
            #     dict(id=category_id) for category_id in master_cat_ids
            # ]
            # update_params['old_value'] = [
            #     dict(id=category_id) for category_id in master_cat_ids
            # ]

            match_index = prod_match.singular_index
            product_category_matches = matches.category.prod.get(match_index)
            if product_category_matches and any([
                product_category_matches.slaveless,
                product_category_matches.masterless
            ]):
                assert \
                    master_cat_ids != slave_cat_ids, \
                    (
                        "if change_match_list exists, then master_cat_ids "
                         "should not equal slave_cat_ids. "
                         "This might mean that you have not enabled "
                         "auto_create_new categories.\n"
                         "master_cat_ids: %s\n"
                         "slave_cat_ids: %s\n"
                         "change_match_list: \n%s"
                    ) % (
                        master_cat_ids,
                        slave_cat_ids,
                        product_category_matches.tabulate()
                    )
                update_params['reason'] = 'updating'

                sync_update.loser_update(**update_params)
            else:
                assert\
                    master_cat_ids == slave_cat_ids, \
                    "should equal, %s | %s" % (
                        repr(master_cat_ids),
                        repr(slave_cat_ids)
                    )
                update_params['reason'] = 'identical'
                sync_update.tie_update(**update_params)

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
        if matches.variation.duplicate:
            exc = UserWarning(
                "variations couldn't be synchronized because of ambiguous SKUs:%s"
                % '\n'.join(map(str, matches.variation.duplicate)))
            Registrar.register_error(exc)
            raise exc

        for var_match_count, var_match in enumerate(matches.variation.globals):
            # print "processing var_match: %s" % var_match.tabulate()
            m_object = var_match.m_object
            s_object = var_match.s_object

            sync_update = settings.syncupdate_class_var(m_object, s_object)

            sync_update.update()

            # Assumes that GDrive is read only, doesn't care about master
            # updates
            if not sync_update.s_updated:
                continue

            if Registrar.DEBUG_VARS:
                Registrar.register_message("var update %d:\n%s" % (
                    var_match_count, sync_update.tabulate()))

            if not sync_update.important_static:
                insort(updates.variation.problematic, sync_update)
                continue

            if sync_update.s_updated:
                insort(updates.variation.slave, sync_update)

        for var_match_count, var_match in enumerate(
                matches.variation.slaveless):
            assert var_match.has_no_slave
            m_object = var_match.m_object

            # sync_update = SyncUpdateVarWoo(m_object, None)

            # sync_update.update()

            if Registrar.DEBUG_VARS:
                Registrar.register_message("var create %d:\n%s" % (
                    var_match_count, m_object.identifier))

            # TODO: figure out which attribute terms to add

        for var_match_count, var_match in enumerate(
                matches.variation.masterless):
            assert var_match.has_no_master
            s_object = var_match.s_object

            # sync_update = SyncUpdateVarWoo(None, s_object)

            # sync_update.update()

            if Registrar.DEBUG_VARS:
                Registrar.register_message("var delete: %d:\n%s" % (
                    var_match_count, s_object.identifier))

            # TODO: figure out which attribute terms to delete

    if settings['auto_create_new']:
        for new_prod_count, new_prod_match in enumerate(matches.slaveless):
            m_object = new_prod_match.m_object
            Registrar.register_message(
                "will create product %d: %s" % (
                    new_prod_count, m_object.identifier
                )
            )
            api_data = m_object.to_api_data(settings.coldata_class, 'wp-api')
            for key in ['id', 'slug']:
                if key in api_data:
                    del api_data[key]
            # print "has api data: %s" % pformat(api_data)
            updates.slaveless.append(api_data)

    return updates

def do_report_categories(reporters, matches, updates, parsers, settings):
    Registrar.register_progress("Write Categories Report")

    do_cat_sync_gruop(reporters.cat, matches, updates, parsers, settings)

    if reporters.cat:
        reporters.cat.write_document_to_file('cat', settings.rep_cat_path)

    return reporters

    # with io.open(settings.rep_cat_path, 'w+', encoding='utf8') as res_file:
    #     reporter = HtmlReporter()
    #
    #     syncing_group = HtmlReporter.Group('cats',
    #                                        'Category Syncing Results')
    #
    #     # TODO: change this to change this to updates.category.prod
    #     # syncing_group.add_section(
    #     #     HtmlReporter.Section(
    #     #         ('matches.category.delete_slave'),
    #     #         description="%s items will leave categories" %
    #     #         settings.slave_name,
    #     #         data=tabulate(
    #     #             [
    #     #                 [
    #     #                     index,
    #     #                     # parsers.slave.products[index],
    #     #                     # parsers.slave.products[index].categories,
    #     #                     # ", ".join(category.cat_name \
    #     #                     # for category in matches_.merge().m_objects),
    #     #                     ", ".join([
    #     #                         category_.cat_name
    #     #                         for category_ in matches_.merge().s_objects
    #     #                     ])
    #     #                 ] for index, matches_ in matches.category.delete_slave.items()
    #     #             ],
    #     #             tablefmt="html"),
    #     #         length=len(matches.category.delete_slave)
    #     #         # data = '<hr>'.join([
    #     #         #         "%s<br/>%s" % (index, match.tabulate(tablefmt="html")) \
    #     #         #         for index, match in matches.category.delete_slave.items()
    #     #         #     ]
    #     #         # )
    #     #     ))
    #
    #     # TODO: change this to change this to updates.category.prod
    #     # matches.category.delete_slave_ns_data = tabulate(
    #     #     [
    #     #         [
    #     #             index,
    #     #             ", ".join([
    #     #                 category_.cat_name
    #     #                 for category_ in matches_.merge().s_objects
    #     #                 if not re.search('Specials', category_.cat_name)
    #     #             ])
    #     #         ] for index, matches_ in matches.category.delete_slave.items()
    #     #     ],
    #     #     tablefmt="html"
    #     # )
    #     #
    #     # syncing_group.add_section(
    #     #     HtmlReporter.Section(
    #     #         ('matches.category.delete_slave_not_specials'),
    #     #         description="%s items will leave categories" %
    #     #         settings.slave_name,
    #     #         data=matches.category.delete_slave_ns_data,
    #     #         length=len(matches.category.delete_slave)
    #     #         # data = '<hr>'.join([
    #     #         #         "%s<br/>%s" % (index, match.tabulate(tablefmt="html")) \
    #     #         #         for index, match in matches.category.delete_slave.items()
    #     #         #     ]
    #     #         # )
    #     #     ))
    #
    #     # TODO: change this to updates.category.prod
    #     # syncing_group.add_section(
    #     #     HtmlReporter.Section(
    #     #         ('matches.category.slaveless'),
    #     #         description="%s items will join categories" %
    #     #         settings.slave_name,
    #     #         data=tabulate(
    #     #             [
    #     #                 [
    #     #                     index,
    #     #                     # parsers.slave.products[index],
    #     #                     # parsers.slave.products[index].categories,
    #     #                     ", ".join([
    #     #                         category_.cat_name
    #     #                         for category_ in matches_.merge()
    #     #                         .m_objects
    #     #                     ]),
    #     #                     # ", ".join(category_.cat_name \
    #     #                     # for category_ in matches_.merge().s_objects)
    #     #                 ] for index, matches_ in matches.category.slaveless.items()
    #     #             ],
    #     #             tablefmt="html"),
    #     #         length=len(matches.category.slaveless)
    #     #         # data = '<hr>'.join([
    #     #         #         "%s<br/>%s" % (index, match.tabulate(tablefmt="html")) \
    #     #         #         for index, match in matches.category.delete_slave.items()
    #     #         #     ]
    #     #         # )
    #     #     ))
    #
    #     reporter.add_group(syncing_group)
    #
    # if not reporter.groups:
    #     empty_group = HtmlReporter.Group('empty', 'Nothing to report')
    #     # empty_group.add_section(
    #     #     HtmlReporter.Section(
    #     #         ('empty'),
    #     #         data = ''
    #     #
    #     #     )
    #     # )
    #     Registrar.register_message('nothing to report')
    #     reporter.add_group(empty_group)
    #
    # res_file.write(reporter.get_document_unicode())


def do_report(reporters, matches, updates, parsers, settings):
    """ Write report of changes to be made. """

    if not settings.get('do_report'):
        return reporters

    Registrar.register_progress("Write Report")

    do_main_summary_group(
        reporters.main, matches, updates, parsers, settings
    )
    do_delta_group(
        reporters.main, matches, updates, parsers, settings
    )
    do_sync_group(
        reporters.main, matches, updates, parsers, settings
    )
    do_variation_sync_group(
        reporters.main, matches, updates, parsers, settings
    )

    if reporters.main:
        reporters.main.write_document_to_file('main', settings.rep_main_path)

    if settings.get('report_matching'):
        Registrar.register_progress("Write Matching Report")

        do_matches_summary_group(
            reporters.match, matches, updates, parsers, settings
        )
        do_matches_group(
            reporters.match, matches, updates, parsers, settings
        )
        if settings.do_variations:
            do_variation_matches_group(
                reporters.match, matches, updates, parsers, settings
            )
        if settings.do_categories:
            do_category_matches_group(
                reporters.match, matches, updates, parsers, settings
            )

        if reporters.match:
            reporters.match.write_document_to_file(
                'match', settings.rep_match_path)

    return reporters

def do_report_post(reporters, results, settings):
    """ Reports results from performing updates."""
    pass


def do_updates_categories(updates, parsers, results, settings):
    """Perform a list of updates."""

    if not hasattr(updates, 'categories'):
        return

    if settings['auto_create_new']:
        # create categories that do not yet exist on slave
        if Registrar.DEBUG_CATS:
            Registrar.register_message("NEW CATEGORIES: %d" % (
                len(updates.category.slaveless)
            ))

        if Registrar.DEBUG_CATS:
            Registrar.DEBUG_API = True

        upload_client_class = settings.slave_cat_sync_client_class
        upload_client_args = settings.slave_cat_sync_client_args

        with upload_client_class(**upload_client_args) as client:
            if Registrar.DEBUG_CATS:
                Registrar.register_message("created cat client")
            new_categories = [
                update.m_object for update in updates.category.slaveless
            ]
            if Registrar.DEBUG_CATS:
                Registrar.register_message("new categories %s" %
                                           new_categories)

            while new_categories:
                category = new_categories.pop(0)
                if category.parent:
                    parent = category.parent
                    if not parent.is_root and not parent.wpid and parent in new_categories:
                        new_categories.append(category)
                        continue

                m_api_data = category.to_api_data(
                    settings.coldata_class, 'wp-api')
                for key in ['id', 'slug', 'sku']:
                    if key in m_api_data:
                        del m_api_data[key]
                m_api_data['name'] = category.cat_name
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
                    for key, data in settings.coldata_class.get_wpapi_category_cols(
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
    elif updates.category.slaveless:
        for update in updates.category.slaveless:
            exc = UserWarning("category needs to be created: %s" %
                              update.m_object)
            Registrar.register_warning(exc)


def do_updates(updates, settings):
    """Perform a list of updates."""

    all_product_updates = updates.slave
    if settings['do_variations']:
        all_product_updates += updates.variation.slave
    if settings.do_problematic:
        all_product_updates += updates.problematic
        if settings['do_variations']:
            all_product_updates += updates.variation.problematic

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


def main(override_args=None, settings=None):
    """Main function for generator."""
    if not settings:
        settings = SettingsNamespaceProd()
    settings.init_settings(override_args)

    settings.init_dirs()

    ########################################
    # Create Product Parser object
    ########################################

    parsers = ParserNamespace()
    populate_master_parsers(parsers, settings)

    check_warnings()

    if settings.schema_is_woo and settings.do_images:
        process_images(settings, parsers)

    if parsers.master.objects:
        export_master_parser(settings, parsers)

    populate_slave_parsers(parsers, settings)

    if parsers.slave.objects:
        cache_api_data(settings, parsers)

    matches = MatchNamespace(
        index_fn=ProductMatcher.product_index_fn
    )
    updates = UpdateNamespace()
    reporters = ReporterNamespace()
    results = ResultsNamespace()

    if settings.do_images:
        do_match_images(parsers, matches, settings)
        do_merge_images(matches, parsers, updates, settings)

    if settings.do_categories:

        do_match_categories(parsers, matches, settings)
        do_merge_categories(matches, parsers, updates, settings)
        do_report_categories(
            reporters, matches, updates, parsers, settings
        )
        check_warnings()

        try:
            results = do_updates_categories(
                updates, parsers, results, settings)
        except (SystemExit, KeyboardInterrupt):
            return reporters, results

    do_match(parsers, matches, settings)
    do_merge(matches, parsers, updates, settings)
    # check_warnings()
    do_report(reporters, matches, updates, parsers, settings)

    if settings.report_and_quit:
        sys.exit(ExitStatus.success)

    check_warnings()

    Registrar.register_message(
        "pre-sync summary: \n%s" % reporters.main.get_summary_text()
    )

    try:
        results = do_updates(updates, settings)
    except (SystemExit, KeyboardInterrupt):
        return reporters, results
    do_report_post(reporters, results, settings)

    Registrar.register_message(
        "post-sync summary: \n%s" % reporters.post.get_summary_text()
    )

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
            # print "moved file from %s to %s" % (settings.rep_main_path,
            # repWeb_path)

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

    full_run_str = "%s %s %s" % (
        str(sys.executable), str(file_path), override_args_repr)

    settings = SettingsNamespaceProd()

    status = 0
    try:
        main(settings=settings, override_args=override_args)
    except SystemExit:
        status = ExitStatus.failure
    except KeyboardInterrupt:
        pass
    except BaseException as exc:
        status = 1
        if isinstance(exc, UserWarning):
            status = 65
        elif isinstance(exc, IOError):
            status = 74
            print( "cwd: %s" % os.getcwd() )
        elif exc.__class__ in ["ReadTimeout", "ConnectionError", "ConnectTimeout", "ServerNotFoundError"]:
            status = 69  # service unavailable

        if status:
            Registrar.register_error(traceback.format_exc())
            Registrar.raise_exception(exc)

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
            except BaseException:
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
