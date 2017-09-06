from __future__ import absolute_import, unicode_literals

import argparse
import io
import re
from collections import OrderedDict
from string import Formatter
import functools

import unicodecsv
import tabulate

from woogenerator.duplicates import Duplicates
from woogenerator.parsing.user import UsrObjList

from .clock import TimeUtils
from .core import Registrar, SanitationUtils


class ReporterNamespace(argparse.Namespace):
    """ Collect variables used in reporting into a single namespace. """

    reporter_attrs = ['main', 'dup', 'san', 'match', 'post']

    def __init__(self, *args, **kwargs):
        super(ReporterNamespace, self).__init__(*args, **kwargs)
        self.main = RenderableReporter()
        self.dup = RenderableReporter(css=DUP_CSS)
        self.san = RenderableReporter()
        self.match = RenderableReporter()
        self.post = RenderableReporter()

    @property
    def as_dict(self):
        return dict([
            (attr, getattr(self, attr)) \
            for attr in self.reporter_attrs \
            if hasattr(self, attr)
        ])

    def get_csv_files(self):
        csv_files = OrderedDict()
        for reporter in self.as_dict.values():
            csv_files.update(reporter.csv_files)
        return csv_files

    def get_html_files(self):
        html_files = OrderedDict()
        for reporter in self.as_dict.values():
            html_files.update(reporter.html_files)
        return html_files

DUP_CSS = "\n".join([
    ".highlight_old {color: red !important; }"
    ".highlight_oldish {color: orange;}"
    ".highlight_master {background: lightblue !important;}"
    ".highlight_slave {background: lightpink !important;}"
])

class OptionalFormatter(Formatter):
    """ Formatter where keys are optional """
    def get_value(self, key, args, kwds):
        if isinstance(key, basestring):
            return kwds.get(key, '')
        return Formatter.get_value(self, key, args, kwds)

class AbstractReporter(object):
    formatter = OptionalFormatter()
    def __init__(self, css=None):
        self.groups = OrderedDict()
        self.css = css
        self.csv_files = OrderedDict()
        self.html_files = OrderedDict()
        self.non_instructionals = []

    class Section(object):
        def __init__(self, classname, title=None,
                     description="", data="", length=None):
            if title is None:
                title = classname.title()
            self.title = title
            self.description = description
            self.data = data
            self.length = length
            self.classname = classname

        @classmethod
        def format(cls, *args, **kwargs):
            return AbstractReporter.format(*args, **kwargs)

        @classmethod
        def get_data_heading_fmt(cls, fmt):
            if fmt=='html':
                return u"<h3>{heading}</h3>"
            else:
                return u"*{heading}*"

        @classmethod
        def get_data_separator(cls, fmt):
            if fmt=='html':
                return u"<hr>"
            else:
                return u"\n" + ("-" * 50) + "\n"

        @classmethod
        def get_title_fmt(cls, fmt=None):
            if fmt=='html':
                return u"<h2>{title}</h2>"
            return u"\n**{title}**\n"

        @classmethod
        def get_descr_fmt(cls, fmt=None):
            if fmt=='html':
                return (u'<p class="description {class}">'
                        u'<strong>{strong}</strong>{description}</p>')
            return u"\n{strong}{description}"

        @classmethod
        def get_data_fmt(cls, fmt=None):
            if fmt=='html':
                return u'<p class="data {class}">{data}</p>'
            return u'\n{data}'

        def get_section_fmt(self, fmt=None):
            if not fmt == 'html':
                return u"{title}{description}{data}"
            section_id = SanitationUtils.make_safe_class(self.classname)
            section_id = SanitationUtils.coerce_unicode(section_id)
            out = u'<div class="section">'
            out += self.format(
                (u'<a data-toggle="collapse" href="#{0}" aria-expanded="true" '
                 u'data-target="#{0}" aria-controls="{0}">'),
                section_id
            )
            out += u"{title}"
            out += u"</a>"
            out += u'<div class="collapse" id="' + section_id + '">'
            out += u"{description}"
            out += u"{data}"
            out += u'</div>'
            return out


        def render_title(self, fmt=None):
            response = self.title
            response = SanitationUtils.coerce_unicode(response)
            if self.length:
                response += u' ({})'.format(self.length)
            response = self.format(self.get_title_fmt(fmt), title=response)
            return response

        def render_description(self, fmt=None):
            response = self.description
            response = SanitationUtils.coerce_unicode(response)
            if self.length is not None:
                response = u"{length} ".format(length=self.length) + response
            response = self.format(self.get_descr_fmt(fmt), description=response)
            return response

        def render_data(self, fmt=None):
            response = self.data
            response = SanitationUtils.coerce_unicode(response)
            if fmt == 'html':
                response = re.sub(
                    ur"<table>", ur'<table class="table table-striped">', response
                )
            response = self.format(self.get_data_fmt(fmt), data=response)
            return response

        def render(self, fmt=None):
            data = self.render_data(fmt)
            data = SanitationUtils.coerce_unicode(data)

            out = self.format(
                self.get_section_fmt(fmt),
                title=self.render_title(fmt),
                data=data,
                description=self.render_description(fmt)
            )

            out = SanitationUtils.coerce_unicode(out)
            return out

        def to_html(self):
            return self.render('html')

        def to_text(self):
            return self.render()

    class Group(object):

        def __init__(self, classname, title=None, sections=None, instructional=False):
            if title is None:
                title = classname.title()
            if sections is None:
                sections = OrderedDict()
            self.title = title
            self.sections = sections
            self.classname = classname
            self.instructional = instructional

        def add_section(self, section):
            self.sections[section.classname] = section

        @classmethod
        def format(cls, *args, **kwargs):
            return AbstractReporter.format(*args, **kwargs)

        @classmethod
        def get_title_fmt(cls, fmt=None):
            if fmt == 'html':
                return "<h1>{title}</h1>"
            else:
                return "\n***{title}***\n"

        @classmethod
        def get_group_div_fmt(cls, fmt=None):
            if fmt == 'html':
                return '<div class="group {class}">{group}</div>'
            else:
                return '\n{group}'

        def render(self, fmt=None):
            out = ''
            out += self.format(self.get_title_fmt(fmt), title=self.title)
            for section in self.sections.values():
                out += section.render(fmt)
            out = self.format(self.get_group_div_fmt(fmt), group=out)
            out = SanitationUtils.coerce_unicode(out)
            return out

        def to_html(self):
            return self.render('html')

        def to_text(self):
            return self.render()


    @classmethod
    def format(cls, format_spec, *format_args, **format_kwargs):
        return cls.formatter.format(
            format_spec, *format_args, **format_kwargs
        )

    def yield_noninstructional_groups(self):
        for group in self.groups.values():
            if not group.instructional:
                return group

    @property
    def contains_noninstructinoal_groups(self):
        if list(self.yield_noninstructional_groups()):
            return True

    def __bool__(self):
        return self.contains_noninstructinoal_groups

    def add_group(self, group):
        self.groups[group.classname] = group

    def add_groups(self, *groups):
        for group in groups:
            self.add_group(group)

    def get_css(self):
        response = ''
        if self.css:
            response = "<style>" + self.css + "</style>"
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
        response = """\
    <!-- Latest compiled and minified CSS -->
""" + bootstrap_link + """
    <!-- Optional theme -->
""" + bootstrap_theme_link + """
        """
        return response

    def get_head(self):
        return """\
<head>
    <meta charset="UTF-8">
""" + self.get_css() + """
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
        response = "<br/>".join(group.to_html() for group in self.groups.values())
        response = re.sub(
            ur'<div class="collapse" ', ur'<div ', response
        )
        response = self.get_css() + "<br/>" + response
        return response

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

    def write_document_to_file(self, name, path):
        with io.open(path, 'w+', encoding='utf8') as rep_file:
            rep_file.write(self.get_document_unicode())
        self.add_html_file(name, path)

class HtmlReporter(AbstractReporter):
    """**DEPRECATED** Reporter which produces only html"""

class RenderableReporter(AbstractReporter):
    """ Report renderable objects in html or plaintext. """

    class Section(AbstractReporter.Section):
        def render_data(self, fmt=None):
            response = self.data(fmt)
            response = SanitationUtils.coerce_unicode(response)
            if fmt == 'html':
                response = re.sub(
                    ur"<table>", ur'<table class="table table-striped">', response
                )
            response = self.format(self.get_data_fmt(fmt), data=response)
            return response

def do_duplicates_summary_group(reporter, matches, updates, parsers, settings):
    def render_help_instructions(fmt=None):
        response = u""
        format_params = [
            (reporter.Section.get_descr_fmt(fmt), {
                'description':(
                    "This is a detailed report of all the duplicated and "
                    "conflicting records. Ideally this report would be empty."
                )
            }),
            (reporter.Section.get_data_heading_fmt(fmt), {'heading':'Sections'}),
            (reporter.Section.get_descr_fmt(fmt), {
                'strong':'Usernamematcher.Duplicate_Matches',
                'description':(
                    " are instances where multiple records from a single database "
                    "were found to have the same username which is certainly an "
                    "indicator of erroneous data."
                )
            }),
        ]
        if fmt == 'html': format_params += [
            (reporter.Section.get_data_heading_fmt(fmt), {'heading':'Colours'}),
            (reporter.Section.get_descr_fmt(fmt), {
                'class':'highlight_master',
                'strong':settings.master_name,
                'description':" records are highlighted with a light blue background"
            }),
            (reporter.Section.get_descr_fmt(fmt), {
                'class':'highlight_slave',
                'strong':settings.slave_name,
                'description':" records are highlighted with a light pink background"
            }),
            (reporter.Section.get_descr_fmt(fmt), {
                'class':'highlight_old',
                'strong':'Old',
                'description':(" records are highlighted with a red font. "
                                "By default these are older than 5 years")
            }),
            (reporter.Section.get_descr_fmt(fmt), {
                'class':'highlight_oldish',
                'strong':'Old-ish',
                'description':(" records are highlighted with an orange font. "
                                "By default these are older than 3 years")
            })
        ]
        for format_spec, format_kwargs in format_params:
            response += reporter.format(format_spec, **format_kwargs)
        return response

    group = reporter.Group('summary_group', 'Summary', instructional=True)
    group.add_section(
        reporter.Section(
            'instructions',
            title='Instructions',
            data=render_help_instructions
        )
    )
    reporter.add_group(group)

def do_duplicates_group(reporter, matches, updates, parsers, settings):

    group = reporter.Group('dup', 'Duplicate Results')

    dup_cols = OrderedDict(settings.basic_cols.items() + [
        # ('Create Date', {}),
        # ('Last Sale', {})
    ])

    # What we're doing here is analysing the duplicates we've seen so far, and
    # creating a list of all the potential objects to delete and WHY
    # they should be deleted.

    def obj_source_is(object_data, target_source):
        """Check if the object source equals target source."""
        obj_source = object_data.get('source')
        if obj_source and target_source == obj_source:
            return True

    def fn_obj_source_is(target_source):
        """Return function that checks if object source equals target source."""
        return functools.partial(obj_source_is, target_source=target_source)

    def user_older_than(user_data, wp_time_obj):
        """Determine if user is older than a given wp_time object."""
        if fn_obj_source_is(settings.master_name)(user_data):
            try:
                user_time_obj = getattr(user_data, 'act_last_transaction')
            except AssertionError:
                return True
        else:
            user_time_obj = user_data.last_modtime
        return user_time_obj < wp_time_obj

    def fn_user_older_than_wp(wp_time):
        """Return function ot check user is older than wp_time."""
        wp_time_obj = TimeUtils.wp_strp_mktime(wp_time)
        assert wp_time_obj, "should be valid time struct: %s" % wp_time
        return functools.partial(user_older_than, wp_time_obj=wp_time_obj)

    duplicates = Duplicates()

    for duplicate_type, duplicate_matchlist in matches.duplicate.items(
    ):
        # print "checking duplicates of type %s" % duplicate_type
        # print "len(duplicate_matchlist) %s" % len(duplicate_matchlist)
        for match in duplicate_matchlist:
            if match.m_len <= 1:
                continue
                # only care about master duplicates at the moment
            duplicate_objects = list(match.m_objects)
            duplicates.add_conflictors(duplicate_objects, duplicate_type)

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

    fn_usr_oldish = fn_user_older_than_wp(settings['oldish_threshold'])
    fn_usr_old = fn_user_older_than_wp(settings['old_threshold'])
    assert id(fn_usr_old) != id(fn_usr_oldish)

    highlight_rules_old = [
        ('highlight_oldish', fn_usr_oldish),
        ('highlight_old', fn_usr_old)
    ]

    highlight_rules_all = highlight_rules_master_slave + highlight_rules_old

    if Registrar.DEBUG_DUPLICATES:
        # print duplicates.tabulate({}, tablefmt='plain')
        if duplicates:
            def render_all_duplicates(fmt):
                return duplicates.tabulate(
                    dup_cols, tablefmt=fmt, highlight_rules=highlight_rules_all
                )

            group.add_section(
                reporter.Section(
                    'all duplicates',
                    title='All Duplicates',
                    description="%s records are involved in duplicates" %
                    settings.master_name,
                    data=render_all_duplicates,
                    length=len(duplicates)
                ))

    if matches.conflict['email']:
        def render_email_conflicts(fmt):
            return matches.conflict['email'].tabulate(
                cols=dup_cols,
                tablefmt=fmt,
                highlight_rules=highlight_rules_all
            )

        group.add_section(
            reporter.Section(
                "email conflicts",
                description= "email conflicts",
                data= render_email_conflicts,
                length= len(matches.conflict['email'])
            )
        )

    if matches.duplicate['email']:
        def render_email_duplicates(fmt):
            return matches.duplicate['email'].tabulate(
                tablefmt=fmt,
                highlight_rules=highlight_rules_all
            )

        group.add_section(
            reporter.Section(
                'email_duplicates',
                title='Email Duplicates',
                description="%s records match with multiple records in %s on email" % (
                    settings.slave_name, settings.master_name
                ),
                data= render_email_duplicates,
                length= len(matches.duplicate['email'])
            ))

    if address_duplicates:
        def render_address_duplicates(fmt):
            duplicate_delmieter = reporter.Section.get_data_separator(fmt)
            if fmt == 'html':
                duplicate_format = u"<h4>%s</h4><p>%s</p>"
            else:
                duplicate_format = u"**%s**\n%s"
            return duplicate_delmieter.join([
                duplicate_format % (
                    address,
                    UsrObjList(objects).tabulate(
                        cols=dup_cols,
                        tablefmt=fmt,
                        highlight_rules=highlight_rules_all
                    )
                ) for address, objects in address_duplicates.items()
            ])
        group.add_section(
            reporter.Section(
                'address_duplicates',
                title='Duplicate %s Addresses' % settings.master_name.title(),
                description='%s addresses that appear in multiple records' % settings.master_name,
                data=render_address_duplicates,
                length=len(address_duplicates)
            )
        )


    match_list_instructions = {
        'cardMatcher.duplicate_matches':
        '%s records have multiple CARD IDs in %s' % (
            settings.slave_name, settings.master_name
        ),
        'usernameMatcher.duplicate_matches':
        '%s records have multiple USERNAMEs in %s' % (
            settings.slave_name, settings.master_name
        )
    }

    def render_matchlist_data(fmt, match_list, matchlist_type):
        if 'masterless' in matchlist_type or 'slaveless' in matchlist_type:
            data = match_list.merge().tabulate(tablefmt=fmt)
        else:
            data = match_list.tabulate(
                tablefmt=fmt,
                highlight_rules=highlight_rules_all
            )
        return data

    for matchlist_type, match_list in matches.anomalous.items():
        if not match_list:
            continue
        description = match_list_instructions.get(matchlist_type, matchlist_type)
        group.add_section(
            reporter.Section(
                matchlist_type,
                title=matchlist_type.title(),
                description=description,
                data=functools.partial(
                    render_matchlist_data,
                    matchlist_type=matchlist_type,
                    match_list=match_list
                ),
                length=len(match_list)
            )
        )

    reporter.add_group(group)


def do_main_summary_group(reporter, matches, updates, parsers, settings):
    def render_help_instructions(fmt=None):
        response = u""
        for format_spec, format_kwargs in [
            (reporter.Section.get_descr_fmt(fmt), {
                'description':(
                    "This is a detailed report of all the changes that will be "
                    "made if this sync were to go ahead."
                )
            }),
            (reporter.Section.get_data_heading_fmt(fmt), {'heading':'Field Changes'}),
            (reporter.Section.get_descr_fmt(fmt), {
                'description':(
                    "These reports show all the changes that will happen to "
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
                    "customer from being able to log in or purchase items correctly."
                )
            }),
            (reporter.Section.get_data_heading_fmt(fmt), {'heading':'Syncing Results'}),
            (reporter.Section.get_descr_fmt(fmt), {
                'description':(
                    "Each of the items in these reports has the following sections:"
                )
            }),
            (reporter.Section.get_descr_fmt(fmt), {
                'strong':'Update Name',
                'description':(
                    " - The primary keys of the records being synchronized "
                    "({master_pkey} and {slave_pkey}) which should be unique "
                    "for any matched records."
                )
            }),
            (reporter.Section.get_descr_fmt(fmt), {
                'strong':'OLD',
                'description':(
                    " - The {master_name} and {slave_name} records before the sync."
                )
            }),
            (reporter.Section.get_descr_fmt(fmt), {
                'strong':'INFO',
                'description':(
                    " - Mostly information about mod times for debugging."
                )
            }),
            (reporter.Section.get_descr_fmt(fmt), {
                'strong':'PROBLEMATIC CHANGES',
                'description':(
                    " - instances where an important field has been changed. "
                    "Important fields can be configured in coldata.py by "
                    "changing the 'static' property."
                )
            }),
            (reporter.Section.get_descr_fmt(fmt), {
                'strong':'CHANGES',
                'description': " - all changes including problematic."
            }),
            (reporter.Section.get_descr_fmt(fmt), {
                'strong':'NEW',
                'description':(
                    " - the end result of all changed records after"
                    "syncing"
                )
            }),
        ]:
            if 'description' in format_kwargs:
                format_kwargs['description'] = format_kwargs['description'].format(
                    master_name=settings.master_name,
                    slave_name=settings.slave_name,
                    master_pkey="MYOB Card ID",
                    slave_pkey="WP ID"
                )
            response += reporter.format(format_spec, **format_kwargs)
        return response

    group = reporter.Group('summary_group', 'Summary', instructional=True)
    group.add_section(
        reporter.Section(
            'instructions',
            title='Instructions',
            data=render_help_instructions
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
    csv_colnames = settings.col_data_class.get_col_names(
        OrderedDict(settings.basic_cols.items() + settings.col_data_class.name_cols([
            'address_reason',
            'name_reason',
            'Edited Name',
            'Edited Address',
            'Edited Alt Address',
        ]).items()))

    group = reporter.Group('sanitizing', 'Sanitizing Results')

    def render_bad_register(fmt, register, cols):
        users = UsrObjList(register.values())
        return users.tabulate(
            cols=address_cols,
            tablefmt=fmt
        )

    for source in ['master', 'slave']:
        parser = getattr(parsers, source)

        if not (parser.bad_name or parser.bad_address):
            continue

        for attr, cols, descr_fmt in [
            (
                'bad_address',
                address_cols,
                '%s records that have badly formatted addresses'
            ),
            (
                'bad_name',
                name_cols,
                '%s records that have badly formatted names'
            )
        ]:
            register = getattr(parser, attr)
            if not register:
                continue
            source_name = settings.get('%s_name' % source)
            group.add_section(
                reporter.Section(
                    title="%s %s" % (attr.title(), source_name.title()),
                    description=descr_fmt % source_name,
                    data=functools.partial(
                        render_bad_register, register=register, cols=cols
                    ),
                    length=len(register)
                )
            )

        bad_users = UsrObjList(
            parser.bad_name.values() + parser.bad_address.values()
        )
        report_path = settings.get('rep_san_%s_csv_path' % source)
        bad_users.export_items(report_path, csv_colnames)
        reporter.add_csv_file('master_sanitation', report_path)

    reporter.add_group(group)

def do_delta_group(reporter, matches, updates, parsers, settings):
    if not (settings.do_sync and (updates.delta_master + updates.delta_slave)):
        return

    group = reporter.Group('deltas', 'Field Changes')

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

    def render_delta_list(fmt, delta_list):
        return delta_list.tabulate(
            cols=all_delta_cols, tablefmt=fmt
        )

    for source, delta_list in [
        ('master', m_delta_list),
        ('slave', s_delta_list)
    ]:
        if not delta_list:
            continue

        source_name = settings.get("%s_name" % source, '')

        group.add_section(
            reporter.Section(
                "%s_deltas" % source,
                title="%s Changes List" % source_name.title(),
                description="%s records that have changed important fields" % (
                    source_name
                ),
                data=functools.partial(render_delta_list, delta_list=delta_list),
                length=len(delta_list)
            )
        )

        csv_path = settings.get('rep_delta_%s_csv_path' % source)

        delta_list.export_items(
            csv_path,
            settings.col_data_class.get_col_names(all_delta_cols))
        reporter.add_csv_file(
            'delta_%s' % source,
            csv_path
        )

    reporter.add_group(group)

def do_matches_summary_group(reporter, matches, updates, parsers, settings):
    def render_help_instructions(fmt=None):
        response = u""
        for format_spec, format_kwargs in [
            (reporter.Section.get_descr_fmt(fmt), {
                'description':(
                    "These reports show the results of the matching algorithm. "
                )
            }),
            (reporter.Section.get_descr_fmt(fmt), {
                'strong':'Perfect Matches',
                'description':(
                    " show matches that were detected without ambiguity."
                )
            }),
            (reporter.Section.get_descr_fmt(fmt), {
                'strong':'Masterless Card Matches',
                'description':(
                    " are instances where a record in {slave_name} is seen to "
                    "have a {master_pkey} value that is that is not found in "
                    "{master_name}. This could mean that the {master_name} "
                    "record associated with that user has been deleted or badly "
                    "merged."
                )
            }),
            (reporter.Section.get_descr_fmt(fmt), {
                'strong':'Slaveless Username Matches',
                'description':(
                    " are instances where a record in {master_name} has a "
                    "username value that is not found in {slave_name}. This "
                    "could be because the {slave_name} account was deleted."
                )
            })
        ]:
            if 'description' in format_kwargs:
                format_kwargs['description'] = format_kwargs['description'].format(
                    master_name=settings.master_name,
                    slave_name=settings.slave_name,
                    master_pkey="MYOB Card ID",
                    slave_pkey="WP ID"
                )
            response += reporter.format(format_spec, **format_kwargs)
        return response

    group = reporter.Group('summary_group', 'Summary', instructional=True)
    group.add_section(
        reporter.Section(
            'instructions',
            title='Instructions',
            data=render_help_instructions
        )
    )
    reporter.add_group(group)


def do_matches_group(reporter, matches, updates, parsers, settings):
    group = reporter.Group('matching', 'Matching Results')
    def render_perfect_matches(fmt):
        return matches.globals.tabulate(tablefmt=fmt)

    group.add_section(
        reporter.Section(
            'perfect_matches',
            title='Perfect Matches',
            description="%s records match well with %s" % (
                settings.slave_name, settings.master_name),
            data=render_perfect_matches,
            length=len(matches.globals)
        )
    )

    match_list_instructions = {
        'cardMatcher.masterless_matches':
        '%s records do not have a corresponding CARD ID in %s (deleted?)' % (
            settings.slave_name, settings.master_name
        ),
        'usernameMatcher.slaveless_matches':
        '%s records have no USERNAMEs in %s' % (
            settings.master_name, settings.slave_name
        ),
    }

    def render_matchlist_data(fmt, match_list, matchlist_type):
        if 'masterless' in matchlist_type or 'slaveless' in matchlist_type:
            data = match_list.merge().tabulate(tablefmt=fmt)
        else:
            data = match_list.tabulate(
                tablefmt=fmt,
            )
        return data

    for matchlist_type, match_list in matches.anomalous.items():
        if not match_list:
            continue
        description = match_list_instructions.get(matchlist_type, matchlist_type)
        group.add_section(
            reporter.Section(
                matchlist_type,
                title=matchlist_type.title(),
                description=description,
                data=functools.partial(
                    render_matchlist_data,
                    matchlist_type=matchlist_type,
                    match_list=match_list
                ),
                length=len(match_list)
            )
        )

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

    def render_parselist_data(fmt, parse_list, parselist_type):
        usr_list = UsrObjList()
        for obj in parse_list.values():
            usr_list.append(obj)
        return usr_list.tabulate(tablefmt=fmt)

    for parselist_type, parse_list in parsers.anomalous.items():
        if not parse_list:
            continue
        description = parse_list_instructions.get(parselist_type, parselist_type)
        group.add_section(
            reporter.Section(
                parselist_type,
                title=parselist_type.title(),
                description=description,
                data=functools.partial(
                    render_parselist_data,
                    parselist_type=parselist_type,
                    parse_list=parse_list
                ),
                length=len(parse_list)
            )
        )

    reporter.add_group(group)

def render_update_list(fmt, reporter, update_list):
    delimeter = reporter.Section.get_data_separator(fmt)
    return delimeter.join([
        update.tabulate(tablefmt=fmt) for update in update_list
    ])

def do_sync_group(reporter, matches, updates, parsers, settings):
    if not settings.do_sync:
        return

    group = reporter.Group('sync', 'Syncing Results')

    for attr, name, description in [
        (
            'master',
            settings.master_name + "_updates",
            settings.master_name + " items will be updated"
        ),
        (
            'slave',
            settings.slave_name + "_updates",
            settings.slave_name + " items will be updated"
        ),
        (
            'problematic',
            "problematic_updates",
            "items can't be automatically merged because they are too dissimilar"
        )
    ]:
        target_update_list = getattr(updates, attr)
        group.add_section(
            reporter.Section(
                name,
                description=description,
                data=functools.partial(
                    render_update_list,
                    update_list=target_update_list,
                    reporter=reporter
                ),
                length=len(target_update_list)
            )
        )

    reporter.add_group(group)

def do_post_summary_group(reporter, settings):
    """ Create post-update summary report section. """
    group = reporter.Group('summary_group', 'Summary', instructional=True)

    def render_help_instructions(fmt=None):
        response = u""
        for format_spec, format_kwargs in [
            (reporter.Section.get_descr_fmt(fmt), {
                'description':(
                    "This is a sumary of the completed updates. "
                )
            }),
        ]:
            response += reporter.format(format_spec, **format_kwargs)
        return response

    group.add_section(
        reporter.Section(
            'instructions',
            title='Instructions',
            data=render_help_instructions
        )
    )
    reporter.add_group(group)


def do_failures_group(reporter, results, settings):
    """ Create failures report section. """

    group = reporter.Group('fail', 'Failed Updates')

    for source in ['master', 'slave']:
        source_failures = getattr(results, 'fails_%s' % source)
        if not source_failures:
            continue
        # TODO: Write failure HTML report here

        cols = [
            'update', 'master', 'slave', 'mchanges', 'schanges',
            'exception'
        ]

        name = '%s_fails' % source
        description = '%s records failed to sync because of an API client error' % source

        def render_fail_section(fmt, fails):
            return tabulate(fails, tablefmt=fmt)

        group.add_section(
            reporter.Section(
                name,
                description=description,
                data=functools.partial(render_fail_section, fails=source_failures),
                length=len(source_failures)
            )
        )

        file_path = settings.get('rep_fail_%s_csv_path' % source)
        if file_path:
            with open(file_path, 'w+') as out_file:
                # for failure in source_failures:
                #     Registrar.register_error(failure)
                dictwriter = unicodecsv.DictWriter(
                    out_file,
                    fieldnames=cols,
                    extrasaction='ignore', )
                dictwriter.writerows(source_failures)
            reporter.add_csv_file(source, file_path)

def do_successes_group(reporter, results, settings):
    """ Create successes report section. """

    group = reporter.Group('success', 'Succesful Updates')

    target_update_list = results.successes
    group.add_section(
        reporter.Section(
            'successes',
            description='updates completed succesfully',
            data=functools.partial(
                render_update_list,
                update_list=target_update_list,
                reporter=reporter
            ),
            length=len(target_update_list)
        )
    )
