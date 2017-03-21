import re
from collections import OrderedDict
import io

from core import SanitationUtils


class HtmlReporter(object):
    """docstring for htmlReporter"""

    class Section:
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

        def to_html(self):
            section_id = SanitationUtils.make_safe_class(self.classname)
            out = '<div class="section">'
            out += '<a data-toggle="collapse" href="#{0}" aria-expanded="true" data-target="#{0}" aria-controls="{0}">'.format(
                section_id)
            out += '<h2>' + self.title + \
                (' ({})'.format(self.length) if self.length else '') + '</h2>'
            out += '</a>'
            out += '<div class="collapse" id="' + section_id + '">'
            out += '<p class="description">' + \
                (str(self.length) if self.length else "No") + \
                ' ' + self.description + '</p>'
            out += '<p class="data">'
            out += re.sub("<table>", "<table class=\"table table-striped\">",
                          SanitationUtils.coerce_unicode(self.data))
            out += '</p>'
            out += '</div>'
            out = SanitationUtils.coerce_unicode(out)
            return out

    class Group:

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

        def to_html(self):
            out = '<div class="group">'
            out += '<h1>' + self.title + '</h1>'
            for section in self.sections.values():
                out += section.to_html()
            out += '</div>'
            out = SanitationUtils.coerce_unicode(out)
            return out

    def __init__(self, css=None):
        self.groups = OrderedDict()
        self.css = css

    def add_group(self, group):
        self.groups[group.classname] = group

    def get_head(self):
        css = ''
        if self.css:
            css = "<style>" + self.css + "</style>"
        return """\
<head>
    <meta charset="UTF-8">
    <!-- Latest compiled and minified CSS -->
    <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.6/css/bootstrap.min.css" integrity="sha384-1q8mTJOASx8j1Au+a5WDVnPi2lkFfwwEAa8hDDdjZlpLegxhjVME1fgjWPGmkzs7" crossorigin="anonymous">

    <!-- Optional theme -->
    <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.6/css/bootstrap-theme.min.css" integrity="sha384-fLW2N01lMqjakBkx3l/M9EahuwpSfeNvV63J5ezn3uZzapT0u7EYsXMjQV+0En5r" crossorigin="anonymous">
""" + css + """
</head>
"""

    def get_body(self):
        content = "<br/>".join(
            group.to_html() for group in self.groups.values()
        )
        out = """
<body>
""" + content + """
    <script src="https://ajax.googleapis.com/ajax/libs/jquery/2.1.4/jquery.min.js"></script>
    <script src="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.6/js/bootstrap.min.js" integrity="sha384-0mSbJDEHialfmuBBQP6A4Qrprq5OVfW37PRR3j5ELqxss1yVqOtnepnHVP9aJ7xS" crossorigin="anonymous"></script>
</body>
"""
        out = SanitationUtils.coerce_unicode(out)
        return out

    def get_document(self):
        head = self.get_head()
        body = self.get_body()
        out = """\
<!DOCTYPE html>
<html lang="en">
""" + head + """"
""" + body + """
</html>
"""
        out = SanitationUtils.coerce_unicode(out)
        return out

    def get_document_unicode(self):
        return SanitationUtils.coerce_unicode(self.get_document())


def test_html_reporter():
    with\
            open('../output/htmlReporterTest.html', 'w+') as res_file,\
            io.open('../output/htmlReporterTestU.html', 'w+', encoding="utf8") as ures_file:
        reporter = HtmlReporter()

        matching_group = HtmlReporter.Group('matching', 'Matching Results')

        matching_group.add_section(
            HtmlReporter.Section(
                'perfect_matches',
                **{
                    'title': 'Perfect Matches',
                    'description': "%s records match well with %s" % ("WP", "ACT"),
                    'data': u"<\U0001F44C'&>",
                    'length': 3
                }
            )
        )

        reporter.add_group(matching_group)

        document = reporter.get_document()
        # SanitationUtils.safe_print( document)
        ures_file.write(SanitationUtils.coerce_unicode(document))
        res_file.write(SanitationUtils.coerce_ascii(document))
