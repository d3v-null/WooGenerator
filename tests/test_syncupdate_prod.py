

from context import woogenerator
from test_syncupdate import TestSyncUpdateAbstract
from woogenerator.conf.parser import ArgumentParserProd
from woogenerator.namespace.prod import SettingsNamespaceProd

# from woogenerator.contact_objects import ...

class TestSyncUpdateProdAbstract(TestSyncUpdateAbstract):
    config_file = "generator_config_test.yaml"
    settings_namespace_class = SettingsNamespaceProd
    argument_parser_class = ArgumentParserProd
