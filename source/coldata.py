from collections import OrderedDict

class ColData_Base(object):
    """docstring for ColData_Base"""
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
            if data.get('import') and data.get('default'):
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
    """docstring for ColData_MYO"""
    data = OrderedDict([
        ('codesum', {
            'label': 'Item Number',
            'product':True,
        }),
        ('item_name', {
            'label': 'Item Name',
            'product':True,
        }),
        ('WNR', {
            'label': 'Selling Price',
            'import': True,
            'product': True,
            'price': True,
        }),
        ('RNR',{
            'label': 'Price Level B, Qty Break 1',
            'import': True,
            'product': True,
            'price': True,
        }),
        ('DNR',{
            'label': 'Price Level C, Qty Break 1',
            'import': True,
            'product': True,
            'price': True,
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
    """docstring for ColData_Woo"""
    data = OrderedDict([
        ('parent_SKU',{
            'variation':True,
        }),
        ('codesum',{
            'label':'SKU',
            'product': True,
            'variation': True,
            'category': True,
        }),
        ('itemsum', {
            'label':'post_title',
            'product':True, 
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
        }),
        ('E',{
            'import': True,
        }),
        ('DYNCAT', {
            'import':True,
            'category': True,
            'product':True,
        }),
        ('DYNPROD', {
            'import':True,
            'category': True,
            'product':True
        }),
        ('SCHEDULE', {
            'import':True,
            'category':True,
            'product':True,
            'default':''
        }),
        ('spsum', {
            'product':True,
            'variation':True,
        }),
        ('dprclist', {
            'label': 'meta:dynamic_category_rulesets',
            # 'product': True,
            'category': True  
        }),
        ('dprplist', {
            'label': 'meta:dynamic_product_rulesets',
            'product': True,
            # 'category': True
        }),
        ('dprcIDlist', {
            'label': 'meta:dynamic_category_ruleset_IDs',
            # 'product': True,
            'category': True  
        }),
        ('dprpIDlist', {
            'label': 'meta:dynamic_product_ruleset_IDs',
            'product': True,
            # 'category': True
        }),
        ('price', {
            'label':'regular_price',
            'product': True,
            'variation': True,
            'price': True,
        }),
        ('sale_price', {
            'label':'sale_price',
            'product': True,
            'variation': True,
            'price': True,
        }),
        ('sale_price_dates_from', {
            'label':'sale_price_dates_from',
            'product': True,
            'variation': True,
            'price': True,
        }),
        ('sale_price_dates_to', {
            'label':'sale_price_dates_to',
            'product': True,
            'variation': True,
            'price': True,
        }),
        ('RNR', {
            'label': 'meta:lc_rn_regular_price',
            'import': True,
            'product': True,
            'variation': True,
            'price': True,
        }),
        ('RNS', {
            'label': 'meta:lc_rn_sale_price',
            'product': True,
            'variation': True,
            'price': True,
        }),
        ('RNF', {
            'label': 'meta:lc_rn_sale_price_dates_from',
            'product': True,
            'variation': True,
            'price': True,
        }),
        ('RNT', {
            'label': 'meta:lc_rn_sale_price_dates_to',
            'product': True,
            'variation': True,
            'price': True,
        }),
        ('RPR', {
            'label': 'meta:lc_rp_regular_price',
            'import': True,
            'product': True,
            'variation': True,
            'price': True,
        }),
        ('RPS', {
            'label': 'meta:lc_rp_sale_price',
            'product': True,
            'variation': True,
            'price': True,
        }),
        ('RPF', {
            'label': 'meta:lc_rp_sale_price_dates_from',
            'product': True,
            'variation': True,
            'price': True,
        }),
        ('RPT', {
            'label': 'meta:lc_rp_sale_price_dates_to',
            'product': True,
            'variation': True,
            'price': True,
        }),
        ('WNR', {
            'label': 'meta:lc_wn_regular_price',
            'import': True,
            'product': True,
            'variation': True,
            'price': True,
        }),
        ('WNS', {
            'label': 'meta:lc_wn_sale_price',
            'product': True,
            'variation': True,
            'price': True,
        }),
        ('WNF', {
            'label': 'meta:lc_wn_sale_price_dates_from',
            'product': True,
            'variation': True,
            'price': True,
        }),
        ('WNT', {
            'label': 'meta:lc_wn_sale_price_dates_to',
            'product': True,
            'variation': True,
            'price': True,
        }),
        ('WPR', {
            'label': 'meta:lc_wp_regular_price',
            'import': True,
            'product': True,
            'variation': True,
            'price': True,
        }),
        ('WPS', {
            'label': 'meta:lc_wp_sale_price',
            'product': True,
            'variation': True,
            'price': True,
        }),
        ('WPF', {
            'label': 'meta:lc_wp_sale_price_dates_from',
            'product': True,
            'variation': True,
            'price': True,
        }),
        ('WPT', {
            'label': 'meta:lc_wp_sale_price_dates_to',
            'product': True,
            'variation': True,
            'price': True,
        }),
        ('DNR', {
            'label': 'meta:lc_dn_regular_price',
            'import': True,
            'product': True,
            'variation': True,
            'price': True,
        }),
        ('DNS', {
            'label': 'meta:lc_dn_sale_price',
            'product': True,
            'variation': True,
            'price': True,
        }),
        ('DNF', {
            'label': 'meta:lc_dn_sale_price_dates_from',
            'product': True,
            'variation': True,
            'price': True,
        }),
        ('DNT', {
            'label': 'meta:lc_dn_sale_price_dates_to',
            'product': True,
            'variation': True,
            'price': True,
        }),
        ('DPR', {
            'label': 'meta:lc_dp_regular_price',
            'import': True,
            'product': True,
            'variation': True,
            'price': True,
        }),
        ('DPS', {
            'label': 'meta:lc_dp_sale_price',
            'product': True,
            'variation': True,
            'price': True,
        }),
        ('DPF', {
            'label': 'meta:lc_dp_sale_price_dates_from',
            'product': True,
            'variation': True,
            'price': True,
        }),
        ('DPT', {
            'label': 'meta:lc_dp_sale_price_dates_to',
            'product': True,
            'variation': True,
            'price': True,
        }),
        ('CVC', {
            'label': 'meta:commissionable_value',
            'import': True,
            'product': True,
            'variation': True,
            'default': 0
        }),
        ('weight', {
            'import': True,
            'product': True,
            'variation': True,
        }),
        ('length', {
            'import': True,
            'product': True,
            'variation': True,
        }),
        ('width', {
            'import': True,
            'product': True,
            'variation': True,
        }),
        ('height', {
            'import': True,
            'product': True,
            'variation': True,
        }),
        ('stock', {
            'import': True,
            'product': True,
            'variation': True,
        }),
        ('stock_status', {
            'import': True,
            'product': True,
            'variation': True,
        }),
        ('Images',{
            'import': True,
            'default': ''
        }),
        ('HTML Description', {
            'import': True,
        }),
        ('dprcsum', {
            'label': 'meta:DPRC_Table',
            'product': True,   
        }),
        ('dprpsum', {
            'label': 'meta:DPRP_Table',
            'product': True,   
        }),
        ('last_import',{
            'label':'meta:last_import',
            'product': True,
        })
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

    def getAttributeCols(self, attributes):
        attributeCols = OrderedDict()
        for attr in attributes.keys():
            attributeCols['attribute:'+attr] = {}
            attributeCols['attribute_default:'+attr] = {}
            attributeCols['attribute_data:'+attr] = {}
        return attributeCols

    def getAttributeMetaCols(self, attributes):
        atttributeMetaCols = OrderedDict()
        for attr in attributes.keys():
            atttributeMetaCols['meta:attribute_'+attr] = {}
        return atttributeMetaCols

class ColData_User(ColData_Base):
    """docstring for ColData_User"""
    data = OrderedDict([
        ('username',{
            'user':True,
        }),
        ('E-mail', {
            'label':'user_email',
            'import': True,
            'user':True,
        }),
        ('Role', {
            'label': 'act_role',
            'import':True,
            'user':True
        }),
        ('First Name', {
            'label':'first_name',
            'import':True,
            'user':True,
        }),
        ('Surname', {
            'label':'last_name',
            'import': True,
            'user':True,
        }),
        ('Contact',{
            'import':True,
            'label':'nickname',
            'user':True,
        }),
        ('Client Grade',{
            'import':True,
            'label':'client_grade',
            'user':True
        }),
        ('Direct Brand', {
            'import':True,
            'label':'direct_brand',
            'user':True,
        }),
        ('Agent', {
            'label':'agent',
            'import':'true',
            'user':True
        }),
        ('Birth Date',{
            'label':'birth_date',
            'import':True,
            'user':True,
        }),
        ('Mobile Phone',{
            'label':'mobile_number',
            'import':True,
            'user':True,
        }),
        ('Fax',{
            'label':'fax_number',
            'import':True,
            'user':True,
        }),
        ('Company',{
            'label':'billing_company',
            'import':True,
            'user':True,
        }),
        ('Address 1',{
            'label':'billing_address_1',
            'import':True,
            'user':True,
        }),
        ('Address 2',{
            'label':'billing_address_2',
            'import':True,
            'user':True,
        }),
        ('City',{
            'label':'billing_city',
            'import':True,
            'user':True,
        }),
        ('Postcode',{
            'label':'billing_postcode',
            'import':True,
            'user':True,
        }),
        ('State',{
            'label':'billing_state',
            'import':True,
            'user':True,
        }),
        ('Phone',{
            'label':'billing_phone',
            'import':True,
            'user':True,
        }),
        ('Home Address 1',{
            'label':'shipping_address_1',
            'import':True,
            'user':True,
        }),
        ('Home Address 2',{
            'label':'shipping_address_2',
            'import':True,
            'user':True,
        }),
        ('Home City',{
            'label':'shipping_city',
            'import':True,
            'user':True,
        }),
        ('Home Postcode',{
            'label':'shipping_postcode',
            'import':True,
            'user':True,
        }),
        ('Home Country',{
            'label':'shipping_country',
            'import':True,
            'user':True,
        }),
        ('Home State',{
            'label':'shipping_state',
            'import':True,
            'user':True,
        }),
        ('MYOB Card ID',{
            'label':'myob_card_id',
            'import':True,
            'user':True,
        }),
        ('MYOB Customer Card ID',{
            'label':'myob_customer_card_id',
            'import':True,
            'user':True,
        }),
        ('Web Site',{
            'label':'url',
            'import':True,
            'user':True,
        }),
        ('ABN',{
            'label':'abn',
            'import':True,
            'user':True,            
        }),
        ('Business Type',{
            'label':'business_type',
            'import':True,
            'user':True,    
        }),
        ('Lead Source',{
            'label':'how_hear_about',
            'import':True,
            'user':True,    
        }),
        ('Referred By',{
            'label':'referred_by',
            'import':True,
            'user':True,
        }),
        ('Mobile Phone Preferred',{
            'label':'pref_mob',
            'import':True,
            'user':True,
        }),
        ('Phone Preferred',{
            'label':'pref_tel',
            'import':True,
            'user':True,
        })
    ])

    def __init__(self, data=None):
        if not data: data = self.data
        super(ColData_User, self).__init__(data)

    def getUserCols(self):
        return self.getExportCols('user')
        

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
    