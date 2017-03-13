from collections import OrderedDict

from csvparse_abstract import BLANK_CELL
from csvparse_tree import CSVParse_Tree
from csvparse_tree import TaxoList, ItemList
from csvparse_tree import ImportTreeItem, ImportTreeObject, ImportTreeTaxo
from utils import listUtils, descriptorUtils, TimeUtils, Registrar, SanitationUtils

class SpecialGruopList(TaxoList):
    pass

class SpecialRuleList(ItemList):
    pass

class ImportSpecialMixin(object):
    ruleCodeKey = 'Rule Code'
    groupIDKey = 'Special Group ID'
    startTimeKey = 'start_time'
    endTimeKey = 'end_time'
    startTimeRawKey = 'FROM'
    endTimeRawKey = 'TO'

    def init_from_to(self, data):
        if self.startTimeRawKey in data:
            data[self.startTimeKey] = TimeUtils.gDriveStrpTime(data[self.startTimeRawKey])
        else:
            data[self.startTimeKey] = BLANK_CELL

        if self.endTimeRawKey in data:
            data[self.endTimeKey] = TimeUtils.gDriveStrpTime(data[self.endTimeRawKey])
        else:
            data[self.endTimeKey] = BLANK_CELL

        return data

class ImportSpecialObject(ImportTreeObject, ImportSpecialMixin):
    pass

class ImportSpecialGroup(ImportTreeTaxo, ImportSpecialMixin):
    container = SpecialGruopList

    ID = descriptorUtils.safeKeyProperty(ImportSpecialMixin.groupIDKey)
    start_time = descriptorUtils.safeKeyProperty(ImportSpecialMixin.startTimeKey)
    end_time = descriptorUtils.safeKeyProperty(ImportSpecialMixin.endTimeKey)
    verifyMetaKeys = [
        ImportSpecialMixin.startTimeKey,
        ImportSpecialMixin.endTimeKey,
        ImportSpecialMixin.groupIDKey
    ]

    def __init__(self, data, **kwargs):
        for key in ["FROM", "TO"]:
            if key not in data:
                raise UserWarning("Missing %s field. data: %s, kwargs: %s" % (key, data, kwargs))

        data = self.init_from_to(data)
        super(ImportSpecialGroup, self).__init__(data, **kwargs)

        try:
            self.ID
        except:
            raise UserWarning('ID exist for Special to be valid')

    @property
    def index(self):
        return self.ID

class ImportSpecialRule(ImportTreeItem, ImportSpecialMixin):
    ruleCode = descriptorUtils.safeKeyProperty(ImportSpecialMixin.ruleCodeKey)
    verifyMetaKeys = [
        ImportSpecialMixin.ruleCodeKey
    ]

    def __init__(self, data, **kwargs):
        data = self.init_from_to(data)
        super(ImportSpecialRule, self).__init__(data, **kwargs)

    @property
    def start_time(self):
        return self.getFirstFilteredAncestorSelfKey(self.startTimeKey)

    @property
    def end_time(self):
        return self.getFirstFilteredAncestorSelfKey(self.endTimeKey)

    @property
    def ID(self):
        if self.ruleCode == '-':
            return self.parent.ID
        else:
            return '-'.join([self.parent.ID, self.ruleCode])

    @property
    def index(self):
        return self.ID

class CSVParse_Special(CSVParse_Tree):

    itemContainer = ImportSpecialRule
    taxoContainer = ImportSpecialGroup
    objectContainer = ImportSpecialObject

    def __init__(self, cols=None, defaults=None):
        if self.DEBUG_MRO:
            self.registerMessage(' ')
        if cols is None:
            cols = []
        if defaults is None:
            defaults = {}
        extra_cols = [
            ImportSpecialMixin.groupIDKey,
            # "Special Group ID",
            "FROM",
            "TO",
            ImportSpecialMixin.ruleCodeKey,
            # "Rule ID",
            "RNS",
            "RPS",
            "WNS",
            "WPS",
            "XRNS",
            "XRPS",
            "XWNS",
            "XWPS"
        ]
        cols = listUtils.combineLists(cols, extra_cols)

        super(CSVParse_Special, self).__init__(
                cols,
                defaults,
                taxoDepth=1,
                itemDepth=1,
                metaWidth=1
            )
        self.objectIndexer = self.getObjectID
        self.registerItem = self.registerRule
        self.registerTaxo = self.registerRuleGroup

    def clearTransients(self):
        if Registrar.DEBUG_MRO:
            Registrar.registerMessage(' ')
        super(CSVParse_Special, self).clearTransients()
        self.ruleGroups = OrderedDict()
        self.rules = OrderedDict()

    def registerRuleGroup(self, groupData):
        if Registrar.DEBUG_SPECIAL:
            Registrar.registerMessage("registering rule group: %s", groupData.identifier)
        assert groupData.isTaxo
        self.registerAnything(
            groupData,
            self.ruleGroups,
            indexer = self.objectIndexer,
            singular = True,
            resolver = self.duplicateObjectExceptionResolver,
            registerName = 'rule groups'
        )

    def registerRule(self, ruleData):
        if Registrar.DEBUG_SPECIAL:
            Registrar.registerMessage("registering rule: %s", ruleData.identifier)
        assert ruleData.isItem
        self.registerAnything(
            ruleData,
            self.rules,
            indexer = self.objectIndexer,
            singular = True,
            resolver = self.duplicateObjectExceptionResolver,
            registerName = 'rules'
        )



    @classmethod
    def getObjectID(cls, objectData):
        return objectData.ID

    def sanitizeCell(self, cell):
        return SanitationUtils.sanitizeSpecialCell(cell)

    def tabulate(self, tablefmt=None):
        if not tablefmt:
            tablefmt="simple"
        #

        out = "\n"
        for index, ruleGroup in self.ruleGroups.items():
            out += "-> %s\n" % index
            ruleList = SpecialRuleList(ruleGroup.children)
            out += SanitationUtils.coerceBytes(ruleList.tabulate(tablefmt='simple'))
            out += '\n'

        return out