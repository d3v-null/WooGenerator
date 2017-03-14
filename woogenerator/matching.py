from parsing.csvparse_abstract import ImportObject, ObjList
# from parsing.csvparse_flat import UsrObjList #, ImportUser
from utils import SanitationUtils, Registrar, InheritenceUtils, listUtils
from collections import OrderedDict
from pprint import pformat

class Match(object):
    """ A list of master objects and slave objects that match in sosme way """

    def __init__(self, mObjects = None, sObjects = None):
        self._mObjects = filter(None, mObjects) or []
        self._sObjects = filter(None, sObjects) or []
        for _object in self._mObjects + self._sObjects:
            assert isinstance(_object, ImportObject)

    @property
    def mObjects(self):
        return self._mObjects

    @property
    def mObject(self):
        assert self.mLen == 1, \
            ".mObject assumes mObjects unique, instead it is %d long" % len(self._mObjects)
        return self._mObjects[0]

    @property
    def sObjects(self):
        return self._sObjects

    @property
    def sObject(self):
        assert self.sLen == 1, \
            ".sObject assumes mObjects unique, instead it is %d long" % len(self._sObjects)
        return self._sObjects[0]

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
            # Registrar.registerMessage("getting GCS of %s" % (self.mObjects + self.sObjects))
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

    def containerize(self):
        print_headings = False
        if self.type in ['duplicate']:
            if self.mObjects:
                # out += "The following ACT records are diplicates"
                if self.sObjects:
                    pass
                    # print_headings = True # we don't need to print headings any more :P
                    # out += " of the following WORDPRESS records"
            else:
                assert self.sObjects
                # out += "The following WORDPRESS records are duplicates"
        elif self.type in ['masterless', 'slavelaveless']:
            pass
            # out += "The following records do not exist in %s" % {'masterless':'ACT', 'slaveless':'WORDPRESS'}[self.type]
        # out += "\n"
        obj_container = None
        if self.mLen or self.sLen:
            gcs = self.gcs
            if gcs is not None and hasattr(gcs, 'container'):
                obj_container = gcs.container(indexer=(lambda x: x.identifier))
                # else:
                    # container = None
                    # if hasattr(gcs, 'container'):
                    #     container = gcs.container
                    # Registrar.registerError("could not create GCS %s, container: %s | %s" % (repr(gcs), repr(container), str(e)))
                    # obj_container = ObjList()
                # Registrar.registerMessage(
                #     "tabulating with container: %s because of gcs %s" \
                #     % (type(obj_container), gcs)
                # )
            else:
                obj_container = ObjList(indexer=(lambda x: x.identifier))
                # Registrar.registerMessage(
                #     "tabulating with container: %s because no gcs" \
                #     % (type(obj_container))
                # )
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
        return obj_container

    def tabulate(self, cols=None, tablefmt=None, highlight_rules=None):
        out  = ""

        obj_container = self.containerize()
        if obj_container:
            try:
                out += obj_container.tabulate(cols=cols, tablefmt=tablefmt, highlight_rules=highlight_rules)
            except TypeError as e:
                print "obj_container could not tabulate: %s " % type(obj_container) 
                raise e
            except AssertionError as e:
                print "could not tabulate\nmObjects:%s\nsObjects:%s" % (
                    self.mObjects,
                    self.sObjects
                )
                raise e
        else:
            out += 'EMPTY'
        # return SanitationUtils.coerceUnicode(out)
        return (out)

def findCardMatches(match):
    return match.findKeyMatches( lambda obj: obj.MYOBID or '')

def findPCodeMatches(match):
    return match.findKeyMatches( lambda obj: obj.get('Postcode') or obj.get('Home Postcode') or '')

class MatchList(list):
    """ A sequence of Match objects indexed by an indexFn"""

    check_indices = True

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
                "can't add match sObject %s : sIndex %s already in sIndices: %s \n %s \n all matches: \n%s ;\n probably ambiguous category names" % (
                    str(sObject), str(sIndex), str(self.sIndices), str(match), str('\n'.join(map(str,self)))
                )
            matchSIndices.append(sIndex)
        if matchSIndices:
            if self.check_indices:
                assert listUtils.checkEqual(matchSIndices), "all sIndices should be equal: %s" % matchSIndices
            self.sIndices.append(matchSIndices[0])
        for mObject in match.mObjects:
            # Registrar.registerMessage('indexing master %s with %s : %s' \
                                    # % (sObject, repr(self._indexFn), sIndex))
            mIndex = self._indexFn(mObject)
            assert \
                mIndex not in self.mIndices, \
                "can't add match mObject %s : mIndex %s already in mIndices: %s \n %s \n all matches: %s" % (
                    str(mObject), str(mIndex), str(self.mIndices), str(match), str('\n'.join(map(str,self)))
                )
            matchMIndices.append(mIndex)
        if matchMIndices:
            if self.check_indices:
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

    def tabulate(self, cols=None, tablefmt=None, highlight_rules=None):
        if(self):
            prefix, suffix = "", ""
            delimeter = "\n"
            if tablefmt == 'html':
                delimeter = ''
                prefix = '<div class="matchList">'
                suffix = '</div>'
            return prefix + delimeter.join(
                [SanitationUtils.coerceBytes(match.tabulate(cols=cols, tablefmt=tablefmt, highlight_rules=highlight_rules))\
                 for match in self if match]
            ) + suffix
        else:
            return ""

class ConflictingMatchList(MatchList):
    check_indices = False


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
        # self.retrieveObjects = self.retrieveObjectsNonsingular
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
        """ Groups items in both registers by the result of applying the index function when both are nonsingular """
        # It's messy because we can't assume that our indexFn is the same as the indexFn of the register :(
        # Properly index maRegister:
        msIndexed = OrderedDict()
        for regValues in maRegister.values():
            for regValue in regValues:
                regIndex = self.indexFn(regValue)
                if not regIndex in msIndexed:
                    msIndexed[regIndex] = ([], [])
                msIndexed[regIndex][0].append(regValue)

        for regValues in saRegister.values():
            for regValue in regValues:
                regIndex = self.indexFn(regValue)
                if not regIndex in msIndexed:
                    msIndexed[regIndex] = ([], [])
                msIndexed[regIndex][1].append(regValue)

        for msValues in msIndexed.values():
            self.processMatch(msValues[0], msValues[1])

        # mKeys = set(maRegister.keys())
        # for regKey, regValue in saRegister.items():
        #     saObjects = regValue
        #     maObjects = self.retrieveObjects(maRegister, regKey)
        #     if regKey in mKeys:
        #         mKeys.remove(regKey)
        #     self.processMatch(maObjects, saObjects)
        # for mKey in mKeys:
        #     saObjects = []
        #     maObjects = self.retrieveObjects(maRegister, mKey)
        #     self.processMatch(maObjects, saObjects)

    # saRegister is in singular form. regIndex => slaveObject
    def processRegistersSingular(self, saRegister, maRegister):
        """ Groups items in both registers by the result of applying the index function when both are singular """
        # again, complicated because can't assume we have the same indexFn as the registers

        msIndexed = OrderedDict()
        for regValue in maRegister.values():
            regIndex = self.indexFn(regValue)
            if not regIndex in msIndexed:
                msIndexed[regIndex] = ([], [])
            msIndexed[regIndex][0].append(regValue)

        for regValue in saRegister.values():
            regIndex = self.indexFn(regValue)
            if not regIndex in msIndexed:
                msIndexed[regIndex] = ([], [])
            msIndexed[regIndex][1].append(regValue)

        for msValues in msIndexed.values():
            self.processMatch(msValues[0], msValues[1])

        # mKeys = OrderedDict()
        # for regKey, regValue in maRegister.items():
        #     regIndex = self.indexFn(regValue)
        #     if not regIndex in mKeys:
        #         mKeys[regIndex] = []
        #     mKeys[regIndex].append(regKey)
        #
        # sKeys = OrderedDict()
        # for regKey, regValue in saRegister.items():
        #     regIndex = self.indexFn(regValue)
        #     if not regIndex in sKeys:
        #         sKeys[regIndex] = []
        #     sKeys[regIndex].append(regKey)
        #
        # for regIndex in list(set(mKeys) | set(sKeys)):
        #     mObjects = []
        #     sObjects = []
        #     if regIndex in mKeys:
        #         for regKey in mKeys[regIndex]:
        #             mObjects.extend(self.retrieveObjects(maRegister, regKey))
        #     if regIndex in sKeys:
        #         for regKey in sKeys[regIndex]:
        #             sObjects.extend(self.retrieveObjects(saRegister, regKey))
        #     self.processMatch(mObjects, sObjects)

    def processRegistersSingularNonSingular(self, saRegister, maRegister):
        """ Master is nonsingular, slave is singular """
        msIndexed = OrderedDict()
        for regValues in maRegister.values():
            for regValue in regValues:
                regIndex = self.indexFn(regValue)
                if not regIndex in msIndexed:
                    msIndexed[regIndex] = ([], [])
                msIndexed[regIndex][0].append(regValue)

        for regValue in saRegister.values():
            regIndex = self.indexFn(regValue)
            if not regIndex in msIndexed:
                msIndexed[regIndex] = ([], [])
            msIndexed[regIndex][1].append(regValue)

        for msValues in msIndexed.values():
            self.processMatch(msValues[0], msValues[1])

        # # make slave nonsingular and process both as nonsingular
        # saRegister = OrderedDict([(key, [value]) for key, value in saRegister.items()])
        # self.processRegistersNonsingular(saRegister, maRegister)

    def processRegistersNonSingularSingular(self, saRegister, maRegister):
        """ Master is singular, slave is nonsingular """

        msIndexed = OrderedDict()
        for regValue in maRegister.values():
            regIndex = self.indexFn(regValue)
            if not regIndex in msIndexed:
                msIndexed[regIndex] = ([], [])
            msIndexed[regIndex][0].append(regValue)

        for regValues in saRegister.values():
            for regValue in regValues:
                regIndex = self.indexFn(regValue)
                if not regIndex in msIndexed:
                    msIndexed[regIndex] = ([], [])
                msIndexed[regIndex][1].append(regValue)

        for msValues in msIndexed.values():
            self.processMatch(msValues[0], msValues[1])

        # # make master nonsingular and process both as nonsingular
        # maRegister = OrderedDict([(key, [value]) for key, value in maRegister.items()])
        # self.processRegistersNonsingular(saRegister, maRegister)

    # def retrieveObjectsNonsingular(self, register, key):
    #     # print "retrieving nonsingular object"
    #     return register.get(key, [])

    # def retrieveObjectsSingular(self, register, key):
    #     # print "retrieving singular object"
    #     regObject = register.get(key, [])
    #     if(regObject):
    #         return [regObject]
    #     else:
    #         return []

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
        # Registrar.registerMessage(
        #     "processing match: \n\t%s \n\t%s" % (
        #         repr(maObjects),
        #         repr(saObjects)
        #     )
        # )

        # print "processing match %s | %s" % (repr(maObjects), repr(saObjects))
        maObjects = self.mFilter(maObjects)
        for maObject in maObjects:
            assert \
                isinstance(maObject, ImportObject), \
                "maObject must be instance of ImportObject, not %s \n objects: %s \n self: %s" \
                % (type(maObject), maObjects, self.__repr__())
        saObjects = self.sFilter(saObjects)
        for saObject in saObjects:
            assert \
                isinstance(saObject, ImportObject), \
                "saObject must be instance of ImportObject, not %s \n objects: %s \n self: %s" \
                % (type(saObject), saObjects, self.__repr__())
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
        repr_str += "pure matches: (%d) \n" % len(self.pureMatches)
        for match in self.pureMatches:
            repr_str += " -> " + repr(match) + "\n"
        repr_str += "masterless matches: (%d) \n" % len(self.masterlessMatches)
        for match in self.masterlessMatches:
            repr_str += " -> " + repr(match) + "\n"
        repr_str += "slaveless matches:(%d) \n" % len(self.slavelessMatches)
        for match in self.slavelessMatches:
            repr_str += " -> " + repr(match) + "\n"
        repr_str += "duplicate matches:(%d) \n" % len(self.duplicateMatches)
        for match in self.duplicateMatches:
            repr_str += " -> " + repr(match) + "\n"
        return repr_str

class ProductMatcher(AbstractMatcher):
    processRegisters = AbstractMatcher.processRegistersSingular
    # retrieveObjects = AbstractMatcher.retrieveObjectsSingular
    @staticmethod
    def productIndexFn(x):
        return x.codesum

    def __init__(self):
        super(ProductMatcher, self).__init__( self.productIndexFn )
        self.processRegisters = self.processRegistersSingular
        # self.retrieveObjects = self.retrieveObjectsSingular

class VariationMatcher(ProductMatcher):
    pass

class CategoryMatcher(AbstractMatcher):
    processRegisters = AbstractMatcher.processRegistersSingular
    # retrieveObjects = AbstractMatcher.retrieveObjectsSingular
    @staticmethod
    def categoryIndexFn(x):
        return x.wooCatName

    def __init__(self):
        super(CategoryMatcher, self).__init__( self.categoryIndexFn )
        self.processRegisters = self.processRegistersSingular
        # self.retrieveObjects = self.retrieveObjectsSingular

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
    @staticmethod
    def cardIndexFn(x):
        assert hasattr(x, 'MYOBID'), 'must be able to get MYOBID, instead type is %s' % type(x)
        return x.MYOBID

    def __init__(self, sMatchIndices = [], mMatchIndices = []):
        # print "entering CardMatcher __init__"
        super(CardMatcher, self).__init__( self.cardIndexFn, sMatchIndices, mMatchIndices  )

class EmailMatcher(FilteringMatcher):
    @staticmethod
    def emailIndexFn(x):
        assert hasattr(x, 'email'), "must be able to get email, instead type is %s" % type(x)
        return SanitationUtils.normalizeVal(x.email)

    def __init__(self, sMatchIndices = [], mMatchIndices = []):
        # print "entering EmailMatcher __init__"
        super(EmailMatcher, self).__init__(
            self.emailIndexFn,
            sMatchIndices, mMatchIndices )

class NocardEmailMatcher(EmailMatcher):
    def __init__(self, sMatchIndices = [], mMatchIndices = []):
        # print "entering NocardEmailMatcher __init__"
        super(NocardEmailMatcher, self).__init__( sMatchIndices, mMatchIndices )
        self.processRegisters = self.processRegistersSingularNonSingular
