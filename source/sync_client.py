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

import httplib2

from apiclient import discovery
import oauth2client
from oauth2client import client
from oauth2client import tools

class SyncClient_Abstract(Registrar):
    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        raise NotImplementedError()

    """docstring for UsrSyncClient_Abstract"""

    @property
    def connectionReady(self):
        raise NotImplementedError()

    def analyseRemote(self, parser):
        raise NotImplementedError()

    def uploadChanges(self, pkey, updates=None):
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

    def __exit__(self, type, value, traceback):
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


    def analyseRemote(self, parser, gid=None, outPath=None):
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
        parser.analyseFile(outPath)

















            #
