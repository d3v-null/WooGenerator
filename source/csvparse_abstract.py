from pprint import pprint
from collections import OrderedDict
from utils import debugUtils, listUtils, UnicodeReader, SanitationUtils, UnicodeDictWriter
from tabulate import tabulate
import csv
from coldata import ColData_User
from copy import deepcopy, copy

DEBUG = False
DEBUG_PARSER = False
DEBUG_MESSAGE = True

import os


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
        return SanitationUtils.makeSafeOutput( u"%31s %s %s" % (index, delimeter, thing) )

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
        if DEBUG_MESSAGE: Registrar.printAnything(source, message, ' ')
        self.registerAnything(
            message,
            self.messages,
            source,
            singular = False,
            registerName = 'messages'
        )

class ImportObject(OrderedDict, Registrar):

    def __init__(self, data, rowcount = None, row = None):
        super(ImportObject, self).__init__(data)
        Registrar.__init__(self)
        if rowcount is not None:
            self['rowcount'] = rowcount
        assert isinstance(self['rowcount'], int), "must specify integer rowcount"
        if row is not None:
            self._row = row
        else:
            if not '_row' in self.keys():
                self['_row'] = []

    @property
    def row(self): return self._row

    @property
    def rowcount(self): return self['rowcount']    

    @property
    def index(self): return self.rowcount   

    @staticmethod
    def getContainer():
        return ObjList

    def getTypeName(self):
        return type(self).__name__ 

    def getIdentifierDelimeter(self):
        return ""

    def getIdentifier(self):
        return Registrar.stringAnything( self.index, "<%s>" % self.getTypeName(), self.getIdentifierDelimeter() )

    def __getstate__(self): return self.__dict__
    def __setstate__(self, d): self.__dict__.update(d)
    def __copy__(self): return self.__class__(copy(super(ImportObject,self)), self.rowcount, self.row)
    def __deepcopy__(self, memodict={}): return self.__class__(deepcopy(OrderedDict(self)), self.rowcount, self.row[:])

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

class ObjList(list):
    def __init__(self, objects=None, indexer=None):
        super(ObjList, self).__init__()
        self._indexer = indexer if indexer else (lambda x: x.index)
        self._objList_type = 'objects'
        # self._objects = []
        self._indices = []
        if objects:
            self.addObjects(objects)

    @property
    def objects(self):
        return self[:]

    @property
    def objList_type(self):
        return self._objList_type

    @property
    def indices(self):
        return self._indices
    

    # def __len__(self):
    #     return len(self.objects)

    def addObject(self, objectData):
        try:
            assert(isinstance(objectData, ImportObject))
        except Exception as e:
            pprint( objectData)
            raise e
        index = self._indexer(objectData)
        if(index not in self._indices):
            self.append(objectData)
            self._indices.append(index)

    def addObjects(self, objects):
        for obj in objects:
            self.addObject(obj)

    def getKey(self, key):
        values = listUtils.filterUniqueTrue([
            obj.get(key) for obj in self.objects
        ])

        if values:
            return values[0]

    def tabulate(self, cols=None, tablefmt=None):
        objs = self.objects
        sanitizer = SanitationUtils.makeSafeOutput
        # sanitizer = (lambda x: str(x)) if tablefmt == 'html' else SanitationUtils.makeSafeOutput
        if(objs):
            # print "there are objects"
            if not cols: cols = self.getReportCols()                
            header = [self.objList_type]
            for col, data in cols.items():
                header += [col]
            table = []
            for obj in objs:
                table += [[obj.index] + [ sanitizer(obj.get(col) )or "" for col in cols.keys()]]
            # print "table", table
            return tabulate(table, headers=header, tablefmt=tablefmt)
            # print repr(table)
            # print repr(table.encode('utf8'))
            # return table.encode('utf8')
        else:
            # print "there are no objects"
            pass

    def exportItems(self, filePath, colNames, dialect = None):
        assert filePath, "needs a filepath"
        assert colNames, "needs colNames"
        assert self.objects, "meeds items"
        with open(filePath, 'w+') as outFile:
            csv.register_dialect('act_out', delimiter=',', quoting=csv.QUOTE_ALL, doublequote=False, strict=True, quotechar="\"", escapechar="`")
            dictwriter = UnicodeDictWriter(
                outFile,
                dialect = 'act_out',
                fieldnames = colNames.keys(),
                # extrasaction = 'ignore',
            )
            dictwriter.writerow(colNames)
            dictwriter.writerows(self.objects)
        print "WROTE FILE: ", filePath

    def getReportCols(self):
        return OrderedDict([
                    ('row',{'label':'Row'}),
                    ('index',{})
                ])

class CSVParse_Base(object, Registrar):
    objectContainer = ImportObject

    def __init__(self, cols, defaults ):
        super(CSVParse_Base, self).__init__()
        Registrar.__init__(self)

        extra_cols = []
        extra_defaults = OrderedDict()

        self.cols = listUtils.combineLists( cols, extra_cols )
        self.defaults = listUtils.combineOrderedDicts( defaults, extra_defaults )
        self.objectIndexer = self.getObjectRowcount
        self.clearTransients()

    def __getstate__(self): return self.__dict__
    def __setstate__(self, d): self.__dict__.update(d)

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
        if(DEBUG_PARSER): print row
        for col in self.cols:
            if( col in row ):
                self.indices[col] = row.index(col)
            # elif( '\xef\xbb\xbf'+col in row ):
            #     self.indices[col] = row.index('\xef\xbb\xbf'+col)
            else:
                self.registerError('Could not find index of '+str(col) )
            if DEBUG: print "indices [%s] = %s" % (col, self.indices.get(col))

    def retrieveColFromRow(self, col, row):
        # if DEBUG_PARSER: print "retrieveColFromRow | col: ", col
        try:
            index = self.indices[col]
        except KeyError as e:
            self.registerError('No such column'+str(col)+' | '+str(e))
            return None
        try:
            # if DEBUG: print "row [%s] = %s" % (index, row[index])
            #this may break shit
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
        if(DEBUG_PARSER): self.registerMessage( "allData: {}".format(allData) )
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

    def analyseRows(self, rows):
        for rowcount, row in enumerate(rows):
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
        self.registerMessage("Completed analysis") 

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
            if(DEBUG_PARSER): print "CSV DIALECT: "
            if(DEBUG_PARSER): print "DEL ", repr(csvdialect.delimiter), \
                  "DBL ", repr(csvdialect.doublequote), \
                  "ESC ", repr(csvdialect.escapechar), \
                  "QUC ", repr(csvdialect.quotechar), \
                  "QUT ", repr(csvdialect.quoting), \
                  "SWS ", repr(csvdialect.skipinitialspace)
            
            csvreader = UnicodeReader(filePointer, dialect=csvdialect, strict=True)
            return self.analyseRows(csvreader)
        return None

    def getObjects(self):
        return self.objects

    def tabulate(self, cols=None, tablefmt=None):
        listClass = self.objectContainer.getContainer()
        objlist = listClass(self.objects.values())
        return objlist.tabulate(cols, tablefmt)

if __name__ == '__main__':
    inFolder = "../input/"
    # actPath = os.path.join(inFolder, 'partial act records.csv')
    actPath = os.path.join(inFolder, "200-act-records.csv")
    outFolder = "../output/"
    usrPath = os.path.join(outFolder, 'users.csv')

    usrData = ColData_User()

    # print "import cols", usrData.getImportCols()
    # print "defaults", usrData.getDefaults()

    usrParser = CSVParse_Base(
        cols = usrData.getImportCols(),
        defaults = usrData.getDefaults()
    )

    usrParser.analyseFile(actPath)

    print usrParser.tabulate()

    for usr in usrParser.objects.values()[:3]:    
        pprint(OrderedDict(usr))



