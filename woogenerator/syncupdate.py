"""
Utilites for storing and performing operations on pending updates
"""

from __future__ import absolute_import

import traceback
from collections import OrderedDict
from copy import copy, deepcopy

from tabulate import tabulate

from .coldata import ColDataBase, ColDataProd, ColDataUser, ColDataWoo
from .contact_objects import ContactAddress, FieldGroup
from .matching import Match
from .parsing.abstract import ImportObject
from .utils import Registrar, SanitationUtils, TimeUtils


class SyncViolation(UserWarning):
    """Update violates some sync condition"""


class InvincibilityViolation(SyncViolation):
    """Update violates an invincibility condition."""


class SemistaticViolation(SyncViolation):
    """Update violates a semistatic condition."""


class SyncUpdate(Registrar):
    """
    Stores information about and performs operations on a pending update
    """

    col_data = ColDataBase
    merge_mode = None
    s_meta_target = None
    m_meta_target = 'act'

    @classmethod
    def set_globals(cls, merge_mode, default_last_sync):
        """
        sets the class attributes to those specified in the user config
        """
        # TODO: Fix this awful mess
        cls.merge_mode = merge_mode
        cls.default_last_sync = default_last_sync

    def __init__(self, old_m_object, old_s_object, lastSync=None):
        super(SyncUpdate, self).__init__()
        for old_object in old_m_object, old_s_object:
            assert isinstance(old_object, ImportObject)
        if not lastSync:
            lastSync = self.default_last_sync
        # print "Creating SyncUpdate: ", old_m_object.__repr__(),
        # old_s_object.__repr__()
        self.old_m_object = old_m_object
        self.old_s_object = old_s_object
        self.t_time = TimeUtils.wp_strp_mktime(lastSync)

        self.new_s_object = None
        self.new_m_object = None
        self.static = True
        self.important_static = True
        self.sync_warnings = OrderedDict()
        self.sync_passes = OrderedDict()
        self.sync_problematics = OrderedDict()
        self.sync_reflections = OrderedDict()
        self.updates = 0
        self.important_updates = 0
        self.important_cols = []
        self.m_deltas = False
        self.s_deltas = False
        self.m_time = 0
        self.s_time = 0
        self.b_time = 0

    @property
    def s_updated(self):
        """Return whether slave has been updated."""
        return bool(self.new_s_object)

    @property
    def m_updated(self):
        """Return whether master has been updated."""
        return bool(self.new_m_object)

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
            return self.new_m_object
        elif subject == self.slave_name:
            return self.new_s_object

    def set_new_subject_object(self, value, subject):
        if subject == self.master_name:
            self.new_m_object = value
        elif subject == self.slave_name:
            self.new_s_object = value

    def get_old_subject_object(self, subject):
        """Return the new object associated with the subject."""
        if subject == self.master_name:
            return self.old_m_object
        elif subject == self.slave_name:
            return self.old_s_object

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
        """Parse a raw act-like time string."""
        return TimeUtils.act_server_to_local_time(
            TimeUtils.act_strp_mktime(raw_m_time)
        )

    @classmethod
    def parse_s_time(cls, raw_s_time):
        """Parse a raw wp-like time string."""
        return TimeUtils.wp_server_to_local_time(
            TimeUtils.wp_strp_mktime(raw_s_time)
        )

    def parse_subject_time(self, raw_time, subject):
        """Parse a raw time string for a given subject's format."""
        if subject == self.master_name:
            return self.parse_m_time(raw_time)
        elif subject == self.slave_name:
            return self.parse_s_time(raw_time)

    def sanitize_value(self, col, value):
        """Sanitize a value dependent on the col the value is from."""
        if 'phone' in col.lower():
            if 'preferred' in col.lower():
                if value and len(SanitationUtils.strip_non_numbers(value)) > 1:
                    return ""
        return value

    def get_old_subject_value(self, col, subject):
        """Get the value for the subject's old object."""
        value = self.get_old_subject_object(subject).get(col)
        if value is not None:
            return self.sanitize_value(col, value)
        return ""

    def get_old_m_value(self, col):
        """Get master value from old object."""
        # TODO: deprecate this
        return self.get_old_subject_value(col, self.master_name)

    def get_old_s_value(self, col):
        """Get slave value from old object."""
        # TODO: deprecate this
        return self.get_old_subject_value(col, self.slave_name)

    def get_new_subject_value(self, col, subject):
        """Get the value for the subject's new object."""
        new_object = self.get_new_subject_object(subject)
        if new_object:
            value = new_object.get(col)
            if value is not None:
                return self.sanitize_value(col, value)
            return ""
        return self.get_old_subject_value(col, subject)

    def get_new_m_value(self, col):
        """Get master value from new object."""
        # TODO: deprecate this
        return self.get_new_subject_value(col, self.master_name)

    def get_new_s_value(self, col):
        """Get slave value from new object."""
        # TODO: deprecate this
        return self.get_new_subject_value(col, self.slave_name)

    def values_similar(self, col, m_value, s_value):
        """Check if two values are similar. Depends on col."""
        response = False
        if not (m_value or s_value):
            response = True
        elif not (m_value and s_value):
            response = False
        # check if they are similar
        # if hasattr(m_value, 'reprocess_kwargs') and m_value.reprocess_kwargs:
        # if col == 'Role Info':
        if hasattr(m_value, 'similar') and callable(m_value.similar):
            response = m_value.similar(s_value)
        similar_m_value = SanitationUtils.similar_comparison(m_value)
        similar_s_value = SanitationUtils.similar_comparison(s_value)

        if similar_m_value == similar_s_value:
            response = True

        if self.DEBUG_UPDATE:
            self.register_message(
                self.test_to_str(
                    col, m_value, s_value, response))
        return response

    def old_col_identical(self, col):
        """For given col, check if the master value is similar to the slave value in old objects."""
        m_value = self.get_old_subject_value(col, self.master_name)
        s_value = self.get_old_subject_value(col, self.slave_name)
        response = m_value == s_value
        if self.DEBUG_UPDATE:
            self.register_message(
                self.test_to_str(
                    col, m_value, s_value, response))
        return response

    def new_col_similar(self, col):
        """For given col, check if the master value is similar to the slave value in new objects."""
        m_value = self.get_new_subject_value(col, self.master_name)
        s_value = self.get_new_subject_value(col, self.slave_name)
        response = self.values_similar(col, m_value, s_value)
        if self.DEBUG_UPDATE:
            self.register_message(
                self.test_to_str(
                    col, m_value, s_value, response))
        return response

    def new_col_identical(self, col):
        """For given col, check if the master value is equal to the slave value in new objects."""
        m_value = self.get_new_subject_value(col, self.master_name)
        s_value = self.get_new_subject_value(col, self.slave_name)
        response = m_value == s_value
        if self.DEBUG_UPDATE:
            self.register_message(
                self.test_to_str(
                    col, m_value, s_value, response))
        return response

    def col_static(self, col, subject):
        """For given col, check if the old value is similar to the new value in subject."""
        o_value = self.get_old_subject_value(col, subject)
        n_value = self.get_new_subject_value(col, subject)
        response = o_value == n_value
        if self.DEBUG_UPDATE:
            self.register_message(
                self.test_to_str(
                    col, o_value, n_value, response))
        return response

    def col_semi_static(self, col, subject):
        """For given col, check if the old value is equal to the new value in subject."""
        o_value = self.get_old_subject_value(col, subject)
        n_value = self.get_new_subject_value(col, subject)
        response = self.values_similar(col, o_value, n_value)
        if self.DEBUG_UPDATE:
            self.register_message(
                self.test_to_str(
                    col, o_value, n_value, response))
        return response

    def m_col_static(self, col):
        """For given col, check if the old value is equal to the new value in master."""
        # TODO: deprecate this
        return self.col_static(col, self.master_name)

    def s_col_static(self, col):
        """For given col, check if the old value is equal to the new value in slave."""
        # TODO: deprecate this
        return self.col_static(col, self.slave_name)

    def m_col_semi_static(self, col):
        """For given col, check if the old value is similar to the new value in master."""
        # TODO: deprecate this
        return self.col_semi_static(col, self.master_name)

    def s_col_semi_static(self, col):
        """For given col, check if the old value is similar to the new value in slave."""
        # TODO: deprecate this
        return self.col_semi_static(col, self.slave_name)

    def col_violates_invincible(self, **update_params):
        """Determine if an update to a column has violated an invincibility condition."""
        for key in ['col', 'data', 'subject']:
            assert key in update_params, 'missing mandatory update param, %s from %s' % (
                key, update_params)
        return
        subject = update_params['subject']
        data = update_params['data']
        col_aliases = data.get('aliases', [])
        for col_alias in col_aliases:
            new_alias_value = self.get_new_subject_value(col_alias, subject)
            col_alias_data = self.col_data.data.get(col_alias, {})
            col_alias_invincibility = str(
                col_alias_data.get('invincible')).lower()
            if col_alias_invincibility and not new_alias_value:
                failed_conditions = [
                    (col_alias_invincibility ==
                     'both' or col_alias_invincibility == 'true'),
                    (col_alias_invincibility ==
                     'master' and subject == self.master_name),
                    (col_alias_invincibility ==
                     'slave' and subject == self.slave_name),
                ]
                return any(failed_conditions)

    def test_to_str(self, col, val1, val2, res):
        return u"testing col %s: %s | %s -> %s" % (
            unicode(col),
            repr(val1),
            repr(val2),
            SanitationUtils.bool_to_truish_string(res)
        )

    def update_to_str(self, update_type, update_params):
        assert isinstance(update_type, str)
        assert 'col' in update_params
        out = u""
        out += "SYNC %s:" % update_type
        out += " | %s " % SanitationUtils.coerce_ascii(self)
        out += " | col:  %s" % update_params['col']
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
        for key in ['col', 'subject', 'reason']:
            assert update_params[key], 'missing mandatory prob param %s' % key
        col = update_params['col']
        if col not in self.sync_problematics.keys():
            self.sync_problematics[col] = []
        self.sync_problematics[col].append(update_params)
        self.register_warning(self.update_to_str('PROB', update_params))

    def add_sync_warning(self, **update_params):
        for key in ['col', 'subject', 'reason']:
            assert update_params[
                key], 'missing mandatory warning param %s' % key
        col = update_params['col']
        if col not in self.sync_warnings.keys():
            self.sync_warnings[col] = []
        self.sync_warnings[col].append(update_params)
        if self.DEBUG_UPDATE:
            self.register_warning(self.update_to_str('WARN', update_params))

    def add_sync_pass(self, **update_params):
        for key in ['col']:
            assert update_params[key], 'missing mandatory pass param %s' % key
        col = update_params['col']
        if col not in self.sync_passes.keys():
            self.sync_passes[col] = []
        self.sync_passes[col].append(update_params)
        if self.DEBUG_UPDATE:
            self.register_message(self.update_to_str('PASS', update_params))

    def add_sync_reflection(self, **update_params):
        for key in ['col']:
            assert update_params[key], 'missing mandatory reflection param %s' % key
        col = update_params['col']
        if col not in self.sync_reflections.keys():
            self.sync_reflections[col] = []
        self.sync_reflections[col].append(update_params)
        if self.DEBUG_UPDATE:
            self.register_message(self.update_to_str('REFL', update_params))

    def display_update_list(
            self, update_list, tablefmt=None, update_type=None):
        if not update_list:
            return ""

        delimeter = "<br/>" if tablefmt == "html" else "\n"
        subject_fmt = "<h4>%s</h4>" if tablefmt == "html" else "%s"
        # header = ["Column", "Reason", "Old", "New"]
        header_items = [
            ('col', 'Column'),
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
            ('m_col_time', 'M TIME'),
            ('s_col_time', 'S TIME'),
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
                for key in ['m_col_time', 's_col_time']:
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
        return delimeter.join(tables)

    def display_sync_warnings(self, tablefmt=None):
        return self.display_update_list(self.sync_warnings, tablefmt)

    def display_sync_passes(self, tablefmt=None):
        return self.display_update_list(
            self.sync_passes, tablefmt, update_type='pass')

    def display_problematic_updates(self, tablefmt=None):
        return self.display_update_list(self.sync_problematics, tablefmt)

    def display_sync_reflections(self, tablefmt=None):
        return self.display_update_list(
            self.sync_reflections, tablefmt, update_type='reflect')

    # def getOldLoserObject(self, winner=None):
    #     if not winner: winner = self.winner
    #     if(winner == self.master_name):
    #         oldLoserObject = self.old_s_object

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
        return "%s - %s" % (
            id(thing),
            hash(thing)
        )

    def set_loser_value(self, **update_params):
        for key in ['col', 'data', 'subject', 'old_value', 'new_value']:
            assert key in update_params, 'missing mandatory update param, %s from %s' % (
                key, update_params)

        loser = update_params['subject']
        col = update_params['col']
        data = update_params['data']
        reason = update_params.get('reason', '')

        prev_old_val_hash = self.snapshot_hash(update_params['old_value'])

        new_loser_object = self.get_new_subject_object(loser)
        prev_new_loser_object = bool(new_loser_object)
        if not prev_new_loser_object:
            old_object = self.get_old_subject_object(loser)
            self.set_new_subject_object(deepcopy(old_object), loser)
            new_loser_object = self.get_new_subject_object(loser)
        prev_loser_val = deepcopy(new_loser_object.get(col))

        if data.get('delta'):
            delta_col = self.col_data.delta_col(col)
            if not new_loser_object.get(delta_col):
                new_loser_object[delta_col] = copy(update_params['old_value'])
                if data.get('aliases'):
                    new_loser_object[delta_col].perform_post = False

        if data.get('aliases') and getattr(
                new_loser_object[col], 'reprocess_kwargs'):
            new_loser_object[col].update_from(
                update_params['new_value'], data.get('aliases'))
        else:
            new_loser_object[col] = update_params['new_value']

        # Check update does not violate conditions before marking as changed
        col_violates_invincible = self.col_violates_invincible(**update_params)
        col_semi_static = self.col_semi_static(col, loser)
        if col_semi_static or col_violates_invincible:
            # revert new_loser_object
            if not prev_new_loser_object:
                self.set_new_subject_object(prev_new_loser_object, loser)
            else:
                new_loser_object[col] = prev_loser_val
            if col_violates_invincible:
                raise InvincibilityViolation(
                    "col should't be updated, violates invincibility: %s" %
                    update_params)
            if col_semi_static:
                raise SemistaticViolation(
                    "col shouldn't be updated, too similar: %s" %
                    update_params)

        if data.get('delta') and reason in ['updating', 'deleting', 'reflect']:
            if loser == self.slave_name:
                self.s_deltas = True
            elif loser == self.master_name:
                self.m_deltas = True

        self.updates += 1
        if data.get('static'):
            self.static = False
        if(reason in ['updating', 'deleting', 'reflect']):
            self.important_updates += 1
            self.important_cols.append(col)
            if data.get('static'):
                self.add_problematic_update(**update_params)
                self.important_static = False

        assert \
            prev_old_val_hash == self.snapshot_hash(update_params['old_value']), \
            "should never update old_value"

    # def loser_update(self, winner, col, reason = "", data={}, s_time=None,
    # m_time=None):
    def loser_update(self, **update_params):
        for key in ['col', 'data', 'subject', 'old_value', 'new_value']:
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
        # print "tie_update ", col, reason
        for key in ['col']:
            assert update_params[
                key], 'missing mandatory update param, %s' % key
        col = update_params['col']
        if self.old_s_object:
            update_params['value'] = self.old_s_object.get(col)
        elif self.old_m_object:
            update_params['value'] = self.old_s_object.get(col)
        self.add_sync_pass(**update_params)

    def reflect_update(self, **update_params):
        for key in ['col', 'data', 'm_value', 's_value']:
            assert key in update_params, 'missing mandatory update param, %s from %s' % (
                key, update_params)

        if 'reflected_master' in update_params or 'reflected_slave' in update_params:
            self.add_sync_reflection(**update_params)

            if 'reflected_master' in update_params:
                master_update_params = copy(update_params)
                master_update_params['subject'] = self.master_name
                master_update_params['reason'] = 'reflect'
                master_update_params['old_value'] = update_params['m_value']
                master_update_params['new_value'] = update_params['reflected_master']
                self.loser_update(**master_update_params)

            if 'reflected_slave' in update_params:
                slave_update_params = copy(update_params)
                slave_update_params['subject'] = self.slave_name
                slave_update_params['reason'] = 'reflect'
                slave_update_params['old_value'] = update_params['s_value']
                slave_update_params['new_value'] = update_params['reflected_slave']
                self.loser_update(**slave_update_params)

    def get_col_mod_time(self, col, subject):
        pass

    def get_m_col_mod_time(self, col):
        return self.get_col_mod_time(col, self.master_name)

    def get_s_col_mod_time(self, col):
        return self.get_col_mod_time(col, self.slave_name)

    def reflect_col(self, **update_params):
        for key in ['col', 'data', 'm_value', 's_value']:
            assert \
                key in update_params, 'missing mandatory update param %s' % key
        data = update_params['data']
        reflect_mode = str(data['reflective'])
        if reflect_mode == 'both' or reflect_mode == 'master':
            assert isinstance(update_params['m_value'], FieldGroup), \
                "why are we reflecting something that isn't a fieldgroup?: %s" % \
                update_params['m_value']
            reflected_m_value = update_params['m_value'].reflect()
            if reflected_m_value != update_params['m_value']:
                update_params['reflected_master'] = reflected_m_value
                # if Registrar.DEBUG_UPDATE:
                #     Registrar.register_message("reflecting. m_value: %s / %s / %s, reflected: %s / %s / %s" % (
                #         pformat(update_params['m_value'].properties),
                #         pformat(update_params['m_value'].kwargs),
                #         pformat([update_params['m_value'][key] for key in update_params['m_value'].equality_keys]),
                #         pformat(reflected_m_value.properties),
                #         pformat(reflected_m_value.kwargs),
                #         pformat([reflected_m_value[key] for key in reflected_m_value.equality_keys]),
                #     ))

        if reflect_mode == 'both' or reflect_mode == 'slave':
            assert isinstance(update_params['s_value'], FieldGroup), \
                "why are we reflecting something that isn't a fieldgroup?: %s" % \
                update_params['s_value']
            reflected_s_value = update_params['s_value'].reflect()
            if reflected_s_value != update_params['s_value']:
                update_params['reflected_slave'] = reflected_s_value

        if 'reflected_slave' in update_params or 'reflected_master' in update_params:
            self.reflect_update(**update_params)

    def sync_col(self, **update_params):
        for key in ['col', 'data', 'm_value',
                    's_value', 'm_col_time', 's_col_time']:
            assert \
                key in update_params, 'missing mandatory update param %s' % key
        col = update_params['col']
        data = update_params['data']

        sync_mode = str(data['sync']).lower()

        if self.new_col_identical(col):
            update_params['reason'] = 'identical'
            self.tie_update(**update_params)
            return
        # else:
        #     pass

        winner = self.get_winner_name(
            update_params['m_col_time'], update_params['s_col_time']
        )

        if 'override' in sync_mode:
            # update_params['reason'] = 'overriding'
            if 'master' in sync_mode:
                winner = self.master_name
            elif 'slave' in sync_mode:
                winner = self.slave_name
        else:
            if self.new_col_similar(col):
                update_params['reason'] = 'similar'
                self.tie_update(**update_params)
                return

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

        if 'invincible' in data and not update_params['new_value']:
            update_params['reason'] = 'invincible'
            self.tie_update(**update_params)
            return

        if 'reason' not in update_params:
            if not update_params['new_value']:
                update_params['reason'] = 'deleting'
            elif not update_params['old_value']:
                update_params['reason'] = 'inserting'
            else:
                update_params['reason'] = 'updating'

        update_params['subject'] = self.opposite_src(winner)
        self.loser_update(**update_params)

    def update_col(self, **update_params):
        for key in ['col', 'data']:
            assert \
                update_params[key], 'missing mandatory update param %s' % key
        col = update_params['col']
        data = update_params['data']

        if data.get('reflective') or data.get('sync'):
            update_params['m_value'] = self.get_new_subject_value(
                col, self.master_name)
            update_params['s_value'] = self.get_new_subject_value(
                col, self.slave_name)
            update_params['m_col_time'] = self.get_col_mod_time(
                col, self.master_name)
            update_params['s_col_time'] = self.get_col_mod_time(
                col, self.slave_name)

            if data.get('reflective'):
                self.reflect_col(**update_params)
                update_params['m_value'] = self.get_new_subject_value(
                    col, self.master_name)
                update_params['s_value'] = self.get_new_subject_value(
                    col, self.slave_name)

            if data.get('sync'):
                self.sync_col(**update_params)

    def update(self, sync_cols):
        for col, data in sync_cols.items():
            self.update_col(col=col, data=data)
        # if self.m_updated:
        #     self.new_m_object.refresh_contact_objects()
        # if self.s_updated:
        #     self.new_s_object.refresh_contact_objects()

    def get_info_components(self, info_fmt="%s"):
        return [
            (info_fmt % ("static", "yes" if self.static else "no")),
            (info_fmt % ("important_static", "yes" if self.important_static else "no"))
        ]

    def tabulate(self, tablefmt=None):
        subtitle_fmt = heading_fmt = "%s"
        info_delimeter = "\n"
        info_fmt = "%s: %s"
        if tablefmt == "html":
            heading_fmt = "<h2>%s</h2>"
            subtitle_fmt = "<h3>%s</h3>"
            info_delimeter = "<br/>"
            info_fmt = "<strong>%s:</strong> %s"
        old_match = Match([self.old_m_object], [self.old_s_object])
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
                    self.sync_problematics),
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
            if self.sync_passes:
                passes_components += [
                    subtitle_fmt % "PASSES (%d)" % len(self.sync_passes),
                    self.display_sync_passes(tablefmt)
                ]
            out_str += info_delimeter.join(filter(None, passes_components))
            out_str += info_delimeter
            reflection_components = []
            if self.sync_reflections:
                reflection_components += [
                    subtitle_fmt % "REFLECTIONS (%d)" % len(
                        self.sync_reflections),
                    self.display_sync_reflections(tablefmt)
                ]
            out_str += info_delimeter.join(filter(None, reflection_components))
            out_str += info_delimeter
        new_match = Match([self.new_m_object], [self.new_s_object])
        out_str += info_delimeter
        out_str += info_delimeter.join([
            subtitle_fmt % 'NEW',
            new_match.tabulate(cols=None, tablefmt=tablefmt)
        ])

        return out_str

    #
    def get_slave_updates_native_rec(self, col, updates=None):
        return updates

    def get_slave_updates_recursive(self, col, updates=None):
        return updates

    def get_master_updates_recursive(self, col, updates=None):
        return updates

    def get_slave_updates_native(self):
        updates = OrderedDict()
        for col, warnings in self.sync_warnings.items():
            if self.DEBUG_UPDATE:
                self.register_message(u"checking col %s" % unicode(col))
            for warning in warnings:
                if self.DEBUG_UPDATE:
                    self.register_message(
                        u"-> checking warning %s" % unicode(warning))
                loser = warning['subject']
                if loser == self.slave_name:
                    updates = self.get_slave_updates_native_rec(
                        col, updates)
        if self.DEBUG_UPDATE:
            self.register_message(u"returned %s" % unicode(updates))
        return updates

    def get_slave_updates(self):
        updates = OrderedDict()
        for col, warnings in self.sync_warnings.items():
            for warning in warnings:
                loser = warning['subject']
                if loser == self.slave_name:
                    updates = self.get_slave_updates_recursive(col, updates)
        if self.DEBUG_UPDATE:
            self.register_message(u"returned %s" % unicode(updates))
        return updates

    def get_master_updates(self):
        updates = OrderedDict()
        for col, warnings in self.sync_warnings.items():
            for warning in warnings:
                loser = warning['subject']
                if loser == self.master_name:
                    updates = self.get_master_updates_recursive(col, updates)
        if self.DEBUG_UPDATE:
            self.register_message(u"returned %s" % unicode(updates))
        return updates

    def display_slave_changes(self, tablefmt=None):
        if self.sync_warnings:
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
        if self.sync_warnings:
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
        updates = self.get_master_updates()
        if not updates:
            return

        pkey = self.master_id
        return client.upload_changes(pkey, updates)

        # todo: Determine if file imported correctly and delete file

    def update_slave(self, client):
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


class SyncUpdateUsr(SyncUpdate):
    col_data = ColDataUser
    s_meta_target = 'wp'

    def __init__(self, *args, **kwargs):
        super(SyncUpdateUsr, self).__init__(*args, **kwargs)

        self.m_time = self.old_m_object.act_modtime
        self.s_time = self.old_s_object.wp_modtime
        self.b_time = self.old_m_object.last_sale
        self.winner = self.get_winner_name(self.m_time, self.s_time)

        # extra heuristics for merge mode:
        if self.merge_mode == 'merge' and not self.s_mod:
            might_be_s_edited = False
            if not self.old_s_object.addresses_act_like():
                might_be_s_edited = True
            elif self.old_s_object.get('Home Country') == 'AU':
                might_be_s_edited = True
            elif self.old_s_object.username_act_like():
                might_be_s_edited = True
            if might_be_s_edited:
                # print repr(self.old_s_object), "might be edited"
                self.s_time = self.t_time
                if self.m_mod:
                    self.static = False
                    # self.important_static = False

    @property
    def master_id(self):
        return self.get_new_subject_value('MYOB Card ID', self.master_name)

    @property
    def slave_id(self):
        return self.get_new_subject_value("Wordpress ID", self.slave_name)

    def values_similar(self, col, m_value, s_value):
        response = super(SyncUpdateUsr, self).values_similar(
            col, m_value, s_value)
        if not response:
            if col.lower() in ['phone', 'mobile phone', 'home phone', 'fax']:
                m_phone = SanitationUtils.similar_phone_comparison(m_value)
                s_phone = SanitationUtils.similar_phone_comparison(s_value)
                plen = min(len(m_phone), len(s_phone))
                if plen > 7 and m_phone[-plen:] == s_phone[-plen:]:
                    response = True
            elif "role" == col.lower():
                m_role = SanitationUtils.similar_comparison(m_value)
                s_role = SanitationUtils.similar_comparison(s_value)
                if m_role == 'rn':
                    m_role = ''
                if s_role == 'rn':
                    s_role = ''
                if m_role == s_role:
                    response = True
            elif "address" in col.lower() and isinstance(m_value, ContactAddress):
                if m_value != s_value:
                    pass
                    # print "M: ", m_value.__str__(out_schema="flat"), "S: ",
                    # s_value.__str__(out_schema="flat")
                response = m_value.similar(s_value)
            elif "web site" in col.lower():
                if SanitationUtils.similar_url_comparison(
                        m_value) == SanitationUtils.similar_url_comparison(s_value):
                    response = True

        # if self.DEBUG_UPDATE:
        #     self.register_message(self.test_to_str(
        #         col,
        #         SanitationUtils.coerce_unicode(m_value),
        #         SanitationUtils.coerce_unicode(s_value),
        #         response
        #     ))
        return response

    def get_col_mod_time(self, col, subject):
        response = self.get_subject_mod_time(subject)
        if subject == self.master_name:
            tracked_cols_items = self.col_data.get_master_tracked_cols().items()
            future_tracked_cols_items = self.col_data.get_act_future_tracked_cols().items()
            old_object = self.old_m_object
        elif subject == self.slave_name:
            tracked_cols_items = self.col_data.get_wp_tracked_cols().items()
            future_tracked_cols_items = []
            old_object = self.old_s_object

        if self.col_data.data.get(col, {}).get('tracked'):
            col_tracking_name = self.col_data.mod_time_col(col)
        else:
            col_tracking_name = None
            for tracking_name, tracked_cols in tracked_cols_items:
                if col in tracked_cols:
                    col_tracking_name = tracking_name

        if col_tracking_name:
            if old_object.get(col_tracking_name):
                response = self.parse_subject_time(
                    old_object.get(col_tracking_name), subject
                )
            elif col_tracking_name not in future_tracked_cols_items:
                response = None
        return response

    def get_info_components(self, info_fmt="%s"):
        info_components = super(
            SyncUpdateUsr, self).get_info_components(info_fmt)
        info_components += [
            (info_fmt % ("Last Sale", TimeUtils.wp_time_to_string(
                self.b_time))) if self.b_time else "No Last Sale",
            (info_fmt % ("%s Mod Time" % self.master_name, TimeUtils.wp_time_to_string(
                self.m_time))) if self.m_mod else "%s Not Modded" % self.master_name,
            (info_fmt % ("%s Mod Time" % self.slave_name, TimeUtils.wp_time_to_string(
                self.s_time))) if self.s_mod else "%s Not Modded" % self.slave_name
        ]
        for tracking_name, cols in self.col_data.get_act_tracked_cols().items():
            col = cols[0]
            m_col_mod_time = self.get_col_mod_time(col, self.master_name)
            s_col_mod_time = self.get_col_mod_time(col, self.slave_name)
            if m_col_mod_time or s_col_mod_time:
                info_components.append(info_fmt % (tracking_name, '%s: %s; %s: %s' % (
                    self.master_name,
                    TimeUtils.wp_time_to_string(m_col_mod_time),
                    self.slave_name,
                    TimeUtils.wp_time_to_string(s_col_mod_time),
                )))
        return info_components

    def get_slave_updates_native_rec(self, col, updates=None):
        if updates is None:
            updates = OrderedDict()
        if self.DEBUG_UPDATE:
            SanitationUtils.safe_print(
                "getting updates for col %s, updates: %s" % (col, str(updates)))
        if col in self.col_data.data.keys():
            data = self.col_data.data[col]
            if data.get(self.s_meta_target):
                data_target = data.get(self.s_meta_target, {})
                if not data_target.get('final') and data_target.get('key'):
                    updates[data_target.get(
                        'key')] = self.new_s_object.get(col)
            if data.get('aliases'):
                data_aliases = data.get('aliases')
                for alias in data_aliases:
                    if self.s_col_semi_static(alias):
                        continue
                    updates = self.get_slave_updates_native_rec(
                        alias, updates)
        return updates

    def get_slave_updates_recursive(self, col, updates=None):
        if updates is None:
            updates = OrderedDict()
        if self.DEBUG_UPDATE:
            self.register_message(u"checking %s" % unicode(col))
        if col in self.col_data.data:
            if self.DEBUG_UPDATE:
                self.register_message(u"col exists")
            data = self.col_data.data[col]
            if data.get(self.s_meta_target):
                if self.DEBUG_UPDATE:
                    self.register_message(u"target exists")
                data_target = data.get(self.s_meta_target, {})
                if not data_target.get('final') and data_target.get('key'):
                    new_val = self.new_s_object.get(col)
                    updates[col] = new_val
                    if self.DEBUG_UPDATE:
                        self.register_message(u"newval: %s" % repr(new_val))
            if data.get('aliases'):
                if self.DEBUG_UPDATE:
                    self.register_message(u"has aliases")
                data_aliases = data['aliases']
                for alias in data_aliases:
                    if self.s_col_semi_static(alias):
                        if self.DEBUG_UPDATE:
                            self.register_message(u"Alias semistatic")
                        continue
                    else:
                        updates = self.get_slave_updates_recursive(
                            alias, updates)
        else:
            if self.DEBUG_UPDATE:
                self.register_message(u"col doesn't exist")
        return updates

    def get_master_updates_recursive(self, col, updates=None):
        if updates is None:
            updates = OrderedDict()
        if self.DEBUG_UPDATE:
            self.register_message(u"checking %s" % unicode(col))
        if col in self.col_data.data:
            if self.DEBUG_UPDATE:
                self.register_message(u"col exists")
            data = self.col_data.data[col]
            if self.DEBUG_UPDATE:
                self.register_message(u"data: %s, target: %s" % (
                    data, self.m_meta_target
                ))
            if data.get(self.m_meta_target):
                if self.DEBUG_UPDATE:
                    self.register_message(u"target exists")
                new_val = self.new_m_object.get(col)
                updates[col] = new_val
                if self.DEBUG_UPDATE:
                    self.register_message(u"newval: %s" % repr(new_val))
            if data.get('aliases'):
                if self.DEBUG_UPDATE:
                    self.register_message(u"has aliases")
                data_aliases = data['aliases']
                for alias in data_aliases:
                    if self.m_col_semi_static(alias):
                        if self.DEBUG_UPDATE:
                            self.register_message(u"Alias semistatic")
                        continue
                    else:
                        updates = self.get_master_updates_recursive(
                            alias, updates)
        else:
            if self.DEBUG_UPDATE:
                self.register_message(u"col doesn't exist")
        return updates


class SyncUpdateUsrApi(SyncUpdateUsr):
    s_meta_target = 'wp-api'

    def s_validate_col(self, col, value):
        # TODO: Probably need more validation here
        if col.lower() in ['e-mail']:
            if not value:
                raise UserWarning("email does not look right")
        return value

    def get_slave_updates_native_rec(self, col, updates=None):
        if updates is None:
            updates = OrderedDict()
        if self.DEBUG_UPDATE:
            self.register_message(u"checking %s : %s" %
                                  (unicode(col), self.col_data.data.get(col)))
        if col in self.col_data.data:
            if self.DEBUG_UPDATE:
                self.register_message(u"col exists")
            data = self.col_data.data[col]
            if data.get(self.s_meta_target):
                if self.DEBUG_UPDATE:
                    self.register_message(u"wp-api exists")
                data_target = data.get(self.s_meta_target, {})
                if not data_target.get('final') and data_target.get('key'):
                    new_val = self.new_s_object.get(col)
                    try:
                        new_val = self.s_validate_col(col, new_val)
                    except UserWarning:
                        return updates
                    new_key = col
                    if 'key' in data_target:
                        new_key = data_target.get('key')
                    if data_target.get('meta'):
                        if 'meta' not in updates:
                            updates['meta'] = OrderedDict()
                        updates['meta'][new_key] = new_val
                    else:
                        updates[new_key] = new_val
                    if self.DEBUG_UPDATE:
                        self.register_message(u"newval: %s" % repr(new_val))
                    if self.DEBUG_UPDATE:
                        self.register_message(u"newkey: %s" % repr(new_key))
            if data.get('aliases'):
                if self.DEBUG_UPDATE:
                    self.register_message(u"has aliases")
                data_aliases = data['aliases']
                for alias in data_aliases:
                    if self.s_col_semi_static(alias):
                        if self.DEBUG_UPDATE:
                            self.register_message(u"Alias semistatic")
                        continue
                    else:
                        updates = self.get_slave_updates_native_rec(
                            alias, updates)
        else:
            if self.DEBUG_UPDATE:
                self.register_message(u"col doesn't exist")
        return updates


class SyncUpdateProd(SyncUpdate):
    col_data = ColDataProd
    s_meta_target = 'wp-api'

    def __init__(self, *args, **kwargs):
        super(SyncUpdateProd, self).__init__(*args, **kwargs)

    @property
    def master_id(self):
        return self.get_new_subject_value('rowcount', self.master_name)

    @property
    def slave_id(self):
        return self.get_new_subject_value('ID', self.slave_name)

    def values_similar(self, col, m_value, s_value):
        response = super(SyncUpdateProd, self).values_similar(
            col, m_value, s_value)
        if col in self.col_data.data:
            col_data = self.col_data.data[col]
            if col_data.get('type'):
                if col_data.get('type') == 'currency':
                    m_price = SanitationUtils.similar_currency_comparison(
                        m_value)
                    s_price = SanitationUtils.similar_currency_comparison(
                        s_value)
                    if m_price == s_price:
                        response = True
        elif not response:
            if col is 'descsum':
                m_desc = SanitationUtils.similar_markup_comparison(m_value)
                s_desc = SanitationUtils.similar_markup_comparison(s_value)
                if m_desc == s_desc:
                    response = True
            elif col is 'CVC':
                m_com = SanitationUtils.similar_comparison(m_value) or '0'
                s_com = SanitationUtils.similar_comparison(s_value) or '0'
                if m_com == s_com:
                    response = True

        if self.DEBUG_UPDATE:
            self.register_message(self.test_to_str(
                col, m_value.__repr__(), s_value.__repr__(), response))
        return response


class SyncUpdateProdWoo(SyncUpdateProd):
    col_data = ColDataWoo

    def get_slave_updates_native_rec(self, col, updates=None):
        if updates is None:
            updates = OrderedDict()

        if col in self.col_data.data:
            data = self.col_data.data[col]
            if self.s_meta_target in data:
                data_target = data[self.s_meta_target]
                if 'key' in data_target:
                    key = data_target.get('key')
                    val = self.new_s_object.get(col)
                    if data_target.get('meta'):
                        if not val:
                            if 'delete_meta' not in updates:
                                updates['delete_meta'] = []
                            updates['delete_meta'].append(key)

                        if 'custom_meta' not in updates:
                            updates['custom_meta'] = OrderedDict()
                        updates['custom_meta'][key] = val

                    elif not data_target.get('final'):
                        updates[key] = val
                elif 'special' in data_target:
                    key = col
                    val = self.new_s_object.get(col)
                    updates[key] = val
        return updates

    def get_slave_updates_recursive(self, col, updates=None):
        if updates is None:
            updates = OrderedDict()
        if self.DEBUG_UPDATE:
            self.register_message(u"checking %s" % unicode(col))
        if col in self.col_data.data:
            if self.DEBUG_UPDATE:
                self.register_message(u"col exists")
            data = self.col_data.data[col]
            if data.get(self.s_meta_target):
                if self.DEBUG_UPDATE:
                    self.register_message(u"wp exists")
                data_target = data.get(self.s_meta_target, {})
                if not data_target.get('final') and data_target.get('key'):
                    new_val = self.new_s_object.get(col)
                    updates[col] = new_val
                    if self.DEBUG_UPDATE:
                        self.register_message(u"newval: %s" % repr(new_val))
        else:
            if self.DEBUG_UPDATE:
                self.register_message(u"col doesn't exist")
        return updates

    def get_master_updates_recursive(self, col, updates=None):
        if updates is None:
            updates = OrderedDict()
        if self.DEBUG_UPDATE:
            self.register_message(u"checking %s" % unicode(col))

        if col == 'catlist':
            if hasattr(self.old_s_object,
                       'is_variation') and self.old_s_object.is_variation:
                # print "excluded item because is_variation"
                return updates

        if col in self.col_data.data:
            if self.DEBUG_UPDATE:
                self.register_message(u"col exists")
            data = self.col_data.data[col]
            if data.get(self.m_meta_target):
                if self.DEBUG_UPDATE:
                    self.register_message(u"wp exists")
                new_val = self.new_m_object.get(col)
                updates[col] = new_val
                if self.DEBUG_UPDATE:
                    self.register_message(u"newval: %s" % repr(new_val))
        else:
            if self.DEBUG_UPDATE:
                self.register_message(u"col doesn't exist")
        return updates


class SyncUpdateVarWoo(SyncUpdateProdWoo):
    pass


class SyncUpdateCatWoo(SyncUpdate):
    col_data = ColDataWoo
    s_meta_target = 'wp-api'

    @property
    def master_id(self):
        return self.get_new_subject_value('rowcount', self.master_name)

    @property
    def slave_id(self):
        return self.get_new_subject_value('ID', self.slave_name)

    def values_similar(self, col, m_value, s_value):
        response = super(SyncUpdateCatWoo, self).values_similar(
            col, m_value, s_value)
        if not response:
            if col is 'descsum':
                m_desc = SanitationUtils.similar_markup_comparison(m_value)
                s_desc = SanitationUtils.similar_markup_comparison(s_value)
                if m_desc == s_desc:
                    response = True

        if self.DEBUG_UPDATE:
            self.register_message(self.test_to_str(
                col, m_value.__repr__(), s_value.__repr__(), response))
        return response

    def get_slave_updates_native_rec(self, col, updates=None):
        if updates is None:
            updates = OrderedDict()

        if col in self.col_data.data:
            data = self.col_data.data[col]
            if self.s_meta_target in data:
                data_target = data[self.s_meta_target]
                if 'key' in data_target:
                    key = data_target.get('key')
                    val = self.new_s_object.get(col)
                    if data_target.get('meta'):
                        if not val:
                            if 'delete_meta' not in updates:
                                updates['delete_meta'] = []
                            updates['delete_meta'].append(key)

                        if 'custom_meta' not in updates:
                            updates['custom_meta'] = OrderedDict()
                        updates['custom_meta'][key] = val

                    elif not data_target.get('final'):
                        updates[key] = val
                elif 'special' in data_target:
                    key = col
                    val = self.new_s_object.get(col)
                    updates[key] = val
        return updates

    def get_slave_updates_recursive(self, col, updates=None):
        if updates is None:
            updates = OrderedDict()
        if self.DEBUG_UPDATE:
            self.register_message(u"checking %s" % unicode(col))
        if col in self.col_data.data:
            if self.DEBUG_UPDATE:
                self.register_message(u"col exists")
            data = self.col_data.data[col]
            if data.get(self.s_meta_target):
                if self.DEBUG_UPDATE:
                    self.register_message(u"wp exists")
                data_target = data.get(self.s_meta_target, {})
                if not data_target.get('final') and data_target.get('key'):
                    new_val = self.new_s_object.get(col)
                    updates[col] = new_val
                    if self.DEBUG_UPDATE:
                        self.register_message(u"newval: %s" % repr(new_val))
        else:
            if self.DEBUG_UPDATE:
                self.register_message(u"col doesn't exist")
        return updates

    def get_master_updates_recursive(self, col, updates=None):
        if updates is None:
            updates = OrderedDict()
        if self.DEBUG_UPDATE:
            self.register_message(u"checking %s" % unicode(col))

        if col == 'catlist':
            if hasattr(self.old_s_object,
                       'is_variation') and self.old_s_object.is_variation:
                # print "excluded item because is_variation"
                return updates

        if col in self.col_data.data:
            if self.DEBUG_UPDATE:
                self.register_message(u"col exists")
            data = self.col_data.data[col]
            if data.get(self.m_meta_target):
                if self.DEBUG_UPDATE:
                    self.register_message(u"wp exists")
                new_val = self.new_m_object.get(col)
                updates[col] = new_val
                if self.DEBUG_UPDATE:
                    self.register_message(u"newval: %s" % repr(new_val))
        else:
            if self.DEBUG_UPDATE:
                self.register_message(u"col doesn't exist")
        return updates
