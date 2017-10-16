""" Provide configuration namespace for WC <-> Xero sync """

from __future__ import absolute_import

from ..client.prod import ProdSyncClientXero
from ..conf.parser import ArgumentParserProd
from .core import SettingsNamespaceProto

class SettingsNamespaceXero(SettingsNamespaceProto):
    argparser_class = ArgumentParserProd

    def __init__(self, *args, **kwargs):
        self.local_live_config = getattr(
            self, 'local_live_config', DEFAULT_LOCAL_PROD_PATH)
        self.local_test_config = getattr(
            self, 'local_test_config', DEFAULT_LOCAL_PROD_TEST_PATH)
        super(SettingsNamespaceXero, self).__init__(*args, **kwargs)

    @property
    def file_prefix(self):
        return "xero_"

    @property
    def col_data_class(self):
        return
