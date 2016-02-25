from csvparse_abstract import ImportObject
from csvparse_flat import UsrObjList #, ImportUser


class Match(object):
    def __init__(self, mObjects = None, sObjects = None):
        self._mObjects = filter(None, mObjects) or [] 
        self._sObjects = filter(None, sObjects) or []

    @property
    def mObjects(self):
        return self._mObjects
    
    @property
    def sObjects(self):
        return self._sObjects

    @property
    def isSingular(self):
        return len(self.mObjects) <= 1 and len(self.sObjects) <= 1

    @property
    def hasNoMaster(self):
        return len(self.mObjects) == 0

    @property
    def hasNoSlave(self):
        return len(self.sObjects) == 0

    @property
    def type(self):
        if(self.isSingular):
            if(self.hasNoMaster):
                if(not self.hasNoSlave):
                    return 'masterless'
                else:
                    return 'empty'
            elif(self.hasNoSlave):
                return 'slaveless'
            else:
                return 'pure'
        else:
            return 'duplicate'
    

    def addSObject(self, sObject):
        if sObject not in self.sObjects: self.sObjects.append(sObject)

    def addMObject(self, mObject):
        if mObject not in self.mObjects: self.mObjects.append(mObject)

    def findKeyMatches(self, keyFn):
        kMatches = {}
        for sObject in self.sObjects:
            value = keyFn(sObject)
            if not value in kMatches.keys(): 
                kMatches[value] = Match()
            kMatches[value].addSObject(sObject)
            # for mObject in self.mObjects:
            #     if keyFn(mObject) == value:
            #         kMatches[value].addMObject(mObject)
        for mObject in self.mObjects:
            value = keyFn(mObject)
            if not value in kMatches.keys():
                kMatches[value] = Match()
            kMatches[value].addMObject(mObject)
        return kMatches
    
    def WooObjListRepr(self, objs):
        length = len(objs)
        return "({0}) [{1:^200s}]".format(len(objs), ",".join(map(lambda obj: obj.__repr__()[:200/length], objs)))

    def __repr__(self):
        return " | ".join( [self.WooObjListRepr(self.mObjects), self.WooObjListRepr(self.sObjects)] ) 

    def tabulate(self, tablefmt=None):
        out  = ""
        match_type = self.type
        m_len, s_len = len(self.mObjects), len(self.sObjects)
        print_headings = False
        if(match_type in ['duplicate']):
            if(m_len > 0):
                # out += "The following ACT records are diplicates"
                if(s_len > 0):
                    print_headings = True
                    # out += " of the following WORDPRESS records"
            else:
                assert (s_len > 0)
                # out += "The following WORDPRESS records are duplicates"
        elif(match_type in ['masterless', 'slavelaveless']):
            pass
            # out += "The following records do not exist in %s" % {'masterless':'ACT', 'slaveless':'WORDPRESS'}[match_type]
        # out += "\n"
        users = UsrObjList()
        if(m_len > 0):
            objs = self.mObjects
            if(print_headings): 
                heading = ImportObject({}, 'M')
                objs = [heading] + objs
            for obj in objs :
                users.addObject(obj)
        if(s_len > 0):
            objs = self.sObjects
            if(print_headings): 
                heading = ImportObject({}, 'S')
                objs = [heading] + objs
            for obj in objs:
                # pprint(obj)
                users.addObject(obj)
        out += users.tabulate(tablefmt=tablefmt)
        return out


def findCardMatches(match):
    return match.findKeyMatches( lambda obj: obj.MYOBID or '')

def findPCodeMatches(match):
    return match.findKeyMatches( lambda obj: obj.get('Postcode') or obj.get('Home Postcode') or '')

class MatchList(list):
    def __init__(self, matches=None, indexFn = None):
        if(indexFn):
            self._indexFn = indexFn
        else:
            self._indexFn = (lambda x: x.index)
        self._sIndices = []
        self._mIndices = []
        if(matches):
            for match in matches:
                assert isinstance(match, Match)
                self.addMatch(match)

    @property
    def sIndices(self):
        return self._sIndices
    
    @property
    def mIndices(self):
        return self._mIndices

    def addMatch(self, match):
        for sObject in match.sObjects:
            sIndex = self._indexFn(sObject)
            assert sIndex not in self.sIndices
            self.sIndices.append(sIndex)
        for mObject in match.mObjects:
            mIndex = self._indexFn(mObject)
            assert mIndex not in self.mIndices
            self.mIndices.append(mIndex)
        self.append(match)

    def addMatches(self, matches):
        for match in matches:
            self.addMatch(match)

    def merge(self):
        mObjects = []
        sObjects = []
        for match in self:
            for mObj in match.mObjects:
                mObjects.append(mObj)
            for sObj in match.sObjects:
                sObjects.append(sObj)

        return Match(mObjects, sObjects)

    def tabulate(self, tablefmt=None):
        if(self):
            prefix, suffix = "", ""
            delimeter = "\n"
            if tablefmt == 'html':
                delimeter = ''
                prefix = '<div class="matchList">'
                suffix = '</div>'
            return prefix + delimeter.join(
                [match.tabulate(tablefmt=tablefmt) for match in self if match]
            ) + suffix
        else: 
            return ""



class AbstractMatcher(object):
    def __init__(self, keyFn = None):
        # print "entering AbstractMatcher __init__"
        if(keyFn):
            # print "-> keyFn"
            self.keyFn = keyFn
        else:
            # print "-> not keyFn"
            self.keyFn = (lambda x: x.index)
        self.processRegisters = self.processRegistersNonsingular
        self.retrieveObjects = self.retrieveObjectsNonsingular
        self.mFilterFn = None
        self.fFilterFn = None
        self.clear()

    def clear(self):
        self._matches = {
            'all': MatchList(),
            'pure': MatchList(),
            'slaveless': MatchList(),
            'masterless': MatchList(),
            'duplicate': MatchList()
        }

    @property
    def matches(self):
        return self._matches['all']

    @property
    def pureMatches(self):
        return self._matches['pure']

    @property
    def slavelessMatches(self):
        return self._matches['slaveless']
    
    @property
    def masterlessMatches(self):
        return self._matches['masterless']

    @property
    def duplicateMatches(self):
        return self._matches['duplicate']

    # saRegister is in nonsingular form. regkey => [slaveObjects]
    def processRegistersNonsingular(self, saRegister, maRegister):
        # print "processing nonsingular register"
        for regKey, regValue in saRegister.items():
            maObjects = self.retrieveObjects(maRegister, regKey)
            self.processMatch(maObjects, regValue)            

    # saRegister is in singular form. regIndex => slaveObject
    def processRegistersSingular(self, saRegister, maRegister):
        # print "processing singular register"
        for regKey, regValue in saRegister.items():
            maObjects = self.retrieveObjects(maRegister, self.keyFn(regValue))
            self.processMatch(maObjects, [regValue])

    def retrieveObjectsNonsingular(self, register, key):
        # print "retrieving nonsingular object"
        return register.get(key, [])

    def retrieveObjectsSingular(self, register, key):
        # print "retrieving singular object"
        regObject = register.get(key, [])
        if(regObject):
            return [regObject]
        else:
            return []

    def get_match_type(self, match):
        return match.type

    def addMatch(self, match, match_type):
        try:
            self._matches[match_type].addMatch(match)
        except Exception as e:
            print "could not add match to " + match_type + " matches ", e
        try:
            self._matches['all'].addMatch(match)
        except Exception as e:
            print "could not add match to matches ", e

    def mFilter(self, objects):
        if(self.mFilterFn):
            return filter(self.mFilterFn, objects)
        else:
            return objects

    def sFilter(self, objects):
        if(self.fFilterFn):
            return filter(self.fFilterFn, objects)
        else:
            return objects

    def processMatch(self, maObjects, saObjects):
        maObjects = self.mFilter(maObjects)
        saObjects = self.sFilter(saObjects)
        match = Match(maObjects, saObjects)
        match_type = self.get_match_type(match)
        if(match_type and match_type != 'empty'):
            self.addMatch(match, match_type)
            # print "match_type: ", match_type

    def __repr__(self):
        repr_str = ""
        repr_str += "pure matches:\n"
        for match in self.pureMatches:
             repr_str += " -> " + repr(match) + "\n"
        repr_str += "masterless matches:\n"
        for match in self.masterlessMatches:
             repr_str += " -> " + repr(match) + "\n"
        repr_str += "slaveless matches:\n"
        for match in self.slavelessMatches:
             repr_str += " -> " + repr(match) + "\n"
        repr_str += "duplicate matches:\n"
        for match in self.duplicateMatches:
             repr_str += " -> " + repr(match) + "\n"
        return repr_str

class UsernameMatcher(AbstractMatcher):
    def __init__(self):
        super(UsernameMatcher, self).__init__( lambda x: x.username )

class FilteringMatcher(AbstractMatcher):
    def __init__(self, keyFn, sMatchIndices = [], mMatchIndices = []):
        # print "entering FilteringMatcher __init__"
        super(FilteringMatcher, self).__init__( keyFn )
        self.sMatchIndices = sMatchIndices
        self.mMatchIndices = mMatchIndices
        self.mFilterFn = lambda x: x.index not in self.mMatchIndices
        self.fFilterFn = lambda x: x.index not in self.sMatchIndices

class CardMatcher(FilteringMatcher):
    def __init__(self, sMatchIndices = [], mMatchIndices = []):
        # print "entering CardMatcher __init__"
        super(CardMatcher, self).__init__( lambda x: x.MYOBID, sMatchIndices, mMatchIndices  )

class EmailMatcher(FilteringMatcher):
    def __init__(self, sMatchIndices = [], mMatchIndices = []):
        # print "entering EmailMatcher __init__"
        super(EmailMatcher, self).__init__( lambda x: x.email.lower(), sMatchIndices, mMatchIndices )
        
class NocardEmailMatcher(EmailMatcher):
    def __init__(self, sMatchIndices = [], mMatchIndices = []):
        # print "entering NocardEmailMatcher __init__"
        super(NocardEmailMatcher, self).__init__( sMatchIndices, mMatchIndices )
        self.processRegisters = self.processRegistersSingular