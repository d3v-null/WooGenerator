from __future__ import absolute_import

import time
from collections import OrderedDict
import json
from pprint import pformat

from ..coldata import ColDataXero
from ..utils import SeqUtils, DescriptorUtils, SanitationUtils
from .abstract import CsvParseBase
from .tree import CsvParseTreeMixin
from .gen import CsvParseGenTree, ImportGenItem, ImportGenObject, ImportGenTaxo
from .myo import CsvParseMyo
from .shop import (
    ImportShopMixin, ImportShopProductMixin, ImportShopProductSimpleMixin, ShopProdList, CsvParseShopMixin
)
from .api import ImportApiObjectMixin, ApiProdListMixin, ApiParseMixin

class XeroApiProdList(ShopProdList, ApiProdListMixin):
    @property
    def report_cols(self):
        return CsvParseXero.coldata_class.get_product_cols()

class ImportXeroMixin(object):
    container = XeroApiProdList
    description_key = 'Xero Description'
    description = DescriptorUtils.safe_key_property(description_key)

class ImportXeroObject(ImportGenObject, ImportShopMixin, ImportXeroMixin):
    description_key = ImportXeroMixin.description_key
    description = ImportXeroMixin.description
    container = ImportXeroMixin.container
    api_id_key = 'item_id'
    api_id = DescriptorUtils.safe_key_property(api_id_key)

    def __init__(self, *args, **kwargs):
        ImportGenObject.__init__(self, *args, **kwargs)
        ImportShopMixin.__init__(self, *args, **kwargs)

class ImportXeroItem(ImportXeroObject, ImportGenItem):
    container = ImportXeroMixin.container
    is_item = ImportGenItem.is_item
    verify_meta_keys = SeqUtils.combine_lists(
        ImportXeroObject.verify_meta_keys,
        ImportGenItem.verify_meta_keys
    )

class ImportXeroProduct(ImportXeroItem, ImportShopProductMixin):
    is_product = ImportShopProductMixin.is_product
    container = ImportXeroMixin.container
    name_delimeter = ' - '

    def __init__(self, *args, **kwargs):
        ImportXeroItem.__init__(self, *args, **kwargs)
        ImportShopProductMixin.__init__(self, *args, **kwargs)

class ImportXeroApiObject(ImportXeroObject, ImportApiObjectMixin):
    process_meta = ImportApiObjectMixin.process_meta
    container = ImportXeroMixin.container
    is_item = ImportGenItem.is_item

class ImportXeroApiItem(ImportXeroApiObject, ImportGenItem):
    container = ImportXeroMixin.container

class ImportXeroApiProduct(ImportXeroApiItem, ImportShopProductMixin):
    is_product = ImportShopProductMixin.is_product
    container = ImportXeroMixin.container
    name_delimeter = ' - '

    verify_meta_keys = [
        ImportXeroItem.codesum_key,
        # ImportXeroItem.namesum_key
    ]

class ParseXeroMixin(object):
    """
    Provide Mixin for parsing Xero data.
    """

    object_container = ImportXeroObject
    item_container = ImportXeroItem
    product_container = ImportXeroProduct
    coldata_class = ColDataXero
    default_schema = "XERO"

    @classmethod
    def get_xero_id(cls, item_data):
        assert isinstance(item_data, ImportXeroMixin)
        return item_data.api_id


class CsvParseXero(CsvParseGenTree, CsvParseShopMixin, ParseXeroMixin):
    """
    Parse Xero data from CSV Files
    """

    object_container = ParseXeroMixin.object_container
    item_container = ParseXeroMixin.item_container
    product_container = ParseXeroMixin.product_container
    coldata_class = ParseXeroMixin.coldata_class

    @property
    def containers(self):
        return {
            'Y': self.product_container
        }

    # extra_taxo_subs = CsvParseMyo.extra_taxo_subs
    # extra_item_subs = CsvParseMyo.extra_item_subs

    def __init__(self, cols=None, defaults=None, **kwargs):
        if defaults is None:
            defaults = {}
        if cols is None:
            cols = {}
        # kwargs['taxo_subs'] = SeqUtils.combine_ordered_dicts(
        #     taxo_subs, CsvParseXero.extra_taxo_subs
        # )
        # kwargs['item_subs'] = SeqUtils.combine_ordered_dicts(
        #     item_subs, CsvParseXero.extra_item_subs
        # )
        if not kwargs.get('schema'):
            kwargs['schema'] = self.default_schema

        CsvParseGenTree.__init__(self, cols, defaults, **kwargs)

    def clear_transients(self):
        CsvParseGenTree.clear_transients(self)
        CsvParseShopMixin.clear_transients(self)

    def register_object(self, object_data):
        CsvParseGenTree.register_object(self, object_data)
        CsvParseShopMixin.register_object(self, object_data)

class ApiParseXero(
    CsvParseBase, CsvParseTreeMixin, CsvParseShopMixin, ParseXeroMixin, ApiParseMixin
):
    """
    Provide Xero API data parsing functionality
    """
    object_container = ImportXeroApiObject
    item_container = ImportXeroApiItem
    product_container = ImportXeroApiProduct
    coldata_class = ParseXeroMixin.coldata_class
    col_data_target = 'xero-api'
    item_indexer = ParseXeroMixin.get_xero_id
    analyse_stream = ApiParseMixin.analyse_stream

    def __init__(self, cols=None, defaults=None, **kwargs):
        if defaults is None:
            defaults = {}
        if cols is None:
            cols = {}
        if not kwargs.get('schema'):
            kwargs['schema'] == self.default_schema

        super(ApiParseXero, self).__init__(cols, defaults, **kwargs)

    def clear_transients(self):
        CsvParseBase.clear_transients(self)
        CsvParseTreeMixin.clear_transients(self)
        CsvParseShopMixin.clear_transients(self)

    def register_object(self, object_data):
        CsvParseBase.register_object(self, object_data)
        CsvParseTreeMixin.register_object(self, object_data)
        CsvParseShopMixin.register_object(self, object_data)

    @classmethod
    def get_api_accounting_details_data(cls, field, details):
        response = {}
        if field == 'SalesDetails' and 'UnitPrice' in details:
            unit_price_sales_key = cls.coldata_class.unit_price_sales_field(
                cls.col_data_target
            )
            response[unit_price_sales_key] = details['UnitPrice']
        return response

    @classmethod
    def get_stock_status_data(cls, quantity, inventory):
        response = {}
        if inventory:
            precision = 100
            if int(float(quantity) * precision) / precision == 0:
                response['stock_status'] = 'outofstock'
            else:
                response['stock_status'] = 'instock'
        return response

    @classmethod
    def get_parser_data(cls, **kwargs):
        """
        Gets data ready for the parser, in this case from api_data
        """

        parser_data = OrderedDict()
        api_data = kwargs.get('api_data', {})
        if cls.DEBUG_API:
            cls.register_message("api_data before unsecape: \n%s" % pformat(api_data))
        api_data = dict([(key, SanitationUtils.html_unescape_recursive(value))
                         for key, value in api_data.items()])
        if cls.DEBUG_API:
            cls.register_message("api_data after unescape: \n%s" % pformat(api_data))

        translation = OrderedDict()
        for col, col_data in cls.coldata_class.data.items():
            try:
                translated_key = col_data[cls.col_data_target]['key']
                translation[translated_key] = col
            except (KeyError, TypeError):
                pass

        if cls.DEBUG_API:
            cls.register_message("translation: %s" % translation)
        translated_api_data = cls.translate_keys(api_data, translation)
        if cls.DEBUG_API:
            cls.register_message("translated_api_data: %s" % translated_api_data)
        parser_data.update(**translated_api_data)

        if 'SalesDetails' in api_data:
            parser_data.update(
                **cls.get_api_accounting_details_data(
                    'SalesDetails',
                    api_data['SalesDetails']
                )
            )

        if 'PurchaseDetails' in api_data:
            parser_data.update(
                **cls.get_api_accounting_details_data(
                    'PurchaseDetails',
                    api_data['PurchaseDetails']
                )
            )

        if 'QuantityOnHand' in api_data and 'IsTrackedAsInventory':
            parser_data.update(
                **cls.get_stock_status_data(
                    api_data['QuantityOnHand'],
                    api_data['IsTrackedAsInventory']
                )
            )

        if cls.DEBUG_API:
            cls.register_message("returning parser_data: %s" % parser_data)

        parser_data['api_data'] = api_data

        return parser_data

    def get_kwargs(self, all_data, container, **kwargs):
        if 'parent' not in kwargs:
            kwargs['parent'] = self.root_data
        return kwargs

    def get_new_obj_container(self, all_data, **kwargs):
        # container = super(ApiParseXero, self).get_new_obj_container(
        #     all_data, **kwargs)
        # api_data = kwargs.get('api_data', {})
        # if self.DEBUG_API:
        #     self.register_message('api_data: %s' % str(api_data))
        return self.product_container

    def analyse_xero_api_obj(self, api_data):
        """
        Analyse an object from the wp api.
        """
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
