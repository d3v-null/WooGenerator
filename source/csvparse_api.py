"""Introduces woo structure to shop classes"""
from utils import listUtils, SanitationUtils, TimeUtils, PHPUtils, Registrar, descriptorUtils
from csvparse_abstract import ObjList, CSVParse_Base
from csvparse_tree import ItemList, TaxoList, ImportTreeObject, CSVParse_Rootable_Mixin
from csvparse_gen import CSVParse_Gen_Tree, ImportGenItem
from csvparse_gen import ImportGenTaxo, ImportGenObject, ImportGenFlat, CSVParse_Gen_Mixin
from csvparse_shop import ImportShop, ImportShopProduct, ImportShopProductSimple
from csvparse_shop import ImportShopProductVariable, ImportShopProductVariation
from csvparse_shop import ImportShopCategory, CSVParse_Shop_Mixin
from csvparse_flat import CSVParse_Flat, ImportFlat
from csvparse_woo import CSVParse_Woo_Mixin, ImportWooMixin
from coldata import ColData_Woo
from collections import OrderedDict
import bisect
import time

class ImportApiObject(ImportGenFlat, ImportShop, ImportWooMixin):
    def __init__(self, *args, **kwargs):
        super(ImportApiObject, self).__init__(*args, **kwargs)
        self.categoryIndexer = CSVParse_Gen_Mixin.getNameSum

class ImportApiProduct(ImportApiObject, ImportShopProduct): pass

class ImportApiProductSimple(ImportApiObject, ImportShopProductSimple): pass

class ImportApiProductVariable(ImportApiObject, ImportShopProductVariable): pass

class ImportApiProductVariation(ImportApiObject, ImportShopProductVariation): pass

class ImportApiCategory(ImportApiObject, ImportShopCategory):
    @property
    def index(self):
        return self.namesum

class CSVParse_Woo_Api(CSVParse_Flat, CSVParse_Shop_Mixin, CSVParse_Woo_Mixin, CSVParse_Rootable_Mixin):
    objectContainer = ImportApiObject
    productContainer = ImportApiProduct
    simpleContainer = ImportApiProductSimple
    variableContainer = ImportApiProductVariable
    variationContainer = ImportApiProductVariation
    categoryContainer = ImportApiCategory
    categoryIndexer = CSVParse_Gen_Mixin.getNameSum
    categoryIndexer = CSVParse_Woo_Mixin.getTitle
    productIndexer = CSVParse_Shop_Mixin.productIndexer


    def __init__(self, *args, **kwargs):
        super(CSVParse_Woo_Api, self).__init__(*args, **kwargs)
        # self.categoryIndexer = CSVParse_Gen_Mixin.getNameSum
        # if hasattr(CSVParse_Woo_Mixin, '__init__'):
        #     CSVParse_Gen_Mixin.__init__(self, *args, **kwargs)

    def clearTransients(self):
        # for base_class in CSVParse_Woo_Api.__bases__:
        #     if hasattr(base_class, 'clearTransients'):
        #         base_class.clearTransients(self)
        CSVParse_Flat.clearTransients(self)
        CSVParse_Shop_Mixin.clearTransients(self)
        CSVParse_Woo_Mixin.clearTransients(self)
        CSVParse_Rootable_Mixin.clearTransients(self)

        # super(CSVParse_Woo_Api, self).clearTransients()
        # CSVParse_Shop_Mixin.clearTransients(self)


    def registerObject(self, objectData):
        CSVParse_Gen_Tree.registerObject(self, objectData)
        CSVParse_Shop_Mixin.registerObject(self, objectData)

    # def processObject(self, objectData):
        # super(CSVParse_Woo_Api, self).processObject(objectData)
        #todo: this

    # def registerObject(self, objectData):
    #     if self.DEBUG_MRO:
    #         self.registerMessage(' ')
    #     if self.DEBUG_API:
    #         self.registerMessage("registering objectData: %s" % str(objectData))
    #     super(CSVParse_Woo_Api, self).registerObject(objectData)

    def getApiDimensionData(self, objectData, dimensions):
        for dimension_key in ['length', 'width', 'height']:
            if dimension_key in dimensions:
                objectData[dimension_key] = dimensions[dimension_key]

    def getApiStockStatusData(self, objectData, in_stock):
        if in_stock:
            stock_status = 'in_stock'
        else:
            stock_status = 'outofstock'
        objectData['stock_status'] = stock_status

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
        categorySearchData = {}
        if 'id' in categoryApiData:
            categorySearchData[self.categoryContainer.wpidKey] = categoryApiData['id']
        if 'name' in categoryApiData:
            categorySearchData[self.categoryContainer.titleKey] = categoryApiData['name']
            categorySearchData[self.categoryContainer.namesumKey] = categoryApiData['name']
        if 'slug' in categoryApiData:
            categorySearchData[self.categoryContainer.slugKey] = categoryApiData['slug']
            categorySearchData[self.categoryContainer.codesumKey] = categoryApiData['slug']
        catData = self.findCategory(categorySearchData)
        if not catData:
            if self.DEBUG_API:
                self.registerMessage("CATEGORY NOT FOUND")

            categoryApiData['type'] = 'category'

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

        else:
            if self.DEBUG_API:
                self.registerMessage("FOUND CATEGORY: %s" % repr(catData))



        if self.DEBUG_API:
            self.registerMessage("CONSTRUCTED: %s" % catData.identifier)
        self.processObject(catData)
        if self.DEBUG_API:
            self.registerMessage("PROCESSED: %s" % catData.identifier)
        if self.DEBUG_API:
            index = self.categoryIndexer(catData)
            self.registerMessage(repr(self.categoryIndexer))
            self.registerMessage("REGISTERING CATEGORY WITH INDEX %s" % repr(index))
        self.registerCategory(catData, objectData)
        if self.DEBUG_API:
            self.registerMessage("REGISTERED: %s" % catData.identifier)

        self.rowcount += 1


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


    def getParserData(self, **kwargs):
        """
        Gets data ready for the parser, in this case from apiData
        """
        parserData = OrderedDict()
        apiData = kwargs.get('apiData',{})
        for col, col_data in ColData_Woo.getWPAPICoreCols().items():
            try:
                wp_api_key = col_data['wp-api']['key']
            except:
                wp_api_key = col
            if wp_api_key in apiData:
                parserData[col] = apiData[wp_api_key]
        if 'meta' in apiData:
            metaData = apiData['meta']
            for col, col_data in ColData_Woo.getWPAPIMetaCols().items():
                try:
                    wp_api_key = col_data['wp-api']['key']
                except:
                    wp_api_key = col
                if wp_api_key in metaData:
                    parserData[col] = metaData[wp_api_key]
        if 'dimensions' in apiData:
            self.getApiDimensionData(parserData, apiData['dimensions'])
        if 'in_stock' in apiData:
            self.getApiStockStatusData(parserData, apiData['in_stock'])
        if 'description' in apiData:
            parserData[self.categoryContainer.descriptionKey] = apiData['description']
        if 'name' in apiData:
            parserData[self.categoryContainer.titleKey] = apiData['name']
        if 'slug' in apiData:
            parserData[self.categoryContainer.slugKey] = apiData['slug']
        if self.DEBUG_API: self.registerMessage( "parserData: {}".format(parserData) )
        return parserData

    def getNewObjContainer(self, allData, **kwargs):
        if self.DEBUG_MRO:
            self.registerMessage(' ')
        container = super(CSVParse_Woo_Api, self).getNewObjContainer( allData, **kwargs)
        apiData = kwargs.get('apiData', {})
        if 'type' in apiData:
            api_type = apiData['type']
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
            'apiData':apiData,
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
        variationApiData.update(
            type='variation',
            title='Variation #%s of %s' % (variationApiData.get('id'), objectData.namesum),
            description=objectData.get('descsum')
        )
        kwargs = {
            'apiData':variationApiData,
        }
        variationData = self.newObject(rowcount=self.rowcount, **kwargs)

        if self.DEBUG_API:
            self.registerMessage("CONSTRUCTED: %s" % variationData.identifier)
        self.processObject(variationData)
        if self.DEBUG_API:
            self.registerMessage("PROCESSED: %s" % variationData.identifier)
        self.registerObject(variationData)
        self.registerVariation(objectData, variationData)
        if self.DEBUG_API:
            self.registerMessage("REGISTERED: %s" % variationData.identifier)

        self.rowcount += 1

        if 'attributes' in variationApiData:
            self.processApiAttributes(objectData, variationApiData['attributes'], True)
