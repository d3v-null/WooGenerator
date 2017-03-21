"""
Introduces the shop products and categories interfaces to CSV Parser classes
"""

import bisect
from collections import OrderedDict

from woogenerator.utils import descriptorUtils, SanitationUtils, Registrar
from woogenerator.coldata import ColData_Prod, ColData_Woo
from woogenerator.parsing.abstract import CSVParse_Base, ImportObject, ObjList
from woogenerator.parsing.tree import ItemList, TaxoList
from woogenerator.parsing.gen import CSVParse_Gen_Tree, ImportGenItem, CSVParse_Gen_Mixin
from woogenerator.parsing.gen import ImportGenMixin, ImportGenObject


class ShopProdList(ItemList):
    "Container for shop products"
    objList_type = 'products'
    reportCols = ColData_Prod.get_report_cols()

    def append(self, object_data):
        assert issubclass(object_data.__class__, ImportShopMixin), \
            "object must be subclass of ImportShopMixin not %s : %s" % (
                SanitationUtils.coerce_unicode(object_data.__class__),
                SanitationUtils.coerce_unicode(object_data)
        )
        return super(ShopProdList, self).append(object_data)


class ShopCatList(ItemList):
    reportCols = ColData_Prod.get_report_cols()


class ShopObjList(ObjList):

    def __init__(self, file_name=None, objects=None, indexer=None):
        self.file_name = file_name
        self.isValid = True
        if not self.file_name:
            self.isValid = False
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
        self.registerError(exc)
        raise exc

    @property
    def title(self):
        return self.getKey('fullnamesum')

    @property
    def description(self):
        description = self.getKey('HTML Description')
        if not description:
            description = self.getKey('descsum')
        if not description:
            description = self.name
        return description

    # @property
    # def isValid(self):
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
            self.registerError(reason, self.file_name)
        self.isValid = False


class ImportShopMixin(object):
    "Base class for shop objects (products, categories)"
    isProduct = None
    isCategory = None
    isVariable = None
    isVariation = None
    #container = ObjList

    def __init__(self, *args, **kwargs):
        if Registrar.DEBUG_MRO:
            Registrar.registerMessage('ImportShopMixin')
        if Registrar.DEBUG_SHOP:
            self.registerMessage("creating shop object; %s %s %s %s" % (
                'isProduct' if self.isProduct else '!isProduct',
                'isCategory' if self.isCategory else '!isCategory',
                'isVariable' if self.isVariable else '!isVariable',
                'isVariation' if self.isVariation else '!isVariation'
            ))
        super(ImportShopMixin, self).__init__(*args, **kwargs)
        self.attributes = OrderedDict()
        self.images = []

    # @classmethod
    # def getNewObjContainer(cls):
    #     exc = DeprecationWarning("use .container instead of .getNewObjContainer()")
    #     self.registerError(exc)
    #     return cls.container
    #     # return ObjList

    def registerAttribute(self, attr, val, var=False):
        if Registrar.DEBUG_SHOP:
            self.registerMessage(
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
        exc = DeprecationWarning("use .attributes instead of .get_attributes()")
        self.registerError(exc)
        return self.attributes

    def registerImage(self, image):
        assert isinstance(image, (str, unicode))
        this_images = self.images
        if image not in this_images:
            this_images.append(image)
            # parent = self.getParent()
            # parentImages = parent.get_images()
            # if not parentImages:
            #     parent.registerImage(image)

    def get_images(self):
        exc = DeprecationWarning("use .images instead of .get_images()")
        self.registerError(exc)
        return self.images

    def toApiData(self, col_data, api):
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
            for col, col_data in col_data.getWPAPIMetaCols(api).items():
                if col in self:
                    try:
                        wp_api_key = col_data[api]['key']
                    except:
                        wp_api_key = col
                    if not 'meta' in api_data:
                        api_data['meta'] = {}
                    api_data['meta'][wp_api_key] = self[col]
            if self.isVariable:
                variations = []
                for variation in self.variations.values():
                    variation_data = variation.toApiData(col_data, api)
                    variations.append(variation_data)
                api_data['variations'] = variations
        return api_data


class ImportShopProductMixin(object):
    container = ShopProdList
    # category_indexer = Registrar.getObjectIndex
    category_indexer = Registrar.getObjectRowcount
    # category_indexer = CSVParse_Gen_Mixin.get_full_name_sum
    # category_indexer = CSVParse_Gen_Mixin.getNameSum
    product_type = None
    isProduct = True

    def __init__(self, *args, **kwargs):
        if Registrar.DEBUG_MRO:
            Registrar.registerMessage('ImportShopProductMixin')
        # super(ImportShopProductMixin, self).__init__(*args, **kwargs)
        self.categories = OrderedDict()

    def registerCategory(self, cat_data):
        self.registerAnything(
            cat_data,
            self.categories,
            # indexer = self.getSum,
            indexer=self.category_indexer,
            singular=True,
            resolver=self.duplicate_object_exception_resolver,
            registerName='product categories'
        )

    def joinCategory(self, cat_data):
        self.registerCategory(cat_data)
        cat_data.registerMember(self)

    def get_categories(self):
        exc = DeprecationWarning("use .categories instead of .get_categories()")
        self.registerError(exc)
        return self.categories

    @property
    def type_name(self):
        return self.product_type

    def getTypeName(self):
        exc = DeprecationWarning(
            "use .extraSpecialCategory insetad of .get_extra_special_category()")
        self.registerError(exc)
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
            Registrar.registerMessage('ImportShopProductVariableMixin')
        # super(ImportShopProductVariableMixin, self).__init__(*args, **kwargs)
        self.variations = OrderedDict()

    def registerVariation(self, varData):
        assert varData.isVariation
        self.registerAnything(
            varData,
            self.variations,
            indexer=varData.codesum,
            singular=True,
            registerName="product variations"
        )

    def getVariations(self):
        exc = DeprecationWarning("use .variations instead of .getVariations()")
        self.registerError(exc)
        return self.variations


class ImportShopProductVariationMixin(object):
    product_type = 'variable-instance'
    isVariation = True
    container = ImportShopProductMixin.container

    def registerParentProduct(self, parent_data):
        assert issubclass(type(parent_data), ImportShopProductVariableMixin)
        self.parentProduct = parent_data
        self['parent_SKU'] = parent_data.codesum

    def joinVariable(self, parent_data):
        assert issubclass(type(parent_data), ImportShopProductVariableMixin)
        self.registerParentProduct(parent_data)
        parent_data.registerVariation(self)

    def getParentProduct(self):
        return self.parentProduct


class ImportShopCategoryMixin(object):
    isCategory = True
    isProduct = False
    container = ShopCatList

    def __init__(self, *args, **kwargs):
        if Registrar.DEBUG_MRO:
            Registrar.registerMessage('ImportShopCategoryMixin')
        # super(ImportShopCategoryMixin, self).__init__(*args, **kwargs)
        self.members = OrderedDict()

    def registerMember(self, itemData):
        self.registerAnything(
            itemData,
            self.members,
            # indexer = self.getSum,
            indexer=itemData.rowcount,
            singular=True,
            resolver=self.passiveResolver,
            registerName='product categories'
        )

    def getMembers(self, itemData):
        exc = DeprecationWarning("use .members instead of .getMembers()")
        self.registerError(exc)
        return self.members

    # @property
    # def identifier_delimeter(self):
    #     delim = super(ImportShopCategoryMixin, self).identifier_delimeter
    #     return '|'.join([d for d in [delim, self.namesum] ])


class CSVParse_Shop_Mixin(object):
    """
    Mixin class provides shop interface for Parser classes
    """
    objectContainer = ImportShopMixin
    productContainer = ImportShopProductMixin
    simpleContainer = ImportShopProductSimpleMixin
    variableContainer = ImportShopProductVariableMixin
    variationContainer = ImportShopProductVariationMixin
    categoryContainer = ImportShopCategoryMixin
    productIndexer = CSVParse_Gen_Mixin.get_code_sum
    category_indexer = CSVParse_Gen_Mixin.get_code_sum
    variationIndexer = CSVParse_Gen_Mixin.get_code_sum
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
            Registrar.registerMessage(' ')
        # super(CSVParse_Shop_Mixin,self).clear_transients()
        self.products = OrderedDict()
        self.categories = OrderedDict()
        self.attributes = OrderedDict()
        self.vattributes = OrderedDict()
        self.variations = OrderedDict()
        self.images = OrderedDict()
        self.categories_name = OrderedDict()

    def registerProduct(self, prodData):
        if Registrar.DEBUG_SHOP:
            Registrar.registerMessage(
                "registering product %s" % prodData.identifier)
        assert prodData.isProduct
        self.registerAnything(
            prodData,
            self.products,
            indexer=self.productIndexer,
            singular=True,
            resolver=self.resolveConflict,
            registerName='products'
        )

    def registerImage(self, image, object_data):
        assert isinstance(image, (str, unicode))
        assert image is not ""
        if image not in self.images.keys():
            self.images[image] = ShopObjList(image)
        self.images[image].append(object_data)
        object_data.registerImage(image)

    def getProducts(self):
        exc = DeprecationWarning("Use .products instead of .getProducts()")
        self.registerError(exc)
        if Registrar.DEBUG_SHOP:
            Registrar.registerMessage(
                "returning products: {}".format(self.products.keys()))
        return self.products

    def registerObject(self, object_data):
        if Registrar.DEBUG_MRO:
            Registrar.registerMessage(' ')
        # super(CSVParse_Shop_Mixin, self).registerObject(object_data)
        if issubclass(type(object_data), ImportShopProductMixin):
            if issubclass(type(object_data), ImportShopProductVariationMixin):
                assert \
                    object_data.isVariation, \
                    "object_data not variation %s, obj isVariation: %s, cls isVariation; %s" \
                    % (type(object_data), repr(object_data.isVariation), repr(type(object_data).isVariation))
                parent_data = object_data.parent
                assert parent_data and parent_data.isVariable
                self.registerVariation(parent_data, object_data)
            else:
                self.registerProduct(object_data)
            # if Registrar.DEBUG_SHOP:
                # Registrar.registerMessage("Object is product")
        # else:
            # if Registrar.DEBUG_SHOP:
            #     Registrar.registerMessage("Object is not product")

    def registerCategory(self, cat_data):
        assert\
            issubclass(type(cat_data), ImportShopCategoryMixin), \
            "cat_data should be ImportShopCategoryMixin not %s" % str(
                type(cat_data))
        self.registerAnything(
            cat_data,
            self.categories,
            indexer=self.category_indexer,
            resolver=self.passiveResolver,
            singular=True,
            registerName='categories'
        )
        self.registerAnything(
            cat_data,
            self.categories_name,
            indexer=cat_data.wooCatName,
            singular=False
        )

    def joinCategory(self, cat_data, itemData=None):
        if itemData:
            assert\
                issubclass(type(itemData), ImportShopProductMixin), \
                "itemData should be ImportShopProductMixin not %s" % str(
                    type(itemData))
            # for product_cat in itemData.categories:
            #     assert self.category_indexer(product_cat) != self.category_indexer(cat_data)
            itemData.joinCategory(cat_data)

    def registerJoinCategory(self, cat_data, itemData=None):
        self.registerCategory(cat_data)
        self.joinCategory(cat_data, itemData)

    def registerVariation(self, parent_data, varData):
        assert issubclass(type(parent_data), ImportShopProductVariableMixin)
        assert issubclass(type(
            varData), ImportShopProductVariationMixin), "varData should subclass ImportShopProductVariationMixin instead %s" % type(varData)
        assert parent_data.isVariable
        assert varData.isVariation, "varData should be a variation, is %s instead. type: %s" \
                                    % (repr(varData.isVariable), repr(type(varData)))
        # if self.DEBUG_API:
        # self.registerMessage("about to register variation: %s with %s" %
        # self.)
        self.registerAnything(
            varData,
            self.variations,
            indexer=self.variationIndexer,
            singular=True,
            resolver=self.duplicate_object_exception_resolver,
            registerName='variations'
        )

        varData.joinVariable(parent_data)

    def registerAttribute(self, object_data, attr, val, var=False):
        try:
            attr = str(attr)
            assert isinstance(attr, (str, unicode)), 'Attribute must be a string not {}'.format(
                type(attr).__name__)
            assert attr is not '', 'Attribute must not be empty'
            assert attr[
                0] is not ' ', 'Attribute must not start with whitespace or '
        except AssertionError as exc:
            self.registerError("could not register attribute: {}".format(exc))
            # raise exc
        else:
            object_data.registerAttribute(attr, val, var)
            self.registerAnything(
                val,
                self.attributes,
                indexer=attr,
                singular=False,
                registerName='Attributes'
            )
            if var:
                self.registerAnything(
                    val,
                    self.vattributes,
                    indexer=attr,
                    singular=False,
                    registerName='Variable Attributes'
                )

    def toStrTreeRecursive(self, cat_data):
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
            response += self.toStrTreeRecursive(child)
        return response

    def toStrTree(self):
        return self.toStrTreeRecursive(self.rootData)
