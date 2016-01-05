import pprint
from collections import OrderedDict
from utils import debugUtils, listUtils
from tabulate import tabulate
import bisect
import csv

DEBUG = False
DEBUG_PARSER = False

class Registrar:
    messages = OrderedDict()
    errors = OrderedDict()
    warnings = OrderedDict()

    def __init__(self):
        self.objectIndexer = id
        self.conflictResolver = self.passiveResolver

    def resolveConflict(self, new, old, index, registerName = ''):
        self.registerError("Object [index: %s] already exists in register %s"%(index, registerName))

    def getObjectRowcount(self, objectData):
        return objectData.rowcount

    def getObjectIndex(self, objectData):
        return objectData.index

    def passiveResolver(*args):
        pass

    def exceptionResolver(self, new, old, index, registerName = ''):
        raise Exception("could not register %s in %s. Duplicate index: %s" % (str(new), registerName, index) )

    def warningResolver(self, new, old, index, registerName = ''):
        try:
            self.exceptionResolver(new, old, index, registerName)
        except Exception as e:
            self.registerError(e, new )

    @classmethod
    def stringAnything(self, index, thing, delimeter):
        return "%31s %s %s" % (index, delimeter, thing)

    @classmethod
    def printAnything(self, index, thing, delimeter):
        print Registrar.stringAnything(index, thing, delimeter)

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
        if data:
            try:
                index = data.index
            except:
                index = data
        else:
            index = debugUtils.getCallerProcedure()
        error_string = str(error)
        if DEBUG: Registrar.printAnything(index, error, '!')
        self.registerAnything(
            error_string, 
            self.errors, 
            index, 
            singular = False,
            registerName = 'errors'
        )

    def registerWarning(self, message, source=None):
        if source is None:
            source = debugUtils.getCallerProcedure()
        if DEBUG: Registrar.printAnything(source, message, ' ')
        self.registerAnything(
            message,
            self.warnings,
            source,
            singular = False,
            registerName = 'warnings'
        )

    def registerMessage(self, message, source=None):
        if source is None:
            source = debugUtils.getCallerProcedure()
        if DEBUG: Registrar.printAnything(source, message, ' ')
        self.registerAnything(
            message,
            self.messages,
            source,
            singular = False,
            registerName = 'messages'
        )

class ImportObject(OrderedDict, Registrar):
    def __init__(self, data, rowcount, row =[]):
        super(ImportObject, self).__init__(data)
        Registrar.__init__(self)
        self['rowcount'] = rowcount
        self._row = row

    @property
    def row(self): return self._row

    @property
    def rowcount(self): return self['rowcount']    

    @property
    def index(self): return self.rowcount   

    def getTypeName(self):
        return type(self).__name__ 

    def getIdentifierDelimeter(self):
        return ""

    def getIdentifier(self):
        return Registrar.stringAnything( self.index, "<%s>" % self.getTypeName(), self.getIdentifierDelimeter() )

    def __str__(self):
        return "%10s <%s>" % (self.index, self.getTypeName())

    def __repr__(self):
        return self.__str__()

    def __cmp__(self, other):
        if other == None:
            return -1
        if not isinstance(other, ImportObject):
            return -1  
        return cmp(self.rowcount, other.rowcount)

class ObjList(object):
    def __init__(self):
        super(ObjList, self).__init__()
        self._objList_type = 'objects'
        self._objects = []

    @property
    def objects(self):
        return self._objects

    def addObject(self, objectData):
        assert(isinstance(objectData, ImportObject))
        if(objectData not in self._objects):
            self._objects.append(objectData)

    def getKey(self, key):
        values = listUtils.filterUniqueTrue([
            obj.get(key) for obj in self.objects
        ])

        if values:
            return values[0]

    @property
    def objList_type(self):
        return self._objList_type

    def rep_str(self):
        objs = self.objects
        if(objs):
            # print "there are objects"
            cols = self.getReportCols()                
            header = [self.objList_type]
            for col, data in cols.items():
                header += [col]
            table = [header]
            for obj in objs:
                table += [[obj.index] + [obj.get(col) for col in cols.keys()]]
            # print "table", table
            return tabulate(table, headers="firstrow")
        else:
            # print "there are no objects"
            pass

    def getReportCols(self):
        return {'_row':{'label':'Row'}}

class CSVParse_Base(object, Registrar):
    objectContainer = ImportObject

    def __init__(self, cols, defaults ):
        super(CSVParse_Base, self).__init__()
        Registrar.__init__(self)

        extra_cols = []
        extra_defaults = OrderedDict()

        self.cols = listUtils.combineLists( cols, extra_cols )
        self.defaults = listUtils.combineOrderedDicts( defaults, extra_defaults )
        self.pp = pprint.PrettyPrinter(indent=2, depth=2)
        self.objectIndexer = self.getObjectRowcount
        self.clearTransients()

    def clearTransients(self):
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
        # print row
        for col in self.cols:
            if( col in row ):
                self.indices[col] = row.index(col)
            elif( '\xef\xbb\xbf'+col in row ):
                self.indices[col] = row.index('\xef\xbb\xbf'+col)
            else:
                self.registerError('Could not find index of '+str(col) )
            if DEBUG: print "indices [%s] = %d" % (col, self.indices.get(col))

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

    def getContainer(self, allData, **kwargs):
        return self.objectContainer

    def getKwargs(self, allData, container, **kwargs):
        return kwargs

    def newObject(self, rowcount, row, **kwargs):
        # self.registerMessage( 'row: {} | {}'.format(rowcount, row) )
        defaultData = OrderedDict(self.defaults.items())
        # self.registerMessage( "defaultData: {}".format(defaultData) )
        rowData = self.getRowData(row)
        # self.registerMessage( "rowData: {}".format(rowData) )
        allData = listUtils.combineOrderedDicts(rowData, defaultData)
        # self.registerMessage( "allData: {}".format(allData) )
        container = self.getContainer(allData, **kwargs)
        # self.registerMessage("container: {}".format(container.__name__))                
        kwargs = self.getKwargs(allData, container, **kwargs)
        # self.registerMessage("kwargs: {}".format(kwargs))                
        objectData = container(allData, rowcount, row, **kwargs)
        # self.registerMessage("mro: {}".format(container.mro()))                
        return objectData

    def initializeObject(self, objectData):
        pass

    def processObject(self, objectData):
        pass

    # def processObject(self, objectData):
        # self.initializeObject(objectData)
        # objectData.initialized = True;
        # self.processObject(objectData)
        # self.registerObject(objectData)

    def analyseFile(self, fileName):
        self.registerMessage("Analysing file: {}".format(fileName))
        # self.clearTransients()

        with open(fileName) as filePointer:
            try:
                sample = filePointer.read(10000)
                filePointer.seek(0)
                csvdialect = csv.Sniffer().sniff(sample)
            except Exception as e:
                if(e): pass
                # print "dialect is probably ACT"
                csv.register_dialect('act', delimiter=',', quoting=csv.QUOTE_ALL, doublequote=False, strict=True)
                csvdialect = 'act'
            # print "CSV DIALECT: "
            # print "DEL ", csvdialect.delimiter, "DBL ", csvdialect.doublequote, "ESC ", csvdialect.escapechar, "QUC ", csvdialect.quotechar, "QUT", csvdialect.quoting, "SWS ", csvdialect.skipinitialspace
            
            csvreader = csv.reader(filePointer, dialect=csvdialect, strict=True)
            objects = []
            for rowcount, row in enumerate(csvreader):
                if not self.indices :
                    self.analyseHeader(row)
                    continue
                try:
                    objectData = self.newObject( rowcount, row )
                except UserWarning as e:
                    self.registerWarning("could not create new object: {}".format(e), rowcount)
                    continue
                else:
                    if (DEBUG_PARSER): self.registerMessage("%s CREATED" % objectData.getIdentifier() )
                    pass
                try:
                    self.processObject(objectData) 
                    if (DEBUG_PARSER): self.registerMessage("%s PROCESSED" % objectData.getIdentifier() )
                except UserWarning as e:
                    self.registerError("could not process new object: {}".format(e), objectData)
                    continue
                try:
                    self.registerObject(objectData)
                    if (DEBUG_PARSER): self.registerMessage("%s REGISTERED" % objectData.getIdentifier() )
                except UserWarning as e:
                    self.registerError("could not register new object: {}".format(e), objectData)
                    continue
                            
            return objects
        return None

    def getObjects(self):
        return self.objects

if __name__ == '__main__':
    parser = CSVParse_Base( [], {})
    # parser.analyseFile('../input/export-everything-dec-23.csv')
    parser.analyseFile('../input/100-act-records.csv')
    objList = ObjList()
    print "all objects: ", parser.objects
    for obj in parser.objects.values():
        print "adding object: ", obj
        objList.addObject(obj)
        if(len(objList.objects) > 4):
            break
    print objList.rep_str()



