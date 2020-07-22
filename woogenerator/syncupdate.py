"""
Utilites for storing and performing operations on pending updates
"""

from __future__ import absolute_import

from collections import OrderedDict
from copy import copy, deepcopy

from past.builtins import cmp
from tabulate import tabulate

from six import text_type

from .coldata import (ColDataAbstract, ColDataAttachment,
                      ColDataProductMeridian, ColDataProductVariationMeridian,
                      ColDataWcProdCategory)
from .matching import Match
from .parsing.abstract import ImportObject
from .parsing.api import ImportWooApiCategory
from .parsing.woo import ImportWooCategory
from .utils import Registrar, SanitationUtils, TimeUtils


class SyncViolation(UserWarning):
    """Update violates some sync condition"""


class InvincibilityViolation(SyncViolation):
    """Update violates an invincibility condition."""


class SemistaticViolation(SyncViolation):
    """Update violates a semistatic condition."""


class UnwritableViolation(SyncViolation):
    """Update violates an unwritable condition."""


class SyncUpdate(Registrar):
    """
    Stores information about and performs operations on a pending update
    """

    coldata_class = ColDataAbstract
    merge_mode = None
    main_target = None
    subordinate_target = None
    # The target format of (m|s)_object, gets immediately converted to core
    object_target = 'gen-api'
    default_main_container = ImportObject
    default_subordinate_container = ImportObject

    @classmethod
    def set_globals(cls, merge_mode, default_last_sync):
        """
        sets the class attributes to those specified in the user config
        """
        # TODO: Fix this awful mess
        cls.merge_mode = merge_mode
        cls.default_last_sync = default_last_sync

    def __init__(
        self, old_m_object_gen=None, old_s_object_gen=None, last_sync=None
    ):
        super(SyncUpdate, self).__init__()

        if last_sync is None:
            last_sync = self.default_last_sync
        # print "Creating SyncUpdate: ", old_m_object_core.__repr__(),
        # old_s_object_core.__repr__()
        self.old_m_object_core = {}
        self.old_s_object_core = {}
        self.new_m_object_core = {}
        self.new_s_object_core = {}
        self.old_m_object_gen = {}
        self.old_s_object_gen = {}
        self.main_parent = None
        self.subordinate_parent = None
        self.main_container = self.default_main_container
        self.subordinate_container = self.default_subordinate_container
        self.m_time = 0
        self.s_time = 0
        if old_m_object_gen:
            self.set_old_m_object_gen(old_m_object_gen)
        if old_s_object_gen:
            self.set_old_s_object_gen(old_s_object_gen)
        self.t_time = last_sync
        self.static = True
        self.important_static = True
        self.sync_warnings_core = OrderedDict()
        self.sync_passes_core = OrderedDict()
        self.sync_problematics_core = OrderedDict()
        self.updates = 0
        self.important_updates = 0
        self.important_handles = []

        # If there is a change in main that is not just an insertion
        self.m_deltas = False
        # If there is a change in main that is not just an insertion
        self.s_deltas = False

        self.b_time = 0

    def set_old_m_object_gen(self, old_m_object_gen):
        self.old_m_object_gen = old_m_object_gen
        self.main_container = type(self.old_m_object_gen)
        assert issubclass(self.main_container, ImportObject)
        self.main_parent = self.old_m_object_gen.parent
        self.old_m_object_core = self.coldata_class.translate_data_from(
            self.old_m_object_gen.to_dict(), self.object_target,
            excluding_properties=['sync']
        )
        if self.old_m_object_core.get('modified_gmt'):
            self.m_time = self.parse_m_time(
                self.old_m_object_core['modified_gmt']
            )

    def set_old_s_object_gen(self, old_s_object_gen):
        self.old_s_object_gen = old_s_object_gen
        self.subordinate_container = type(self.old_s_object_gen)
        assert issubclass(self.subordinate_container, ImportObject)
        self.subordinate_parent = self.old_s_object_gen.parent
        self.old_s_object_core = self.coldata_class.translate_data_from(
            self.old_s_object_gen.to_dict(), self.object_target,
            excluding_properties=['sync']
        )
        if self.old_s_object_core.get('modified_gmt'):
            self.s_time = self.parse_s_time(
                self.old_s_object_core['modified_gmt']
            )

    def set_new_m_object_gen(self, new_m_object_gen):
        self.main_container = type(new_m_object_gen)
        assert issubclass(self.main_container, ImportObject)
        self.main_parent = new_m_object_gen.parent
        new_m_object_core = self.coldata_class.translate_data_from(
            new_m_object_gen.to_dict(), self.object_target,
            excluding_properties=['sync']
        )
        self.set_new_subject_object(new_m_object_core, self.main_name)

    def set_new_s_object_gen(self, new_s_object_gen):
        self.subordinate_container = type(new_s_object_gen)
        assert issubclass(self.main_container, ImportObject)
        self.subordinate_parent = new_s_object_gen.parent
        new_s_object_core = self.coldata_class.translate_data_from(
            new_s_object_gen.to_dict(), self.object_target,
            excluding_properties=['sync']
        )
        self.set_new_subject_object(new_s_object_core, self.subordinate_name)

    sync_warning_value_keys = ['old_value', 'new_value', 'm_value', 's_value']

    def simplify_sync_warning_value_singular(self, handle, sub_handles):
        """
        Reduce the values in the sync warning for `handle` so that each object
        only shows the value for the `sub_handle`.
        Assumes core representation of `handle` has a singular structure.
        `sub_handle` is most likely the primary key of the sub object.
        """
        if handle in self.sync_warnings_core:
            for sync_warning in self.sync_warnings_core.get(handle, {}):
                for key in self.sync_warning_value_keys:
                    value = sync_warning.get(key)
                    if not value:
                        continue
                    if not isinstance(value, dict):
                        continue
                    new_value = {}
                    for sub_handle in sub_handles:
                        if value.get(sub_handle) is not None:
                            new_value.update({
                                sub_handle: value.get(sub_handle)
                            })
                    sync_warning[key] = new_value

    def simplify_sync_warning_value_listed(self, handle, sub_handles):
        """
        Reduce the values in the sync warning for `handle` so that each object
        only shows the value for the `sub_handles`.
        Assumes core representation of `handle` has a listed structure.
        """
        if handle in self.sync_warnings_core:
            for sync_warning in self.sync_warnings_core.get(handle, {}):
                for key in self.sync_warning_value_keys:
                    values = sync_warning.get(key)
                    if not values:
                        continue
                    if not isinstance(values, list):
                        continue
                    new_values = []
                    for value in values:
                        if not isinstance(value, dict):
                            continue
                        new_value = {}
                        for sub_handle in sub_handles:
                            if value.get(sub_handle) is not None:
                                new_value.update({
                                    sub_handle: value.get(sub_handle)
                                })
                        if not new_value:
                            continue
                        new_values.append(new_value)
                    sync_warning[key] = sorted(new_values)

    @property
    def sync_warnings(self):
        return self.coldata_class.translate_handle_keys(
            self.sync_warnings_core, self.object_target
        )

    @property
    def sync_passes(self):
        return self.coldata_class.translate_handle_keys(
            self.sync_passes_core, self.object_target
        )

    @property
    def sync_problematics(self):
        return self.coldata_class.translate_handle_keys(
            self.sync_problematics_core, self.object_target
        )

    @property
    def s_updated(self):
        """Return whether subordinate has been updated."""
        return bool(self.new_s_object_core)

    @property
    def m_updated(self):
        """Return whether main has been updated."""
        return bool(self.new_m_object_core)

    @property
    def e_updated(self):
        """Return whether either main or subordinate has updated."""
        return self.s_updated or self.m_updated

    @property
    def l_time(self):
        """Return latest modtime out of main and subordinate."""
        return max(self.m_time, self.s_time)

    def get_subject_mod_time(self, subject):
        """Return the modtime of a subject."""
        if subject == self.main_name:
            return self.m_time
        elif subject == self.subordinate_name:
            return self.s_time

    def get_new_subject_object(self, subject):
        """Return the new object associated with the subject."""
        if subject == self.main_name:
            return self.new_m_object_core
        elif subject == self.subordinate_name:
            return self.new_s_object_core

    def set_new_subject_object(self, value, subject):
        if subject == self.main_name:
            self.new_m_object_core = value
        elif subject == self.subordinate_name:
            self.new_s_object_core = value

    def get_old_subject_object(self, subject):
        """Return the new object associated with the subject."""
        if subject == self.main_name:
            return self.old_m_object_core
        elif subject == self.subordinate_name:
            return self.old_s_object_core

    @property
    def m_mod(self):
        """Return whether has been updated since last sync."""
        return self.m_time >= self.t_time

    @property
    def s_mod(self):
        """Return whether subordinate has been updated since last sync."""
        return self.s_time >= self.t_time

    @property
    def main_id(self):
        """Abstract method fo getting the ID of the main object."""
        raise NotImplementedError()

    @property
    def subordinate_id(self):
        """Abstract method fo getting the ID of the subordinate object."""
        raise NotImplementedError()

    @classmethod
    def make_index(cls, main_id, subordinate_id):
        return u"|".join([
            u"m:%s" % text_type(main_id),
            u"s:%s" % text_type(subordinate_id)
        ])

    @property
    def index(self):
        return self.make_index(self.main_id, self.subordinate_id)

    def get_winner_name(self, m_time, s_time):
        """Get name of database containing winning object (main / subordinate)."""
        if not s_time:
            return self.main_name
        elif not m_time:
            return self.subordinate_name
        else:
            return self.subordinate_name if(s_time >= m_time) else self.main_name

    @classmethod
    def parse_m_time(cls, raw_m_time):
        """Parse a raw main time value into a timestamp."""
        return TimeUtils.datetime2localtimestamp(raw_m_time)
        # return raw_m_time

    @classmethod
    def parse_s_time(cls, raw_s_time):
        """Parse a raw subordinate time value into a timestamp."""
        return TimeUtils.datetime2localtimestamp(raw_s_time)
        # return raw_s_time

    def parse_subject_time(self, raw_time, subject):
        """Parse a raw time string for a given subject's format."""
        if subject == self.main_name:
            return self.parse_m_time(raw_time)
        elif subject == self.subordinate_name:
            return self.parse_s_time(raw_time)

    def sanitize_value(self, handle, value):
        """Sanitize a value dependent on the handle the value is from."""
        if 'phone' in handle.lower():
            if 'preferred' in handle.lower():
                if value and len(SanitationUtils.strip_non_numbers(value)) > 1:
                    return ""
        return value

    def get_old_subject_value(self, handle, subject):
        """Get the value for the subject's old object."""
        value = self.get_old_subject_object(subject).get(handle)
        if value is not None:
            return self.sanitize_value(handle, value)
        return ""

    def get_new_subject_value(self, handle, subject):
        """Get the value for the subject's new object."""
        new_object = self.get_new_subject_object(subject)
        if new_object:
            value = new_object.get(handle)
            if value is not None:
                return self.sanitize_value(handle, value)
            return ""
        return self.get_old_subject_value(handle, subject)

    def get_subject_target(self, subject):
        """Get the value for the subject's new object."""
        if subject == self.main_name:
            return self.main_target
        elif subject == self.subordinate_name:
            return self.subordinate_target

    def values_similar(self, handle, m_value, s_value):
        """Check if two values are similar. Depends on handle."""
        response = False
        if not (m_value or s_value):
            response = True
        elif not (m_value and s_value):
            response = False
        if hasattr(m_value, 'similar') and callable(m_value.similar):
            response = m_value.similar(s_value)
        # if handle in self.coldata_class.get_property_inclusions('sub_data'):
        #     if isinstance(m_value, list):
        #         m_value = sorted(m_value) # only sorts keys
        #     if isinstance(s_value, list):
        #         s_value = sorted(s_value)
        similar_m_value = SanitationUtils.similar_comparison(m_value)
        similar_s_value = SanitationUtils.similar_comparison(s_value)

        if similar_m_value == similar_s_value:
            response = True

        if self.DEBUG_UPDATE:
            self.register_message(
                self.test_to_str(
                    handle, m_value, s_value, response,
                    similar_m_value, similar_s_value
                ))
        return response

    def old_handle_identical(self, handle):
        """Check if handle's main / subordinate values are identical in old."""
        m_value = self.get_old_subject_value(handle, self.main_name)
        s_value = self.get_old_subject_value(handle, self.subordinate_name)
        response = m_value == s_value
        if self.DEBUG_UPDATE:
            self.register_message(
                self.test_to_str(
                    handle, m_value, s_value, response))
        return response

    def new_handle_similar(self, handle):
        """Check if handle's main / subordinate values are similar in new."""
        m_value = self.get_new_subject_value(handle, self.main_name)
        s_value = self.get_new_subject_value(handle, self.subordinate_name)
        response = self.values_similar(handle, m_value, s_value)
        if self.DEBUG_UPDATE:
            self.register_message(
                self.test_to_str(
                    handle, m_value, s_value, response))
        return response

    def new_handle_identical(self, handle):
        """Check if handle's main / subordinate values are identical in new."""
        m_value = self.get_new_subject_value(handle, self.main_name)
        s_value = self.get_new_subject_value(handle, self.subordinate_name)
        response = m_value == s_value
        if self.DEBUG_UPDATE:
            self.register_message(
                self.test_to_str(
                    handle, m_value, s_value, response))
        return response

    def col_static(self, handle, subject):
        """Check if handle's old / new values are identical in `subject`."""
        o_value = self.get_old_subject_value(handle, subject)
        n_value = self.get_new_subject_value(handle, subject)
        response = o_value == n_value
        if self.DEBUG_UPDATE:
            self.register_message(
                self.test_to_str(
                    handle, o_value, n_value, response))
        return response

    def col_semi_static(self, handle, subject):
        """Check if handle's old / new values are similar in `subject`."""
        o_value = self.get_old_subject_value(handle, subject)
        n_value = self.get_new_subject_value(handle, subject)
        response = self.values_similar(handle, o_value, n_value)
        if self.DEBUG_UPDATE:
            self.register_message(
                self.test_to_str(
                    handle, o_value, n_value, response))
        return response

    def m_handle_static(self, handle):
        """Check if handle's old / new values are identical in main."""
        # TODO: deprecate this
        return self.col_static(handle, self.main_name)

    def s_handle_static(self, handle):
        """Check if handle's old / new values are identical in subordinate."""
        # TODO: deprecate this
        return self.col_static(handle, self.subordinate_name)

    def m_handle_semi_static(self, handle):
        """Check if handle's old / new values are similar in main."""
        # TODO: deprecate this
        return self.col_semi_static(handle, self.main_name)

    def s_handle_semi_static(self, handle):
        """Check if handle's old / new values are similar in subordinate."""
        # TODO: deprecate this
        return self.col_semi_static(handle, self.subordinate_name)

    def test_to_str(self, handle, val1, val2, res, norm1=None, norm2=None):
        left = repr(val1)
        if norm1 is not None and norm1 != val1:
            left += " (%s %s)" % (norm1, type(norm1))
        right = repr(val2)
        if norm2 is not None and norm2 != val2:
            right += " (%s %s)" % (norm2, type(norm2))

        return u"testing handle %s: %s | %s -> %s" % (
            text_type(handle),
            left,
            right,
            SanitationUtils.bool_to_truish_string(res)
        )

    def update_to_str(self, update_type, update_params):
        assert isinstance(update_type, str)
        assert 'handle' in update_params
        out = u""
        out += "SYNC %s:" % update_type
        out += " | %s " % SanitationUtils.coerce_ascii(self)
        out += " | handle:  %s" % update_params['handle']
        if 'subject' in update_params:
            out += " | subj: %s " % update_params['subject']
        if 'reason' in update_params:
            out += " | reas: %s " % update_params['reason']
        if update_type in ['WARN', 'PROB']:
            if 'new_value' in update_params:
                out += " | OLD: %s " % SanitationUtils.coerce_ascii(
                    update_params['old_value'])
            if 'old_value' in update_params:
                out += " | NEW: %s " % SanitationUtils.coerce_ascii(
                    update_params['new_value'])
        return out

    def add_problematic_update(self, **update_params):
        for key in ['handle', 'subject', 'reason']:
            assert update_params[key], 'missing mandatory prob param %s' % key
        handle = update_params['handle']
        if handle not in self.sync_problematics_core.keys():
            self.sync_problematics_core[handle] = []
        self.sync_problematics_core[handle].append(update_params)
        self.register_warning(self.update_to_str('PROB', update_params))

    def add_sync_warning(self, **update_params):
        for key in ['handle', 'subject', 'reason']:
            assert update_params[
                key], 'missing mandatory warning param %s' % key
        handle = update_params['handle']
        if handle not in self.sync_warnings_core.keys():
            self.sync_warnings_core[handle] = []
        self.sync_warnings_core[handle].append(update_params)
        if self.DEBUG_UPDATE:
            self.register_warning(self.update_to_str('WARN', update_params))

    def add_sync_pass(self, **update_params):
        for key in ['handle']:
            assert update_params[key], 'missing mandatory pass param %s' % key
        handle = update_params['handle']
        if handle not in self.sync_passes_core.keys():
            self.sync_passes_core[handle] = []
        self.sync_passes_core[handle].append(update_params)
        if self.DEBUG_UPDATE:
            self.register_message(self.update_to_str('PASS', update_params))

    def display_update_list(
            self, update_list, tablefmt=None, update_type=None):
        if not update_list:
            return ""

        delimeter = "<br/>" if tablefmt == "html" else "\n"
        subject_fmt = "<h4>%s</h4>" if tablefmt == "html" else "%s"
        # header = ["Column", "Reason", "Old", "New"]
        header_items = [
            ('handle', 'Column'),
            ('reason', 'Reason'),
        ]
        if update_type is None:
            header_items += [
                ('subject', 'Subject'),
                ('old_value', 'Old'),
                ('new_value', 'New'),
            ]
        elif update_type == 'pass':
            header_items += [
                ('m_value', 'Main'),
                ('s_value', 'Subordinate'),
            ]
        elif update_type == 'reflect':
            header_items += [
                ('m_value', 'Main'),
                ('s_value', 'Subordinate'),
                ('reflected_main', 'Reflected Main'),
                ('reflected_subordinate', 'Reflected Subordinate'),
            ]
        header_items += [
            ('m_handle_time', 'M TIME'),
            ('s_handle_time', 'S TIME'),
            ('data', 'EXTRA'),
        ]
        header = OrderedDict(header_items)
        subjects = {}
        for warnings in update_list.values():
            for warning in warnings:
                subject = warning.get('subject', '-')
                if subject not in subjects.keys():
                    subjects[subject] = []
                warning_fmtd = dict([
                    (key, SanitationUtils.sanitize_for_table(val))
                    for key, val in warning.items()
                    if key in header
                ])
                for key in ['m_handle_time', 's_handle_time']:
                    try:
                        raw_time = int(warning[key])
                        if raw_time:
                            warning_fmtd[key] = \
                                TimeUtils.wp_time_to_string(raw_time)
                    except Exception as exc:
                        if exc:
                            pass
                if 'data' in warning:
                    true_data_keys = []
                    for key, value in warning['data'].items():
                        if value and key in ['static', 'delta']:
                            true_data_keys.append(key)
                    warning_fmtd['data'] = "; ".join(
                        map(str.upper, true_data_keys))
                subjects[subject].append(warning_fmtd)
        tables = []
        for warnings in subjects.values():
            subject_formatted = subject_fmt % "-"
            table = [header] + warnings
            try:
                table_fmtd = tabulate(table, headers='firstrow',
                                      tablefmt=tablefmt)
            except ValueError:
                # stupid fix for tabulate
                table = [
                    OrderedDict([
                        (key, "_%s" % value)
                        for key, value in odict.items()
                    ]) for odict in table
                ]
                table_fmtd = tabulate(table, headers='firstrow',
                                      tablefmt=tablefmt)
            tables.append(delimeter.join([subject_formatted, table_fmtd]))
        return SanitationUtils.coerce_ascii(delimeter.join(tables))

    def display_sync_warnings(self, tablefmt=None):
        return self.display_update_list(self.sync_warnings_core, tablefmt)

    def display_sync_passes(self, tablefmt=None):
        return self.display_update_list(
            self.sync_passes_core, tablefmt, update_type='pass')

    def display_problematic_updates(self, tablefmt=None):
        return self.display_update_list(self.sync_problematics_core, tablefmt)

    # def getOldLoserObject(self, winner=None):
    #     if not winner: winner = self.winner
    #     if(winner == self.main_name):
    #         oldLoserObject = self.old_s_object_core

    def opposite_src(self, subject):
        if subject == self.main_name:
            return self.subordinate_name
        elif subject == self.subordinate_name:
            return self.main_name
        elif subject == '-':
            return '-'
        else:
            raise Exception("unknown subject: %s" % subject)

    def snapshot_hash(self, thing):
        try:
            hash_ = hash(thing)
        except TypeError:
            hash_ = hash(str(thing))

        return "%s - %s" % (
            id(thing),
            hash_
        )

    def set_loser_value(self, **update_params):
        for key in ['handle', 'subject', 'old_value', 'new_value']:
            assert key in update_params, \
                'missing mandatory update param, %s from %s' % (
                    key, update_params)

        loser = update_params['subject']
        handle = update_params['handle']
        reason = update_params.get('reason', '')

        prev_old_val_hash = self.snapshot_hash(update_params['old_value'])

        new_loser_object = self.get_new_subject_object(loser)
        prev_new_loser_object = bool(new_loser_object)
        if not prev_new_loser_object:
            old_object = self.get_old_subject_object(loser)
            # TODO: rewrite this with the function i just wrote?
            self.set_new_subject_object(deepcopy(old_object), loser)
            new_loser_object = self.get_new_subject_object(loser)
        prev_loser_val = deepcopy(new_loser_object.get(handle))

        loser_target = self.get_subject_target(loser)
        loser_delta = self.coldata_class.get_handle_property(
            handle, 'delta', loser_target)
        if loser_delta:
            delta_col = self.coldata_class.delta_col(handle)
            if not new_loser_object.get(delta_col):
                new_loser_object[delta_col] = copy(update_params['old_value'])

        new_loser_object[handle] = update_params['new_value']

        # Check update does not violate conditions before marking as changed
        col_semi_static = self.col_semi_static(handle, loser)
        if col_semi_static:
            # revert new_loser_object
            if not prev_new_loser_object:
                self.set_new_subject_object(prev_new_loser_object, loser)
            else:
                new_loser_object[handle] = prev_loser_val
            raise SemistaticViolation(
                "handle shouldn't be updated, too similar: %s" %
                update_params)

        if loser_delta and reason in ['updating', 'deleting', 'reflect']:
            if loser == self.subordinate_name:
                self.s_deltas = True
            elif loser == self.main_name:
                self.m_deltas = True

        self.updates += 1
        static = self.coldata_class.get_handle_property(
            handle, 'static', loser_target)
        if static:
            self.static = False
        if(reason in ['updating', 'deleting', 'reflect']):
            self.important_updates += 1
            self.important_handles.append(handle)
            if static:
                self.add_problematic_update(**update_params)
                self.important_static = False

        assert \
            prev_old_val_hash == \
            self.snapshot_hash(update_params['old_value']), \
            "should never update old_value"

    def loser_update(self, **update_params):
        for key in ['handle', 'subject', 'old_value', 'new_value']:
            assert key in update_params, \
                'missing mandatory update param, %s from %s' % (
                    key, update_params)

        try:
            self.set_loser_value(**update_params)
        except InvincibilityViolation:
            update_params['reason'] = 'invincible'
        except SemistaticViolation:
            update_params['reason'] = 'semistatic'

        else:
            self.add_sync_warning(**update_params)
            return

        del update_params['subject']
        self.tie_update(**update_params)
        return

    def tie_update(self, **update_params):
        # print "tie_update ", handle, reason
        for key in ['handle']:
            assert update_params[
                key], 'missing mandatory update param, %s' % key
        handle = update_params['handle']
        if self.old_s_object_core:
            update_params['value'] = self.old_s_object_core.get(handle)
        elif self.old_m_object_core:
            update_params['value'] = self.old_s_object_core.get(handle)
        self.add_sync_pass(**update_params)

    def get_handle_mod_time(self, handle, subject):
        return self.get_subject_mod_time(subject)

    def sync_handle(self, **update_params):
        for key in ['handle', 'm_value',
                    's_value', 'm_handle_time', 's_handle_time']:
            assert \
                key in update_params, 'missing mandatory update param %s' % key
        handle = update_params['handle']

        if self.new_handle_identical(handle):
            update_params['reason'] = 'identical'
            self.tie_update(**update_params)
            return

        if self.new_handle_similar(handle):
            update_params['reason'] = 'similar'
            self.tie_update(**update_params)
            return

        winner = None

        main_read = self.coldata_class.get_handle_property(
            handle, 'read', self.main_target)
        subordinate_read = self.coldata_class.get_handle_property(
            handle, 'read', self.subordinate_target)
        # main_write = self.coldata_class.get_handle_property(
        #     handle, 'write', self.main_target)
        # subordinate_write = self.coldata_class.get_handle_property(
        #     handle, 'write', self.subordinate_target)

        if bool(main_read) ^ bool(subordinate_read):
            if not subordinate_read and update_params['m_value']:
                winner = self.main_name
                update_params['reason'] = 'merging-read'
            if not main_read and update_params['s_value']:
                winner = self.subordinate_name
                update_params['reason'] = 'merging-read'

        if not winner:
            winner = self.get_winner_name(
                update_params['m_handle_time'], update_params['s_handle_time']
            )

        if (
            self.merge_mode == 'merge'
            and not (update_params['m_value'] and update_params['s_value'])
        ):
            if winner == self.subordinate_name and not update_params['s_value']:
                winner = self.main_name
                update_params['reason'] = 'merging'
            elif winner == self.main_name and not update_params['m_value']:
                winner = self.subordinate_name
                update_params['reason'] = 'merging'

        if winner == self.subordinate_name:
            update_params['new_value'] = update_params['s_value']
            update_params['old_value'] = update_params['m_value']
        else:
            update_params['new_value'] = update_params['m_value']
            update_params['old_value'] = update_params['s_value']

        if 'reason' not in update_params:
            if not update_params['new_value']:
                update_params['reason'] = 'deleting'
            elif not update_params['old_value']:
                update_params['reason'] = 'inserting'
            else:
                update_params['reason'] = 'updating'

        update_params['subject'] = self.opposite_src(winner)
        self.loser_update(**update_params)

    def update_handle(self, **update_params):
        for key in ['handle']:
            assert \
                update_params[key], 'missing mandatory update param %s' % key
        handle = update_params['handle']

        update_params['m_value'] = self.get_new_subject_value(
            handle, self.main_name
        )
        update_params['s_value'] = self.get_new_subject_value(
            handle, self.subordinate_name
        )
        update_params['m_handle_time'] = self.get_handle_mod_time(
            handle, self.main_name
        )
        update_params['s_handle_time'] = self.get_handle_mod_time(
            handle, self.subordinate_name
        )
        self.sync_handle(**update_params)

    @classmethod
    def get_sync_handles(cls):
        return cls.coldata_class.get_sync_handles(
            cls.main_target, cls.subordinate_target
        )

    def update(self, sync_handles=None):
        # TODO: get rid of reference to "data", just read off coldata instead.
        if sync_handles is None:
            sync_handles = self.get_sync_handles()
        for handle, _ in sync_handles.items():
            self.update_handle(handle=handle)

    def get_info_components(self, info_fmt="%s"):
        return [
            (info_fmt % ("static", "yes" if self.static else "no")),
            (info_fmt % (
                "important_static", "yes" if self.important_static else "no"))
        ]

    def containerize_main(self, main_data):
        main_data_gen = self.coldata_class.translate_data_to(
            deepcopy(main_data), self.object_target)
        if 'rowcount' not in main_data_gen:
            main_data_gen['rowcount'] = 0
        if 'ID' not in main_data_gen:
            main_data_gen['ID'] = ''
        return self.main_container(
            main_data_gen, parent=self.main_parent)

    def containerize_subordinate(self, subordinate_data):
        subordinate_data_gen = self.coldata_class.translate_data_to(
            deepcopy(subordinate_data), self.object_target)
        return self.subordinate_container(subordinate_data_gen, parent=self.subordinate_parent)

    @property
    def old_m_object(self):
        return self.old_m_object_gen
        # return self.containerize_main(self.old_m_object_core)

    @property
    def old_s_object(self):
        return self.old_s_object_gen
        # return self.containerize_main(self.new_m_object_core)

    @property
    def new_m_object(self):
        return self.containerize_main(self.new_m_object_core)

    @property
    def new_s_object(self):
        return self.containerize_subordinate(self.new_s_object_core)

    def tabulate(self, tablefmt=None):
        subtitle_fmt = heading_fmt = "%s"
        info_delimeter = "\n"
        info_fmt = "%s: %s"
        if tablefmt == "html":
            heading_fmt = "<h2>%s</h2>"
            subtitle_fmt = "<h3>%s</h3>"
            info_delimeter = "<br/>"
            info_fmt = "<strong>%s:</strong> %s"
        old_objects = [[], []]
        if self.old_m_object_core:
            old_objects[0] = [self.old_m_object]
        if self.old_s_object_core:
            old_objects[1] = [self.old_s_object]
        old_match = Match(*old_objects)
        out_str = ""
        out_str += heading_fmt % self.__str__()
        out_str += info_delimeter.join([
            subtitle_fmt % "OLD",
            old_match.tabulate(cols=None, tablefmt=tablefmt)
        ])
        out_str += info_delimeter

        if Registrar.DEBUG_UPDATE:
            info_components = self.get_info_components(info_fmt)
            if info_components:
                info_components = [subtitle_fmt % "INFO"] + info_components
                out_str += info_delimeter.join(filter(None, info_components))
                out_str += info_delimeter

        changes_components = []
        if Registrar.DEBUG_UPDATE and not self.important_static:
            changes_components += [
                subtitle_fmt % 'PROBLEMATIC CHANGES (%d)' % len(
                    self.sync_problematics_core),
                self.display_problematic_updates(tablefmt),
            ]
        changes_components += [
            subtitle_fmt % 'CHANGES (%d!%d)' % (
                self.updates, self.important_updates),
            self.display_sync_warnings(tablefmt),
        ]
        if self.m_updated:
            changes_components += [
                subtitle_fmt % '%s CHANGES' % self.main_name,
                self.display_main_changes(tablefmt),
            ]
        if self.s_updated:
            changes_components += [
                subtitle_fmt % '%s CHANGES' % self.subordinate_name,
                self.display_subordinate_changes(tablefmt),
            ]
        out_str += info_delimeter.join(filter(None, changes_components))
        out_str += info_delimeter
        if Registrar.DEBUG_UPDATE or 1:
            passes_components = []
            if self.sync_passes_core:
                passes_components += [
                    subtitle_fmt % "PASSES (%d)" % len(self.sync_passes_core),
                    self.display_sync_passes(tablefmt)
                ]
            out_str += info_delimeter.join(filter(None, passes_components))
            out_str += info_delimeter
        new_objects = [[], []]
        if self.new_m_object_core:
            new_objects[0] = [self.new_m_object]
        if self.new_s_object_core:
            new_objects[1] = [self.new_s_object]
        new_match = Match(*new_objects)
        out_str += info_delimeter
        out_str += info_delimeter.join([
            subtitle_fmt % 'NEW',
            new_match.tabulate(cols=None, tablefmt=tablefmt)
        ])

        return out_str

    def get_subject_updates(self, subject):
        updates_core = OrderedDict()
        for handle, warnings in self.sync_warnings_core.items():
            for warning in warnings:
                loser = warning['subject']
                if loser == subject:
                    updates_core[handle] = warning['new_value']
                #     winner = self.opposite_src(loser)
                #     new_val = self.get_new_subject_value(handle, winner)
                #     updates_core[handle] = new_val
        if self.DEBUG_UPDATE:
            self.register_message(u"returned %s" % text_type(updates_core))
        return updates_core

    def get_subordinate_updates(self):
        return self.get_subject_updates(self.subordinate_name)

    def get_main_updates(self):
        return self.get_subject_updates(self.main_name)

    def get_subordinate_updates_native(self):
        updates_core = self.get_subordinate_updates()
        updates_native = self.coldata_class.translate_data_to(
            updates_core, self.subordinate_target)
        return updates_native

    def get_main_updates_native(self):
        updates_core = self.get_main_updates()
        updates_native = self.coldata_class.translate_data_to(
            updates_core, self.main_target)
        return updates_native

    def display_subordinate_changes(self, tablefmt=None):
        if self.sync_warnings_core:
            info_delimeter = "\n"
            # subtitle_fmt = "%s"
            if tablefmt == "html":
                info_delimeter = "<br/>"
                # subtitle_fmt = "<h4>%s</h4>"

            print_elements = []

            try:
                pkey = self.subordinate_id
                assert pkey, "primary key must be valid, %s" % repr(pkey)
            except Exception as exc:
                print_elements.append(
                    "NO %s CHANGES: must have a primary key to update data: " %
                    self.subordinate_name + repr(exc)
                )
                pkey = None
                return info_delimeter.join(print_elements)

            updates = self.get_subordinate_updates_native()
            additional_updates = OrderedDict()
            if pkey:
                additional_updates['ID'] = pkey

            if updates:
                updates_table = OrderedDict([
                    (key, [value])
                    for key, value
                    in additional_updates.items() + updates.items()
                ])
                print_elements.append(
                    info_delimeter.join([
                        # subtitle_fmt % "all updates" ,
                        tabulate(updates_table, headers="keys",
                                 tablefmt=tablefmt)
                    ])
                )
                # print_elements.append(updates_json_base64)
                # return (pkey, all_updates_json_base64)
            else:
                print_elements.append(
                    "NO %s CHANGES: no user_updates or meta_updates"
                    % self.subordinate_name)

            return info_delimeter.join(print_elements)
        return ""

    def display_main_changes(self, tablefmt=None):
        if self.sync_warnings_core:
            info_delimeter = "\n"
            # subtitle_fmt = "%s"
            if tablefmt == "html":
                info_delimeter = "<br/>"
                # subtitle_fmt = "<h4>%s</h4>"

            print_elements = []

            try:
                pkey = self.main_id
                assert pkey, "primary key must be valid, %s" % repr(pkey)
            except Exception as exc:
                print_elements.append(
                    ("NO %s CHANGES: "
                     "must have a primary key to update data: ") %
                    self.main_name + repr(exc))
                pkey = None
                return info_delimeter.join(print_elements)

            updates = self.get_main_updates()
            additional_updates = OrderedDict()
            if pkey:
                additional_updates['ID'] = pkey

            if updates:
                updates_table = OrderedDict([
                    (key, [value])
                    for key, value
                    in additional_updates.items() + updates.items()
                ])
                print_elements.append(
                    info_delimeter.join([
                        # subtitle_fmt % "changes" ,
                        tabulate(updates_table, headers="keys",
                                 tablefmt=tablefmt)
                    ])
                )
                # print_elements.append(updates_json_base64)
                # return (pkey, all_updates_json_base64)
            else:
                print_elements.append(
                    "NO %s CHANGES: no user_updates or meta_updates"
                    % self.main_name)

            return info_delimeter.join(print_elements)
        return ""

    def update_main(self, client):
        raise DeprecationWarning("calling syncupate.update* is deprecated")
        updates = self.get_main_updates()
        if not updates:
            return

        pkey = self.main_id
        return client.upload_changes(pkey, updates)

        # todo: Determine if file imported correctly and delete file

    def update_subordinate(self, client):
        raise DeprecationWarning("calling syncupate.update* is deprecated")
        # SanitationUtils.safe_print(  self.display_subordinate_changes() )
        updates = self.get_subordinate_updates_native()
        if not updates:
            return

        pkey = self.subordinate_id

        return client.upload_changes(pkey, updates)

    def __cmp__(self, other):
        return -cmp(self.b_time, other.b_time)

    def __str__(self):
        return "update < %7s | %7s >" % (self.main_id, self.subordinate_id)

    def __nonzero__(self):
        return self.e_updated


class SyncUpdateGen(SyncUpdate):
    """
    Abstract class for when sync main is in generator format.
    """
    main_target = 'gen-api'
    merge_mode = 'merge'

    @property
    def main_id(self):
        return self.get_new_subject_value('rowcount', self.main_name)


class SyncUpdateProd(SyncUpdateGen):
    """
    Abstract class for product updates
    """
    coldata_class = ColDataProductMeridian

    def __init__(self, *args, **kwargs):
        super(SyncUpdateProd, self).__init__(*args, **kwargs)

    @property
    def subordinate_id(self):
        return self.get_new_subject_value('id', self.subordinate_name)


class SyncUpdateWooMixin(object):
    subordinate_target = 'wc-wp-api-v2-edit'


class SyncUpdateProdWoo(SyncUpdateProd, SyncUpdateWooMixin):
    coldata_class = SyncUpdateProd.coldata_class
    subordinate_target = SyncUpdateWooMixin.subordinate_target


class SyncUpdateProdXero(SyncUpdateProd):
    coldata_class = SyncUpdateProd.coldata_class
    subordinate_target = 'xero-api'

    @property
    def subordinate_id(self):
        return self.get_new_subject_value('xero_id', self.subordinate_name)


class SyncUpdateVarWoo(SyncUpdateProdWoo):
    coldata_class = ColDataProductVariationMeridian

    @property
    def main_id(self):
        if not self.old_m_object_gen:
            return
        old_m_object_gen = self.old_m_object_gen
        return old_m_object_gen.variation_indexer(old_m_object_gen)


class SyncUpdateImgWoo(SyncUpdateGen, SyncUpdateWooMixin):
    coldata_class = ColDataAttachment
    subordinate_target = SyncUpdateWooMixin.subordinate_target

    @property
    def main_id(self):
        if not self.old_m_object_gen:
            return
        old_m_object_gen = self.old_m_object_gen
        return old_m_object_gen.attachment_indexer(old_m_object_gen)

    @property
    def subordinate_id(self):
        return self.get_new_subject_value('id', self.subordinate_name)


class SyncUpdateCatWoo(SyncUpdateGen, SyncUpdateWooMixin):
    coldata_class = ColDataWcProdCategory
    subordinate_target = SyncUpdateWooMixin.subordinate_target
    default_main_container = ImportWooCategory
    default_subordinate_container = ImportWooApiCategory

    @property
    def subordinate_id(self):
        return self.get_new_subject_value('term_id', self.subordinate_name)


class UpdateList(list, Registrar):
    """
    Mutable sequence of sync updates which is unique on update index.
    A list of update indices is kept which is modified whenever the update list
    is modified so that updates can be retrieved by index
    """
    supported_type = SyncUpdate

    def __init__(self, updates=None):
        list.__init__(self)
        Registrar.__init__(self)
        self.indices = []
        if updates:
            self.extend(updates)

    def indexer(self, sync_update):
        return sync_update.index

    def append(self, sync_update):
        assert issubclass(sync_update.__class__, self.supported_type), \
            "object must be subclass of %s not %s" % (
            str(self.supported_type.__name__), str(sync_update.__class__))
        index = self.indexer(sync_update)
        if index not in self.indices:
            self.indices.append(index)
            return list.append(self, sync_update)

    def extend(self, updates):
        for obj in updates:
            return self.append(obj)

    def pop(self, index):
        self.indices.pop(index)
        return list.pop(self, index)

    def __setitem__(self, key, value):
        index = self.indexer(value)
        self.indices.__setitem__(key, index)
        return list.__setitem__(self, key, value)

    def __delitem__(self, key):
        self.indices.__delitem__(key)
        return list.__delitem__(self, key)

    def get_by_index(self, index):
        return self[self.indices.index(index)]

    def get_by_ids(self, main_id='', subordinate_id=''):
        index = self.supported_type.make_index(main_id, subordinate_id)
        return self.get_by_index(index)

    def tabulate(self, cols=None, tablefmt=None, highlight_rules=None):
        """
        Returns a string that contains a representation of the updates in the
        table format specified
        """

        prefix, suffix = "", ""
        delimeter = "\n"
        if tablefmt == 'html':
            delimeter = ''
            prefix = '<div class="updateList">'
            suffix = '</div>'
        return prefix + delimeter.join([
            SanitationUtils.coerce_bytes(update.tabulate(tablefmt=tablefmt))
            for update in self if update
        ]) + suffix
