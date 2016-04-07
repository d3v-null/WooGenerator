# import csv
from collections import OrderedDict
import os
# import shutil
from utils import SanitationUtils, TimeUtils, listUtils
from matching import Match, MatchList, UsernameMatcher, CardMatcher, NocardEmailMatcher
from csvparse_flat import CSVParse_User, UsrObjList #, ImportUser
from contact_objects import ContactAddress
from coldata import ColData_User
from tabulate import tabulate
import re
import time
import yaml
import MySQLdb
from sshtunnel import SSHTunnelForwarder
import json

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

    #mandatory
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
resPath = os.path.join(outFolder, "changes_report%s.html" % fileSuffix)

#########################################
# Download / Generate Slave Parser Object
#########################################

colData = ColData_User()

saRows = []

since = "2016-03-01"
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

    sql = ("SELECT user_id, time, changed, data FROM %stansync_updates" % tbl_prefix) + ( " WHERE time > '%s'" % since if since else "")

    cursor = conn.cursor()
    cursor.execute(sql)
    # headers = colData.getWPCols().keys() + ['ID', 'user_id', 'updated']
    headers = [i[0] for i in cursor.description]

    # print headers
    changeData = [headers] + list(cursor.fetchall())

print "formatting data..."

def json2map(map_json):
    try:
        map_obj = json.loads(map_json)
        map_obj = OrderedDict([ \
            ((map_key, [SanitationUtils.anythingToAscii(map_value)]) if not isinstance(map_value, list) else (map_key, map(SanitationUtils.anythingToAscii, map_value))) \
            for map_key, map_value in sorted(map_obj.items()) if any (map_value) \
        ])
        if not map_obj:
            raise Exception()
        return map_obj
        # return tabulate(map_obj, headers="keys", tablefmt="html")
    except:
        return map_json

def map2table(map_obj):
    return tabulate(map_obj, headers="keys", tablefmt="html")

def subtractDicts(a, b):
    return listUtils.keysNotIn(a, b.keys())

changeDataFmt = [
    [user_id, time, json2map(changed), json2map(data)] for user_id, time, changed, data in sorted(changeData)
]

changeDataFmt = \
[["ID", "time", "changed", "not changed"]] + \
[
    [
        user_id, 
        time, 
        "C:%s<br/>S:%s" % (map2table(changed), map2table(subtractDicts(data, changed)) if isinstance(changed, dict) else data )
    ] \
    for rowcount, (user_id, time, changed, data) in enumerate(changeDataFmt[1:]) \
    if isinstance(changed, dict) 
]

print "creating report..."

with open(resPath, 'w+') as resFile:
        def writeSection(title, description, data, length = 0, html_class="results_section"):
            sectionID = SanitationUtils.makeSafeClass(title)
            description = "%s %s" % (str(length) if length else "No", description)
            resFile.write('<div class="%s">'% html_class )
            resFile.write('<a data-toggle="collapse" href="#%s" aria-expanded="true" data-target="#%s" aria-controls="%s">' % (sectionID, sectionID, sectionID))
            resFile.write('<h2>%s (%d)</h2>' % (title, length))
            resFile.write('</a>')
            resFile.write('<div class="collapse" id="%s">' % sectionID)
            resFile.write('<p class="description">%s</p>' % description)
            resFile.write('<p class="data">' )
            resFile.write( re.sub("<table>","<table class=\"table table-striped\">",data) )
            resFile.write('</p>')
            resFile.write('</div>')
            resFile.write('</div>')

        resFile.write('<!DOCTYPE html>')
        resFile.write('<html lang="en">')
        resFile.write('<head>')
        resFile.write("""
    <!-- Latest compiled and minified CSS -->
    <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.6/css/bootstrap.min.css" integrity="sha384-1q8mTJOASx8j1Au+a5WDVnPi2lkFfwwEAa8hDDdjZlpLegxhjVME1fgjWPGmkzs7" crossorigin="anonymous">

    <!-- Optional theme -->
    <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.6/css/bootstrap-theme.min.css" integrity="sha384-fLW2N01lMqjakBkx3l/M9EahuwpSfeNvV63J5ezn3uZzapT0u7EYsXMjQV+0En5r" crossorigin="anonymous">
    """)
        resFile.write('<body>')
        resFile.write('<div class="matching">')
        resFile.write('<h1>%s</h1>' % 'Wordpress Changes Report')

        writeSection(
            "Wordpress Changes", 
            "modifications made to wordpress" + ( "since %s" % since if since else ""),
            re.sub("<table>","<table class=\"table table-striped\">", 
                tabulate(changeDataFmt, headers="firstrow", tablefmt="html")
            ),
            length = len(changeDataFmt)
        )

        resFile.write('</div>')
        resFile.write("""
    <script src="https://ajax.googleapis.com/ajax/libs/jquery/2.1.4/jquery.min.js"></script>
    <script src="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.6/js/bootstrap.min.js" integrity="sha384-0mSbJDEHialfmuBBQP6A4Qrprq5OVfW37PRR3j5ELqxss1yVqOtnepnHVP9aJ7xS" crossorigin="anonymous"></script>
    """)
        resFile.write('</body>')
        resFile.write('</html>')
