import unittest
from unittest import TestCase

from context import woogenerator
from woogenerator.contact_objects import (FieldGroup, SocialMediaFields,
                                          ContactAddress, ContactName,
                                          ContactPhones, RoleGroup)

class TestFieldGroups(TestCase):

    def setUp(self):
        # defaults
        FieldGroup.DEBUG_ERROR = False
        FieldGroup.DEBUG_WARN = False
        FieldGroup.DEBUG_MESSAGE = False
        FieldGroup.perform_post = True
        FieldGroup.enforce_mandatory_keys = False

        # Temporarily enable debugging
        # FieldGroup.DEBUG_MESSAGE = True
        # FieldGroup.DEBUG_WARN = True
        # FieldGroup.DEBUG_ERROR = True
        # FieldGroup.DEBUG_CONTACT = True
        # FieldGroup.DEBUG_ADDRESS = True

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

    # @unittest.skip("can't handle yet")
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

    # @unittest.skip("can't handle yet")
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
        self.assertEqual(
            address.properties['buildings'],
            [('BAYSIDE', 'SHOP. CENTRE')]
        )
        self.assertItemsEqual(
            address.properties['subunits'],
            [('SHOP', 'G33Q')]
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


class TestContactName(TestFieldGroups):

    def test_basic_name(self):
        name = ContactName(
            contact="Derwent McElhinney"
        )
        self.assertTrue(name.valid)
        self.assertEqual(name.first_name, "DERWENT")
        self.assertEqual(name.family_name, "MCELHINNEY")

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
    def test(self):
        pass

if __name__ == '__main__':
    unittest.main()

    # testSuite = unittest.TestSuite()
    # testSuite.addTest(testContactPhones('test_phones_equality'))
    # unittest.TextTestRunner().run(testSuite)
