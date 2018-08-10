# -*- coding: utf-8 -*-
from __future__ import absolute_import

from collections import OrderedDict

from .core import SyncClientWC, SyncClientWCLegacy
from .xero import SyncClientXero
from ..coldata import ColDataProductMeridian, ColDataWcProdCategory, ColDataProductVariationMeridian

class ProdSyncClientMixin(object):
    endpoint_singular = 'product'
    coldata_class = ColDataProductMeridian

    def get_first_variable_product(self):
        endpoint = "%s/%s" % (self.endpoint_plural, "?type=variable")
        for page in self.get_page_generator(endpoint):
            for product in page:
                return product
        raise UserWarning("no variable products")

class ProdSyncClientWC(SyncClientWC, ProdSyncClientMixin):
    endpoint_singular = ProdSyncClientMixin.endpoint_singular
    coldata_class = ProdSyncClientMixin.coldata_class

class ProdSyncClientWCLegacy(SyncClientWCLegacy, ProdSyncClientMixin):
    endpoint_singular = ProdSyncClientMixin.endpoint_singular
    coldata_class = ProdSyncClientMixin.coldata_class

class CatSyncClientMixin(object):
    endpoint_singular = 'product_category'
    endpoint_plural = 'products/categories'
    coldata_class = ColDataWcProdCategory
    primary_key_handle = 'term_id'

    def analyse_remote_categories(self, parser, **kwargs):
        categories = []
        for page in self.get_page_generator():
            for page_item in page:
                categories.append(page_item)
        parser.process_api_categories_raw(categories)
        if self.DEBUG_API:
            self.register_message("Analysed categories:")
            self.register_message(parser.to_str_tree())

class CatSyncClientWC(SyncClientWC, CatSyncClientMixin):
    endpoint_singular = CatSyncClientMixin.endpoint_singular
    endpoint_plural = CatSyncClientMixin.endpoint_plural
    coldata_class = CatSyncClientMixin.coldata_class
    primary_key_handle = CatSyncClientMixin.primary_key_handle

class CatSyncClientWCLegacy(SyncClientWCLegacy, CatSyncClientMixin):
    endpoint_singular = CatSyncClientMixin.endpoint_singular
    endpoint_plural = CatSyncClientMixin.endpoint_plural
    coldata_class = CatSyncClientMixin.coldata_class
    primary_key_handle = CatSyncClientMixin.primary_key_handle

class VarSyncClientMixin(object):
    coldata_class = ColDataProductVariationMeridian
    @property
    def endpoint_singular(self):
        raise UserWarning("concept of endpoint singular does not apply to var sync client")

    def get_variations(self, parent_pkey):
        try:
            parent_pkey = int(parent_pkey)
        except ValueError:
            raise UserWarning("Can't convert parent_pkey %s to int" % parent_pkey)
        endpoint = "%ss/%d/variations" % (
            ProdSyncClientMixin.endpoint_singular,
            parent_pkey
        )
        return self.get_page_generator(endpoint)

    def get_first_variation(self, parent_id):
        return self.get_variations(parent_id).next()[0]

    def get_single_endpoint(self, parent_pkey, **kwargs):
        assert 'var_pkey' in kwargs, "must specify variation pkey"
        var_pkey = kwargs['var_pkey']
        try:
            var_pkey = int(var_pkey)
        except ValueError:
            raise UserWarning("Can't convert var_pkey %s to int" % var_pkey)
        try:
            parent_pkey = int(parent_pkey)
        except ValueError:
            raise UserWarning("Can't convert parent_pkey %s to int" % parent_pkey)

        return "%ss/%d/variations/%d" % (
            ProdSyncClientMixin.endpoint_singular,
            parent_pkey,
            var_pkey
        )


class VarSyncClientWC(SyncClientWC, VarSyncClientMixin):
    coldata_class = VarSyncClientMixin.coldata_class
    endpoint_singular = VarSyncClientMixin.endpoint_singular
    get_single_endpoint = VarSyncClientMixin.get_single_endpoint


class VarSyncClientWCLegacy(SyncClientWCLegacy, VarSyncClientMixin):
    coldata_class = VarSyncClientMixin.coldata_class
    endpoint_singular = VarSyncClientMixin.endpoint_singular
    get_single_endpoint = VarSyncClientMixin.get_single_endpoint

class ProdSyncClientXero(SyncClientXero):
    endpoint_singular = 'item'
