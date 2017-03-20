#pylint: disable=too-many-lines
"""
Utilites for storing and performing operations on pending updates
"""
# TODO: fix too-many-lines

from collections import OrderedDict
from copy import deepcopy
from tabulate import tabulate

from woogenerator.utils import SanitationUtils, TimeUtils, Registrar #, UnicodeCsvDialectUtils
from woogenerator.contact_objects import ContactAddress
from woogenerator.coldata import ColData_Base, ColData_User, ColData_Prod, ColData_Woo
from woogenerator.matching import Match
from woogenerator.parsing.abstract import ImportObject

class SyncUpdate(Registrar): #pylint: disable=too-many-instance-attributes,too-many-public-methods
    """
    Stores information about and performs operations on a pending update
    """
    # TODO: fix too-many-instance-attributes,too-many-public-methods

    colData = ColData_Base
    master_name = None
    slave_name = None
    merge_mode = None
    s_meta_target = None
    m_meta_target = 'act'

    @classmethod
    def set_globals(cls, master_name, slave_name, merge_mode, default_last_sync):
        """
        sets the class attributes to those specified in the user config
        """
        # TODO: Fix this awful mess

        cls.master_name = master_name
        cls.slave_name = slave_name
        cls.merge_mode = merge_mode
        cls.default_last_sync = default_last_sync

    def __init__(self, oldMObject, oldSObject, lastSync=None):
        super(SyncUpdate, self).__init__()
        for old_object in oldMObject, oldSObject:
            assert isinstance(old_object, ImportObject)
        if not lastSync:
            lastSync = self.default_last_sync
        # print "Creating SyncUpdate: ", oldMObject.__repr__(), oldSObject.__repr__()
        self.oldMObject = oldMObject
        self.oldSObject = oldSObject
        self.tTime = TimeUtils.wp_strp_mktime(lastSync)

        self.newSObject = None
        self.newMObject = None
        self.static = True
        self.importantStatic = True
        self.syncWarnings = OrderedDict()
        self.syncPasses = OrderedDict()
        self.syncProblematics = OrderedDict()
        self.updates = 0
        self.importantUpdates = 0
        self.importantCols = []
        self.mDeltas = False
        self.sDeltas = False

        self.mTime = 0
        self.sTime = 0
        self.bTime = 0

    @property
    def sUpdated(self): return bool( self.newSObject)
    @property
    def mUpdated(self): return bool(self.newMObject)
    @property
    def eUpdated(self): return self.sUpdated or self.mUpdated
    @property
    def lTime(self): return max(self.mTime, self.sTime)
    @property
    def mMod(self): return self.mTime >= self.tTime
    @property
    def sMod(self): return self.sTime >= self.tTime

    @property
    def MasterID(self):
        raise NotImplementedError()

    @property
    def SlaveID(self):
        raise NotImplementedError()

    # @property
    # def winner(self): return self.winner

    # def colBlank(self, col):
    #     mValue = (m_object.get(col) or "")
    #     sValue = (s_object.get(col) or "")
    #     return (not mValue and not sValue)

    def getWinnerName(self, mTime, sTime):
        # print "determining winnner: ", mTime, sTime
        if not sTime:
            return self.master_name
        elif not mTime:
            return self.slave_name
        else:
            return self.slave_name if(sTime >= mTime) else self.master_name

    def parseMTime(self, rawMTime):
        return TimeUtils.act_server_to_local_time(TimeUtils.act_strp_mktime(rawMTime))

    def parseSTime(self, rawSTime):
        return TimeUtils.wp_server_to_local_time(TimeUtils.wp_strp_mktime(rawSTime))

    # def getWinnerKey(self, key):
    #     # if self.syncWarnings and key in self.syncWarnings.keys():
    #     #     # print "key in warnings"
    #     #     keySyncWarnings = self.syncWarnings[key]
    #     #     assert len(keySyncWarnings) < 2
    #     #     subject, reason, oldVal, newVal, data = keySyncWarnings[0]
    #     #     return newVal
    #     # if self.syncPasses and key in self.syncPasses.keys():
    #     #     # print "key in passes"
    #     #     keySyncPasses = self.syncPasses[key]
    #     #     assert len(keySyncPasses) < 2
    #     #     reason, val, data = keySyncPasses[0]
    #     #     return val
    #     # else:
    #     if self.winner == self.slave_name and self.newSObject:
    #         return self.newSObject.get(key)
    #     if self.winner == self.master_name and self.newMObject:
    #         return self.newMObject.get(key)
    #     self.registerError( "could not find any value for key {}".format(key) )
    #     return None

    def sanitizeValue(self, col, value):
        # print "sanitizing", col, repr(value)
        if 'phone' in col.lower():
            if 'preferred' in col.lower():
                if value and len(SanitationUtils.stripNonNumbers(value)) > 1:
                    # print "value nullified", value
                    return ""
        return value

    def getMValue(self, col):
        return self.sanitizeValue(col, self.oldMObject.get(col) or "")

    def getSValue(self, col):
        return self.sanitizeValue(col, self.oldSObject.get(col) or "")

    def getNewMValue(self, col):
        if self.newMObject:
            return self.sanitizeValue(col, self.newMObject.get(col) or "")
        else:
            return self.getMValue(col)

    def getNewSValue(self, col):
        if self.newSObject:
            return self.sanitizeValue(col, self.newSObject.get(col) or "")
        else:
            return self.getSValue(col)

    def valuesSimilar(self, col, mValue, sValue):
        response = False
        if not (mValue or sValue):
            response = True
        elif not (mValue and sValue):
            response = False
        #check if they are similar
        if SanitationUtils.similarComparison(mValue) == SanitationUtils.similarComparison(sValue):
            response = True

        if self.DEBUG_UPDATE: self.registerMessage(self.testToStr(col, mValue, sValue, response))
        return response

    def colIdentical(self, col):
        mValue = self.getMValue(col)
        sValue = self.getSValue(col)
        response = mValue == sValue
        if self.DEBUG_UPDATE: self.registerMessage( self.testToStr(col, mValue, sValue, response) )
        return response

    def colSimilar(self, col):
        mValue = self.getMValue(col)
        sValue = self.getSValue(col)
        response = self.valuesSimilar(col, mValue, sValue)
        if self.DEBUG_UPDATE: self.registerMessage( self.testToStr(col, mValue, sValue, response) )
        return response

    def newColIdentical(self, col):
        mValue = self.getNewMValue(col)
        sValue = self.getNewSValue(col)
        response = mValue == sValue
        if self.DEBUG_UPDATE: self.registerMessage( self.testToStr(col, mValue, sValue, response) )
        return response

    def mColStatic(self, col):
        oValue = self.getMValue(col)
        nValue = self.getNewMValue(col)
        response = oValue == nValue
        if self.DEBUG_UPDATE: self.registerMessage( self.testToStr(col, oValue, nValue, response) )
        return response

    def sColStatic(self, col):
        oValue = self.getSValue(col)
        nValue = self.getNewSValue(col)
        response = oValue == nValue
        if self.DEBUG_UPDATE: self.registerMessage( self.testToStr(col, oValue, nValue, response) )
        return response

    def mColSemiStatic(self, col):
        oValue = self.getMValue(col)
        nValue = self.getNewMValue(col)
        response = self.valuesSimilar(col, oValue, nValue)
        if self.DEBUG_UPDATE: self.registerMessage( self.testToStr(col, oValue, nValue, response) )
        return response

    def sColSemiStatic(self, col):
        oValue = self.getSValue(col)
        nValue = self.getNewSValue(col)
        response = self.valuesSimilar(col, oValue, nValue)
        if self.DEBUG_UPDATE: self.registerMessage( self.testToStr(col, oValue, nValue, response) )
        return response

    def testToStr(self, col, val1, val2, res):
        return u"testing col %s: %s | %s -> %s" % (
            unicode(col),
            repr(val1),
            repr(val2),
            SanitationUtils.boolToTruishString(res)
        )


    def updateToStr(self, updateType, updateParams):
        assert isinstance(updateType, str)
        assert 'col' in updateParams
        out = u""
        out += "SYNC %s:" % updateType
        out += " | %s " % SanitationUtils.coerceAscii(self)
        out += " | col:  %s" % updateParams['col']
        if 'subject' in updateParams:
            out += " | subj: %s " % updateParams['subject']
        if 'reason' in updateParams:
            out += " | reas: %s " % updateParams['reason']
        if updateType in ['WARN', 'PROB']:
            if 'oldWinnerValue' in updateParams:
                out += " | OLD: %s " % SanitationUtils.coerceAscii(updateParams['oldWinnerValue'])
            if 'oldLoserValue' in updateParams:
                out += " | NEW: %s " % SanitationUtils.coerceAscii(updateParams['oldLoserValue'])
        return out

    def addProblematicUpdate(self, **updateParams):
        for key in ['col', 'subject', 'reason']:
            assert updateParams[key], 'missing mandatory prob param %s' % key
        col = updateParams['col']
        if col not in self.syncProblematics.keys():
            self.syncProblematics[col] = []
        self.syncProblematics[col].append(updateParams)
        self.registerWarning(self.updateToStr('PROB', updateParams))
        # self.registerWarning("SYNC PROB: %s | %s" % (self.__str__(), SanitationUtils.coerceUnicode(updateParams)))

    def addSyncWarning(self, **updateParams):
        for key in ['col', 'subject', 'reason']:
            assert updateParams[key], 'missing mandatory warning param %s' % key
        col = updateParams['col']
        if col not in self.syncWarnings.keys():
            self.syncWarnings[col] = []
        self.syncWarnings[col].append(updateParams)
        if self.DEBUG_UPDATE: self.registerWarning(self.updateToStr('WARN', updateParams))
        # self.registerWarning("SYNC WARNING: %s | %s" % (self.__str__(), SanitationUtils.coerceUnicode(updateParams)))

    def addSyncPass(self, **updateParams):
        for key in ['col']:
            assert updateParams[key], 'missing mandatory pass param %s' % key
        col = updateParams['col']
        if col not in self.syncPasses.keys():
            self.syncPasses[col] = []
        self.syncPasses[col].append(updateParams)
        if self.DEBUG_UPDATE: self.registerWarning(self.updateToStr('PASS', updateParams))
        # if self.DEBUG_UPDATE: self.registerMessage("SYNC PASS: %s | %s" % (self.__str__(), SanitationUtils.coerceUnicode(updateParams)))


    def displayUpdateList(self, updateList, tablefmt=None):
        if updateList:
            delimeter = "<br/>" if tablefmt=="html" else "\n"
            subject_fmt = "<h4>%s</h4>" if tablefmt=="html" else "%s"
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
                    warning_fmtd = dict([\
                        (key, SanitationUtils.sanitizeForTable(val))\
                        for key, val in warning.items()\
                        if key in header
                    ])
                    for key in ['mColTime', 'sColTime']:
                        try:
                            rawTime = int(warning[key])
                            if rawTime:
                                warning_fmtd[key] = TimeUtils.wp_time_to_string(rawTime)
                        except Exception, e:
                            if(e):
                                pass
                    subjects[subject].append(warning_fmtd)
            tables = []
            for subject, warnings in subjects.items():
                antiSubject_fmtd = subject_fmt % self.opposite_src(subject)
                table = [header]+warnings
                table_fmtd = tabulate(table, headers='firstrow', \
                                      tablefmt=tablefmt )
                tables.append(delimeter.join([antiSubject_fmtd, table_fmtd]))
            return delimeter.join(tables)
        else:
            return ""

    def displaySyncWarnings(self, tablefmt=None):
        return self.displayUpdateList(self.syncWarnings, tablefmt)

    def displayProblematicUpdates(self, tablefmt=None):
        return self.displayUpdateList(self.syncProblematics, tablefmt)

    # def getOldLoserObject(self, winner=None):
    #     if not winner: winner = self.winner
    #     if(winner == self.master_name):
    #         oldLoserObject = self.oldSObject

    def opposite_src(self, subject):
        if subject == self.master_name:
            return self.slave_name
        else:
            return self.master_name

    # def loserUpdate(self, winner, col, reason = "", data={}, sTime=None, mTime=None):
    def loserUpdate(self, **updateParams):
        for key in ['col', 'subject']:
            assert updateParams[key], 'missing mandatory update param, %s from %s' % (key, updateParams)

        col = updateParams['col']
        winner = updateParams['subject']
        reason = updateParams.get('reason', '')
        data = updateParams.get('data', {})


        # self.registerMessage("loserUpdate " + SanitationUtils.coerceUnicode([winner, col, reason]))
        if(winner == self.master_name):
            # oldLoserObject = self.oldSObject
            updateParams['oldLoserValue'] = self.getSValue(col)
            # oldWinnerObject = self.oldMObject
            updateParams['oldWinnerValue'] = self.getMValue(col)
            if not self.newSObject: self.newSObject = deepcopy(self.oldSObject)
            newLoserObject = self.newSObject
            if data.get('delta') and reason in ['updating', 'deleting']:
                # print "setting sDeltas"
                self.sDeltas = True
        elif(winner == self.slave_name):
            # oldLoserObject = self.oldMObject
            updateParams['oldLoserValue'] = self.getMValue(col)
            # oldWinnerObject = self.oldSObject
            updateParams['oldWinnerValue'] = self.getSValue(col)
            if not self.newMObject: self.newMObject = deepcopy(self.oldMObject)
            newLoserObject = self.newMObject
            if data.get('delta') and reason in ['updating', 'deleting']:
                # print "setting mDeltas"
                self.mDeltas = True
        # if data.get('warn'):

        self.addSyncWarning(**updateParams)
        # self.addSyncWarning(col, winner, reason, oldLoserValue, oldWinnerValue, data, sTime, mTime)
        # SanitationUtils.safePrint("loser %s was %s" % (col, repr(newLoserObject[col])))
        # SanitationUtils.safePrint("updating to ", oldWinnerValue)
        if data.get('delta'):
            # print "delta true for ", col, \
            # "loser", updateParams['oldLoserValue'], \
            # "winner", updateParams['oldWinnerValue']
            newLoserObject[self.colData.deltaCol(col)] = updateParams['oldLoserValue']

        newLoserObject[col] = updateParams['oldWinnerValue']
        # SanitationUtils.safePrint( "loser %s is now %s" % (col, repr(newLoserObject[col])))
        # SanitationUtils.safePrint( "loser Name is now ", newLoserObject['Name'])
        self.updates += 1
        if data.get('static'):
            self.static = False
        if(reason in ['updating', 'deleting']):
            self.importantUpdates += 1
            self.importantCols.append(col)
            if data.get('static'):
                self.addProblematicUpdate(**updateParams)
                self.importantStatic = False

    def tieUpdate(self, **updateParams):
        # print "tieUpdate ", col, reason
        for key in ['col']:
            assert updateParams[key], 'missing mandatory update param, %s' % key
        col = updateParams['col']
        if self.oldSObject:
            updateParams['value'] = self.oldSObject.get(col)
        elif self.oldMObject:
            updateParams['value'] = self.oldSObject.get(col)
        self.addSyncPass(**updateParams)

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

        if(self.colIdentical(col)):
            updateParams['reason'] = 'identical'
            self.tieUpdate(**updateParams)
            return
        else:
            pass

        mValue = self.getMValue(col)
        sValue = self.getSValue(col)

        updateParams['mColTime'] = self.getMColModTime(col)
        updateParams['sColTime'] = self.getSColModTime(col)

        winner = self.getWinnerName(updateParams['mColTime'],
                                    updateParams['sColTime'] )

        # if data.get('tracked'):
        #     mTimeRaw =  self.oldMObject.get(ColData_User.modTimeCol(col))
        #     print "mTimeRaw:",mTimeRaw
        #     mTime = self.parseMTime(mTimeRaw)
        #     print "mTimeRaw:",mTime
        #     if not mTime: mTime = self.mTime
        #
        #     sTimeRaw = self.oldSObject.get(ColData_User.modTimeCol(col))
        #     print "sTimeRaw:",sTimeRaw
        #     mTime = self.parseSTime(sTimeRaw)
        #     print "sTime:",sTime
        #     if not sTime: sTime = self.sTime
        #
        #     winner = self.getWinnerName(mTime, sTime)
        # else:
        #     winner = self.winner

        if( 'override' in str(sync_mode).lower() ):
            # updateParams['reason'] = 'overriding'
            if( 'master' in str(sync_mode).lower() ):
                winner = self.master_name
            elif( 'slave' in str(sync_mode).lower() ):
                winner = self.slave_name
        else:
            if(self.colSimilar(col)):
                updateParams['reason'] = 'similar'
                self.tieUpdate(**updateParams)
                return

            if self.merge_mode == 'merge' and not (mValue and sValue):
                if winner == self.slave_name and not sValue:
                    winner = self.master_name
                    updateParams['reason'] = 'merging'
                elif winner == self.master_name and not mValue:
                    winner = self.slave_name
                    updateParams['reason'] = 'merging'

        if 'reason' not in updateParams:
            if winner == self.slave_name:
                wValue, lValue = sValue, mValue
            else:
                wValue, lValue = mValue, sValue

            if not wValue:
                updateParams['reason'] = 'deleting'
            elif not lValue:
                updateParams['reason'] = 'inserting'
            else:
                updateParams['reason'] = 'updating'

        updateParams['subject'] = winner
        self.loserUpdate(**updateParams)

    def update(self, syncCols):
        for col, data in syncCols.items():
            self.updateCol(col=col, data=data)
        # if self.mUpdated:
        #     self.newMObject.refreshContactObjects()
        # if self.sUpdated:
        #     self.newSObject.refreshContactObjects()

    def getInfoComponents(self, info_fmt="%s"):
        return [
            (info_fmt % ("static", "yes" if self.static else "no")),
            (info_fmt % ("importantStatic", "yes" if self.importantStatic else "no"))
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
        oldMatch = Match([self.oldMObject], [self.oldSObject])
        # if self.DEBUG_UPDATE:
        #     self.registerMessage(oldMatch.__str__())
        out_str =  ""
        out_str += heading_fmt % self.__str__()
        out_str += info_delimeter.join([
            subtitle_fmt % "OLD",
            oldMatch.tabulate(cols=None, tablefmt=tablefmt)
        ])
        out_str += info_delimeter

        info_components = self.getInfoComponents(info_fmt)
        if info_components:
            info_components = [subtitle_fmt % "INFO"] + info_components
            out_str += info_delimeter.join(filter(None,info_components))
            out_str += info_delimeter

        changes_components = []
        if not self.importantStatic:
            changes_components += [
                subtitle_fmt % 'PROBLEMATIC CHANGES (%d)' % len(self.syncProblematics),
                self.displayProblematicUpdates(tablefmt),
            ]
        changes_components += [
            subtitle_fmt % 'CHANGES (%d!%d)' % (self.updates, self.importantUpdates),
            self.displaySyncWarnings(tablefmt),
        ]
        if self.newMObject:
            changes_components += [
                subtitle_fmt % '%s CHANGES' % self.master_name,
                self.displayMasterChanges(tablefmt),
            ]
        if self.newSObject:
            changes_components += [
                subtitle_fmt % '%s CHANGES' % self.slave_name,
                self.displaySlaveChanges(tablefmt),
            ]
        out_str += info_delimeter.join(filter(None,changes_components))
        newMatch = Match([self.newMObject], [self.newSObject])
        out_str += info_delimeter
        out_str += info_delimeter.join([
            subtitle_fmt % 'NEW',
            newMatch.tabulate(cols=None, tablefmt=tablefmt)
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
        for col, warnings in self.syncWarnings.items():
            if self.DEBUG_UPDATE: self.registerMessage( u"checking col %s" % unicode(col) )
            for warning in warnings:
                if self.DEBUG_UPDATE: self.registerMessage( u"-> checking warning %s" % unicode(warning) )
                subject = warning['subject']
                if subject == self.opposite_src(self.slave_name):
                    updates = self.getSlaveUpdatesNativeRecursive(col, updates)
        if self.DEBUG_UPDATE: self.registerMessage( u"returned %s" % unicode(updates) )
        return updates

    def getSlaveUpdates(self):
        updates = OrderedDict()
        for col, warnings in self.syncWarnings.items():
            for warning in warnings:
                subject = warning['subject']
                if subject == self.opposite_src(self.slave_name):
                    updates = self.getSlaveUpdatesRecursive(col, updates)
        if self.DEBUG_UPDATE: self.registerMessage( u"returned %s" % unicode(updates) )
        return updates

    def getMasterUpdates(self):
        updates = OrderedDict()
        for col, warnings in self.syncWarnings.items():
            for warning in warnings:
                subject = warning['subject']
                if subject == self.opposite_src(self.master_name):
                    updates = self.getMasterUpdatesRecursive(col, updates)
        if self.DEBUG_UPDATE: self.registerMessage( u"returned %s" % unicode(updates) )
        return updates

    def displaySlaveChanges(self, tablefmt=None):
        if self.syncWarnings:
            info_delimeter = "\n"
            # subtitle_fmt = "%s"
            if(tablefmt == "html"):
                info_delimeter = "<br/>"
                # subtitle_fmt = "<h4>%s</h4>"

            print_elements = []

            try:
                pkey = self.SlaveID
                assert pkey, "primary key must be valid, %s" % repr(pkey)
            except Exception as e:
                print_elements.append("NO %s CHANGES: must have a primary key to update user data: " % self.slave_name +repr(e))
                pkey = None
                return info_delimeter.join(print_elements)

            updates = self.getSlaveUpdatesNative()
            additional_updates = OrderedDict()
            if pkey:
                additional_updates['ID'] = pkey

            if updates:
                updates_table = OrderedDict([(key, [value]) for key, value in additional_updates.items() + updates.items()])
                print_elements.append(
                    info_delimeter.join([
                        # subtitle_fmt % "all updates" ,
                        tabulate(updates_table, headers="keys", tablefmt=tablefmt)
                    ])
                )
                # updates_json_base64 = SanitationUtils.encodeBase64(SanitationUtils.encodeJSON(updates))
                # print_elements.append(updates_json_base64)
                # return (pkey, all_updates_json_base64)
            else:
                print_elements.append("NO %s CHANGES: no user_updates or meta_updates" % self.slave_name)

            return info_delimeter.join(print_elements)
        return ""

    def displayMasterChanges(self, tablefmt=None):
        if self.syncWarnings:
            info_delimeter = "\n"
            # subtitle_fmt = "%s"
            if(tablefmt == "html"):
                info_delimeter = "<br/>"
                # subtitle_fmt = "<h4>%s</h4>"

            print_elements = []

            try:
                pkey = self.SlaveID
                assert pkey, "primary key must be valid, %s" % repr(pkey)
            except Exception as e:
                print_elements.append("NO %s CHANGES: must have a primary key to update user data: " % self.master_name+repr(e))
                pkey = None
                return info_delimeter.join(print_elements)

            updates = self.getMasterUpdates()
            additional_updates = OrderedDict()
            if pkey:
                additional_updates['ID'] = pkey

            if updates:
                updates_table = OrderedDict([(key, [value]) for key, value in additional_updates.items() + updates.items()])
                print_elements.append(
                    info_delimeter.join([
                        # subtitle_fmt % "changes" ,
                        tabulate(updates_table, headers="keys", tablefmt=tablefmt)
                    ])
                )
                # updates_json_base64 = SanitationUtils.encodeBase64(SanitationUtils.encodeJSON(updates))
                # print_elements.append(updates_json_base64)
                # return (pkey, all_updates_json_base64)
            else:
                print_elements.append("NO %s CHANGES: no user_updates or meta_updates" %self.master_name)

            return info_delimeter.join(print_elements)
        return ""

    def updateMaster(self, client):
        updates = self.getMasterUpdates()
        if not updates:
            return

        pkey = self.MasterID
        return client.uploadChanges(pkey, updates)

        #todo: Determine if file imported correctly and delete file

    def updateSlave(self, client):
        # SanitationUtils.safePrint(  self.displaySlaveChanges() )
        updates = self.getSlaveUpdatesNative()
        if not updates:
            return

        pkey = self.SlaveID

        return client.uploadChanges(pkey, updates)

    def __cmp__(self, other):
        return -cmp(self.bTime, other.bTime)
        # return -cmp((self.importantUpdates, self.updates, - self.lTime), (other.importantUpdates, other.updates, - other.lTime))

    def __str__(self):
        return "update < %7s | %7s >" % (self.MasterID, self.SlaveID)

    def __nonzero__(self):
        return self.eUpdated

class SyncUpdate_Usr(SyncUpdate):
    colData = ColData_User
    s_meta_target = 'wp'

    def __init__(self, *args, **kwargs):
        super(SyncUpdate_Usr, self).__init__(*args, **kwargs)

        self.mTime = self.oldMObject.act_modtime
        self.sTime = self.oldSObject.wp_modtime
        self.bTime = self.oldMObject.last_sale
        self.winner = self.getWinnerName(self.mTime, self.sTime)

        #extra heuristics for merge mode:
        if self.merge_mode == 'merge' and not self.sMod:
            might_be_sEdited = False
            if not self.oldSObject.addressesActLike():
                might_be_sEdited = True
            elif self.oldSObject.get('Home Country') == 'AU':
                might_be_sEdited = True
            elif self.oldSObject.usernameActLike():
                might_be_sEdited = True
            if might_be_sEdited:
                # print repr(self.oldSObject), "might be edited"
                self.sTime = self.tTime
                if self.mMod:
                    self.static = False
                    # self.importantStatic = False

    @property
    def MasterID(self):
        return self.getMValue('MYOB Card ID')

    @property
    def SlaveID(self):
        return self.getSValue("Wordpress ID")

    def valuesSimilar(self, col, mValue, sValue):
        response = super(SyncUpdate_Usr, self).valuesSimilar(col, mValue, sValue)
        if not response:
            if "phone" in col.lower():
                if "preferred" in col.lower():
                    mPreferred = SanitationUtils.similarTruStrComparison(mValue)
                    sPreferred = SanitationUtils.similarTruStrComparison(sValue)
                    # print repr(mValue), " -> ", mPreferred
                    # print repr(sValue), " -> ", sPreferred
                    if mPreferred == sPreferred:
                        response = True
                else:
                    mPhone = SanitationUtils.similarPhoneComparison(mValue)
                    sPhone = SanitationUtils.similarPhoneComparison(sValue)
                    plen = min(len(mPhone), len(sPhone))
                    if plen > 7 and mPhone[-plen] == sPhone[-plen]:
                        response = True
            elif "role" in col.lower():
                mRole = SanitationUtils.similarComparison(mValue)
                sRole = SanitationUtils.similarComparison(sValue)
                if mRole == 'rn':
                    mRole = ''
                if sRole == 'rn':
                    sRole = ''
                if mRole == sRole:
                    response = True
            elif "address" in col.lower() and isinstance(mValue, ContactAddress):
                if( mValue != sValue ):
                    pass
                    # print "M: ", mValue.__str__(out_schema="flat"), "S: ", sValue.__str__(out_schema="flat")
                response = mValue.similar(sValue)
            elif "web site" in col.lower():
                if SanitationUtils.similarURLComparison(mValue) == SanitationUtils.similarURLComparison(sValue):
                    response = True

        if self.DEBUG_UPDATE: self.registerMessage(self.testToStr(col, mValue.__str__(), sValue.__str__(), response))
        return response

    #
    def getMColModTime(self, col):
        if self.colData.data.get(col,{}).get('tracked'):
            col_tracking_name = self.colData.modTimeCol(col)
        else:
            col_tracking_name = None
            for tracking_name, tracked_cols in self.colData.getACTTrackedCols().items():
                if col in tracked_cols:
                    col_tracking_name = tracking_name

        if col_tracking_name:
            # print 'sColModTime tracking_name', col_tracking_name
            if self.oldMObject.get(col_tracking_name):
                # print 'sColModTime tracking_name exists', \
                #         self.oldMObject.get(col_tracking_name), \
                #         ' -> ',\
                #         self.parseMTime(self.oldMObject.get(col_tracking_name))
                return self.parseMTime(self.oldMObject.get(col_tracking_name))
            elif col_tracking_name not in self.colData.getACTFutureTrackedCols().items():
                return None
        return self.mTime

    def getSColModTime(self, col):
        if self.colData.data.get(col,{}).get('tracked'):
            col_tracking_name = self.colData.modTimeCol(col)
        else:
            col_tracking_name = None
            for tracking_name, tracked_cols in self.colData.getWPTrackedCols().items():
                if col in tracked_cols:
                    col_tracking_name = tracking_name

        if col_tracking_name:
            # print 'mColModTime tracking_name', col_tracking_name
            if self.oldSObject.get(col_tracking_name):
                return self.parseSTime(self.oldSObject.get(col_tracking_name))
            else:
                return None

        return self.sTime

    def getInfoComponents(self, info_fmt="%s"):
        info_components = super(SyncUpdate_Usr, self).getInfoComponents(info_fmt)
        info_components += [
            (info_fmt % ("Last Sale", TimeUtils.wp_time_to_string(self.bTime))) if self.bTime else "No Last Sale",
            (info_fmt % ("%s Mod Time" % self.master_name, TimeUtils.wp_time_to_string(self.mTime))) if self.mMod else "%s Not Modded" % self.master_name,
            (info_fmt % ("%s Mod Time" % self.slave_name, TimeUtils.wp_time_to_string(self.sTime))) if self.sMod else "%s Not Modded" % self.slave_name
        ]
        for tracking_name, cols in self.colData.getACTTrackedCols().items():
            col = cols[0]
            mColModTime = self.getMColModTime(col)
            sColModTime = self.getSColModTime(col)
            if mColModTime or sColModTime:
                info_components.append(info_fmt % (tracking_name, '%s: %s; %s: %s' % (
                    self.master_name,
                    TimeUtils.wp_time_to_string(mColModTime),
                    self.slave_name,
                    TimeUtils.wp_time_to_string(sColModTime),
                )))
        return info_components

    def getSlaveUpdatesNativeRecursive(self, col, updates=None):
        if updates == None: updates = OrderedDict()
        if self.DEBUG_UPDATE:
            SanitationUtils.safePrint("getting updates for col %s, updates: %s" % (col, str(updates)))
        if col in self.colData.data.keys():
            data = self.colData.data[col]
            if data.get(self.s_meta_target):
                data_s = data.get(self.s_meta_target,{})
                if not data_s.get('final') and data_s.get('key'):
                    updates[data_s.get('key')] = self.newSObject.get(col)
            if data.get('aliases'):
                data_aliases = data.get('aliases')
                for alias in data_aliases:
                    if self.sColSemiStatic(alias):
                        continue
                    updates = self.getSlaveUpdatesNativeRecursive(alias, updates)
        return updates


    def getSlaveUpdatesRecursive(self, col, updates=None):
        if updates == None: updates = OrderedDict()
        if self.DEBUG_UPDATE: self.registerMessage( u"checking %s" % unicode(col) )
        if col in self.colData.data:
            if self.DEBUG_UPDATE: self.registerMessage( u"col exists" )
            data = self.colData.data[col]
            if data.get(self.s_meta_target):
                if self.DEBUG_UPDATE: self.registerMessage( u"wp exists" )
                data_s = data.get(self.s_meta_target,{})
                if not data_s.get('final') and data_s.get('key'):
                    newVal = self.newSObject.get(col)
                    updates[col] = newVal
                    if self.DEBUG_UPDATE: self.registerMessage( u"newval: %s" % repr(newVal) )
            if data.get('aliases'):
                if self.DEBUG_UPDATE: self.registerMessage( u"has aliases" )
                data_aliases = data['aliases']
                for alias in data_aliases:
                    if self.sColSemiStatic(alias):
                        if self.DEBUG_UPDATE: self.registerMessage( u"Alias semistatic" )
                        continue
                    else:
                        updates = self.getSlaveUpdatesRecursive(alias, updates)
        else:
            pass
            if self.DEBUG_UPDATE: self.registerMessage( u"col doesn't exist" )
        return updates


    def getMasterUpdatesRecursive(self, col, updates=None):
        if updates == None: updates = OrderedDict()
        if self.DEBUG_UPDATE: self.registerMessage( u"checking %s" % unicode(col) )
        if col in self.colData.data:
            if self.DEBUG_UPDATE: self.registerMessage( u"col exists" )
            data = self.colData.data[col]
            if data.get(self.m_meta_target):
                if self.DEBUG_UPDATE: self.registerMessage( u"wp exists" )
                newVal = self.newMObject.get(col)
                updates[col] = newVal
                if self.DEBUG_UPDATE: self.registerMessage( u"newval: %s" % repr(newVal) )
            if data.get('aliases'):
                if self.DEBUG_UPDATE: self.registerMessage( u"has aliases" )
                data_aliases = data['aliases']
                for alias in data_aliases:
                    if self.mColSemiStatic(alias):
                        if self.DEBUG_UPDATE: self.registerMessage( u"Alias semistatic" )
                        continue
                    else:
                        updates = self.getMasterUpdatesRecursive(alias, updates)
        else:
            pass
            if self.DEBUG_UPDATE: self.registerMessage( u"col doesn't exist" )
        return updates

class SyncUpdate_Usr_Api(SyncUpdate_Usr):
    s_meta_target = 'wp-api'

    def getSlaveUpdatesNativeRecursive(self, col, updates=None):
        if updates == None: updates = OrderedDict()
        if self.DEBUG_UPDATE: self.registerMessage( u"checking %s : %s" % (unicode(col), self.colData.data.get(col)) )
        if col in self.colData.data:
            if self.DEBUG_UPDATE: self.registerMessage( u"col exists" )
            data = self.colData.data[col]
            if data.get(self.s_meta_target):
                if self.DEBUG_UPDATE: self.registerMessage( u"wp-api exists" )
                data_s = data.get(self.s_meta_target,{})
                if not data_s.get('final') and data_s.get('key'):
                    newVal = self.newSObject.get(col)
                    newKey = col
                    if 'key' in data_s:
                        newKey = data_s.get('key')
                    if data_s.get('meta'):
                        if not 'meta' in updates :
                            updates['meta'] = OrderedDict()
                        updates['meta'][newKey] = newVal
                    else:
                        updates[newKey] = newVal
                    if self.DEBUG_UPDATE: self.registerMessage( u"newval: %s" % repr(newVal) )
                    if self.DEBUG_UPDATE: self.registerMessage( u"newkey: %s" % repr(newKey) )
            if data.get('aliases'):
                if self.DEBUG_UPDATE: self.registerMessage( u"has aliases" )
                data_aliases = data['aliases']
                for alias in data_aliases:
                    if self.sColSemiStatic(alias):
                        if self.DEBUG_UPDATE: self.registerMessage( u"Alias semistatic" )
                        continue
                    else:
                        updates = self.getSlaveUpdatesNativeRecursive(alias, updates)
        else:
            if self.DEBUG_UPDATE: self.registerMessage( u"col doesn't exist" )
        return updates



class SyncUpdate_Prod(SyncUpdate):
    colData = ColData_Prod
    s_meta_target = 'wp-api'

    def __init__(self, *args, **kwargs):
        super(SyncUpdate_Prod, self).__init__(*args, **kwargs)

    @property
    def MasterID(self):
        return self.getMValue('rowcount')

    @property
    def SlaveID(self):
        return self.getSValue('ID')

    def valuesSimilar(self, col, mValue, sValue):
        response = super(SyncUpdate_Prod, self).valuesSimilar(col, mValue, sValue)
        if col in self.colData.data:
            colData = self.colData.data[col]
            if colData.get('type'):
                if colData.get('type') == 'currency':
                    mPrice = SanitationUtils.similarCurrencyComparison(mValue)
                    sPrice = SanitationUtils.similarCurrencyComparison(sValue)
                    if mPrice == sPrice:
                        response = True
        elif not response:
            if col is 'descsum':
                mDesc = SanitationUtils.similarMarkupComparison(mValue)
                sDesc = SanitationUtils.similarMarkupComparison(sValue)
                if mDesc == sDesc:
                    response = True
            elif col is 'CVC':
                mCom = SanitationUtils.similarComparison(mValue) or '0'
                sCom = SanitationUtils.similarComparison(sValue) or '0'
                if mCom == sCom:
                    response = True

        if self.DEBUG_UPDATE: self.registerMessage(self.testToStr(col, mValue.__repr__(), sValue.__repr__(), response))
        return response

class SyncUpdate_Prod_Woo(SyncUpdate_Prod):
    colData = ColData_Woo

    def getSlaveUpdatesNativeRecursive(self, col, updates=None):
        if updates == None: updates = OrderedDict()
        # SanitationUtils.safePrint("getting updates for col %s, updates: %s" % (col, str(updates)))
        # if col == 'catlist':
        #     if hasattr(self.oldSObject, 'isVariation') and self.oldSObject.isVariation:
        #         # print "excluded item because isVariation"
        #         return updates
        #     else:
        #         update_catlist = self.newSObject.get('catlist')
        #         actual_catlist = self.oldSObject.categories.keys()
        #         print "comparing cats of %s" % repr(self.newSObject)
        #         static_catlist = list(set(update_catlist) | set(actual_catlist))
        #         # updates['categories'] = static_catlist
        #         # update_catids = []
        #         return updates
        #         # new_catlist = list(set(update_catlist) - set(actual_catlist))
        #         # print update_catlist
        #         # print actual_catlist

        if col in self.colData.data:
            data = self.colData.data[col]
            if self.s_meta_target in data:
                data_s = data[self.s_meta_target]
                if 'key' in data_s:
                    key = data_s.get('key')
                    val = self.newSObject.get(col)
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
                    val = self.newSObject.get(col)
                    updates[key] = val
            # if data.get('aliases'):
            #     data_aliases = data.get('aliases')
            #     for alias in data_aliases:
            #         if self.sColSemiStatic(alias):
            #             continue
            #         updates = self.getSlaveUpdatesNativeRecursive(alias, updates)
        return updates

    def getSlaveUpdatesRecursive(self, col, updates=None):
        if updates == None: updates = OrderedDict()
        if self.DEBUG_UPDATE: self.registerMessage( u"checking %s" % unicode(col) )
        if col in self.colData.data:
            if self.DEBUG_UPDATE: self.registerMessage( u"col exists" )
            data = self.colData.data[col]
            if data.get(self.s_meta_target):
                if self.DEBUG_UPDATE: self.registerMessage( u"wp exists" )
                data_s = data.get(self.s_meta_target,{})
                if not data_s.get('final') and data_s.get('key'):
                    newVal = self.newSObject.get(col)
                    updates[col] = newVal
                    if self.DEBUG_UPDATE: self.registerMessage( u"newval: %s" % repr(newVal) )
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
            if self.DEBUG_UPDATE: self.registerMessage( u"col doesn't exist" )
        return updates


    def getMasterUpdatesRecursive(self, col, updates=None):
        if updates == None: updates = OrderedDict()
        if self.DEBUG_UPDATE: self.registerMessage( u"checking %s" % unicode(col) )

        if col == 'catlist':
            if hasattr(self.oldSObject, 'isVariation') and self.oldSObject.isVariation:
                # print "excluded item because isVariation"
                return updates

        if col in self.colData.data:
            if self.DEBUG_UPDATE: self.registerMessage( u"col exists" )
            data = self.colData.data[col]
            if data.get(self.m_meta_target):
                if self.DEBUG_UPDATE: self.registerMessage( u"wp exists" )
                newVal = self.newMObject.get(col)
                updates[col] = newVal
                if self.DEBUG_UPDATE: self.registerMessage( u"newval: %s" % repr(newVal) )
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
            if self.DEBUG_UPDATE: self.registerMessage( u"col doesn't exist" )
        return updates

class SyncUpdate_Var_Woo(SyncUpdate_Prod_Woo):
    pass

class SyncUpdate_Cat_Woo(SyncUpdate):
    colData = ColData_Woo
    s_meta_target = 'wp-api'

    @property
    def MasterID(self):
        return self.getMValue('rowcount')

    @property
    def SlaveID(self):
        return self.getSValue('ID')

    def valuesSimilar(self, col, mValue, sValue):
        response = super(SyncUpdate_Cat_Woo, self).valuesSimilar(col, mValue, sValue)
        if not response:
            if col is 'descsum':
                mDesc = SanitationUtils.similarMarkupComparison(mValue)
                sDesc = SanitationUtils.similarMarkupComparison(sValue)
                if mDesc == sDesc:
                    response = True

        if self.DEBUG_UPDATE: self.registerMessage(self.testToStr(col, mValue.__repr__(), sValue.__repr__(), response))
        return response

    def getSlaveUpdatesNativeRecursive(self, col, updates=None):
        if updates == None: updates = OrderedDict()
        # SanitationUtils.safePrint("getting updates for col %s, updates: %s" % (col, str(updates)))

        if col in self.colData.data:
            data = self.colData.data[col]
            if self.s_meta_target in data:
                data_s = data[self.s_meta_target]
                if 'key' in data_s:
                    key = data_s.get('key')
                    val = self.newSObject.get(col)
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
                    val = self.newSObject.get(col)
                    updates[key] = val
            # if data.get('aliases'):
            #     data_aliases = data.get('aliases')
            #     for alias in data_aliases:
            #         if self.sColSemiStatic(alias):
            #             continue
            #         updates = self.getSlaveUpdatesNativeRecursive(alias, updates)
        return updates


    def getSlaveUpdatesRecursive(self, col, updates=None):
        if updates == None: updates = OrderedDict()
        if self.DEBUG_UPDATE: self.registerMessage( u"checking %s" % unicode(col) )
        if col in self.colData.data:
            if self.DEBUG_UPDATE: self.registerMessage( u"col exists" )
            data = self.colData.data[col]
            if data.get(self.s_meta_target):
                if self.DEBUG_UPDATE: self.registerMessage( u"wp exists" )
                data_s = data.get(self.s_meta_target,{})
                if not data_s.get('final') and data_s.get('key'):
                    newVal = self.newSObject.get(col)
                    updates[col] = newVal
                    if self.DEBUG_UPDATE: self.registerMessage( u"newval: %s" % repr(newVal) )
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
            if self.DEBUG_UPDATE: self.registerMessage( u"col doesn't exist" )
        return updates


    def getMasterUpdatesRecursive(self, col, updates=None):
        if updates == None: updates = OrderedDict()
        if self.DEBUG_UPDATE: self.registerMessage( u"checking %s" % unicode(col) )

        if col == 'catlist':
            if hasattr(self.oldSObject, 'isVariation') and self.oldSObject.isVariation:
                # print "excluded item because isVariation"
                return updates

        if col in self.colData.data:
            if self.DEBUG_UPDATE: self.registerMessage( u"col exists" )
            data = self.colData.data[col]
            if data.get(self.m_meta_target):
                if self.DEBUG_UPDATE: self.registerMessage( u"wp exists" )
                newVal = self.newMObject.get(col)
                updates[col] = newVal
                if self.DEBUG_UPDATE: self.registerMessage( u"newval: %s" % repr(newVal) )
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
            if self.DEBUG_UPDATE: self.registerMessage( u"col doesn't exist" )
        return updates
