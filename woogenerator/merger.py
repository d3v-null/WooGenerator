"""Module for updating woocommerce and ACT databases from ACT import file."""

from __future__ import absolute_import

import io
import os
import re
import sys
import traceback
import zipfile
from bisect import insort
from pprint import pformat, pprint

import dill
import sshtunnel
from httplib2 import ServerNotFoundError
from requests.exceptions import ConnectionError, ConnectTimeout, ReadTimeout

from six.moves import input

from .matching import (CardMatcher, ConflictingMatchList, EmailMatcher, Match,
                       NocardEmailMatcher, UsernameMatcher)
from .namespace.core import (MatchNamespace, ParserNamespace, ResultsNamespace,
                             UpdateNamespace)
from .namespace.user import SettingsNamespaceUser
from .syncupdate import SyncUpdateUsrApi
from .utils import ProgressCounter, Registrar, SanitationUtils, TimeUtils
from .utils.reporter import (ReporterNamespace, do_delta_group,
                             do_duplicates_group, do_duplicates_summary_group,
                             do_failures_group, do_main_summary_group,
                             do_matches_group, do_matches_summary_group,
                             do_post_summary_group, do_sanitizing_group,
                             do_successes_group, do_sync_group)

BORING_EXCEPTIONS = [ConnectionError, ConnectTimeout, ReadTimeout]


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
            settings.filter_items['emails'].extend(
                settings.get('filter_emails').split(','))
        if settings.get('filter_cards'):
            if not settings.filter_items.get('cards'):
                settings.filter_items['cards'] = []
            settings.filter_items['cards'].extend(
                settings.get('filter_cards').split(','))
        if settings.get('ignore_cards'):
            if not settings.filter_items.get('ignore_cards'):
                settings.filter_items['ignore_cards'] = []
            settings.filter_items['ignore_cards'].extend(
                settings.get('ignore_cards').split(','))
        if settings.get('since_m'):
            settings.filter_items['since_m'] = TimeUtils.wp_strp_mktime(
                settings['since_m'])
        if settings.get('since_s'):
            settings.filter_items['since_s'] = TimeUtils.wp_strp_mktime(
                settings['since_s'])

        for key in ['emails', 'cards', 'users']:
            if key in settings.filter_items:
                settings.filter_items[key] = [
                    SanitationUtils.normalize_val(value)
                    for value in settings.filter_items[key]
                ]

    else:
        settings.filter_items = None

    if Registrar.DEBUG_UPDATE and settings.do_filter:
        Registrar.register_message("filter_items: %s" % settings.filter_items)


def populate_subordinate_parsers(parsers, settings):
    """Populate the parsers for data from the subordinate database."""
    parsers.subordinate = settings.subordinate_parser_class(**settings.subordinate_parser_args)

    if settings['download_subordinate']:
        for host_key in [
                'ssh_address_or_host',
                'remote_bind_address'
        ]:
            try:
                sshtunnel.check_address(
                    settings.subordinate_connect_params.get(host_key))
            except AttributeError:
                Registrar.register_error("invalid host: %s -> %s" %
                                         (host_key, settings.get(host_key)))
            except Exception as exc:
                raise UserWarning("Host must be valid: %s [%s = %s]" %
                                  (str(exc), host_key, repr(settings.get(host_key))))
        if Registrar.DEBUG_CLIENT:
            Registrar.register_message(
                "SSHTunnelForwarderParams: %s\nPyMySqlconnect_params: %s" % (
                    settings.subordinate_connect_params,
                    settings.subordinate_db_params
                )
            )

    if Registrar.DEBUG_PARSER:
        Registrar.register_message(
            "client_args: %s" % settings.subordinate_download_client_args
        )

    Registrar.register_progress("analysing subordinate user data")

    subordinate_client_class = settings.subordinate_download_client_class
    subordinate_client_args = settings.subordinate_download_client_args

    with subordinate_client_class(**subordinate_client_args) as client:
        client.analyse_remote(parsers.subordinate, data_path=settings.subordinate_path)

    if Registrar.DEBUG_UPDATE and settings.do_filter:
        Registrar.register_message(
            "subordinate parser: \n%s" %
            SanitationUtils.coerce_unicode(parsers.subordinate.tabulate())
        )

    return parsers


def export_subordinate_parser(parsers, settings):
    """Export subordinate parser to disk."""
    subordinate_items = parsers.subordinate.get_obj_list()
    col_names = settings.coldata_class.get_wp_import_col_names()
    exclude_cols = settings.get('exclude_cols')
    if exclude_cols:
        for col in exclude_cols:
            if col in col_names:
                del col_names[col]
    include_cols = settings.get('include_cols')
    if include_cols:
        for col in include_cols:
            if col not in col_names:
                col_names[col] = col

    if subordinate_items:
        subordinate_items.export_items(
            settings.subordinate_path,
            col_names
        )


def populate_main_parsers(parsers, settings):
    """Populate the parsers for data from the subordinate database."""
    things_to_check = []
    if settings['download_main']:
        things_to_check.extend(
            ['main_connect_params', 'main_db_params', 'fs_params'])
    else:
        things_to_check.extend(['main_path'])
    for thing in things_to_check:
        Registrar.register_message(
            "%s: %s" % (thing, getattr(settings, thing))
        )
        assert getattr(settings, thing), "settings must specify %s" % thing

    Registrar.register_message(
        "main_parser_args:\n%s" %
        pformat(
            settings.main_parser_args))

    parsers.main = settings.main_parser_class(
        **settings.main_parser_args
    )

    Registrar.register_progress("analysing main user data")

    main_client_class = settings.main_download_client_class
    main_client_args = settings.main_download_client_args
    with main_client_class(**main_client_args) as client:
        client.analyse_remote(parsers.main, data_path=settings.main_path)

    if Registrar.DEBUG_UPDATE and settings.do_filter:
        Registrar.register_message(
            "main parser: \n%s" %
            SanitationUtils.coerce_unicode(parsers.main.tabulate())
        )

    return parsers


def export_main_parser(parsers, settings):
    """Export the Masater parser to disk."""
    main_items = parsers.main.get_obj_list()
    if main_items:
        main_items.export_items(
            os.path.join(settings.in_dir_full, settings.m_x_name),
            settings.coldata_class.get_act_import_col_names()
        )


def do_match(parsers, settings):
    """For every item in subordinate, find its counterpart in main."""

    matches = MatchNamespace()
    matches.conflict['email'] = ConflictingMatchList(
        index_fn=EmailMatcher.email_index_fn)

    if not settings.do_sync:
        return matches

    Registrar.register_progress("Processing matches")

    parsers.deny_anomalous('sa_parser.nousernames', parsers.subordinate.nousernames)

    username_matcher = UsernameMatcher()
    username_matcher.process_registers(parsers.subordinate.usernames,
                                       parsers.main.usernames)

    matches.deny_anomalous(
        'usernameMatcher.subordinateless_matches', username_matcher.subordinateless_matches)
    matches.deny_anomalous(
        'usernameMatcher.duplicate_matches', username_matcher.duplicate_matches)

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

    # Registrar.register_progress("processing cards")

    # for every card in subordinate not already matched, check that it exists in
    # main

    parsers.deny_anomalous('ma_parser.nocards', parsers.main.nocards)

    card_matcher = CardMatcher(
        matches.globals.s_indices, matches.globals.m_indices
    )
    card_matcher.process_registers(parsers.subordinate.cards, parsers.main.cards)

    matches.deny_anomalous(
        'cardMatcher.duplicate_matches', card_matcher.duplicate_matches
    )
    matches.deny_anomalous(
        'cardMatcher.mainless_matches', card_matcher.mainless_matches
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

    # #for every email in subordinate, check that it exists in main

    # Registrar.register_progress("processing emails")

    parsers.deny_anomalous("sa_parser.noemails", parsers.subordinate.noemails)

    email_matcher = NocardEmailMatcher(
        matches.globals.s_indices, matches.globals.m_indices
    )

    email_matcher.process_registers(
        parsers.subordinate.nocards,
        parsers.main.emails)

    matches.mainless.add_matches(email_matcher.mainless_matches)
    matches.subordinateless.add_matches(email_matcher.subordinateless_matches)
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

    sync_cols = settings.coldata_class.get_sync_handles()

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
            insort(updates.delta_main, sync_update)

        if sync_update.s_updated and sync_update.s_deltas:
            insort(updates.delta_subordinate, sync_update)

        if not sync_update:
            continue

        if sync_update.s_updated:
            sync_subordinate_updates = sync_update.get_subordinate_updates()
            new_email = sync_subordinate_updates.get('E-mail', None)
            new_email = SanitationUtils.normalize_val(new_email)
            if new_email and new_email in parsers.subordinate.emails:
                m_objects = [m_object]
                s_objects = [s_object] + parsers.subordinate.emails[new_email]
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
                insort(updates.nonstatic_main, sync_update)
                if sync_update.s_mod:
                    insort(updates.problematic, sync_update)
                    continue
            elif sync_update.s_updated and not sync_update.m_updated:
                insort(updates.nonstatic_subordinate, sync_update)
                if sync_update.s_mod:
                    insort(updates.problematic, sync_update)
                    continue

        if sync_update.s_updated or sync_update.m_updated:
            insort(updates.static, sync_update)
            if sync_update.m_updated and sync_update.s_updated:
                insort(updates.main, sync_update)
                insort(updates.subordinate, sync_update)
            if sync_update.m_updated and not sync_update.s_updated:
                insort(updates.main, sync_update)
            if sync_update.s_updated and not sync_update.m_updated:
                insort(updates.subordinate, sync_update)

    Registrar.register_progress("COMPLETED MERGE")
    return updates


def do_report(matches, updates, parsers, settings):
    """Write report of changes to be made."""
    reporters = ReporterNamespace()

    if not settings.get('do_report'):
        return reporters

    Registrar.register_progress("Write Main Report")

    do_main_summary_group(
        reporters.main, matches, updates, parsers, settings
    )
    do_delta_group(
        reporters.main, matches, updates, parsers, settings
    )
    do_sync_group(
        reporters.main, matches, updates, parsers, settings
    )
    if reporters.main:
        reporters.main.write_document_to_file('main', settings.rep_main_path)

    if settings.get('report_sanitation'):
        Registrar.register_progress("Write Sanitation Report")

        do_sanitizing_group(reporters.san, parsers, settings)
        if reporters.san:
            reporters.san.write_document_to_file(
                'san', settings.rep_san_path)

    if settings.get('report_matching'):
        Registrar.register_progress("Write Matching Report")

        do_matches_summary_group(
            reporters.match, matches, updates, parsers, settings
        )
        do_matches_group(
            reporters.match, matches, updates, parsers, settings
        ),
        if reporters.match:
            reporters.match.write_document_to_file(
                'match', settings.rep_match_path)

    if settings.get('report_duplicates'):
        Registrar.register_progress("Write Duplicates Report")

        do_duplicates_summary_group(
            reporters.dup, matches, updates, parsers, settings),
        do_duplicates_group(
            reporters.dup, matches, updates, parsers, settings
        )
        if reporters.dup:
            reporters.dup.write_document_to_file(
                'dup', settings.rep_dup_path)

    return reporters


def pickle_state(matches=None, updates=None, parsers=None,
                 settings=None, progress=None):
    """Save execution state of a pickle file which can be restored later."""
    # Registrar.register_progress("pickling state")
    settings.progress = progress
    pickle_obj = (matches, updates, parsers, settings)

    with open(settings.pickle_path, 'w') as pickle_file:
        dill.dump(pickle_obj, pickle_file)

    Registrar.register_message("state saved to %s" % settings.pickle_path)


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
    fail = (update, exc)
    if source == settings.main_name:
        pkey = update.main_id
        results.fails_main.append(fail)
    elif source == settings.subordinate_name:
        pkey = update.subordinate_id
        results.fails_subordinate.append(fail)
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
                import pudb
                pudb.set_trace()


def do_updates(updates, settings):
    """Perform a list of updates."""
    all_updates = updates.static
    if settings.do_problematic:
        all_updates += updates.problematic

    results = ResultsNamespace()

    if not all_updates or not (
            settings.update_main or settings.update_subordinate):
        return results

    Registrar.register_progress("UPDATING %d RECORDS" % len(all_updates))

    if len(all_updates) and settings['ask_before_update']:
        try:
            raw_in = input("\n".join([
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

    subordinate_client_args = settings.subordinate_upload_client_args
    subordinate_client_class = settings.subordinate_upload_client_class
    main_client_args = settings.main_upload_client_args
    main_client_class = settings.main_upload_client_class

    with \
            main_client_class(**main_client_args) as main_client, \
            subordinate_client_class(**subordinate_client_args) as subordinate_client:
        for count, update in enumerate(all_updates):
            if Registrar.DEBUG_PROGRESS:
                update_progress_counter.maybe_print_update(count)
            if Registrar.DEBUG_UPDATE:
                Registrar.register_message(
                    "performing update: \n%s",
                    SanitationUtils.coerce_unicode(update.tabulate())
                )
            update_was_performed = False
            if settings['update_main'] and update.m_updated:
                try:
                    update.update_main(main_client)
                    update_was_performed = True
                except Exception as exc:
                    handle_failed_update(
                        update, results, exc, settings, source=settings.main_name
                    )
            if settings['update_subordinate'] and update.s_updated:
                try:
                    update.update_subordinate(subordinate_client)
                    update_was_performed = True
                except Exception as exc:
                    handle_failed_update(
                        update, results, exc, settings, source=settings.subordinate_name
                    )
            if update_was_performed:
                results.successes.append(update)
    return results


def do_report_post(reporters, results, settings):
    """Reports results from performing updates."""
    if settings.get('do_report'):
        Registrar.register_progress("Write Post Report")

        do_post_summary_group(reporters.post, results, settings)
        do_failures_group(reporters.post, results, settings)
        do_successes_group(reporters.post, results, settings)
        if reporters.post:
            reporters.post.write_document_to_file(
                'post', settings.rep_post_path)


def main(override_args=None, settings=None):
    """Use settings object to load config file and detect changes in wordpress."""
    if not settings:
        settings = SettingsNamespaceUser()
    settings.init_settings(override_args)

    if hasattr(settings, 'pickle_file') and getattr(settings, 'pickle_file'):
        return unpickle_state(settings)
    else:
        Registrar.register_progress("Starting Merge %s" % settings.import_name)

    settings.init_dirs()

    populate_filter_settings(settings)

    parsers = ParserNamespace()
    parsers = populate_subordinate_parsers(parsers, settings)
    if settings['download_subordinate'] or settings['do_filter']:
        export_subordinate_parser(parsers, settings)
    parsers = populate_main_parsers(parsers, settings)
    if settings['download_main'] or settings['do_filter']:
        export_main_parser(parsers, settings)

    # pickle_state(None, None, parsers, settings, 'sync')

    matches = do_match(parsers, settings)
    updates = do_merge(matches, parsers, settings)

    # pickle_state(matches, updates, parsers, settings, 'report')

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


def do_summary(settings, reporters=None, results=None,
               status=1, reason="Uknown"):
    Registrar.register_progress("Doing summary for %s" % settings.import_name)

    if status or results.fails_main or results.fails_subordinate:
        summary_text = u"Sync failed with status %s (%s)" % (reason, status)
    else:
        summary_text = u"Sync succeeded"

    summary_html = "<p>%s</p>" % re.sub(ur'\n', ur'\n<br/>\n', summary_text)

    # TODO: move this block to Registrar.write_log()
    with io.open(settings.log_path, 'w+', encoding='utf8') as log_file:
        for source, messages in Registrar.get_message_items(1).items():
            log_file.write(SanitationUtils.coerce_unicode(source) + u'\r\n')
            for message in messages:
                log_file.write(
                    u'\t' + SanitationUtils.coerce_unicode(message) + u'\r\n'
                )
            for message in messages:
                if Registrar.DEBUG_MESSAGE:
                    pprint(message, indent=4, width=80, depth=2)

    try:
        files_to_zip = []
        attrs_to_zip = [
            'log_path'
        ]
        reports_to_ignore = [
            # 'dup'
        ]
        for attr in attrs_to_zip:
            filename = settings.get(attr)
            if filename:
                files_to_zip.append(settings.get(attr))
                size = None
                try:
                    size = os.path.getsize(filename)
                except Exception:
                    pass
                Registrar.register_message("file name %s, size %s" % (
                    filename, size
                ))

        if reporters is not None:
            for name, csv_file in reporters.get_csv_files().items():
                if name in reports_to_ignore:
                    continue
                if csv_file not in files_to_zip:
                    files_to_zip.append(csv_file)
                size = None
                try:
                    size = os.path.getsize(csv_file)
                except Exception:
                    pass
                Registrar.register_message("csv report name %s, size %s" % (
                    name, size
                ))

            for name, html_file in reporters.get_html_files().items():
                if name in reports_to_ignore:
                    continue
                if html_file not in files_to_zip:
                    files_to_zip.append(html_file)
                size = None
                try:
                    size = os.path.getsize(html_file)
                except Exception:
                    pass
                Registrar.register_message("html report name %s, size %s" % (
                    name, size
                ))
    except Exception as exc:
        Registrar.register_warning(
            (
                "could not get files to zip: %s\n%s"
            ) % (
                exc,
                traceback.format_exc()
            )
        )
        print traceback.format_exc()

    with zipfile.ZipFile(settings.zip_path, 'w') as zip_file:
        for file_to_zip in files_to_zip:
            arcname = os.path.basename(file_to_zip)
            try:
                os.stat(file_to_zip)
                zip_file.write(file_to_zip, arcname)
            except Exception as exc:
                Registrar.register_warning(
                    (
                        "could not zip file %s: %s\n%s"
                    ) % (
                        file_to_zip,
                        exc,
                        traceback.format_exc()
                    )
                )
        Registrar.register_message('wrote file %s' % settings.zip_path)

    zip_size = None
    try:
        zip_size = os.path.getsize(settings.zip_path)
    except Exception:
        pass

    Registrar.register_message("zip size is: %s" % zip_size)

    if reporters is not None:
        summary_html += reporters.post.get_summary_html()
        summary_text += "\n%s" % reporters.post.get_summary_text()

    if settings.get('do_mail') and reporters and results:
        try:
            do_mail(
                settings,
                summary_html,
                summary_text
            )
        except Exception as exc:
            zip_stats = None
            try:
                zip_stats = os.stat(settings.zip_path)
            except Exception as exc:
                pass
            Registrar.register_warning(
                (
                    "%s\n"
                    "Failed to send email because %s\n"
                    "zip file stats: %s\n"
                    "summary text is \n%s"
                ) % (
                    traceback.format_exc(),
                    exc,
                    zip_stats,
                    summary_text
                )
            )
    else:
        Registrar.register_warning(
            (
                "not emailing because no reporters or results.\n"
                "reporters: \n%s"
                "results: \n%s"
            ) % (
                [
                    (name, len(reporter.groups))
                    for name, reporter in reporters.as_dict.items()
                ],
                [
                    (name, len(result))
                    for name, result in results.as_dict.items()
                ]
            )
        )

    return summary_html, summary_text


def catch_main(override_args=None):
    """Run the main function within a try statement and attempt to analyse failure."""
    settings = SettingsNamespaceUser()
    reporters = ReporterNamespace()
    results = ResultsNamespace()

    status = 0
    reason = None

    try:
        reporters, results = main(
            settings=settings, override_args=override_args)
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
                import pudb
                pudb.set_trace()

    try:
        summary_html, summary_text = do_summary(
            settings, reporters, results, status, reason)
    except (SystemExit, KeyboardInterrupt):
        status = 0
    except Exception:
        status = 1
    finally:
        if status:
            print("Failed to do summary. Exception:")
            print(traceback.format_exc())
            if Registrar.DEBUG_TRACE:
                import pudb
                pudb.set_trace()

    sys.exit(status)


if __name__ == '__main__':
    catch_main()
