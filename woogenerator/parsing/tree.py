"""
Classes that add the concept of heirarchy to the CSVParse classes and corresponding helper classes
"""
from __future__ import absolute_import

import weakref
from collections import OrderedDict

from ..utils import Registrar
from .abstract import CsvParseBase, ImportObject, ObjList


class ImportTreeRootableMixin(object):
    pass


class ImportTreeObject(ImportObject):
    """ Implements the tree interface for tree objects """
    is_root = None
    is_item = None
    is_taxo = None
    _depth = None
    verify_meta_keys = []
    child_indexer = Registrar.get_object_rowcount

    def __init__(self, *args, **kwargs):
        try:
            parent = kwargs.pop('parent', None)
            if not self.is_root:
                assert parent is not None, "parent should not be none"
        except (KeyError, AssertionError) as exc:
            import pudb; pudb.set_trace()
            warn = UserWarning(
                "No parent specified, try specifying root as parent. %s" % exc)
            self.raise_exception(warn)
        self.parent = parent

        try:
            depth = kwargs.pop('depth', -1)
            if not self.is_root:
                assert depth is not None
                assert depth >= 0
        except (AssertionError):
            depth = self.parent.depth + 1
        finally:
            self.depth = depth

        try:
            meta = kwargs.pop('meta', None)
            assert meta is not None
        except (AssertionError, KeyError):
            meta = []
        finally:
            self.meta = meta

        for base_class in ImportTreeObject.__bases__:
            if hasattr(base_class, '__init__'):
                base_class.__init__(self, *args, **kwargs)

        if self.DEBUG_PARSER:
            self.register_message(
                'About to register child: %s' % str(self.items()))

        self.process_meta()
        if not self.is_root:
            parent.register_child(self)

        self.child_register = OrderedDict()

        self.verify_meta()

    #
    def verify_meta(self):
        # return
        for key in self.verify_meta_keys:
            if self.DEBUG_PARSER:
                self.register_message("CHECKING KEY: %s" % key)
            assert key in self.keys(), \
            "tree_verify_meta: key %s must be set in %s object" % (
                str(key), type(self)
            )

    #
    @property
    def ancestors(self):
        "gets all ancestors not including self or root"
        this = self.parent
        ancestors = []
        while this and not this.is_root:
            ancestors.insert(0, this)
            this = this.parent
        return ancestors

    #
    def register_child(self, child_data):
        assert child_data, "child_data must be valid"
        self.register_anything(
            child_data,
            self.child_register,
            indexer=self.child_indexer,
            singular=True,
            # resolver = self.passive_resolver,
            register_name='parent'
        )

    @property
    def children(self):
        return self.child_register.values()
    #

    @property
    def siblings(self):
        parent = self.parent
        if parent:
            return parent.children
        else:
            return []

    def get_copy_args(self):
        args = super(ImportTreeObject, self).get_copy_args()
        args.update(
            depth=self.depth,
            parent=self.parent,
            meta=self.meta,
        )
        return args

    def process_meta(self):
        pass

    @property
    def inheritence_ancestors(self):
        return self.ancestors

    def inherit_key(self, key):
        if not self.get(key):
            inheritence = filter(None, map(
                lambda x: x.get(key),
                self.inheritence_ancestors
            ))
            if inheritence:
                self[key] = inheritence[-1]

    @property
    def depth(self):
        return self._depth

    @depth.setter
    def depth(self, depth):
        assert(isinstance(depth, int))
        self._depth = depth

    @property
    def identifier_delimeter(self):
        # delim = super(ImportTreeObject, self).identifier_delimeter
        return "=" * self.depth

    @property
    def taxo_ancestors(self):
        return filter(lambda x: x.is_taxo, self.ancestors)

    def get_ancestor_key(self, key):
        # ancestors = self.getAncestors()
        return [ancestor.get(key) for ancestor in self.ancestors]

    def get_ancestor_self_key(self, key):
        # ancestors = self.getAncestors()
        return [ancestor.get(key) for ancestor in [self] + self.ancestors]

    def get_first_filtd_anc_self_key(self, key):
        ancestor_values = self.get_ancestor_self_key(key)
        filtered_ancestor_values = [
            value for value in ancestor_values if value]
        if filtered_ancestor_values[0]:
            return filtered_ancestor_values[0]

class ImportTreeRoot(ImportTreeObject):
    is_root = True

    def __init__(self, *args, **kwargs):
        data = OrderedDict()
        ImportTreeObject.__init__(self, data, rowcount=-1, row=[])

    @property
    def title(self):
        return "root"

    @property
    def wpid(self):
        return "-1"


class ImportTreeItem(ImportTreeObject):
    is_item = True

    @property
    def identifier_delimeter(self):
        return super(ImportTreeItem, self).identifier_delimeter + '>'

    @property
    def item_ancestors(self):
        return filter(lambda x: x.is_item, self.ancestors)


class ImportTreeTaxo(ImportTreeObject):
    is_taxo = True

    @property
    def identifier_delimeter(self):
        return super(ImportTreeTaxo, self).identifier_delimeter + '#'

    def get_identifier_delimeter(self):
        exc = DeprecationWarning(
            "use .identifier_delimeter instead of .get_identifier_delimeter()")
        self.register_error(exc)
        return self.identifier_delimeter
        # return super(ImportTreeTaxo, self).get_identifier_delimeter() + '#'


class ItemList(ObjList):
    supported_type = ImportTreeItem
    objList_type = 'items'

ImportTreeItem.container = ItemList

class TaxoList(ObjList):
    supported_type = ImportTreeTaxo
    objList_type = 'taxos'

ImportTreeTaxo.container = TaxoList

class ImportStack(list):

    def top_has_parent(self):
        return len(self) > 1

    def get_top_parent(self):
        if self.top_has_parent():
            return self[-2]
        else:
            return None

    def is_empty(self):
        return len(self) is 0

    def get_top(self):
        return None if self.is_empty() else self[-1]

    def retrieve_key(self, key):
        vals = []
        for layer in self:
            try:
                vals.append(layer[key])
            except (IndexError, KeyError):
                vals.append('')
        return vals

    def get_left_slice(self, index):
        return ImportStack(self[:index])

    def __repr__(self):
        return ''.join([
            '<%s>' % self.__class__.__name__,
            '[%s]' % ','.join([str(x.index) for x in self]),
        ])

    def __getslice__(self, i, j):
        return self.__class__(list.__getslice__(self, i, j))

    def display(self):
        out = "\n"
        for object_data in self:
            try:
                out += object_data.identifier + "\n"
            except BaseException:
                out += repr(object_data) + "\n"
        return out

    def copy(self):
        return ImportStack(self[:])


class CsvParseTreeMixin(object):
    """
    Provide mixin for parsing tree-like data structures
    """
    root_container = ImportTreeRoot
    object_container = ImportTreeObject
    item_container = ImportTreeItem
    taxo_container = ImportTreeTaxo

    def clear_transients(self):
        self.root_data = self.root_container()
        # TODO: what if items, taxos were weakrefs?
        self.items = OrderedDict()
        # self.items = weakref.WeakValueDictionary()
        self.taxos = OrderedDict()
        # self.taxos = weakref.WeakValueDictionary()
        self.stack = ImportStack()

    def register_item(self, item_data):
        assert isinstance(item_data, ImportTreeObject)
        assert item_data.is_item
        self.register_anything(
            item_data,
            self.items,
            indexer=self.item_indexer,
            singular=True,
            register_name='items'
        )

    def register_taxo(self, taxo_data):
        assert isinstance(taxo_data, ImportTreeObject)
        assert taxo_data.is_taxo
        self.register_anything(
            taxo_data,
            self.taxos,
            indexer=self.taxo_indexer,
            singular=True,
            # resolver = self.passive_resolver,
            register_name='taxos',
        )

    def register_object(self, object_data):
        assert isinstance(object_data, ImportTreeObject)
        if object_data.is_item:
            self.register_item(object_data)
        if object_data.is_taxo:
            self.register_taxo(object_data)

    def assign_parent(self, parent_data=None, item_data=None):
        assert isinstance(item_data, ImportTreeObject)
        if not parent_data:
            parent_data = self.root_data
        assert isinstance(parent_data, ImportTreeObject)
        parent_data.register_child(item_data)
        item_data.registerParent(parent_data)

    def is_taxo_depth(self, depth):
        return depth < self.taxo_depth and depth >= 0

    def is_item_depth(self, depth):
        return depth >= self.taxo_depth and depth < self.max_depth

    def get_empty_instance(self, **kwargs):
        for key in kwargs['container'].verify_meta_keys:
            if not kwargs['row_data'].get(key):
                kwargs['row_data'][key] = ''
        if not kwargs.get('parent'):
            kwargs['parent'] = self.root_data
        return CsvParseBase.get_empty_instance(self, **kwargs)

class CsvParseTree(CsvParseBase, CsvParseTreeMixin):
    object_container = CsvParseTreeMixin.object_container
    item_indexer = CsvParseBase.get_object_rowcount
    taxo_indexer = CsvParseBase.get_object_rowcount

    def __init__(self, cols, defaults, taxo_depth,
                 item_depth, meta_width=0, **kwargs):
        self.taxo_depth = taxo_depth
        self.item_depth = item_depth
        # self.max_depth  = taxo_depth + item_depth
        self.meta_width = meta_width
        for base_class in [CsvParseBase]:
            if hasattr(base_class, '__init__'):
                base_class.__init__(self, cols, defaults, **kwargs)

    @property
    def max_depth(self):
        return self.taxo_depth + self.item_depth

    def clear_transients(self):
        for base_class in CsvParseTree.__bases__:
            if hasattr(base_class, 'clear_transients'):
                base_class.clear_transients(self)

    def register_object(self, object_data):
        assert isinstance(object_data, ImportTreeObject)
        for base_class in CsvParseTree.__bases__:
            if hasattr(base_class, 'clear_transients'):
                base_class.register_object(self, object_data)

    def depth(self, row):
        sanitized_row = [self.sanitize_cell(cell) for cell in row]
        for i, sanitized_cell in enumerate(sanitized_row):
            if sanitized_cell:
                return i
            if i >= self.max_depth:
                break
        return -1

    def extract_meta(self, row, this_depth):
        # return [row[this_depth+i*self.max_depth]for i in
        # range(self.meta_width)]
        meta = [''] * self.meta_width
        sanitized_row = map(self.sanitize_cell, row)
        if sanitized_row:
            for i in range(self.meta_width):
                row_index = this_depth + i * self.max_depth
                try:
                    meta[i] = sanitized_row[row_index]
                except IndexError as exc:
                    meta[i] = ""
                    warn = UserWarning("could not get meta[{}] | {}".format(i, exc))
                    self.register_error(warn)
        return meta

    def get_new_obj_container(self, all_data, **kwargs):
        container = super(CsvParseTree, self).get_new_obj_container(
            all_data, **kwargs)
        depth = kwargs['depth']
        assert depth is not None, "depth should be available to CsvParseTree.get_new_obj_container"
        if self.is_taxo_depth(depth):
            container = self.taxo_container
        elif self.is_item_depth(depth):
            container = self.item_container
        return container

    def get_kwargs(self, all_data, **kwargs):
        kwargs = super(CsvParseTree, self).get_kwargs(
            all_data, **kwargs
        )
        assert \
            issubclass(kwargs['container'], ImportTreeObject), \
            "Container should inherit from tree object, instead found %s" % \
                kwargs['container'].__name__

        # sanity check kwargs has been called with correct arguments
        for key in ['row', 'rowcount']:
            assert key in kwargs

        try:
            depth = kwargs['depth']
            assert depth is not None
        except (AssertionError, KeyError):
            kwargs['depth'] = self.depth(kwargs['row'])
        if self.DEBUG_TREE:
            self.register_message("depth: {}".format(kwargs['depth']))
        try:
            meta = kwargs['meta']
            assert meta is not None
        except (AssertionError, KeyError):
            kwargs['meta'] = self.extract_meta(kwargs['row'], kwargs['depth'])
        if self.DEBUG_TREE:
            self.register_message("meta: {}".format(kwargs['meta']))

        parent = kwargs.pop('parent', None)
        if not parent:
            try:
                stack = kwargs.pop('stack', None)
                # stack = kwargs['stack']
                # del kwargs['stack']
                assert stack is not None
            except (AssertionError):
                self.refresh_stack(kwargs['rowcount'], kwargs[
                    'row'], kwargs['depth'])
                stack = self.stack
            assert isinstance(stack, ImportStack)
            if self.DEBUG_TREE:
                self.register_message("stack: {}".format(stack))

            parent = stack.get_top()
            if parent is None:
                parent = self.root_data
            if self.DEBUG_TREE:
                self.register_message("parent: {}".format(parent))
        kwargs['parent'] = parent

        # sanity check
        for key in ['meta', 'parent', 'depth']:
            assert kwargs[key] is not None
        return kwargs

    def new_object(self, rowcount, **kwargs):
        kwargs['row'] = kwargs.get('row', [])
        if self.DEBUG_TREE:
            self.register_message(u"new tree object! rowcount: %d, row: %s, kwargs: %s" %
                                  (rowcount, unicode(kwargs['row']), unicode(kwargs)))

        # TODO: replace the following with this:
        # depth = kwargs.pop('depth')
        # if depth is None or depth is '':
        #     depth = self.depth(kwargs['row'])
        #     kwargs['depth'] = depth
        try:
            depth = kwargs['depth']
            assert depth is not None
        except BaseException:
            depth = self.depth(kwargs['row'])
            kwargs['depth'] = depth
        if self.DEBUG_TREE:
            self.register_message("depth: %d" % (depth))

        return super(CsvParseTree, self).new_object(rowcount, **kwargs)

    def refresh_stack(self, rowcount, row, this_depth):
        try:
            assert this_depth >= 0, "stack should not be broken"
        except AssertionError as exc:
            warn = UserWarning(str(exc))
            self.raise_exception(warn)
        del self.stack[this_depth:]
        for depth in range(len(self.stack), this_depth):
            layer = self.new_object(rowcount, row=row, depth=depth)
            self.stack.append(layer)
            # self.initializeObject(layer)
        assert len(
            self.stack) == this_depth, "stack should have been properly refreshed"

    def refresh_stack_from_object(self, object_data):
        assert isinstance(object_data, ImportTreeObject)
        return self.refresh_stack(
            object_data.rowcount, object_data.row, object_data.depth)

    def process_object(self, object_data):
        assert isinstance(self.stack, ImportStack)
        oldstack = self.stack[:]
        assert isinstance(
            oldstack, ImportStack), 'stack should be ImportStack not %s' % oldstack.__class__.__name__
        self.refresh_stack_from_object(object_data)
        assert isinstance(
            self.stack, ImportStack), 'stack should be ImportStack not %s' % self.stack.__class__.__name__
        assert oldstack == self.stack, 'self.stack (%s) is inconsistent with %s' % (
            oldstack.display(), self.stack.display())
        self.stack.append(object_data)
        super(CsvParseTree, self).process_object(object_data)

    def verify_item(self, item_data):
        index = self.item_indexer(item_data)
        item_id = id(item_data)
        lookup_data = self.items[index]
        lookup_id = id(lookup_data)
        assert item_id == lookup_id, "item has deviated from its place in items"

    # def analyse_file(self, file_name):
    #     super(CsvParseTree, self).analyse_file(file_name)

    def find_taxo(self, taxo_data):
        response = None
        for key in [self.taxo_container.rowcount_key]:
            value = taxo_data.get(key)
            if value:
                for taxo in self.taxos:
                    if taxo.get(key) == value:
                        response = taxo
                        return response
        return response

    def get_items(self):
        exc = DeprecationWarning("Use .items instead of .get_items()")
        self.register_error(exc)
        return self.items

    def get_taxos(self):
        exc = DeprecationWarning("use .taxos instead of .get_taxos()")
        self.register_error(exc)
        return self.taxos
