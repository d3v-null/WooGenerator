from pprint import pprint
from collections import OrderedDict
from utils import listUtils, SanitationUtils, Registrar
from tabulate import tabulate
import unicodecsv
from coldata import ColData_User
from copy import deepcopy, copy
from time import time

DEBUG = False
DEBUG_PARSER = False
DEBUG_PROGRESS = True

import os

class ImportObject(OrderedDict, Registrar):

    def __init__(self, data, rowcount = None, row = None):
        super(ImportObject, self).__init__(data)
        Registrar.__init__(self)
        if rowcount is not None:
            self['rowcount'] = rowcount
        # if not self.get('rowcount'): self['rowcount'] = 0
        # assert isinstance(self['rowcount'], int), "must specify integer rowcount not %s" % (self['rowcount'])
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
            assert issubclass(objectData.__class__, ImportObject), "object must be subclass of ImportObject not %s" % str(objectData.__class__)
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

    def getSanitizer(self, tablefmt=None):
        if tablefmt == 'html':
            return SanitationUtils.sanitizeForXml
        else:
            return SanitationUtils.sanitizeForTable

    def tabulate(self, cols=None, tablefmt=None):
        objs = self.objects
        sanitizer = self.getSanitizer(tablefmt);
        # sanitizer = (lambda x: str(x)) if tablefmt == 'html' else SanitationUtils.makeSafeOutput
        if(objs):
            # print "there are objects"
            if not cols: cols = self.getReportCols()                
            header = [self.objList_type]
            for col, data in cols.items():
                header += [col]
            table = []
            for obj in objs:
                row = [obj.index]
                for col in cols.keys():
                    # if col == 'Address':
                    #     print repr(str(obj.get(col))), repr(sanitizer(obj.get(col)))
                    row += [ sanitizer(obj.get(col) )or ""]
                    try:
                        unicode(row[-1])
                    except:
                        print "can't turn row into unicode:", repr(row), SanitationUtils.coerceBytes(row)

                table += [row]
                # table += [[obj.index] + [ sanitizer(obj.get(col) )or "" for col in cols.keys()]]
            # print "table", table
            # SanitationUtils.safePrint(table)
            # return SanitationUtils.coerceUnicode(tabulate(table, headers=header, tablefmt=tablefmt))
            return (tabulate(table, headers=header, tablefmt=tablefmt))
            # print repr(table)
            # print repr(table.encode('utf8'))
            # return table.encode('utf8')
        else:
            if DEBUG:
                print "there are no objects"
            return None

    def exportItems(self, filePath, colNames, dialect = None, encoding="utf8"):
        assert filePath, "needs a filepath"
        assert colNames, "needs colNames"
        assert self.objects, "meeds items"
        with open(filePath, 'w+') as outFile:
            unicodecsv.register_dialect('act_out', delimiter=',', quoting=unicodecsv.QUOTE_ALL, doublequote=False, strict=True, quotechar="\"", escapechar="`")
            dictwriter = unicodecsv.dictWriter(
                outFile,
                dialect = 'act_out',
                fieldnames = colNames.keys(),
                encoding = encoding

                # extrasaction = 'ignore',
            )
            dictwriter.writerow(colNames)
            dictwriter.writerows(self.objects)
        print "WROTE FILE: ", filePath

    def getReportCols(self):
        return OrderedDict([
                    ('_row',{'label':'Row'}),
                    ('index',{})
                ])

class CSVParse_Base(object, Registrar):
    objectContainer = ImportObject

    def __init__(self, cols, defaults):
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

    def analyseRows(self, unicode_rows):
        if DEBUG_PROGRESS:
            unicode_rows = list(unicode_rows)
            rowlen = len(unicode_rows)
            last_print = time()

        for rowcount, unicode_row in enumerate(unicode_rows):
            if DEBUG_PROGRESS:
                now = time()
                if now - last_print > 1:
                    last_print = now
                    print "%d of %d rows processed" % (rowcount, rowlen)


            if unicode_row: 
                non_unicode = filter(
                    lambda unicode_cell: not isinstance(unicode_cell, unicode) if unicode_cell else False,
                    unicode_row
                )
                assert not non_unicode, "non-empty cells must be unicode objects, {}".format(repr(non_unicode))
                    
            if not self.indices :
                self.analyseHeader(unicode_row)
                continue
            try:
                objectData = self.newObject( rowcount, unicode_row )
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
                if (DEBUG_PARSER): 
                    self.registerMessage("%s REGISTERED" % objectData.getIdentifier() )
                    self.registerMessage("%s" % objectData.__repr__())

            except UserWarning as e:
                self.registerError("could not register new object: {}".format(e), objectData)
                continue
        self.registerMessage("Completed analysis") 

    def analyseFile(self, fileName, encoding=None):
        if encoding is None:
            encoding = "utf8"
        self.registerMessage("Analysing file: {0}, encoding: {1}".format(fileName, encoding))
        with open(fileName, 'rb') as byte_file_obj:
            # I can't imagine this having any problems
            byte_sample = byte_file_obj.read(1000)
            byte_file_obj.seek(0)
            csvdialect = unicodecsv.Sniffer().sniff(byte_sample)
            if DEBUG_PARSER: print "CSV Dialect:",    \
                "DEL ", repr(csvdialect.delimiter)  , \
                "DBL ", repr(csvdialect.doublequote), \
                "ESC ", repr(csvdialect.escapechar) , \
                "QUC ", repr(csvdialect.quotechar)  , \
                "QUT ", repr(csvdialect.quoting)    , \
                "SWS ", repr(csvdialect.skipinitialspace)
            
            unicodecsvreader = unicodecsv.reader(byte_file_obj, dialect=csvdialect, encoding=encoding, strict=True)
            return self.analyseRows(unicodecsvreader)
        return None

    def getObjects(self):
        return self.objects

    def tabulate(self, cols=None, tablefmt=None):
        listClass = self.objectContainer.getContainer()
        objlist = listClass(self.objects.values())
        return SanitationUtils.coerceBytes(objlist.tabulate(cols, tablefmt))

if __name__ == '__main__':
    inFolder = "../input/"
    # actPath = os.path.join(inFolder, 'partial act records.csv')
    actPath = os.path.join(inFolder, "500-act-records.csv")
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

    SanitationUtils.safePrint( usrParser.tabulate(cols = usrData.getReportCols()))
    print ( usrParser.tabulate(cols = usrData.getReportCols()))

    for usr in usrParser.objects.values()[:3]:    
        pprint(OrderedDict(usr))



