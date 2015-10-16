from csvparse_abstract import CSVParse_Base, ImportObject
from collections import OrderedDict

DEBUG_TREE = False
DEBUG_TREE = True

class ImportTreeBase(ImportObject):
    def __init__(self, data, rowcount, row, depth, meta=None, parent=None):
        super(ImportTreeBase, self).__init__(data, rowcount, row)
        self.setDepth(depth)
        self.meta = meta
        self.parent = parent
        self.children = OrderedDict()
        self.parentIndexer = self.getObjectRowcount
        self.childIndexer = self.getObjectRowcount
        self.processMeta()

    def getParent(self):
        return self.parent

    def getAncestors(self):
        "gets all ancestors not including self or root"
        this = self.getParent()
        ancestors = []
        while this and not this.isRoot():
            ancestors.append(this)
        return ancestors

    def getAncestorKey(self, key):
        ancestors = self.getAncestors()
        return [ancestor[key] for ancestor in ancestors]

    def registerChild(self, childData):
        assert childData, "childData must be valid"
        self.registerAnything(
            childData, 
            self.getChildren(),
            indexer = self.childIndexer,
            singular = True,
            # resolver = self.passiveResolver,
            registerName = 'parent'
        )

    def getChildren(self):
        return self.children

    def setDepth(self, depth):
        assert(isinstance(depth, int))
        self.depth = depth

    def getDepth(self):
        return self.depth

    def getMeta(self):
        return self.meta

    def processMeta(self, stack):
        pass

    def isItem(self): return False
    def isTaxo(self): return False
    def isRoot(self): return False

class ImportTreeRoot(ImportTreeBase):
    def __init__(self):
        data = OrderedDict()
        rowcount = -1
        row = []
        depth = -1
        meta = None
        parent = None
        super(ImportTreeRoot, self).__init__(data, rowcount, row, depth, meta, parent)

    def isRoot(self): return True

class ImportTreeItem(ImportTreeBase):
    """docstring for ImportTreeItem"""
    def __init__(self, *args):
        super(ImportTreeItem, self).__init__(*args)

    def isItem(self): return True

class ImportTreeTaxo(ImportTreeBase):
    """docstring for ImportTreeTaxo"""
    def __init__(self, *args):
        super(ImportTreeTaxo, self).__init__(*args)

    def isTaxo(self): return True

class ImportStack(list):
    def topHasParent(self):
        return len(self) > 1

    def getTopParent(self):
        if self.topHasParent():
            return self[-2]
        else:
            return None

    def isEmpty(self):
        return len(self) is not 0

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

class CSVParse_Tree(CSVParse_Base):

    """docstring for CSVParse_Tree"""
    def __init__(self, cols, defaults, taxoDepth, itemDepth, metaWidth):
        self.taxoDepth = taxoDepth
        self.itemDepth = itemDepth
        self.maxDepth  = taxoDepth + itemDepth
        self.metaWidth = metaWidth
        super(CSVParse_Tree, self).__init__(cols, defaults)
        self.itemContainer = ImportTreeItem
        self.itemIndexer = self.getObjectRowcount
        self.taxoContainer = ImportTreeTaxo
        self.taxoIndexer = self.getObjectRowcount
        self.rootContainer = ImportTreeRoot

        if DEBUG_TREE:
            print "TREE initializing: "
            print "-> taxoDepth: ", self.taxoDepth
            print "-> itemDepth: ", self.itemDepth
            print "-> maxDepth: ", self.maxDepth
            print "-> metaWidth: ", self.metaWidth

        
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
        self.registerAnything(
            itemData, 
            self.items, 
            self.itemIndexer,
            singular = True,
            registerName = 'items'
        )    

    def registerTaxo(self, taxoData):
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
        if objectData.isItem():
            self.registerItem(objectData)
        if objectData.isTaxo():
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
                    self.registerError("could not get meta["+str(i)+"] | "+str(e))
        return meta

    def isTaxoDepth(self, depth):
        return depth < self.taxoDepth and depth >= 0

    def isItemDepth(self, depth):
        return depth >= self.taxoDepth and depth < self.maxDepth    

    def newObject(self, rowcount, row, depth=None, stack=None):
        if depth is None: depth = self.depth( row )
        if stack is None: stack = self.stack
        objectData = super(CSVParse_Tree, self).newObject(rowcount, row)
        meta = self.extractMeta(row, depth)
        parent = self.stack.getTop()
        if parent is None: parent = self.rootData
        if self.isTaxoDepth(depth):
            container = self.taxoContainer
        else:
            assert self.isItemDepth(depth), "sanity check"
            container = self.itemContainer
        return container(objectData, rowcount, row, depth, meta, parent)

    def processMeta(self, itemData): #overridden later
        pass

    def initializeObject(self, objectData):
        self.processMeta(objectData)
        super(CSVParse_Tree, self).initializeObject(objectData)
        parentData = self.getStackParent()
        self.assignParent(parentData, objectData)

    # def processObject(self, objectData):
    #     pass

    def refreshStack(self, objectData):
        thisDepth = objectData.getDepth()
        assert thisDepth >= 0, "stack should not be broken"

        del self.stack[thisDepth:]
        for depth in range(len(self.stack), thisDepth):
            layer = self.newObject(objectData.getRowcount(), objectData.getRow(), depth)
            self.stack.append(layer)
            self.initializeObject(layer)

        assert len(self.stack) == thisDepth , "stack should have been properly refreshed"
        self.stack.append(objectData)

    def analyseObject(self, objectData):
        self.refreshStack(objectData)
        super(CSVParse_Tree, self).analyseObject(objectData)

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
