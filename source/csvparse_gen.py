from csvparse_tree import CSVParse_Tree
from collections import OrderedDict
import functools
from itertools import chain
import re

DEBUG_GEN = False

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
        self.schema     = schema
        self.taxoSubs   = self.combineOrderedDicts( taxoSubs, extra_taxoSubs )
        self.itemSubs   = self.combineOrderedDicts( itemSubs, extra_itemSubs )   
        self.taxoRegex  = compileRegex(self.taxoSubs)
        self.itemRegex  = compileRegex(self.itemSubs)
        if DEBUG_GEN:
            print "GEN initializing: "
            print "-> taxoDepth: ", self.taxoDepth
            print "-> itemDepth: ", self.itemDepth
            print "-> maxDepth: ", self.maxDepth
            print "-> metaWidth: ", self.metaWidth

    def clearTransients(self):
        super(CSVParse_Gen, self).clearTransients()
        self.products   = OrderedDict()

    def getCodesum(self, itemData):
        try:
            index = itemData.get('codesum')
            assert index is not None, "index cannot be None"
            return index
        except:
            return super(CSVParse_Gen, self).getIndex(itemData)

    def getIndex(self, itemData):
        return self.getCodesum(itemData)

    def registerProduct(self, itemData):
        self.registerAnything(
            itemData, 
            self.products,
            self.getCodesum,
            singular = True,
            registerName = 'products'
        )

    def changeTaxo(self, taxo):
        return shorten(self.taxoRegex, self.taxoSubs, taxo)

    def changeItem(self, item):
        return shorten(self.itemRegex, self.itemSubs, item)

    def changeFullname(self, item):
        subs = OrderedDict([(' \xe2\x80\x94 ', ' ')])
        return shorten(compileRegex(subs), subs, item)

    def depth(self, row):
        for i, cell in enumerate(row):
            if cell: 
                return i
            if i >= self.maxDepth: 
                return -1
        return -1

    def sanitizeCell(self, cell):
        return compose(
            removeLeadingDollarWhiteSpace,
            removeLeadingPercentWhiteSpace,
            removeLoneDashes,
            removeThousandsSeparator,
            removeLoneWhiteSpace
        )(cell)     

    def retrieveStack(self, key, stack=None):
        if not stack: stack = self.stack
        vals = []
        for layer in stack:
            try:
                vals.append(layer[key])
            except (IndexError, KeyError):
                vals.append('')
        return vals

    def processMeta(self, itemData):
        meta = itemData.get('meta')
        if not meta: meta = [None]*self.metaWidth
        itemData['fullname'] = itemData['meta'][0]
        itemData['code'] = itemData['meta'][1]
        codes = self.retrieveStack('code')
        itemData['codesum'] = self.joinCodes(codes)
        super(CSVParse_Gen, self).processMeta(itemData)

    def processTaxo(self, itemData):
        itemData['name'] = self.changeTaxo(itemData['fullname'])
        names = []
        for name in self.retrieveStack('name'):
            if name not in names:
                names.append(name)
        itemData['taxosum'] = self.joinTaxos(names)
        super(CSVParse_Gen, self).processTaxo(itemData)

    def processItem(self, itemData):
        itemData['name'] = self.changeItem(itemData['fullname'])        
        names = self.retrieveStack('name')[self.taxoDepth:]
        # print "NAMES: ", names
        itemData['itemsum'] = self.joinItems(names)
        # print "ITEMSUM ", itemData['itemsum']
        super(CSVParse_Gen, self).processItem(itemData)

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
        itemData = super(CSVParse_Gen, self).analyseRow(row, itemData)
        if DEBUG_GEN: 
            print "GEN is analysing row: ", self.getSum(itemData)
            self.pp.pprint(itemData)

        fullnames, descs = \
            [self.retrieveStack(key) for key in ['fullname', 'HTML Description']]
        itemData['descsum'] = self.joinDescs(descs, fullnames)

        itemData['itemtype'] = itemData.get(self.schema,'')
        if itemData['itemtype']:
            self.processItemtype(itemData) 

        if DEBUG_GEN: 
            print "GEN finished analysing row: ", self.getSum(itemData)
            self.pp.pprint(itemData)

        return itemData

    def analyseFile(self, fileName):
        super(CSVParse_Tree, self).analyseFile(fileName)

    def flatten(self, values):
        return chain(*values)

    # def getItems(self):
    #     return self.flatten(self.items.values())

    # def getTaxos(self):
        # return self.taxos.values()
        # return self.flatten(self.taxos.values())

    def getProducts(self):
        return self.products.values()
