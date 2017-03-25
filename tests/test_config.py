import os
import re
from collections import OrderedDict
import unittest
import configargparse
from pprint import pformat

from context import tests_datadir
from woogenerator.config import ArgumentParserUser, ArgumentParserProd
# import woogenerator.config as config
# from woogenerator import config

class TestConfigProd(unittest.TestCase):
    def test_basic(self):
        parser = ArgumentParserProd()
        # pylint: disable=protected-access
        self.assertIsInstance(
            parser._config_file_parser, configargparse.YAMLConfigFileParser)

    def test_read_config(self):
        parser = ArgumentParserProd(skip_local_config=True)
        args = parser.parse_args()
        print "args: %s" % pformat(vars(args))
        known_args = parser.parse_known_args()
        print "known args: \n%s\n%s" % (pformat(vars(known_args[0])), pformat(known_args[1]))
        self.assertEqual(args.master_name, "MASTER")
        self.assertEqual(args.schema, "WC")

    def test_override_config(self):
        parser = ArgumentParserProd()
        args = parser.parse_args(['--master-name', 'MASTER_OVERRIDE'])
        self.assertEqual(args.master_name, "MASTER_OVERRIDE")

    def test_config_stages(self):
        # TODO: complete this
        parser = configargparse.ArgParser(
            default_config_files=['sample_data/baseconfig.yaml'],
            config_file_parser_class=configargparse.YAMLConfigFileParser
        )
        parser.add('-c', '--my-config', required=True, is_config_file=True, help='config file path')
        parser.add('-o', '--my-other-config', is_config_file=True, help='other config file path')
        parser.add('--an-argument')

        arg_string = ("--my-config sample_data/overconfig.yaml "
                      "--my-other-config sample_data/otherconfig.yaml")
        options = parser.parse_args(args=arg_string.split())
        print "parsed options: %s" % pformat(vars(options))

    def test_testmode(self):
        """ test the logic of testmode, make sure configargparse detects test config """

if __name__ == '__main__':
    unittest.main()
