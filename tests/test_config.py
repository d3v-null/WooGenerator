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


if __name__ == '__main__':
    unittest.main()
