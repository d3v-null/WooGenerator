"""
Classes that add the concept of heirarchy to the CSVParse classes and corresponding helper classes
"""

from collections import OrderedDict
from pprint import pformat
from woogenerator.utils import Registrar
from woogenerator.parsing.abstract import CSVParse_Base, ImportObject, ObjList


class ImportTreeRootableMixin(object):
    pass


class ImportTreeObject(ImportObject):
    """ Implements the tree interface for tree objects """
    isRoot = None
    isItem = None
    isTaxo = None
    _depth = None
    verifyMetaKeys = []

    def __init__(self, *args, **kwargs):
        if self.DEBUG_MRO:
            self.registerMessage('ImportTreeObject')
        super(ImportTreeObject, self).__init__(*args, **kwargs)
        # if self.DEBUG_PARSER:
        #     self.registerMessage('called with kwargs: %s' % pformat(kwargs))

        # row = kwargs.get('row')
        # rowcount = kwargs.get('rowcount')
        try:
            parent = kwargs.pop('parent', None)
            if not self.isRoot:
                assert parent is not None
        except (KeyError, AssertionError):
            raise UserWarning(
                "No parent specified, try specifying root as parent")
        self.parent = parent

        try:
            depth = kwargs.pop('depth', -1)
            if not self.isRoot:
                assert depth is not None
                assert depth >= 0
        except (AssertionError):
            depth = self.parent.depth + 1
        finally:
            self.depth = depth

        try:
            meta = kwargs.pop('meta', None)
            assert meta is not None
        except (AssertionError, KeyError):
            meta = []
        finally:
            self.meta = meta

        #

        if self.DEBUG_PARSER:
            self.registerMessage(
                'About to register child: %s' % str(self.items()))

        self.processMeta()
        if not self.isRoot:
            parent.registerChild(self)

        self.child_register = OrderedDict()
        self.child_indexer = Registrar.getObjectRowcount

        self.verifyMeta()

    # @property
    # def verifyMetaKeys(self):
    #     return []

    #
    def verifyMeta(self):
        # return
        for key in self.verifyMetaKeys:
            if self.DEBUG_PARSER:
                self.registerMessage("CHECKING KEY: %s" % key)
            assert key in self.keys(), "key %s must be set" % str(key)

    #
    @property
    def ancestors(self):
        "gets all ancestors not including self or root"
        this = self.parent
        ancestors = []
        while this and not this.isRoot:
            ancestors.insert(0, this)
            this = this.parent
        return ancestors

    #
    def registerChild(self, childData):
        assert childData, "childData must be valid"
        # self.registerMessage("Registering child %s of %s with siblings: %s"\
        #     % (
        #         childData.identifier,
        #         self.identifier,
        #         str(self.children)
        #     ))
        # for child in self.children:
        #     assert child.fullname != childData.fullname, "child %s of %s not unique to %s" \
        #                                             % (
        #                                                 childData.identifier,
        #                                                 self.identifier,
        #                                                 self.children
        #                                             )
        self.registerAnything(
            childData,
            self.child_register,
            indexer=self.child_indexer,
            singular=True,
            # resolver = self.passiveResolver,
            registerName='parent'
        )

    @property
    def children(self):
        return self.child_register.values()
    #

    @property
    def siblings(self):
        parent = self.parent
        if parent:
            return parent.children
        else:
            return []

    #
    # @classmethod
    # def fromImportObject(cls, object_data, depth, meta, parent):
    #     exc = DeprecationWarning()
    #     self.registerError(exc)
        # assert isinstance(object_data, ImportObject)
        # row = object_data.row
        # rowcount = object_data.rowcount
        # return cls(object_data, rowcount, row, depth, meta, parent)
    #
    # @property
    # def isItem(self): return self.isItem
    #
    # @property
    # def isTaxo(self): return self.isTaxo
    #
    # @property
    # def isRoot(self): return self.isRoot

    # @property
    # def meta(self): return self._meta

    # @property
    # def parent(self): return self._parent

    def getCopyArgs(self):
        args = super(ImportTreeObject, self).getCopyArgs()
        args.update(
            depth=self.depth,
            parent=self.parent,
            meta=self.meta,
        )
        return args

    def processMeta(self): pass

    @property
    def inheritenceAncestors(self):
        return self.ancestors

    # def getInheritanceAncestors(self):
    #     exc = DeprecationWarning("use .inheritenceAncestors insetad of .getInheritanceAncestors()")
    #     self.registerError(exc)
    #     return self.inheritenceAncestors

    def inheritKey(self, key):
        if not self.get(key):
            inheritence = filter(None, map(
                lambda x: x.get(key),
                self.inheritenceAncestors
            ))
            if inheritence:
                self[key] = inheritence[-1]

    @property
    def depth(self):
        return self._depth

    @depth.setter
    def depth(self, depth):
        assert(isinstance(depth, int))
        self._depth = depth

    @property
    def identifier_delimeter(self):
        # delim = super(ImportTreeObject, self).identifier_delimeter
        return "=" * self.depth

    # def getIdentifierDelimeter(self):
    #     exc = DeprecationWarning("Use .identifier_delimeter instead of .getIdentifierDelimeter()")
    #     self.registerError(exc)
    #     return self.identifier_delimeter

    # def getParent(self):
    #     exc = DeprecationWarning("Use .parent instead of .getParent()")
    #     self.registerError(exc)
    #     return self.parent
    #
    # def getAncestors(self):
    #     exc = DeprecationWarning("use .ancestors instead of .getAncestors()")
    #     self.registerError(exc)
    #     return self.ancestors
    #     # "gets all ancestors not including self or root"
    #     # this = self.getParent()
    #     # ancestors = []
    #     # while this and not this.isRoot:
    #     #     ancestors.insert(0, this)
    #     #     this = this.getParent()
    #     # return ancestors

    @property
    def taxoAncestors(self):
        return filter(lambda x: x.isTaxo, self.ancestors)

    # def getTaxoAncestors(self):
    #     exc = DeprecationWarning("use .taxoAncestors instead of .getTaxoAncestors()")
    #     self.registerError(exc)
    #     return self.taxoAncestors
    #     # ancestors = self.getAncestors()
    #     # return filter( lambda x: x.isTaxo, ancestors)

    def getAncestorKey(self, key):
        # ancestors = self.getAncestors()
        return [ancestor.get(key) for ancestor in self.ancestors]

    def getAncestorSelfKey(self, key):
        # ancestors = self.getAncestors()
        return [ancestor.get(key) for ancestor in [self] + self.ancestors]

    def getFirstFilteredAncestorSelfKey(self, key):
        ancestor_values = self.getAncestorSelfKey(key)
        filtered_ancestor_values = [value for value in ancestor_values if value]
        if filtered_ancestor_values[0]:
            return filtered_ancestor_values[0]
    #
    # def getChildren(self):
    #     exc = DeprecationWarning("use .children instead of .getChildren()")
    #     self.registerError(exc)
    #     return self.children
    #
    # def getSiblings(self):
    #     exc = DeprecationWarning("use .siblings instead of .getSiblings()")
    #     self.registerError(exc)
    #     return self.siblings

# do we need these?
    #
    # def getDepth(self):
    #     exc = DeprecationWarning("use .depth instead of .getDepth()")
    #     self.registerError(exc)
    #     return self.depth
    #
    # def getMeta(self):
    #     exc = DeprecationWarning("use .meta instead of .getMeta()")
    #     self.registerError(exc)
    #     return self.meta


class ImportTreeRoot(ImportTreeObject):
    isRoot = True

    def __init__(self, *args, **kwargs):
        if self.DEBUG_MRO:
            self.registerMessage('ImportTreeRoot')
        data = OrderedDict()
        super(ImportTreeRoot, self).__init__(data, rowcount=-1, row=[])

    @property
    def title(self):
        return "root"

    @property
    def wpid(self):
        return "-1"


class ImportTreeItem(ImportTreeObject):
    isItem = True

    @property
    def identifier_delimeter(self):
        return super(ImportTreeItem, self).identifier_delimeter + '>'

    # def getIdentifierDelimeter(self):
    #     exc = DeprecationWarning("use .identifier_delimeter instead of .getIdentifierDelimeter()")
    #     self.registerError(exc)
    #     return self.identifier_delimeter
        # return super(ImportTreeItem, self).getIdentifierDelimeter() + '>'

    @property
    def itemAncestors(self):
        return filter(lambda x: x.isItem, self.ancestors)

    # def getItemAncestors(self):
    #     exc = DeprecationWarning("use .itemAncestors instead of .getItemAncestors()")
    #     self.registerError(exc)
    #     return self.itemAncestors
    #     # ancestors = self.getAncestors()
    #     # return filter( lambda x: x.isItem, ancestors)


class ImportTreeTaxo(ImportTreeObject):
    isTaxo = True

    @property
    def identifier_delimeter(self):
        return super(ImportTreeTaxo, self).identifier_delimeter + '#'

    def getIdentifierDelimeter(self):
        exc = DeprecationWarning(
            "use .identifier_delimeter instead of .getIdentifierDelimeter()")
        self.registerError(exc)
        return self.identifier_delimeter
        # return super(ImportTreeTaxo, self).getIdentifierDelimeter() + '#'


class ItemList(ObjList):
    supported_type = ImportTreeItem
    objList_type = 'items'


class TaxoList(ObjList):
    supported_type = ImportTreeTaxo
    objList_type = 'taxos'


class ImportStack(list):

    def topHasParent(self):
        return len(self) > 1

    def getTopParent(self):
        if self.topHasParent():
            return self[-2]
        else:
            return None

    def isEmpty(self):
        return len(self) is 0

    def getTop(self):
        return None if self.isEmpty() else self[-1]

    def retrieveKey(self, key):
        vals = []
        for layer in self:
            try:
                vals.append(layer[key])
            except (IndexError, KeyError):
                vals.append('')
        return vals

    def getLeftSlice(self, index):
        return ImportStack(self[:index])

    def __repr__(self):
        return ''.join([
            '<%s>' % self.__class__.__name__,
            '[%s]' % ','.join([str(x.index) for x in self]),
        ])

    def __getslice__(self, i, j):
        return self.__class__(list.__getslice__(self, i, j))

    def display(self):
        out = "\n"
        for object_data in self:
            try:
                out += object_data.identifier + "\n"
            except:
                out += repr(object_data) + "\n"
        return out

    def copy(self):
        return ImportStack(self[:])


class CSVParse_Tree_Mixin(object):
    rootContainer = ImportTreeRoot

    def clearTransients(self):
        self.rootData = self.rootContainer()


class CSVParse_Tree(CSVParse_Base, CSVParse_Tree_Mixin):
    objectContainer = ImportTreeObject
    itemContainer = ImportTreeItem
    taxoContainer = ImportTreeTaxo

    def __init__(self, cols, defaults, taxoDepth,
                 itemDepth, meta_width, **kwargs):
        if self.DEBUG_MRO:
            self.registerMessage('CSVParse_Tree')
        self.taxoDepth = taxoDepth
        self.itemDepth = itemDepth
        # self.maxDepth  = taxoDepth + itemDepth
        self.meta_width = meta_width
        self.itemIndexer = self.getObjectRowcount
        self.taxoIndexer = self.getObjectRowcount
        super(CSVParse_Tree, self).__init__(cols, defaults, **kwargs)

        # if self.DEBUG_TREE:
        #     print "TREE initializing: "
        #     print "-> taxoDepth: ", self.taxoDepth
        #     print "-> itemDepth: ", self.itemDepth
        #     print "-> maxDepth: ", self.maxDepth
        #     print "-> meta_width: ", self.meta_width

    @property
    def maxDepth(self):
        return self.taxoDepth + self.itemDepth

    def clearTransients(self):
        if self.DEBUG_MRO:
            self.registerMessage('CSVParse_Tree')
        CSVParse_Base.clearTransients(self)
        CSVParse_Tree_Mixin.clearTransients(self)
        self.items = OrderedDict()
        self.taxos = OrderedDict()
        self.stack = ImportStack()

    #
    def registerItem(self, itemData):
        assert isinstance(itemData, ImportTreeObject)
        assert itemData.isItem
        self.registerAnything(
            itemData,
            self.items,
            indexer=self.itemIndexer,
            singular=True,
            registerName='items'
        )

    def registerTaxo(self, taxoData):
        assert isinstance(taxoData, ImportTreeObject)
        assert taxoData.isTaxo
        self.registerAnything(
            taxoData,
            self.taxos,
            indexer=self.taxoIndexer,
            singular=True,
            # resolver = self.passiveResolver,
            registerName='taxos',
        )

    def registerObject(self, object_data):
        assert isinstance(object_data, ImportTreeObject)
        super(CSVParse_Tree, self).registerObject(object_data)
        if self.DEBUG_MRO:
            self.registerMessage(' ')
        if object_data.isItem:
            self.registerItem(object_data)
        if object_data.isTaxo:
            self.registerTaxo(object_data)

    # def registerObject(self, object_data):
    #     CSVParse_Base.registerObject(self, object_data)
    #     CSVParse_Tree_Mixin.registerObject(self, object_data)

        # self.registerMessage("ceated root: %s" % str(self.rootData))

    def assignParent(self, parent_data=None, itemData=None):
        assert isinstance(itemData, ImportTreeObject)
        if not parent_data:
            parent_data = self.rootData
        assert isinstance(parent_data, ImportTreeObject)
        parent_data.registerChild(itemData)
        itemData.registerParent(parent_data)

    def depth(self, row):
        sanitized_row = [self.sanitizeCell(cell) for cell in row]
        for i, sanitized_cell in enumerate(sanitized_row):
            if sanitized_cell:
                return i
            if i >= self.maxDepth:
                break
        return -1

    def extractMeta(self, row, thisDepth):
        # return [row[thisDepth+i*self.maxDepth]for i in range(self.meta_width)]
        meta = [''] * self.meta_width
        if row:
            for i in range(self.meta_width):
                try:
                    meta[i] = row[thisDepth + i * self.maxDepth]
                except IndexError as exc:
                    self.registerError(
                        "could not get meta[{}] | {}".format(i, exc))
        return meta

    def isTaxoDepth(self, depth):
        return depth < self.taxoDepth and depth >= 0

    def isItemDepth(self, depth):
        return depth >= self.taxoDepth and depth < self.maxDepth

    def getNewObjContainer(self, all_data, **kwargs):
        container = super(CSVParse_Tree, self).getNewObjContainer(
            all_data, **kwargs)
        if self.DEBUG_MRO:
            self.registerMessage(' ')
        depth = kwargs['depth']
        assert depth is not None, "depth should be available to CSVParse_Tree.getNewObjContainer"
        if self.isTaxoDepth(depth):
            container = self.taxoContainer
        else:
            assert \
                self.isItemDepth(depth), \
                "sanity check: depth should be either taxo or item: %s" % depth
            container = self.itemContainer
        return container

    def getKwargs(self, all_data, container, **kwargs):
        kwargs = super(CSVParse_Tree, self).getKwargs(
            all_data, container, **kwargs)
        assert issubclass(container, ImportTreeObject)

        # sanity check kwargs has been called with correct arguments
        for key in ['row', 'rowcount']:
            assert key in kwargs

        try:
            depth = kwargs['depth']
            assert depth is not None
        except (AssertionError, KeyError):
            kwargs['depth'] = self.depth(kwargs['row'])
        if self.DEBUG_TREE:
            self.registerMessage("depth: {}".format(kwargs['depth']))
        try:
            meta = kwargs['meta']
            assert meta is not None
        except (AssertionError, KeyError):
            kwargs['meta'] = self.extractMeta(kwargs['row'], kwargs['depth'])
        if self.DEBUG_TREE:
            self.registerMessage("meta: {}".format(kwargs['meta']))

        try:
            stack = kwargs.pop('stack', None)
            # stack = kwargs['stack']
            # del kwargs['stack']
            assert stack is not None
        except (AssertionError):
            self.refreshStack(kwargs['rowcount'], kwargs[
                              'row'], kwargs['depth'])
            stack = self.stack
        assert isinstance(stack, ImportStack)
        if self.DEBUG_TREE:
            self.registerMessage("stack: {}".format(stack))

        parent = stack.getTop()
        if parent is None:
            parent = self.rootData
        if self.DEBUG_TREE:
            self.registerMessage("parent: {}".format(parent))
        kwargs['parent'] = parent

        # sanity check
        for key in ['meta', 'parent', 'depth']:
            assert kwargs[key] is not None
        return kwargs

    def newObject(self, rowcount, **kwargs):
        kwargs['row'] = kwargs.get('row', [])
        if self.DEBUG_TREE:
            self.registerMessage(u"new tree object! rowcount: %d, row: %s, kwargs: %s" %
                                 (rowcount, unicode(kwargs['row']), unicode(kwargs)))

        try:
            depth = kwargs['depth']
            assert depth is not None
        except:
            depth = self.depth(kwargs['row'])
            kwargs['depth'] = depth
        if self.DEBUG_TREE:
            self.registerMessage("depth: %d" % (depth))
    #
    #     # try:
    #     #     meta = kwargs['meta']
    #     #     assert meta is not None
    #     # except:
    #     #     meta = self.extractMeta(kwargs['row'], depth)
    #     # finally:
    #     #     kwargs['meta'] = meta
    #     # if self.DEBUG_TREE:
    #     #     self.registerMessage("meta: {}".format(meta))
    #
    #     # try:
    #     #     stack = kwargs.pop('stack', None)
    #     #     # stack = kwargs['stack']
    #     #     # del kwargs['stack']
    #     #     assert stack is not None
    #     # except (AssertionError):
    #     #     self.refreshStack(rowcount, kwargs['row'], depth)
    #     #     stack = self.stack
    #     # assert isinstance(stack, ImportStack)
    #     # if self.DEBUG_TREE:
    #     #     self.registerMessage("stack: {}".format(stack))
    #     #
    #     # parent = stack.getTop()
    #     # if parent is None: parent = self.rootData
    #     # if self.DEBUG_TREE:
    #     #     self.registerMessage("parent: {}".format(parent))
    #     # kwargs['parent'] = parent
    #
        return super(CSVParse_Tree, self).newObject(rowcount, **kwargs)

    def refreshStack(self, rowcount, row, thisDepth):
        try:
            assert thisDepth >= 0, "stack should not be broken"
        except AssertionError as exc:
            raise UserWarning(str(exc))
        del self.stack[thisDepth:]
        for depth in range(len(self.stack), thisDepth):
            layer = self.newObject(rowcount, row=row, depth=depth)
            self.stack.append(layer)
            # self.initializeObject(layer)
        assert len(
            self.stack) == thisDepth, "stack should have been properly refreshed"

    def refreshStackFromObject(self, object_data):
        assert isinstance(object_data, ImportTreeObject)
        return self.refreshStack(
            object_data.rowcount, object_data.row, object_data.depth)

    def processObject(self, object_data):
        assert isinstance(self.stack, ImportStack)
        oldstack = self.stack[:]
        assert isinstance(
            oldstack, ImportStack), 'stack should be ImportStack not %s' % oldstack.__class__.__name__
        self.refreshStackFromObject(object_data)
        assert isinstance(
            self.stack, ImportStack), 'stack should be ImportStack not %s' % self.stack.__class__.__name__
        assert oldstack == self.stack, 'self.stack (%s) is inconsistent with %s' % (
            oldstack.display(), self.stack.display())
        self.stack.append(object_data)
        super(CSVParse_Tree, self).processObject(object_data)

    def verifyItem(self, itemData):
        index = self.itemIndexer(itemData)
        item_id = id(itemData)
        lookup_data = self.items[index]
        lookup_id = id(lookup_data)
        assert item_id == lookup_id, "item has deviated from its place in items"

    # def analyseFile(self, file_name):
    #     super(CSVParse_Tree, self).analyseFile(file_name)

    def findTaxo(self, taxoData):
        response = None
        for key in [self.taxoContainer.rowcountKey]:
            value = taxoData.get(key)
            if value:
                for taxo in self.taxos:
                    if taxo.get(key) == value:
                        response = taxo
                        return response
        return response

    def getItems(self):
        exc = DeprecationWarning("Use .items instead of .getItems()")
        self.registerError(exc)
        return self.items

    def getTaxos(self):
        exc = DeprecationWarning("use .taxos instead of .getTaxos()")
        self.registerError(exc)
        return self.taxos
