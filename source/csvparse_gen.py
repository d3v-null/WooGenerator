from csvparse_abstract import listUtils
from csvparse_tree import CSVParse_Tree, ImportTreeItem, ImportTreeTaxo, ImportTreeBase
from collections import OrderedDict
import functools
from itertools import chain
import re

DEBUG_GEN = True

class sanitationUtils:
    def compose(*functions):
        return functools.reduce(lambda f, g: lambda x: f(g(x)), functions)

    def removeLeadingDollarWhiteSpace(string):
        return re.sub('^\W*\$','', string)

    def removeLeadingPercentWhiteSpace(string):
        return re.sub('%\W*$','', string)

    def removeLoneDashes(string):
        return re.sub('^-$', '', string)

    def removeThousandsSeparator(string):
        return re.sub('(\d+),(\d{3})', '\g<1>\g<2>', string)

    def removeLoneWhiteSpace(string):
        return re.sub('^\s*$','', string)    

    def compileRegex(subs):
        if subs:
            return re.compile( "(%s)" % '|'.join(filter(None, map(re.escape, subs))) )
        else:
            return None

    def sanitizeCell(cell):
        return sanitationUtils.compose(
            sanitationUtils.removeLeadingDollarWhiteSpace,
            sanitationUtils.removeLeadingPercentWhiteSpace,
            sanitationUtils.removeLoneDashes,
            sanitationUtils.removeThousandsSeparator,
            sanitationUtils.removeLoneWhiteSpace
        )(cell)   

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

class ImportGenMixin(ImportTreeBase):
    """docstring for ImportGenMixin"""
    codeKey = 'code'
    nameKey = 'name'
    fullnameKey = 'fullname'
    descriptionKey = 'HTML description'
    codesumKey = 'codesum'
    descsumKey = 'descsum'
    isset = OrderedDict()

    def isProduct(self):
        return False

    def verifyMeta(self):
        assert all(map(
            lambda x: self.isset.get(x),
            [
                self.codeKey,
                self.nameKey,
                self.fullnameKey,
                self.sumKey,
                self.descriptionKey,
                self.codesumKey,
                self.descsumKey
            ]
        ))

    def assertGet(self, key):
        assert self.isset.get(key)
        return self[key]

    def assertSet(self, key, value):
        assert type(value) == str
        self[key] = value
        self.isset[key] = True

    def getCode(self):              return self.assertGet(self.codeKey)
    def setCode(self, value):       return self.assertSet(self.codeKey, value)
    def getName(self):              return self.assertGet(self.nameKey)
    def setName(self, value):       return self.assertSet(self.nameKey, value) 
    def getFullname(self):          return self.assertGet(self.fullnameKey)
    def setFullname(self, value):   return self.assertSet(self.fullnameKey, value) 
    def getSum(self):               return self.assertGet(self.sumKey)
    def setSum(self, value):        return self.assertSet(self.sumKey, value)  
    def getCodesum(self):           return self.assertGet(self.descsumKey)
    def setCodesum(self, value):    return self.assertSet(self.descsumKey, value) 
    def getDescsum(self):           return self.assertGet(self.descsumKey)
    def setDescsum(self, value):    return self.assertSet(self.descsumKey, value) 

    def getDescription(self):
        return self[self.descriptionKey]

    def setDescription(self, value):
        assert type(value) == str
        self[self.descriptionKey] = value

    def getCodeDelimeter(self):
        return ''

    def joinCodes(self):
        parent = self.getParent()
        codesum = self['code']
        if parent and not parent.isRoot():
            codesum = parent['codesum'] + self.getCodeDelimeter(parent) + codesum
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
        names = listUtils.filterUniqueTrue(map(lambda x: x.getName(), self.getItemAncestors()))
        nameDelimeter = self.getNameDelimeter()
        return nameDelimeter.join ( names )         

    def changeName(self, name):
        return sanitationUtils.shorten(self.regex, self.subs, name)

    def processMeta(self):
        meta = self.getMeta()
        try:
            self.setFullname( meta[0] )
        except:
            pass
        try:
            self.setCode( meta[1] )
        except:
            pass

        self.setCodesum(self.joinCodes())
        self.setDescsum(self.joinDescs())   
        self.setName(self.changeName(self.getFullname()))
        self.setSum(self.joinNames())  

class ImportGenItem(ImportTreeItem, ImportGenMixin):
    """docstring for ImportGenItem"""
    def __init__(self, data, rowcount, row, depth, meta=None, parent=None, regex=None, subs=None):
        self.subs = subs
        self.regex = regex
        super(ImportGenItem, self).__init__(self, data, rowcount, row, depth, meta, parent)

    def getCodeDelimeter(self):
        parent = self.getParent()
        if not parent.isRoot() and parent.isTaxo():
            return '-'
        else:
            return super(ImportGenItem, self).getCodeDelimeter(parent)

class importGenProduct(ImportGenItem):
    def isProduct(self):
        return True   

class ImportGenTaxo(ImportTreeTaxo, ImportGenMixin):
    """docstring for ImportGenTaxo"""
    sumKey = 'taxosum'

    def __init__(self, data, rowcount, row, depth, meta=None, parent=None, regex=None, subs=None):
        self.subs = subs
        self.regex = regex
        super(ImportGenTaxo, self).__init__(self, data, rowcount, row, depth, meta, parent)    

    def joinNames(self):
        names = listUtils.filterUniqueTrue(map(lambda x: x.getName(), self.getAncestors()))
        return ' > '.join(names)

class CSVParse_Gen(CSVParse_Tree):
    """docstring for CSVParse_Gen"""

    def __init__(self, cols, defaults, schema, \
                    taxoSubs={}, itemSubs={}, taxoDepth=2, itemDepth=2, metaWidth=2):
        assert metaWidth >= 2, "metaWidth must be greater than 2 for a GEN subclass"
        extra_defaults = OrderedDict([
            ('CVC', '0'),   
            ('code', ''),
            ('name', ''),
            ('fullname', ''),   
            ('description', ''),
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

        cols = self.combineLists( cols, extra_cols )
        defaults = self.combineOrderedDicts( defaults, extra_defaults )
        super(CSVParse_Gen, self).__init__( cols, defaults, taxoDepth, itemDepth, metaWidth)
        self.taxoContainer = ImportGenTaxo
        self.itemContainer = ImportGenItem
        self.productContainer = importGenProduct
        self.schema     = schema
        self.taxoSubs   = listUtils.combineOrderedDicts( taxoSubs, extra_taxoSubs )
        self.itemSubs   = listUtils.combineOrderedDicts( itemSubs, extra_itemSubs )   
        self.taxoRegex  = sanitationUtils.compileRegex(self.taxoSubs)
        self.itemRegex  = sanitationUtils.compileRegex(self.itemSubs)
        if DEBUG_GEN:
            print "GEN initializing: "
            print "-> taxoDepth: ", self.taxoDepth
            print "-> itemDepth: ", self.itemDepth
            print "-> maxDepth: ", self.maxDepth
            print "-> metaWidth: ", self.metaWidth


    def clearTransients(self):
        super(CSVParse_Gen, self).clearTransients()
        self.products   = OrderedDict()

    def getGenCodesum(self, genData):
        return genData.getCodesum() 

    def registerProduct(self, itemData):
        self.registerAnything(
            itemData, 
            self.products,
            self.getGenCodesum,
            singular = True,
            resolver = self.resolveConflict,
            registerName = 'products'
        )

    def registerObject(self, objectData):
        super(CSVParse_Gen, self).registerObject(objectData)
        if objectData.isProduct():
            self.registerProduct(objectData)

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

    def newObject(self, rowcount, row):
        objectData = super(CSVParse_Tree, self).newObject(rowcount, row)
        if objectData.isTaxo():
            regex = self.taxoRegex
            subs = self.taxoSubs
            container = self.taxoContainer
        else:
            assert objectData.isItem()
            regex = self.itemRegex
            subs = self.itemSubs
            container = self.itemContainer
        depth = objectData.getDepth()
        meta = objectData.getMeta()
        itemtype = objectData.get(self.schema,'')
        objectData['itemtype'] = itemtype
        if itemtype in self.prod_containers.keys():
            container = self.prod_containers[itemtype]
        return container(objectData, rowcount, row, depth, meta, regex, subs) 


    def getProducts(self):
        return self.products
