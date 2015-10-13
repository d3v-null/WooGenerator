import csv
from collections import OrderedDict
import pprint

DEBUG = True
DEBUG_PARSER = True

class CSVParse_Base(object):
    """docstring for CSVParse_Base"""

    def __init__(self, cols, defaults ):
        super(CSVParse_Base, self).__init__()
        
        extra_cols = []
        extra_defaults = OrderedDict()

        self.cols = self.combineLists( cols, extra_cols )
        self.defaults = self.combineOrderedDicts( defaults, extra_defaults )
        self.pp = pprint.PrettyPrinter(indent=2, depth=2)
        self.indexSingularity = True

        # if DEBUG_PARSER:
        #     print "Initializing: "
        #     self.pp.pprint({
        #         "cols":self.cols,
        #         "defs":self.defaults
        #     })

        self.clearTransients()

    def clearTransients(self):
        self.errors = OrderedDict()
        self.items = OrderedDict()
        self.indices = OrderedDict()

    def combineLists(self, a, b):
        if not a and not b: return []
        if not a: return b
        if not b: return a
        return list(set(a) | set(b))

    def combineOrderedDicts(self, a, b):
        if not a and not b: return OrderedDict()
        if not a: return b
        if not b: return a
        for key, value in a.items():
            b[key] = value
        return b

    def getRowcount(self, itemData):
        try:
            count = itemData['rowcount']
            if count: return count
        except:
            pass
        return None

    def getIndex(self, itemData):
        return self.getRowcount(itemData)

    def resolveConflict(self, newItem, oldItem, index, registerName = ''):
        self.registerError("Item [index: %s] already exists in register %s"%(index, registerName))

    def passiveResolver(self, newItem, oldItem, index, registerAnything):
        pass

    def registerAnything(self, thing, register, indexer = None, resolver = None, singular = True, registerName = ''):
        if not resolver: resolver = self.resolveConflict
        if not indexer: indexer = self.getIndex
        try:
            if callable(indexer):
                index = indexer(thing)
            else: 
                index = indexer
            assert index.__hash__, "Index must be hashable"
            assert index == index, "index must support eq"
        except AssertionError as e:
            raise Exception("Indexer [%s] produced invalid index: %s | %s" % (indexer.__name__, repr(index), str(e)))
        else:
            # if not register:
            #     register = OrderedDict()
            if singular:
                if index not in register:
                    register[index] = thing
                else:
                    resolver(thing, register[index], index, registerName)
            else:
                if index not in register:
                    register[index] = []
                register[index].append(thing)
        # print "registered", thing

    def registerError(self, error, itemData = None):
        index = self.getIndex(itemData)
        error_string = str(error)
        if DEBUG: print "%15s ! %s" % (index, error_string)
        self.registerAnything(
            error_string, 
            self.errors, 
            index, 
            singular = False,
            registerName = 'errors'
        )


    def registerItem(self, itemData):
        self.registerAnything(
            itemData, 
            self.items, 
            self.getRowcount,
            singular = True,
            registerName = 'items'
        )

    def analyseHeader(self, row):
        for col in self.cols:
            try:
                self.indices[col] = row.index(col)
                if DEBUG: print "indices [%s] = %d" % (col, row.index(col))
            except ValueError as e:
                self.registerError('Could not find index of '+str(col)+" | "+str(e) )

    def retrieveColFromRow(self, col, row):
        # if DEBUG_PARSER: print "retrieveColFromRow | col: ", col
        try:
            index = self.indices[col]
        except KeyError as e:
            self.registerError('No such column'+str(col)+' | '+str(e))
            return None
        try:
            # if DEBUG: print "row [%s] = %s" % (index, row[index])
            return row[index]
        except Exception as e:
            self.registerError('Could not retrieve '+str(col)+' from row['+str(index)+'] | '+str(e))
            return None

    def newData(self, **kwargs):
        newData = OrderedDict(self.defaults.items())
        for key, val in kwargs.items():
            newData[key] = val
        return newData

    def getRowData(self, row, cols):
        if not cols: cols = self.cols
        rowData = OrderedDict()
        for col in cols:
            retrieved = self.retrieveColFromRow(col, row)
            if retrieved is not None and retrieved is not '': 
                rowData[col] = self.sanitizeCell(retrieved)

    def processItem(self, itemData):
        self.registerItem(itemData)

    def isItem(self, itemData):
        return True

    def fillData(self, itemData, row):
        for col in self.cols:
            # print "retrieving %s from row" % col
            retrieved = self.retrieveColFromRow(col, row)
            # print " -> retrieved %s" % str(retrieved)
            # if retrieved is not None and retrieved is not '': 
            if retrieved: 
                itemData[col] = self.sanitizeCell(retrieved)

    def initializeData(self, itemData):
        if self.isItem(itemData):
            self.processItem(itemData)        

    def analyseRow(self, row, itemData): #overridden by child classes
        if DEBUG_PARSER: 
            print "BASE is analysing row: "
            self.pp.pprint(itemData.items())
        self.fillData(itemData, row)
        self.initializeData(itemData)
        return itemData

    def analyseFile(self, fileName):
        # if DEBUG_PARSER: print "Analysing file: ", self.filePath
        with open(fileName) as filePointer:
            csvreader = csv.reader(filePointer, strict=True)

            for rowcount, row in enumerate(csvreader):
                if not self.indices :
                    self.analyseHeader(row)
                    continue
                itemData = self.newData( rowcount = rowcount)
                try:
                    itemData = self.analyseRow(row, itemData)
                except AssertionError as e:
                    self.registerError(str(e), itemData)

    def getItems(self):
        return self.items.values()
