"""
Utilities for parsing and handling dynamic pricing information.
"""

from collections import OrderedDict
from copy import copy

import bleach

from woogenerator.utils import (SeqUtils, DescriptorUtils, ValidationUtils,
                                PHPUtils, SanitationUtils)
from woogenerator.parsing.tree import (CsvParseTree, ImportTreeItem,
                                       ImportTreeTaxo, ImportTreeObject)


class ImportDynObject(ImportTreeObject):
    """
    Abstract class encompasing Dynamic rule lines and rules.
    """

    # def is_rule_line(self):
    #     return False

    # def validate(self):
    #     for key, validation in self.validations:
    #         assert callable(validation)
    #         if not validation(self.get(key)):
    #             raise UserWarning("%s could be be validated by %s" %
    #                               (key, self.__class__.__name__))


class ImportDynRuleLine(ImportDynObject, ImportTreeItem):
    """
    ImportObject for individual dynamic pricing rule line.
    """
    validations = {
        'Discount': ValidationUtils.is_not_none,
        'Discount Type': ValidationUtils.is_contained_in(['PDSC'])
    }

    discount = DescriptorUtils.safe_key_property('Discount')
    discount_type = DescriptorUtils.safe_key_property('Discount Type')

    def __init__(self, *args, **kwargs):
        super(ImportDynRuleLine, self).__init__(*args, **kwargs)

        if all([
                self.get('Min ( Buy )') is None,
                self.get('Max ( Receive )') is None
        ]):
            raise UserWarning(
                "one of buy or receiver must be visible to ImportDynObject")

    # def is_rule_line(self): return True

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
    """
    An ImportObject which is a parent to group of dynamic parsing rules.
    """

    validations = {
        'ID': ValidationUtils.is_not_none,
        'Qty. Base': ValidationUtils.is_contained_in(['PROD', 'VAR', 'CAT']),
        'Rule Mode': ValidationUtils.is_contained_in(['BULK', 'SPECIAL']),
        'Roles': ValidationUtils.is_not_none
    }

    qty_base = DescriptorUtils.safe_key_property('Qty. Base')
    rule_mode = DescriptorUtils.safe_key_property('Rule Mode')
    roles = DescriptorUtils.safe_key_property('Roles')
    rule_id = DescriptorUtils.safe_key_property('ID')

    def __init__(self, *args, **kwargs):
        super(ImportDynRule, self).__init__(*args, **kwargs)
        self.rule_lines = []
        assert self.rule_id

    @property
    def index(self):
        return self.rule_id

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

    def get_rule_lines(self):
        return self.children

    def get_col_names(self):
        rule_mode = self.get('Rule Mode', 'BULK')
        if rule_mode == 'BULK' or not rule_mode:
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
        if self.get_rule_lines():
            rep += ' | '
            rep += ', '.join([line.get('Meaning', '')
                              for line in self.get_rule_lines()])
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

        if self.rule_mode == 'BULK':
            mode = 'continuous'
            block_rules = {
                1: empty_blockrule
            }
            rules = {}
            for i, rule_line in enumerate(self.get_rule_lines()):
                rule = copy(empty_rule)
                rule['from'] = rule_line.pricing_rule_from
                rule['to'] = rule_line.pricing_rule_to
                rule['amount'] = rule_line.discount
                rule['type'] = rule_line.pricing_rule_disc_type
                rules[i + 1] = rule
        else:
            mode = 'block'
            rules = {
                1: empty_rule
            }
            block_rules = {}
            for i, block_rule_line in enumerate(self.get_rule_lines()):
                block_rule = copy(empty_blockrule)
                block_rule['from'] = block_rule_line.pricing_rule_from
                block_rule['to'] = block_rule_line.pricing_rule_to
                block_rule['amount'] = block_rule_line.discount
                block_rule['type'] = block_rule_line.pricing_rule_disc_type
                block_rules[i + 1] = block_rule

        pricing_rule = OrderedDict([
            ('conditions_type', 'all'),
            ('conditions', self.pricing_rule_conditions),
            ('collector', self.pricing_rule_collector),
            ('mode', mode),
            ('date_from', ''),
            ('date_to', ''),
            ('rules', rules),
            ('blockrules', block_rules),
        ])

        return PHPUtils.serialize(pricing_rule)

    def to_html(self):
        col_names = self.get_col_names()

        html = u'<table class="shop_table lasercommerce pricing_table table table-striped">'
        html += '<thead><tr>'
        for col, name in col_names.items():
            col_class = SanitationUtils.sanitize_class(col)
            html += '<th class=%s>' % col_class
            html += bleach.clean(name)
            html += '</th>'
        html += '</tr></thead>'
        rule_lines = self.get_rule_lines()
        self.register_message("rule_lines: %s" % (rule_lines))
        for rule_line_data in rule_lines:
            line_type = rule_line_data.get('Discount Type', '')
            html += '<tr>'
            for col in col_names.keys():
                value = rule_line_data.get(col, '')
                if col == 'Discount' and line_type in ['PDSC']:
                    value += '%'
                html += '<td>'
                html += value  # bleach.clean(value)
                html += '</td>'
            html += '</tr>'
        html += "</table>"

        return html.encode('UTF-8')


class CsvParseDyn(CsvParseTree):
    """
    Parser for dynamic pricing rules.
    """

    itemContainer = ImportDynRuleLine
    taxoContainer = ImportDynRule
    objectContainer = ImportDynObject

    def __init__(self, cols=None, defaults=None):
        if cols is None:
            cols = []
        if defaults is None:
            defaults = {}
        extra_cols = [
            'ID', 'Qty. Base', 'Rule Mode', 'Roles',
            'Min ( Buy )', 'Max ( Receive )', 'Discount Type', 'Discount', 'Repeating', 'Meaning']

        extra_defaults = {
            'Discount Type': 'PDSC',
            'Rule Mode': 'BULK'
        }

        cols = SeqUtils.combine_lists(cols, extra_cols)
        defaults = SeqUtils.combine_ordered_dicts(extra_defaults, defaults)
        super(CsvParseDyn, self).__init__(cols, defaults,
                                          taxo_depth=1, item_depth=1, meta_width=0)

        self.taxo_indexer = self.get_object_index

    def depth(self, row):
        for i, cell in enumerate(row):
            if cell:
                if i < 4:
                    return 0
                else:
                    return 1
        return -1
