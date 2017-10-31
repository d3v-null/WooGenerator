# -*- coding: utf-8 -*-
from __future__ import absolute_import

from collections import OrderedDict

from .core import SyncClientWC, SyncClientWCLegacy
from .xero import SyncClientXero

class ProdSyncClientMixin(object):
    endpoint_singular = 'product'

    def analyse_remote_categories(self, parser, **kwargs):
        taxo_api_iterator = self.get_iterator('products/categories')
        categories = []
        for page in taxo_api_iterator:
            if self.page_nesting:
                page = page['product_categories']
            for page_item in page:
                categories.append(page_item)
        parser.process_api_categories(categories)
        if self.DEBUG_API:
            self.register_message("Analysed categories:")
            self.register_message(parser.to_str_tree())

class ProdSyncClientWC(SyncClientWC, ProdSyncClientMixin):
    endpoint_singular = ProdSyncClientMixin.endpoint_singular

class ProdSyncClientWCLegacy(SyncClientWCLegacy, ProdSyncClientMixin):
    endpoint_singular = ProdSyncClientMixin.endpoint_singular

    #
    # def __init__(self, *args, **kwargs):
    #     super(ProdSyncClientWC, self).__init__(*args, **kwargs)



    # def analyse_remote(self, parser, since=None, limit=None):
    # return super(ProdSyncClientWC, self).analyse_remote(parser, since,
    # limit)

    # def upload_changes(self, pkey, updates=None):
    #     # print "\n\n\ncalling uploadchanges on %s\n\n\n" % str(pkey)
    #     if updates is None:
    #         updates = OrderedDict()
    #     if self.DEBUG_API:
    #         categories = updates.get('categories')
    #         if categories:
    #             self.register_message(
    #                 "WILL CHANGE THESE CATEGORIES: %s" % str(categories))
    #         else:
    #             self.register_message("NO CAT CHANGES IN %s" % str(updates))
    #         custom_meta = updates.get(self.meta_set_key)
    #         if custom_meta:
    #             self.register_message("CUSTOM META: %s" % str(custom_meta))
    #         else:
    #             self.register_message("NO CUSTOM META")
    #
    #     response = None
    #     if updates:
    #         response = super(ProdSyncClientWC,
    #                          self).upload_changes(pkey, updates)
    #     return response

    # def setCategories(self, pkey, categories):
    #     """ Sets the item specified by pkey to be a member exclusively of the categories specified """
    #     categories = map(SanitationUtils.similar_comparison, categories)
    #     get_categories_response = self.service.get('products/%s?fields=categories' % pkey)
    #     current_categories = []
    #     if get_categories_response.status_code == 200:
    #         try:
    #             current_categories = get_categories_response.json()\
    #                 .get('product', {})\
    #                 .get('categories', [])
    #         except JSONDecodeError:
    #             raise UserWarning("could not decode get_categories_response: %s" % get_categories_response.text)
    #     print "CURRENT CATEGORIES: %s" % unicode(current_categories)
    #     current_categories = map(SanitationUtils.similar_comparison, current_categories)
    #     new_categories = list(set(categories) - set(current_categories))
        # delete_categories = list(set(current_categories) - set(categories))

        # not efficient but whatever


class CatSyncClientWC(SyncClientWC):
    endpoint_singular = 'product_category'
    endpoint_plural = 'products/categories'

class ProdSyncClientXero(SyncClientXero):
    endpoint_singular = 'item'
