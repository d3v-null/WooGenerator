from os import sys, path
import random
# import unittest
import traceback
from unittest import main #, skip, TestCase
# from tabulate import tabulate
from bisect import insort

if __name__ == '__main__' and __package__ is None:
    sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

from testSyncClient import abstractSyncClientTestCase
from source.utils import TimeUtils, Registrar, SanitationUtils
from source.sync_client_user import UsrSyncClient_WP
from source.coldata import ColData_User
from source.csvparse_user import CSVParse_User, CSVParse_User_Api #, ImportUser
from source.matching import UsernameMatcher, MatchList #, CardMatcher, NocardEmailMatcher, EmailMatcher
from source.SyncUpdate import SyncUpdate, SyncUpdate_Usr_Api

class testUsrSyncUpdate(abstractSyncClientTestCase):
    yamlPath = "merger_config.yaml"
    optionNamePrefix = 'test_'

    def __init__(self, *args, **kwargs):
        super(testUsrSyncUpdate, self).__init__(*args, **kwargs)
        self.SSHTunnelForwarderParams = {}
        self.PyMySqlConnectParams = {}
        self.jsonConnectParams = {}
        self.actConnectParams = {}
        self.actDbParams = {}
        self.fsParams = {}

    def processConfig(self, config):
        wp_srv_offset = config.get(self.optionNamePrefix+'wp_srv_offset', 0)
        wp_api_key = config.get(self.optionNamePrefix+'wp_api_key')
        wp_api_secret = config.get(self.optionNamePrefix+'wp_api_secret')
        store_url = config.get(self.optionNamePrefix+'store_url', '')
        wp_user = config.get(self.optionNamePrefix+'wp_user')
        wp_pass = config.get(self.optionNamePrefix+'wp_pass')
        wp_callback = config.get(self.optionNamePrefix+'wp_callback')

        TimeUtils.setWpSrvOffset(wp_srv_offset)

        self.wpApiParams = {
            'api_key': wp_api_key,
            'api_secret': wp_api_secret,
            'url':store_url,
            'wp_user':wp_user,
            'wp_pass':wp_pass,
            'callback':wp_callback
        }

    def setUp(self):
        super(testUsrSyncUpdate, self).setUp()

        for var in ['wpApiParams']:
            print var, getattr(self, var)

        Registrar.DEBUG_API = True

    def testUploadSlaveChanges(self):

        maParser = CSVParse_User(
            cols=ColData_User.getACTImportCols(),
            defaults=ColData_User.getDefaults()
        )

        master_data = [map(unicode, row) for row in [
            ["E-mail","Role","First Name","Surname","Nick Name","Contact","Client Grade","Direct Brand","Agent","Birth Date","Mobile Phone","Fax","Company","Address 1","Address 2","City","Postcode","State","Country","Phone","Home Address 1","Home Address 2","Home City","Home Postcode","Home Country","Home State","MYOB Card ID","MYOB Customer Card ID","Web Site","ABN","Business Type","Referred By","Lead Source","Mobile Phone Preferred","Phone Preferred","Personal E-mail","Edited in Act","Wordpress Username","display_name","ID","updated"],
            ["neil@technotan.com.au","ADMIN","Neil","Cunliffe-Williams","Neil Cunliffe-Williams","","","","","",+61416160912,"","Laserphile","7 Grosvenor Road","","Bayswater",6053,"WA","AU","0416160912","7 Grosvenor Road","","Bayswater",6053,"AU","WA","","","http://technotan.com.au",32,"","","","","","","","neil","Neil",1,"2015-07-13 22:33:05"]
        ]]

        maParser.analyseRows(master_data)

        print "MASTER RECORDS: \n", maParser.tabulate()

        saParser = CSVParse_User_Api(
            cols=ColData_User.getWPImportCols(),
            defaults=ColData_User.getDefaults()
        )

        with UsrSyncClient_WP(self.wpApiParams) as slaveClient:
            slaveClient.analyseRemote(saParser)

        print "SLAVE RECORDS: \n", saParser.tabulate()

        updates = []
        globalMatches = MatchList()

        # Matching 
        usernameMatcher = UsernameMatcher()
        usernameMatcher.processRegisters(saParser.usernames, maParser.usernames)
        globalMatches.addMatches( usernameMatcher.pureMatches)

        print "username matches (%d pure)" % len(usernameMatcher.pureMatches)


        # updates = ???

        slaveFailures = []

        nonce = str(random.random())


        with UsrSyncClient_WP(self.wpApiParams) as slaveClient:

            for count, update in enumerate(updates):
                try:
                    update.updateSlave(slaveClient)
                except Exception, e:
                    slaveFailures.append({
                        'update':update,
                        'master':SanitationUtils.coerceUnicode(update.newMObject),
                        'slave':SanitationUtils.coerceUnicode(update.newSObject),
                        'mchanges':SanitationUtils.coerceUnicode(update.getMasterUpdates()),
                        'schanges':SanitationUtils.coerceUnicode(update.getSlaveUpdates()),
                        'exception':repr(e)
                    })
                    Registrar.registerError("ERROR UPDATING SLAVE (%s): %s\n%s" % (
                        update.SlaveID, 
                        repr(e),
                        traceback.format_exc() 
                    ) )


if __name__ == '__main__':
    main()