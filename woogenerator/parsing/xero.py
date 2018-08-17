from __future__ import absolute_import

import json
import time
from collections import OrderedDict
from pprint import pformat

from ..coldata import ColDataProductMeridian
from ..utils import DescriptorUtils, SanitationUtils, SeqUtils
from .abstract import CsvParseBase
from .api import ApiListMixin, ApiParseMixin, ImportApiObjectMixin
from .gen import CsvParseGenTree, ImportGenItem, ImportGenObject, ImportGenTaxo
from .myo import CsvParseMyo
from .shop import (CsvParseShopMixin, ImportShopMixin, ImportShopProductMixin,
                   ImportShopProductSimpleMixin, ShopMixin, ShopProdList)
from .tree import CsvParseTreeMixin, ImportTreeRoot


class ApiXeroMixin(object):
    coldata_target = 'xero-api'

class ImportXeroMixin(object):
    description_key = 'Xero Description'
    description = DescriptorUtils.safe_key_property(description_key)
    api_id_key = 'item_id'
    api_id = DescriptorUtils.safe_key_property(api_id_key)

    @classmethod
    def get_object_id(cls, object_data):
        return object_data.get(cls.api_id_key)

    child_indexer = get_object_id


class ImportXeroRoot(ImportTreeRoot, ImportXeroMixin):
    child_indexer = ImportXeroMixin.child_indexer


class ImportXeroObject(ImportGenObject, ImportShopMixin, ImportXeroMixin, ApiXeroMixin):
    description_key = ImportXeroMixin.description_key
    description = ImportXeroMixin.description
    coldata_target = ApiXeroMixin.coldata_target
    child_indexer = ImportXeroMixin.child_indexer

    def __init__(self, *args, **kwargs):
        for base_class in [ImportGenObject, ImportShopMixin]:
            if hasattr(base_class, '__init__'):
                base_class.__init__(self, *args, **kwargs)

    def to_dict(self):
        response = {}
        for base_class in ImportXeroObject.__bases__:
            if hasattr(base_class, 'to_dict'):
                response.update(base_class.to_dict(self))
        return response

class ImportXeroItem(ImportXeroObject, ImportGenItem):
    is_item = ImportGenItem.is_item
    verify_meta_keys = SeqUtils.combine_lists(
        ImportXeroObject.verify_meta_keys,
        ImportGenItem.verify_meta_keys
    )

class ImportXeroProduct(ImportXeroItem, ImportShopProductMixin):
    is_product = ImportShopProductMixin.is_product
    name_delimeter = ' - '

    def __init__(self, *args, **kwargs):
        for base_class in [ImportXeroItem, ImportShopProductMixin]:
            if hasattr(base_class, '__init__'):
                base_class.__init__(self, *args, **kwargs)

    def process_meta(self):
        # import pudb; pudb.set_trace()
        for base_class in ImportXeroProduct.__bases__:
            if hasattr(base_class, 'process_meta'):
                base_class.process_meta(self)

class ImportXeroApiObject(ImportXeroObject, ImportApiObjectMixin):
    is_item = ImportGenItem.is_item

    def process_meta(self):
        # import pudb; pudb.set_trace()
        for base_class in ImportXeroApiObject.__bases__:
            if hasattr(base_class, 'process_meta'):
                base_class.process_meta(self)

class ImportXeroApiItem(ImportXeroApiObject, ImportGenItem):
    pass

class ImportXeroApiProduct(ImportXeroApiItem, ImportShopProductMixin):
    is_product = ImportShopProductMixin.is_product
    name_delimeter = ' - '

    verify_meta_keys = [
        ImportXeroItem.codesum_key,
        # ImportXeroItem.namesum_key
    ]

class XeroApiProdList(ShopProdList, ApiListMixin, ApiXeroMixin):
    supported_type = ImportXeroApiProduct

    @property
    def report_cols(self):
        return CsvParseXero.coldata_class.get_col_data_native('report')

ImportXeroApiProduct.container = XeroApiProdList

class ParseXeroMixin(object):
    """
    Provide Mixin for parsing Xero data.
    """

    object_container = ImportXeroObject
    item_container = ImportXeroItem
    product_container = ImportXeroProduct
    coldata_class = ShopMixin.coldata_class
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
            cols = []
        extra_cols = [kwargs.get('schema')]
        cols = SeqUtils.combine_lists(cols, extra_cols)

        # kwargs['taxo_subs'] = SeqUtils.combine_ordered_dicts(
        #     taxo_subs, CsvParseXero.extra_taxo_subs
        # )
        # kwargs['item_subs'] = SeqUtils.combine_ordered_dicts(
        #     item_subs, CsvParseXero.extra_item_subs
        # )
        if not kwargs.get('schema'):
            kwargs['schema'] = self.default_schema

        CsvParseGenTree.__init__(self, cols, defaults, **kwargs)

    # def process_object(self, object_data):
    #     super(CsvParseXero, self).process_object(object_data)
    #     import pudb; pudb.set_trace()

    def clear_transients(self):
        CsvParseGenTree.clear_transients(self)
        CsvParseShopMixin.clear_transients(self)

    def register_object(self, object_data):
        CsvParseGenTree.register_object(self, object_data)
        CsvParseShopMixin.register_object(self, object_data)

    def get_new_obj_container(self, all_data, **kwargs):
        container = super(CsvParseXero, self).get_new_obj_container(all_data, **kwargs)

        if issubclass(container, self.item_container) \
                and self.schema in all_data:
            xero_type = all_data[self.schema]
            if xero_type:
                try:
                    container = self.containers[xero_type]
                except KeyError:
                    pass
        return container

class ApiParseXero(
    CsvParseBase, CsvParseTreeMixin, CsvParseShopMixin, ParseXeroMixin, ApiParseMixin
):
    """
    Provide Xero API data parsing functionality
    """
    root_container = ImportXeroRoot
    object_container = ImportXeroApiObject
    item_container = ImportXeroApiItem
    product_container = ImportXeroApiProduct
    coldata_class = ParseXeroMixin.coldata_class
    coldata_target = 'xero-api'
    item_indexer = ParseXeroMixin.get_xero_id
    analyse_stream = ApiParseMixin.analyse_stream
    coldata_gen_target = ApiParseMixin.coldata_gen_target
    get_kwargs = ApiParseMixin.get_kwargs

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

    def get_new_obj_container(self, all_data, **kwargs):
        return self.product_container
