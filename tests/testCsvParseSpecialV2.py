import os
from unittest import TestCase, main, skip, TestSuite, TextTestRunner

from context import source
from source.coldata import ColData_Woo
from source.csvparse_special import CSVParse_Special, SpecialGruopList, SpecialRuleList
from source.utils import SanitationUtils, Registrar

from context import get_testdata, tests_datadir

class TestCSVParseSpecialV2(TestCase):
    def setUp(self):
        # importName = TimeUtils.getMsTimeStamp()

        self.specPath = os.path.join(tests_datadir, "specials_v2.csv")

        self.specialParserArgs = {
            # 'importName':importName
        }

        Registrar.DEBUG_MESSAGE = True

    def test_basic(self):
        specialParser = CSVParse_Special(
            **self.specialParserArgs
        )

        # Registrar.DEBUG_PARSER = True
        # Registrar.DEBUG_SPECIAL = True

        specialParser.analyseFile(self.specPath)

        print "number of special groups: %s" % len(specialParser.ruleGroups)
        print "number of special rules: %s" % len(specialParser.rules)
        print specialParser.tabulate(tablefmt="simple")

        # check that loner has correct ending
        isSingularChild = False
        for index, special in specialParser.ruleGroups.items():
            if len(special.children) == 1:
                isSingularChild = True
                child = special.children[0]
                self.assertEqual(index, child.index)
        self.assertTrue(isSingularChild)


if __name__ == '__main__':
    main()
