import csv
# import re
from collections import OrderedDict
import os
import shutil
from PIL import Image
import time
# from itertools import chain
from metagator import MetaGator
from utils import listUtils, sanitationUtils
from csvparse_abstract import Registrar
from csvparse_woo import CSVParse_TT, CSVParse_VT, CSVParse_Woo
from csvparse_myo import CSVParse_MYO
from csvparse_dyn import CSVParse_Dyn
from csvparse_flat import CSVParse_Special
from coldata import ColData_Woo, ColData_MYO #, ColData_User
import xml.etree.ElementTree as ET
import rsync
import sys
import yaml

import httplib2

from apiclient import discovery
import oauth2client
from oauth2client import client
from oauth2client import tools

### PIP DEPENDENCIES ###
# - pyyaml

### DEFAULT CONFIG ###

inFolder = "../input/"
outFolder = "../output/"
logFolder = "../logs/"

yamlPath = "config.yaml"

thumbsize = 1920, 1200

rename = False
resize = False
remeta = False
delete = False
skip_images = False

importName = time.strftime("%Y-%m-%d %H:%M:%S")

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
	webFolder = config.get('webFolder')
	imgFolder_glb = config.get('imgFolder_glb')
	myo_schemas = config.get('myo_schemas')
	woo_schemas = config.get('woo_schemas')
	taxoDepth = config.get('taxoDepth')
	itemDepth = config.get('itemDepth')

	#optional
	fallback_schema = config.get('fallback_schema')
	fallback_variant = config.get('fallback_variant')
	imgFolder_extra = config.get('imgFolder_extra')

#mandatory params
assert all([inFolder, outFolder, logFolder, webFolder, imgFolder_glb, woo_schemas, myo_schemas, taxoDepth, itemDepth])

genPath = os.path.join(inFolder, 'generator.csv')
dprcPath= os.path.join(inFolder, 'DPRC.csv')
dprpPath= os.path.join(inFolder, 'DPRP.csv')
specPath= os.path.join(inFolder, 'specials.csv')
usPath  = os.path.join(inFolder, 'US.csv')
xsPath  = os.path.join(inFolder, 'XS.csv')
imgFolder = [imgFolder_glb]

### GET SHELL ARGS ###

schema = ""
variant = ""

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

	#todo: set currentSpecial, imgFolder_glb, delete, remeta, resize, download from args

### FALLBACK SHELL ARGS ###

if not schema:
	assert fallback_schema
	schema = fallback_schema
if not variant and fallback_variant:
	variant = fallback_variant

### CONFIG OVERRIDE ###

# skip_images = True
delete = True
remeta = True
resize = True
download = True

if variant == "ACC": 
	genPath = os.path.join(inFolder, 'generator-solution.csv')

if variant == "SOL":
	genPath = os.path.join(inFolder, 'generator-accessories.csv')

DEBUG = True

# currentSpecial = None
currentSpecial = "CHRS2015-"

### PROCESS CONFIG ###

if variant:
	delete = False
	remeta = False
	resize = False

suffix = schema 
if variant:
	suffix += "-" + variant

flaPath = os.path.join(outFolder , "flattened-"+suffix+".csv")
flvPath = os.path.join(outFolder , "flattened-variations-"+suffix+".csv")
catPath = os.path.join(outFolder , "categories-"+suffix+".csv")
myoPath = os.path.join(outFolder , "myob-"+suffix+".csv")
bunPath = os.path.join(outFolder , "bundles-"+suffix+".csv")
xmlPath = os.path.join(outFolder , "items-"+suffix+".xml")
objPath = os.path.join(webFolder, "objects-"+suffix+".xml")
wpaiFolder = os.path.join(webFolder, "images-"+schema)
refFolder = wpaiFolder

maxDepth = taxoDepth + itemDepth

if imgFolder_extra and schema in imgFolder_extra.keys():
	imgFolder += [imgFolder_extra[schema]]


########################################
# Download CSV files from GDrive
########################################

SCOPES = 'https://spreadsheets.google.com/feeds https://docs.google.com/feeds'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Laserphile WooGenerator Drive API'

genFID = "1ps0Z7CYN4D3fQWTPlKJ0cjIkU-ODwlUnZj7ww1gN3xM"
genGID = "784188347"

def get_credentials():
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir, 'drive-woogenerator.json')
    store = oauth2client.file.Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        # if flags:
        #     credentials = tools.run_flow(flow, store, flags)
        # else: # Needed only for compatibility with Python 2.6
        #     credentials = tools.run(flow, store)
        credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials

def download_file_gid_csv(service, drive_file, gid=None):
    """Download a file's content.

    Args:
      service: Drive API service instance.
      drive_file: Drive File instance.

    Returns:
      File's content if successful, None otherwise.
    """
    # print( type(drive_file) )
    # print( drive_file)
    download_url = drive_file['exportLinks']['text/csv']
    if gid:
        download_url += "&gid=" + str(gid )
    print "Downloading: ", download_url
    if download_url:
      resp, content = service._http.request(download_url)
      if resp.status == 200:
        print ('Status: %s' % resp)
        return content
      else:
        print ('An error occurred: %s' % resp)
        return None
    else:
      # The file doesn't have any content stored on Drive.
      return None      

genFID = config.get('genFID')
if download and genFID:
	credentials = get_credentials()
	auth_http = credentials.authorize(httplib2.Http())
	print repr(auth_http)
	service = discovery.build('drive', 'v2', http=auth_http)
	print repr(service)
	drive_file = service.files().get(fileId=genFID).execute()

	for gid, path in [
		(config.get('genGID'), genPath),
		(config.get('dprcGID'), dprcPath),
		(config.get('dprpGID'), dprpPath),
		(config.get('specGID'), specPath),
		(config.get('usGID'), usPath),
		(config.get('xsGID'), xsPath)
	]:
		if gid and path:
		    content = download_file_gid_csv(service, drive_file, str(gid) )
		    if content:
		    	with open(path, 'w') as outFile:
		    		outFile.write(content)

#########################################
# Import Info From Spreadsheets
#########################################

if schema in myo_schemas:
	colData = ColData_MYO()
	productParser = CSVParse_MYO(
		cols = colData.getImportCols(),
		defaults = colData.getDefaults(),
		importName = importName,
		itemDepth = itemDepth,
		taxoDepth = taxoDepth,
	)
elif schema in woo_schemas:

	if DEBUG: print "analysing dprcPath"
	dynParser = CSVParse_Dyn()
	dynParser.analyseFile(dprcPath)
	dprcRules = dynParser.taxos

	print dprcRules

	if DEBUG: print "analysing dprpPath"
	dynParser.clearTransients()
	dynParser.analyseFile(dprpPath)
	dprpRules = dynParser.taxos

	print dprpRules

	if DEBUG: print "analysing specPath"
	specialParser = CSVParse_Special()
	specialParser.analyseFile(specPath)
	specials = specialParser.objects

	print specials

	colData = ColData_Woo()
	if schema == "TT":
		productParser = CSVParse_TT(
			cols = colData.getImportCols(),
			defaults = colData.getDefaults(),
			importName = importName,
			itemDepth = itemDepth,
			taxoDepth = taxoDepth,
			dprcRules = dprcRules,
			dprpRules = dprpRules,
			specials = specials
		)
	elif schema == "VT":
		productParser = CSVParse_VT(
			cols = colData.getImportCols(),
			defaults = colData.getDefaults(),
			importName = importName,
			itemDepth = itemDepth,
			taxoDepth = taxoDepth,
			dprcRules = dprcRules,
			dprpRules = dprpRules,
			specials = specials
		)
	else:
		productParser = CSVParse_Woo(
			cols = colData.getImportCols(),
			defaults = colData.getDefaults(),
			schema = schema, 
			importName = importName,
			itemDepth = itemDepth,
			taxoDepth = taxoDepth,
			dprcRules = dprcRules,
			dprpRules = dprpRules,
			specials = specials
		)
	# usrParser = CSVParse_Usr()

if DEBUG: print "analysing products"
objects = productParser.analyseFile(genPath)

# if schema in woo_schemas:

products = productParser.getProducts()
	
if schema in woo_schemas:
	attributes 	= productParser.attributes
	vattributes = productParser.vattributes
	categories 	= productParser.categories
	variations 	= productParser.variations
	images 		= productParser.images

import_errors = productParser.errors

#########################################
# Images
#########################################	

if schema in woo_schemas:

	print ""
	print "Images:"
	print "==========="

	def reportImportError(source, error):
		import_errors[source] = import_errors.get(source,[]) + [str(error)]

	def invalidImage(img, error):
		reportImportError(img, error)
		images[img].invalidate()

	if skip_images: 
		images = {}
		delete = False;


	ls_imgs = {}
	for folder in imgFolder:
		ls_imgs[folder] = os.listdir(folder)

	def getImage(img):
		for folder in imgFolder:
			if img in ls_imgs[folder]:
				return os.path.join(folder, img)
		raise UserWarning("no img found")

	if not os.path.exists(refFolder):
		os.makedirs(refFolder)

	ls_reflattened = os.listdir(refFolder)
	for f in ls_reflattened:
		if f not in images.keys():
			print "DELETING", f, "FROM REFLATTENED"
			if delete:
				os.remove(os.path.join(refFolder,f))


	for img, data in images.items():
		print img
		if data.taxos:
			print "-> Associated Taxos"
			for taxo in data.taxos:
				print " -> (%4d) %10s" % (taxo.rowcount, taxo.codesum)

		if data.items:
			print "-> Associated Items"
			for item in data.items:
				print " -> (%4d) %10s" % (item.rowcount, item.codesum)

		if data.products:
			print "-> Associated Products"
			for item in data.products:
				print " -> (%4d) %10s" % (item.rowcount, item.codesum)
		else:
			continue
			# we only care about product images atm

		try:
			imgsrcpath = getImage(img)
		except Exception as e:
			invalidImage(img, e)

		name, ext = os.path.splitext(img)
		if(not name): 
			invalidImage(img, "could not extract name")
			continue

		try:
			title, description = data.title, data.description
		except Exception as e:
			invalidImage(img, "could not get title or description: "+str(e) )
			continue

		# print "-> title, description", title, description

		# ------
		# REMETA
		# ------

		try:
			metagator = MetaGator(imgsrcpath)
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

		if resize:
			imgdstpath = os.path.join(refFolder, img)
			if not os.path.isfile(imgsrcpath) :
				print "SOURCE FILE NOT FOUND: ", imgsrcpath
				continue

			if os.path.isfile(imgdstpath) :
				imgsrcmod = max(os.path.getmtime(imgsrcpath), os.path.getctime(imgsrcpath))
				imgdstmod = os.path.getmtime(imgdstpath)
				# print "image mod (src, dst): ", imgsrcmod, imgdstmod
				if imgdstmod > imgsrcmod:
					# print "DESTINATION FILE NEWER: ", imgdstpath
					continue

			print "resizing:", img
			shutil.copy(imgsrcpath, imgdstpath)
			
			try:
				imgmeta = MetaGator(imgdstpath)
				imgmeta.write_meta(title, description)
				print imgmeta.read_meta()

				image = Image.open(imgdstpath)
				image.thumbnail(thumbsize)
				image.save(imgdstpath)

				imgmeta = MetaGator(imgdstpath)
				imgmeta.write_meta(title, description)
				print imgmeta.read_meta()

			except Exception as e:
				invalidImage(img, "could not resize: " + str(e))
				continue

	# ------
	# RSYNC
	# ------

	if not os.path.exists(wpaiFolder):
		os.makedirs(wpaiFolder)

	rsync.main([os.path.join(refFolder,'*'), wpaiFolder])

#########################################
# Export Info to Spreadsheets
#########################################

def joinOrderedDicts(a, b):
	return OrderedDict(a.items() + b.items())

def exportItemsCSV(filePath, colNames, items):
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

def addSubElement(parentElement, tag, attrib={}, value=None):
	# print "addSubElement: tag %s ; attrib %s ; value %s" % (tag, attrib, value)
	tag = sanitationUtils.cleanXMLString(tag)
	# print "addSubElement: tag post clean: %s" % tag
	subElement = ET.SubElement(parentElement, tag, attrib)
	value = sanitationUtils.cleanXMLString(value)
	# print "addSubElement: value post clean: %s" % value
	if value:
		subElement.text = value
	return subElement

def addCols(parentElement, product, cols):
	assert isinstance(cols, dict)
	assert isinstance(product, dict)
	for index, data in cols.items():
		tag = data.get('tag')
		if not tag: tag = index
		value = product.get(index)
		if value is None:
			# pass
			continue
			#would normall not bother adding element if it is None
		attrs = {}
		label = data.get('label')
		if label and label.startswith('meta:'):
			attrs['meta_key'] = label[len('meta:'):]
		addSubElement(parentElement, tag, value=value, attrib=attrs)

def addColGroup(parentElement, product, cols, tag):
	assert isinstance(cols, dict)
	assert isinstance(product, dict)
	if cols:
		prod_keys = product.keys()
		if not any([key in prod_keys for key in cols.keys()]):
			# pass
			return None
			#would normally not bother with subelement				
		subElement = addSubElement(parentElement, tag)
		addCols(subElement, product, cols)
		return subElement

def addImages(parentElement, product, imageData):
	images = product.getImages()
	datum = filter(
		lambda data: data.isValid and data.fileName, 
		[imageData.get(image) for image in images if image in imageData.keys()]
	)
	if not datum:
		return None
	else:
		imagesElement = addSubElement(parentElement, 'images')
		for data in datum:
			fileName = data.fileName
			if not fileName:
				continue
			imageElement = addSubElement(imagesElement, 'image', attrib={'filename': fileName})
			addSubElement(imageElement, 'filename', value=fileName)
			addSubElement(imageElement, 'title', value=data.title)
			addSubElement(imageElement, 'description', value=data.description)

		return imagesElement

def exportProductsXML(filePath, products, productCols, variationCols={}, categoryCols={},
	attributeCols={}, attributeMetaCols={}, pricingCols={}, shippingCols={}, inventoryCols={}, imageData={}):
	print "productCols: ", productCols.keys()
	print "variationCols: ", variationCols.keys()
	print "categoryCols: ", categoryCols.keys()
	prod_exclude_keys = listUtils.getAllkeys(
		attributeCols,
		attributeMetaCols,
		pricingCols,
		shippingCols,
		inventoryCols
	)
	prod_exclude_keys += ['codesum', 'prod_type']
	print "prod_exclude_keys: ", prod_exclude_keys
	product_only_cols = listUtils.keysNotIn(productCols, prod_exclude_keys) 
	print "product_only_cols: ", product_only_cols.keys()
	shipping_exclude_keys = []
	print "shipping_exclude_keys: ", shipping_exclude_keys
	shipping_only_cols = listUtils.keysNotIn(shippingCols, shipping_exclude_keys)
	# shipping_only_cols = listUtils.keysNotIn(shippingCols, listUtils.getAllkeys(pricingCols, inventoryCols)) 
	print "shipping_only_cols: ", shipping_only_cols.keys()
	pricing_exclude_keys = listUtils.getAllkeys(shipping_only_cols)
	print "pricing_exclude_keys: ", pricing_exclude_keys
	pricing_only_cols = listUtils.keysNotIn(pricingCols, pricing_exclude_keys) 
	# pricing_only_cols = listUtils.keysNotIn(shippingCols, listUtils.getAllkeys(shippingCols, inventoryCols)) 
	print "pricing_only_cols: ", pricing_only_cols.keys()
	inventory_exclude_keys = listUtils.getAllkeys(shipping_only_cols, pricing_only_cols)
	print "inventory_exclude_keys: ", inventory_exclude_keys
	inventory_only_cols = listUtils.keysNotIn(inventoryCols, inventory_exclude_keys) 
	print "inventory_only_cols: ", inventory_only_cols.keys()
	variation_exclude_keys = listUtils.getAllkeys(shipping_only_cols, pricing_only_cols, inventory_only_cols)
	print "variation_exclude_keys: ", variation_exclude_keys
	variation_only_cols = listUtils.keysNotIn(listUtils.combineOrderedDicts(attributeMetaCols, variationCols), variation_exclude_keys) 
	print "variation_only_cols: ", variation_only_cols.keys()


	root = ET.Element('products')
	tree = ET.ElementTree(root)
	prodcount = 0
	for sku, product in products.items():
		prodcount += 1
		try:
			product_type = product.product_type
		except:
			product_type = None
		productElement = addSubElement(root, 'product', attrib={'sku':str(sku), 'type':str(product_type), 'prodcount':str(prodcount)})
		# main data:
		addCols(productElement, product, product_only_cols )
		# category data:
		# categories = product.getCategories()
		# if categories:
		# 	categoriesElement = addSubElement(productElement, 'categories')
		# 	for index, category in categories.items():
		# 		categoryElement = addSubElement(categoriesElement, 'category')
		# 		addCols(categoryElement, category, categoryCols)
		# shipping data:
		addColGroup(productElement, product, shipping_only_cols, 'shipping')
		# pricing data:
		addColGroup(productElement, product, pricing_only_cols, 'pricing')
		# inventory data:
		addColGroup(productElement, product, inventory_only_cols, 'inventory')
		# attribute data:
		attributes = product.getAttributes()
		if attributes:
			attributesElement = addSubElement(productElement, 'attributes')
			for attr, data in attributes.items():
				values = data.get('values')
				if values:
					attributeElement = addSubElement(attributesElement, 'attribute', {'attr':str(attr)})
					valuestr = '|'.join( map(str, values))
					addSubElement(attributeElement, 'values', value=valuestr)
					visiblestr = 'yes' if data.get('visible') else 'no'
					addSubElement(attributeElement, 'visible', value=visiblestr)
					variationstr = 'yes' if data.get('variation') else 'no'
					addSubElement(attributeElement, 'variation', value=variationstr)

		#images data:
		addImages(productElement, product, imageData)

		# variation data:
		variations = product.getVariations()
		if variations:
			variationsElement = addSubElement(productElement, 'variations') 
			for vsku, variation in variations.items():
				variationElement = addSubElement(variationsElement, 'variation', {'vsku':str(vsku)})
				addCols(variationElement, variation, variation_only_cols)
				addColGroup(variationElement, variation, shipping_only_cols, 'shipping')
				addColGroup(variationElement, variation, pricing_only_cols, 'pricing')
				addColGroup(variationElement, variation, inventory_only_cols, 'inventory')
				addColGroup(variationElement, variation, attributeMetaCols, 'attributes')
				addImages(variationElement, variation, imageData)

		# print "completed item: ", sku

	# print ET.dump(root)
	if isinstance(filePath, str):
		filePath = [filePath]
	for path in filePath:
		tree.write(path)
		print "WROTE FILE: ", path


def onCurrentSpecial(product):
	return currentSpecial in product.get('spsum')

productCols = colData.getProductCols()

# print "productCols", productCols

if schema in myo_schemas:
	#products
	exportItemsCSV(
		myoPath,
		colData.getColNames(productCols),
		products.values()
	)
elif schema in woo_schemas:

	#products
	attributeCols = colData.getAttributeCols(attributes, vattributes)
	# print 'attributeCols:', attributeCols.keys()
	# print 'productCols: ', productCols.keys()
	productColnames = colData.getColNames( joinOrderedDicts( productCols, attributeCols))
	# print 'productColnames: ', productColnames

	exportItemsCSV(
		flaPath,
		productColnames,
		products.values()
	)

	#variations
		
	variationCols = colData.getVariationCols()
	# print 'variationCols:', variationCols
	attributeMetaCols = colData.getAttributeMetaCols(vattributes)
	# print 'attributeMetaCols:', attributeMetaCols

	if variations:

		exportItemsCSV(
			flvPath,
			colData.getColNames(
				joinOrderedDicts( variationCols, attributeMetaCols)
			),
			variations.values()
		)

	#categories
	categoryCols = colData.getCategoryCols()

	exportItemsCSV(
		catPath,
		colData.getColNames(categoryCols),
		categories.values()
	)

	print 'categoryCols: ', categoryCols.keys()

	#specials
	try:
		assert currentSpecial, "currentSpecial should be set"
		specialProducts = filter(
			onCurrentSpecial,
			products.values()
		)
		if specialProducts:
			flaName, flaExt = os.path.splitext(flaPath)
			flsPath = os.path.join(outFolder , flaName+"-"+currentSpecial+flaExt)
			exportItemsCSV(
					flsPath,
					colData.getColNames(
						joinOrderedDicts( productCols, attributeCols)
					),
					specialProducts
				)
		else:
			print "no products match special"
		specialVariations = filter(
			onCurrentSpecial,
			variations.values()
		)
		if specialVariations:
			flvName, flvExt = os.path.splitext(flvPath)
			flvsPath = os.path.join(outFolder , flvName+"-"+currentSpecial+flvExt)
			exportItemsCSV(
				flvsPath,
				colData.getColNames(
					joinOrderedDicts( variationCols, attributeMetaCols)
				),
				specialVariations
			)
		else:
			print "no variations match special"
	except Exception as e:
		print "no specials 4 u", e
		pass

	pricingCols = colData.getPricingCols()
	print 'pricingCols: ', pricingCols.keys()
	shippingCols = colData.getShippingCols()
	print 'shippingCols: ', shippingCols.keys()
	inventoryCols = colData.getInventoryCols()
	print 'inventoryCols: ', inventoryCols.keys()
	print 'categoryCols: ', categoryCols.keys()

	#export items XML
	exportProductsXML(
		[xmlPath, objPath],
		products,
		productCols,
		variationCols = variationCols,
		categoryCols = categoryCols,
		attributeCols = attributeCols, 
		attributeMetaCols = attributeMetaCols, 
		pricingCols = pricingCols,
		shippingCols = shippingCols,
		inventoryCols = inventoryCols,
		imageData = images
	)


#########################################
# Attempt import
#########################################

for source, error in import_errors.items():
	Registrar.printAnything(source, error, '!')