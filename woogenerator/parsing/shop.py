"""
Introduce the shop products and categories interfaces to CSV Parser classes.
"""
from __future__ import absolute_import

import bisect
from collections import OrderedDict

from ..coldata import ColDataProd
from ..utils import Registrar, SanitationUtils
from .abstract import ObjList
from .gen import CsvParseGenMixin
from .tree import ItemList


class ShopProdList(ItemList):
    "Container for shop products"
    objList_type = 'products'
    report_cols = ColDataProd.get_report_cols()

    def append(self, object_data):
        assert issubclass(object_data.__class__, ImportShopMixin), \
            "object must be subclass of ImportShopMixin not %s : %s" % (
                SanitationUtils.coerce_unicode(object_data.__class__),
                SanitationUtils.coerce_unicode(object_data)
        )
        return super(ShopProdList, self).append(object_data)


class ShopCatList(ItemList):
    report_cols = ColDataProd.get_report_cols()


class ShopObjList(ObjList):

    def __init__(self, file_name=None, objects=None, indexer=None):
        self.file_name = file_name
        self.is_valid = True
        if not self.file_name:
            self.is_valid = False
        self.products = ShopProdList()
        self.categories = ShopCatList()
        self._objects = ObjList()
        super(ShopObjList, self).__init__(objects, indexer=indexer)

    @property
    def objects(self):
        return self.products + self.categories + self._objects

    @property
    def name(self):
        exc = DeprecationWarning(".name deprecated")
        self.register_error(exc)
        raise exc

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

    # @property
    # def is_valid(self):
    #     return self._isValid
    #
    # @property
    # def file_name(self):
    #     return self._fileName

    def append(self, object_data):
        assert isinstance(object_data, ImportShopMixin)
        if object_data.isCategory:
            container = self.categories
        elif object_data.isProduct:
            container = self.products
        else:
            container = self._objects

        if object_data not in container:
            bisect.insort(container, object_data)

    def invalidate(self, reason=""):
        if self.DEBUG_IMG:
            if not reason:
                reason = "IMG INVALID"
            self.register_error(reason, self.file_name)
        self.is_valid = False


class ImportShopMixin(object):
    "Base class for shop objects (products, categories)"
    isProduct = None
    isCategory = None
    isVariable = None
    isVariation = None
    #container = ObjList

    def __init__(self, *args, **kwargs):
        if Registrar.DEBUG_MRO:
            Registrar.register_message('ImportShopMixin')
        if Registrar.DEBUG_SHOP:
            self.register_message("creating shop object; %s %s %s %s" % (
                'isProduct' if self.isProduct else '!isProduct',
                'isCategory' if self.isCategory else '!isCategory',
                'isVariable' if self.isVariable else '!isVariable',
                'isVariation' if self.isVariation else '!isVariation'
            ))
        super(ImportShopMixin, self).__init__(*args, **kwargs)
        self.attributes = OrderedDict()
        self.images = []

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
            assert self.isProduct, "sanity: must be a product to assign ba"
            assert self.isVariation or self.isVariable
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

    def get_attributes(self):
        exc = DeprecationWarning(
            "use .attributes instead of .get_attributes()")
        self.register_error(exc)
        return self.attributes

    def register_image(self, image):
        assert isinstance(image, (str, unicode))
        this_images = self.images
        if image not in this_images:
            this_images.append(image)
            # parent = self.getParent()
            # parentImages = parent.get_images()
            # if not parentImages:
            #     parent.register_image(image)

    def get_images(self):
        exc = DeprecationWarning("use .images instead of .get_images()")
        self.register_error(exc)
        return self.images

    def to_api_data(self, col_data, api):
        api_data = OrderedDict()
        if self.isCategory:
            for col, col_data in col_data.get_wpapi_category_cols(api).items():
                if col in self:
                    try:
                        wp_api_key = col_data[api]['key']
                    except:
                        wp_api_key = col
                    api_data[wp_api_key] = self[col]
            if self.parent and self.parent.wpid:
                api_data['parent'] = self.parent.wpid
        else:
            assert self.isProduct
            for col, col_data in col_data.get_wpapi_core_cols(api).items():
                if col in self:
                    try:
                        wp_api_key = col_data[api]['key']
                    except:
                        wp_api_key = col
                    api_data[wp_api_key] = self[col]
            for col, col_data in col_data.get_wpapi_meta_cols(api).items():
                if col in self:
                    try:
                        wp_api_key = col_data[api]['key']
                    except:
                        wp_api_key = col
                    if 'meta' not in api_data:
                        api_data['meta'] = {}
                    api_data['meta'][wp_api_key] = self[col]
            if self.isVariable:
                variations = []
                for variation in self.variations.values():
                    variation_data = variation.to_api_data(col_data, api)
                    variations.append(variation_data)
                api_data['variations'] = variations
        return api_data


class ImportShopProductMixin(object):
    container = ShopProdList
    # category_indexer = Registrar.get_object_index
    category_indexer = Registrar.get_object_rowcount
    # category_indexer = CsvParseGenMixin.get_full_name_sum
    # category_indexer = CsvParseGenMixin.get_name_sum
    product_type = None
    isProduct = True

    def __init__(self, *args, **kwargs):
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

    def get_categories(self):
        exc = DeprecationWarning(
            "use .categories instead of .get_categories()")
        self.register_error(exc)
        return self.categories

    @property
    def type_name(self):
        return self.product_type

    def get_type_name(self):
        exc = DeprecationWarning(
            "use .extra_special_category insetad of .get_extra_special_category()")
        self.register_error(exc)
        return self.type_name
        # return self.product_type


class ImportShopProductSimpleMixin(object):
    product_type = 'simple'
    container = ImportShopProductMixin.container


class ImportShopProductVariableMixin(object):
    product_type = 'variable'
    isVariable = True
    container = ImportShopProductMixin.container

    def __init__(self, *args, **kwargs):
        if Registrar.DEBUG_MRO:
            Registrar.register_message('ImportShopProductVariableMixin')
        # super(ImportShopProductVariableMixin, self).__init__(*args, **kwargs)
        self.variations = OrderedDict()

    def register_variation(self, var_data):
        assert var_data.isVariation
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


class ImportShopProductVariationMixin(object):
    product_type = 'variable-instance'
    isVariation = True
    container = ImportShopProductMixin.container

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
    isCategory = True
    isProduct = False
    container = ShopCatList

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

    def get_members(self, item_data):
        exc = DeprecationWarning("use .members instead of .get_members()")
        self.register_error(exc)
        return self.members

    # @property
    # def identifier_delimeter(self):
    #     delim = super(ImportShopCategoryMixin, self).identifier_delimeter
    #     return '|'.join([d for d in [delim, self.namesum] ])


class CsvParseShopMixin(object):
    """
    Mixin class provides shop interface for Parser classes
    """
    objectContainer = ImportShopMixin
    productContainer = ImportShopProductMixin
    simpleContainer = ImportShopProductSimpleMixin
    variableContainer = ImportShopProductVariableMixin
    variationContainer = ImportShopProductVariationMixin
    categoryContainer = ImportShopCategoryMixin
    productIndexer = CsvParseGenMixin.get_code_sum
    category_indexer = CsvParseGenMixin.get_code_sum
    variationIndexer = CsvParseGenMixin.get_code_sum
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
    #     self.productIndexer = self.get_code_sum
    #     self.category_indexer = self.get_code_sum

    @property
    def containers(self):
        return {
            'simple': self.simpleContainer,
            'variable': self.variableContainer,
            'variation': self.variationContainer,
            'category': self.categoryContainer
        }

    def clear_transients(self):
        if Registrar.DEBUG_MRO:
            Registrar.register_message(' ')
        # super(CsvParseShopMixin,self).clear_transients()
        self.products = OrderedDict()
        self.categories = OrderedDict()
        self.attributes = OrderedDict()
        self.vattributes = OrderedDict()
        self.variations = OrderedDict()
        self.images = OrderedDict()
        self.categories_name = OrderedDict()

    def register_product(self, prod_data):
        if Registrar.DEBUG_SHOP:
            Registrar.register_message(
                "registering product %s" % prod_data.identifier)
        assert prod_data.isProduct
        self.register_anything(
            prod_data,
            self.products,
            indexer=self.productIndexer,
            singular=True,
            resolver=self.resolve_conflict,
            register_name='products'
        )

    def register_image(self, image, object_data):
        assert isinstance(image, (str, unicode))
        assert image is not ""
        if image not in self.images.keys():
            self.images[image] = ShopObjList(image)
        self.images[image].append(object_data)
        object_data.register_image(image)

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
                    object_data.isVariation, \
                    "object_data not variation %s, obj isVariation: %s, cls isVariation; %s" \
                    % (
                        type(object_data),
                        repr(object_data.isVariation),
                        repr(type(object_data).isVariation)
                    )
                parent_data = object_data.parent
                assert parent_data and parent_data.isVariable
                self.register_variation(parent_data, object_data)
            else:
                self.register_product(object_data)
            # if Registrar.DEBUG_SHOP:
                # Registrar.register_message("Object is product")
        # else:
            # if Registrar.DEBUG_SHOP:
            #     Registrar.register_message("Object is not product")

    def register_category(self, cat_data):
        assert\
            issubclass(type(cat_data), ImportShopCategoryMixin), \
            "cat_data should be ImportShopCategoryMixin not %s" % str(
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
            indexer=cat_data.woo_cat_name,
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
        assert parent_data.isVariable
        assert var_data.isVariation, "var_data should be a variation, is %s instead. type: %s" \
            % (repr(var_data.isVariable), repr(type(var_data)))
        # if self.DEBUG_API:
        # self.register_message("about to register variation: %s with %s" %
        # self.)
        self.register_anything(
            var_data,
            self.variations,
            indexer=self.variationIndexer,
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
            self.register_error("could not register attribute: {}".format(exc))
            # raise exc
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
            if child.isRoot or not child.isCategory:
                continue
            registered = self.category_indexer(child) in self.categories.keys()
            response += " | ".join([
                "%-5s" % ((child.depth) * ' ' + '*'),
                "%-16s" % str(child.get(self.objectContainer.codesumKey))[:16],
                "%50s" % str(child.get(self.objectContainer.titleKey))[:50],
                "r:%5s" % str(child.rowcount)[:10],
                "w:%5s" % str(child.get(self.objectContainer.wpidKey))[:10],
                "%1s" % "R" if registered else " "
                # "%5s" % child.wpid
            ])
            response += '\n'
            response += self.to_str_tree_recursive(child)
        return response

    def to_str_tree(self):
        return self.to_str_tree_recursive(self.root_data)
