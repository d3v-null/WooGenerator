from collections import OrderedDict
from utils import listUtils

class ColData_Base(object):

    def __init__(self, data):
        super(ColData_Base, self).__init__()
        assert issubclass(type(data), dict), "Data should be a dictionary subclass"
        self.data = data
        
    def getImportCols(self):
        imports = []
        for col, data in self.data.items():
            if data.get('import', False):
                imports.append(col)
        return imports

    def getDefaults(self):
        defaults = {}
        for col, data in self.data.items():
            # if data.get('import') and data.get('default'):
            if data.get('default'):
                    defaults[col] = data.get('default')
        return defaults

    def getExportCols(self, schema=None):
        if not schema: return None
        exportCols = OrderedDict()
        for col, data in self.data.items():
            if data.get(schema, ''):
                exportCols[col] = data
        return exportCols

    def getColNames(self, cols):
        colNames = OrderedDict()
        for col, data in cols.items():
            label = data.get('label','')
            colNames[col] = label if label else col
        return colNames

class ColData_MYO(ColData_Base):

    data = OrderedDict([
        ('codesum', {
            'label': 'Item Number',
            'product':True,
        }),
        ('itemsum', {
            'label': 'Item Name',
            'product':True,
        }),
        ('WNR', {
            'label': 'Selling Price',
            'import': True,
            'product': True,
            'pricing': True,
        }),
        ('RNR',{
            'label': 'Price Level B, Qty Break 1',
            'import': True,
            'product': True,
            'pricing': True,
        }),
        ('DNR',{
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
        }),
        ('HTML Description',{
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

    def getProductCols(self):
        return self.getExportCols('product')

class ColData_Woo(ColData_Base):

    data = OrderedDict([
        ('ID', {
            'wp':{
                'key': 'ID',
                'meta': False
            }
        }),
        ('parent_SKU',{
            'variation':True,
        }),
        ('codesum',{
            'label':'SKU',
            'tag':'SKU',
            'product': True,
            'variation': True,
            'category': True,
            'wp':{
                'key':'_sku',
                'meta':True
            }
        }),
        ('itemsum', {
            'tag':'Title',
            'label':'post_title',
            'product':True, 
            'variation': True,
            'wp':{
                'key':'post_title',
                'meta':False
            }
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
        ('taxosum',{
            'label':'category_title',
            'category':True,
        }),
        ('prod_type', {
            'label':'tax:product_type',
            'product':True,
        }),
        ('catsum',{
            'label':'tax:product_cat',
            'product':True,
        }),
        ('descsum', {
            'label':'post_content',
            'tag':'Description',
            'product': True,
            'category': True,
        }),
        ('imgsum',{
            'label':'Images',
            'product': True,
            'variation': True,
            'category': True,
        }),
        ('rowcount', {
            'label':'menu_order',
            'product': True,
            'category': True,
            'variation': True
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
        }),
        ('E',{
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
        ('pricing_rules',{
            'label': 'meta:_pricing_rules',
            'pricing':True,
            'wp':{
                'key':'post_title',
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
            'import': True,
            'product': True,
            'variation': True,
            'pricing': True,
            'wp':{
                'key':'lc_rn_regular_price',
                'meta':True
            },        
        }),
        ('RNS', {
            'label': 'meta:lc_rn_sale_price',
            'product': True,
            'variation': True,
            'pricing': True,
            'wp':{
                'key':'lc_rn_sale_price',
                'meta':True
            },        
        }),
        ('RNF', {
            'label': 'meta:lc_rn_sale_price_dates_from',
            'product': True,
            'variation': True,
            'pricing': True,
            'wp':{
                'key':'lc_rn_sale_price_dates_from',
                'meta':True
            },        
        }),
        ('RNT', {
            'label': 'meta:lc_rn_sale_price_dates_to',
            'product': True,
            'variation': True,
            'pricing': True,
            'wp':{
                'key':'lc_rn_sale_price_dates_to',
                'meta':True
            },        
        }),
        ('RPR', {
            'label': 'meta:lc_rp_regular_price',
            'import': True,
            'product': True,
            'variation': True,
            'pricing': True,
            'wp':{
                'key':'lc_rp_regular_price',
                'meta':True
            },        
        }),
        ('RPS', {
            'label': 'meta:lc_rp_sale_price',
            'product': True,
            'variation': True,
            'pricing': True,
            'wp':{
                'key':'lc_rp_sale_price',
                'meta':True
            },        
        }),
        ('RPF', {
            'label': 'meta:lc_rp_sale_price_dates_from',
            'product': True,
            'variation': True,
            'pricing': True,
            'wp':{
                'key':'lc_rp_sale_price_dates_from',
                'meta':True
            },        
        }),
        ('RPT', {
            'label': 'meta:lc_rp_sale_price_dates_to',
            'product': True,
            'variation': True,
            'pricing': True,
            'wp':{
                'key':'lc_rp_sale_price_dates_to',
                'meta':True
            },        
        }),
        ('WNR', {
            'label': 'meta:lc_wn_regular_price',
            'import': True,
            'product': True,
            'variation': True,
            'pricing': True,
            'wp':{
                'key':'lc_wn_regular_price',
                'meta':True
            },        
        }),
        ('WNS', {
            'label': 'meta:lc_wn_sale_price',
            'product': True,
            'variation': True,
            'pricing': True,
            'wp':{
                'key':'lc_wn_sale_price',
                'meta':True
            },        
        }),
        ('WNF', {
            'label': 'meta:lc_wn_sale_price_dates_from',
            'product': True,
            'variation': True,
            'pricing': True,
            'wp':{
                'key':'lc_wn_sale_price_dates_from',
                'meta':True
            },        
        }),
        ('WNT', {
            'label': 'meta:lc_wn_sale_price_dates_to',
            'product': True,
            'variation': True,
            'pricing': True,
            'wp':{
                'key':'lc_wn_sale_price_dates_to',
                'meta':True
            },        
        }),
        ('WPR', {
            'label': 'meta:lc_wp_regular_price',
            'import': True,
            'product': True,
            'variation': True,
            'pricing': True,
            'wp':{
                'key':'lc_wp_regular_price',
                'meta':True
            },        
        }),
        ('WPS', {
            'label': 'meta:lc_wp_sale_price',
            'product': True,
            'variation': True,
            'pricing': True,
            'wp':{
                'key':'lc_wp_sale_price',
                'meta':True
            },        
        }),
        ('WPF', {
            'label': 'meta:lc_wp_sale_price_dates_from',
            'product': True,
            'variation': True,
            'pricing': True,
            'wp':{
                'key':'lc_wp_sale_price_dates_from',
                'meta':True
            },        
        }),
        ('WPT', {
            'label': 'meta:lc_wp_sale_price_dates_to',
            'product': True,
            'variation': True,
            'pricing': True,
            'wp':{
                'key':'lc_wp_sale_price_dates_to',
                'meta':True
            },        
        }),
        ('DNR', {
            'label': 'meta:lc_dn_regular_price',
            'import': True,
            'product': True,
            'variation': True,
            'pricing': True,
            'wp':{
                'key':'lc_dn_regular_price',
                'meta':True
            },        
        }),
        ('DNS', {
            'label': 'meta:lc_dn_sale_price',
            'product': True,
            'variation': True,
            'pricing': True,
            'wp':{
                'key':'lc_dn_sale_price',
                'meta':True
            },        
        }),
        ('DNF', {
            'label': 'meta:lc_dn_sale_price_dates_from',
            'product': True,
            'variation': True,
            'pricing': True,
            'wp':{
                'key':'lc_dn_sale_price_dates_from',
                'meta':True
            },        
        }),
        ('DNT', {
            'label': 'meta:lc_dn_sale_price_dates_to',
            'product': True,
            'variation': True,
            'pricing': True,
            'wp':{
                'key':'lc_dn_sale_price_dates_to',
                'meta':True
            },        
        }),
        ('DPR', {
            'label': 'meta:lc_dp_regular_price',
            'import': True,
            'product': True,
            'variation': True,
            'pricing': True,
            'wp':{
                'key':'lc_dp_regular_price',
                'meta':True
            },        
        }),
        ('DPS', {
            'label': 'meta:lc_dp_sale_price',
            'product': True,
            'variation': True,
            'pricing': True,
            'wp':{
                'key':'lc_dp_sale_price',
                'meta':True
            },        
        }),
        ('DPF', {
            'label': 'meta:lc_dp_sale_price_dates_from',
            'product': True,
            'variation': True,
            'pricing': True,
            'wp':{
                'key':'lc_dp_sale_price_dates_from',
                'meta':True
            },        
        }),
        ('DPT', {
            'label': 'meta:lc_dp_sale_price_dates_to',
            'product': True,
            'variation': True,
            'pricing': True,
            'wp':{
                'key':'lc_dp_sale_price_dates_to',
                'meta':True
            },        
        }),
        ('CVC', {
            'label': 'meta:commissionable_value',
            'import': True,
            'product': True,
            'variation': True,
            'pricing': True,
            'default': 0,
            'wp':{
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
        }),
        ('manage_stock', {
            'product': True,
            'variation': True,
            'inventory':True,
            'wp':{
                'key':'_manage_stock',
                'meta':True
            },     
        }),
        ('Images',{
            'import': True,
            'default': ''
        }),
        ('HTML Description', {
            'import': True,
        }),
        ('last_import',{
            'label':'meta:last_import',
            'product': True,
        }),
        ('Updated',{
            'import': True,
            'product':True
        }),
        ('post_status', {
            'import':True,
            'product':True,
            'variation':True
        }),
    ])

    def __init__( self, data = None):
        if not data: data = self.data
        super(ColData_Woo, self).__init__( data )

    def getProductCols(self):
        return self.getExportCols('product')

    def getVariationCols(self):
        return self.getExportCols('variation')

    def getCategoryCols(self):
        return self.getExportCols('category')

    def getPricingCols(self):
        return self.getExportCols('pricing')

    def getShippingCols(self):
        return self.getExportCols('shipping')

    def getInventoryCols(self):
        return self.getExportCols('inventory')

    def getWPCols(self):
        return self.getExportCols('wp')

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

    def getAttributeMetaCols(self, vattributes):
        atttributeMetaCols = OrderedDict()
        for attr in vattributes.keys():
            atttributeMetaCols['meta:attribute_'+attr] = {
                'variable': True,
                'tag': attr
            }
        return atttributeMetaCols

class ColData_User(ColData_Base):

    data = OrderedDict([
        ('E-mail', {
            'wp': {
                'meta': False, 
                'key': 'user_email'
            },
            'import': True,
            'user':True,
            'report': True,
            'sync':True,
            'warn':True,
            'static':True,
        }),
        ('Wordpress Username',{
            # 'label':'Username',
            'wp': {
                'meta': False, 
                'key': 'user_login',
                'final': True
            },
            'user':True,
            'report': True,
            'import':True,
            'sync':'slave_override',
            'warn':True,
            'static':True,
        }),
        ('Wordpress ID',{
            # 'label':'Username',
            'wp': {
                'meta': False, 
                'key': 'ID',
                'final': True
            },
            'user':True,
            'report': True,
            'import':True,
            'sync':'slave_override',
            'warn':True,
            'static':True,
        }),
        ('Wordpress Username',{
            # 'label':'Username',
            'wp': {
                'meta': False, 
                'key': 'user_login'
            },
            'user':True,
            'report': True,
            'import':True,
            'sync':'slave_override',
            'warn':True,
            'static':True,
        }),
        ('Role', {
            'wp': {
                'meta': True, 
                'key': 'act_role'
            },
            # 'label': 'act_role',
            'import':True,
            'user':True,
            'report': True,
            'sync':True,
            'warn': True,
            'static':True,
        }),
        ('MYOB Card ID',{
            'wp': {
                'meta': True, 
                'key': 'myob_card_id'
            },
            # 'label':'myob_card_id',
            'import':True,
            'user':True,
            'report':True,
            'sync':'master_override',
            'warn':True,
            'static':True,
        }),
        ('Contact',{
            'import':True,
            'wp': {
                'meta': True, 
                'key': 'nickname'
            },
            # 'label':'contact_name',
            'warn': True,
            'user':True,
            'sync':True,
            "static": True,
            'repor':True,
            'aliases': ['Name Prefix', 'First Name', 'Middle Name', 'Surname', 'Name Suffix', 'Company', 'Name Notes']

        }),
        ('First Name', {
            'wp': {
                'meta': True, 
                'key': 'first_name'
            },
            # 'label':'first_name',
            'import':True,
            'user':True,
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
            # 'label':'last_name',
            'import': True,
            'user':True,
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
            'import': True,
            'user': True,    
        }),
        ('Name Suffix', {
            'wp': {
                'meta': True,
                'key': 'name_suffix'
            },
            'import': True,
            'user': True,    
        }),
        ('Name Prefix', {
            'wp': {
                'meta': True,
                'key': 'name_prefix'
            },
            'import': True,
            'user': True,    
        }),
        ('Company',{
            'wp': {
                'meta': True, 
                'key': 'billing_company'
            },
            # 'label':'billing_company',
            'import':True,
            'user':True,
            # 'report': True,
            # 'sync':True,
            # 'warn': True,
            # 'static':True,
        }),
        ('Mobile Phone',{
            'wp': {
                'meta': True, 
                'key': 'mobile_number'
            },
            # 'label':'mobile_number',
            'import':True,
            'user':True,
            'sync':True,
            'report':True,
            'warn': True,
            'static':True,
        }),
        ('Phone',{
            'wp': {
                'meta': True, 
                'key': 'billing_phone'
            },
            # 'label':'billing_phone',
            'import':True,
            'user':True,
            'report': True,
            'sync':True,
            'warn': True,
            'static':True,
        }),
        ('Birth Date',{
            'wp': {
                'meta': True, 
                'key': 'birth_date'
            },
            # 'label':'birth_date',
            'import':True,
            'user':True,
            'sync':True,
        }),
        ('Fax',{
            'wp': {
                'meta': True, 
                'key': 'fax_number'
            },
            # 'label':'fax_number',
            'import':True,
            'user':True,
            'sync':True,
        }),
        ('MYOB Customer Card ID',{
            # 'label':'myob_customer_card_id',
            'wp': {
                'meta': True, 
                'key': 'myob_customer_card_id'
            },
            'import':True,
            # 'report':True,
            'user':True,
            'sync':'master_override',
            'warn':True,
        }),
        ('Client Grade',{
            'import':True,
            'wp': {
                'meta': True, 
                'key': 'client_grade'
            },
            # 'label':'client_grade',
            'user':True,
            # 'report':True,
            'sync':'master_override',
            'warn':True,
        }),
        ('Direct Brand', {
            'import':True,
            'wp': {
                'meta': True, 
                'key': 'direct_brand'
            },
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
            # 'label':'agent',
            'import':'true',
            'user':True,
            'sync':'master_override',
            'warn':True,
        }),
        ('Address',{
            'report':True,
            'warn':True,
            'static':True,
            'sync':True,
            'aliases':['Address 1', 'Address 2', 'City', 'Postcode', 'State', 'Country']
        }),
        ('Home Address',{
            'report':True,
            'warn':True,
            'static':True,
            'sync':True,
            'aliases':['Home Address 1', 'Home Address 2', 'Home City', 'Home Postcode', 'Home State', 'Home Country']
        }),
        ('Address 1',{
            'wp': {
                'meta': True, 
                'key': 'billing_address_1'
            },
            # 'label':'billing_address_1',
            'import':True,
            'user':True,
            # 'sync':True,
            'warn': True,
            'static':True,
            'capitalized':True,
        }),
        ('Address 2',{
            'wp': {
                'meta': True, 
                'key': 'billing_address_2'
            },
            # 'label':'billing_address_2',
            'import':True,
            'user':True,
            # 'sync':True,
            'warn': True,
            'static':True,
            'capitalized':True,
        }),
        ('City',{
            'wp': {
                'meta': True, 
                'key': 'billing_city'
            },
            # 'label':'billing_city',
            'import':True,
            'user':True,
            # 'sync':True,
            'warn': True,
            'static':True,
            # 'report': True,
            'capitalized':True,
        }),
        ('Postcode',{
            'wp': {
                'meta': True, 
                'key': 'billing_postcode'
            },
            # 'label':'billing_postcode',
            'import':True,
            'user':True,
            # 'sync':True,
            'warn': True,
            'static':True,
            # 'report': True,
        }),
        ('State',{
            'wp': {
                'meta': True, 
                'key': 'billing_state'
            },
            # 'label':'billing_state',
            'import':True,
            'user':True,
            # 'sync':True,
            'warn': True,
            'static':True,
            # 'report':True,
            'capitalized':True,
        }),
        ('Country', {
            'wp': {
                'meta': True, 
                'key': 'billing_country'
            },
            # 'label':'billing_country',
            'import':True,
            'user':True,
            'warn':True,
            'static':True,
            'capitalized':True
        }),
        ('Home Address 1',{
            'wp': {
                'meta': True, 
                'key': 'shipping_address_1'
            },
            # 'label':'shipping_address_1',
            'import':True,
            'user':True,
            # 'sync':True,
            'static':True,
            'capitalized':True,
        }),
        ('Home Address 2',{
            'wp': {
                'meta': True, 
                'key': 'shipping_address_2'
            },
            # 'label':'shipping_address_2',
            'import':True,
            'user':True,
            # 'sync':True,
            'static':True,
            'capitalized':True,
        }),
        ('Home City',{
            'wp': {
                'meta': True, 
                'key': 'shipping_city'
            },
            # 'label':'shipping_city',
            'import':True,
            'user':True,
            # 'sync':True,
            'static':True,
            'capitalized':True,
        }),
        ('Home Postcode',{
            'wp': {
                'meta': True, 
                'key': 'shipping_postcode'
            },
            # 'label':'shipping_postcode',
            'import':True,
            'user':True,
            # 'sync':True,
            'static':True,
        }),
        ('Home Country',{
            'wp': {
                'meta': True, 
                'key': 'shipping_country'
            },
            # 'label':'shipping_country',
            'import':True,
            'user':True,
            # 'sync':True,
            'static':True,
            'capitalized':True,
        }),
        ('Home State',{
            'wp': {
                'meta': True, 
                'key': 'shipping_state'
            },
            # 'label':'shipping_state',
            'import':True,
            'user':True,
            # 'sync':True,
            'static':True,
            'capitalized':True,
        }),
        ('Web Site',{
            'wp': {
                'meta': False, 
                'key': 'user_url'
            },
            'label': 'user_url',
            'import':True,
            'user':True,
            'sync':True,
        }),
        ('ABN',{
            'wp': {
                'meta': True, 
                'key': 'abn'
            },
            # 'label':'abn',
            'import':True,
            'user':True,   
            'sync':True,   
            'warn': True,      
        }),
        ('Business Type',{
            'wp': {
                'meta': True, 
                'key': 'business_type'
            },
            # 'label':'business_type',
            'import':True,
            'user':True,    
            'sync':True,
        }),
        ('Lead Source',{
            'wp': {
                'meta': True, 
                'key': 'how_hear_about'
            },
            # 'label':'how_hear_about',
            'import':True,
            'user':True,    
            'sync':True,
        }),
        ('Referred By',{
            'wp': {
                'meta': True, 
                'key': 'referred_by'
            },
            # 'label':'referred_by',
            'import':True,
            'user':True,
            'sync':True,
        }),
        ('Mobile Phone Preferred',{
            'wp': {
                'meta': True, 
                'key': 'pref_mob'
            },
            # 'label':'pref_mob',
            'import':True,
            'user':True,
            'sync':True,
        }),
        ('Phone Preferred',{
            'wp': {
                'meta': True, 
                'key': 'pref_tel'
            },
            # 'label':'pref_tel',
            'import':True,
            'user':True,
            'sync':True,
        }),
        ('Personal E-mail', {
            'wp': {
                'meta': True, 
                'key': 'personal_email'
            },
            # 'label':'personal_email',
            'import':True,
            'user':True,
            # 'report':True,
        }),
        # ('Nick Name', {
        #     'wp': {
        #         'meta': True, 
        #         'key': 'nickname'
        #     },
        #     # 'label': 'nickname'
        # }),
        # ('rowcount', {
        #     # 'import':True,
        #     # 'user':True,
        #     'report':True,
        # }),
        # ('Editedt Date', {
        #     'import': True,
        #     'report': True
        # }),
        ('Edited in Act', {
            'wp': {
                'meta': True, 
                'key': 'edited_in_act'
            },
            'import': True,
            'report': True
        }),
        ('Edited in Wordpress', {
            'import':True,
            'report':True
        }),
        ('Last Sale', {
            'wp': {
                'meta': True, 
                'key': 'act_last_sale'
            },
            'import': True,
            # 'report': True
        })
    ])

    def __init__(self, data=None):
        if not data: data = self.data
        super(ColData_User, self).__init__(data)

    def getUserCols(self):
        return self.getExportCols('user')

    def getReportCols(self):
        return self.getExportCols('report')

    def getSyncCols(self):
        return self.getExportCols('sync')

    def getCapitalCols(self):
        return self.getExportCols('capitalized')

    def getWPCols(self):
        return self.getExportCols('wp')

    def getAliasCols(self):
        return self.getExportCols('aliases')

if __name__ == '__main__':
    print "Testing ColData_MYO Class:"
    colData = ColData_MYO()
    print colData.getImportCols()
    print colData.getDefaults()
    print colData.getProductCols()

    print ""
    print "Testing ColData_Woo class:"
    colData = ColData_Woo()
    print colData.getImportCols()
    print colData.getDefaults()
    print colData.getProductCols()

    print ""
    print "Testing ColData_User class:"
    colData = ColData_User()
    print "importCols", colData.getImportCols()
    print "userCols", colData.getUserCols().keys()
    print "reportCols", colData.getReportCols().keys()
    print "capitalCols", colData.getCapitalCols().keys()
    print "syncCols", colData.getSyncCols().keys()
    print "wpcols", colData.getWPCols().keys()

    