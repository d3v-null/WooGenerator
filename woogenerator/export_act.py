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


def download_main(settings):
    """Populate the parsers for data from the subordinate database."""

    Registrar.register_message(
        "main_parser_args:\n%s" %
        pformat(settings.main_parser_args)
    )

    Registrar.register_progress("analysing main user data")

    main_client_class = settings.main_download_client_class
    main_client_args = settings.main_download_client_args
    with main_client_class(**main_client_args) as client:
        client.export_remote(
            data_path=settings.main_path,
            since=settings.since_m
        )
        Registrar.register_message(
            "exported ACT data to %s" % settings.main_path
        )


def main(override_args=None, settings=None):
    """Use settings object to load config file and detect changes in wordpress."""
    if not settings:
        settings = SettingsNamespaceUser()
    settings.init_settings(override_args)
    settings.download_main = True
    settings.init_dirs()

    download_main(settings)


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
