from __future__ import absolute_import

import time

from ..coldata import ColDataXero
from ..utils import SeqUtils, DescriptorUtils
from .gen import CsvParseGenTree, ImportGenItem, ImportGenObject, ImportGenTaxo
from .myo import CsvParseMyo
from .shop import (
    ImportShopMixin, ImportShopProductMixin, ImportShopProductSimpleMixin, ShopProdList, CsvParseShopMixin
)

class ImportXeroMixin(object):
    xeroidKey = 'ID'
    xeroid = DescriptorUtils.safe_key_property(xeroidKey)

class ImportXeroObject(ImportGenObject, ImportShopMixin, ImportXeroMixin):
    pass

class ImportXeroItem(ImportXeroObject, ImportGenItem):
    pass

class ImportXeroProduct(ImportXeroItem, ImportShopProductMixin):
    isProduct = ImportShopProductMixin.isProduct
    name_delimeter = ' - '

class CsvParseXero(CsvParseGenTree, CsvParseShopMixin):
    objectContainer = ImportXeroObject
    itemContainer = ImportXeroItem
    productContainer = ImportXeroProduct
    coldata_class = ColDataXero

    @property
    def containers(self):
        return {
            'Y': self.productContainer
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
            kwargs['schema'] = "XERO"

        super(CsvParseXero, self).__init__(cols, defaults, **kwargs)

    def clear_transients(self):
        CsvParseGenTree.clear_transients(self)
        CsvParseShopMixin.clear_transients(self)

    def register_object(self, object_data):
        CsvParseGenTree.register_object(self, object_data)
        CsvParseShopMixin.register_object(self, object_data)

class XeroProdList(ShopProdList):

    @property
    def report_cols(self):
        return CsvParseXero.coldata_class.get_product_cols()
