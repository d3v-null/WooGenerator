# -*- coding: utf-8 -*-
from collections import OrderedDict
# import os
# import shutil
# from utils import SanitationUtils, TimeUtils, listUtils, debugUtils, Registrar
# from utils import ProgressCounter
# from csvparse_flat import CSVParse_User, UsrObjList #, ImportUser
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
# from woocommerce import API as WCAPI
# from coldata import ColData_Woo

# class ProdSyncClient_Abstract(SyncClient_Abstract):
#     pass

class ProdSyncClient_WC(SyncClient_WC):
    endpoint_singular = 'product'
    #
    # def __init__(self, *args, **kwargs):
    #     super(ProdSyncClient_WC, self).__init__(*args, **kwargs)

    def uploadChanges(self, pkey, updates=None):
        # print "\n\n\ncalling uploadchanges on %s\n\n\n" % str(pkey)
        if updates == None:
            updates = OrderedDict()
        categories = None
        if 'categories' in updates:
            categories = updates.pop('categories')
        response = None
        if updates:
            response = super(ProdSyncClient_WC, self).uploadChanges(pkey, updates)
        if categories:
            print "\n\n\nWILL CHANGE THESE CATEGORIES: %s\n\n\n" % str(categories)
            # self.setCategories(pkey, categories)
        else:
            print "\n\n\nNO CAT CHANGES IN %s\n\n\n" % str(updates)
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
    #     for category in current_categories:
    #         for
