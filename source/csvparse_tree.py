from csvparse_abstract import CSVParse_Base, ImportItem
from collections import OrderedDict

DEBUG_TREE = False
# DEBUG_TREE = True

class ImportTreeMixin:
    def getDepth(self):
        return self.get('thisDepth')

    def setDepth(self, depth):
        assert(isinstance(depth, int))
        self['thisDepth'] = depth

class ImportTreeItem(ImportItem, ImportTreeMixin):
    """docstring for ImportTreeItem"""
    def __init__(self, arg):
        super(ImportTreeItem, self).__init__(arg)

    def getSum(self):
        return self.get('itemsum')

class ImportTreeTaxo(ImportItem, ImportTreeMixin):
    """docstring for ImportTreeTaxo"""
    def __init__(self, arg):
        super(ImportTreeTaxo, self).__init__(arg)
        
    def getSum(self):
        return self.get('taxosum')


class CSVParse_Tree(CSVParse_Base):

    """docstring for CSVParse_Tree"""
    def __init__(self, cols, defaults, taxoDepth, itemDepth, metaWidth):
        try:
            assert( self.itemContainer )
        except :
            self.itemContainer = ImportTreeItem
        try:
            assert( self.taxoContainer )
        except :
            self.taxoContainer = ImportTreeTaxo
        self.taxoDepth = taxoDepth
        self.itemDepth = itemDepth
        self.maxDepth  = taxoDepth + itemDepth
        self.metaWidth = metaWidth
        super(CSVParse_Tree, self).__init__(cols, defaults)

        if DEBUG_TREE:
            print "TREE initializing: "
            print "-> taxoDepth: ", self.taxoDepth
            print "-> itemDepth: ", self.itemDepth
            print "-> maxDepth: ", self.maxDepth
            print "-> metaWidth: ", self.metaWidth

        
    def clearTransients(self):
        super(CSVParse_Tree, self).clearTransients()
        self.taxos = OrderedDict()
        self.stack = []
        self.rootData = self.newData()

    # def resolveConflict(self, newItem, oldItem):
    #     return self.combineOrderedDicts(oldItem, newItem)

    def getSum(self, itemData):
        if self.isTaxo(itemData):
            return itemData['taxosum']
        elif self.isItem(itemData):
            return itemData['itemsum']

    def assignParent(self, parentData = None, itemData = None):
        if not parentData: parentData = self.rootData
        assert itemData
        if not parentData.get('children'):
            parentData['children'] = OrderedDict()

        self.registerAnything(
            itemData, 
            parentData['children'],
            indexer = self.getRowcount,
            singular = True,
            # resolver = self.passiveResolver,
            registerName = 'parent'
        )

        if not itemData.get('parents'):
            itemData['parents'] = {}

        self.registerAnything(
            parentData,
            itemData['parents'],
            indexer = self.getRowcount,
            singular  = True,
            registerName = 'child'
        )
    
    def registerTaxo(self, itemData):
        self.registerAnything(
            itemData, 
            self.taxos, 
            indexer = self.getRowcount,
            singular = True,
            # resolver = self.passiveResolver,
            registerName = 'taxos',
        )

    def depth(self, row): #overridden by child classes
        pass

    def getMeta(self, row, thisDepth):
        # return [row[thisDepth+i*self.maxDepth]for i in range(self.metaWidth)]
        meta = [''] * self.metaWidth
        if row:
            for i, m in enumerate(meta):
                try:
                    meta[i] = row[thisDepth + i*self.maxDepth]
                except IndexError as e:
                    self.registerError("could not get meta["+str(i)+"] | "+str(e))
        return meta

    def hasParent(self, itemData, stack=None):
        if not stack: stack = self.stack
        return len(stack) > 1

    def getParent(self, itemData, stack=None):
        if not stack: stack = self.stack
        if self.hasParent(itemData, stack):
            return stack[-2]
        else:
            return None

    def sanitizeCell(self, cell):
        return cell

    def processMeta(self, itemData): #overridden later
        pass

    def newData(self, **kwargs):
        data = super(CSVParse_Tree, self).newData(**kwargs)
        if self.isTaxo(data):
            return self.taxoContainer(data)
        else: 
            return data

    def isTaxo(self, itemData):
        depth = itemData.getDepth()
        return depth < self.taxoDepth and depth >= 0

    def isItem(self, itemData):
        depth = itemData.getDepth()
        return depth >= self.taxoDepth and depth < self.maxDepth        

    def processTaxo(self, itemData):
        self.registerTaxo(itemData) 

    def initializeData(self, itemData, stack=None):
        if not stack: stack = self.stack
        self.processMeta(itemData)
        super(CSVParse_Tree, self).initializeData(itemData)
        if self.isTaxo(itemData):
            self.processTaxo(itemData) 
        parentData = self.getParent(itemData, stack)
        self.assignParent(parentData, itemData)

    def analyseRow(self, row, itemData):
        if DEBUG_TREE: 
            print "TREE started analysing row: ", self.getRowcount(itemData)

        #refresh depth and stack
        thisDepth = self.depth(row)
        assert thisDepth >= 0, "stack should not be broken"
        itemData.setDepth(thisDepth) 

        del self.stack[thisDepth:]
        for depth in range(len(self.stack), thisDepth):
            layer = self.newData( 
                thisDepth = depth,
                rowcount = itemData['rowcount'],
                meta =  self.getMeta(None, depth),
            )
            self.stack.append(layer)
            self.initializeData(layer, self.stack)

        assert len(self.stack) == thisDepth , "stack should have been properly refreshed"
        self.stack.append(itemData)

        #fill metadata
        itemData['meta'] = self.getMeta(row, thisDepth)
        #fill the rest
        self.fillData(itemData, row)

        self.initializeData(itemData)

        if DEBUG_TREE: 
            print "TREE finished analysing row: ", self.getSum(itemData)

        return itemData

    def analyseFile(self, fileName):
        super(CSVParse_Tree, self).analyseFile(fileName)

    def getTaxos(self):
        return self.taxos.values()
