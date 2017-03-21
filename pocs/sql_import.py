import csv
# import re
from collections import OrderedDict
import os
import time
# from itertools import chain
from utils import listUtils, SanitationUtils, UnicodeDictWriter
from parsing.abstract import Registrar
from parsing.woo import CSVParse_TT, CSVParse_VT, CSVParse_Woo, WooObjList
from parsing.myo import CSVParse_MYO
from parsing.dyn import CSVParse_Dyn
from parsing.flat import CSVParse_Special
from coldata import ColData_Woo
import yaml
import MySQLdb
from sshtunnel import SSHTunnelForwarder

### DEFAULT CONFIG ###

in_folder = "../input/"
out_folder = "../output/"
logFolder = "../logs/"
srcFolder = "../source"

yamlPath = "generator_config.yaml"

thumbsize = 1920, 1200

import_name = time.strftime("%Y-%m-%d %H:%M:%S")

### Process YAML file ###

with open(yamlPath) as stream:
    config = yaml.load(stream)
    # overrides
    if 'in_folder' in config.keys():
        in_folder = config['in_folder']
    if 'out_folder' in config.keys():
        out_folder = config['out_folder']
    if 'logFolder' in config.keys():
        logFolder = config['logFolder']

    # mandatory
    webFolder = config.get('webFolder')
    imgFolder_glb = config.get('imgFolder_glb')
    myo_schemas = config.get('myo_schemas')
    woo_schemas = config.get('woo_schemas')
    taxoDepth = config.get('taxoDepth')
    itemDepth = config.get('itemDepth')

    # optional
    fallback_schema = config.get('fallback_schema')
    fallback_variant = config.get('fallback_variant')
    imgFolder_extra = config.get('imgFolder_extra')

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
assert all([in_folder, out_folder, logFolder, webFolder, imgFolder_glb,
            woo_schemas, myo_schemas, taxoDepth, itemDepth])

genPath = os.path.join(in_folder, 'generator.csv')
dprcPath = os.path.join(in_folder, 'DPRC.csv')
dprpPath = os.path.join(in_folder, 'DPRP.csv')
specPath = os.path.join(in_folder, 'specials.csv')
usPath = os.path.join(in_folder, 'US.csv')
xsPath = os.path.join(in_folder, 'XS.csv')
imgFolder = [imgFolder_glb]

sqlPath = os.path.join(srcFolder, 'select_productdata.sql')

col_data = ColData_Woo()

sql_run = True

if sql_run:
    with \
        SSHTunnelForwarder(
            (ssh_host, ssh_port),
            ssh_password=ssh_pass,
            ssh_username=ssh_user,
            remote_bind_address=(remote_bind_host, remote_bind_port)
        ) as server,\
            open(sqlPath) as sqlFile:
        # server.start()
        print server.local_bind_address
        conn = MySQLdb.connect(
            host='127.0.0.1',
            port=server.local_bind_port,
            user=db_user,
            passwd=db_pass,
            db=db_name)

        wpCols = col_data.get_wp_cols()

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
        # headers = col_data.get_wp_cols().keys() + ['ID', 'user_id', 'updated']
        headers = [i[0] for i in cursor.description]
        # print headers
        sqlRows = [headers] + list(cursor.fetchall())

print sqlRows

sqlParser = CSVParse_TT

sqlParser = CSVParse_TT(
    cols=col_data.get_import_cols(),
    defaults=col_data.get_defaults()
)
if sqlRows:
    sqlParser.analyse_rows(sqlRows)

print sqlParser.products
