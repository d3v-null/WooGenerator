# -*- coding: utf-8 -*-
from collections import OrderedDict
import os
# import shutil
from utils import SanitationUtils, TimeUtils, listUtils, debugUtils, Registrar
from utils import ProgressCounter
from csvparse_flat import CSVParse_User, UsrObjList #, ImportUser
from coldata import ColData_User
from tabulate import tabulate
from itertools import chain
# from pprint import pprint
# import sys
from copy import deepcopy
import unicodecsv
# import pickle
import dill as pickle
import requests
from bisect import insort
import re
import time
import yaml
# import MySQLdb
import paramiko
from sshtunnel import SSHTunnelForwarder, check_address
import io
# import wordpress_xmlrpc
from wordpress_json import WordpressJsonWrapper, WordpressError
import pymysql
from simplejson import JSONDecodeError
from sync_client import SyncClient_Abstract
from woocommerce import API as WCAPI

class ProdSyncClient_Abstract(SyncClient_Abstract):
    pass

class ProdSyncClient_WC(SyncClient_Abstract):
    def __exit__(self, type, value, traceback):
        pass

    def __init__(self, connectParams):
        super(ProdSyncClient_WC, self).__init__()
        mandatory_params = ['api_key', 'api_secret', 'url']
        for param in mandatory_params:
            assert param in connectParams, "missing mandatory param: %s" % param
        self.client = WCAPI(
            url=connectParams['url'],
            consumer_key=connectParams['api_key'],
            consumer_secret=connectParams['api_secret']
        )

    def uploadChanges(self, pkey, updates=None):
        super(type(self), self).uploadChanges(pkey)
        endpoint = 'products/%s' % pkey
        response = self.client.put(endpoint, updates)
