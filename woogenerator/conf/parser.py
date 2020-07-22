"""Provide configuration parsers."""
from __future__ import absolute_import

import argparse
import ast
import os

import configargparse
from six import text_type

from ..utils import TimeUtils
from .core import (DEFAULT_LOCAL_IMG_RAW_DIR, DEFAULT_LOCAL_IN_DIR,
                   DEFAULT_LOCAL_LOG_DIR, DEFAULT_LOCAL_OUT_DIR,
                   DEFAULT_LOCAL_PROD_PATH, DEFAULT_LOCAL_PROD_TEST_PATH,
                   DEFAULT_LOCAL_USER_PATH, DEFAULT_LOCAL_USER_TEST_PATH,
                   DEFAULTS_COMMON_PATH, DEFAULTS_PROD_PATH,
                   DEFAULTS_USER_PATH)


class ArgumentParserProto(configargparse.ArgumentParser):
    """
    Provide ArgumentParser first stage argument parsing.

    First stage of argument parsing determines which config files to parse in
    the next stage of argument parsing and arguments required for setting up
    logging.
    """

    def __init__(self, **kwargs):

        if not kwargs.get('args_for_setting_config_path'):
            kwargs['args_for_setting_config_path'] = ['-c', '--config-file']

        if not kwargs.get('config_arg_help_message'):
            kwargs['config_arg_help_message'] = \
                "the location of your config file"

        if not kwargs.get('config_file_parser_class'):
            kwargs['config_file_parser_class'] = \
                configargparse.YAMLConfigFileParser

        super(ArgumentParserProto, self).__init__(**kwargs)

        self.add_proto_options()

    def get_actions(self):
        """Returns the actions object (hidden in configargparse super)."""
        return self._actions

    def add_proto_options(self):
        """Add options to top of options list."""
        # TODO: refactor this when switch to logging

        group = self.add_mutually_exclusive_group()
        group.add_argument(
            "-v",
            "--verbosity",
            action="count",
            help="increase output verbosity")
        group.add_argument("-q", "--quiet", action="store_true")
        group = self.add_mutually_exclusive_group()
        group.add_argument(
            '--testmode',
            help='Run in test mode with test servers',
            action='store_true',
            default=True)
        group.add_argument(
            '--livemode',
            help='Run the script on the live servers',
            action='store_false',
            dest='testmode')
        self.add_argument(
            '--import-name',
            help='a name to identify this run of the importer')
        self.add_argument(
            '--local-work-dir',
            help='specify the directory containing all important dirs')
        self.add_argument(
            '--local-live-config',
            help=('In livemode, this config file overrides core configs. '
                  'Path relative to local-work-dir unless local-work-dir '
                  'is falsey.'),
        )
        self.add_argument(
            '--local-test-config',
            help=('In testmode this config file overrides core configs and '
                  'local-live-config. Path relative to local-work-dir unless '
                  'local-work-dir is falsey.'),
        )
        self.add_argument(
            '--in-dir',
            help=('Dir for import files. Path relative to local-work-dir '
                  'unless local-work-dir is falsey.'),
            default=DEFAULT_LOCAL_IN_DIR,
        )
        self.add_argument(
            '--out-dir',
            help=('Dir for output files. Path relative to local-work-dir '
                  'unless local-work-dir is falsey.'),
            default=DEFAULT_LOCAL_OUT_DIR,
        )
        self.add_argument(
            '--log-dir',
            help=('Dir for log files. Path relative to local-work-dir '
                  'unless local-work-dir is falsey.'),
            default=DEFAULT_LOCAL_LOG_DIR,
        )
        self.add_argument(
            '--help-verbose', help='Verbose help', action='store_true')


class ArgumentParserProtoProd(ArgumentParserProto):
    """Provide namespace for product sync settings in first stage."""

    default_local_live_path = DEFAULT_LOCAL_PROD_PATH
    default_local_test_path = DEFAULT_LOCAL_PROD_TEST_PATH
    #
    # def __init__(self, **kwargs):
    #     if not kwargs.get('extra_default_config_files'):
    #         kwargs['extra_default_config_files'] = [DEFAULTS_PROD_PATH]
    #     super(ArgumentParserProtoProd, self).__init__(**kwargs)


class ArgumentParserProtoUser(ArgumentParserProto):
    """Provide namespace for user sync settings in first stage."""

    default_local_live_path = DEFAULT_LOCAL_USER_PATH
    default_local_test_path = DEFAULT_LOCAL_USER_TEST_PATH
    #
    # def __init__(self, **kwargs):
    #     if not kwargs.get('extra_default_config_files'):
    #         kwargs['extra_default_config_files'] = [DEFAULTS_USER_PATH]
    #     super(ArgumentParserProtoUser, self).__init__(**kwargs)


class ArgumentParserCommon(ArgumentParserProto):
    """
    Provide second stage ArgumentParser for product and user sync.

    Second stage is where all arguments are parsed from the config files
    specified
    """

    proto_argparser = ArgumentParserProto

    def __init__(self, **kwargs):
        # set common defaults

        if not kwargs.get('ignore_unknown_config_file_keys'):
            kwargs['ignore_unknown_config_file_keys'] = True

        if not kwargs.get('default_config_files'):
            kwargs['default_config_files'] = []
        if os.path.exists(DEFAULTS_COMMON_PATH):
            kwargs['default_config_files'].append(DEFAULTS_COMMON_PATH)
        if kwargs.get('extra_default_config_files'):
            for path in kwargs.pop('extra_default_config_files'):
                if os.path.exists(path):
                    kwargs['default_config_files'].append(path)

        super(ArgumentParserCommon, self).__init__(**kwargs)

        # add args
        download_group = self.add_argument_group('Import options')
        self.add_download_options(download_group)
        processing_group = self.add_argument_group('Processing options')
        self.add_processing_options(processing_group)
        reporting_group = self.add_argument_group('Reporting options')
        self.add_report_options(reporting_group)
        update_group = self.add_argument_group('Update options')
        self.add_update_options(update_group)
        client_group = self.add_argument_group('Client options')
        self.add_client_options(client_group)
        self.add_other_options()
        self.add_debug_options()

    def add_default_config_file(self, config_file):
        if config_file not in self._default_config_files:
            self._default_config_files.append(config_file)

    @property
    def default_config_files(self):
        return self._default_config_files

    def add_suppressed_argument(self, name, **kwargs):
        kwargs['help'] = argparse.SUPPRESS
        self.add_argument(name, **kwargs)

    def add_download_options(self, download_group):
        """Add options pertaining to downloading data."""

        group = download_group.add_mutually_exclusive_group()
        group.add_argument(
            '--download-main',
            help='download the main data',
            action="store_true",
            default=False)
        group.add_argument(
            '--skip-download-main',
            help=('use the local main file'
                  'instead of downloading the main data'),
            action="store_false",
            dest='download_main')
        group = download_group.add_mutually_exclusive_group()
        group.add_argument(
            '--download-subordinate',
            help='download the subordinate data',
            action="store_true")
        group.add_argument(
            '--skip-download-subordinate',
            help=('use the local subordinate file instead of downloading the subordinate '
                  'data'),
            action="store_false",
            dest='download_subordinate')
        download_group.add_argument(
            '--schema', help='what schema to process the files as')
        download_group.add_argument(
            '--since-s',
            help='filter out subordinate records edited before this date')

    def add_processing_options(self, processing_group):
        """Add options pertaining to processing data."""

        group = processing_group.add_mutually_exclusive_group()
        group.add_argument(
            '--do-sync', help='sync the databases', action="store_true")
        group.add_argument(
            '--skip-sync',
            help='don\'t sync the databases',
            action="store_false",
            dest='do_sync')

        # TODO: Figure out what the donk is with merge_mode
        processing_group.add_argument(
            '--merge-mode', choices=['sync', 'merge'], help='')
        processing_group.add_argument(
            '--last-sync',
            help="When the last sync was run ('YYYY-MM-DD HH:MM:SS')")
        # processing_group.add_argument(
        #     '--wp-srv-offset',
        #     help="the offset in seconds of the wp server",
        #     type=int,
        #     default=0
        # )
        processing_group.add_argument(
            '--wp-srv-tz',
            help="the timezone of the wp server",
            type=text_type,
            default=TimeUtils._wp_srv_tz.zone)
        processing_group.add_argument(
            '--gdrive-tz',
            help="the timezone specified in Google Drive",
            type=text_type,
            default=TimeUtils._gdrive_tz.zone)
        processing_group.add_argument(
            '--act-srv-tz',
            help="the timezone used by the Act! Database",
            type=text_type,
            default=TimeUtils._act_srv_tz.zone)
        processing_group.add_argument(
            '--xero-tz',
            help="the timezone used by the Xero API",
            type=text_type,
            default=TimeUtils._xero_tz.zone)
        processing_group.add_argument(
            '--local-tz',
            help="Override the timezone of the local computer",
            type=text_type,
            default=TimeUtils._local_tz.zone)
        processing_group.add_argument(
            '--main-parse-limit',
            help="limit number of items parsed by main parser",
            type=int,
            default=0)
        processing_group.add_argument(
            '--subordinate-parse-limit',
            help="limit number of items parsed by subordinate parser",
            type=int,
            default=0)
        processing_group.add_argument(
            '--main-and-quit',
            help="quit after exporting main parsers, don't process subordinate",
            action="store_true",
        )
        processing_group.add_argument(
            '--images-and-quit',
            help="quit after syncing images, don't process anything else",
            action="store_true",
        )
        processing_group.add_argument(
            '--categories-and-quit',
            help="quit after syncing categories, don't process anything else",
            action="store_true",
        )
        group = processing_group.add_mutually_exclusive_group()
        group.add_argument(
            '--do-export-main',
            help="Export main parsers to file",
            default=True,
        )
        group.add_argument(
            '--skip-export-main',
            help="don't export main parsers to file",
            action="store_false",
            dest='do_export_main')
        processing_group.add_argument(
            '--save-api-data',
            help=('store data from the api so it can be replayed later '
                  '(expensive)'),
            action='store_true')

        current_tsecs = TimeUtils.current_tsecs()
        year_tsecs = 60 * 60 * 24 * 365.25
        old_threshold_str = TimeUtils.wp_time_to_string(
            (current_tsecs - year_tsecs * 5))
        oldis_threshold_str = TimeUtils.wp_time_to_string(
            (current_tsecs - year_tsecs * 3))
        self.add_suppressed_argument(
            '--old_threshold', default=old_threshold_str)
        self.add_suppressed_argument(
            '--oldish_threshold', default=oldis_threshold_str)

    def add_update_options(self, update_group):
        """Add options pertaining to updating database."""

        group = update_group.add_mutually_exclusive_group()
        group.add_argument(
            '--update-subordinate',
            help='update the subordinate database',
            action="store_true")
        group.add_argument(
            '--skip-update-subordinate',
            help='don\'t update the subordinate database',
            action="store_false",
            dest='update_subordinate')

        group = update_group.add_mutually_exclusive_group()
        group.add_argument(
            '--do-problematic',
            help='make problematic updates to the databases',
            action="store_true")
        group.add_argument(
            '--skip-problematic',
            help='don\'t make problematic updates to the databases',
            action="store_false",
            dest='do_problematic')

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

        group = update_group.add_mutually_exclusive_group()
        group.add_argument(
            '--auto-create-new',
            help='automatically create new items if they don\'t exist yet',
            action="store_true")
        update_group.add_argument(
            '--skip-create-new',
            help='do not create new items, print which need to be created',
            action="store_false",
            dest="auto_create_new")

        group = update_group.add_mutually_exclusive_group()
        group.add_argument(
            '--auto-delete-old',
            help=('automatically delete old items if they don\'t exist any '
                  'more'),
            action="store_true")
        group.add_argument(
            '--skip-delete-old',
            help='do not delete old items, print which need to be deleted',
            action="store_false",
            dest="auto_create_new")

    def add_report_options(self, report_group):
        group = report_group.add_mutually_exclusive_group()
        group.add_argument(
            '--do-report', help='generate report files', action="store_true")
        group.add_argument(
            '--skip-report',
            help='don\'t generate report files',
            action="store_false",
            dest='do_report')
        group = report_group.add_mutually_exclusive_group()
        group.add_argument(
            '--print-report',
            help='pirnt report in terminal',
            action="store_true")
        group.add_argument(
            '--skip-print-report',
            help='don\'t print report in terminal',
            action="store_false",
            dest='print_report')
        report_group.add_argument(
            '--report-and-quit',
            help='quit after generating report',
            action="store_true",
            default=False)
        report_group.add_argument(
            '--report-sanitation',
            help='Add sanitation information to report',
            default=False,
            action='store_true')
        report_group.add_argument(
            '--report-duplicates',
            help='Add duplicates information to report',
            default=False,
            action='store_true')
        report_group.add_argument(
            '--report-matching',
            help='Add matching information to report',
            default=False,
            action='store_true')
        group = report_group.add_mutually_exclusive_group()
        group.add_argument(
            '--do-mail',
            help='email summary of actions upon completion',
            action="store_true",
            default=False)
        group.add_argument(
            '--skip-mail',
            help='don\'t email summary',
            action="store_false",
            dest='do_mail')

    def add_client_options(self, client_group):
        self.add_suppressed_argument('--wp-user', type=str)
        self.add_suppressed_argument('--wp-pass', type=str)
        self.add_suppressed_argument('--wp-callback', type=str)
        self.add_suppressed_argument('--wp-api-key', type=str)
        self.add_suppressed_argument('--wp-api-secret', type=str)
        self.add_suppressed_argument('--wp-api-version', type=str)
        self.add_suppressed_argument('--wp-creds-store', type=str)
        self.add_suppressed_argument('--wc-api-key', type=str)
        self.add_suppressed_argument('--wc-api-secret', type=str)
        self.add_suppressed_argument('--wc-api-version', type=str)
        self.add_suppressed_argument('--wc-api-namespace', type=str)
        self.add_suppressed_argument('--wc-api-basic-auth', type=bool)
        self.add_suppressed_argument('--wc-api-timeout', type=str, default=30)
        self.add_suppressed_argument('--wc-callback', type=str)
        self.add_suppressed_argument('--wc-creds-store', type=str)
        self.add_suppressed_argument('--store-url', type=str)
        self.add_suppressed_argument('--mail-type', type=str)
        self.add_suppressed_argument('--mail-host', type=str)
        self.add_suppressed_argument('--mail-port', type=int)
        self.add_suppressed_argument('--mail-user', type=str)
        self.add_suppressed_argument('--mail-pass', type=str)
        self.add_suppressed_argument('--mail-sender', type=str)
        self.add_suppressed_argument('--mail-recipients', type=str, nargs='*')

    def add_other_options(self):
        self.add_suppressed_argument('--main-name')
        self.add_suppressed_argument('--subordinate-name')
        self.add_argument(
            '--main-file', help='location of local main data file')
        self.add_argument(
            '--subordinate-file', help='location of local subordinate data file')
        self.add_argument('--pickle-file', help='location of saved state file')
        self.add_argument(
            '--override-progress', help='override progress of saved state')

        self.add_suppressed_argument('--main-dialect-suggestion')
        self.add_suppressed_argument('--web-dir')
        self.add_suppressed_argument('--web-address')
        self.add_suppressed_argument('--web-browser')

    def add_debug_options(self):
        self.add_suppressed_argument('--debug-abstract', action='store_true')
        self.add_suppressed_argument('--debug-parser', action='store_true')
        self.add_suppressed_argument('--debug-self', action='store_true')
        self.add_suppressed_argument('--debug-client', action='store_true')
        self.add_suppressed_argument('--debug-utils', action='store_true')
        self.add_suppressed_argument('--debug-gen', action='store_true')
        self.add_suppressed_argument('--debug-myo', action='store_true')
        self.add_suppressed_argument('--debug-tree', action='store_true')
        self.add_suppressed_argument('--debug-woo', action='store_true')
        self.add_suppressed_argument('--debug-img', action='store_true')
        self.add_suppressed_argument('--debug-api', action='store_true')
        self.add_suppressed_argument('--debug-shop', action='store_true')
        self.add_suppressed_argument('--debug-update', action='store_true')
        self.add_suppressed_argument('--debug-mro', action='store_true')
        self.add_suppressed_argument('--debug-gdrive', action='store_true')
        self.add_suppressed_argument('--debug-special', action='store_true')
        self.add_suppressed_argument('--debug-cats', action='store_true')
        self.add_suppressed_argument('--debug-vars', action='store_true')
        self.add_suppressed_argument('--debug-contact', action='store_true')
        self.add_suppressed_argument('--debug-address', action='store_true')
        self.add_suppressed_argument('--debug-name', action='store_true')
        self.add_suppressed_argument('--debug-duplicates', action='store_true')
        self.add_suppressed_argument(
            '--debug-trace', action='store_true', default=False)
        self.add_suppressed_argument('--debug-usr', action='store_true')


class ArgumentParserProd(ArgumentParserCommon):
    """Provide ArgumentParser class for product syncing."""

    proto_argparser = ArgumentParserProtoProd

    def __init__(self, **kwargs):
        kwargs['description'] = \
            'Synchronize product data from multiple remote sources'
        if not kwargs.get('extra_default_config_files'):
            kwargs['extra_default_config_files'] = [DEFAULTS_PROD_PATH]
        super(ArgumentParserProd, self).__init__(**kwargs)

    # def add_proto_options(self):
    #     super(ArgumentParserProd, self).add_proto_options()

    def add_download_options(self, download_group):
        super(ArgumentParserProd, self).add_download_options(download_group)
        download_group.add_argument(
            '--variant', help='what variant of schema to process the files')

    def add_processing_options(self, processing_group):
        super(ArgumentParserProd,
              self).add_processing_options(processing_group)

        self.add_suppressed_argument('--item-depth', type=int)
        self.add_suppressed_argument('--taxo-depth', type=int)

        group = processing_group.add_mutually_exclusive_group()
        group.add_argument(
            '--do-categories', help='sync categories', action="store_true")
        group.add_argument(
            '--skip-categories',
            help='don\'t sync categories',
            action="store_false",
            dest='do_categories')

        group = processing_group.add_mutually_exclusive_group()
        group.add_argument(
            '--do-variations', help='sync variations', action="store_true")
        group.add_argument(
            '--skip-variations',
            help='don\'t sync variations',
            action="store_false",
            dest='do_variations')

        group = processing_group.add_mutually_exclusive_group()
        group.add_argument(
            '--do-attributes',
            help='sync attributes',
            action="store_true",
            default=True,
        )
        group.add_argument(
            '--skip-attributes',
            help='don\'t sync attributes',
            action="store_false",
            dest='do_attributes')

        images_group = self.add_argument_group('Image options')
        group = images_group.add_mutually_exclusive_group()
        group.add_argument(
            '--do-images', help='process images', action="store_true")
        group.add_argument(
            '--skip-images',
            help='don\'t process images',
            action="store_false",
            dest='do_images')
        group = images_group.add_mutually_exclusive_group()
        group.add_argument(
            '--do-delete-images',
            help='delete extra images in compressed dir',
            action="store_true")
        group.add_argument(
            '--skip-delete-images',
            help='protect images from deletion',
            action="store_false",
            dest='do_delete_images')
        group = images_group.add_mutually_exclusive_group()
        group.add_argument(
            '--do-resize-images',
            help='resize images in compressed dir',
            action="store_true")
        group.add_argument(
            '--skip-resize-images',
            help='protect images from resizing',
            action="store_false",
            dest='do_resize_images')
        group = images_group.add_mutually_exclusive_group()
        group.add_argument(
            '--do-remeta-images',
            help='remeta images in compressed dir',
            action="store_true")
        group.add_argument(
            '--skip-remeta-images',
            help='protect images from resizing',
            action="store_false",
            dest='do_remeta_images')
        images_group.add_argument(
            '--require-images',
            help=('require that all items have images and that all images '
                  'exist'),
            type=ast.literal_eval,
            default=True)
        images_group.add_argument(
            '--img-raw-dir',
            help='location of raw images',
            type=text_type,
            default=DEFAULT_LOCAL_IMG_RAW_DIR)
        images_group.add_argument(
            '--img-raw-extra-dir',
            type=text_type,
            help='location of additional raw images')
        images_group.add_argument(
            '--img-cmp-dir',
            help='location of compressed images',
            default=DEFAULT_LOCAL_IMG_RAW_DIR)
        images_group.add_argument(
            '--thumbsize-x', help='X value of thumbnail crop size', type=int)
        images_group.add_argument(
            '--thumbsize-y', help='Y value of thumbnail crop size')
        group = images_group.add_mutually_exclusive_group()
        group.add_argument(
            '--skip-unattached-images',
            help="process only images which are attached to api objects",
            action="store_true",
            default=True)
        group.add_argument(
            '--do-unattached-images',
            help=("process all images including those which aren't attached "
                  "to parser objects"),
            dest='skip_unattached_images',
            action="store_false",
        )

        specials_group = self.add_argument_group('Specials options')
        group = specials_group.add_mutually_exclusive_group()
        group.add_argument(
            '--do-specials', help='process specials', action="store_true")
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
            '--skip-special-categories',
            help="don't create new special category groups",
            action='store_true')
        specials_group.add_argument(
            '--current-special', help='prefix of current special code')
        specials_group.add_argument(
            '--specials-file', help='location of specials file')

        group = self.add_mutually_exclusive_group()
        group.add_argument(
            '--do-dyns',
            help='process dynamic pricing rules',
            action="store_true")
        group.add_argument(
            '--skip-dyns',
            help='don\'t process dynamic pricing rules',
            action="store_false",
            dest='do_dyns')

    def add_update_options(self, update_group):
        super(ArgumentParserProd, self).add_update_options(update_group)
        update_group.add_argument(
            '--subordinate-limit', help='limit per page when using the subordinate api')
        update_group.add_argument(
            '--subordinate-offset',
            help='offset when using the subordinate api (for debugging)')

    def add_report_options(self, report_group):
        super(ArgumentParserProd, self).add_report_options(report_group)
        report_group.add_argument(
            '--report-matched-categories',
            help=('generating CSV file of categories with their corresponding '
                  'term_ids'),
            action="store_true",
            default=False)
        report_group.add_argument(
            '--report-matched-products',
            help=('generating CSV file of products with their corresponding '
                  'IDs'),
            action="store_true",
            default=False)

    def add_other_options(self):
        super(ArgumentParserProd, self).add_other_options()
        self.add_suppressed_argument('--myo-schemas', nargs='+')
        self.add_suppressed_argument('--xero-schemas', nargs='+')
        self.add_suppressed_argument('--woo-schemas', nargs='+')
        self.add_suppressed_argument('--subordinate-cat-file')

    def add_client_options(self, client_group):
        super(ArgumentParserProd, self).add_client_options(client_group)
        self.add_suppressed_argument('--gdrive-scopes')
        self.add_suppressed_argument('--gdrive-client-secret-file')
        self.add_suppressed_argument('--gdrive-app-name')
        self.add_suppressed_argument('--gdrive-oauth-client-id')
        self.add_suppressed_argument('--gdrive-oauth-client-secret')
        self.add_suppressed_argument(
            '--gdrive-credentials-dir', default='~/.credentials')
        self.add_suppressed_argument(
            '--gdrive-credentials-file', default='drive-woogenerator.json')
        self.add_suppressed_argument('--gen-fid')
        self.add_suppressed_argument('--gen-gid')
        self.add_suppressed_argument('--dprc-gid')
        self.add_suppressed_argument('--dprp-gid')
        self.add_suppressed_argument('--spec-gid')
        self.add_suppressed_argument('--us-gid')
        self.add_suppressed_argument('--xs-gid')
        self.add_suppressed_argument('--ssh-user')
        self.add_suppressed_argument('--ssh-pass')
        self.add_suppressed_argument('--ssh-host')
        self.add_suppressed_argument('--ssh-port')
        self.add_suppressed_argument('--remote-bind-host')
        self.add_suppressed_argument('--remote-bind-port')
        self.add_suppressed_argument('--db-user')
        self.add_suppressed_argument('--db-pass')
        self.add_suppressed_argument('--db-name')
        self.add_suppressed_argument('--tbl-prefix')

        self.add_suppressed_argument('--xero-consumer-key')
        self.add_suppressed_argument('--xero-consumer-secret')
        self.add_suppressed_argument('--xero-private-key-file')
        self.add_suppressed_argument('--xero-api-endpoint-url')


class ArgumentParserUser(ArgumentParserCommon):
    """Provide ArgumentParser class for syncing contacts."""

    proto_argparser = ArgumentParserProtoUser

    def __init__(self, **kwargs):
        kwargs['description'] = \
            'Merge contact records between two databases'
        if not kwargs.get('extra_default_config_files'):
            kwargs['extra_default_config_files'] = [DEFAULTS_USER_PATH]
        super(ArgumentParserUser, self).__init__(**kwargs)

    def add_download_options(self, download_group):
        super(ArgumentParserUser, self).add_download_options(download_group)

        filter_group = self.add_argument_group("Filter Options")
        group = filter_group.add_mutually_exclusive_group()
        group.add_argument(
            '--do-filter', help='filter the databases', action="store_true")
        group.add_argument(
            '--skip-filter',
            help='don\'t filter the databases',
            action="store_false",
            dest='do_filter')
        filter_group.add_argument(
            '--card-file', help='file containing list of card IDs to filer on')
        filter_group.add_argument(
            '--email-file',
            help='file containing list of emails to filer on (one per line)')
        filter_group.add_argument(
            '--filter-emails', help='list of emails to filer on')
        filter_group.add_argument(
            '--filter-cards', help='list of cards to filer on')
        filter_group.add_argument(
            '--ignore-cards', help='list of cards to ignore')
        filter_group.add_argument(
            '--since-m',
            help='filter out main records edited before this date')

    def add_processing_options(self, processing_group):
        super(ArgumentParserUser,
              self).add_processing_options(processing_group)
        group = processing_group.add_mutually_exclusive_group()
        group.add_argument(
            '--do-post', help='post process the contacts', action="store_true")
        group.add_argument(
            '--skip-post',
            help='don\'t post process the contacts',
            action="store_false",
            dest='do_post')
        processing_group.add_argument(
            '--reflect-only',
            help="report only changes do to reflection, not syncing",
            default=False,
            action="store_true")

    def add_update_options(self, update_group):
        super(ArgumentParserUser, self).add_update_options(update_group)
        group = update_group.add_mutually_exclusive_group()
        group.add_argument(
            '--update-main',
            help='update the main database',
            action="store_true")
        group.add_argument(
            '--skip-update-main',
            help='don\'t update the main database',
            action="store_false",
            dest='update_main')

    def add_client_options(self, client_group):
        super(ArgumentParserUser, self).add_client_options(client_group)

        self.add_suppressed_argument('--ssh-user', type=str)
        self.add_suppressed_argument('--ssh-pass', type=str)
        self.add_suppressed_argument('--ssh-host', type=str)
        self.add_suppressed_argument('--ssh-port', type=int, default=22)
        self.add_suppressed_argument('--remote-bind-host', type=str)
        self.add_suppressed_argument('--remote-bind-port', type=int)
        self.add_suppressed_argument('--db-host', type=str)
        self.add_suppressed_argument('--db-user', type=str)
        self.add_suppressed_argument('--db-pass', type=str)
        self.add_suppressed_argument('--db-name', type=str)
        self.add_suppressed_argument('--db-charset', type=str)
        self.add_suppressed_argument('--tbl-prefix', type=str)

        self.add_suppressed_argument('--m-ssh-user', type=str)
        self.add_suppressed_argument('--m-ssh-pass', type=str)
        self.add_suppressed_argument(
            '--m-ssh-host', help='location of main ssh server')
        self.add_suppressed_argument(
            '--m-ssh-port', type=int, help='main ssh port')
        self.add_suppressed_argument('--remote-export-dir', type=str)
        self.add_suppressed_argument('--m-x-cmd', type=str)
        self.add_suppressed_argument('--m-i-cmd', type=str)
        self.add_suppressed_argument('--m-db-user', type=str)
        self.add_suppressed_argument('--m-db-pass', type=str)
        self.add_suppressed_argument('--m-db-name', type=str)
        self.add_suppressed_argument('--m-db-host', type=str)
