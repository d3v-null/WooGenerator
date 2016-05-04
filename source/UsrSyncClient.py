from collections import OrderedDict
import os
# import shutil
from utils import SanitationUtils, TimeUtils, listUtils, debugUtils
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
from bisect import insort
import re
import time
import yaml
import MySQLdb
import paramiko
from sshtunnel import SSHTunnelForwarder, check_address
import io
import wordpress_xmlrpc

class UsrSyncClient_Abstract(object):
    """docstring for UsrSyncClient_Abstract"""

    @property
    def connectionReady(self):
        return self.client
        
    def analyseRemote(self, parser):
        raise NotImplementedError()

    def uploadChanges(self, user_pkey, updates=None):
        assert user_pkey, "must have a valid primary key"
        assert self.connectionReady, "connection should be ready"

class UsrSyncClient_XMLRPC(UsrSyncClient_Abstract):
    class UpdateUserXMLRPC( wordpress_xmlrpc.AuthenticatedMethod ):
        method_name = 'tansync.update_user_fields'
        method_args = ('user_id', 'fields_json_base64')

    def __init__(self, connectParams):
        mandatory_params = ['xmlrpc_uri', 'wp_user', 'wp_pass']
        xmlrpc_uri, wp_user, wp_pass = map(lambda k: connectParams.get(k), mandatory_params)
        for param in mandatory_params:
            assert eval(param), "missing mandatory param: " + param
        self.client = wordpress_xmlrpc.Client(*map(eval, mandatory_params))
        
    # @property
    # def connectionReady(self):
    #     return self.client

    def uploadChanges(self, user_pkey, updates=None):
        super(type(self), self).uploadChanges(user_pkey)
        updates_json_base64 = SanitationUtils.encodeBase64(SanitationUtils.encodeJSON(updates))
        xmlrpc_out = self.client.call(self.UpdateUserXMLRPC(user_pkey, updates_json_base64))
        #TODO: process xmlrpc_out and determine if update was successful
        return xmlrpc_out

class UsrSyncClient_SSH_ACT(UsrSyncClient_Abstract):
    def __init__(self, connectParams, dbParams):
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(**connectParams)
        self.dbParams = dbParams

    @property
    def connectionReady(self):
        return self.client and self.client._transport and self.client._transport.active

    def putFile(self, localPath, remotePath):
        assert self.connectionReady, "master connection must be ready"
        exception = None
        remoteDir, remoteFileName = os.path.split(remotePath)

        try:
            sftpClient = self.client.open_sftp()    
            if remoteDir:
                try:
                    sftpClient.stat(remoteDir)
                except:
                    sftpClient.mkdir(remoteDir)
            sftpClient.put(localPath, remotePath)
            fstat = sftpClient.stat(remotePath)
            if not fstat:
                exception = Exception("could not stat remote file")
        except Exception, e:
            exception = e
        finally:
            sftpClient.close()
        if exception:
            raise exception

    