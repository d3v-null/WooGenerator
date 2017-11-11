import csv
# import re
from collections import OrderedDict
import os
import time
# from itertools import chain
from woogenerator.utils import SeqUtils, SanitationUtils, UnicodeDictWriter
from parsing.abstract import Registrar
from parsing.woo import CsvParseTT, CsvParseVT, CsvParseWoo, WooObjList
from parsing.myo import CsvParseMyo
from parsing.dyn import CsvParseDyn
from parsing.flat import CsvParseSpecial
from coldata import ColDataWoo
import yaml
import MySQLdb
from sshtunnel import SSHTunnelForwarder

### DEFAULT CONFIG ###

in_folder = "../input/"
out_folder = "../output/"
log_folder = "../logs/"
src_folder = "../source"

yaml_path = "generator_config.yaml"

thumbsize = 1920, 1200

import_name = time.strftime("%Y-%m-%d %H:%M:%S")

### Process YAML file ###

with open(yaml_path) as stream:
    config = yaml.load(stream)
    # overrides
    if 'in_folder' in config.keys():
        in_folder = config['in_folder']
    if 'out_folder' in config.keys():
        out_folder = config['out_folder']
    if 'log_folder' in config.keys():
        log_folder = config['log_folder']

    # mandatory
    web_folder = config.get('web_folder')
    img_folder_glb = config.get('img_folder_glb')
    myo_schemas = config.get('myo_schemas')
    woo_schemas = config.get('woo_schemas')
    taxo_depth = config.get('taxo_depth')
    item_depth = config.get('item_depth')

    # optional
    fallback_schema = config.get('fallback_schema')
    fallback_variant = config.get('fallback_variant')
    img_folder_extra = config.get('img_folder_extra')

    ssh_user = config.get('ssh_user')
    ssh_pass = config.get('ssh_pass')
    ssh_host = config.get('ssh_host')
    ssh_port = config.get('ssh_port', 22)
    remote_bind_host = config.get('remote_bind_host', '127.0.0.1')
    remote_bind_port = config.get('remote_bind_port', 3306)
    db_user = config.get('db_user')
    db_pass = config.get('db_pass')
    db_name = config.get('db_name')
    tbl_prefix = config.get('tbl_prefix', '')

# mandatory params
assert all([in_folder, out_folder, log_folder, web_folder, img_folder_glb,
            woo_schemas, myo_schemas, taxo_depth, item_depth])

gen_path = os.path.join(in_folder, 'generator.csv')
dprc_path = os.path.join(in_folder, 'DPRC.csv')
dprp_path = os.path.join(in_folder, 'DPRP.csv')
spec_path = os.path.join(in_folder, 'specials.csv')
us_path = os.path.join(in_folder, 'US.csv')
xs_path = os.path.join(in_folder, 'XS.csv')
img_folder = [img_folder_glb]

sql_path = os.path.join(src_folder, 'select_productdata.sql')

col_data = ColDataWoo()

sql_run = True

if sql_run:
    with \
        SSHTunnelForwarder(
            (ssh_host, ssh_port),
            ssh_password=ssh_pass,
            ssh_username=ssh_user,
            remote_bind_address=(remote_bind_host, remote_bind_port)
        ) as server,\
            open(sql_path) as sqlFile:
        # server.start()
        print server.local_bind_address
        conn = MySQLdb.connect(
            host='127.0.0.1',
            port=server.local_bind_port,
            user=db_user,
            passwd=db_pass,
            db=db_name)

        wpCols = col_data.get_wp_sql_cols()

        assert all([
            'ID' in wpCols.keys(),
            wpCols['ID'].get('wp', {}).get('key') == 'ID',
        ]), 'ColData should be configured correctly'
        postdata_select = ",\n\t".join([
            ("MAX(CASE WHEN pm.meta_key = '%s' THEN pm.meta_value ELSE \"\" END) as `%s`"
                if data['wp']['meta']
                else "p.%s as `%s`") % (data['wp']['key'], col)
            for col, data in wpCols.items()
        ])

        cursor = conn.cursor()

        sql = sqlFile.read() \
            % (postdata_select, '%sposts' % tbl_prefix, '%spostmeta' % tbl_prefix,)
        print sql

        cursor.execute(
            sql
        )
        # headers = col_data.get_wp_sql_cols().keys() + ['ID', 'user_id', 'updated']
        headers = [i[0] for i in cursor.description]
        # print headers
        sqlRows = [headers] + list(cursor.fetchall())

print sqlRows

sql_parser = CsvParseTT

sql_parser = CsvParseTT(
    cols=col_data.get_import_cols(),
    defaults=col_data.get_defaults()
)
if sqlRows:
    sql_parser.analyse_rows(sqlRows)

print sql_parser.products
