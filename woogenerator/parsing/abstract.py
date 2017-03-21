"""
CSVParse Abstract
Abstract base classes originally intended to be used for parsing and storing CSV data in a
convenient accessible dictionary structure, but modified to parse data in other formats.
Parse classes store Import objects in their internal structure and output ObjList instances
for easy analyis.
Here be dragons. Some of the design decisions are pretty bizarre, so please have a full read
through before changing anything. Sorry about that.
"""

from collections import OrderedDict
from copy import deepcopy, copy
from pprint import pformat
import re

from tabulate import tabulate
import unicodecsv

from woogenerator.utils import listUtils, SanitationUtils, Registrar, ProgressCounter
from woogenerator.utils import UnicodeCsvDialectUtils

BLANK_CELL = ''


class ObjList(list, Registrar):
    """
    An abstract list of `ImportObject`s
    """
    # supports_tablefmt = True
    objList_type = 'objects'
    supported_type = object

    def __init__(self, objects=None, indexer=None):
        super(ObjList, self).__init__()
        Registrar.__init__(self)
        if self.DEBUG_MRO:
            self.registerMessage('ObjList')
        self.indexer = indexer if indexer else (lambda x: x.index)
        self.supported_type = ImportObject
        # self._obj_list_type = 'objects'
        # self._objects = []
        self.indices = []
        if objects:
            self.extend(objects)

    @property
    def objects(self):
        """
        Returns a copy of the `ImportObject`s
        """
        return self[:]

    # @property
    # def objList_type(self):
    #     return self._obj_list_type

    # @property
    # def indices(self):
    #     return self._indices

    # def __len__(self):
    #     return len(self.objects)

    def append(self, object_data):
        # re-implemeny by overriding .append()?
        try:
            assert issubclass(object_data.__class__, self.supported_type), \
                "object must be subclass of %s not %s" % \
                (str(self.supported_type.__name__), str(object_data.__class__))
        except Exception as exc:
            self.registerError(exc)
            return
        index = self.indexer(object_data)
        if(index not in self.indices):
            super(ObjList, self).append(object_data)
            self.indices.append(index)

    def extend(self, objects):
        # re-implemeny by overriding .extend()?
        for obj in objects:
            self.append(obj)

    def getKey(self, key):
        values = listUtils.filter_unique_true([
            obj.get(key) for obj in self.objects
        ])

        if values:
            return values[0]

    def getSanitizer(self, tablefmt=None):
        if tablefmt == 'html':
            return SanitationUtils.sanitizeForXml
        else:
            return SanitationUtils.sanitizeForTable

    def tabulate(self, cols=None, tablefmt=None, highlight_rules=None):
        objs = self.objects
        sanitizer = self.getSanitizer(tablefmt)
        # sanitizer = (lambda x: str(x)) if tablefmt == 'html' else SanitationUtils.makeSafeOutput
        if objs:
            if not cols:
                cols = self.reportCols
            assert isinstance(cols, dict), \
                "cols should be a dict, found %s instead: %s" % (
                    type(cols), repr(cols))
            header = [self.objList_type]
            for col in cols.keys():
                header += [col]
            table = []
            for obj in objs:
                row = [obj.identifier]

                # process highlighting rules
                if highlight_rules:
                    classes = []
                    for highlight_class, rule in highlight_rules:
                        if rule(obj):
                            classes.append(highlight_class)
                    row = [" ".join(classes)] + row

                for col in cols.keys():
                    # if col == 'Address':
                    # print repr(str(obj.get(col))),
                    # repr(sanitizer(obj.get(col)))
                    row += [sanitizer(obj.get(col))or ""]
                    try:
                        SanitationUtils.coerce_unicode(row[-1])
                    except:
                        Registrar.registerWarning("can't turn row into unicode: %s" %
                                                  SanitationUtils.coerce_unicode(row))

                table += [row]
                # table += [[obj.index] + [ sanitizer(obj.get(col) )or "" for col in cols.keys()]]
            # print "table", table
            # SanitationUtils.safePrint(table)
            # return SanitationUtils.coerce_unicode(tabulate(table, headers=header,
            # tablefmt=tablefmt))
            table_str = (tabulate(table, headers=header, tablefmt=tablefmt))
            if highlight_rules and tablefmt == 'html':
                # print "table pre:", (table_str.encode('utf8'))
                table_str = re.sub(
                    r'<tr><td>([^<]*)</td>', r'<tr class="\1">', table_str)
                # also delete first row
                table_str = re.sub(r'<tr><th>\s*</th>', r'<tr>', table_str)
                # print "table post:", (table_str.encode('utf8'))

            return table_str
            # return table.encode('utf8')
        else:
            Registrar.registerWarning(
                "cannot tabulate Objlist: there are no objects")
            return ""

    def export_items(self, filePath, col_names, dialect=None, encoding="utf8"):
        assert filePath, "needs a filepath"
        assert col_names, "needs col_names"
        assert self.objects, "meeds items"
        with open(filePath, 'w+') as out_file:
            if dialect is None:
                csvdialect = UnicodeCsvDialectUtils.act_out
            else:
                csvdialect = UnicodeCsvDialectUtils.get_dialect_from_suggestion(
                    dialect)
            # unicodecsv.register_dialect('act_out', delimiter=',', quoting=unicodecsv.QUOTE_ALL, doublequote=False, strict=True, quotechar="\"", escapechar="`")
            if self.DEBUG_ABSTRACT:
                self.registerMessage(
                    UnicodeCsvDialectUtils.dialect_to_str(csvdialect))
            dictwriter = unicodecsv.DictWriter(
                out_file,
                dialect=csvdialect,
                fieldnames=col_names.keys(),
                encoding=encoding,
                extrasaction='ignore',
            )
            dictwriter.writerow(col_names)
            dictwriter.writerows(self.objects)
        self.registerMessage("WROTE FILE: %s" % filePath)

    reportCols = OrderedDict([
        ('_row', {'label': 'Row'}),
        ('index', {})
    ])

    def get_report_cols(self):
        exc = DeprecationWarning("use .reportCols instead of .get_report_cols()")
        self.registerError(exc)
        return self.reportCols

    @classmethod
    def get_basic_cols(cls):
        return cls.reportCols


class ImportObject(OrderedDict, Registrar):
    container = ObjList
    rowcountKey = 'rowcount'
    rowKey = '_row'

    def __init__(self, *args, **kwargs):
        if self.DEBUG_MRO:
            self.registerMessage('ImportObject')
        data = args[0]
        # Registrar.__init__(self)
        if self.DEBUG_PARSER:
            self.registerMessage('About to register child,\n -> DATA: %s\n -> KWARGS: %s'
                                 % (pformat(data), pformat(kwargs)))

        rowcount = kwargs.pop(self.rowcountKey, None)
        if rowcount is not None:
            data[self.rowcountKey] = rowcount
        OrderedDict.__init__(self, **data)
        row = kwargs.pop('row', None)

        # if not self.get('rowcount'): self['rowcount'] = 0
        # assert isinstance(self['rowcount'], int), "must specify integer rowcount not %s" % (self['rowcount'])
        if row is not None:
            self._row = row
        else:
            if not '_row' in self.keys():
                self['_row'] = []
        super(ImportObject, self).__init__(*args, **kwargs)

    def __hash__(self):
        return hash(self.index)

    @property
    def row(self): return self._row

    @property
    def rowcount(self): return self.get(self.rowcountKey, 0)

    @property
    def index(self): return self.rowcount

    @property
    def identifier_delimeter(self): return ""

    # @classmethod
    # def getNewObjContainer(cls):
    #     exc = DeprecationWarning("user .container instead of .getNewObjContainer()")
    #     self.registerError(exc)
    #     return cls.container
    #     # return ObjList

    @property
    def type_name(self):
        return type(self).__name__

    def getTypeName(self):
        exc = DeprecationWarning("use .type_name instead of .getTypeName()")
        self.registerError(exc)
        return self.type_name

    def get_identifier_delimeter(self):
        exc = DeprecationWarning(
            "use .identifier_delimeter instead of .get_identifier_delimeter()")
        self.registerError(exc)
        return self.identifier_delimeter

    @property
    def identifier(self):
        index = self.index
        if self.DEBUG_ABSTRACT:
            self.registerMessage("index: %s" % repr(index))
        type_name = self.type_name
        if self.DEBUG_ABSTRACT:
            self.registerMessage("type_name %s" % repr(type_name))
        identifier_delimeter = self.identifier_delimeter
        if self.DEBUG_ABSTRACT:
            self.registerMessage("identifier_delimeter %s" %
                                 repr(identifier_delimeter))
        return self.stringAnything(index, "<%s>" %
                                   type_name, identifier_delimeter)

    def get_identifier(self):
        exc = DeprecationWarning("use .identifier instead of .get_identifier()")
        self.registerError(exc)
        return self.identifier
        # return Registrar.stringAnything( self.index, "<%s>" %
        # self.getTypeName(), self.get_identifier_delimeter() )

    def get_copy_args(self):
        return {
            'rowcount': self.rowcount,
            'row': self.row[:]
        }

    def containerize(self):
        """ put self in a container by itself """
        return self.container([self])

    def __getstate__(self): return self.__dict__

    def __setstate__(self, d): self.__dict__.update(d)

    def __copy__(self):
        items = copy(self.items())
        print "doing a copy on %s \nwith items %s \nand copyargs %s" % (
            repr(self.__class__),
            pformat(items),
            self.get_copy_args(),
        )
        return self.__class__(
            copy(OrderedDict(self.items())),
            **self.get_copy_args()
        )

    def __deepcopy__(self, memodict=None):
        if not hasattr(Registrar, 'deepcopyprefix'):
            Registrar.deepcopyprefix = '>'
        Registrar.deepcopyprefix = '=' + Registrar.deepcopyprefix
        items = deepcopy(self.items())
        # print Registrar.deepcopyprefix, "doing a deepcopy on %s \nwith items %s \nand copyargs %s, \nmemodict: %s" % (
        #     repr(self.__class__),
        #     pformat(items),
        #     self.get_copy_args(),
        #     pformat(memodict)
        # )
        Registrar.deepcopyprefix = Registrar.deepcopyprefix[1:]
        return self.__class__(
            deepcopy(OrderedDict(items)),
            **self.get_copy_args()
        )

    def __str__(self):
        return "%10s <%s>" % (self.identifier, self.type_name)

    def __repr__(self):
        return self.__str__()

    def __cmp__(self, other):
        if other is None:
            return -1
        if not isinstance(other, ImportObject):
            return -1
        return cmp(self.rowcount, other.rowcount)


class CSVParse_Base(Registrar):
    objectContainer = ImportObject

    def __init__(self, cols, defaults, **kwargs):
        # super(CSVParse_Base, self).__init__()
        # Registrar.__init__(self)
        if self.DEBUG_MRO:
            self.registerMessage('CSVParse_Base')

        extra_cols = []
        extra_defaults = OrderedDict()

        self.limit = kwargs.pop('limit', None)
        self.cols = listUtils.combine_lists(cols, extra_cols)
        self.defaults = listUtils.combine_ordered_dicts(defaults, extra_defaults)
        self.objectIndexer = self.getObjectRowcount
        self.clear_transients()
        self.source = kwargs.get('source')

    def __getstate__(self): return self.__dict__

    def __setstate__(self, d): self.__dict__.update(d)

    def clear_transients(self):
        if self.DEBUG_MRO:
            self.registerMessage(' ')
        self.indices = OrderedDict()
        self.objects = OrderedDict()
        self.rowcount = 1

    def registerObject(self, object_data):
        if self.DEBUG_MRO:
            self.registerMessage(' ')
        self.registerAnything(
            object_data,
            self.objects,
            self.objectIndexer,
            singular=True,
            registerName='objects'
        )

    def analyse_header(self, row):
        # if self.DEBUG_PARSER: self.registerMessage( 'row: %s' % unicode(row) )
        sanitized_row = [self.sanitizeCell(cell) for cell in row]
        for col in self.cols:
            sanitized_col = self.sanitizeCell(col)
            if sanitized_col in sanitized_row:
                self.indices[col] = sanitized_row.index(sanitized_col)
                continue
            if self.indices[col]:
                if self.DEBUG_ABSTRACT:
                    self.registerMessage("indices [%s] = %s" % (
                        col, self.indices.get(col)))
            else:
                self.registerError('Could not find index of %s -> %s in %s' %
                                   (repr(col), repr(sanitized_col), repr(sanitized_row)))
        if not self.indices:
            raise UserWarning("could not find any indices")

    def retrieveColFromRow(self, col, row):
        # if self.DEBUG_PARSER: print "retrieveColFromRow | col: ", col
        try:
            index = self.indices[col]
        except KeyError as exc:
            if col in self.defaults:
                return self.defaults[col]
            self.registerError('No default for column ' + str(col) + ' | ' +
                               str(exc) + ' ' + unicode(self.defaults))
            return None
        try:
            if self.DEBUG_ABSTRACT:
                self.registerMessage(u"row [%3d] = %s" %
                                     (index, repr(row[index])))
            # this may break shit
            return row[index]
        except Exception as exc:
            self.registerWarning('Could not retrieve ' + str(col) + ' from row[' + str(index) + '] | ' +
                                 str(exc) + ' | ' + repr(row))
            return None

    def sanitizeCell(self, cell):
        return cell

    def getParserData(self, **kwargs):
        """
        gets data for the parser (in this case from row, specified in kwargs)
        generalized from getRowData
        """
        if self.DEBUG_MRO:
            self.registerMessage(' ')
        row = kwargs.get('row', [])
        row_data = OrderedDict()
        for col in self.cols:
            retrieved = self.retrieveColFromRow(col, row)
            if retrieved is not None and unicode(retrieved) is not u"":
                row_data[col] = self.sanitizeCell(retrieved)
        return row_data

    def getMandatoryData(self, **kwargs):
        mandatory_data = OrderedDict()
        if self.source:
            mandatory_data['source'] = self.source
        return mandatory_data

    def getNewObjContainer(self, all_data, **kwargs):
        if kwargs:
            pass  # gets rid of unused argument error
        if self.DEBUG_MRO:
            self.registerMessage(' ')
        return self.objectContainer

    def getKwargs(self, all_data, container, **kwargs):
        return kwargs

    def newObject(self, rowcount, **kwargs):
        """
        An import object is created with two pieces of information:
         - data: a dict containing the raw data in the import_object as a dictionary
         - kwargs: extra arguments passed to subclass __init__s to initialize the object
        Subclasses of CSVParse_Base override the getKwargs and getParserData methods
        so that they can supply their own arguments to an object's initialization
        """
        if self.DEBUG_PARSER:
            self.registerMessage(
                'rowcount: {} | kwargs {}'.format(rowcount, kwargs))
        kwargs['row'] = kwargs.get('row', [])
        kwargs['rowcount'] = rowcount
        default_data = OrderedDict(self.defaults.items())
        if self.DEBUG_PARSER:
            self.registerMessage("default_data: {}".format(default_data))
        parser_data = self.getParserData(**kwargs)
        if self.DEBUG_PARSER:
            self.registerMessage("parser_data: {}".format(parser_data))
        # all_data = listUtils.combine_ordered_dicts(parser_data, default_data)
        all_data = listUtils.combine_ordered_dicts(default_data, parser_data)
        mandatory_data = self.getMandatoryData(**kwargs)
        all_data = listUtils.combine_ordered_dicts(all_data, mandatory_data)
        if self.DEBUG_PARSER:
            self.registerMessage("all_data: {}".format(all_data))
        container = self.getNewObjContainer(all_data, **kwargs)
        if self.DEBUG_PARSER:
            self.registerMessage("container: {}".format(container.__name__))
        kwargs = self.getKwargs(all_data, container, **kwargs)
        if self.DEBUG_PARSER:
            self.registerMessage("kwargs: {}".format(kwargs))
        object_data = container(all_data, **kwargs)
        return object_data

    # def initializeObject(self, object_data):
    #     pass

    def processObject(self, object_data):
        pass

    # def processObject(self, object_data):
        # self.initializeObject(object_data)
        # object_data.initialized = True;
        # self.processObject(object_data)
        # self.registerObject(object_data)

    def analyse_rows(self, unicode_rows, file_name="rows", limit=None):
        if limit and isinstance(limit, int):
            unicode_rows = list(unicode_rows)[:limit]
        if self.DEBUG_PROGRESS:

            # last_print = time()
            rows = []
            try:
                for row in unicode_rows:
                    rows.append(row)
            except Exception as exc:
                raise Exception("could not append row %d, %s: \n\t%s" %
                                (len(rows), str(exc), repr(rows[-1:])))
            rowlen = len(rows)
            self.progress_counter = ProgressCounter(rowlen)
            unicode_rows = rows

        for unicode_row in (unicode_rows):
            self.rowcount += 1

            if limit and self.rowcount > limit:
                break
            if self.DEBUG_PROGRESS:
                self.progress_counter.maybePrintUpdate(self.rowcount)
                # now = time()
                # if now - last_print > 1:
                #     last_print = now
                #     print "%d of %d rows processed" % (self.rowcount, rowlen)

            if unicode_row:
                non_unicode = filter(
                    lambda unicode_cell: not isinstance(
                        unicode_cell, unicode) if unicode_cell else False,
                    unicode_row
                )
                assert not non_unicode, "non-empty cells must be unicode objects, {}".format(
                    repr(non_unicode))

            if not any(unicode_row):
                continue

            if not self.indices:
                self.analyse_header(unicode_row)
                continue
            try:
                object_data = self.newObject(self.rowcount, row=unicode_row)
            except UserWarning as exc:
                self.registerWarning("could not create new object: {}".format(
                    exc), "%s:%d" % (file_name, self.rowcount))
                continue
            else:
                if self.DEBUG_PARSER:
                    self.registerMessage("%s CREATED" % object_data.identifier)
            try:
                self.processObject(object_data)
                if self.DEBUG_PARSER:
                    self.registerMessage("%s PROCESSED" %
                                         object_data.identifier)
            except UserWarning as exc:
                self.registerError(
                    "could not process new object: {}".format(exc), object_data)
                continue
            try:
                self.registerObject(object_data)
                if self.DEBUG_PARSER:
                    self.registerMessage("%s REGISTERED" %
                                         object_data.identifier)
                    self.registerMessage("%s" % object_data.__repr__())

            except UserWarning as exc:
                self.registerWarning(
                    "could not register new object: {}".format(exc), object_data)
                continue
        if self.DEBUG_PARSER:
            self.registerMessage("Completed analysis")

    def analyse_stream(self, byte_file_obj, streamName=None,
                      encoding=None, dialect_suggestion=None, limit=None):
        """ may want to revert back to this commit if things break:
        https://github.com/derwentx/WooGenerator/commit/c4fabf83d5b4d1e0a4d3ff755cd8eadf1433d253 """

        if hasattr(self, 'rowcount') and self.rowcount > 1:
            raise UserWarning(
                'rowcount should be 0. Make sure clear_transients is being called on ancestors')
        if encoding is None:
            encoding = "utf8"

        if streamName is None:
            if hasattr(byte_file_obj, 'name'):
                streamName = byte_file_obj.name
            else:
                streamName = 'stream'

        if self.DEBUG_PARSER:
            self.registerMessage(
                "Analysing stream: {0}, encoding: {1}".format(streamName, encoding))

        # I can't imagine this having any problems
        byte_sample = SanitationUtils.coerce_bytes(byte_file_obj.read(1000))
        byte_file_obj.seek(0)

        if dialect_suggestion:
            csvdialect = UnicodeCsvDialectUtils.get_dialect_from_suggestion(
                dialect_suggestion)
        else:
            csvdialect = unicodecsv.Sniffer().sniff(byte_sample)
            assert \
                csvdialect.delimiter == ',' and isinstance(
                    csvdialect.delimiter, str)
            # try:
            #     csvdialect = unicodecsv.Sniffer().sniff(byte_sample)
            #     assert csvdialect.delimiter ==',', "sanity test"
            #     assert isinstance(csvdialect.delimiter, str)
            # except AssertionError:
            #     csvdialect = UnicodeCsvDialectUtils.default_dialect

        if self.DEBUG_PARSER:
            self.registerMessage(
                UnicodeCsvDialectUtils.dialect_to_str(csvdialect))

        unicodecsvreader = unicodecsv.reader(
            byte_file_obj,
            dialect=csvdialect,
            encoding=encoding,
            strict=True
        )
        return self.analyse_rows(
            unicodecsvreader, file_name=streamName, limit=limit)

    def analyse_file(self, file_name, encoding=None,
                    dialect_suggestion=None, limit=None):
        with open(file_name, 'rbU') as byte_file_obj:
            return self.analyse_stream(
                byte_file_obj,
                streamName=file_name,
                encoding=encoding,
                dialect_suggestion=dialect_suggestion,
                limit=limit
            )
        return None

    @classmethod
    def translateKeys(cls, object_data, key_translation):
        translated = OrderedDict()
        for col, translation in key_translation.items():
            if col in object_data:
                translated[translation] = object_data[col]
        return translated

    def analyse_wp_api_obj(self, api_data):
        raise NotImplementedError()

    def getObjects(self):
        exc = DeprecationWarning("Use .objects instead of .getObjects()")
        self.registerError(exc)
        return self.objects

    def getObjList(self):
        list_class = self.objectContainer.container
        # list_class = self.objectContainer.getNewObjContainer()
        objlist = list_class(self.objects.values())
        return objlist

    def tabulate(self, cols=None, tablefmt=None):
        objlist = self.getObjList()
        return SanitationUtils.coerce_bytes(objlist.tabulate(cols, tablefmt))

    @classmethod
    def printBasicColumns(cls, objects):
        obj_list = cls.objectContainer.container()
        for _object in objects:
            obj_list.append(_object)

        cols = cls.objectContainer.container.get_basic_cols()

        SanitationUtils.safePrint(obj_list.tabulate(
            cols,
            tablefmt='simple'
        ))
#
# if __name__ == '__main__':
#     in_folder = "../input/"
#     # actPath = os.path.join(in_folder, 'partial act records.csv')
#     actPath = os.path.join(in_folder, "500-act-records.csv")
#     out_folder = "../output/"
#     usrPath = os.path.join(out_folder, 'users.csv')
#
#     usrData = ColData_User()
#
#     # print "import cols", usrData.get_import_cols()
#     # print "defaults", usrData.get_defaults()
#
#     usrParser = CSVParse_Base(
#         cols = usrData.get_import_cols(),
#         defaults = usrData.get_defaults()
#     )
#
#     usrParser.analyse_file(actPath)
#
#     SanitationUtils.safePrint( usrParser.tabulate(cols = usrData.get_report_cols()))
#     print ( usrParser.tabulate(cols = usrData.get_report_cols()))
#
#     for usr in usrParser.objects.values()[:3]:
#         pprint(OrderedDict(usr))
