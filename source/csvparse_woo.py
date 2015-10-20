from csvparse_abstract import listUtils
from csvparse_gen import CSVParse_Gen, ImportGenProduct, ImportGenItem, ImportGenTaxo
from collections import OrderedDict
import re
import time
import datetime
import json

def findAllImages(imgString):
    assert type(imgString) == str, "param must be a string not %s"% type(imgString)
    return re.findall(r'\s*([^.|]*\.[^.|\s]*)(?:\s*|\s*)',imgString)

def findAllTokens(tokenString, delim = "|"):
    assert type(tokenString) == str, "param must be a string not %s"% type(tokenString)
    return re.findall(r'\s*(\b[^\s.|]+\b)\s*', tokenString )

def findallDollars(instring):
    assert type(instring) == str, "param must be a string not %s"% type(instring)
    return re.findall("\s*\$([\d,]+\.?\d*)", instring)

def findallPercent(instring):
    assert type(instring) == str, "param must be a string not %s"% type(instring)
    return re.findall("\s*(\d+\.?\d*)%", instring)

def datetotimestamp(datestring):
    assert type(datestring) == str, "param must be a string not %s"% type(datestring)
    return int(time.mktime(datetime.datetime.strptime(datestring, "%d/%m/%Y").timetuple()))

DEBUG_WOO = True

class ImportWooMixin:
    """docstring for ImportWooMixin"""

    def __init__(self, *args):
        self.attributes = OrderedDict()
        self.images = []
        self.specials = []

    def isFirstOrder(self): return False;
    def isVariable(self): return False;
    def isVariation(self): return False;

    def registerImage(self, image):
        assert type(image) == str
        thisImages = self.getImages()
        if image not in thisImages:
            thisImages.append(image)
            # parent = self.getParent()
            # parentImages = parent.getImages()
            # if not parentImages:
            #     parent.registerImage(image)

    def getImages(self):
        return self.images

    def registerAttribute(self, attr, val, var=False):
        if var:
            assert self.isVariation() or self.isVariable()
        attrs = self.getAttributes()
        if attr not in attrs:
            attrs[attr] = {
                'values':[val],
                'visible':1,
                'variation':0
            }
            if var:
                attrs[attr]['default'] = val
        elif val not in attrs[attr]['values'] :
            attrs[attr]['values'].append(val)
        if var:
            if not attrs[attr]['default']:
                attrs[attr]['default'] = val
            attrs[attr]['variation'] = 1

    def getAttributes(self):
        try:
            return self.attributes
        except:
            return OrderedDict()

    def registerSpecial(self, special):
        if special not in self.specials:
            self.specials.append(special)

    def getSpecials(self):
        return self.specials

    def getInheritanceAncestors(self):
        return self.getAncestors()

class ImportWooItem(ImportGenItem, ImportWooMixin):
    """docstring for ImportWooItem"""
    def __init__(self, *args):
        super(ImportWooItem, self).__init__(*args)
        ImportWooMixin.__init__(self, *args)

class ImportWooProduct(ImportGenProduct, ImportWooMixin):
    """docstring for ImportWooProduct"""

    def __init__(self, *args):
        super(ImportWooProduct, self).__init__(*args)
        ImportWooMixin.__init__(self, *args)
        self.categories = OrderedDict()
        self['prod_type'] = self.product_type

    def registerCategory(self, catData):
        self.registerAnything(
            catData,
            self.categories,
            # indexer = self.getSum,
            indexer = catData.getRowcount(),
            singular = True,
            resolver = self.exceptionResolver,
            registerName = 'product categories'
        )

    def joinCategory(self, catData):
        self.registerCategory(catData)
        catData.registerMember(self)

    def getCategories(self):
        return self.categories

    def getAttributes(self):
        return self.get('attributes', OrderedDict())

    def getVariations(self):
        return None

    def getNameDelimeter(self):
        return ' \xe2\x80\x94 '

    def getInheritanceAncestors(self):
        return listUtils.filterUniqueTrue( 
            super(ImportWooProduct, self).getInheritanceAncestors() + self.getCategories().values() 
        )

class ImportWooSimpleProduct(ImportWooProduct):
    """docstring for ImportWooSimpleProduct"""
    product_type = 'simple'

    def isFirstOrder(): return True; 

class ImportWooVariableProduct(ImportWooProduct):
    """docstring for ImportWooVariableProduct"""
    product_type = 'variable'

    def __init__(self, *args):
        super(ImportWooVariableProduct, self).__init__(*args)
        self.variations = OrderedDict()

    def registerVariation(self, varData):
        self.registerAnything(
            varData,
            self.variations,
            indexer = varData.getCodesum(),
            singular = True,
            registerName = "product variations"
        )

    def getVariations(self):
        return self.variations

    def isFirstOrder(self): return True; 
    def isVariable(self): return True; 

class ImportWooVariation(ImportWooProduct):
    """docstring for ImportWooVariation"""
    product_type = 'variable-instance'

    def registerParentProduct(self, parentData):
        self.parentProduct = parentData
        self['parent_SKU'] = parentData.getCodesum()

    def joinVariable(self, parentData):
        self.registerParentProduct(parentData)
        parentData.registerVariation(self)

    def getParentProduct(self):
        return self.parentProduct

    def isVariation(self): return True;        

class ImportWooCompositeProduct(ImportWooProduct):
    """docstring for ImportWooVariableProduct"""
    product_type = 'composite'

    def isFirstOrder(self): return True; 

class ImportWooGroupedProduct(ImportWooProduct):
    """docstring for ImportWooGroupedProduct"""
    product_type = 'grouped'

    def isFirstOrder(self): return True; 

class ImportWooBundledProduct(ImportWooProduct):
    """docstring for ImportWooBundledProduct"""
    product_type = 'bundle'

    def isFirstOrder(self): return True; 

class ImportWooCategory(ImportGenTaxo, ImportWooMixin):
    """docstring for ImportWooCategory"""
    productsKey = 'products'

    def __init__(self, *args):
        super(ImportWooCategory, self).__init__(*args) 
        ImportWooMixin.__init__(self, *args)
        self.members = OrderedDict()

    def registerMember(self, itemData):
        self.registerAnything(
            itemData,
            self.members,
            # indexer = self.getSum,
            indexer = itemData.getRowcount(),
            singular = True,
            resolver = self.passiveResolver,
            registerName = 'product categories'
        )

    def getMembers(self, itemData):
        return self.members

class CSVParse_Woo(CSVParse_Gen):
    """docstring for CSVParse_Woo"""

    prod_containers = {
        'S': ImportWooSimpleProduct,
        'V': ImportWooVariableProduct,
        'I': ImportWooVariation,
        'C': ImportWooCompositeProduct,
        'G': ImportWooGroupedProduct,
        'B': ImportWooBundledProduct,
    }

    def __init__(self, cols, defaults, schema="", importName="", \
                taxoSubs={}, itemSubs={}, taxoDepth=2, itemDepth=2, metaWidth=2,\
                dprcRules={}, dprpRules={}, specials={}):
        extra_cols = [ 'PA', 'VA', 'weight', 'length', 'width', 'height', 
                    'stock', 'stock_status', 'Images', 'HTML Description',
                    'post_status']

        extra_defaults =  OrderedDict([
            ('post_status', 'publish'),
            # ('last_import', importName),
        ])

        extra_taxoSubs = OrderedDict([
            ('Generic Literature', 'Marketing > Literature'),
            ('Generic Signage', 'Marketing > Signage'),
            ('Generic ', ''),
            ('Shimmerz for Hair', 'Shimmerz for Hair'),
            ('Sqiffy Accessories', 'Sqiffy'),
            ('Sticky Soul Accessories', 'Sticky Soul'),
            ('Tanning Advantage ', ''),   
            ('Assorted ', ''),
            ('My Tan Apparel', 'My Tan Dress'),
            # ('Shimmerz for Hair', 'Tanning Accessories > Shimmerz for Hair'),
            # ('Sqiffy Accessories', 'Tanning Accessories > Sqiffy'),
            # ('EzeBreathe', 'Tanning Accessories > EzeBreathe'),
            # ('My Tan', 'Tanning Accessories > My Tan'),
            # ('Tan Sleeper', 'Tanning Accessories > Tan Sleeper'),
            # ('Tanning Advantage Application Equipment', 'Equipment > Application Equipment'),   
            # ('Generic Application Equipment', 'Equipment > Application Equipment'),
            # ('Generic Tanning Booths', 'Equipment > Tanning Booths'),
        ])

        extra_itemSubs = OrderedDict()

        if not importName: importName = time.strftime("%Y-%m-%d %H:%M:%S")
        cols = listUtils.combineLists( cols, extra_cols )
        defaults = listUtils.combineOrderedDicts( defaults, extra_defaults )
        taxoSubs = listUtils.combineOrderedDicts( taxoSubs, extra_taxoSubs )
        itemSubs = listUtils.combineOrderedDicts( itemSubs, extra_itemSubs ) 
        if not schema: schema = "TT"
        super(CSVParse_Woo, self).__init__( cols, defaults, schema, \
                taxoSubs, itemSubs, taxoDepth, itemDepth, metaWidth)
        self.dprcRules = dprcRules
        self.dprpRules = dprpRules
        self.specials = specials
        self.itemContainer      = ImportWooItem
        self.productContainer   = ImportWooProduct
        self.taxoContainer      = ImportWooCategory
        if DEBUG_WOO:
            print "WOO initializing: "
            print "-> taxoDepth: ", self.taxoDepth
            print "-> itemDepth: ", self.itemDepth
            print "-> maxDepth: ", self.maxDepth
            print "-> metaWidth: ", self.metaWidth

    def clearTransients(self):
        super(CSVParse_Woo, self).clearTransients()
        self.categories = OrderedDict()
        self.attributes = OrderedDict()
        self.vattributes= OrderedDict()
        self.variations = OrderedDict()
        self.images     = OrderedDict()        

    def registerImage(self, image, objectData):
        assert isinstance(image,str) 
        assert image is not "" 
        self.registerAnything(
            objectData,
            self.images,
            indexer = image,
            singular = False,
            registerName = 'images'
        )
        objectData.registerImage(image)

    def registerCategory(self, catData, itemData):
        self.registerAnything(
            catData, 
            self.categories, 
            # indexer = self.getSum,
            indexer = catData.getIndex(),
            resolver = self.passiveResolver,
            singular = True,
            registerName = 'categories'
        )
        itemData.joinCategory(catData)

    def registerAttribute(self, objectData, attr, val, var=False):
        try:
            attr = str(attr)
            assert isinstance(attr, str), 'Attribute must be a string not {}'.format(type(attr).__name__)
            assert attr is not '', 'Attribute must not be empty'
            assert attr[0] is not ' ', 'Attribute must not start with whitespace or '
        except AssertionError as e:
            self.registerError("could not register attribute: {}".format(e))
            # raise e
        else:
            objectData.registerAttribute(attr, val, var)
            self.registerAnything(
                val,
                self.attributes,
                indexer = attr,
                singular = False,
                registerName = 'Attributes'
            )
            if var:
                self.registerAnything(
                    val,
                    self.vattributes,
                    indexer = attr,
                    singular = False,
                    registerName = 'Variable Attributes'
                )

    def registerVariation(self, parentData, varData):
        assert parentData.isVariable()
        assert varData.isVariation()
        self.registerAnything( 
            varData, 
            self.variations, 
            indexer = varData.getIndex(),
            registerName = 'variations' 
        )
        # if not parentData.get('variations'): parentData['variations'] = OrderedDict()
        varData.joinVariable(parentData)

    def registerSpecial(self, objectData, special):
        try:
            special = str(special)
            assert isinstance(special, str), 'Special must be a string not {}'.format(type(special).__name__)
            assert special is not '', 'Attribute must not be empty'
        except AssertionError as e:
            self.registerError("could not register special: {}".format(e))
        # self.registerAnything(
        #     objectData,
        #     self.specials,
        #     indexer = special,
        #     singular = False,
        #     registerName = 'specials'
        # )
        objectData.registerSpecial(special)

    def processImages(self, objectData):
        # if DEBUG_WOO: print "called processImages"

        imglist = filter(None, findAllImages(objectData.get('Images','')))
        for image in imglist:
            self.registerImage(image, objectData)
            # objectData.registerImage(image)

        # todo: share images with nearest parent

    def processCategories(self, objectData):
        if objectData.isProduct():
            for ancestor in objectData.getTaxoAncestors():
                self.registerCategory(ancestor, objectData)

        #todo: this "extra item" crap


    def processVariation(self, varData):
        assert varData.isVariation()
        parentData = varData.getParent()
        assert parentData and parentData.isVariable()
        self.registerVariation(parentData, varData)

    def decodeAttributes(self, string):
        assert isinstance(string, str)
        attrs = json.loads(string)
        return attrs

    def processAttributes(self, objectData):
        ancestors = \
            objectData.getInheritanceAncestors() + \
            [objectData]

        palist = listUtils.filterUniqueTrue( map(
            lambda ancestor: ancestor.get('PA'),
            ancestors
        )) 

        self.registerMessage("palist: %s" % palist)

        for attrs in palist:
            try:
                decoded = self.decodeAttributes(attrs)
                for attr, val in decoded.items():
                    self.registerAttribute(objectData, attr, val)
            except Exception as e:
                self.registerError("could not decode attributes: %s | %s" % (attrs, e), objectData )

        if objectData.isVariation():
            parentData = objectData.getParent()
            assert parentData and parentData.isVariable()
            vattrs = self.decodeAttributes(objectData.get('VA'))
            assert vattrs
            for attr, val in vattrs.items():
                self.registerAttribute(parentData, attr, val, True)   
                self.registerAttribute(objectData, attr, val, True)   

    def processSpecials(self, objectData):
        schedule = objectData.get('SCHEDULE')
        if schedule:
            print "specials for %s: %s" % (objectData, schedule)
            splist = filter(None, findAllTokens(schedule))
            for special in splist:
                self.registerSpecial(objectData, special)

    def processObject(self, objectData):
        super(CSVParse_Woo, self).processObject(objectData)
        assert isinstance(objectData, ImportWooMixin)
        self.processCategories(objectData)
        if objectData.isProduct():
            catSKUs = map(lambda x: x.getCodesum(), objectData.getCategories().values())
            self.registerMessage("categories: {}".format(catSKUs))
        if objectData.isVariation():
            self.processVariation(objectData)
            self.registerMessage("variation of: {}".format(objectData.get('parent_SKU')))
        self.processAttributes(objectData)
        self.registerMessage("attributes: {}".format(objectData.getAttributes()))
        self.processImages(objectData)
        self.registerMessage("images: {}".format(objectData.getImages()))
        self.processSpecials(objectData)
        self.registerMessage("specials: {}".format(objectData.getSpecials()))


    def addDynRules(self, itemData, dynType, ruleIDs):
        rules = {
            'dprc':self.dprcRules, 
            'dprp':self.dprpRules
        }[dynType]
        dynListIndex = dynType+'list'
        dynIDListIndex = dynType+'IDlist'
        if not itemData.get(dynListIndex):
            itemData[dynListIndex]=[]
        if not itemData.get(dynIDListIndex):
            itemData[dynIDListIndex]=[]
        for ruleID in ruleIDs:
            if ruleID not in itemData[dynIDListIndex]:
                itemData[dynIDListIndex] = ruleID
            # print "adding %s to %s" % (ruleID, itemData['codesum'])
            rule = rules.get(ruleID)
            if rule: 
                if rule not in itemData[dynListIndex]:
                    itemData[dynListIndex].append(rule)
            else:
                self.registerError('rule should exist: %s'%ruleID, itemData)

    def postProcessDyns(self, objectData):
        self.registerMessage(objectData.getIndex())
        if objectData.isProduct():
            ancestors = objectData.getInheritanceAncestors() + [objectData]
            for ancestor in ancestors:
                # print "%16s is a member of %s" % (objectData['codesum'], ancestor['taxosum'])
                dprcString = ancestor.get('DYNCAT')
                if dprcString:
                    # print " -> DPRC", dprcString
                    dprclist = dprcString.split('|')
                    self.addDynRules(objectData, 'dprc', dprclist)
                dprpString = ancestor.get('DYNPROD')
                if dprpString:
                    # print " -> DPRP", dprpString
                    dprplist = dprpString.split('|')
                    self.addDynRules(objectData, 'dprp', dprplist)

            objectData['dprcsum'] = '<br/>'.join(
                filter( 
                    None,
                    map(
                        lambda x: x.toHTML(),
                        objectData.get( 'dprclist','')
                    )
                )
            )
            self.registerMessage("dprcsum of %s is %s"%(objectData.getIndex(), objectData.get('dprcsum')))

            objectData['dprpsum'] = '<br/>'.join(
                filter( 
                    None,
                    map(
                        lambda x: x.toHTML(),
                        objectData.get('dprplist','')
                    )
                )
            )
            self.registerMessage("dprpsum of %s is %s"%(objectData.getIndex(), objectData.get('dprpsum')))


    def postProcessCategories(self, objectData):
        self.registerMessage(objectData.getIndex())
        if objectData.isProduct():
            categories = objectData.getCategories().values()
            objectData['catsum'] = '|'.join(listUtils.filterUniqueTrue(
                map(
                    lambda x: x.getSum(),
                    categories
                )
            ))
            self.registerMessage("catsum of %s is %s"%(objectData.getIndex(), objectData.get('catsum')))

    def postProcessImages(self, objectData):
        self.registerMessage(objectData.getIndex())
        objectData['imgsum'] = '|'.join(filter(
            None, 
            objectData.getImages()
        ))

        # if objectData.isProduct() :
            # try:
            #     assert objectData['imgsum'], "All Products should have images"
            # except AssertionError as e:
            #     self.registerError(e, objectData)

        self.registerMessage("imgsum of %s is %s"%(objectData.getIndex(), objectData.get('imgsum')))

    def postProcessAttributes(self, objectData):
        self.registerMessage(objectData.getIndex())
        # print 'analysing attributes', objectData.get('codesum')

        for attr, data in objectData.getAttributes().items():
            if not data: continue
            values = '|'.join(map(str,data.get('values',[])))
            visible = data.get('visible', 1)
            variation = data.get('variation',0)
            position = data.get('position',0)
            default = data.get('default', '')

            self.registerMessage({
                'attr':attr,
                'values':values,
                'visible':visible,
                'variation':variation,
                'default':default
            })

            if objectData.isProduct():
                objectData['attribute:'+attr] = values
                objectData['attribute_data:'+attr] = '|'.join(map(str,[
                    position,
                    visible,
                    variation
                ]))
                objectData['attribute_default:'+attr] = default

            if objectData.isVariation():
                try:
                    assert variation == 1, "variations should have 'variation' set" 
                except Exception as e:
                    self.registerError(e, objectData)

                objectData['meta:attribute_'+attr] = values

    def postProcessSpecials(self, objectData):
        self.registerMessage(objectData.getIndex())

        if objectData.isProduct():

            ancestors = objectData.getInheritanceAncestors() + [objectData]
            for ancestor in ancestors:
                for special in ancestor.getSpecials():
                    objectData.registerSpecial(special)

            specials = objectData.getSpecials()
            objectData['spsum'] = '|'.join(specials)
            self.registerMessage("spsum of %s is %s"%(objectData.getIndex(), objectData.get('spsum')))


            for special in specials:
                # print "--> all specials: ", self.specials.keys()
                if special in self.specials.keys():
                    self.registerMessage( "special %s exists!" % special )

                    specialparams = self.specials[special]

                    specialfrom = datetotimestamp( specialparams["FROM"])
                    specialto = datetotimestamp(specialparams["TO"])
                    if( specialto < time.time() ):
                        self.registerMessage( "special %s is over" % special )
                        continue

                    self.registerMessage( "special %s is from %s to %s" % (special, specialfrom, specialto) )

                    for tier in ["RNS", "RPS", "WNS", "WPS", "DNS", "DPS"]:
                        discount = specialparams.get(tier)
                        if discount:
                            # print "discount is ", discount
                            special_price = None

                            percentages = findallPercent(discount)
                            # print "percentages are", percentages
                            if percentages:
                                coefficient = float(percentages[0]) / 100
                                regular_price_string = objectData.get(tier[:-1]+"R")
                                # print "regular_price_string", regular_price_string
                                if regular_price_string:
                                    regular_price = float(regular_price_string)
                                    special_price = regular_price * coefficient  
                            else:    
                                dollars = findallDollars(discount)
                                if dollars:
                                    dollar = float(self.sanitizeCell( dollars[0]) )
                                    if dollar:
                                        special_price = dollar

                            if special_price:
                                self.registerMessage( "special %s price is %s " % (special, special_price) )
                                tier_key = tier
                                tier_from_key = tier[:-1]+"F"
                                tier_to_key = tier[:-1]+"T"
                                for key, value in {
                                    tier_key: special_price,
                                    tier_from_key: specialfrom,
                                    tier_to_key: specialto
                                }.items():
                                    self.registerMessage( "special %s setting objectData[ %s ] to %s " % (special, key, value) )
                                    objectData[key] = value
                                # objectData[tier_key] = special_price
                                # objectData[tier_from_key] = specialfrom
                                # objectData[tier_to_key] = specialto

                else:
                    self.registerError("special %s does not exist " % special, objectData) 

            objectData['price'] = objectData.get('RNR')
            objectData['sale_price'] = objectData.get('RNS')
            objectData['sale_price_dates_from'] = objectData.get('RNF')
            objectData['sale_price_dates_to'] = objectData.get('RNT')


    def analyseFile(self, fileName):
        objects = super(CSVParse_Woo, self).analyseFile(fileName)  
        #post processing
        # for itemData in self.taxos.values() + self.items.values():
            # print 'POST analysing product', itemData.getCodesum(), itemData.getSum()
        
        for index, objectData in self.getObjects().items():
            print '%s POST' % objectData.getIdentifier()
            self.postProcessDyns(objectData)
            self.postProcessCategories(objectData)
            self.postProcessImages(objectData)
            self.postProcessAttributes(objectData)
            self.postProcessSpecials(objectData)

        return objects

    def getCategories(self):
        return self.categories
        # return self.flatten(self.categories.values())

    def getAttributes(self):
        return self.attributes
        # return self.flatten(self.attributes.values())

    def getVariations(self):
        return self.variations


class CSVParse_TT(CSVParse_Woo):
    """docstring for CSVParse_TT"""

    def __init__(self, cols={}, defaults ={}, importName="", \
                taxoSubs={}, itemSubs={}, taxoDepth=2, itemDepth=2, metaWidth=2,\
                dprcRules={}, dprpRules={}, specials={}):

        schema = "TT"

        extra_cols = [ 'RNRC', 'RPRC', 'WNRC', 'WPRC', 'DNRC', 'DPRC']
        extra_defaults    = OrderedDict([])
        extra_taxoSubs = OrderedDict([
            # ('TechnoTan After Care', 'Tan Care > After Care'),
            # ('TechnoTan Pre Tan', 'Tan Care > Pre Tan'),
            # ('TechnoTan Tan Enhancement', 'Tan Care > Tan Enhancement'),
            # ('TechnoTan Hair Care', 'Tan Care > Hair Care'),
            # ('TechnoTan Application Equipment', 'Equipment > Application Equipment'),
            # ('TechnoTan Tanning Booths', 'Equipment > Tanning Booths'),
            ('TechnoTan Literature', 'Marketing > Literature'),
            ('TechnoTan Signage', 'Marketing > Signage'),
            ('TechnoTan Spray Tanning Packages', 'Packages'),  
            # ('TechnoTan Solution', 'Solution'),
            # ('TechnoTan After Care', 'After Care'),
            # ('TechnoTan Pre Tan', 'Pre Tan'),
            # ('TechnoTan Tan Enhancement', 'Tan Enhancement'),
            # ('TechnoTan Hair Care', 'Hair Care'),
            # ('TechnoTan Tanning Accessories', 'Tanning Accessories'),
            # ('TechnoTan Technician Accessories', 'Technician Accessories'),
            # ('TechnoTan Application Equipment', 'Application Equipment'),
            # ('TechnoTan Tanning Booths', 'Tanning Booths'),
            # ('TechnoTan Apparel', 'Apparel'),
            ('TechnoTan ', ''),
        ])
        extra_itemSubs = OrderedDict()

        cols = listUtils.combineLists( cols, extra_cols )
        defaults = listUtils.combineOrderedDicts( defaults, extra_defaults )
        taxoSubs = listUtils.combineOrderedDicts( taxoSubs, extra_taxoSubs )
        itemSubs = listUtils.combineOrderedDicts( itemSubs, extra_itemSubs ) 
        super(CSVParse_TT, self).__init__( cols, defaults, schema, importName,\
                taxoSubs, itemSubs, taxoDepth, itemDepth, metaWidth, \
                dprcRules, dprpRules, specials) 
        if DEBUG_WOO:
            print "WOO initializing: "
            print "-> taxoDepth: ", self.taxoDepth
            print "-> itemDepth: ", self.itemDepth
            print "-> maxDepth: ", self.maxDepth
            print "-> metaWidth: ", self.metaWidth

class CSVParse_VT(CSVParse_Woo):
    """docstring for CSVParse_VT"""

    def __init__(self, cols={}, defaults ={}, importName="", \
                taxoSubs={}, itemSubs={}, taxoDepth=2, itemDepth=2, metaWidth=2,\
                dprcRules={}, dprpRules={}, specials={}):

        schema = "VT"

        extra_cols = [ 'RNRC', 'RPRC', 'WNRC', 'WPRC', 'DNRC', 'DPRC']
        extra_defaults    = OrderedDict([])
        extra_taxoSubs = OrderedDict([
            # ('VuTan After Care', 'Tan Care > After Care'),
            # ('VuTan Pre Tan', 'Tan Care > Pre Tan'),
            # ('VuTan Tan Enhancement', 'Tan Care > Tan Enhancement'),
            # ('VuTan Hair Care', 'Tan Care > Hair Care'),
            # ('VuTan Application Equipment', 'Equipment > Application Equipment'),
            # ('VuTan Tanning Booths', 'Equipment > Tanning Booths'),
            ('VuTan Literature', 'Marketing > Literature'),
            ('VuTan Signage', 'Marketing > Signage'),
            ('VuTan Spray Tanning Packages', 'Packages'),  
            # ('VuTan Solution', 'Solution'),
            # ('VuTan After Care', 'After Care'),
            # ('VuTan Pre Tan', 'Pre Tan'),
            # ('VuTan Tan Enhancement', 'Tan Enhancement'),
            # ('VuTan Hair Care', 'Hair Care'),
            # ('VuTan Tanning Accessories', 'Tanning Accessories'),
            # ('VuTan Technician Accessories', 'Technician Accessories'),
            # ('VuTan Application Equipment', 'Application Equipment'),
            # ('VuTan Tanning Booths', 'Tanning Booths'),
            # ('VuTan Apparel', 'Apparel'),
            ('VuTan ', ''),
        ])
        extra_itemSubs = OrderedDict()

        cols = listUtils.combineLists( cols, extra_cols )
        defaults = listUtils.combineOrderedDicts( defaults, extra_defaults )
        taxoSubs = listUtils.combineOrderedDicts( taxoSubs, extra_taxoSubs )
        itemSubs = listUtils.combineOrderedDicts( itemSubs, extra_itemSubs ) 
        super(CSVParse_VT, self).__init__( cols, defaults, schema, importName,\
                taxoSubs, itemSubs, taxoDepth, itemDepth, metaWidth, \
                dprcRules, dprpRules, specials) 
        if DEBUG_WOO:
            print "WOO initializing: "
            print "-> taxoDepth: ", self.taxoDepth
            print "-> itemDepth: ", self.itemDepth
            print "-> maxDepth: ", self.maxDepth
            print "-> metaWidth: ", self.metaWidth


if __name__ == '__main__':
    from coldata import ColData_Woo
    colData = ColData_Woo()

    print "Testing script..."
    inFolder = "../input/"
    genPath = inFolder + "generator.csv"

    outFolder = "../output/"
    prodPath = outFolder + 'products.csv'

    importName = time.strftime("%Y-%m-%d %H:%M:%S")

    # WooParser = CSVParse_TT(
    #     cols = colData.getImportCols(),
    #     defaults = colData.getDefaults(),
    #     importName = importName,
    #     taxoDepth = 3,
    # )
    # WooParser.analyseFile(genPath)

    # with open(prodPath, 'w+') as outFile:
    #     cols = ['rowcount', 'codesum', 'itemsum', 'descsum', 'attributes']
    #     dictwriter = csv.DictWriter(outFile, fieldnames=cols, extrasaction='ignore' )
    #     dictwriter.writeheader()
    #     dictwriter.writerows(WooParser.products.values())

    # sort_keys = lambda (ka, va), (kb, vb): cmp(ka, kb)

    # print "Categories:"
    # for key, category in sorted(WooParser.categories.items(), sort_keys):
    #     print "%15s | %s" % (category.get('codesum', ''), category.get('taxosum', ''))

    # print "Products:"
    # for product in WooParser.getProducts():
    #     print "%15s | %s" % (product.get('codesum', ''), product.get('itemsum', '')), product.get('dprplist')

    # print "Variations:"
    # for sku, variation in WooParser.variations.items():
    #     print "%15s | %s" % (sku, variation.get('itemsum', ''))

    # print "Attributes"
    # for attr, vals in WooParser.attributes.items():
    #     print "%15s | %s" % (attr[:15], "|".join(map(str,vals)))

    # for img, items in WooParser.images.items():
    #         print "%s " % img
    #         for item in items:
    #             print " -> (%4d) %15s " % (item['rowcount'], item['codesum'])




