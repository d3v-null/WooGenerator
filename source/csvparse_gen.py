from csvparse_abstract import ImportObject
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
    fullnameKey = 'fullname'
    codeKey = 'code'
    descriptionKey = 'HTML description'
    codesumKey = 'codesum'

    def isProduct(self):
        return False

    def getFullname(self):
        assert self.FullnameSet
        return self[self.fullnameKey]

    def setFullname(self, value):
        assert type(value) == str
        self[self.fullnameKey] = value
        self.FullnameSet = True

    def getCode(self):
        assert self.CodeSet
        return self[self.codeKey]

    def setCode(self, value):
        assert type(value) == str 
        self[self.codeKey] = value
        self.codeSet = True

    def getDescription(self):
        return self[self.descriptionKey]

    def setDescription(self, value):
        assert type(value) == str
        self[self.descriptionKey] = value

    def getCodesum(self):
        return self[self.codesumKey]

    def setCodesum(self, value):
        assert type(value) == str
        self[self.codesumKey] = value

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

        self['codesum'] = self.joinCodes()
        self
        # ancestors = self.getAncestors()
        fullnames = self.getAncestorKey('fullname') + self['fullname']
        descs     = self.getAncestorKey('HTML description') + self['HTML description']


        # super(CSVParse_Gen, self).processMeta(objectData)
        # meta = objectData.getMeta()
        # if not meta: meta = [None]*self.metaWidth
        # objectData['fullname'] = meta[0]
        # objectData['code'] = meta[1]
        # codes = self.stack.retrieveKey('code')
        # objectData['codesum'] = self.joinCodes(codes)
        # fullnames, descs = \
        #     [self.stack.retrieveKey(key) for key in ['fullname', 'HTML Description']]
        # objectData['descsum'] = self.joinDescs(descs, fullnames)
        # if objectData.isItem():
        #     self.processItemMeta()        

class ImportGenItem(ImportTreeItem, ImportGenMixin):
    """docstring for ImportGenItem"""
    def __init__(self, *args):
        super(ImportGenItem, self).__init__(*args)

    def getCodeDelimeter(self):
        parent = self.getParent()
        if if not parent.isRoot() and parent.isTaxo():
            return '-'
        else:
            return super(ImportGenItem, self).getCodeDelimeter(parent)

    def getSum(self):
        return self.get('itemsum')  

class importGenProduct(ImportGenItem):
    def isProduct(self):
        return True   

class ImportGenTaxo(ImportTreeTaxo, ImportGenMixin):
    """docstring for ImportGenTaxo"""
    def __init__(self, *args):
        super(ImportGenTaxo, self).__init__(*args)     

    def getSum(self):
        return self.get('taxosum')        

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

        cols = self.combineLists( cols, extra_cols )
        defaults = self.combineOrderedDicts( defaults, extra_defaults )
        super(CSVParse_Gen, self).__init__( cols, defaults, taxoDepth, itemDepth, metaWidth)
        self.taxoContainer = ImportGenTaxo
        self.itemContainer = ImportGenItem
        self.productContainer = importGenProduct
        self.schema     = schema
        self.taxoSubs   = self.combineOrderedDicts( taxoSubs, extra_taxoSubs )
        self.itemSubs   = self.combineOrderedDicts( itemSubs, extra_itemSubs )   
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
            registerName = 'products'
        )

    def changeTaxo(self, taxo):
        return sanitationUtils.shorten(self.taxoRegex, self.taxoSubs, taxo)

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







    def processItemMeta(self, itemData):
        itemData['name'] = self.changeItem(itemData['fullname'])        
        names = self.stack.retrieveKey('name')[self.taxoDepth:]
        itemData['itemsum'] = self.joinItems(names)

        super(CSVParse_Gen, self).processItem(itemData)

    def processMeta(self, objectData):
        super(CSVParse_Gen, self).processMeta(objectData)
        meta = objectData.getMeta()
        if not meta: meta = [None]*self.metaWidth
        objectData['fullname'] = meta[0]
        objectData['code'] = meta[1]
        codes = self.stack.retrieveKey('code')
        objectData['codesum'] = self.joinCodes(codes)
        fullnames, descs = \
            [self.stack.retrieveKey(key) for key in ['fullname', 'HTML Description']]
        objectData['descsum'] = self.joinDescs(descs, fullnames)
        if objectData.isItem():
            self.processItemMeta()

    def processTaxo(self, itemData):
        super(CSVParse_Gen, self).processTaxo(itemData)
        itemData['name'] = self.changeTaxo(itemData['fullname'])
        names = []
        for name in self.stack.retrieveKey('name'):
            if name not in names:
                names.append(name)
        itemData['taxosum'] = self.joinTaxos(names)
        print "taxosum of ", itemData.getCodesum(), "is", itemData['taxosum']

    def joinCodes(self, codes):
        return '-'.join(filter (None, [
            ''.join(codes[:self.taxoDepth]),
            ''.join(codes[self.taxoDepth:])
        ]))

    def joinTaxos(self, names):
        return ' > '.join( filter( None, names[:self.taxoDepth]) )

    def joinItems(self, names):
        print "names: ", names
        return ' '.join ( filter( None, names ) )

    def joinDescs(self, descs, fullnames):
        pass

    def processItemType(self, itemData):
        pass

    def analyseRow(self, row, itemData):
        super(CSVParse_Gen, self).analyseRow(row, itemData)
        if DEBUG_GEN: 
            print "GEN is analysing row: ", itemData.getSum()

        fullnames, descs = \
            [self.stack.retrieveKey(key) for key in ['fullname', 'HTML Description']]
        itemData['descsum'] = self.joinDescs(descs, fullnames)

        itemData['itemtype'] = itemData.get(self.schema,'')

        if itemData['itemtype']:
            self.processItemtype(itemData) 

        if DEBUG_GEN: 
            print "GEN finished analysing row: ", itemData.getSum()


    def initializeObject(self, objectData):
        super(CSVParse_Gen, self).initializeObject(objectData)

    def newObject(self, rowcount, row):
        objectData = super(CSVParse_Tree, self).newObject(rowcount, row)
        depth = objectData.getDepth()
        meta = objectData.getMeta()
        itemtype = objectData.get(self.schema,'')
        objectData['itemtype'] = itemtype
        if itemtype in self.product_types.keys():
            container = self.product_types[itemtype]
            return container(objectData, rowcount, row, depth, meta) 
        else:
            return objectData

    # def analyseObject(self, objectData):
    #     super(CSVParse_Gen, self).analyseObject(objectData)

    def getProducts(self):
        return self.products
