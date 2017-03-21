import os
import bleach
import re
# from phpserialize import dumps
from collections import OrderedDict
from copy import copy

from woogenerator.utils import listUtils, descriptorUtils, ValidationUtils, PHPUtils, SanitationUtils
from woogenerator.parsing.abstract import ObjList
from woogenerator.parsing.tree import CSVParse_Tree, ImportTreeItem, ImportTreeTaxo, ImportTreeObject


class ImportDynObject(ImportTreeObject):

    def isRuleLine(self): return False

    def validate(self):
        for key, validation in self.validations:
            assert callable(validation)
            if not validation(self.get(key)):
                raise UserWarning("%s could be be validated by %s" %
                                  (key, self.__class__.__name__))


class ImportDynRuleLine(ImportDynObject, ImportTreeItem):

    validations = {
        'Discount': ValidationUtils.isNotNone,
        'Discount Type': ValidationUtils.isContainedIn(['PDSC'])
    }

    discount = descriptorUtils.safeKeyProperty('Discount')
    discount_type = descriptorUtils.safeKeyProperty('Discount Type')

    def __init__(self, *args, **kwargs):
        super(ImportDynRuleLine, self).__init__(*args, **kwargs)

        if all([
            self.get('Min ( Buy )') is None,
            self.get('Max ( Receive )') is None
        ]):
            raise UserWarning(
                "one of buy or receiver must be visible to ImportDynObject")

    def isRuleLine(self): return True

    @property
    def pricing_rule_disc_type(self):
        return {
            'PDSC': 'percentage_discount'
        }.get(self.discount_type)

    @property
    def pricing_rule_from(self):
        return self.get('Min ( Buy )', '')

    @property
    def pricing_rule_to(self):
        return self.get('Max ( Receive )', '')


class ImportDynRule(ImportDynObject, ImportTreeTaxo):

    validations = {
        'ID': ValidationUtils.isNotNone,
        'Qty. Base': ValidationUtils.isContainedIn(['PROD', 'VAR', 'CAT']),
        'Rule Mode': ValidationUtils.isContainedIn(['BULK', 'SPECIAL']),
        'Roles': ValidationUtils.isNotNone
    }

    qty_base = descriptorUtils.safeKeyProperty('Qty. Base')
    rule_mode = descriptorUtils.safeKeyProperty('Rule Mode')
    roles = descriptorUtils.safeKeyProperty('Roles')

    def __init__(self, *args, **kwargs):
        super(ImportDynRule, self).__init__(*args, **kwargs)
        self.ruleLines = []
        assert self.ID

    ID = descriptorUtils.safeKeyProperty('ID')

    @property
    def index(self): return self.ID

    @property
    def pricing_rule_collector(self):
        collector_type = {
            'PROD': 'product'
        }.get(self.qty_base, 'product')
        assert collector_type, self.qty_base
        return {'type': collector_type}

    @property
    def pricing_rule_conditions(self):
        roles = map(unicode.lower, self.roles.split('|'))
        return {
            1: {
                'args': {
                    'applies_to': 'roles',
                    'roles': roles
                },
                'type': 'apply_to'
            }
        }

    # def addRuleData(self, ruleData):
    #     self.ruleData = ruleData

    # def addLineData(self, ruleLineData):
    #     if ruleLineData:
    #         self['children'].append(ruleLineData)

    # def registerRuleLine(self, lineData):
    #     # assert isinstance(lineData, ImportDynObject)
    #     assert lineData.isRuleLine()
    #     self.registerAnything(
    #         lineData,
    #         self.getRuleLines()
    #     )

    def getRuleLines(self):
        # return self.ruleLines
        return self.getChildren()

    def getColNames(self):
        ruleMode = self.get('Rule Mode', 'BULK')
        if ruleMode == 'BULK' or not ruleMode:
            return OrderedDict([
                ('Min ( Buy )', 'From'),
                ('Max ( Receive )', 'To'),
                ('Discount', 'Discount'),
                ('Meaning', 'Meaning')
            ])
        else:
            return OrderedDict([
                ('Min ( Buy )', 'Buy'),
                ('Max ( Receive )', 'Receive'),
                ('Discount', 'Discount'),
                ('Meaning', 'Meaning)')
            ])

    def __repr__(self):
        rep = "<ImportDynRule | "
        rep += ', '.join(
            map(
                lambda x: str((x, self.get(x, ''))),
                ['Qty. Base', 'Rule Mode', 'Roles']
            )
        )
        if self.getRuleLines():
            rep += ' | '
            rep += ', '.join([line.get('Meaning', '')
                              for line in self.getRuleLines()])
        rep += ' >'
        return rep

    def to_pricing_rule(self):
        # defaults (empty rules)
        empty_blockrule = OrderedDict([
            ('adjust', ''),
            ('amount', ''),
            ('from', ''),
            ('repeating', 'no'),
            ('type', 'fixed_adjustment')
        ])
        empty_rule = OrderedDict([
            ('amount', ''),
            ('from', ''),
            ('to', ''),
            ('type', 'price_discount')
        ])

        if(self.rule_mode == 'BULK'):
            mode = 'continuous'
            blockRules = {
                1: empty_blockrule
            }
            rules = {}
            for i, ruleLine in enumerate(self.getRuleLines()):
                rule = copy(empty_rule)
                rule['from'] = ruleLine.pricing_rule_from
                rule['to'] = ruleLine.pricing_rule_to
                rule['amount'] = ruleLine.discount
                rule['type'] = ruleLine.pricing_rule_disc_type
                rules[i + 1] = rule
        else:
            mode = 'block'
            rules = {
                1: empty_rule
            }
            blockRules = {}
            for i, blockRuleLine in enumerate(self.getRuleLines()):
                blockRule = copy(empty_blockrule)
                blockRule['from'] = blockRuleLine.pricing_rule_from
                blockRule['to'] = blockRuleLine.pricing_rule_to
                blockRule['amount'] = blockRuleLine.discount
                blockRule['type'] = blockRuleLine.pricing_rule_disc_type
                blockRules[i + 1] = blockRule

        pricing_rule = OrderedDict([
            ('conditions_type', 'all'),
            ('conditions', self.pricing_rule_conditions),
            ('collector', self.pricing_rule_collector),
            ('mode', mode),
            ('date_from', ''),
            ('date_to', ''),
            ('rules', rules),
            ('blockrules', blockRules),
        ])

        return PHPUtils.serialize(pricing_rule)

    def toHTML(self):
        colNames = self.getColNames()

        html = u'<table class="shop_table lasercommerce pricing_table table table-striped">'
        html += '<thead><tr>'
        for col, name in colNames.items():
            colClass = SanitationUtils.sanitizeClass(col)
            html += '<th class=%s>' % colClass
            html += bleach.clean(name)
            html += '</th>'
        html += '</tr></thead>'
        ruleLines = self.getRuleLines()
        self.registerMessage("ruleLines: %s" % (ruleLines))
        for ruleLineData in ruleLines:
            lineType = ruleLineData.get('Discount Type', '')
            html += '<tr>'
            for col in colNames.keys():
                value = ruleLineData.get(col, '')
                if col == 'Discount' and lineType in ['PDSC']:
                    value += '%'
                html += '<td>'
                html += value  # bleach.clean(value)
                html += '</td>'
            html += '</tr>'
        html += "</table>"

        return html.encode('UTF-8')


class CSVParse_Dyn(CSVParse_Tree):

    itemContainer = ImportDynRuleLine
    taxoContainer = ImportDynRule
    objectContainer = ImportDynObject

    def __init__(self, cols=[], defaults={}):
        extra_cols = [
            'ID', 'Qty. Base', 'Rule Mode', 'Roles',
            'Min ( Buy )', 'Max ( Receive )', 'Discount Type', 'Discount', 'Repeating', 'Meaning']

        extra_defaults = {
            'Discount Type': 'PDSC',
            'Rule Mode': 'BULK'
        }

        cols = listUtils.combineLists(cols, extra_cols)
        defaults = listUtils.combineOrderedDicts(extra_defaults, defaults)
        super(CSVParse_Dyn, self).__init__(cols, defaults,
                                           taxoDepth=1, itemDepth=1, metaWidth=0)

        self.taxoIndexer = self.getObjectIndex

    # def clearTransients(self):
    #     super(CSVParse_Dyn, self).clearTransients()
    #     self.rules = {}

    # def getRuleData(self, itemData):
    #     ruleID = itemData['ID']
    #     assert ruleID, 'ruleID must exist to register rule'
    #     if not ruleID in self.rules.keys():
    #         self.rules[ruleID] = ImportDynRule(itemData)
    #     return self.rules[ruleID]

    # def registerRuleLine(self, parentData, itemData):
    #     ruleData = self.getRuleData(parentData)
    #     ruleData.addLineData(itemData)

    # def registerRule(self, itemData):
    #     ruleData = self.getRuleData(itemData)
    #     ruleData.addRuleData(itemData)
    #     print "registering rule ", itemData

    def depth(self, row):
        for i, cell in enumerate(row):
            if cell:
                if i < 4:
                    return 0
                else:
                    return 1
        return -1

    # def processItem(self, itemData):
    #     super(CSVParse_Dyn, self).processItem(itemData)
        # assert len(self.stack) > 1, "Item must have a parent since taxoDepth = 1"
        # parentData = self.stack[-2]
        # self.registerRuleLine(parentData, itemData)

    # def processTaxo(self, itemData):
    #     super(CSVParse_Dyn, self).processTaxo(itemData)
    #     self.registerRule(itemData)

    # def analyseRow(self, row, itemData):
    #     itemData = super(CSVParse_Dyn, self).analyseRow(row, itemData)
    #     if isRuleLine


if __name__ == '__main__':
    inFolder = "../input/"
    dprcPath = os.path.join(inFolder, 'DPRC.csv')
    dprpPath = os.path.join(inFolder, 'DPRP.csv')
    outFolder = "../output/"
    out_path = os.path.join(outFolder, 'dynRules.html')

    dynParser = CSVParse_Dyn()
    dynParser.analyseFile(dprpPath)

    # todo: rewrite in htmlReporter

    with open(out_path, 'w+') as out_file:
        def writeSection(title, description, data, length=0, html_class="results_section"):
            sectionID = SanitationUtils.makeSafeClass(title)
            description = "%s %s" % (
                str(length) if length else "No", description)
            out_file.write('<div class="%s">' % html_class)
            out_file.write('<a data-toggle="collapse" href="#%s" aria-expanded="true" data-target="#%s" aria-controls="%s">' %
                           (sectionID, sectionID, sectionID))
            out_file.write('<h2>%s (%d)</h2>' % (title, length))
            out_file.write('</a>')
            out_file.write('<div class="collapse" id="%s">' % sectionID)
            out_file.write('<p class="description">%s</p>' % description)
            out_file.write('<p class="data">')
            out_file.write(
                re.sub("<table>", "<table class=\"table table-striped\">", data))
            out_file.write('</p>')
            out_file.write('</div>')
            out_file.write('</div>')
        out_file.write('<!DOCTYPE html>')
        out_file.write('<html lang="en">')
        out_file.write('<head>')
        out_file.write("""
    <!-- Latest compiled and minified CSS -->
    <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.6/css/bootstrap.min.css" integrity="sha384-1q8mTJOASx8j1Au+a5WDVnPi2lkFfwwEAa8hDDdjZlpLegxhjVME1fgjWPGmkzs7" crossorigin="anonymous">

    <!-- Optional theme -->
    <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.6/css/bootstrap-theme.min.css" integrity="sha384-fLW2N01lMqjakBkx3l/M9EahuwpSfeNvV63J5ezn3uZzapT0u7EYsXMjQV+0En5r" crossorigin="anonymous">
    """)
        out_file.write('<body>')
        out_file.write('<div class="matching">')
        out_file.write('<h1>%s</h1>' % 'Dynamic Pricing Ruels Report')
        for rule in dynParser.taxos.values():
            rule['html'] = rule.toHTML()
            rule['_pricing_rule'] = rule.to_pricing_rule()

        # print '\n'.join(map(str , dynParser.taxos.values()))
        dynList = ObjList(dynParser.taxos.values())

        writeSection(
            "Dynamic Pricing Rules",
            "all products and their dynaimc pricing rules",
            re.sub("<table>", "<table class=\"table table-striped\">",
                   dynList.tabulate(cols=OrderedDict([
                    ('html', {}),
                    ('_pricing_rule', {}),
                   ]), tablefmt="html")
                   ),
            length=len(dynList.objects)
        )

        out_file.write('</div>')
        out_file.write("""
    <script src="https://ajax.googleapis.com/ajax/libs/jquery/2.1.4/jquery.min.js"></script>
    <script src="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.6/js/bootstrap.min.js" integrity="sha384-0mSbJDEHialfmuBBQP6A4Qrprq5OVfW37PRR3j5ELqxss1yVqOtnepnHVP9aJ7xS" crossorigin="anonymous"></script>
    """)
        out_file.write('</body>')
        out_file.write('</html>')
