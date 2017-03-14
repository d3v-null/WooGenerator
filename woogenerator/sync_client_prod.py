# -*- coding: utf-8 -*-
from collections import OrderedDict
# import os
# import shutil
from utils import SanitationUtils
# from utils import ProgressCounter, TimeUtils, listUtils, debugUtils, Registrar
# from parsing.flat import CSVParse_User, UsrObjList #, ImportUser
# from coldata import ColData_User
# from tabulate import tabulate
# from itertools import chain
# from pprint import pprint
# import sys
# from copy import deepcopy
# import unicodecsv
# import pickle
# import dill as pickle
# import requests
# from bisect import insort
# import re
# import time
# import yaml
# import MySQLdb
# import paramiko
# from sshtunnel import SSHTunnelForwarder, check_address
# import io
# import wordpress_xmlrpc
# from wordpress_json import WordpressJsonWrapper, WordpressError
# import pymysql
from simplejson import JSONDecodeError
from sync_client import SyncClient_WC # SyncClient_Abstract,
from pprint import pformat
from utils import Registrar
# from woocommerce import API as WCAPI
# from coldata import ColData_Woo

# class ProdSyncClient_Abstract(SyncClient_Abstract):
#     pass

class ProdSyncClient_WC(SyncClient_WC):
    endpoint_singular = 'product'
    #
    # def __init__(self, *args, **kwargs):
    #     super(ProdSyncClient_WC, self).__init__(*args, **kwargs)

    def analyseRemoteCategories(self, parser):
        taxoApiIterator = self.ApiIterator(self.service, '/products/categories')
        categories = []
        for page in taxoApiIterator:
            if 'product_categories' in page:
                for page_item in page.get('product_categories'):
                    categories.append(page_item)
        parser.processApiCategories(categories)
        if self.DEBUG_API:
            self.registerMessage("Analysed categories:")
            self.registerMessage(parser.toStrTree())

    # def analyseRemote(self, parser, since=None, limit=None):
    #     return super(ProdSyncClient_WC, self).analyseRemote(parser, since, limit)

    def uploadChanges(self, pkey, updates=None):
        # print "\n\n\ncalling uploadchanges on %s\n\n\n" % str(pkey)
        if updates == None:
            updates = OrderedDict()
        if self.DEBUG_API:
            categories = updates.get('categories')
            if categories:
                self.registerMessage( "WILL CHANGE THESE CATEGORIES: %s" % str(categories))
            else:
                self.registerMessage( "NO CAT CHANGES IN %s" % str(updates))
            custom_meta = updates.get('custom_meta')
            if custom_meta:
                self.registerMessage( "CUSTOM META: %s" % str(custom_meta))
            else:
                self.registerMessage( "NO CUSTOM META" )


        response = None
        if updates:
            response = super(ProdSyncClient_WC, self).uploadChanges(pkey, updates)
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

        #not efficient but whatever

class CatSyncClient_WC(SyncClient_WC):
    endpoint_singular = 'product_category'
    endpoint_plural = 'products/categories'
