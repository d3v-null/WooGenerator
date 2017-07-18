import os
import re
from collections import OrderedDict
from unittest import TestCase, main

from context import tests_datadir
from woogenerator.utils import SanitationUtils, Registrar
from woogenerator.parsing.abstract import ObjList
from woogenerator.parsing.dyn import CsvParseDyn


class TestParseDyn(TestCase):
    """
    Test the Dynamic pricing parsing functions of parsing.dyn
    """
    def setUp(self):
        Registrar.DEBUG_ERROR = False
        Registrar.DEBUG_WARN = False
        Registrar.DEBUG_MESSAGE = False

    def test_parse_dyn(self):

        dprp_path = os.path.join(tests_datadir, 'DPRP.csv')

        dyn_parser = CsvParseDyn()
        dyn_parser.analyse_file(dprp_path)

        self.assertTrue(dyn_parser.objects)

        # TODO: rewrite in htmlReporter

        # out_folder = "../output/"
        # out_path = os.path.join(out_folder, 'dynRules.html')
        # with open(out_path, 'w+') as out_file:
        #     def write_section(title, description, data, length=0,
        #                       html_class="results_section"):
        #         section_id = SanitationUtils.make_safe_class(title)
        #         description = "%s %s" % (
        #             str(length) if length else "No", description)
        #         out_file.write('<div class="%s">' % html_class)
        #         out_file.write(('<a data-toggle="collapse" href="#%s" aria-expanded="true" '
        #                         'data-target="#%s" aria-controls="%s">') %
        #                        (section_id, section_id, section_id))
        #         out_file.write('<h2>%s (%d)</h2>' % (title, length))
        #         out_file.write('</a>')
        #         out_file.write('<div class="collapse" id="%s">' % section_id)
        #         out_file.write('<p class="description">%s</p>' % description)
        #         out_file.write('<p class="data">')
        #         out_file.write(
        #             re.sub("<table>", "<table class=\"table table-striped\">", data))
        #         out_file.write('</p>')
        #         out_file.write('</div>')
        #         out_file.write('</div>')
        #     out_file.write('<!DOCTYPE html>')
        #     out_file.write('<html lang="en">')
        #     out_file.write('<head>')
        #     out_file.write("""
        # <!-- Latest compiled and minified CSS -->
        # <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.6/css/bootstrap.min.css" integrity="sha384-1q8mTJOASx8j1Au+a5WDVnPi2lkFfwwEAa8hDDdjZlpLegxhjVME1fgjWPGmkzs7" crossorigin="anonymous">
        #
        # <!-- Optional theme -->
        # <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.6/css/bootstrap-theme.min.css" integrity="sha384-fLW2N01lMqjakBkx3l/M9EahuwpSfeNvV63J5ezn3uZzapT0u7EYsXMjQV+0En5r" crossorigin="anonymous">
        # """)
        #     out_file.write('<body>')
        #     out_file.write('<div class="matching">')
        #     out_file.write('<h1>%s</h1>' % 'Dynamic Pricing Ruels Report')
        #     for rule in dyn_parser.taxos.values():
        #         rule['html'] = rule.to_html()
        #         rule['_pricing_rule'] = rule.to_pricing_rule()
        #
        #     # print '\n'.join(map(str , dyn_parser.taxos.values()))
        #     dyn_list = ObjList(dyn_parser.taxos.values())
        #
        #     write_section(
        #         "Dynamic Pricing Rules",
        #         "all products and their dynaimc pricing rules",
        #         re.sub("<table>", "<table class=\"table table-striped\">",
        #                dyn_list.tabulate(cols=OrderedDict([
        #                    ('html', {}),
        #                    ('_pricing_rule', {}),
        #                ]), tablefmt="html")
        #         ),
        #         length=len(dyn_list.objects)
        #     )
        #
        #     out_file.write('</div>')
        #     out_file.write("""
        # <script src="https://ajax.googleapis.com/ajax/libs/jquery/2.1.4/jquery.min.js"></script>
        # <script src="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.6/js/bootstrap.min.js" integrity="sha384-0mSbJDEHialfmuBBQP6A4Qrprq5OVfW37PRR3j5ELqxss1yVqOtnepnHVP9aJ7xS" crossorigin="anonymous"></script>
        # """)
        #     out_file.write('</body>')
        #     out_file.write('</html>')


if __name__ == '__main__':
    main()
