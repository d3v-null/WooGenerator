from __future__ import absolute_import

import argparse
import io
import os
import re
from collections import OrderedDict

import unicodecsv

from woogenerator.duplicates import Duplicates
from woogenerator.parsing.user import UsrObjList

from .clock import TimeUtils
from .core import Registrar, SanitationUtils


class ReporterNamespace(argparse.Namespace):
    """ Collect variables used in reporting into a single namespace. """

    reporter_attrs = ['main', 'dup', 'san', 'match', 'fail']

    def __init__(self, *args, **kwargs):
        super(ReporterNamespace, self).__init__(*args, **kwargs)
        self.main = HtmlReporter()
        self.dup = HtmlReporter(css=DUP_CSS)
        self.san = HtmlReporter()
        self.match = HtmlReporter()
        self.fail = HtmlReporter()

    def get_csv_files(self):
        csv_files = OrderedDict()
        for attr in self.reporter_attrs:
            reporter = getattr(self, attr)
            csv_files.update(reporter.csv_files)
        return csv_files

    def get_html_files(self):
        html_files = OrderedDict()
        for attr in self.reporter_attrs:
            reporter = getattr(self, attr)
            html_files.update(reporter.html_files)
        return html_files

DUP_CSS = "\n".join([
    ".highlight_old {color: red !important; }"
    ".highlight_oldish {color: orange;}"
    ".highlight_master {background: lightblue !important;}"
    ".highlight_slave {background: lightpink !important;}"
])

class HtmlReporter(object):
    """docstring for htmlReporter"""

    class Section(object):
        data_heading_fmt = "<h3>%s</h3>"
        data_separater = "<hr>"

        def __init__(self, classname, title=None,
                     description="", data="", length=None):
            if title is None:
                title = classname.title()
            self.title = title
            self.description = description
            self.data = data
            self.length = length
            self.classname = classname

        def render(self, fmt=None):
            if fmt=='html':
                title_fmt = "<h2>%s</h2>"
                descr_fmt = '<p class="description">%s</p>'
                data_fmt = '<p class="data">%s</p>'
            else:
                title_fmt = "**%s**"
                descr_fmt = '\n%s'
                data_fmt = '\n%s'

            out = ''
            section_id = SanitationUtils.make_safe_class(self.classname)
            if fmt == 'html':
                out = '<div class="section">'
                out += ('<a data-toggle="collapse" href="#{0}" aria-expanded="true" '
                        'data-target="#{0}" aria-controls="{0}">').format(
                            section_id
                        )
            title = self.title
            title += ' ({})'.format(self.length) if self.length else ''
            out += title_fmt % title
            out += '</a>' if fmt == 'html' else ''
            out += '<div class="collapse" id="' + section_id + '">'

            description = (str(self.length) if self.length else "No") + ' ' + self.description
            out += descr_fmt % description

            data = self.data
            if fmt == 'html':
                data = re.sub("<table>", "<table class=\"table table-striped\">",
                              SanitationUtils.coerce_unicode(self.data))
            out += data_fmt % data

            out += '</div>' if fmt == 'html' else ''
            out = SanitationUtils.coerce_unicode(out)
            return out

        def to_html(self):
            return self.render('html')

        def to_text(self):
            return self.render()

    class Group(object):

        def __init__(self, classname, title=None, sections=None):
            if title is None:
                title = classname.title()
            if sections is None:
                sections = OrderedDict()
            self.title = title
            self.sections = sections
            self.classname = classname

        def add_section(self, section):
            self.sections[section.classname] = section

        def render(self, fmt=None):
            if fmt == 'html':
                title_fmt = "<h1>%s</h1>"
            else:
                title_fmt = "***%s***"
            out = ''
            out += '<div class="group">' if fmt == 'html' else ''
            out += title_fmt % self.title
            for section in self.sections.values():
                out += section.render(fmt)
            out += '</div>' if fmt == 'html' else ''
            out = SanitationUtils.coerce_unicode(out)
            return out

        def to_html(self):
            return self.render('html')

        def to_text(self):
            return self.render()

    def __init__(self, css=None):
        self.groups = OrderedDict()
        self.css = css
        self.csv_files = OrderedDict()
        self.html_files = OrderedDict()

    def add_group(self, group):
        self.groups[group.classname] = group

    def add_groups(self, *groups):
        for group in groups:
            self.add_group(group)

    def get_head(self):
        css = ''
        if self.css:
            css = "<style>" + self.css + "</style>"
        bootstrap_link = (
            '<link rel="stylesheet"'
            ' href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.6/css/bootstrap.min.css"'
            ' integrity="sha384-1q8mTJOASx8j1Au+a5WDVnPi2lkFfwwEAa8hDDdjZlpLegxhjVME1fgjWPGmkzs7"'
            ' crossorigin="anonymous">'
        )
        bootstrap_theme_link = (
            '<link rel="stylesheet"'
            ' href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.6/css/bootstrap-theme.min.css"'
            ' integrity="sha384-fLW2N01lMqjakBkx3l/M9EahuwpSfeNvV63J5ezn3uZzapT0u7EYsXMjQV+0En5r"'
            ' crossorigin="anonymous">'
        )
        return """\
<head>
    <meta charset="UTF-8">
    <!-- Latest compiled and minified CSS -->
""" + bootstrap_link + """
    <!-- Optional theme -->
""" + bootstrap_theme_link + """
""" + css + """
</head>
"""

    def get_body(self):
        content = "<br/>".join(
            group.to_html() for group in self.groups.values()
        )
        bootstrap_script = (
            '<script'
            ' src="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.6/js/bootstrap.min.js"'
            ' integrity="sha384-0mSbJDEHialfmuBBQP6A4Qrprq5OVfW37PRR3j5ELqxss1yVqOtnepnHVP9aJ7xS"'
            ' crossorigin="anonymous"></script>'
        )
        out = """
<body>
""" + content + """
    <script src="https://ajax.googleapis.com/ajax/libs/jquery/2.1.4/jquery.min.js"></script>
""" + bootstrap_script + """
</body>
"""
        out = SanitationUtils.coerce_unicode(out)
        return out

    def get_summary_html(self):
        return "<br/>".join(group.to_html() for group in self.groups.values())

    def get_summary_text(self):
        return "\n".join(group.to_text() for group in self.groups.values())

    def get_document(self):
        head = self.get_head()
        body = self.get_body()
        out = """\
<!DOCTYPE html>
<html lang="en">
""" + head + """
""" + body + """
</html>
"""
        out = SanitationUtils.coerce_unicode(out)
        return out

    def get_document_unicode(self):
        return SanitationUtils.coerce_unicode(self.get_document())

    def add_csv_file(self, name, path):
        Registrar.register_message(
            "wrote %s CSV file to %s" % (name, path)
        )
        self.csv_files[name] = path

    def add_html_file(self, name, path):
        Registrar.register_message(
            "wrote %s HTML file to %s" % (name, path)
        )
        self.html_files[name] = path

    def write_to_file(self, name, path):
        with io.open(path, 'w+', encoding='utf8') as rep_file:
            rep_file.write(self.get_document_unicode())
        self.add_html_file(name, path)


def do_duplicates_summary_group(reporter, matches, updates, parsers, settings):
    help_instructions = (
        "<p>This is a detailed report of all the duplicated and conflicting records. "
        "Ideally this report would be empty. </p>"
        "<h3>Sections</h3>"
        "<p><strong>Usernamematcher.Duplicate_Matches</strong> are instances where "
        "multiple records from a single database were found to have the same username "
        "which is certainly an indicator of erroneous data.</p>"
        "<h3>Colours</h3>"
        "<p class='highlight_master'><strong>Master</strong> Master records are "
        "highlighted with a light pink background<p>"
        "<p class='highlight_slave'><strong>Slave</strong> Slave records are "
        "highlighted with a light blue background<p>"
        "<p class='highlight_old'><strong>Old Records</strong> Old records are "
        "highlighted with a red font. By default these are older than 5 years<p>"
        "<p class='highlight_oldish'><strong>Old-ish Records</strong> Old-ish records are "
        "highlighted with a red font. By default these are older than 3 years<p>"
    ).format(
        master_name=settings.master_name,
        slave_name=settings.slave_name,
        master_pkey="MYOB Card ID",
        slave_pkey="WP ID"
    )
    group = HtmlReporter.Group('summary_group', 'Summary')
    group.add_section(
        HtmlReporter.Section(
            'instructions',
            title='Instructions',
            data=help_instructions
        )
    )
    reporter.add_group(group)

def do_duplicates_group(reporter, matches, updates, parsers, settings):

    group = HtmlReporter.Group('dup', 'Duplicate Results')

    dup_cols = OrderedDict(settings.basic_cols.items() + [
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
                try:
                    user_time_obj = getattr(user_data, 'act_last_transaction')
                except AssertionError:
                    return True
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
                object_data.act_last_transaction
            ) or "UNKN"
            duplicates.add_conflictor(
                object_data, "last_transaction_old", 0.5, details)
        elif fn_user_older_than_wp(settings['oldish_threshold'])(object_data):
            details = TimeUtils.wp_time_to_string(
                object_data.act_last_transaction
            ) or "UNKN"
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
        group.add_section(
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
    group.add_section(
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
        group.add_section(
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

    if address_duplicates:

        print "there are address duplicates"
        group.add_section(
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
                tablefmt="html",
                # highlight_rules=highlight_rules_all
            )
            # TODO: maybe re-enable highlight rules?
        group.add_section(
            HtmlReporter.Section(
                matchlist_type,
                **{
                    # 'title': matchlist_type.title(),
                    'description': description,
                    'data': data,
                    'length': len(match_list)
                }))

    reporter.add_group(group)


def do_main_summary_group(reporter, matches, updates, parsers, settings):
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

    group = HtmlReporter.Group('summary_group', 'Summary')
    group.add_section(
        HtmlReporter.Section(
            'instructions',
            title='Instructions',
            data=help_instructions
        )
    )
    reporter.add_group(group)

def do_sanitizing_group(reporter, matches, updates, parsers, settings):
    address_cols = OrderedDict(settings.basic_cols.items() + [
        ('address_reason', {}),
        ('Edited Address', {}),
        ('Edited Alt Address', {}),
    ])
    name_cols = OrderedDict(settings.basic_cols.items() + [
        ('name_reason', {}),
        ('Edited Name', {}),
    ])

    group = HtmlReporter.Group('sanitizing',
                                          'Sanitizing Results')

    if parsers.slave.bad_address:
        group.add_section(
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
        group.add_section(
            HtmlReporter.Section(
                's_bad_names_list',
                title='Bad %s Names List' % settings.slave_name.title(),
                description='%s records that have badly formatted names' %
                settings.slave_name,
                data=UsrObjList(parsers.slave.bad_name.values()).tabulate(
                    cols=name_cols,
                    tablefmt='html', ),
                length=len(parsers.slave.bad_name)))

    if parsers.master.bad_address:
        group.add_section(
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
        group.add_section(
            HtmlReporter.Section(
                'm_bad_names_list',
                title='Bad %s Names List' % settings.master_name.title(),
                description='%s records that have badly formatted names' %
                settings.master_name,
                data=UsrObjList(parsers.master.bad_name.values()).tabulate(
                    cols=name_cols,
                    tablefmt='html', ),
                length=len(parsers.master.bad_name)))

    reporter.add_group(group)

def do_delta_group(reporter, matches, updates, parsers, settings):
    if not (settings.do_sync and (updates.delta_master + updates.delta_slave)):
        return

    settings.master_delta_csv_path = os.path.join(
        settings.out_dir_full,
        "%sdelta_report_%s_%s.csv" % \
            (settings.file_prefix, settings.master_name, settings.file_suffix))
    settings.slave_delta_csv_path = os.path.join(
        settings.out_dir_full,
        "%sdelta_report_%s_%s.csv" % \
            (settings.file_prefix, settings.slave_name, settings.file_suffix))

    group = HtmlReporter.Group('deltas', 'Field Changes')

    m_delta_list = UsrObjList(
        filter(None, [update.new_m_object
                      for update in updates.delta_master]))

    s_delta_list = UsrObjList(
        filter(None, [update.new_s_object
                      for update in updates.delta_slave]))

    delta_cols = settings.col_data_class.get_delta_cols()

    all_delta_cols = OrderedDict(
        settings.basic_cols.items()
        + settings.col_data_class.name_cols(
            delta_cols.keys() + delta_cols.values()
        ).items())

    if m_delta_list:
        group.add_section(
            HtmlReporter.Section(
                'm_deltas',
                title='%s Changes List' % settings.master_name.title(),
                description='%s records that have changed important fields'
                % settings.master_name,
                data=m_delta_list.tabulate(
                    cols=all_delta_cols, tablefmt='html'),
                length=len(m_delta_list)))

    if s_delta_list:
        group.add_section(
            HtmlReporter.Section(
                's_deltas',
                title='%s Changes List' % settings.slave_name.title(),
                description='%s records that have changed important fields'
                % settings.slave_name,
                data=s_delta_list.tabulate(
                    cols=all_delta_cols, tablefmt='html'),
                length=len(s_delta_list)))

    if m_delta_list:
        m_delta_list.export_items(
            settings['master_delta_csv_path'],
            settings.col_data_class.get_col_names(all_delta_cols))
        reporter.add_csv_file('master_delta', settings['master_delta_csv_path'])
    if s_delta_list:
        s_delta_list.export_items(
            settings['slave_delta_csv_path'],
            settings.col_data_class.get_col_names(all_delta_cols))
        reporter.add_csv_file('slave_delta', settings['slave_delta_csv_path'])

    reporter.add_group(group)

def do_matches_group(reporter, matches, updates, parsers, settings):
    group = HtmlReporter.Group('matching', 'Matching Results')
    group.add_section(
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
        group.add_section(
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
        "sa_parser.noemails":
        "%s records have invalid emails" % settings.slave_name,
        "ma_parser.noemails":
        "%s records have invalid emails" % settings.master_name,
        "ma_parser.nocards":
        "%s records have no cards" % settings.master_name,
        "sa_parser.nousernames":
        "%s records have no username" % settings.slave_name
    }

    for parselist_type, parse_list in parsers.anomalous.items():
        description = parse_list_instructions.get(parselist_type,
                                                  parselist_type)
        usr_list = UsrObjList()
        for obj in parse_list.values():
            usr_list.append(obj)

        data = usr_list.tabulate(tablefmt="html")

        group.add_section(
            HtmlReporter.Section(
                parselist_type,
                **{
                    # 'title': matchlist_type.title(),
                    'description': description,
                    'data': data,
                    'length': len(parse_list)
                }))

    reporter.add_group(group)

def do_sync_group(reporter, matches, updates, parsers, settings):
    if not settings.do_sync:
        return

    group = HtmlReporter.Group('sync', 'Syncing Results')

    group.add_section(
        HtmlReporter.Section(
            (settings.master_name + "_updates"),
            description=settings.master_name +
            " items will be updated",
            data='<hr>'.join([
                update.tabulate(tablefmt="html")
                for update in updates.master
            ]),
            length=len(updates.master)))

    group.add_section(
        HtmlReporter.Section(
            (settings.slave_name + "_updates"),
            description=settings.slave_name + " items will be updated",
            data='<hr>'.join([
                update.tabulate(tablefmt="html")
                for update in updates.slave
            ]),
            length=len(updates.slave)))

    group.add_section(
        HtmlReporter.Section(
            "updates.problematic",
            description="items can't be merged because they are too dissimilar",
            data='<hr>'.join([
                update.tabulate(tablefmt="html")
                for update in updates.problematic
            ]),
            length=len(updates.problematic)))

    reporter.add_group(group)

def do_report_bad_contact(reporter, matches, updates, parsers, settings):
    settings.w_pres_csv_path = os.path.join(
        settings.out_dir_full,
        "%ssync_report_%s_%s.csv" % \
            (settings.file_prefix, settings.slave_name, settings.file_suffix))
    settings.master_res_csv_path = os.path.join(
        settings.out_dir_full,
        "%ssync_report_%s_%s.csv" % \
            (settings.file_prefix, settings.master_name, settings.file_suffix))

    csv_colnames = settings.col_data_class.get_col_names(
        OrderedDict(settings.basic_cols.items() + settings.col_data_class.name_cols([
            'address_reason',
            'name_reason',
            'Edited Name',
            'Edited Address',
            'Edited Alt Address',
        ]).items()))

    if parsers.master.bad_name or parsers.master.bad_address:
        UsrObjList(parsers.master.bad_name.values() + parsers.master.bad_address.values())\
            .export_items(settings['master_res_csv_path'], csv_colnames)
        reporter.add_csv_file('master_bad_name', settings['master_res_csv_path'])


    if parsers.slave.bad_name or parsers.slave.bad_address:
        UsrObjList(parsers.slave.bad_name.values() + parsers.master.bad_address.
                   values()).export_items(settings['w_pres_csv_path'], csv_colnames)
        reporter.add_csv_file('slave_bad_name', settings['w_pres_csv_path'])

def do_report_failures(reporter, failures, settings):
    """Output a list of lists of failures as a csv file to the path specified."""
    for source in ['master', 'slave']:
        failures = getattr(failures, source)

        # TODO: Write failure HTML report here

        file_path = settings.get(source[0] + '_fail_path_full')
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
        reporter.add_csv_file(source, file_path)
