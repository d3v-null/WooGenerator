from context import woogenerator
from woogenerator.coldata import ColDataProd
from woogenerator.conf.parser import ArgumentParserProd
from woogenerator.namespace.core import SettingsNamespaceProd
from test_syncupdate import TestSyncUpdateAbstract

# from woogenerator.contact_objects import ...

class TestSyncUpdateProdAbstract(TestSyncUpdateAbstract):
    config_file = "generator_config_test.yaml"
    settings_namespace_class = SettingsNamespaceProd
    argument_parser_class = ArgumentParserProd
