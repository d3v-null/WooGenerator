"""
Utilites for storing and performing operations on pending updates
"""

from __future__ import absolute_import

import traceback
from collections import OrderedDict
from copy import copy, deepcopy

from tabulate import tabulate

from .coldata import (ColDataAbstract, ColDataAttachment,
                      ColDataProductMeridian, ColDataProductVariationMeridian,
                      ColDataWcProdCategory, ColDataWcProdCategory)
# from .coldata import ColDataBase, ColDataProd, ColDataUser, ColDataWoo, ColDataXero, ColDataAttachment
from .contact_objects import ContactAddress, FieldGroup
from .matching import Match
from .parsing.abstract import ImportObject
from .utils import Registrar, SanitationUtils, TimeUtils
from .parsing.api import ImportWooApiCategory
from .parsing.woo import ImportWooCategory



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
    master_target = None
    slave_target = None
    # The target format of (m|s)_object, which gets immediately converted to core
    object_target = 'gen-api'
    default_master_container = ImportObject
    default_slave_container = ImportObject

    @classmethod
    def set_globals(cls, merge_mode, default_last_sync):
        """
        sets the class attributes to those specified in the user config
        """
        # TODO: Fix this awful mess
        cls.merge_mode = merge_mode
        cls.default_last_sync = default_last_sync

    def __init__(self, old_m_object_gen=None, old_s_object_gen=None, lastSync=None):
        super(SyncUpdate, self).__init__()


        if not lastSync:
            lastSync = self.default_last_sync
        # print "Creating SyncUpdate: ", old_m_object_core.__repr__(),
        # old_s_object_core.__repr__()
        self.old_m_object_core = {}
        self.old_s_object_core = {}
        self.new_s_object_core = {}
        self.new_m_object_core = {}
        self.master_parent = None
        self.slave_parent = None
        self.master_container = self.default_master_container
        self.slave_container = self.default_slave_container
        self.m_time = 0
        self.s_time = 0
        if old_m_object_gen:
            self.set_old_m_object_gen(old_m_object_gen)
        if old_s_object_gen:
            self.set_old_s_object_gen(old_s_object_gen)
        self.t_time = TimeUtils.wp_strp_mktime(lastSync)
        self.static = True
        self.important_static = True
        self.sync_warnings_core = OrderedDict()
        self.sync_passes_core = OrderedDict()
        self.sync_problematics_core = OrderedDict()
        self.updates = 0
        self.important_updates = 0
        self.important_handles = []
        self.m_deltas = False
        self.s_deltas = False

        self.b_time = 0

    def set_old_m_object_gen(self, old_m_object_gen):
        self.old_m_object_gen = old_m_object_gen
        self.master_container = type(self.old_m_object_gen)
        assert issubclass(self.master_container, ImportObject)
        self.master_parent = self.old_m_object_gen.parent
        self.old_m_object_core = self.coldata_class.translate_data_from(
            self.old_m_object_gen.to_dict(), self.object_target
        )
        if self.old_m_object_core.get('modified_gmt'):
            self.m_time = self.parse_m_time(self.old_m_object_core['modified_gmt'])

    def set_old_s_object_gen(self, old_s_object_gen):
        self.old_s_object_gen = old_s_object_gen
        self.slave_container = type(self.old_s_object_gen)
        assert issubclass(self.slave_container, ImportObject)
        self.slave_parent = self.old_s_object_gen.parent
        self.old_s_object_core = self.coldata_class.translate_data_from(
            self.old_s_object_gen.to_dict(), self.object_target
        )
        if self.old_s_object_core.get('modified_gmt'):
            self.s_time = self.parse_s_time(self.old_s_object_core['modified_gmt'])

    def set_new_m_object_gen(self, new_m_object_gen):
        self.master_container = type(new_m_object_gen)
        assert issubclass(self.master_container, ImportObject)
        self.master_parent = new_m_object_gen.parent
        new_m_object_core = self.coldata_class.translate_data_from(
            new_m_object_gen.to_dict(), self.object_target
        )
        self.set_new_subject_object(new_m_object_core, self.master_name)

    def set_new_s_object_gen(self, new_s_object_gen):
        self.slave_container = type(new_s_object_gen)
        assert issubclass(self.master_container, ImportObject)
        self.slave_parent = new_s_object_gen.parent
        new_s_object_core = self.coldata_class.translate_data_from(
            new_s_object_gen.to_dict(), self.object_target
        )
        self.set_new_subject_object(new_s_object_core, self.slave_name)

    @property
    def sync_warnings(self):
        return self.coldata_class.translate_keys(
            self.sync_warnings_core, self.object_target
        )

    @property
    def sync_passes(self):
        return self.coldata_class.translate_keys(
            self.sync_passes_core, self.object_target
        )

    @property
    def sync_problematics(self):
        return self.coldata_class.translate_keys(
            self.sync_problematics_core, self.object_target
        )

    @property
    def s_updated(self):
        """Return whether slave has been updated."""
        return bool(self.new_s_object_core)

    @property
    def m_updated(self):
        """Return whether master has been updated."""
        return bool(self.new_m_object_core)

    @property
    def e_updated(self):
        """Return whether either master or slave has updated."""
        return self.s_updated or self.m_updated

    @property
    def l_time(self):
        """Return latest modtime out of master and slave."""
        return max(self.m_time, self.s_time)

    def get_subject_mod_time(self, subject):
        """Return the modtime of a subject."""
        if subject == self.master_name:
            return self.m_time
        elif subject == self.slave_name:
            return self.s_time

    def get_new_subject_object(self, subject):
        """Return the new object associated with the subject."""
        if subject == self.master_name:
            return self.new_m_object_core
        elif subject == self.slave_name:
            return self.new_s_object_core

    def set_new_subject_object(self, value, subject):
        if subject == self.master_name:
            self.new_m_object_core = value
        elif subject == self.slave_name:
            self.new_s_object_core = value

    def get_old_subject_object(self, subject):
        """Return the new object associated with the subject."""
        if subject == self.master_name:
            return self.old_m_object_core
        elif subject == self.slave_name:
            return self.old_s_object_core

    @property
    def m_mod(self):
        """Return whether has been updated since last sync."""
        return self.m_time >= self.t_time

    @property
    def s_mod(self):
        """Return whether slave has been updated since last sync."""
        return self.s_time >= self.t_time

    @property
    def master_id(self):
        """Abstract method fo getting the ID of the master object."""
        raise NotImplementedError()

    @property
    def slave_id(self):
        """Abstract method fo getting the ID of the slave object."""
        raise NotImplementedError()

    def get_winner_name(self, m_time, s_time):
        """Get the name of the database containing the winning object (master / slave)."""
        if not s_time:
            return self.master_name
        elif not m_time:
            return self.slave_name
        else:
            return self.slave_name if(s_time >= m_time) else self.master_name

    @classmethod
    def parse_m_time(cls, raw_m_time):
        """Parse a raw master time value into a timestamp."""
        return TimeUtils.datetime2timestamp(raw_m_time)
        # return raw_m_time

    @classmethod
    def parse_s_time(cls, raw_s_time):
        """Parse a raw slave time value into a timestamp."""
        return TimeUtils.datetime2timestamp(raw_s_time)
        # return raw_s_time

    def parse_subject_time(self, raw_time, subject):
        """Parse a raw time string for a given subject's format."""
        if subject == self.master_name:
            return self.parse_m_time(raw_time)
        elif subject == self.slave_name:
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
        if subject == self.master_name:
            return self.master_target
        elif subject == self.slave_name:
            return self.slave_target

    def values_similar(self, handle, m_value, s_value):
        """Check if two values are similar. Depends on handle."""
        response = False
        if not (m_value or s_value):
            response = True
        elif not (m_value and s_value):
            response = False
        # check if they are similar
        # if hasattr(m_value, 'reprocess_kwargs') and m_value.reprocess_kwargs:
        # if handle == 'Role Info':
        if hasattr(m_value, 'similar') and callable(m_value.similar):
            response = m_value.similar(s_value)
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
        """For given handle, check if the master value is similar to the slave value in old objects."""
        m_value = self.get_old_subject_value(handle, self.master_name)
        s_value = self.get_old_subject_value(handle, self.slave_name)
        response = m_value == s_value
        if self.DEBUG_UPDATE:
            self.register_message(
                self.test_to_str(
                    handle, m_value, s_value, response))
        return response

    def new_handle_similar(self, handle):
        """For given handle, check if the master value is similar to the slave value in new objects."""
        m_value = self.get_new_subject_value(handle, self.master_name)
        s_value = self.get_new_subject_value(handle, self.slave_name)
        response = self.values_similar(handle, m_value, s_value)
        if self.DEBUG_UPDATE:
            self.register_message(
                self.test_to_str(
                    handle, m_value, s_value, response))
        return response

    def new_handle_identical(self, handle):
        """For given handle, check if the master value is equal to the slave value in new objects."""
        m_value = self.get_new_subject_value(handle, self.master_name)
        s_value = self.get_new_subject_value(handle, self.slave_name)
        response = m_value == s_value
        if self.DEBUG_UPDATE:
            self.register_message(
                self.test_to_str(
                    handle, m_value, s_value, response))
        return response

    def col_static(self, handle, subject):
        """For given handle, check if the old value is similar to the new value in subject."""
        o_value = self.get_old_subject_value(handle, subject)
        n_value = self.get_new_subject_value(handle, subject)
        response = o_value == n_value
        if self.DEBUG_UPDATE:
            self.register_message(
                self.test_to_str(
                    handle, o_value, n_value, response))
        return response

    def col_semi_static(self, handle, subject):
        """For given handle, check if the old value is equal to the new value in subject."""
        o_value = self.get_old_subject_value(handle, subject)
        n_value = self.get_new_subject_value(handle, subject)
        response = self.values_similar(handle, o_value, n_value)
        if self.DEBUG_UPDATE:
            self.register_message(
                self.test_to_str(
                    handle, o_value, n_value, response))
        return response

    def m_handle_static(self, handle):
        """For given handle, check if the old value is equal to the new value in master."""
        # TODO: deprecate this
        return self.col_static(handle, self.master_name)

    def s_handle_static(self, handle):
        """For given handle, check if the old value is equal to the new value in slave."""
        # TODO: deprecate this
        return self.col_static(handle, self.slave_name)

    def m_handle_semi_static(self, handle):
        """For given handle, check if the old value is similar to the new value in master."""
        # TODO: deprecate this
        return self.col_semi_static(handle, self.master_name)

    def s_handle_semi_static(self, handle):
        """For given handle, check if the old value is similar to the new value in slave."""
        # TODO: deprecate this
        return self.col_semi_static(handle, self.slave_name)

    def test_to_str(self, handle, val1, val2, res, norm1=None, norm2=None):
        left = repr(val1)
        if norm1 is not None and norm1 != val1:
            left += " (%s %s)" % (norm1, type(norm1))
        right = repr(val2)
        if norm2 is not None and norm2 != val2:
            right += " (%s %s)" % (norm2, type(norm2))

        return u"testing handle %s: %s | %s -> %s" % (
            unicode(handle),
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
                ('m_value', 'Master'),
                ('s_value', 'Slave'),
            ]
        elif update_type == 'reflect':
            header_items += [
                ('m_value', 'Master'),
                ('s_value', 'Slave'),
                ('reflected_master', 'Reflected Master'),
                ('reflected_slave', 'Reflected Slave'),
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
    #     if(winner == self.master_name):
    #         oldLoserObject = self.old_s_object_core

    def opposite_src(self, subject):
        if subject == self.master_name:
            return self.slave_name
        elif subject == self.slave_name:
            return self.master_name
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
            assert key in update_params, 'missing mandatory update param, %s from %s' % (
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
        loser_delta = self.coldata_class.get_handle_property(handle, 'delta', loser_target)
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
            if loser == self.slave_name:
                self.s_deltas = True
            elif loser == self.master_name:
                self.m_deltas = True

        self.updates += 1
        static = self.coldata_class.get_handle_property(handle, 'static', loser_target)
        if static:
            self.static = False
        if(reason in ['updating', 'deleting', 'reflect']):
            self.important_updates += 1
            self.important_handles.append(handle)
            if static:
                self.add_problematic_update(**update_params)
                self.important_static = False

        assert \
            prev_old_val_hash == self.snapshot_hash(update_params['old_value']), \
            "should never update old_value"

    def loser_update(self, **update_params):
        for key in ['handle', 'subject', 'old_value', 'new_value']:
            assert key in update_params, 'missing mandatory update param, %s from %s' % (
                key, update_params)

        try:
            self.set_loser_value(**update_params)
        except InvincibilityViolation:
            update_params['reason'] = 'invincible'
        except SemistaticViolation:
            update_params['reason'] = 'semistatic'
        # except Exception as exc:
        #     raise UserWarning("Unhandled Exception in set_loser_value:\n%s" % (
        #         traceback.format_exc(exc)
        #     ))
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

        master_read = self.coldata_class.get_handle_property(handle, 'read', self.master_target)
        slave_read = self.coldata_class.get_handle_property(handle, 'read', self.slave_target)
        # master_write = self.coldata_class.get_handle_property(handle, 'write', self.master_target)
        # slave_write = self.coldata_class.get_handle_property(handle, 'write', self.slave_target)

        if bool(master_read) ^ bool(slave_read):
            if not slave_read and update_params['m_value']:
                winner = self.master_name
                update_params['reason'] = 'merging-read'
            if not master_read and update_params['s_value']:
                winner = self.slave_name
                update_params['reason'] = 'merging-read'

        if not winner:
            winner = self.get_winner_name(
                update_params['m_handle_time'], update_params['s_handle_time']
            )

        if self.merge_mode == 'merge' \
        and not (update_params['m_value'] and update_params['s_value']):
            if winner == self.slave_name and not update_params['s_value']:
                winner = self.master_name
                update_params['reason'] = 'merging'
            elif winner == self.master_name and not update_params['m_value']:
                winner = self.slave_name
                update_params['reason'] = 'merging'

        if winner == self.slave_name:
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
            handle, self.master_name
        )
        update_params['s_value'] = self.get_new_subject_value(
            handle, self.slave_name
        )
        update_params['m_handle_time'] = self.get_handle_mod_time(
            handle, self.master_name
        )
        update_params['s_handle_time'] = self.get_handle_mod_time(
            handle, self.slave_name
        )
        self.sync_handle(**update_params)

    @classmethod
    def get_sync_handles(cls):
        return cls.coldata_class.get_sync_handles(
            cls.master_target, cls.slave_target
        )

    def update(self, sync_handles=None):
        # TODO: get rid of reference to "data", and just read off coldata instead.
        if sync_handles is None:
            sync_handles = self.get_sync_handles()
        for handle, _ in sync_handles.items():
            self.update_handle(handle=handle)

    def get_info_components(self, info_fmt="%s"):
        return [
            (info_fmt % ("static", "yes" if self.static else "no")),
            (info_fmt % ("important_static", "yes" if self.important_static else "no"))
        ]

    def containerize_master(self, master_data):
        master_data_gen = self.coldata_class.translate_data_to(deepcopy(master_data), self.object_target)
        return self.master_container(master_data_gen, parent=self.master_parent)

    def containerize_slave(self, slave_data):
        slave_data_gen = self.coldata_class.translate_data_to(deepcopy(slave_data), self.object_target)
        return self.slave_container(slave_data_gen, parent=self.slave_parent)

    @property
    def old_m_object(self):
        return self.old_m_object_gen
        # return self.containerize_master(self.old_m_object_core)

    @property
    def new_m_object(self):
        return self.old_s_object_gen
        # return self.containerize_master(self.new_m_object_core)

    @property
    def old_s_object(self):
        return self.containerize_slave(self.old_s_object_core)

    @property
    def new_s_object(self):
        return self.containerize_slave(self.new_s_object_core)

    def tabulate(self, tablefmt=None):
        subtitle_fmt = heading_fmt = "%s"
        info_delimeter = "\n"
        info_fmt = "%s: %s"
        if tablefmt == "html":
            heading_fmt = "<h2>%s</h2>"
            subtitle_fmt = "<h3>%s</h3>"
            info_delimeter = "<br/>"
            info_fmt = "<strong>%s:</strong> %s"
        old_match = Match(
            [self.old_m_object],
            [self.old_s_object]
        )
        # if self.DEBUG_UPDATE:
        #     self.register_message(old_match.__str__())
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
                subtitle_fmt % '%s CHANGES' % self.master_name,
                self.display_master_changes(tablefmt),
            ]
        if self.s_updated:
            changes_components += [
                subtitle_fmt % '%s CHANGES' % self.slave_name,
                self.display_slave_changes(tablefmt),
            ]
        out_str += info_delimeter.join(filter(None, changes_components))
        out_str += info_delimeter
        if Registrar.DEBUG_UPDATE:
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
                    winner = self.opposite_src(loser)
                    new_val = self.get_new_subject_value(handle, winner)
                    updates_core[handle] = new_val
        if self.DEBUG_UPDATE:
            self.register_message(u"returned %s" % unicode(updates_core))
        return updates_core

    def get_slave_updates(self):
        return self.get_subject_updates(self.slave_name)

    def get_master_updates(self):
        return self.get_subject_updates(self.master_name)

    def get_slave_updates_native(self):
        updates_core = self.get_slave_updates()
        updates_native = self.coldata_class.translate_data_to(updates_core, self.slave_target)
        if self.DEBUG_UPDATE:
            self.register_message(u"returned %s" % unicode(updates_native))
        return updates_native

    def display_slave_changes(self, tablefmt=None):
        if self.sync_warnings_core:
            info_delimeter = "\n"
            # subtitle_fmt = "%s"
            if tablefmt == "html":
                info_delimeter = "<br/>"
                # subtitle_fmt = "<h4>%s</h4>"

            print_elements = []

            try:
                pkey = self.slave_id
                assert pkey, "primary key must be valid, %s" % repr(pkey)
            except Exception as exc:
                print_elements.append(
                    "NO %s CHANGES: must have a primary key to update user data: " %
                    self.slave_name + repr(exc)
                )
                pkey = None
                return info_delimeter.join(print_elements)

            updates = self.get_slave_updates_native()
            additional_updates = OrderedDict()
            if pkey:
                additional_updates['ID'] = pkey

            if updates:
                updates_table = OrderedDict(
                    [(key, [value]) for key, value in additional_updates.items() + updates.items()])
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
                    "NO %s CHANGES: no user_updates or meta_updates" % self.slave_name)

            return info_delimeter.join(print_elements)
        return ""

    def display_master_changes(self, tablefmt=None):
        if self.sync_warnings_core:
            info_delimeter = "\n"
            # subtitle_fmt = "%s"
            if tablefmt == "html":
                info_delimeter = "<br/>"
                # subtitle_fmt = "<h4>%s</h4>"

            print_elements = []

            try:
                pkey = self.master_id
                assert pkey, "primary key must be valid, %s" % repr(pkey)
            except Exception as exc:
                print_elements.append(
                    ("NO %s CHANGES: "
                     "must have a primary key to update user data: ") %
                    self.master_name + repr(exc))
                pkey = None
                return info_delimeter.join(print_elements)

            updates = self.get_master_updates()
            additional_updates = OrderedDict()
            if pkey:
                additional_updates['ID'] = pkey

            if updates:
                updates_table = OrderedDict(
                    [(key, [value]) for key, value in additional_updates.items() + updates.items()])
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
                    "NO %s CHANGES: no user_updates or meta_updates" % self.master_name)

            return info_delimeter.join(print_elements)
        return ""

    def update_master(self, client):
        raise DeprecationWarning("calling syncupate.update* is deprecated")
        updates = self.get_master_updates()
        if not updates:
            return

        pkey = self.master_id
        return client.upload_changes(pkey, updates)

        # todo: Determine if file imported correctly and delete file

    def update_slave(self, client):
        raise DeprecationWarning("calling syncupate.update* is deprecated")
        # SanitationUtils.safe_print(  self.display_slave_changes() )
        updates = self.get_slave_updates_native()
        if not updates:
            return

        pkey = self.slave_id

        return client.upload_changes(pkey, updates)

    def __cmp__(self, other):
        return -cmp(self.b_time, other.b_time)
        # return -cmp((self.important_updates, self.updates, - self.l_time),
        # (other.important_updates, other.updates, - other.l_time))

    def __str__(self):
        return "update < %7s | %7s >" % (self.master_id, self.slave_id)

    def __nonzero__(self):
        return self.e_updated


# class SyncUpdateUsr(SyncUpdate):
#     coldata_class = ColDataUser
#     slave_target = 'wp'
#     master_target = 'act'
#
#     def __init__(self, *args, **kwargs):
#         super(SyncUpdateUsr, self).__init__(*args, **kwargs)
#
#         self.m_time = self.old_m_object_core.act_modtime
#         self.s_time = self.old_s_object_core.wp_modtime
#         self.b_time = self.old_m_object_core.last_sale
#         self.winner = self.get_winner_name(self.m_time, self.s_time)
#
#         # extra heuristics for merge mode:
#         if self.merge_mode == 'merge' and not self.s_mod:
#             might_be_s_edited = False
#             if not self.old_s_object_core.addresses_act_like():
#                 might_be_s_edited = True
#             elif self.old_s_object_core.get('Home Country') == 'AU':
#                 might_be_s_edited = True
#             elif self.old_s_object_core.username_act_like():
#                 might_be_s_edited = True
#             if might_be_s_edited:
#                 # print repr(self.old_s_object_core), "might be edited"
#                 self.s_time = self.t_time
#                 if self.m_mod:
#                     self.static = False
#                     # self.important_static = False
#
#     @property
#     def master_id(self):
#         return self.get_new_subject_value('MYOB Card ID', self.master_name)
#
#     @property
#     def slave_id(self):
#         return self.get_new_subject_value("Wordpress ID", self.slave_name)
#
#     def values_similar(self, handle, m_value, s_value):
#         response = super(SyncUpdateUsr, self).values_similar(
#             handle, m_value, s_value)
#         if not response:
#             if handle.lower() in ['phone', 'mobile phone', 'home phone', 'fax']:
#                 m_phone = SanitationUtils.similar_phone_comparison(m_value)
#                 s_phone = SanitationUtils.similar_phone_comparison(s_value)
#                 plen = min(len(m_phone), len(s_phone))
#                 if plen > 7 and m_phone[-plen:] == s_phone[-plen:]:
#                     response = True
#             elif "role" == handle.lower():
#                 m_role = SanitationUtils.similar_comparison(m_value)
#                 s_role = SanitationUtils.similar_comparison(s_value)
#                 if m_role == 'rn':
#                     m_role = ''
#                 if s_role == 'rn':
#                     s_role = ''
#                 if m_role == s_role:
#                     response = True
#             elif "address" in handle.lower() and isinstance(m_value, ContactAddress):
#                 if m_value != s_value:
#                     pass
#                     # print "M: ", m_value.__str__(out_schema="flat"), "S: ",
#                     # s_value.__str__(out_schema="flat")
#                 response = m_value.similar(s_value)
#             elif "web site" in handle.lower():
#                 if SanitationUtils.similar_url_comparison(
#                         m_value) == SanitationUtils.similar_url_comparison(s_value):
#                     response = True
#
#         # if self.DEBUG_UPDATE:
#         #     self.register_message(self.test_to_str(
#         #         handle,
#         #         SanitationUtils.coerce_unicode(m_value),
#         #         SanitationUtils.coerce_unicode(s_value),
#         #         response
#         #     ))
#         return response
#
#     def get_handle_mod_time(self, handle, subject):
#         response = self.get_subject_mod_time(subject)
#         if subject == self.master_name:
#             tracked_handles_items = self.coldata_class.get_master_tracked_handles().items()
#             future_tracked_handles_items = self.coldata_class.get_act_future_tracked_handles().items()
#             old_object = self.old_m_object_core
#         elif subject == self.slave_name:
#             tracked_handles_items = self.coldata_class.get_wp_tracked_handles().items()
#             future_tracked_handles_items = []
#             old_object = self.old_s_object_core
#
#         if self.coldata_class.data.get(handle, {}).get('tracked'):
#             col_tracking_name = self.coldata_class.mod_time_handle(handle)
#         else:
#             col_tracking_name = None
#             for tracking_name, tracked_handles in tracked_handles_items:
#                 if handle in tracked_handles:
#                     col_tracking_name = tracking_name
#
#         if col_tracking_name:
#             if old_object.get(col_tracking_name):
#                 response = self.parse_subject_time(
#                     old_object.get(col_tracking_name), subject
#                 )
#             elif col_tracking_name not in future_tracked_handles_items:
#                 response = None
#         return response
#
#     def get_info_components(self, info_fmt="%s"):
#         info_components = super(
#             SyncUpdateUsr, self).get_info_components(info_fmt)
#         info_components += [
#             (info_fmt % ("Last Sale", TimeUtils.wp_time_to_string(
#                 self.b_time))) if self.b_time else "No Last Sale",
#             (info_fmt % ("%s Mod Time" % self.master_name, TimeUtils.wp_time_to_string(
#                 self.m_time))) if self.m_mod else "%s Not Modded" % self.master_name,
#             (info_fmt % ("%s Mod Time" % self.slave_name, TimeUtils.wp_time_to_string(
#                 self.s_time))) if self.s_mod else "%s Not Modded" % self.slave_name
#         ]
#         for tracking_name, cols in self.coldata_class.get_act_tracked_handles().items():
#             handle = cols[0]
#             m_handle_mod_time = self.get_handle_mod_time(handle, self.master_name)
#             s_handle_mod_time = self.get_handle_mod_time(handle, self.slave_name)
#             if m_handle_mod_time or s_handle_mod_time:
#                 info_components.append(info_fmt % (tracking_name, '%s: %s; %s: %s' % (
#                     self.master_name,
#                     TimeUtils.wp_time_to_string(m_handle_mod_time),
#                     self.slave_name,
#                     TimeUtils.wp_time_to_string(s_handle_mod_time),
#                 )))
#         return info_components
#
#     def get_slave_updates_native_rec(self, handle, updates=None):
#         if updates is None:
#             updates = OrderedDict()
#         if self.DEBUG_UPDATE:
#             SanitationUtils.safe_print(
#                 "getting updates for handle %s, updates: %s" % (handle, str(updates)))
#         if handle in self.coldata_class.data.keys():
#             data = self.coldata_class.data[handle]
#             if data.get(self.slave_target):
#                 data_target = data.get(self.slave_target, {})
#                 if not data_target.get('final') and data_target.get('key'):
#                     updates[data_target.get(
#                         'key')] = self.new_s_object_core.get(handle)
#             if data.get('aliases'):
#                 data_aliases = data.get('aliases')
#                 for alias in data_aliases:
#                     if self.s_handle_semi_static(alias):
#                         continue
#                     updates = self.get_slave_updates_native_rec(
#                         alias, updates)
#         return updates
#
#     def get_slave_updates_recursive(self, handle, updates=None):
#         if updates is None:
#             updates = OrderedDict()
#         if self.DEBUG_UPDATE:
#             self.register_message(u"checking %s" % unicode(handle))
#         if handle in self.coldata_class.data:
#             if self.DEBUG_UPDATE:
#                 self.register_message(u"handle exists")
#             data = self.coldata_class.data[handle]
#             if data.get(self.slave_target):
#                 if self.DEBUG_UPDATE:
#                     self.register_message(u"target exists")
#                 data_target = data.get(self.slave_target, {})
#                 if not data_target.get('final') and data_target.get('key'):
#                     new_val = self.new_s_object_core.get(handle)
#                     updates[handle] = new_val
#                     if self.DEBUG_UPDATE:
#                         self.register_message(u"newval: %s" % repr(new_val))
#             if data.get('aliases'):
#                 if self.DEBUG_UPDATE:
#                     self.register_message(u"has aliases")
#                 data_aliases = data['aliases']
#                 for alias in data_aliases:
#                     if self.s_handle_semi_static(alias):
#                         if self.DEBUG_UPDATE:
#                             self.register_message(u"Alias semistatic")
#                         continue
#                     else:
#                         updates = self.get_slave_updates_recursive(
#                             alias, updates)
#         else:
#             if self.DEBUG_UPDATE:
#                 self.register_message(u"handle doesn't exist")
#         return updates
#
#     def get_master_updates_recursive(self, handle, updates=None):
#         if updates is None:
#             updates = OrderedDict()
#         if self.DEBUG_UPDATE:
#             self.register_message(u"checking %s" % unicode(handle))
#         if handle in self.coldata_class.data:
#             if self.DEBUG_UPDATE:
#                 self.register_message(u"handle exists")
#             data = self.coldata_class.data[handle]
#             if self.DEBUG_UPDATE:
#                 self.register_message(u"data: %s, target: %s" % (
#                     data, self.master_target
#                 ))
#             if data.get(self.master_target):
#                 if self.DEBUG_UPDATE:
#                     self.register_message(u"target exists")
#                 new_val = self.new_m_object_core.get(handle)
#                 updates[handle] = new_val
#                 if self.DEBUG_UPDATE:
#                     self.register_message(u"newval: %s" % repr(new_val))
#             if data.get('aliases'):
#                 if self.DEBUG_UPDATE:
#                     self.register_message(u"has aliases")
#                 data_aliases = data['aliases']
#                 for alias in data_aliases:
#                     if self.m_handle_semi_static(alias):
#                         if self.DEBUG_UPDATE:
#                             self.register_message(u"Alias semistatic")
#                         continue
#                     else:
#                         updates = self.get_master_updates_recursive(
#                             alias, updates)
#         else:
#             if self.DEBUG_UPDATE:
#                 self.register_message(u"handle doesn't exist")
#         return updates
#
#
# class SyncUpdateUsrApi(SyncUpdateUsr):
#     slave_target = 'wp-api'
#
#     def s_validate_handle(self, handle, value):
#         # TODO: Probably need more validation here
#         if handle.lower() in ['e-mail']:
#             if not value:
#                 raise UserWarning("email does not look right")
#         return value
#
#     def get_slave_updates_native_rec(self, handle, updates=None):
#         if updates is None:
#             updates = OrderedDict()
#         if self.DEBUG_UPDATE:
#             self.register_message(u"checking %s : %s" %
#                                   (unicode(handle), self.coldata_class.data.get(handle)))
#         if handle in self.coldata_class.data:
#             if self.DEBUG_UPDATE:
#                 self.register_message(u"handle exists")
#             data = self.coldata_class.data[handle]
#             if data.get(self.slave_target):
#                 if self.DEBUG_UPDATE:
#                     self.register_message(u"wp-api exists")
#                 data_target = data.get(self.slave_target, {})
#                 if not data_target.get('final') and data_target.get('key'):
#                     new_val = self.new_s_object_core.get(handle)
#                     try:
#                         new_val = self.s_validate_handle(handle, new_val)
#                     except UserWarning:
#                         return updates
#                     new_key = handle
#                     if 'key' in data_target:
#                         new_key = data_target.get('key')
#                     if data_target.get('meta'):
#                         if 'meta' not in updates:
#                             updates['meta'] = OrderedDict()
#                         updates['meta'][new_key] = new_val
#                     else:
#                         updates[new_key] = new_val
#                     if self.DEBUG_UPDATE:
#                         self.register_message(u"newval: %s" % repr(new_val))
#                     if self.DEBUG_UPDATE:
#                         self.register_message(u"newkey: %s" % repr(new_key))
#             if data.get('aliases'):
#                 if self.DEBUG_UPDATE:
#                     self.register_message(u"has aliases")
#                 data_aliases = data['aliases']
#                 for alias in data_aliases:
#                     if self.s_handle_semi_static(alias):
#                         if self.DEBUG_UPDATE:
#                             self.register_message(u"Alias semistatic")
#                         continue
#                     else:
#                         updates = self.get_slave_updates_native_rec(
#                             alias, updates)
#         else:
#             if self.DEBUG_UPDATE:
#                 self.register_message(u"handle doesn't exist")
#         return updates

class SyncUpdateGen(SyncUpdate):
    """
    Abstract class for when sync master is in generator format.
    """
    master_target = 'gen-api'
    merge_mode = 'merge'

    @property
    def master_id(self):
        return self.get_new_subject_value('menu_order', self.master_name)

class SyncUpdateProd(SyncUpdateGen):
    """
    Abstract class for product updates
    """
    coldata_class = ColDataProductMeridian
    slave_target = 'wc-wp-api-v2-edit'

    def __init__(self, *args, **kwargs):
        super(SyncUpdateProd, self).__init__(*args, **kwargs)

    @property
    def slave_id(self):
        return self.get_new_subject_value('id', self.slave_name)

class SyncUpdateProdWoo(SyncUpdateProd):
    coldata_class = ColDataProductMeridian

class SyncUpdateProdXero(SyncUpdateProd):
    coldata_class = ColDataProductMeridian
    slave_target = 'xero-api'

    @property
    def slave_id(self):
        return self.get_new_subject_value('xero_id', self.slave_name)


class SyncUpdateVarWoo(SyncUpdateProdWoo):
    coldata_class = ColDataProductVariationMeridian

class SyncUpdateImgWoo(SyncUpdateGen):
    coldata_class = ColDataAttachment
    slave_target = 'wp-api-v2-edit'

    @property
    def slave_id(self):
        return self.get_new_subject_value('id', self.slave_name)

class SyncUpdateCatWoo(SyncUpdateGen):
    coldata_class = ColDataWcProdCategory
    slave_target = 'wc-wp-api-v2-edit'
    default_master_container = ImportWooCategory
    default_slave_container = ImportWooApiCategory

    @property
    def slave_id(self):
        return self.get_new_subject_value('term_id', self.slave_name)
