import unittest
from unittest import TestCase
import traceback
from pprint import pformat

from context import woogenerator
from woogenerator.utils import Registrar
from woogenerator.contact_objects import (FieldGroup, SocialMediaFields,
                                          ContactAddress, ContactName,
                                          ContactPhones, RoleGroup)

class TestFieldGroups(TestCase):

    def setUp(self):
        # defaults
        Registrar.DEBUG_ERROR = False
        Registrar.DEBUG_WARN = False
        Registrar.DEBUG_MESSAGE = False
        FieldGroup.perform_post = True
        FieldGroup.enforce_mandatory_keys = False

        # Temporarily enable debugging
        debug = False
        # debug = True
        if debug:
            FieldGroup.DEBUG_MESSAGE = True
            FieldGroup.DEBUG_WARN = True
            FieldGroup.DEBUG_ERROR = True
            # FieldGroup.DEBUG_CONTACT = True
            FieldGroup.DEBUG_ADDRESS = True

class TestContactAddress(TestFieldGroups):
    # thoroughfare tests

    def test_thoroughfare_num_off_line(self):
        address = ContactAddress(
            line1="SHOP 10, 575/577",
            line2="CANNING HIGHWAY"
        )
        self.assertTrue(address.valid)
        self.assertTrue(address.properties['isShop'])
        self.assertItemsEqual(
            address.properties['thoroughfares'],
            [('575/577', 'CANNING', 'HIGHWAY', None)]
        )
        self.assertItemsEqual(address.properties['subunits'], [('SHOP', '10')])

    def test_irregular_thoroughfare_num(self):
        address = ContactAddress(
            line1='LEVEL 2, SHOP 202 / 8B "WAX IT"',
            line2="ROBINA TOWN CENTRE"
        )
        self.assertTrue(address.properties['isShop'])
        self.assertItemsEqual(
            address.properties['buildings'],
            [('ROBINA TOWN', 'CENTRE')]
        )
        self.assertItemsEqual(address.properties['floors'], [('LEVEL', '2')])
        self.assertItemsEqual(
            address.properties['subunits'],
            [('SHOP', '202')]
        )
        self.assertTrue(address.problematic)

    def test_coerce_thoroughfare_type(self):
        address = ContactAddress(
            line1="3/3 HOWARD AVE"
        )
        self.assertFalse(address.problematic)
        self.assertTrue(address.valid)
        self.assertItemsEqual(
            address.properties['thoroughfares'],
            [('3/3', 'HOWARD', 'AVE', None)]
        )

    def test_no_coerce_bad_thoroughfare(self):
        address = ContactAddress(
            line1="3/3 HOWARD AVA"
        )
        self.assertTrue(address.problematic)

    def test_coerce_thoroughfare(self):
        address = ContactAddress(
            line1="7 Grosvenor",
        )
        self.assertTrue(address.problematic)
        self.assertItemsEqual(
            address.properties['thoroughfares'],
            [('7', 'GROSVENOR', None, None)]
        )

        address = ContactAddress(
            line1="SH115A, FLOREAT FORUM"
        )
        self.assertTrue(address.valid)
        self.assertItemsEqual(
            address.properties['subunits'], [('SHOP', '115A')])
        self.assertItemsEqual(
            address.properties['buildings'],
            [('FLOREAT', 'FORUM')]
        )

        address = ContactAddress(
            line1="SHOP 3091 WESTFIELD HORNSBY",
            line2="236 PACIFIC H'WAY"
        )
        self.assertTrue(address.valid)
        self.assertItemsEqual(
            address.properties['thoroughfares'],
            [('236', 'PACIFIC', 'HWY', None)]
        )

    def test_and_thoroughfare_number(self):
        address = ContactAddress(
            line1="SHOP 5&6, 39 MURRAY ST"
        )
        self.assertFalse(address.problematic)
        self.assertTrue(address.valid)
        self.assertTrue(address.properties['isShop'])
        self.assertItemsEqual(
            address.properties['subunits'],
            [('SHOP', '5-6')]
        )
        self.assertItemsEqual(
            address.properties['thoroughfares'],
            [('39', 'MURRAY', 'ST', None)]
        )

    def test_ordinal_thoroughfare(self):
        address = ContactAddress(
            city='ROSSMORE',
            state='NSW',
            line1="700 15TH AVE",
            line2="LANDSBOROUGH PARADE",
            postcode="2557"
        )
        self.assertFalse(address.empty)
        self.assertItemsEqual(
            address.properties['thoroughfares'],
            [('700', '15TH', 'AVE', None)]
        )
        self.assertTrue(address.problematic)

    def test_thoroughfare_suffix(self):
        address = ContactAddress(
            line1="8/5-7 KILVINGTON DRIVE EAST"
        )
        self.assertTrue(address.valid)
        self.assertItemsEqual(
            address.properties['thoroughfares'],
            [('5-7', 'KILVINGTON', 'DR', 'E')]
        )
        self.assertItemsEqual(
            address.properties['coerced_subunits'], [(None, '8')])

    # building tests
    def test_building_no_tf_type(self):
        address = ContactAddress(
            line1='BROADWAY FAIR SHOPPING CTR',
            line2='SHOP 16, 88 BROADWAY'
        )
        self.assertFalse(address.valid)
        self.assertTrue(address.problematic)

    def test_building_valid_tf(self):
        address = ContactAddress(
            line1='BROADWAY FAIR SHOPPING CTR',
            line2='SHOP 16, 88 BROADWAY FAIR'
        )
        self.assertTrue(address.properties['isShop'])
        self.assertItemsEqual(
            address.properties['buildings'],
            [('BROADWAY FAIR', 'SHOPPING CTR')]
        )
        self.assertItemsEqual(
            address.properties['thoroughfares'],
            [('88', 'BROADWAY', 'FAIR', None)]
        )
        self.assertItemsEqual(
            address.properties['subunits'],
            [('SHOP', '16')]
        )
        self.assertTrue(address.problematic)

    def test_multiple_buildings(self):
        address = ContactAddress(
            line1="SHOP 9 PASPALIS CENTREPOINT",
            line2="SMITH STREET MALL"
        )
        self.assertTrue(address.properties['isShop'])
        self.assertItemsEqual(
            address.properties['buildings'],
            [('PASPALIS CENTREPOINT', None)]
        )
        self.assertItemsEqual(
            address.properties['weak_thoroughfares'],
            [('SMITH STREET', 'MALL', None)]
        )
        self.assertItemsEqual(
            address.properties['subunits'],
            [('SHOP', '9')]
        )
        self.assertFalse(address.problematic)
        self.assertTrue(address.valid)

    def test_irregular_slash_abbrv(self):
        address = ContactAddress(
            line1="Factory 5/ inglewood s/c Shop 7/ 12 15th crs"
        )
        self.assertFalse(address.problematic)
        self.assertTrue(address.valid)
        self.assertTrue(address.properties['isShop'])
        self.assertItemsEqual(
            address.properties['subunits'],
            [('SHOP', '7'), ('FACTORY', '5')]
        )
        self.assertItemsEqual(
            address.properties['thoroughfares'],
            [('12', '15TH', 'CRES', None)]
        )
        self.assertItemsEqual(
            address.properties['buildings'],
            [('INGLEWOOD', 'SHOPPING CENTRE')]
        )

    @unittest.skip("can't handle yet")
    def test_ambiguous_building_hard(self):
        address = ContactAddress(
            **{'city': u'TEA TREE GULLY',
               'country': u'AUSTRALIA',
               'line1': u'SHOP 238/976',
               'line2': u'TEA TREE PLAZA',
               'postcode': u'5092',
               'state': u'SA'}
        )
        self.assertTrue(address.valid)
        self.assertTrue(address.problematic)
        self.assertItemsEqual(address.properties['buildings'], [])
        self.assertItemsEqual(
            address.properties['subunits'], [('SHOP', '238')]
        )
        self.assertItemsEqual(
            address.properties['thoroughfares'],
            [('976', 'TEA TREE', 'PLAZA', None)]
        )

        address = ContactAddress(
            line1="SHOP 9A GREEN POINT SHOPPING VILLAGE"
        )
        self.assertTrue(address.valid)

    def test_ambiguous_building(self):
        address = ContactAddress(
            line1="73 NORTH PARK AVENUE",
            line2="ROCKVILLE CENTRE"
        )
        self.assertTrue(address.problematic)
        self.assertItemsEqual(
            address.properties['thoroughfares'],
            [('73', 'NORTH PARK', 'AVE', None)]
        )
        self.assertItemsEqual(
            address.properties['buildings'],
            [("ROCKVILLE", "CENTRE")]
        )

        address = ContactAddress(
            line1="THE MARKET PLACE",
            line2="SHOP 28/33 HIBBERSON ST"
        )
        self.assertTrue(address.valid)

    def test_coerce_building(self):
        address = ContactAddress(
            line1="SHOP  2052 LEVEL 1 WESTFIELD"
        )
        self.assertFalse(address.problematic)
        self.assertTrue(address.valid)
        self.assertTrue(address.properties['isShop'])
        self.assertItemsEqual(address.properties['floors'], [('LEVEL', '1')])
        self.assertItemsEqual(
            address.properties['subunits'],
            [('SHOP', '2052')]
        )
        self.assertItemsEqual(
            address.properties['buildings'],
            [('WESTFIELD', None)]
        )

    # subunit tests
    def test_irregular_slash_in_subunit(self):
        address = ContactAddress(
            line1='SUITE 3/ LEVEL 8',
            line2='187 MACQUARIE STREET'
        )
        self.assertFalse(address.problematic)
        self.assertTrue(address.valid)
        self.assertItemsEqual(address.properties['floors'], [('LEVEL', '8')])
        self.assertItemsEqual(address.properties['subunits'], [('SUITE', '3')])
        self.assertItemsEqual(
            address.properties['thoroughfares'],
            [('187', 'MACQUARIE', 'ST', None)]
        )

        address = ContactAddress(
            line1='UNIT 4/ 12-14 COMENARA CRS',
        )
        self.assertFalse(address.problematic)
        self.assertTrue(address.valid)
        self.assertFalse(address.properties['isShop'])
        self.assertItemsEqual(address.properties['subunits'], [('UNIT', '4')])
        self.assertItemsEqual(
            address.properties['thoroughfares'],
            [('12-14', 'COMENARA', 'CRES', None)]
        )

        address = ContactAddress(
            line1='UNIT 4/12-14 COMENARA CRS',
        )
        self.assertFalse(address.problematic)
        self.assertTrue(address.valid)
        self.assertFalse(address.properties['isShop'])
        self.assertItemsEqual(address.properties['subunits'], [('UNIT', '4')])
        self.assertItemsEqual(
            address.properties['thoroughfares'],
            [('12-14', 'COMENARA', 'CRES', None)]
        )

        address = ContactAddress(
            line1='UNIT 6/7 38 GRAND BOULEVARD',
        )
        self.assertFalse(address.problematic)
        self.assertTrue(address.valid)
        self.assertFalse(address.properties['isShop'])
        self.assertItemsEqual(
            address.properties['subunits'],
            [('UNIT', '6/7')]
        )
        self.assertItemsEqual(
            address.properties['thoroughfares'],
            [('38', 'GRAND', 'BLVD', None)]
        )

        address = ContactAddress(
            line1='UNIT 25/39 ASTLEY CRS',
        )

        self.assertFalse(address.problematic)
        self.assertTrue(address.valid)
        self.assertFalse(address.properties['isShop'])
        self.assertItemsEqual(address.properties['subunits'], [('UNIT', '25')])
        self.assertItemsEqual(
            address.properties['thoroughfares'],
            [('39', 'ASTLEY', 'CRES', None)]
        )

    def test_slash_subunit_split_lines(self):
        address = ContactAddress(
            line1='TOWNHOUSE 4/115 - 121',
            line2='CARINGBAH ROAD'
        )
        self.assertFalse(address.problematic)
        self.assertTrue(address.valid)
        self.assertItemsEqual(
            address.properties['subunits'],
            [('TOWNHOUSE', '4')]
        )
        self.assertItemsEqual(
            address.properties['thoroughfares'],
            [('115-121', 'CARINGBAH', 'ROAD', None)]
        )

    def test_too_many_numbers(self):
        address = ContactAddress(
            line1='SHOP 3 81-83',
        )
        self.assertFalse(address.valid)

        address = ContactAddress(
            line1='UNIT 4 / 24',
        )
        self.assertFalse(address.valid)

    def test_coerce_subunit_range(self):
        address = ContactAddress(
            line1="6/7 118 RODWAY ARCADE"
        )
        self.assertFalse(address.problematic)
        self.assertTrue(address.valid)
        self.assertItemsEqual(
            address.properties['thoroughfares'],
            [('118', 'RODWAY', 'ARC', None)]
        )

    def test_coerce_subunit(self):
        address = ContactAddress(
            line1='SUIT 1 1 MAIN STREET',
        )
        self.assertTrue(address.problematic)
        self.assertItemsEqual(address.properties['subunits'], [('SUIT', '1')])
        self.assertItemsEqual(
            address.properties['thoroughfares'],
            [('1', 'MAIN', 'ST', None)]
        )

        address = ContactAddress(
            line1='SAHOP 5/7-13 BEACH ROAD',
        )
        self.assertTrue(address.problematic)
        self.assertItemsEqual(address.properties['subunits'], [('SAHOP', '5')])
        self.assertItemsEqual(
            address.properties['thoroughfares'],
            [('7-13', 'BEACH', 'RD', None)]
        )

        address = ContactAddress(
            line1='THE OFFICE OF SENATOR DAVID BUSHBY',
            line2='LEVE 2, 18 ROSSE AVE'
        )
        self.assertItemsEqual(address.properties['subunits'], [('LEVE', '2')])
        self.assertItemsEqual(
            address.properties['thoroughfares'],
            [('18', 'ROSSE', 'AVE', None)]
        )
        self.assertItemsEqual(
            address.properties['names'],
            ['THE OFFICE OF SENATOR DAVID BUSHBY']
        )
        self.assertTrue(address.problematic)

    def test_number_alpha_subunit(self):
        address = ContactAddress(
            city='CHATSWOOD',
            state='NSW',
            country='Australia',
            line1="SHOP 330 A VICTORIA AVE",
            postcode="2067"
        )
        self.assertTrue(address.valid)
        self.assertItemsEqual(
            address.properties['weak_thoroughfares'],
            [('VICTORIA', 'AVE', None)]
        )
        self.assertItemsEqual(
            address.properties['subunits'], [('SHOP', '330 A')])

    def test_alpha_number_subunit(self):
        address = ContactAddress(
            city='Perth',
            state='WA',
            country='Australia',
            line1="SHOP G159 BROADMEADOWS SHOP. CENTRE",
            line2="104 PEARCEDALE PARADE"
        )
        self.assertTrue(address.valid)
        self.assertItemsEqual(
            address.properties['subunits'],
            [('SHOP', 'G159')]
        )
        self.assertItemsEqual(
            address.properties['buildings'],
            [('BROADMEADOWS', 'SHOP. CENTRE')]
        )
        self.assertItemsEqual(
            address.properties['thoroughfares'],
            [('104', 'PEARCEDALE', 'PDE', None)]
        )

    @unittest.skip("can't handle yet")
    def test_alpha_number_alpha_subunit(self):
        address = ContactAddress(
            line1="SHOP G33Q, BAYSIDE SHOPPING CENTRE"
        )
        self.assertItemsEqual(
            address.properties['subunits'],
            [('SHOP', 'G33Q')]
        )
        self.assertEqual(
            address.properties['buildings'],
            [('BAYSIDE', 'SHOP. CENTRE')]
        )
        self.assertTrue(address.valid)

    def test_abbreviated_subunit(self):
        address = ContactAddress(
            line1="A8/90 MOUNT STREET"
        )
        self.assertTrue(address.valid)
        self.assertFalse(address.empty)
        self.assertItemsEqual(
            address.properties['subunits'],
            [('APARTMENT', '8')]
        )
        self.assertItemsEqual(
            address.properties['thoroughfares'],
            [('90', 'MOUNT', 'ST', None)]
        )

    # delivery tests

    def test_handle_delivery(self):
        address = ContactAddress(
            line1='P.O.BOX 3385',
        )
        self.assertFalse(address.problematic)
        self.assertTrue(address.valid)
        self.assertItemsEqual(
            address.properties['deliveries'],
            [('P.O.BOX', '3385')]
        )

        address = ContactAddress(
            line1="PO 5217 MACKAY MAIL CENTRE"
        )
        self.assertFalse(address.problematic)
        self.assertTrue(address.valid)
        self.assertItemsEqual(
            address.properties['deliveries'], [('PO', '5217')])
        self.assertItemsEqual(
            address.properties['buildings'],
            [("MACKAY MAIL", "CENTRE")]
        )

        address = ContactAddress(
            line1="G.P.O BOX 440",
            line2="CANBERRA CITY",
        )

        self.assertTrue(address.valid)
        self.assertItemsEqual(
            address.properties['deliveries'],
            [('G.P.O BOX', '440')]
        )

    def test_name_and_delivery(self):
        address = ContactAddress(
            line1=u'ANTONY WHITE, PO BOX 886',
            line2=u'LEVEL1 468 KINGSFORD SMITH DRIVE'
        )
        self.assertTrue(address.valid)
        self.assertFalse(address.problematic)
        self.assertItemsEqual(address.properties['names'], ['ANTONY WHITE'])
        self.assertItemsEqual(
            address.properties['deliveries'], [('PO BOX', '886')])
        self.assertItemsEqual(address.properties['floors'], [('LEVEL', '1')])
        self.assertItemsEqual(
            address.properties['thoroughfares'],
            [('468', 'KINGSFORD SMITH', 'DR', None)]
        )

    def test_careof(self):
        address = ContactAddress(
            line1="C/O COCO BEACH",
            line2="SHOP 3, 17/21 PROGRESS RD"
        )
        self.assertFalse(address.problematic)
        self.assertTrue(address.valid)
        self.assertTrue(address.properties['isShop'])
        self.assertItemsEqual(
            address.properties['careof_names'],
            [('C/O', 'COCO BEACH')]
        )
        self.assertItemsEqual(address.properties['subunits'], [('SHOP', '3')])
        self.assertItemsEqual(
            address.properties['thoroughfares'],
            [('17/21', 'PROGRESS', 'RD', None)]
        )

    @unittest.skip("can't handle yet")
    def test_careof_hard(self):
        address = ContactAddress(
            city='GOLDEN BEACH',
            state='QLD',
            country='Australia',
            line1="C/- PAMPERED LADY - GOLDEN BEACH SHOPPING CENTRE",
            line2="LANDSBOROUGH PARADE",
            postcode="4551"
        )
        self.assertFalse(address.problematic)
        self.assertTrue(address.valid)
        # self.assertItemsEqual(
        #     address.properties['careof_names'],
        #     [('C/O', 'PAMPERED LADY - GOLDEN BEACH SHOPPING CENTRE')]
        # )
        self.assertItemsEqual(
            address.properties['careof_names'],
            [('C/O', 'PAMPERED LADY')]
        )
        self.assertItemsEqual(
            address.properties['buildings'],
            [('GOLDEN BEACH', 'SHOPPING CENTRE')]
        )
        self.assertItemsEqual(
            address.properties['weak_thoroughfares'],
            [('LANDSBOROUGH', 'PARADE', None)]
        )

    def test_name_subunit_lvl_building(self):
        address = ContactAddress(
            line1="DANNY, SPG1 LG3 INGLE FARM SHOPPING CENTRE"
        )
        self.assertTrue(address.valid)
        self.assertFalse(address.problematic)
        self.assertItemsEqual(address.properties['names'], [('DANNY')])
        self.assertItemsEqual(address.properties['floors'], [('LG', '3')])
        self.assertItemsEqual(address.properties['subunits'], [('SHOP', 'G1')])
        self.assertItemsEqual(
            address.properties['buildings'],
            [('INGLE FARM', 'SHOPPING CENTRE')]
        )

    def test_name_after_thoroughfare(self):
        address = ContactAddress(
            line1="77 PHILLIP STREET",
            line2="OXLEY VALE"
        )
        self.assertTrue(address.problematic)

    @unittest.skip("can't handle yet")
    def test_handle_corner_thoroughfare(self):
        address = ContactAddress(
            line1="CANBERRA OLYMPIC POOL COMPLEX",
            line2="CR ALLARA ST & CONSTITUTION WAY"
        )
        self.assertTrue(address)
        self.assertItemsEqual(address.properties['buildings'], [('CANBERRA OLYMPIC POOL COMPLEX')])
        self.assertItemsEqual(address.properties['thoroughfares'], [('CR ALLARA ST & CONSTITUTION WAY')])

    def test_alpha_level(self):
        address = ContactAddress(
            line1="LEVEL A",
            line2="MYER CENTRE",
        )
        self.assertTrue(address.valid)
        self.assertItemsEqual(address.properties['floors'], [('LEVEL', 'A')])
        self.assertItemsEqual(
            address.properties['buildings'],
            [('MYER', 'CENTRE')]
        )
        self.assertFalse(address.problematic)

    def test_similarity(self):
        ca_m = ContactAddress(
            line1="20 BOWERBIRD ST",
            city="DEEBING HEIGHTS",
            state="QLD",
            postcode="4306",
            country="AU"
        )
        ca_n = ContactAddress(
            line1="MAX POWER",
            line2="20 BOWERBIRD STREET",
            city="DEEBING HEIGHTS",
            state="QLD",
            postcode="4306"
        )
        ca_o = ContactAddress(
            line2="20 BOWERBIRD STREET",
            city="DEEBING HEIGHTS",
            state="QLD",
            postcode="4306",
            country="AU"
        )
        ca_p = ContactAddress(
            line1="MAX POWER, UNIT 1/20 BOWERBIRD STREET",
            state="QLD",
            postcode="4306",
            country="AU"
        )
        self.assertTrue(ca_m.similar(ca_n))
        self.assertTrue(ca_m.similar(ca_o))
        self.assertTrue(ca_m.similar(ca_p))
        self.assertEqual(ca_m, ca_o)
        self.assertNotEqual(ca_m, ca_n)
        self.assertNotEqual(ca_m, ca_p)

    # TODO: "1st floor"

class TestContactAddressNoPost(TestFieldGroups):
    def setUp(self):
        FieldGroup.perform_post = False
        super(TestContactAddressNoPost, self).setUp()
        FieldGroup.perform_post = False
        self.ca_a = ContactAddress(
            line1=u'369 Katie Lane',
            line2='',
            city=u'Washington',
            country=u'US',
            postcode=u'20551',
            state=u'District of Columbia',
        )
        self.ca_b = ContactAddress(
            line1=u'5817 Rockefeller Circle',
            line2='',
            city=u'Clearwater',
            country=u'US',
            postcode=u'33758',
            state=u'Florida',
        )
        self.ca_c = ContactAddress(
            line1=u'5817 Rockefeller Circle',
            line2='',
            city=u'Clearwater',
            postcode=u'33758',
            state=u'Florida',
        )
        self.ca_e = ContactAddress()
        # print("CA_A: %s\nCA_B: %s" % (str(self.ca_a), str(self.ca_b)))

    def test_empty(self):
        self.assertFalse(self.ca_a.empty)
        self.assertFalse(self.ca_b.empty)
        self.assertFalse(self.ca_c.empty)
        self.assertTrue(self.ca_e.empty)

    def test_truth(self):
        self.assertTrue(self.ca_a)
        self.assertTrue(self.ca_b)
        self.assertFalse(self.ca_e)
        # print("CA_A TRUE: %s\nCA_B TRUE: %s" % (bool(self.ca_a), bool(self.ca_b)))

    def test_equality(self):
        self.assertNotEqual(self.ca_a, self.ca_b)
        self.assertNotEqual(self.ca_b, self.ca_c)

    def test_similarity(self):
        self.assertFalse(self.ca_a.similar(self.ca_b))
        self.assertTrue(self.ca_c.similar(self.ca_b))


class TestContactName(TestFieldGroups):

    def test_basic_name(self):
        name = ContactName(
            contact="Derwent McElhinney"
        )
        self.assertTrue(name)
        self.assertTrue(name.valid)
        self.assertEqual(name.first_name, "DERWENT")
        self.assertEqual(name.family_name, "MCELHINNEY")
        name = ContactName(
            family_name='Jackson',
            first_name='Abe'
        )
        self.assertTrue(name)
        self.assertTrue(name.valid)

    def test_note_detection(self):
        name = ContactName(
            contact="C ARCHIVE STEPHANIDIS"
        )
        # self.assertTrue(name.problematic)
        self.assertItemsEqual(name.name_notes, "ARCHIVE")

    def test_concurrent_note_detection(self):
        name = ContactName(
            contact="KAREN IRVINE - STOCK ACCOUNT"
        )
        # self.assertTrue(name.problematic)
        self.assertTrue(name.valid)
        self.assertEqual(name.name_notes, "STOCK")

    def test_irregular_last_name(self):
        name = ContactName(
            contact='EMILY O\'CALLAGHAN'
        )
        self.assertTrue(name.valid)
        self.assertEqual(name.first_name, "EMILY")
        self.assertEqual(name.family_name, "O'CALLAGHAN")

        name = ContactName(
            contact='RICHARD DI NATALE'
        )
        self.assertTrue(name.valid)
        self.assertEqual(name.first_name, "RICHARD")
        self.assertEqual(name.family_name, "DI NATALE")

    def test_irregular_last_name_hard(self):
        name = ContactName(
            contact='EMILY VAN DER WAL'
        )

        self.assertTrue(name.valid)
        self.assertEqual(name.first_name, "EMILY")
        self.assertEqual(name.family_name, "VAN DER WAL")

    def test_irregular_first_name(self):
        name = ContactName(
            contact='THI THU THAO NGUYENL'
        )

        self.assertTrue(name.valid)
        self.assertEqual(name.first_name, "THI THU")
        self.assertEqual(name.middle_name, "THAO")
        self.assertEqual(name.family_name, "NGUYENL")

    def test_double_names(self):
        name = ContactName(
            contact='NEIL CUNLIFFE-WILLIAMS',
            first_name='NEIL',
            family_name='CUNLIFFE-WILLIAMS'
        )

        name_copy = name.__deepcopy__()
        self.assertEqual(name, name_copy)
        self.assertEqual(name.first_name, name_copy.first_name)
        self.assertEqual(name.family_name, name_copy.family_name)


class TestContactPhones(TestFieldGroups):
    @unittest.skip("does not cover yet")
    def test_phones_equality(self):
        phones_1 = ContactPhones(
            mob_number='0416160912'
        )
        phones_2 = ContactPhones(
            tel_number='0416160912'
        )
        self.assertFalse(phones_1.empty)
        self.assertFalse(phones_2.empty)
        self.assertEqual(phones_1, phones_2)

    def test_phones_basic(self):
        numbers = ContactPhones(
            mob_number='0416160912',
            tel_number='93848512',
            fax_number='0892428032',
            mob_pref=True
        )


        self.assertTrue(numbers)
        self.assertFalse(numbers.empty)
        self.assertEqual(
            numbers.mob_number,
            '0416160912'
        )
        self.assertEqual(
            numbers.tel_number,
            '93848512'
        )
        self.assertEqual(
            numbers.fax_number,
            '0892428032'
        )
        self.assertEqual(
            numbers.mob_pref,
            True
        )


class TestSocialMediaGroup(TestFieldGroups):

    def test_print(self):
        smf = SocialMediaFields(
            facebook='facebook',
            twitter='@twitter',
            gplus='+gplus',
            instagram='@insta',
            # website = 'http://www.google.com'
        )

        # self.assertEqual(smf['Web Site'], 'http://www.google.com')
        self.assertEqual(smf['Facebook Username'], 'facebook')
        self.assertEqual(smf['Twitter Username'], '@twitter')
        self.assertEqual(smf['GooglePlus Username'], '+gplus')
        self.assertEqual(smf['Instagram Username'], '@insta')

class TestRoleGroup(TestFieldGroups):

    def fail_rolegroup_assertion(self, exc, role_info_a, role_info_b):
        msg = "Failed assertion: \n%s\nleft:  %s / %s\nright: %s / %s" % (
            traceback.format_exc(exc),
            pformat(role_info_a.kwargs),
            pformat(role_info_a.properties),
            pformat(role_info_b.kwargs),
            pformat(role_info_b.properties)
        )
        raise Exception(msg)

    def test_role_group_basic(self):
        rgrp = RoleGroup(
            role='WN',
            direct_brands='TechnoTan Wholesale'
        )

        self.assertTrue(rgrp)
        self.assertFalse(rgrp.empty)
        self.assertTrue(rgrp.valid)
        self.assertEqual(rgrp.role, 'WN')
        self.assertEqual(rgrp.direct_brands, 'TechnoTan Wholesale')

    def test_role_group_no_post(self):
        RoleGroup.perform_post = False
        rgrp = RoleGroup(
            role='WN',
            direct_brands='TechnoTan Wholesale'
        )

        self.assertTrue(rgrp)
        self.assertFalse(rgrp.empty)
        self.assertTrue(rgrp.valid)
        self.assertEqual(rgrp.role, 'WN')
        self.assertEqual(rgrp.direct_brands, 'TechnoTan Wholesale')

    def test_role_group_reflect_equality(self):
        RoleGroup.perform_post = True
        FieldGroup.enforce_mandatory_keys = False

        rgrp = RoleGroup(
            role='WN',
            direct_brands='TechnoTan Wholesale'
        )
        reflected = rgrp.reflect()
        self.assertEqual(rgrp, reflected)

        rgrp = RoleGroup(
            role='RN',
        )
        reflected = rgrp.reflect()
        try:
            self.assertEqual(rgrp, reflected)
        except AssertionError as exc:
            self.fail_rolegroup_assertion(exc, rgrp, reflected)

        rgrp = RoleGroup(
            role='RN',
            direct_brands='TechnoTan Retail'
        )
        reflected = rgrp.reflect()
        self.assertEqual(rgrp, reflected)

        rgrp = RoleGroup(
            role='WN',
            direct_brands='Pending'
        )
        reflected = rgrp.reflect()
        try:
            self.assertEqual(rgrp, reflected)
        except AssertionError as exc:
            self.fail_rolegroup_assertion(exc, rgrp, reflected)

    def test_role_group_reflect_equality_no_post(self):
        RoleGroup.perform_post = False
        FieldGroup.enforce_mandatory_keys = True

        rgrp = RoleGroup(
            role='WN',
            direct_brands='TechnoTan Wholesale'
        )
        reflected = rgrp.reflect()
        self.assertEqual(rgrp, reflected)

        rgrp = RoleGroup(
            role='RN',
        )
        reflected = rgrp.reflect()
        try:
            self.assertNotEqual(rgrp, reflected)
        except AssertionError as exc:
            self.fail_rolegroup_assertion(exc, rgrp, reflected)

        rgrp = RoleGroup(
            role='RN',
            direct_brands='TechnoTan Retail'
        )
        reflected = rgrp.reflect()
        self.assertEqual(rgrp, reflected)

        rgrp = RoleGroup(
            role='WN',
            direct_brands='Pending'
        )
        reflected = rgrp.reflect()
        self.assertNotEqual(rgrp, reflected)

    def test_roles_jess(self):
        RoleGroup.perform_post = True

        for direct_brands, role, expected_brand, expected_role in [
            # If Direct Brand is TechnoTan and Role is WN - Change Direct Brand to TechnoTan Wholesale and keep Role as WN
            ("TechnoTan", "WN", "TechnoTan Wholesale", "WN"),
            # If Direct Brand is TechnoTan and Role is RN - Change Direct Brand to TechnoTan Retail and keep Role as RN
            ("TechnoTan", "RN", "TechnoTan Retail", 'RN'),
            # If Direct Brand is VuTan and Role is WN - Change Direct Brand to VuTan Wholesale and keep Role as WN
            ("VuTan", "WN", "VuTan Wholesale", "WN"),
            # If Direct Brand is VuTan and Role is RN - Change Direct Brand to VuTan Retail and keep Role as RN
            ("VuTan", "RN", "VuTan Retail", "RN"),
            # If Direct Brand is TechnoTan Wholesale and Role is WP - Change Direct Brand to TechnoTan Wholesale Preferred and keep Role as WP
            ("TechnoTan Wholesale", "WP", "TechnoTan Wholesale Preferred", "WP"),
            # If Direct Brand is TechnoTan and Role is WP - Change Direct Brand to TechnoTan Wholesale Preferred and keep Role as WP
            ("TechnoTan", "WP", "TechnoTan Wholesale Preferred", "WP"),
            # If Direct Brand is VuTan Wholesale and Role is WP - Change Direct Brand to VuTan Wholesale Preferred and keep Role as WP
            ("VuTan Wholesale", "WP", "VuTan Wholesale Preferred", "WP"),
            # If Direct Brand is VuTan and Role is WP - Change Direct Brand to VuTan Wholesale Preferred and keep Role as WP
            ("VuTan", "WP", "VuTan Wholesale Preferred", "WP"),
            # If Direct Brand is TechnoTan Wholesale and Role is WN - Leave as is
            ("TechnoTan Wholesale", "WN", "TechnoTan Wholesale", "WN"),
            # If Direct Brand is VuTan Wholesale and Role is WN - Leave as is
            ("VuTan Wholesale", "WN", "VuTan Wholesale", "WN"),
            # If Direct Brand is Pending and Role is WN - Leave Direct Brand as pending and change Role to RN
            ("Pending", "WN", "Pending", "RN"),
            # If Direct Brand is TechnoTan Wholesale and Role is WP - Change Direct Brand to TechnoTan Wholesale Preferred and keep Role as WP
                # Duplicate
            # If Direct Brand is VuTan Wholesale and Role is WP - Change Direct Brand to VuTan Wholesale Preferred and keep Role as WP
                # Duplicate
            # If Direct Brand is Tanbience and Role is WN - Change Direct Brand to Tanbience Retail and Role to RN
            # Depracated:
            # ("Tanbience", "WN", "Tanbience Retail", "RN"),
            # If Direct Brand is TechnoTan Wholesale and Role is RN - Change Role to WN
            ("TechnoTan Wholesale", "RN", "TechnoTan Wholesale", "WN"),
            # If Direct Brand is VuTan Wholesale and Role is RN - Change Role to WN
            ("VuTan Wholesale", "RN", "VuTan Wholesale", "WN"),
            # If Direct Brand is PrintWorx and Role is WN - Change Role to RN
            ("PrintWorx", "WN", "PrintWorx", "RN"),
            # If customer has more than one direct brand that includes TechnoTan/TechnoTan Wholesale and role is set to WN - Keep role as WN
                # "???",
            # If customer has more than one direct brand that includes VuTan/VuTan Wholesale and role is set to WN - Keep role as WN
            # If Direct Brand is TechnoTan and Role is XWN - Change Direct Brand to TechnoTan Export and keep Role as XWN
            ("TechnoTan", "XWN", "TechnoTan Wholesale Export", "XWN"),
            # If Direct Brand is VuTan and Role is XWN - Change Direct Brand to VuTan Export and keep Role as XWN
            ("VuTan", "XWN", "VuTan Wholesale Export", "XWN"),
            # If Direct Brand is VuTan Distributor and Role is RN, WP or WN - Leave Direct Brand as is and change Role to DN
            ("VuTan Distributor", "RN", "VuTan Distributor", "DN"),
            ("VuTan Distributor", "WN", "VuTan Distributor", "DN"),
            ("VuTan Distributor", "WP", "VuTan Distributor", "DN"),
            # If Direct Brand is TechnoTan Retail and Role is WN - Change Direct Brand to TechnoTan Wholesale and leave Role as is
            ("TechnoTan Retail", "WN", "TechnoTan Wholesale", "WN"),
            # If Direct Brand is VuTan Retail and Role is WN - Change Direct Brand to VuTan Wholesale and leave Role as is
            ("VuTan Retail", "WN", "VuTan Wholesale", "WN"),
            # If Direct Brand is Pending and Role is ADMIN - Change Direct Brand to Staff and leave Role as is (anyone with ADMIN as the role are staff members that need to have access to the back end of the website, so I'm not sure if Direct Brand Should be something else so all prices are visible?).
            ("Pending", "ADMIN", "Staff", "ADMIN"),
            # If Direct Brand is VuTan and Role is DN - Change Direct Brand to VuTan Distributor and keep Role as DN
            ("VuTan", "DN", "VuTan Distributor", "DN"),
            # If Direct Brand is TechnoTan Wholesale and Role is XDN - Keep direct brand as is and change Role to WN
            ("TechnoTan Wholesale", "XDN", "TechnoTan Wholesale", "WN"),
            # If Direct Brand and Role is blank - Change Direct Brand to Pending and Role to RN
            ("", "", "Pending", "RN"),
            # If Direct Brand is Pending  and Role is RP - Change Role to RN
            ("Pending", "RP", "Pending", "RN"),
            # If Direct Brand is Pending  and Role is WN - Change Role to RN
            ("Pending", "WN", "Pending", "RN"),
            # If Direct Brand is Mosiac Minerals and Role is WN - Change Direct Brand to Mosaic Minerals Retail and Role to RN
            # Deprecated:
            # ("Mosaic Minerals", "WN", "Mosaic Minerals Retail", "RN"),
            # If Direct Brand is Mosaic Minerals and Role is WN - Change Direct Brand to Mosaic Minerals Wholesale and leave role as WN
            ("Mosaic Minerals", "WN", "Mosaic Minerals Wholesale", "WN"),
            # If a person has more than one Direct Brand and their role is set to WN - Leave Role as is and change all Direct Brands to Wholesale. i.e. customers:
            # - C010428 - set Direct Brands as TechnoTan Wholesale and Mosaic Minerals Wholesale and leave Role as WN
            ("Mosaic Minerals;TechnoTan Wholesale", "WN", "Mosaic Minerals Wholesale;TechnoTan Wholesale", "WN"),
            # - C024668 - set Direct Brands as TechnoTan Wholesale and Tanbience Wholesale and leave Role as WN
            ("Tanbience;TechnoTan Wholesale", "WN", "Tanbience Wholesale;TechnoTan Wholesale", "WN"),
            # If Direct Brand is TechnoTan Wholesale and Role is ADMIN - Change Direct Brand to Staff and leave role as ADMIN
            ("TechnoTan Wholesale", "ADMIN", "Staff", "ADMIN"),
            # Janelle Valles C027805 - I have added a Direct Brand now called TechnoTan Retail Export
            # If Direct Brand is Mosaic Minerals and Role is RN - Change Direct Brand to Mosaic Minerals Retail and leave role as RN
            ("Mosaic Minerals", "RN", "Mosaic Minerals Retail", "RN"),

            # --- Derwent Tests ---
            # Remove pending if other roles
            ("Pending;TechnoTan", "RN", "TechnoTan Retail", "RN"),
            (None, "ADMIN", "Staff", "ADMIN"),

        ]:
            rgrp = RoleGroup(role=role, direct_brands=direct_brands)
            result_brand, result_role = rgrp.direct_brands, rgrp.role
            try:
                self.assertEqual(result_brand, expected_brand)
                self.assertEqual(result_role, expected_role)
            except Exception, exc:
                raise AssertionError("failed %s because of exception %s" % (
                    (direct_brands, role, expected_brand, expected_role),
                    str(exc)
                ))

if __name__ == '__main__':
    unittest.main()

    # testSuite = unittest.TestSuite()
    # testSuite.addTest(testContactPhones('test_phones_equality'))
    # unittest.TextTestRunner().run(testSuite)
