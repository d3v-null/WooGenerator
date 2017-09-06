"""Module for updating woocommerce and ACT databases from ACT import file."""

import io
import os
import re
import sys
import time
import traceback
import zipfile
from bisect import insort
from pprint import pformat, pprint

import dill
import sshtunnel
from httplib2 import ServerNotFoundError
from requests.exceptions import ConnectionError, ConnectTimeout, ReadTimeout

from six.moves import input
from woogenerator.conf.namespace import (MatchNamespace, ParserNamespace,
                                         ResultsNamespace,
                                         SettingsNamespaceUser,
                                         UpdateNamespace, init_dirs,
                                         init_settings)
from woogenerator.conf.parser import ArgumentParserUser
from woogenerator.matching import (CardMatcher, ConflictingMatchList,
                                   EmailMatcher, Match, NocardEmailMatcher,
                                   UsernameMatcher)
from woogenerator.syncupdate import SyncUpdateUsrApi
from woogenerator.utils import (ProgressCounter, Registrar, SanitationUtils,
                                TimeUtils)
from woogenerator.utils.reporter import (ReporterNamespace, do_delta_group,
                                         do_duplicates_group,
                                         do_duplicates_summary_group,
                                         do_failures_group,
                                         do_main_summary_group,
                                         do_matches_group,
                                         do_matches_summary_group,
                                         do_post_summary_group,
                                         do_sanitizing_group,
                                         do_successes_group, do_sync_group)

BORING_EXCEPTIONS = [ConnectionError, ConnectTimeout, ReadTimeout]

def timediff(settings):
    """Return the time delta since the start time according to settings."""
    return time.time() - settings.start_time

def populate_filter_settings(settings):
    """Populate the settings for filtering input data."""

    Registrar.register_progress("Prepare Filter Data")

    if settings['do_filter']:
        filter_files = {
            'users': settings.get('user_file'),
            'emails': settings.get('email_file'),
            'cards': settings.get('card_file'),
        }
        settings.filter_items = {}
        for key, filter_file in filter_files.items():
            if filter_file:
                try:
                    with open(os.path.join(settings.in_dir_full,
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
        if settings.get('filter_emails'):
            if not settings.filter_items.get('emails'):
                settings.filter_items['emails'] = []
            settings.filter_items['emails'].extend(settings.get('filter_emails').split(','))
        if settings.get('ignore_cards'):
            if not settings.filter_items.get('ignore_cards'):
                settings.filter_items['ignore_cards'] = []
            settings.filter_items['ignore_cards'].extend(settings.get('ignore_cards').split(','))
        if settings.get('since_m'):
            settings.filter_items['sinceM'] = TimeUtils.wp_strp_mktime(settings['since_m'])
        if settings.get('since_s'):
            settings.filter_items['sinceS'] = TimeUtils.wp_strp_mktime(settings['since_s'])

        for key in ['emails', 'cards', 'users']:
            if key in settings.filter_items:
                settings.filter_items[key] = [
                    SanitationUtils.normalize_val(value) \
                    for value in settings.filter_items[key]
                ]

    else:
        settings.filter_items = None

    if Registrar.DEBUG_UPDATE and settings.do_filter:
        Registrar.register_message("filter_items: %s" % settings.filter_items)

def populate_slave_parsers(parsers, settings):
    """Populate the parsers for data from the slave database."""
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

    if Registrar.DEBUG_UPDATE and settings.do_filter:
        Registrar.register_message(
            "slave parser: \n%s" %
            SanitationUtils.coerce_unicode(parsers.slave.tabulate())
        )

    return parsers

def export_slave_parser(parsers, settings):
    """Export slave parser to disk."""
    parsers.slave.get_obj_list().export_items(
        settings.slave_path,
        settings.col_data_class.get_wp_import_col_names())

def populate_master_parsers(parsers, settings):
    """Populate the parsers for data from the slave database."""
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

    with settings.master_download_client_class(**settings.master_download_client_args) as client:
        client.analyse_remote(parsers.master, data_path=settings.master_path)

    if Registrar.DEBUG_UPDATE and settings.do_filter:
        Registrar.register_message(
            "master parser: \n%s" %
            SanitationUtils.coerce_unicode(parsers.master.tabulate())
        )

    return parsers

def export_master_parser(parsers, settings):
    """Export the Masater parser to disk."""
    parsers.master.get_obj_list().export_items(
        os.path.join(settings.in_dir_full, settings.m_x_name),
        settings.col_data_class.get_act_import_col_names())

def do_match(parsers, settings):
    """For every item in slave, find its counterpart in master."""

    matches = MatchNamespace()
    matches.conflict['email'] = ConflictingMatchList(index_fn=EmailMatcher.email_index_fn)

    if not settings.do_sync:
        return matches

    Registrar.register_progress("Processing matches")

    parsers.deny_anomalous('sa_parser.nousernames', parsers.slave.nousernames)

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

    parsers.deny_anomalous('ma_parser.nocards', parsers.master.nocards)

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

    parsers.deny_anomalous("sa_parser.noemails", parsers.slave.noemails)

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

def do_merge(matches, parsers, settings):
    """For a given list of matches, return a description of updates required to merge them."""
    Registrar.register_progress("BEGINNING MERGE (%d)" % len(matches.globals))

    updates = UpdateNamespace()

    if not settings.do_sync:
        return updates

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
            new_email = sync_slave_updates.get('E-mail', None)
            new_email = SanitationUtils.normalize_val(new_email)
            if new_email and new_email in parsers.slave.emails:
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
    """Write report of changes to be made."""
    reporters = ReporterNamespace()

    if settings.get('do_report'):
        Registrar.register_progress("Write Main Report")

        do_main_summary_group(reporters.main, matches, updates, parsers, settings),
        do_delta_group(reporters.main, matches, updates, parsers, settings),
        do_sync_group(reporters.main, matches, updates, parsers, settings)
        if reporters.main:
            reporters.main.write_document_to_file('main', settings.rep_main_path)

        if settings.get('report_sanitation'):
            Registrar.register_progress("Write Sanitation Report")

            do_sanitizing_group(reporters.san, matches, updates, parsers, settings),
            if reporters.san:
                reporters.san.write_document_to_file('san', settings.rep_san_path)

        if settings.get('report_matching'):
            Registrar.register_progress("Write Matching Report")

            do_matches_summary_group(reporters.match, matches, updates, parsers, settings)
            do_matches_group(reporters.match, matches, updates, parsers, settings),
            if reporters.match:
                reporters.match.write_document_to_file('match', settings.rep_match_path)

        if settings.get('report_duplicates'):
            Registrar.register_progress("Write Duplicates Report")

            do_duplicates_summary_group(reporters.dup, matches, updates, parsers, settings),
            do_duplicates_group(reporters.dup, matches, updates, parsers, settings)
            if reporters.dup:
                reporters.dup.write_document_to_file('dup', settings.rep_dup_path)

    return reporters

def pickle_state(matches=None, updates=None, parsers=None, settings=None, progress=None):
    """Save execution state of a pickle file which can be restored later."""
    # Registrar.register_progress("pickling state")
    settings.progress = progress
    pickle_obj = (matches, updates, parsers, settings)

    with open(settings.pickle_path, 'w') as pickle_file:
        dill.dump(pickle_obj, pickle_file)

    print "state saved to %s" % settings.pickle_path

def unpickle_state(settings_pickle):
    """Restore state from a pickle file."""
    Registrar.register_progress(
        "restoring state from pickle of %s" % settings_pickle.import_name
    )

    with open(settings_pickle.pickle_path) as pickle_file:
        pickle_obj = dill.load(pickle_file)
        matches, updates, parsers, settings = pickle_obj
        settings.picklemode = True

    if settings_pickle.get('override_progress'):
        settings.progress = settings_pickle['override_progress']

    if settings.progress in ['sync']:
        matches = do_match(parsers, settings)
        updates = do_merge(matches, parsers, settings)
    if settings.progress in ['sync', 'report']:
        reporters = do_report(matches, updates, parsers, settings)
        results = do_updates(updates, settings)
        if results:
            do_report_post(reporters.main, results, settings)
        return reporters, results

def handle_failed_update(update, results, exc, settings, source=None):
    """Handle a failed update."""
    fail = {
        'update': update,
        'master': SanitationUtils.coerce_unicode(update.new_m_object),
        'slave': SanitationUtils.coerce_unicode(update.new_s_object),
        'mchanges': SanitationUtils.coerce_unicode(update.get_master_updates()),
        'schanges': SanitationUtils.coerce_unicode(update.get_slave_updates()),
        'exception': repr(exc)
    }
    if source == settings.master_name:
        pkey = update.master_id
        results.fails_master.append(fail)
    elif source == settings.slave_name:
        pkey = update.slave_id
        results.fails_slave.append(fail)
    else:
        pkey = ''
    Registrar.register_error(
        "ERROR UPDATING %s (%s): %s\n%s\n%s" % (
            source or '',
            pkey,
            repr(exc),
            update.tabulate(),
            traceback.format_exc()
        )
    )

    if Registrar.DEBUG_TRACE:
        boring = False
        for exc_class in BORING_EXCEPTIONS:
            if isinstance(exc, exc_class):
                boring = True
                break
        if not boring:
            if Registrar.DEBUG_TRACE:
                import pudb; pudb.set_trace()

def do_updates(updates, settings):
    """Perform a list of updates."""
    all_updates = updates.static
    if settings.do_problematic:
        all_updates += updates.problematic

    results = ResultsNamespace()

    if not all_updates or not (settings.update_master or settings.update_slave):
        return results

    Registrar.register_progress("UPDATING %d RECORDS" % len(all_updates))

    if len(all_updates) and settings['ask_before_update']:
        try:
            raw_in = input( "\n".join([
                "Please read reports and then make your selection",
                " - press Enter to continue and perform updates",
                " - press s to skip updates",
                " - press c to cancel",
                "..."
            ]))
        except SyntaxError:
            raw_in = ""
        if raw_in == 's':
            return results
        if raw_in == 'c':
            raise SystemExit

    if Registrar.DEBUG_PROGRESS:
        update_progress_counter = ProgressCounter(len(all_updates))

    slave_client_args = settings.slave_upload_client_args
    slave_client_class = settings.slave_upload_client_class
    master_client_args = settings.master_upload_client_args
    master_client_class = settings.master_upload_client_class

    with \
    master_client_class(**master_client_args) as master_client, \
    slave_client_class(**slave_client_args) as slave_client:
        for count, update in enumerate(all_updates):
            if Registrar.DEBUG_PROGRESS:
                update_progress_counter.maybe_print_update(count)
            if Registrar.DEBUG_UPDATE:
                Registrar.register_message(
                    "performing update: \n%s",
                    SanitationUtils.coerce_unicode(update.tabulate())
                )
            update_was_performed = False
            if settings['update_master'] and update.m_updated:
                try:
                    update.update_master(master_client)
                    update_was_performed = True
                except Exception as exc:
                    handle_failed_update(
                        update, results, exc, settings, source=settings.master_name
                    )
            if settings['update_slave'] and update.s_updated:
                try:
                    update.update_slave(slave_client)
                    update_was_performed = True
                except Exception as exc:
                    handle_failed_update(
                        update, results, exc, settings, source=settings.slave_name
                    )
            if update_was_performed:
                results.successes.append(update)
    return results

def do_report_post(reporters, results, settings):
    """ Reports results from performing updates."""
    if settings.get('do_report'):
        Registrar.register_progress("Write Post Report")

        do_post_summary_group(reporters.post, settings)
        do_failures_group(reporters.post, results, settings)
        do_successes_group(reporters.post, results, settings)
        if reporters.post:
            reporters.post.write_document_to_file('post', settings.rep_post_path)

def main(override_args=None, settings=None):
    """Use settings object to load config file and detect changes in wordpress."""
    settings = init_settings(override_args, settings, ArgumentParserUser)

    if hasattr(settings, 'pickle_file') and getattr(settings, 'pickle_file'):
        return unpickle_state(settings)
    else:
        Registrar.register_progress("Starting Merge %s" % settings.import_name)

    init_dirs(settings)

    populate_filter_settings(settings)

    parsers = ParserNamespace()
    parsers = populate_slave_parsers(parsers, settings)
    if settings['download_slave']:
        export_slave_parser(parsers, settings)
    parsers = populate_master_parsers(parsers, settings)
    # export_master_parser(parsers, settings)

    pickle_state(None, None, parsers, settings, 'sync')

    matches = do_match(parsers, settings)
    updates = do_merge(matches, parsers, settings)

    pickle_state(matches, updates, parsers, settings, 'report')

    reporters = do_report(matches, updates, parsers, settings)

    Registrar.register_message(
        "pre-sync summary: \n%s" % reporters.main.get_summary_text()
    )

    try:
        results = do_updates(updates, settings)
    except (SystemExit, KeyboardInterrupt):
        return reporters, results
    do_report_post(reporters, results, settings)

    Registrar.register_message(
        "post-sync summary: \n%s" % reporters.post.get_summary_text()
    )

    return reporters, results

def do_mail(settings, summary_html=None, summary_text=None):
    with settings.email_client(settings.email_connect_params) as email_client:
        message = email_client.compose_message(
            settings.mail_sender,
            settings.mail_recipients,
            'Summary of Import %s' % settings.import_name,
            summary_html,
            summary_text
        )
        message = email_client.attach_file(message, settings.zip_path)
        email_client.send(message)

def do_summary(settings, reporters=None, results=None, status=1, reason="Uknown"):
    Registrar.register_progress("Doing summary for %s" % settings.import_name)

    if status:
        summary_text = u"Sync failed with status %s (%s)" % (reason, status)
    else:
        summary_text = u"Sync succeeded"
    if results:
        if results.successes:
            summary_text += u"\nSuccesses: %d" % len(results.successes)
        if results.fails_master:
            summary_text += u"\nMaster Fails: %d" % len(results.fails_master)
        if results.fails_slave:
            summary_text += u"\nSlave Fails: %d" % len(results.fails_slave)
    else:
        summary_text += u"\nNo changes made"
    summary_html = "<p>%s</p>" % re.sub(ur'\n', ur'<br/>', summary_text)

    # TODO: move this block to Registrar.write_log()
    with io.open(settings.log_path, 'w+', encoding='utf8') as log_file:
        for source, messages in Registrar.get_message_items(1).items():
            print source
            log_file.write(SanitationUtils.coerce_unicode(source) + u'\r\n')
            for message in messages:
                log_file.write(u'\t' + SanitationUtils.coerce_unicode(message) + u'\r\n')
            for message in messages:
                pprint(message, indent=4, width=80, depth=2)

    try:
        files_to_zip = []
        attrs_to_zip = [
            'master_path', 'slave_path', 'log_path'
        ]
        for attr in attrs_to_zip:
            files_to_zip.append(settings.get(attr))
        if reporters is not None:
            for name, csv_file in reporters.get_csv_files().items():
                # print("appending CSV file %s = %s" % (name, csv_file))
                if csv_file not in files_to_zip:
                    files_to_zip.append(csv_file)
            for name, html_file in reporters.get_html_files().items():
                # print("appending HTML file %s = %s" % (name, html_file))
                if html_file not in files_to_zip:
                    files_to_zip.append(html_file)
    except Exception as exc:
        print traceback.format_exc()

    with zipfile.ZipFile(settings.zip_path, 'w') as zip_file:
        for file_to_zip in files_to_zip:
            arcname = os.path.basename(file_to_zip)
            # print("zipping file %s to %s" % (
            #     file_to_zip, arcname
            # ))
            try:
                os.stat(file_to_zip)
                zip_file.write(file_to_zip, arcname)
            except Exception as exc:
                if exc:
                    print("could not zip file %s: %s" % (
                        file_to_zip, exc
                    ))
                    print traceback.format_exc()
        Registrar.register_message('wrote file %s' % settings.zip_path)

    # try:
    #     stats = os.stat(settings.zip_path)
    #     print("zip file stats: %s" % stats)
    # except Exception as exc:
    #     if exc:
    #         print("could not stat zip file %s" % (
    #             settings.zip_path
    #         ))
    #         print traceback.format_exc()

    if reporters is not None:
        summary_html += reporters.post.get_summary_html()
        summary_text += "\n%s" % reporters.post.get_summary_text()

    if settings.get('do_mail') and reporters and results:
        do_mail(
            settings,
            summary_html,
            summary_text
        )
    else:
        print("not emailing because not reporters or results.")
        print("reporters: %s, results: %s" % (reporters, results))

    return summary_html, summary_text

def catch_main(override_args=None):
    """Run the main function within a try statement and attempt to analyse failure."""
    settings = SettingsNamespaceUser()
    reporters = ReporterNamespace()
    results = ResultsNamespace()

    status = 0
    reason = None

    try:
        reporters, results = main(settings=settings, override_args=override_args)
    except (SystemExit, KeyboardInterrupt):
        pass
    except (ReadTimeout, ConnectionError, ConnectTimeout, ServerNotFoundError):
        status = 69  # service unavailable
        reason = "Service unavailable"
    except IOError:
        status = 74
        reason = "IOError"
        print "IOError. cwd: %s" % os.getcwd()
    except UserWarning:
        status = 65
        reason = "User Warning"
    except Exception:
        status = 1
        reason = "Other"
    finally:
        if status:
            Registrar.register_error(traceback.format_exc())
            if Registrar.DEBUG_TRACE:
                import pudb; pudb.set_trace()

    try:
        summary_html, summary_text = do_summary(settings, reporters, results, status, reason)
        # print("Summary:\n%s" % summary_text)
    except (SystemExit, KeyboardInterrupt):
        status = 0
    except Exception:
        status = 1
    finally:
        if status:
            print("Failed to do summary. Exception:")
            print(traceback.format_exc())
            if Registrar.DEBUG_TRACE:
                import pudb; pudb.set_trace()

    sys.exit(status)

if __name__ == '__main__':
    catch_main()
