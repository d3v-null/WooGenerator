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
        self.category_indexer = CSVParse_Woo_Mixin.getTitle

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
        assert self.descsumKey in self, "descsum should be set in %s. data: %s " % (
            self, self.items())
        # self.namesum = self.title
        assert self.namesumKey in self, "namesum should be set in %s. data: %s " % (
            self, self.items())
        # if self.isCategory:
        #     self.codesum = ''
        assert self.codesumKey in self, "codesum should be set in %s. data: %s " % (
            self, self.items())


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


class ImportApiProductVariable(
        ImportApiProduct, ImportShopProductVariableMixin):
    isVariable = ImportShopProductVariableMixin.isVariable
    product_type = ImportShopProductVariableMixin.product_type

    def __init__(self, *args, **kwargs):
        if self.DEBUG_MRO:
            self.registerMessage('ImportApiProductVariable')
        ImportApiProduct.__init__(self, *args, **kwargs)
        ImportShopProductVariableMixin.__init__(self, *args, **kwargs)


class ImportApiProductVariation(
        ImportApiProduct, ImportShopProductVariationMixin):
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
# class CSVParse_Woo_Api(CSVParse_Base, CSVParse_Shop_Mixin,
# CSVParse_Woo_Mixin):


class CSVParse_Woo_Api(CSVParse_Base, CSVParse_Tree_Mixin,
                       CSVParse_Shop_Mixin, CSVParse_Woo_Mixin):
    objectContainer = ImportApiObject
    productContainer = ImportApiProduct
    simpleContainer = ImportApiProductSimple
    variableContainer = ImportApiProductVariable
    variationContainer = ImportApiProductVariation
    categoryContainer = ImportApiCategory
    # category_indexer = CSVParse_Gen_Mixin.getNameSum
    # category_indexer = CSVParse_Woo_Mixin.getTitle
    # category_indexer = CSVParse_Woo_Mixin.getWPID
    category_indexer = CSVParse_Base.getObjectRowcount
    productIndexer = CSVParse_Shop_Mixin.productIndexer
    variationIndexer = CSVParse_Woo_Mixin.getTitle

    def __init__(self, *args, **kwargs):
        if self.DEBUG_MRO:
            self.registerMessage('CSVParse_Woo_Api')
        super(CSVParse_Woo_Api, self).__init__(*args, **kwargs)
        # self.category_indexer = CSVParse_Gen_Mixin.getNameSum
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

    def registerObject(self, object_data):
        # CSVParse_Gen_Tree.registerObject(self, object_data)
        CSVParse_Base.registerObject(self, object_data)
        # CSVParse_Tree_Mixin.registerObject(self, object_data)
        CSVParse_Shop_Mixin.registerObject(self, object_data)
        # CSVParse_Woo_Mixin.registerObject(self, object_data)

    # def processObject(self, object_data):
        # super(CSVParse_Woo_Api, self).processObject(object_data)
        # todo: this

    # def registerObject(self, object_data):
    #     if self.DEBUG_MRO:
    #         self.registerMessage(' ')
    #     if self.DEBUG_API:
    #         self.registerMessage("registering object_data: %s" % str(object_data))
    #     super(CSVParse_Woo_Api, self).registerObject(object_data)

    @classmethod
    def getApiDimensionData(cls, dimensions):
        new_data = OrderedDict()
        for dimension_key in ['length', 'width', 'height']:
            if dimension_key in dimensions:
                new_data[dimension_key] = dimensions[dimension_key]
                # object_data[dimension_key] = dimensions[dimension_key]
        return new_data

    @classmethod
    def getApiStockStatusData(cls, in_stock):
        new_data = OrderedDict()
        if in_stock:
            stock_status = 'in_stock'
        else:
            stock_status = 'outofstock'
        new_data['stock_status'] = stock_status
        return new_data

    def processApiCategory(self, categoryApiData, object_data=None):
        """
        Create category if not exist or find if exist, then assign object_data to category
        Has to emulate CSVParse_Base.newObject()
        """
        if self.DEBUG_API:
            category_title = categoryApiData.get('title', '')
            if object_data:
                identifier = object_data.identifier
                self.registerMessage(
                    "%s member of category %s"
                    % (identifier, category_title)
                )
            else:
                self.registerMessage(
                    "creating category %s" % (category_title)
                )

        #
        if self.DEBUG_API:
            self.registerMessage("ANALYSE CATEGORY: %s" %
                                 repr(categoryApiData))
        core_translation = OrderedDict()
        for col, col_data in ColData_Woo.get_wpapi_core_cols().items():
            try:
                wp_api_key = col_data['wp-api']['key']
            except:
                wp_api_key = col
            core_translation[wp_api_key] = col
        category_search_data = {}
        category_search_data.update(
            **self.translateKeys(categoryApiData, core_translation))
        category_search_data = dict([(key, SanitationUtils.html_unescape_recursive(value))
                                   for key, value in category_search_data.items()])

        # if 'id' in categoryApiData:
        #     category_search_data[self.categoryContainer.wpidKey] = categoryApiData['id']
        # if 'name' in categoryApiData:
        #     category_search_data[self.categoryContainer.titleKey] = categoryApiData['name']
        #     category_search_data[self.categoryContainer.namesumKey] = categoryApiData['name']
        # elif 'title' in categoryApiData:
        #     category_search_data[self.categoryContainer.titleKey] = categoryApiData['title']
        #     category_search_data[self.categoryContainer.namesumKey] = categoryApiData['title']
        # if 'slug' in categoryApiData:
        #     category_search_data[self.categoryContainer.slugKey] = categoryApiData['slug']
        if self.DEBUG_API:
            self.registerMessage("SEARCHING FOR CATEGORY: %s" %
                                 repr(category_search_data))
        cat_data = self.findCategory(category_search_data)
        if not cat_data:
            if self.DEBUG_API:
                self.registerMessage("CATEGORY NOT FOUND")

            categoryApiData['type'] = 'category'
            if not 'description' in categoryApiData:
                categoryApiData['description'] = ''
            if not 'slug' in categoryApiData:
                categoryApiData['slug'] = ''

            kwargs = OrderedDict()
            kwargs['api_data'] = categoryApiData

            # default_data = OrderedDict(self.defaults.items())
            #
            # parser_data = self.getParserData(**kwargs)
            #
            # all_data = listUtils.combineOrderedDicts(default_data, parser_data)
            #
            # container = self.getNewObjContainer(all_data, **kwargs)
            #
            # cat_data = container(all_data, **kwargs)

            # kwargs = OrderedDict(self.defaults.items())
            # kwargs.update(category_search_data)
            # catRowcount = getattr(self, 'rowcount')
            # if 'id' in categoryApiData:
            #     catRowcount = categoryApiData['id']
            parent_category_data = None
            if 'parent' in categoryApiData:
                parent_category_search_data = {}
                parent_category_search_data[
                    self.categoryContainer.wpidKey] = categoryApiData['parent']
                parent_category_data = self.findCategory(
                    parent_category_search_data)
            if parent_category_data:
                kwargs['parent'] = parent_category_data
            else:
                kwargs['parent'] = self.rootData

            cat_data = self.newObject(rowcount=self.rowcount, **kwargs)

            if self.DEBUG_API:
                self.registerMessage("CONSTRUCTED: %s" % cat_data.identifier)
            self.processObject(cat_data)
            if self.DEBUG_API:
                self.registerMessage("PROCESSED: %s" % cat_data.identifier)
            self.registerCategory(cat_data)
            if self.DEBUG_API:
                self.registerMessage("REGISTERED: %s" % cat_data.identifier)

        else:
            if self.DEBUG_API:
                self.registerMessage("FOUND CATEGORY: %s" % repr(cat_data))

        self.joinCategory(cat_data, object_data)
        # if self.DEBUG_API:
        #     index = self.category_indexer(cat_data)
        #     self.registerMessage(repr(self.category_indexer))
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
                queue_category_ids = [queue_category.get(
                    'id') for queue_category in categories]
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

    def processApiAttributes(self, object_data, attributes, var=False):
        varstr = 'var ' if var else ''
        for attribute in attributes:
            if self.DEBUG_API:
                self.registerMessage("%s has %sattribute %s" % (
                    object_data.identifier, varstr, attribute))
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
                    self.registerAttribute(object_data, attr, val, var)

    @classmethod
    def getParserData(cls, **kwargs):
        """
        Gets data ready for the parser, in this case from api_data
        """
        parser_data = OrderedDict()
        api_data = kwargs.get('api_data', {})
        # print "api_data before: %s" % str(api_data)
        api_data = dict([(key, SanitationUtils.html_unescape_recursive(value))
                        for key, value in api_data.items()])
        # print "api_data after:  %s" % str(api_data)
        parser_data = OrderedDict()
        core_translation = OrderedDict()
        for col, col_data in ColData_Woo.get_wpapi_core_cols().items():
            try:
                wp_api_key = col_data['wp-api']['key']
            except:
                wp_api_key = col
            core_translation[wp_api_key] = col
        # if Registrar.DEBUG_API: Registrar.registerMessage("core_translation: %s" % pformat(core_translation))
        parser_data.update(**cls.translateKeys(api_data, core_translation))

        meta_translation = OrderedDict()
        if 'meta' in api_data:
            meta_data = api_data['meta']
            for col, col_data in ColData_Woo.getWPAPIMetaCols().items():
                try:
                    wp_api_key = col_data['wp-api']['key']
                except:
                    wp_api_key = col
                meta_translation[wp_api_key] = col
            parser_data.update(**cls.translateKeys(meta_data, meta_translation))
        if 'dimensions' in api_data:
            parser_data.update(**cls.getApiDimensionData(api_data['dimensions']))
        if 'in_stock' in api_data:
            parser_data.update(**cls.getApiStockStatusData(api_data['in_stock']))
        # if 'description' in api_data:
        #     parser_data[cls.objectContainer.descriptionKey] = api_data['description']
        # Stupid hack because 'name' is 'title' in products, but 'name' in
        # categories
        if 'title' in api_data:
            parser_data[cls.objectContainer.titleKey] = api_data['title']

        assert \
            cls.objectContainer.descriptionKey in parser_data, \
            "parser_data should have description: %s\n original: %s\ntranslations: %s, %s" \
            % (parser_data, api_data, core_translation, meta_translation)
        parser_data[cls.objectContainer.descsumKey] = parser_data[
            cls.objectContainer.descriptionKey]
        assert \
            cls.objectContainer.titleKey in parser_data, \
            "parser_data should have title: %s\n original: %s\ntranslations: %s, %s" \
            % (parser_data, api_data, core_translation, meta_translation)
        if api_data['type'] == 'category':
            parser_data[cls.categoryContainer.namesumKey] = parser_data[
                cls.objectContainer.titleKey]
            assert \
                cls.objectContainer.slugKey in parser_data, \
                "parser_data should have slug: %s\n original: %s\ntranslations: %s, %s" \
                % (parser_data, api_data, core_translation, meta_translation)
            parser_data[cls.objectContainer.codesumKey] = parser_data[
                cls.objectContainer.slugKey]
        else:
            parser_data[cls.objectContainer.namesumKey] = parser_data[
                cls.objectContainer.titleKey]
        assert \
            cls.objectContainer.codesumKey in parser_data, \
            "parser_data should have codesum: %s\n original: %s\ntranslations: %s, %s" \
            % (parser_data, api_data, core_translation, meta_translation)
        assert \
            cls.objectContainer.namesumKey in parser_data, \
            "parser_data should have namesum: %s\n original: %s\ntranslations: %s, %s" \
            % (parser_data, api_data, core_translation, meta_translation)

        # title = parser_data.get(cls.objectContainer.titleKey, '')
        # if not title and 'title' in api_data:
        #     title = api_data['title']
        # if not title and 'name' in api_data:
        #     title = api_data['name']
        # parser_data[cls.objectContainer.titleKey] = title
        # parser_data[cls.objectContainer.namesumKey] = title
        #
        # slug = parser_data.get(cls.objectContainer.slugKey,'')
        # if not slug and 'slug' in api_data:
        #     slug = api_data['slug']
        # parser_data[cls.objectContainer.slugKey] = slug
        #
        description = parser_data.get(cls.objectContainer.descriptionKey, '')
        if not description and 'description' in api_data:
            description = api_data['description']
        parser_data[cls.objectContainer.descriptionKey] = description
        parser_data[cls.objectContainer.descsumKey] = description

        if Registrar.DEBUG_API:
            Registrar.registerMessage(
                "parser_data: {}".format(pformat(parser_data)))
        return parser_data

    def getKwargs(self, all_data, container, **kwargs):
        if not 'parent' in kwargs:
            kwargs['parent'] = self.rootData
        return kwargs

    def getNewObjContainer(self, all_data, **kwargs):
        if self.DEBUG_MRO:
            self.registerMessage(' ')
        container = super(CSVParse_Woo_Api, self).getNewObjContainer(
            all_data, **kwargs)
        api_data = kwargs.get('api_data', {})
        if self.DEBUG_API:
            self.registerMessage('api_data: %s' % str(api_data))
            self.registerMessage('api_data[type]: %s' %
                                 repr(api_data.get('type')))
        if 'type' in api_data:
            api_type = api_data['type']
            if self.DEBUG_API:
                self.registerMessage('api type: %s' % str(api_type))
            try:
                container = self.containers[api_type]
            except IndexError:
                exc = UserWarning("Unknown API product type: %s" % api_type)
                source = api_data.get('SKU')
                self.registerError(exc, source)
        if self.DEBUG_API:
            self.registerMessage("container: {}".format(container.__name__))
        return container

    def analyseWpApiObj(self, api_data):
        if self.DEBUG_API:
            self.registerMessage("API DATA CATEGORIES: %s" %
                                 repr(api_data.get('categories')))
        if not api_data.get('categories'):
            if self.DEBUG_API:
                self.registerMessage(
                    "NO CATEGORIES FOUND IN API DATA: %s" % repr(api_data))
        kwargs = {
            'api_data': api_data
        }
        object_data = self.newObject(rowcount=self.rowcount, **kwargs)
        if self.DEBUG_API:
            self.registerMessage("CONSTRUCTED: %s" % object_data.identifier)
        self.processObject(object_data)
        if self.DEBUG_API:
            self.registerMessage("PROCESSED: %s" % object_data.identifier)
        self.registerObject(object_data)
        if self.DEBUG_API:
            self.registerMessage("REGISTERED: %s" % object_data.identifier)
        # self.registerMessage("mro: {}".format(container.mro()))
        self.rowcount += 1

        if 'categories' in api_data:
            for category in api_data['categories']:
                self.processApiCategory({'title': category}, object_data)
                # self.rowcount += 1

        if 'variations' in api_data:
            for variation in api_data['variations']:
                self.analyseWpApiVariation(object_data, variation)
                # self.rowcount += 1

        if 'attributes' in api_data:
            self.processApiAttributes(object_data, api_data['attributes'], False)

    def analyseWpApiVariation(self, object_data, variationApiData):
        if self.DEBUG_API:
            self.registerMessage("parent_data: %s" %
                                 pformat(object_data.items()))
            self.registerMessage("variationApiData: %s" %
                                 pformat(variationApiData))
        default_var_data = dict(
            type='variation',
            title='Variation #%s of %s' % (
                variationApiData.get('id'), object_data.title),
            description=object_data.get('descsum'),
            parent_id=object_data.get('ID')
        )
        default_var_data.update(**variationApiData)
        if self.DEBUG_API:
            self.registerMessage("default_var_data: %s" %
                                 pformat(default_var_data))

        kwargs = {
            'api_data': default_var_data,
            'parent': object_data
        }

        variation_data = self.newObject(rowcount=self.rowcount, **kwargs)

        if self.DEBUG_API:
            self.registerMessage("CONSTRUCTED: %s" % variation_data.identifier)
        self.processObject(variation_data)
        if self.DEBUG_API:
            self.registerMessage("PROCESSED: %s" % variation_data.identifier)
        self.registerObject(variation_data)
        # self.registerVariation(object_data, variation_data)
        if self.DEBUG_API:
            self.registerMessage("REGISTERED: %s" % variation_data.identifier)

        self.rowcount += 1

        if 'attributes' in variationApiData:
            self.processApiAttributes(
                object_data, variationApiData['attributes'], True)
