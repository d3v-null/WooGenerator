""" Stores all information about how a record is duplicated and stores references to the objects 
with which it conflicts """

from collections import OrderedDict
from utils import SanitationUtils

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
        self.coConflictors = set()
        self.reasons = OrderedDict()

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
                reason_info.get('weighting', 1) * len(reason_info.get('coConflictors', []))\
                    for reason_info in self.reasons.values()
            ])

    def add_reason(self, reason, coConflictors=None, weighting=1):
        if reason not in self.reasons:
            self.reasons[reason] = {
                'weighting':weighting,
                'coConflictors':set()
            }
        if coConflictors:
            self.coConflictors.update(coConflictors)
            self.reasons[reason]['coConflictors'].update(coConflictors)

    def tabulate(self, cols, tablefmt):
        pass

class Duplicates(OrderedDict):
    """a dictionary of duplicates stored by index"""
    def __init__(self):
        super(Duplicates, self).__init__()

    def add_conflictors(self, conflictors, reason, weighting=1):
        assert isinstance(conflictors, list), "conflictors should be in a list"
        assert isinstance(reason, str), "reason should be a string"
        for duplicateObject in conflictors:
            coConflictors = set(conflictors) - set(duplicateObject) # conflictors other than self
            duplicateIndex = object_glb_index_fn(duplicateObject)
            if duplicateIndex not in self:
                self[duplicateIndex] = DuplicateObject(duplicateObject)
            self[duplicateIndex].add_reason(reason, coConflictors, weighting)

    def tabulate(self, cols, tablefmt):
        pass



        
