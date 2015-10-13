import csv
import re
import json
import functools
from itertools import chain
from collections import OrderedDict
import os
import shutil
from PIL import Image
import time
from metagator import MetaGator

importName = time.strftime("%Y-%m-%d %H:%M:%S")

taxoDepth = 2
itemDepth = 2
maxDepth = taxoDepth + itemDepth

inFolder = "../input/"
genPath = inFolder + "generator.csv"
uxsPath = inFolder + "usxs.csv"

outFolder = "../output/"
flaPath = outFolder + "flattened.csv"
flvPath = outFolder + "flattened-variations.csv"
catPath = outFolder + "categories.csv"
myoPath = outFolder + "myob.csv"
bunPath = outFolder + "bundles.csv"

imgFolder = "../../../flattened/"
refFolder = "../../../reflattened/"
logFolder = "../logs/"

thumbsize = 1920, 1200


rename = False
resize = False
remeta = False
delete = False

# rename = True
detele = True
remeta = True
resize = True

myo_schemas = ["MY"]
woo_schemas = ["TT", "VT", "TS"]

# schema = "MY"
schema = "TT"
# schema = "VT"
# schema = "TS"

# The list of column names that need to be read from the import file
cols = woo_schemas + myo_schemas

nameReplace = OrderedDict([
	('Hot Pink', 'Pink'),
	('Hot Lips (Red)', 'Red'),
	('Hot Lips', 'Red'),
	('Silken Chocolate (Bronze)', 'Bronze'),
	('Silken Chocolate', 'Bronze'),
	('Moon Marvel (Silver)', 'Silver'),
	('Dusty Gold', 'Gold'),

	('Screen Printed', ''),
	('Embroidered', ''),
])
defaults = OrderedDict([
	('CVC', '0'),	
	('code', ''),
	('name', ''),
	('fullname', ''),	
	('description', ''),
	('imglist', [])
])
catReplace = OrderedDict([])
colNames = OrderedDict([])
product_types = {}

if schema in woo_schemas:
	execfile('config-woo.py')

elif schema in myo_schemas:
	execfile('config-myo.py')

cols += colNames.keys() 

#########################################
# First Pass: Collect all basic info
#########################################

categories = []
products = []
variations = []
bundles = []
attributes = []
variable_attributes = []
images = OrderedDict()
import_errors = OrderedDict()

def depth(row):
	for i, cell in enumerate(row):
	    if cell: 
	        return i
	    if i >= maxDepth: 
	        return -1
	return -1

namereg = re.compile( "(%s)" % '|'.join(filter(None, map(re.escape, nameReplace))))
def changename(name):
	if not name or not nameReplace: 
		return name
	result = namereg.sub( 
		lambda mo: nameReplace[mo.string[mo.start():mo.end()]], 
		name 
	)
	if name != result: 
		# print "changed %s (%d) to %s (%d)" % ( name, len(name), result, len(result) )
		if len(result) > 29:
			print "!"*30
			print result
	return result

catreg = re.compile( "(%s)" % '|'.join(map(re.escape, catReplace)))
def changecat(cat):
	# print "changing ", cat
	if not cat or not catReplace:
		return cat
	result = catreg.sub( 
		lambda mo: catReplace[mo.string[mo.start():mo.end()]], 
		cat 
	)
	if cat != result: 
		# print "changed %s (%d) to %s (%d)" % ( cat, len(cat), result, len(result) )
		pass
	return result	
# 
def retreiveFromRow(col):
	# print "retrieving", col, "from row"
	default = defaults.get(col,'')
	# print "-> default:", default
	try:
		index = indices[col]
	except KeyError:
		pass
		# print "-> no such column %s " % col
	try:
		value = row[index]
	except TypeError:
		# print "-> could not retrieve %s" % str(col)
		value = ''
	if default != '' and value == '':
		value = default
	# print "-> returning:", value
	return value

def retreiveStackInherited(index):
	for i in range(thisDepth, 0, -1):
		try:
			val = stack[i][index]
		except IndexError:
			break;
		if val:
			return val
	
	return ''

def retreiveStackCascading(index):
	val = []
	for i in range(thisDepth+1):
		try:
			val.append(stack[i][index])
		except IndexError:
			val.append('')
		except KeyError:
			val.append('')
	return val

def compose(*functions):
    return functools.reduce(lambda f, g: lambda x: f(g(x)), functions)

# Parse input file
with open(genPath) as inFile: 		
	csvreader = csv.reader(inFile, strict=True)

	stack = []
	indices = {}

	for rowcount, row in enumerate(csvreader):
		if not indices :
			# fill in indices
			for col in cols:
				try:
					indices[col] = row.index(col) 
					# print "index of column %s is %s" % (col, indices[col])
				except ValueError:
					# pass
					indices[col] = None
					# print "index of column %s could not be found" % col
			stack = []
			continue

		#refresh depth and stack
		thisDepth = depth(row)
		if thisDepth < 0: 
			stack = []
			assert "Stack shouldn't be broken!"
			continue
		
		# stack = stack[:thisDepth]
		del stack[thisDepth:]
		for i in range( len(stack), thisDepth+1):
			stack.append( dict(defaults.items()) )
		
		# print "stack so far: "
		# for i in stack: print " %s" % i

		# capture data in stack
		# ---------------------
		itemData = stack[thisDepth]
		assert len(stack) -1 == thisDepth, 'len(stack) = %d, thisDepth = %d' % (len(stack), thisDepth)

		# -> name
		# --> if is a category
		itemData['fullname'] = row[thisDepth]
		if thisDepth < taxoDepth :
			itemData['name'] = changecat(itemData['fullname'])
		else:
			itemData['name'] = changename(itemData['fullname'])
		# -> code
		try:
			itemData['code'] = row[thisDepth + maxDepth]
		except IndexError:
			itemData['code'] = ""
		# -> others
		# --> preferm replacements on cells
		row[maxDepth*2:] = map( 
			compose(
				lambda x: re.sub('^\W*\$','', x),
				lambda x: re.sub('%\W*$','', x),
				lambda x: re.sub('^-$', '', x),
				lambda x: re.sub('(\d+),(\d{3})', '\g<1>\g<2>', x)
			),
			row[maxDepth*2:]
		)

		print "itemData: %s" % itemData

		# --> get other data inherited by descendents
		for x in cols : 
			itemData[x] = retreiveFromRow(x)
		# --> get ancestoral codes, names
		try:
			codes, names, fullnames = [retreiveStackCascading(x) for x in ['code', 'name', 'fullname']]
		except KeyError:
			print "FAILED IMPORT"
			for layer in stack:
				print layer
			break

		# print "codes: %s\nnames: %s" % (str(codes), str(names))
		# --> get codesum (sku / itemnumber)
		itemData['codesum'] = '-'.join( filter( None, [
			''.join(codes[:taxoDepth]), 
			''.join(codes[taxoDepth:])
		] ) )

		itemData['imglist'] = re.findall( r"[\w\d.-]+", itemData.get('Images','') )
		# if not itemData['imglist'] :
		# 	if itemData['codesum'] not in import_errors.keys():
		# 		import_errors[itemData['codesum']] = []
		# 	import_errors[itemData['codesum']].append( 'no images' )
		for image in itemData['imglist']:
			assert( isinstance(image,str) )
			assert( image is not "" )
			if image not in images.keys():
				images[image] = []
			images[image].append(itemData)
		# print "processing: %s" % itemData['codesum']
		# print "itemData: %s" % itemData
		# --> Perform MYOB-specific tasks
		if schema in myo_schemas:
			# if it is a myob product
			if retreiveFromRow(schema) :
				itemData['item_name'] = ' '.join ( filter( None, names[taxoDepth:] ) )[:32]
				itemData['description'] = ' '.join ( filter( None, fullnames[taxoDepth:] ) )
				itemData['code_len'] = len(itemData['codesum'])
				itemData['desc_len'] = len(itemData['description'])
				itemData['name_len'] = len(itemData['item_name'])

				products.append(itemData)
			else:
				categories.append(itemData)
				continue
		# --> Perform WOO-specific tasks
		elif schema in woo_schemas:
			product_type = retreiveFromRow(schema)

			if product_type in ['Y'] :
				if itemData['codesum'] not in import_errors.keys():
					import_errors[itemData['codesum']] = []
				import_errors[itemData['codesum']].append( 'invalid product type: %s' % product_type )

			itemData['product_type'] = product_types.get(product_type, 'nonproduct')
			print itemData['product_type']

			status = retreiveFromRow('post_status')
			if status:
				itemData['post_status'] = status
			else:
				itemData['post_status'] = defaults.get('post_status', status)

			itemData['catsum'] = ' > '.join( filter( None, names[:taxoDepth]) )
			itemData['namesum'] = ' \xe2\x80\x94 '.join ( filter( None, names[taxoDepth:] ) )
			html_descriptions = filter(None, retreiveStackCascading('HTML Description'))
			if html_descriptions:
				itemData['description'] = html_descriptions[-1]
			else: 
				# if (itemData['product_type'] == 'nonproduct' and thisDepth < taxoDepth ):
				# 	if itemData['codesum'] not in import_errors.keys():
				# 		import_errors[itemData['codesum']] = []
				# 	import_errors[itemData['codesum']].append( 'no explicit description' )
				itemData['description'] = ' '.join ( filter( None, fullnames ) )
			itemData['menu_order'] = rowcount

			all_images = list(itemData['imglist'])
			ancestoral_images = retreiveStackCascading('imglist')
			parent_images = ancestoral_images[max(thisDepth-1,taxoDepth):-1]
			category_images = ancestoral_images[0:min(thisDepth + 1, taxoDepth)]
			# Fill rest of images with parent product images
			for i in reversed(parent_images):
				for j in i:
					if j not in all_images:
						all_images.append(j)
			# if category and can't find any images, fill with parent category images
			if not all_images and thisDepth < taxoDepth:
				for i in reversed(category_images):
					for j in i:
						if j not in all_images:
							all_images.append(j)		
			
			# print "thi: ", itemData['imglist']
			# print "anc: ", ancestoral_images			
			# print "par: ", parent_images
			# print "cat: ", category_images
			# print "all: ", all_images

			itemData['imgsum'] = '|'.join( all_images )

			# if product has parent products
			if thisDepth > taxoDepth:
				#if parent product has no image
				parent_data = stack[-2]
				if not parent_data['imgsum']:
					parent_data['imgsum'] = itemData['imgsum']

			# print itemData['stock_status']  

			#if item is a category
			if itemData['product_type'] == 'nonproduct' :
				if(thisDepth < taxoDepth):
					itemData['product_type'] = 'category'
					# print "found category"
					categories.append(itemData)
				continue

			#if item is a parent product
			if itemData['product_type'] in ['simple', 'variable', 'composite', 'grouped', 'bundle']:
				# process product_category
				itemData['product_category'] = '|'.join( filter( None, retreiveStackCascading( 'catsum')[:taxoDepth] ) )
				# process attributes
				for attr_string in retreiveStackCascading('PA'):
					# print "decoding string: %s " % string
					if not attr_string:
						continue
					try:
						new_attrs = json.loads(attr_string)
					except ValueError:
						print "ValueError while decoding string %s" % attr_string
						new_attrs = {}
					for attr, val in new_attrs.items():
						if 'attributes' not in itemData.keys():
							itemData['attributes'] = {}
						if attr not in itemData['attributes']:
							itemData['attributes'][attr] = {
								'values':[val],
								'visible': 1,
								'variation': 0
							}
							if attr not in attributes: attributes.append( attr )
							continue
						itemData['attributes'][attr]['values'].append(val)

				# complete product
				products.append(itemData)
				continue

			# if item is a variation of a product
			if itemData['product_type'] in ['variable-instance']:
				# process parent sku
				parent_product = products[-1]
				# itemData['parent_SKU'] = products[-1]['codesum']
				itemData['parent_SKU'] = parent_product['codesum']
				# process variable attributes
				attr_string = itemData['VA']
				assert( attr_string )
				try:
					itemData['attributes'] = json.loads(attr_string)
				except ValueError:
					print "ValueError while decoding variable attribute string %s" % attr_string
					itemData['attributes'] = {}
				# modify parent product
				parent_product = products[-1]
				for attr, val in itemData['attributes'].items():
					if 'variable-attributes' not in parent_product.keys():
						parent_product['variable-attributes'] = {}
					if attr not in parent_product['variable-attributes']:
						parent_product['variable-attributes'][attr] = {
							'values':[val], 
							'default':val, 
							'visible':1, 
							'variation':1, 
						}
						if attr not in variable_attributes: variable_attributes.append(attr)
						continue
					parent_product['variable-attributes'][attr]['values'].append(val)
				# get price
				prices = filter(
					None, 
					[
						itemData.get('RNRC',''),
						itemData.get('RPRC',''),
						itemData.get('WNRC',''),
						itemData.get('WPRC',''),
					]
				)
				# itemData['price'] = max(prices)

				# complete variation
				variations.append(itemData)
				continue

			if itemData['product_type'] in ['product-bundle']:
				bundles.append(itemData)

prodPath = outFolder + 'products.csv'
with open(prodPath, 'w+') as outFile:
    cols = ['rowcount', 'codesum', 'itemsum', 'descsum', 'attributes']
    dictwriter = csv.DictWriter(outFile, fieldnames=cols, extrasaction='ignore' )
    dictwriter.writeheader()
    dictwriter.writerows(products)

#########################################
# Export Basic Info to Spreadsheets
#########################################

# update extraNames
extraAttrNames = OrderedDict()
extraAtdaNames = OrderedDict()
# extraAtdeNames = OrderedDict()
extraVttrNames = OrderedDict()
extraVtdaNames = OrderedDict()
extraVtdeNames = OrderedDict()
for attr in attributes:
	extraAttrNames['ATTR:%s' % attr] = 'attribute:%s' % attr
	extraAtdaNames['ATDA:%s' % attr] = 'attribute_data:%s' % attr
	# extraAtdeNames['ATDE:%s' % attr] = 'attribute_default:%s' % attr
for attr in variable_attributes:
	extraVttrNames['VTTR:%s' % attr] = 'attribute:%s' % attr
	extraVtdaNames['VTDA:%s' % attr] = 'attribute_data:%s' % attr
	extraVtdeNames['VTDE:%s' % attr] = 'attribute_default:%s' % attr
extraSimpleNames = OrderedDict( [
	('codesum', 'SKU'),
	('namesum', 'post_title'),
	('product_type', 'tax:product_type'),
	('product_category', 'tax:product_cat'),
	('menu_order', 'menu_order'),
	('HTML Description', 'post_content'),
	('price', 'regular_price'),
	# ('post_status', 'post_status'),
	# ('upsell_skus', 'upsell_skus'),
	# ('crosssell_skus', 'crosssell_skus'),
	# ('last_import', 'meta:last_import'),
] )
extraVarNames = OrderedDict( [
	('parent_SKU', 'parent_SKU'),
	('codesum', 'SKU'),
	('price', 'regular_price'),
] )
extraVarMetaNames = OrderedDict()
for attr in variable_attributes:
	extraVarMetaNames['ATTR:%s' % attr] = 'meta:attribute_%s' % attr
extraCatNames = OrderedDict([
	('codesum', 'SKU'),
	# ('namesum', 'name'),
	('catsum', 'category'),
	('HTML Description', 'description'),
	('menu_order', 'menu_order'),
	('imgsum', 'images'),
])
extraBundleNames = OrderedDict([
	('codesum', 'SKU'),
	('namesum', 'name'),
	('catsum', 'category'),
	('HTML Description', 'description'),
	('menu_order', 'menu_order'),
	('imgsum', 'images'),
	# ('composition', 'composition'),
])
extraMyoNames = OrderedDict([
	('item_name', 'item_name'),
	('description', 'description'),
	('code_len', 'code_len'),
	('name_len', 'name_len'),
	('desc_len', 'desc_len')
])


def getFieldNames( colNames ):
	return OrderedDict( filter(
		lambda x: x[1],
		colNames.items()
	))

if schema in myo_schemas: 
	path = myoPath
	with open(path, 'w') as outFile:
		csvwriter = csv.writer(outFile)
		# writer header

		print ""
		print "MYO HEADER"
		print "=========="
		fieldNames = getFieldNames(OrderedDict( chain(
			filter( 
				lambda (key, val): key not in extraMyoNames.keys(),
				colNames.items()
			),
			extraMyoNames.items()
		)))
		print fieldNames.values()
		csvwriter.writerow(fieldNames.values())
		sort = lambda p, q: cmp(len(p.get('item_name')),len(q.get('item_name')))
		for product in products: #sorted(products, sort):
			csvwriter.writerow( [product[col] for col in fieldNames.keys()] )


if schema in woo_schemas: 
	path = flaPath
	with open(path, 'w') as outFile:
		csvwriter = csv.writer(outFile)
		# writer header

		print ""
		print "PRODUCT HEADER"
		print "=============="
		fieldNames = getFieldNames( OrderedDict( chain (
			extraSimpleNames.items(),
			filter( 
				lambda (key, val): key not in extraSimpleNames.keys(),
				colNames.items()
			),
			extraAttrNames.items(),
			extraVttrNames.items(),
			extraAtdaNames.items(),
			extraVtdaNames.items(),
			# extraAtdeNames.items(),
			extraVtdeNames.items(),
		) ) )
		print fieldNames.values()
		csvwriter.writerow(fieldNames.values())
		for product in products:
			row = []
			for col in fieldNames.keys():
				# print "getting col %s" % col
				
				if col in colNames.keys() + extraSimpleNames.keys():
					row.append(product.get(col,""))
					continue
				if col in extraAttrNames.keys():
					attr = col[len("ATTR:"):]
					values = product.get('attributes',{}).get(attr,{}).get('values',[])
					row.append('|'.join(map(str,values)))
					continue
				# if col in extraAtdeNames.keys():
				# 	attr = col[len("ATDE:"):]
				# 	default = product.get('attributes',{}).get(attr,{}).get('default','')				
				# 	row.append(default)
				# 	continue	
				if col in extraAtdaNames.keys():
					attr = col[len("ATDA:"):]
					data = product.get('attributes',{}).get(attr,{})
					if data:
						visible = data.get('visible',1)
						variation = data.get('variation',0)
						position = data.get('position',0)
						row.append('|'.join(map(str,[position,visible,variation])))
					else:
						row.append('')
					continue
				if col in extraVttrNames.keys():
					attr = col[len("ATTR:"):]
					values = product.get('variable-attributes',{}).get(attr,{}).get('values',[])
					row.append('|'.join(map(str, values)))
					continue			
				if col in extraVtdeNames.keys():		
					attr = col[len("VTDE:"):]
					default = product.get('variable-attributes',{}).get(attr,{}).get('default','')				
					row.append(default)
					continue
				if col in extraVtdaNames.keys():
					attr = col[len("VTDA:"):]
					data = product.get('variable-attributes',{}).get(attr,{})
					if data:
						visible = data.get('visible',1)
						variation = data.get('variation',1)
						position = data.get('position',0)
						row.append('|'.join(map(str,[position,visible,variation])))
					else:
						row.append('')
					continue
			csvwriter.writerow(row)

#variations
if schema in woo_schemas: 
	with open(flvPath, 'w') as outFile:
		csvwriter = csv.writer(outFile)
		print ""
		print "VARIATION HEADER"
		print "================"

		fieldNames = getFieldNames( OrderedDict( chain (
			extraVarNames.items(),
			filter(
				lambda (key, val): key not in extraVarNames.keys(),
				colNames.items(),
			),
			extraVarMetaNames.items()
		)))
		
		print fieldNames.values()
		csvwriter.writerow(fieldNames.values())
		for variation in variations:
			# print "processing variation: %s" % str(variation)
			row = []
			for col in fieldNames.keys():
				if col in extraVarNames.keys() + colNames.keys():
					row.append(variation.get(col,''))
					continue
				if col in extraVarMetaNames.keys():
					attr = col[len('ATTR:'):]
					value = variation.get('attributes',{}).get(attr,'')
					row.append(value)
					continue
			csvwriter.writerow(row)

#categories
if schema in woo_schemas:
	with open(catPath, 'w') as outFile:
		csvwriter = csv.writer(outFile)
		print ""
		print "CAT HEADER"
		print "=========="

		fieldNames = getFieldNames(extraCatNames)

		print fieldNames.values()
		csvwriter.writerow(fieldNames.values())
		for cat in categories:
			# print cat
			row = []
			for col in fieldNames.keys():
				if col in extraCatNames.keys():
					row.append(cat.get(col,''))
					continue
			csvwriter.writerow(row)
#bundles
if schema in woo_schemas:
	with open(bunPath, 'w') as outFile:
		csvwriter = csv.writer(outFile)
		print ""
		print "BUNDLE HEADER"
		print "============="

		fieldNames = getFieldNames(extraBundleNames)

		print fieldNames.values()
		csvwriter.writerow(fieldNames.values())
		for bun in bundles:
			# print bun
			row = []
			for col in fieldNames.keys():
				if col in extraBundleNames.keys():
					row.append(bun.get(col, ''))
					continue
			csvwriter.writerow(row)


# todo: init bunPath and extraBundleNames composition column

# print ""
# print "products:"
# print "========="
# skus = []
# for product in products:
# 	# assert product['codesum'] not in skus , product['codesum']
# 	skus.append(product['codesum'])
# 	print "[%s]: %s" % (str(product['codesum']), str(product['item_name']))
# 	print product

# print ""
# print "variations:"
# print "==========="
# skus = []
# for variation in variations:
# 	assert(variation['codesum'] not in skus )
# 	skus.append(variation['codesum'])
# 	print "[%s][%s]: %s" % (str(variation['parent_SKU']), str(variation['codesum']), str(variation['namesum']))

# print ""
# print "Attributes:"
# print "==========="
# print "simple"
# print "------"
# for attr in attributes:
# 	print attr
# print "variable"
# print "--------"
# for attr in variable_attributes:
# 	print attr

# print ""
# print "Import Errors:"
# print "=============="
# for sku, errors in import_errors.items():
# 	print sku
# 	for error in errors:
# 		print "-> ", error


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
	if f not in ls_flattened:
		print "DELETING", f, "FROM REFLATTENED"
		if delete:
			os.remove(os.path.join(refFolder,f))
			pass

cmp_codelen = lambda a, b: cmp( len(a.get('codesum',)), len(b.get('codesum')))
not_category = lambda x: x.get('product_type') != 'category' 

new_img = {}
changes_name = OrderedDict()
changes_meta = OrderedDict()
for img, items in sorted(images.items(), lambda (ak, av), (bk, bv): cmp(len(av), len(bv))):
	if img not in changes_meta.keys():
		changes_meta[img] = []
	if img not in changes_name.keys():
		changes_name[img] = []
	cm = changes_meta[img]
	cn = changes_name[img]
	# print ""
	print img
	print "-> Associated items"
	for item in items:
		print " -> (%4d) %10s : %32s | %5s" % (item['menu_order'], item['codesum'], item['namesum'], item['product_type'])
	
	#image name and extention

	# extmatches = re.findall( r".[\w\d]+", img)
	# assert len(extmatches) > 0
	# ext = extmatches[-1]
	# name = img[:-len(ext)]

	name, ext = os.path.splitext(img)
	if(not name): continue

	# print "%s: name: %s, ext: %s" % (img, name, ext)

	noncategories = filter(not_category, items )
	if noncategories:
		head = sorted(noncategories, cmp_codelen)[0]
		name = head.get('codesum')
		title = head.get('namesum') if head['namesum'] else head['catsum']
		description = head.get('description')
	else:
		head = sorted(items, cmp_codelen)[0]
		title = head.get('catsum')
		description = head.get('description')

	#TODO: add exception for product categories
	
	if not title:
		import_errors[name] = import_errors.get(name,[]) + ["no title"]
	if not description:
		import_errors[name] = import_errors.get(name,[]) + ["no description"]

	# ------
	# RENAME
	# ------

	for item in items:
		if item['menu_order'] in new_img.keys():
			new_img[item['menu_order']] += '|' + name + ext
		else:
			new_img[item['menu_order']] = name + ext

	if name + ext != img:
		cn.append("Changing name to %s" % (name + ext))
		if rename: 
			try:
				shutil.move(imgFolder + img, imgFolder + name + ext )
				img = name + ext
			except IOError:
				print "IMAGE NOT FOUND: ", img
				continue


	# ------
	# REMETA
	# ------

	fullname = os.path.join(imgFolder, img)
	# print "fullname", fullname
	try:
		metagator = MetaGator(os.path.join(imgFolder, img))
	except Exception, e:
		import_errors[name] = import_errors.get(name,[]) + ["error creating metagator: " + str(e)]
		continue

	try:
		oldmeta = metagator.read_meta()
	except Exception, e:
		import_errors[name] = import_errors.get(name,[]) + ["error reading from metagator: " + str(e)]	
		continue

	newmeta = {
		'title': (title),
		'description': (description)
	}

	for oldval, newval in (
		(oldmeta['title'], newmeta['title']),
		(oldmeta['description'], newmeta['description']), 
	):
		if oldval != newval:
			cm.append("changing imgmeta from %s to %s" % (str(oldval)[:10]+'...'+str(oldval)[-10:], str(newval)[:10]+'...'+str(newval)[-10:]))

	if len(cm) > 0 and remeta:
		print ' -> errors', cm
		try:	
			metagator.write_meta(title, description)
		except Exception, e:
			import_errors[name] = import_errors.get(name,[]) + ["error writing to metagator: " + str(e)]


	# ------
	# RESIZE
	# ------

	if resize:
		imgsrcpath = imgFolder + img
		imgdstpath = refFolder + img
		if not os.path.isfile(imgsrcpath) :
			print "SOURCE FILE NOT FOUND:", imgsrcpath
			continue

		if os.path.isfile(imgdstpath) :
			imgsrcmod = os.path.getmtime(imgsrcpath)
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


if not os.path.exists(logFolder):

	os.makedirs(logFolder)

logname = importName + ".log"
with open( os.path.join(logFolder, logname), 'w+' ) as logFile:

	logFile.write( "import errors:\n")
	for code, errors in import_errors.items():
		logFile.write( "%s :\n" % code)
		for error in errors:
			logFile.write(" -> %s\n" % error)

	logFile.write("")
	logFile.write( "Changes:\n" )
	logFile.write( " -> name\n")
	for img, chlist in changes_name.iteritems():
		if chlist: 
			logFile.write( "%s: \n" % img )
			for change in chlist:
				logFile.write( "-> %s\n" % change	)
	logFile.write( " -> meta\n")
	for img, chlist in changes_meta.iteritems():
		if chlist: 
			logFile.write( "%s: \n" % img )
			for change in chlist:
				logFile.write( "-> %s\n" % change	)			

	logFile.write("")
	if rename:
		logFile.write( "Img column:\n" )
		i = 0
		while new_img:
			if i in new_img.keys():
				logFile.write( "%s\n" % new_img[i] )
				del new_img[i]
			else:
				logFile.write( "\n" )
			i += 1

with open( os.path.join(logFolder, logname) ) as logFile:

	for line in logFile:
		print line[:-1]