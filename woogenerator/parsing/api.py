"""
Introduce woo api structure to shop classes.
"""
from __future__ import absolute_import, print_function

import io
import json
from collections import OrderedDict
from pprint import pformat

from ..coldata import ColDataWoo
from ..utils import DescriptorUtils, Registrar, SanitationUtils, SeqUtils
from .abstract import CsvParseBase
from .gen import ImportGenItem, ImportGenObject, ImportGenTaxo
from .shop import (CsvParseShopMixin, ImportShopCategoryMixin, ImportShopMixin,
                   ImportShopProductMixin, ImportShopProductSimpleMixin,
                   ImportShopProductVariableMixin,
                   ImportShopProductVariationMixin)
from .tree import CsvParseTreeMixin
from .woo import CsvParseWooMixin, ImportWooMixin, WooCatList, WooProdList


class ApiProdListMixin(object):
    def export_api_data(self, file_path, encoding='utf-8'):
        """
        Export the items in the object list to a json file in the given file path.
        """

        assert file_path, "needs a filepath"
        assert self.objects, "meeds items"
        with open(file_path, 'wb') as out_file:
            data = []
            for item in self.objects:
                try:
                    data.append(dict(item['api_data']))
                except KeyError:
                    raise UserWarning("could not get api_data from item")
            data = json.dumps(data)
            data = data.encode(encoding)
            print(data, file=out_file)
        self.register_message("WROTE FILE: %s" % file_path)

class WooApiProdList(WooProdList, ApiProdListMixin):
    pass

class WooApiCatList(WooCatList, ApiProdListMixin):
    pass

class ImportApiObjectMixin(object):

    def process_meta(self):
        # API Objects don't process meta
        pass

    @property
    def index(self):
        return self.get(self.api_id_key)

    @property
    def identifier(self):
        # identifier = super(ImportWooApiObject, self).identifier
        return "|".join([
            'r:%s' % str(self.rowcount),
            'a:%s' % str(self.get(self.api_id_key)),
            self.codesum,
            self.title,
        ])

class ImportWooApiObject(ImportGenObject, ImportShopMixin, ImportWooMixin, ImportApiObjectMixin):

    category_indexer = CsvParseWooMixin.get_title
    process_meta = ImportApiObjectMixin.process_meta
    index = ImportApiObjectMixin.index
    identifier = ImportApiObjectMixin.identifier
    api_id_key = ImportWooMixin.wpid_key
    api_id = DescriptorUtils.safe_key_property(api_id_key)
    verify_meta_keys = SeqUtils.combine_lists(
        ImportGenObject.verify_meta_keys,
        ImportWooMixin.verify_meta_keys
    )

    def __init__(self, *args, **kwargs):
        if self.DEBUG_MRO:
            self.register_message('ImportWooApiObject')
        ImportGenObject.__init__(self, *args, **kwargs)
        ImportShopMixin.__init__(self, *args, **kwargs)
        ImportWooMixin.__init__(self, *args, **kwargs)


    # def verify_meta(self):
    #     # self.descsum = self.description
    #     assert self.descsum_key in self, "descsum should be set in %s. data: %s " % (
    #         self, self.items())
    #     # self.namesum = self.title
    #     assert self.namesum_key in self, "namesum should be set in %s. data: %s " % (
    #         self, self.items())
    #     # if self.is_category:
    #     #     self.codesum = ''
    #     assert self.codesum_key in self, "codesum should be set in %s. data: %s " % (
    #         self, self.items())

class ImportWooApiItem(ImportWooApiObject, ImportGenItem):
    verify_meta_keys = SeqUtils.combine_lists(
        ImportWooApiObject.verify_meta_keys,
        ImportGenItem.verify_meta_keys
    )
    is_item = ImportGenItem.is_item

class ImportWooApiProduct(ImportWooApiItem, ImportShopProductMixin):
    is_product = ImportShopProductMixin.is_product
    container = WooApiProdList

    verify_meta_keys = SeqUtils.subtrace_two_lists(
        ImportWooApiObject.verify_meta_keys,
        ['slug']
    )

    def __init__(self, *args, **kwargs):
        if self.DEBUG_MRO:
            self.register_message('ImportWooApiProduct')
        if self.product_type:
            args[0]['prod_type'] = self.product_type
        ImportWooApiObject.__init__(self, *args, **kwargs)
        ImportShopProductMixin.__init__(self, *args, **kwargs)


class ImportWooApiProductSimple(ImportWooApiProduct, ImportShopProductSimpleMixin):
    product_type = ImportShopProductSimpleMixin.product_type


class ImportWooApiProductVariable(
        ImportWooApiProduct, ImportShopProductVariableMixin):
    is_variable = ImportShopProductVariableMixin.is_variable
    product_type = ImportShopProductVariableMixin.product_type

    def __init__(self, *args, **kwargs):
        if self.DEBUG_MRO:
            self.register_message('ImportWooApiProductVariable')
        ImportWooApiProduct.__init__(self, *args, **kwargs)
        ImportShopProductVariableMixin.__init__(self, *args, **kwargs)


class ImportWooApiProductVariation(
        ImportWooApiProduct, ImportShopProductVariationMixin):
    is_variation = ImportShopProductVariationMixin.is_variation
    product_type = ImportShopProductVariationMixin.product_type

class ImportWooApiTaxo(ImportWooApiObject, ImportGenTaxo):
    is_taxo = ImportGenTaxo.is_taxo

    verify_meta_keys = SeqUtils.combine_lists(
        ImportWooApiObject.verify_meta_keys,
        ImportGenTaxo.verify_meta_keys
    )


class ImportWooApiCategory(ImportWooApiTaxo, ImportShopCategoryMixin):
    is_category = ImportShopCategoryMixin.is_category
    identifier = ImportWooApiObject.identifier
    container = WooApiCatList

    def __init__(self, *args, **kwargs):
        if self.DEBUG_MRO:
            self.register_message('ImportWooApiCategory')
        ImportWooApiObject.__init__(self, *args, **kwargs)
        ImportShopCategoryMixin.__init__(self, *args, **kwargs)

    @property
    def cat_name(self):
        return self.title

    @property
    def index(self):
        return self.title

class ApiParseMixin(object):
    def analyse_stream(self, byte_file_obj, **kwargs):
        limit, encoding, stream_name = \
            (kwargs.get('limit'), kwargs.get('encoding'), kwargs.get('stream_name'))

        if encoding is None:
            encoding = "utf8"

        if stream_name is None:
            if hasattr(byte_file_obj, 'name'):
                stream_name = byte_file_obj.name
            else:
                stream_name = 'stream'

        if self.DEBUG_PARSER:
            self.register_message(
                "Analysing stream: {}, encoding: {}, type: {}".format(
                    stream_name, encoding, type(byte_file_obj))
            )

        # I can't imagine this having any problems
        byte_sample = SanitationUtils.coerce_bytes(byte_file_obj.read(1000))
        byte_file_obj.seek(0)
        if self.DEBUG_PARSER:
            self.register_message("Byte sample: %s" % repr(byte_sample))

        decoded = json.loads(byte_file_obj.read(), encoding=encoding)
        if not decoded:
            return
        if isinstance(decoded, list):
            for decoded_obj in decoded[:limit]:
                self.analyse_api_obj(decoded_obj)

class ApiParseWoo(
    CsvParseBase, CsvParseTreeMixin, CsvParseShopMixin, CsvParseWooMixin, ApiParseMixin
):
    object_container = ImportWooApiObject
    product_container = ImportWooApiProduct
    simple_container = ImportWooApiProductSimple
    variable_container = ImportWooApiProductVariable
    variation_container = ImportWooApiProductVariation
    category_container = ImportWooApiCategory
    category_indexer = CsvParseBase.get_object_rowcount
    item_indexer = CsvParseBase.get_object_rowcount
    taxo_indexer = CsvParseBase.get_object_rowcount
    product_indexer = CsvParseShopMixin.product_indexer
    variation_indexer = CsvParseWooMixin.get_title
    coldata_class = ColDataWoo
    col_data_target = 'wp-api'
    analyse_stream = ApiParseMixin.analyse_stream

    def __init__(self, *args, **kwargs):
        if self.DEBUG_MRO:
            self.register_message('ApiParseWoo')
        super(ApiParseWoo, self).__init__(*args, **kwargs)
        # self.category_indexer = CsvParseGenMixin.get_name_sum
        # if hasattr(CsvParseWooMixin, '__init__'):
        #     CsvParseGenMixin.__init__(self, *args, **kwargs)

    def clear_transients(self):
        CsvParseBase.clear_transients(self)
        CsvParseTreeMixin.clear_transients(self)
        CsvParseShopMixin.clear_transients(self)
        CsvParseWooMixin.clear_transients(self)

        # super(ApiParseWoo, self).clear_transients()
        # CsvParseShopMixin.clear_transients(self)

    def register_object(self, object_data):
        # CsvParseGenTree.register_object(self, object_data)
        CsvParseBase.register_object(self, object_data)
        CsvParseTreeMixin.register_object(self, object_data)
        CsvParseShopMixin.register_object(self, object_data)
        # CsvParseWooMixin.register_object(self, object_data)

    # def process_object(self, object_data):
        # super(ApiParseWoo, self).process_object(object_data)
        # todo: this

    # def register_object(self, object_data):
    #     if self.DEBUG_MRO:
    #         self.register_message(' ')
    #     if self.DEBUG_API:
    #         self.register_message("registering object_data: %s" % str(object_data))
    #     super(ApiParseWoo, self).register_object(object_data)

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

    def process_api_category(self, category_api_data, object_data=None):
        """
        Create category if not exist or find if exist, then assign object_data to category
        Has to emulate CsvParseBase.new_object()
        """
        if self.DEBUG_API:
            category_title = category_api_data.get('title', '')
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
                                  repr(category_api_data))
        core_translation = OrderedDict()
        for col, col_data in self.coldata_class.get_wpapi_core_cols().items():
            try:
                wp_api_key = col_data[self.col_data_target]['key']
            except BaseException:
                wp_api_key = col
            core_translation[wp_api_key] = col
        category_search_data = {}
        category_search_data.update(
            **self.translate_keys(category_api_data, core_translation))
        category_search_data = dict([(key, SanitationUtils.html_unescape_recursive(value))
                                     for key, value in category_search_data.items()])

        if 'itemsum' in category_search_data:
            category_search_data['taxosum'] = category_search_data['itemsum']
            del category_search_data['itemsum']

        if self.DEBUG_API:
            self.register_message("SEARCHING FOR CATEGORY: %s" %
                                  repr(category_search_data))

        cat_data = self.find_category(category_search_data)
        if not cat_data:
            if self.DEBUG_API:
                self.register_message("CATEGORY NOT FOUND")

            category_api_data['type'] = 'category'
            if not 'description' in category_api_data:
                category_api_data['description'] = ''
            if not 'slug' in category_api_data:
                category_api_data['slug'] = ''

            kwargs = OrderedDict()
            kwargs['api_data'] = category_api_data

            parent_category_data = None
            if 'parent' in category_api_data:
                parent_category_search_data = {}
                parent_category_search_data[
                    self.category_container.wpid_key] = category_api_data['parent']
                parent_category_data = self.find_category(
                    parent_category_search_data)
            if parent_category_data:
                kwargs['parent'] = parent_category_data
            else:
                kwargs['parent'] = self.root_data

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

        # TODO: merge with ApiParseXero.get_parser_data in ApiParseMixin

        api_data = kwargs.get('api_data', {})
        if cls.DEBUG_API:
            cls.register_message("api_data before unsecape: \n%s" % pformat(api_data))
        api_data = dict([(key, SanitationUtils.html_unescape_recursive(value))
                         for key, value in api_data.items()])
        if cls.DEBUG_API:
            cls.register_message("api_data after unescape: \n%s" % pformat(api_data))

        parser_data = OrderedDict()
        core_translation = OrderedDict()
        for col, col_data in cls.coldata_class.get_wpapi_core_cols().items():
            try:
                translated_key = col_data[cls.col_data_target]['key']
            except KeyError:
                translated_key = col
            core_translation[translated_key] = col
        parser_data.update(**cls.translate_keys(api_data, core_translation))

        meta_translation = OrderedDict()
        if 'meta' in api_data:
            meta_data = api_data['meta']
            for col, col_data in cls.coldata_class.get_wpapi_meta_cols().items():
                try:
                    translated_key = col_data[cls.col_data_target]['key']
                except KeyError:
                    translated_key = col
                meta_translation[translated_key] = col
            parser_data.update(
                **cls.translate_keys(meta_data, meta_translation))
        if 'dimensions' in api_data:
            parser_data.update(
                **cls.get_api_dimension_data(api_data['dimensions']))
        if 'in_stock' in api_data:
            parser_data.update(
                **cls.get_api_stock_status_data(api_data['in_stock']))
        # if 'description' in api_data:
        #     parser_data[cls.object_container.description_key] = api_data['description']
        # Stupid hack because 'name' is 'title' in products, but 'name' in
        # categories
        if 'title' in api_data:
            parser_data[cls.object_container.titleKey] = api_data['title']

        assert \
            cls.object_container.description_key in parser_data, \
            "parser_data should have description: %s\n original: %s\ntranslations: %s, %s" \
            % (parser_data, api_data, core_translation, meta_translation)
        parser_data[cls.object_container.descsum_key] = parser_data[
            cls.object_container.description_key]
        assert \
            cls.object_container.titleKey in parser_data, \
            "parser_data should have title: %s\n original: %s\ntranslations: %s, %s" \
            % (parser_data, api_data, core_translation, meta_translation)
        if api_data['type'] == 'category':
            parser_data[cls.category_container.namesum_key] = parser_data[
                cls.object_container.titleKey]
            assert \
                cls.object_container.slugKey in parser_data, \
                "parser_data should have slug: %s\n original: %s\ntranslations: %s, %s" \
                % (parser_data, api_data, core_translation, meta_translation)
            parser_data[cls.object_container.codesum_key] = parser_data[
                cls.object_container.slugKey]
        else:
            parser_data[cls.object_container.namesum_key] = parser_data[
                cls.object_container.titleKey]
        assert \
            cls.object_container.codesum_key in parser_data, \
            "parser_data should have codesum: %s\n original: %s\ntranslations: %s, %s" \
            % (parser_data, api_data, core_translation, meta_translation)
        # assert \
        #     cls.object_container.namesum_key in parser_data, \
        #     "parser_data should have namesum: %s\n original: %s\ntranslations: %s, %s" \
        #     % (parser_data, api_data, core_translation, meta_translation)

        # title = parser_data.get(cls.object_container.titleKey, '')
        # if not title and 'title' in api_data:
        #     title = api_data['title']
        # if not title and 'name' in api_data:
        #     title = api_data['name']
        # parser_data[cls.object_container.titleKey] = title
        # parser_data[cls.object_container.namesum_key] = title
        #
        # slug = parser_data.get(cls.object_container.slugKey,'')
        # if not slug and 'slug' in api_data:
        #     slug = api_data['slug']
        # parser_data[cls.object_container.slugKey] = slug
        #
        description = parser_data.get(cls.object_container.description_key, '')
        if not description and 'description' in api_data:
            description = api_data['description']
        parser_data[cls.object_container.description_key] = description
        parser_data[cls.object_container.descsum_key] = description

        parser_data['api_data'] = api_data

        if Registrar.DEBUG_API:
            Registrar.register_message(
                "parser_data: {}".format(pformat(parser_data)))
        return parser_data

    def get_kwargs(self, all_data, container, **kwargs):
        if 'parent' not in kwargs:
            kwargs['parent'] = self.root_data
        return kwargs

    def get_new_obj_container(self, all_data, **kwargs):
        if self.DEBUG_MRO:
            self.register_message(' ')
        container = super(ApiParseWoo, self).get_new_obj_container(
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

    def analyse_api_obj(self, api_data):
        """
        Analyse an object from the api.
        """

        # TODO: merge with ApiParseXero.analyse_api_obj in ApiParseMixin

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
