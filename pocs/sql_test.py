import MySQLdb
from sshtunnel import SSHTunnelForwarder
import yaml
import os
import time
from coldata import ColDataUser
from parsing.flat import CsvParseUser
from collections import OrderedDict

srcFolder = "../source/"
in_folder = "../input/"
yaml_path = "merger_config.yaml"
import_name = time.strftime("%Y-%m-%d %H:%M:%S")

with open(yaml_path) as stream:
    config = yaml.load(stream)

    ssh_user = config.get('ssh_user')
    ssh_pass = config.get('ssh_pass')
    ssh_host = config.get('ssh_host')
    ssh_port = config.get('ssh_port', 22)
    remote_bind_host = config.get('remote_bind_host', '127.0.0.1')
    remote_bind_port = config.get('remote_bind_port', 3306)
    db_host = config.get('db_host', '127.0.0.1')
    db_user = config.get('db_user')
    db_pass = config.get('db_pass')
    db_name = config.get('db_name')
    tbl_prefix = config.get('tbl_prefix', '')

sqlPath = os.path.join(srcFolder, "select_userdata_modtime.sql")

col_data = ColDataUser()

sa_rows = []

with \
    SSHTunnelForwarder(
        (ssh_host, ssh_port),
        ssh_password=ssh_pass,
        ssh_username=ssh_user,
        remote_bind_address=(remote_bind_host, remote_bind_port)
    ) as server, \
        open(sqlPath) as sqlFile:

    # server.start()
    print server.local_bind_address
    conn = MySQLdb.connect(
        host=db_host,
        port=server.local_bind_port,
        user=db_user,
        passwd=db_pass,
        db=db_name)

    wpCols = OrderedDict(filter(lambda k_v: not k_v[1].get(
        'wp', {}).get('generated'), ColDataUser.get_wp_cols().items()))

    assert all([
        'Wordpress ID' in wpCols.keys(),
        wpCols['Wordpress ID'].get('wp', {}).get('key') == 'ID',
        wpCols['Wordpress ID'].get('wp', {}).get('final')
    ]), 'ColData should be configured correctly'
    userdata_select = ",\n\t\t\t".join([
        ("MAX(CASE WHEN um.meta_key = '%s' THEN um.meta_value ELSE \"\" END) as `%s`" if data[
         'wp']['meta'] else "u.%s as `%s`") % (data['wp']['key'], col)
        for col, data in wpCols.items()
    ])

    print sqlFile.read() % (userdata_select, '%susers' % tbl_prefix, '%susermeta' % tbl_prefix, '%stansync_updates' % tbl_prefix)
    sqlFile.seek(0)

    cursor = conn.cursor()
    cursor.execute(sqlFile.read() % (userdata_select, '%susers' % tbl_prefix,
                                     '%susermeta' % tbl_prefix, '%stansync_updates' % tbl_prefix))
    # headers = wpCols.keys() + ['ID', 'user_id', 'updated']
    headers = [i[0] for i in cursor.description]
    # print headers
    sa_rows = [headers] + list(cursor.fetchall())

# print sa_rows

saParser = CsvParseUser(
    cols=col_data.get_import_cols(),
    defaults=col_data.get_defaults()
)
if sa_rows:
    saParser.analyse_rows(sa_rows)

print saParser.tabulate()
