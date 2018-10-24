# -*- coding: utf-8 -*-
from __future__ import absolute_import

from ..coldata import (ColDataProductMeridian, ColDataProductVariationMeridian,
                       ColDataWcProdCategory)
from ..utils.core import InvisibleProgressCounter
from .core import SyncClientWC, SyncClientWCLegacy
from .xero import SyncClientXero


class ProdSyncClientMixin(object):
    endpoint_singular = 'product'
    coldata_class = ColDataProductMeridian

    # TODO: merge this with get_first_endpoint_item
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
    page_key = 'product_categories'
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
        raise UserWarning(
            "concept of endpoint singular does not apply to var sync client")

    def get_variations(self, parent_pkey, **kwargs):
        endpoint, _ = self.get_endpoint(parent_pkey=parent_pkey)
        return self.get_page_generator(endpoint, **kwargs)

    def get_first_variation(self, parent_id):
        return self.get_variations(parent_id).next()[0]

    def get_endpoint(self, **kwargs):
        """
        Override SyncClientRest.endpoint to work with Variations
        """
        kwargs.pop('singular', None)  # no concept of singular
        assert 'parent_pkey' in kwargs, "must specify parent pkey"
        parent_pkey = kwargs.pop('parent_pkey')
        try:
            parent_pkey = int(parent_pkey)
        except ValueError:
            raise UserWarning(
                "Can't convert parent_pkey %s to int" % parent_pkey)

        return "%ss/%d/variations" % (ProdSyncClientMixin.endpoint_singular,
                                      parent_pkey), kwargs

    def analyse_remote_variations(self, parser, **kwargs):
        parent_pkey = kwargs.pop('parent_pkey', None)
        # Hijack progress counter
        progress_counter = kwargs.pop('progress_counter', None)
        kwargs['progress_counter'] = InvisibleProgressCounter()

        import pudb; pudb.set_trace()
        # TODO: fix progress prints for variations

        for page in self.get_variations(parent_pkey, **kwargs):
            for page_item in page:
                if progress_counter is not None:
                    progress_counter.increment_count()
                    progress_counter.maybe_print_update()
                parser.process_api_variation_raw(
                    page_item, parent_id=parent_pkey)


class VarSyncClientWC(SyncClientWC, VarSyncClientMixin):
    coldata_class = VarSyncClientMixin.coldata_class
    endpoint_singular = VarSyncClientMixin.endpoint_singular
    get_endpoint = VarSyncClientMixin.get_endpoint


class VarSyncClientWCLegacy(SyncClientWCLegacy, VarSyncClientMixin):
    coldata_class = VarSyncClientMixin.coldata_class
    endpoint_singular = VarSyncClientMixin.endpoint_singular
    get_endpoint = VarSyncClientMixin.get_endpoint

    def __init__(self, *args, **kwargs):
        raise DeprecationWarning(
            "Variations undocumented in WooCommerce Legacy API")


# class AttrSyncClient(SyncClientWC):
#     # TODO: this
#     coldata_class = ColData


class ProdSyncClientXero(SyncClientXero):
    endpoint_singular = 'item'
