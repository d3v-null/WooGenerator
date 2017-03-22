# TODO: Convert this to test cases

#
# if __name__ == '__main__':
#     in_folder = "../input/"
#     # actPath = os.path.join(in_folder, 'partial act records.csv')
#     actPath = os.path.join(in_folder, "500-act-records.csv")
#     out_folder = "../output/"
#     usrPath = os.path.join(out_folder, 'users.csv')
#
#     usrData = ColData_User()
#
#     # print "import cols", usrData.get_import_cols()
#     # print "defaults", usrData.get_defaults()
#
#     usrParser = CsvParseBase(
#         cols = usrData.get_import_cols(),
#         defaults = usrData.get_defaults()
#     )
#
#     usrParser.analyse_file(actPath)
#
#     SanitationUtils.safe_print( usrParser.tabulate(cols = usrData.get_report_cols()))
#     print ( usrParser.tabulate(cols = usrData.get_report_cols()))
#
#     for usr in usrParser.objects.values()[:3]:
#         pprint(OrderedDict(usr))
