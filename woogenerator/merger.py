"""Module for updating woocommerce and ACT databases from ACT import file."""

# import argparse
import io
import os
import re
import sys
import time
import traceback
import zipfile
import dill
from bisect import insort
from collections import OrderedDict
from pprint import pformat, pprint

import sshtunnel
import unicodecsv
from httplib2 import ServerNotFoundError
from requests.exceptions import ConnectionError, ConnectTimeout, ReadTimeout

import __init__
from woogenerator.client.user import UsrSyncClientSshAct, UsrSyncClientWP
from woogenerator.conf.namespace import (MatchNamespace, ParserNamespace,
                                         SettingsNamespaceUser,
                                         UpdateNamespace, init_settings)
from woogenerator.conf.parser import ArgumentParserUser
from woogenerator.duplicates import Duplicates
from woogenerator.matching import (CardMatcher, ConflictingMatchList,
                                   EmailMatcher, Match, NocardEmailMatcher,
                                   UsernameMatcher)
from woogenerator.parsing.user import UsrObjList
from woogenerator.syncupdate import SyncUpdateUsrApi
from woogenerator.utils import (HtmlReporter, ProgressCounter, Registrar,
                                SanitationUtils, TimeUtils)


def timediff(settings):
    """
    Return the difference in time since the start time according to settings.
    """
    return time.time() - settings.start_time

def populate_filter_settings(settings):
    if settings['do_filter']:
        # TODO: I don't think emails filter is actually working
        filter_files = {
            'users': settings.get('user_file'),
            'emails': settings.get('email_file'),
            'cards': settings.get('card_file'),
        }
        settings.filter_items = {}
        for key, filter_file in filter_files.items():
            if filter_file:
                try:
                    with open(os.path.join(settings.in_folder_full,
                                           filter_file)) as filter_file_obj:
                        settings.filter_items[key] = [
                            re.sub(r'\s*([^\s].*[^\s])\s*(?:\n)', r'\1', line)
                            for line in filter_file_obj
                        ]
                except IOError as exc:
                    SanitationUtils.safe_print(
                        "could not open %s file [%s] from %s" % (
                            key, filter_file, unicode(os.getcwd())))
                    raise exc
        if 'emails' in settings and settings.emails:
            if not 'emails' in settings.filter_items or not settings.filter_items['emails']:
                settings.filter_items['emails'] = []
            settings.filter_items['emails'].extend(settings.emails.split(','))
        if 'since_m' in settings:
            settings.filter_items['sinceM'] = TimeUtils.wp_strp_mktime(settings['since_m'])
        if 'since_s' in settings:
            settings.filter_items['sinceS'] = TimeUtils.wp_strp_mktime(settings['since_s'])
    else:
        settings.filter_items = None

def populate_slave_parsers(parsers, settings):
    """
    Populate the parsers for data from the slave database.
    """

    parsers.slave = settings.slave_parser_class(**settings.slave_parser_args)

    if settings['download_slave']:
        for host_key in [
                'ssh_address_or_host',
                'remote_bind_address'
        ]:
            try:
                sshtunnel.check_address(settings.slave_connect_params.get(host_key))
            except AttributeError:
                Registrar.register_error("invalid host: %s -> %s" % \
                                         (host_key, settings.get(host_key)))
            except Exception as exc:
                raise UserWarning("Host must be valid: %s [%s = %s]" % \
                                  (str(exc), host_key, repr(settings.get(host_key))))
        if Registrar.DEBUG_CLIENT:
            Registrar.register_message(
                "SSHTunnelForwarderParams: %s\nPyMySqlconnect_params: %s" % (
                    settings.slave_connect_params,
                    settings.slave_db_params
                )
            )

    if Registrar.DEBUG_PARSER:
        Registrar.register_message(
            "client_args: %s" % settings.slave_download_client_args
        )

    Registrar.register_progress("analysing slave user data")

    with settings.slave_download_client_class(**settings.slave_download_client_args) as client:
        client.analyse_remote(parsers.slave, data_path=settings.slave_path)

    return parsers

def export_slave_parser(parsers, settings):
    parsers.slave.get_obj_list().export_items(
        os.path.join(settings.in_folder_full, settings.s_x_name),
        settings.col_data_class.get_wp_import_col_names())

def populate_master_parsers(parsers, settings):
    """
    Populate the parsers for data from the slave database.
    """

    things_to_check = []
    if settings['download_master']:
        things_to_check.extend(['master_connect_params', 'master_db_params', 'fs_params'])
    else:
        things_to_check.extend(['master_path'])
    for thing in things_to_check:
        Registrar.register_message(
            "%s: %s" % (thing, getattr(settings, thing))
        )
        assert getattr(settings, thing), "settings must specify %s" % thing

    Registrar.register_message("master_parser_args:\n%s" % pformat(settings.master_parser_args))

    parsers.master = settings.master_parser_class(
        **settings.master_parser_args
    )

    Registrar.register_progress("analysing master user data")

    with settings.master_client_class(**settings.master_client_args) as client:
        client.analyse_remote(parsers.master, data_path=settings.master_path)

    if Registrar.DEBUG_UPDATE and settings.do_filter:
        Registrar.register_message(
            "master parser: \n%s",
            SanitationUtils.coerce_unicode(parsers.master.tabulate())
        )

    return parsers

def export_master_parser(parsers, settings):
    parsers.master.get_obj_list().export_items(
        os.path.join(settings.in_folder_full, settings.m_x_name),
        settings.col_data_class.get_act_import_col_names())

def do_match(matches, parsers, settings):
    """ for every username in slave, find its counterpart in master. """

    Registrar.register_progress("Processing matches")

    parsers.deny_anomalous('saParser.nousernames', parsers.slave.nousernames)

    username_matcher = UsernameMatcher()
    username_matcher.process_registers(parsers.slave.usernames,
                                       parsers.master.usernames)

    matches.deny_anomalous('usernameMatcher.slaveless_matches',
                           username_matcher.slaveless_matches)
    matches.deny_anomalous('usernameMatcher.duplicate_matches',
                           username_matcher.duplicate_matches)

    matches.duplicate['username'] = username_matcher.duplicate_matches

    matches.globals.add_matches(username_matcher.pure_matches)

    if Registrar.DEBUG_MESSAGE:
        Registrar.register_message(
            "username matches (%d pure)" % len(username_matcher.pure_matches)
        )

    if Registrar.DEBUG_DUPLICATES and username_matcher.duplicate_matches:
        Registrar.register_message(
            "username duplicates: %s" % len(username_matcher.duplicate_matches)
        )

    Registrar.register_progress("processing cards")

    # for every card in slave not already matched, check that it exists in
    # master

    parsers.deny_anomalous('maParser.nocards', parsers.master.nocards)

    card_matcher = CardMatcher(
        matches.globals.s_indices, matches.globals.m_indices
    )
    card_matcher.process_registers(parsers.slave.cards, parsers.master.cards)

    matches.deny_anomalous(
        'cardMatcher.duplicate_matches', card_matcher.duplicate_matches
    )
    matches.deny_anomalous(
        'cardMatcher.masterless_matches', card_matcher.masterless_matches
    )

    matches.duplicate['card'] = card_matcher.duplicate_matches

    matches.globals.add_matches(card_matcher.pure_matches)

    if Registrar.DEBUG_MESSAGE:
        Registrar.register_message(
            "card matches (%d pure)" % len(card_matcher.pure_matches)
        )
        # print repr(cardMatcher)

    if Registrar.DEBUG_DUPLICATES and card_matcher.duplicate_matches:
        Registrar.register_message(
            "card duplicates: %s" % len(card_matcher.duplicate_matches)
        )

    # #for every email in slave, check that it exists in master

    Registrar.register_progress("processing emails")

    parsers.deny_anomalous("saParser.noemails", parsers.slave.noemails)

    email_matcher = NocardEmailMatcher(
        matches.globals.s_indices, matches.globals.m_indices
    )

    email_matcher.process_registers(parsers.slave.nocards, parsers.master.emails)

    matches.new_master.add_matches(email_matcher.masterless_matches)
    matches.new_slave.add_matches(email_matcher.slaveless_matches)
    matches.globals.add_matches(email_matcher.pure_matches)
    matches.duplicate['email'] = email_matcher.duplicate_matches

    if Registrar.DEBUG_MESSAGE:
        Registrar.register_message(
            "email matches (%d pure)" % (len(email_matcher.pure_matches))
        )
        # print repr(emailMatcher)

    if Registrar.DEBUG_DUPLICATES and matches.duplicate['email']:
        Registrar.register_message(
            "email duplicates: %s" % len(matches.duplicate['email'])
        )

    # TODO: further sort emailMatcher

    return matches

def do_merge(matches, updates, parsers, settings):

    Registrar.register_progress("BEGINNING MERGE (%d)" % len(matches.globals))

    sync_cols = settings.col_data_class.get_sync_cols()

    if settings['reflect_only']:
        for data in sync_cols.values():
            if isinstance(data.get('sync'), bool):
                data.update(sync=False)
        # sync_cols = dict([
        #     (col, data['sync']) if isinstance(data.get('sync'), str) \
        #     else data.update(**{'sync':False})
        #     for col, data in sync_cols.items()
        # ])

    # print "sync_cols: %s" % pformat(sync_cols.items())

    if Registrar.DEBUG_PROGRESS:
        sync_progress_counter = ProgressCounter(len(matches.globals))

    for count, match in enumerate(matches.globals):
        if Registrar.DEBUG_PROGRESS:
            sync_progress_counter.maybe_print_update(count)
            # print "examining globalMatch %d" % count
            # # print SanitationUtils.safe_print( match.tabulate(tablefmt = 'simple'))
            # print repr(match)

        m_object = match.m_objects[0]
        s_object = match.s_objects[0]

        sync_update = SyncUpdateUsrApi(m_object, s_object)
        sync_update.update(sync_cols)

        # if(Registrar.DEBUG_MESSAGE):
        #     print "examining SyncUpdate"
        #     SanitationUtils.safe_print( syncUpdate.tabulate(tablefmt = 'simple'))

        if sync_update.m_updated and sync_update.m_deltas:
            insort(updates.delta_master, sync_update)

        if sync_update.s_updated and sync_update.s_deltas:
            insort(updates.delta_slave, sync_update)

        if not sync_update:
            continue

        if sync_update.s_updated:
            sync_slave_updates = sync_update.get_slave_updates()
            if 'E-mail' in sync_slave_updates:
                new_email = sync_slave_updates['E-mail']
                if new_email in parsers.slave.emails:
                    m_objects = [m_object]
                    s_objects = [s_object] + parsers.slave.emails[new_email]
                    SanitationUtils.safe_print("duplicate emails",
                                               m_objects, s_objects)
                    try:
                        matches.conflict['email'].add_match(
                            Match(m_objects, s_objects))
                    except Exception as exc:
                        SanitationUtils.safe_print(
                            ("something happened adding an email "
                             "conflict, new_email: %s ; exception: %s") %
                            (new_email, exc))
                    continue

        if not sync_update.important_static:
            if sync_update.m_updated and sync_update.s_updated:
                if sync_update.s_mod:
                    insort(updates.problematic, sync_update)
                    continue
            elif sync_update.m_updated and not sync_update.s_updated:
                insort(updates.nonstatic_master, sync_update)
                if sync_update.s_mod:
                    insort(updates.problematic, sync_update)
                    continue
            elif sync_update.s_updated and not sync_update.m_updated:
                insort(updates.nonstatic_slave, sync_update)
                if sync_update.s_mod:
                    insort(updates.problematic, sync_update)
                    continue

        if sync_update.s_updated or sync_update.m_updated:
            insort(updates.static, sync_update)
            if sync_update.m_updated and sync_update.s_updated:
                insort(updates.master, sync_update)
                insort(updates.slave, sync_update)
            if sync_update.m_updated and not sync_update.s_updated:
                insort(updates.master, sync_update)
            if sync_update.s_updated and not sync_update.m_updated:
                insort(updates.slave, sync_update)

    Registrar.register_progress("COMPLETED MERGE")
    return updates

def do_report(matches, updates, parsers, settings):
    Registrar.register_progress("Write Report")

    settings.repd_path = os.path.join(
        settings.out_folder_full,
        "%ssync_report_duplicate_%s.html" % (settings.file_prefix, settings.file_suffix))
    settings.w_pres_csv_path = os.path.join(
        settings.out_folder_full,
        "%ssync_report_%s_%s.csv" % \
            (settings.file_prefix, settings.slave_name, settings.file_suffix))
    settings.master_res_csv_path = os.path.join(
        settings.out_folder_full,
        "%ssync_report_%s_%s.csv" % \
            (settings.file_prefix, settings.master_name, settings.file_suffix))
    settings.master_delta_csv_path = os.path.join(
        settings.out_folder_full,
        "%sdelta_report_%s_%s.csv" % \
            (settings.file_prefix, settings.master_name, settings.file_suffix))
    settings.slave_delta_csv_path = os.path.join(
        settings.out_folder_full,
        "%sdelta_report_%s_%s.csv" % \
            (settings.file_prefix, settings.slave_name, settings.file_suffix))


    with io.open(settings.rep_path_full, 'w+', encoding='utf8') as res_file:

        repd_file = None
        if settings['process_duplicates']:
            repd_file = io.open(settings['repd_path'], 'w+', encoding='utf8')

        css = ""
        reporter = HtmlReporter(css=css)

        basic_cols = settings.col_data_class.get_basic_cols()
        address_cols = OrderedDict(basic_cols.items() + [
            ('address_reason', {}),
            ('Edited Address', {}),
            ('Edited Alt Address', {}),
        ])
        name_cols = OrderedDict(basic_cols.items() + [
            ('name_reason', {}),
            ('Edited Name', {}),
        ])
        csv_colnames = settings.col_data_class.get_col_names(
            OrderedDict(basic_cols.items() + settings.col_data_class.name_cols([
                'address_reason',
                'name_reason',
                'Edited Name',
                'Edited Address',
                'Edited Alt Address',
            ]).items()))

        help_instructions = (
            "<p>This is a detailed report of all the changes that will be "
            "made if this sync were to go ahead. </p>"
            "<h3>Field Changes</h3>"
            "<p>These reports show all the changes that will happen to "
            "the most important fields (default: email and role). "
            "The role field shows the new value for role, and the Delta role "
            "field shows the previous value for role if the value will be "
            "changed by the update. Same for email: the email field shows the "
            "new value for email, and the delta email field shows the old value "
            "for email if it will be changed in the update."
            "These are the most important changes to check. You should look to "
            "make sure that the value in the the Email and Role field is correct "
            "and that the value in the delta email or delta role field is incorrect. "
            "If an email or role is changed to the wrong value, it could stop the "
            "customer from being able to log in or purchase items correctly.</p>"
            "<h3>Matching Results</h3>"
            "<p>These reports show the results of the matching algorithm. </p>"
            "<p><strong>Perfect Matches</strong> show matches that were detected "
            "without ambiguity. </p>"
            "<p><strong>Cardmatcher.Masterless_Matches</strong> are instances where "
            "a record in {slave_name} is seen to have a {master_pkey} value that is "
            "that is not found in {master_name}. This could mean that the {master_name}"
            "record associated with that user has been deleted or badly merged.</p>"
            "<p><strong>Usernamematcher.Duplicate_Matches</strong> are instances where "
            "multiple records from a single database were found to have the same username "
            "which is certainly an indicator of erroneous data.</p>"
            "<p><strong>Usernamematcher.Slaveless_Matches</strong> are instances "
            "where a record in {master_name} has a username value that is not found in"
            "{slave_name}. This could be because the {slave_name} account was deleted.</p>"
            "<h3>Syncing Results</h3><p>Each of the items in these reports has "
            "the following sections:<br/><ul>"
            "<li><strong>Update Name</strong> - The primary keys of the records "
            "being synchronized ({master_pkey} and {slave_pkey}) which should "
            "be unique for any matched records.</li>"
            "<li><strong>OLD</strong> - The {master_name} and {slave_name} records "
            "before the sync.</li>"
            "<li><strong>INFO</strong> - Mostly information about mod times for "
            "debugging.</li>"
            "<li><strong>PROBLEMATIC CHANGES</strong> - instances where an important "
            "field has been changed. Important fields can be configured in coldata.py"
            "by changing the 'static' property.</li>"
            "<li><strong>CHANGES</strong> - all changes including problematic</li>"
            "<li><strong>NEW</strong> - the end result of all changed records after"
            "syncing</li>"
        ).format(
            master_name=settings.master_name,
            slave_name=settings.slave_name,
            master_pkey="MYOB Card ID",
            slave_pkey="WP ID"
        )

        summary_group = HtmlReporter.Group('summary_group', 'Summary')
        summary_group.add_section(
            HtmlReporter.Section(
                'instructions',
                title='Instructions',
                data=help_instructions
            )
        )
        reporter.add_group(summary_group)

        sanitizing_group = HtmlReporter.Group('sanitizing',
                                              'Sanitizing Results')

        if parsers.slave.bad_address:
            sanitizing_group.add_section(
                HtmlReporter.Section(
                    's_bad_addresses_list',
                    title='Bad %s Address List' % settings.slave_name.title(),
                    description='%s records that have badly formatted addresses'
                    % settings.slave_name,
                    data=UsrObjList(parsers.slave.bad_address.values()).tabulate(
                        cols=address_cols,
                        tablefmt='html', ),
                    length=len(parsers.slave.bad_address)))

        if parsers.slave.bad_name:
            sanitizing_group.add_section(
                HtmlReporter.Section(
                    's_bad_names_list',
                    title='Bad %s Names List' % settings.slave_name.title(),
                    description='%s records that have badly formatted names' %
                    settings.slave_name,
                    data=UsrObjList(parsers.slave.bad_name.values()).tabulate(
                        cols=name_cols,
                        tablefmt='html', ),
                    length=len(parsers.slave.bad_name)))
        if parsers.slave.bad_name or parsers.slave.bad_address:
            UsrObjList(parsers.slave.bad_name.values() + parsers.master.bad_address.
                       values()).export_items(settings['w_pres_csv_path'], csv_colnames)

        if parsers.master.bad_address:
            sanitizing_group.add_section(
                HtmlReporter.Section(
                    'm_bad_addresses_list',
                    title='Bad %s Address List' % settings.master_name.title(),
                    description='%s records that have badly formatted addresses'
                    % settings.master_name,
                    data=UsrObjList(parsers.master.bad_address.values()).tabulate(
                        cols=address_cols,
                        tablefmt='html', ),
                    length=len(parsers.master.bad_address)))

        if parsers.master.bad_name:
            sanitizing_group.add_section(
                HtmlReporter.Section(
                    'm_bad_names_list',
                    title='Bad %s Names List' % settings.master_name.title(),
                    description='%s records that have badly formatted names' %
                    settings.master_name,
                    data=UsrObjList(parsers.master.bad_name.values()).tabulate(
                        cols=name_cols,
                        tablefmt='html', ),
                    length=len(parsers.master.bad_name)))

        if parsers.master.bad_name or parsers.master.bad_address:
            UsrObjList(parsers.master.bad_name.values() + parsers.master.bad_address.values())\
                .export_items(settings['master_res_csv_path'], csv_colnames)

        reporter.add_group(sanitizing_group)

        if settings.do_sync and (updates.delta_master + updates.delta_slave):

            delta_group = HtmlReporter.Group('deltas', 'Field Changes')

            m_delta_list = UsrObjList(
                filter(None, [update.new_m_object
                              for update in updates.delta_master]))

            s_delta_list = UsrObjList(
                filter(None, [update.new_s_object
                              for update in updates.delta_slave]))

            delta_cols = settings.col_data_class.get_delta_cols()

            all_delta_cols = OrderedDict(
                settings.col_data_class.get_basic_cols().items()
                + settings.col_data_class.name_cols(
                    delta_cols.keys() + delta_cols.values()
                ).items())

            if m_delta_list:
                delta_group.add_section(
                    HtmlReporter.Section(
                        'm_deltas',
                        title='%s Changes List' % settings.master_name.title(),
                        description='%s records that have changed important fields'
                        % settings.master_name,
                        data=m_delta_list.tabulate(
                            cols=all_delta_cols, tablefmt='html'),
                        length=len(m_delta_list)))

            if s_delta_list:
                delta_group.add_section(
                    HtmlReporter.Section(
                        's_deltas',
                        title='%s Changes List' % settings.slave_name.title(),
                        description='%s records that have changed important fields'
                        % settings.slave_name,
                        data=s_delta_list.tabulate(
                            cols=all_delta_cols, tablefmt='html'),
                        length=len(s_delta_list)))

            reporter.add_group(delta_group)
            if m_delta_list:
                m_delta_list.export_items(
                    settings['master_delta_csv_path'],
                    settings.col_data_class.get_col_names(all_delta_cols))
            if s_delta_list:
                s_delta_list.export_items(
                    settings['slave_delta_csv_path'],
                    settings.col_data_class.get_col_names(all_delta_cols))

        if settings.do_sync:

            matching_group = HtmlReporter.Group('matching', 'Matching Results')
            matching_group.add_section(
                HtmlReporter.Section(
                    'perfect_matches',
                    **{
                        'title':
                        'Perfect Matches',
                        'description':
                        "%s records match well with %s" % (
                            settings.slave_name, settings.master_name),
                        'data':
                        matches.globals.tabulate(tablefmt="html"),
                        'length':
                        len(matches.globals)
                    }))

            match_list_instructions = {
                'cardMatcher.masterless_matches':
                '%s records do not have a corresponding CARD ID in %s (deleted?)'
                % (settings.slave_name, settings.master_name),
                'usernameMatcher.slaveless_matches':
                '%s records have no USERNAMEs in %s' %
                (settings.master_name, settings.slave_name),
            }

            for matchlist_type, match_list in matches.anomalous.items():
                if not match_list:
                    continue
                description = match_list_instructions.get(matchlist_type,
                                                          matchlist_type)
                if ('masterless' in matchlist_type or
                        'slaveless' in matchlist_type):
                    data = match_list.merge().tabulate(tablefmt="html")
                else:
                    data = match_list.tabulate(tablefmt="html")
                matching_group.add_section(
                    HtmlReporter.Section(
                        matchlist_type,
                        **{
                            # 'title': matchlist_type.title(),
                            'description': description,
                            'data': data,
                            'length': len(match_list)
                        }))

            # Registrar.register_progress("anomalous ParseLists: ")

            parse_list_instructions = {
                "saParser.noemails":
                "%s records have invalid emails" % settings.slave_name,
                "maParser.noemails":
                "%s records have invalid emails" % settings.master_name,
                "maParser.nocards":
                "%s records have no cards" % settings.master_name,
                "saParser.nousernames":
                "%s records have no username" % settings.slave_name
            }

            for parselist_type, parse_list in parsers.anomalous.items():
                description = parse_list_instructions.get(parselist_type,
                                                          parselist_type)
                usr_list = UsrObjList()
                for obj in parse_list.values():
                    usr_list.append(obj)

                data = usr_list.tabulate(tablefmt="html")

                matching_group.add_section(
                    HtmlReporter.Section(
                        parselist_type,
                        **{
                            # 'title': matchlist_type.title(),
                            'description': description,
                            'data': data,
                            'length': len(parse_list)
                        }))

            reporter.add_group(matching_group)

        if settings.do_sync:
            syncing_group = HtmlReporter.Group('sync', 'Syncing Results')

            syncing_group.add_section(
                HtmlReporter.Section(
                    (settings.master_name + "_updates"),
                    description=settings.master_name +
                    " items will be updated",
                    data='<hr>'.join([
                        update.tabulate(tablefmt="html")
                        for update in updates.master
                    ]),
                    length=len(updates.master)))

            syncing_group.add_section(
                HtmlReporter.Section(
                    (settings.slave_name + "_updates"),
                    description=settings.slave_name + " items will be updated",
                    data='<hr>'.join([
                        update.tabulate(tablefmt="html")
                        for update in updates.slave
                    ]),
                    length=len(updates.slave)))

            syncing_group.add_section(
                HtmlReporter.Section(
                    "updates.problematic",
                    description="items can't be merged because they are too dissimilar",
                    data='<hr>'.join([
                        update.tabulate(tablefmt="html")
                        for update in updates.problematic
                    ]),
                    length=len(updates.problematic)))

            reporter.add_group(syncing_group)

        if settings['process_duplicates']:

            dup_css = """
.highlight_old {color: red !important; }
.highlight_old {color: orange;}
.highlight_master {background: lightblue !important;}
.highlight_slave {background: lightpink !important;}
            """
            dup_reporter = HtmlReporter(css=dup_css)
            duplicate_group = HtmlReporter.Group('dup', 'Duplicate Results')

            basic_cols = settings.col_data_class.get_basic_cols()
            dup_cols = OrderedDict(basic_cols.items() + [
                # ('Create Date', {}),
                # ('Last Sale', {})
            ])

            # What we're doing here is analysing the duplicates we've seen so far, and
            # creating a list of all the potential objects to delete and WHY
            # they should be deleted.

            def fn_obj_source_is(target_source):
                """Return function that checks if object source equals target source."""

                def obj_source_is(object_data):
                    """Check if the object source equals target source."""

                    obj_source = object_data.get('source')
                    if obj_source and target_source == obj_source:
                        return True

                return obj_source_is

            def fn_user_older_than_wp(wp_time):
                """Return function ot check user is older than wp_time."""
                wp_time_obj = TimeUtils.wp_strp_mktime(wp_time)
                assert wp_time_obj, "should be valid time struct: %s" % wp_time

                def user_older_than(user_data):
                    """Determine if user is older than wp_time."""
                    if fn_obj_source_is(settings.master_name)(user_data):
                        assert hasattr(user_data, 'act_last_transaction'), \
                            "%s user should have act_last_transaction attr: %s, %s, source: %s" % (
                                settings.master_name,
                                type(user_data),
                                SanitationUtils.coerce_ascii(user_data),
                                user_data.get('source'))
                        user_time_obj = user_data.act_last_transaction
                    else:
                        user_time_obj = user_data.last_modtime
                    return user_time_obj < wp_time_obj

                return user_older_than

            duplicates = Duplicates()

            for duplicate_type, duplicate_matchlist in matches.duplicate.items(
            ):
                print "checking duplicates of type %s" % duplicate_type
                print "len(duplicate_matchlist) %s" % len(duplicate_matchlist)
                for match in duplicate_matchlist:
                    if match.m_len <= 1:
                        continue
                        # only care about master duplicates at the moment
                    duplicate_objects = list(match.m_objects)
                    duplicates.add_conflictors(duplicate_objects,
                                               duplicate_type)

            address_duplicates = {}
            for address, objects in parsers.master.addresses.items():
                # print "analysing address %s " % address
                # for object_data in objects:
                # print " -> associated object: %s" % object_data
                if len(objects) > 1:
                    # if there are more than one objects associated with an address,
                    # add to the duplicate addresses report
                    address_duplicates[address] = objects
                    duplicates.add_conflictors(
                        objects, "address", weighting=0.1)

            for object_data in parsers.master.objects.values():
                if fn_user_older_than_wp(settings['old_threshold'])(object_data):
                    details = TimeUtils.wp_time_to_string(
                        object_data.act_last_transaction)
                    duplicates.add_conflictor(
                        object_data, "last_transaction_old", 0.5, details)
                elif fn_user_older_than_wp(settings['oldish_threshold'])(object_data):
                    details = TimeUtils.wp_time_to_string(
                        object_data.act_last_transaction)
                    duplicates.add_conflictor(
                        object_data, "last_transaction_oldish", 0.2, details)

            highlight_rules_master_slave = [
                ('highlight_master', fn_obj_source_is(settings.master_name)),
                ('highlight_slave', fn_obj_source_is(settings.slave_name))
            ]

            highlight_rules_old = [
                ('highlight_oldish', fn_user_older_than_wp(settings['oldish_threshold'])),
                ('highlight_old', fn_user_older_than_wp(settings['old_threshold']))
            ]

            highlight_rules_all = highlight_rules_master_slave + highlight_rules_old

            # if Registrar.DEBUG_DUPLICATES:
            # print duplicates.tabulate({}, tablefmt='plain')
            if duplicates:
                duplicate_group.add_section(
                    HtmlReporter.Section('all duplicates', **{
                        'title':
                        'All Duplicates',
                        'description':
                        "%s records are involved in duplicates" %
                        settings.master_name,
                        'data':
                        duplicates.tabulate(
                            dup_cols,
                            tablefmt='html',
                            highlight_rules=highlight_rules_all),
                        'length':
                        len(duplicates)
                    }))

            email_conflict_data = matches.conflict['email'].tabulate(
                cols=dup_cols,
                tablefmt="html",
                highlight_rules=highlight_rules_all)
            duplicate_group.add_section(
                HtmlReporter.Section(
                    "email conflicts",
                    **{
                        # 'title': matchlist_type.title(),
                        'description': "email conflicts",
                        'data': email_conflict_data,
                        'length': len(matches.conflict['email'])
                    }))

            email_duplicate_data = matches.duplicate['email'].tabulate(
                tablefmt="html", highlight_rules=highlight_rules_all)
            if matches.duplicate['email']:
                duplicate_group.add_section(
                    HtmlReporter.Section('email_duplicates', **{
                        'title':
                        'Email Duplicates',
                        'description':
                        "%s records match with multiple records in %s on email"
                        % (settings.slave_name, settings.master_name),
                        'data':
                        email_duplicate_data,
                        'length':
                        len(matches.duplicate['email'])
                    }))

            match_list_instructions = {
                'cardMatcher.duplicate_matches':
                '%s records have multiple CARD IDs in %s' %
                (settings.slave_name, settings.master_name),
                'usernameMatcher.duplicate_matches':
                '%s records have multiple USERNAMEs in %s' %
                (settings.slave_name, settings.master_name)
            }

            for matchlist_type, match_list in matches.anomalous.items():
                if not match_list:
                    continue
                description = match_list_instructions.get(matchlist_type,
                                                          matchlist_type)
                if ('masterless' in matchlist_type or
                        'slaveless' in matchlist_type):
                    data = match_list.merge().tabulate(tablefmt="html")
                else:
                    data = match_list.tabulate(
                        tablefmt="html", highlight_rules=highlight_rules_all)
                matching_group.add_section(
                    HtmlReporter.Section(
                        matchlist_type,
                        **{
                            # 'title': matchlist_type.title(),
                            'description': description,
                            'data': data,
                            'length': len(match_list)
                        }))

            if address_duplicates:

                print "there are address duplicates"
                duplicate_group.add_section(
                    HtmlReporter.Section(
                        'address_duplicates',
                        title='Duplicate %s Addresses' %
                        settings.master_name.title(),
                        description='%s addresses that appear in multiple records'
                        % settings.master_name,
                        data="<br/>".join([
                            "<h4>%s</h4><p>%s</p>" % (address, UsrObjList(
                                objects).tabulate(
                                    cols=dup_cols,
                                    tablefmt='html',
                                    highlight_rules=highlight_rules_old))
                            for address, objects in address_duplicates.items()
                        ]),
                        length=len(address_duplicates)))
            dup_reporter.add_group(duplicate_group)
            repd_file.write(dup_reporter.get_document_unicode())

        res_file.write(reporter.get_document_unicode())

def pickle_state(matches=None, updates=None, parsers=None, settings=None, progress=None):
    Registrar.register_progress("pickling updates")

    pickle_obj = (matches, updates, parsers, settings, progress)

    with open(settings.pickle_path_full, 'w') as pickle_file:
        dill.dump(pickle_obj, pickle_file)

    print "state saved to %s" % settings.pickle_path_full

def unpickle_state(settings):
    with open(settings.pickle_path_full) as pickle_file:
        pickle_obj = dill.load(pickle_file)
        matches, updates, parsers, settings, progress = pickle_obj

    if progress == 'report':
        do_report(matches, updates, parsers, settings)
        do_updates(updates, settings)

def output_failures(failures, file_path):
    """
    Output a list of lists of failures as a csv file to the path specified.
    """
    with open(file_path, 'w+') as out_file:
        for failure in failures:
            Registrar.register_error(failure)
        dictwriter = unicodecsv.DictWriter(
            out_file,
            fieldnames=[
                'update', 'master', 'slave', 'mchanges', 'schanges',
                'exception'
            ],
            extrasaction='ignore', )
        dictwriter.writerows(failures)
        print "WROTE FILE: ", file_path

def do_updates(updates, settings):
    all_updates = updates.static
    if settings.do_problematic:
        all_updates += updates.problematic

    Registrar.register_progress("Updating databases (%d)" % len(all_updates))

    master_failures = []
    slave_failures = []

    if all_updates:
        Registrar.register_progress("UPDATING %d RECORDS" % len(all_updates))

        if settings['ask_before_update']:
            try:
                input(
                    "Please read reports and press Enter to continue or ctrl-c to stop..."
                )
            except SyntaxError:
                pass

        if Registrar.DEBUG_PROGRESS:
            update_progress_counter = ProgressCounter(len(all_updates))

        # with UsrSyncClientSshAct(
        #     settings.master_connect_params,
        #     settings.master_db_params,
        #     settings.fs_params
        # ) as master_client, UsrSyncClientWP(settings.slave_wp_api_params) as slave_client:
        with \
        settings.master_client_class(settings.master_client_args) as master_client, \
        settings.slave_upload_client_class(settings.slave_upload_client_args) as slave_client:

            for count, update in enumerate(all_updates):
                if Registrar.DEBUG_PROGRESS:
                    update_progress_counter.maybe_print_update(count)
                if Registrar.DEBUG_UPDATE:
                    Registrar.register_message(
                        "performing update: \n%s",
                        SanitationUtils.coerce_unicode(update.tabulate())
                    )
                if settings['update_master'] and update.m_updated:
                    try:
                        update.update_master(master_client)
                    except Exception as exc:
                        master_failures.append({
                            'update':
                            update,
                            'master':
                            SanitationUtils.coerce_unicode(
                                update.new_m_object),
                            'slave':
                            SanitationUtils.coerce_unicode(
                                update.new_s_object),
                            'mchanges':
                            SanitationUtils.coerce_unicode(
                                update.get_master_updates()),
                            'schanges':
                            SanitationUtils.coerce_unicode(
                                update.get_slave_updates()),
                            'exception':
                            repr(exc)
                        })
                        # if Registrar.DEBUG_UPDATE:
                        #     import pudb; pudb.set_trace()
                        Registrar.register_error(
                            "ERROR UPDATING MASTER (%s): %s\n%s" %
                            (update.master_id, repr(exc),
                             traceback.format_exc()))

                        # continue
                if settings['update_slave'] and update.s_updated:
                    try:
                        update.update_slave(slave_client)
                    except Exception as exc:
                        slave_failures.append({
                            'update':
                            update,
                            'master':
                            SanitationUtils.coerce_unicode(
                                update.new_m_object),
                            'slave':
                            SanitationUtils.coerce_unicode(
                                update.new_s_object),
                            'mchanges':
                            SanitationUtils.coerce_unicode(
                                update.get_master_updates()),
                            'schanges':
                            SanitationUtils.coerce_unicode(
                                update.get_slave_updates()),
                            'exception':
                            repr(exc)
                        })
                        # if Registrar.DEBUG_UPDATE:
                        #     import pudb; pudb.set_trace()
                        Registrar.register_error(
                            "ERROR UPDATING SLAVE (%s): %s\n%s" %
                            (update.slave_id, repr(exc),
                             traceback.format_exc()))

    output_failures(master_failures, settings.m_fail_path_full)
    output_failures(slave_failures, settings.s_fail_path_full)

def main(override_args=None, settings=None):
    """
    Use settings object to load config file and detect changes in wordpress.
    """
    # DONE: fix too-many-branches,too-many-locals
    # DONE: implement override_args

    settings = init_settings(override_args, settings, ArgumentParserUser)

    if hasattr(settings, 'pickle_file') and getattr(settings, 'pickle_file'):
        unpickle_state(settings)

    ### SET UP DIRECTORIES ###

    for path in (
            settings.in_folder_full, settings.out_folder_full,
            settings.log_folder_full, settings.pickle_folder_full
    ):
        if not os.path.exists(path):
            os.mkdir(path)

    ### PROCESS OTHER CONFIG ###

    #########################################
    # Prepare Filter Data
    #########################################

    Registrar.register_progress("Prepare Filter Data")

    populate_filter_settings(settings)

    if Registrar.DEBUG_UPDATE and settings.do_filter:
        Registrar.register_message("filter_items: %s" % settings.filter_items)

    parsers = ParserNamespace()
    parsers = populate_slave_parsers(parsers, settings)
    export_slave_parser(parsers, settings)
    parsers = populate_master_parsers(parsers, settings)
    # export_master_parser(parsers, settings)

    matches = MatchNamespace()
    matches.conflict['email'] = ConflictingMatchList(index_fn=EmailMatcher.email_index_fn)
    updates = UpdateNamespace()

    if settings['do_sync']:
        matches = do_match(matches, parsers, settings)
        updates = do_merge(matches, updates, parsers, settings)

    pickle_state(matches, updates, parsers, settings, 'report')

    do_report(matches, updates, parsers, settings)

    do_updates(updates, settings)

def catch_main(override_args=None):
    """
    Run the main function within a try statement and attempt to analyse failure.
    """

    settings = SettingsNamespaceUser()

    status = 0

    try:
        main(settings=settings, override_args=override_args)
    except SystemExit:
        exit()
    except (ReadTimeout, ConnectionError, ConnectTimeout, ServerNotFoundError):
        status = 69  # service unavailable
        Registrar.register_error(traceback.format_exc())
    except IOError:
        status = 74
        print "cwd: %s" % os.getcwd()
        Registrar.register_error(traceback.format_exc())
    except UserWarning:
        status = 65
        Registrar.register_error(traceback.format_exc())
    else:
        status = 1
        Registrar.register_error(traceback.format_exc())

    with io.open(settings.log_path_full, 'w+', encoding='utf8') as log_file:
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
        settings.m_fail_path_full, settings.s_fail_path_full, settings.rep_path_full
    ]

    with zipfile.ZipFile(settings.zip_path_full, 'w') as zip_file:
        for file_to_zip in files_to_zip:
            try:
                os.stat(file_to_zip)
                zip_file.write(file_to_zip)
            except Exception as exc:
                if exc:
                    pass
        Registrar.register_message('wrote file %s' % settings.zip_path_full)

    sys.exit(status)

if __name__ == '__main__':
    catch_main()
