# from __future__ import absolute_import
from collections import OrderedDict
from utils import listUtils, Registrar #, debugUtils
import json

class ColData_Base(object):
    data = OrderedDict()

    def __init__(self, data):
        super(ColData_Base, self).__init__()
        assert issubclass(type(data), dict), "Data should be a dictionary subclass"
        self.data = data

    @classmethod
    def getImportCols(cls):
        imports = []
        for col, data in cls.data.items():
            if data.get('import', False):
                imports.append(col)
        return imports

    @classmethod
    def getDefaults(cls):
        defaults = {}
        # Registrar.registerMessage('called with class: '+ unicode(cls) + ', data=' + unicode(cls.data))
        for col, data in cls.data.items():
            # Registrar.registerMessage('col is %s' % col)
            if 'default' in data:
                # Registrar.registerMessage('has default')
                defaults[col] = data.get('default')
            else:
                pass
                # Registrar.registerMessage('does not have default')
        return defaults

    @classmethod
    def getExportCols(cls, schema=None):
        if not schema: return None
        exportCols = OrderedDict()
        for col, data in cls.data.items():
            if data.get(schema, ''):
                exportCols[col] = data
        return exportCols

    @classmethod
    def getBasicCols(self):
        return self.getExportCols('basic')

    @classmethod
    def getDeltaCols(self):
        cols = OrderedDict()
        for col, data in self.data.items():
            if data.get('delta'):
                cols[col] = self.deltaCol(col)
        return cols

    @classmethod
    def getColNames(cls, cols):
        colNames = OrderedDict()
        for col, data in cols.items():
            label = data.get('label','')
            colNames[col] = label if label else col
        return colNames

    @classmethod
    def nameCols(cls, cols):
        return OrderedDict(
            [(col, {}) for col in cols]
        )


    @classmethod
    def getReportCols(cls):
        return cls.getExportCols('report')

    @classmethod
    def getWPAPICols(cls):
        return cls.getExportCols('wp-api')

    @classmethod
    def getWPAPIVariableCols(cls):
        cols = OrderedDict()
        for col, data in cls.getWPAPICols().items():
            if 'sync' in data:
                if data.get('sync') == 'simple_only':
                    continue
            cols[col] = data
        return cols


    @classmethod
    def getWPAPICoreCols(cls):
        exportCols = cls.getExportCols('wp-api')
        apiCols = OrderedDict()
        for col, data in exportCols.items():
            apiData = data.get('wp-api', {})
            if hasattr(apiData, '__getitem__') \
            and not apiData.get('meta'):
                apiCols[col] = data

        return apiCols

    @classmethod
    def getWPAPIMetaCols(cls):
        exportCols = cls.getExportCols('wp-api')
        apiCols = OrderedDict()
        for col, data in exportCols.items():
            apiData = data.get('wp-api', {})
            if hasattr(apiData, '__getitem__') \
            and apiData.get('meta'):
                apiCols[col] = data
        return apiCols

    @classmethod
    def getSyncCols(self):
        return self.getExportCols('sync')

    @classmethod
    def deltaCol(self, col):
        return 'Delta ' + col

class ColData_Prod(ColData_Base):
    data = OrderedDict([
        ('codesum', {
            'label': 'SKU',
            'product':True,
            'report':True
        }),
        ('itemsum', {
            'label': 'Name',
            'product':True,
            'report':True
        }),
        ('descsum', {
            'label': 'Description',
            'product': True,
            'report':True,
        }),
        ('WNR', {
            'product':True,
            'report':True,
            'pricing':True,
        }),
        ('RNR', {
            'product':True,
            'report':True,
            'pricing':True,
        }),
        ('DNR', {
            'product':True,
            'report':True,
            'pricing':True,
        }),
        ('weight', {
            'import': True,
            'product': True,
            'variation': True,
            'shipping': True,
            'wp':{
                'key':'_weight',
                'meta':True
            },
            'wp-api':True,
            'sync':True,
            'report':True
        }),
        ('length', {
            'import': True,
            'product': True,
            'variation': True,
            'shipping':True,
            'wp':{
                'key':'_length',
                'meta':True
            },
            'sync':True,
            'report':True
        }),
        ('width', {
            'import': True,
            'product': True,
            'variation': True,
            'shipping': True,
            'wp':{
                'key':'_width',
                'meta':True
            },
            'sync':True,
            'report':True
        }),
        ('height', {
            'import': True,
            'product': True,
            'variation': True,
            'shipping': True,
            'wp':{
                'key':'_height',
                'meta':True
            },
            'sync':True,
            'report':True
        }),
    ])

class ColData_MYO(ColData_Prod):

    data = OrderedDict(ColData_Prod.data.items() + [
        ('codesum', {
            'label': 'Item Number',
            'product':True,
        }),
        ('itemsum', {
            'label': 'Item Name',
            'product':True,
            'report':True,
        }),
        ('WNR', {
            'label': 'Selling Price',
            'import': True,
            'product': True,
            'pricing': True,
        }),
        ('RNR', {
            'label': 'Price Level B, Qty Break 1',
            'import': True,
            'product': True,
            'pricing': True,
        }),
        ('DNR', {
            'label': 'Price Level C, Qty Break 1',
            'import': True,
            'product': True,
            'pricing': True,
        }),
        ('CVC', {
            'label': 'Custom Field 1',
            'product': True,
            'import': True,
            'default': 0
        }),
        ('descsum', {
            'label': 'Description',
            'product': True,
            'report':True,
        }),
        ('HTML Description', {
            'import': True,
        }),
        ('Sell', {
            'default':'S',
            'product':True,
        }),
        ('Tax Code When Sold', {
            'default':'GST',
            'product': True,
        }),
        ('Sell Price Inclusive', {
            'default':'X',
            'product':True,
        }),
        ('Income Acct', {
            'default':'41000',
            'product':True,
        }),
        ('Inactive Item', {
            'default':'N',
            'product':True,
        }),
        ('use_desc', {
            'label':'Use Desc. On Sale',
            'default':'X',
            'product':True
        })
    ])

    def __init__(self, data=None):
        if not data: data = self.data
        super(ColData_MYO, self).__init__(data)

    @classmethod
    def getProductCols(self):
        return self.getExportCols('product')

class ColData_Woo(ColData_Prod):

    data = OrderedDict(ColData_Prod.data.items() + [
        ('ID', {
            'wp':{
                'key': 'ID',
                'meta': False
            },
            'wp-api':{
                'key':'id'
            },
            'report':True
        }),
        ('parent_SKU', {
            'variation':True,
        }),
        ('codesum', {
            'label':'SKU',
            'tag':'SKU',
            'product': True,
            'variation': True,
            'category': True,
            'wp':{
                'key':'_sku',
                'meta':True
            },
            'wp-api':{
                'key':'sku'
            },
            'report':True,
            'sync':True
        }),
        ('itemsum', {
            'tag':'Title',
            'label':'post_title',
            'product':True,
            'variation': True,
            'wp':{
                'key':'post_title',
                'meta':False
            },
            'wp-api':{
                'key':'name',
                'meta':False
            },
            'report':True,
            'sync':'simple_only'
        }),
        ('title_1', {
            'label': 'meta:title_1',
            'product':True,
            'wp':{
                'key':'title_1',
                'meta':True
            }
        }),
        ('title_2', {
            'label': 'meta:title_2',
            'product':True,
            'wp':{
                'key':'title_2',
                'meta':True
            }
        }),
        ('taxosum', {
            'label':'category_title',
            'category':True,
        }),
        ('catlist', {
            'wp-api':{
                'key':'categories'
            },
            # 'sync':'simple_only'
        }),
        ('prod_type', {
            'label':'tax:product_type',
            'product':True,
            'wp-api':{
                'key':'type'
            }
        }),
        ('catsum', {
            'label':'tax:product_cat',
            'product':True,
        }),
        ('descsum', {
            'label':'post_content',
            'tag':'Description',
            'product': True,
            'category': True,
            'wp-api':{
                'key':'description'
            },
            'sync':'simple_only'
        }),
        ('imgsum', {
            'label':'Images',
            'product': True,
            'variation': True,
            'category': True,
        }),
        ('rowcount', {
            'label':'menu_order',
            'product': True,
            'category': True,
            'variation': True,
            'wp-api':{
                'key':'menu_order'
            },
            # 'sync':True
        }),
        ('PA', {
            'import': True
        }),
        ('VA', {
            'import': True
        }),
        ('D', {
            'label': 'meta:wootan_danger',
            'import': True,
            'product': True,
            'variation': True,
            'shipping': True,
            'wp-api':{
                'key':'wootan_danger',
                'meta':True
            },
            'sync':True
        }),
        ('E', {
            'import': True,
        }),
        ('DYNCAT', {
            'import':True,
            'category': True,
            'product':True,
            'pricing': True,
        }),
        ('DYNPROD', {
            'import':True,
            'category': True,
            'product':True,
            'pricing': True,
        }),
        ('VISIBILITY', {
            'import':True,
        }),
        ('catalog_visibility', {
            'product':True,
            'default':'visible'
        }),
        ('SCHEDULE', {
            'import':True,
            'category':True,
            'product':True,
            'pricing': True,
            'default':''
        }),
        ('spsum', {
            'tag': 'active_specials',
            'product':True,
            'variation':True,
            'pricing':True,
        }),
        ('dprclist', {
            'label': 'meta:dynamic_category_rulesets',
            # 'pricing': True,
            # 'product': True,
            # 'category': True
        }),
        ('dprplist', {
            'label': 'meta:dynamic_product_rulesets',
            # 'pricing': True,
            # 'product': True,
            # 'category': True
        }),
        ('dprcIDlist', {
            'label': 'meta:dynamic_category_ruleset_IDs',
            'pricing': True,
            'product': True,
            # 'category': True
        }),
        ('dprpIDlist', {
            'label': 'meta:dynamic_product_ruleset_IDs',
            'product': True,
            'pricing': True,
            # 'category': True
        }),
        ('dprcsum', {
            'label': 'meta:DPRC_Table',
            'product': True,
            'pricing': True,
        }),
        ('dprpsum', {
            'label': 'meta:DPRP_Table',
            'product': True,
            'pricing': True,
        }),
        ('pricing_rules', {
            'label': 'meta:_pricing_rules',
            'pricing':True,
            'wp':{
                'key':'pricing_rules',
                'meta':False
            },
            'product':True,
        }),
        ('price', {
            'label':'regular_price',
            'product': True,
            'variation': True,
            'pricing': True,
            'wp':{
                'key':'_regular_price',
                'meta':True
            },
            'wp-api':{
                'key':'regular_price'
            },
            'report':True
        }),
        ('sale_price', {
            'label':'sale_price',
            'product': True,
            'variation': True,
            'pricing': True,
            'wp':{
                'key':'_sale_price',
                'meta':True
            },
            'wp-api':True,
            'report':True
        }),
        ('sale_price_dates_from', {
            'label':'sale_price_dates_from',
            'tag':'sale_from',
            'product': True,
            'variation': True,
            'pricing': True,
            'wp':{
                'key':'_sale_price_dates_from',
                'meta':True
            },
            'wp-api':{
                'key':'regular_price'
            },
        }),
        ('sale_price_dates_to', {
            'label':'sale_price_dates_to',
            'tag':'sale_to',
            'product': True,
            'variation': True,
            'pricing': True,
            'wp':{
                'key':'_sale_price_dates_to',
                'meta':True
            },
        }),
        ('RNR', {
            'label': 'meta:lc_rn_regular_price',
            'sync':True,
            'import': True,
            'product': True,
            'variation': True,
            'pricing': True,
            'wp':{
                'key':'lc_rn_regular_price',
                'meta':True
            },
            'wp-api':{
                'key':'lc_rn_regular_price',
                'meta':True
            },
        }),
        ('RNS', {
            'label': 'meta:lc_rn_sale_price',
            'sync':True,
            'product': True,
            'variation': True,
            'pricing': True,
            'wp':{
                'key':'lc_rn_sale_price',
                'meta':True
            },
            'wp-api':{
                'key':'lc_rn_sale_price',
                'meta':True
            },
        }),
        ('RNF', {
            'label': 'meta:lc_rn_sale_price_dates_from',
            'sync':True,
            'product': True,
            'variation': True,
            'pricing': True,
            'wp':{
                'key':'lc_rn_sale_price_dates_from',
                'meta':True
            },
            'wp-api':{
                'key':'lc_rn_sale_price_dates_from',
                'meta':True
            },
        }),
        ('RNT', {
            'label': 'meta:lc_rn_sale_price_dates_to',
            'sync':True,
            'product': True,
            'variation': True,
            'pricing': True,
            'wp':{
                'key':'lc_rn_sale_price_dates_to',
                'meta':True
            },
            'wp-api':{
                'key':'lc_rn_sale_price_dates_to',
                'meta':True
            },
        }),
        ('RPR', {
            'label': 'meta:lc_rp_regular_price',
            'sync':True,
            'import': True,
            'product': True,
            'variation': True,
            'pricing': True,
            'wp':{
                'key':'lc_rp_regular_price',
                'meta':True
            },
            'wp-api':{
                'key':'lc_rp_regular_price',
                'meta':True
            },
        }),
        ('RPS', {
            'label': 'meta:lc_rp_sale_price',
            'sync':True,
            'product': True,
            'variation': True,
            'pricing': True,
            'wp':{
                'key':'lc_rp_sale_price',
                'meta':True
            },
            'wp-api':{
                'key':'lc_rp_sale_price',
                'meta':True
            },
        }),
        ('RPF', {
            'label': 'meta:lc_rp_sale_price_dates_from',
            'sync':True,
            'product': True,
            'variation': True,
            'pricing': True,
            'wp':{
                'key':'lc_rp_sale_price_dates_from',
                'meta':True
            },
            'wp-api':{
                'key':'lc_rp_sale_price_dates_from',
                'meta':True
            },
        }),
        ('RPT', {
            'label': 'meta:lc_rp_sale_price_dates_to',
            'sync':True,
            'product': True,
            'variation': True,
            'pricing': True,
            'wp':{
                'key':'lc_rp_sale_price_dates_to',
                'meta':True
            },
            'wp-api':{
                'key':'lc_rp_sale_price_dates_to',
                'meta':True
            },
        }),
        ('WNR', {
            'label': 'meta:lc_wn_regular_price',
            'sync':True,
            'import': True,
            'product': True,
            'variation': True,
            'pricing': True,
            'wp':{
                'key':'lc_wn_regular_price',
                'meta':True
            },
            'wp-api':{
                'key':'lc_wn_regular_price',
                'meta':True
            },
        }),
        ('WNS', {
            'label': 'meta:lc_wn_sale_price',
            'sync':True,
            'product': True,
            'variation': True,
            'pricing': True,
            'wp':{
                'key':'lc_wn_sale_price',
                'meta':True
            },
            'wp-api':{
                'key':'lc_wn_sale_price',
                'meta':True
            },
        }),
        ('WNF', {
            'label': 'meta:lc_wn_sale_price_dates_from',
            'sync':True,
            'product': True,
            'variation': True,
            'pricing': True,
            'wp':{
                'key':'lc_wn_sale_price_dates_from',
                'meta':True
            },
            'wp-api':{
                'key':'lc_wn_sale_price_dates_from',
                'meta':True
            },
        }),
        ('WNT', {
            'label': 'meta:lc_wn_sale_price_dates_to',
            'sync':True,
            'product': True,
            'variation': True,
            'pricing': True,
            'wp':{
                'key':'lc_wn_sale_price_dates_to',
                'meta':True
            },
            'wp-api':{
                'key':'lc_wn_sale_price_dates_to',
                'meta':True
            },
        }),
        ('WPR', {
            'label': 'meta:lc_wp_regular_price',
            'sync':True,
            'import': True,
            'product': True,
            'variation': True,
            'pricing': True,
            'wp':{
                'key':'lc_wp_regular_price',
                'meta':True
            },
            'wp-api':{
                'key':'lc_wp_regular_price',
                'meta':True
            },
        }),
        ('WPS', {
            'label': 'meta:lc_wp_sale_price',
            'sync':True,
            'product': True,
            'variation': True,
            'pricing': True,
            'wp':{
                'key':'lc_wp_sale_price',
                'meta':True
            },
            'wp-api':{
                'key':'lc_wp_sale_price',
                'meta':True
            },
        }),
        ('WPF', {
            'label': 'meta:lc_wp_sale_price_dates_from',
            'sync':True,
            'product': True,
            'variation': True,
            'pricing': True,
            'wp':{
                'key':'lc_wp_sale_price_dates_from',
                'meta':True
            },
            'wp-api':{
                'key':'lc_wp_sale_price_dates_from',
                'meta':True
            },
        }),
        ('WPT', {
            'label': 'meta:lc_wp_sale_price_dates_to',
            'sync':True,
            'product': True,
            'variation': True,
            'pricing': True,
            'wp':{
                'key':'lc_wp_sale_price_dates_to',
                'meta':True
            },
            'wp-api':{
                'key':'lc_wp_sale_price_dates_to',
                'meta':True
            },
        }),
        ('DNR', {
            'label': 'meta:lc_dn_regular_price',
            'sync':True,
            'import': True,
            'product': True,
            'variation': True,
            'pricing': True,
            'wp':{
                'key':'lc_dn_regular_price',
                'meta':True
            },
            'wp-api':{
                'key':'lc_dn_regular_price',
                'meta':True
            },
        }),
        ('DNS', {
            'label': 'meta:lc_dn_sale_price',
            'sync':True,
            'product': True,
            'variation': True,
            'pricing': True,
            'wp':{
                'key':'lc_dn_sale_price',
                'meta':True
            },
            'wp-api':{
                'key':'lc_dn_sale_price',
                'meta':True
            },
        }),
        ('DNF', {
            'label': 'meta:lc_dn_sale_price_dates_from',
            'sync':True,
            'product': True,
            'variation': True,
            'pricing': True,
            'wp':{
                'key':'lc_dn_sale_price_dates_from',
                'meta':True
            },
            'wp-api':{
                'key':'lc_dn_sale_price_dates_from',
                'meta':True
            },
        }),
        ('DNT', {
            'label': 'meta:lc_dn_sale_price_dates_to',
            'sync':True,
            'product': True,
            'variation': True,
            'pricing': True,
            'wp':{
                'key':'lc_dn_sale_price_dates_to',
                'meta':True
            },
            'wp-api':{
                'key':'lc_dn_sale_price_dates_to',
                'meta':True
            },
        }),
        ('DPR', {
            'label': 'meta:lc_dp_regular_price',
            'sync':True,
            'import': True,
            'product': True,
            'variation': True,
            'pricing': True,
            'wp':{
                'key':'lc_dp_regular_price',
                'meta':True
            },
            'wp-api':{
                'key':'lc_dp_regular_price',
                'meta':True
            },
        }),
        ('DPS', {
            'label': 'meta:lc_dp_sale_price',
            'sync':True,
            'product': True,
            'variation': True,
            'pricing': True,
            'wp':{
                'key':'lc_dp_sale_price',
                'meta':True
            },
            'wp-api':{
                'key':'lc_dp_sale_price',
                'meta':True
            },
        }),
        ('DPF', {
            'label': 'meta:lc_dp_sale_price_dates_from',
            'sync':True,
            'product': True,
            'variation': True,
            'pricing': True,
            'wp':{
                'key':'lc_dp_sale_price_dates_from',
                'meta':True
            },
            'wp-api':{
                'key':'lc_dp_sale_price_dates_from',
                'meta':True
            },
        }),
        ('DPT', {
            'label': 'meta:lc_dp_sale_price_dates_to',
            'sync':True,
            'product': True,
            'variation': True,
            'pricing': True,
            'wp':{
                'key':'lc_dp_sale_price_dates_to',
                'meta':True
            },
            'wp-api':{
                'key':'lc_dp_sale_price_dates_to',
                'meta':True
            },
        }),
        ('CVC', {
            'label': 'meta:commissionable_value',
            'sync':True,
            'import': True,
            'product': True,
            'variation': True,
            'pricing': True,
            'default': 0,
            'wp':{
                'key':'commissionable_value',
                'meta':True
            },
            'wp-api':{
                'key':'commissionable_value',
                'meta':True
            },
        }),
        ('weight', {
            'import': True,
            'product': True,
            'variation': True,
            'shipping': True,
            'wp':{
                'key':'_weight',
                'meta':True
            },
            'wp-api':{
                'key':'weight'
            },
            'sync':True
        }),
        ('length', {
            'import': True,
            'product': True,
            'variation': True,
            'shipping':True,
            'wp':{
                'key':'_length',
                'meta':True
            },
            'sync':True
        }),
        ('width', {
            'import': True,
            'product': True,
            'variation': True,
            'shipping': True,
            'wp':{
                'key':'_width',
                'meta':True
            },
            'sync':True
        }),
        ('height', {
            'import': True,
            'product': True,
            'variation': True,
            'shipping': True,
            'wp':{
                'key':'_height',
                'meta':True
            },
            'sync':True
        }),
        ('stock', {
            'import': True,
            'product': True,
            'variation': True,
            'inventory':True,
            'wp':{
                'key':'_stock',
                'meta':True
            },
            'sync':True,
            'wp-api':{
                'key':'stock_quantity'
            }
        }),
        ('stock_status', {
            'import': True,
            'product': True,
            'variation': True,
            'inventory':True,
            'wp':{
                'key':'_stock_status',
                'meta':True
            },
            'sync':True
        }),
        ('manage_stock', {
            'product': True,
            'variation': True,
            'inventory':True,
            'wp':{
                'key':'_manage_stock',
                'meta':True
            },
            'wp-api':{
                'key': 'manage_stock'
            },
            'sync':True,
            'default':'no'
        }),
        ('Images', {
            'import': True,
            'default': ''
        }),
        ('HTML Description', {
            'import': True
        }),
        ('last_import', {
            'label':'meta:last_import',
            'product': True,
        }),
        ('Updated', {
            'import': True,
            'product':True,
            'wp-api':{
                'key':'updated_at'
            }
        }),
        ('post_status', {
            'import':True,
            'product':True,
            'variation':True,
            'wp-api':{
                'key':'status'
            },
            'sync':True,
            'default':'publish'
        }),
    ])

    def __init__( self, data = None):
        if not data: data = self.data
        super(ColData_Woo, self).__init__( data )

    @classmethod
    def getProductCols(self):
        return self.getExportCols('product')

    @classmethod
    def getVariationCols(self):
        return self.getExportCols('variation')

    @classmethod
    def getCategoryCols(self):
        return self.getExportCols('category')

    @classmethod
    def getPricingCols(self):
        return self.getExportCols('pricing')

    @classmethod
    def getShippingCols(self):
        return self.getExportCols('shipping')

    @classmethod
    def getInventoryCols(self):
        return self.getExportCols('inventory')

    @classmethod
    def getWPCols(self):
        return self.getExportCols('wp')

    @classmethod
    def getAttributeCols(self, attributes, vattributes):
        attributeCols = OrderedDict()
        all_attrs = listUtils.combineLists(attributes.keys(), vattributes.keys())
        for attr in all_attrs:
            attributeCols['attribute:'+attr] = {
                'product':True,
            }
            if attr in vattributes.keys():
                attributeCols['attribute_default:'+attr] = {
                    'product':True,
                }
                attributeCols['attribute_data:'+attr] = {
                    'product':True,
                }
        return attributeCols

    @classmethod
    def getAttributeMetaCols(self, vattributes):
        atttributeMetaCols = OrderedDict()
        for attr in vattributes.keys():
            atttributeMetaCols['meta:attribute_'+attr] = {
                'variable': True,
                'tag': attr
            }
        return atttributeMetaCols

class ColData_User(ColData_Base):
    # modTimeSuffix = ' Modified'

    modMapping = {
        'Home Address': 'Alt Address',
    }

    @classmethod
    def modTimeCol(self, col):
        if col in self.modMapping:
            col = self.modMapping[col]
        return 'Edited ' + col

    wpdbPKey = 'Wordpress ID'

    data = OrderedDict([
        ('MYOB Card ID', {
            'wp': {
                'meta': True,
                'key': 'myob_card_id'
            },
            'act':True,
            # 'label':'myob_card_id',
            'import':True,
            'user':True,
            'report':True,
            'sync':'master_override',
            'warn':True,
            'static':True,
            'basic':True,
        }),

        ('E-mail', {
            'wp': {
                'meta': False,
                'key': 'user_email'
            },
            'act':True,
            'import': True,
            'user':True,
            'report': True,
            'sync':True,
            'warn':True,
            'static':True,
            'basic':True,
            'tracked':True,
            'delta':True,
        }),
        ('Wordpress Username', {
            # 'label':'Username',
            'wp': {
                'meta': False,
                'key': 'user_login',
                'final': True
            },
            'act':True,
            'user':True,
            'report': True,
            'import':True,
            'sync':'slave_override',
            'warn':True,
            'static':True,
            # 'tracked':True,
            # 'basic':True,
        }),
        ('Wordpress ID', {
            # 'label':'Username',
            'wp': {
                'meta': False,
                'key': 'ID',
                'final': True
            },
            'act':False,
            'user':True,
            'report': True,
            'import':True,
            # 'sync':'slave_override',
            'warn':True,
            'static':True,
            'basic':True,
            'default':'',
            # 'tracked':True,
        }),
        ('Role', {
            'wp': {
                'meta': True,
                'key': 'act_role'
            },
            # 'label': 'act_role',
            'act':True,
            'delta':True,
            'import':True,
            'user':True,
            'report': True,
            'sync':True,
            'warn': True,
            'static':True,
            # 'tracked':'future',
        }),

        ('Name', {
            'user':True,
            'aliases': [
                'Name Prefix',
                'First Name',
                'Middle Name',
                'Surname',
                'Name Suffix',
                'Memo',
                'Spouse',
                'Salutation',
                'Search Text',
                'HO Contact',
                'Contact'
            ],
            'sync':True,
            'static':True,
            'basic':True,
            'report':True,
            'tracked':True,
        }),
        ('Contact', {
            'import':True,
            'wp': {
                'meta': False,
                'key': 'display_name'
            },
            'act': True,
            'mutable':True,
            'visible':True,
            # 'label':'contact_name',
            # 'warn': True,
            # 'user':True,
            # 'sync':True,
            # "static": True,
            # 'report':True,
        }),
        ('First Name', {
            'wp': {
                'meta': True,
                'key': 'first_name'
            },
            'act': True,
            'mutable':True,
            'visible':True,
            # 'label':'first_name',
            'import':True,
            # 'user':True,
            # 'report': True,
            # 'sync':True,
            # 'warn': True,
            # 'static':True,
        }),
        ('Surname', {
            'wp': {
                'meta': True,
                'key': 'last_name'
            },
            'act': True,
            'mutable':True,
            # 'label':'last_name',
            'import': True,
            'visible':True,
            # 'user':True,
            # 'report': True,
            # 'sync':True,
            # 'warn': True,
            # 'static':True,
        }),
        ('Middle Name', {
            'wp': {
                'meta': True,
                'key': 'middle_name'
            },
            'act': True,
            'import': True,
            'mutable':True,
            'visible':True,
            # 'user': True,
        }),
        ('Name Suffix', {
            'wp': {
                'meta': True,
                'key': 'name_suffix'
            },
            'act': True,
            'import': True,
            'visible':True,
            # 'user': True,
            'mutable':True,
        }),
        ('Name Prefix', {
            'wp': {
                'meta': True,
                'key': 'name_prefix'
            },
            'act': True,
            'import': True,
            'visible':True,
            # 'user': True,
            'mutable':True,
        }),
        ('Memo', {
            'wp': {
                'meta': True,
                'key': 'name_notes'
            },
            'act': True,
            'import': True,
            'tracked':True,
        }),
        ('Spouse', {
            'wp': {
                'meta': True,
                'key': 'spouse'
            },
            'act': True,
            'import': True,
            'tracked': 'future',
        }),
        ('Salutation', {
            'wp': {
                'meta': True,
                'key': 'nickname'
            },
            'act': True,
            'import': True,
        }),

        ('Company', {
            'wp': {
                'meta': True,
                'key': 'billing_company'
            },
            'act': True,
            # 'label':'billing_company',
            'import':True,
            'user':True,
            'basic':True,
            'report': True,
            'sync':True,
            'warn': True,
            'static':True,
            # 'visible':True,
            'tracked':True,
        }),


        ('Phone Numbers', {
            'tracked':'future',
            'aliases':[ 'Mobile Phone', 'Phone', 'Fax'],
                        # 'Mobile Phone Preferred', 'Phone Preferred', ]
            'basic':True,
            'report':True,
        }),

        ('Mobile Phone', {
            'wp': {
                'meta': True,
                'key': 'mobile_number'
            },
            'act': True,
            # 'label':'mobile_number',
            'import':True,
            'user':True,
            'sync':True,
            'warn': True,
            'static':True,
            # 'visible':True,
            'contact':True,
        }),
        ('Phone', {
            'wp': {
                'meta': True,
                'key': 'billing_phone'
            },
            'act':True,
            # 'label':'billing_phone',
            'import':True,
            'user':True,
            # 'report': True,
            'sync':True,
            'warn': True,
            'static':True,
            # 'visible':True,
        }),
        ('Fax', {
            'wp': {
                'meta': True,
                'key': 'fax_number'
            },
            'act':True,
            # 'label':'fax_number',
            'import':True,
            'user':True,
            'sync':True,
            'contact':True,
            'visible':True,
            'mutable':True,
        }),
        ('Mobile Phone Preferred', {
            'wp': {
                'meta': True,
                'key': 'pref_mob'
            },
            'act':True,
            # 'label':'pref_mob',
            'import':True,
            'user':True,
            'sync':True,
            'visible':True,
            'mutable':True,
        }),
        ('Phone Preferred', {
            'wp': {
                'meta': True,
                'key': 'pref_tel'
            },
            'act':True,
            # 'label':'pref_tel',
            'import':True,
            'user':True,
            'sync':True,
            'visible':True,
            'mutable':True,
        }),


        ('Address', {
            'act':False,
            'wp':False,
            'report':True,
            'warn':True,
            'static':True,
            'sync':True,
            'aliases':['Address 1', 'Address 2', 'City', 'Postcode', 'State', 'Country', 'Shire'],
            'basic':True,
            'tracked':True,
        }),
        ('Home Address', {
            'act':False,
            'wp':False,
            'report':True,
            'warn':True,
            'static':True,
            'sync':True,
            'basic':True,
            'aliases':['Home Address 1', 'Home Address 2', 'Home City', 'Home Postcode', 'Home State', 'Home Country'],
            'tracked':'future',
        }),
        ('Address 1', {
            'wp': {
                'meta': True,
                'key': 'billing_address_1'
            },
            'act':True,
            # 'label':'billing_address_1',
            'import':True,
            'user':True,
            # 'sync':True,
            # 'warn': True,
            # 'static':True,
            # 'capitalized':True,
            # 'visible':True,
        }),
        ('Address 2', {
            'wp': {
                'meta': True,
                'key': 'billing_address_2'
            },
            'act':True,
            # 'label':'billing_address_2',
            'import':True,
            'user':True,
            # 'sync':True,
            # 'warn': True,
            # 'static':True,
            # 'capitalized':True,
            # 'visible':True,
        }),
        ('City', {
            'wp': {
                'meta': True,
                'key': 'billing_city'
            },
            'act':True,
            # 'label':'billing_city',
            'import':True,
            'user':True,
            # 'sync':True,
            # 'warn': True,
            # 'static':True,
            # 'report': True,
            # 'capitalized':True,
            # 'visible':True,
        }),
        ('Postcode', {
            'wp': {
                'meta': True,
                'key': 'billing_postcode'
            },
            'act':True,
            # 'label':'billing_postcode',
            'import':True,
            'user':True,
            # 'sync':True,
            # 'warn': True,
            # 'static':True,
            # 'visible':True,
            # 'report': True,
        }),
        ('State', {
            'wp': {
                'meta': True,
                'key': 'billing_state'
            },
            'act':True,
            # 'label':'billing_state',
            'import':True,
            'user':True,
            # 'sync':True,
            # 'warn': True,
            # 'static':True,
            # 'report':True,
            # 'capitalized':True,
            # 'visible':True,
        }),
        ('Country', {
            'wp': {
                'meta': True,
                'key': 'billing_country'
            },
            'act':True,
            # 'label':'billing_country',
            'import':True,
            'user':True,
            # 'warn':True,
            # 'static':True,
            # 'capitalized':True,
            # 'visible':True,
        }),
        ('Shire', {
            'wp': False,
            'act': True,
            # 'label':'billing_country',
            'import':True,
            'user':True,
            # 'warn':True,
            # 'static':True,
            # 'capitalized':True,
            # 'visible':True,
        }),
        ('Home Address 1', {
            'wp': {
                'meta': True,
                'key': 'shipping_address_1'
            },
            'act':True,
            # 'label':'shipping_address_1',
            'import':True,
            'user':True,
            # 'sync':True,
            # 'static':True,
            # 'capitalized':True,
            # 'visible':True,
        }),
        ('Home Address 2', {
            'wp': {
                'meta': True,
                'key': 'shipping_address_2'
            },
            'act':True,
            # 'label':'shipping_address_2',
            'import':True,
            'user':True,
            # 'sync':True,
            # 'static':True,
            # 'capitalized':True,
            # 'visible':True,
        }),
        ('Home City', {
            'wp': {
                'meta': True,
                'key': 'shipping_city'
            },
            'act':True,
            # 'label':'shipping_city',
            'import':True,
            'user':True,
            # 'sync':True,
            # 'static':True,
            # 'capitalized':True,
            # 'visible':True,
        }),
        ('Home Postcode', {
            'wp': {
                'meta': True,
                'key': 'shipping_postcode'
            },
            'act':True,
            # 'label':'shipping_postcode',
            'import':True,
            'user':True,
            # 'sync':True,
            # 'static':True,
            # 'visible':True,
        }),
        ('Home Country', {
            'wp': {
                'meta': True,
                'key': 'shipping_country'
            },
            'act':True,
            # 'label':'shipping_country',
            'import':True,
            'user':True,
            # 'sync':True,
            # 'static':True,
            # 'capitalized':True,
            # 'visible':True,
        }),
        ('Home State', {
            'wp': {
                'meta': True,
                'key': 'shipping_state'
            },
            'act':True,
            # 'label':'shipping_state',
            'import':True,
            'user':True,
            # 'sync':True,
            # 'static':True,
            # 'capitalized':True,
            # 'visible':True,
        }),



        ('MYOB Customer Card ID', {
            # 'label':'myob_customer_card_id',
            'wp': {
                'meta': True,
                'key': 'myob_customer_card_id'
            },
            'act':True,
            'import':True,
            # 'report':True,
            'user':True,
            'sync':'master_override',
            'warn':True,
        }),
        ('Client Grade', {
            'import':True,
            'wp': {
                'meta': True,
                'key': 'client_grade'
            },
            'act':True,
            # 'label':'client_grade',
            'user':True,
            # 'report':True,
            'sync':'master_override',
            'warn':True,
            'visible':True,
        }),
        ('Direct Brand', {
            'import':True,
            'wp': {
                'meta': True,
                'key': 'direct_brand'
            },
            'act':True,
            # 'label':'direct_brand',
            'user':True,
            # 'report': True,
            'sync':'master_override',
            'warn':True,
        }),
        ('Agent', {
            'wp': {
                'meta': True,
                'key': 'agent'
            },
            'act':True,
            # 'label':'agent',
            'import':'true',
            'user':True,
            'sync':'master_override',
            'warn':True,
            'visible':True,
        }),

        ('ABN', {
            'wp': {
                'meta': True,
                'key': 'abn'
            },
            'act':True,
            # 'label':'abn',
            'import':True,
            'user':True,
            'sync':True,
            'warn': True,
            'visible':True,
            'mutable':True,
        }),
        ('Business Type', {
            'wp': {
                'meta': True,
                'key': 'business_type'
            },
            'act':True,
            # 'label':'business_type',
            'import':True,
            'user':True,
            'sync':True,
            'visible':True,
            # 'mutable':True
        }),
        ('Lead Source', {
            'wp': {
                'meta': True,
                'key': 'how_hear_about'
            },
            'act':True,
            # 'label':'how_hear_about',
            'import':True,
            'user':True,
            'sync':True,
            # 'visible':True,
        }),
        ('Referred By', {
            'wp': {
                'meta': True,
                'key': 'referred_by'
            },
            'act':True,
            # 'label':'referred_by',
            'import':True,
            'user':True,
            'sync':True,
        }),

        # ('E-mails', {
        #     'aliases': ['E-mail', 'Personal E-mail']
        # }),
        ('Personal E-mail', {
            'wp': {
                'meta': True,
                'key': 'personal_email'
            },
            'act':True,
            # 'label':'personal_email',
            'import':True,
            'user':True,
            'tracked':'future',
            'report':True,
        }),
        ('Create Date', {
            'import': True,
            'act':True,
            'wp':False,
            # 'report': True,
            # 'basic':True
        }),
        ('Wordpress Start Date', {
            'import': True,
            'wp': {
                'meta': False,
                'key': 'user_registered'
            },
            'act':True,
            # 'report': True,
            # 'basic':True
        }),
        ('Edited in Act', {
            'wp': {
                'meta': True,
                'key': 'edited_in_act'
            },
            'act':True,
            'import': True,
            'report': True,
            'basic':True,
        }),
        ('Edited in Wordpress', {
            'wp': {
                'generated':True,
            },
            'act':True,
            'import':True,
            'report':True,
            'basic':True
        }),
        ('Last Sale', {
            'wp': {
                'meta': True,
                'key': 'act_last_sale'
            },
            'act':True,
            'import': True,
            'basic':True,
            # 'report': True
        }),

        ('Social Media', {
            'sync':True,
            'aliases':['Facebook Username', 'Twitter Username',
                       'GooglePlus Username', 'Instagram Username',
                       ],
                    #    'Web Site'],
            'tracked':True,
        }),

        ("Facebook Username", {
            'wp': {
                'key': "facebook",
                'meta': True
            },
            'mutable':True,
            'visible':True,
            'contact':True,
            'import':True,
            'act':True,
        }),
        ("Twitter Username", {
            'wp': {
                'key': "twitter",
                'meta': True
            },
            'contact':True,
            'mutable':True,
            'visible':True,
            'import':True,
            'act':True,
        }),
        ("GooglePlus Username", {
            'wp': {
                'key': "gplus",
                'meta': True
            },
            'contact':True,
            'mutable':True,
            'visible':True,
            'import':True,
            'act':True,
        }),
        ("Instagram Username", {
            'wp': {
                'key': "instagram",
                'meta': True
            },
            'contact':True,
            'mutable':True,
            'visible':True,
            'import':True,
            'act':True,
        }),
        ('Web Site', {
            'wp': {
                'meta': False,
                'key': 'user_url'
            },
            'act':True,
            'label': 'user_url',
            'import':True,
            'user':True,
            'sync':True,
            'tracked':True,
        }),

        ("Added to mailing list", {
            'wp': {
                'key': 'mailing_list',
                'meta':True,
            },
            'sync':True,
            'import':True,
            'tracked':True,
            'default':'',
        })
        # ('rowcount', {
        #     # 'import':True,
        #     # 'user':True,
        #     'report':True,
        # }),
    ])

    def __init__(self, data=None):
        if not data: data = self.data
        super(ColData_User, self).__init__(data)

    @classmethod
    def getUserCols(self):
        return self.getExportCols('user')

    @classmethod
    def getSyncCols(self):
        return self.getExportCols('sync')

    @classmethod
    def getCapitalCols(self):
        return self.getExportCols('capitalized')

    @classmethod
    def getWPCols(self):
        return self.getExportCols('wp')

    @classmethod
    def getACTCols(self):
        return self.getExportCols('act')

    @classmethod
    def getAliasCols(self):
        return self.getExportCols('aliases')

    @classmethod
    def getWPImportCols(self):
        cols = []
        for col, data in self.data.items():
            if data.get('wp') and data.get('import'):
                cols.append(col)
            if data.get('tracked'):
                cols.append(self.modTimeCol(col))
        return cols


    @classmethod
    def getWPImportColNames(self):
        cols = OrderedDict()
        for col, data in self.data.items():
            if data.get('wp') and data.get('import'):
                cols[col] = col
            if data.get('tracked'):
                modCol = self.modTimeCol(col)
                cols[modCol] = modCol
        return cols

    @classmethod
    def getWPDBCols(self, meta=None):
        cols = OrderedDict()
        for col, data in self.data.items():
            if data.get('wp'):
                wp_data = data['wp']
                if hasattr(wp_data, '__getitem__'):
                    if wp_data.get('generated')\
                      or (meta and not wp_data.get('meta'))\
                      or (not meta and wp_data.get('meta')):
                        continue
                    if wp_data.get('key'):
                        key = wp_data['key']
                        if key:
                            cols[key] = col
        if not meta:
            assert self.wpdbPKey in cols.values()
        return cols

    @classmethod
    def getAllWPDBCols(self):
        return listUtils.combineOrderedDicts(
            self.getWPDBCols(True),
            self.getWPDBCols(False)
        )



    # @classmethod
    # def getWPTrackedColsRecursive(self, col, cols = None, data={}):
    #     if cols is None:
    #         cols = OrderedDict()
    #     if data.get('wp'):
    #         wp_data = data.get('wp')
    #         if hasattr(wp_data, '__getitem__'):
    #             if wp_data.get('key'):
    #                 key = wp_data.get('key')
    #                 if key:
    #                     cols[col] = cols.get(col, []) + [key]
    #     if data.get('tracked'):
    #         for alias in data.get('aliases', []):
    #             alias_data = self.data.get(alias, {})
    #             cols = self.getWPTrackedColsRecursive(alias, cols, alias_data)

    #     return cols


    @classmethod
    def getWPTrackedCols(self):
        cols = OrderedDict()
        for col, data in self.data.items():
            if data.get('tracked'):
                tracking_name = self.modTimeCol(col)
                for alias in data.get('aliases', []) + [col]:
                    alias_data = self.data.get(alias, {})
                    if alias_data.get('wp'):
                        this_tracking_name = tracking_name
                        if alias_data.get('tracked'):
                            this_tracking_name = self.modTimeCol(alias)
                        cols[this_tracking_name] = cols.get(this_tracking_name, []) + [alias]
                        # wp_data = alias_data.get('wp')

                        # if hasattr(wp_data, '__getitem__') and wp_data.get('key'):
                        #     key = wp_data.get('key')
                        #     if key and not key in cols.get(tracking_name, []):
                        #         cols[tracking_name] = cols.get(tracking_name, []) + [key]
        return cols

    @classmethod
    def getACTTrackedCols(self):
        cols = OrderedDict()
        for col, data in self.data.items():
            if data.get('tracked'):
                tracking_name = self.modTimeCol(col)
                for alias in data.get('aliases', []) + [col]:
                    alias_data = self.data.get(alias, {})
                    if alias_data.get('act'):
                        this_tracking_name = tracking_name
                        if alias_data.get('tracked'):
                            this_tracking_name = self.modTimeCol(alias)
                        cols[this_tracking_name] = cols.get(this_tracking_name, []) + [alias]
        return cols

    @classmethod
    def getACTFutureTrackedCols(self):
        cols = OrderedDict()
        for col, data in self.data.items():
            if data.get('tracked') and data.get('tracked') == 'future':
                tracking_name = self.modTimeCol(col)
                for alias in data.get('aliases', []) + [col]:
                    alias_data = self.data.get(alias, {})
                    if alias_data.get('act'):
                        this_tracking_name = tracking_name
                        if alias_data.get('tracked'):
                            this_tracking_name = self.modTimeCol(alias)
                        cols[this_tracking_name] = cols.get(this_tracking_name, []) + [alias]
        return cols

    @classmethod
    def getACTImportCols(self):
        cols = []
        for col, data in self.data.items():
            if data.get('act') and data.get('import'):
                cols.append(col)
            if data.get('tracked'):
                cols.append(self.modTimeCol(col))
        return cols

    @classmethod
    def getACTImportColNames(self):
        cols = OrderedDict()
        for col, data in self.data.items():
            if data.get('act') and data.get('import'):
                cols[col] = col
            if data.get('tracked'):
                modCol = self.modTimeCol(col)
                cols[modCol] = modCol
        return cols

    @classmethod
    def getTansyncDefaultsRecursive(self, col, exportCols=None, data=None):
        if data is None:
            data = {}
        if exportCols is None:
            exportCols = OrderedDict()

        # print "getting sync data: ", col, data

        new_data = {}
        if data.get('sync'):
            sync_data = data.get('sync')
            if sync_data == 'master_override':
                new_data['sync_ingress'] = 1
                new_data['sync_egress'] = 0
            elif sync_data == 'slave_override':
                new_data['sync_ingress'] = 0
                new_data['sync_egress'] = 1
            else:
                new_data['sync_egress'] = 1
                new_data['sync_ingress'] = 1
            new_data['sync_label'] = col

        if data.get('visible'): new_data['profile_display'] = 1
        if data.get('mutable'): new_data['profile_modify'] = 1
        if data.get('contact'): new_data['contact_method'] = 1


        if new_data and data.get('wp'):
            wp_data = data['wp']
            if not wp_data.get('meta'):
                new_data['core'] = 1
            if not wp_data.get('generated'):
                assert wp_data.get('key'), "column %s must have key" % col
                key = wp_data['key']
                exportCols[key] = new_data

        if data.get('aliases'):
            for alias in data['aliases']:
                alias_data = self.data.get(alias, {})
                alias_data['sync'] = data.get('sync')
                exportCols = self.getTansyncDefaultsRecursive(alias, exportCols, alias_data)

        return exportCols

    @classmethod
    def getTansyncDefaults(self):
        exportCols = OrderedDict()
        for col, data in self.data.items():
            exportCols = self.getTansyncDefaultsRecursive(col, exportCols, data)
        return exportCols

#
#
# def testColDataMyo():
#     print "Testing ColData_MYO Class:"
#     colData = ColData_MYO()
#     print colData.getImportCols()
#     print colData.getDefaults()
#     print colData.getProductCols()
#
# def testColDataWoo():
#     print "Testing ColData_Woo class:"
#     colData = ColData_Woo()
#     print colData.getImportCols()
#     print colData.getDefaults()
#     print colData.getProductCols()
#
# def testColDataUser():
#     print "Testing ColData_User class:"
#     colData = ColData_User()
#     # print "importCols", colData.getImportCols()
#     # print "userCols", colData.getUserCols().keys()
#     # print "reportCols", colData.getReportCols().keys()
#     # print "capitalCols", colData.getCapitalCols().keys()
#     # print "syncCols", colData.getSyncCols().keys()
#     print "actCols", colData.getACTCols().keys()
#     # print "wpcols", colData.getWPCols().keys()
#     print "getWPTrackedCols", colData.getWPTrackedCols()
#     print "getACTTrackedCols", colData.getACTTrackedCols()
#     print "getACTFutureTrackedCols", colData.getACTFutureTrackedCols()
#
# def testTansyncDefaults():
#     colData = ColData_User()
#     print '{'
#     for col, data in colData.getTansyncDefaults().items():
#         print '"%s": %s,' % (col, json.dumps(data))
#     print '}'
#
# if __name__ == '__main__':
#     # testColDataMyo()
#     # testColDataWoo()
#     testColDataUser()
#     # testTansyncDefaults()
