"""
module for detecting changes in a wordpress database
"""

import argparse
import io
import json
import os
import re
import time
import traceback
import zipfile
from collections import OrderedDict
from pprint import pprint

import yaml
from sshtunnel import SSHTunnelForwarder
from tabulate import tabulate

import MySQLdb
from woogenerator import MODULE_LOCATION, MODULE_PATH
from woogenerator.utils import (HtmlReporter, Registrar, SanitationUtils,
                                SeqUtils, TimeUtils)


def timediff(settings):
    """
    Return the difference in time since the start time according to settings.
    """
    return time.time() - settings.start_time


def main(settings):
    """
    Use settings object to load config file and detect changes in wordpress.
    """

    with open(settings.yaml_path) as stream:
        config = yaml.load(stream)

        if 'out_dir' in config.keys():
            settings.out_dir = config['out_dir']

        # mandatory
        # settings.merge_mode = config.get('merge_mode', 'sync')
        # settings.master_name = config.get('master_name', 'MASTER')
        # settings.slave_name = config.get('slave_name', 'SLAVE')
        # settings.default_last_sync = config.get('default_last_sync')
        settings.ssh_user = config.get('ssh_user')
        settings.ssh_pass = config.get('ssh_pass')
        settings.ssh_host = config.get('ssh_host')
        settings.ssh_port = config.get('ssh_port', 22)
        settings.remote_bind_host = config.get('remote_bind_host', '127.0.0.1')
        settings.remote_bind_port = config.get('remote_bind_port', 3306)
        settings.db_user = config.get('db_user')
        settings.db_pass = config.get('db_pass')
        settings.db_name = config.get('db_name')
        settings.tbl_prefix = config.get('tbl_prefix', '')

    #########################################
    # Set up directories
    #########################################

    file_suffix = "_test" if settings.test_mode else ""
    rep_path = os.path.join(settings.out_dir,
                            "changes_report%s.html" % file_suffix)

    #########################################
    # Download / Generate Slave Parser Object
    #########################################

    # settings.col_data = ColDataUser()

    # settings.sa_rows = []

    settings.since = "2016-03-13"

    with \
            SSHTunnelForwarder(
                (settings.ssh_host, settings.ssh_port),
                ssh_password=settings.ssh_pass,
                ssh_username=settings.ssh_user,
                remote_bind_address=(
                    settings.remote_bind_host,
                    settings.remote_bind_port)
            ) as server:

        conn = MySQLdb.connect(
            host='127.0.0.1',
            port=server.local_bind_port,
            user=settings.settings.db_user,
            passwd=settings.db_pass,
            db=settings.db_name)

        sql = ("SELECT user_id, time, changed, data FROM %stansync_updates" %
               settings.tbl_prefix) + (" WHERE time > '%s'" % settings.since
                                       if settings.since else "")

        cursor = conn.cursor()
        cursor.execute(sql)
        # headers = col_data.get_wp_cols().keys() + ['ID', 'user_id', 'updated']
        headers = [i[0] for i in cursor.description]

        # print headers
        change_data = [headers] + list(cursor.fetchall())

    print "formatting data..."

    def json2map(map_json):
        """
        Convert a map_obj into json.
        """
        try:
            sanitizer = SanitationUtils.coerce_unicode
            map_obj = json.loads(map_json)
            map_obj = OrderedDict(
                [((map_key, [sanitizer(map_value)])
                  if not isinstance(map_value, list) else
                  (map_key, map(sanitizer, map_value)))
                 for map_key, map_value in sorted(map_obj.items())
                 if any(map_value)])
            if not map_obj:
                raise Exception()
            return map_obj
            # return tabulate(map_obj, headers="keys", tablefmt="html")
        except:
            return map_json

    def map2table(map_obj):
        """
        Return a string table representation of a map_obj.
        """
        return tabulate(map_obj, headers="keys", tablefmt="html")

    change_data_fmt = change_data[:1]

    for user_id, c_time, changed, data in sorted(change_data[1:]):
        if user_id == 1:
            SanitationUtils.safe_print(changed)
        changed_map = json2map(changed)
        if not isinstance(changed_map, dict):
            continue
        if user_id == 1:
            for value in changed_map.values():
                for val in value:
                    SanitationUtils.safe_print(val)
        data_map = json2map(data)
        diff_map = SeqUtils.keys_not_in(
            data_map, changed_map.keys()) if isinstance(changed_map,
                                                        dict) else data_map
        change_data_fmt.append([
            user_id, c_time,
            "C:%s<br/>S:%s" % (map2table(changed_map), map2table(diff_map))
        ])

    print "creating report..."

    with io.open(rep_path, 'w+', encoding='utf-8') as res_file:
        reporter = HtmlReporter()

        group = HtmlReporter.Group('changes', 'Changes')
        group.add_section(
            HtmlReporter.Section(
                'wp_changes',
                'Wordpress Changes',
                "modifications made to wordpress" + (
                    "since %s" % settings.since if settings.since else ""),
                data=re.sub(
                    "<table>", "<table class=\"table table-striped\">",
                    tabulate(
                        change_data_fmt, headers="firstrow", tablefmt="html")),
                length=len(change_data_fmt)))

        res_file.write(SanitationUtils.coerce_unicode(reporter.get_document()))


def catch_main(settings=None):
    """
    Run the main function within a try statement and attempt to analyse failure.
    """
    if settings is None:
        settings = argparse.Namespace()

    settings.in_dir = "../input/"
    settings.out_dir = "../output/"
    settings.log_dir = "../logs/"
    settings.src_dir = MODULE_LOCATION
    settings.pkl_dir = "pickles/"

    os.chdir(MODULE_PATH)

    settings.import_name = TimeUtils.get_ms_timestamp()
    settings.start_time = time.time()

    settings.test_mode = True
    settings.rep_path = ''
    settings.yaml_path = os.path.join("merger_config.yaml")
    settings.m_fail_path = os.path.join(settings.out_dir, "act_fails.csv")
    settings.s_fail_path = os.path.join(settings.out_dir, "wp_fails.csv")
    settings.log_path = os.path.join(settings.log_dir,
                                     "log_%s.txt" % settings.import_name)
    settings.zip_path = os.path.join(settings.log_dir,
                                     "zip_%s.zip" % settings.import_name)
    settings.user_file = False
    settings.card_file = False
    settings.email_file = False
    settings.since_m = False
    settings.since_s = False

    try:
        main(settings)
    except SystemExit:
        exit()
    except:
        Registrar.register_error(traceback.format_exc())

    with io.open(settings.log_path, 'w+', encoding='utf8') as log_file:
        for source, messages in Registrar.get_message_items(1).items():
            print source
            log_file.writelines([SanitationUtils.coerce_unicode(source)])
            log_file.writelines([
                SanitationUtils.coerce_unicode(message) for message in messages
            ])
            for message in messages:
                pprint(message, indent=4, width=80, depth=2)

    #########################################
    # email reports
    #########################################

    files_to_zip = [
        settings.m_fail_path, settings.s_fail_path, settings.rep_path
    ]

    with zipfile.ZipFile(settings.zip_path, 'w') as zip_file:
        for file_to_zip in files_to_zip:
            try:
                os.stat(file_to_zip)
                zip_file.write(file_to_zip)
            except Exception as exc:
                if exc:
                    pass
        Registrar.register_message('wrote file %s' % settings.zip_path)


if __name__ == '__main__':
    catch_main()
