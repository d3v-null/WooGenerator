# import re
from collections import OrderedDict
import os
import shutil
from PIL import Image
import time
import datetime
# from itertools import chain
from metagator import MetaGator
from utils import listUtils, SanitationUtils, TimeUtils
from csvparse_abstract import Registrar
from csvparse_woo import CSVParse_TT, CSVParse_VT, CSVParse_Woo, WooObjList
from csvparse_woo import WooCatList, WooProdList, WooVarList
from csvparse_myo import CSVParse_MYO, MYOProdList
from csvparse_dyn import CSVParse_Dyn
from csvparse_flat import CSVParse_Special, CSVParse_WPSQLProd
from coldata import ColData_Woo, ColData_MYO , ColData_Base
from sync_client import SyncClient_GDrive
# import xml.etree.ElementTree as ET
# import rsync
import sys
import yaml
# import re
# import MySQLdb
# from sshtunnel import SSHTunnelForwarder

### DEFAULT CONFIG ###

inFolder = "../input/"
outFolder = "../output/"
logFolder = "../logs/"
srcFolder = "../source"

os.chdir('source')

yamlPath = "generator_config.yaml"

# thumbsize = 1920, 1200

importName = TimeUtils.getMsTimeStamp()

### Process YAML file ###

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
    # webFolder = config.get('webFolder')
    # imgFolder_glb = config.get('imgFolder_glb')
    myo_schemas = config.get('myo_schemas')
    woo_schemas = config.get('woo_schemas')
    taxoDepth = config.get('taxoDepth')
    itemDepth = config.get('itemDepth')

    #optional
    fallback_schema = config.get('fallback_schema')
    fallback_variant = config.get('fallback_variant')
    # imgFolder_extra = config.get('imgFolder_extra')

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
    skip_images = config.get('skip_images')
    # assert isinstance(download, bool), "%s %s" % tuple(map(str, [download, download.__class__] ))
    # assert isinstance(skip_images, bool), "%s %s" % tuple(map(str, [skip_images, skip_images.__class__] ))

    current_special = config.get('current_special')
    add_special_categories = config.get('add_special_categories')

#mandatory params
assert all([inFolder, outFolder, logFolder, woo_schemas, myo_schemas, taxoDepth, itemDepth])

genPath = os.path.join(inFolder, 'generator.csv')
dprcPath= os.path.join(inFolder, 'DPRC.csv')
dprpPath= os.path.join(inFolder, 'DPRP.csv')
specPath= os.path.join(inFolder, 'specials.csv')
usPath  = os.path.join(inFolder, 'US.csv')
xsPath  = os.path.join(inFolder, 'XS.csv')
# imgFolder = [imgFolder_glb]

sqlPath = os.path.join(srcFolder, 'select_productdata.sql')

### GET SHELL ARGS ###

schema = ""
variant = ""
# skip_google_download = True

if __name__ == "__main__":
    if sys.argv and len(sys.argv) > 1 and sys.argv[1]:
        if sys.argv[1] in myo_schemas + woo_schemas :
            schema = sys.argv[1]
            if len(sys.argv) > 2 and sys.argv[2]:
                variant = sys.argv[2]
        else:
            print "invalid schema"
    else:
        print "no schema specified"

    #todo: set current_special, imgFolder_glb, delete, remeta, resize, download from args

### FALLBACK SHELL ARGS ###

if not schema:
    assert fallback_schema
    schema = fallback_schema
if not variant and fallback_variant:
    variant = fallback_variant

### CONFIG OVERRIDE ###

# skip_images = True
# delete = True
# remeta = True
# resize = False
# rename = False

if variant == "ACC":
    genPath = os.path.join(inFolder, 'generator-solution.csv')

if variant == "SOL":
    genPath = os.path.join(inFolder, 'generator-accessories.csv')

### PROCESS CONFIG ###

# if variant:
#     delete = False
#     remeta = False
#     resize = False

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

maxDepth = taxoDepth + itemDepth

# if imgFolder_extra and schema in imgFolder_extra.keys():
#     imgFolder += [imgFolder_extra[schema]]

if current_special:
    CSVParse_Woo.specialsCategory = "Specials"
    CSVParse_Woo.current_special = current_special
    CSVParse_Woo.add_special_categories = add_special_categories

if skip_google_download:
    SyncClient_GDrive.skip_download = True

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
# Download data from GDrive
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

with SyncClient_GDrive(gDriveParams) as client:
    if schema in myo_schemas:
        productParser = CSVParse_MYO(
            cols = ColData_MYO.getImportCols(),
            defaults = ColData_MYO.getDefaults(),
            importName = importName,
            itemDepth = itemDepth,
            taxoDepth = taxoDepth,
        )

    elif schema in woo_schemas:
        productParserArgs = {
            'cols': ColData_Woo.getImportCols(),
            'defaults': ColData_Woo.getDefaults(),
            'importName': importName,
            'itemDepth': itemDepth,
            'taxoDepth': taxoDepth,
        }

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

        Registrar.registerMessage("analysing specials")
        specialParser = CSVParse_Special()
        client.analyseRemote(specialParser, specGID, specPath)
        specials = specialParser.objects
        productParserArgs['specials'] = specials


        if schema == "TT":
            productParser = CSVParse_TT(
                **productParserArgs
            )
        elif schema == "VT":
            productParser = CSVParse_VT(
                **productParserArgs
            )
        else:
            productParserArgs['schema'] = schema

            productParser = CSVParse_Woo(
                **productParserArgs
            )

    Registrar.registerMessage("analysing products")
    client.analyseRemote(productParser, None, genPath)

products = productParser.getProducts()

if schema in woo_schemas:
    attributes     = productParser.attributes
    vattributes    = productParser.vattributes
    categories     = productParser.categories
    variations     = productParser.variations
    # images         = productParser.images

if Registrar.errors:
    print "there were some errors that need to be reviewed before sync can happen"
    Registrar.print_message_dict(0)
    quit()
elif Registrar.warnings:
    print "there were some warnings that should be reviewed"
    Registrar.print_message_dict(1)


# #########################################
# # Images
# #########################################
#
# if schema in woo_schemas and not skip_images:
#     print ""
#     print "Images:"
#     print "==========="
#
#     def reportImportError(source, error):
#         Registrar.registerError(error, source)
#         # import_errors[source] = import_errors.get(source,[]) + [str(error)]
#
#     def invalidImage(img, error):
#         reportImportError(img, error)
#         images[img].invalidate()
#
#     if skip_images:
#         images = {}
#         delete = False
#
#     ls_imgs = {}
#     for folder in imgFolder:
#         ls_imgs[folder] = os.listdir(folder)
#
#     def getImage(img):
#         for folder in imgFolder:
#             if img in ls_imgs[folder]:
#                 return os.path.join(folder, img)
#         raise UserWarning("no img found")
#
#     if not os.path.exists(refFolder):
#         os.makedirs(refFolder)
#
#     ls_reflattened = os.listdir(refFolder)
#     for f in ls_reflattened:
#         if f not in images.keys():
#             print "DELETING", f, "FROM REFLATTENED"
#             if delete:
#                 os.remove(os.path.join(refFolder,f))
#
#
#     for img, data in images.items():
#         print img
#         if data.taxos:
#             print "-> Associated Taxos"
#             for taxo in data.taxos:
#                 print " -> (%4d) %10s" % (taxo.rowcount, taxo.codesum)
#
#         if data.items:
#             print "-> Associated Items"
#             for item in data.items:
#                 print " -> (%4d) %10s" % (item.rowcount, item.codesum)
#
#         if data.products:
#             print "-> Associated Products"
#             for item in data.products:
#                 print " -> (%4d) %10s" % (item.rowcount, item.codesum)
#         else:
#             continue
#             # we only care about product images atm
#
#         try:
#             imgsrcpath = getImage(img)
#         except Exception as e:
#             invalidImage(img, e)
#
#         name, ext = os.path.splitext(img)
#         if(not name):
#             invalidImage(img, "could not extract name")
#             continue
#
#         try:
#             title, description = data.title, data.description
#         except Exception as e:
#             invalidImage(img, "could not get title or description: "+str(e) )
#             continue
#
#         # print "-> title, description", title, description
#
#         # ------
#         # REMETA
#         # ------
#
#         try:
#             metagator = MetaGator(imgsrcpath)
#         except Exception, e:
#             invalidImage(img, "error creating metagator: " + str(e))
#             continue
#
#         try:
#             metagator.update_meta({
#                 'title': title,
#                 'description': description
#             })
#         except Exception as e:
#             invalidImage(img, "error updating meta: " + str(e))
#
#         # ------
#         # RESIZE
#         # ------
#
#         if resize:
#             imgdstpath = os.path.join(refFolder, img)
#             if not os.path.isfile(imgsrcpath) :
#                 print "SOURCE FILE NOT FOUND: ", imgsrcpath
#                 continue
#
#             if os.path.isfile(imgdstpath) :
#                 imgsrcmod = max(os.path.getmtime(imgsrcpath), os.path.getctime(imgsrcpath))
#                 imgdstmod = os.path.getmtime(imgdstpath)
#                 # print "image mod (src, dst): ", imgsrcmod, imgdstmod
#                 if imgdstmod > imgsrcmod:
#                     # print "DESTINATION FILE NEWER: ", imgdstpath
#                     continue
#
#             print "resizing:", img
#             shutil.copy(imgsrcpath, imgdstpath)
#
#             try:
#                 # imgmeta = MetaGator(imgdstpath)
#                 # imgmeta.write_meta(title, description)
#                 # print imgmeta.read_meta()
#
#                 image = Image.open(imgdstpath)
#                 image.thumbnail(thumbsize)
#                 image.save(imgdstpath)
#
#                 imgmeta = MetaGator(imgdstpath)
#                 imgmeta.write_meta(title, description)
#                 # print imgmeta.read_meta()
#
#             except Exception as e:
#                 invalidImage(img, "could not resize: " + str(e))
#                 continue
#
#     # ------
#     # RSYNC
#     # ------
#
#     if not os.path.exists(wpaiFolder):
#         os.makedirs(wpaiFolder)
#
#     rsync.main([os.path.join(refFolder,'*'), wpaiFolder])

#########################################
# Export Info to Spreadsheets
#########################################

if schema in myo_schemas:
    product_cols = ColData_MYO.getProductCols()
    productList = MYOProdList(products.values())
    productList.exportItems(myoPath, ColData_Base.getColNames(product_cols))
elif schema in woo_schemas:
    product_cols = ColData_Woo.getProductCols()

    if skip_images:
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
# Attempt import
#########################################
