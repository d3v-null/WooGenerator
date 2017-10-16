from __future__ import absolute_import

import time

from ..coldata import ColDataXero
from ..utils import SeqUtils
from .gen import CsvParseGenTree
from .myo import CsvParseMyo
from .shop import ImportShopProductMixin, ShopProdList


class CsvParseXero(CsvParseGenTree):
    productContainer = ImportShopProductMixin
    coldata_class = ColDataXero

    @property
    def containers(self):
        return {
            'Y': self.productContainer
        }

    # extra_taxo_subs = CsvParseMyo.extra_taxo_subs
    # extra_item_subs = CsvParseMyo.extra_item_subs

    def __init__(
        self, cols=None, defaults=None, schema='XERO', import_name="",
        taxo_subs=None, item_subs=None, taxo_depth=3, item_depth=2,
        meta_width=2
    ):
        if defaults is None:
            defaults = {}
        if cols is None:
            cols = {}
        if taxo_subs is None:
            taxo_subs = {}
        if item_subs is None:
            item_subs = {}
        if not import_name:
            import_name = time.strftime("%Y-%m-%d %H:%M:%S")
        taxo_subs = SeqUtils.combine_ordered_dicts(taxo_subs, CsvParseXero.extra_taxo_subs)
        item_subs = SeqUtils.combine_ordered_dicts(item_subs, CsvParseXero.extra_item_subs)

        super(CsvParseXero, self).__init__(
            cols, defaults, schema, taxo_subs, item_subs, taxo_depth,
            item_depth, meta_width
        )

class XeroProdList(ShopProdList):

    def get_report_cols(self):
        return CsvParseXero.coldata_class.get_product_cols()
