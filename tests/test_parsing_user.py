# from os import sys, path
# import unittest
# from unittest import TestCase
# import tempfile
# import dill
# from copy import copy
# from collections import OrderedDict
#
# from context import woogenerator
# from woogenerator.parsing.user import ImportUser
# from woogenerator.utils import Registrar
# from woogenerator.contact_objects import FieldGroup
#
# class TestUsrObj(TestCase):
#
#     def setUp(self):
#         # FieldGroup.perform_post = True
#         self.usr = ImportUser(
#             {
#                 'E-mail': 'derwentx@gmail.com invalid',
#                 'Personal E-mail': 'derwent@laserphile.com notes',
#                 'Web Site': 'http://www.laserphile.com/ blah',
#                 'Phone': '0416160912 bad',
#                 'Mobile Phone': '(+61) 433124710 derp'
#             }
#         )
#         args = (OrderedDict([
#             ('Tans Per Week', ''),
#             ('MYOB Customer Card ID', ''),
#             ('GooglePlus Username', ''),
#             ('Home Address 2', ''),
#             ('Instagram Username', ''),
#             ('Added to mailing list', ''),
#             ('Edited in Wordpress', ''),
#             ('Address 2', ''),
#             ('Wordpress ID', ''),
#             ('Twitter Username', ''),
#             ('Name Suffix', ''),
#             ('Middle Name', ''),
#             ('Contact', ''),
#             ('Name Prefix', ''),
#             ('Agent', ''),
#             ('Salutation', ''),
#             ('Shire', ''),
#             ('Lead Source', ''),
#             ('Spouse', ''),
#             ('Facebook Username', ''),
#             ('MYOB Card ID', u'C001280'),
#             ('E-mail', u'lhayeb@wikia.com'),
#             ('Role', u'WN'),
#             ('Direct Brand', u'VuTan Wholesale'),
#             ('Edited Name', u'10/04/2016 3:32:56 PM'),
#             ('First Name', u'Lorry'),
#             ('Surname', u'Haye'),
#             ('Memo', u'\uff9f\uff65\u273f\u30fe\u2572(\uff61\u25d5\u203f\u25d5\uff61)\u2571\u273f\uff65\uff9f'),
#             ('Edited Memo', u'28/12/2016 9:19:40 AM'),
#             ('Edited Spouse', u'3/06/2017 4:38:30 AM'),
#             ('Company', u'Skinte'),
#             ('Edited Company', u'13/01/2017 3:33:11 PM'),
#             ('Edited Phone Numbers', u'8/06/2016 11:24:07 AM'),
#             ('Mobile Phone', u'0447 267 588'),
#             ('Phone', u'02 1614 3894'),
#             ('Fax', u'02 5576 7738'),
#             ('Mobile Phone Preferred', u'true'),
#             ('Phone Preferred', u'true'),
#             ('Edited Address', u'16/11/2015 11:06:24 PM'),
#             ('Edited Alt Address', u'2/05/2017 9:45:40 PM'),
#             ('Address 1', u'68283 Monterey Lane'),
#             ('City', u'Narutoch\u014d-mitsuishi'),
#             ('Postcode', u'779-0311'),
#             ('Country', u'JP'),
#             ('Home Address 1', u'43 Miller Junction'),
#             ('Home City', u'Novonikol\u2019sk'),
#             ('Home Postcode', u'692557'),
#             ('Home Country', u'RU'),
#             ('Client Grade', u'Inactive 3yrs+'),
#             ('ABN', u'47 862 859 335'),
#             ('Business Type', u'Advertising'),
#             ('Edited Personal E-mail', u'30/08/2015 1:25:53 PM'),
#             ('Create Date', u'17/10/2009 7:42:01 AM'),
#             ('Wordpress Start Date', u'2013-06-12 02:39:06'),
#             ('Edited in Act', u'21/08/2013 8:10:55 AM'),
#             ('Last Sale', u'17/03/2016'),
#             ('Edited Social Media', u'13/09/2016 9:50:32 PM'),
#             ('contact_schema', 'act'),
#             ('schema', None),
#             ('source', 'ACT')
#         ]),)
#         kwargs = OrderedDict([
#             ('rowcount', 3),
#             ('row', [
#                 u'C001280', u'lhayeb@wikia.com', u'', u'', u'', u'WN', u'Lorry',
#                 u'Haye', u'Skinte', u'0447 267 588', u'02 1614 3894', u'02 5576 7738',
#                 u'true', u'true', u'68283 Monterey Lane', u'Narutoch\u014d-mitsuishi',
#                 u'779-0311', u'', u'JP', u'43 Miller Junction', u'Novonikol\u2019sk',
#                 u'692557', u'', u'RU', u'', u'', u'47 862 859 335', u'Inactive 3yrs+',
#                 u'VuTan Wholesale', u'Advertising', u'', u'15/04/2016 5:13:03 PM',
#                 u'10/04/2016 3:32:56 PM', u'13/01/2017 3:33:11 PM', u'8/06/2016 11:24:07 AM',
#                 u'16/11/2015 11:06:24 PM', u'2/05/2017 9:45:40 PM', u'13/09/2016 9:50:32 PM',
#                 u'19/01/2017 4:17:19 PM', u'3/06/2017 4:38:30 AM', u'28/12/2016 9:19:40 AM',
#                 u'30/08/2015 1:25:53 PM', u'', u'17/10/2009 7:42:01 AM', u'2013-06-12 02:39:06',
#                 u'21/08/2013 8:10:55 AM', u'17/03/2016',
#                 u'\uff9f\uff65\u273f\u30fe\u2572(\uff61\u25d5\u203f\u25d5\uff61)\u2571\u273f\uff65\uff9f'
#             ])
#         ])
#         self.obj = ImportUser(*args, **kwargs)
#
#         Registrar.DEBUG_ERROR = False
#         Registrar.DEBUG_WARN = False
#         Registrar.DEBUG_MESSAGE = False
#
#     def test_sanitizeURL(self):
#         self.assertEqual(self.usr['Web Site'], 'http://www.laserphile.com/')
#
#     @unittest.skip("fix this later")
#     def test_sanitizeEmail(self):
#         self.assertEqual(self.usr.email.lower(), 'derwentx@gmail.com')
#         self.assertEqual(self.usr['Personal E-mail'], 'derwent@laserphile.com')
#
#
#     @unittest.skip("fix this later")
#     def test_sanitizePhone(self):
#         self.assertEqual(self.usr['Phone'], '0416160912')
#         self.assertEqual(self.usr['Mobile Phone'], '(+61)433124710')
#
#     def test_pickle(self):
#         # FieldGroup.perform_post = False
#         self.assertEqual(self.obj.index, '3 | C001280')
#         _, pickle_path = tempfile.mkstemp("usr_pickle")
#         with open(pickle_path, 'w') as pickle_file:
#             dill.dump(self.obj, pickle_file)
#         with open(pickle_path) as pickle_file:
#             unpickled_obj = dill.load(pickle_file)
#         self.assertEqual(unpickled_obj.index, '3 | C001280')
#         self.assertEqual(repr(self.obj), repr(unpickled_obj))
#
#     def test_copy(self):
#         copied_obj = copy(self.obj)
#         self.assertEqual(self.obj.index, copied_obj.index)
#         self.assertEqual(repr(self.obj), repr(copied_obj))
#
# if __name__ == '__main__':
#     # unittest.main()
#
#     test_suite = unittest.TestSuite()
#     test_suite.addTest(TestUsrObj('test_pickle'))
#     unittest.TextTestRunner().run(test_suite)
