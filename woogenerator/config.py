"""
Provide configuration utilities.
"""
import os
# import sys

import argparse
import configargparse

from __init__ import MODULE_LOCATION

CONF_DIR = os.path.join(MODULE_LOCATION, 'conf')
DEFAULTS_COMMON_PATH = os.path.join(CONF_DIR, 'defaults_common.yaml')
DEFAULTS_PROD_PATH = os.path.join(CONF_DIR, 'defaults_prod.yaml')
DEFAULTS_USER_PATH = os.path.join(CONF_DIR, 'defaults_user.yaml')

LOCAL_WORK_DIR = os.path.expanduser('~/woogenerator')
LOCAL_PROD_PATH = os.path.join(LOCAL_WORK_DIR, 'conf_prod.yaml')
LOCAL_PROD_TEST_PATH = os.path.join(LOCAL_WORK_DIR, 'conf_prod.yaml')
LOCAL_USER_PATH = os.path.join(LOCAL_WORK_DIR, 'conf_user.yaml')
LOCAL_USER_TEST_PATH = os.path.join(LOCAL_WORK_DIR, 'conf_user.yaml')
DEFAULT_LOCAL_IN_DIR = os.path.join(LOCAL_WORK_DIR, 'input/')
DEFAULT_LOCAL_OUT_DIR = os.path.join(LOCAL_WORK_DIR, 'output/')
DEFAULT_LOCAL_LOG_DIR = os.path.join(LOCAL_WORK_DIR, 'log/')
DEFAULT_LOCAL_IMG_RAW_DIR = os.path.join(LOCAL_WORK_DIR, 'imgs_raw/')
DEFAULT_LOCAL_IMG_CMP_DIR = os.path.join(LOCAL_WORK_DIR, 'imgs_cmp/')


class ArgumentParserCommon(configargparse.ArgumentParser):
    """
    Provide ArgumentParser superclass for product and user sync.
    """

    def __init__(self, **kwargs):
        # set common defaults

        if not isinstance(kwargs.get('default_config_files'), list):
            kwargs['default_config_files'] = [DEFAULTS_COMMON_PATH]
        else:
            if os.path.exists(DEFAULTS_COMMON_PATH):
                print "path exists: %s" % DEFAULTS_COMMON_PATH
                kwargs['default_config_files'].insert(0, DEFAULTS_COMMON_PATH)
            else:
                print "path not exists: %s " % DEFAULTS_COMMON_PATH

        if not kwargs.get('args_for_setting_config_path'):
            kwargs['args_for_setting_config_path'] = ['-c', '--config-file']

        if not kwargs.get('config_arg_help_message'):
            kwargs['config_arg_help_message'] = \
                "the location of your config file"

        if not kwargs.get('config_file_parser_class'):
            kwargs['config_file_parser_class'] = configargparse.YAMLConfigFileParser

        if not kwargs.get('ignore_unknown_config_file_keys'):
            kwargs['ignore_unknown_config_file_keys'] = True

        skip_local_config = kwargs.pop('skip_local_config', None)
        local_config = kwargs.pop('local_config', '')
        if local_config and not skip_local_config and os.path.exists(local_config):
            print "path exists: %s" % local_config
            kwargs['default_config_files'].append(local_config)
        else:
            print "path not exists: %s" % local_config

        super(ArgumentParserCommon, self).__init__(**kwargs)

        # add args
        self.add_global_options()
        download_group = self.add_argument_group('Import options')
        self.add_download_options(download_group)
        processing_group = self.add_argument_group('Processing options')
        self.add_processing_options(processing_group)
        reporting_group = self.add_argument_group('Reporting options')
        self.add_report_options(reporting_group)
        update_group = self.add_argument_group('Update options')
        self.add_update_options(update_group)
        self.add_other_options()
        self.add_debug_options()

    def add_default_config_file(self, config_file):
        if not config_file in self._default_config_files:
            self._default_config_files.append(config_file)

    def add_suppressed_argument(self, name, **kwargs):
        kwargs['help'] = argparse.SUPPRESS
        self.add_argument(name, **kwargs)

    def get_actions(self):
        return self._actions

    def add_global_options(self):
        """
        Add options to top of options list.
        """
        # TODO: refactor this when switch to logging

        group = self.add_mutually_exclusive_group()
        group.add_argument(
            "-v", "--verbosity", action="count", help="increase output verbosity")
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
        group.add_argument(
            '--in-folder',
            default=DEFAULT_LOCAL_IN_DIR,
        )
        group.add_argument(
            '--out-folder',
            default=DEFAULT_LOCAL_OUT_DIR,
        )
        group.add_argument(
            '--log-folder',
            default=DEFAULT_LOCAL_LOG_DIR,
        )


    def add_download_options(self, download_group):
        """
        Add options pertaining to downloading data.
        """

        group = download_group.add_mutually_exclusive_group()
        group.add_argument(
            '--download-master',
            help='download the master data',
            action="store_true")
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
            action="store_true")
        group.add_argument(
            '--skip-download-slave',
            help='use the local slave file instead of downloading the slave data',
            action="store_false",
            dest='download_slave')
        download_group.add_argument(
            '--download-limit',
            help='global limit of objects to download (for debugging)',
            type=int)

    def add_processing_options(self, processing_group):
        """
        Add options pertaining to processing data.
        """

        group = processing_group.add_mutually_exclusive_group()
        group.add_argument(
            '--do-sync',
            help='sync the databases',
            action="store_true")
        group.add_argument(
            '--skip-sync',
            help='don\'t sync the databases',
            action="store_false",
            dest='do_sync')

        # TODO: Figure out what the donk is with merge_mode
        processing_group.add_argument(
            '--merge-mode',
            choices=['sync', 'merge'],
            help=''
        )

        processing_group.add_argument(
            '--last-sync',
            help="When the last sync was run ('YYYY-MM-DD HH:MM:SS')"
        )


    def add_update_options(self, update_group):
        """
        Add options pertaining to updating database.
        """

        group = update_group.add_mutually_exclusive_group()
        group.add_argument(
            '--update-slave',
            help='update the slave database',
            action="store_true")
        group.add_argument(
            '--skip-update-slave',
            help='don\'t update the slave database',
            action="store_false",
            dest='update_slave')

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
            help='automatically delete old items if they don\'t exist any more',
            action="store_true")
        group.add_argument(
            '--skip-delete-old',
            help='do not delete old items, print which need to be deleted',
            action="store_false",
            dest="auto_create_new")

    def add_report_options(self, report_group):
        group = report_group.add_mutually_exclusive_group()
        group.add_argument(
            '--show-report',
            help='generate report files',
            action="store_true")
        group.add_argument(
            '--skip-report',
            help='don\'t generate report files',
            action="store_false",
            dest='show_report')
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
            default=False
        )

    def add_other_options(self):
        self.add_suppressed_argument('--master-name')
        self.add_suppressed_argument('--slave-name')
        self.add_argument('--master-file', help='location of local master data file')
        self.add_argument('--slave-file', help='location of local slave data file')

        self.add_suppressed_argument('--web-folder')
        self.add_suppressed_argument('--web-address')
        self.add_suppressed_argument('--web-browser')


    def add_debug_options(self):
        self.add_suppressed_argument('--debug-abstract', action='store_true')
        self.add_suppressed_argument('--debug-parser', action='store_true')
        self.add_suppressed_argument('--debug-self', action='store_true')
        self.add_suppressed_argument('--debug-flat', action='store_true')
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


class ArgumentParserProd(ArgumentParserCommon):
    """
    Provide ArgumentParser class for product syncing.
    """

    def __init__(self, **kwargs):
        kwargs['description'] = \
            'Synchronize product data from multiple remote sources'
        kwargs['default_config_files'] = [
            DEFAULTS_PROD_PATH,
        ]
        kwargs['local_config'] = LOCAL_PROD_PATH
        super(ArgumentParserProd, self).__init__(**kwargs)

    def add_global_options(self):
        super(ArgumentParserProd, self).add_global_options()
        # TODO: self.add_argument('--local-live-conf')

    def add_download_options(self, download_group):
        super(ArgumentParserProd, self).add_download_options(download_group)
        download_group.add_argument(
            '--schema',
            help='what schema to process the files as')
        download_group.add_argument(
            '--variant',
            help='what variant of schema to process the files')

        self.add_suppressed_argument('--gdrive-scopes')
        self.add_suppressed_argument('--gdrive-client-secret-file')
        self.add_suppressed_argument('--gdrive-app-name')
        self.add_suppressed_argument('--gdrive-oauth-client-id')
        self.add_suppressed_argument('--gdrive-oauth-client-secret')
        self.add_suppressed_argument('--gdrive-credentials-dir')
        self.add_suppressed_argument('--gdrive-credentials-file')
        self.add_suppressed_argument('--gen-fid')
        self.add_suppressed_argument('--gen-gid')
        self.add_suppressed_argument('--dprc-gid')
        self.add_suppressed_argument('--dprp-gid')
        self.add_suppressed_argument('--spec-gid')
        self.add_suppressed_argument('--us-gid')
        self.add_suppressed_argument('--xs-gid')
        self.add_suppressed_argument('--wc-api-key')
        self.add_suppressed_argument('--wc-api-secret')
        self.add_suppressed_argument('--store-url')
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

    def add_processing_options(self, processing_group):
        super(ArgumentParserProd, self).add_processing_options(processing_group)

        self.add_suppressed_argument('--item-depth', type=int)
        self.add_suppressed_argument('--taxo-depth', type=int)

        self.add_argument(
            '--wp-srv-offset',
            help="the offset in seconds of the wp server",
            type=int,
            default=0
        )

        group = processing_group.add_mutually_exclusive_group()
        group.add_argument(
            '--do-categories',
            help='sync categories',
            action="store_true")
        group.add_argument(
            '--skip-categories',
            help='don\'t sync categories',
            action="store_false",
            dest='do_categories')

        group = processing_group.add_mutually_exclusive_group()
        group.add_argument(
            '--do-variations',
            help='sync variations',
            action="store_true")
        group.add_argument(
            '--skip-variations',
            help='don\'t sync variations',
            action="store_false",
            dest='do_variations')

        images_group = self.add_argument_group('Image options')
        group = images_group.add_mutually_exclusive_group()
        group.add_argument(
            '--do-images',
            help='process images',
            action="store_true")
        group.add_argument(
            '--skip-images',
            help='don\'t process images',
            action="store_false",
            dest='do_images')
        group = images_group.add_mutually_exclusive_group()
        group.add_argument(
            '--do-delete-images',
            help='delete extra images in compressed folder',
            action="store_true")
        group.add_argument(
            '--skip-delete-images',
            help='protect images from deletion',
            action="store_false",
            dest='do_delete_images')
        group = images_group.add_mutually_exclusive_group()
        group.add_argument(
            '--do-resize-images',
            help='resize images in compressed folder',
            action="store_true")
        group.add_argument(
            '--skip-resize-images',
            help='protect images from resizing',
            action="store_false",
            dest='do_resize_images')
        group = images_group.add_mutually_exclusive_group()
        group.add_argument(
            '--do-remeta-images',
            help='remeta images in compressed folder',
            action="store_true")
        group.add_argument(
            '--skip-remeta-images',
            help='protect images from resizing',
            action="store_false",
            dest='do_remeta_images')
        images_group.add_argument(
            '--require-images',
            help='require that all items have images',
            default=True)
        images_group.add_argument(
            '--img-raw-folder',
            help='location of raw images',
            default=DEFAULT_LOCAL_IMG_RAW_DIR
        )
        self.add_suppressed_argument('--img-raw-folders', default=[])
        images_group.add_argument(
            '--img-raw-extra-folder',
            help='location of additional raw images')
        images_group.add_argument(
            '--img-cmp-folder',
            help='location of compressed images',
            default=DEFAULT_LOCAL_IMG_RAW_DIR
        )

        specials_group = self.add_argument_group('Specials options')
        group = specials_group.add_mutually_exclusive_group()
        group.add_argument(
            '--do-specials',
            help='process specials',
            action="store_true")
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
            help='prefix of current special code')

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
            '--slave-timeout',
            help='timeout when using the slave api')
        update_group.add_argument(
            '--slave-limit',
            help='limit per page when using the slave api')
        update_group.add_argument(
            '--slave-offset',
            help='offset when using the slave api (for debugging)')

    def add_report_options(self, report_group):
        super(ArgumentParserProd, self).add_report_options(report_group)
        report_group.add_argument(
            '--exclude-cols',
            help='exclude these columns from the reports',
            default=[]
        )

    def add_other_options(self):
        super(ArgumentParserProd, self).add_other_options()
        self.add_suppressed_argument('--myo-schemas', nargs='+')
        self.add_suppressed_argument('--woo-schemas', nargs='+')

class ArgumentParserUser(ArgumentParserCommon):
    """
    Provide ArgumentParser class for syncing contacts.
    """
    def __init__(self, **kwargs):
        kwargs['description'] = \
            'Merge contact records between two databases'
        kwargs['default_config_files'] = [
            DEFAULTS_USER_PATH
        ]
        kwargs['local_config'] = LOCAL_USER_PATH
        super(ArgumentParserUser, self).__init__(**kwargs)

    def add_download_options(self, download_group):
        super(ArgumentParserUser, self).add_download_options(download_group)

    def add_processing_options(self, processing_group):
        super(ArgumentParserUser, self).add_processing_options(processing_group)
        group = processing_group.add_mutually_exclusive_group()
        group.add_argument(
            '--do-post',
            help='post process the contacts',
            action="store_true")
        group.add_argument(
            '--skip-post',
            help='don\'t post process the contacts',
            action="store_false",
            dest='do_post')
        processing_group.add_argument(
            '--process-duplicates',
            help="do extra processing to figure out duplicates",
            default=False,
            action="store_true")

    def add_update_options(self, update_group):
        group = update_group.add_mutually_exclusive_group()
        group.add_argument(
            '--update-master',
            help='update the master database',
            action="store_true")
        group.add_argument(
            '--skip-update-master',
            help='don\'t update the master database',
            action="store_false",
            dest='update_master')
        super(ArgumentParserUser, self).add_update_options(update_group)

    def add_other_options(self):
        filter_group = self.add_argument_group("Filter Options")
        group = filter_group.add_mutually_exclusive_group()
        group.add_argument(
            '--do-filter',
            help='filter the databases',
            action="store_true")
        group.add_argument(
            '--skip-filter',
            help='don\'t filter the databases',
            action="store_false",
            dest='do_filter')
        filter_group.add_argument(
            '--limit', type=int, help='global limit of objects to process')
        filter_group.add_argument(
            '--card-file',
            help='list of cards to filter on')

        self.add_argument('--m-ssh-host', help='location of master ssh server')
        self.add_argument(
            '--m-ssh-port', type=int, help='location of master ssh port')
