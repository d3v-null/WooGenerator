from csvparse_abstract import CSVParse_Base, ImportObject, listUtils
from collections import OrderedDict
from coldata import ColData_User
import os
import csv
import re

usrs_per_file = 1000
email_regex = "^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"

class ImportFlat(ImportObject):
    pass

class CSVParse_Flat(CSVParse_Base):
    """docstring for CSVParse_Flat"""
    # def __init__(self, cols, defaults):
    #     super(CSVParse_Flat, self).__init__(cols, defaults)

class ImportSpecial(ImportFlat):
    """docstring for ImportSpecial"""
    def __init__(self,  data, rowcount, row, ID):
        super(ImportSpecial, self).__init__(data, rowcount, row)
        self['ID'] = ID

    def getID(self):
        return self['ID']

    def getIndex(self):
        return self.getID()

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
        cols = listUtils.combineLists(cols, extra_cols)

        super(CSVParse_Special, self).__init__(cols, defaults)
        self.itemContainer = ImportSpecial
        self.itemIndexer = self.getID

    def getID(self, itemData):
        return itemData.getID()

    def newObject(self, rowcount, row):
        retrieved = self.retrieveColFromRow('ID', row)
        assert retrieved, "must be able to retrieve ID for special"
        ID = self.sanitizeCell(retrieved)
        return self.itemContainer( self.defaults.items(), rowcount, row, ID )

    def registerItem(self, itemData):
        if not self.itemIndexer(itemData):
            self.registerError(Exception("invalid index"), itemData )
            return
        super(CSVParse_Flat, self).registerItem(itemData)         

class ImportUser(ImportObject):
    """docstring for ImportUser"""
    def __init__(self, *args):
        super(ImportUser, self).__init__(*args)

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
        cols = listUtils.combineLists( cols, extra_cols )
        defaults = listUtils.combineOrderedDicts( defaults, extra_defaults )
        try:
            assert self.itemContainer 
        except :
            self.itemContainer = ImportUser
        super(CSVParse_User, self).__init__(cols, defaults)
        self.itemIndexer = self.getUsername

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
            raise Exception("invalid email address: %s"%email)
        super(CSVParse_User, self).registerItem(itemData)

    def processRoles(self, itemData):
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
        self.processRoles(itemData) 

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
    actPath = os.path.join(inFolder, 'partial act records.csv')
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
        usrParser.objects.values()
    )

    for role, usrs in usrParser.roles.items():
        for i, u in enumerate(range(0, len(usrs), usrs_per_file)):
            rolPath = os.path.join(outFolder, 'users_%s_%d.csv'%(role,i))

            exportItems(
                rolPath,
                usrData.getColNames(usrCols),
                usrs.values()[u:u+usrs_per_file]
            )
        
