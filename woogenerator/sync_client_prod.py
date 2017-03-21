# -*- coding: utf-8 -*-
from collections import OrderedDict
from woogenerator.sync_client import SyncClientWC


class ProdSyncClient_WC(SyncClientWC):
    endpoint_singular = 'product'
    #
    # def __init__(self, *args, **kwargs):
    #     super(ProdSyncClient_WC, self).__init__(*args, **kwargs)

    def analyseRemoteCategories(self, parser):
        taxoApiIterator = self.ApiIterator(
            self.service, '/products/categories')
        categories = []
        for page in taxoApiIterator:
            if 'product_categories' in page:
                for page_item in page.get('product_categories'):
                    categories.append(page_item)
        parser.processApiCategories(categories)
        if self.DEBUG_API:
            self.registerMessage("Analysed categories:")
            self.registerMessage(parser.toStrTree())

    # def analyse_remote(self, parser, since=None, limit=None):
    # return super(ProdSyncClient_WC, self).analyse_remote(parser, since,
    # limit)

    def upload_changes(self, pkey, updates=None):
        # print "\n\n\ncalling uploadchanges on %s\n\n\n" % str(pkey)
        if updates == None:
            updates = OrderedDict()
        if self.DEBUG_API:
            categories = updates.get('categories')
            if categories:
                self.registerMessage(
                    "WILL CHANGE THESE CATEGORIES: %s" % str(categories))
            else:
                self.registerMessage("NO CAT CHANGES IN %s" % str(updates))
            custom_meta = updates.get('custom_meta')
            if custom_meta:
                self.registerMessage("CUSTOM META: %s" % str(custom_meta))
            else:
                self.registerMessage("NO CUSTOM META")

        response = None
        if updates:
            response = super(ProdSyncClient_WC,
                             self).upload_changes(pkey, updates)
        return response

    # def setCategories(self, pkey, categories):
    #     """ Sets the item specified by pkey to be a member exclusively of the categories specified """
    #     categories = map(SanitationUtils.similarComparison, categories)
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
    #     current_categories = map(SanitationUtils.similarComparison, current_categories)
    #     new_categories = list(set(categories) - set(current_categories))
        # delete_categories = list(set(current_categories) - set(categories))

        # not efficient but whatever


class CatSyncClient_WC(SyncClientWC):
    endpoint_singular = 'product_category'
    endpoint_plural = 'products/categories'
