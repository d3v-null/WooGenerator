import os
import time
from unittest import TestCase, main, skip, TestSuite, TextTestRunner

from context import woogenerator
from context import get_testdata, tests_datadir
from woogenerator.coldata import ColData_Woo
from woogenerator.parsing.special import CSVParse_Special, SpecialGruopList, SpecialRuleList
from woogenerator.utils import SanitationUtils, Registrar, TimeUtils


class TestCSVParseSpecialV2(TestCase):

    def setUp(self):
        # importName = TimeUtils.get_ms_timestamp()

        self.specPath = os.path.join(tests_datadir, "specials_v2.csv")

        self.specialParserArgs = {
            # 'importName':importName
        }

        # Registrar.DEBUG_MESSAGE = True

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

    def test_has_happened_yet(self):
        specialParser = CSVParse_Special(
            **self.specialParserArgs
        )

        specialParser.analyseFile(self.specPath)

        Registrar.DEBUG_SPECIAL = True
        Registrar.DEBUG_MESSAGE = True

        TimeUtils.set_override_time(time.strptime(
            "2018-01-01", TimeUtils.dateFormat))

        eofySpecial = specialParser.ruleGroups.get('EOFY2016')
        # print "start time", eofySpecial.start_time
        # print "override", TimeUtils.current_tsecs()
        self.assertLess(eofySpecial.start_time, TimeUtils.current_tsecs())
        self.assertTrue(eofySpecial.hasStarted)
        self.assertTrue(eofySpecial.hasFinished)
        self.assertFalse(eofySpecial.isActive)

    def test_determine_groups(self):
        specialParser = CSVParse_Special(
            **self.specialParserArgs
        )

        specialParser.analyseFile(self.specPath)

        # Registrar.DEBUG_SPECIAL = True
        # Registrar.DEBUG_MESSAGE = True

        overrideGroups = specialParser.determine_current_special_groups(
            'override',
            'EOFY2016'
        )
        self.assertEquals(
            overrideGroups, [specialParser.ruleGroups.get('EOFY2016')])

        TimeUtils.set_override_time(time.strptime(
            "2018-01-01", TimeUtils.dateFormat))

        autoNextGroups = specialParser.determine_current_special_groups(
            'auto_next'
        )
        self.assertEquals(autoNextGroups, [])

        TimeUtils.set_override_time(time.strptime(
            "2016-08-11", TimeUtils.dateFormat))

        autoNextGroups = specialParser.determine_current_special_groups(
            'auto_next'
        )
        self.assertEquals(
            autoNextGroups, [specialParser.ruleGroups.get('SP2016-08-12')])

        TimeUtils.set_override_time(time.strptime(
            "2016-06-11", TimeUtils.dateFormat))

        autoNextGroups = specialParser.determine_current_special_groups(
            'auto_next'
        )
        self.assertEquals(
            autoNextGroups, [specialParser.ruleGroups.get('EOFY2016')])

        TimeUtils.set_override_time(time.strptime(
            "2016-06-13", TimeUtils.dateFormat))

        autoNextGroups = specialParser.determine_current_special_groups(
            'auto_next'
        )
        self.assertEquals(
            autoNextGroups, [specialParser.ruleGroups.get('EOFY2016')])


if __name__ == '__main__':
    main()
