from csvparse_abstract import CSVParse_Base, ImportItem
from collections import OrderedDict
from coldata import ColData_User
import os
import csv
import re

usrs_per_file = 1000
email_regex = "^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"

class CSVParse_Flat(CSVParse_Base):
    """docstring for CSVParse_Flat"""
    def __init__(self, cols, defaults):
        super(CSVParse_Flat, self).__init__(cols, defaults)

    def sanitizeCell(self, cell):
        return cell

class ImportSpecial(ImportItem):
    """docstring for ImportSpecial"""
    def __init__(self, arg):
        super(ImportSpecial, self).__init__(arg)

    def getID(self):
        return self.get('ID')

class CSVParse_Special(CSVParse_Flat):
    """docstring for CSVParse_Special"""

    def __init__(self, cols=[], defaults={}):
        extra_cols = [
            "ID", 
            "FROM",
            "TO",
            "RNS",
            "RPS",
            "WNS",
            "WPS",
            "XRNS",
            "XRPS",
            "XWNS",
            "XWPS"
        ]
        cols = self.combineLists(cols, extra_cols)
        try:
            assert self.itemContainer 
        except :
            self.itemContainer = ImportSpecial

        super(CSVParse_Special, self).__init__(cols, defaults)

    def getID(self, itemData):
        return itemData.getID()

    def registerItem(self, itemData):
        ID = self.getID(itemData)

        if not ID:
            self.registerError(Exception("no rule ID"), itemData )
            return

        self.registerAnything(
            itemData,
            self.items,
            self.getID,
            singular = True,
            registerName = 'items'
        )          

class ImportUser(ImportItem):
    """docstring for ImportUser"""
    def __init__(self, arg):
        super(ImportUser, self).__init__(arg)

    def getEmail(self):
        return self.get('E-mail')

    def getMYOBID(self):
        return self.get('MYOB Card ID')

    def getUsername(self):
        return self.get('username')

    def getRole(self):
        return self.get('Role')
                            

class CSVParse_User(CSVParse_Flat):
    """docstring for CSVParse_User"""
        
    def __init__(self, cols=[], defaults = {}):
        extra_cols = [  
            # 'ABN', 'Added to mailing list', 'Address 1', 'Address 2', 'Agent', 'Birth Date', 
            # 'book_spray_tan', 'Book-a-Tan Expiry', 'Business Type', 'Canvasser', ''
            # 'post_status'
        ]
        extra_defaults =  OrderedDict([
            # ('post_status', 'publish'),
            # ('last_import', importName),
        ])
        cols = self.combineLists( cols, extra_cols )
        defaults = self.combineOrderedDicts( defaults, extra_defaults )
        try:
            assert self.itemContainer 
        except :
            self.itemContainer = ImportUser
        super(CSVParse_User, self).__init__(cols, defaults)

    def clearTransients(self):
        super(CSVParse_User, self).clearTransients()
        self.roles = OrderedDict()

    def getEmail(self, itemData):
        return itemData.getEmail()

    def getMYOBID(self, itemData):
        return itemData.getMYOBID()

    def getUsername(self, itemData):
        return itemData.getUsername()

    def getRole(self, itemData):
        return itemData.getRole()

    def registerItem(self, itemData):
        email = self.getEmail(itemData)
        if not email or not re.match(email_regex, email):
            self.registerError( Exception("invalid email address: %s"%email), itemData)
            return

        self.registerAnything(
            itemData, 
            self.items, 
            self.getUsername,
            singular = True,
            registerName = 'items'
        )
        role = self.getRole(itemData)
        if not self.roles.get(role): self.roles[role] = OrderedDict()
        self.registerAnything(
            itemData,
            self.roles[role],
            self.getUsername,
            singular = True,
            registerName = 'roles'
        )

    def processItem(self, itemData):
        itemData['username'] = self.getMYOBID(itemData)
        super(CSVParse_Flat, self).processItem(itemData)

    # def analyzeRow(self, row, itemData):
    #     itemData = super(CSVParse_Flat, self).analyseRow(row, itemData)
    #     return itemData

def exportItems(filePath, colNames, items):
    assert filePath, "needs a filepath"
    assert colNames, "needs colNames"
    assert items, "meeds items"
    with open(filePath, 'w+') as outFile:
        dictwriter = csv.DictWriter(
            outFile,
            fieldnames = colNames.keys(),
            extrasaction = 'ignore',
        )
        dictwriter.writerow(colNames)
        dictwriter.writerows(items)
    print "WROTE FILE: ", filePath

if __name__ == '__main__':
    inFolder = "../input/"
    actPath = os.path.join(inFolder, 'export.csv')
    outFolder = "../output/"
    usrPath = os.path.join(outFolder, 'users.csv')

    usrData = ColData_User()

    print "import cols", usrData.getImportCols()
    print "defaults", usrData.getDefaults()

    usrParser = CSVParse_User(
        cols = usrData.getImportCols(),
        defaults = usrData.getDefaults()
    )

    usrParser.analyseFile(actPath)

    usrCols = usrData.getUserCols()

    exportItems(
        usrPath,
        usrData.getColNames(usrCols),
        usrParser.items.values()
    )

    for role, usrs in usrParser.roles.items():

        for i, u in enumerate(range(0, len(usrs), usrs_per_file)):
            rolPath = os.path.join(outFolder, 'users_%s_%d.csv'%(role,i))

            exportItems(
                rolPath,
                usrData.getColNames(usrCols),
                usrs.values()[u:u+usrs_per_file]
            )
        
