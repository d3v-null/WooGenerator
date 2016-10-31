"""Introduces woo structure to shop classes"""
from utils import listUtils, SanitationUtils, TimeUtils, PHPUtils, Registrar, descriptorUtils
from csvparse_abstract import ObjList, CSVParse_Base
from csvparse_tree import ItemList, TaxoList, ImportTreeObject, ImportTreeItem
from csvparse_gen import CSVParse_Gen_Tree, CSVParse_Gen_Mixin
from csvparse_gen import ImportGenTaxo, ImportGenObject, ImportGenFlat, ImportGenItem, ImportGenMixin
from csvparse_shop import ImportShopMixin, ImportShopProductMixin, ImportShopProductSimpleMixin
from csvparse_shop import ImportShopProductVariableMixin, ImportShopProductVariationMixin
from csvparse_shop import ImportShopCategoryMixin, CSVParse_Shop_Mixin, ShopObjList
from csvparse_flat import CSVParse_Flat, ImportFlat
from coldata import ColData_Woo
from collections import OrderedDict
import time
import re

class WooProdList(ItemList):
    reportCols = ColData_Woo.getProductCols()

class WooCatList(TaxoList):
    reportCols = ColData_Woo.getCategoryCols()

class WooVarList(ItemList):
    reportCols = ColData_Woo.getVariationCols()

class ImportWooMixin(object):
    """ all things common to Woo import classes """

    wpidKey = 'ID'
    WPID = descriptorUtils.safeKeyProperty(wpidKey)
    titleKey = 'title'
    title = descriptorUtils.safeKeyProperty(titleKey)
    slugKey = 'slug'
    slug = descriptorUtils.safeKeyProperty(slugKey)
    verifyMetaKeys = [
        wpidKey,
        titleKey,
        slugKey
    ]

    def __init__(self, *args, **kwargs):
        if self.DEBUG_MRO:
            self.registerMessage('ImportWooMixin')
        super(ImportWooMixin, self).__init__(*args, **kwargs)
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

    def registerSpecial(self, special):
        if special not in self.specials:
            self.specials.append(special)

    def getSpecials(self):
        e = DeprecationWarning("use .specials instead of .getSpecials()")
        self.registerError(e)
        return self.specials

class ImportWooObject(ImportGenObject, ImportShopMixin, ImportWooMixin):
    container = ShopObjList

    verifyMetaKeys = ImportGenObject.verifyMetaKeys + ImportWooMixin.verifyMetaKeys

    def __init__(self, *args, **kwargs):
        if self.DEBUG_MRO:
            self.registerMessage('ImportWooObject')
        ImportGenObject.__init__(self, *args, **kwargs)
        ImportShopMixin.__init__(self, *args, **kwargs)
        ImportWooMixin.__init__(self, *args, **kwargs)
    # def __init__(self, *args, **kwargs):
    #     if self.DEBUG_MRO:
    #         self.registerMessage(' ')
    #     super(ImportWooObject, self).__init__(*args, **kwargs)
    #
    # @property
    # def verifyMetaKeys(self):
    #     superVerifyMetaKeys = super(ImportWooObject, self).verifyMetaKeys
    #     # superVerifyMetaKeys += ImportShopMixin.verifyMetaKeys
    #     superVerifyMetaKeys += ImportWooMixin.verifyMetaKeys
    #     return superVerifyMetaKeys

class ImportWooItem(ImportWooObject, ImportGenItem):
    verifyMetaKeys = ImportWooObject.verifyMetaKeys + ImportGenItem.verifyMetaKeys

    def __init__(self, *args, **kwargs):
        if self.DEBUG_MRO:
            self.registerMessage('ImportWooItem')
        ImportWooObject.__init__(self, *args, **kwargs)
        # ImportGenItem.__init__(self, *args, **kwargs)
    # def __init__(self, *args, **kwargs):
    #     if self.DEBUG_MRO:
    #         self.registerMessage(' ')
    #     super(ImportWooItem, self).__init__(*args, **kwargs)
    #
    # @property
    # def verifyMetaKeys(self):
    #     superVerifyMetaKeys = super(ImportWooItem, self).verifyMetaKeys
    #     # superVerifyMetaKeys += ImportGenItem.verifyMetaKeys
    #     return superVerifyMetaKeys

class ImportWooProduct(ImportWooItem, ImportShopProductMixin):
    isProduct = ImportShopProductMixin.isProduct
    nameDelimeter = ' - '

    def __init__(self, *args, **kwargs):
        if self.DEBUG_MRO:
            self.registerMessage('ImportWooProduct')
        ImportWooItem.__init__(self, *args, **kwargs)
        ImportShopProductMixin.__init__(self, *args, **kwargs)

    def processMeta(self):
        if self.DEBUG_MRO:
            self.registerMessage('ImportWooProduct')
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

class ImportWooProductSimple(ImportWooProduct, ImportShopProductSimpleMixin):
    product_type = ImportShopProductSimpleMixin.product_type

class ImportWooProductVariable(ImportWooProduct, ImportShopProductVariableMixin):
    isVariable = ImportShopProductVariableMixin.isVariable
    product_type = ImportShopProductVariableMixin.product_type

    def __init__(self, *args, **kwargs):
        if self.DEBUG_MRO:
            self.registerMessage('ImportWooProductVariable')
        ImportWooProduct.__init__(self, *args, **kwargs)
        ImportShopProductVariableMixin.__init__(self, *args, **kwargs)

class ImportWooProductVariation(ImportWooProduct, ImportShopProductVariationMixin):
    isVarition = ImportShopProductVariationMixin.isVariation
    product_type = ImportShopProductVariationMixin.product_type

class ImportWooProductComposite(ImportWooProduct):
    product_type = 'composite'

class ImportWooProductGrouped(ImportWooProduct):
    product_type = 'grouped'

class ImportWooProductBundled(ImportWooProduct):
    product_type = 'bundle'

class ImportWooTaxo(ImportWooObject, ImportGenTaxo):
    verifyMetaKeys = ImportWooObject.verifyMetaKeys + ImportGenTaxo.verifyMetaKeys

    def __init__(self, *args, **kwargs):
        if self.DEBUG_MRO:
            self.registerMessage('ImportWooTaxo')
        ImportWooObject.__init__(self, *args, **kwargs)
        # ImportGenTaxo.__init__(self, *args, **kwargs)
    # def __init__(self, *args, **kwargs):
    #     if self.DEBUG_MRO:
    #         self.registerMessage('ImportWooTaxo')
    #     super(ImportWooTaxo, self).__init__(*args, **kwargs)
    #
    # @property
    # def verifyMetaKeys(self):
    #     superVerifyMetaKeys = super(ImportWooTaxo, self).verifyMetaKeys
    #     # superVerifyMetaKeys += ImportGenTaxo.verifyMetaKeys
    #     return superVerifyMetaKeys

class ImportWooCategory(ImportWooTaxo, ImportShopCategoryMixin):
    isCategory = ImportShopCategoryMixin.isCategory
    isProduct = ImportShopCategoryMixin.isProduct

    def __init__(self, *args, **kwargs):
        if self.DEBUG_MRO:
            self.registerMessage('ImportWooCategory')
        ImportWooTaxo.__init__(self, *args, **kwargs)
        ImportShopCategoryMixin.__init__(self, *args, **kwargs)
        # super(ImportWooCategory, self).__init__(*args, **kwargs)
    # @property
    # def identifierDelimeter(self):
    #     return ImportWooObject.identifierDelimeter(self)

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

    @property
    def wooCatName(self):
        cat_layers = self.namesum.split(' > ')
        return cat_layers[-1]

    @property
    def index(self):
        return self.rowcount

    @property
    def identifier(self):
        identifier = super(ImportWooCategory, self).identifier
        return "|".join([
            self.codesum,
            'r:%s' % str(self.rowcount),
            'w:%s' % str(self.get(self.wpidKey)),
            self.wooCatName,
        ])

    @property
    def title(self):
        return self.wooCatName
    #
    # def __getitem__(self, key):
    #     if key == self.titleKey:
    #         return self.wooCatName
    #     else:
    #         return super(ImportWooCategory, self).__getitem__(key)


class CSVParse_Woo_Mixin(object):
    """ All the stuff that's common to Woo Parser classes """
    objectContainer = ImportWooObject

    def findCategory(self, searchData):
        response = None
        for key in [
            self.objectContainer.wpidKey,
            self.objectContainer.slugKey,
            self.objectContainer.titleKey,
            self.objectContainer.namesumKey,
        ]:
            value = searchData.get(key)
            if value:
                for category in self.categories.values():
                    if category.get(key) == value:
                        response = category
                        return response
        return response

    @classmethod
    def getTitle(cls, objectData):
        assert isinstance(objectData, ImportWooMixin)
        return objectData.title

    def getParserData(self, **kwargs):
        if Registrar.DEBUG_MRO:
            Registrar.registerMessage(' ')
        defaults = {
            self.objectContainer.wpidKey:'',
            self.objectContainer.slugKey:'',
            self.objectContainer.titleKey:''
        }
        # superData = super(CSVParse_Woo_Mixin, self).getParserData(**kwargs)
        # defaults.update(superData)
        # if self.DEBUG_PARSER:
            # self.registerMessage("PARSER DATA: %s" % repr(defaults))
        return defaults

    def clearTransients(self):
        pass

class CSVParse_Woo(CSVParse_Gen_Tree, CSVParse_Shop_Mixin, CSVParse_Woo_Mixin):
    objectContainer    = ImportWooObject
    itemContainer      = ImportWooItem
    productContainer   = ImportWooProduct
    taxoContainer      = ImportWooCategory
    simpleContainer    = ImportWooProductSimple
    variableContainer  = ImportWooProductVariable
    variationContainer = ImportWooProductVariation
    categoryContainer  = ImportWooCategory
    compositeContainer = ImportWooProductComposite
    groupedContainer  = ImportWooProductGrouped
    bundledContainer  = ImportWooProductBundled
    categoryIndexer = Registrar.getObjectRowcount

    do_specials = True
    do_dyns = True
    current_special = None
    specialsCategory = None
    add_special_categories = False



    @property
    def containers(self):
        return {
            'S': self.simpleContainer,
            'V': self.variableContainer,
            'I': self.variationContainer,
            'C': self.compositeContainer,
            'G': self.groupedContainer,
            'B': self.bundledContainer,
        }

    def __init__(self, cols, defaults, **kwargs):
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

        cols = listUtils.combineLists( cols, extra_cols )
        defaults = listUtils.combineOrderedDicts( defaults, extra_defaults )
        kwargs['taxoSubs'] = listUtils.combineOrderedDicts( kwargs.get('taxoSubs', {}), extra_taxoSubs )
        kwargs['itemSubs'] = listUtils.combineOrderedDicts( kwargs.get('itemSubs', {}), extra_itemSubs )
        # importName = kwargs.pop('importName', time.strftime("%Y-%m-%d %H:%M:%S") )
        if not kwargs.get('schema'):
            kwargs['schema'] = "TT"
        self.catMapping = listUtils.combineOrderedDicts( kwargs.pop('catMapping', {}), extra_catMaps )
        self.dprcRules = kwargs.pop('dprcRules', {})
        self.dprpRules = kwargs.pop('dprpRules', {})
        self.specials = kwargs.pop('specials', {})
        if not kwargs.get('metaWidth'): kwargs['metaWidth'] = 2
        if not kwargs.get('itemDepth'): kwargs['itemDepth'] = 2
        if not kwargs.get('taxoDepth'): kwargs['taxoDepth'] = 2

        super(CSVParse_Woo, self).__init__( cols, defaults, **kwargs)

        # self.categoryIndexer = self.productIndexer

        # if self.DEBUG_WOO:
        #     self.registerMessage("catMapping woo post: %s" % str(catMapping))

        # if self.DEBUG_WOO:
        #     print "WOO initializing: "
        #     print "-> taxoDepth: ", self.taxoDepth
        #     print "-> itemDepth: ", self.itemDepth
        #     print "-> maxDepth: ", self.maxDepth
        #     print "-> metaWidth: ", self.metaWidth

    def clearTransients(self):
        if self.DEBUG_MRO:
            self.registerMessage(' ')
        CSVParse_Gen_Tree.clearTransients(self)
        CSVParse_Shop_Mixin.clearTransients(self)
        CSVParse_Woo_Mixin.clearTransients(self)
        self.special_items = OrderedDict()
        self.updated_products = OrderedDict()
        self.updated_variations = OrderedDict()
        self.onspecial_products = OrderedDict()
        self.onspecial_variations = OrderedDict()

    def registerObject(self, objectData):
        CSVParse_Gen_Tree.registerObject(self, objectData)
        CSVParse_Shop_Mixin.registerObject(self, objectData)

    def getParserData(self, **kwargs):
        if self.DEBUG_MRO:
            self.registerMessage(' ')
        superData = {}
        for base_class in reversed(CSVParse_Woo.__bases__):
            if hasattr(base_class, 'getParserData'):
                superData.update(base_class.getParserData(self, **kwargs))
        # superData = CSVParse_Woo_Mixin.getParserData(self, **kwargs)
        # superData.update(CSVParse_Shop_Mixin.getParserData(self, **kwargs))
        # superData.update(CSVParse_Gen_Tree.getParserData(self, **kwargs))
        if self.DEBUG_PARSER:
            self.registerMessage("PARSER DATA: %s" % repr(superData))
        return superData

    def getNewObjContainer(self, *args, **kwargs):
        if self.DEBUG_MRO:
            self.registerMessage(' ')
        container = super(CSVParse_Woo, self).getNewObjContainer(*args, **kwargs)
        try:
            allData = args[0]
        except IndexError:
            e = UserWarning("allData not specified")
            self.registerError(e)
            raise e

        if issubclass(container, ImportTreeItem) \
        and self.schema in allData:
            woo_type = allData[self.schema]
            if woo_type:
                try:
                    container = self.containers[woo_type]
                except IndexError:
                    e = UserWarning("Unknown API product type: %s" % woo_type)
                    source = kwargs.get('rowcount')
                    self.registerError(e, source)
        if self.DEBUG_SHOP:
            self.registerMessage("container: {}".format(container.__name__))
        return container


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
                if ancestor.name and self.categoryIndexer(ancestor) not in self.categories:
                    self.registerCategory(ancestor)
                self.joinCategory(ancestor, objectData)

        if objectData.get('E'):
            if self.DEBUG_WOO:
                self.registerMessage("HAS EXTRA LAYERS")
            if objectData.isProduct:
                # self.registerMessage("ANCESTOR NAMESUM: %s" % str(objectData.getAncestorKey('namesum')))
                # self.registerMessage("ANCESTOR DESCSUM: %s" % str(objectData.getAncestorKey('descsum')))
                # self.registerMessage("ANCESTOR CATSUM: %s" % str(objectData.getAncestorKey('catsum')))
                # self.registerMessage("ANCESTOR ITEMSUM: %s" % str(objectData.getAncestorKey('itemsum')))
                # self.registerMessage("ANCESTOR TAXOSUM: %s" % str(objectData.getAncestorKey('taxosum')))
                # self.registerMessage("ANCESTOR NAME: %s" % str(objectData.getAncestorKey('name')))
                taxoAncestorNames = [ancestorData.get('name') for ancestorData in objectData.taxoAncestors]
                # self.registerMessage("TAXO ANCESTOR NAMES: %s" % str(taxoAncestorNames))

                # I'm so sorry for this code, it is utter horse shit but it works

                extraName = objectData.name
                extraName = re.sub(r' ?\([^\)]*\)', '', extraName)
                extraName = re.sub(r'1Litre', '1 Litre', extraName)
                extraTaxoName = ''
                if taxoAncestorNames:
                    if len(taxoAncestorNames) > 2:
                        extraTaxoName = taxoAncestorNames[-2]
                    else:
                        extraTaxoName = taxoAncestorNames[0]
                extraSuffix = 'Items'
                if re.search('Sample', extraName, flags=re.I):
                    extraSuffix = 'Samples'
                    extraName = re.sub(r' ?Samples?', '', extraName, flags=re.I)
                elif re.search('Trial Size', extraName, flags=re.I):
                    extraSuffix = 'Trial Sizes'
                    extraName = re.sub(r' ?Trial Sizes?', '', extraName, flags=re.I)
                elif re.search('10g', extraName, flags=re.I):
                    if re.search('Bronzing Powder', extraTaxoName, flags=re.I) \
                    or re.search('Foundation', extraTaxoName, flags=re.I):
                        extraSuffix = 'Jars'

                if re.search('Brushes', extraTaxoName, flags=re.I):
                    extraSuffix = ''
                    if re.search('Concealor', extraName, flags=re.I):
                        extraName += 's'
                        extraTaxoName = ''
                elif re.search('Kits', extraTaxoName, flags=re.I):
                    extraSuffix = ''
                elif re.search('Tan Care Kits', extraTaxoName, flags=re.I):
                    extraSuffix = 'Items'
                    extraTaxoName = ''
                elif re.search('Natural Soy Wax Candles', extraTaxoName, flags=re.I):
                    extraSuffix = ''
                    extraTaxoName = ''
                    if not extraName.endswith('s'):
                        extraName += 's'
                elif re.search('Shimmerz 4 Hair', extraTaxoName, flags=re.I):
                    extraTaxoName = 'Shimmerz'
                    if extraName.endswith('s'):
                        extraName = extraName[:-1]
                    extraSuffix = 'Packs'
                elif re.search('Hair Care', extraTaxoName, flags=re.I):
                    extraName = re.sub(' Sachet', '', extraName, flags=re.I)
                elif re.search('Tanbience Product Packs', extraTaxoName, flags=re.I):
                    extraTaxoName = ''


                extraDepth = self.taxoDepth - 1
                extraRowcount = objectData.rowcount
                extraStack = self.stack.getLeftSlice(extraDepth)
                extraName = ' '.join(filter(None, [extraName, extraTaxoName, extraSuffix]))
                extraName = SanitationUtils.stripExtraWhitespace(extraName)
                extraCode = objectData.code
                extraRow = objectData.row

                # print "SKU: %s" % objectData.codesum
                # print "-> EXTRA LAYER NAME: %s" % str(extraName)
                # print "-> EXTRA STACK: %s" % repr(extraStack)
                # print "-> EXTRA LAYER CODE: %s" % extraCode
                # print "-> EXTRA ROW: %s" % str(extraRow)

                # extraCodesum = (extraLayer).codesum

                siblings = extraStack.getTop().children
                # codeAncestors = [ancestor.code for ancestor in extraStack if ancestor.code ]
                # codeAncestors += [extraCode]
                # extraCodesum = ''.join(codeAncestors)

                # assert issubclass(type(extraLayer), ImportTreeObject), \
                    # "needs to subclass ImportTreeObject to do siblings"
                # siblings = getattr(extraLayer, 'siblings')
                # siblings = extraLayer.siblings
                extraLayer = None
                for sibling in siblings:
                    # print "sibling meta: %s" % repr(sibling.meta)
                    if sibling.name == extraName:
                        extraLayer = sibling
                    # if sibling.codesum == extraCodesum:
                    #     if sibling.rowcount != extraRowcount:
                    #         extraLayer = sibling
                    #         found_sibling = True
                    #         # if self.DEBUG_WOO: self.registerMessage("found sibling: %s"% extraLayer.index )
                    #         break

                if extraLayer:
                    if self.DEBUG_WOO: self.registerMessage("found sibling: %s"% extraLayer.identifier )
                else:
                    if self.DEBUG_WOO: self.registerMessage("did not find sibling: %s"% extraLayer.identifier )

                    extraLayer = self.newObject(
                        extraRowcount,
                        row=extraRow,
                        depth = extraDepth,
                        meta = [
                            extraName,
                            extraCode
                        ],
                        stack = extraStack
                    )

                    assert isinstance(extraLayer, ImportWooCategory )
                    # extraStack.append(extraLayer)
                    # print "-> EXTRA LAYER ANCESTORS: %s" % repr(extraLayer.ancestors)
                    if self.DEBUG_WOO:
                        self.registerMessage("extraLayer name: %s; type: %s" % (str(extraName), str(type(extraLayer))))
                    assert issubclass(type(extraLayer), ImportGenTaxo)
                    # assert issubclass(type(extraLayer), ImportGenMixin), \
                    #     "needs to subclass ImportGenMixin to do codesum"

                    self.registerCategory(extraLayer)

                self.joinCategory(extraLayer, objectData)


                # print "-> FINAL EXTRA LAYER: %s" % repr(extraLayer)

                # self.registerJoinCategory(extraLayer, objectData)
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
                                self.registerJoinCategory(result, member)

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
                    if self.DEBUG_WOO:
                        self.registerMessage( "special %s exists!" % special )

                    if not objectData.isVariable :

                        specialparams = self.specials[special]

                        specialfrom = specialparams.start_time
                        specialto = specialparams.end_time

                        if( not TimeUtils.hasHappenedYet(specialto) ):
                            if self.DEBUG_WOO:
                                self.registerMessage( "special %s is over: %s" % (special, specialto) )
                            continue
                        else:
                            specialfromString = TimeUtils.wpTimeToString(specialfrom)
                            specialtoString = TimeUtils.wpTimeToString(specialto)
                            if self.DEBUG_WOO:
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
                                    if self.DEBUG_WOO:
                                        self.registerMessage( "special %s price is %s " % (special, special_price) )
                                    tier_key = tier
                                    tier_from_key = tier[:-1]+"F"
                                    tier_to_key = tier[:-1]+"T"
                                    for key, value in {
                                        tier_key: special_price,
                                        tier_from_key: TimeUtils.localToServerTime( specialfrom),
                                        tier_to_key: TimeUtils.localToServerTime(specialto)
                                    }.items():
                                        if self.DEBUG_WOO:
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
                if isinstance(objectData, ImportShopProductVariationMixin):
                # if objectData.isVariation:
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
                            objectData.extraSpecialCategory
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
                if not objectData.get(key):
                    self.registerWarning("All products must have shipping: %s"%key, objectData)
                    break

    def postProcessPricing(self, objectData):
        if objectData.isProduct and not objectData.isVariable:
            for key in ['WNR']:
                if not objectData.get(key):
                    self.registerWarning("All products must have pricing: %s"%key, objectData)
                    break


    def analyseFile(self, fileName, encoding=None, limit=None):
        objects = super(CSVParse_Woo, self).analyseFile(fileName, encoding=encoding, limit=limit)
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
    def __init__(self, cols=None, defaults=None, **kwargs):
        if cols is None:
            cols = {}
        if defaults is None:
            defaults = {}
        # schema = "TT"

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

        # cols = listUtils.combineLists( cols, extra_cols )
        # defaults = listUtils.combineOrderedDicts( defaults, extra_defaults )
        # taxoSubs = listUtils.combineOrderedDicts( taxoSubs, extra_taxoSubs )
        # itemSubs = listUtils.combineOrderedDicts( itemSubs, extra_itemSubs )
        # catMapping = listUtils.combineOrderedDicts( catMapping, extra_catMaps )
        #
        #
        # super(CSVParse_TT, self).__init__( cols, defaults, schema, importName,\
        #         taxoSubs, itemSubs, taxoDepth, itemDepth, metaWidth, \
        #         dprcRules, dprpRules, specials, catMapping)

        #
        cols = listUtils.combineLists( cols, extra_cols )
        defaults = listUtils.combineOrderedDicts( defaults, extra_defaults )
        kwargs['taxoSubs'] = listUtils.combineOrderedDicts( kwargs.get('taxoSubs', {}), extra_taxoSubs )
        kwargs['itemSubs'] = listUtils.combineOrderedDicts( kwargs.get('itemSubs', {}), extra_itemSubs )
        kwargs['catMapping'] = listUtils.combineOrderedDicts( kwargs.get('catMapping', {}), extra_catMaps )
        kwargs['schema'] = "TT"
        # importName = kwargs.pop('importName', time.strftime("%Y-%m-%d %H:%M:%S") )
        super(CSVParse_TT, self).__init__( cols, defaults, **kwargs)

        # if self.DEBUG_WOO:
        #     self.registerMessage("catMapping: %s" % str(catMapping))
        # if self.DEBUG_WOO:
        #     print "WOO initializing: "
        #     print "-> taxoDepth: ", self.taxoDepth
        #     print "-> itemDepth: ", self.itemDepth
        #     print "-> maxDepth: ", self.maxDepth
        #     print "-> metaWidth: ", self.metaWidth

class CSVParse_VT(CSVParse_Woo):
    def __init__(self, cols=None, defaults=None, **kwargs):
        if cols is None:
            cols = {}
        if defaults is None:
            defaults = {}


        # schema = "VT"

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

        # cols = listUtils.combineLists( cols, extra_cols )
        # defaults = listUtils.combineOrderedDicts( defaults, extra_defaults )
        # taxoSubs = listUtils.combineOrderedDicts( taxoSubs, extra_taxoSubs )
        # itemSubs = listUtils.combineOrderedDicts( itemSubs, extra_itemSubs )
        # catMapping = listUtils.combineOrderedDicts( catMapping, extra_catMaps )
        #
        # self.registerMessage("catMapping: %s" % str(catMapping))
        #
        # super(CSVParse_VT, self).__init__( cols, defaults, schema, importName,\
        #         taxoSubs, itemSubs, taxoDepth, itemDepth, metaWidth, \
        #         dprcRules, dprpRules, specials, catMapping)
        #


        #
        cols = listUtils.combineLists( cols, extra_cols )
        defaults = listUtils.combineOrderedDicts( defaults, extra_defaults )
        kwargs['taxoSubs'] = listUtils.combineOrderedDicts( kwargs.get('taxoSubs', {}), extra_taxoSubs )
        kwargs['itemSubs'] = listUtils.combineOrderedDicts( kwargs.get('itemSubs', {}), extra_itemSubs )
        kwargs['catMapping'] = listUtils.combineOrderedDicts( kwargs.get('catMapping', {}), extra_catMaps )
        kwargs['schema'] = "VT"
        # importName = kwargs.pop('importName', time.strftime("%Y-%m-%d %H:%M:%S") )
        super(CSVParse_VT, self).__init__( cols, defaults, **kwargs)
