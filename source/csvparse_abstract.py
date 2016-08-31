"""
CSVParse Abstract
Abstract base classes originally intended to be used for parsing and storing CSV data in a
convenient accessible dictionary structure, but modified to store data in other formats.
Parse classes store Import objects in their internal structure and output ObjList instances
for easy analyis.
"""


# from pprint import pprint
from collections import OrderedDict
from utils import listUtils, SanitationUtils, Registrar, ProgressCounter
from utils import UnicodeCsvDialectUtils
from tabulate import tabulate
import unicodecsv
# from coldata import ColData_User
from copy import deepcopy, copy
# from time import time
# import os

class ObjList(list, Registrar):
    # supports_tablefmt = True
    objList_type = 'objects'
    supported_type = object

    def __init__(self, objects=None, indexer=None):
        super(ObjList, self).__init__()
        Registrar.__init__(self)
        if self.DEBUG_MRO:
            self.registerMessage(' ')
        self.indexer = indexer if indexer else (lambda x: x.index)
        self.supported_type = ImportObject
        # self._objList_type = 'objects'
        # self._objects = []
        self.indices = []
        if objects:
            self.extend(objects)

    @property
    def objects(self):
        return self[:]

    # @property
    # def objList_type(self):
    #     return self._objList_type

    # @property
    # def indices(self):
    #     return self._indices


    # def __len__(self):
    #     return len(self.objects)

    def append(self, objectData):
        #re-implemeny by overriding .append()?
        try:
            assert issubclass(objectData.__class__, self.supported_type), \
                "object must be subclass of %s not %s" % \
                    (str(self.supported_type.__name__), str(objectData.__class__))
        except Exception as e:
            self.registerError(e)
            return
        index = self.indexer(objectData)
        if(index not in self.indices):
            super(ObjList, self).append(objectData)
            self.indices.append(index)

    def extend(self, objects):
        #re-implemeny by overriding .extend()?
        for obj in objects:
            self.append(obj)

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
        sanitizer = self.getSanitizer(tablefmt)
        # sanitizer = (lambda x: str(x)) if tablefmt == 'html' else SanitationUtils.makeSafeOutput
        if objs:
            if not cols: cols = self.reportCols
            header = [self.objList_type]
            for col in cols.keys():
                header += [col]
            table = []
            for obj in objs:
                row = [obj.index]
                for col in cols.keys():
                    # if col == 'Address':
                    #     print repr(str(obj.get(col))), repr(sanitizer(obj.get(col)))
                    row += [ sanitizer(obj.get(col) )or ""]
                    try:
                        SanitationUtils.coerceUnicode(row[-1])
                    except:
                        Registrar.registerWarning("can't turn row into unicode: %s" % SanitationUtils.coerceUnicode(row))

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
            Registrar.registerWarning("cannot tabulate Objlist: there are no objects")
            return ""

    def exportItems(self, filePath, colNames, dialect = None, encoding="utf8"):
        assert filePath, "needs a filepath"
        assert colNames, "needs colNames"
        assert self.objects, "meeds items"
        with open(filePath, 'w+') as outFile:
            if dialect is None:
                csvdialect = UnicodeCsvDialectUtils.act_out
            else:
                csvdialect = UnicodeCsvDialectUtils.get_dialect_from_suggestion(dialect)
            # unicodecsv.register_dialect('act_out', delimiter=',', quoting=unicodecsv.QUOTE_ALL, doublequote=False, strict=True, quotechar="\"", escapechar="`")
            if self.DEBUG_ABSTRACT:
                self.registerMessage(UnicodeCsvDialectUtils.dialect_to_str(csvdialect))
            dictwriter = unicodecsv.DictWriter(
                outFile,
                dialect=csvdialect,
                fieldnames=colNames.keys(),
                encoding=encoding,
                extrasaction='ignore',
            )
            dictwriter.writerow(colNames)
            dictwriter.writerows(self.objects)
        self.registerMessage("WROTE FILE: %s" % filePath)

    reportCols = OrderedDict([
        ('_row',{'label':'Row'}),
        ('index',{})
    ])

    def getReportCols(self):
        e = DeprecationWarning("use .reportCols instead of .getReportCols()")
        self.registerError(e)
        return self.reportCols


class ImportObject(OrderedDict, Registrar):
    container = ObjList

    def __init__(self, data, rowcount = None, row = None):
        super(ImportObject, self).__init__(data)
        Registrar.__init__(self)
        if self.DEBUG_MRO:
            self.registerMessage(' ')
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

    @property
    def identifierDelimeter(self): return ""

    # @classmethod
    # def getNewObjContainer(cls):
    #     e = DeprecationWarning("user .container instead of .getNewObjContainer()")
    #     self.registerError(e)
    #     return cls.container
    #     # return ObjList

    @property
    def typeName(self):
        return type(self).__name__

    def getTypeName(self):
        e = DeprecationWarning("use .typeName instead of .getTypeName()")
        self.registerError(e)
        return self.typeName

    def getIdentifierDelimeter(self):
        e = DeprecationWarning("use .identifierDelimeter instead of .getIdentifierDelimeter()")
        self.registerError(e)
        return self.identifierDelimeter

    @property
    def identifier(self):
        Registrar.stringAnything( self.index, "<%s>" % self.typeName, self.identifierDelimeter )

    def getIdentifier(self):
        e = DeprecationWarning("use .identifier instead of .getIdentifier()")
        self.registerError(e)
        return self.identifier
        # return Registrar.stringAnything( self.index, "<%s>" % self.getTypeName(), self.getIdentifierDelimeter() )

    def __getstate__(self): return self.__dict__
    def __setstate__(self, d): self.__dict__.update(d)
    def __copy__(self): return self.__class__(copy(super(ImportObject,self)), self.rowcount, self.row)
    def __deepcopy__(self, memodict={}): return self.__class__(deepcopy(OrderedDict(self)), self.rowcount, self.row[:])

    def __str__(self):
        return "%10s <%s>" % (self.index, self.typeName)

    def __repr__(self):
        return self.__str__()

    def __cmp__(self, other):
        if other == None:
            return -1
        if not isinstance(other, ImportObject):
            return -1
        return cmp(self.rowcount, other.rowcount)

class CSVParse_Base(Registrar):
    objectContainer = ImportObject

    def __init__(self, cols, defaults, limit=None, **kwargs):
        super(CSVParse_Base, self).__init__()
        Registrar.__init__(self)
        if self.DEBUG_MRO:
            self.registerMessage(' ')

        extra_cols = []
        extra_defaults = OrderedDict()

        self.limit = limit
        self.cols = listUtils.combineLists( cols, extra_cols )
        self.defaults = listUtils.combineOrderedDicts( defaults, extra_defaults )
        self.objectIndexer = self.getObjectRowcount
        self.clearTransients()

    def __getstate__(self): return self.__dict__
    def __setstate__(self, d): self.__dict__.update(d)

    def clearTransients(self):
        if self.DEBUG_MRO:
            self.registerMessage(' ')
        self.indices = OrderedDict()
        self.objects = OrderedDict()
        self.rowcount = 0

    def registerObject(self, objectData):
        if self.DEBUG_MRO:
            self.registerMessage(' ')
        self.registerAnything(
            objectData,
            self.objects,
            self.objectIndexer,
            singular = True,
            registerName = 'objects'
        )

    def analyseHeader(self, row):
        if self.DEBUG_PARSER: self.registerMessage( 'row: %s' % unicode(row) )
        for col in self.cols:
            if( col in row ):
                self.indices[col] = row.index(col)
            # elif( '\xef\xbb\xbf'+col in row ):
            #     self.indices[col] = row.index('\xef\xbb\xbf'+col)
            else:
                self.registerError('Could not find index of '+str(col) )
            if self.DEBUG_ABSTRACT: self.registerMessage( "indices [%s] = %s" % (col, self.indices.get(col)))

    def retrieveColFromRow(self, col, row):
        # if self.DEBUG_PARSER: print "retrieveColFromRow | col: ", col
        try:
            index = self.indices[col]
        except KeyError as e:
            if col in self.defaults:
                return self.defaults[col]
            self.registerError('No default for column '+str(col)+' | '+str(e) + ' ' + unicode(self.defaults))
            return None
        try:
            if self.DEBUG_ABSTRACT: self.registerMessage(u"row [%3d] = %s" % (index, repr(row[index])))
            #this may break shit
            return row[index]
        except Exception as e:
            self.registerWarning('Could not retrieve '+str(col)+' from row['+str(index)+'] | '+\
                                 str(e) +' | '+repr(row))
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

    def getNewObjContainer(self, allData, **kwargs):
        if kwargs:
            pass # gets rid of unused argument error
        if self.DEBUG_MRO:
            self.registerMessage(' ')
        return self.objectContainer

    def getKwargs(self, allData, container, **kwargs):
        return kwargs

    def newObject(self, rowcount, row, **kwargs):
        # self.registerMessage( 'row: {} | {}'.format(rowcount, row) )
        defaultData = OrderedDict(self.defaults.items())
        if self.DEBUG_PARSER: self.registerMessage( "defaultData: {}".format(defaultData) )
        rowData = self.getRowData(row)
        if self.DEBUG_PARSER: self.registerMessage( "rowData: {}".format(rowData) )
        # allData = listUtils.combineOrderedDicts(rowData, defaultData)
        allData = listUtils.combineOrderedDicts(defaultData, rowData)
        if self.DEBUG_PARSER: self.registerMessage( "allData: {}".format(allData) )
        kwargs['rowcount'] = rowcount
        kwargs['row'] = row
        container = self.getNewObjContainer(allData, **kwargs)
        if self.DEBUG_PARSER: self.registerMessage("container: {}".format(container.__name__))
        kwargs = self.getKwargs(allData, container, **kwargs)
        if self.DEBUG_PARSER: self.registerMessage("kwargs: {}".format(kwargs))
        objectData = container(allData, **kwargs)
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

    def analyseRows(self, unicode_rows, fileName="rows"):
        limit = None
        if hasattr(self, 'limit'):
            limit = self.limit
        if limit and isinstance(limit, int):
            unicode_rows = list(unicode_rows)[:limit]
        if self.DEBUG_PROGRESS:

            # last_print = time()
            rows = []
            try:
                for row in unicode_rows:
                    rows.append(row)
            except Exception, e:
                raise Exception("could not append row %d, %s: \n\t%s" % (len(rows), str(e), rows[-1]))
            rowlen = len(rows)
            self.progressCounter = ProgressCounter(rowlen)
            unicode_rows = rows

        for unicode_row in (unicode_rows):
            if self.DEBUG_PROGRESS:
                self.progressCounter.maybePrintUpdate(self.rowcount)
                # now = time()
                # if now - last_print > 1:
                #     last_print = now
                #     print "%d of %d rows processed" % (self.rowcount, rowlen)

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
                objectData = self.newObject( self.rowcount, unicode_row )
            except UserWarning as e:
                self.registerWarning("could not create new object: {}".format(e), "%s:%d" % (fileName, self.rowcount))
                continue
            else:
                if self.DEBUG_PARSER:
                    self.registerMessage("%s CREATED" % objectData.identifier )
            try:
                self.processObject(objectData)
                if self.DEBUG_PARSER:
                    self.registerMessage("%s PROCESSED" % objectData.identifier )
            except UserWarning as e:
                self.registerError("could not process new object: {}".format(e), objectData)
                continue
            try:
                self.registerObject(objectData)
                if self.DEBUG_PARSER:
                    self.registerMessage("%s REGISTERED" % objectData.identifier )
                    self.registerMessage("%s" % objectData.__repr__())

            except UserWarning as e:
                self.registerWarning("could not register new object: {}".format(e), objectData)
                continue
            self.rowcount += 1
        if self.DEBUG_PARSER:
            self.registerMessage("Completed analysis")

    def analyseFile(self, fileName, encoding=None, dialect_suggestion=None):
        if encoding is None:
            encoding = "utf8"
        if self.DEBUG_PARSER:
            self.registerMessage("Analysing file: {0}, encoding: {1}".format(fileName, encoding))
        with open(fileName, 'rbU') as byte_file_obj:
            # I can't imagine this having any problems
            byte_sample = byte_file_obj.read(1000)
            byte_file_obj.seek(0)

            if dialect_suggestion:
                csvdialect = UnicodeCsvDialectUtils.get_dialect_from_suggestion(dialect_suggestion)
            else:
                try:
                    csvdialect = unicodecsv.Sniffer().sniff(byte_sample)
                    assert csvdialect.delimiter ==',', "sanity test"
                except Exception:
                    csvdialect = UnicodeCsvDialectUtils.default_dialect

            if self.DEBUG_PARSER:
                self.registerMessage(UnicodeCsvDialectUtils.dialect_to_str(csvdialect))

            unicodecsvreader = unicodecsv.reader(byte_file_obj, dialect=csvdialect, encoding=encoding, strict=True)
            return self.analyseRows(unicodecsvreader, fileName)
        return None

    def analyseWpApiObj(self, apiData):
        raise NotImplementedError()

    def getObjects(self):
        e = DeprecationWarning("Use .objects instead of .getObjects()")
        self.registerError(e)
        return self.objects

    def getObjList(self):
        listClass = self.objectContainer.container
        # listClass = self.objectContainer.getNewObjContainer()
        objlist = listClass(self.objects.values())
        return objlist

    def tabulate(self, cols=None, tablefmt=None):
        objlist = self.getObjList()
        return SanitationUtils.coerceBytes(objlist.tabulate(cols, tablefmt))
#
# if __name__ == '__main__':
#     inFolder = "../input/"
#     # actPath = os.path.join(inFolder, 'partial act records.csv')
#     actPath = os.path.join(inFolder, "500-act-records.csv")
#     outFolder = "../output/"
#     usrPath = os.path.join(outFolder, 'users.csv')
#
#     usrData = ColData_User()
#
#     # print "import cols", usrData.getImportCols()
#     # print "defaults", usrData.getDefaults()
#
#     usrParser = CSVParse_Base(
#         cols = usrData.getImportCols(),
#         defaults = usrData.getDefaults()
#     )
#
#     usrParser.analyseFile(actPath)
#
#     SanitationUtils.safePrint( usrParser.tabulate(cols = usrData.getReportCols()))
#     print ( usrParser.tabulate(cols = usrData.getReportCols()))
#
#     for usr in usrParser.objects.values()[:3]:
#         pprint(OrderedDict(usr))
