from csvparse_abstract import listUtils
from csvparse_tree import CSVParse_Tree, ImportTreeItem, ImportTreeTaxo, ImportTreeObject
from collections import OrderedDict
import functools
from itertools import chain
import re

DEBUG_GEN = True

class sanitationUtils:
    @staticmethod
    def compose(*functions):
        return functools.reduce(lambda f, g: lambda x: f(g(x)), functions)

    @staticmethod
    def removeLeadingDollarWhiteSpace(string):
        return re.sub('^\W*\$','', string)

    @staticmethod
    def removeLeadingPercentWhiteSpace(string):
        return re.sub('%\W*$','', string)

    @staticmethod
    def removeLoneDashes(string):
        return re.sub('^-$', '', string)

    @staticmethod
    def removeThousandsSeparator(string):
        return re.sub('(\d+),(\d{3})', '\g<1>\g<2>', string)

    @staticmethod
    def removeLoneWhiteSpace(string):
        return re.sub('^\s*$','', string)    

    @staticmethod
    def compileRegex(subs):
        if subs:
            return re.compile( "(%s)" % '|'.join(filter(None, map(re.escape, subs))) )
        else:
            return None

    @staticmethod
    def sanitizeCell(cell):
        return sanitationUtils.compose(
            sanitationUtils.removeLeadingDollarWhiteSpace,
            sanitationUtils.removeLeadingPercentWhiteSpace,
            sanitationUtils.removeLoneDashes,
            sanitationUtils.removeThousandsSeparator,
            sanitationUtils.removeLoneWhiteSpace
        )(cell)   

    @staticmethod
    def shorten(reg, subs, str_in):
        # if(DEBUG_GEN):
        #     print "calling shorten"
        #     print " | reg:", reg
        #     print " | subs:", subs
            # print " | str_i: ",str_in
        if not all([reg, subs, str_in]):
            str_out = str_in
        else:
            str_out = reg.sub(
                lambda mo: subs[mo.string[mo.start():mo.end()]],
                str_in
            )
        # if DEBUG_GEN: 
        #     print " | str_o: ",str_out
        return str_out

class ImportGenObject(ImportTreeObject):
    """docstring for ImportGenObject"""
    codeKey = 'code'
    nameKey = 'name'
    fullnameKey = 'fullname'
    descriptionKey = 'HTML description'
    codesumKey = 'codesum'
    descsumKey = 'descsum'

    def __init__(self, *args, **kwargs):
        subs = kwargs['subs']
        regex = kwargs['regex']
        self.subs = subs
        self.regex = regex
        super(ImportGenObject, self).__init__(*args, **kwargs)

    @classmethod
    def fromImportTreeObject(cls, objectData, regex, subs):
        assert isinstance(objectData, ImportTreeObject)
        row = objectData.getRow()
        rowcount = objectData.getRowcount()
        depth = objectData.getDepth()
        meta = objectData.getMeta()
        parent = objectData.getParent()
        return cls(objectData, rowcount, row, depth, meta, parent, regex, subs)

    def isProduct(self):
        return False

    def verifyMeta(self):
        keys = [
            self.codeKey,
            self.nameKey,
            self.fullnameKey,
            self.sumKey,
            self.codesumKey,
            self.descsumKey
        ]
        for key in keys:
            assert key in self.keys()
            # if key in self.keys():
            #     self.registerMessage("{} is set".format( key ) )
            # else:
            #     self.registerError("{} is not set".format( key ), "verifyMeta")

    def assertGet(self, key):
        assert key in self.keys(), "{} must be set before get".format(key)
        return self[key]

    def assertSet(self, key, value):
        assert type(value) == str, "{} must be set with string not {}".format(key, type(value))
        self[key] = value

    def getCode(self):              return self.assertGet(self.codeKey)
    def setCode(self, value):       return self.assertSet(self.codeKey, value)
    def getName(self):              return self.assertGet(self.nameKey)
    def setName(self, value):       return self.assertSet(self.nameKey, value) 
    def getFullname(self):          return self.assertGet(self.fullnameKey)
    def setFullname(self, value):   return self.assertSet(self.fullnameKey, value) 
    def getSum(self):               return self.assertGet(self.sumKey)
    def setSum(self, value):        return self.assertSet(self.sumKey, value)  
    def getCodesum(self):           return self.assertGet(self.codesumKey)
    def setCodesum(self, value):    return self.assertSet(self.codesumKey, value) 
    def getDescsum(self):           return self.assertGet(self.descsumKey)
    def setDescsum(self, value):    return self.assertSet(self.descsumKey, value) 

    def getDescription(self):
        return self.get(self.descriptionKey,"")

    def setDescription(self, value):
        assert type(value) == str
        self[self.descriptionKey] = value

    def getIndex(self):
        return self.getCodesum()

    def getCodeDelimeter(self):
        return ''

    def joinCodes(self):
        parent = self.getParent()
        codesum = self.getCode()
        if parent and not parent.isRoot():
            codesum = parent.getCodesum() + self.getCodeDelimeter() + codesum      
        return codesum

    def joinDescs(self):
        thisDescription = self.getDescription()
        if thisDescription: return thisDescription
        thisFullname = self.getFullname()
        if thisFullname: return thisFullname
        parent = self.getParent()
        if parent and not parent.isRoot():
            parentDescription = parent.getDescription()
            if parentDescription: return parentDescription
            parentFullname = parent.getFullname()
            if parentFullname: return parentFullname
        return ""

    def getNameDelimeter(self):
        return ' '

    def joinNames(self):
        ancestors = self.getItemAncestors() + [self]
        # self.registerMessage("ancestors: {}".format(ancestors ) )
        names = listUtils.filterUniqueTrue(map(lambda x: x.getName(), ancestors))
        # self.registerMessage("names: {}".format(names ) )
        nameDelimeter = self.getNameDelimeter()
        return nameDelimeter.join ( names )         

    def changeName(self, name):
        return sanitationUtils.shorten(self.regex, self.subs, name)

    def processMeta(self):

        meta = self.getMeta()
        try:
            self.setFullname( meta[0] )
        except:
            self.setFullname( "" )
        self.registerMessage("fullname: {}".format(self.getFullname() ) )

        try:
            self.setCode( meta[1] )
        except:
            self.setCode( "" )
        self.registerMessage("code: {}".format(self.getCode() ) )

        codesum = self.joinCodes()
        self.registerMessage("codesum: {}".format(codesum) )
        self.setCodesum(codesum)

        descsum = self.joinDescs()
        self.registerMessage("descsum: {}".format( descsum ) )
        self.setDescsum(descsum)   

        name = self.changeName(self.getFullname())
        self.registerMessage("name: {}".format(name ) )
        self.setName(name)

        nameSum = self.joinNames()
        self.registerMessage("nameSum: {}".format(nameSum) )
        self.setSum(nameSum)  

class ImportGenItem(ImportGenObject, ImportTreeItem):
    """docstring for ImportGenItem"""
    sumKey = 'itemsum'

    # def __init__(self, *args, **kwargs):
    #     super(ImportGenItem, self).__init__(*args, **kwargs)

    def getCodeDelimeter(self):
        parent = self.getParent()
        if not parent.isRoot() and parent.isTaxo():
            return '-'
        else:
            return super(ImportGenItem, self).getCodeDelimeter()

class ImportGenProduct(ImportGenItem):
    def isProduct(self):
        return True   

class ImportGenTaxo(ImportGenObject, ImportTreeTaxo):
    """docstring for ImportGenTaxo"""
    sumKey = 'taxosum'

    # def __init__(self, *args, **kwargs):
    #     super(ImportGenTaxo, self).__init__(*args, **kwargs)

    def joinNames(self):
        ancestors = self.getAncestors() + [self]
        # self.registerMessage("ancestors: {}".format(ancestors ) )
        names = listUtils.filterUniqueTrue(map(lambda x: x.getName(), ancestors))
        # self.registerMessage("names: {}".format(names ) )
        return ' > '.join(names)

class CSVParse_Gen(CSVParse_Tree):
    """docstring for CSVParse_Gen"""

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
            ('HTML description', ''),
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
        self.taxoRegex  = sanitationUtils.compileRegex(self.taxoSubs)
        self.itemRegex  = sanitationUtils.compileRegex(self.itemSubs)
        self.productIndexer = self.getGenCodesum
        # if DEBUG_GEN:
        #     print "GEN initializing: "
        #     print "-> taxoDepth: ", self.taxoDepth
        #     print "-> itemDepth: ", self.itemDepth
        #     print "-> maxDepth: ", self.maxDepth
        #     print "-> metaWidth: ", self.metaWidth


    def clearTransients(self):
        super(CSVParse_Gen, self).clearTransients()
        self.products   = OrderedDict() 

    def registerProduct(self, prodData):
        assert prodData.isProduct()
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
        if itemData.isProduct():
            self.registerProduct(itemData)

    def changeItem(self, item):
        return sanitationUtils.shorten(self.itemRegex, self.itemSubs, item)

    def changeFullname(self, item):
        subs = OrderedDict([(' \xe2\x80\x94 ', ' ')])
        return sanitationUtils.shorten(sanitationUtils.compileRegex(subs), subs, item)

    def depth(self, row):
        for i, cell in enumerate(row):
            if cell: 
                return i
            if i >= self.maxDepth: 
                return -1
        return -1

    def sanitizeCell(self, cell):
        return sanitationUtils.sanitizeCell(cell)  

    def getGenCodesum(self, genData):
        assert isinstance(genData, ImportGenObject)
        return genData.getCodesum()

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
