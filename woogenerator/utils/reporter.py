import re
from collections import OrderedDict
import io

from core import SanitationUtils

class HtmlReporter(object):
    """docstring for htmlReporter"""

    class Section:
        data_heading_fmt = "<h3>%s</h3>"
        data_separater = "<hr>"

        def __init__(self, classname, title = None, description = "", data = "", length = None):
            if title is None: title = classname.title()
            self.title = title
            self.description = description
            self.data = data
            self.length = length
            self.classname = classname

        def toHtml(self):
            sectionID = SanitationUtils.makeSafeClass(self.classname)
            out  = '<div class="section">'
            out += '<a data-toggle="collapse" href="#{0}" aria-expanded="true" data-target="#{0}" aria-controls="{0}">'.format(sectionID)
            out += '<h2>' + self.title + (' ({})'.format(self.length) if self.length else '') + '</h2>'
            out += '</a>'
            out += '<div class="collapse" id="' + sectionID + '">'
            out += '<p class="description">' + (str(self.length) if self.length else "No") + ' ' + self.description + '</p>'
            out += '<p class="data">'
            out += re.sub("<table>","<table class=\"table table-striped\">",SanitationUtils.coerceUnicode(self.data))
            out += '</p>'
            out += '</div>'
            out = SanitationUtils.coerceUnicode( out )
            return out


    class Group:
        def __init__(self, classname, title = None, sections = None):
            if title is None: title = classname.title()
            if sections is None: sections = OrderedDict()
            self.title = title
            self.sections = sections
            self.classname = classname

        def addSection(self, section):
            self.sections[section.classname] = section

        def toHtml(self):
            out  = '<div class="group">'
            out += '<h1>' + self.title + '</h1>'
            for section in self.sections.values():
                out += section.toHtml()
            out += '</div>'
            out = SanitationUtils.coerceUnicode( out )
            return out

    def __init__(self, css=None):
        self.groups = OrderedDict()
        self.css = css

    def addGroup( self, group):
        self.groups[group.classname] = group

    def getHead(self):
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

    def getBody(self):
        content = "<br/>".join(
            group.toHtml() for group in self.groups.values()
        )
        out = """
<body>
""" + content + """
    <script src="https://ajax.googleapis.com/ajax/libs/jquery/2.1.4/jquery.min.js"></script>
    <script src="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.6/js/bootstrap.min.js" integrity="sha384-0mSbJDEHialfmuBBQP6A4Qrprq5OVfW37PRR3j5ELqxss1yVqOtnepnHVP9aJ7xS" crossorigin="anonymous"></script>
</body>
"""
        out = SanitationUtils.coerceUnicode( out )
        return out

    def getDocument(self):
        head = self.getHead()
        body = self.getBody()
        out = """\
<!DOCTYPE html>
<html lang="en">
""" + head + """"
""" + body + """
</html>
"""
        out = SanitationUtils.coerceUnicode( out )
        return out

    def getDocumentUnicode(self):
        return SanitationUtils.coerceUnicode( self.getDocument() )

def testHTMLReporter():
    with\
             open('../output/htmlReporterTest.html', 'w+') as resFile,\
             io.open('../output/htmlReporterTestU.html', 'w+', encoding="utf8") as uresFile :
        reporter = HtmlReporter()

        matchingGroup = HtmlReporter.Group('matching', 'Matching Results')

        matchingGroup.addSection(
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

        reporter.addGroup(matchingGroup)

        document = reporter.getDocument()
        # SanitationUtils.safePrint( document)
        uresFile.write( SanitationUtils.coerceUnicode(document))
        resFile.write( SanitationUtils.coerceAscii(document) )
