#
#
# def test_html_reporter():
#     with\
#             open('../output/htmlReporterTest.html', 'w+') as res_file,\
#             io.open('../output/htmlReporterTestU.html', 'w+', encoding="utf8") as ures_file:
#         reporter = HtmlReporter()
#
#         matching_group = HtmlReporter.Group('matching', 'Matching Results')
#
#         matching_group.add_section(
#             HtmlReporter.Section(
#                 'perfect_matches',
#                 **{
#                     'title': 'Perfect Matches',
#                     'description': "%s records match well with %s" % ("WP", "ACT"),
#                     'data': u"<\U0001F44C'&>",
#                     'length': 3
#                 }
#             )
#         )
#
#         reporter.add_group(matching_group)
#
#         document = reporter.get_document()
#         # SanitationUtils.safe_print( document)
#         ures_file.write(SanitationUtils.coerce_unicode(document))
#         res_file.write(SanitationUtils.coerce_ascii(document))
