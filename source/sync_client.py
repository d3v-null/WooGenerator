# -*- coding: utf-8 -*-
from collections import OrderedDict, Iterable
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

import httplib2

from apiclient import discovery
import oauth2client
from oauth2client import client
from oauth2client import tools

from woocommerce import API as WCAPI
from simplejson.scanner import JSONDecodeError

class AbstractClientInterface:
    def close(self):
        pass

    def connect(self, connectParams):
        pass

class SyncClient_Abstract(Registrar):
    """docstring for UsrSyncClient_Abstract"""
    def __enter__(self):
        return self

    def __exit__(self, exit_type, value, traceback):
        raise NotImplementedError()

    @property
    def connectionReady(self):
        raise NotImplementedError()

    def analyseRemote(self, parser, *args):
        raise NotImplementedError()

    def uploadChanges(self, pkey, updates=None):
        if updates:
            assert pkey, "must have a valid primary key"
            assert self.connectionReady, "connection should be ready"

class SyncClient_GDrive(SyncClient_Abstract):
    skip_download = None

    def __init__(self, gdriveParams):
        super(SyncClient_GDrive, self).__init__()
        for key in ['credentials_dir', 'credentials_file', 'client_secret_file',
                    'scopes', 'app_name']:
            assert key in gdriveParams
        self.gdriveParams = gdriveParams
        credentials = self.get_credentials()
        auth_http = credentials.authorize(httplib2.Http())
        self.service = discovery.build('drive', 'v2', http=auth_http)
        self.drive_file = self.service.files().get(fileId=self.gdriveParams['genFID']).execute()

    def __exit__(self, exit_type, value, traceback):
        pass

    @property
    def connectionReady(self):
        return self.service

    def get_credentials(self):
        credential_dir = os.path.expanduser(self.gdriveParams['credentials_dir'])
        if not os.path.exists(credential_dir):
            os.makedirs(credential_dir)
        credential_path = os.path.join(credential_dir, self.gdriveParams['credentials_file'])
        store = oauth2client.file.Storage(credential_path)
        credentials = store.get()
        if not credentials or credentials.invalid:
            flow = client.flow_from_clientsecrets(self.gdriveParams['client_secret_file'],
                                                  self.gdriveParams['scopes'])
            flow.user_agent = self.gdriveParams['app_name']
            # if flags:
            #     credentials = tools.run_flow(flow, store, flags)
            # else: # Needed only for compatibility with Python 2.6
            #     credentials = tools.run(flow, store)
            credentials = tools.run(flow, store)
            self.registerMessage('Storing credentials to ' + credential_path)
        return credentials

    def download_file_content_csv(self, gid=None):
        """Download current file's content as csv.

        Args:
          gid: GID of file to download

        Returns:
          File's content if successful, None otherwise.
        """
        # print( type(drive_file) )
        # print( drive_file)
        download_url = self.drive_file['exportLinks']['text/csv']
        if gid:
            download_url += "&gid=" + str(gid )
        self.registerMessage( "Downloading: %s" % download_url )
        if download_url:
            resp, content = self.service._http.request(download_url)
            if resp.status == 200:
                self.registerMessage('Status: %s' % resp)
                return content
            else:
                self.registerError('An error occurred: %s' % resp)
                return None
        else:
            return None
            # The file doesn't have any content stored on Drive.

    def get_gm_modtime(self, gid=None):
        modifiedDate = self.drive_file['modifiedDate']

        return time.strptime(modifiedDate, '%Y-%m-%dT%H:%M:%S.%fZ')


    def analyseRemote(self, parser, gid=None, outPath=None, limit=None):
        if not outPath:
            outPath = '/tmp/' + gid + '.csv'
        if not self.skip_download:
            # try:
            #     assert os.path.isfile(outPath)
            #     local_timestamp = os.path.getmtime(outPath)
            # except:
            #     local_timestamp = 0
            # local_gmtime = time.gmtime(local_timestamp)
            #
            # remote_gmtime = get_gm_modtime(gid)
            #
            # print "local / remote gmtime", local_gmtime, remote_gmtime

            # if local_gmtime < remote_gmtime:
            content = self.download_file_content_csv(gid)
            if content:
                with open(outPath, 'w') as outFile:
                    outFile.write(content)
                    print "downloaded ", outFile
        parser.analyseFile(outPath, limit=limit)

class SyncClient_WC(SyncClient_Abstract):
    class ApiIterator(Iterable):
        def __init__(self, api, endpoint):
            assert isinstance(api, WCAPI)
            self.api = api
            self.next_endpoint = endpoint
            self.prev_response = None
            self.next_page = None
            # self.progressCounter = None
            self.total_pages = None
            self.total_items = None
            # self.stopNextIteration = False

        def get_page_param(self, url):
            params = SanitationUtils.findall_url_params(url)
            if 'page' in params:
                pages = params['page']
                assert len(pages) == 1
                return int(pages[0])
            else:
                return None

        def processHeaders(self, headers):
            if self.total_pages is None:
                self.total_pages = int(headers.get('x-wc-totalpages'))
            if self.total_items is None:
                self.total_items = int(headers.get('x-wc-total'))
            # if self.progressCounter is None:
            #     self.progressCounter = ProgressCounter(total=self.total_pages)
            # self.stopNextIteration = True
            # self.next_page = self.total_pages
            self.next_endpoint = None
            links_str = headers.get('link', '')
            if Registrar.DEBUG_API:
                Registrar.registerMessage("links str: {}".format(links_str))
            for link in SanitationUtils.findall_wc_links(links_str):
                if link.get('rel') == 'next' and link.get('url'):
                    next_response_url = link['url']
                    self.next_page = self.get_page_param(next_response_url)
                    if self.next_page == 2:
                        next_response_url = re.sub(r'page=\d', 'page=8', next_response_url)
                    # self.stopNextIteration = False
                    if Registrar.DEBUG_API:
                        Registrar.registerMessage('next_response_url: %s' % str(next_response_url))
                    self.next_endpoint = self.__get_endpoint(next_response_url)
                    if Registrar.DEBUG_API:
                        Registrar.registerMessage('next_endpoint: %s' % str(self.next_endpoint))
                    break

            # self.progressCounter.maybePrintUpdate(self.next_page)

        def __get_endpoint(self, url):
            url_path = SanitationUtils.stripURLHost(url)
            api_url_path = SanitationUtils.stripURLHost(self.api._API__get_url(''))
            if url_path.startswith(api_url_path):
                return url_path.replace(api_url_path, '')
            else:
                return url_path

        def __iter__(self):
            return self

        def next(self):
            if Registrar.DEBUG_API:
                Registrar.registerMessage('start')

            if self.next_endpoint is None:
                if Registrar.DEBUG_API:
                    Registrar.registerMessage('stopping due to no next endpoint')
                raise StopIteration()

            # get API response
            self.prev_response = self.api.get(self.next_endpoint)

            # handle API errors
            if self.prev_response.status_code in [404]:
                raise UserWarning('api call failed: 404d')
            try:
                prev_response_json = self.prev_response.json()
            except JSONDecodeError:
                Registrar.registerWarning("first attempt timed out, trying again on %s" % self.next_endpoint)
                old_timeout = self.api.timeout
                self.api.timeout = old_timeout * 2
                self.prev_response = self.api.get(self.next_endpoint)
                self.api.timeout = old_timeout

                try:
                    prev_response_json = self.prev_response.json()
                except JSONDecodeError:
                    prev_response_json = {}
                    e = UserWarning('api call failed: timed out on %s' % self.next_endpoint)
                    Registrar.registerError(e)

                    # raise e

            if Registrar.DEBUG_API:
                Registrar.registerMessage('first api response: %s' % str(prev_response_json))
            if 'errors' in prev_response_json:
                raise UserWarning('first api call returned errors: %s' % (prev_response_json['errors']))

            # process API headers
            self.processHeaders(self.prev_response.headers)

            return prev_response_json


    def __init__(self, connectParams):
        super(SyncClient_WC, self).__init__()
        mandatory_params = ['api_key', 'api_secret', 'url']
        for param in mandatory_params:
            assert param in connectParams and connectParams[param], \
                "missing mandatory param: %s" % param
        self.client = WCAPI(
            url=connectParams['url'],
            consumer_key=connectParams['api_key'],
            consumer_secret=connectParams['api_secret'],
            timeout=60,
            # wp_api=True, # Enable the WP REST API integration
            # version="v3", # WooCommerce WP REST API version
            # version="wc/v1"
        )

    def connectionReady(self):
        return self.client

    def __exit__(self, exit_type, value, traceback):
        pass
