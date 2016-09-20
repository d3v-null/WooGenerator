"""
Introduces the shop products and categories interfaces to CSV Parser classes
"""

from csvparse_abstract import CSVParse_Base, ImportObject, ObjList
from csvparse_tree import ItemList, TaxoList
from csvparse_gen import CSVParse_Gen_Tree, ImportGenItem, CSVParse_Gen_Mixin
from csvparse_gen import ImportGenBase
from collections import OrderedDict
from utils import descriptorUtils, SanitationUtils, Registrar
from coldata import ColData_Prod
import bisect

class ShopProdList(ItemList):
    "Container for shop products"
    objList_type = 'products'
    reportCols = ColData_Prod.getReportCols()

    def append(self, objectData):
        assert issubclass(objectData.__class__, ImportShop), \
            "object must be subclass of ImportShop not %s : %s" % (
                SanitationUtils.coerceUnicode(objectData.__class__),
                SanitationUtils.coerceUnicode(objectData)
            )
        return super(ShopProdList, self).append(objectData)

class ShopCatList(ItemList):
    reportCols = ColData_Prod.getReportCols()

class ShopObjList(ObjList):
    def __init__(self, fileName=None, objects=None, indexer=None):
        self.fileName = fileName
        self.isValid = True
        if not self.fileName:
            self.isValid = False
        self.products = ShopProdList()
        self.categories = ShopCatList()
        super(ShopObjList, self).__init__(objects, indexer=indexer)

    @property
    def objects(self):
        return self.products + self.categories

    @property
    def name(self):
        e = DeprecationWarning(".name deprecated")
        self.registerError(e)
        raise e

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
    # def fileName(self):
    #     return self._fileName

    def append(self, objectData):
        assert isinstance(objectData, ImportShop)
        if objectData.isCategory:
            container = self.categories
        elif objectData.isProduct:
            container = self.products

        if objectData not in container:
            bisect.insort(container, objectData)

    def invalidate(self, reason=""):
        if self.DEBUG_IMG:
            if not reason:
                reason = "IMG INVALID"
            self.registerError(reason, self.fileName)
        self.isValid = False

class ImportShop(ImportGenBase):
    "Base class for shop objects (products, categories)"
    isProduct = None
    isCategory = None
    isVariable = None
    isVariation = None
    #container = ObjList

    def __init__(self, *args, **kwargs):
        if self.DEBUG_MRO:
            self.registerMessage(' ')
        if self.DEBUG_SHOP:
            self.registerMessage("creating shop object; %s %s %s %s" % (
                'isProduct' if self.isProduct else '!isProduct',
                'isCategory' if self.isCategory else '!isCategory',
                'isVariable' if self.isVariable else '!isVariable',
                'isVariation' if self.isVariation else '!isVariation'
            ) )
        super(ImportShop, self).__init__(*args, **kwargs)
        self.attributes = OrderedDict()
        self.images = []

    # @classmethod
    # def getNewObjContainer(cls):
    #     e = DeprecationWarning("use .container instead of .getNewObjContainer()")
    #     self.registerError(e)
    #     return cls.container
    #     # return ObjList

    def registerAttribute(self, attr, val, var=False):
        if self.DEBUG_SHOP:
            self.registerMessage("attr: %s ; val: %s ; var: %s" % (attr, val, var) )
        if var:
            assert self.isProduct, "sanity: must be a product to assign ba"
            assert self.isVariation or self.isVariable
        attrs = self.attributes
        if attr not in attrs.keys():
            attrs[attr] = {
                'values':[val],
                'visible':1,
                'variation':1 if var else 0
            }
            if var:
                attrs[attr]['default'] = val
        elif val not in attrs[attr]['values'] :
            attrs[attr]['values'].append(val)
        if var:
            if not attrs[attr]['default']:
                attrs[attr]['default'] = val
            attrs[attr]['variation'] = 1

        assert attrs == self.attributes, "sanity: something went wrong assigning attribute"

    def getAttributes(self):
        e = DeprecationWarning("use .attributes instead of .getAttributes()")
        self.registerError(e)
        return self.attributes


    def registerImage(self, image):
        assert isinstance(image, (str, unicode))
        thisImages = self.images
        if image not in thisImages:
            thisImages.append(image)
            # parent = self.getParent()
            # parentImages = parent.getImages()
            # if not parentImages:
            #     parent.registerImage(image)

    def getImages(self):
        e = DeprecationWarning("use .images instead of .getImages()")
        self.registerError(e)
        return self.images

class ImportShopProduct(ImportShop):
    container = ShopProdList
    categoryIndexer = Registrar.getObjectRowcount
    # categoryIndexer = CSVParse_Gen_Mixin.getFullNameSum
    product_type = None
    isProduct = True

    def __init__(self, *args, **kwargs):
        if self.DEBUG_MRO:
            self.registerMessage(' ')
        super(ImportShopProduct, self).__init__(*args, **kwargs)
        self.categories = OrderedDict()
        if self.product_type:
            self['prod_type'] = self.product_type

    def registerCategory(self, catData):
        self.registerAnything(
            catData,
            self.categories,
            # indexer = self.getSum,
            indexer = self.categoryIndexer,
            singular = True,
            resolver = self.exceptionResolver,
            registerName = 'product categories'
        )

    def joinCategory(self, catData):
        self.registerCategory(catData)
        catData.registerMember(self)

    def getCategories(self):
        e = DeprecationWarning("use .categories instead of .getCategories()")
        self.registerError(e)
        return self.categories

    @property
    def typeName(self):
        return self.product_type

    def getTypeName(self):
        e = DeprecationWarning("use .extraSpecialCategory insetad of .getExtraSpecialCategory()")
        self.registerError(e)
        return self.typeName
        # return self.product_type

class ImportShopProductSimple(ImportShopProduct):
    product_type = 'simple'

class ImportShopProductVariable(ImportShopProduct):
    product_type = 'variable'
    isVariable = True

    def __init__(self, *args, **kwargs):
        if self.DEBUG_MRO:
            self.registerMessage(' ')
        super(ImportShopProductVariable, self).__init__(*args, **kwargs)
        self.variations = OrderedDict()

    def registerVariation(self, varData):
        assert varData.isVariation
        self.registerAnything(
            varData,
            self.variations,
            indexer = varData.codesum,
            singular = True,
            registerName = "product variations"
        )

    def getVariations(self):
        e = DeprecationWarning("use .variations instead of .getVariations()")
        self.registerError(e)
        return self.variations

class ImportShopProductVariation(ImportShopProduct):
    product_type = 'variable-instance'
    isVariation = True

    def registerParentProduct(self, parentData):
        assert issubclass(type(parentData), ImportShopProductVariable)
        self.parentProduct = parentData
        self['parent_SKU'] = parentData.codesum

    def joinVariable(self, parentData):
        assert issubclass(type(parentData), ImportShopProductVariable)
        self.registerParentProduct(parentData)
        parentData.registerVariation(self)

    def getParentProduct(self):
        return self.parentProduct

class ImportShopCategory(ImportShop):
    isCategory = True
    container = ShopCatList

    def __init__(self, *args, **kwargs):
        if self.DEBUG_MRO:
            self.registerMessage(' ')
        super(ImportShopCategory, self).__init__(*args, **kwargs)
        self.members = OrderedDict()

    def registerMember(self, itemData):
        self.registerAnything(
            itemData,
            self.members,
            # indexer = self.getSum,
            indexer = itemData.rowcount,
            singular = True,
            resolver = self.passiveResolver,
            registerName = 'product categories'
        )

    def getMembers(self, itemData):
        e = DeprecationWarning("use .members instead of .getMembers()")
        self.registerError(e)
        return self.members

    @property
    def wooCatName(self):
        cat_layers = self.namesum.split(' > ')
        return cat_layers[-1]

    @classmethod
    def getWooCatName(cls, inst):
        assert isinstance(inst, ImportShopCategory)
        return inst.wooCatName

    # @property
    # def identifierDelimeter(self):
    #     delim = super(ImportShopCategory, self).identifierDelimeter
    #     return '|'.join([d for d in [delim, self.namesum] ])

class CSVParse_Shop_Mixin(CSVParse_Gen_Mixin):
    """
    Mixin class provides shop interface for Parser classes
    """
    objectContainer = ImportShop
    productContainer = ImportShopProduct
    simpleContainer = ImportShopProductSimple
    variableContainer = ImportShopProductVariable
    variationContainer = ImportShopProductVariation
    categoryContainer = ImportShopCategory
    productIndexer = CSVParse_Gen_Mixin.getCodeSum
    categoryIndexer = CSVParse_Gen_Mixin.getCodeSum
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
    #     self.productIndexer = self.getCodeSum
    #     self.categoryIndexer = self.getCodeSum


    @property
    def containers(self):
        return {
            'simple':self.simpleContainer,
            'variable':self.variableContainer,
            'variation':self.variationContainer,
            'category':self.categoryContainer
        }

    def clearTransients(self):
        if self.DEBUG_MRO:
            self.registerMessage(' ')
        super(CSVParse_Shop_Mixin,self).clearTransients()
        self.products   = OrderedDict()
        self.categories = OrderedDict()
        self.attributes = OrderedDict()
        self.vattributes= OrderedDict()
        self.variations = OrderedDict()
        self.images     = OrderedDict()

    def registerProduct(self, prodData):
        if self.DEBUG_SHOP:
            self.registerMessage("registering product %s" % prodData.identifier)
        assert prodData.isProduct
        self.registerAnything(
            prodData,
            self.products,
            indexer = self.productIndexer,
            singular = True,
            resolver = self.resolveConflict,
            registerName = 'products'
        )


    def registerImage(self, image, objectData):
        assert isinstance(image,(str,unicode))
        assert image is not ""
        if image not in self.images.keys():
            self.images[image] = ShopObjList(image)
        self.images[image].append(objectData)
        objectData.registerImage(image)

    def getProducts(self):
        e = DeprecationWarning("Use .products instead of .getProducts()")
        self.registerError(e)
        if self.DEBUG_SHOP:
            self.registerMessage("returning products: {}".format(self.products.keys()))
        return self.products

    def registerObject(self, objectData):
        if self.DEBUG_MRO:
            self.registerMessage(' ')
        super(CSVParse_Shop_Mixin, self).registerObject(objectData)
        if issubclass(type(objectData), ImportShopProduct):
            # and not issubclass(type(objectData), ImportShopProductVariation):
            self.registerProduct(objectData)
            # if self.DEBUG_SHOP:
                # self.registerMessage("Object is product")
        # else:
            # if self.DEBUG_SHOP:
            #     self.registerMessage("Object is not product")

    def registerCategory(self, catData, itemData):
        assert issubclass(type(catData), ImportShopCategory)
        assert issubclass(type(itemData), ImportShopProduct)
        self.registerAnything(
            catData,
            self.categories,
            indexer = self.categoryIndexer,
            resolver = self.passiveResolver,
            singular = True,
            registerName = 'categories'
        )
        itemData.joinCategory(catData)

    def registerVariation(self, parentData, varData):
        assert issubclass(type(parentData), ImportShopProductVariable)
        assert issubclass(type(varData), ImportShopProductVariation), "varData should subclass ImportShopProductVariation instead %s" % type(varData)
        assert parentData.isVariable
        assert varData.isVariation
        self.registerAnything(
            varData,
            self.variations,
            indexer=self.productIndexer,
            singular=True,
            resolver=self.exceptionResolver,
            registerName='variations'
        )
        # if not parentData.get('variations'): parentData['variations'] = OrderedDict()
        varData.joinVariable(parentData)

    def registerAttribute(self, objectData, attr, val, var=False):
        try:
            attr = str(attr)
            assert isinstance(attr, (str, unicode)), 'Attribute must be a string not {}'.format(type(attr).__name__)
            assert attr is not '', 'Attribute must not be empty'
            assert attr[0] is not ' ', 'Attribute must not start with whitespace or '
        except AssertionError as e:
            self.registerError("could not register attribute: {}".format(e))
            # raise e
        else:
            objectData.registerAttribute(attr, val, var)
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
