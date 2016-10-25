"""Introduces woo structure to shop classes"""
from utils import listUtils, SanitationUtils, TimeUtils, PHPUtils, Registrar, descriptorUtils
from csvparse_abstract import ObjList, CSVParse_Base
from csvparse_tree import ItemList, TaxoList, ImportTreeObject
from csvparse_gen import CSVParse_Gen_Tree, ImportGenItem, ImportGenBase
from csvparse_gen import ImportGenTaxo, ImportGenObject, ImportGenFlat, CSVParse_Gen_Mixin
from csvparse_shop import ImportShop, ImportShopProduct, ImportShopProductSimple
from csvparse_shop import ImportShopProductVariable, ImportShopProductVariation
from csvparse_shop import ImportShopCategory, CSVParse_Shop_Mixin
from csvparse_flat import CSVParse_Flat, ImportFlat
from coldata import ColData_Woo
from collections import OrderedDict
import bisect
import time

class ImportApi(ImportGenFlat, ImportShop):
    pass
    # def __init__(self, *args, **kwargs):
    #     super(ImportApiShop, self).__init__(*args, **kwargs)
    #     self.verifyMeta()

class ImportApiProduct(ImportApi, ImportShopProduct): pass

class ImportApiProductSimple(ImportApi, ImportShopProductSimple): pass

class ImportApiProductVariable(ImportApi, ImportShopProductVariable): pass

class ImportApiProductVariation(ImportApi, ImportShopProductVariation): pass

class ImportApiCategory(ImportApi, ImportShopCategory):
    @property
    def index(self):
        return self.namesum

class CSVParse_Woo_Api(CSVParse_Flat, CSVParse_Shop_Mixin):
    productContainer = ImportApiProduct
    simpleContainer = ImportApiProductSimple
    variableContainer = ImportApiProductVariable
    variationContainer = ImportApiProductVariation
    categoryContainer = ImportApiCategory

    productIndexer = CSVParse_Shop_Mixin.productIndexer
    categoryIndexer = CSVParse_Gen_Mixin.getNameSum

    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)

    def clearTransients(self):
        super(CSVParse_Woo_Api, self).clearTransients()
        # CSVParse_Shop_Mixin.clearTransients(self)

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

    def processApiCategory(self, objectData, category):
        if self.DEBUG_API:
            self.registerMessage("%s member of category %s" % (objectData.identifier, category))
        defaultData = OrderedDict(self.defaults.items())
        kwargs = {
            'apiData':{
                'title':category,
                'type':'category',
                'description':'',
                'sku':'',
            },
        }
        catData = self.newObject(rowcount=self.rowcount, **kwargs)
        # parserData = {
        #     'taxosum': category,
        #     'descsum': '',
        #     'codesum': '',
        #     'itemsum': ''
        # }
        # catKwargs = {
        #     'row':[],
        #     'rowcount':self.rowcount,
        # }
        # catData = self.categoryContainer(
        #     parserData,
        #     **catKwargs
        # )
        if self.DEBUG_API:
            self.registerMessage("CONSTRUCTED: %s" % catData.identifier)
        self.processObject(catData)
        if self.DEBUG_API:
            self.registerMessage("PROCESSED: %s" % catData.identifier)
        self.registerCategory(catData, objectData)
        if self.DEBUG_API:
            self.registerMessage("REGISTERED: %s" % catData.identifier)

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
                self.processApiCategory(objectData, category)
                self.rowcount += 1


        if 'variations' in apiData:
            for variation in apiData['variations']:
                self.analyseWpApiVariation(objectData, variation)
                self.rowcount += 1

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

        if 'attributes' in variationApiData:
            self.processApiAttributes(objectData, variationApiData['attributes'], True)
