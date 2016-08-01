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

class TansyncWordpressJsonWrapper(WordpressJsonWrapper):
    def _request(self, method_name, **kw):
        method, endpoint, params, data, headers = self._prepare_req(
            method_name, **kw
        )

        http_response = requests.request(
            method,
            self.site + endpoint,
            auth=self.auth,
            params=params,
            json=data,
            headers=headers
        )

        try:
            http_response_json = http_response.json()
        except JSONDecodeError:
            raise WordpressError(' '.join([
                'could not decode JSON:',
                str(http_response.text)
            ]))

        if http_response.status_code not in [200, 201, 400]:
            try:
                first_json_response = http_response_json[0]
            except KeyError:
                raise WordpressError(' '.join([
                    "invalid JSON response from",
                    http_response.url,
                    ": ",
                    http_response.text
                ]))
            raise WordpressError(" ".join([
                str(http_response.status_code),
                str(http_response.reason),
                ": ",
                '[%s] %s' % (first_json_response.get('code'),
                             first_json_response.get('message'))
            ]))

        return http_response_json

class UsrSyncClient_Abstract(SyncClient_Abstract):
    def __exit__(self, type, value, traceback):
        self.client.close()

    def connectionReady(self):
        return self.client

class UsrSyncClient_JSON(UsrSyncClient_Abstract):

    def __exit__(self, type, value, traceback):
        pass

    def __init__(self, connectParams):
        super(UsrSyncClient_JSON, self).__init__()
        mandatory_params = ['json_uri', 'wp_user', 'wp_pass']
        json_uri, wp_user, wp_pass = map(lambda k: connectParams.get(k), mandatory_params)
        for param in mandatory_params:
            assert eval(param), "missing mandatory param: " + param
        self.client = TansyncWordpressJsonWrapper(*map(eval, mandatory_params))

    # @property
    # def connectionReady(self):
    #     return self.client

    def uploadChanges(self, user_pkey, updates=None):
        super(type(self), self).uploadChanges(user_pkey)
        updates_json = SanitationUtils.encodeJSON(updates)
        # print "UPDATES:", updates
        updates_json_base64 = SanitationUtils.encodeBase64(updates_json)
        # print updates_json_base64
        json_out = self.client.update_user(user_id=user_pkey, data={'tansync_updated_fields': updates_json_base64})

        # print json_out
        if json_out is None:
            json_out = self.client.get_user(user_id=user_pkey)
            if 'tansync_last_error' in json_out:
                last_error = json_out['tansync_last_error']
                raise Exception(
                    "No response from json api, last error: %s" % last_error
                )
            raise Exception("No response from json api")
        return json_out

# class UsrSyncClient_XMLRPC(UsrSyncClient_Abstract):
#     class UpdateUserXMLRPC( wordpress_xmlrpc.AuthenticatedMethod ):
#         method_name = 'tansync.update_user_fields'
#         method_args = ('user_id', 'fields_json_base64')
#
#     def __exit__(self, type, value, traceback):
#         pass
#
#     def __init__(self, connectParams):
#         mandatory_params = ['xmlrpc_uri', 'wp_user', 'wp_pass']
#         xmlrpc_uri, wp_user, wp_pass = map(lambda k: connectParams.get(k), mandatory_params)
#         for param in mandatory_params:
#             assert eval(param), "missing mandatory param: " + param
#         self.client = wordpress_xmlrpc.Client(*map(eval, mandatory_params))
#
#     # @property
#     # def connectionReady(self):
#     #     return self.client
#
#     def uploadChanges(self, user_pkey, updates=None):
#         super(type(self), self).uploadChanges(user_pkey)
#         updates_json_base64 = SanitationUtils.encodeBase64(SanitationUtils.encodeJSON(updates))
#         xmlrpc_out = self.client.call(self.UpdateUserXMLRPC(user_pkey, updates_json_base64))
#         #TODO: process xmlrpc_out and determine if update was successful
#         SanitationUtils.safePrint( xmlrpc_out)
#         return xmlrpc_out

class UsrSyncClient_SSH_ACT(UsrSyncClient_Abstract):
    def __init__(self, connectParams, dbParams, fsParams):
        super(UsrSyncClient_SSH_ACT, self).__init__()
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
        for error in possible_errors:
            if re.match("^Countries.*", error):
                print error
                continue
            assert not error, "command <%s> returned errors: %s" % (
                SanitationUtils.coerceUnicode(command),
                SanitationUtils.coerceUnicode(error)
            )

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

    @classmethod
    def printFileProgress(self, completed, total):
        if not hasattr(self, 'progressCounter'):
            self.progressCounter = ProgressCounter(total)
        self.progressCounter.maybePrintUpdate(completed)

    def getDeleteFile(self, remotePath, localPath):
        self.assertRemoteFileExists(remotePath)
        exception = None
        try:
            sftpClient = self.client.open_sftp()
            sftpClient.get(remotePath, localPath, self.printFileProgress)
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
        # print "UPDATES:", updates
        assert self.connectionReady, "connection must be ready"
        updates['MYOB Card ID'] = user_pkey

        importName = self.fsParams['importName']
        outFolder = self.fsParams['outFolder']
        remote_export_folder = self.fsParams['remote_export_folder']
        fileRoot = 'act_i_' + importName + '_' + user_pkey
        fileName = fileRoot + '.csv'
        localPath = os.path.join(outFolder, fileName)
        remotePath = os.path.join(remote_export_folder, fileName)
        importedFile = os.path.join(remote_export_folder, fileRoot + '.imported')

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
            'cd ' + remote_export_folder + ';',
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

    def analyseRemote(self, parser, since=None, limit=None):
        if not since:
            since = '1970-01-01'

        importName = self.fsParams['importName']
        remote_export_folder = self.fsParams['remote_export_folder']
        fileRoot = 'act_x_' + importName
        fileName = fileRoot + '.csv'
        inFolder = self.fsParams['inFolder']
        localPath = os.path.join(inFolder, fileName)
        remotePath = os.path.join(remote_export_folder, fileName)

        command = " ".join(filter(None,[
            'cd ' + remote_export_folder + ';',
            '{db_x_exe} "-d{db_name}" "-h{db_host}" "-u{db_user}" "-p{db_pass}" -c"{fields}"'.format(
                **self.dbParams
            ),
            '-s"%s"' % since,
            '"%s"' % fileName
        ]))

        print "executing export command..."
        self.execSilentCommandAssert(command)
        print "donloading file..."
        self.getDeleteFile(remotePath, localPath)
        print "analysing file..."
        parser.analyseFile(localPath)

class UsrSyncClient_SQL_WP(UsrSyncClient_Abstract):
    """docstring for UsrSyncClient_SQL_WP"""
    def __init__(self, connectParams, dbParams):
        super(UsrSyncClient_SQL_WP, self).__init__()
        self.connectParams = connectParams
        self.dbParams = dbParams
        # self.fsParams = fsParams
        self.client = SSHTunnelForwarder( **connectParams )

    def __enter__(self):
        self.client.start()
        return self

    def __exit__(self, type, value, traceback):
        self.client.close()

    def analyseRemote(self, parser, since=None, limit=None):
        tbl_prefix = self.dbParams.pop('tbl_prefix','')
        # srv_offset = self.dbParams.pop('srv_offset','')
        self.dbParams['port'] = self.client.local_bind_address[-1]
        cursor = pymysql.connect( **self.dbParams ).cursor()

        if since:
            since_t = TimeUtils.wpServerToLocalTime( TimeUtils.wpStrptime(since))
            assert since_t, "Time should be valid format, got %s" % since
            since_s = TimeUtils.wpTimeToString(since_t)

            where_clause = "WHERE tu.`time` > '%s'" % since_s
        else:
            where_clause = ""

        modtime_cols = [
            "tu.`user_id` as `user_id`",
            "MAX(tu.`time`) as `Edited in Wordpress`"
        ]

        for tracking_name, aliases in ColData_User.getWPTrackedCols().items():
            case_clauses = []
            for alias in aliases:
                case_clauses.append("LOCATE('\"%s\"', tu.`changed`) > 0" % alias)
            modtime_cols.append("MAX(CASE WHEN {case_clauses} THEN tu.`time` ELSE \"\" END) as `{tracking_name}`".format(
                case_clauses = " OR ".join(case_clauses),
                tracking_name = tracking_name
            ))

        sql_select_modtime = """\
    SELECT
        {modtime_cols}
    FROM
        {tbl_tu} tu
    {where_clause}
    GROUP BY
        tu.`user_id`""".format(
            modtime_cols = ",\n\t\t".join(modtime_cols),
            tbl_tu=tbl_prefix+'tansync_updates',
            where_clause = where_clause,
        )
        # print sql_select_modtime

        if since:
            cursor.execute(sql_select_modtime)
            headers = [SanitationUtils.coerceUnicode(i[0]) for i in cursor.description]
            results = [[SanitationUtils.coerceUnicode(cell) for cell in row] for row in cursor]
            table = [headers] + results
            # print tabulate(table, headers='firstrow')
            # results = list(cursor)
            # if len(results) == 0:
            #     #nothing to analyse
            #     return
            # else:
            #     # n rows to analyse
            #     print "THERE ARE %d ITEMS" % len(results)

        wpDbMetaCols = ColData_User.getWPDBCols(meta=True)
        wpDbCoreCols = ColData_User.getWPDBCols(meta=False)

        userdata_cols = ",\n\t\t".join(filter(None,
            [
                "u.%s as `%s`" % (key, name)\
                    for key, name in wpDbCoreCols.items()
            ] + [
                "MAX(CASE WHEN um.meta_key = '%s' THEN um.meta_value ELSE \"\" END) as `%s`" % (key, name) \
                    for key, name in wpDbMetaCols.items()
            ]
        ))


        # wpCols = OrderedDict(filter( lambda (k, v): not v.get('wp',{}).get('generated'), ColData_User.getWPCols().items()))

        # assert all([
        #     'Wordpress ID' in wpCols.keys(),
        #     wpCols['Wordpress ID'].get('wp', {}).get('key') == 'ID',
        #     wpCols['Wordpress ID'].get('wp', {}).get('final')
        # ]), 'ColData should be configured correctly'

        # userdata_cols2 = ",\n\t\t".join(filter(None,[
        #     ("MAX(CASE WHEN um.meta_key = '%s' THEN um.meta_value ELSE \"\" END) as `%s`" if data['wp'].get('meta') else "u.%s as `%s`") % (data['wp']['key'], col)\
        #     for col, data in wpCols.items()
        # ]))

        # print " -> COLS1: ", userdata_cols
        # print " -> COLS2: ", userdata_cols2

        # print userdata_cols

        sql_select_user = """
    SELECT
        {usr_cols}
    FROM
        {tbl_u} u
        LEFT JOIN {tbl_um} um
        ON ( um.`user_id` = u.`ID`)
    GROUP BY
        u.`ID`""".format(
            tbl_u = tbl_prefix+'users',
            tbl_um = tbl_prefix+'usermeta',
            usr_cols = userdata_cols,
        )

        # print sql_select_user

        sql_select_user_modtime = """
SELECT *
FROM
(
    {sql_ud}
) as ud
{join_type} JOIN
(
    {sql_mt}
) as lu
ON (ud.`Wordpress ID` = lu.`user_id`)
{limit_clause};""".format(
            sql_ud = sql_select_user,
            sql_mt = sql_select_modtime,
            join_type = "INNER" if where_clause else "LEFT",
            limit_clause = "LIMIT %d" % limit if limit else ""
        )

        # Registrar.registerMessage(sql_select_user_modtime)

        cursor.execute(sql_select_user_modtime)

        headers = [SanitationUtils.coerceUnicode(i[0]) for i in cursor.description]

        results = [[SanitationUtils.coerceUnicode(cell) for cell in row] for row in cursor]

        rows = [headers] + results

        # print rows

        if results:
            print "there are %d results" % len(results)
            parser.analyseRows(rows)

        # for row in cursor:
            # print row

        # saRows = []

        # for i, row in enumerate(cursor):
        #     saRows += [map(SanitationUtils.coerceUnicode, row)]

        # if saRows:
        #     parser.analyseRows(saRows)

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
#
# def testXMLRPC():
#     # store_url = 'http://technotea.com.au/'
#     # username = 'Neil'
#     # password = 'Stretch@6164'
#     store_url = 'http://minimac.ddns.me:11182/'
#     username = 'neil'
#     password = 'Stretch6164'
#     xmlrpc_uri = store_url + 'xmlrpc.php'
#
#     xmlConnectParams = {
#         'xmlrpc_uri': xmlrpc_uri,
#         'wp_user': username,
#         'wp_pass': password
#     }
#
#     client = UsrSyncClient_XMLRPC(xmlConnectParams)
#
#     fields = {
#         u'first_name':  SanitationUtils.coerceBytes(u'no👌od👌le'),
#         'user_url': "http://www.laserphile.com/",
#         'user_login': "admin"
#     }
#
#     client.uploadChanges(1, fields)
#
# def testJSON():
#     store_url = 'http://technotea.com.au/'
#     username = 'Neil'
#     password = 'Stretch@6164'
#     # store_url = 'http://minimac.ddns.me:11182/'
#     # username = 'neil'
#     # password = 'Stretch6164'
#     json_uri = store_url + 'wp-json/wp/v2'
#
#     jsonConnectParams = {
#         'json_uri': json_uri,
#         'wp_user': username,
#         'wp_pass': password
#     }
#
#     client = UsrSyncClient_JSON(jsonConnectParams)
#
#     fields = {
#         u'first_name':  SanitationUtils.coerceBytes(u'no👌od👌le'),
#         'user_url': "http://www.laserphile.com/asd",
#         # 'first_name': 'noodle',
#         'user_login': "admin"
#     }
#
#     #
#
#     client.uploadChanges(1, fields)
#
# def testSQLWP(SSHTunnelForwarderParams, PyMySqlConnectParams):
#
#
#
#     saParser = CSVParse_User(
#         cols = ColData_User.getImportCols(),
#         defaults = ColData_User.getDefaults()
#     )
#     with UsrSyncClient_SQL_WP(SSHTunnelForwarderParams, PyMySqlConnectParams) as sqlClient:
#         sqlClient.analyseRemote(saParser, since='2016-01-01 00:00:00')
#
#     CSVParse_User.printBasicColumns( list(chain( *saParser.emails.values() )) )
#
# if __name__ == '__main__':
#     # srcFolder = "../source/"
#     # inFolder = "../input/"
#     yamlPath = "merger_config.yaml"
#     # importName = time.strftime("%Y-%m-%d %H:%M:%S")
#
#     with open(yamlPath) as stream:
#         # optionNamePrefix = 'test_'
#         optionNamePrefix = ''
#
#         config = yaml.load(stream)
#
#         # if 'inFolder' in config.keys():
#         #     inFolder = config['inFolder']
#         # if 'outFolder' in config.keys():
#         #     outFolder = config['outFolder']
#         # if 'logFolder' in config.keys():
#         #     logFolder = config['logFolder']
#
#         #mandatory
#         # merge_mode = config.get('merge_mode', 'sync')
#         ssh_user = config.get(optionNamePrefix+'ssh_user')
#         ssh_pass = config.get(optionNamePrefix+'ssh_pass')
#         ssh_host = config.get(optionNamePrefix+'ssh_host')
#         ssh_port = config.get(optionNamePrefix+'ssh_port', 22)
#         remote_bind_host = config.get(optionNamePrefix+'remote_bind_host', '127.0.0.1')
#         remote_bind_port = config.get(optionNamePrefix+'remote_bind_port', 3306)
#         db_user = config.get(optionNamePrefix+'db_user')
#         db_pass = config.get(optionNamePrefix+'db_pass')
#         db_name = config.get(optionNamePrefix+'db_name')
#         db_charset = config.get(optionNamePrefix+'db_charset', 'utf8mb4')
#         wp_srv_offset = config.get(optionNamePrefix+'wp_srv_offset', 0)
#         tbl_prefix = config.get(optionNamePrefix+'tbl_prefix', '')
#
#     TimeUtils.setWpSrvOffset(wp_srv_offset)
#
#     SSHTunnelForwarderAddress = (ssh_host, ssh_port)
#     SSHTunnelForwarderBindAddress = (remote_bind_host, remote_bind_port)
#
#     SSHTunnelForwarderParams = {
#         'ssh_address_or_host':SSHTunnelForwarderAddress,
#         'ssh_password':ssh_pass,
#         'ssh_username':ssh_user,
#         'remote_bind_address': SSHTunnelForwarderBindAddress,
#     }
#
#     PyMySqlConnectParams = {
#         'host' : 'localhost',
#         'user' : db_user,
#         'password': db_pass,
#         'db'   : db_name,
#         'charset': db_charset,
#         'use_unicode': True,
#         'tbl_prefix': tbl_prefix,
#         # 'srv_offset': wp_srv_offset,
#     }
#     # testXMLRPC()
#     # testJSON()
#     testSQLWP(SSHTunnelForwarderParams, PyMySqlConnectParams)
