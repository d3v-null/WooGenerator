# import re
from collections import OrderedDict
import os
import shutil
from PIL import Image
import time
import datetime
import argparse
# from itertools import chain
from metagator import MetaGator
from utils import listUtils, SanitationUtils, TimeUtils
from csvparse_abstract import Registrar
from csvparse_woo import CSVParse_TT, CSVParse_VT, CSVParse_Woo, WooObjList
from csvparse_woo import WooCatList, WooProdList, WooVarList
from csvparse_api import CSVParse_Woo_Api
from csvparse_myo import CSVParse_MYO, MYOProdList
from csvparse_dyn import CSVParse_Dyn
from csvparse_flat import CSVParse_Special, CSVParse_WPSQLProd
from coldata import ColData_Woo, ColData_MYO , ColData_Base
from sync_client import SyncClient_GDrive
from sync_client_prod import ProdSyncClient_WC
from matching import ProductMatcher
from SyncUpdate import SyncUpdate_Prod
# import xml.etree.ElementTree as ET
# import rsync
import sys
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
    # webFolder = config.get('webFolder')
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
    do_images = config.get('do_images')
    do_specials = config.get('do_specials')
    do_dyns = config.get('do_dyns')
    do_sync = config.get('do_sync')
    do_delete_images = config.get('do_delete_images')
    do_resize_images = config.get('do_resize_images')

    current_special = config.get('current_special')
    add_special_categories = config.get('add_special_categories')
    download_master = config.get('download_master')
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
                   action="store_false", dest='update_slave')
group = parser.add_mutually_exclusive_group()
group.add_argument('--do-sync', help='sync the databases',
                  action="store_true", default=None)
group.add_argument('--skip-sync', help='don\'t sync the databases',
                  action="store_false", dest='do_sync')
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
        do_sync = args.do_sync
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
SyncUpdate_Prod.setGlobals( MASTER_NAME, SLAVE_NAME, merge_mode, DEFAULT_LAST_SYNC)

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
    productParser.analyseFile(genPath)

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


#########################################
# Images
#########################################

if do_images and schema in woo_schemas:
    print ""
    print "Images:"
    print "==========="

    def invalidImage(img, error):
        # Registrar.registerError(error, img)
        images[img].invalidate(error)

    ls_raw = {}
    for folder in imgRawFolders:
        ls_raw[folder] = os.listdir(folder)

    def getRawImage(img):
        for imgRawFolder in imgRawFolders:
            if img in ls_raw[imgRawFolder]:
                return os.path.join(imgRawFolder, img)
        raise UserWarning("no img found")

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
            invalidImage(img, e)
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

        Registrar.registerMessage("title: %s | description: %s" % (title, description), img)

        # ------
        # REMETA
        # ------

        try:
            metagator = MetaGator(imgRawPath)
        except Exception, e:
            invalidImage(img, "error creating metagator: " + str(e))
            continue

        try:
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
                invalidImage("SOURCE FILE NOT FOUND: %s" % imgRawPath, img)
                continue

            imgDstPath = os.path.join(imgDst, img)
            if os.path.isfile(imgDstPath) :
                imgSrcMod = max(os.path.getmtime(imgRawPath), os.path.getctime(imgRawPath))
                imgDstMod = os.path.getmtime(imgDstPath)
                # print "image mod (src, dst): ", imgSrcMod, imgdstmod
                if imgDstMod > imgSrcMod:
                    if Registrar.DEBUG_IMG:
                        Registrar.registerMessage("DESTINATION FILE NEWER: %s" % imgDstPath, img)
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

                imgmeta = MetaGator(imgDstPath)
                imgmeta.write_meta(title, description)
                # print imgmeta.read_meta()

            except Exception as e:
                invalidImage(img, "could not resize: " + str(e))
                continue
#
#     # ------
#     # RSYNC
#     # ------
#
#     if not os.path.exists(wpaiFolder):
#         os.makedirs(wpaiFolder)
#
#     rsync.main([os.path.join(imgDst,'*'), wpaiFolder])

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
# Report
#########################################

    # with open(spoPath, 'w+') as spoFile:
    #     def writeSection(title, description, data, length = 0, html_class="results_section"):
    #         sectionID = SanitationUtils.makeSafeClass(title)
    #         description = "%s %s" % (str(length) if length else "No", description)
    #         spoFile.write('<div class="%s">'% html_class )
    #         spoFile.write('<a data-toggle="collapse" href="#%s" aria-expanded="true" data-target="#%s" aria-controls="%s">' % (sectionID, sectionID, sectionID))
    #         spoFile.write('<h2>%s (%d)</h2>' % (title, length))
    #         spoFile.write('</a>')
    #         spoFile.write('<div class="collapse" id="%s">' % sectionID)
    #         spoFile.write('<p class="description">%s</p>' % description)
    #         spoFile.write('<p class="data">' )
    #         spoFile.write( re.sub("<table>","<table class=\"table table-striped\">",data) )
    #         spoFile.write('</p>')
    #         spoFile.write('</div>')
    #         spoFile.write('</div>')
    #
    #     spoFile.write('<!DOCTYPE html>')
    #     spoFile.write('<html lang="en">')
    #     spoFile.write('<head>')
    #     spoFile.write("""
    # <!-- Latest compiled and minified CSS -->
    # <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.6/css/bootstrap.min.css" integrity="sha384-1q8mTJOASx8j1Au+a5WDVnPi2lkFfwwEAa8hDDdjZlpLegxhjVME1fgjWPGmkzs7" crossorigin="anonymous">
    #
    # <!-- Optional theme -->
    # <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.6/css/bootstrap-theme.min.css" integrity="sha384-fLW2N01lMqjakBkx3l/M9EahuwpSfeNvV63J5ezn3uZzapT0u7EYsXMjQV+0En5r" crossorigin="anonymous">
    # """)
    #     spoFile.write('<body>')
    #     spoFile.write('<div class="matching">')
    #     spoFile.write('<h1>%s</h1>' % 'Dynamic Pricing Ruels Report')
    #
    #     dynProducts = [ \
    #         product \
    #         for product in products.values() \
    #         if product.get('dprpIDlist') or product.get('dprcIDlist') \
    #     ]
    #
    #     dynProductList = WooObjList("fileName", dynProducts )
    #
    #     writeSection(
    #         "Dynamic Pricing Rules",
    #         "all products and their dynaimc pricing rules",
    #         re.sub("<table>","<table class=\"table table-striped\">",
    #             dynProductList.tabulate(cols=OrderedDict([
    #                 ('itemsum', {}),
    #                 ('dprcIDlist', {}),
    #                 ('dprcsum', {}),
    #                 ('dprpIDlist', {}),
    #                 ('dprpsum', {}),
    #                 ('pricing_rules', {})
    #             ]), tablefmt="html")
    #         ),
    #         length = len(dynProductList.objects)
    #     )
    #
    #     spoFile.write('</div>')
    #     spoFile.write("""
    # <script src="https://ajax.googleapis.com/ajax/libs/jquery/2.1.4/jquery.min.js"></script>
    # <script src="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.6/js/bootstrap.min.js" integrity="sha384-0mSbJDEHialfmuBBQP6A4Qrprq5OVfW37PRR3j5ELqxss1yVqOtnepnHVP9aJ7xS" crossorigin="anonymous"></script>
    # """)
    #     spoFile.write('</body>')
    #     spoFile.write('</html>')
    #
    # for source, error in import_errors.items():
    #     Registrar.printAnything(source, error, '!')

#########################################
# Attempt download API data
#########################################

apiProductParser = CSVParse_Woo_Api(
    **apiProductParserArgs
)

with ProdSyncClient_WC(wcApiParams) as client:
    client.analyseRemote(apiProductParser, limit=global_limit)

#########################################
# Attempt sync
#########################################

if do_sync:
    productMatcher = ProductMatcher()
    productMatcher.processRegisters(productParser.products, apiProductParser.products)
    print productMatcher.__repr__()

    for matchCount, match in enumerate(productMatcher.pureMatches):
        mObject = match.mObjects[0]
        sObject = match.sObjects[0]
        syncUpdate = SyncUpdate_Prod(mObject, sObject)



# for sku, product in apiProductParser.products.items():
#     print sku
#
#     if sku in productParser.products:
#         print 'sku match found'
#     else:
#         print 'sku_match not found'
