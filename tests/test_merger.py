from __future__ import print_function
import os
# import sys
import unittest
# from unittest import TestCase, main, skip, TestSuite, TextTestRunner
import argparse
from pprint import pformat

from context import woogenerator
# from woogenerator.coldata import ColDataWoo
# from woogenerator.parsing.woo import ImportWooProduct, CsvParseWoo, CsvParseTT, WooProdList
from woogenerator.utils import Registrar #, SanitationUtils
from woogenerator.conf.parser import ArgumentParserUser
from woogenerator.conf.namespace import (init_settings, ParserNamespace,
                                         SettingsNamespaceUser, MatchNamespace)
from woogenerator.merger import populate_master_parsers, populate_slave_parsers, do_match
from context import tests_datadir

class TestMerger(unittest.TestCase):
    def setUp(self):

        self.settings = SettingsNamespaceUser()
        self.settings.local_work_dir = tests_datadir
        self.settings.local_live_config = None
        self.settings.local_test_config = "merger_config_test.yaml"
        self.settings.master_dialect_suggestion = "ActOut"
        self.settings.download_master = False
        self.settings.master_file = os.path.join(tests_datadir, "merger_master_dummy.csv")
        self.settings.slave_file = os.path.join(tests_datadir, "merger_slave_dummy.csv")
        # self.settings.master_parse_limit = 10
        # self.settings.slave_parse_limit = 10
        self.override_args = ""
        self.parsers = ParserNamespace()

        Registrar.DEBUG_ERROR = False
        Registrar.DEBUG_WARN = False
        Registrar.DEBUG_MESSAGE = False
        Registrar.DEBUG_PROGRESS = False

        # Registrar.DEBUG_ERROR = True
        # Registrar.DEBUG_WARN = True
        # Registrar.DEBUG_MESSAGE = True
        # Registrar.DEBUG_PROGRESS = True
        # Registrar.DEBUG_ABSTRACT = True
        # Registrar.DEBUG_PARSER = True

        self.settings = init_settings(
            settings=self.settings,
            override_args=self.override_args,
            argparser_class=ArgumentParserUser
        )

        self.matches = MatchNamespace()

    def test_init_settings(self):

        self.assertEqual(self.settings.master_name, "ACT")
        self.assertEqual(self.settings.slave_name, "WORDPRESS")
        self.assertEqual(self.settings.download_master, False)
        self.assertEqual(
            self.settings.master_client_args["limit"],
            self.settings.master_parse_limit
        )
        self.assertEqual(self.settings.master_client_args["dialect_suggestion"], "ActOut")

    def test_populate_master_parsers(self):
        self.settings.master_parse_limit = 4

        # Registrar.DEBUG_ERROR = True
        # Registrar.DEBUG_WARN = True
        # Registrar.DEBUG_MESSAGE = True
        # Registrar.DEBUG_CONTACT = True
        # Registrar.DEBUG_ADDRESS = True
        # Registrar.DEBUG_NAME = True

        self.parsers = populate_master_parsers(
            self.parsers, self.settings
        )

        usr_list = self.parsers.master.get_obj_list()

        #number of objects:
        self.assertTrue(len(usr_list))
        # print("len: %s" % len(usr_list))
        # self.assertEqual(len(usr_list), 86)

        #first user:
        first_usr = usr_list[0]
        # print("pformat@dict:\n%s" % pformat(dict(first_usr)))
        # print("pformat@dir:\n%s" % pformat(dir(first_usr)))
        # print("str@.act_modtime:\n%s" % str(first_usr.act_modtime))
        # print("str@.act_created:\n%s" % str(first_usr.act_created))
        # print("str@.wp_created:\n%s" % str(first_usr.wp_created))
        # print("str@.wp_modtime:\n%s" % str(first_usr.wp_modtime))
        # print("str@.last_sale:\n%s" % str(first_usr.last_sale))
        # print("str@.last_modtime:\n%s" % str(first_usr.last_modtime))
        # print("str@.act_last_transaction:\n%s" % str(first_usr.act_last_transaction))
        # print("pformat@.name.to_dict:\n%s" % pformat(dict(first_usr.name.to_dict())))
        # print("pformat@.shipping_address.valid:\n%s" % pformat(first_usr.shipping_address.valid))
        # print("pformat@.shipping_address.kwargs:\n%s" % \
        #       pformat(first_usr.shipping_address.kwargs))
        # print("pformat@.shipping_address.to_dict:\n%s" % \
        #       pformat(dict(first_usr.shipping_address.to_dict())))
        # print(".billing_address:\n%s" % first_usr.billing_address)
        # print("pformat@.billing_address.to_dict:\n%s" % \
        #       pformat(dict(first_usr.billing_address.to_dict())))
        # print("pformat@.phones.to_dict:\n%s" % pformat(dict(first_usr.phones.to_dict())))
        # print("pformat@.socials.to_dict:\n%s" % pformat(dict(first_usr.socials.to_dict())))

        self.assertEqual(first_usr.name.first_name, 'Giacobo')
        self.assertEqual(first_usr.name.family_name, 'Piolli')
        self.assertEqual(first_usr.name.company, 'Linkbridge')
        self.assertEqual(str(first_usr.name), 'Giacobo Piolli')
        self.assertEqual(first_usr.shipping_address.city, 'Congkar')
        self.assertEqual(first_usr.shipping_address.country, 'AU')
        self.assertEqual(first_usr.shipping_address.postcode, '6054')
        self.assertEqual(first_usr.shipping_address.state, 'VIC')
        self.assertEqual(
            str(first_usr.shipping_address),
            '4552 Sunfield Circle; Congkar, VIC, 6054, AU'
        )
        self.assertEqual(first_usr.billing_address.city, 'Duwaktenggi')
        self.assertEqual(first_usr.billing_address.country, 'AU')
        self.assertEqual(first_usr.billing_address.postcode, '6011')
        self.assertEqual(first_usr.billing_address.state, 'WA')
        self.assertEqual(
            str(first_usr.billing_address),
            '91 Alpine Trail; Duwaktenggi, WA, 6011, AU'
        )
        self.assertEqual(first_usr.phones.mob_number, '+614 40 564 957')
        self.assertEqual(first_usr.phones.tel_number, '02 2791 7625')
        self.assertEqual(first_usr.phones.fax_number, '07 5971 6312')
        self.assertEqual(
            str(first_usr.phones),
            "02 2791 7625 PREF; +614 40 564 957 PREF; 07 5971 6312"
        )
        self.assertEqual(first_usr.socials.twitter, "kmainstone5")
        website = ("https://wikispaces.com/vivamus/metus/arcu/adipiscing.jpg?"
                   "duis=justo" "&consequat=sollicitudin" "&dui=ut"
                   "&nec=suscipit" "&nisi=a" "&volutpat=feugiat" "&eleifend=et"
                   "&donec=eros" "&ut=vestibulum" "&dolor=ac" "&morbi=est"
                   "&vel=lacinia" "&lectus=nisi" "&in=venenatis")
        self.assertEqual(first_usr.socials.website, website)
        self.assertEqual(first_usr['Web Site'], website)

        self.assertEqual(first_usr.act_modtime, 1284447467.0)
        self.assertEqual(first_usr.act_created, 1303530357.0)
        self.assertEqual(first_usr.wp_created, 1406544037.0)
        self.assertEqual(first_usr.wp_modtime, None)
        self.assertEqual(first_usr.last_sale, 1445691600.0)
        self.assertEqual(first_usr.last_modtime, 1445691600.0)
        self.assertEqual(first_usr.act_last_transaction, 1445691600.0)
        self.assertEqual(str(first_usr.role), "RN")
        self.assertEqual(str(first_usr.role.direct_brands), "TechnoTan Wholesale")

        # print(SanitationUtils.coerce_bytes(usr_list.tabulate(tablefmt='simple')))

    def test_populate_slave_parsers(self):
        self.parsers = populate_slave_parsers(
            self.parsers, self.settings
        )

        usr_list = self.parsers.slave.get_obj_list()

        self.assertEqual(len(usr_list), 100)

        # print(SanitationUtils.coerce_bytes(obj_list.tabulate(tablefmt='simple')))

        self.assertTrue(len(usr_list))

        first_usr = usr_list[0]
        # print("pformat@dict:\n%s" % pformat(dict(first_usr)))
        # print("pformat@dir:\n%s" % pformat(dir(first_usr)))
        # print("str@.act_modtime:\n%s" % str(first_usr.act_modtime))
        # print("str@.act_created:\n%s" % str(first_usr.act_created))
        # print("str@.wp_created:\n%s" % str(first_usr.wp_created))
        # print("str@.wp_modtime:\n%s" % str(first_usr.wp_modtime))
        # print("str@.last_sale:\n%s" % str(first_usr.last_sale))
        # print("str@.last_modtime:\n%s" % str(first_usr.last_modtime))
        # print("pformat@.name.to_dict:\n%s" % pformat(dict(first_usr.name.to_dict())))
        # print("pformat@.shipping_address.valid:\n%s" % pformat(first_usr.shipping_address.valid))
        # print("pformat@.shipping_address.kwargs:\n%s" % \
        #       pformat(first_usr.shipping_address.kwargs))
        # print("pformat@.shipping_address.to_dict:\n%s" % \
        #       pformat(dict(first_usr.shipping_address.to_dict())))
        # print(".billing_address:\n%s" % first_usr.billing_address)
        # print("pformat@.billing_address.to_dict:\n%s" % \
        #       pformat(dict(first_usr.billing_address.to_dict())))
        # print("pformat@.phones.to_dict:\n%s" % pformat(dict(first_usr.phones.to_dict())))
        # print("pformat@.socials.to_dict:\n%s" % pformat(dict(first_usr.socials.to_dict())))

        self.assertEqual(first_usr.name.first_name, 'Gustav')
        self.assertEqual(first_usr.name.family_name, 'Sample')
        self.assertEqual(first_usr.name.company, 'Thoughtstorm')
        self.assertEqual(str(first_usr.name), 'Gustav Sample')
        self.assertEqual(first_usr.shipping_address.city, 'Washington')
        self.assertEqual(first_usr.shipping_address.country, 'US')
        self.assertEqual(first_usr.shipping_address.postcode, '20260')
        self.assertEqual(first_usr.shipping_address.state, 'District of Columbia')
        self.assertEqual(
            str(first_usr.shipping_address),
            '99 Oneill Point; Washington, District of Columbia, 20260, US'
        )
        self.assertEqual(first_usr.billing_address.city, 'Boulder')
        self.assertEqual(first_usr.billing_address.country, 'US')
        self.assertEqual(first_usr.billing_address.postcode, '80305')
        self.assertEqual(first_usr.billing_address.state, 'Colorado')
        self.assertEqual(
            str(first_usr.billing_address),
            '13787 Oakridge Parkway; Boulder, Colorado, 80305, US'
        )
        self.assertEqual(first_usr.phones.mob_number, '+614 37 941 958')
        self.assertEqual(first_usr.phones.tel_number, '07 2258 3571')
        self.assertEqual(first_usr.phones.fax_number, '07 4029 1259')
        self.assertEqual(
            str(first_usr.phones),
            "07 2258 3571 PREF; +614 37 941 958 PREF; 07 4029 1259"
        )
        self.assertEqual(first_usr.socials.twitter, "bblakeway7")

        self.assertEqual(first_usr.act_modtime, None)
        self.assertEqual(first_usr.act_created, None)
        self.assertEqual(first_usr.wp_created, 1479060113.0)
        self.assertEqual(first_usr.wp_modtime, None)
        self.assertEqual(first_usr.last_sale, None)
        self.assertEqual(first_usr.last_modtime, 1479060113.0)
        self.assertEqual(str(first_usr.role.direct_brands), "Pending")
        self.assertEqual(str(first_usr.role), "WN")

    def test_do_match(self):
        self.parsers = populate_master_parsers(
            self.parsers, self.settings
        )
        self.parsers = populate_slave_parsers(
            self.parsers, self.settings
        )
        self.matches = do_match(
            self.matches, self.parsers, self.settings
        )




if __name__ == '__main__':
    unittest.main()

# just in case the files get lost
MASTER_LINK = """https://www.mockaroo.com/8b4d8950"""
MASTER_FIRST_ROWS = """
MYOB Card ID,E-mail,Personal E-mail,Wordpress Username,Wordpress ID,Role,First Name,Surname,Company,Mobile Phone,Phone,Fax,Mobile Phone Preferred,Phone Preferred,Address 1,City,Postcode,State,Country,Home Address 1,Home City,Home Postcode,Home State,Home Country,Twitter Username,Web Site,ABN,Client Grade,Direct Brand,Business Type,Referred By,Edited E-mail,Edited Name,Edited Company,Edited Phone Numbers,Edited Address,Edited Alt Address,Edited Social Media,Edited Webi Site,Edited Spouse,Edited Memo,Edited Personal E-mail,Edited Web Site,Create Date,Wordpress Start Date,Edited in Act,Last Sale,Memo,Edited Added to mailing list
C001322,gpiolli1@ezinearticles.com,kmainstone5@altervista.org,mmeddings3,1007,RN,Giacobo,Piolli,Linkbridge,+614 40 564 957,02 2791 7625,07 5971 6312,true,true,91 Alpine Trail,Duwaktenggi,6011,WA,AU,4552 Sunfield Circle,Congkar,6054,VIC,AU,kmainstone5,https://wikispaces.com/vivamus/metus/arcu/adipiscing.jpg?duis=justo&consequat=sollicitudin&dui=ut&nec=suscipit&nisi=a&volutpat=feugiat&eleifend=et&donec=eros&ut=vestibulum&dolor=ac&morbi=est&vel=lacinia&lectus=nisi&in=venenatis,57667755181,New,TechnoTan Wholesale,Internet Search,Salon Melb '14,8/11/2016 1:38:51 PM,27/11/2015 2:28:22 AM,19/09/2016 3:56:43 AM,12/11/2015 12:30:27 PM,19/05/2017 4:04:04 AM,8/08/2015 6:18:47 AM,24/11/2015 10:54:31 AM,23/04/2016 9:12:28 AM,12/12/2015 9:41:32 AM,15/09/2015 6:54:40 AM,14/02/2016 1:50:26 PM,8/02/2016 3:35:46 AM,23/04/2011 1:45:57 PM,2014-07-28 20:40:37,14/09/2010 4:57:47 PM,25/10/2015,
"""
SLAVE_FIRST_ROWS = """
MYOB Card ID,E-mail,Personal E-mail,Wordpress Username,Wordpress ID,Role,First Name,Surname,Company,Mobile Phone,Phone,Fax,Mobile Phone Preferred,Phone Preferred,Address 1,City,Postcode,State,Country,Home Address 1,Home City,Home Postcode,Home State,Home Country,Twitter Username,Web Site,ABN,Client Grade,Direct Brand,Business Type,Referred By,Edited E-mail,Edited Name,Edited Company,Edited Phone Numbers,Edited Address,Edited Alt Address,Edited Social Media,Edited Web Site,Edited Spouse,Edited Memo,Edited Personal E-mail,Edited Added to mailing list,Wordpress Start Date,Edited in Act,Last Sale,Memo
C001453,gsample6@free.fr,bblakeway7@timesonline.co.uk,gsample6,1080,WN,Gustav,Sample,Thoughtstorm,+614 37 941 958,07 2258 3571,07 4029 1259,false,false,13787 Oakridge Parkway,Boulder,80305,Colorado,US,99 Oneill Point,Washington,20260,District of Columbia,US,bblakeway7.,,97 375 915 674,Bronze,Pending,Internet Search,Salon Melb '14,2017-04-14 02:13:09,2016-08-12 10:36:16,2017-03-07 01:44:01,2016-10-09 03:31:04,2017-01-14 14:09:58,2016-07-16 09:57:20,2016-08-09 23:10:49,2016-10-05 17:20:59,2016-08-29 16:53:21,2017-04-24 16:37:41,2017-03-05 22:04:12,,2016-11-14 05:01:53,,,null
"""
SLAVE_LINK = """https://www.mockaroo.com/7ebfedb0"""
