# -*- coding: utf-8 -*-
from collections import OrderedDict
import os
import re

import unicodecsv
import paramiko
from sshtunnel import SSHTunnelForwarder
import pymysql

from woogenerator.coldata import ColData_User
from woogenerator.sync_client import SyncClientAbstract  # , AbstractServiceInterface
from woogenerator.sync_client import SyncClientWP
from woogenerator.sync_client import SyncClientWC
from woogenerator.utils import SanitationUtils, TimeUtils, Registrar
from woogenerator.utils import ProgressCounter, UnicodeCsvDialectUtils


class UsrSyncClient_WC(SyncClientWC):
    endpoint_singular = 'customer'


class UsrSyncClient_WP(SyncClientWP):
    endpoint_singular = 'user'

    @property
    def endpoint_plural(self):
        return "%ss?context=edit" % self.endpoint_singular


class UsrSyncClient_SSH_ACT(SyncClientAbstract):

    def __init__(self, connect_params, dbParams, fsParams):
        self.dbParams = dbParams
        self.fsParams = fsParams
        super(UsrSyncClient_SSH_ACT, self).__init__(connect_params)

    def attempt_connect(self):
        self.service = paramiko.SSHClient()
        self.service.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.service.connect(**self.connect_params)

    @property
    def connection_ready(self):
        return self.service and self.service._transport and self.service._transport.active

    def execSilentCommandAssert(self, command):
        self.assert_connect()
        stdin, stdout, stderr = self.service.exec_command(command)
        if stdin:
            pass  # gets rid of annoying warnings
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
        self.assert_connect()

        # remoteDir, remoteFileName = os.path.split(remotePath)
        remoteDir = os.path.split(remotePath)[0]

        exception = Exception()
        sftpClient = self.service.open_sftp()
        if remoteDir:
            try:
                sftpClient.stat(remoteDir)
            except:
                sftpClient.mkdir(remoteDir)
        sftpClient.put(localPath, remotePath)
        fstat = sftpClient.stat(remotePath)
        sftpClient.close()

        if not fstat:
            exception = UserWarning("could not stat remote file")
            raise exception

        # try:
        #     sftpClient = self.service.open_sftp()
        #     if remoteDir:
        #         try:
        #             sftpClient.stat(remoteDir)
        #         except:
        #             sftpClient.mkdir(remoteDir)
        #     sftpClient.put(localPath, remotePath)
        #     fstat = sftpClient.stat(remotePath)
        #     if not fstat:
        #         exception = UserWarning("could not stat remote file")
        # except Exception, exc:
        #     exception = exc
        # finally:
        #     sftpClient.close()
        # if not isinstance(exception, Exception):
        #     raise exception

    def assertRemoteFileExists(self, remotePath, assertion=""):
        self.assert_connect()

        # stdin, stdout, stderr = self.service.exec_command('stat "%s"' % remotePath)
        stderr = self.service.exec_command('stat "%s"' % remotePath)[2]
        possible_errors = stderr.readlines()
        assert not possible_errors, " ".join(
            [assertion, "stat returned possible errors", str(possible_errors)])

    @classmethod
    def printFileProgress(self, completed, total):
        if not hasattr(self, 'progress_counter'):
            self.progress_counter = ProgressCounter(total)
        self.progress_counter.maybePrintUpdate(completed)

    def getDeleteFile(self, remotePath, localPath):
        self.assertRemoteFileExists(remotePath)

        sftpClient = self.service.open_sftp()
        sftpClient.get(remotePath, localPath, self.printFileProgress)
        sftpClient.remove(remotePath)
        sftpClient.close()

        # exception = None
        # try:
        #     sftpClient = self.service.open_sftp()
        #     sftpClient.get(remotePath, localPath, self.printFileProgress)
        #     sftpClient.remove(remotePath)
        # except Exception, exc:
        #     exception = exc
        # finally:
        #     sftpClient.close()
        # if exception:
        #     raise exception

    def removeRemoteFile(self, remotePath):
        self.assertRemoteFileExists(remotePath)
        self.service.exec_command('rm "%s"' % remotePath)

    def upload_changes(self, user_pkey, updates=None):
        if not updates:
            return
        # print "UPDATES:", updates

        self.assert_connect()

        if 'MYOB Card ID' in updates:
            del updates['MYOB Card ID']

        updates = OrderedDict(
            [('MYOB Card ID', user_pkey)]
            + updates.items()
        )

        importName = self.fsParams['importName']
        outFolder = self.fsParams['outFolder']
        remote_export_folder = self.fsParams['remote_export_folder']
        fileRoot = 'act_i_' + importName + '_' + user_pkey
        fileName = fileRoot + '.csv'
        localPath = os.path.join(outFolder, fileName)
        remotePath = os.path.join(remote_export_folder, fileName)
        importedFile = os.path.join(
            remote_export_folder, fileRoot + '.imported')

        with open(localPath, 'w+') as out_file:
            csvdialect = UnicodeCsvDialectUtils.act_out
            dictwriter = unicodecsv.DictWriter(
                out_file,
                dialect=csvdialect,
                fieldnames=updates.keys(),
                encoding='utf8',
                extrasaction='ignore',
            )
            dictwriter.writeheader()
            dictwriter.writerow(updates)

        self.putFile(localPath, remotePath)

        tokens = [
            'cd ' + remote_export_folder + ';',
            '{db_i_exe} "-d{db_name}" "-h{db_host}" "-u{db_user}" "-p{db_pass}"'.format(
                **self.dbParams
            ),
            ('"%s"' % fileName) if fileName else None
        ]

        command = " ".join(token for token in tokens if token)

        # command = " ".join(filter(None,))
        #
        # command = " ".join(filter(None,[
        #     'cd ' + remote_export_folder + ';',
        #     '{db_i_exe} "-d{db_name}" "-h{db_host}" "-u{db_user}" "-p{db_pass}"'.format(
        #         **self.dbParams
        #     ),
        #     ('"%s"' % fileName) if fileName else None
        # ]))

        self.execSilentCommandAssert(command)

        try:
            self.removeRemoteFile(importedFile)
        except:
            raise Exception("import didn't produce a .imported file")

    def analyse_remote(self, parser, since=None, limit=None):
        if not since:
            since = '1970-01-01'
        if limit:
            # todo: implement limit
            # this gets rid of unused argument warnings
            pass

        importName = self.fsParams['importName']
        remote_export_folder = self.fsParams['remote_export_folder']
        fileRoot = 'act_x_' + importName
        fileName = fileRoot + '.csv'
        inFolder = self.fsParams['inFolder']
        localPath = os.path.join(inFolder, fileName)
        remotePath = os.path.join(remote_export_folder, fileName)

        tokens = [
            'cd ' + remote_export_folder + ';',
            '{db_x_exe} "-d{db_name}" "-h{db_host}" "-u{db_user}" "-p{db_pass}" -c"{fields}"'.format(
                **self.dbParams
            ),
            '-s"%s"' % since,
            '"%s"' % fileName
        ]

        command = " ".join([token for token in tokens if token])

        # command = " ".join(filter(None,[
        #     'cd ' + remote_export_folder + ';',
        #     '{db_x_exe} "-d{db_name}" "-h{db_host}" "-u{db_user}" "-p{db_pass}" -c"{fields}"'.format(
        #         **self.dbParams
        #     ),
        #     '-s"%s"' % since,
        #     '"%s"' % fileName
        # ]))

        print "executing export command..."
        self.execSilentCommandAssert(command)
        print "donloading file..."
        self.getDeleteFile(remotePath, localPath)
        print "analysing file..."
        parser.analyseFile(localPath, dialect_suggestion='act_out')


class UsrSyncClient_SQL_WP(SyncClientAbstract):
    service_builder = SSHTunnelForwarder

    """docstring for UsrSyncClient_SQL_WP"""

    def __init__(self, connect_params, dbParams):
        self.dbParams = dbParams
        self.tbl_prefix = self.dbParams.pop('tbl_prefix', '')
        super(UsrSyncClient_SQL_WP, self).__init__(connect_params)
        # self.fsParams = fsParams

    def __enter__(self):
        self.service.start()
        return self

    def __exit__(self, exit_type, value, traceback):
        self.service.close()

    def attempt_connect(self):
        self.service = SSHTunnelForwarder(**self.connect_params)

    def analyse_remote(self, parser, since=None, limit=None, filterItems=None):

        self.assert_connect()

        # srv_offset = self.dbParams.pop('srv_offset','')
        self.dbParams['port'] = self.service.local_bind_address[-1]
        cursor = pymysql.connect(**self.dbParams).cursor()

        sm_where_clauses = []

        if since:
            since_t = TimeUtils.wp_server_to_local_time(
                TimeUtils.wp_strp_mktime(since))
            assert since_t, "Time should be valid format, got %s" % since
            since_s = TimeUtils.wp_time_to_string(since_t)

            sm_where_clauses.append("tu.`time` > '%s'" % since_s)

        modtime_cols = [
            "tu.`user_id` as `user_id`",
            "MAX(tu.`time`) as `Edited in Wordpress`"
        ]

        for tracking_name, aliases in ColData_User.getWPTrackedCols().items():
            case_clauses = []
            for alias in aliases:
                case_clauses.append(
                    "LOCATE('\"%s\"', tu.`changed`) > 0" % alias)
            modtime_cols.append("MAX(CASE WHEN {case_clauses} THEN tu.`time` ELSE \"\" END) as `{tracking_name}`".format(
                case_clauses=" OR ".join(case_clauses),
                tracking_name=tracking_name
            ))

        if sm_where_clauses:
            sm_where_clause = 'WHERE ' + ' AND '.join(sm_where_clauses)
        else:
            sm_where_clause = ''

        sql_select_modtime = """\
    SELECT
        {modtime_cols}
    FROM
        {tbl_tu} tu
    {sm_where_clause}
    GROUP BY
        tu.`user_id`""".format(
            modtime_cols=",\n\t\t".join(modtime_cols),
            tbl_tu=self.tbl_prefix + 'tansync_updates',
            sm_where_clause=sm_where_clause,
        )

        # print sql_select_modtime

        if since:
            cursor.execute(sql_select_modtime)
            headers = [SanitationUtils.coerceUnicode(
                i[0]) for i in cursor.description]
            results = [[SanitationUtils.coerceUnicode(
                cell) for cell in row] for row in cursor]
            # table = [headers] + results
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
                                                  "u.%s as `%s`" % (key, name)
                                                  for key, name in wpDbCoreCols.items()
                                              ] + [
                                                  "MAX(CASE WHEN um.meta_key = '%s' THEN um.meta_value ELSE \"\" END) as `%s`" % (
                                                      key, name)
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
            tbl_u=self.tbl_prefix + 'users',
            tbl_um=self.tbl_prefix + 'usermeta',
            usr_cols=userdata_cols,
        )

        um_on_clauses = []
        um_where_clauses = []

        um_on_clauses.append('ud.`Wordpress ID` = lu.`user_id`')

        if filterItems:
            if 'cards' in filterItems:
                um_where_clauses.append("ud.`MYOB Card ID` IN (%s)" % (','.join([
                    '"%s"' % card for card in filterItems['cards']
                ])))

        if um_on_clauses:
            um_on_clause = ' AND '.join([
                "(%s)" % clause for clause in um_on_clauses
            ])
        else:
            um_on_clause = ''

        if um_where_clauses:
            um_where_clause = 'WHERE ' + ' AND '.join([
                "(%s)" % clause for clause in um_where_clauses
            ])
        else:
            um_where_clause = ''

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
ON {um_on_clause}
{um_where_clause}
{limit_clause};""".format(
            sql_ud=sql_select_user,
            sql_mt=sql_select_modtime,
            join_type="INNER" if sm_where_clause else "LEFT",
            limit_clause="LIMIT %d" % limit if limit else "",
            um_on_clause=um_on_clause,
            um_where_clause=um_where_clause
        )

        if Registrar.DEBUG_CLIENT:
            Registrar.registerMessage(sql_select_user_modtime)

        cursor.execute(sql_select_user_modtime)

        headers = [SanitationUtils.coerceUnicode(
            i[0]) for i in cursor.description]

        results = [[SanitationUtils.coerceUnicode(
            cell) for cell in row] for row in cursor]

        rows = [headers] + results

        # print rows

        if results:
            print "there are %d results" % len(results)
            parser.analyseRows(rows)
