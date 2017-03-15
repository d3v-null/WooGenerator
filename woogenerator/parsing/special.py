from collections import OrderedDict

from woogenerator.utils import listUtils, descriptorUtils, TimeUtils, Registrar, SanitationUtils
from woogenerator.parsing.abstract import BLANK_CELL
from woogenerator.parsing.tree import CSVParse_Tree
from woogenerator.parsing.tree import TaxoList, ItemList
from woogenerator.parsing.tree import ImportTreeItem, ImportTreeObject, ImportTreeTaxo

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

    @property
    def hasStarted(self):
        return not TimeUtils.hasHappenedYet(self.start_time)

    @property
    def hasFinished(self):
        return not TimeUtils.hasHappenedYet(self.end_time)

    @property
    def isActive(self):
        return self.hasStarted and not self.hasFinished

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

    def auto_next(self):
        """ return the next future rule """
        all_future = self.all_future()
        if all_future:
            # TODO: may have to sort this
            return all_future[0]

    def all_future(self):
        """ return all future rules """
        if self.DEBUG_SPECIAL:
            self.registerMessage("entering all_future")
        all_future = []
        for specialIndex, specialGroup in self.ruleGroups.items():
            if specialGroup.hasFinished:
                if self.DEBUG_SPECIAL:
                    self.registerMessage("specialGroup has finished: %s" % specialIndex)
                continue
            all_future.append(specialGroup)
        return all_future

    #
    def determine_current_special_groups(self, specials_mode, current_special=None):
        # modes: ['override', 'auto_next', 'all_future']
        if specials_mode == 'override':
            if current_special and current_special in self.ruleGroups.keys():
                return [self.ruleGroups[current_special]]
        elif specials_mode == 'auto_next':
            auto_next = self.auto_next()
            if auto_next: return [auto_next]
        elif specials_mode == 'all_future':
            all_future = self.all_future()
            if all_future:
                return all_future
        return []

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
