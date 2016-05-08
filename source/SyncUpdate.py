from collections import OrderedDict
from utils import SanitationUtils, TimeUtils, listUtils, Registrar
from contact_objects import ContactAddress
from coldata import ColData_User
from tabulate import tabulate
from copy import deepcopy
from matching import Match

class SyncUpdate(Registrar):

    @classmethod
    def setGlobals(_class, master_name, slave_name, merge_mode, default_lastSync):
        _class.master_name = master_name
        _class.slave_name = slave_name
        _class.merge_mode = merge_mode
        _class.default_lastSync = default_lastSync

    def __init__(self, oldMObject, oldSObject, lastSync=None):
        if not lastSync:
            lastSync = self.default_lastSync
        # print "Creating SyncUpdate: ", oldMObject.__repr__(), oldSObject.__repr__()
        self.oldMObject = oldMObject
        self.oldSObject = oldSObject
        self.tTime = TimeUtils.wpStrptime( lastSync )
        self.mTime = self.oldMObject.act_modtime
        self.sTime = self.oldSObject.wp_modtime
        self.bTime = self.oldMObject.last_sale

        self.winner = self.slave_name if(self.sTime >= self.mTime) else self.master_name
        
        self.newSObject = False
        self.newMObject = False
        self.static = True
        self.importantStatic = True
        self.syncWarnings = OrderedDict()
        self.syncPasses = OrderedDict()
        self.updates = 0
        self.importantUpdates = 0
        # self.problematic = False

        #extra heuristics for merge mode:
        if(self.merge_mode == 'merge' and not self.sMod):
            might_be_sEdited = False
            if not oldSObject.addressesActLike():
                might_be_sEdited = True
            elif( oldSObject.get('Home Country') == 'AU' ):
                might_be_sEdited = True
            elif oldSObject.usernameActLike():
                might_be_sEdited = True
            if(might_be_sEdited):
                # print repr(oldSObject), "might be edited"
                self.sTime = self.tTime
                if(self.mMod):
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
    def mMod(self): return (self.mTime >= self.tTime)
    @property
    def sMod(self): return (self.sTime >= self.tTime)



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

    def getWinnerKey(self, key):
        # if self.syncWarnings and key in self.syncWarnings.keys():
        #     # print "key in warnings"
        #     keySyncWarnings = self.syncWarnings[key]
        #     assert len(keySyncWarnings) < 2
        #     subject, reason, oldVal, newVal, data = keySyncWarnings[0]
        #     return newVal
        # if self.syncPasses and key in self.syncPasses.keys():
        #     # print "key in passes"
        #     keySyncPasses = self.syncPasses[key]
        #     assert len(keySyncPasses) < 2
        #     reason, val, data = keySyncPasses[0]
        #     return val
        # else:
        if self.winner == self.slave_name and self.newSObject:
            return self.newSObject.get(key)
        if self.winner == self.master_name and self.newMObject:
            return self.newMObject.get(key)
        self.registerError( "could not find any value for key {}".format(key) )
        return None

    def sanitizeValue(self, col, value):
        # print "sanitizing", col, repr(value)
        if('phone' in col.lower()):
            if('preferred' in col.lower()):
                if(value and len(SanitationUtils.stripNonNumbers(value)) > 1):
                    # print "value nullified", value
                    return ""
        return value

    def getMValue(self, col):
        return self.sanitizeValue(col, self.oldMObject.get(col) or "")

    def getSValue(self, col):
        return self.sanitizeValue(col, self.oldSObject.get(col) or "")

    def colIdentical(self, col):
        mValue = self.getMValue(col)
        # print "-> mValue", mValue
        sValue = self.getSValue(col)
        # print "-> sValue", sValue
        return (mValue == sValue)

    def colSimilar(self, col):
        # print "-> comparing ", col
        mValue = self.getMValue(col)
        sValue = self.getSValue(col)
        if not (mValue or sValue):
            return True
        elif not ( mValue and sValue ):
            return False
        #check if they are similar
        if( "phone" in col.lower() ):
            if( "preferred" in col.lower() ):
                mPreferred = SanitationUtils.similarTruStrComparison(mValue)
                sPreferred = SanitationUtils.similarTruStrComparison(sValue)
                # print repr(mValue), " -> ", mPreferred
                # print repr(sValue), " -> ", sPreferred
                if(mPreferred == sPreferred):
                    return True
            else:
                mPhone = SanitationUtils.similarPhoneComparison(mValue)
                sPhone = SanitationUtils.similarPhoneComparison(sValue)
                plen = min(len(mPhone), len(sPhone))
                if(plen > 7 and mPhone[-plen] == sPhone[-plen]):
                    return True
        elif( "role" in col.lower() ):
            mRole = SanitationUtils.similarComparison(mValue)
            sRole = SanitationUtils.similarComparison(sValue)
            if (mRole == 'rn'): 
                mRole = ''
            if (sRole == 'rn'): 
                sRole = ''
            if( mRole == sRole ): 
                return True
        elif( "address" in col.lower() and isinstance(mValue, ContactAddress)):
            if( mValue != sValue ):
                pass
                # print "M: ", mValue.__str__(out_schema="flat"), "S: ", sValue.__str__(out_schema="flat")
            return mValue.similar(sValue)
        else:
            if( SanitationUtils.similarComparison(mValue) == SanitationUtils.similarComparison(sValue) ):
                return True

        return False

    def addSyncWarning(self, col, subject, reason, oldVal =  "", newVal = "", data = {}):
        if( col not in self.syncWarnings.keys()):
            self.syncWarnings[col] = []
        self.syncWarnings[col].append((subject, reason, oldVal, newVal, data))
        # print "SYNC WARNING: ", self.syncWarnings[col][-1]

    def addSyncPass(self, col, reason, val="", data={}):
        if( col not in self.syncPasses.keys()):
            self.syncPasses[col] = []
        self.syncPasses[col].append((reason, val, data))
        # print "SYNC PASS: ", self.syncPasses[col][-1]


    def displaySyncWarnings(self, tablefmt=None):
        if self.syncWarnings:
            delimeter = "<br/>" if tablefmt=="html" else "\n"
            subject_fmt = "<h4>%s</h4>" if tablefmt=="html" else "%s"
            header = ["Column", "Reason", "Old", "New"]
            subjects = {}
            for col, warnings in self.syncWarnings.items():
                for subject, reason, oldVal, newVal, data in warnings:    
                    if subject not in subjects.keys():
                        subjects[subject] = []
                    subjects[subject] += [map( 
                        lambda x: SanitationUtils.coerceUnicode(x)[:64], 
                        [col, reason, oldVal, newVal] 
                    )]
            tables = []
            for subject, subjList in subjects.items():
                subjList = [map(SanitationUtils.sanitizeForTable, subj ) for subj in subjList ]
                tables += [delimeter.join([(subject_fmt % self.opposite_src(subject)), tabulate(subjList, headers=header, tablefmt=tablefmt)])]
            return delimeter.join(tables)
        else:
            return ""

    # def getOldLoserObject(self, winner=None):
    #     if not winner: winner = self.winner
    #     if(winner == self.master_name):
    #         oldLoserObject = self.oldSObject

    def opposite_src(self, subject):
        if subject == self.master_name:
            return self.slave_name
        else:
            return self.master_name

    def loserUpdate(self, winner, col, reason = "", data={}):
        # SanitationUtils.safePrint("loserUpdate ", winner, col, reason)
        if(winner == self.master_name):
            # oldLoserObject = self.oldSObject
            oldLoserValue = self.getSValue(col)
            # oldWinnerObject = self.oldMObject
            oldWinnerValue = self.getMValue(col)
            if(not self.newSObject): self.newSObject = deepcopy(self.oldSObject)
            newLoserObject = self.newSObject
        elif(winner == self.slave_name):
            # oldLoserObject = self.oldMObject
            oldLoserValue = self.getMValue(col)
            # oldWinnerObject = self.oldSObject
            oldWinnerValue = self.getSValue(col)
            if(not self.newMObject): self.newMObject = deepcopy(self.oldMObject)
            newLoserObject = self.newMObject
        # if data.get('warn'): 
        self.addSyncWarning(col, winner, reason, oldLoserValue, oldWinnerValue, data)
        # SanitationUtils.safePrint("loser %s was %s" % (col, repr(newLoserObject[col])))
        # SanitationUtils.safePrint("updating to ", oldWinnerValue)
        newLoserObject[col] = oldWinnerValue
        # SanitationUtils.safePrint( "loser %s is now %s" % (col, repr(newLoserObject[col])))
        # SanitationUtils.safePrint( "loser Name is now ", newLoserObject['Name'])
        self.updates += 1
        if data.get('static'): 
            self.static = False
        if(reason in ['updating', 'deleting']):
            self.importantUpdates += 1
            if data.get('static'): self.importantStatic = False

    def tieUpdate(self, col, reason, data={}):
        # print "tieUpdate ", col, reason
        if self.oldSObject:
            self.addSyncPass(col, reason, self.oldSObject.get(col))
        elif self.oldMObject:
            self.addSyncPass(col, reason, self.oldMObject.get(col))
        else:
            self.addSyncPass(col, reason)        
        
    def updateCol(self, col, data={}):
        # print "sync ", col

        try:
            sync_mode = data['sync']
        except:
            return
        # sync_warn = data.get('warn')
        # syncstatic = data.get('static')
        
        # if(self.colBlank(col)): continue
        if(self.colIdentical(col)): 
            # print "-> cols identical"
            self.tieUpdate(col, "identical", data)
            return
        else:
            # print "-> cols not identical"
            pass

        mValue = self.getMValue(col)
        sValue = self.getSValue(col)

        winner = self.winner
        reason = 'updating' if mValue and sValue else 'inserting'
            
        if( 'override' in str(sync_mode).lower() ):
            # reason = 'overriding'
            if( 'master' in str(sync_mode).lower() ):
                winner = self.master_name
            elif( 'slave' in str(sync_mode).lower() ):
                winner = self.slave_name
        else:
            if(self.colSimilar(col)): 
                self.tieUpdate(col, "identical", data)
                return 

            if not (mValue and sValue):
                if(self.merge_mode == 'merge'):
                    if(winner == self.slave_name and not sValue):
                        winner = self.master_name
                        reason = 'merging'
                    elif(winner == self.master_name and not mValue):
                        winner = self.slave_name
                        reason = 'merging'
                else:
                    if(winner == self.slave_name and not sValue):
                        reason = 'deleting'
                    elif(winner == self.master_name and not mValue):
                        reason = 'deleting'

        self.loserUpdate(winner, col, reason, data)

    def update(self, syncCols):
        for col, data in syncCols.items():
            self.updateCol(col, data)
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
        out_str += info_delimeter.join(filter(None,[
            subtitle_fmt % "INFO",
            (info_fmt % ("Last Sale", TimeUtils.wpTimeToString(self.bTime))) if self.bTime else "No Last Sale",
            (info_fmt % ("%s Mod Time" % self.master_name, TimeUtils.wpTimeToString(self.mTime))) if self.mMod else "%s Not Modded" % self.master_name,
            (info_fmt % ("%s Mod Time" % self.slave_name, TimeUtils.wpTimeToString(self.sTime))) if self.sMod else "%s Not Modded" % self.slave_name,
            (info_fmt % ("static", "yes" if self.static else "no")),
            (info_fmt % ("importantStatic", "yes" if self.importantStatic else "no"))
        ]))
        out_str += info_delimeter
        out_str += info_delimeter.join(filter(None,[
            subtitle_fmt % 'CHANGES (%d!%d)' % (self.updates, self.importantUpdates),
            self.displaySyncWarnings(tablefmt),
            subtitle_fmt % '%s CHANGES' % self.master_name,
            self.displayMasterChanges(tablefmt),        
            subtitle_fmt % '%s CHANGES' % self.slave_name,
            self.displaySlaveChanges(tablefmt),        
        ]))
        newMatch = Match([self.newMObject], [self.newSObject])
        out_str += info_delimeter
        out_str += info_delimeter.join([
            subtitle_fmt % 'NEW',
            newMatch.tabulate(tablefmt)
        ])

        return out_str

    def getSlaveUpdatesRecursive(self, col, updates=None):
        if updates == None: updates = {}
        # SanitationUtils.safePrint("getting updates for col %s, updates: %s" % (col, str(updates)))
        if col in ColData_User.data.keys():
            data = ColData_User.data[col]
            if data.get('wp'):
                data_wp = data.get('wp',{})
                if data_wp.get('meta'):
                    updates[data_wp.get('key')] = self.newSObject.get(col)
                elif not data_wp.get('final'):
                    updates[data_wp.get('key')] = self.newSObject.get(col)
            if data.get('aliases'):
                data_aliases = data.get('aliases')
                for alias in data_aliases:
                    if \
                      SanitationUtils.coerceUnicode(self.newSObject.get(alias)) == \
                      SanitationUtils.coerceUnicode(self.oldSObject.get(alias)):
                        # SanitationUtils.safePrint( "aliases [%s->%s] are the same: %s | %s" % ( col, alias, self.newSObject.get(alias), self.oldSObject.get(alias)) )
                        continue
                    # else:
                        # SanitationUtils.safePrint( "aliases [%s->%s] are not the same: %s | %s" % ( col, alias, self.newSObject.get(alias), self.oldSObject.get(alias)) )
                    #if the new value is not the same as the old value
                    # SanitationUtils.safePrint("pre:", updates)
                    updates = self.getSlaveUpdatesRecursive(alias, updates)
                    # SanitationUtils.safePrint("post:", updates)
        # SanitationUtils.safePrint("returning updates for col %s : %s" % (col, str(updates)))
        return updates

    def getSlaveUpdates(self):
        updates = {}
        for col, warnings in self.syncWarnings.items():
            for subject, reason, oldVal, newVal, data in warnings:  
                if subject == self.opposite_src(self.slave_name):
                    updates = self.getSlaveUpdatesRecursive(col, updates)
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
                    if \
                      SanitationUtils.coerceUnicode(self.newMObject.get(alias)) == \
                      SanitationUtils.coerceUnicode(self.oldMObject.get(alias)):
                        # SanitationUtils.safePrint( "aliases [%s->%s] are the same: %s | %s" % (col, alias, self.newMObject.get(alias), self.oldMObject.get(alias)) )
                        continue
                    # else:
                        # SanitationUtils.safePrint( "aliases [%s->%s] are not the same: %s | %s" % (col, alias, self.newMObject.get(alias), self.oldMObject.get(alias)) )

                    #if the new value is not the same as the old value
                    updates = self.getMasterUpdatesRecursive(alias, updates)
                    # SanitationUtils.safePrint(updates)
        return updates

    def getMasterUpdates(self):
        updates = {}
        for col, warnings in self.syncWarnings.items():
            for subject, reason, oldVal, newVal, data in warnings:
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

            updates = self.getSlaveUpdates()
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
        updates = self.getSlaveUpdates()
        if not updates:
            return

        user_pkey = self.WPID

        return client.uploadChanges(user_pkey, updates)

    def __cmp__(self, other):
        return -cmp(self.bTime, other.bTime)
        # return -cmp((self.importantUpdates, self.updates, - self.lTime), (other.importantUpdates, other.updates, - other.lTime))
