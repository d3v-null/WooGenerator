from os import sys, path
if __name__ == '__main__' and __package__ is None:
    sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

from unittest import TestCase, main, skip
from source.contact_objects import *

class testFieldGroups(TestCase):
    def setUp(self):
        FieldGroup.DEBUG_MESSAGE = True
        FieldGroup.DEBUG_WARN = True
        FieldGroup.DEBUG_ERROR = True
        FieldGroup.performPost = True

class testContactAddress(testFieldGroups):

    def test_thoroughfareNumberOnDifferentLine(self):
        address = ContactAddress(
            line1 = "SHOP 10, 575/577",
            line2 = "CANNING HIGHWAY"
        )
        self.assertTrue(address.valid)
        self.assertTrue(address.properties['isShop'])
        self.assertItemsEqual(address.properties['thoroughfares'], [('575/577', 'CANNING', 'HIGHWAY', None)])
        self.assertItemsEqual(address.properties['subunits'], [('SHOP', '10')])

    # @skip("can't handle yet")
    def test_irregularThoroughfareNumber(self):
        address = ContactAddress(
            line1 = 'LEVEL 2, SHOP 202 / 8B "WAX IT"',
            line2 = "ROBINA TOWN CENTRE"
        )
        self.assertTrue(address.properties['isShop'])
        self.assertItemsEqual(address.properties['buildings'], [('ROBINA TOWN', 'CENTRE')])
        self.assertItemsEqual(address.properties['floors'], [('LEVEL', '2')])
        self.assertItemsEqual(address.properties['subunits'], [('SHOP', '202')])
        self.assertTrue(address.problematic)

    def test_BuildingWithNoThoroughfareType(self):
        address = ContactAddress(
            line1 = 'BROADWAY FAIR SHOPPING CTR',
            line2 = 'SHOP 16, 88 BROADWAY'
        )
        self.assertFalse(address.valid)
        self.assertTrue(address.problematic)

    def test_BuildingWithValidThoroughfare(self):
        address = ContactAddress(
            line1 = 'BROADWAY FAIR SHOPPING CTR',
            line2 = 'SHOP 16, 88 BROADWAY FAIR'
        )
        self.assertTrue(address.properties['isShop'])
        self.assertItemsEqual(address.properties['buildings'], [('BROADWAY FAIR', 'SHOPPING CTR')])
        self.assertItemsEqual(address.properties['thoroughfares'], [('88', 'BROADWAY', 'FAIR', None)])
        self.assertItemsEqual(address.properties['subunits'], [('SHOP', '16')])
        self.assertTrue(address.problematic)

    def test_MultipleBuildings(self):
        address = ContactAddress(
            line1 = "SHOP 9 PASPALIS CENTREPOINT",
            line2 = "SMITH STREET MALL"
        )
        self.assertTrue(address.properties['isShop'])
        self.assertItemsEqual(address.properties['buildings'], [('PASPALIS CENTREPOINT', None)])
        self.assertItemsEqual(address.properties['weak_thoroughfares'], [('SMITH STREET', 'MALL', None)])
        self.assertItemsEqual(address.properties['subunits'], [('SHOP', '9')])
        self.assertFalse(address.problematic)
        self.assertTrue(address.valid)

    def test_irregularSlashInSubunit(self):
        address = ContactAddress(
            line1 = 'SUITE 3/ LEVEL 8',
            line2 = '187 MACQUARIE STREET'
        )
        self.assertFalse(address.problematic)
        self.assertTrue(address.valid)
        self.assertItemsEqual(address.properties['floors'], [('LEVEL', '8')])
        self.assertItemsEqual(address.properties['subunits'], [('SUITE', '3')])
        self.assertItemsEqual(address.properties['thoroughfares'], [('187', 'MACQUARIE', 'ST', None)])

        address = ContactAddress(
            line1 = 'UNIT 4/ 12-14 COMENARA CRS',
        )
        self.assertFalse(address.problematic)
        self.assertTrue(address.valid)
        self.assertFalse(address.properties['isShop'])
        self.assertItemsEqual(address.properties['subunits'], [('UNIT', '4')])
        self.assertItemsEqual(address.properties['thoroughfares'], [('12-14', 'COMENARA', 'CRES', None)])

        address = ContactAddress(
            line1 = 'UNIT 4/12-14 COMENARA CRS',
        )
        self.assertFalse(address.problematic)
        self.assertTrue(address.valid)
        self.assertFalse(address.properties['isShop'])
        self.assertItemsEqual(address.properties['subunits'], [('UNIT', '4')])
        self.assertItemsEqual(address.properties['thoroughfares'], [('12-14', 'COMENARA', 'CRES', None)])

        address = ContactAddress(
            line1 = 'UNIT 6/7 38 GRAND BOULEVARD',
        )
        self.assertFalse(address.problematic)
        self.assertTrue(address.valid)
        self.assertFalse(address.properties['isShop'])
        self.assertItemsEqual(address.properties['subunits'], [('UNIT', '6/7')])
        self.assertItemsEqual(address.properties['thoroughfares'], [('38', 'GRAND', 'BLVD', None)])

        address = ContactAddress(
            line1 = 'UNIT 25/39 ASTLEY CRS',
        )

        self.assertFalse(address.problematic)
        self.assertTrue(address.valid)
        self.assertFalse(address.properties['isShop'])
        self.assertItemsEqual(address.properties['subunits'], [('UNIT', '25')])
        self.assertItemsEqual(address.properties['thoroughfares'], [('39', 'ASTLEY', 'CRES', None)])

    @skip("can't handle yet")
    def test_AmbiguousBuildingHard(self):
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
        self.assertItemsEqual(address.properties['subunits'], [('SHOP', '238')])
        self.assertItemsEqual(address.properties['thoroughfares'], [('976', 'TEA TREE', 'PLAZA', None)])

    def test_AmbiguousBuilding(self):
        address = ContactAddress(
            line1 = "73 NORTH PARK AVENUE",
            line2 = "ROCKVILLE CENTRE"
        )
        self.assertTrue(address.problematic)
        self.assertItemsEqual(address.properties['thoroughfares'], [('73', 'NORTH PARK', 'AVE', None)])
        self.assertItemsEqual(address.properties['buildings'], [("ROCKVILLE", "CENTRE")])


    def test_irregularSlashInSubunitAndSplitLines(self):
        address = ContactAddress(
            line1 = 'TOWNHOUSE 4/115 - 121',
            line2 = 'CARINGBAH ROAD'
        )
        self.assertFalse(address.problematic)
        self.assertTrue(address.valid)
        self.assertItemsEqual(address.properties['subunits'], [('TOWNHOUSE', '4')])
        self.assertItemsEqual(address.properties['thoroughfares'], [('115-121', 'CARINGBAH', 'ROAD', None)])

    def test_irregularSlashAbbreviation(self):
        address = ContactAddress(
            line1 = "Factory 5/ inglewood s/c Shop 7/ 12 15th crs"
        )
        self.assertFalse(address.problematic)
        self.assertTrue(address.valid)
        self.assertTrue(address.properties['isShop'])
        self.assertItemsEqual(address.properties['subunits'], [('SHOP', '7'), ('FACTORY', '5')])
        self.assertItemsEqual(address.properties['thoroughfares'], [('12', '15TH', 'CRES', None)])
        self.assertItemsEqual(address.properties['buildings'],[('INGLEWOOD','SHOPPING CENTRE')])

    def test_tooManyNumbers(self):
        address = ContactAddress(
            line1 = 'SHOP 3 81-83',
        )
        self.assertFalse(address.valid)

        address = ContactAddress(
            line1 = 'UNIT 4 / 24',
        )
        self.assertFalse(address.valid)

    def test_coerceThoroughfareType(self):
        address = ContactAddress(
            line1 = "3/3 HOWARD AVE"
        )
        self.assertFalse(address.problematic)
        self.assertTrue(address.valid)
        self.assertItemsEqual(address.properties['thoroughfares'], [('3/3', 'HOWARD', 'AVE', None)])

    def test_dontCoerceBadThoroughfare(self):
        address = ContactAddress(
            line1 = "3/3 HOWARD AVA"
        )
        self.assertTrue(address.problematic)

    def test_coerceSubunitNumberRange(self):
        address = ContactAddress(
            line1 = "6/7 118 RODWAY ARCADE"
        )
        self.assertFalse(address.problematic)
        self.assertTrue(address.valid)
        self.assertItemsEqual(address.properties['thoroughfares'], [('118', 'RODWAY', 'ARC', None)])

    def test_coerceThoroughfare(self):
        address = ContactAddress(
            line1 = "7 Grosvenor",
        )
        self.assertTrue(address.problematic)
        self.assertItemsEqual(address.properties['thoroughfares'], [('7', 'GROSVENOR', None, None)])

        address = ContactAddress(
            line1 = "SH115A, FLOREAT FORUM"
        )
        self.assertTrue(address.valid)
        self.assertItemsEqual(address.properties['subunits'], [('SHOP', '115A')])
        self.assertItemsEqual(address.properties['buildings'],[('FLOREAT', 'FORUM')])

    def test_coerceBuilding(self):
        address = ContactAddress(
            line1 = "SHOP  2052 LEVEL 1 WESTFIELD"
        )
        self.assertFalse(address.problematic)
        self.assertTrue(address.valid)
        self.assertTrue(address.properties['isShop'])
        self.assertItemsEqual(address.properties['floors'], [('LEVEL', '1')])
        self.assertItemsEqual(address.properties['subunits'], [('SHOP', '2052')])
        self.assertItemsEqual(address.properties['buildings'],[('WESTFIELD', None)])

    def test_amperstandThoroughfareNumber(self):
        address = ContactAddress(
            line1 = "SHOP 5&6, 39 MURRAY ST"
        )
        self.assertFalse(address.problematic)
        self.assertTrue(address.valid)
        self.assertTrue(address.properties['isShop'])
        self.assertItemsEqual(address.properties['subunits'], [('SHOP', '5-6')])
        self.assertItemsEqual(address.properties['thoroughfares'], [('39', 'MURRAY', 'ST', None)])

    def test_coerceSubunit(self):
        address = ContactAddress(
            line1 = 'SUIT 1 1 MAIN STREET',
        )
        self.assertTrue(address.problematic)
        self.assertItemsEqual(address.properties['subunits'], [('SUIT', '1')])
        self.assertItemsEqual(address.properties['thoroughfares'], [('1', 'MAIN', 'ST', None)])

        address = ContactAddress(
            line1 = 'SAHOP 5/7-13 BEACH ROAD',
        )
        self.assertTrue(address.problematic)
        self.assertItemsEqual(address.properties['subunits'], [('SAHOP', '5')])
        self.assertItemsEqual(address.properties['thoroughfares'], [('7-13', 'BEACH', 'RD', None)])

        address = ContactAddress(
            line1 = 'THE OFFICE OF SENATOR DAVID BUSHBY',
            line2 = 'LEVE 2, 18 ROSSE AVE'
        )
        self.assertItemsEqual(address.properties['subunits'], [('LEVE', '2')])
        self.assertItemsEqual(address.properties['thoroughfares'], [('18', 'ROSSE', 'AVE', None)])
        self.assertItemsEqual(address.properties['names'], ['THE OFFICE OF SENATOR DAVID BUSHBY'])
        self.assertTrue(address.problematic)

    def test_handleDelivery(self):
        address = ContactAddress(
            line1 = 'P.O.BOX 3385',
        )
        self.assertFalse(address.problematic)
        self.assertTrue(address.valid)
        self.assertItemsEqual(address.properties['deliveries'], [('P.O.BOX', '3385')])

        address = ContactAddress(
            line1 = "PO 5217 MACKAY MAIL CENTRE"
        )
        self.assertFalse(address.problematic)
        self.assertTrue(address.valid)
        self.assertItemsEqual(address.properties['deliveries'], [('PO', '5217')])
        self.assertItemsEqual(address.properties['buildings'], [("MACKAY MAIL", "CENTRE")])

        address = ContactAddress(
            line1 = "G.P.O BOX 440",
            line2 = "CANBERRA CITY",
        )

        self.assertTrue(address.valid)
        self.assertItemsEqual(address.properties['deliveries'], [('G.P.O BOX', '440')])

    def testOrdinalThoroughfare(self):
        address = ContactAddress(
            city = 'ROSSMORE',
            state = 'NSW',
            line1 = "700 15TH AVE",
            line2 = "LANDSBOROUGH PARADE",
            postcode = "2557"
        )
        self.assertTrue(address.problematic)
        self.assertItemsEqual(address.properties['thoroughfares'], [('700', '15TH', 'AVE', None)])

    def test_careof(self):
        address = ContactAddress(
            line1 = "C/O COCO BEACH",
            line2 = "SHOP 3, 17/21 PROGRESS RD"
        )
        self.assertFalse(address.problematic)
        self.assertTrue(address.valid)
        self.assertTrue(address.properties['isShop'])
        self.assertItemsEqual(address.properties['careof_names'], [('C/O', 'COCO BEACH')])
        self.assertItemsEqual(address.properties['subunits'], [('SHOP', '3')])
        self.assertItemsEqual(address.properties['thoroughfares'], [('17/21', 'PROGRESS', 'RD', None)])

        ContactAddress(
            city = 'GOLDEN BEACH',
            state = 'QLD',
            country = 'Australia',
            line1 = "C/- PAMPERED LADY - GOLDEN BEACH SHOPPING CENTRE",
            line2 = "LANDSBOROUGH PARADE",
            postcode = "4551"
        )
        self.assertTrue(address.valid)
        self.assertItemsEqual(address.properties['buildings'],[('GOLDEN BEACH','SHOPPING CENTRE')])
        self.assertItemsEqual(address.properties['careof_names'], [('C/O', 'PAMPERED LADY')])
        self.assertItemsEqual(address.properties['weak_thoroughfares'], [('LANDSBOROUGH', 'PDE', None)])



    def test_nameAndDelivery(self):
        address = ContactAddress(
             line1 = u'ANTONY WHITE, PO BOX 886',
             line2 = u'LEVEL1 468 KINGSFORD SMITH DRIVE'
        )
        self.assertTrue(address.valid)
        self.assertFalse(address.problematic)
        self.assertItemsEqual(address.properties['names'], ['ANTONY WHITE'])
        self.assertItemsEqual(address.properties['deliveries'], [('PO BOX', '886')])
        self.assertItemsEqual(address.properties['floors'], [('LEVEL', '1')])
        self.assertItemsEqual(address.properties['thoroughfares'], [('468', 'KINGSFORD SMITH', 'DR', None)])

    def test_nameSubunitLevelBuilding(self):
        address = ContactAddress(
            line1 = "DANNY, SPG1 LG3 INGLE FARM SHOPPING CENTRE"
        )
        self.assertTrue(address.valid)
        self.assertFalse(address.problematic)
        self.assertItemsEqual(address.properties['names'], [('DANNY')])
        self.assertItemsEqual(address.properties['floors'], [('LG', '3')])
        self.assertItemsEqual(address.properties['subunits'], [('SHOP', 'G1')])
        self.assertItemsEqual(address.properties['buildings'], [('INGLE FARM', 'SHOPPING CENTRE')])

    def testAlphaLevel(self):
        address = ContactAddress(
            line1 = "LEVEL A",
            line2 = "MYER CENTRE",
        )
        self.assertTrue(address.valid)
        self.assertItemsEqual(address.properties['floors'], [('LEVEL', 'A')])
        self.assertItemsEqual(address.properties['buildings'], [('MYER', 'CENTRE')])
        self.assertFalse(address.problematic)










if __name__ == '__main__':
    main()
