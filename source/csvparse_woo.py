"""Introduces woo structure to shop classes"""
from utils import listUtils, SanitationUtils, TimeUtils, PHPUtils, Registrar, descriptorUtils
from csvparse_abstract import ObjList, CSVParse_Base
from csvparse_tree import ItemList, TaxoList, ImportTreeObject
from csvparse_gen import CSVParse_Gen_Tree, ImportGenItem, ImportGenBase
from csvparse_gen import ImportGenTaxo, ImportGenObject
from csvparse_shop import ImportShop, ImportShopProduct, ImportShopProductSimple
from csvparse_shop import ImportShopProductVariable, ImportShopProductVariation
from csvparse_shop import ImportShopCategory, CSVParse_Shop_Mixin
from csvparse_flat import CSVParse_Flat, ImportFlat
from coldata import ColData_Woo
from collections import OrderedDict
import bisect
import time


class WooProdList(ItemList):
    reportCols = ColData_Woo.getProductCols()

class WooCatList(TaxoList):
    reportCols = ColData_Woo.getCategoryCols()

class WooVarList(ItemList):
    reportCols = ColData_Woo.getVariationCols()

class WooObjList(ObjList):
    def __init__(self, fileName, objects=None):
        self.fileName = fileName
        self.isValid = True
        if not self.fileName:
            self.isValid = False
        self.products = []
        self.items = []
        self.taxos = []
        super(WooObjList, self).__init__(objects)

    @property
    def objects(self):
        return self.products + self.items + self.taxos

    @property
    def name(self):
        e = DeprecationWarning(".name deprecated")
        self.registerError(e)
        raise e

    @property
    def title(self):
        return self.getKey('fullnamesum')

    @property
    def description(self):
        description = self.getKey('HTML Description')
        if not description:
            description = self.getKey('descsum')
        if not description:
            description = self.name
        return description

    # @property
    # def isValid(self):
    #     return self._isValid
    #
    # @property
    # def fileName(self):
    #     return self._fileName

    def append(self, objectData):
        assert isinstance(objectData, ImportWooObject)
        if objectData.isTaxo:
            container = self.taxos
        else:
            if objectData.isProduct:
                container = self.products
            else:
                assert objectData.isItem
                container = self.items

        if objectData not in container:
            bisect.insort(container, objectData)

    def invalidate(self, reason=""):
        if self.DEBUG_IMG:
            if not reason:
                reason = "IMG INVALID"
            self.registerError(reason, self.fileName)
        self.isValid = False

class ImportWooObject(ImportGenObject, ImportShop):
    container = WooObjList

    def __init__(self, *args, **kwargs):
        if self.DEBUG_MRO:
            self.registerMessage(' ')
        super(ImportWooObject, self).__init__(*args, **kwargs)
        self.images = []
        self.specials = []


    @property
    def isUpdated(self):
        return "Y" == SanitationUtils.normalizeVal(self.get('Updated', ""))

    @property
    def splist(self):
        schedule = self.get('SCHEDULE')
        if schedule:
            return filter(None, SanitationUtils.findAllTokens(schedule))
        else:
            return []

    def has_special(self, special):
        return special in map(SanitationUtils.normalizeVal, self.specials)

    def has_special_fuzzy(self, special):
        for sp in map(SanitationUtils.normalizeVal, self.specials):
            if special in sp:
                return True

    def registerImage(self, image):
        assert isinstance(image, (str, unicode))
        thisImages = self.images
        if image not in thisImages:
            thisImages.append(image)
            # parent = self.getParent()
            # parentImages = parent.getImages()
            # if not parentImages:
            #     parent.registerImage(image)

    def getImages(self):
        e = DeprecationWarning("use .images instead of .getImages()")
        self.registerError(e)
        return self.images

    def registerSpecial(self, special):
        if special not in self.specials:
            self.specials.append(special)

    def getSpecials(self):
        e = DeprecationWarning("use .specials instead of .getSpecials()")
        self.registerError(e)
        return self.specials

    @property
    def inheritenceAncestors(self):
        return self.ancestors

    def getInheritanceAncestors(self):
        e = DeprecationWarning("use .inheritenceAncestors insetad of .getInheritanceAncestors()")
        self.registerError(e)
        return self.inheritenceAncestors
        # return self.getAncestors()

class ImportWooItem(ImportWooObject, ImportGenItem):
    pass

class ImportWooProduct(ImportWooItem, ImportShopProduct):
    nameDelimeter = ' - '

    def processMeta(self):
        if self.DEBUG_MRO:
            self.registerMessage(' ')
        super(ImportWooProduct, self).processMeta()

        #process titles
        line1, line2 = SanitationUtils.titleSplitter( self.namesum )
        if not line2:
            nameAncestors = self.nameAncestors
            ancestorsSelf = nameAncestors + [self]
            names = listUtils.filterUniqueTrue(map(lambda x: x.name, ancestorsSelf))
            if names and len(names) < 2:
                line1 = names[0]
                nameDelimeter = self.nameDelimeter
                line2 = nameDelimeter.join(names[1:])

        self['title_1'] = line1
        self['title_2'] = line2

    def getNameDelimeter(self):
        e = DeprecationWarning("use .nameDelimeter insetad of .getNameDelimeter()")
        self.registerError(e)
        return self.nameDelimeter

    @property
    def inheritenceAncestors(self):
        return listUtils.filterUniqueTrue(
            self.categories.values() + super(ImportWooProduct, self).inheritenceAncestors
        )

    def getInheritanceAncestors(self):
        e = DeprecationWarning("use .inheritenceAncestors insetad of .getInheritanceAncestors()")
        self.registerError(e)
        return self.inheritenceAncestors
        # return listUtils.filterUniqueTrue(
        #     self.getCategories().values() + \
        #         super(ImportWooProduct, self).getInheritanceAncestors()
        # )

    @property
    def extraSpecialCategory(self):
        ancestorsSelf = self.taxoAncestors + [self]
        names = listUtils.filterUniqueTrue(map(lambda x: x.fullname, ancestorsSelf))
        return "Specials > " + names[0] + " Specials"

    def getExtraSpecialCategory(self):
        e = DeprecationWarning("use .extraSpecialCategory insetad of .getExtraSpecialCategory()")
        self.registerError(e)
        return self.extraSpecialCategory
        # ancestorsSelf = self.getTaxoAncestors() + [self]
        # names = listUtils.filterUniqueTrue(map(lambda x: x.fullname, ancestorsSelf))
        # return "Specials > " + names[0] + " Specials"

class ImportWooProductSimple(ImportWooProduct, ImportShopProductSimple):
    pass

class ImportWooProductVariable(ImportWooProduct, ImportShopProductVariable):
    pass

class ImportWooProductVariation(ImportWooProduct, ImportShopProductVariation):
    pass

class ImportWooProductComposite(ImportWooProduct):
    product_type = 'composite'

class ImportWooProductGrouped(ImportWooProduct):
    product_type = 'grouped'

class ImportWooProductBundled(ImportWooProduct):
    product_type = 'bundle'

class ImportWooCategory(ImportGenTaxo, ImportWooObject, ImportShopCategory):
    def findChildCategory(self, index):
        for child in self.children:
            if child.isCategory:
                if child.index == index:
                    return child
                else:
                    result = child.findChildCategory(index)
                    if result:
                        return result
        return None

class CSVParse_Woo(CSVParse_Gen_Tree, CSVParse_Shop_Mixin):
    itemContainer      = ImportWooItem
    productContainer   = ImportWooProduct
    taxoContainer      = ImportWooCategory

    containers = {
        'S': ImportWooProductSimple,
        'V': ImportWooProductVariable,
        'I': ImportWooProductVariation,
        'C': ImportWooProductComposite,
        'G': ImportWooProductGrouped,
        'B': ImportWooProductBundled,
    }

    do_images = True
    do_specials = True
    do_dyns = True
    current_special = None
    specialsCategory = None
    add_special_categories = False

    def __init__(self, cols, defaults, schema="", importName="", \
                taxoSubs={}, itemSubs={}, taxoDepth=2, itemDepth=2, metaWidth=2,\
                dprcRules={}, dprpRules={}, specials={}, catMapping={}):
        if self.DEBUG_MRO:
            self.registerMessage(' ')
        # print ("catMapping woo pre: %s" % str(catMapping))

        extra_cols = [ 'PA', 'VA', 'weight', 'length', 'width', 'height',
                    'stock', 'stock_status', 'Images', 'HTML Description',
                    'post_status']

        extra_defaults =  OrderedDict([
            # ('post_status', 'publish'),
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

        extra_catMaps = OrderedDict()

        # if not importName: importName = time.strftime("%Y-%m-%d %H:%M:%S")
        cols = listUtils.combineLists( cols, extra_cols )
        defaults = listUtils.combineOrderedDicts( defaults, extra_defaults )
        taxoSubs = listUtils.combineOrderedDicts( taxoSubs, extra_taxoSubs )
        itemSubs = listUtils.combineOrderedDicts( itemSubs, extra_itemSubs )
        catMapping = listUtils.combineOrderedDicts( catMapping, extra_catMaps )
        if not schema: schema = "TT"
        super(CSVParse_Woo, self).__init__( cols, defaults, schema, \
                taxoSubs, itemSubs, taxoDepth, itemDepth, metaWidth)
        self.dprcRules = dprcRules
        self.dprpRules = dprpRules
        self.specials = specials
        self.categoryIndexer = self.productIndexer
        self.catMapping = catMapping

        if self.DEBUG_WOO:
            self.registerMessage("catMapping woo post: %s" % str(catMapping))

        # if self.DEBUG_WOO:
        #     print "WOO initializing: "
        #     print "-> taxoDepth: ", self.taxoDepth
        #     print "-> itemDepth: ", self.itemDepth
        #     print "-> maxDepth: ", self.maxDepth
        #     print "-> metaWidth: ", self.metaWidth

    def clearTransients(self):
        if self.DEBUG_MRO:
            self.registerMessage(' ')
        super(CSVParse_Woo, self).clearTransients()
        # CSVParse_Shop_Mixin.clearTransients(self)
        self.images     = OrderedDict()
        self.special_items = OrderedDict()
        self.updated_products = OrderedDict()
        self.updated_variations = OrderedDict()
        self.onspecial_products = OrderedDict()
        self.onspecial_variations = OrderedDict()

    # def getNewObjContainer(self, *args, **kwargs):
    #     if self.DEBUG_MRO:
    #         self.registerMessage(' ')
    #     container = super(CSVParse_Woo, self).getNewObjContainer(*args, **kwargs)
    #     return container

    def registerImage(self, image, objectData):
        assert isinstance(image,(str,unicode))
        assert image is not ""
        if image not in self.images.keys():
            self.images[image] = WooObjList(image)
        self.images[image].append(objectData)
        objectData.registerImage(image)

    def registerSpecial(self, objectData, special):
        try:
            special = str(special)
            assert isinstance(special, (str, unicode)), 'Special must be a string not {}'.format(type(special).__name__)
            assert special is not '', 'Attribute must not be empty'
        except AssertionError as e:
            self.registerError("could not register special: {}".format(e))
        self.registerAnything(
            objectData,
            self.special_items,
            indexer=special,
            singular=False,
            registerName='specials'
        )
        objectData.registerSpecial(special)

    # def registerProduct(self, objectData):
    #     assert isinstance(objectData, ImportWooProduct)
    #     if not objectData.isVariation:
    #         super(CSVParse_Woo, self).registerProduct(objectData)

    def registerUpdatedProduct(self, objectData):
        assert \
            isinstance(objectData, ImportWooProduct), \
            "object should be ImportWooProduct not %s" % str(type(objectData))
        assert \
            not isinstance(objectData, ImportWooProductVariation), \
            "object should not be ImportWooProductVariation"
        self.registerAnything(
            objectData,
            self.updated_products,
            registerName='updated_products',
            singular=True
        )

    def registerUpdatedVariation(self, objectData):
        assert \
            isinstance(objectData, ImportWooProductVariation), \
            "object should be ImportWooProductVariation not %s" % str(type(objectData))
        self.registerAnything(
            objectData,
            self.updated_variations,
            registerName='updated_variations',
            singular=True
        )

    def registerCurrentSpecialProduct(self, objectData):
        assert \
            isinstance(objectData, ImportWooProduct), \
            "object should be ImportWooProduct not %s" % str(type(objectData))
        assert \
            not isinstance(objectData, ImportWooProductVariation), \
            "object should not be ImportWooProductVariation"
        self.registerAnything(
            objectData,
            self.onspecial_products,
            registerName='onspecial_products',
            singular=True
        )

    def registerCurrentSpecialVariation(self, objectData):
        assert \
            isinstance(objectData, ImportWooProductVariation), \
            "object should be ImportWooProductVariation not %s" % str(type(objectData))
        self.registerAnything(
            objectData,
            self.onspecial_variations,
            registerName='onspecial_variations',
            singular=True
        )


    def processImages(self, objectData):
        imglist = filter(None, SanitationUtils.findAllImages(objectData.get('Images','')))
        for image in imglist:
            self.registerImage(image, objectData)
        thisImages = objectData.images
        if objectData.isItem:
            ancestors = objectData.itemAncestors
        else:
            ancestors = []
        for ancestor in ancestors:
            ancestorImages = ancestor.images
            if len(thisImages) and not len(ancestorImages):
                self.registerImage(thisImages[0], ancestor)
            elif not len(thisImages) and len(ancestorImages):
                self.registerImage(ancestorImages[0], objectData)

    def processCategories(self, objectData):
        if objectData.isProduct:
            for ancestor in objectData.taxoAncestors:
                self.registerCategory(ancestor, objectData)

        if objectData.get('E'):
            if objectData.isProduct:
                extraDepth = self.taxoDepth - 1
                extraRowcount = objectData.rowcount
                extraStack = self.stack.getLeftSlice(extraDepth)
                extraLayer = self.newObject(
                    extraRowcount,
                    row=objectData.row,
                    depth = extraDepth,
                    meta = [
                        objectData.name + ' Items',
                        objectData.code
                    ],
                    stack = extraStack
                )
                if self.DEBUG_WOO:
                    self.registerMessage("extraLayer type: %s" % str(type(extraLayer)))
                # extraStack.append(extraLayer)
                assert issubclass(type(extraLayer), ImportGenBase), \
                    "needs to subclass ImportGenBase to do codesum"
                extraCodesum = (extraLayer).codesum
                assert issubclass(type(extraLayer), ImportTreeObject), \
                    "needs to subclass ImportTreeObject to do siblings"
                for sibling in extraLayer.siblings:
                    if sibling.codesum == extraCodesum:
                        if sibling.rowcount != extraRowcount:
                            extraLayer = sibling
                            self.registerMessage("found sibling: %s"% extraLayer.index )
                            break

                assert isinstance(extraLayer, ImportWooCategory )

                self.registerCategory(extraLayer, objectData)
            # todo maybe something with extra categories


    def processVariation(self, varData):
        assert varData.isVariation
        parentData = varData.parent
        assert parentData and parentData.isVariable
        self.registerVariation(parentData, varData)

    def processAttributes(self, objectData):
        ancestors = \
            objectData.inheritenceAncestors + \
            [objectData]

        palist = listUtils.filterUniqueTrue( map(
            lambda ancestor: ancestor.get('PA'),
            ancestors
        ))

        if self.DEBUG_WOO:
            self.registerMessage("palist: %s" % palist)

        for attrs in palist:
            try:
                decoded = SanitationUtils.decodeJSON(attrs)
                for attr, val in decoded.items():
                    self.registerAttribute(objectData, attr, val)
            except Exception as e:
                self.registerError("could not decode attributes: %s | %s" % (attrs, e), objectData )

        if objectData.isVariation:
            parentData = objectData.parent
            assert parentData and parentData.isVariable
            vattrs = SanitationUtils.decodeJSON(objectData.get('VA'))
            assert vattrs
            for attr, val in vattrs.items():
                self.registerAttribute(parentData, attr, val, True)
                self.registerAttribute(objectData, attr, val, True)

    def processSpecials(self, objectData):
        for special in objectData.splist:
            self.registerSpecial(objectData, special)

    def processObject(self, objectData):
        if self.DEBUG_MRO:
            self.registerMessage(' ')
        if self.DEBUG_WOO:
            self.registerMessage(objectData.index)
        super(CSVParse_Woo, self).processObject(objectData)
        assert issubclass(objectData.__class__, ImportWooObject), "objectData should subclass ImportWooObject not %s" % objectData.__class__.__name__
        self.processCategories(objectData)
        if objectData.isProduct:
            catSKUs = map(lambda x: x.codesum, objectData.categories.values())
            if self.DEBUG_WOO:
                self.registerMessage("categories: {}".format(catSKUs))
        if objectData.isVariation:
            self.processVariation(objectData)
            if self.DEBUG_WOO:
                self.registerMessage("variation of: {}".format(objectData.get('parent_SKU')))
        self.processAttributes(objectData)
        if self.DEBUG_WOO:
            self.registerMessage("attributes: {}".format(objectData.attributes))
        if self.do_images:
            self.processImages(objectData)
            if self.DEBUG_WOO:
                self.registerMessage("images: {}".format(objectData.images))
        if self.do_specials:
            self.processSpecials(objectData)
            if self.DEBUG_WOO:
                self.registerMessage("specials: {}".format(objectData.specials))


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
        # self.registerMessage(objectData.index)
        if objectData.isProduct:
            ancestors = objectData.inheritenceAncestors + [objectData]
            for ancestor in ancestors:
                # print "%16s is a member of %s" % (objectData['codesum'], ancestor['taxosum'])
                dprcString = ancestor.get('DYNCAT')
                if dprcString:
                    # print " -> DPRC", dprcString
                    dprclist = dprcString.split('|')
                    if self.DEBUG_WOO:
                        self.registerMessage("found dprclist %s"%(dprclist))
                    self.addDynRules(objectData, 'dprc', dprclist)
                dprpString = ancestor.get('DYNPROD')
                if dprpString:
                    # print " -> DPRP", dprpString
                    dprplist = dprpString.split('|')
                    if self.DEBUG_WOO:
                        self.registerMessage("found dprplist %s"%(dprplist))
                    self.addDynRules(objectData, 'dprp', dprplist)

            if(objectData.get( 'dprclist','')):
                objectData['dprcsum'] = '<br/>'.join(
                    filter(
                        None,
                        map(
                            lambda x: x.toHTML(),
                            objectData.get( 'dprclist','')
                        )
                    )
                )
                if self.DEBUG_WOO:
                    self.registerMessage("dprcsum of %s is %s"%(objectData.index, objectData.get('dprcsum')))

            if(objectData.get('dprplist','')):
                objectData['dprpsum'] = '<br/>'.join(
                    filter(
                        None,
                        map(
                            lambda x: x.toHTML(),
                            objectData.get('dprplist','')
                        )
                    )
                )
                if self.DEBUG_WOO:
                    self.registerMessage("dprpsum of %s is %s"%(objectData.index, objectData.get('dprpsum')))

                pricing_rules = {}
                for rule in objectData.get('dprplist', ''):
                    pricing_rules[PHPUtils.ruleset_uniqid()] = PHPUtils.unserialize(rule.to_pricing_rule())

                objectData['pricing_rules'] = PHPUtils.serialize(pricing_rules)


    def postProcessCategories(self, objectData):
        # self.registerMessage(objectData.index)
        if objectData.isCategory:
            if objectData.get('E'):
                # print objectData
                objectIndex = self.categoryIndexer(objectData)
                if objectIndex in self.catMapping.keys():
                    index = self.catMapping[objectIndex]
                    for ancestor in objectData.ancestors:
                        result = ancestor.findChildCategory(index)
                        if result:
                            for member in objectData.members.values():
                                self.registerCategory(result, member)

        if objectData.isProduct:
            categories = objectData.categories.values()
            objectData['catsum'] = '|'.join(listUtils.filterUniqueTrue(
                map(
                    lambda x: x.namesum,
                    categories
                )
            ))
            if self.DEBUG_WOO:
                self.registerMessage("catsum of %s is %s"%(objectData.index, objectData.get('catsum')))


    def postProcessImages(self, objectData):
        # self.registerMessage(objectData.index)
        objectData['imgsum'] = '|'.join(filter(
            None,
            objectData.images
        ))

        if self.do_images and objectData.isProduct and not objectData.isVariation:
            try:
                assert objectData['imgsum'], "All Products should have images"
            except AssertionError as e:
                self.registerWarning(e, objectData)

        if self.DEBUG_WOO:
            self.registerMessage("imgsum of %s is %s"%(objectData.index, objectData.get('imgsum')))

    def postProcessAttributes(self, objectData):
        # self.registerMessage(objectData.index)
        # print 'analysing attributes', objectData.get('codesum')

        for attr, data in objectData.attributes.items():

            if not data: continue
            values = '|'.join(map(str,data.get('values',[])))
            visible = data.get('visible', 1)
            variation = data.get('variation',0)
            position = data.get('position',0)
            default = data.get('default', '')

            if self.DEBUG_WOO:
                self.registerMessage(OrderedDict([
                    ('attr',attr),
                    ('values',values),
                    ('visible',visible),
                    ('variation',variation),
                    ('default',default)
                ]))

            if objectData.isProduct:
                objectData['attribute:'+attr] = values
                objectData['attribute_data:'+attr] = '|'.join(map(str,[
                    position,
                    visible,
                    variation
                ]))
                objectData['attribute_default:'+attr] = default

            if objectData.isVariation:
                if variation:
                    objectData['meta:attribute_'+attr] = values

    def postProcessSpecials(self, objectData):
        # self.registerMessage(objectData.index)

        if objectData.isProduct or objectData.isVariation:

            ancestors = objectData.inheritenceAncestors
            for ancestor in reversed(ancestors):
                ancestorSpecials = ancestor.specials
                for special in ancestorSpecials:
                    objectData.registerSpecial(special)

            specials = objectData.specials
            objectData['spsum'] = '|'.join(specials)
            if self.DEBUG_WOO:
                self.registerMessage("spsum of %s is %s"%(objectData.index, objectData.get('spsum')))

            for special in specials:
                # print "--> all specials: ", self.specials.keys()
                if special in self.specials.keys():
                    self.registerMessage( "special %s exists!" % special )

                    if not objectData.isVariable :

                        specialparams = self.specials[special]

                        specialfrom = specialparams.start_time
                        specialto = specialparams.end_time

                        if( not TimeUtils.hasHappenedYet(specialto) ):
                            self.registerMessage( "special %s is over: %s" % (special, specialto) )
                            continue
                        else:
                            specialfromString = TimeUtils.wpTimeToString(specialfrom)
                            specialtoString = TimeUtils.wpTimeToString(specialto)
                            self.registerMessage( "special %s is from %s (%s) to %s (%s)" % (special, specialfrom, specialfromString, specialto, specialtoString) )

                        for tier in ["RNS", "RPS", "WNS", "WPS", "DNS", "DPS"]:
                            discount = specialparams.get(tier)
                            if discount:
                                # print "discount is ", discount
                                special_price = None

                                percentages = SanitationUtils.findallPercent(discount)
                                # print "percentages are", percentages
                                if percentages:
                                    coefficient = float(percentages[0]) / 100
                                    regular_price_string = objectData.get(tier[:-1]+"R")
                                    # print "regular_price_string", regular_price_string
                                    if regular_price_string:
                                        regular_price = float(regular_price_string)
                                        special_price = regular_price * coefficient
                                else:
                                    dollars = SanitationUtils.findallDollars(discount)
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
                                        tier_from_key: TimeUtils.localToServerTime( specialfrom),
                                        tier_to_key: TimeUtils.localToServerTime(specialto)
                                    }.items():
                                        self.registerMessage( "special %s setting objectData[ %s ] to %s " % (special, key, value) )
                                        objectData[key] = value
                                    # objectData[tier_key] = special_price
                                    # objectData[tier_from_key] = specialfrom
                                    # objectData[tier_to_key] = specialto
                    break
                    #only applies first special

                else:
                    self.registerError("special %s does not exist " % special, objectData)

            for key, value in {
                'price': objectData.get('RNR'),
                'sale_price': objectData.get('RNS')
            }.items():
                if value is not None:
                    objectData[key] = value

            for key, value in {
                'sale_price_dates_from': objectData.get('RNF'),
                'sale_price_dates_to': objectData.get('RNT')
            }.items():
                if value is not None:
                    objectData[key] = TimeUtils.wpTimeToString(TimeUtils.serverToLocalTime(value))
            # objectData['price'] = objectData.get('RNR')
            # objectData['sale_price'] = objectData.get('RNS')
            # objectData['sale_price_dates_from'] = objectData.get('RNF')
            # objectData['sale_price_dates_to'] = objectData.get('RNT')

    def postProcessUpdated(self, objectData):
        objectData.inheritKey('Updated')

        if objectData.isProduct:
            if objectData.isUpdated:
                if objectData.isVariation:
                    self.registerUpdatedVariation(objectData)
                else:
                    self.registerUpdatedProduct(objectData)

    def postProcessInventory(self, objectData):
        objectData.inheritKey('stock_status')

        if objectData.isItem:
            stock = objectData.get('stock')
            if stock or stock is "0":
                objectData['manage_stock'] = 'yes'
                if stock is "0":
                    objectData['stock_status'] = 'outofstock'
            else:
                objectData['manage_stock'] = 'no'

            if objectData.get('stock_status') != 'outofstock':
                objectData['stock_status'] = 'instock'

    def postProcessVisibility(self, objectData):
        objectData.inheritKey('VISIBILITY')

        if objectData.isItem:
            visible = objectData.get('VISIBILITY')
            if visible is "hidden":
                objectData['catalog_visibility'] = "hidden"

    def postProcessCurrentSpecial(self, objectData):
        if objectData.isProduct:
            if objectData.has_special_fuzzy(self.current_special):
                # print ("%s matches special %s"%(str(objectData), self.current_special))
                if self.add_special_categories:
                    objectData['catsum'] = "|".join(
                        filter(None,[
                            objectData.get('catsum', ""),
                            self.specialsCategory,
                            objectData.getExtraSpecialCategory()
                        ])
                    )
                if objectData.isVariation:
                    self.registerCurrentSpecialVariation(objectData)
                else:
                    self.registerCurrentSpecialProduct(objectData)
            # else:
                # print ("%s does not match special %s | %s"%(str(objectData), self.current_special, str(objectData.splist)))

    def postProcessShipping(self, objectData):
        if objectData.isProduct and not objectData.isVariable:
            for key in ['weight', 'length', 'height', 'width']:
                if not objectData[key]:
                    self.registerWarning("All products must have shipping: %s"%key, objectData)
                    break

    def postProcessPricing(self, objectData):
        if objectData.isProduct and not objectData.isVariable:
            for key in ['WNR']:
                if not objectData[key]:
                    self.registerWarning("All products must have pricing: %s"%key, objectData)
                    break


    def analyseFile(self, fileName, encoding=None):
        objects = super(CSVParse_Woo, self).analyseFile(fileName, encoding)
        #post processing
        # for itemData in self.taxos.values() + self.items.values():
            # print 'POST analysing product', itemData.codesum, itemData.namesum

        for index, objectData in self.objects.items():
            # print '%s POST' % objectData.getIdentifier()
            if self.do_dyns:
                self.postProcessDyns(objectData)
            self.postProcessCategories(objectData)
            if self.do_images:
                self.postProcessImages(objectData)
            self.postProcessAttributes(objectData)
            if self.do_specials:
                self.postProcessSpecials(objectData)
            self.postProcessInventory(objectData)
            self.postProcessUpdated(objectData)
            self.postProcessVisibility(objectData)
            self.postProcessShipping(objectData)
            if self.specialsCategory and self.current_special:
                self.postProcessCurrentSpecial(objectData)

        return objects

    def getCategories(self):
        e = DeprecationWarning("use .categories instead of .getCategories()")
        self.registerError(e)
        return self.categories
        # return self.flatten(self.categories.values())

    def getAttributes(self):
        e = DeprecationWarning("use .attributes instead of .getAttributes()")
        self.registerError(e)
        return self.attributes
        # return self.flatten(self.attributes.values())

    def getVariations(self):
        e = DeprecationWarning("use .variations instead of .getVariations()")
        self.registerError(e)
        return self.variations


class CSVParse_TT(CSVParse_Woo):

    def __init__(self, cols={}, defaults ={}, importName="", \
                taxoSubs={}, itemSubs={}, taxoDepth=2, itemDepth=2, metaWidth=2,\
                dprcRules={}, dprpRules={}, specials={}, catMapping={}):

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

        extra_catMaps = OrderedDict([
            ('CTPP', 'CTKPP')
        ])

        cols = listUtils.combineLists( cols, extra_cols )
        defaults = listUtils.combineOrderedDicts( defaults, extra_defaults )
        taxoSubs = listUtils.combineOrderedDicts( taxoSubs, extra_taxoSubs )
        itemSubs = listUtils.combineOrderedDicts( itemSubs, extra_itemSubs )
        catMapping = listUtils.combineOrderedDicts( catMapping, extra_catMaps )


        super(CSVParse_TT, self).__init__( cols, defaults, schema, importName,\
                taxoSubs, itemSubs, taxoDepth, itemDepth, metaWidth, \
                dprcRules, dprpRules, specials, catMapping)

        if self.DEBUG_WOO:
            self.registerMessage("catMapping: %s" % str(catMapping))
        # if self.DEBUG_WOO:
        #     print "WOO initializing: "
        #     print "-> taxoDepth: ", self.taxoDepth
        #     print "-> itemDepth: ", self.itemDepth
        #     print "-> maxDepth: ", self.maxDepth
        #     print "-> metaWidth: ", self.metaWidth

class CSVParse_VT(CSVParse_Woo):
    def __init__(self, cols={}, defaults ={}, importName="", \
                taxoSubs={}, itemSubs={}, taxoDepth=2, itemDepth=2, metaWidth=2,\
                dprcRules={}, dprpRules={}, specials={}, catMapping={}):

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

        extra_catMaps = OrderedDict()

        cols = listUtils.combineLists( cols, extra_cols )
        defaults = listUtils.combineOrderedDicts( defaults, extra_defaults )
        taxoSubs = listUtils.combineOrderedDicts( taxoSubs, extra_taxoSubs )
        itemSubs = listUtils.combineOrderedDicts( itemSubs, extra_itemSubs )
        catMapping = listUtils.combineOrderedDicts( catMapping, extra_catMaps )

        self.registerMessage("catMapping: %s" % str(catMapping))

        super(CSVParse_VT, self).__init__( cols, defaults, schema, importName,\
                taxoSubs, itemSubs, taxoDepth, itemDepth, metaWidth, \
                dprcRules, dprpRules, specials, catMapping)
