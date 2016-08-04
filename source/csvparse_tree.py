from csvparse_abstract import CSVParse_Base, ImportObject
from collections import OrderedDict

class ImportTreeObject(ImportObject):
    _isRoot = False
    _isItem = False
    _isTaxo = False

    def __init__(self, data, rowcount, row, depth=-1, meta=None, parent=None, **kwargs):
        super(ImportTreeObject, self).__init__(data, rowcount, row)
        if not isinstance(self, ImportTreeRoot):
            assert all([
                depth is not None and depth >= 0,
                meta is not None,
                parent is not None
            ])
        self.setDepth(depth)
        self._meta = meta
        if parent:
            self._parent = parent
            parent.registerChild(self)
        self.children = OrderedDict()
        self.childIndexer = self.getObjectRowcount
        self.processMeta()
        self.verifyMeta()

    @classmethod
    def fromImportObject(cls, objectData, depth, meta, parent):
        assert isinstance(objectData, ImportObject)
        row = objectData.row
        rowcount = objectData.rowcount
        return cls(objectData, rowcount, row, depth, meta, parent)

    @property
    def isItem(self): return self._isItem

    @property
    def isTaxo(self): return self._isTaxo

    @property
    def isRoot(self): return self._isRoot

    @property
    def meta(self): return self._meta

    @property
    def parent(self): return self._parent

    def processMeta(self): pass
    def verifyMeta(self): pass

    def getIdentifierDelimeter(self):
        return "=" * self.getDepth()

    def getParent(self):
        return self.parent

    def getAncestors(self):
        "gets all ancestors not including self or root"
        this = self.getParent()
        ancestors = []
        while this and not this.isRoot:
            ancestors.insert(0, this)
            this = this.getParent()
        return ancestors

    def getTaxoAncestors(self):
        ancestors = self.getAncestors()
        return filter( lambda x: x.isTaxo, ancestors)

    def getAncestorKey(self, key):
        ancestors = self.getAncestors()
        return [ancestor[key] for ancestor in ancestors]

    def registerChild(self, childData):
        assert childData, "childData must be valid"
        self.registerAnything(
            childData,
            self.children,
            indexer = self.childIndexer,
            singular = True,
            # resolver = self.passiveResolver,
            registerName = 'parent'
        )

    def getChildren(self):
        return self.children.values()

    def getSiblings(self):
        return self.getParent().getChildren()

    def setDepth(self, depth):
        assert(isinstance(depth, int))
        self.depth = depth

#do we need these?

    def getDepth(self):
        return self.depth

    def getMeta(self):
        return self.meta

class ImportTreeRoot(ImportTreeObject):
    _isRoot = True

    def __init__(self):
        data = OrderedDict()
        rowcount = -1
        row = []
        super(ImportTreeRoot, self).__init__(data, rowcount, row)

class ImportTreeItem(ImportTreeObject):
    _isItem = True

    def getIdentifierDelimeter(self):
        return super(ImportTreeItem, self).getIdentifierDelimeter() + '>'

    def getItemAncestors(self):
        ancestors = self.getAncestors()
        return filter( lambda x: x.isItem, ancestors)

class ImportTreeTaxo(ImportTreeObject):
    _isTaxo = True

    def getIdentifierDelimeter(self):
        return super(ImportTreeTaxo, self).getIdentifierDelimeter() + '#'


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
            '[',
            ','.join([str(x.index) for x in self]),
            ']'
        ])

    def display(self):
        out = "\n"
        for objectData in self:
            try:
                out += objectData.getIdentifier() + "\n"
            except:
                out += repr(objectData) + "\n"
        return out

    def copy(self):
        return ImportStack(self[:])

class CSVParse_Tree(CSVParse_Base):
    objectContainer = ImportTreeObject
    rootContainer   = ImportTreeRoot
    itemContainer   = ImportTreeItem
    taxoContainer   = ImportTreeTaxo

    def __init__(self, cols, defaults, taxoDepth, itemDepth, metaWidth):
        self.taxoDepth = taxoDepth
        self.itemDepth = itemDepth
        self.maxDepth  = taxoDepth + itemDepth
        self.metaWidth = metaWidth
        self.itemIndexer = self.getObjectRowcount
        self.taxoIndexer = self.getObjectRowcount
        super(CSVParse_Tree, self).__init__(cols, defaults)

        # if self.DEBUG_TREE:
        #     print "TREE initializing: "
        #     print "-> taxoDepth: ", self.taxoDepth
        #     print "-> itemDepth: ", self.itemDepth
        #     print "-> maxDepth: ", self.maxDepth
        #     print "-> metaWidth: ", self.metaWidth


    def clearTransients(self):
        super(CSVParse_Tree, self).clearTransients()
        self.items = OrderedDict()
        self.taxos = OrderedDict()
        self.stack = ImportStack()
        self.rootData = self.rootContainer()

    def assignParent(self, parentData = None, itemData = None):
        if not parentData: parentData = self.rootData
        parentData.registerChild(itemData)
        itemData.registerParent(parentData)

    def registerItem(self, itemData):
        assert itemData.isItem
        self.registerAnything(
            itemData,
            self.items,
            indexer = self.itemIndexer,
            singular = True,
            registerName = 'items'
        )

    def registerTaxo(self, taxoData):
        assert taxoData.isTaxo
        self.registerAnything(
            taxoData,
            self.taxos,
            indexer = self.taxoIndexer,
            singular = True,
            # resolver = self.passiveResolver,
            registerName = 'taxos',
        )

    def registerObject(self, objectData):
        super(CSVParse_Tree, self).registerObject(objectData)
        if objectData.isItem:
            self.registerItem(objectData)
        if objectData.isTaxo:
            self.registerTaxo(objectData)

    def depth(self, row): #overridden by child classes
        return 0

    def extractMeta(self, row, thisDepth):
        # return [row[thisDepth+i*self.maxDepth]for i in range(self.metaWidth)]
        meta = [''] * self.metaWidth
        if row:
            for i, m in enumerate(meta):
                try:
                    meta[i] = row[thisDepth + i*self.maxDepth]
                except IndexError as e:
                    self.registerError("could not get meta[{}] | {}".format(i, e))
        return meta

    def isTaxoDepth(self, depth):
        return depth < self.taxoDepth and depth >= 0

    def isItemDepth(self, depth):
        return depth >= self.taxoDepth and depth < self.maxDepth

    def getContainer(self, allData, **kwargs):
        depth = kwargs['depth']
        assert depth is not None, "depth should be available to CSVParse_Tree.getContainer"
        if self.isTaxoDepth(depth):
            container = self.taxoContainer
        else:
            assert self.isItemDepth(depth), "sanity check: depth is either taxo or item"
            container = self.itemContainer
        return container

    def getKwargs(self, allData, container, **kwargs):
        kwargs = super(CSVParse_Tree, self).getKwargs(allData, container, **kwargs)
        assert issubclass(container, ImportTreeObject)
        for key in ['meta', 'parent']:
            assert kwargs[key] is not None
        return kwargs

    def newObject(self, rowcount, row, **kwargs):
        # self.registerMessage(u"new tree object! rowcount: %d, row: %s, kwargs: %s"%\
        #                      (rowcount, unicode(row), unicode(kwargs)))

        try:
            depth = kwargs['depth']
            assert depth is not None
        except:
            depth = self.depth( row )
            kwargs['depth'] = depth
        # self.registerMessage("depth: %d"%(depth))

        try:
            meta = kwargs['meta']
            assert meta is not None
        except:
            meta = self.extractMeta(row, depth)
            kwargs['meta'] = meta
        # self.registerMessage("meta: {}".format(meta))

        try:
            stack = kwargs['stack']
            del kwargs['stack']
            assert stack is not None
        except:
            self.refreshStack(rowcount, row, depth)
            stack = self.stack
        assert isinstance(stack, ImportStack)
        self.registerMessage("stack: {}".format(stack))

        parent = stack.getTop()
        if parent is None: parent = self.rootData
        self.registerMessage("parent: {}".format(parent))
        kwargs['parent'] = parent

        return super(CSVParse_Tree, self).newObject(rowcount, row, **kwargs)

    def refreshStack(self, rowcount, row, thisDepth):
        try:
            assert thisDepth >= 0, "stack should not be broken"
        except AssertionError as e:
            raise UserWarning(str(e))
        del self.stack[thisDepth:]
        for depth in range(len(self.stack), thisDepth):
            layer = self.newObject(rowcount, row, depth=depth)
            self.stack.append(layer)
            # self.initializeObject(layer)
        assert len(self.stack) == thisDepth , "stack should have been properly refreshed"

    def refreshStackFromObject(self, objectData):
        assert isinstance(objectData, ImportTreeObject)
        return self.refreshStack(objectData.rowcount, objectData.row, objectData.getDepth() )

    def processObject(self, objectData):
        oldstack = self.stack[:]
        self.refreshStackFromObject(objectData)
        assert oldstack == self.stack
        self.stack.append(objectData)
        super(CSVParse_Tree, self).processObject(objectData)

    def verifyItem(self, itemData):
        index = self.itemIndexer(itemData)
        itemID = id(itemData)
        lookupData = self.items[index]
        lookupID = id(lookupData)
        assert itemID == lookupID, "item has deviated from its place in items"

    # def analyseFile(self, fileName):
    #     super(CSVParse_Tree, self).analyseFile(fileName)

    def getItems(self):
        return self.items

    def getTaxos(self):
        return self.taxos
