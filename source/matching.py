from csvparse_abstract import ImportObject, ObjList
# from csvparse_flat import UsrObjList #, ImportUser
from utils import SanitationUtils, Registrar, InheritenceUtils, listUtils
from collections import OrderedDict
from pprint import pformat

class Match(object):
    def __init__(self, mObjects = None, sObjects = None):
        self._mObjects = filter(None, mObjects) or []
        self._sObjects = filter(None, sObjects) or []
        for _object in self._mObjects + self._sObjects:
            assert isinstance(_object, ImportObject)

    @property
    def mObjects(self):
        return self._mObjects

    @property
    def sObjects(self):
        return self._sObjects

    @property
    def sLen(self):
        return len(self._sObjects)

    @property
    def mLen(self):
        return len(self._mObjects)

    @property
    def isSingular(self):
        return self.mLen <= 1 and self.sLen <= 1

    @property
    def hasNoMaster(self):
        return self.mLen == 0

    @property
    def hasNoSlave(self):
        return self.sLen == 0

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

    @property
    def gcs(self):
        """Greatest common subset"""
        if self.mLen or self.sLen:
            return InheritenceUtils.gcs(*(self.mObjects + self.sObjects))
        else:
            return None


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
        return "({0}) [{1:^100s}]".format(len(objs), ",".join(map(lambda obj: obj.__repr__()[:200/length], objs)))

    def __repr__(self):
        return " | ".join( [self.WooObjListRepr(self.mObjects), self.WooObjListRepr(self.sObjects)] )

    def tabulate(self, tablefmt=None):
        out  = ""
        match_type = self.type
        print_headings = False
        if match_type in ['duplicate']:
            if self.mObjects:
                # out += "The following ACT records are diplicates"
                if self.sObjects:
                    print_headings = True
                    # out += " of the following WORDPRESS records"
            else:
                assert self.sObjects
                # out += "The following WORDPRESS records are duplicates"
        elif match_type in ['masterless', 'slavelaveless']:
            pass
            # out += "The following records do not exist in %s" % {'masterless':'ACT', 'slaveless':'WORDPRESS'}[match_type]
        # out += "\n"

        if self.mLen or self.sLen:
            gcs = self.gcs
            if gcs is not None:
                try:
                    obj_container = gcs.container(indexer=(lambda x: x.identifier))
                except Exception, e:
                    Registrar.registerError("could not create GCS %s, container: %s | %s" % (repr(gcs), repr(gcs.container), str(e)))
                    raise e
            else:
                obj_container = ObjList()
            if self.mObjects:
                mobjs = self.mObjects[:]
                if(print_headings):
                    heading = gcs({}, rowcount='M')
                    # heading = ImportObject({}, rowcount='M')
                    mobjs = [heading] + mobjs
                for mobj in mobjs :
                    obj_container.append(mobj)
            if self.sObjects:
                sobjs = self.sObjects[:]
                if(print_headings):
                    heading = gcs({}, rowcount='S')
                    # heading = ImportObject({}, rowcount='S')
                    sobjs = [heading] + sobjs
                for sobj in sobjs:
                    # pprint(sobj)
                    obj_container.append(sobj)
            out += obj_container.tabulate(tablefmt=tablefmt)
        else:
            out += 'EMPTY'
        # return SanitationUtils.coerceUnicode(out)
        return (out)


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
        # Registrar.registerMessage("adding match: %s" % str(match))
        matchSIndices = []
        matchMIndices = []
        for sObject in match.sObjects:
            # Registrar.registerMessage('indexing slave %s with %s : %s' \
            #                         % (sObject, repr(self._indexFn), sIndex))
            sIndex = self._indexFn(sObject)
            assert \
                sIndex not in self.sIndices, \
                "can't add match: sIndex %s already in sIndices: %s \n %s \n all matches: %s" % (
                    str(sIndex), str(self.sIndices), str(match), str(self)
                )
            matchSIndices.append(sIndex)
        if matchSIndices:
            assert listUtils.checkEqual(matchSIndices), "all sIndices should be equal: %s" % matchSIndices
            self.sIndices.append(matchSIndices[0])
        for mObject in match.mObjects:
            # Registrar.registerMessage('indexing master %s with %s : %s' \
                                    # % (sObject, repr(self._indexFn), sIndex))
            mIndex = self._indexFn(mObject)
            assert \
                mIndex not in self.mIndices, \
                "can't add match: mIndex %s already in mIndices: %s \n %s \n all matches: %s" % (
                    str(mIndex), str(self.mIndices), str(match), str('\n'.join(map(str,self)))
                )
            matchMIndices.append(mIndex)
        if matchMIndices:
            assert listUtils.checkEqual(matchMIndices), "all mIndices should be equal: %s" % matchMIndices
            self.mIndices.append(matchMIndices[0])
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
                [SanitationUtils.coerceBytes(match.tabulate(tablefmt=tablefmt)) for match in self if match]
            ) + suffix
        else:
            return ""



class AbstractMatcher(Registrar):
    def __init__(self, indexFn = None):
        super(AbstractMatcher, self).__init__()
        # print "entering AbstractMatcher __init__"
        if(indexFn):
            # print "-> indexFn"
            self.indexFn = indexFn
        else:
            # print "-> not indexFn"
            self.indexFn = (lambda x: x.index)
        self.processRegisters = self.processRegistersNonsingular
        self.retrieveObjects = self.retrieveObjectsNonsingular
        self.mFilterFn = None
        self.fFilterFn = None
        self.clear()

    def clear(self):
        self._matches = {
            'all': MatchList(indexFn=self.indexFn),
            'pure': MatchList(indexFn=self.indexFn),
            'slaveless': MatchList(indexFn=self.indexFn),
            'masterless': MatchList(indexFn=self.indexFn),
            'duplicate': MatchList(indexFn=self.indexFn)
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
        mKeys = set(maRegister.keys())

        for regKey, regValue in saRegister.items():
            saObjects = regValue
            maObjects = self.retrieveObjects(maRegister, regKey)
            if regKey in mKeys:
                mKeys.remove(regKey)
            self.processMatch(maObjects, saObjects)
        for mKey in mKeys:
            saObjects = []
            maObjects = self.retrieveObjects(maRegister, mKey)
            self.processMatch(maObjects, saObjects)

    # saRegister is in singular form. regIndex => slaveObject
    def processRegistersSingular(self, saRegister, maRegister):
        # print "processing singular register"
        # mKeys = set(maRegister.keys())
        # mKeys = OrderedDict()
        # for regKey, regValue in maRegister:
        #     mKeys.update({self.indexFn(regValue):regKey})
        # mKeys = \
        #     [(self.indexFn(regValue), regKey) for regKey, regValue in maRegister.items()]

        # mKeys is a mapping from indexes of regValues to their corresponding regKeys
        mKeys = OrderedDict()
        for regKey, regValue in maRegister.items():
            regIndex = self.indexFn(regValue)
            if not regIndex in mKeys:
                mKeys[regIndex] = []
            mKeys[regIndex].append(regKey)

        # self.registerMessage('mkeys: %s' % pformat(mKeys))

        # print "mKeys", mKeys
        for regKey, regValue in saRegister.items():
            # self.registerMessage('analysing saRegisteritem (%s, %s)' % (regKey, regValue))
            saObjects = [regValue]
            mKey = self.indexFn(regValue)
            maObjects = []
            if mKey in mKeys:
                mRegKeys = mKeys[mKey]
                # print "removing key", mKey, "from", mKeys
                mKeys.pop(mKey)
                maObjects = []
                for mRegKey in mRegKeys:
                    maObjects.extend(self.retrieveObjects(maRegister, mRegKey))
            self.processMatch(maObjects, saObjects)
        for mKey, regKeys in mKeys.items():
            saObjects = []
            maObjects = []
            for regKey in regKeys:
                maObjects.extend(self.retrieveObjects(maRegister, regKey))
            self.processMatch(maObjects, saObjects)

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
        # except Exception as e:
        finally:
            pass
            # self.registerWarning( "could not add match to %s matches %s" % (
            #     match_type,
            #     SanitationUtils.coerceUnicode(repr(e))
            # ))
            # raise e
        try:
            self._matches['all'].addMatch(match)
        # except Exception as e:
        finally:
            pass
            # self.registerWarning( "could not add match to matches %s" % (
            #     SanitationUtils.coerceUnicode(repr(e))
            # ))

    def mFilter(self, objects):
        if self.mFilterFn:
            return filter(self.mFilterFn, objects)
        else:
            return objects

    def sFilter(self, objects):
        if self.fFilterFn:
            return filter(self.fFilterFn, objects)
        else:
            return objects

    def processMatch(self, maObjects, saObjects):
        # print "processing match %s | %s" % (repr(maObjects), repr(saObjects))
        maObjects = self.mFilter(maObjects)
        for maObject in maObjects:
            assert \
                isinstance(maObject, ImportObject), \
                "maObject must be instance of ImportObject, not %s \n objects: %s \n self: %s" % (type(maObject), maObjects, self.__repr__())
        saObjects = self.sFilter(saObjects)
        for saObject in saObjects:
            assert \
                isinstance(saObject, ImportObject), \
                "saObject must be instance of ImportObject, not %s \n objects: %s \n self: %s" % (type(saObject), saObjects, self.__repr__())
        match = Match(maObjects, saObjects)
        match_type = self.get_match_type(match)
        if(match_type and match_type != 'empty'):
            self.addMatch(match, match_type)
            # print "match_type: ", match_type

    def __repr__(self):
        repr_str = ""
        # repr_str += "all matches:\n"
        # for match in self.matches:
        #     repr_str += " -> " + repr(match) + "\n"
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

class ProductMatcher(AbstractMatcher):
    # processRegisters = AbstractMatcher.processRegistersSingular
    # retrieveObjects = AbstractMatcher.retrieveObjectsSingular
    @staticmethod
    def productIndexFn(x):
        return x.codesum

    def __init__(self):
        super(ProductMatcher, self).__init__( self.productIndexFn )
        self.processRegisters = self.processRegistersSingular
        self.retrieveObjects = self.retrieveObjectsSingular

class CategoryMatcher(AbstractMatcher):
    # processRegisters = AbstractMatcher.processRegistersSingular
    # retrieveObjects = AbstractMatcher.retrieveObjectsSingular
    @staticmethod
    def categoryIndexFn(x):
        return x.wooCatName

    def __init__(self):
        super(CategoryMatcher, self).__init__( self.categoryIndexFn )
        self.processRegisters = self.processRegistersSingular
        self.retrieveObjects = self.retrieveObjectsSingular

class UsernameMatcher(AbstractMatcher):
    def __init__(self):
        super(UsernameMatcher, self).__init__( lambda x: x.username )

class FilteringMatcher(AbstractMatcher):
    def __init__(self, indexFn, sMatchIndices = [], mMatchIndices = []):
        # print "entering FilteringMatcher __init__"
        super(FilteringMatcher, self).__init__( indexFn )
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
        super(EmailMatcher, self).__init__(
            lambda x: SanitationUtils.normalizeVal(x.email),
            sMatchIndices, mMatchIndices )

class NocardEmailMatcher(EmailMatcher):
    def __init__(self, sMatchIndices = [], mMatchIndices = []):
        # print "entering NocardEmailMatcher __init__"
        super(NocardEmailMatcher, self).__init__( sMatchIndices, mMatchIndices )
        self.processRegisters = self.processRegistersSingular
