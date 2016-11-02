# import re
from collections import OrderedDict
import os
import shutil
from PIL import Image
# import time
# import datetime
import argparse
import io

# from itertools import chain
from metagator import MetaGator
from utils import listUtils, SanitationUtils, TimeUtils, debugUtils, ProgressCounter
from utils import HtmlReporter
from csvparse_abstract import Registrar
from csvparse_shop import ShopProdList, ShopObjList
from csvparse_woo import CSVParse_TT, CSVParse_VT, CSVParse_Woo
from csvparse_woo import WooCatList, WooProdList, WooVarList
from csvparse_api import CSVParse_Woo_Api
from csvparse_myo import CSVParse_MYO, MYOProdList
from csvparse_dyn import CSVParse_Dyn
from csvparse_flat import CSVParse_Special, CSVParse_WPSQLProd
from csvparse_api import CSVParse_Woo_Api
from coldata import ColData_Woo, ColData_MYO , ColData_Base
from sync_client import SyncClient_GDrive
from sync_client_prod import ProdSyncClient_WC, CatSyncClient_WC
from matching import ProductMatcher, CategoryMatcher
from SyncUpdate import SyncUpdate, SyncUpdate_Prod, SyncUpdate_Prod_Woo, SyncUpdate_Cat_Woo
from bisect import insort
from matching import MatchList
from tabulate import tabulate
import urlparse
import webbrowser
import re
from pprint import pformat, pprint
import time

# import xml.etree.ElementTree as ET
# import rsync
# import sys
import yaml
# import re
# import MySQLdb
# from sshtunnel import SSHTunnelForwarder

testMode = False
testMode = True

### DEFAULT CONFIG ###

inFolder = "../input/"
outFolder = "../output/"
logFolder = "../logs/"
srcFolder = "../source"

os.chdir('source')

yamlPath = "generator_config.yaml"

repPath = ''

thumbsize = 1920, 1200

importName = TimeUtils.getMsTimeStamp()

### Process YAML file for defaults ###

with open(yamlPath) as stream:
    config = yaml.load(stream)
    #overrides
    if 'inFolder' in config.keys():
        inFolder = config['inFolder']
    if 'outFolder' in config.keys():
        outFolder = config['outFolder']
    if 'logFolder' in config.keys():
        logFolder = config['logFolder']

    #mandatory
    merge_mode = config.get('merge_mode', 'sync')
    MASTER_NAME = config.get('master_name', 'MASTER')
    SLAVE_NAME = config.get('slave_name', 'SLAVE')
    DEFAULT_LAST_SYNC = config.get('default_last_sync')
    webFolder = config.get('webFolder')
    webAddress = config.get('webAddress')
    webBrowser = config.get('webBrowser')
    myo_schemas = config.get('myo_schemas')
    woo_schemas = config.get('woo_schemas')
    taxoDepth = config.get('taxoDepth')
    itemDepth = config.get('itemDepth')

    #optional
    imgRawFolder = config.get('imgRawFolder')
    imgCmpFolder = config.get('imgCmpFolder')
    fallback_schema = config.get('fallback_schema')
    fallback_variant = config.get('fallback_variant')

    # ssh_user = config.get('ssh_user')
    # ssh_pass = config.get('ssh_pass')
    # ssh_host = config.get('ssh_host')
    # ssh_port = config.get('ssh_port', 22)
    # remote_bind_host = config.get('remote_bind_host', '127.0.0.1')
    # remote_bind_port = config.get('remote_bind_port', 3306)
    # db_user = config.get('db_user')
    # db_pass = config.get('db_pass')
    # db_name = config.get('db_name')
    # tbl_prefix = config.get('tbl_prefix', '')

    gdrive_scopes = config.get('gdrive_scopes')
    gdrive_client_secret_file = config.get('gdrive_client_secret_file')
    gdrive_app_name = config.get('gdrive_app_name')
    gdrive_oauth_clientID = config.get('gdrive_oauth_clientID')
    gdrive_oauth_clientSecret = config.get('gdrive_oauth_clientSecret')
    gdrive_credentials_dir = config.get('gdrive_credentials_dir')
    gdrive_credentials_file = config.get('gdrive_credentials_file')
    genFID = config.get('genFID')
    genGID = config.get('genGID')
    dprcGID = config.get('dprcGID')
    dprpGID = config.get('dprpGID')
    specGID = config.get('specGID')
    usGID = config.get('usGID')
    xsGID = config.get('xsGID')

    skip_google_download = config.get('skip_google_download')
    show_report = config.get('show_report')
    report_and_quit = config.get('report_and_quit')
    do_images = config.get('do_images')
    do_specials = config.get('do_specials')
    do_dyns = config.get('do_dyns')
    do_sync = config.get('do_sync')
    do_delete_images = config.get('do_delete_images')
    do_resize_images = config.get('do_resize_images')
    do_remeta_images = config.get('do_remeta_images')

    current_special = config.get('current_special')
    add_special_categories = config.get('add_special_categories')
    download_master = config.get('download_master')
    download_slave = config.get('download_slave')
    update_slave = config.get('update_slave')

#mandatory params
assert all([inFolder, outFolder, logFolder, woo_schemas, myo_schemas, taxoDepth, itemDepth])

genPath = os.path.join(inFolder, 'generator.csv')
dprcPath= os.path.join(inFolder, 'DPRC.csv')
dprpPath= os.path.join(inFolder, 'DPRP.csv')
specPath= os.path.join(inFolder, 'specials.csv')
usPath  = os.path.join(inFolder, 'US.csv')
xsPath  = os.path.join(inFolder, 'XS.csv')

sqlPath = os.path.join(srcFolder, 'select_productdata.sql')

### GET SHELL ARGS ###

parser = argparse.ArgumentParser(description = 'Generate Import files from Google Drive')
group = parser.add_mutually_exclusive_group()
group.add_argument("-v", "--verbosity", action="count",
                    help="increase output verbosity")
group.add_argument("-q", "--quiet", action="store_true")
parser.add_argument('--testmode', help='Run in test mode with test servers',
                    action='store_true')
group = parser.add_mutually_exclusive_group()
group.add_argument('--download-master', help='download the master data from google',
                   action="store_true", default=None)
group.add_argument('--skip-download-master', help='use the local master file instead\
    of downloading the master data', action="store_false", dest='download_master')
group = parser.add_mutually_exclusive_group()
group.add_argument('--download-slave', help='download the slave data',
                   action="store_true", default=None)
group.add_argument('--skip-download-slave', help='use the local slave file instead\
    of downloading the slave data', action="store_false", dest='download_slave')
group = parser.add_mutually_exclusive_group()
group.add_argument('--update-slave', help='update the slave database in WooCommerce',
                   action="store_true", default=None)
group.add_argument('--skip-update-slave', help='don\'t update the slave database',
                   action="store_false", dest='update_slave', default=update_slave)
group = parser.add_mutually_exclusive_group()
group.add_argument('--do-sync', help='sync the databases',
                  action="store_true", default=None)
group.add_argument('--skip-sync', help='don\'t sync the databases',
                  action="store_false", dest='do_sync', default=do_sync)
group = parser.add_mutually_exclusive_group()
group.add_argument('--show-report', help='show report',
                   action="store_true", default=show_report)
group.add_argument('--skip-report', help='don\'t show report',
                   action="store_false", dest='show_report')
group = parser.add_mutually_exclusive_group()
group.add_argument('--report-and-quit', help='quit after generating report',
                   action="store_true", default=report_and_quit)
group = parser.add_mutually_exclusive_group()
group.add_argument('--do-images', help='process images',
                   action="store_true", default=do_images)
group.add_argument('--skip-images', help='don\'t process images',
                   action="store_false", dest='do_images')
group = parser.add_mutually_exclusive_group()
group.add_argument('--do-specials', help='process specials',
                   action="store_true", default=do_specials)
group.add_argument('--skip-specials', help='don\'t process specials',
                   action="store_false", dest='do_specials')
group = parser.add_mutually_exclusive_group()
group.add_argument('--do-dyns', help='process dyns',
                   action="store_true", default=do_dyns)
group.add_argument('--skip-dyns', help='don\'t process dyns',
                   action="store_false", dest='do_dyns')
group = parser.add_mutually_exclusive_group()
group.add_argument('--do-delete-images', help='delete extra images in compressed folder',
                   action="store_true", default=do_delete_images)
group.add_argument('--skip-delete-images', help='protect images from deletion',
                   action="store_false", dest='do_delete_images')
group = parser.add_mutually_exclusive_group()
group.add_argument('--do-resize-images', help='resize images in compressed folder',
                   action="store_true", default=do_resize_images)
group.add_argument('--skip-resize-images', help='protect images from resizing',
                   action="store_false", dest='do_resize_images')
parser.add_argument('--img-raw-folder', help='location of raw images',
                    default=imgRawFolder)
parser.add_argument('--img-raw-extra-folder', help='location of additional raw images',
                    default='')
parser.add_argument('--current-special', help='prefix of current special code')
parser.add_argument('--add-special-categories', help='add special items to special category', action="store_true", default=None)
parser.add_argument('--schema', help='what schema to process the files as', default=fallback_schema)
parser.add_argument('--variant', help='what variant of schema to process the files', default=fallback_variant)
parser.add_argument('--taxo-depth', help='what depth of taxonomy columns is used in the generator file', default=taxoDepth)
parser.add_argument('--item-depth', help='what depth of item columns is used in the generator file', default=itemDepth)
parser.add_argument('--limit', type=int, help='global limit of objects to process')

group = parser.add_argument_group()
group.add_argument('--debug-abstract', action='store_true', dest='debug_abstract')
group.add_argument('--debug-parser', action='store_true', dest='debug_parser')
group.add_argument('--debug-flat', action='store_true', dest='debug_flat')
group.add_argument('--debug-client', action='store_true', dest='debug_client')
group.add_argument('--debug-utils', action='store_true', dest='debug_utils')
group.add_argument('--debug-gen', action='store_true', dest='debug_gen')
group.add_argument('--debug-myo', action='store_true', dest='debug_myo')
group.add_argument('--debug-tree', action='store_true', dest='debug_tree')
group.add_argument('--debug-woo', action='store_true', dest='debug_woo')
group.add_argument('--debug-name', action='store_true', dest='debug_name')
group.add_argument('--debug-img', action='store_true', dest='debug_img')
group.add_argument('--debug-api', action='store_true', dest='debug_api')
group.add_argument('--debug-shop', action='store_true', dest='debug_shop')
group.add_argument('--debug-update', action='store_true', dest='debug_update')
group.add_argument('--debug-mro', action='store_true', dest='debug_mro')

args = parser.parse_args()
if args:
    print args
    if args.verbosity > 0:
        Registrar.DEBUG_PROGRESS = True
        Registrar.DEBUG_ERROR = True
    if args.verbosity > 1:
        Registrar.DEBUG_MESSAGE = True
    if args.quiet:
        Registrar.DEBUG_PROGRESS = False
        Registrar.DEBUG_ERROR = False
        Registrar.DEBUG_MESSAGE = False
    if args.testmode is not None:
        testMode = args.testmode
    if args.download_master is not None:
        download_master = args.download_master
    if args.download_slave is not None:
        download_slave = args.download_slave
    if args.update_slave is not None:
        update_slave = args.update_slave
    if args.current_special:
        current_special = args.current_special
    if args.add_special_categories:
        add_special_categories = args.add_special_categories
    if args.taxo_depth:
        taxoDepth = args.taxo_depth
    if args.item_depth:
        itemDepth = args.item_depth
    if args.do_images is not None:
        do_images = args.do_images
    if args.do_specials is not None:
        do_specials = args.do_specials
    if args.do_dyns is not None:
        do_dyns = args.do_dyns
    if args.do_sync is not None:
        do_sync = args.do_sync and download_slave
    if args.show_report is not None:
        show_report = args.show_report
    if args.report_and_quit is not None:
        report_and_quit = args.report_and_quit
    global_limit = args.limit

    schema = args.schema
    variant = args.variant
    do_images = args.do_images
    do_delete_images = args.do_delete_images
    do_resize_images = args.do_resize_images
    do_resize_images = args.do_resize_images
    imgRawFolder = args.img_raw_folder
    imgRawFolders = [imgRawFolder]
    if args.img_raw_extra_folder is not None:
        imgRawFolders.append(args.img_raw_extra_folder)

    if args.debug_abstract is not None:
        Registrar.DEBUG_ABSTRACT = args.debug_abstract
    if args.debug_parser is not None:
        Registrar.DEBUG_PARSER = args.debug_parser
    if args.debug_flat is not None:
        Registrar.DEBUG_FLAT = args.debug_flat
    if args.debug_gen is not None:
        Registrar.DEBUG_GEN = args.debug_gen
    if args.debug_myo is not None:
        Registrar.DEBUG_MYO = args.debug_myo
    if args.debug_tree is not None:
        Registrar.DEBUG_TREE = args.debug_tree
    if args.debug_woo is not None:
        Registrar.DEBUG_WOO = args.debug_woo
    if args.debug_name is not None:
        Registrar.DEBUG_NAME = args.debug_name
    if args.debug_img is not None:
        Registrar.DEBUG_IMG = args.debug_img
    if args.debug_api is not None:
        Registrar.DEBUG_API = args.debug_api
    if args.debug_shop is not None:
        Registrar.DEBUG_SHOP = args.debug_shop
    if args.debug_update is not None:
        Registrar.DEBUG_UPDATE = args.debug_update
    if args.debug_mro is not None:
        Registrar.DEBUG_MRO = args.debug_mro

#process YAML file after determining mode

with open(yamlPath) as stream:
    optionNamePrefix = 'test_' if testMode else ''
    config = yaml.load(stream)
    wc_api_key = config.get(optionNamePrefix+'wc_api_key')
    wc_api_secret = config.get(optionNamePrefix+'wc_api_secret')
    wp_srv_offset = config.get(optionNamePrefix+'wp_srv_offset', 0)
    store_url = config.get(optionNamePrefix+'store_url', '')

### PROCESS CONFIG ###

TimeUtils.setWpSrvOffset(wp_srv_offset)
SyncUpdate.setGlobals( MASTER_NAME, SLAVE_NAME, merge_mode, DEFAULT_LAST_SYNC)

if variant == "ACC":
    genPath = os.path.join(inFolder, 'generator-solution.csv')

if variant == "SOL":
    genPath = os.path.join(inFolder, 'generator-accessories.csv')

suffix = schema
if variant:
    suffix += "-" + variant

flaPath = os.path.join(outFolder , "flattened-"+suffix+".csv")
flvPath = os.path.join(outFolder , "flattened-variations-"+suffix+".csv")
catPath = os.path.join(outFolder , "categories-"+suffix+".csv")
myoPath = os.path.join(outFolder , "myob-"+suffix+".csv")
bunPath = os.path.join(outFolder , "bundles-"+suffix+".csv")
repName = "prod_sync_report%s.html" % suffix
repPath = os.path.join(outFolder, repName)
repWebPath = os.path.join(webFolder, repName)
repWebLink = urlparse.urljoin(webAddress, repName)

# masterResCsvPath = os.path.join(outFolder, "sync_report_act%s.csv" % suffix)
# masterDeltaCsvPath = os.path.join(outFolder, "delta_report_act%s.csv" % suffix)
slaveDeltaCsvPath = os.path.join(outFolder, "delta_report_wp%s.csv" % suffix)

# xmlPath = os.path.join(outFolder , "items-"+suffix+".xml")
# objPath = os.path.join(webFolder, "objects-"+suffix+".xml")
# spoPath = os.path.join(outFolder , "specials-"+suffix+".html")
# wpaiFolder = os.path.join(webFolder, "images-"+schema)
# refFolder = wpaiFolder
imgDst = os.path.join(imgCmpFolder, "images-"+schema)

maxDepth = taxoDepth + itemDepth

if current_special:
    CSVParse_Woo.specialsCategory = "Specials"
    CSVParse_Woo.current_special = current_special
    CSVParse_Woo.add_special_categories = add_special_categories

if skip_google_download:
    SyncClient_GDrive.skip_download = True

CSVParse_Woo.do_images = do_images
CSVParse_Woo.do_dyns = do_dyns
CSVParse_Woo.do_specials = do_specials

### DISPLAY CONFIG ###
if Registrar.DEBUG_MESSAGE:
    if testMode:
        print "testMode enabled"
    else:
        print "testMode disabled"
    if not download_master:
        print "no download_master"
    if not update_slave:
        print "not updating slave"

#
# gDriveFsParams = {
#     'csvPaths': {
#         'gen': genPath,
#         'dprc': dprcPath,
#         'dprp': dprpPath,
#         'spec': specPath,
#         'us': usPath,
#         'xs': xsPath,
#     }
# }

########################################
# Create Product Parser object
########################################

gDriveParams = {
    'scopes': gdrive_scopes,
    'client_secret_file': gdrive_client_secret_file,
    'app_name': gdrive_app_name,
    'oauth_clientID': gdrive_oauth_clientID,
    'oauth_clientSecret': gdrive_oauth_clientSecret,
    'credentials_dir': gdrive_credentials_dir,
    'credentials_file': gdrive_credentials_file,
    'genFID': genFID,
}

wcApiParams = {
    'api_key':wc_api_key,
    'api_secret':wc_api_secret,
    'url':store_url
}

apiProductParserArgs = {
    'importName': importName,
    'itemDepth': itemDepth,
    'taxoDepth': taxoDepth,
    'cols': ColData_Woo.getImportCols(),
    'defaults': ColData_Woo.getDefaults(),
}

productParserArgs = {
    'importName': importName,
    'itemDepth': itemDepth,
    'taxoDepth': taxoDepth,
}

if Registrar.DEBUG_GEN:
    for thing in ['gDriveParams', 'wcApiParams', 'apiProductParserArgs', 'productParserArgs']:
        Registrar.registerMessage( "%s: %s" % (thing, eval(thing)))


if schema in myo_schemas:
    colDataClass = ColData_MYO
elif schema in woo_schemas:
    colDataClass = ColData_Woo
else:
    colDataClass = ColData_Base
productParserArgs.update(**{
    'cols': colDataClass.getImportCols(),
    'defaults': colDataClass.getDefaults(),
})
if schema in myo_schemas:
    productParserClass = CSVParse_MYO
elif schema in woo_schemas:
    if schema == "TT":
        productParserClass = CSVParse_TT
    elif schema == "VT":
        productParserClass = CSVParse_VT
    else:
        productParserArgs['schema'] = schema
        productParserClass = CSVParse_Woo
if download_master:
    with SyncClient_GDrive(gDriveParams) as client:
        if schema in woo_schemas:
            if do_dyns:
                Registrar.registerMessage("analysing dprc rules")
                dynParser = CSVParse_Dyn()
                client.analyseRemote(dynParser, dprcGID, dprcPath)
                dprcRules = dynParser.taxos
                productParserArgs['dprcRules'] = dprcRules

                Registrar.registerMessage("analysing dprp rules")
                dynParser.clearTransients()
                client.analyseRemote(dynParser, dprpGID, dprpPath)
                dprpRules = dynParser.taxos
                productParserArgs['dprpRules'] = dprpRules

            if do_specials:
                Registrar.registerMessage("analysing specials")
                specialParser = CSVParse_Special()
                client.analyseRemote(specialParser, specGID, specPath)
                specials = specialParser.objects
                productParserArgs['specials'] = specials

        productParser = productParserClass(**productParserArgs)

        Registrar.registerMessage("analysing products")
        client.analyseRemote(productParser, None, genPath, limit=global_limit)
else:
    if schema in woo_schemas:
        if do_dyns:
            Registrar.registerMessage("analysing dprc rules")
            dynParser = CSVParse_Dyn()
            dynParser.analyseFile(dprcPath)
            dprcRules = dynParser.taxos
            productParserArgs['dprcRules'] = dprcRules

            Registrar.registerMessage("analysing dprp rules")
            dynParser.clearTransients()
            dynParser.analyseFile(dprpPath)
            dprpRules = dynParser.taxos
            productParserArgs['dprpRules'] = dprpRules

        if do_specials:
            Registrar.registerMessage("analysing specials")
            specialParser = CSVParse_Special()
            specialParser.analyseFile(specPath)
            specials = specialParser.objects
            productParserArgs['specials'] = specials

    productParser = productParserClass(**productParserArgs)
    Registrar.registerMessage("analysing products")
    productParser.analyseFile(genPath, limit=global_limit)

products = productParser.products

if schema in woo_schemas:
    attributes     = productParser.attributes
    vattributes    = productParser.vattributes
    categories     = productParser.categories
    variations     = productParser.variations
    images         = productParser.images

if Registrar.errors:
    print "there were some errors that need to be reviewed before sync can happen"
    Registrar.print_message_dict(0)
    quit()
elif Registrar.warnings:
    print "there were some warnings that should be reviewed"
    Registrar.print_message_dict(1)

for category_name, category_list in productParser.categories_name.items():
    if len(category_list) < 2: continue
    if listUtils.checkEqual([category.namesum for category in category_list]): continue
    print "bad category: %50s | %d | %s" % (category_name[:50], len(category_list), str(category_list))

# quit()

#########################################
# Images
#########################################

if do_images and schema in woo_schemas:
    # e = UserWarning("do_images currently not supported")
    # Registrar.registerError(e)
    # raise e

    print ""
    print "Images:"
    print "==========="

    def invalidImage(img_name, error):
        Registrar.registerError(error, img_name)
        images[img_name].invalidate(error)

    ls_raw = {}
    for folder in imgRawFolders:
        if folder:
            ls_raw[folder] = os.listdir(folder)

    def getRawImage(img_name):
        for path in imgRawFolders:
            if path and img_name in ls_raw[path]:
                return os.path.join(path, img_name)
        raise UserWarning("no image named %s found" % str(img_name))

    if not os.path.exists(imgDst):
        os.makedirs(imgDst)

    #list of images in compressed directory
    ls_cmp = os.listdir(imgDst)
    for f in ls_cmp:
        if f not in images.keys():
            Registrar.registerWarning("DELETING FROM REFLATTENED", f)
            if do_delete_images:
                os.remove(os.path.join(imgDst,f))

    for img, data in images.items():
        if not data.products:
            continue
            # we only care about product images atm
        if Registrar.DEBUG_IMG:
            if data.categories:
                Registrar.registerMessage(
                    "Associated Taxos: " + str([(taxo.rowcount, taxo.codesum) for taxo in data.categories]),
                    img
                )

            # if data.items:
            #     Registrar.registerMessage(
            #         "Associated Items: " + str([(item.rowcount, item.codesum) for item in data.items]),
            #         img
            #     )

            if data.products:
                Registrar.registerMessage(
                    "Associated Products: " + str([(item.rowcount, item.codesum) for item in data.products]),
                    img
                )

        try:
            imgRawPath = getRawImage(img)
        except Exception as e:
            invalidImage(img, UserWarning("could not get raw image: %s " % repr(e)))
            continue

        name, ext = os.path.splitext(img)
        if(not name):
            invalidImage(img, UserWarning("could not extract name"))
            continue

        try:
            title, description = data.title, data.description
        except Exception as e:
            invalidImage(img, "could not get title or description: "+str(e) )
            continue

        if Registrar.DEBUG_IMG:
            Registrar.registerMessage("title: %s | description: %s" % (title, description), img)

        # ------
        # REMETA
        # ------

        try:
            if do_remeta_images:
                metagator = MetaGator(imgRawPath)
        except Exception, e:
            invalidImage(img, "error creating metagator: " + str(e))
            continue

        try:
            if do_remeta_images:
                metagator.update_meta({
                    'title': title,
                    'description': description
                })
        except Exception as e:
            invalidImage(img, "error updating meta: " + str(e))

        # ------
        # RESIZE
        # ------

        if do_resize_images:
            if not os.path.isfile(imgRawPath) :
                invalidImage(img, "SOURCE FILE NOT FOUND: %s" % imgRawPath)
                continue

            imgDstPath = os.path.join(imgDst, img)
            if os.path.isfile(imgDstPath) :
                imgSrcMod = max(os.path.getmtime(imgRawPath), os.path.getctime(imgRawPath))
                imgDstMod = os.path.getmtime(imgDstPath)
                # print "image mod (src, dst): ", imgSrcMod, imgdstmod
                if imgDstMod > imgSrcMod:
                    if Registrar.DEBUG_IMG:
                        Registrar.registerMessage(img, "DESTINATION FILE NEWER: %s" % imgDstPath)
                    continue

            print "resizing:", img
            shutil.copy(imgRawPath, imgDstPath)

            try:
                # imgmeta = MetaGator(imgDstPath)
                # imgmeta.write_meta(title, description)
                # print imgmeta.read_meta()

                image = Image.open(imgDstPath)
                image.thumbnail(thumbsize)
                image.save(imgDstPath)

                if do_remeta_images:
                    imgmeta = MetaGator(imgDstPath)
                    imgmeta.write_meta(title, description)
                    # print imgmeta.read_meta()

            except Exception as e:
                invalidImage(img, "could not resize: " + str(e))
                continue

    # # ------
    # # RSYNC
    # # ------
    #
    # if not os.path.exists(wpaiFolder):
    #     os.makedirs(wpaiFolder)
    #
    # rsync.main([os.path.join(imgDst,'*'), wpaiFolder])

#########################################
# Export Info to Spreadsheets
#########################################

if schema in myo_schemas:
    product_cols = ColData_MYO.getProductCols()
    productList = MYOProdList(products.values())
    productList.exportItems(myoPath, ColData_Base.getColNames(product_cols))
elif schema in woo_schemas:
    product_cols = ColData_Woo.getProductCols()

    if not do_images:
        if(product_cols.get('Images')):
            del product_cols['Images']

    attributeCols = ColData_Woo.getAttributeCols(attributes, vattributes)
    productColnames = ColData_Base.getColNames( listUtils.combineOrderedDicts( product_cols, attributeCols))

    productList = WooProdList(products.values())
    productList.exportItems(flaPath, productColnames)

    #variations

    variationCols = ColData_Woo.getVariationCols()

    attributeMetaCols = ColData_Woo.getAttributeMetaCols(vattributes)
    variationColNames = ColData_Base.getColNames(
        listUtils.combineOrderedDicts( variationCols, attributeMetaCols)
    )

    if variations:
        variationList = WooVarList(variations.values())
        variationList.exportItems(
            flvPath,
            variationColNames
        )


    if categories:
        #categories
        categoryCols = ColData_Woo.getCategoryCols()

        categoryList = WooCatList(categories.values())
        categoryList.exportItems(catPath, ColData_Base.getColNames(categoryCols))

    #specials
    specialProducts = productParser.onspecial_products.values()
    if specialProducts:
        flaName, flaExt = os.path.splitext(flaPath)
        flsPath = os.path.join(outFolder , flaName+"-"+current_special+flaExt)
        specialProductList = WooProdList(specialProducts)
        specialProductList.exportItems(
            flsPath,
            productColnames
        )
    specialVariations = productParser.onspecial_variations.values()
    if specialVariations:
        flvName, flvExt = os.path.splitext(flvPath)
        flvsPath = os.path.join(outFolder , flvName+"-"+current_special+flvExt)

        spVariationList = WooVarList(specialVariations)
        spVariationList.exportItems(
            flvsPath,
            variationColNames
        )

    #Updated
    updatedProducts = productParser.updated_products.values()
    if updatedProducts:
        flaName, flaExt = os.path.splitext(flaPath)
        fluPath = os.path.join(outFolder , flaName+"-Updated"+flaExt)

        updatedProductList = WooProdList(updatedProducts)
        updatedProductList.exportItems(
            fluPath,
            productColnames
        )

    #updatedVariations
    updatedVariations = productParser.updated_variations.values()

    if updatedVariations:
        flvName, flvExt = os.path.splitext(flvPath)
        flvuPath = os.path.join(outFolder , flvName+"-Updated"+flvExt)

        updatedVariationsList = WooVarList(updatedVariations)
        updatedVariationsList.exportItems(
            flvuPath,
            variationColNames
        )


    #pricingRule
    # pricingRuleProducts = filter(
    #     hasPricingRule,
    #     products.values()[:]
    # )
    # if pricingRuleProducts:
    #     flaName, flaExt = os.path.splitext(flaPath)
    #     flpPath = os.path.join(outFolder , flaName+"-pricing_rules"+flaExt)
    #     exportItemsCSV(
    #         flpPath,
    #         ColData_Base.getColNames(
    #             listUtils.combineOrderedDicts(product_cols, attributeCols)
    #         ),
    #         pricingRuleProducts
    #     )
    #
    # pricingCols = ColData_Woo.getPricingCols()
    # print 'pricingCols: ', pricingCols.keys()
    # shippingCols = ColData_Woo.getShippingCols()
    # print 'shippingCols: ', shippingCols.keys()
    # inventoryCols = ColData_Woo.getInventoryCols()
    # print 'inventoryCols: ', inventoryCols.keys()
    # print 'categoryCols: ', categoryCols.keys()
    #
    # #export items XML
    # exportProductsXML(
    #     [xmlPath, objPath],
    #     products,
    #     product_cols,
    #     variationCols = variationCols,
    #     categoryCols = categoryCols,
    #     attributeCols = attributeCols,
    #     attributeMetaCols = attributeMetaCols,
    #     pricingCols = pricingCols,
    #     shippingCols = shippingCols,
    #     inventoryCols = inventoryCols,
    #     imageData = images
    # )

#########################################
# Attempt download API data
#########################################

if download_slave:

    apiProductParser = CSVParse_Woo_Api(
        **apiProductParserArgs
    )

    with ProdSyncClient_WC(wcApiParams) as client:
        # try:
        client.analyseRemote(apiProductParser, limit=global_limit)
        # except Exception, e:
        #     Registrar.registerError(e)
        #     report_and_quit = True

    # print apiProductParser.categories
else:
    apiProductParser = None

# print productParser.toStrTree()
print apiProductParser.toStrTree()
# quit()
# quit()

# print "API PRODUCTS"
# print ShopProdList(apiProductParser.products.values()).tabulate()

# CSVParse_Woo_Api.printBasicColumns(apiProductParser.products.values())

#########################################
# Attempt Matching
#########################################

sDeltaUpdates = []
mDeltaUpdates = []
slaveProductUpdates = []
problematicProductUpdates = []
masterCategoryUpdates = []
slaveCategoryUpdates = []
problematicCategoryUpdates = []
# productIndexFn = (lambda x: x.codesum)
def productIndexFn(x): return x.codesum
globalProductMatches = MatchList(indexFn=productIndexFn)
masterlessProductMatches = MatchList(indexFn=productIndexFn)
slavelessProductMatches = MatchList(indexFn=productIndexFn)
def categoryIndexFn(x): return x.title
# categoryIndexFn = (lambda x: x.title)
globalCategoryMatches = MatchList(indexFn=categoryIndexFn)
masterlessCategoryMatches = MatchList(indexFn=categoryIndexFn)
slavelessCategoryMatches = MatchList(indexFn=categoryIndexFn)
delete_categories = OrderedDict()
join_categories = OrderedDict()

if do_sync:

    #changes that I'm going to make to syncing:

    # [x] syncs ALL categories on WooCatName first, and updates Master categoryIDs
    # [x] creates list of categories that don't yet exist to be created
    # [x] Fix upload has quotations
    # [x] Fix toStrTree not working on apiProductParser
    # [x] AssertionError: can't add match: sIndex  already in sIndices: ['']
    # [x] Why no alerts for duplicate names
    # [x] get one-to-many matching working for category WPIDs
    # [x] Store API cats by WPID not name, since duplicates happen
    # [ ] reduce false positive product title syncs
    # [ ] Syncs categories on ID instead of WooCatName
    # [ ] Probably need to patch SyncUpdate

    # SYNC CATEGORIES
    # try:

    print "matching %d master categories with %d slave categories" % (
         len(productParser.categories),
         len(apiProductParser.categories)
    )

    categoryMatcher = CategoryMatcher()
    categoryMatcher.clear()
    categoryMatcher.processRegisters(apiProductParser.categories, productParser.categories)


    validCategoryMatches = []
    validCategoryMatches += categoryMatcher.pureMatches

    # if categoryMatcher.pureMatches:
    #     print "ALL MATCHES"
    #     print '\n'.join(map(str,categoryMatcher.matches))


    if categoryMatcher.duplicateMatches:
        # e = UserWarning(
        #     "categories couldn't be synchronized because of ambiguous names:\n%s"\
        #     % '\n'.join(map(str,categoryMatcher.duplicateMatches))
        # )
        # Registrar.registerError(e)
        # raise e
        # taxoSums = []
        invalidCategoryMatches = []
        for match in categoryMatcher.duplicateMatches:
            masterTaxoSums = [cat.namesum for cat in match.mObjects]
            if listUtils.checkEqual(masterTaxoSums) and not len(match.sObjects) > 1:
                validCategoryMatches.append(match)
            else:
                invalidCategoryMatches.append(match)
        if invalidCategoryMatches:
            e = UserWarning(
                "categories couldn't be synchronized because of ambiguous names:\n%s"\
                % '\n'.join(map(str,invalidCategoryMatches))
            )
            Registrar.registerError(e)
            raise e

    if categoryMatcher.slavelessMatches and categoryMatcher.masterlessMatches:
        e = UserWarning(
            "You may want to fix up the following categories before syncing:\n%s\n%s"\
            % (
                '\n'.join(map(str,categoryMatcher.slavelessMatches)),
                '\n'.join(map(str,categoryMatcher.masterlessMatches))
            )
        )
        Registrar.registerError(e)
        # raise e
    # quit()

    globalCategoryMatches.addMatches( categoryMatcher.pureMatches)
    masterlessCategoryMatches.addMatches( categoryMatcher.masterlessMatches)
    slavelessCategoryMatches.addMatches( categoryMatcher.slavelessMatches)

    sync_cols = ColData_Woo.getWPAPICategoryCols()

    # print "SYNC COLS: %s" % pformat(sync_cols.items())
    # quit()

    for matchCount, match in enumerate(validCategoryMatches):
        assert len(match.sObjects) == 1, "invalid number of slave objects in match"
        sObject = match.sObjects[0]
        for mObject in match.mObjects:
            # mObject = match.mObjects[0]

            syncUpdate = SyncUpdate_Cat_Woo(mObject, sObject)

            syncUpdate.update(sync_cols)

            print syncUpdate.tabulate()

            if not syncUpdate.importantStatic:
                insort(problematicCategoryUpdates, syncUpdate)
                continue

            if syncUpdate.mUpdated:
                masterCategoryUpdates.append(syncUpdate)

            if syncUpdate.sUpdated:
                slaveCategoryUpdates.append(syncUpdate)

    for update in masterCategoryUpdates:
        print "updating %s" % str(update.MasterID)
        if not update.MasterID in productParser.categories:
            print "couldn't fine pkey %s in productParser.categories" % update.MasterID
            continue
        for col, warnings in update.syncWarnings.items():
            if not col == 'ID':
                continue
            for warning in warnings:
                if not warning['subject'] == update.opposite_src(update.master_name):
                    continue

                newVal = warning['oldWinnerValue']
                productParser.categories[update.MasterID][col] = newVal

    # create categories that do not yet exist on slave

    print "PRINTING NEW CATEGORIES: %d" % (len(slavelessCategoryMatches))


    # Registrar.DEBUG_API = True

    with CatSyncClient_WC(wcApiParams) as client:
        print "created client"
        new_categories = [match.mObjects[0] for match in slavelessCategoryMatches]
        print new_categories

        while new_categories:
            category = new_categories.pop(0)
            if category.parent:
                parent = category.parent
                if not parent.isRoot and not parent.WPID and parent in new_categories:
                    new_categories.append(category)
                    continue

            mApiData = category.toApiData(ColData_Woo, 'wp-api')
            for key in ['id', 'slug', 'sku']:
                if key in mApiData:
                    del mApiData[key]
            mApiData['name'] = category.wooCatName
            print "uploading category: %s" % mApiData
            # pprint(mApiData)
            if update_slave:
                response = client.createItem(mApiData)
                # print response
                # print response.json()
                responseApiData = response.json()
                responseApiData = responseApiData.get('product_category', responseApiData)
                apiProductParser.processApiCategory(responseApiData)
                api_cat_translation = OrderedDict()
                for key, data in ColData_Woo.getWPAPICategoryCols().items():
                    try:
                        wp_api_key = data['wp-api']['key']
                    except:
                        wp_api_key = key
                    api_cat_translation[wp_api_key] = key
                print "TRANSLATION: ", api_cat_translation
                categoryParserData = apiProductParser.translateKeys(responseApiData, api_cat_translation)
                print "CATEGORY PARSER DATA: ", categoryParserData

                category.update(categoryParserData)

                print "CATEGORY: ", category
                # quit()

    print "product parser"
    print productParser.toStrTree()
    for key, category in productParser.categories.items():
        print "%5s | %50s | %s" % (key, category.title[:50], category.WPID)
    print "api product parser"
    print "there are %s categories registered" % len(apiProductParser.categories)
    print "there are %s children of root" % len(apiProductParser.rootData.children)
    print apiProductParser.toStrTree()
    for key, category in apiProductParser.categories.items():
        print "%5s | %50s" % (key, category.title[:50])

    # quit()

    categoryMatcher = CategoryMatcher()
    categoryMatcher.clear()
    categoryMatcher.processRegisters(apiProductParser.categories, productParser.categories)


    print "PRINTING NEW SYNCING PROUCTS"

    # SYNC PRODUCTS

    productMatcher = ProductMatcher()
    productMatcher.processRegisters(apiProductParser.products, productParser.products)
    # print productMatcher.__repr__()

    globalProductMatches.addMatches( productMatcher.pureMatches)
    masterlessProductMatches.addMatches( productMatcher.masterlessMatches)
    slavelessProductMatches.addMatches( productMatcher.slavelessMatches)

    sync_cols = ColData_Woo.getWPAPICols()
    sync_cols_var = ColData_Woo.getWPAPIVariableCols()
    if Registrar.DEBUG_UPDATE:
        Registrar.registerMessage("sync_cols: %s" % repr(sync_cols))

    if productMatcher.duplicateMatches:
        e = UserWarning(
            "products couldn't be synchronized because of ambiguous SKUs:%s"\
            % '\n'.join(map(str,productMatcher.duplicateMatches))
        )
        Registrar.registerError(e)
        raise e

    for matchCount, match in enumerate(productMatcher.pureMatches):
        mObject = match.mObjects[0]
        sObject = match.sObjects[0]

        # gcs = match.gcs
        # if gcs and gcs.isVariable:

        syncUpdate = SyncUpdate_Prod_Woo(mObject, sObject)
        if mObject.isVariation or sObject.isVariation:
            # if gcs and hasattr(gcs,'isVariation') and gcs.isVariation:
            # print "IS VARIATION"
            syncUpdate.update(sync_cols_var)
        else:
            # print "IS NOT VARIATION"
            syncUpdate.update(sync_cols)
            assert not mObject.isVariation #, "gcs %s is not variation but object is" % repr(gcs)
            assert not sObject.isVariation #, "gcs %s is not variation but object is" % repr(gcs)

            # print syncUpdate.tabulate()

            # if gcs and hasattr(gcs,'isProduct') and gcs.isProduct:
            #category matching

            categoryMatcher.clear()
            categoryMatcher.processRegisters(sObject.categories, mObject.categories)

            updateParams = {
                'col':'catlist',
                'data':{
                    # 'sync'
                },
                'subject': syncUpdate.master_name
            }



            changeMatchList = categoryMatcher.masterlessMatches
            changeMatchList.addMatches(categoryMatcher.slavelessMatches)

            master_categories = set(
                [category.WPID for category in mObject.categories.values() if category.WPID]
            )
            slave_categories =  set(
                [category.WPID for category in sObject.categories.values() if category.WPID]
            )

            print "comparing categories of %s:\n%s\n%s\n%s\n%s"\
                % (
                    mObject.codesum,
                    str(mObject.categories.values()),
                    str(sObject.categories.values()),
                    str(master_categories),
                    str(slave_categories),
                )
            syncUpdate.oldMObject['catlist'] = list(master_categories)
            syncUpdate.oldSObject['catlist'] = list(slave_categories)

            if changeMatchList:
                assert master_categories != slave_categories, "should not be equal"
                updateParams['reason'] = 'updating'
                # updateParams['subject'] = SyncUpdate.master_name

                # master_categories = [category.wooCatName for category in changeMatchList.merge().mObjects]
                # slave_categories =  [category.wooCatName for category in changeMatchList.merge().sObjects]

                syncUpdate.loserUpdate(**updateParams)
                # syncUpdate.newMObject['catlist'] = master_categories
                # syncUpdate.newSObject['catlist'] = master_categories

                # updateParams['oldLoserValue'] = slave_categories
                # updateParams['oldWinnerValue'] = master_categories
            else:
                assert\
                    master_categories == slave_categories, \
                    "should equal, %s | %s" % (
                        repr(master_categories),
                        repr(slave_categories)
                    )
                updateParams['reason'] = 'identical'
                syncUpdate.tieUpdate(**updateParams)


            # print categoryMatcher.__repr__()
            for cat_match in categoryMatcher.masterlessMatches:
                sIndex = sObject.index
                if delete_categories.get(sIndex) is None:
                    delete_categories[sIndex] = MatchList()
                delete_categories[sIndex].append(cat_match)
            for cat_match in categoryMatcher.slavelessMatches:
                sIndex = sObject.index
                if join_categories.get(sIndex) is None:
                    join_categories[sIndex] = MatchList()
                join_categories[sIndex].append(cat_match)

        if not syncUpdate.eUpdated:
            continue

        print syncUpdate.tabulate()

        if syncUpdate.sUpdated and syncUpdate.sDeltas:
            insort(sDeltaUpdates, syncUpdate)

        if not syncUpdate.importantStatic:
            insort(problematicProductUpdates, syncUpdate)
            continue

        if syncUpdate.sUpdated:
            insort(slaveProductUpdates, syncUpdate)


    print debugUtils.hashify("COMPLETED MERGE")

    # except Exception, e:
    #     Registrar.registerError(repr(e))
    #     report_and_quit = True


#########################################
# Write Report
#########################################

print debugUtils.hashify("Write Report")

with io.open(repPath, 'w+', encoding='utf8') as resFile:
    reporter = HtmlReporter()

    basic_cols = ColData_Woo.getBasicCols()
    csv_colnames = ColData_Woo.getColNames(
        OrderedDict(basic_cols.items() + ColData_Woo.nameCols([
            # 'address_reason',
            # 'name_reason',
            # 'Edited Name',
            # 'Edited Address',
            # 'Edited Alt Address',
        ]).items()))

    # print repr(basic_colnames)
    unicode_colnames = map(SanitationUtils.coerceUnicode, csv_colnames.values())
    # print repr(unicode_colnames)

    if do_sync and (sDeltaUpdates):

        deltaGroup = HtmlReporter.Group('deltas', 'Field Changes')

        sDeltaList = ShopObjList(filter(None,
                            [syncUpdate.newSObject for syncUpdate in sDeltaUpdates]))

        deltaCols = ColData_Woo.getDeltaCols()

        allDeltaCols = OrderedDict(
            ColData_Woo.getBasicCols().items() +
            ColData_Woo.nameCols(deltaCols.keys()+deltaCols.values()).items()
        )

        if sDeltaList:
            deltaGroup.addSection(
                HtmlReporter.Section(
                    's_deltas',
                    title = '%s Changes List' % SLAVE_NAME.title(),
                    description = '%s records that have changed important fields' % SLAVE_NAME,
                    data = sDeltaList.tabulate(
                        cols=allDeltaCols,
                        tablefmt='html'),
                    length = len(sDeltaList)
                )
            )

        reporter.addGroup(deltaGroup)

        if sDeltaList:
            sDeltaList.exportItems(slaveDeltaCsvPath, ColData_Woo.getColNames(allDeltaCols))

    #
    report_matching = do_sync
    if report_matching:

        matchingGroup = HtmlReporter.Group('product_matching', 'Product Matching Results')
        matchingGroup.addSection(
            HtmlReporter.Section(
                'perfect_product_matches',
                **{
                    'title': 'Perfect Matches',
                    'description': "%s records match well with %s" % (SLAVE_NAME, MASTER_NAME),
                    'data': globalProductMatches.tabulate(tablefmt="html"),
                    'length': len(globalProductMatches)
                }
            )
        )
        matchingGroup.addSection(
            HtmlReporter.Section(
                'masterless_product_matches',
                **{
                    'title': 'Masterless matches',
                    'description': "matches are masterless",
                    'data': masterlessProductMatches.tabulate(tablefmt="html"),
                    'length': len(masterlessProductMatches)
                }
            )
        )
        matchingGroup.addSection(
            HtmlReporter.Section(
                'slaveless_product_matches',
                **{
                    'title': 'Slaveless matches',
                    'description': "matches are slaveless",
                    'data': slavelessProductMatches.tabulate(tablefmt="html"),
                    'length': len(slavelessProductMatches)
                }
            )
        )

        reporter.addGroup(matchingGroup)

        matchingGroup = HtmlReporter.Group('category_matching', 'Category Matching Results')
        matchingGroup.addSection(
            HtmlReporter.Section(
                'perfect_category_matches',
                **{
                    'title': 'Perfect Matches',
                    'description': "%s records match well with %s" % (SLAVE_NAME, MASTER_NAME),
                    'data': globalCategoryMatches.tabulate(tablefmt="html"),
                    'length': len(globalCategoryMatches)
                }
            )
        )
        matchingGroup.addSection(
            HtmlReporter.Section(
                'masterless_category_matches',
                **{
                    'title': 'Masterless matches',
                    'description': "matches are masterless",
                    'data': masterlessCategoryMatches.tabulate(tablefmt="html"),
                    'length': len(masterlessCategoryMatches)
                }
            )
        )
        matchingGroup.addSection(
            HtmlReporter.Section(
                'slaveless_category_matches',
                **{
                    'title': 'Slaveless matches',
                    'description': "matches are slaveless",
                    'data': slavelessCategoryMatches.tabulate(tablefmt="html"),
                    'length': len(slavelessCategoryMatches)
                }
            )
        )

        reporter.addGroup(matchingGroup)


    report_sync = do_sync
    if report_sync:
        syncingGroup = HtmlReporter.Group('sync', 'Syncing Results')

        syncingGroup.addSection(
            HtmlReporter.Section(
                (SanitationUtils.makeSafeClass(SLAVE_NAME) + "_updates"),
                description = SLAVE_NAME + " items will be updated",
                data = '<hr>'.join([update.tabulate(tablefmt="html") for update in slaveProductUpdates ]),
                length = len(slaveProductUpdates)
            )
        )

        syncingGroup.addSection(
            HtmlReporter.Section(
                "problematic_updates",
                description = "items can't be merged because they are too dissimilar",
                data = '<hr>'.join([update.tabulate(tablefmt="html") for update in problematicProductUpdates ]),
                length = len(problematicProductUpdates)
            )
        )

        reporter.addGroup(syncingGroup)

    report_cats = do_sync
    if report_cats:
        syncingGroup = HtmlReporter.Group('cats', 'Category Syncing Results')

        syncingGroup.addSection(
            HtmlReporter.Section(
                ('delete_categories'),
                description = "%s items will leave categories" % SLAVE_NAME,
                data = tabulate(
                    [
                        [
                            index,
                            # apiProductParser.products[index],
                            # apiProductParser.products[index].categories,
                            # ", ".join(category.wooCatName for category in matches.merge().mObjects),
                            ", ".join(category.wooCatName for category in matches.merge().sObjects)
                        ] for index, matches in delete_categories.items()
                    ],
                    tablefmt="html"
                ),
                length = len(delete_categories)
                # data = '<hr>'.join([
                #         "%s<br/>%s" % (index, match.tabulate(tablefmt="html")) \
                #         for index, match in delete_categories.items()
                #     ]
                # )
            )
        )

        syncingGroup.addSection(
            HtmlReporter.Section(
                ('delete_categories_not_specials'),
                description = "%s items will leave categories" % SLAVE_NAME,
                data = tabulate(
                    [
                        [
                            index,
                            # apiProductParser.products[index],
                            # apiProductParser.products[index].categories,
                            # ", ".join(category.wooCatName for category in matches.merge().mObjects),
                            ", ".join(category.wooCatName for category in matches.merge().sObjects\
                            if not re.search('Specials', category.wooCatName))
                        ] for index, matches in delete_categories.items()
                    ],
                    tablefmt="html"
                ),
                length = len(delete_categories)
                # data = '<hr>'.join([
                #         "%s<br/>%s" % (index, match.tabulate(tablefmt="html")) \
                #         for index, match in delete_categories.items()
                #     ]
                # )
            )
        )

        syncingGroup.addSection(
            HtmlReporter.Section(
                ('join_categories'),
                description = "%s items will join categories" % SLAVE_NAME,
                data = tabulate(
                    [
                        [
                            index,
                            # apiProductParser.products[index],
                            # apiProductParser.products[index].categories,
                            ", ".join(category.wooCatName for category in matches.merge().mObjects),
                            # ", ".join(category.wooCatName for category in matches.merge().sObjects)
                        ] for index, matches in join_categories.items()
                    ],
                    tablefmt="html"
                ),
                length = len(join_categories)
                # data = '<hr>'.join([
                #         "%s<br/>%s" % (index, match.tabulate(tablefmt="html")) \
                #         for index, match in delete_categories.items()
                #     ]
                # )
            )
        )

        reporter.addGroup(syncingGroup)

    resFile.write( reporter.getDocumentUnicode() )


if report_and_quit:
    quit()


#########################################
# Perform updates
#########################################

allProductUpdates = slaveProductUpdates
allProductUpdates += problematicProductUpdates

slaveFailures = []
if allProductUpdates:
    print debugUtils.hashify("UPDATING %d RECORDS" % len(allProductUpdates))

    if Registrar.DEBUG_PROGRESS:
        updateProgressCounter = ProgressCounter(len(allProductUpdates))

    with ProdSyncClient_WC(wcApiParams) as slaveClient:
        for count, update in enumerate(allProductUpdates):
            if Registrar.DEBUG_PROGRESS:
                updateProgressCounter.maybePrintUpdate(count)

            if update_slave and update.sUpdated :
                # print "attempting update to %s " % str(update)

                try:
                    update.updateSlave(slaveClient)
                except Exception, e:
                    # slaveFailures.append({
                    #     'update':update,
                    #     'master':SanitationUtils.coerceUnicode(update.newMObject),
                    #     'slave':SanitationUtils.coerceUnicode(update.newSObject),
                    #     'mchanges':SanitationUtils.coerceUnicode(update.getMasterUpdates()),
                    #     'schanges':SanitationUtils.coerceUnicode(update.getSlaveUpdates()),
                    #     'exception':repr(e)
                    # })
                    SanitationUtils.safePrint("ERROR UPDATING SLAVE (%s): %s" % (update.SlaveID, repr(e) ) )
            # else:
            #     print "no update made to %s " % str(update)

    print debugUtils.hashify("COMPLETED UPDATES")

#########################################
# Display reports
#########################################

shutil.copyfile(repPath, repWebPath)
if show_report:
    if webBrowser:
        os.environ['BROWSER'] = webBrowser
        print "set browser environ to %s" % repr(webBrowser)
    # print "moved file from %s to %s" % (repPath, repWebPath)

    webbrowser.open(repWebLink)
else:
    print "open this link to view report %s" % repWebLink


# for sku, product in apiProductParser.products.items():
#     print sku
#
#     if sku in productParser.products:
#         print 'sku match found'
#     else:
#         print 'sku_match not found'
