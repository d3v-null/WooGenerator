"""
Utilities for parsing and handling data import files.

Abstract base classes originally intended to be used for parsing and storing CSV data in a
convenient accessible dictionary structure, but modified to parse data in other formats.
Parse classes store Import objects in their internal structure and output ObjList instances
for easy analyis.
Here be dragons. Some of the design decisions are pretty bizarre, so please have a full read
through before changing anything. Sorry about that.
"""
from __future__ import absolute_import

import re
from collections import OrderedDict
from copy import copy, deepcopy
from pprint import pformat

import unicodecsv
from tabulate import tabulate

from ..coldata import ColDataAbstract
from ..utils import (ProgressCounter, Registrar, SanitationUtils, SeqUtils,
                     UnicodeCsvDialectUtils)

BLANK_CELL = ''

class ImportObject(OrderedDict, Registrar):
    """
    A container for a parsed object.
    """

    rowcount_key = 'rowcount'
    row_key = '_row'
    coldata_gen_target = 'gen-csv'

    def __init__(self, *args, **kwargs):
        if self.DEBUG_ABSTRACT:
            self.register_message("args = %s\nkwargs = %s\n" % (
                pformat(args), pformat(kwargs.items())
            ))

        if self.DEBUG_MRO:
            self.register_message('ImportObject')
        data = args[0]
        try:
            assert \
                isinstance(data, dict), \
                "expected data to be a dict, instead found: %s" % type(data)
        except AssertionError as exc:
            try:
                data = OrderedDict(data)
            except Exception:
                self.raise_exception(exc)

        # Registrar.__init__(self)
        if self.DEBUG_PARSER:
            self.register_message(
                'Abstract init: \n -> DATA: %s\n -> KWARGS: %s' %
                (pformat(data), pformat(kwargs)))

        rowcount = kwargs.pop(self.rowcount_key, None)
        if rowcount is not None:
            data[self.rowcount_key] = rowcount
        row = kwargs.pop('row', None)

        OrderedDict.__init__(self, data)
        self._row = row
        if '_row' not in self.keys():
            self['_row'] = []
        Registrar.__init__(self, *args, **kwargs)

    def __hash__(self):
        return hash(self.index)

    def to_dict(self):
        return OrderedDict(self)

    def to_target_type(self, **kwargs):
        """
        Return the object as a dictionary which has had types converted to
        `coldata_target` format.
        """
        coldata_class = kwargs.get('coldata_class')
        if not coldata_class:
            coldata_class = self.coldata_class
        coldata_target = kwargs.get('coldata_target')
        if not coldata_target:
            coldata_target = self.coldata_target
        # translate data without deleting unknown columns
        return coldata_class.translate_data_from_to_simple(
            self.to_dict(),
            self.coldata_gen_target,
            coldata_target
        )

    # TODO: refactor to get rid of row property, rename _row to row
    @property
    def row(self):
        return self._row

    # TODO: refactor to get rid of row property, rename _row to row
    @property
    def rowcount(self):
        return self.get(self.rowcount_key, 0)

    @property
    def index(self):
        """
        Return a unique identifier to differentiate this from others within import.
        """

        return self.rowcount

    @property
    def identifier_delimeter(self):
        """
        Return the delimeter used in creating the identifier for this instance.

        Override in subclasses.
        """

        return ""

    @property
    def type_name(self):
        """
        Return the name of the type of this instance for creating an identifier.
        """

        return type(self).__name__

    @property
    def identifier(self):
        """
        Return a unique identifier to distinguish this from others outside import.
        """

        index = self.index
        if self.DEBUG_ABSTRACT:
            self.register_message("index: %s" % repr(index))
        type_name = self.type_name
        if self.DEBUG_ABSTRACT:
            self.register_message("type_name %s" % repr(type_name))
        identifier_delimeter = self.identifier_delimeter
        if self.DEBUG_ABSTRACT:
            self.register_message("identifier_delimeter %s" %
                                  repr(identifier_delimeter))
        return self.string_anything(index, "<%s>" % type_name,
                                    identifier_delimeter)

    def get_copy_args(self):
        """
        Return the arguments provided to the copy method.

        Override in subclasses.
        """
        copy_args = {}
        if self.rowcount is not None:
            copy_args['rowcount'] = self.rowcount
        if self.row is not None:
            copy_args['row'] = self.row[:]
        return copy_args

    def containerize(self):
        """ Put self in preferred container. """
        return self.container([self])

    def update(self, other):
        """ Update the ImportObject with the values from another ImportObject or dict"""
        if isinstance(other, ImportObject):
            other_dict = other.to_dict()
        else:
            other_dict = deepcopy(other)
        if 'rowcount' in other_dict:
            del other_dict['rowcount']
        if '_row' in other_dict:
            del other_dict['_row']
        return OrderedDict.update(self, other_dict)

    def __getstate__(self):
        return self.__dict__

    def __setstate__(self, copy_dict):
        self.__dict__.update(copy_dict)

    def __recuce__(self):
        items = copy(OrderedDict(self.items()))
        return (self.__class__, (items, ))

    def __copy__(self):
        items = copy(OrderedDict(self.items()))
        return self.__class__(items, **self.get_copy_args())

    def __deepcopy__(self, memodict=None):
        if not hasattr(Registrar, 'deepcopyprefix'):
            Registrar.deepcopyprefix = '>'
        Registrar.deepcopyprefix = '=' + Registrar.deepcopyprefix
        items = deepcopy(self.items())
        Registrar.deepcopyprefix = Registrar.deepcopyprefix[1:]
        return self.__class__(
            deepcopy(OrderedDict(items)), **self.get_copy_args())

    def __str__(self):
        return "%10s <%s>" % (self.identifier, self.type_name)

    def __repr__(self, *_):
        return self.__str__()

    def __cmp__(self, other):
        if other is None:
            return -1
        if not isinstance(other, ImportObject):
            return -1
        return cmp(self.rowcount, other.rowcount)

class ObjList(list, Registrar):
    """
    An abstract list of `ImportObject`s.
    """

    objList_type = 'objects'
    supported_type = ImportObject
    coldata_class = ColDataAbstract
    coldata_target = 'wc-csv'

    def __init__(self, objects=None, indexer=None):
        list.__init__(self)
        Registrar.__init__(self)
        if self.DEBUG_MRO:
            self.register_message('ObjList')
        if indexer is None:
            indexer = (lambda x: getattr(x, 'index'))
        self.indexer = indexer
        # self._obj_list_type = 'objects'
        # self._objects = []
        self.indices = []
        if objects:
            self.extend(objects)

    @property
    def objects(self):
        """
        Return a copy of the `ImportObject`s.
        """
        return self[:]

    def append(self, object_data):
        try:
            assert issubclass(object_data.__class__, self.supported_type), \
                "object must be subclass of %s not %s" % \
                (str(self.supported_type.__name__), str(object_data.__class__))
        except Exception as exc:
            self.register_error(exc)
            return
        index = self.indexer(object_data)
        if index not in self.indices:
            self.indices.append(index)
            return list.append(self, object_data)

    def extend(self, objects):
        for obj in objects:
            self.append(obj)

    def pop(self, index):
        self.indices.pop(index)
        return list.pop(self, index)

    def __setitem__(self, key, value):
        index = self.indexer(value)
        self.indices.__setitem__(key, index)
        return list.__setitem__(self, key, value)

    def __delitem__(self, key):
        self.indices.__delitem__(key)
        return list.__delitem__(self, key)

    def get_by_index(self, index):
        return self[self.indices.index(index)]

    def get_key(self, key):
        values = SeqUtils.filter_unique_true(
            [obj.get(key) for obj in self.objects])

        if values:
            return values[0]

    @classmethod
    def get_sanitizer(cls, tablefmt=None):
        """
        Return the appropriate sanitizer for the given table format.
        """
        if tablefmt == 'html':
            return SanitationUtils.sanitize_for_xml
        else:
            return SanitationUtils.sanitize_for_table

    def tabulate(self, cols=None, tablefmt=None, highlight_rules=None):
        """
        Create a table string representation of the list of objects.
        """
        objs = self.objects
        sanitizer = self.get_sanitizer(tablefmt)
        if objs:
            if not cols:
                cols = self.report_cols
            assert isinstance(cols, dict), \
                "cols should be a dict, found %s instead: %s" % (
                    type(cols), repr(cols))
            header = [self.objList_type]
            for key, val in cols.items():
                col_header = key
                if isinstance(val, dict) and 'label' in val:
                    col_header = val['label']
                elif isinstance(val, basestring):
                    col_header = val
                header += [col_header]
            table = []
            for obj in objs:
                row = [obj.identifier]

                # process highlighting rules
                if highlight_rules and tablefmt == 'html':
                    classes = []
                    for highlight_class, rule in highlight_rules:
                        if rule(obj):
                            classes.append(highlight_class)
                    row = [" ".join(classes)] + row

                for col in cols.keys():

                    row += [sanitizer(obj.get(col)) or ""]
                    try:
                        SanitationUtils.coerce_unicode(row[-1])
                    except BaseException:
                        Registrar.register_warning(
                            "can't turn row into unicode: %s" %
                            SanitationUtils.coerce_unicode(row))

                table += [row]

            table_str = (tabulate(table, headers=header, tablefmt=tablefmt))
            if highlight_rules and tablefmt == 'html':
                table_str = re.sub(r'<tr><td>([^<]*)</td>', r'<tr class="\1">',
                                   table_str)
                # also delete first row
                table_str = re.sub(r'<tr><th>\s*</th>', r'<tr>', table_str)

            return table_str
        else:
            Registrar.register_warning(
                "cannot tabulate Objlist: there are no objects")
            return ""

    def export_items(
        self, file_path, col_names, dialect=None, encoding="utf8",
        coldata_target=None, coldata_class=None
    ):
        """
        Export the items in the object list to a csv file in the given file path.
        """
        assert file_path, "needs a filepath"
        assert col_names, "needs col_names"
        assert self.objects, "meeds items"
        if coldata_class is None:
            coldata_class = self.coldata_class
        if coldata_target is None:
            coldata_target = self.coldata_target
        with open(file_path, 'w+') as out_file:
            if dialect is None:
                csvdialect = UnicodeCsvDialectUtils.ActOut
            else:
                csvdialect = UnicodeCsvDialectUtils.get_dialect_from_suggestion(
                    dialect)
            if self.DEBUG_ABSTRACT:
                self.register_message(
                    UnicodeCsvDialectUtils.dialect_to_str(csvdialect))
            # import pudb; pudb.set_trace()
            dictwriter = unicodecsv.DictWriter(
                out_file,
                dialect=csvdialect,
                fieldnames=col_names.values(),
                encoding=encoding,
                extrasaction='ignore'
            )
            dictwriter.writerow(col_names)
            objects = [
                object_.to_target_type(
                    coldata_class=coldata_class,
                    coldata_target=coldata_target
                )
                for object_ in self.objects
            ]
            dictwriter.writerows(objects)
        self.register_message("WROTE FILE: %s" % file_path)

    report_cols = OrderedDict([('_row', {'label': 'Row'}), ('index', {})])

ImportObject.container = ObjList

class CsvParseBase(Registrar):
    """
    Base class for Parsing spreadsheet-like formats.
    """

    object_container = ImportObject
    coldata_class = ColDataAbstract
    coldata_gen_target = 'gen-csv'

    def __init__(self, cols, defaults, **kwargs):
        # super(CsvParseBase, self).__init__()
        # Registrar.__init__(self)
        if self.DEBUG_MRO:
            self.register_message('CsvParseBase')

        extra_cols = []
        extra_defaults = OrderedDict()

        self.limit = kwargs.pop('limit', None)
        self.cols = SeqUtils.combine_lists(cols, extra_cols)
        self.defaults = SeqUtils.combine_ordered_dicts(defaults,
                                                       extra_defaults)
        self.object_indexer = self.get_object_rowcount
        self.clear_transients()
        self.source = kwargs.get('source')

    def __getstate__(self):
        return self.__dict__

    def __setstate__(self, copy_dict):
        self.__dict__.update(copy_dict)

    def clear_transients(self):
        if self.DEBUG_MRO:
            self.register_message(' ')
        self.indices = OrderedDict()
        self.objects = OrderedDict()
        self.rowcount = 1

    def register_object(self, object_data):
        if self.DEBUG_MRO:
            self.register_message(' ')
        self.register_anything(
            object_data,
            self.objects,
            self.object_indexer,
            singular=True,
            register_name='objects')

    def analyse_header(self, row):
        sanitized_row = [self.sanitize_cell(cell) for cell in row]
        if self.DEBUG_PARSER:
            self.register_message('sanitized row: %s' % repr(sanitized_row))
        for col in self.cols:
            sanitized_col = self.sanitize_cell(col)
            if sanitized_col in sanitized_row:
                self.indices[col] = sanitized_row.index(sanitized_col)
            if self.indices.get(col) is not None:
                if self.DEBUG_ABSTRACT:
                    self.register_message("indices [%s] = %s" %
                                          (col, self.indices.get(col)))
            else:
                self.register_error(
                    'Could not find index of %s -> %s in %s' %
                    (repr(col), repr(sanitized_col), repr(sanitized_row)))
        if not self.indices:
            warn = UserWarning("could not find any indices")
            self.raise_exception(warn)


    def retrieve_col_from_row(self, col, row):
        # if self.DEBUG_PARSER: print "retrieve_col_from_row | col: ", col
        try:
            index = self.indices[col]
        except KeyError as exc:
            if col in self.defaults:
                return self.defaults[col]
            if self.strict:
                self.register_message(
                    'No default for column ' + str(col) + ' | '
                    + str(exc) + ' ' + unicode(self.defaults)
                )
            return None
        try:
            if self.DEBUG_ABSTRACT:
                self.register_message(u"row [%3d] = %s" %
                                      (index, repr(row[index])))
            # this may break shit
            return row[index]
        except Exception as exc:
            self.register_warning(
                'Could not retrieve ' + str(col) +
                ' from row[' + str(index) + '] | ' +
                str(exc) + ' | ' + repr(row)
            )
            return None

    def sanitize_cell(self, cell):
        """
        Sanitize a singular cell from the raw data before parsing.
        """

        return cell

    @classmethod
    def find_object(cls, search_data, registry, search_keys):
        """
        Search for an object within a registry on search_keys.
        """
        response = None
        matching_sets = []

        for search_key in search_keys:
            value = search_data.get(search_key)
            if value:
                if Registrar.DEBUG_API:
                    Registrar.register_message(
                        "checking search key %s" % search_key)
                matching_objects = set()
                for object_key, object_ in registry.items():
                    if object_.get(search_key) == value:
                        matching_objects.add(object_key)
                matching_sets.append(matching_objects)
        # if Registrar.DEBUG_API:
        #     Registrar.register_message(
        #         "matching_sets: %s" % matching_sets)
        if matching_sets:
            matches = set.intersection(*matching_sets)
            if matches:
                assert \
                len(matches) == 1, \
                (
                    "should only have one match:\n"
                    "-> search_data:\n%s\n"
                    "-> match_keys:\n%s\n"
                    "-> matches:\n%s\n%s"
                ) % (
                    pformat(search_data.items()),
                    pformat(search_keys),
                    pformat(matches),
                    pformat(['%s' % registry.get(match) for match in matches])
                )
                response = registry.get(list(matches)[0])
        return response

    def get_parser_data(self, **kwargs):
        """
        Get data for the parser generalized from get_row_data.

        in this case from row, specified in kwargs, can be overridden in subs.
        """

        if self.DEBUG_MRO:
            self.register_message(' ')
        if 'row_data' in kwargs:
            return kwargs['row_data']
        row = kwargs.get('row', [])
        row_data = OrderedDict()
        for col in self.cols:
            retrieved = self.retrieve_col_from_row(col, row)
            if retrieved is not None and unicode(retrieved) is not u"":
                row_data[col] = self.sanitize_cell(retrieved)
        return row_data

    def get_mandatory_data(self, **_):
        """
        Get mandatory data from provided kwargs.

        Override in subclasses.
        """

        mandatory_data = OrderedDict()
        if self.source:
            mandatory_data['source'] = self.source
        return mandatory_data

    def get_new_obj_container(self, all_data, **kwargs):  # pylint: disable=unused-argument
        """
        Get container for new object.

        Override in subclass.
        """

        if self.DEBUG_MRO:
            self.register_message(' ')
        return kwargs.get('container', self.object_container)

    def get_kwargs(self, all_data, **kwargs):  # pylint: disable=unused-argument
        """
        Use all_data, container and other kwargs to get kwargs for creating new_object.

        Override in subclasses.
        """

        return kwargs

    def get_defaults(self, **kwargs):
        """
        Use kwargs to get defaults for creating new_object.

        Override in subclasses.
        """
        return deepcopy(kwargs.get('defaults', self.defaults))

    # TODO: remove rowcount, rely on self.rowcount?
    def new_object(self, rowcount, **kwargs):
        """
        Create a new ImportObject subclass instance from provided args.

        An import object is created with two pieces of information:
         - data: a dict containing the raw data in the import_object as a dictionary
         - kwargs: extra arguments passed to subclass __init__s to initialize the object
        Subclasses of CsvParseBase override the get_kwargs and get_parser_data methods
        so that they can supply their own arguments to an object's initialization
        """

        if self.DEBUG_PARSER:
            self.register_message(
                'rowcount: {} | kwargs {}'.format(rowcount, kwargs))
        kwargs['row'] = kwargs.get('row', [])
        kwargs['rowcount'] = rowcount
        default_data = self.get_defaults(**kwargs)
        if self.DEBUG_PARSER:
            self.register_message("default_data: {}".format(default_data))
        parser_data = self.get_parser_data(**kwargs)
        if self.DEBUG_PARSER:
            self.register_message("parser_data: {}".format(parser_data))
        # all_data = SeqUtils.combine_ordered_dicts(parser_data, default_data)
        all_data = SeqUtils.combine_ordered_dicts(default_data, parser_data)
        mandatory_data = self.get_mandatory_data(**kwargs)
        # TODO: is this in the wrong order?
        all_data = SeqUtils.combine_ordered_dicts(all_data, mandatory_data)
        if self.DEBUG_PARSER:
            self.register_message("all_data: {}".format(all_data))
        kwargs['container'] = self.get_new_obj_container(all_data, **kwargs)
        if self.DEBUG_PARSER:
            self.register_message("container: {}".format(kwargs['container'].__name__))
        kwargs = self.get_kwargs(all_data, **kwargs)
        if self.DEBUG_PARSER:
            self.register_message("kwargs: {}".format(kwargs))
        object_data = kwargs['container'](all_data, **kwargs)
        return object_data

    def get_empty_instance(self, **kwargs):
        object_data = self.new_object(self.rowcount, row=[], **kwargs)
        self.rowcount += 1
        return object_data

    def process_object(self, object_data):
        """
        Process a parsed object. Override in subclasses.
        """

        pass

    def analyse_rows(self, unicode_rows, file_name="rows", limit=None):
        """
        Analyse a list of unicode rows to create objects.
        """

        if limit and isinstance(limit, int):
            unicode_rows = list(unicode_rows)[:limit]
        if self.DEBUG_PROGRESS:

            # last_print = time()
            rows = []
            try:
                for row in unicode_rows:
                    rows.append(row)
            except Exception as exc:
                warn = Exception("could not append row %d, %s: \n\t%s" %
                                (len(rows), str(exc), repr(rows[-1:])))
                self.raise_exception(warn)
            rowlen = len(rows)
            self.progress_counter = ProgressCounter(rowlen)
            unicode_rows = rows

        for unicode_row in unicode_rows:
            self.rowcount += 1

            if limit and self.rowcount > limit:
                break
            if self.DEBUG_PROGRESS:
                self.progress_counter.maybe_print_update(self.rowcount)
                # now = time()
                # if now - last_print > 1:
                #     last_print = now
                #     print "%d of %d rows processed" % (self.rowcount, rowlen)

            if unicode_row:
                non_unicode = [
                    cell for cell in unicode_row
                    if not isinstance(cell, unicode)
                ]
                # non_unicode = filter(
                #     lambda unicode_cell: not isinstance(unicode_cell, unicode) \
                #                          if unicode_cell else False,
                #     unicode_row)
                assert not non_unicode, "non-empty cells must be unicode objects, {}".format(
                    repr(non_unicode))

            if not any(unicode_row):
                continue

            if not self.indices:
                self.analyse_header(unicode_row)
                continue
            try:
                # if Registrar.DEBUG_TRACE and 'Xero' in str(self.__class__):
                #     import pudb; pudb.set_trace()
                object_data = self.new_object(self.rowcount, row=unicode_row)
            except UserWarning as exc:
                warn = UserWarning("could not process new object: {}". format(exc))
                self.register_warning(
                    warn,
                    "%s:%d" % (file_name, self.rowcount))
                if self.strict:
                    self.raise_exception(warn)
                continue
            else:
                if self.DEBUG_PARSER:
                    self.register_message("%s CREATED" %
                                          object_data.identifier)
            try:
                self.process_object(object_data)
                if self.DEBUG_PARSER:
                    self.register_message("%s PROCESSED" %
                                          object_data.identifier)
            except UserWarning as exc:
                warn = UserWarning("could not process new object: {}".format(exc))
                self.register_error(
                    warn,
                    object_data
                )
                if self.strict:
                    self.raise_exception(warn)
                continue
            try:
                self.register_object(object_data)
                if self.DEBUG_PARSER:
                    self.register_message("%s REGISTERED" %
                                          object_data.identifier)
                    self.register_message("%s" % object_data.__repr__())

            except UserWarning as exc:
                self.register_warning(
                    "could not register new object: {}".format(exc),
                    object_data)
                continue
        if self.DEBUG_PARSER:
            self.register_message("Completed analysis")

        return self.objects

    def analyse_stream(self, byte_file_obj, **kwargs):
        """
        Analyse a stream of bytes and interpret as csv file.

        may want to revert back to this commit if things break:
        https://github.com/derwentx/WooGenerator/commit/c4fabf83d5b4d1e0a4d3ff755cd8eadf1433d253

        Arguments:
        ----
            byte_file_obj (io.IOBase):
                The byte stream to be analysed
            limit (int):
                The number of items to process from the stream
            dialect_suggestion (unicodecsv.Dalect, basestring, optional):
                A suggestion for the dialect to process the csv file as
            encoding (basestring, optional):
                The encoding of the file stream. Defaults to utf8
            stream_name:
                Used to differentiate this stream from others in debugging.

        Raises:
        ----
            UserWarning:
                When analyse_stream called withoud clearing transient first
        """

        limit, dialect_suggestion, encoding, stream_name = \
            (kwargs.get('limit'), kwargs.get('dialect_suggestion'),
             kwargs.get('encoding'), kwargs.get('stream_name'))

        if hasattr(self, 'rowcount') and self.rowcount > 1:
            warn = UserWarning(
                'rowcount should be 0. Make sure clear_transients is being called on ancestors'
            )
            self.raise_exception(warn)
        if encoding is None:
            encoding = "utf8"

        if stream_name is None:
            if hasattr(byte_file_obj, 'name'):
                stream_name = byte_file_obj.name
            else:
                stream_name = 'stream'

        if self.DEBUG_PARSER:
            self.register_message("Analysing stream: {0}, encoding: {1}".
                                  format(stream_name, encoding))

        # I can't imagine this having any problems
        byte_sample = SanitationUtils.coerce_bytes(byte_file_obj.read(1000))
        byte_file_obj.seek(0)

        if self.DEBUG_PARSER:
            self.register_message(
                "dialect_suggestion: %s" % dialect_suggestion
            )

        if dialect_suggestion:
            csvdialect = UnicodeCsvDialectUtils.get_dialect_from_suggestion(
                dialect_suggestion)
        else:
            csvdialect = unicodecsv.Sniffer().sniff(byte_sample)
            assert \
                csvdialect.delimiter == ',' and isinstance(
                    csvdialect.delimiter, str)

        if self.DEBUG_PARSER:
            self.register_message(
                UnicodeCsvDialectUtils.dialect_to_str(csvdialect)
            )

        unicodecsvreader = unicodecsv.reader(
            byte_file_obj, dialect=csvdialect, encoding=encoding, strict=True)
        return self.analyse_rows(
            unicodecsvreader, file_name=stream_name, limit=limit)

    def analyse_file(self,
                     file_name,
                     encoding=None,
                     dialect_suggestion=None,
                     limit=None):
        """
        Call analyse_stream on a given file.
        """
        if self.DEBUG_PARSER:
            self.register_message(
                "dialect_suggestion: %s" % dialect_suggestion
            )

        with open(file_name, 'rbU') as byte_file_obj:
            return self.analyse_stream(
                byte_file_obj,
                stream_name=file_name,
                encoding=encoding,
                dialect_suggestion=dialect_suggestion,
                limit=limit)
        return None

    @classmethod
    def translate_handle_keys(cls, object_data, key_translation):
        """
        Translate keys from one type of dict to another using the key_translation.
        """
        raise DeprecationWarning("Use API whisperer to translate stuff")
        translated = OrderedDict()
        for col, translation in key_translation.items():
            if col in object_data:
                translated[translation] = object_data[col]
        return translated

    def get_obj_list(self):
        """
        Return the objects parsed by this instance in their preferred container.
        """
        list_class = self.object_container.container
        objlist = list_class(self.objects.values())
        return objlist

    def tabulate(self, cols=None, tablefmt=None):
        """
        Provide a string table representation of the objects parsed by this instance.
        """
        objlist = self.get_obj_list()
        return SanitationUtils.coerce_bytes(objlist.tabulate(cols, tablefmt))

    @classmethod
    def print_basic_columns(cls, objects):
        """
        Provide a basic string table representation of the objects parsed by this instance.
        """
        obj_list = cls.object_container.container()
        for _object in objects:
            obj_list.append(_object)

        cols = cls.object_container.container.coldata_class.get_col_data_native('basic')

        SanitationUtils.safe_print(obj_list.tabulate(cols, tablefmt='simple'))
