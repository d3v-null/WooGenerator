from utils import descriptorUtils, listUtils, sanitationUtils
from csvparse_abstract import CSVParse_Base, ImportObject
from collections import OrderedDict
from coldata import ColData_User
import os
import csv
import re

usrs_per_file = 1000

class ImportFlat(ImportObject):
    pass

class CSVParse_Flat(CSVParse_Base):

    objectContainer = ImportFlat
    # def __init__(self, cols, defaults):
    #     super(CSVParse_Flat, self).__init__(cols, defaults)

class ImportSpecial(ImportFlat):
    def __init__(self,  data, rowcount, row):
        super(ImportSpecial, self).__init__(data, rowcount, row)
        try:
            self.ID
        except:
            raise UserWarning('ID exist for Special to be valid')

    ID = descriptorUtils.safeKeyProperty('ID')

    def getIndex(self):
        return self.ID

class CSVParse_Special(CSVParse_Flat):

    objectContainer = ImportSpecial

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
        self.objectIndexer = self.getObjectID

    def getObjectID(self, objectData):
        return objectData.ID     

class ImportUser(ImportObject):

    email = descriptorUtils.safeKeyProperty('E-mail')
    MYOBID = descriptorUtils.safeKeyProperty('MYOB Card ID')
    username = descriptorUtils.safeKeyProperty('username')
    role = descriptorUtils.safeKeyProperty('Role')
                            
class CSVParse_User(CSVParse_Flat):

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

    def registerObject(self, objectData):
        email = objectData.email
        if not email or not sanitationUtils.stringIsEmail(email) :
            raise Exception("invalid email address: %s"%email)
        super(CSVParse_User, self).registerObject(objectData)

    def processRoles(self, objectData):
        role = objectData.role
        if not self.roles.get(role): self.roles[role] = OrderedDict()
        self.registerAnything(
            objectData,
            self.roles[role],
            self.getUsername,
            singular = True,
            registerName = 'roles'
        )

    def processObject(self, objectData):
        objectData.username = self.getMYOBID(objectData)
        super(CSVParse_Flat, self).processObject(objectData)
        self.processRoles(objectData) 

    # def analyzeRow(self, row, objectData):
    #     objectData = super(CSVParse_Flat, self).analyseRow(row, objectData)
    #     return objectData

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
        
