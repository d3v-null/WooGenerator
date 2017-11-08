"""
Introduce the shop products and categories interfaces to CSV Parser classes.
"""
from __future__ import absolute_import

import bisect
import os
from collections import OrderedDict

from ..coldata import ColDataProd, ColDataCat
from ..utils import Registrar, SanitationUtils
from .abstract import ObjList
from .gen import CsvParseGenMixin
from .tree import ItemList, TaxoList

class ImportShopMixin(object):
    "Base mixin class for shop objects (products, categories, images)"
    is_product = None
    is_category = None
    is_variable = None
    is_variation = None
    #container = ObjList

    def __init__(self, *args, **kwargs):
        # TODO: Remove any dependencies on __init__ in mixins
        if Registrar.DEBUG_MRO:
            Registrar.register_message('ImportShopMixin')
        if Registrar.DEBUG_SHOP:
            self.register_message("creating shop object; %s %s %s %s" % (
                'is_product' if self.is_product else '!is_product',
                'is_category' if self.is_category else '!is_category',
                'is_variable' if self.is_variable else '!is_variable',
                'is_variation' if self.is_variation else '!is_variation'
            ))
        self.attributes = OrderedDict()
        self.images = OrderedDict()

    # @classmethod
    # def get_new_obj_container(cls):
    #     exc = DeprecationWarning("use .container instead of .get_new_obj_container()")
    #     self.register_error(exc)
    #     return cls.container
    #     # return ObjList

    def register_attribute(self, attr, val, var=False):
        if Registrar.DEBUG_SHOP:
            self.register_message(
                "attr: %s ; val: %s ; var: %s" % (attr, val, var))
        if var:
            assert self.is_product, "sanity: must be a product to assign ba"
            assert self.is_variation or self.is_variable
        attrs = self.attributes
        if attr not in attrs.keys():
            attrs[attr] = {
                'values': [val],
                'visible': 1,
                'variation': 1 if var else 0
            }
            if var:
                attrs[attr]['default'] = val
        elif val not in attrs[attr]['values']:
            attrs[attr]['values'].append(val)
        if var:
            if not attrs[attr]['default']:
                attrs[attr]['default'] = val
            attrs[attr]['variation'] = 1

        assert attrs == self.attributes, "sanity: something went wrong assigning attribute"

    def register_image(self, img_data):
        assert isinstance(img_data, ImportShopImgMixin)
        file_name = img_data.file_name
        if file_name not in self.images:
            self.register_anything(
                img_data,
                self.images,
                indexer=file_name,
                singular=True
            )
        self.images[file_name].register_attachment(self)

    def to_api_data(self, col_data, target_api):
        api_data = OrderedDict()
        if self.is_category:
            for col, col_data in col_data.get_wpapi_category_cols(target_api).items():
                if col in self:
                    try:
                        target_api_key = col_data[target_api]['key']
                    except BaseException:
                        target_api_key = col
                    api_data[target_api_key] = self[col]
            if self.parent and self.parent.wpid:
                api_data['parent'] = self.parent.wpid
        else:
            assert self.is_product
            for col, col_data in col_data.get_wpapi_core_cols(target_api).items():
                if col in self:
                    try:
                        target_api_key = col_data[target_api]['key']
                    except BaseException:
                        target_api_key = col
                    api_data[target_api_key] = self[col]
            for col, col_data in col_data.get_wpapi_meta_cols(target_api).items():
                if col in self:
                    try:
                        target_api_key = col_data[target_api]['key']
                    except BaseException:
                        target_api_key = col
                    if 'meta' not in api_data:
                        api_data['meta'] = {}
                    api_data['meta'][target_api_key] = self[col]
            if self.is_variable:
                variations = []
                for variation in self.variations.values():
                    variation_data = variation.to_api_data(col_data, target_api)
                    variations.append(variation_data)
                api_data['variations'] = variations
        return api_data

class ImportShopProductMixin(object):
    # category_indexer = Registrar.get_object_index
    category_indexer = Registrar.get_object_rowcount
    # category_indexer = CsvParseGenMixin.get_full_name_sum
    # category_indexer = CsvParseGenMixin.get_name_sum
    product_type = None
    is_product = True

    def __init__(self, *args, **kwargs):
        # TODO: Remove any dependencies on __init__ in mixins

        if Registrar.DEBUG_MRO:
            Registrar.register_message('ImportShopProductMixin')
        # super(ImportShopProductMixin, self).__init__(*args, **kwargs)
        self.categories = OrderedDict()

    def register_category(self, cat_data):
        self.register_anything(
            cat_data,
            self.categories,
            # indexer = self.getSum,
            indexer=self.category_indexer,
            singular=True,
            resolver=self.duplicate_obj_exc_resolver,
            register_name='product categories'
        )

    def join_category(self, cat_data):
        self.register_category(cat_data)
        cat_data.register_member(self)

    @property
    def type_name(self):
        return self.product_type

class ImportShopImgMixin(object):
    file_path_key = 'file_path'
    source_url_key = 'source_url'

    verify_meta_keys = [
        file_path_key
    ]

    def __init__(self, *args, **kwargs):
        self.attachments = ShopObjList()
        self.is_valid = True

    @property
    def file_name(self):
        if self[self.file_path_key]:
            return os.path.basename(self[self.file_path_key])
        elif self[self.source_url_key]:
            return os.path.basename(self[self.source_url_key])

    @property
    def index(self):
        return self.file_name

    def register_attachment(self, attach_data):
        self.attachments.append(attach_data)

    def invalidate(self, reason=""):
        if self.DEBUG_IMG:
            if not reason:
                reason = "IMG INVALID"
            self.register_error(reason, self.file_name)
        self.is_valid = False

class ShopProdList(ItemList):
    "Container for shop products"
    objList_type = 'products'
    report_cols = ColDataProd.get_report_cols()
    supported_type = ImportShopProductMixin

    def append(self, object_data):
        assert issubclass(object_data.__class__, ImportShopMixin), \
            "object must be subclass of ImportShopMixin not %s : %s" % (
                SanitationUtils.coerce_unicode(object_data.__class__),
                SanitationUtils.coerce_unicode(object_data)
        )
        return super(ShopProdList, self).append(object_data)

ImportShopProductMixin.container = ShopProdList

class ImportShopProductSimpleMixin(ImportShopProductMixin):
    product_type = 'simple'


class ImportShopProductVariableMixin(ImportShopProductMixin):
    product_type = 'variable'
    is_variable = True

    def __init__(self, *args, **kwargs):
        if Registrar.DEBUG_MRO:
            Registrar.register_message('ImportShopProductVariableMixin')
        # super(ImportShopProductVariableMixin, self).__init__(*args, **kwargs)
        self.variations = OrderedDict()

    def register_variation(self, var_data):
        assert var_data.is_variation
        self.register_anything(
            var_data,
            self.variations,
            indexer=var_data.codesum,
            singular=True,
            register_name="product variations"
        )

    def get_variations(self):
        exc = DeprecationWarning(
            "use .variations instead of .get_variations()")
        self.register_error(exc)
        return self.variations


class ImportShopProductVariationMixin(ImportShopProductMixin):
    product_type = 'variable-instance'
    is_variation = True

    def register_parent_product(self, parent_data):
        assert issubclass(type(parent_data), ImportShopProductVariableMixin)
        self.parent_product = parent_data
        self['parent_SKU'] = parent_data.codesum

    def join_variable(self, parent_data):
        assert issubclass(type(parent_data), ImportShopProductVariableMixin)
        self.register_parent_product(parent_data)
        parent_data.register_variation(self)

    def get_parent_product(self):
        return self.parent_product


class ImportShopCategoryMixin(object):
    is_category = True
    is_product = False

    def __init__(self, *args, **kwargs):
        if Registrar.DEBUG_MRO:
            Registrar.register_message('ImportShopCategoryMixin')
        # super(ImportShopCategoryMixin, self).__init__(*args, **kwargs)
        self.members = OrderedDict()

    def register_member(self, item_data):
        self.register_anything(
            item_data,
            self.members,
            # indexer = self.getSum,
            indexer=item_data.rowcount,
            singular=True,
            resolver=self.passive_resolver,
            register_name='product categories'
        )

class ShopCatList(TaxoList):
    report_cols = ColDataCat.get_category_cols()
    supported_type = ImportShopCategoryMixin

ImportShopCategoryMixin.container = ShopCatList

class ShopObjList(ObjList):
    supported_type = ImportShopMixin

    def __init__(self, objects=None, indexer=None):
        self.is_valid = True
        self.products = ShopProdList()
        self.categories = ShopCatList()
        self._objects = ObjList()
        super(ShopObjList, self).__init__(objects, indexer=indexer)

    @property
    def objects(self):
        return self.products + self.categories + self._objects

    @property
    def title(self):
        return self.get_key('fullnamesum')

    @property
    def description(self):
        description = self.get_key('HTML Description')
        if not description:
            description = self.get_key('descsum')
        if not description:
            description = self.name
        return description

    @property
    def has_product_categories(self):
        return self.products or any([
            category.children for category in self.categories
        ])

    def append(self, object_data):
        assert isinstance(object_data, ImportShopMixin)
        if object_data.is_category:
            container = self.categories
        elif object_data.is_product:
            container = self.products
        else:
            container = self._objects
            # warn = UserWarning("shopObjList appended non-product, non-category: %s" % object_data)
            # self.register_warning(warn)
            # raise warn

        bisect.insort(container, object_data)

    def extend(self, iterable):
        for thing in iterable:
            self.append(thing)

    def __iter__(self):
        for thing in self.categories:
            yield thing
        for thing in self.products:
            yield thing
        for thing in self._objects:
            yield thing

    def __reversed__(self, *args, **kwargs):
        return list(self.__iter__).__reversed__(*args, **kwargs)

    def __sizeof__(self, *args, **kwargs):
        return list(self.__iter__).__sizeof__(*args, **kwargs)

    def count(self, *args, **kwargs):
        return list(self.__iter__).count(*args, **kwargs)

    def index(self, *args, **kwargs):
        return list(self.__iter__).index(*args, **kwargs)

    def insert(self, index, thing):
        return self.append(thing)

    def remove(self, value):
        if value in self.categories:
            return self.categories.remove(value)
        if value in self.products:
            return self.products.remove(value)
        if value in self._objects:
            return self._objects.remove(value)

class CsvParseShopMixin(object):
    """
    Mixin class provides shop interface for Parser classes
    """
    object_container = ImportShopMixin
    product_container = ImportShopProductMixin
    simple_container = ImportShopProductSimpleMixin
    variable_container = ImportShopProductVariableMixin
    variation_container = ImportShopProductVariationMixin
    category_container = ImportShopCategoryMixin
    product_indexer = CsvParseGenMixin.get_code_sum
    category_indexer = CsvParseGenMixin.get_code_sum
    variation_indexer = CsvParseGenMixin.get_code_sum
    product_resolver = Registrar.resolve_conflict
    image_resolver = Registrar.passive_resolver
    do_images = True

    # products = None
    # categories = None
    # attributes = None
    # vattributes = None
    # variations = None

    # def __init__(self, *args, **kwargs):
    #     if args:
    #         pass # gets rid of unused args warnings
    #     if kwargs:
    #         pass # gets rid of unused kwargs warnings
    #     self.product_indexer = self.get_code_sum
    #     self.category_indexer = self.get_code_sum

    @property
    def containers(self):
        return {
            'simple': self.simple_container,
            'variable': self.variable_container,
            'variation': self.variation_container,
            'category': self.category_container
        }

    def clear_transients(self):
        if Registrar.DEBUG_MRO:
            Registrar.register_message(' ')
        # super(CsvParseShopMixin,self).clear_transients()

        # TODO: what if products, categories, variations, images were weakrefs?

        self.products = OrderedDict()
        # self.products = weakref.WeakValueDictionary()
        self.categories = OrderedDict()
        # self.categories = weakref.WeakValueDictionary()
        self.attributes = OrderedDict()
        self.vattributes = OrderedDict()
        self.variations = OrderedDict()
        # self.variations = weakref.WeakValueDictionary()

        # Images now stores image objects instead of products
        self.images = OrderedDict()
        # self.images = weakref.WeakValueDictionary()

        self.categories_name = OrderedDict()

    def register_product(self, prod_data):
        if Registrar.DEBUG_SHOP:
            Registrar.register_message(
                "registering product %s" % prod_data.identifier)
        assert prod_data.is_product
        self.register_anything(
            prod_data,
            self.products,
            indexer=self.product_indexer,
            singular=True,
            resolver=self.product_resolver,
            register_name='products'
        )

    def register_attachment(self, img_data, object_data=None):
        if self.DEBUG_IMG:
            self.register_message("attaching %s to %s" % (img_data, object_data))
        if object_data:
            object_data.register_image(img_data)
            if self.DEBUG_IMG:
                self.register_message("object_data.images: %s" % (object_data.images.keys()))
                self.register_message("img_data.attachments: %s" % list(img_data.attachments.__iter__()))


    def register_image(self, img_data):
        assert isinstance(img_data, ImportShopImgMixin)
        file_name = img_data.file_name
        assert isinstance(file_name, basestring)
        assert file_name is not ""
        self.register_anything(
            img_data,
            self.images,
            indexer=file_name,
            singular=True,
            resolver=self.image_resolver,
            register_name='images'
        )

    def get_products(self):
        exc = DeprecationWarning("Use .products instead of .get_products()")
        self.register_error(exc)
        if Registrar.DEBUG_SHOP:
            Registrar.register_message(
                "returning products: {}".format(self.products.keys()))
        return self.products

    def register_object(self, object_data):
        if Registrar.DEBUG_MRO:
            Registrar.register_message(' ')
        # super(CsvParseShopMixin, self).register_object(object_data)
        if issubclass(type(object_data), ImportShopProductMixin):
            if issubclass(type(object_data), ImportShopProductVariationMixin):
                assert \
                    object_data.is_variation, \
                    "object_data not variation %s, obj is_variation: %s, cls is_variation; %s" \
                    % (
                        type(object_data),
                        repr(object_data.is_variation),
                        repr(type(object_data).is_variation)
                    )
                parent_data = object_data.parent
                assert parent_data and parent_data.is_variable
                self.register_variation(parent_data, object_data)
            else:
                self.register_product(object_data)
            if Registrar.DEBUG_SHOP:
                Registrar.register_message("Object is product")
        else:
            if Registrar.DEBUG_SHOP:
                Registrar.register_message("Object is not product")

    def register_category(self, cat_data):
        assert\
            issubclass(type(cat_data), ImportShopCategoryMixin), \
            "cat_data should subclass ImportShopCategoryMixin not %s" % str(
                type(cat_data))
        self.register_anything(
            cat_data,
            self.categories,
            indexer=self.category_indexer,
            resolver=self.passive_resolver,
            singular=True,
            register_name='categories'
        )
        self.register_anything(
            cat_data,
            self.categories_name,
            indexer=cat_data.cat_name,
            singular=False
        )

    def join_category(self, cat_data, item_data=None):
        if item_data:
            assert\
                issubclass(type(item_data), ImportShopProductMixin), \
                "item_data should be ImportShopProductMixin not %s" % str(
                    type(item_data))
            # for product_cat in item_data.categories:
            #     assert self.category_indexer(product_cat) != self.category_indexer(cat_data)
            item_data.join_category(cat_data)

    def register_join_category(self, cat_data, item_data=None):
        self.register_category(cat_data)
        self.join_category(cat_data, item_data)

    def register_variation(self, parent_data, var_data):
        assert issubclass(type(parent_data), ImportShopProductVariableMixin)
        assert \
            issubclass(type(var_data), ImportShopProductVariationMixin), \
            "var_data should subclass ImportShopProductVariationMixin instead %s" % type(
                var_data)
        assert parent_data.is_variable
        assert var_data.is_variation, "var_data should be a variation, is %s instead. type: %s" \
            % (repr(var_data.is_variable), repr(type(var_data)))
        # if self.DEBUG_API:
        # self.register_message("about to register variation: %s with %s" %
        # self.)
        self.register_anything(
            var_data,
            self.variations,
            indexer=self.variation_indexer,
            singular=True,
            resolver=self.duplicate_obj_exc_resolver,
            register_name='variations'
        )

        var_data.join_variable(parent_data)

    def register_attribute(self, object_data, attr, val, var=False):
        try:
            attr = str(attr)
            assert isinstance(attr, (str, unicode)), 'Attribute must be a string not {}'.format(
                type(attr).__name__)
            assert attr is not '', 'Attribute must not be empty'
            assert attr[
                0] is not ' ', 'Attribute must not start with whitespace or '
        except AssertionError as exc:
            warn = UserWarning("could not register attribute: {}".format(exc))
            self.register_error(warn)
            if self.strict:
                self.raise_exception(warn)
        else:
            object_data.register_attribute(attr, val, var)
            self.register_anything(
                val,
                self.attributes,
                indexer=attr,
                singular=False,
                register_name='Attributes'
            )
            if var:
                self.register_anything(
                    val,
                    self.vattributes,
                    indexer=attr,
                    singular=False,
                    register_name='Variable Attributes'
                )

    def to_str_tree_recursive(self, cat_data):
        response = ''
        # print "stringing cat %s" % repr(cat_data)
        for child in cat_data.children:
            if child.is_root or not getattr(child, 'is_category'):
                continue
            registered = self.category_indexer(child) in self.categories.keys()
            response += " | ".join([
                "%-5s" % ((child.depth) * ' ' + '*'),
                "%-16s" % str(child.get(self.object_container.codesum_key))[:16],
                "%50s" % str(child.get(self.object_container.title_key))[:50],
                "r:%5s" % str(child.rowcount)[:10],
                "w:%5s" % str(child.get(self.object_container.wpid_key))[:10],
                "%1s" % "R" if registered else " "
                # "%5s" % child.wpid
            ])
            response += '\n'
            response += self.to_str_tree_recursive(child)
        return response

    def to_str_tree(self):
        return self.to_str_tree_recursive(self.root_data)
