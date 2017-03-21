# pylint: disable=too-many-lines
"""
Utilites for storing and performing operations on pending updates
"""
# TODO: fix too-many-lines

from collections import OrderedDict
from copy import deepcopy
from tabulate import tabulate

# , UnicodeCsvDialectUtils
from woogenerator.utils import SanitationUtils, TimeUtils, Registrar
from woogenerator.contact_objects import ContactAddress
from woogenerator.coldata import ColDataBase, ColData_User, ColData_Prod, ColData_Woo
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

    def parse_m_time(self, rawMTime):
        """
        Parse a raw act-like time string
        """
        return TimeUtils.act_server_to_local_time(
            TimeUtils.act_strp_mktime(rawMTime))

    def parse_s_time(self, rawSTime):
        """
        Parse a raw wp-like time string
        """
        return TimeUtils.wp_server_to_local_time(
            TimeUtils.wp_strp_mktime(rawSTime))

    def sanitize_value(self, col, value):
        """
        Sanitize a value dependent on the col the value is from
        """
        if 'phone' in col.lower():
            if 'preferred' in col.lower():
                if value and len(SanitationUtils.stripNonNumbers(value)) > 1:
                    return ""
        return value

    def get_m_value(self, col):
        return self.sanitize_value(col, self.old_m_object.get(col) or "")

    def get_s_value(self, col):
        return self.sanitize_value(col, self.old_s_object.get(col) or "")

    def get_new_m_value(self, col):
        if self.new_m_object:
            return self.sanitize_value(col, self.new_m_object.get(col) or "")
        else:
            return self.get_m_value(col)

    def get_new_s_value(self, col):
        if self.new_s_object:
            return self.sanitize_value(col, self.new_s_object.get(col) or "")
        else:
            return self.get_s_value(col)

    def valuesSimilar(self, col, m_value, s_value):
        response = False
        if not (m_value or s_value):
            response = True
        elif not (m_value and s_value):
            response = False
        # check if they are similar
        if SanitationUtils.similarComparison(
                m_value) == SanitationUtils.similarComparison(s_value):
            response = True

        if self.DEBUG_UPDATE:
            self.registerMessage(self.testToStr(col, m_value, s_value, response))
        return response

    def col_identical(self, col):
        m_value = self.get_m_value(col)
        s_value = self.get_s_value(col)
        response = m_value == s_value
        if self.DEBUG_UPDATE:
            self.registerMessage(self.testToStr(col, m_value, s_value, response))
        return response

    def col_similar(self, col):
        m_value = self.get_m_value(col)
        s_value = self.get_s_value(col)
        response = self.valuesSimilar(col, m_value, s_value)
        if self.DEBUG_UPDATE:
            self.registerMessage(self.testToStr(col, m_value, s_value, response))
        return response

    def newColIdentical(self, col):
        m_value = self.get_new_m_value(col)
        s_value = self.get_new_s_value(col)
        response = m_value == s_value
        if self.DEBUG_UPDATE:
            self.registerMessage(self.testToStr(col, m_value, s_value, response))
        return response

    def mColStatic(self, col):
        o_value = self.get_m_value(col)
        n_value = self.get_new_m_value(col)
        response = o_value == n_value
        if self.DEBUG_UPDATE:
            self.registerMessage(self.testToStr(col, o_value, n_value, response))
        return response

    def sColStatic(self, col):
        o_value = self.get_s_value(col)
        n_value = self.get_new_s_value(col)
        response = o_value == n_value
        if self.DEBUG_UPDATE:
            self.registerMessage(self.testToStr(col, o_value, n_value, response))
        return response

    def mColSemiStatic(self, col):
        o_value = self.get_m_value(col)
        n_value = self.get_new_m_value(col)
        response = self.valuesSimilar(col, o_value, n_value)
        if self.DEBUG_UPDATE:
            self.registerMessage(self.testToStr(col, o_value, n_value, response))
        return response

    def sColSemiStatic(self, col):
        o_value = self.get_s_value(col)
        n_value = self.get_new_s_value(col)
        response = self.valuesSimilar(col, o_value, n_value)
        if self.DEBUG_UPDATE:
            self.registerMessage(self.testToStr(col, o_value, n_value, response))
        return response

    def testToStr(self, col, val1, val2, res):
        return u"testing col %s: %s | %s -> %s" % (
            unicode(col),
            repr(val1),
            repr(val2),
            SanitationUtils.bool_to_truish_string(res)
        )

    def updateToStr(self, updateType, updateParams):
        assert isinstance(updateType, str)
        assert 'col' in updateParams
        out = u""
        out += "SYNC %s:" % updateType
        out += " | %s " % SanitationUtils.coerce_ascii(self)
        out += " | col:  %s" % updateParams['col']
        if 'subject' in updateParams:
            out += " | subj: %s " % updateParams['subject']
        if 'reason' in updateParams:
            out += " | reas: %s " % updateParams['reason']
        if updateType in ['WARN', 'PROB']:
            if 'oldWinnerValue' in updateParams:
                out += " | OLD: %s " % SanitationUtils.coerce_ascii(
                    updateParams['oldWinnerValue'])
            if 'oldLoserValue' in updateParams:
                out += " | NEW: %s " % SanitationUtils.coerce_ascii(
                    updateParams['oldLoserValue'])
        return out

    def add_problematic_update(self, **updateParams):
        for key in ['col', 'subject', 'reason']:
            assert updateParams[key], 'missing mandatory prob param %s' % key
        col = updateParams['col']
        if col not in self.sync_problematics.keys():
            self.sync_problematics[col] = []
        self.sync_problematics[col].append(updateParams)
        self.registerWarning(self.updateToStr('PROB', updateParams))
        # self.registerWarning("SYNC PROB: %s | %s" % (self.__str__(), SanitationUtils.coerce_unicode(updateParams)))

    def add_sync_warning(self, **updateParams):
        for key in ['col', 'subject', 'reason']:
            assert updateParams[
                key], 'missing mandatory warning param %s' % key
        col = updateParams['col']
        if col not in self.sync_warnings.keys():
            self.sync_warnings[col] = []
        self.sync_warnings[col].append(updateParams)
        if self.DEBUG_UPDATE:
            self.registerWarning(self.updateToStr('WARN', updateParams))
        # self.registerWarning("SYNC WARNING: %s | %s" % (self.__str__(), SanitationUtils.coerce_unicode(updateParams)))

    def add_sync_pass(self, **updateParams):
        for key in ['col']:
            assert updateParams[key], 'missing mandatory pass param %s' % key
        col = updateParams['col']
        if col not in self.sync_passes.keys():
            self.sync_passes[col] = []
        self.sync_passes[col].append(updateParams)
        if self.DEBUG_UPDATE:
            self.registerWarning(self.updateToStr('PASS', updateParams))
        # if self.DEBUG_UPDATE: self.registerMessage("SYNC PASS: %s | %s" % (self.__str__(), SanitationUtils.coerce_unicode(updateParams)))

    def display_update_list(self, updateList, tablefmt=None):
        if updateList:
            delimeter = "<br/>" if tablefmt == "html" else "\n"
            subject_fmt = "<h4>%s</h4>" if tablefmt == "html" else "%s"
            # header = ["Column", "Reason", "Old", "New"]
            header = OrderedDict([
                ('col', 'Column'),
                ('reason', 'Reason'),
                ('oldLoserValue', 'Old'),
                ('oldWinnerValue', 'New'),
                ('mColTime', 'M TIME'),
                ('sColTime', 'S TIME'),
            ])
            subjects = {}
            for warnings in updateList.values():
                for warning in warnings:
                    subject = warning['subject']
                    if subject not in subjects.keys():
                        subjects[subject] = []
                    warning_fmtd = dict([
                        (key, SanitationUtils.sanitizeForTable(val))
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
                            if(exc):
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
        else:
            return ""

    def display_sync_warnings(self, tablefmt=None):
        return self.display_update_list(self.sync_warnings, tablefmt)

    def display_problematic_updates(self, tablefmt=None):
        return self.display_update_list(self.sync_problematics, tablefmt)

    # def getOldLoserObject(self, winner=None):
    #     if not winner: winner = self.winner
    #     if(winner == self.master_name):
    #         oldLoserObject = self.old_s_object

    def opposite_src(self, subject):
        if subject == self.master_name:
            return self.slave_name
        else:
            return self.master_name

    # def loserUpdate(self, winner, col, reason = "", data={}, s_time=None,
    # m_time=None):
    def loserUpdate(self, **updateParams):
        for key in ['col', 'subject']:
            assert updateParams[key], 'missing mandatory update param, %s from %s' % (
                key, updateParams)

        col = updateParams['col']
        winner = updateParams['subject']
        reason = updateParams.get('reason', '')
        data = updateParams.get('data', {})

        # self.registerMessage("loserUpdate " + SanitationUtils.coerce_unicode([winner, col, reason]))
        if(winner == self.master_name):
            # oldLoserObject = self.old_s_object
            updateParams['oldLoserValue'] = self.get_s_value(col)
            # oldWinnerObject = self.old_m_object
            updateParams['oldWinnerValue'] = self.get_m_value(col)
            if not self.new_s_object:
                self.new_s_object = deepcopy(self.old_s_object)
            new_loser_object = self.new_s_object
            if data.get('delta') and reason in ['updating', 'deleting']:
                # print "setting s_deltas"
                self.s_deltas = True
        elif(winner == self.slave_name):
            # oldLoserObject = self.old_m_object
            updateParams['oldLoserValue'] = self.get_m_value(col)
            # oldWinnerObject = self.old_s_object
            updateParams['oldWinnerValue'] = self.get_s_value(col)
            if not self.new_m_object:
                self.new_m_object = deepcopy(self.old_m_object)
            new_loser_object = self.new_m_object
            if data.get('delta') and reason in ['updating', 'deleting']:
                # print "setting m_deltas"
                self.m_deltas = True
        # if data.get('warn'):

        self.add_sync_warning(**updateParams)
        # self.add_sync_warning(col, winner, reason, oldLoserValue, oldWinnerValue, data, s_time, m_time)
        # SanitationUtils.safePrint("loser %s was %s" % (col, repr(new_loser_object[col])))
        # SanitationUtils.safePrint("updating to ", oldWinnerValue)
        if data.get('delta'):
            # print "delta true for ", col, \
            # "loser", updateParams['oldLoserValue'], \
            # "winner", updateParams['oldWinnerValue']
            new_loser_object[self.col_data.delta_col(col)] = updateParams[
                'oldLoserValue']

        new_loser_object[col] = updateParams['oldWinnerValue']
        # SanitationUtils.safePrint( "loser %s is now %s" % (col, repr(new_loser_object[col])))
        # SanitationUtils.safePrint( "loser Name is now ", new_loser_object['Name'])
        self.updates += 1
        if data.get('static'):
            self.static = False
        if(reason in ['updating', 'deleting']):
            self.important_updates += 1
            self.important_cols.append(col)
            if data.get('static'):
                self.add_problematic_update(**updateParams)
                self.important_static = False

    def tieUpdate(self, **updateParams):
        # print "tieUpdate ", col, reason
        for key in ['col']:
            assert updateParams[
                key], 'missing mandatory update param, %s' % key
        col = updateParams['col']
        if self.old_s_object:
            updateParams['value'] = self.old_s_object.get(col)
        elif self.old_m_object:
            updateParams['value'] = self.old_s_object.get(col)
        self.add_sync_pass(**updateParams)

    def getMColModTime(self, col):
        return None

    def getSColModTime(self, col):
        return None

    def updateCol(self, **updateParams):
        for key in ['col', 'data']:
            assert updateParams[key], 'missing mandatory update param %s' % key
        col = updateParams['col']
        # if self.DEBUG_UPDATE:
        #     self.registerMessage('updating col: %s | data: %s' % (col, updateParams.get('data')))
        try:
            data = updateParams['data']
            sync_mode = data['sync']
        except KeyError:
            return
        # sync_warn = data.get('warn')
        # syncstatic = data.get('static')

        if(self.col_identical(col)):
            updateParams['reason'] = 'identical'
            self.tieUpdate(**updateParams)
            return
        else:
            pass

        m_value = self.get_m_value(col)
        s_value = self.get_s_value(col)

        updateParams['mColTime'] = self.getMColModTime(col)
        updateParams['sColTime'] = self.getSColModTime(col)

        winner = self.get_winner_name(updateParams['mColTime'],
                                      updateParams['sColTime'])

        # if data.get('tracked'):
        #     mTimeRaw =  self.old_m_object.get(ColData_User.mod_time_col(col))
        #     print "mTimeRaw:",mTimeRaw
        #     m_time = self.parse_m_time(mTimeRaw)
        #     print "mTimeRaw:",m_time
        #     if not m_time: m_time = self.m_time
        #
        #     sTimeRaw = self.old_s_object.get(ColData_User.mod_time_col(col))
        #     print "sTimeRaw:",sTimeRaw
        #     m_time = self.parse_s_time(sTimeRaw)
        #     print "s_time:",s_time
        #     if not s_time: s_time = self.s_time
        #
        #     winner = self.get_winner_name(m_time, s_time)
        # else:
        #     winner = self.winner

        if('override' in str(sync_mode).lower()):
            # updateParams['reason'] = 'overriding'
            if('master' in str(sync_mode).lower()):
                winner = self.master_name
            elif('slave' in str(sync_mode).lower()):
                winner = self.slave_name
        else:
            if(self.col_similar(col)):
                updateParams['reason'] = 'similar'
                self.tieUpdate(**updateParams)
                return

            if self.merge_mode == 'merge' and not (m_value and s_value):
                if winner == self.slave_name and not s_value:
                    winner = self.master_name
                    updateParams['reason'] = 'merging'
                elif winner == self.master_name and not m_value:
                    winner = self.slave_name
                    updateParams['reason'] = 'merging'

        if 'reason' not in updateParams:
            if winner == self.slave_name:
                w_value, l_value = s_value, m_value
            else:
                w_value, l_value = m_value, s_value

            if not w_value:
                updateParams['reason'] = 'deleting'
            elif not l_value:
                updateParams['reason'] = 'inserting'
            else:
                updateParams['reason'] = 'updating'

        updateParams['subject'] = winner
        self.loserUpdate(**updateParams)

    def update(self, syncCols):
        for col, data in syncCols.items():
            self.updateCol(col=col, data=data)
        # if self.m_updated:
        #     self.new_m_object.refreshContactObjects()
        # if self.s_updated:
        #     self.new_s_object.refreshContactObjects()

    def get_info_components(self, info_fmt="%s"):
        return [
            (info_fmt % ("static", "yes" if self.static else "no")),
            (info_fmt % ("important_static", "yes" if self.important_static else "no"))
        ]

    def tabulate(self, tablefmt=None):
        subtitle_fmt = heading_fmt = "%s"
        info_delimeter = "\n"
        info_fmt = "%s: %s"
        if(tablefmt == "html"):
            heading_fmt = "<h2>%s</h2>"
            subtitle_fmt = "<h3>%s</h3>"
            info_delimeter = "<br/>"
            info_fmt = "<strong>%s:</strong> %s"
        old_match = Match([self.old_m_object], [self.old_s_object])
        # if self.DEBUG_UPDATE:
        #     self.registerMessage(old_match.__str__())
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
    def getSlaveUpdatesNativeRecursive(self, col, updates=None):
        return updates

    def getSlaveUpdatesRecursive(self, col, updates=None):
        return updates

    def getMasterUpdatesRecursive(self, col, updates=None):
        return updates

    def getSlaveUpdatesNative(self):
        updates = OrderedDict()
        for col, warnings in self.sync_warnings.items():
            if self.DEBUG_UPDATE:
                self.registerMessage(u"checking col %s" % unicode(col))
            for warning in warnings:
                if self.DEBUG_UPDATE:
                    self.registerMessage(
                        u"-> checking warning %s" % unicode(warning))
                subject = warning['subject']
                if subject == self.opposite_src(self.slave_name):
                    updates = self.getSlaveUpdatesNativeRecursive(col, updates)
        if self.DEBUG_UPDATE:
            self.registerMessage(u"returned %s" % unicode(updates))
        return updates

    def getSlaveUpdates(self):
        updates = OrderedDict()
        for col, warnings in self.sync_warnings.items():
            for warning in warnings:
                subject = warning['subject']
                if subject == self.opposite_src(self.slave_name):
                    updates = self.getSlaveUpdatesRecursive(col, updates)
        if self.DEBUG_UPDATE:
            self.registerMessage(u"returned %s" % unicode(updates))
        return updates

    def getMasterUpdates(self):
        updates = OrderedDict()
        for col, warnings in self.sync_warnings.items():
            for warning in warnings:
                subject = warning['subject']
                if subject == self.opposite_src(self.master_name):
                    updates = self.getMasterUpdatesRecursive(col, updates)
        if self.DEBUG_UPDATE:
            self.registerMessage(u"returned %s" % unicode(updates))
        return updates

    def display_slave_changes(self, tablefmt=None):
        if self.sync_warnings:
            info_delimeter = "\n"
            # subtitle_fmt = "%s"
            if(tablefmt == "html"):
                info_delimeter = "<br/>"
                # subtitle_fmt = "<h4>%s</h4>"

            print_elements = []

            try:
                pkey = self.slave_id
                assert pkey, "primary key must be valid, %s" % repr(pkey)
            except Exception as exc:
                print_elements.append(
                    "NO %s CHANGES: must have a primary key to update user data: " % self.slave_name + repr(exc))
                pkey = None
                return info_delimeter.join(print_elements)

            updates = self.getSlaveUpdatesNative()
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
                # updates_json_base64 = SanitationUtils.encode_base64(SanitationUtils.encode_json(updates))
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
            if(tablefmt == "html"):
                info_delimeter = "<br/>"
                # subtitle_fmt = "<h4>%s</h4>"

            print_elements = []

            try:
                pkey = self.slave_id
                assert pkey, "primary key must be valid, %s" % repr(pkey)
            except Exception as exc:
                print_elements.append(
                    "NO %s CHANGES: must have a primary key to update user data: " % self.master_name + repr(exc))
                pkey = None
                return info_delimeter.join(print_elements)

            updates = self.getMasterUpdates()
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
                # updates_json_base64 = SanitationUtils.encode_base64(SanitationUtils.encode_json(updates))
                # print_elements.append(updates_json_base64)
                # return (pkey, all_updates_json_base64)
            else:
                print_elements.append(
                    "NO %s CHANGES: no user_updates or meta_updates" % self.master_name)

            return info_delimeter.join(print_elements)
        return ""

    def updateMaster(self, client):
        updates = self.getMasterUpdates()
        if not updates:
            return

        pkey = self.master_id
        return client.upload_changes(pkey, updates)

        # todo: Determine if file imported correctly and delete file

    def updateSlave(self, client):
        # SanitationUtils.safePrint(  self.display_slave_changes() )
        updates = self.getSlaveUpdatesNative()
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


class SyncUpdate_Usr(SyncUpdate):
    col_data = ColData_User
    s_meta_target = 'wp'

    def __init__(self, *args, **kwargs):
        super(SyncUpdate_Usr, self).__init__(*args, **kwargs)

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
            elif self.old_s_object.usernameActLike():
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

    def valuesSimilar(self, col, m_value, s_value):
        response = super(SyncUpdate_Usr, self).valuesSimilar(
            col, m_value, s_value)
        if not response:
            if "phone" in col.lower():
                if "preferred" in col.lower():
                    m_preferred = SanitationUtils.similarTruStrComparison(
                        m_value)
                    s_preferred = SanitationUtils.similarTruStrComparison(
                        s_value)
                    # print repr(m_value), " -> ", m_preferred
                    # print repr(s_value), " -> ", s_preferred
                    if m_preferred == s_preferred:
                        response = True
                else:
                    m_phone = SanitationUtils.similarPhoneComparison(m_value)
                    s_phone = SanitationUtils.similarPhoneComparison(s_value)
                    plen = min(len(m_phone), len(s_phone))
                    if plen > 7 and m_phone[-plen] == s_phone[-plen]:
                        response = True
            elif "role" in col.lower():
                m_role = SanitationUtils.similarComparison(m_value)
                s_role = SanitationUtils.similarComparison(s_value)
                if m_role == 'rn':
                    m_role = ''
                if s_role == 'rn':
                    s_role = ''
                if m_role == s_role:
                    response = True
            elif "address" in col.lower() and isinstance(m_value, ContactAddress):
                if(m_value != s_value):
                    pass
                    # print "M: ", m_value.__str__(out_schema="flat"), "S: ",
                    # s_value.__str__(out_schema="flat")
                response = m_value.similar(s_value)
            elif "web site" in col.lower():
                if SanitationUtils.similarURLComparison(
                        m_value) == SanitationUtils.similarURLComparison(s_value):
                    response = True

        if self.DEBUG_UPDATE:
            self.registerMessage(self.testToStr(
                col, m_value.__str__(), s_value.__str__(), response))
        return response

    #
    def getMColModTime(self, col):
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

    def getSColModTime(self, col):
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
            SyncUpdate_Usr, self).get_info_components(info_fmt)
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
            m_col_mod_time = self.getMColModTime(col)
            s_col_mod_time = self.getSColModTime(col)
            if m_col_mod_time or s_col_mod_time:
                info_components.append(info_fmt % (tracking_name, '%s: %s; %s: %s' % (
                    self.master_name,
                    TimeUtils.wp_time_to_string(m_col_mod_time),
                    self.slave_name,
                    TimeUtils.wp_time_to_string(s_col_mod_time),
                )))
        return info_components

    def getSlaveUpdatesNativeRecursive(self, col, updates=None):
        if updates is None:
            updates = OrderedDict()
        if self.DEBUG_UPDATE:
            SanitationUtils.safePrint(
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
                    if self.sColSemiStatic(alias):
                        continue
                    updates = self.getSlaveUpdatesNativeRecursive(
                        alias, updates)
        return updates

    def getSlaveUpdatesRecursive(self, col, updates=None):
        if updates is None:
            updates = OrderedDict()
        if self.DEBUG_UPDATE:
            self.registerMessage(u"checking %s" % unicode(col))
        if col in self.col_data.data:
            if self.DEBUG_UPDATE:
                self.registerMessage(u"col exists")
            data = self.col_data.data[col]
            if data.get(self.s_meta_target):
                if self.DEBUG_UPDATE:
                    self.registerMessage(u"wp exists")
                data_s = data.get(self.s_meta_target, {})
                if not data_s.get('final') and data_s.get('key'):
                    new_val = self.new_s_object.get(col)
                    updates[col] = new_val
                    if self.DEBUG_UPDATE:
                        self.registerMessage(u"newval: %s" % repr(new_val))
            if data.get('aliases'):
                if self.DEBUG_UPDATE:
                    self.registerMessage(u"has aliases")
                data_aliases = data['aliases']
                for alias in data_aliases:
                    if self.sColSemiStatic(alias):
                        if self.DEBUG_UPDATE:
                            self.registerMessage(u"Alias semistatic")
                        continue
                    else:
                        updates = self.getSlaveUpdatesRecursive(alias, updates)
        else:
            pass
            if self.DEBUG_UPDATE:
                self.registerMessage(u"col doesn't exist")
        return updates

    def getMasterUpdatesRecursive(self, col, updates=None):
        if updates is None:
            updates = OrderedDict()
        if self.DEBUG_UPDATE:
            self.registerMessage(u"checking %s" % unicode(col))
        if col in self.col_data.data:
            if self.DEBUG_UPDATE:
                self.registerMessage(u"col exists")
            data = self.col_data.data[col]
            if data.get(self.m_meta_target):
                if self.DEBUG_UPDATE:
                    self.registerMessage(u"wp exists")
                new_val = self.new_m_object.get(col)
                updates[col] = new_val
                if self.DEBUG_UPDATE:
                    self.registerMessage(u"newval: %s" % repr(new_val))
            if data.get('aliases'):
                if self.DEBUG_UPDATE:
                    self.registerMessage(u"has aliases")
                data_aliases = data['aliases']
                for alias in data_aliases:
                    if self.mColSemiStatic(alias):
                        if self.DEBUG_UPDATE:
                            self.registerMessage(u"Alias semistatic")
                        continue
                    else:
                        updates = self.getMasterUpdatesRecursive(
                            alias, updates)
        else:
            pass
            if self.DEBUG_UPDATE:
                self.registerMessage(u"col doesn't exist")
        return updates


class SyncUpdate_Usr_Api(SyncUpdate_Usr):
    s_meta_target = 'wp-api'

    def getSlaveUpdatesNativeRecursive(self, col, updates=None):
        if updates is None:
            updates = OrderedDict()
        if self.DEBUG_UPDATE:
            self.registerMessage(u"checking %s : %s" %
                                 (unicode(col), self.col_data.data.get(col)))
        if col in self.col_data.data:
            if self.DEBUG_UPDATE:
                self.registerMessage(u"col exists")
            data = self.col_data.data[col]
            if data.get(self.s_meta_target):
                if self.DEBUG_UPDATE:
                    self.registerMessage(u"wp-api exists")
                data_s = data.get(self.s_meta_target, {})
                if not data_s.get('final') and data_s.get('key'):
                    new_val = self.new_s_object.get(col)
                    new_key = col
                    if 'key' in data_s:
                        new_key = data_s.get('key')
                    if data_s.get('meta'):
                        if not 'meta' in updates:
                            updates['meta'] = OrderedDict()
                        updates['meta'][new_key] = new_val
                    else:
                        updates[new_key] = new_val
                    if self.DEBUG_UPDATE:
                        self.registerMessage(u"newval: %s" % repr(new_val))
                    if self.DEBUG_UPDATE:
                        self.registerMessage(u"newkey: %s" % repr(new_key))
            if data.get('aliases'):
                if self.DEBUG_UPDATE:
                    self.registerMessage(u"has aliases")
                data_aliases = data['aliases']
                for alias in data_aliases:
                    if self.sColSemiStatic(alias):
                        if self.DEBUG_UPDATE:
                            self.registerMessage(u"Alias semistatic")
                        continue
                    else:
                        updates = self.getSlaveUpdatesNativeRecursive(
                            alias, updates)
        else:
            if self.DEBUG_UPDATE:
                self.registerMessage(u"col doesn't exist")
        return updates


class SyncUpdate_Prod(SyncUpdate):
    col_data = ColData_Prod
    s_meta_target = 'wp-api'

    def __init__(self, *args, **kwargs):
        super(SyncUpdate_Prod, self).__init__(*args, **kwargs)

    @property
    def master_id(self):
        return self.get_m_value('rowcount')

    @property
    def slave_id(self):
        return self.get_s_value('ID')

    def valuesSimilar(self, col, m_value, s_value):
        response = super(SyncUpdate_Prod, self).valuesSimilar(
            col, m_value, s_value)
        if col in self.col_data.data:
            col_data = self.col_data.data[col]
            if col_data.get('type'):
                if col_data.get('type') == 'currency':
                    m_price = SanitationUtils.similarCurrencyComparison(m_value)
                    s_price = SanitationUtils.similarCurrencyComparison(s_value)
                    if m_price == s_price:
                        response = True
        elif not response:
            if col is 'descsum':
                m_desc = SanitationUtils.similarMarkupComparison(m_value)
                s_desc = SanitationUtils.similarMarkupComparison(s_value)
                if m_desc == s_desc:
                    response = True
            elif col is 'CVC':
                m_com = SanitationUtils.similarComparison(m_value) or '0'
                s_com = SanitationUtils.similarComparison(s_value) or '0'
                if m_com == s_com:
                    response = True

        if self.DEBUG_UPDATE:
            self.registerMessage(self.testToStr(
                col, m_value.__repr__(), s_value.__repr__(), response))
        return response


class SyncUpdate_Prod_Woo(SyncUpdate_Prod):
    col_data = ColData_Woo

    def getSlaveUpdatesNativeRecursive(self, col, updates=None):
        if updates is None:
            updates = OrderedDict()
        # SanitationUtils.safePrint("getting updates for col %s, updates: %s" % (col, str(updates)))
        # if col == 'catlist':
        #     if hasattr(self.old_s_object, 'isVariation') and self.old_s_object.isVariation:
        #         # print "excluded item because isVariation"
        #         return updates
        #     else:
        #         update_catlist = self.new_s_object.get('catlist')
        #         actual_catlist = self.old_s_object.categories.keys()
        #         print "comparing cats of %s" % repr(self.new_s_object)
        #         static_catlist = list(set(update_catlist) | set(actual_catlist))
        #         # updates['categories'] = static_catlist
        #         # update_catids = []
        #         return updates
        #         # new_catlist = list(set(update_catlist) - set(actual_catlist))
        #         # print update_catlist
        #         # print actual_catlist

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
            # if data.get('aliases'):
            #     data_aliases = data.get('aliases')
            #     for alias in data_aliases:
            #         if self.sColSemiStatic(alias):
            #             continue
            #         updates = self.getSlaveUpdatesNativeRecursive(alias, updates)
        return updates

    def getSlaveUpdatesRecursive(self, col, updates=None):
        if updates is None:
            updates = OrderedDict()
        if self.DEBUG_UPDATE:
            self.registerMessage(u"checking %s" % unicode(col))
        if col in self.col_data.data:
            if self.DEBUG_UPDATE:
                self.registerMessage(u"col exists")
            data = self.col_data.data[col]
            if data.get(self.s_meta_target):
                if self.DEBUG_UPDATE:
                    self.registerMessage(u"wp exists")
                data_s = data.get(self.s_meta_target, {})
                if not data_s.get('final') and data_s.get('key'):
                    new_val = self.new_s_object.get(col)
                    updates[col] = new_val
                    if self.DEBUG_UPDATE:
                        self.registerMessage(u"newval: %s" % repr(new_val))
            # if data.get('aliases'):
            #     if self.DEBUG_UPDATE: self.registerMessage( u"has aliases" )
            #     data_aliases = data['aliases']
            #     for alias in data_aliases:
            #         if self.sColSemiStatic(alias):
            #             if self.DEBUG_UPDATE: self.registerMessage( u"Alias semistatic" )
            #             continue
            #         else:
            #             updates = self.getSlaveUpdatesRecursive(alias, updates)
        else:
            pass
            if self.DEBUG_UPDATE:
                self.registerMessage(u"col doesn't exist")
        return updates

    def getMasterUpdatesRecursive(self, col, updates=None):
        if updates is None:
            updates = OrderedDict()
        if self.DEBUG_UPDATE:
            self.registerMessage(u"checking %s" % unicode(col))

        if col == 'catlist':
            if hasattr(self.old_s_object,
                       'isVariation') and self.old_s_object.isVariation:
                # print "excluded item because isVariation"
                return updates

        if col in self.col_data.data:
            if self.DEBUG_UPDATE:
                self.registerMessage(u"col exists")
            data = self.col_data.data[col]
            if data.get(self.m_meta_target):
                if self.DEBUG_UPDATE:
                    self.registerMessage(u"wp exists")
                new_val = self.new_m_object.get(col)
                updates[col] = new_val
                if self.DEBUG_UPDATE:
                    self.registerMessage(u"newval: %s" % repr(new_val))
            # if data.get('aliases'):
            #     if self.DEBUG_UPDATE: self.registerMessage( u"has aliases" )
            #     data_aliases = data['aliases']
            #     for alias in data_aliases:
            #         if self.mColSemiStatic(alias):
            #             if self.DEBUG_UPDATE: self.registerMessage( u"Alias semistatic" )
            #             continue
            #         else:
            #             updates = self.getMasterUpdatesRecursive(alias, updates)
        else:
            pass
            if self.DEBUG_UPDATE:
                self.registerMessage(u"col doesn't exist")
        return updates


class SyncUpdate_Var_Woo(SyncUpdate_Prod_Woo):
    pass


class SyncUpdate_Cat_Woo(SyncUpdate):
    col_data = ColData_Woo
    s_meta_target = 'wp-api'

    @property
    def master_id(self):
        return self.get_m_value('rowcount')

    @property
    def slave_id(self):
        return self.get_s_value('ID')

    def valuesSimilar(self, col, m_value, s_value):
        response = super(SyncUpdate_Cat_Woo, self).valuesSimilar(
            col, m_value, s_value)
        if not response:
            if col is 'descsum':
                m_desc = SanitationUtils.similarMarkupComparison(m_value)
                s_desc = SanitationUtils.similarMarkupComparison(s_value)
                if m_desc == s_desc:
                    response = True

        if self.DEBUG_UPDATE:
            self.registerMessage(self.testToStr(
                col, m_value.__repr__(), s_value.__repr__(), response))
        return response

    def getSlaveUpdatesNativeRecursive(self, col, updates=None):
        if updates is None:
            updates = OrderedDict()
        # SanitationUtils.safePrint("getting updates for col %s, updates: %s" % (col, str(updates)))

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
            # if data.get('aliases'):
            #     data_aliases = data.get('aliases')
            #     for alias in data_aliases:
            #         if self.sColSemiStatic(alias):
            #             continue
            #         updates = self.getSlaveUpdatesNativeRecursive(alias, updates)
        return updates

    def getSlaveUpdatesRecursive(self, col, updates=None):
        if updates is None:
            updates = OrderedDict()
        if self.DEBUG_UPDATE:
            self.registerMessage(u"checking %s" % unicode(col))
        if col in self.col_data.data:
            if self.DEBUG_UPDATE:
                self.registerMessage(u"col exists")
            data = self.col_data.data[col]
            if data.get(self.s_meta_target):
                if self.DEBUG_UPDATE:
                    self.registerMessage(u"wp exists")
                data_s = data.get(self.s_meta_target, {})
                if not data_s.get('final') and data_s.get('key'):
                    new_val = self.new_s_object.get(col)
                    updates[col] = new_val
                    if self.DEBUG_UPDATE:
                        self.registerMessage(u"newval: %s" % repr(new_val))
            # if data.get('aliases'):
            #     if self.DEBUG_UPDATE: self.registerMessage( u"has aliases" )
            #     data_aliases = data['aliases']
            #     for alias in data_aliases:
            #         if self.sColSemiStatic(alias):
            #             if self.DEBUG_UPDATE: self.registerMessage( u"Alias semistatic" )
            #             continue
            #         else:
            #             updates = self.getSlaveUpdatesRecursive(alias, updates)
        else:
            pass
            if self.DEBUG_UPDATE:
                self.registerMessage(u"col doesn't exist")
        return updates

    def getMasterUpdatesRecursive(self, col, updates=None):
        if updates is None:
            updates = OrderedDict()
        if self.DEBUG_UPDATE:
            self.registerMessage(u"checking %s" % unicode(col))

        if col == 'catlist':
            if hasattr(self.old_s_object,
                       'isVariation') and self.old_s_object.isVariation:
                # print "excluded item because isVariation"
                return updates

        if col in self.col_data.data:
            if self.DEBUG_UPDATE:
                self.registerMessage(u"col exists")
            data = self.col_data.data[col]
            if data.get(self.m_meta_target):
                if self.DEBUG_UPDATE:
                    self.registerMessage(u"wp exists")
                new_val = self.new_m_object.get(col)
                updates[col] = new_val
                if self.DEBUG_UPDATE:
                    self.registerMessage(u"newval: %s" % repr(new_val))
            # if data.get('aliases'):
            #     if self.DEBUG_UPDATE: self.registerMessage( u"has aliases" )
            #     data_aliases = data['aliases']
            #     for alias in data_aliases:
            #         if self.mColSemiStatic(alias):
            #             if self.DEBUG_UPDATE: self.registerMessage( u"Alias semistatic" )
            #             continue
            #         else:
            #             updates = self.getMasterUpdatesRecursive(alias, updates)
        else:
            pass
            if self.DEBUG_UPDATE:
                self.registerMessage(u"col doesn't exist")
        return updates
