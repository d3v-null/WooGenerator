import csv
from collections import OrderedDict
import os
import shutil
from utils import listUtils, sanitationUtils
from csvparse_flat import CSVParse_User
from coldata import ColData_User
import sys

inFolder = "../input/"
outFolder = "../output/"
logFolder = "../logs/"

maPath = os.path.join(inFolder, "act-export-all-changes.csv")
saPath = os.path.join(inFolder, "wordpress-export.csv")

# maPath = os.path.join(inFolder, "100-act-records.csv")
# saPath = os.path.join(inFolder, "100-wp-records.csv")

# master_all
# slave_all
# master_changed
# slave_changed
# master_updates
# slave_updates

#########################################
# Import Info From Spreadsheets
#########################################

colData = ColData_User()
maParser = CSVParse_User(
    cols = colData.getUserCols(),
    defaults = colData.getDefaults()
)

saParser = CSVParse_User(
    cols = colData.getUserCols(),
    defaults = colData.getDefaults()
)

maParser.analyseFile(maPath)

saParser.analyseFile(saPath)

bad_emails = []

for email, saObjects in saParser.emails.items():
    print "email: ", email
    saLen = len(saObjects)
    if saLen > 1:
        bad_emails.append(email)
    print " -> associated slave objects: (%d)"%saLen
    for saObject in saObjects:
        print " --> ", saObject.MYOBID, " | ", saObject.username 
    maObjects = maParser.emails.get(email)
    if maObjects:
        maLen = len(maObjects)
        if maLen > 1:
            bad_emails.append(email)
        print " -> associated master objects: (%d)"%maLen
        for maObject in maObjects:
            print " --> ", maObject.MYOBID, " | ", maObject.username 

print "bad emails:", bad_emails