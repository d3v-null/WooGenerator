import os
from utils import listUtils, descriptorUtils
from csvparse_tree import CSVParse_Tree, ImportTreeItem, ImportTreeTaxo, ImportTreeObject
import bleach
import re
from collections import OrderedDict


def sanitizeClass(string):
    return re.sub('[^a-z]', '', string.lower())

def isNotNone(arg):
    return arg is not None

def isContainedIn(l):
    return lambda v: v in l

class ImportDynObject(ImportTreeObject):

    def isRuleLine(self): return False
    def validate(self):
        for key, validation in self.validations:
            assert callable(validation)
            if not validation(self.get(key)):
                raise UserWarning("%s could be be validated by %s" % (key,self.__class__.__name__) )

class ImportDynRuleLine(ImportDynObject, ImportTreeItem):

    validations = {
        'Discount': isNotNone,
        'Discount Type': isContainedIn( ['PDSC'] )
    }

    def __init__(self, *args, **kwargs):
        super(ImportDynRuleLine, self).__init__(*args, **kwargs)    

        if all([
            self.get('Min ( Buy )') is None,
            self.get('Max ( Receive )') is None
        ]):
            raise UserWarning("one of buy or receiver must be visible to ImportDynObject")

    def isRuleLine(self): return True

class ImportDynRule(ImportDynObject, ImportTreeTaxo):

    validations = {
        'ID':isNotNone, 
        'Qty. Base': isContainedIn(['PROD', 'VAR', 'CAT']) , 
        'Rule Mode': isContainedIn(['BULK', 'SPECIAL']), 
        'Roles': isNotNone
    }

    def __init__(self, *args, **kwargs):
        super(ImportDynRule, self).__init__(*args, **kwargs)
        self.ruleLines = []
        assert self.ID

    ID = descriptorUtils.safeKeyProperty('ID')

    @property
    def index(self): return self.ID

    # def addRuleData(self, ruleData):
    #     self.ruleData = ruleData

    # def addLineData(self, ruleLineData):
    #     if ruleLineData:
    #         self['children'].append(ruleLineData)

    def registerRuleLine(self, lineData):
        # assert isinstance(lineData, ImportDynObject)
        assert lineData.isRuleLine()
        self.registerAnything(
            lineData,
            self.getRuleLines()
        )

    def getRuleLines(self):
        return self.ruleLines
        # return self.getChildren().values()

    def getColNames(self, ruleMode='BULK'):
        ruleMode = self.get('Rule Mode', 'BULK')
        if ruleMode == 'BULK' or not ruleMode:
            return OrderedDict([
                ('Min ( Buy )', 'From'), 
                ('Max ( Receive )', 'To'), 
                ('Discount' , 'Discount'), 
                ('Meaning', 'Meaning') 
            ])
        else:
            return OrderedDict([
                ('Min ( Buy )', 'Buy'),
                ('Max ( Receive )', 'Receive'),
                ('Discount' , 'Discount'),
                ('Meaning', 'Meaning)')
            ])       

    def __repr__(self):
        rep = "<ImportDynRule | " 
        rep += ', '.join( 
            map(
                lambda x: str( (x, self.get(x,'')) ),
                ['Qty. Base', 'Rule Mode', 'Roles']
            )
        ) 
        if self.getRuleLines():
            rep += ' | '
            rep += ', '.join([line.get('Meaning', '') for line in self.getRuleLines()])
        rep += ' >'
        return rep

    def toHTML(self, ruleMode = 'BULK'):
        colNames = self.getColNames(ruleMode)

        html  = u'<table class="shop_table lasercommerce pricing_table">'
        html +=   '<thead><tr>'
        for col, name in colNames.items():
            colClass = sanitizeClass(col)
            html += '<th class=%s>' % colClass
            html +=   bleach.clean(name)
            html += '</th>'
        html +=   '</tr></thead>'
        ruleLines = self.getRuleLines()
        self.registerMessage("ruleLines: {}" % (ruleLines))
        for ruleLineData in ruleLines:
            lineType = ruleLineData.get('Discount Type','')
            html += '<tr>'
            for col in colNames.keys():
                value = ruleLineData.get(col, '')
                if col == 'Discount' and lineType in ['PDSC']:
                    value += '%'
                html += '<td>'
                html +=  value #bleach.clean(value)
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
            'Discount Type':'PDSC',
            'Rule Mode': 'BULK'
        }

        cols = listUtils.combineLists(cols, extra_cols)
        defaults = listUtils.combineOrderedDicts(extra_defaults, defaults)
        super(CSVParse_Dyn, self).__init__( cols, defaults, \
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
        for i,cell in enumerate(row):
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
    dprcPath= os.path.join(inFolder, 'DPRC.csv')

    dynParser = CSVParse_Dyn()
    dynParser.analyseFile(dprcPath)

    for html in ([rule.toHTML() for rule in dynParser.taxos.values()]):
        print html
