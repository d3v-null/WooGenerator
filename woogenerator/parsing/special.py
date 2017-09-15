from __future__ import absolute_import

from collections import OrderedDict

from ..utils import (DescriptorUtils, Registrar, SanitationUtils, SeqUtils,
                     TimeUtils)
from .abstract import BLANK_CELL
from .tree import (CsvParseTree, ImportTreeItem, ImportTreeObject,
                   ImportTreeTaxo, ItemList, TaxoList)


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
            data[self.startTimeKey] = TimeUtils.g_drive_strp_mk_time(
                data[self.startTimeRawKey])
        else:
            data[self.startTimeKey] = BLANK_CELL

        if self.endTimeRawKey in data:
            data[self.endTimeKey] = TimeUtils.g_drive_strp_mk_time(
                data[self.endTimeRawKey])
        else:
            data[self.endTimeKey] = BLANK_CELL

        return data


class ImportSpecialObject(ImportTreeObject, ImportSpecialMixin):
    pass


class ImportSpecialGroup(ImportTreeTaxo, ImportSpecialMixin):
    container = SpecialGruopList

    special_id = DescriptorUtils.safe_key_property(
        ImportSpecialMixin.groupIDKey)
    start_time = DescriptorUtils.safe_key_property(
        ImportSpecialMixin.startTimeKey)
    end_time = DescriptorUtils.safe_key_property(ImportSpecialMixin.endTimeKey)
    verifyMetaKeys = [
        ImportSpecialMixin.startTimeKey,
        ImportSpecialMixin.endTimeKey,
        ImportSpecialMixin.groupIDKey
    ]

    def __init__(self, data, **kwargs):
        for key in ["FROM", "TO"]:
            if key not in data:
                raise UserWarning(
                    "Missing %s field. data: %s, kwargs: %s" % (key, data, kwargs))

        data = self.init_from_to(data)
        super(ImportSpecialGroup, self).__init__(data, **kwargs)

        try:
            self.special_id
        except BaseException:
            raise UserWarning('ID exist for Special to be valid')

    @property
    def index(self):
        return self.special_id

    @property
    def has_started(self):
        return not TimeUtils.has_happened_yet(self.start_time)

    @property
    def has_finished(self):
        return not TimeUtils.has_happened_yet(self.end_time)

    @property
    def is_active(self):
        return self.has_started and not self.has_finished


class ImportSpecialRule(ImportTreeItem, ImportSpecialMixin):
    ruleCode = DescriptorUtils.safe_key_property(
        ImportSpecialMixin.ruleCodeKey)
    verifyMetaKeys = [
        ImportSpecialMixin.ruleCodeKey
    ]

    def __init__(self, data, **kwargs):
        data = self.init_from_to(data)
        super(ImportSpecialRule, self).__init__(data, **kwargs)

    @property
    def start_time(self):
        return self.get_first_filtd_anc_self_key(self.startTimeKey)

    @property
    def end_time(self):
        return self.get_first_filtd_anc_self_key(self.endTimeKey)

    @property
    def special_id(self):
        if self.ruleCode == '-':
            return self.parent.special_id
        else:
            return '-'.join([self.parent.special_id, self.ruleCode])

    @property
    def index(self):
        return self.special_id


class CsvParseSpecial(CsvParseTree):

    itemContainer = ImportSpecialRule
    taxoContainer = ImportSpecialGroup
    objectContainer = ImportSpecialObject

    def __init__(self, cols=None, defaults=None):
        if self.DEBUG_MRO:
            Registrar.register_message(' ')
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
        cols = SeqUtils.combine_lists(cols, extra_cols)

        super(CsvParseSpecial, self).__init__(
            cols,
            defaults,
            taxo_depth=1,
            item_depth=1,
            meta_width=1
        )
        self.object_indexer = self.get_object_id
        self.register_item = self.register_rule
        self.register_taxo = self.register_rule_group

    def clear_transients(self):
        if self.DEBUG_MRO:
            Registrar.register_message(' ')
        super(CsvParseSpecial, self).clear_transients()
        self.rule_groups = OrderedDict()
        self.rules = OrderedDict()

    def register_rule_group(self, group_data):
        if Registrar.DEBUG_SPECIAL:
            Registrar.register_message(
                "registering rule group: %s", group_data.identifier)
        assert group_data.isTaxo
        self.register_anything(
            group_data,
            self.rule_groups,
            indexer=self.object_indexer,
            singular=True,
            resolver=self.duplicate_obj_exc_resolver,
            register_name='rule groups'
        )

    def register_rule(self, rule_data):
        if Registrar.DEBUG_SPECIAL:
            Registrar.register_message(
                "registering rule: %s", rule_data.identifier)
        assert rule_data.isItem
        self.register_anything(
            rule_data,
            self.rules,
            indexer=self.object_indexer,
            singular=True,
            resolver=self.duplicate_obj_exc_resolver,
            register_name='rules'
        )

    def auto_next(self):
        """ return the next future rule """
        all_future = self.all_future()
        response = None
        if all_future:
            response = all_future[0]
        if Registrar.DEBUG_SPECIAL:
            Registrar.register_message("returning %s" % (response))
        return response

    def all_future(self):
        """ return all future rules """
        all_future = []
        for _, special_group in self.rule_groups.items():
            if special_group.has_finished:
                continue
            all_future.append(special_group)
        all_future = sorted(all_future, cmp=(
            lambda sa, sb: cmp(sa.start_time, sb.end_time)))
        return all_future

    #
    def determine_current_spec_grps(
            self, specials_mode, current_special=None):
        if Registrar.DEBUG_SPECIAL:
            Registrar.register_message("starting")
        response = []
        if specials_mode == 'override':
            if current_special and current_special in self.rule_groups.keys():
                response = [self.rule_groups[current_special]]
        elif specials_mode == 'auto_next':
            auto_next = self.auto_next()
            if auto_next:
                response = [auto_next]
        elif specials_mode == 'all_future':
            all_future = self.all_future()
            if all_future:
                response = all_future
        if Registrar.DEBUG_SPECIAL:
            Registrar.register_message(
                "returning %s <- %s, %s" % (response, specials_mode, current_special))
        return response

    @classmethod
    def get_object_id(cls, object_data):
        return object_data.special_id

    def sanitize_cell(self, cell):
        return SanitationUtils.sanitize_special_cell(cell)

    def tabulate(self, tablefmt=None, **_):
        if not tablefmt:
            tablefmt = "simple"
        #

        out = "\n"
        for index, rule_group in self.rule_groups.items():
            out += "-> %s\n" % index
            rule_list = SpecialRuleList(rule_group.children)
            out += SanitationUtils.coerce_bytes(
                rule_list.tabulate(tablefmt='simple'))
            out += '\n'

        return out
