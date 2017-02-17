""" Stores all information about how a record is duplicated and stores references to the objects 
with which it conflicts """

from collections import OrderedDict
from utils import SanitationUtils
from tabulate import tabulate

def object_glb_index_fn(objectData):
    assert hasattr(objectData, 'index'), \
        "objectData should have index attr, type: %s " % type(objectData)
    return SanitationUtils.coerceUnicode(objectData.index)

def object_m_index_fn(objectData):
    assert hasattr(objectData, 'MYOBID'), \
        "objectData should have MYOBID attr, type: %s " % type(objectData)
    return SanitationUtils.coerceUnicode(objectData.MYOBID)

def object_s_index_fn(objectData):
    assert hasattr(objectData, 'username'), \
        "objectData should have username attr, type: %s " % type(objectData)
    return SanitationUtils.coerceUnicode(objectData.username)

class DuplicateObject(object):
    """stores all the data about a given objects conflicts with other objects"""
    def __init__(self, objectData):
        super(DuplicateObject, self).__init__()
        self.objectData = objectData
        self.reasons = OrderedDict()

    def __cmp__(self, other):
        return cmp(self.weighted_reason_count, other.weighted_reason_count)

    @property
    def m_index(self):
        return object_m_index_fn(self.objectData)

    @property
    def s_index(self):
        return object_s_index_fn(self.objectData)

    @property
    def reason_count(self):
        if self.reasons:
            return len(self.reasons.keys())

    @property
    def weighted_reason_count(self):
        if self.reasons:
            return sum([
                reason_info.get('weighting', 1)\
                    for reason_info in self.reasons.values()
            ])

    def add_reason(self, reason, weighting=1, details=None):
        if reason not in self.reasons:
            self.reasons[reason] = {
                'weighting':weighting,
            }
        if details:
            self.reasons[reason]['details'] = details


    def tabulate(self, cols, tablefmt=None, highlight_rules=None):
        if not tablefmt:
            tablefmt = 'html'
        linedelim = "\n"
        if tablefmt == 'html':
            linedelim = '<br/>'
        inner_title_fstr = "%10s | %10s | %3d:%3s"
        title_fstr = "-> %s" % inner_title_fstr
        if tablefmt == 'html':
            title_fstr = "<h3>%s</h3>" % inner_title_fstr
        # out = "-> %10s | %10s | %3d | %3s " % (
        out = title_fstr % (
            self.m_index, 
            self.s_index,
            self.reason_count,
            self.weighted_reason_count,
        )

        out += linedelim

        reason_table = []
        for reason, reason_info in self.reasons.items():
            reason_table.append([
                reason,
                reason_info['weighting'],
                reason_info['details']
            ])

        objContainer = self.objectData.containerize()
        out += objContainer.tabulate(cols, tablefmt, highlight_rules)

        out += tabulate(reason_table, tablefmt=tablefmt, headers=["Reason", "Weighting", "Details"])

        return out

class Duplicates(OrderedDict):
    """a dictionary of duplicates stored by index"""
    def __init__(self):
        super(Duplicates, self).__init__()

    def add_conflictors(self, conflictors, reason, weighting=1):
        assert isinstance(conflictors, list), "conflictors should be in a list, instead %s " % type(conflictors)
        assert isinstance(reason, str), "reason should be a string"
        for duplicateObject in conflictors:
            coConflictors = set(conflictors) - set(duplicateObject) # conflictors other than self
            duplicateDetails = ", ".join([
                SanitationUtils.coerceAscii(object_glb_index_fn(objectData)) \
                    for objectData in coConflictors
            ])
            self.add_conflictor(duplicateObject, reason, details=duplicateDetails, weighting=weighting)

    def add_conflictor(self, conflictor, reason, weighting=1, details=None):
        duplicateIndex = object_glb_index_fn(conflictor)
        if duplicateIndex not in self:
            self[duplicateIndex] = DuplicateObject(conflictor)
        self[duplicateIndex].add_reason(reason, weighting, details)
 
    def tabulate(self, cols, tablefmt=None, highlight_rules=None):
        if not tablefmt:
            tablefmt = 'html'
        out = ""
        linedelim = "\n"
        if tablefmt == 'html': linedelim = '<br/>'
        out += linedelim.join(
            [duplicate.tabulate(cols, tablefmt, highlight_rules) for duplicate in sorted(self.values(), reverse=True)[:100]]
        )
        return out
 


        
