""" Stores all information about how a record is duplicated and stores references to the objects
with which it conflicts """

from collections import OrderedDict
from utils import SanitationUtils
from tabulate import tabulate


def object_glb_index_fn(object_data):
    assert hasattr(object_data, 'index'), \
        "object_data should have index attr, type: %s " % type(object_data)
    return SanitationUtils.coerce_unicode(object_data.index)


def object_m_index_fn(object_data):
    assert hasattr(object_data, 'MYOBID'), \
        "object_data should have MYOBID attr, type: %s " % type(object_data)
    return SanitationUtils.coerce_unicode(object_data.MYOBID)


def object_s_index_fn(object_data):
    assert hasattr(object_data, 'username'), \
        "object_data should have username attr, type: %s " % type(object_data)
    return SanitationUtils.coerce_unicode(object_data.username)


class DuplicateObject(object):
    """stores all the data about a given objects conflicts with other objects"""

    def __init__(self, object_data):
        super(DuplicateObject, self).__init__()
        self.object_data = object_data
        self.reasons = OrderedDict()

    def __cmp__(self, other):
        return cmp(self.weighted_reason_count, other.weighted_reason_count)

    @property
    def m_index(self):
        return object_m_index_fn(self.object_data)

    @property
    def s_index(self):
        return object_s_index_fn(self.object_data)

    @property
    def reason_count(self):
        if self.reasons:
            return len(self.reasons.keys())

    @property
    def weighted_reason_count(self):
        if self.reasons:
            return sum([
                reason_info.get('weighting', 1)
                for reason_info in self.reasons.values()
            ])

    def add_reason(self, reason, weighting=1, details=None):
        if reason not in self.reasons:
            self.reasons[reason] = {
                'weighting': weighting,
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

        obj_container = self.object_data.containerize()
        out += obj_container.tabulate(cols, tablefmt, highlight_rules)

        out += tabulate(reason_table, tablefmt=tablefmt,
                        headers=["Reason", "Weighting", "Details"])

        return out


class Duplicates(OrderedDict):
    """a dictionary of duplicates stored by index"""

    def __init__(self):
        super(Duplicates, self).__init__()

    def add_conflictors(self, conflictors, reason, weighting=1):
        assert isinstance(
            conflictors, list), "conflictors should be in a list, instead %s " % type(conflictors)
        assert isinstance(reason, str), "reason should be a string"
        for duplicate_object in conflictors:
            # conflictors other than self
            co_conflictors = set(conflictors) - set(duplicate_object)
            duplicate_details = ", ".join([
                SanitationUtils.coerce_ascii(object_glb_index_fn(object_data))
                for object_data in co_conflictors
            ])
            self.add_conflictor(duplicate_object, reason,
                                details=duplicate_details, weighting=weighting)

    def add_conflictor(self, conflictor, reason, weighting=1, details=None):
        duplicate_index = object_glb_index_fn(conflictor)
        if duplicate_index not in self:
            self[duplicate_index] = DuplicateObject(conflictor)
        self[duplicate_index].add_reason(reason, weighting, details)

    def tabulate(self, cols, tablefmt=None, highlight_rules=None):
        if not tablefmt:
            tablefmt = 'html'
        out = ""
        linedelim = "\n"
        if tablefmt == 'html':
            linedelim = '<br/>'
        out += linedelim.join(
            [duplicate.tabulate(cols, tablefmt, highlight_rules)
             for duplicate in sorted(self.values(), reverse=True)[:100]]
        )
        return out
