"""
Export a list of users which have an anomalous role, such that their ACT_ROLE is
inconsistent with their wordpress roles.
"""

import sys
from collections import OrderedDict

import phpserialize

from .merger import (export_slave_parser, populate_filter_settings,
                     populate_slave_parsers)
from .namespace.core import ParserNamespace, ResultsNamespace
from .namespace.user import SettingsNamespaceUser
from .utils import Registrar, SanitationUtils
from .utils.reporter import ReporterNamespace, do_sanitizing_group


def do_report(parsers, settings):
    reporters = ReporterNamespace()

    if settings.get('report_sanitation'):
        Registrar.register_progress("Write Sanitation Report")

        do_sanitizing_group(reporters.san, parsers, settings)
        if reporters.san:
            reporters.san.write_document_to_file(
                'san', settings.rep_san_path)

    return reporters

def process_role_anomalies(parsers, settings):
    parsers.slave.bad_role = OrderedDict()
    for user in parsers.slave.objects.values():
        role_reason = None
        wp_roles = user.get('WP Roles')
        if wp_roles:
            wp_roles = phpserialize.loads(wp_roles).keys()
            wp_roles = map(unicode.upper, wp_roles)
        # print('wp_roles: %s', wp_roles)
        act_role = user.get('ACT Role')
        if act_role and act_role.startswith('ADMI'):
            act_role = 'ADMINISTRATOR'
        # print('act_role: %s', act_role)
        if wp_roles:
            if len(wp_roles) != 1:
                role_reason = 'wrong number of wp roles: %s' % wp_roles
        if not role_reason and wp_roles and act_role:
            if wp_roles[0] != act_role:
                role_reason = 'roles don\'t match: wp=%s , act=%s' % (wp_roles[0], act_role)

        if role_reason:
            print(
                'user %100s, %50s has bad role: %s' % (
                    user.index,
                    user.get('E-mail'),
                    role_reason,
                )
            )
            parsers.slave.register_anything(
                user,
                parsers.slave.bad_role,
                user.index,
                singular=True,
                register_name='badrole'
            )
    return parsers



def main(override_args=None, settings=None):
    """Use settings object to load config file and detect changes in wordpress."""
    if not settings:
        settings = SettingsNamespaceUser()
    settings.init_settings(override_args)
    settings.download_slave = True
    settings.report_sanitation = True
    settings.exclude_cols = [
        'Address',
        'Home Address',
        'Phone Numbers',
        'Personal E-mail'
    ]
    settings.include_cols = [
        'ACT Role',
        'WP Roles'
    ]
    if Registrar.DEBUG_TRACE:
        from pudb import set_interrupt_handler; set_interrupt_handler()

    settings.init_dirs()

    populate_filter_settings(settings)

    parsers = ParserNamespace()
    # import pudb; pudb.set_trace()
    parsers = populate_slave_parsers(parsers, settings)
    if settings['download_slave'] or settings['do_filter']:
        export_slave_parser(parsers, settings)


    report_cols = settings.col_data_class.get_report_cols()
    exclude_cols = settings.get('exclude_cols')
    if exclude_cols:
        for col in exclude_cols:
            if col in report_cols:
                del report_cols[col]
    include_cols = settings.get('include_cols')
    if include_cols:
        for col in include_cols:
            if col not in report_cols:
                report_cols[col] = col

    Registrar.register_message(
        "slave parser: \n%s" %
        SanitationUtils.coerce_unicode(
            parsers.slave.tabulate(
                cols=report_cols
            )
        )
    )

    parsers = process_role_anomalies(parsers, settings)

    reporters = do_report(parsers, settings)


    Registrar.register_message(
        "Sanitation summary: \n%s" % reporters.san.get_summary_text()
    )

    return reporters, None


def catch_main(override_args=None):
    settings = SettingsNamespaceUser()
    try:
        reporters, results = main(
            settings=settings, override_args=override_args
        )
    except BaseException:
        _, _, traceback = sys.exc_info()
        import pdb; pdb.post_mortem(traceback)

if __name__ == '__main__':
    catch_main()
