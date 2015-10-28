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



importName = time.strftime("%Y-%m-%d %H:%M:%S")

taxoDepth = 3
itemDepth = 2
maxDepth = taxoDepth + itemDepth

inFolder = "../input/"
genPath = os.path.join(inFolder, 'generator.csv')
dprcPath= os.path.join(inFolder, 'DPRC.csv')
dprpPath= os.path.join(inFolder, 'DPRP.csv')
specPath= os.path.join(inFolder, 'specials.csv')
usPath 	= os.path.join(inFolder, 'US.csv')
xsPath	= os.path.join(inFolder, 'XS.csv')

outFolder = "../output/"
flaPath = os.path.join(outFolder , "flattened.csv")
flvPath = os.path.join(outFolder , "flattened-variations.csv")
catPath = os.path.join(outFolder , "categories.csv")
myoPath = os.path.join(outFolder , "myob.csv")
bunPath = os.path.join(outFolder , "bundles.csv")
xmlPath = os.path.join(outFolder , "items.xml")

webFolder = "/Applications/MAMP/htdocs/"
objPath = os.path.join(webFolder, "objects.xml")

wpaiFolder = "/Applications/MAMP/htdocs/wordpress/wp-content/uploads/wpallimport/files/"

imgFolder = "/Users/Derwent/Dropbox/TechnoTan/flattened/"
refFolder = "/Users/Derwent/Dropbox/TechnoTan/reflattened/"
logFolder = "../logs/"

thumbsize = 1920, 1200

rename = False
resize = False
remeta = False
delete = False
skip_images = False

myo_schemas = ["MY"]
woo_schemas = ["TT", "VT", "TS"]

# schema = "MY"
schema = "TT"
# schema = "VT"
# schema = "TS"

###CUSTOM SETTINGS###

# skip_images = True
remeta = True
resize = True
delete = True

#this override gives only solution
# genPath = os.path.join(inFolder, 'generator-solution.csv')
# xmlPath = os.path.join(outFolder , "items-solution.xml")
# objPath = os.path.join(webFolder, "objects-solution.xml")

# this override gives only accessories
genPath = os.path.join(inFolder, 'generator-accessories.csv')
xmlPath = os.path.join(outFolder , "items-accessories.xml")
objPath = os.path.join(webFolder, "objects-accessories.xml")

DEBUG = True

currentSpecial = None
# currentSpecial = "SP2015-09-18"

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
	if images:
		imagesElement = addSubElement(parentElement, 'images')
		for image in images:
			imageElement = addSubElement(imagesElement, 'image')
			addSubElement(imageElement, 'filename', value=image)
			data = imageData.get(image)
			if data:
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

		print "completed item: ", sku

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
			flsPath = os.path.join(outFolder , "flattened-"+currentSpecial+".csv")
			exportItemsCSV(
					flsPath,
					colData.getColNames(
						joinOrderedDicts( productCols, attributeCols)
					),
					specialProducts
				)
		specialVariations = filter(
			onCurrentSpecial,
			variations.values()
		)
		if specialVariations:
			flvsPath = os.path.join(outFolder , "flattened-variations-"+currentSpecial+".csv")
			exportItemsCSV(
				flvsPath,
				colData.getColNames(
					joinOrderedDicts( variationCols, attributeMetaCols)
				),
				specialVariations
			)
	except:
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



#########################################
# Images
#########################################	

if skip_images: images = {}

print ""
print "Images:"
print "==========="

#prepare reflattened directory

if not os.path.exists(refFolder):
	os.makedirs(refFolder)
# if os.path.exists(refFolder):
# 	print "PATH EXISTS"
# 	shutil.rmtree(refFolder)
# os.makedirs(refFolder)
ls_flattened = os.listdir(imgFolder) 
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

	name, ext = os.path.splitext(img)
	if(not name): continue
	title, description = data.title, data.description

	# print "-> title, description", title, description

	# ------
	# REMETA
	# ------

	try:
		metagator = MetaGator(os.path.join(imgFolder, img))
	except Exception, e:
		import_errors[img] = import_errors.get(img,[]) + ["error creating metagator: " + str(e)]
		continue

	try:
		oldmeta = metagator.read_meta()
	except Exception, e:
		import_errors[img] = import_errors.get(img,[]) + ["error reading from metagator: " + str(e)]	
		continue

	newmeta = {
		'title': title,
		'description': description
	}

	for oldval, newval in (
		(oldmeta['title'], newmeta['title']),
		(oldmeta['description'], newmeta['description']), 
	):
		if str(oldval) != str(newval):
			print ("changing imgmeta from %s to %s" % (repr(oldval), str(newval)[:10]+'...'+str(newval)[-10:]))
			try:	
				metagator.write_meta(title, description)
			except Exception, e:
				import_errors[img] = import_errors.get(img,[]) + ["error writing to metagator: " + str(e)]


	# ------
	# RESIZE
	# ------

	if resize:
		imgsrcpath = os.path.join(imgFolder, img)
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
		
		imgmeta = MetaGator(imgdstpath)
		imgmeta.write_meta(title, description)
		print imgmeta.read_meta()

		image = Image.open(imgdstpath)
		image.thumbnail(thumbsize)
		image.save(imgdstpath)

		# try:
		# except Exception as e:
		# 	print "!!!!!", type(e), str(e)
		# 	continue

		imgmeta = MetaGator(imgdstpath)
		imgmeta.write_meta(title, description)
		print imgmeta.read_meta()

# ------
# RSYNC
# ------

rsync.main([os.path.join(refFolder,'*'), wpaiFolder])

for source, error in import_errors.items():
	Registrar.printAnything(source, error, '!')

# cmp_vallen = lambda (ak, av), (bk, bv): cmp(len(av), len(bv))
# cmp_codelen = lambda a, b: cmp( len(a.get('codesum',)), len(b.get('codesum')))
# not_category = lambda x: x.get('thisDepth') >= 2

# new_img = {}
# changes_name = OrderedDict()
# changes_meta = OrderedDict()
# # for img, items in images.items():
# for img, items in sorted(images.items(), cmp_vallen):
# 	if img not in changes_meta.keys():
# 		changes_meta[img] = []
# 	if img not in changes_name.keys():
# 		changes_name[img] = []
# 	cm = changes_meta[img]
# 	cn = changes_name[img]
# 	# print ""
# 	print img
# 	print "-> Associated items"
# 	for item in items:
# 		print " -> (%4d) %10s" % (item['rowcount'], item['codesum'])
	
# 	#image name and extention

# 	# extmatches = re.findall( r".[\w\d]+", img)
# 	# assert len(extmatches) > 0
# 	# ext = extmatches[-1]
# 	# name = img[:-len(ext)]

# 	name, ext = os.path.splitext(img)
# 	if(not name): continue

# 	# print "%s: name: %s, ext: %s" % (img, name, ext)

# 	noncategories = filter(not_category, items )
# 	# print noncategories
# 	if noncategories:
# 		head = sorted(noncategories, cmp_codelen)[0]
# 		name = head.get('codesum')
# 		title = filter(None, [head.get('itemsum'), head.get('fullname')])[0]
# 		description = head.get('descsum')
# 	else:
# 		head = sorted(items, cmp_codelen)[0]
# 		title = head.get('taxosum')
# 		description = head.get('descsum')

# 	#TODO: add exception for product categories
# 	if not description:
# 		description = title
# 	if not title:
# 		import_errors[img] = import_errors.get(img,[]) + ["no title"]
# 	if not description:
# 		import_errors[img] = import_errors.get(img,[]) + ["no description"]

# 	# ------
# 	# RENAME
# 	# ------

# 	for item in items:
# 		if item['rowcount'] in new_img.keys():
# 			new_img[item['rowcount']] += '|' + name + ext
# 		else:
# 			new_img[item['rowcount']] = name + ext

# 	if name + ext != img:
# 		cn.append("Changing name to %s" % (name + ext))
# 		if rename: 
# 			try:
# 				shutil.move(imgFolder + img, imgFolder + name + ext )
# 				img = name + ext
# 			except IOError:
# 				print "IMAGE NOT FOUND: ", img
# 				continue


# 	# ------
# 	# REMETA
# 	# ------

# 	fullname = os.path.join(imgFolder, img)
# 	# print "fullname", fullname
# 	try:
# 		metagator = MetaGator(os.path.join(imgFolder, img))
# 	except Exception, e:
# 		import_errors[img] = import_errors.get(img,[]) + ["error creating metagator: " + str(e)]
# 		continue

# 	try:
# 		oldmeta = metagator.read_meta()
# 	except Exception, e:
# 		import_errors[img] = import_errors.get(img,[]) + ["error reading from metagator: " + str(e)]	
# 		continue

# 	newmeta = {
# 		'title': title,
# 		'description': description
# 	}

# 	for oldval, newval in (
# 		(oldmeta['title'], newmeta['title']),
# 		(oldmeta['description'], newmeta['description']), 
# 	):
# 		if str(oldval) != str(newval):
# 			cm.append("changing imgmeta from %s to %s" % (repr(oldval), str(newval)[:10]+'...'+str(newval)[-10:]))

# 	if len(cm) > 0 and remeta:
# 		print ' -> errors', cm
# 		try:	
# 			metagator.write_meta(title, description)
# 		except Exception, e:
# 			import_errors[img] = import_errors.get(img,[]) + ["error writing to metagator: " + str(e)]


# 	# ------
# 	# RESIZE
# 	# ------

# 	if resize:
# 		imgsrcpath = imgFolder + img
# 		imgdstpath = refFolder + img
# 		if not os.path.isfile(imgsrcpath) :
# 			print "SOURCE FILE NOT FOUND:", imgsrcpath
# 			continue

# 		if os.path.isfile(imgdstpath) :
# 			imgsrcmod = os.path.getmtime(imgsrcpath)
# 			imgdstmod = os.path.getmtime(imgdstpath)
# 			# print "image mod (src, dst): ", imgsrcmod, imgdstmod
# 			if imgdstmod > imgsrcmod:
# 				# print "DESTINATION FILE NEWER: ", imgdstpath
# 				continue

# 		print "resizing:", img
# 		shutil.copy(imgsrcpath, imgdstpath)
		
# 		imgmeta = MetaGator(imgdstpath)
# 		imgmeta.write_meta(title, description)
# 		print imgmeta.read_meta()

# 		image = Image.open(imgdstpath)
# 		image.thumbnail(thumbsize)
# 		image.save(imgdstpath)

# 		# try:
# 		# except Exception as e:
# 		# 	print "!!!!!", type(e), str(e)
# 		# 	continue

# 		imgmeta = MetaGator(imgdstpath)
# 		imgmeta.write_meta(title, description)
# 		print imgmeta.read_meta()


# if not os.path.exists(logFolder):

# 	os.makedirs(logFolder)

# logname = importName + ".log"
# with open( os.path.join(logFolder, logname), 'w+' ) as logFile:

# 	logFile.write( "import errors:\n")
# 	for code, errors in import_errors.items():
# 		logFile.write( "%s :\n" % code)
# 		for error in errors:
# 			logFile.write(" -> %s\n" % error)

# 	logFile.write("")
# 	logFile.write( "Changes:\n" )
# 	logFile.write( " -> name\n")
# 	for img, chlist in changes_name.iteritems():
# 		if chlist: 
# 			logFile.write( "%s: \n" % img )
# 			for change in chlist:
# 				logFile.write( "-> %s\n" % change	)
# 	logFile.write( " -> meta\n")
# 	for img, chlist in changes_meta.iteritems():
# 		if chlist: 
# 			logFile.write( "%s: \n" % img )
# 			for change in chlist:
# 				logFile.write( "-> %s\n" % change	)			

# 	logFile.write("")
# 	if rename:
# 		logFile.write( "Img column:\n" )
# 		i = 0
# 		while new_img:
# 			if i in new_img.keys():
# 				logFile.write( "%s\n" % new_img[i] )
# 				del new_img[i]
# 			else:
# 				logFile.write( "\n" )
# 			i += 1

# with open( os.path.join(logFolder, logname) ) as logFile:

# 	for line in logFile:
# 		print line[:-1]