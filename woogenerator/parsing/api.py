"""Introduces woo api structure to shop classes"""
from collections import OrderedDict
import bisect
import time
from pprint import pformat

from woogenerator.utils import listUtils, SanitationUtils, TimeUtils, PHPUtils
from woogenerator.utils import Registrar, descriptorUtils
from woogenerator.coldata import ColData_Woo
from woogenerator.parsing.abstract import ObjList, CSVParse_Base
from woogenerator.parsing.tree import ItemList, TaxoList, ImportTreeObject
from woogenerator.parsing.tree import CSVParse_Tree, CSVParse_Tree_Mixin
from woogenerator.parsing.gen import CSVParse_Gen_Tree, ImportGenItem
from woogenerator.parsing.gen import ImportGenTaxo, ImportGenObject
from woogenerator.parsing.gen import ImportGenObject, CSVParse_Gen_Mixin
from woogenerator.parsing.shop import ImportShopMixin, ImportShopProductMixin, ImportShopProductSimpleMixin
from woogenerator.parsing.shop import ImportShopProductVariableMixin, ImportShopProductVariationMixin
from woogenerator.parsing.shop import ImportShopCategoryMixin, CSVParse_Shop_Mixin
from woogenerator.parsing.flat import CSVParse_Flat, ImportFlat
from woogenerator.parsing.woo import CSVParse_Woo_Mixin, ImportWooMixin

class ImportApiObject(ImportGenObject, ImportShopMixin, ImportWooMixin):
    def __init__(self, *args, **kwargs):
        if self.DEBUG_MRO:
            self.registerMessage('ImportApiObject')
        ImportGenObject.__init__(self, *args, **kwargs)
        ImportShopMixin.__init__(self, *args, **kwargs)
        ImportWooMixin.__init__(self, *args, **kwargs)
        self.categoryIndexer = CSVParse_Woo_Mixin.getTitle

    @property
    def index(self):
        return self.codesum

    @property
    def identifier(self):
        # identifier = super(ImportApiObject, self).identifier
        return "|".join([
            'r:%s' % str(self.rowcount),
            'w:%s' % str(self.get(self.wpidKey)),
            self.codesum,
            self.title,
        ])

    def processMeta(self):
        # self.descsum = self.description
        assert self.descsumKey in self, "descsum should be set in %s. data: %s " % (self, self.items())
        # self.namesum = self.title
        assert self.namesumKey in self, "namesum should be set in %s. data: %s " % (self, self.items())
        # if self.isCategory:
        #     self.codesum = ''
        assert self.codesumKey in self, "codesum should be set in %s. data: %s " % (self, self.items())

class ImportApiProduct(ImportApiObject, ImportShopProductMixin):
    isProduct = ImportShopProductMixin.isProduct
    def __init__(self, *args, **kwargs):
        if self.DEBUG_MRO:
            self.registerMessage('ImportApiProduct')
        if self.product_type:
            args[0]['prod_type'] = self.product_type
        ImportApiObject.__init__(self, *args, **kwargs)
        ImportShopProductMixin.__init__(self, *args, **kwargs)

class ImportApiProductSimple(ImportApiProduct, ImportShopProductSimpleMixin):
    product_type = ImportShopProductSimpleMixin.product_type

class ImportApiProductVariable(ImportApiProduct, ImportShopProductVariableMixin):
    isVariable = ImportShopProductVariableMixin.isVariable
    product_type = ImportShopProductVariableMixin.product_type

    def __init__(self, *args, **kwargs):
        if self.DEBUG_MRO:
            self.registerMessage('ImportApiProductVariable')
        ImportApiProduct.__init__(self, *args, **kwargs)
        ImportShopProductVariableMixin.__init__(self, *args, **kwargs)

class ImportApiProductVariation(ImportApiProduct, ImportShopProductVariationMixin):
    isVariation = ImportShopProductVariationMixin.isVariation
    product_type = ImportShopProductVariationMixin.product_type

class ImportApiCategory(ImportApiObject, ImportShopCategoryMixin):
    isCategory = ImportShopCategoryMixin.isCategory

    def __init__(self, *args, **kwargs):
        if self.DEBUG_MRO:
            self.registerMessage('ImportApiCategory')
        ImportApiObject.__init__(self, *args, **kwargs)
        ImportShopCategoryMixin.__init__(self, *args, **kwargs)

    @property
    def wooCatName(self):
        return self.title

    @property
    def index(self):
        return self.title

    @property
    def identifier(self):
        # identifier = super(ImportApiObject, self).identifier
        return "|".join([
            'r:%s' % str(self.rowcount),
            'w:%s' % str(self.get(self.wpidKey)),
            self.title,
        ])

# class CSVParse_Woo_Api(CSVParse_Flat, CSVParse_Shop_Mixin, CSVParse_Woo_Mixin, CSVParse_Tree_Mixin):
# class CSVParse_Woo_Api(CSVParse_Gen_Tree, CSVParse_Shop_Mixin, CSVParse_Woo_Mixin):
# class CSVParse_Woo_Api(CSVParse_Base, CSVParse_Shop_Mixin, CSVParse_Woo_Mixin):
class CSVParse_Woo_Api(CSVParse_Base, CSVParse_Tree_Mixin, CSVParse_Shop_Mixin, CSVParse_Woo_Mixin):
    objectContainer = ImportApiObject
    productContainer = ImportApiProduct
    simpleContainer = ImportApiProductSimple
    variableContainer = ImportApiProductVariable
    variationContainer = ImportApiProductVariation
    categoryContainer = ImportApiCategory
    # categoryIndexer = CSVParse_Gen_Mixin.getNameSum
    # categoryIndexer = CSVParse_Woo_Mixin.getTitle
    # categoryIndexer = CSVParse_Woo_Mixin.getWPID
    categoryIndexer = CSVParse_Base.getObjectRowcount
    productIndexer = CSVParse_Shop_Mixin.productIndexer
    variationIndexer = CSVParse_Woo_Mixin.getTitle


    def __init__(self, *args, **kwargs):
        if self.DEBUG_MRO:
            self.registerMessage('CSVParse_Woo_Api')
        super(CSVParse_Woo_Api, self).__init__(*args, **kwargs)
        # self.categoryIndexer = CSVParse_Gen_Mixin.getNameSum
        # if hasattr(CSVParse_Woo_Mixin, '__init__'):
        #     CSVParse_Gen_Mixin.__init__(self, *args, **kwargs)

    def clearTransients(self):
        # for base_class in CSVParse_Woo_Api.__bases__:
        #     if hasattr(base_class, 'clearTransients'):
        #         base_class.clearTransients(self)
        # CSVParse_Flat.clearTransients(self)
        CSVParse_Base.clearTransients(self)
        CSVParse_Tree_Mixin.clearTransients(self)
        CSVParse_Shop_Mixin.clearTransients(self)
        CSVParse_Woo_Mixin.clearTransients(self)

        # super(CSVParse_Woo_Api, self).clearTransients()
        # CSVParse_Shop_Mixin.clearTransients(self)


    def registerObject(self, objectData):
        # CSVParse_Gen_Tree.registerObject(self, objectData)
        CSVParse_Base.registerObject(self, objectData)
        # CSVParse_Tree_Mixin.registerObject(self, objectData)
        CSVParse_Shop_Mixin.registerObject(self, objectData)
        # CSVParse_Woo_Mixin.registerObject(self, objectData)

    # def processObject(self, objectData):
        # super(CSVParse_Woo_Api, self).processObject(objectData)
        #todo: this

    # def registerObject(self, objectData):
    #     if self.DEBUG_MRO:
    #         self.registerMessage(' ')
    #     if self.DEBUG_API:
    #         self.registerMessage("registering objectData: %s" % str(objectData))
    #     super(CSVParse_Woo_Api, self).registerObject(objectData)

    @classmethod
    def getApiDimensionData(cls, dimensions):
        newData = OrderedDict()
        for dimension_key in ['length', 'width', 'height']:
            if dimension_key in dimensions:
                newData[dimension_key] = dimensions[dimension_key]
                # objectData[dimension_key] = dimensions[dimension_key]
        return newData

    @classmethod
    def getApiStockStatusData(cls, in_stock):
        newData = OrderedDict()
        if in_stock:
            stock_status = 'in_stock'
        else:
            stock_status = 'outofstock'
        newData['stock_status'] = stock_status
        return newData

    def processApiCategory(self, categoryApiData, objectData=None):
        """
        Create category if not exist or find if exist, then assign objectData to category
        Has to emulate CSVParse_Base.newObject()
        """
        if self.DEBUG_API:
            category_title = categoryApiData.get('title', '')
            if objectData:
                identifier = objectData.identifier
                self.registerMessage(
                    "%s member of category %s" \
                    % (identifier, category_title)
                )
            else:
                self.registerMessage(
                    "creating category %s" % (category_title)
                )

        #
        if self.DEBUG_API:
            self.registerMessage("ANALYSE CATEGORY: %s" % repr(categoryApiData))
        core_translation = OrderedDict()
        for col, col_data in ColData_Woo.getWPAPICoreCols().items():
            try:
                wp_api_key = col_data['wp-api']['key']
            except:
                wp_api_key = col
            core_translation[wp_api_key] = col
        categorySearchData = {}
        categorySearchData.update(**self.translateKeys(categoryApiData, core_translation))
        categorySearchData = dict([(key, SanitationUtils.html_unescape_recursive(value))\
                        for key, value in categorySearchData.items()])

        # if 'id' in categoryApiData:
        #     categorySearchData[self.categoryContainer.wpidKey] = categoryApiData['id']
        # if 'name' in categoryApiData:
        #     categorySearchData[self.categoryContainer.titleKey] = categoryApiData['name']
        #     categorySearchData[self.categoryContainer.namesumKey] = categoryApiData['name']
        # elif 'title' in categoryApiData:
        #     categorySearchData[self.categoryContainer.titleKey] = categoryApiData['title']
        #     categorySearchData[self.categoryContainer.namesumKey] = categoryApiData['title']
        # if 'slug' in categoryApiData:
        #     categorySearchData[self.categoryContainer.slugKey] = categoryApiData['slug']
        if self.DEBUG_API:
            self.registerMessage("SEARCHING FOR CATEGORY: %s" % repr(categorySearchData))
        catData = self.findCategory(categorySearchData)
        if not catData:
            if self.DEBUG_API:
                self.registerMessage("CATEGORY NOT FOUND")

            categoryApiData['type'] = 'category'
            if not 'description' in categoryApiData:
                categoryApiData['description'] = ''
            if not 'slug' in categoryApiData:
                categoryApiData['slug'] = ''

            kwargs = OrderedDict()
            kwargs['apiData'] = categoryApiData

            # defaultData = OrderedDict(self.defaults.items())
            #
            # parserData = self.getParserData(**kwargs)
            #
            # allData = listUtils.combineOrderedDicts(defaultData, parserData)
            #
            # container = self.getNewObjContainer(allData, **kwargs)
            #
            # catData = container(allData, **kwargs)

            # kwargs = OrderedDict(self.defaults.items())
            # kwargs.update(categorySearchData)
            # catRowcount = getattr(self, 'rowcount')
            # if 'id' in categoryApiData:
            #     catRowcount = categoryApiData['id']
            parentCategoryData = None
            if 'parent' in categoryApiData:
                parentCategorySearchData = {}
                parentCategorySearchData[self.categoryContainer.wpidKey] = categoryApiData['parent']
                parentCategoryData = self.findCategory(parentCategorySearchData)
            if parentCategoryData:
                kwargs['parent'] = parentCategoryData
            else:
                kwargs['parent'] = self.rootData

            catData = self.newObject(rowcount=self.rowcount, **kwargs)

            if self.DEBUG_API:
                self.registerMessage("CONSTRUCTED: %s" % catData.identifier)
            self.processObject(catData)
            if self.DEBUG_API:
                self.registerMessage("PROCESSED: %s" % catData.identifier)
            self.registerCategory(catData)
            if self.DEBUG_API:
                self.registerMessage("REGISTERED: %s" % catData.identifier)

        else:
            if self.DEBUG_API:
                self.registerMessage("FOUND CATEGORY: %s" % repr(catData))

        self.joinCategory(catData, objectData)
        # if self.DEBUG_API:
        #     index = self.categoryIndexer(catData)
        #     self.registerMessage(repr(self.categoryIndexer))
        #     self.registerMessage("REGISTERING CATEGORY WITH INDEX %s" % repr(index))


        self.rowcount += 1

    def processApiCategories(self, categories):
        """ creates a queue of categories to be processed in the correct order """
        while categories:
            category = categories.pop(0)
            # self.registerMessage("analysing category: %s" % category)
            if category.get('parent'):
                parent = category.get('parent')
                # self.registerMessage("parent id: %s" % parent)
                queue_category_ids = [queue_category.get('id') for queue_category in categories]
                if parent in queue_category_ids:
                    # self.registerMessage('analysing later')
                    categories.append(category)
                    continue
                # self.registerMessage("queue categories: %s" % queue_category_ids)
                # for queue_category in categories:
                #     # If category's parent exists in queue
                #     if queue_category.get('id') == parent:
                #         # then put it at the end of the queue
                #         categories.append(category)
            self.processApiCategory(category)



    def processApiAttributes(self, objectData, attributes, var=False):
        varstr = 'var ' if var else ''
        for attribute in attributes:
            if self.DEBUG_API:
                self.registerMessage("%s has %sattribute %s" % (objectData.identifier, varstr, attribute))
            if 'name' in attribute:
                attr = attribute.get('name')
            elif 'slug' in attribute:
                attr = attribute.get('slug')
            else:
                raise UserWarning('could not determine attributte key')

            if 'option' in attribute:
                vals = [attribute['option']]
            elif 'options' in attribute:
                vals = attribute.get('options')
            else:
                raise UserWarning('could not determine attribute values')

            if vals:
                for val in vals:
                    self.registerAttribute(objectData, attr, val, var)


    @classmethod
    def getParserData(cls, **kwargs):
        """
        Gets data ready for the parser, in this case from apiData
        """
        parserData = OrderedDict()
        apiData = kwargs.get('apiData',{})
        # print "apiData before: %s" % str(apiData)
        apiData = dict([(key, SanitationUtils.html_unescape_recursive(value))\
                        for key, value in apiData.items()])
        # print "apiData after:  %s" % str(apiData)
        parserData = OrderedDict()
        core_translation = OrderedDict()
        for col, col_data in ColData_Woo.getWPAPICoreCols().items():
            try:
                wp_api_key = col_data['wp-api']['key']
            except:
                wp_api_key = col
            core_translation[wp_api_key] = col
        # if Registrar.DEBUG_API: Registrar.registerMessage("core_translation: %s" % pformat(core_translation))
        parserData.update(**cls.translateKeys(apiData, core_translation))

        meta_translation = OrderedDict()
        if 'meta' in apiData:
            metaData = apiData['meta']
            for col, col_data in ColData_Woo.getWPAPIMetaCols().items():
                try:
                    wp_api_key = col_data['wp-api']['key']
                except:
                    wp_api_key = col
                meta_translation[wp_api_key] = col
            parserData.update(**cls.translateKeys(metaData, meta_translation))
        if 'dimensions' in apiData:
            parserData.update(**cls.getApiDimensionData(apiData['dimensions']))
        if 'in_stock' in apiData:
            parserData.update(**cls.getApiStockStatusData(apiData['in_stock']))
        # if 'description' in apiData:
        #     parserData[cls.objectContainer.descriptionKey] = apiData['description']
        # Stupid hack because 'name' is 'title' in products, but 'name' in categories
        if 'title' in apiData:
            parserData[cls.objectContainer.titleKey] = apiData['title']

        assert \
            cls.objectContainer.descriptionKey in parserData, \
            "parserData should have description: %s\n original: %s\ntranslations: %s, %s" \
                % (parserData, apiData, core_translation, meta_translation)
        parserData[cls.objectContainer.descsumKey] = parserData[cls.objectContainer.descriptionKey]
        assert \
            cls.objectContainer.titleKey in parserData, \
            "parserData should have title: %s\n original: %s\ntranslations: %s, %s" \
                % (parserData, apiData, core_translation, meta_translation)
        if apiData['type'] == 'category':
            parserData[cls.categoryContainer.namesumKey] = parserData[cls.objectContainer.titleKey]
            assert \
                cls.objectContainer.slugKey in parserData, \
                "parserData should have slug: %s\n original: %s\ntranslations: %s, %s" \
                    % (parserData, apiData, core_translation, meta_translation)
            parserData[cls.objectContainer.codesumKey] = parserData[cls.objectContainer.slugKey]
        else:
            parserData[cls.objectContainer.namesumKey] = parserData[cls.objectContainer.titleKey]
        assert \
            cls.objectContainer.codesumKey in parserData, \
            "parserData should have codesum: %s\n original: %s\ntranslations: %s, %s" \
                % (parserData, apiData, core_translation, meta_translation)
        assert \
            cls.objectContainer.namesumKey in parserData, \
            "parserData should have namesum: %s\n original: %s\ntranslations: %s, %s" \
                % (parserData, apiData, core_translation, meta_translation)

        # title = parserData.get(cls.objectContainer.titleKey, '')
        # if not title and 'title' in apiData:
        #     title = apiData['title']
        # if not title and 'name' in apiData:
        #     title = apiData['name']
        # parserData[cls.objectContainer.titleKey] = title
        # parserData[cls.objectContainer.namesumKey] = title
        #
        # slug = parserData.get(cls.objectContainer.slugKey,'')
        # if not slug and 'slug' in apiData:
        #     slug = apiData['slug']
        # parserData[cls.objectContainer.slugKey] = slug
        #
        description = parserData.get(cls.objectContainer.descriptionKey, '')
        if not description and 'description' in apiData:
            description = apiData['description']
        parserData[cls.objectContainer.descriptionKey] = description
        parserData[cls.objectContainer.descsumKey] = description


        if Registrar.DEBUG_API: Registrar.registerMessage( "parserData: {}".format(pformat(parserData)) )
        return parserData


    def getKwargs(self, allData, container, **kwargs):
        if not 'parent' in kwargs:
            kwargs['parent'] = self.rootData
        return kwargs

    def getNewObjContainer(self, allData, **kwargs):
        if self.DEBUG_MRO:
            self.registerMessage(' ')
        container = super(CSVParse_Woo_Api, self).getNewObjContainer( allData, **kwargs)
        apiData = kwargs.get('apiData', {})
        if self.DEBUG_API:
            self.registerMessage('apiData: %s' % str(apiData))
            self.registerMessage('apiData[type]: %s' % repr(apiData.get('type')))
        if 'type' in apiData:
            api_type = apiData['type']
            if self.DEBUG_API:
                self.registerMessage('api type: %s' % str(api_type))
            try:
                container = self.containers[api_type]
            except IndexError:
                e = UserWarning("Unknown API product type: %s" % api_type)
                source = apiData.get('SKU')
                self.registerError(e, source)
        if self.DEBUG_API: self.registerMessage("container: {}".format(container.__name__))
        return container

    def analyseWpApiObj(self, apiData):
        if self.DEBUG_API:
            self.registerMessage("API DATA CATEGORIES: %s" % repr(apiData.get('categories')))
        if not apiData.get('categories'):
            if self.DEBUG_API:
                self.registerMessage("NO CATEGORIES FOUND IN API DATA: %s" % repr(apiData))
        kwargs = {
            'apiData':apiData
        }
        objectData = self.newObject(rowcount=self.rowcount, **kwargs)
        if self.DEBUG_API:
            self.registerMessage("CONSTRUCTED: %s" % objectData.identifier)
        self.processObject(objectData)
        if self.DEBUG_API:
            self.registerMessage("PROCESSED: %s" % objectData.identifier)
        self.registerObject(objectData)
        if self.DEBUG_API:
            self.registerMessage("REGISTERED: %s" % objectData.identifier)
        # self.registerMessage("mro: {}".format(container.mro()))
        self.rowcount += 1

        if 'categories' in apiData:
            for category in apiData['categories']:
                self.processApiCategory({'title':category}, objectData)
                # self.rowcount += 1

        if 'variations' in apiData:
            for variation in apiData['variations']:
                self.analyseWpApiVariation(objectData, variation)
                # self.rowcount += 1

        if 'attributes' in apiData:
            self.processApiAttributes(objectData, apiData['attributes'], False)

    def analyseWpApiVariation(self, objectData, variationApiData):
        if self.DEBUG_API:
            self.registerMessage("parentData: %s" % pformat(objectData.items()))
            self.registerMessage("variationApiData: %s" % pformat(variationApiData))
        defaultVarData = dict(
            type='variation',
            title='Variation #%s of %s' % (variationApiData.get('id'), objectData.title),
            description=objectData.get('descsum'),
            parent_id=objectData.get('ID')
        )
        defaultVarData.update(**variationApiData)
        if self.DEBUG_API:
            self.registerMessage("defaultVarData: %s" % pformat(defaultVarData))

        kwargs = {
            'apiData':defaultVarData,
            'parent':objectData
        }

        variationData = self.newObject(rowcount=self.rowcount, **kwargs)

        if self.DEBUG_API:
            self.registerMessage("CONSTRUCTED: %s" % variationData.identifier)
        self.processObject(variationData)
        if self.DEBUG_API:
            self.registerMessage("PROCESSED: %s" % variationData.identifier)
        self.registerObject(variationData)
        # self.registerVariation(objectData, variationData)
        if self.DEBUG_API:
            self.registerMessage("REGISTERED: %s" % variationData.identifier)

        self.rowcount += 1

        if 'attributes' in variationApiData:
            self.processApiAttributes(objectData, variationApiData['attributes'], True)
