# -*- coding: utf-8 -*-
from collections import OrderedDict
import os
import re

import unicodecsv
import paramiko
from sshtunnel import SSHTunnelForwarder
import pymysql

from woogenerator.coldata import ColDataUser
from woogenerator.sync_client import SyncClientAbstract  # , AbstractServiceInterface
from woogenerator.sync_client import SyncClientWP
from woogenerator.sync_client import SyncClientWC
from woogenerator.utils import SanitationUtils, TimeUtils, Registrar
from woogenerator.utils import ProgressCounter, UnicodeCsvDialectUtils


class UsrSyncClientWC(SyncClientWC):
    endpoint_singular = 'customer'


class UsrSyncClientWP(SyncClientWP):
    endpoint_singular = 'user'

    @property
    def endpoint_plural(self):
        return "%ss?context=edit" % self.endpoint_singular


class UsrSyncClientSshAct(SyncClientAbstract):

    def __init__(self, connect_params, db_params, fs_params, **kwargs):
        self.db_params = db_params
        self.fs_params = fs_params
        self.dialect_suggestion = kwargs.get('dialect_suggestion', 'ActOut')
        self.encoding = kwargs.get('encoding', 'utf8')
        super(UsrSyncClientSshAct, self).__init__(connect_params, **kwargs)

    def attempt_connect(self):
        self.service = paramiko.SSHClient()
        self.service.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.service.connect(**self.connect_params)

    @property
    def connection_ready(self):
        return self.service and self.service._transport and self.service._transport.active

    def exec_silent_command_assert(self, command):
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
                SanitationUtils.coerce_unicode(command),
                SanitationUtils.coerce_unicode(error)
            )

    def put_file(self, local_path, remote_path):
        self.assert_connect()

        # remote_dir, remoteFileName = os.path.split(remote_path)
        remote_dir = os.path.split(remote_path)[0]

        exception = Exception()
        sftp_client = self.service.open_sftp()
        if remote_dir:
            try:
                sftp_client.stat(remote_dir)
            except:
                sftp_client.mkdir(remote_dir)
        sftp_client.put(local_path, remote_path)
        fstat = sftp_client.stat(remote_path)
        sftp_client.close()

        if not fstat:
            exception = UserWarning("could not stat remote file")
            raise exception

        # try:
        #     sftp_client = self.service.open_sftp()
        #     if remote_dir:
        #         try:
        #             sftp_client.stat(remote_dir)
        #         except:
        #             sftp_client.mkdir(remote_dir)
        #     sftp_client.put(local_path, remote_path)
        #     fstat = sftp_client.stat(remote_path)
        #     if not fstat:
        #         exception = UserWarning("could not stat remote file")
        # except Exception, exc:
        #     exception = exc
        # finally:
        #     sftp_client.close()
        # if not isinstance(exception, Exception):
        #     raise exception

    def assert_remote_file_exists(self, remote_path, assertion=""):
        self.assert_connect()

        # stdin, stdout, stderr = self.service.exec_command('stat "%s"' % remote_path)
        stderr = self.service.exec_command('stat "%s"' % remote_path)[2]
        possible_errors = stderr.readlines()
        assert not possible_errors, " ".join(
            [assertion, "stat returned possible errors", str(possible_errors)])

    @classmethod
    def print_file_progress(self, completed, total):
        if not hasattr(self, 'progress_counter'):
            self.progress_counter = ProgressCounter(total)
        self.progress_counter.maybe_print_update(completed)

    def get_delete_file(self, remote_path, local_path):
        self.assert_remote_file_exists(remote_path)

        sftp_client = self.service.open_sftp()
        sftp_client.get(remote_path, local_path, self.print_file_progress)
        sftp_client.remove(remote_path)
        sftp_client.close()

        # exception = None
        # try:
        #     sftp_client = self.service.open_sftp()
        #     sftp_client.get(remote_path, local_path, self.print_file_progress)
        #     sftp_client.remove(remote_path)
        # except Exception, exc:
        #     exception = exc
        # finally:
        #     sftp_client.close()
        # if exception:
        #     raise exception

    def remove_remote_file(self, remote_path):
        self.assert_remote_file_exists(remote_path)
        self.service.exec_command('rm "%s"' % remote_path)

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

        import_name = self.fs_params['import_name']
        out_folder = self.fs_params['out_folder']
        remote_export_folder = self.fs_params['remote_export_folder']
        file_root = 'act_i_' + import_name + '_' + user_pkey
        file_name = file_root + '.csv'
        local_path = os.path.join(out_folder, file_name)
        remote_path = os.path.join(remote_export_folder, file_name)
        imported_file = os.path.join(
            remote_export_folder, file_root + '.imported')

        with open(local_path, 'w+') as out_file:
            csvdialect = UnicodeCsvDialectUtils.ActOut
            dictwriter = unicodecsv.DictWriter(
                out_file,
                dialect=csvdialect,
                fieldnames=updates.keys(),
                encoding='utf8',
                extrasaction='ignore',
            )
            dictwriter.writeheader()
            dictwriter.writerow(updates)

        self.put_file(local_path, remote_path)

        tokens = [
            'cd ' + remote_export_folder + ';',
            '{db_i_exe} "-d{db_name}" "-h{db_host}" "-u{db_user}" "-p{db_pass}"'.format(
                **self.db_params
            ),
            ('"%s"' % file_name) if file_name else None
        ]

        command = " ".join(token for token in tokens if token)

        # command = " ".join(filter(None,))
        #
        # command = " ".join(filter(None,[
        #     'cd ' + remote_export_folder + ';',
        #     '{db_i_exe} "-d{db_name}" "-h{db_host}" "-u{db_user}" "-p{db_pass}"'.format(
        #         **self.db_params
        #     ),
        #     ('"%s"' % file_name) if file_name else None
        # ]))

        self.exec_silent_command_assert(command)

        try:
            self.remove_remote_file(imported_file)
        except:
            raise Exception("import didn't produce a .imported file")

    def analyse_remote(self, parser, **kwargs): # since=None, limit=None):
        since = kwargs.get('since', '1970-01-01')
        limit = kwargs.get('limit', self.limit)
        dialect_suggestion = kwargs.get('dialect_suggestion', self.dialect_suggestion)
        encoding = kwargs.get('encoding', self.encoding)
        data_file = kwargs.get('data_file')

        # TODO: implement limit
        if limit:
            pass

        import_name = self.fs_params['import_name']
        remote_export_folder = self.fs_params['remote_export_folder']
        file_root = 'act_x_' + import_name
        file_name = file_root + '.csv'
        if not data_file:
            data_file = os.path.join(self.fs_params['in_folder'], file_name)
        remote_path = os.path.join(remote_export_folder, file_name)

        tokens = [
            'cd ' + remote_export_folder + ';',
            '{db_x_exe} "-d{db_name}" "-h{db_host}" "-u{db_user}" "-p{db_pass}" -c"{fields}"'.format(
                **self.db_params
            ),
            '-s"%s"' % since,
            '"%s"' % file_name
        ]

        command = " ".join([token for token in tokens if token])

        # command = " ".join(filter(None,[
        #     'cd ' + remote_export_folder + ';',
        #     '{db_x_exe} "-d{db_name}" "-h{db_host}" "-u{db_user}" "-p{db_pass}" -c"{fields}"'.format(
        #         **self.db_params
        #     ),
        #     '-s"%s"' % since,
        #     '"%s"' % file_name
        # ]))

        print "executing export command..."
        self.exec_silent_command_assert(command)
        print "donloading file..."
        self.get_delete_file(remote_path, data_file)
        print "analysing file..."
        parser.analyse_file(
            data_file, 
            dialect_suggestion=dialect_suggestion, 
            limit=limit,
            encoding=encoding
        )


class UsrSyncClientSqlWP(SyncClientAbstract):
    service_builder = SSHTunnelForwarder

    """docstring for UsrSyncClientSqlWP"""

    def __init__(self, connect_params, db_params, **kwargs):
        self.db_params = db_params
        self.tbl_prefix = self.db_params.pop('tbl_prefix', '')
        self.since = kwargs.get('since')
        super(UsrSyncClientSqlWP, self).__init__(connect_params, **kwargs)
        # self.fs_params = fs_params

    def __enter__(self):
        self.service.start()
        return self

    def __exit__(self, exit_type, value, traceback):
        self.service.close()

    def attempt_connect(self):
        self.service = SSHTunnelForwarder(**self.connect_params)

    def analyse_remote(self, parser, filter_items=None, **kwargs):
        since = kwargs.get('since', self.since)
        limit = kwargs.get('limit', self.limit)

        self.assert_connect()

        # srv_offset = self.db_params.pop('srv_offset','')
        self.db_params['port'] = self.service.local_bind_address[-1]
        cursor = pymysql.connect(**self.db_params).cursor()

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

        for tracking_name, aliases in ColDataUser.get_wp_tracked_cols().items():
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
            headers = [SanitationUtils.coerce_unicode(
                i[0]) for i in cursor.description]
            results = [[SanitationUtils.coerce_unicode(
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

        wp_db_meta_cols = ColDataUser.get_wpdb_cols(meta=True)
        wp_db_core_cols = ColDataUser.get_wpdb_cols(meta=False)

        userdata_cols = ",\n\t\t".join(filter(None,
                                              [
                                                  "u.%s as `%s`" % (key, name)
                                                  for key, name in wp_db_core_cols.items()
                                              ] + [
                                                  "MAX(CASE WHEN um.meta_key = '%s' THEN um.meta_value ELSE \"\" END) as `%s`" % (
                                                      key, name)
                                                  for key, name in wp_db_meta_cols.items()
                                              ]
                                              ))

        # wpCols = OrderedDict(filter( lambda (k, v): not v.get('wp',{}).get('generated'), ColDataUser.get_wp_cols().items()))

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

        if filter_items:
            if 'cards' in filter_items:
                um_where_clauses.append("ud.`MYOB Card ID` IN (%s)" % (','.join([
                    '"%s"' % card for card in filter_items['cards']
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
            Registrar.register_message(sql_select_user_modtime)

        cursor.execute(sql_select_user_modtime)

        headers = [SanitationUtils.coerce_unicode(
            i[0]) for i in cursor.description]

        results = [[SanitationUtils.coerce_unicode(
            cell) for cell in row] for row in cursor]

        rows = [headers] + results

        # print rows

        if results:
            print "there are %d results" % len(results)
            parser.analyse_rows(rows)
