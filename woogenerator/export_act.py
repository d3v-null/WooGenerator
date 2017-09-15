"""
Module for exporting ACT databases.
Much quicker than waiting for merger to analyse file.
"""

from __future__ import absolute_import

import os
import sys
import traceback
from pprint import pformat

from httplib2 import ServerNotFoundError
from requests.exceptions import ConnectionError, ConnectTimeout, ReadTimeout

from .namespace.user import SettingsNamespaceUser
from .utils import Registrar


def download_master(settings):
    """Populate the parsers for data from the slave database."""

    Registrar.register_message(
        "master_parser_args:\n%s" %
        pformat(settings.master_parser_args)
    )

    Registrar.register_progress("analysing master user data")

    master_client_class = settings.master_download_client_class
    master_client_args = settings.master_download_client_args
    with master_client_class(**master_client_args) as client:
        client.export_remote(
            data_path=settings.master_path,
            since=settings.since_m
        )
        Registrar.register_message(
            "exported ACT data to %s" % settings.master_path
        )


def main(override_args=None, settings=None):
    """Use settings object to load config file and detect changes in wordpress."""
    if not settings:
        settings = SettingsNamespaceUser()
    settings.init_settings(override_args)
    settings.download_master = True
    settings.init_dirs()

    download_master(settings)


def catch_main(override_args=None):
    """Run the main function within a try statement and attempt to analyse failure."""
    settings = SettingsNamespaceUser()
    status = 0

    try:
        main(settings=settings, override_args=override_args)
    except (SystemExit, KeyboardInterrupt):
        pass
    except (ReadTimeout, ConnectionError, ConnectTimeout, ServerNotFoundError):
        status = 69  # service unavailable
    except IOError:
        status = 74
        print "IOError. cwd: %s" % os.getcwd()
    except UserWarning:
        status = 65
    except Exception:
        status = 1
    finally:
        if status:
            Registrar.register_error(traceback.format_exc())
            if Registrar.DEBUG_TRACE:
                import pudb
                pudb.set_trace()

    sys.exit(status)


if __name__ == '__main__':
    catch_main()
