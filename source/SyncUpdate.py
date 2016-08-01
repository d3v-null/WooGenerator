import yaml
from collections import OrderedDict
from utils import SanitationUtils, TimeUtils, Registrar
from contact_objects import ContactAddress
from coldata import ColData_User
from tabulate import tabulate
from copy import deepcopy
from matching import Match
from csvparse_flat import ImportUser
from csvparse_abstract import ImportObject

DEBUG_UPDATE = False

class SyncUpdate(Registrar):

    @classmethod
    def setGlobals(_class, master_name, slave_name, merge_mode, default_lastSync):
        _class.master_name = master_name
        _class.slave_name = slave_name
        _class.merge_mode = merge_mode
        _class.default_lastSync = default_lastSync

    def __init__(self, oldMObject, oldSObject, lastSync=None):
        super(SyncUpdate, self).__init__()
        for oldObject in oldMObject, oldSObject:
            assert isinstance(oldObject, ImportObject)
        if not lastSync:
            lastSync = self.default_lastSync
        # print "Creating SyncUpdate: ", oldMObject.__repr__(), oldSObject.__repr__()
        self.oldMObject = oldMObject
        self.oldSObject = oldSObject
        self.tTime = TimeUtils.wpStrptime(lastSync)
        self.mTime = self.oldMObject.act_modtime
        self.sTime = self.oldSObject.wp_modtime
        self.bTime = self.oldMObject.last_sale

        self.winner = self.getWinnerName(self.mTime, self.sTime)

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
        # self.problematic = False

        #extra heuristics for merge mode:
        if self.merge_mode == 'merge' and not self.sMod:
            might_be_sEdited = False
            if not oldSObject.addressesActLike():
                might_be_sEdited = True
            elif oldSObject.get('Home Country') == 'AU':
                might_be_sEdited = True
            elif oldSObject.usernameActLike():
                might_be_sEdited = True
            if might_be_sEdited:
                # print repr(oldSObject), "might be edited"
                self.sTime = self.tTime
                if self.mMod:
                    self.static = False
                    # self.importantStatic = False
#
    @property
    def sUpdated(self): return self.newSObject
    @property
    def mUpdated(self): return self.newMObject
    @property
    def lTime(self): return max(self.mTime, self.sTime)
    @property
    def mMod(self): return self.mTime >= self.tTime
    @property
    def sMod(self): return self.sTime >= self.tTime



    @property
    def WPID(self):
        return self.getSValue("Wordpress ID")

    @property
    def MYOBID(self):
        return self.getMValue('MYOB Card ID')

    # @property
    # def winner(self): return self.winner

    # def colBlank(self, col):
    #     mValue = (mObject.get(col) or "")
    #     sValue = (sObject.get(col) or "")
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
        return TimeUtils.actServerToLocalTime(TimeUtils.actStrptime(rawMTime))

    def parseSTime(self, rawSTime):
        return TimeUtils.wpServerToLocalTime(TimeUtils.wpStrptime(rawSTime))

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
        if not (mValue or sValue):
            return True
        elif not (mValue and sValue):
            return False
        #check if they are similar
        if "phone" in col.lower():
            if "preferred" in col.lower():
                mPreferred = SanitationUtils.similarTruStrComparison(mValue)
                sPreferred = SanitationUtils.similarTruStrComparison(sValue)
                # print repr(mValue), " -> ", mPreferred
                # print repr(sValue), " -> ", sPreferred
                if mPreferred == sPreferred:
                    return True
            else:
                mPhone = SanitationUtils.similarPhoneComparison(mValue)
                sPhone = SanitationUtils.similarPhoneComparison(sValue)
                plen = min(len(mPhone), len(sPhone))
                if plen > 7 and mPhone[-plen] == sPhone[-plen]:
                    return True
        elif "role" in col.lower():
            mRole = SanitationUtils.similarComparison(mValue)
            sRole = SanitationUtils.similarComparison(sValue)
            if mRole == 'rn':
                mRole = ''
            if sRole == 'rn':
                sRole = ''
            if mRole == sRole:
                return True
        elif "address" in col.lower() and isinstance(mValue, ContactAddress):
            if( mValue != sValue ):
                pass
                # print "M: ", mValue.__str__(out_schema="flat"), "S: ", sValue.__str__(out_schema="flat")
            return mValue.similar(sValue)
        elif "web site" in col.lower():
            if SanitationUtils.similarURLComparison(mValue) == SanitationUtils.similarURLComparison(sValue):
                return True
        else:
            if SanitationUtils.similarComparison(mValue) == SanitationUtils.similarComparison(sValue):
                return True
        return False

    def colIdentical(self, col):
        mValue = self.getMValue(col)
        sValue = self.getSValue(col)
        # self.registerMessage(u"testing col %s: M %s | S %s" % (unicode(col), unicode(mValue), unicode(sValue)))
        return mValue == sValue

    def colSimilar(self, col):
        mValue = self.getMValue(col)
        sValue = self.getSValue(col)
        # self.registerMessage(u"testing col %s: M %s | S %s" % (unicode(col), unicode(mValue), unicode(sValue)))
        return self.valuesSimilar(col, mValue, sValue)

    def newColIdentical(self, col):
        mValue = self.getNewMValue(col)
        sValue = self.getNewSValue(col)
        # self.registerMessage(u"testing col %s: M %s | S %s" % (unicode(col), unicode(mValue), unicode(sValue)))
        return mValue == sValue

    def addProblematicUpdate(self, **updateParams):
        for key in ['col', 'subject', 'reason']:
            assert updateParams[key], 'missing mandatory prob param %s' % key
        col = updateParams['col']
        if col not in self.syncProblematics.keys():
            self.syncProblematics[col] = []
        self.syncProblematics[col].append(updateParams)
        self.registerWarning("SYNC PROB: %s" % SanitationUtils.coerceUnicode(updateParams))

    def addSyncWarning(self, **updateParams):
        for key in ['col', 'subject', 'reason']:
            assert updateParams[key], 'missing mandatory warning param %s' % key
        col = updateParams['col']
        if col not in self.syncWarnings.keys():
            self.syncWarnings[col] = []
        self.syncWarnings[col].append(updateParams)
        self.registerWarning("SYNC WARNING: %s" % SanitationUtils.coerceUnicode(updateParams))

    def addSyncPass(self, **updateParams):
        for key in ['col']:
            assert updateParams[key], 'missing mandatory pass param %s' % key
        col = updateParams['col']
        if col not in self.syncPasses.keys():
            self.syncPasses[col] = []
        self.syncPasses[col].append(updateParams)
        if DEBUG_UPDATE: self.registerMessage("SYNC PASS: %s" % SanitationUtils.coerceUnicode(updateParams))


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
                                warning_fmtd[key] = TimeUtils.wpTimeToString(rawTime)
                        except Exception, e:
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
            assert updateParams[key], 'missing mandatory update param, %s' % key

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
            newLoserObject[ColData_User.deltaCol(col)] = updateParams['oldLoserValue']

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
        if ColData_User.data.get(col,{}).get('tracked'):
            col_tracking_name = ColData_User.modTimeCol(col)
        else:
            col_tracking_name = None
            for tracking_name, tracked_cols in ColData_User.getACTTrackedCols().items():
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
            elif col_tracking_name not in ColData_User.getACTFutureTrackedCols().items():
                return None
        return self.mTime

    def getSColModTime(self, col):
        if ColData_User.data.get(col,{}).get('tracked'):
            col_tracking_name = ColData_User.modTimeCol(col)
        else:
            col_tracking_name = None
            for tracking_name, tracked_cols in ColData_User.getWPTrackedCols().items():
                if col in tracked_cols:
                    col_tracking_name = tracking_name

        if col_tracking_name:
            # print 'mColModTime tracking_name', col_tracking_name
            if self.oldSObject.get(col_tracking_name):
                return self.parseSTime(self.oldSObject.get(col_tracking_name))
            else:
                return None

        return self.sTime

    def updateCol(self, **updateParams):
        for key in ['col', 'data']:
            assert updateParams[key], 'missing mandatory update param %s' % key
        col = updateParams['col']
        try:
            data = updateParams['data']
            sync_mode = data['sync']
        except Exception:
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

    def tabulate(self, tablefmt=None):
        subtitle_fmt = "%s"
        info_delimeter = "\n"
        info_fmt = "%s: %s"
        if(tablefmt == "html"):
            subtitle_fmt = "<h3>%s</h3>"
            info_delimeter = "<br/>"
            info_fmt = "<strong>%s:</strong> %s"
        oldMatch = Match([self.oldMObject], [self.oldSObject])
        out_str =  ""
        out_str += info_delimeter.join([
            subtitle_fmt % "OLD",
            oldMatch.tabulate(tablefmt)
        ])
        out_str += info_delimeter

        info_components = [
            subtitle_fmt % "INFO",
            (info_fmt % ("Last Sale", TimeUtils.wpTimeToString(self.bTime))) if self.bTime else "No Last Sale",
            (info_fmt % ("%s Mod Time" % self.master_name, TimeUtils.wpTimeToString(self.mTime))) if self.mMod else "%s Not Modded" % self.master_name,
            (info_fmt % ("%s Mod Time" % self.slave_name, TimeUtils.wpTimeToString(self.sTime))) if self.sMod else "%s Not Modded" % self.slave_name,
            (info_fmt % ("static", "yes" if self.static else "no")),
            (info_fmt % ("importantStatic", "yes" if self.importantStatic else "no"))
        ]
        for tracking_name, cols in ColData_User.getACTTrackedCols().items():
            col = cols[0]
            mColModTime = self.getMColModTime(col)
            sColModTime = self.getSColModTime(col)
            if mColModTime or sColModTime:
                info_components.append(info_fmt % (tracking_name, '%s: %s; %s: %s' % (
                    self.master_name,
                    TimeUtils.wpTimeToString(mColModTime),
                    self.slave_name,
                    TimeUtils.wpTimeToString(sColModTime),
                )))

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
            newMatch.tabulate(tablefmt)
        ])

        return out_str

    def getSlaveUpdatesWPColRecursive(self, col, updates=None):
        if updates == None: updates = {}
        # SanitationUtils.safePrint("getting updates for col %s, updates: %s" % (col, str(updates)))
        if col in ColData_User.data.keys():
            data = ColData_User.data[col]
            if data.get('wp'):
                data_wp = data.get('wp',{})
                if not data_wp.get('final') and data_wp.get('key'):
                    updates[data_wp.get('key')] = self.newSObject.get(col)
            if data.get('aliases'):
                data_aliases = data.get('aliases')
                for alias in data_aliases:
                    if self.newColIdentical(alias):
                        continue
                    updates = self.getSlaveUpdatesWPColRecursive(alias, updates)
        return updates

    def getSlaveUpdatesWPCol(self):
        updates = {}
        for col, warnings in self.syncWarnings.items():
            for warning in warnings:
                subject = warning['subject']
                if subject == self.opposite_src(self.slave_name):
                    updates = self.getSlaveUpdatesWPColRecursive(col, updates)
        return updates

    def getSlaveUpdatesRecursive(self, col, updates=None):
        if updates == None: updates = {}
        # self.registerMessage( u"getSlaveUpdatesRecursive checking %s" % unicode(col) )
        if col in ColData_User.data:
            # self.registerMessage( u"getSlaveUpdatesRecursive col exists" )
            data = ColData_User.data[col]
            if data.get('wp'):
                # self.registerMessage( u"getSlaveUpdatesRecursive wp exists" )
                data_wp = data.get('wp',{})
                if not data_wp.get('final') and data_wp.get('key'):
                    newVal = self.newSObject.get(col)
                    updates[col] = newVal
                    # self.registerMessage( u"getSlaveUpdatesRecursive newval: %s" % unicode(newVal) )
            if data.get('aliases'):
                # self.registerMessage( u"getSlaveUpdatesRecursive has aliases" )
                data_aliases = data['aliases']
                for alias in data_aliases:
                    if self.newColIdentical(alias):
                        # self.registerMessage( u"Alias Identical" )
                        continue
                    else:
                        updates = self.getSlaveUpdatesRecursive(alias, updates)
        else:
            pass
            # self.registerMessage( u"getSlaveUpdatesRecursive col doesn't exist" )
        return updates

    def getSlaveUpdates(self):
        updates = {}
        for col, warnings in self.syncWarnings.items():
            for warning in warnings:
                subject = warning['subject']
                if subject == self.opposite_src(self.slave_name):
                    updates = self.getSlaveUpdatesRecursive(col, updates)
        # self.registerMessage( u"getSlaveUpdates returned %s" % unicode(updates) )
        return updates

    def getMasterUpdatesRecursive(self, col, updates=None):
        if updates == None: updates = {}
        if col in ColData_User.data:
            data = ColData_User.data[col]
            if data.get('act'):
                updates[col] = self.newMObject.get(col)
            if data.get('aliases'):
                data_aliases = data['aliases']
                for alias in data_aliases:
                    if self.newColIdentical(alias):
                        continue
                    else:
                        updates = self.getMasterUpdatesRecursive(alias, updates)
        return updates

    def getMasterUpdates(self):
        updates = {}
        for col, warnings in self.syncWarnings.items():
            for warning in warnings:
                subject = warning['subject']
                if subject == self.opposite_src(self.master_name):
                    updates = self.getMasterUpdatesRecursive(col, updates)
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
                user_pkey = self.WPID
                assert user_pkey, "primary key must be valid, %s" % repr(user_pkey)
            except Exception as e:
                print_elements.append("NO %s CHANGES: must have a primary key to update user data: " % self.slave_name +repr(e))
                user_pkey = None
                return info_delimeter.join(print_elements)

            updates = self.getSlaveUpdatesWPCol()
            additional_updates = OrderedDict()
            if user_pkey:
                additional_updates['ID'] = user_pkey

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
                # return (user_pkey, all_updates_json_base64)
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
                user_pkey = self.WPID
                assert user_pkey, "primary key must be valid, %s" % repr(user_pkey)
            except Exception as e:
                print_elements.append("NO %s CHANGES: must have a primary key to update user data: " % self.master_name+repr(e))
                user_pkey = None
                return info_delimeter.join(print_elements)

            updates = self.getMasterUpdates()
            additional_updates = OrderedDict()
            if user_pkey:
                additional_updates['ID'] = user_pkey

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
                # return (user_pkey, all_updates_json_base64)
            else:
                print_elements.append("NO %s CHANGES: no user_updates or meta_updates" %self.master_name)

            return info_delimeter.join(print_elements)
        return ""

    def updateMaster(self, client):
        updates = self.getMasterUpdates()
        if not updates:
            return

        user_pkey = self.MYOBID
        return client.uploadChanges(user_pkey, updates)

        #todo: Determine if file imported correctly and delete file

    def updateSlave(self, client):
            # SanitationUtils.safePrint(  self.displaySlaveChanges() )
        updates = self.getSlaveUpdatesWPCol()
        if not updates:
            return

        user_pkey = self.WPID

        return client.uploadChanges(user_pkey, updates)

    def __cmp__(self, other):
        return -cmp(self.bTime, other.bTime)
        # return -cmp((self.importantUpdates, self.updates, - self.lTime), (other.importantUpdates, other.updates, - other.lTime))

# def testSyncUpdate1():
#
#
#     usr1 = ImportUser(
#         {
#             'MYOB Card ID': 'C00002',
#             'Wordpress ID': 7,
#             'Wordpress Username': 'derewnt',
#             'First Name': 'Derwent',
#             'Surname': 'Smith',
#             'Name Modified': '2015-11-10 12:55:00',
#             'Edited in Act': '11/11/2015 6:45:00 AM',
#         },
#         1,
#         [],
#     )
#
#     usr2 = ImportUser(
#         {
#             'MYOB Card ID': 'C00002',
#             'Wordpress ID': 7,
#             'Wordpress Username': 'derewnt',
#             'First Name': 'Abe',
#             'Surname': 'Jackson',
#             'Name Modified': '2015-11-10 12:45:03',
#             'Edited in Wordpress': '2015-11-11 6:55:00',
#         },
#         2,
#         [],
#     )
#
#     syncUpdate = SyncUpdate(usr1, usr2)
#
#     syncCols = ColData_User.getSyncCols()
#
#     syncUpdate.update(syncCols)
#
#     SanitationUtils.safePrint( syncUpdate.tabulate(tablefmt = 'simple'))
#
# def testSyncUpdate2():
#
#     usr1 = ImportUser(
#         {
#             'MYOB Card ID': 'C00002',
#             'Wordpress ID': 7,
#             'Wordpress Username': 'derewnt',
#             'First Name': 'Derwent',
#             'Surname': 'Smith',
#             'Edited Name': '10/11/2015 12:45:00 PM',
#             'Edited in Act': '11/11/2015 6:55:00 AM',
#         },
#         1,
#         [],
#     )
#
#     usr2 = ImportUser(
#         {
#             'MYOB Card ID': 'C00002',
#             'Wordpress ID': 7,
#             'Wordpress Username': 'derewnt',
#             'First Name': 'Abe',
#             'Surname': 'Jackson',
#             'Edited Name': '2015-11-10 12:55:03',
#             'Edited in Wordpress': '2015-11-11 6:45:00',
#         },
#         2,
#         [],
#     )
#
#     syncUpdate = SyncUpdate(usr1, usr2)
#
#     syncCols = ColData_User.getSyncCols()
#
#     syncUpdate.update(syncCols)
#
#     # SanitationUtils.safePrint( syncUpdate.tabulate(tablefmt = 'simple'))
#
# if __name__ == '__main__':
#     yamlPath = "source/merger_config.yaml"
#
#     with open(yamlPath) as stream:
#         config = yaml.load(stream)
#         merge_mode = config.get('merge_mode', 'sync')
#         MASTER_NAME = config.get('master_name', 'MASTER')
#         SLAVE_NAME = config.get('slave_name', 'SLAVE')
#         DEFAULT_LAST_SYNC = config.get('default_last_sync')
#
#     SyncUpdate.setGlobals( MASTER_NAME, SLAVE_NAME, merge_mode, DEFAULT_LAST_SYNC)
#     testSyncUpdate1()
#     testSyncUpdate2()
