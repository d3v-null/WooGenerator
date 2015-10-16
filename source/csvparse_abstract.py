import csv
from collections import OrderedDict
import pprint

DEBUG = True
DEBUG_PARSER = True

class Registrar:
    def __init__(self):
        self.objectIndexer = id
        self.conflictResolver = self.passiveResolver

    def resolveConflict(self, new, old, index, registerName = ''):
        self.registerError("Object [index: %s] already exists in register %s"%(index, registerName))

    def getObjectRowcount(self, objectData):
        return objectData.getRowcount()

    def passiveResolver(self, new, old, index, registerAnything):
        pass

    def registerAnything(self, thing, register, indexer = None, resolver = None, singular = True, registerName = ''):
        if resolver is None: resolver = self.conflictResolver
        if indexer is None: indexer = self.Indexer
        index = None
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

    def registerError(self, error, data = None):
        index = self.getIndex(data) if data else ""
        error_string = str(error)
        if DEBUG: print "%15s ! %s" % (index, error_string)
        self.registerAnything(
            error_string, 
            self.errors, 
            index, 
            singular = False,
            registerName = 'errors'
        )

class ImportObject(OrderedDict, Registrar):
    """docstring for ImportObject"""
    def __init__(self, data, rowcount, row):
        super(ImportObject, self).__init__(data)
        Registrar.__init__(self)
        self['rowcount'] = rowcount
        self.row = row
        self.initialized = False

    def getRowcount(self):
        return self['rowcount']

    def getRow(self):
        return self.row

    def getIndex(self):
        return self.getRowcount()

    def __str__(self):
        return (str) ( type(self) ) + (str)( self.getIndex() )     

class listUtils:
    def combineLists(a, b):
        if not a:
            return b if b else []
        if not b: return a
        return list(set(a) | set(b))

    def combineOrderedDicts(a, b):
        if not a:
            return b if b else OrderedDict()
        if not b: return a
        for key, value in a.items():
            b[key] = value
        return b

    def filterUniqueTrue(a):
        b = []
        for i in a:
            if i and i not in b:
                b.append(i)
        return b

class CSVParse_Base(object, Registrar):
    """docstring for CSVParse_Base"""

    def __init__(self, cols, defaults ):
        super(CSVParse_Base, self).__init__()
        Registrar.__init__(self)

        extra_cols = []
        extra_defaults = OrderedDict()

        self.cols = listUtils.combineLists( cols, extra_cols )
        self.defaults = listUtils.combineOrderedDicts( defaults, extra_defaults )
        self.pp = pprint.PrettyPrinter(indent=2, depth=2)
        self.indexSingularity = True
        self.objectIndexer = self.getObjectRowcount
        self.objectContainer = ImportObject

    def clearTransients(self):
        self.errors = OrderedDict()
        self.indices = OrderedDict()
        self.objects = OrderedDict()

    def registerObject(self, objectData):
        self.registerAnything(
            objectData, 
            self.objects, 
            self.objectIndexer,
            singular = True,
            registerName = 'objects'
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

    def sanitizeCell(self, cell):
        return cell   
             
    def getRowData(self, row):
        rowData = OrderedDict()
        for col in self.cols:
            retrieved = self.retrieveColFromRow(col, row)
            if retrieved is not None and retrieved is not '': 
                rowData[col] = self.sanitizeCell(retrieved)
        return rowData

    def newObject(self, rowcount, row):
        defaultData = self.defaults.items()
        rowData = self.getRowData(row)
        allData = listUtils.combineOrderedDicts(rowData, defaultData)
        return self.objectContainer(allData, rowcount, row)

    def initializeObject(self, objectData):
        pass

    def processObject(self, objectData):
        pass

    # def analyseObject(self, objectData):
        # self.initializeObject(objectData)
        # objectData.initialized = True;
        # self.processObject(objectData)
        # self.registerObject(objectData)

    def analyseFile(self, fileName):
        # if DEBUG_PARSER: print "Analysing file: ", self.filePath
        self.clearTransients()

        with open(fileName) as filePointer:
            csvreader = csv.reader(filePointer, strict=True)
            objects = []
            for rowcount, row in enumerate(csvreader):
                if not self.indices :
                    self.analyseHeader(row)
                    continue
                try:
                    objectData = self.newObject( rowcount, row )
                except Exception as e:
                    self.registerError(str(e))
                else:
                    try:
                        self.analyseObject(objectData) 
                    except Exception as e:
                        self.registerError(str(e), objectData)
                    else:
                        try:
                            self.registerObject(objectData)
                        except Exception as e:
                            self.registerError(str(e), objectData)
                            
            return objects
        return None

    def getObjects(self):
        return self.objects
