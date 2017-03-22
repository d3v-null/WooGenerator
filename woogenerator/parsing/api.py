"""
Introduce woo api structure to shop classes.
"""
from collections import OrderedDict
from pprint import pformat

from woogenerator.coldata import ColDataWoo
from woogenerator.parsing.abstract import CsvParseBase
from woogenerator.parsing.tree import CsvParseTreeMixin
from woogenerator.parsing.gen import ImportGenObject
from woogenerator.parsing.shop import (CsvParseShopMixin,
                                       ImportShopCategoryMixin,
                                       ImportShopMixin, ImportShopProductMixin,
                                       ImportShopProductSimpleMixin,
                                       ImportShopProductVariableMixin,
                                       ImportShopProductVariationMixin)
from woogenerator.parsing.woo import CsvParseWooMixin, ImportWooMixin
from woogenerator.utils import Registrar, SanitationUtils


class ImportApiObject(ImportGenObject, ImportShopMixin, ImportWooMixin):

    def __init__(self, *args, **kwargs):
        if self.DEBUG_MRO:
            self.register_message('ImportApiObject')
        ImportGenObject.__init__(self, *args, **kwargs)
        ImportShopMixin.__init__(self, *args, **kwargs)
        ImportWooMixin.__init__(self, *args, **kwargs)
        self.category_indexer = CsvParseWooMixin.get_title

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

    def process_meta(self):
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
            self.register_message('ImportApiProduct')
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
            self.register_message('ImportApiProductVariable')
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
            self.register_message('ImportApiCategory')
        ImportApiObject.__init__(self, *args, **kwargs)
        ImportShopCategoryMixin.__init__(self, *args, **kwargs)

    @property
    def woo_cat_name(self):
        return self.title

    @property
    def index(self):
        return self.title

    @property
    def identifier(self):
        return "|".join([
            'r:%s' % str(self.rowcount),
            'w:%s' % str(self.get(self.wpidKey)),
            self.title,
        ])


class CsvParseWooApi(CsvParseBase, CsvParseTreeMixin,
                     CsvParseShopMixin, CsvParseWooMixin):
    objectContainer = ImportApiObject
    productContainer = ImportApiProduct
    simpleContainer = ImportApiProductSimple
    variableContainer = ImportApiProductVariable
    variationContainer = ImportApiProductVariation
    categoryContainer = ImportApiCategory
    # category_indexer = CsvParseGenMixin.get_name_sum
    # category_indexer = CsvParseWooMixin.get_title
    # category_indexer = CsvParseWooMixin.get_wpid
    category_indexer = CsvParseBase.get_object_rowcount
    productIndexer = CsvParseShopMixin.productIndexer
    variationIndexer = CsvParseWooMixin.get_title

    def __init__(self, *args, **kwargs):
        if self.DEBUG_MRO:
            self.register_message('CsvParseWooApi')
        super(CsvParseWooApi, self).__init__(*args, **kwargs)
        # self.category_indexer = CsvParseGenMixin.get_name_sum
        # if hasattr(CsvParseWooMixin, '__init__'):
        #     CsvParseGenMixin.__init__(self, *args, **kwargs)

    def clear_transients(self):
        # for base_class in CsvParseWooApi.__bases__:
        #     if hasattr(base_class, 'clear_transients'):
        #         base_class.clear_transients(self)
        # CsvParseFlat.clear_transients(self)
        CsvParseBase.clear_transients(self)
        CsvParseTreeMixin.clear_transients(self)
        CsvParseShopMixin.clear_transients(self)
        CsvParseWooMixin.clear_transients(self)

        # super(CsvParseWooApi, self).clear_transients()
        # CsvParseShopMixin.clear_transients(self)

    def register_object(self, object_data):
        # CsvParseGenTree.register_object(self, object_data)
        CsvParseBase.register_object(self, object_data)
        # CsvParseTreeMixin.register_object(self, object_data)
        CsvParseShopMixin.register_object(self, object_data)
        # CsvParseWooMixin.register_object(self, object_data)

    # def process_object(self, object_data):
        # super(CsvParseWooApi, self).process_object(object_data)
        # todo: this

    # def register_object(self, object_data):
    #     if self.DEBUG_MRO:
    #         self.register_message(' ')
    #     if self.DEBUG_API:
    #         self.register_message("registering object_data: %s" % str(object_data))
    #     super(CsvParseWooApi, self).register_object(object_data)

    @classmethod
    def get_api_dimension_data(cls, dimensions):
        new_data = OrderedDict()
        for dimension_key in ['length', 'width', 'height']:
            if dimension_key in dimensions:
                new_data[dimension_key] = dimensions[dimension_key]
                # object_data[dimension_key] = dimensions[dimension_key]
        return new_data

    @classmethod
    def get_api_stock_status_data(cls, in_stock):
        new_data = OrderedDict()
        if in_stock:
            stock_status = 'in_stock'
        else:
            stock_status = 'outofstock'
        new_data['stock_status'] = stock_status
        return new_data

    def process_api_category(self, categoryApiData, object_data=None):
        """
        Create category if not exist or find if exist, then assign object_data to category
        Has to emulate CsvParseBase.new_object()
        """
        if self.DEBUG_API:
            category_title = categoryApiData.get('title', '')
            if object_data:
                identifier = object_data.identifier
                self.register_message(
                    "%s member of category %s"
                    % (identifier, category_title)
                )
            else:
                self.register_message(
                    "creating category %s" % (category_title)
                )

        #
        if self.DEBUG_API:
            self.register_message("ANALYSE CATEGORY: %s" %
                                  repr(categoryApiData))
        core_translation = OrderedDict()
        for col, col_data in ColDataWoo.get_wpapi_core_cols().items():
            try:
                wp_api_key = col_data['wp-api']['key']
            except:
                wp_api_key = col
            core_translation[wp_api_key] = col
        category_search_data = {}
        category_search_data.update(
            **self.translate_keys(categoryApiData, core_translation))
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
            self.register_message("SEARCHING FOR CATEGORY: %s" %
                                  repr(category_search_data))
        cat_data = self.find_category(category_search_data)
        if not cat_data:
            if self.DEBUG_API:
                self.register_message("CATEGORY NOT FOUND")

            categoryApiData['type'] = 'category'
            if not 'description' in categoryApiData:
                categoryApiData['description'] = ''
            if not 'slug' in categoryApiData:
                categoryApiData['slug'] = ''

            kwargs = OrderedDict()
            kwargs['api_data'] = categoryApiData

            # default_data = OrderedDict(self.defaults.items())
            #
            # parser_data = self.get_parser_data(**kwargs)
            #
            # all_data = ListUtils.combine_ordered_dicts(default_data, parser_data)
            #
            # container = self.get_new_obj_container(all_data, **kwargs)
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
                parent_category_data = self.find_category(
                    parent_category_search_data)
            if parent_category_data:
                kwargs['parent'] = parent_category_data
            else:
                kwargs['parent'] = self.rootData

            cat_data = self.new_object(rowcount=self.rowcount, **kwargs)

            if self.DEBUG_API:
                self.register_message("CONSTRUCTED: %s" % cat_data.identifier)
            self.process_object(cat_data)
            if self.DEBUG_API:
                self.register_message("PROCESSED: %s" % cat_data.identifier)
            self.register_category(cat_data)
            if self.DEBUG_API:
                self.register_message("REGISTERED: %s" % cat_data.identifier)

        else:
            if self.DEBUG_API:
                self.register_message("FOUND CATEGORY: %s" % repr(cat_data))

        self.join_category(cat_data, object_data)
        # if self.DEBUG_API:
        #     index = self.category_indexer(cat_data)
        #     self.register_message(repr(self.category_indexer))
        #     self.register_message("REGISTERING CATEGORY WITH INDEX %s" % repr(index))

        self.rowcount += 1

    def process_api_categories(self, categories):
        """ creates a queue of categories to be processed in the correct order """
        while categories:
            category = categories.pop(0)
            # self.register_message("analysing category: %s" % category)
            if category.get('parent'):
                parent = category.get('parent')
                # self.register_message("parent id: %s" % parent)
                queue_category_ids = [queue_category.get(
                    'id') for queue_category in categories]
                if parent in queue_category_ids:
                    # self.register_message('analysing later')
                    categories.append(category)
                    continue
                # self.register_message("queue categories: %s" % queue_category_ids)
                # for queue_category in categories:
                #     # If category's parent exists in queue
                #     if queue_category.get('id') == parent:
                #         # then put it at the end of the queue
                #         categories.append(category)
            self.process_api_category(category)

    def process_api_attributes(self, object_data, attributes, var=False):
        varstr = 'var ' if var else ''
        for attribute in attributes:
            if self.DEBUG_API:
                self.register_message("%s has %sattribute %s" % (
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
                    self.register_attribute(object_data, attr, val, var)

    @classmethod
    def get_parser_data(cls, **kwargs):
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
        for col, col_data in ColDataWoo.get_wpapi_core_cols().items():
            try:
                wp_api_key = col_data['wp-api']['key']
            except:
                wp_api_key = col
            core_translation[wp_api_key] = col
        # if Registrar.DEBUG_API: Registrar.register_message("core_translation: %s" % pformat(core_translation))
        parser_data.update(**cls.translate_keys(api_data, core_translation))

        meta_translation = OrderedDict()
        if 'meta' in api_data:
            meta_data = api_data['meta']
            for col, col_data in ColDataWoo.get_wpapi_meta_cols().items():
                try:
                    wp_api_key = col_data['wp-api']['key']
                except:
                    wp_api_key = col
                meta_translation[wp_api_key] = col
            parser_data.update(
                **cls.translate_keys(meta_data, meta_translation))
        if 'dimensions' in api_data:
            parser_data.update(
                **cls.get_api_dimension_data(api_data['dimensions']))
        if 'in_stock' in api_data:
            parser_data.update(
                **cls.get_api_stock_status_data(api_data['in_stock']))
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
            Registrar.register_message(
                "parser_data: {}".format(pformat(parser_data)))
        return parser_data

    def get_kwargs(self, all_data, container, **kwargs):
        if 'parent' not in kwargs:
            kwargs['parent'] = self.rootData
        return kwargs

    def get_new_obj_container(self, all_data, **kwargs):
        if self.DEBUG_MRO:
            self.register_message(' ')
        container = super(CsvParseWooApi, self).get_new_obj_container(
            all_data, **kwargs)
        api_data = kwargs.get('api_data', {})
        if self.DEBUG_API:
            self.register_message('api_data: %s' % str(api_data))
            self.register_message('api_data[type]: %s' %
                                  repr(api_data.get('type')))
        if 'type' in api_data:
            api_type = api_data['type']
            if self.DEBUG_API:
                self.register_message('api type: %s' % str(api_type))
            try:
                container = self.containers[api_type]
            except IndexError:
                exc = UserWarning("Unknown API product type: %s" % api_type)
                source = api_data.get('SKU')
                self.register_error(exc, source)
        if self.DEBUG_API:
            self.register_message("container: {}".format(container.__name__))
        return container

    def analyse_wp_api_obj(self, api_data):
        """
        Analyse an object from the wp api.
        """
        if self.DEBUG_API:
            self.register_message("API DATA CATEGORIES: %s" %
                                  repr(api_data.get('categories')))
        if not api_data.get('categories'):
            if self.DEBUG_API:
                self.register_message(
                    "NO CATEGORIES FOUND IN API DATA: %s" % repr(api_data))
        kwargs = {
            'api_data': api_data
        }
        object_data = self.new_object(rowcount=self.rowcount, **kwargs)
        if self.DEBUG_API:
            self.register_message("CONSTRUCTED: %s" % object_data.identifier)
        self.process_object(object_data)
        if self.DEBUG_API:
            self.register_message("PROCESSED: %s" % object_data.identifier)
        self.register_object(object_data)
        if self.DEBUG_API:
            self.register_message("REGISTERED: %s" % object_data.identifier)
        # self.register_message("mro: {}".format(container.mro()))
        self.rowcount += 1

        if 'categories' in api_data:
            for category in api_data['categories']:
                self.process_api_category({'title': category}, object_data)
                # self.rowcount += 1

        if 'variations' in api_data:
            for variation in api_data['variations']:
                self.analyse_wp_api_variation(object_data, variation)
                # self.rowcount += 1

        if 'attributes' in api_data:
            self.process_api_attributes(
                object_data, api_data['attributes'], False)

    def analyse_wp_api_variation(self, object_data, variation_api_data):
        """
        Analyse a variation of an object from the wp_api.
        """
        if self.DEBUG_API:
            self.register_message("parent_data: %s" %
                                  pformat(object_data.items()))
            self.register_message("variation_api_data: %s" %
                                  pformat(variation_api_data))
        default_var_data = dict(
            type='variation',
            title='Variation #%s of %s' % (
                variation_api_data.get('id'), object_data.title),
            description=object_data.get('descsum'),
            parent_id=object_data.get('ID')
        )
        default_var_data.update(**variation_api_data)
        if self.DEBUG_API:
            self.register_message("default_var_data: %s" %
                                  pformat(default_var_data))

        kwargs = {
            'api_data': default_var_data,
            'parent': object_data
        }

        variation_data = self.new_object(rowcount=self.rowcount, **kwargs)

        if self.DEBUG_API:
            self.register_message(
                "CONSTRUCTED: %s" %
                variation_data.identifier)
        self.process_object(variation_data)
        if self.DEBUG_API:
            self.register_message("PROCESSED: %s" % variation_data.identifier)
        self.register_object(variation_data)
        # self.register_variation(object_data, variation_data)
        if self.DEBUG_API:
            self.register_message("REGISTERED: %s" % variation_data.identifier)

        self.rowcount += 1

        if 'attributes' in variation_api_data:
            self.process_api_attributes(
                object_data, variation_api_data['attributes'], True)
