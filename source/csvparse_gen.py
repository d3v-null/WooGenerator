from collections import OrderedDict
from utils import descriptorUtils, SanitationUtils, listUtils
from csvparse_tree import CSVParse_Tree, ImportTreeItem, ImportTreeTaxo, ImportTreeObject
from csvparse_abstract import ObjList

class ImportGenObject(ImportTreeObject):

    _isProduct = False
    codeKey = 'code'
    nameKey = 'name'
    fullnameKey = 'fullname'
    descriptionKey = 'HTML Description'
    codesumKey = 'codesum'
    descsumKey = 'descsum'
    namesumKey = 'itemsum'
    fullnamesumKey = 'fullnamesum'

    code        = descriptorUtils.safeKeyProperty(codeKey)
    name        = descriptorUtils.safeKeyProperty(nameKey)
    fullname    = descriptorUtils.safeKeyProperty(fullnameKey)
    namesum     = descriptorUtils.safeKeyProperty(namesumKey)
    description = descriptorUtils.safeKeyProperty(descriptionKey)
    codesum     = descriptorUtils.safeKeyProperty(codesumKey)
    descsum     = descriptorUtils.safeKeyProperty(descsumKey)
    fullnamesum = descriptorUtils.safeKeyProperty(fullnamesumKey)

    def __init__(self, *args, **kwargs):
        subs = kwargs.get('subs')
        regex = kwargs.get('regex')
        if subs:
            self.subs = subs
        if regex:
            self.regex = regex
        super(ImportGenObject, self).__init__(*args, **kwargs)

    @classmethod
    def fromImportTreeObject(cls, objectData, regex, subs):
        assert isinstance(objectData, ImportTreeObject)
        row = objectData.row
        rowcount = objectData.rowcount
        depth = objectData.getDepth()
        meta = objectData.getMeta()
        parent = objectData.getParent()
        return cls(objectData, rowcount, row, depth, meta, parent, regex, subs)

    @property
    def isProduct(self): return self._isProduct

    def verifyMeta(self):
        keys = [
            self.codeKey,
            self.nameKey,
            self.fullnameKey,
            self.namesumKey,
            self.codesumKey,
            self.descsumKey,
            self.fullnamesumKey
        ]
        for key in keys:
            assert key in self.keys()
            # if key in self.keys():
            #     self.registerMessage("{} is set".format( key ) )
            # else:
            #     self.registerError("{} is not set".format( key ), "verifyMeta")

    @property
    def index(self):
        return self.codesum

    def getNameAncestors(self):
        return self.getAncestors()

    def getCodeDelimeter(self, other):
        return ''

    def joinCodes(self, ancestors):
        codeAncestors = [ancestor for ancestor in ancestors + [self] if ancestor.code ]
        if not codeAncestors:
            return ""
        prev = codeAncestors.pop(0)
        codesum = prev.code
        while codeAncestors:
            this = codeAncestors.pop(0)
            codesum += this.getCodeDelimeter(prev) + this.code
            prev = this
        return codesum

    def joinDescs(self, ancestors):
        self.registerMessage(u"given description: {}".format( self.description) )
        self.registerMessage(u"self: {}".format( self.items()) )
        if self.description:
            return self.description
        fullnames = [self.fullname]
        for ancestor in reversed(ancestors):
            ancestorDescription = ancestor.description
            if ancestorDescription:
                return ancestorDescription
            ancestorFullname = ancestor.fullname
            if ancestorFullname:
                fullnames.insert(0, ancestorFullname)
        if fullnames:
            return " - ".join(reversed(fullnames))
        else:
            return ""

    def getNameDelimeter(self):
        return ' '

    def joinNames(self, ancestors):
        ancestorsSelf = ancestors + [self]
        names = listUtils.filterUniqueTrue(map(lambda x: x.name, ancestorsSelf))
        nameDelimeter = self.getNameDelimeter()
        return nameDelimeter.join ( names )

    def joinFullnames(self, ancestors):
        ancestorsSelf = ancestors + [self]
        names = listUtils.filterUniqueTrue(map(lambda x: x.fullname, ancestorsSelf))
        nameDelimeter = self.getNameDelimeter()
        return nameDelimeter.join ( names )

    def changeName(self, name):
        return SanitationUtils.shorten(self.regex, self.subs, name)

    def processMeta(self):

        meta = self.getMeta()
        try:
            self.fullname =  meta[0]
        except:
            self.fullname =  ""
        # self.registerMessage("fullname: {}".format(self.fullname ) )

        try:
            self.code = meta[1]
        except:
            self.code = ""
        # self.registerMessage("code: {}".format(self.code ) )

        ancestors = self.getAncestors()

        codesum = self.joinCodes(ancestors)
        self.registerMessage(u"codesum: {}".format( codesum) )
        self.codesum = codesum

        descsum = self.joinDescs(ancestors)
        self.registerMessage(u"descsum: {}".format( descsum ) )
        self.descsum = descsum

        name = self.changeName(self.fullname)
        self.registerMessage(u"name: {}".format( name ) )
        self.name = name

        nameAncestors = self.getNameAncestors()

        namesum = self.joinNames(nameAncestors)
        self.registerMessage(u"namesum: {}".format( namesum) )
        self.namesum = namesum

        fullnamesum = self.joinFullnames(nameAncestors)
        self.registerMessage(u"fullnamesum: {}".format( fullnamesum) )
        self.fullnamesum = fullnamesum


class ImportGenItem(ImportGenObject, ImportTreeItem):

    def getNameAncestors(self):
        return self.getItemAncestors()

    def getCodeDelimeter(self, other):
        assert isinstance(other, ImportGenObject)
        if not other.isRoot and other.isTaxo:
            return '-'
        else:
            return super(ImportGenItem, self).getCodeDelimeter(other)

class ImportGenProduct(ImportGenItem):

    _isProduct = True

    def processMeta(self):
        super(ImportGenItem, self).processMeta()

        #process titles
        line1, line2 = SanitationUtils.titleSplitter( self.namesum )
        if not line2:
            nameAncestors = self.getNameAncestors()
            ancestorsSelf = nameAncestors + [self]
            names = listUtils.filterUniqueTrue(map(lambda x: x.name, ancestorsSelf))
            if len(names) < 2:
                line1 = names[0]
                nameDelimeter = self.getNameDelimeter()
                line2 = nameDelimeter.join(names[1:])
        self['title_1'] = line1
        self['title_2'] = line2

class GenProdList(ObjList):
    def addObject(self, objectData):
        assert issubclass(objectData.__class__, ImportGenProduct), \
        "object must be subclass of ImportGenProduct not %s : %s" % (
            SanitationUtils.coerceUnicode(objectData.__class__),
            SanitationUtils.coerceUnicode(objectData)
        )
        return super(GenProdList, self).addObject(objectData)

class ImportGenTaxo(ImportGenObject, ImportTreeTaxo):

    namesumKey = 'taxosum'
    namesum     = descriptorUtils.safeKeyProperty(namesumKey)

    def getNameDelimeter(self):
        return ' > '

class GenTaxoList(ObjList):
    def addObject(self, objectData):
        assert issubclass(objectData.__class__, ImportGenTaxo), \
        "object must be subclass of ImportGenTaxo not %s : %s" % (
            SanitationUtils.coerceUnicode(objectData.__class__),
            SanitationUtils.coerceUnicode(objectData)
        )
        return super(GenTaxoList, self).addObject(objectData)

class CSVParse_Gen(CSVParse_Tree):

    taxoContainer = ImportGenTaxo
    itemContainer = ImportGenItem
    productContainer = ImportGenProduct

    def __init__(self, cols, defaults, schema, \
                    taxoSubs={}, itemSubs={}, taxoDepth=2, itemDepth=2, metaWidth=2):
        assert metaWidth >= 2, "metaWidth must be greater than 2 for a GEN subclass"
        extra_defaults = OrderedDict([
            ('CVC', '0'),
            ('code', ''),
            ('name', ''),
            ('fullname', ''),
            ('description', ''),
            ('HTML Description', ''),
            ('imglist', [])
        ])
        extra_taxoSubs = OrderedDict([
            ('', ''),
        ])
        extra_itemSubs = OrderedDict([
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
        extra_cols = [schema]

        cols = listUtils.combineLists( cols, extra_cols )
        defaults = listUtils.combineOrderedDicts( defaults, extra_defaults )
        super(CSVParse_Gen, self).__init__( cols, defaults, taxoDepth, itemDepth, metaWidth)

        self.schema     = schema
        self.taxoSubs   = listUtils.combineOrderedDicts( taxoSubs, extra_taxoSubs )
        self.itemSubs   = listUtils.combineOrderedDicts( itemSubs, extra_itemSubs )
        self.taxoRegex  = SanitationUtils.compileRegex(self.taxoSubs)
        self.itemRegex  = SanitationUtils.compileRegex(self.itemSubs)
        self.productIndexer = self.getGenCodesum

        self.registerMessage("taxoDepth: {}".format(self.taxoDepth), 'CSVParse_Gen.__init__')
        self.registerMessage("itemDepth: {}".format(self.itemDepth), 'CSVParse_Gen.__init__')
        self.registerMessage("maxDepth: {}".format(self.maxDepth), 'CSVParse_Gen.__init__')
        self.registerMessage("metaWidth: {}".format(self.metaWidth), 'CSVParse_Gen.__init__')
        self.registerMessage("schema: {}".format(self.schema), 'CSVParse_Gen.__init__')


    def clearTransients(self):
        super(CSVParse_Gen, self).clearTransients()
        self.products   = OrderedDict()

    def registerProduct(self, prodData):
        assert prodData.isProduct
        self.registerAnything(
            prodData,
            self.products,
            indexer = self.productIndexer,
            singular = True,
            resolver = self.resolveConflict,
            registerName = 'products'
        )

    def registerItem(self, itemData):
        super(CSVParse_Gen, self).registerItem(itemData)
        if itemData.isProduct:
            self.registerProduct(itemData)

    def changeItem(self, item):
        return SanitationUtils.shorten(self.itemRegex, self.itemSubs, item)

    def changeFullname(self, item):
        subs = OrderedDict([(' \xe2\x80\x94 ', ' ')])
        return SanitationUtils.shorten(SanitationUtils.compileRegex(subs), subs, item)

    def depth(self, row):
        for i, cell in enumerate(row):
            if cell:
                return i
            if i >= self.maxDepth:
                return -1
        return -1

    def sanitizeCell(self, cell):
        return SanitationUtils.sanitizeCell(cell)

    def getGenCodesum(self, genData):
        assert isinstance(genData, ImportGenObject)
        return genData.codesum

    def getContainer(self, allData, **kwargs):
        container = super(CSVParse_Gen, self).getContainer( allData, **kwargs)
        if issubclass( container, ImportGenItem ):
            itemtype = allData.get(self.schema,'')
            self.registerMessage("itemtype: {}".format(itemtype))
            if itemtype in self.prod_containers.keys():
                container = self.prod_containers[itemtype]
        return container

    def getKwargs(self, allData, container, **kwargs):
        kwargs = super(CSVParse_Gen, self).getKwargs(allData, container, **kwargs)
        assert issubclass(container, ImportGenObject)
        if issubclass(container, self.taxoContainer):
            regex = self.taxoRegex
            subs = self.taxoSubs
        else:
            assert issubclass(container, self.itemContainer), "class must be item or taxo subclass not %s" % container.__name__
            regex = self.itemRegex
            subs = self.itemSubs
        kwargs['regex'] = regex
        kwargs['subs'] = subs
        for key in ['regex', 'subs']:
            assert kwargs[key] is not None
        return kwargs

    # def newObject(self, rowcount, row, **kwargs):
    #     return super(CSVParse_Gen, self).newObject(rowcount, row, **kwargs)

    def getProducts(self):
        self.registerMessage("returning products: {}".format(self.products.keys()))
        return self.products
