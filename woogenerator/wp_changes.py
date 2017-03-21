# import csv
from collections import OrderedDict
import os
# import shutil
from utils import SanitationUtils, TimeUtils, listUtils, HtmlReporter
from matching import Match, MatchList, UsernameMatcher, CardMatcher, NocardEmailMatcher
from parsing.flat import CSVParse_User, UsrObjList  # , ImportUser
from contact_objects import ContactAddress
import codecs
from coldata import ColData_User
from tabulate import tabulate
import re
import time
import yaml
import MySQLdb
from sshtunnel import SSHTunnelForwarder
import json
import io

importName = time.strftime("%Y-%m-%d %H:%M:%S")
start_time = time.time()


def timediff():
    return time.time() - start_time

### DEFAULT CONFIG ###
outFolder = "../output/"
yamlPath = "merger_config.yaml"
testMode = False

with open(yamlPath) as stream:
    config = yaml.load(stream)

    if 'outFolder' in config.keys():
        outFolder = config['outFolder']

    # mandatory
    merge_mode = config.get('merge_mode', 'sync')
    MASTER_NAME = config.get('master_name', 'MASTER')
    SLAVE_NAME = config.get('slave_name', 'SLAVE')
    DEFAULT_LAST_SYNC = config.get('default_last_sync')
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

#########################################
# Set up directories
#########################################

fileSuffix = "_test" if testMode else ""
repPath = os.path.join(outFolder, "changes_report%s.html" % fileSuffix)

#########################################
# Download / Generate Slave Parser Object
#########################################

colData = ColData_User()

saRows = []

since = "2016-03-13"
# since = ""

with \
        SSHTunnelForwarder(
            (ssh_host, ssh_port),
            ssh_password=ssh_pass,
            ssh_username=ssh_user,
            remote_bind_address=(remote_bind_host, remote_bind_port)
        ) as server:

    conn = MySQLdb.connect(
        host='127.0.0.1',
        port=server.local_bind_port,
        user=db_user,
        passwd=db_pass,
        db=db_name)

    sql = ("SELECT user_id, time, changed, data FROM %stansync_updates" %
           tbl_prefix) + (" WHERE time > '%s'" % since if since else "")

    cursor = conn.cursor()
    cursor.execute(sql)
    # headers = colData.getWPCols().keys() + ['ID', 'user_id', 'updated']
    headers = [i[0] for i in cursor.description]

    # print headers
    changeData = [headers] + list(cursor.fetchall())

print "formatting data..."


def json2map(map_json):
    try:
        sanitizer = SanitationUtils.coerceUnicode
        map_obj = json.loads(map_json)
        map_obj = OrderedDict([
            ((map_key, [sanitizer(map_value)])
                if not isinstance(map_value, list)
                else (map_key, map(sanitizer, map_value)))
            for map_key, map_value in sorted(map_obj.items()) if any(map_value)
        ])
        if not map_obj:
            raise Exception()
        return map_obj
        # return tabulate(map_obj, headers="keys", tablefmt="html")
    except:
        return map_json


def map2table(map_obj):
    return tabulate(map_obj, headers="keys", tablefmt="html")

changeDataFmt = changeData[:1]

for user_id, c_time, changed, data in sorted(changeData[1:]):
    if user_id == 1:
        SanitationUtils.safePrint(changed)
    changedMap = json2map(changed)
    if not isinstance(changedMap, dict):
        continue
    if user_id == 1:
        for value in changedMap.values():
            for val in value:
                SanitationUtils.safePrint(val)
    dataMap = json2map(data)
    diffMap = listUtils.keysNotIn(dataMap, changedMap.keys()) if isinstance(
        changedMap, dict) else dataMap
    changeDataFmt.append([
        user_id,
        c_time,
        "C:%s<br/>S:%s" % (map2table(changedMap), map2table(diffMap))
    ])

print "creating report..."

with io.open(repPath, 'w+', encoding='utf-8') as resFile:
    reporter = HtmlReporter()

    group = HtmlReporter.Group('changes', 'Changes')
    group.addSection(
        HtmlReporter.Section(
            'wp_changes',
            'Wordpress Changes',
            "modifications made to wordpress" +
            ("since %s" % since if since else ""),
            data=re.sub("<table>", "<table class=\"table table-striped\">",
                        tabulate(changeDataFmt, headers="firstrow",
                                   tablefmt="html")
                        ),
            length=len(changeDataFmt)
        )
    )

    resFile.write(SanitationUtils.coerceUnicode(reporter.getDocument()))
