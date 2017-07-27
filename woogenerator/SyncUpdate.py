# pylint: disable=too-many-lines
"""
Utilites for storing and performing operations on pending updates
"""
# TODO: fix too-many-lines

from collections import OrderedDict
from copy import deepcopy, copy
from tabulate import tabulate

# , UnicodeCsvDialectUtils
from woogenerator.utils import SanitationUtils, TimeUtils, Registrar
from woogenerator.contact_objects import FieldGroup, ContactAddress
from woogenerator.coldata import ColDataBase, ColDataUser, ColDataProd, ColDataWoo
from woogenerator.matching import Match
from woogenerator.parsing.abstract import ImportObject


class SyncUpdate(
        Registrar):  # pylint: disable=too-many-instance-attributes,too-many-public-methods
    """
    Stores information about and performs operations on a pending update
    """
    # TODO: fix too-many-instance-attributes,too-many-public-methods

    col_data = ColDataBase
    master_name = None
    slave_name = None
    merge_mode = None
    s_meta_target = None
    m_meta_target = 'act'

    @classmethod
    def set_globals(cls, master_name, slave_name,
                    merge_mode, default_last_sync):
        """
        sets the class attributes to those specified in the user config
        """
        # TODO: Fix this awful mess

        cls.master_name = master_name
        cls.slave_name = slave_name
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
        """
        Return whether slave has been updated
        """
        return bool(self.new_s_object)

    @property
    def m_updated(self):
        """
        Return whether master has been updated
        """
        return bool(self.new_m_object)

    @property
    def e_updated(self):
        """
        Return whether either master or slave has updated
        """
        return self.s_updated or self.m_updated

    @property
    def l_time(self):
        """
        Return latest modtime out of master and slave
        """
        return max(self.m_time, self.s_time)

    @property
    def m_mod(self):
        """
        Return whether has been updated since last sync
        """
        return self.m_time >= self.t_time

    @property
    def s_mod(self):
        """
        Return whether slave has been updated since last sync
        """
        return self.s_time >= self.t_time

    @property
    def master_id(self):
        """
        Abstract method fo getting the ID of the master object
        """
        raise NotImplementedError()

    @property
    def slave_id(self):
        """
        Abstract method fo getting the ID of the slave object
        """
        raise NotImplementedError()

    def get_winner_name(self, m_time, s_time):
        """
        Get the name of the database containing the winning object (master / slave)
        """
        if not s_time:
            return self.master_name
        elif not m_time:
            return self.slave_name
        else:
            return self.slave_name if(s_time >= m_time) else self.master_name

    @classmethod
    def parse_m_time(cls, raw_m_time):
        """
        Parse a raw act-like time string
        """
        return TimeUtils.act_server_to_local_time(
            TimeUtils.act_strp_mktime(raw_m_time)
        )

    @classmethod
    def parse_s_time(cls, raw_s_time):
        """
        Parse a raw wp-like time string
        """
        return TimeUtils.wp_server_to_local_time(
            TimeUtils.wp_strp_mktime(raw_s_time)
        )

    def sanitize_value(self, col, value):
        """
        Sanitize a value dependent on the col the value is from
        """
        if 'phone' in col.lower():
            if 'preferred' in col.lower():
                if value and len(SanitationUtils.strip_non_numbers(value)) > 1:
                    return ""
        return value

    def get_m_value(self, col):
        value = self.old_m_object.get(col)
        if value is not None:
            return self.sanitize_value(col, value)
        return ""

    def get_s_value(self, col):
        value = self.old_s_object.get(col)
        if value is not None:
            return self.sanitize_value(col, value)
        return ""

    def get_new_m_value(self, col):
        if self.new_m_object:
            value = self.new_m_object.get(col)
            if value is not None:
                return self.sanitize_value(col, value)
            return ""
        return self.get_m_value(col)

    def get_new_s_value(self, col):
        if self.new_s_object:
            value = self.new_s_object.get(col)
            if value is not None:
                return self.sanitize_value(col, value)
            return ""
        return self.get_s_value(col)

    def values_similar(self, col, m_value, s_value):
        response = False
        if not (m_value or s_value):
            response = True
        elif not (m_value and s_value):
            response = False
        # check if they are similar
        if SanitationUtils.similar_comparison(
                m_value) == SanitationUtils.similar_comparison(s_value):
            response = True

        if self.DEBUG_UPDATE:
            self.register_message(
                self.test_to_str(
                    col, m_value, s_value, response))
        return response

    def col_identical(self, col):
        m_value = self.get_m_value(col)
        s_value = self.get_s_value(col)
        response = m_value == s_value
        if self.DEBUG_UPDATE:
            self.register_message(
                self.test_to_str(
                    col, m_value, s_value, response))
        return response

    def col_similar(self, col):
        m_value = self.get_m_value(col)
        s_value = self.get_s_value(col)
        response = self.values_similar(col, m_value, s_value)
        if self.DEBUG_UPDATE:
            self.register_message(
                self.test_to_str(
                    col, m_value, s_value, response))
        return response

    def new_col_identical(self, col):
        m_value = self.get_new_m_value(col)
        s_value = self.get_new_s_value(col)
        response = m_value == s_value
        if self.DEBUG_UPDATE:
            self.register_message(
                self.test_to_str(
                    col, m_value, s_value, response))
        return response

    def m_col_static(self, col):
        o_value = self.get_m_value(col)
        n_value = self.get_new_m_value(col)
        response = o_value == n_value
        if self.DEBUG_UPDATE:
            self.register_message(
                self.test_to_str(
                    col, o_value, n_value, response))
        return response

    def s_col_static(self, col):
        o_value = self.get_s_value(col)
        n_value = self.get_new_s_value(col)
        response = o_value == n_value
        if self.DEBUG_UPDATE:
            self.register_message(
                self.test_to_str(
                    col, o_value, n_value, response))
        return response

    def m_col_semi_static(self, col):
        o_value = self.get_m_value(col)
        n_value = self.get_new_m_value(col)
        response = self.values_similar(col, o_value, n_value)
        if self.DEBUG_UPDATE:
            self.register_message(
                self.test_to_str(
                    col, o_value, n_value, response))
        return response

    def s_col_semi_static(self, col):
        o_value = self.get_s_value(col)
        n_value = self.get_new_s_value(col)
        response = self.values_similar(col, o_value, n_value)
        if self.DEBUG_UPDATE:
            self.register_message(
                self.test_to_str(
                    col, o_value, n_value, response))
        return response

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
            if 'oldWinnerValue' in update_params:
                out += " | OLD: %s " % SanitationUtils.coerce_ascii(
                    update_params['oldWinnerValue'])
            if 'oldLoserValue' in update_params:
                out += " | NEW: %s " % SanitationUtils.coerce_ascii(
                    update_params['oldLoserValue'])
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

    def display_update_list(self, update_list, tablefmt=None, update_type=None):
        if not update_list:
            return ""

        delimeter = "<br/>" if tablefmt == "html" else "\n"
        subject_fmt = "<h4>%s</h4>" if tablefmt == "html" else "%s"
        # header = ["Column", "Reason", "Old", "New"]
        header_items = [
            ('col', 'Column'),
            ('reason', 'Reason'),
            ('oldLoserValue', 'Old'),
            ('oldWinnerValue', 'New'),
            ('mColTime', 'M TIME'),
            ('sColTime', 'S TIME'),
        ]
        if update_type == 'pass':
            header_items[2:4] = [('value', 'Value')]
        elif update_type == 'reflect':
            header_items[2:4] = [
                ('old_m_value', 'Old Master'),
                ('old_s_value', 'Old Slave'),
                ('reflected_master', 'Reflected Master'),
                ('reflected_slave', 'Reflected Slave'),
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
                for key in ['mColTime', 'sColTime']:
                    try:
                        raw_time = int(warning[key])
                        if raw_time:
                            warning_fmtd[
                                key] = TimeUtils.wp_time_to_string(raw_time)
                    except Exception as exc:
                        if exc:
                            pass
                subjects[subject].append(warning_fmtd)
        tables = []
        for subject, warnings in subjects.items():
            anti_subject_fmtd = subject_fmt % self.opposite_src(subject)
            table = [header] + warnings
            table_fmtd = tabulate(table, headers='firstrow',
                                  tablefmt=tablefmt)
            tables.append(delimeter.join([anti_subject_fmtd, table_fmtd]))
        return delimeter.join(tables)

    def display_sync_warnings(self, tablefmt=None):
        return self.display_update_list(self.sync_warnings, tablefmt)

    def display_sync_passes(self, tablefmt=None):
        return self.display_update_list(self.sync_passes, tablefmt, update_type='pass')

    def display_problematic_updates(self, tablefmt=None):
        return self.display_update_list(self.sync_problematics, tablefmt)

    def display_sync_reflections(self, tablefmt=None):
        return self.display_update_list(self.sync_reflections, tablefmt, update_type='reflect')

    # def getOldLoserObject(self, winner=None):
    #     if not winner: winner = self.winner
    #     if(winner == self.master_name):
    #         oldLoserObject = self.old_s_object

    def opposite_src(self, subject):
        if subject == self.master_name:
            return self.slave_name
        else:
            return self.master_name

    # def loser_update(self, winner, col, reason = "", data={}, s_time=None,
    # m_time=None):
    def loser_update(self, **update_params):
        for key in ['col', 'subject']:
            assert update_params[key], 'missing mandatory update param, %s from %s' % (
                key, update_params)

        col = update_params['col']
        winner = update_params['subject']
        reason = update_params.get('reason', '')
        data = update_params.get('data', {})

        if winner == self.master_name:
            if not self.new_s_object:
                self.new_s_object = deepcopy(self.old_s_object)
            new_loser_object = self.new_s_object
            if data.get('delta') and reason in ['updating', 'deleting']:
                # print "setting s_deltas"
                self.s_deltas = True
        elif winner == self.slave_name:
            if not self.new_m_object:
                self.new_m_object = deepcopy(self.old_m_object)
            new_loser_object = self.new_m_object
            if data.get('delta') and reason in ['updating', 'deleting']:
                # print "setting m_deltas"
                self.m_deltas = True
        # if data.get('warn'):

        self.add_sync_warning(**update_params)
        if data.get('delta'):
            new_loser_object[self.col_data.delta_col(col)] = update_params[
                'oldLoserValue']

        new_loser_object[col] = update_params['oldWinnerValue']
        self.updates += 1
        if data.get('static'):
            self.static = False
        if(reason in ['updating', 'deleting']):
            self.important_updates += 1
            self.important_cols.append(col)
            if data.get('static'):
                self.add_problematic_update(**update_params)
                self.important_static = False

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
        pass

    def get_m_col_mod_time(self, _):
        return None

    def get_s_col_mod_time(self, _):
        return None

    def reflect_col(self, **update_params):
        for key in ['col', 'data']:
            assert \
                update_params[key], 'missing mandatory update param %s' % key
        col = update_params['col']
        data = update_params['data']
        reflect_mode = str(data['reflective'])
        if reflect_mode == 'both' or reflect_mode == 'master':
            old_m_value = self.get_m_value(col)
            assert isinstance(old_m_value, FieldGroup), \
                "why are we reflecting something that isn't a fieldgroup?"
            reflected_m_value = old_m_value.reflect()
            if reflected_m_value != old_m_value:
                update_params['reflected_master'] = reflected_m_value

        if reflect_mode == 'both' or reflect_mode == 'slave':
            old_s_value = copy(self.get_m_value(col))
            assert isinstance(old_s_value, FieldGroup), \
                "why are we reflecting something that isn't a fieldgroup?"
            reflected_s_value = old_s_value.reflect()
            if reflected_s_value != old_s_value:
                update_params['reflected_slave'] = reflected_s_value

        if 'reflected_slave' in update_params or 'reflected_master' in update_params:
            self.reflect_update(**update_params)

    def update_col(self, **update_params):
        for key in ['col', 'data']:
            assert \
                update_params[key], 'missing mandatory update param %s' % key
        col = update_params['col']
        data = update_params['data']

        if data.get('reflective'):
            self.reflect_col(**update_params)

        if data.get('sync'):
            sync_mode = str(data['sync']).lower()

            if self.col_identical(col):
                update_params['reason'] = 'identical'
                self.tie_update(**update_params)
                return
            else:
                pass

            m_value = self.get_m_value(col)
            s_value = self.get_s_value(col)

            update_params['mColTime'] = self.get_m_col_mod_time(col)
            update_params['sColTime'] = self.get_s_col_mod_time(col)

            winner = self.get_winner_name(
                update_params['mColTime'], update_params['sColTime']
            )

            if 'override' in sync_mode:
                # update_params['reason'] = 'overriding'
                if 'master' in sync_mode:
                    winner = self.master_name
                elif 'slave' in sync_mode:
                    winner = self.slave_name
            else:
                if self.col_similar(col):
                    update_params['reason'] = 'similar'
                    self.tie_update(**update_params)
                    return

                if self.merge_mode == 'merge' \
                and not (m_value and s_value):
                    if winner == self.slave_name and not s_value:
                        winner = self.master_name
                        update_params['reason'] = 'merging'
                    elif winner == self.master_name and not m_value:
                        winner = self.slave_name
                        update_params['reason'] = 'merging'

            if winner == self.slave_name:
                update_params['oldWinnerValue'] = s_value
                update_params['oldLoserValue'] = m_value
            else:
                update_params['oldWinnerValue'] = m_value
                update_params['oldLoserValue'] = s_value

            if 'reason' not in update_params:
                if not update_params['oldWinnerValue']:
                    update_params['reason'] = 'deleting'
                elif not update_params['oldLoserValue']:
                    update_params['reason'] = 'inserting'
                else:
                    update_params['reason'] = 'updating'

            update_params['subject'] = winner
            self.loser_update(**update_params)

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

        info_components = self.get_info_components(info_fmt)
        if info_components:
            info_components = [subtitle_fmt % "INFO"] + info_components
            out_str += info_delimeter.join(filter(None, info_components))
            out_str += info_delimeter

        changes_components = []
        if not self.important_static:
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
        if self.new_m_object:
            changes_components += [
                subtitle_fmt % '%s CHANGES' % self.master_name,
                self.display_master_changes(tablefmt),
            ]
        if self.new_s_object:
            changes_components += [
                subtitle_fmt % '%s CHANGES' % self.slave_name,
                self.display_slave_changes(tablefmt),
            ]
        out_str += info_delimeter.join(filter(None, changes_components))
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
                subject = warning['subject']
                if subject == self.opposite_src(self.slave_name):
                    updates = self.get_slave_updates_native_rec(
                        col, updates)
        if self.DEBUG_UPDATE:
            self.register_message(u"returned %s" % unicode(updates))
        return updates

    def get_slave_updates(self):
        updates = OrderedDict()
        for col, warnings in self.sync_warnings.items():
            for warning in warnings:
                subject = warning['subject']
                if subject == self.opposite_src(self.slave_name):
                    updates = self.get_slave_updates_recursive(col, updates)
        if self.DEBUG_UPDATE:
            self.register_message(u"returned %s" % unicode(updates))
        return updates

    def get_master_updates(self):
        updates = OrderedDict()
        for col, warnings in self.sync_warnings.items():
            for warning in warnings:
                subject = warning['subject']
                if subject == self.opposite_src(self.master_name):
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
                    "NO %s CHANGES: must have a primary key to update user data: " % \
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
                pkey = self.slave_id
                assert pkey, "primary key must be valid, %s" % repr(pkey)
            except Exception as exc:
                print_elements.append(
                    ("NO %s CHANGES: "
                     "must have a primary key to update user data: ") % \
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
        return self.get_m_value('MYOB Card ID')

    @property
    def slave_id(self):
        return self.get_s_value("Wordpress ID")

    def values_similar(self, col, m_value, s_value):
        response = super(SyncUpdateUsr, self).values_similar(
            col, m_value, s_value)
        if not response:
            if "phone" in col.lower():
                if "preferred" in col.lower():
                    m_preferred = SanitationUtils.similar_tru_str_comparison(
                        m_value)
                    s_preferred = SanitationUtils.similar_tru_str_comparison(
                        s_value)
                    # print repr(m_value), " -> ", m_preferred
                    # print repr(s_value), " -> ", s_preferred
                    if m_preferred == s_preferred:
                        response = True
                else:
                    m_phone = SanitationUtils.similar_phone_comparison(m_value)
                    s_phone = SanitationUtils.similar_phone_comparison(s_value)
                    plen = min(len(m_phone), len(s_phone))
                    if plen > 7 and m_phone[-plen] == s_phone[-plen]:
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

    #
    def get_m_col_mod_time(self, col):
        if self.col_data.data.get(col, {}).get('tracked'):
            col_tracking_name = self.col_data.mod_time_col(col)
        else:
            col_tracking_name = None
            for tracking_name, tracked_cols in self.col_data.get_act_tracked_cols().items():
                if col in tracked_cols:
                    col_tracking_name = tracking_name

        if col_tracking_name:
            # print 's_col_mod_time tracking_name', col_tracking_name
            if self.old_m_object.get(col_tracking_name):
                # print 's_col_mod_time tracking_name exists', \
                #         self.old_m_object.get(col_tracking_name), \
                #         ' -> ',\
                #         self.parse_m_time(self.old_m_object.get(col_tracking_name))
                return self.parse_m_time(
                    self.old_m_object.get(col_tracking_name))
            elif col_tracking_name not in self.col_data.get_act_future_tracked_cols().items():
                return None
        return self.m_time

    def get_s_col_mod_time(self, col):
        if self.col_data.data.get(col, {}).get('tracked'):
            col_tracking_name = self.col_data.mod_time_col(col)
        else:
            col_tracking_name = None
            for tracking_name, tracked_cols in self.col_data.get_wp_tracked_cols().items():
                if col in tracked_cols:
                    col_tracking_name = tracking_name

        if col_tracking_name:
            # print 'm_col_mod_time tracking_name', col_tracking_name
            if self.old_s_object.get(col_tracking_name):
                return self.parse_s_time(
                    self.old_s_object.get(col_tracking_name))
            else:
                return None

        return self.s_time

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
            m_col_mod_time = self.get_m_col_mod_time(col)
            s_col_mod_time = self.get_s_col_mod_time(col)
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
                data_s = data.get(self.s_meta_target, {})
                if not data_s.get('final') and data_s.get('key'):
                    updates[data_s.get('key')] = self.new_s_object.get(col)
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
                    self.register_message(u"wp exists")
                data_s = data.get(self.s_meta_target, {})
                if not data_s.get('final') and data_s.get('key'):
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
            if data.get(self.m_meta_target):
                if self.DEBUG_UPDATE:
                    self.register_message(u"wp exists")
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
                data_s = data.get(self.s_meta_target, {})
                if not data_s.get('final') and data_s.get('key'):
                    new_val = self.new_s_object.get(col)
                    new_key = col
                    if 'key' in data_s:
                        new_key = data_s.get('key')
                    if data_s.get('meta'):
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
        return self.get_m_value('rowcount')

    @property
    def slave_id(self):
        return self.get_s_value('ID')

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
                data_s = data[self.s_meta_target]
                if 'key' in data_s:
                    key = data_s.get('key')
                    val = self.new_s_object.get(col)
                    if data_s.get('meta'):
                        if not val:
                            if 'delete_meta' not in updates:
                                updates['delete_meta'] = []
                            updates['delete_meta'].append(key)

                        if 'custom_meta' not in updates:
                            updates['custom_meta'] = OrderedDict()
                        updates['custom_meta'][key] = val

                    elif not data_s.get('final'):
                        updates[key] = val
                elif 'special' in data_s:
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
                data_s = data.get(self.s_meta_target, {})
                if not data_s.get('final') and data_s.get('key'):
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
                       'isVariation') and self.old_s_object.isVariation:
                # print "excluded item because isVariation"
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
        return self.get_m_value('rowcount')

    @property
    def slave_id(self):
        return self.get_s_value('ID')

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
                data_s = data[self.s_meta_target]
                if 'key' in data_s:
                    key = data_s.get('key')
                    val = self.new_s_object.get(col)
                    if data_s.get('meta'):
                        if not val:
                            if 'delete_meta' not in updates:
                                updates['delete_meta'] = []
                            updates['delete_meta'].append(key)

                        if 'custom_meta' not in updates:
                            updates['custom_meta'] = OrderedDict()
                        updates['custom_meta'][key] = val

                    elif not data_s.get('final'):
                        updates[key] = val
                elif 'special' in data_s:
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
                data_s = data.get(self.s_meta_target, {})
                if not data_s.get('final') and data_s.get('key'):
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
                       'isVariation') and self.old_s_object.isVariation:
                # print "excluded item because isVariation"
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
