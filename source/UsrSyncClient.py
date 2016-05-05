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
import pymysql

class UsrSyncClient_Abstract(object):

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.client.close()

    """docstring for UsrSyncClient_Abstract"""

    @property
    def connectionReady(self):
        return self.client
        
    def analyseRemote(self, parser, since=None):
        raise NotImplementedError()

    def uploadChanges(self, user_pkey, updates=None):
        assert user_pkey, "must have a valid primary key"
        assert self.connectionReady, "connection should be ready"

class UsrSyncClient_XMLRPC(UsrSyncClient_Abstract):
    class UpdateUserXMLRPC( wordpress_xmlrpc.AuthenticatedMethod ):
        method_name = 'tansync.update_user_fields'
        method_args = ('user_id', 'fields_json_base64')

    def __exit__(self, type, value, traceback):
        pass

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
        print xmlrpc_out
        return xmlrpc_out

class UsrSyncClient_SSH_ACT(UsrSyncClient_Abstract):
    def __init__(self, connectParams, dbParams, fsParams):
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.client.connect(**connectParams)
        self.dbParams = dbParams
        self.fsParams = fsParams

    @property
    def connectionReady(self):
        return self.client and self.client._transport and self.client._transport.active

    def execSilentCommandAssert(self, command):
        assert self.connectionReady, "master connection must be ready"
        stdin, stdout, stderr = self.client.exec_command(command)
        possible_errors = stdout.readlines() + stderr.readlines()
        assert not possible_errors, "command returned errors: " + str(possible_errors)

    def putFile(self, localPath, remotePath):
        assert self.connectionReady, "master connection must be ready"
        remoteDir, remoteFileName = os.path.split(remotePath)

        exception = None
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


    def assertRemoteFileExists(self, remotePath, assertion = ""):
        assert self.connectionReady, "master connection must be ready"
        stdin, stdout, stderr = self.client.exec_command('stat "%s"' % remotePath)
        possible_errors = stderr.readlines()
        assert not possible_errors, " ".join([assertion, "stat returned possible errors", str(possible_errors)])

    def getDeleteFile(self, remotePath, localPath):
        self.assertRemoteFileExists(remotePath)
        exception = None
        try:
            sftpClient = self.client.open_sftp()    
            sftpClient.get(remotePath, localPath)
            sftpClient.remove(remotePath)
        except Exception, e:
            exception = e
        finally:
            sftpClient.close()
        if exception:
            raise exception

    def removeRemoteFile(self, remotePath):
        self.assertRemoteFileExists(remotePath)
        self.client.exec_command('rm "%s"' % remotePath)

    def uploadChanges(self, user_pkey, updates=None):
        if not updates:
            return
        assert self.connectionReady    
        updates['MYOB Card ID'] = user_pkey

        importName = self.fsParams['importName']
        outFolder = self.fsParams['outFolder']
        remoteExportFolder = self.fsParams['remoteExportFolder']
        fileRoot = 'act_i_' + importName + '_' + user_pkey
        fileName = fileRoot + '.csv'
        localPath = os.path.join(outFolder, fileName)
        remotePath = os.path.join(remoteExportFolder, fileName)
        importedFile = os.path.join(remoteExportFolder, fileRoot + '.imported')

        with open(localPath, 'w+') as outFile:
            unicodecsv.register_dialect('act_out', delimiter=',', quoting=unicodecsv.QUOTE_ALL, doublequote=False, strict=True, quotechar="\"", escapechar="`")
            dictwriter = unicodecsv.DictWriter(
                outFile,
                dialect = 'act_out',
                fieldnames = updates.keys(),
                encoding = 'utf8',
                extrasaction = 'ignore',
            )
            dictwriter.writeheader()
            dictwriter.writerow(updates)

        self.putFile( localPath, remotePath)            

        command = " ".join(filter(None,[
            'cd ' + remoteExportFolder + ';',
            '{db_i_exe} "-d{db_name}" "-h{db_host}" "-u{db_user}" "-p{db_pass}"'.format(
                **self.dbParams
            ),
            ('"%s"' % fileName) if fileName else None
        ]))

        self.execSilentCommandAssert(command)

        try:
            self.removeRemoteFile(importedFile)
        except:
            raise Exception("import didn't produce a .imported file")
        
    def analyseRemote(self, parser, since=None):
        if not since:
            since = '1970-01-01'

        importName = self.fsParams['importName']
        remoteExportFolder = self.fsParams['remoteExportFolder']
        fileRoot = 'act_x_' + importName
        fileName = fileRoot + '.csv'
        inFolder = self.fsParams['inFolder']
        localPath = os.path.join(inFolder, fileName)
        remotePath = os.path.join(remoteExportFolder, fileName)


        command = " ".join(filter(None,[
            'cd ' + remoteExportFolder + ';',
            '{db_x_exe} "-d{db_name}" "-h{db_host}" "-u{db_user}" "-p{db_pass}" -c"{fields}"'.format(
                **self.dbParams
            ),
            '-s"%s"' % since,
            '"%s"' % fileName
        ]))

        self.execSilentCommandAssert(command)

        self.getDeleteFile(remotePath, localPath)

        parser.analyseFile(localPath)

class UsrSyncClient_SQL_WP(UsrSyncClient_Abstract):
    """docstring for UsrSyncClient_SQL_WP"""
    def __init__(self, connectParams, dbParams, fsParams):
        super(UsrSyncClient_SQL_WP, self).__init__()
        self.connectParams = connectParams
        self.dbParams = dbParams
        self.fsParams = fsParams
        self.client = SSHTunnelForwarder( **connectParams )

    def analyseRemote(self, parser, since=None):
        tbl_prefix = self.dbParams.pop('tbl_prefix','')
        self.dbParams['port'] = self.client.local_bind_address[-1]
        cursor = pymysql.connect( **self.dbParams ).cursor()

        sql_select_modtime = """\
    SELECT
        tu.`user_id` as `user_id`,
        MAX(tu.`time`) as `Edited in Wordpress`
    FROM
        {tbl_tu} tu
    GROUP BY 
        tu.`user_id`""".format(
            tbl_tu=tbl_prefix+'tansync_updates'
        )

        cursor.execute(sql_select_modtime)

        print cursor.description

        print "-" * len(cursor.description)

        for row in cursor:
            print row

        # sql_select_user = """\
        # SELECT  
        #     {usr_cols}
        # FROM
        #     {tbl_u} u
        #     LEFT JOIN {tbl_um} um
        #     ON ( um.`user_id` = u.`ID`)
        # GROUP BY
        #     u.`ID`
        # """.format(
        #     tbl_u = tbl_prefix+'users', 
        #     tbl_um = tbl_prefix+'usermeta'
        # )
        


