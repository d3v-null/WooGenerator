"""
Utility for keeping track of column metadata for translating between databases.
"""

from __future__ import absolute_import

from collections import OrderedDict

from .utils import SeqUtils


class ColDataBase(object):
    data = OrderedDict()

    def __init__(self, data):
        super(ColDataBase, self).__init__()
        assert issubclass(
            type(data), dict), "Data should be a dictionary subclass"
        self.data = data

    @classmethod
    def get_import_cols(cls):
        imports = []
        for col, data in cls.data.items():
            if data.get('import', False):
                imports.append(col)
        return imports

    @classmethod
    def get_defaults(cls):
        defaults = {}
        for col, data in cls.data.items():
            # Registrar.register_message('col is %s' % col)
            if 'default' in data:
                # Registrar.register_message('has default')
                defaults[col] = data.get('default')
            else:
                pass
                # Registrar.register_message('does not have default')
        return defaults

    @classmethod
    def get_export_cols(cls, schema=None):
        if not schema:
            return None
        export_cols = OrderedDict()
        for col, data in cls.data.items():
            if data.get(schema, ''):
                export_cols[col] = data
        return export_cols

    @classmethod
    def get_basic_cols(cls):
        return cls.get_export_cols('basic')

    @classmethod
    def get_delta_cols(cls):
        cols = OrderedDict()
        for col, data in cls.data.items():
            if data.get('delta'):
                cols[col] = cls.delta_col(col)
        return cols

    @classmethod
    def get_col_names(cls, cols):
        col_names = OrderedDict()
        for col, data in cols.items():
            label = data.get('label', '')
            col_names[col] = label if label else col
        return col_names

    @classmethod
    def name_cols(cls, cols):
        return OrderedDict(
            [(col, {}) for col in cols]
        )

    @classmethod
    def get_report_cols(cls):
        return cls.get_export_cols('report')

    @classmethod
    def get_wpapi_cols(cls, api='wp-api'):
        return cls.get_export_cols(api)

    @classmethod
    def get_wpapi_variable_cols(cls):
        cols = OrderedDict()
        for col, data in cls.get_wpapi_cols().items():
            if 'sync' in data:
                if data.get('sync') == 'not_variable':
                    continue
            cols[col] = data
        return cols

    @classmethod
    def get_wpapi_core_cols(cls, api='wp-api'):
        export_cols = cls.get_export_cols(api)
        api_cols = OrderedDict()
        for col, data in export_cols.items():
            api_data = data.get(api, {})
            if hasattr(api_data, '__getitem__') \
                    and not api_data.get('meta'):
                api_cols[col] = data

        return api_cols

    @classmethod
    def get_wpapi_meta_cols(cls, api='wp-api'):
        # export_cols = cls.get_export_cols(api)
        api_cols = OrderedDict()
        for col, data in cls.data.items():
            api_data = data.get(api, {})
            if hasattr(api_data, '__getitem__') \
                    and api_data.get('meta') is not None:
                if api_data.get('meta'):
                    api_cols[col] = data
            else:
                backup_api_data = data.get('wp', {})
                if hasattr(backup_api_data, '__getitem__') \
                        and backup_api_data.get('meta') is not None:
                    if backup_api_data.get('meta'):
                        api_cols[col] = data
        return api_cols

    @classmethod
    def get_wpapi_category_cols(cls, api='wp-api'):
        export_cols = cls.get_export_cols(api)
        api_category_cols = OrderedDict()
        for col, data in export_cols.items():
            if data.get('category', ''):
                api_category_cols[col] = data
        return api_category_cols

    @classmethod
    def get_wpapi_import_cols(cls, api='wp-api'):
        export_cols = cls.get_export_cols('import')
        api_import_cols = OrderedDict()
        for col, data in export_cols.items():
            key = col
            if api in data and 'key' in data[api]:
                key = data[api]['key']
            api_import_cols[key] = data
        return api_import_cols

    @classmethod
    def get_sync_cols(cls):
        return cls.get_export_cols('sync')

    @classmethod
    def delta_col(cls, col):
        return 'Delta ' + col


class ColDataProd(ColDataBase):
    data = OrderedDict([
        ('codesum', {
            'label': 'SKU',
            'product': True,
            'report': True
        }),
        ('itemsum', {
            'label': 'Name',
            'product': True,
            'report': True
        }),
        ('descsum', {
            'label': 'Description',
            'product': True,
            'report': True,
        }),
        ('WNR', {
            'product': True,
            'report': True,
            'pricing': True,
        }),
        ('RNR', {
            'product': True,
            'report': True,
            'pricing': True,
        }),
        ('DNR', {
            'product': True,
            'report': True,
            'pricing': True,
        }),
        ('weight', {
            'import': True,
            'product': True,
            'variation': True,
            'shipping': True,
            'wp': {
                'key': '_weight',
                'meta': True
            },
            'wp-api': True,
            'sync': True,
            'report': True
        }),
        ('length', {
            'import': True,
            'product': True,
            'variation': True,
            'shipping': True,
            'wp': {
                'key': '_length',
                'meta': True
            },
            'sync': True,
            'report': True
        }),
        ('width', {
            'import': True,
            'product': True,
            'variation': True,
            'shipping': True,
            'wp': {
                'key': '_width',
                'meta': True
            },
            'sync': True,
            'report': True
        }),
        ('height', {
            'import': True,
            'product': True,
            'variation': True,
            'shipping': True,
            'wp': {
                'key': '_height',
                'meta': True
            },
            'sync': True,
            'report': True
        }),
    ])


class ColDataMyo(ColDataProd):

    data = OrderedDict(ColDataProd.data.items() + [
        ('codesum', {
            'label': 'Item Number',
            'product': True,
        }),
        ('itemsum', {
            'label': 'Item Name',
            'product': True,
            'report': True,
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
            'report': True,
        }),
        ('HTML Description', {
            'import': True,
        }),
        ('Sell', {
            'default': 'S',
            'product': True,
        }),
        ('Tax Code When Sold', {
            'default': 'GST',
            'product': True,
        }),
        ('Sell Price Inclusive', {
            'default': 'X',
            'product': True,
        }),
        ('Income Acct', {
            'default': '41000',
            'product': True,
        }),
        ('Inactive Item', {
            'default': 'N',
            'product': True,
        }),
        ('use_desc', {
            'label': 'Use Desc. On Sale',
            'default': 'X',
            'product': True
        })
    ])

    def __init__(self, data=None):
        if not data:
            data = self.data
        super(ColDataMyo, self).__init__(data)

    @classmethod
    def get_product_cols(cls):
        return cls.get_export_cols('product')


class ColDataWoo(ColDataProd):

    data = OrderedDict(ColDataProd.data.items() + [
        ('ID', {
            'category': True,
            'product': True,
            'wp': {
                'key': 'ID',
                'meta': False
            },
            'wp-api': {
                'key': 'id'
            },
            'report': True,
            'sync': 'slave_override',
        }),
        ('parent_SKU', {
            'variation': True,
        }),
        ('parent_id', {
            'category': True,
            'wp-api': {
                'key': 'parent'
            }
        }),
        ('codesum', {
            'label': 'SKU',
            'tag': 'SKU',
            'product': True,
            'variation': True,
            'category': True,
            'wp': {
                'key': '_sku',
                'meta': True
            },
            'wp-api': {
                'key': 'sku'
            },
            'report': True,
            'sync': True
        }),
        ('slug', {
            'category': True,
            'wp-api': {
                'key': 'slug'
            },
            'sync': 'slave_override'
        }),
        ('display', {
            'category': True,
            'wp-api': True,
        }),
        ('itemsum', {
            'tag': 'Title',
            'label': 'post_title',
            'product': True,
            'variation': True,
            'wp': {
                'key': 'post_title',
                'meta': False
            },
            'wp-api': {
                'key': 'title',
                'meta': False
            },
            'wp-api-wc-v1': {
                'key': 'title',
                'meta': False
            },
            'report': True,
            'sync': 'not_variable',
            'static': True,
        }),
        ('title', {
            'category': True,
            'wp-api': {
                'key': 'name',
                'meta': False
            },
            # 'sync':True
        }),
        ('title_1', {
            'label': 'meta:title_1',
            'product': True,
            'wp': {
                'key': 'title_1',
                'meta': True
            }
        }),
        ('title_2', {
            'label': 'meta:title_2',
            'product': True,
            'wp': {
                'key': 'title_2',
                'meta': True
            }
        }),
        ('taxosum', {
            'label': 'category_title',
            'category': True,
        }),
        ('catlist', {
            'product': True,
            'wp-api': {
                'key': 'categories'
            },
            # 'sync':'not_variable'
        }),
        # ('catids', {
        # }),
        ('prod_type', {
            'label': 'tax:product_type',
            'product': True,
            'wp-api': {
                'key': 'type'
            }
        }),
        ('catsum', {
            'label': 'tax:product_cat',
            'product': True,
        }),
        ('descsum', {
            'label': 'post_content',
            'tag': 'Description',
            'product': True,
            'sync': 'not_variable'
        }),
        ('HTML Description', {
            'import': True,
            'category': True,
            'wp-api': {
                'key': 'description'
            },
        }),
        ('imgsum', {
            'label': 'Images',
            'product': True,
            'variation': True,
            'category': True,
        }),
        ('rowcount', {
            'label': 'menu_order',
            'product': True,
            'category': True,
            'variation': True,
            'wp-api': {
                'key': 'menu_order'
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
            'wp-api': {
                'key': 'wootan_danger',
                'meta': True
            },
            'sync': True
        }),
        ('E', {
            'import': True,
        }),
        ('DYNCAT', {
            'import': True,
            'category': True,
            'product': True,
            'pricing': True,
        }),
        ('DYNPROD', {
            'import': True,
            'category': True,
            'product': True,
            'pricing': True,
        }),
        ('VISIBILITY', {
            'import': True,
        }),
        ('catalog_visibility', {
            'product': True,
            'default': 'visible'
        }),
        ('SCHEDULE', {
            'import': True,
            'category': True,
            'product': True,
            'pricing': True,
            'default': ''
        }),
        ('spsum', {
            'tag': 'active_specials',
            'product': True,
            'variation': True,
            'pricing': True,
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
            'pricing': True,
            'wp': {
                'key': 'pricing_rules',
                'meta': False
            },
            'product': True,
        }),
        ('price', {
            'label': 'regular_price',
            'product': True,
            'variation': True,
            'pricing': True,
            'wp': {
                'key': '_regular_price',
                'meta': True
            },
            'wp-api': {
                'key': 'regular_price'
            },
            'report': True,
            'static': True,
            'type': 'currency',
        }),
        ('sale_price', {
            'label': 'sale_price',
            'product': True,
            'variation': True,
            'pricing': True,
            'wp': {
                'key': '_sale_price',
                'meta': True
            },
            'wp-api': True,
            'report': True,
            'type': 'currency',
        }),
        ('sale_price_dates_from', {
            'label': 'sale_price_dates_from',
            'tag': 'sale_from',
            'product': True,
            'variation': True,
            'pricing': True,
            'wp': {
                'key': '_sale_price_dates_from',
                'meta': True
            },
            'wp-api': {
                'key': 'regular_price'
            },
        }),
        ('sale_price_dates_to', {
            'label': 'sale_price_dates_to',
            'tag': 'sale_to',
            'product': True,
            'variation': True,
            'pricing': True,
            'wp': {
                'key': '_sale_price_dates_to',
                'meta': True
            },
        }),
        ('RNR', {
            'label': 'meta:lc_rn_regular_price',
            'sync': True,
            'import': True,
            'product': True,
            'variation': True,
            'pricing': True,
            'wp': {
                'key': 'lc_rn_regular_price',
                'meta': True
            },
            'wp-api': {
                'key': 'lc_rn_regular_price',
                'meta': True
            },
            'static': True,
            'type': 'currency',
        }),
        ('RNS', {
            'label': 'meta:lc_rn_sale_price',
            'sync': True,
            'product': True,
            'variation': True,
            'pricing': True,
            'wp': {
                'key': 'lc_rn_sale_price',
                'meta': True
            },
            'wp-api': {
                'key': 'lc_rn_sale_price',
                'meta': True
            },
            'type': 'currency',
        }),
        ('RNF', {
            'label': 'meta:lc_rn_sale_price_dates_from',
            'sync': True,
            'product': True,
            'variation': True,
            'pricing': True,
            'wp': {
                'key': 'lc_rn_sale_price_dates_from',
                'meta': True
            },
            'wp-api': {
                'key': 'lc_rn_sale_price_dates_from',
                'meta': True
            },
        }),
        ('RNT', {
            'label': 'meta:lc_rn_sale_price_dates_to',
            'sync': True,
            'product': True,
            'variation': True,
            'pricing': True,
            'wp': {
                'key': 'lc_rn_sale_price_dates_to',
                'meta': True
            },
            'wp-api': {
                'key': 'lc_rn_sale_price_dates_to',
                'meta': True
            },
        }),
        ('RPR', {
            'label': 'meta:lc_rp_regular_price',
            'sync': True,
            'import': True,
            'product': True,
            'variation': True,
            'pricing': True,
            'wp': {
                'key': 'lc_rp_regular_price',
                'meta': True
            },
            'wp-api': {
                'key': 'lc_rp_regular_price',
                'meta': True
            },
            'static': True,
            'type': 'currency',
        }),
        ('RPS', {
            'label': 'meta:lc_rp_sale_price',
            'sync': True,
            'product': True,
            'variation': True,
            'pricing': True,
            'wp': {
                'key': 'lc_rp_sale_price',
                'meta': True
            },
            'wp-api': {
                'key': 'lc_rp_sale_price',
                'meta': True
            },
            'type': 'currency',
        }),
        ('RPF', {
            'label': 'meta:lc_rp_sale_price_dates_from',
            'sync': True,
            'product': True,
            'variation': True,
            'pricing': True,
            'wp': {
                'key': 'lc_rp_sale_price_dates_from',
                'meta': True
            },
            'wp-api': {
                'key': 'lc_rp_sale_price_dates_from',
                'meta': True
            },
        }),
        ('RPT', {
            'label': 'meta:lc_rp_sale_price_dates_to',
            'sync': True,
            'product': True,
            'variation': True,
            'pricing': True,
            'wp': {
                'key': 'lc_rp_sale_price_dates_to',
                'meta': True
            },
            'wp-api': {
                'key': 'lc_rp_sale_price_dates_to',
                'meta': True
            },
        }),
        ('WNR', {
            'label': 'meta:lc_wn_regular_price',
            'sync': True,
            'import': True,
            'product': True,
            'variation': True,
            'pricing': True,
            'wp': {
                'key': 'lc_wn_regular_price',
                'meta': True
            },
            'wp-api': {
                'key': 'lc_wn_regular_price',
                'meta': True
            },
            'static': True,
            'type': 'currency',
        }),
        ('WNS', {
            'label': 'meta:lc_wn_sale_price',
            'sync': True,
            'product': True,
            'variation': True,
            'pricing': True,
            'wp': {
                'key': 'lc_wn_sale_price',
                'meta': True
            },
            'wp-api': {
                'key': 'lc_wn_sale_price',
                'meta': True
            },
            'type': 'currency',
        }),
        ('WNF', {
            'label': 'meta:lc_wn_sale_price_dates_from',
            'sync': True,
            'product': True,
            'variation': True,
            'pricing': True,
            'wp': {
                'key': 'lc_wn_sale_price_dates_from',
                'meta': True
            },
            'wp-api': {
                'key': 'lc_wn_sale_price_dates_from',
                'meta': True
            },
        }),
        ('WNT', {
            'label': 'meta:lc_wn_sale_price_dates_to',
            'sync': True,
            'product': True,
            'variation': True,
            'pricing': True,
            'wp': {
                'key': 'lc_wn_sale_price_dates_to',
                'meta': True
            },
            'wp-api': {
                'key': 'lc_wn_sale_price_dates_to',
                'meta': True
            },
        }),
        ('WPR', {
            'label': 'meta:lc_wp_regular_price',
            'sync': True,
            'import': True,
            'product': True,
            'variation': True,
            'pricing': True,
            'wp': {
                'key': 'lc_wp_regular_price',
                'meta': True
            },
            'wp-api': {
                'key': 'lc_wp_regular_price',
                'meta': True
            },
            'static': True,
            'type': 'currency',
        }),
        ('WPS', {
            'label': 'meta:lc_wp_sale_price',
            'sync': True,
            'product': True,
            'variation': True,
            'pricing': True,
            'wp': {
                'key': 'lc_wp_sale_price',
                'meta': True
            },
            'wp-api': {
                'key': 'lc_wp_sale_price',
                'meta': True
            },
            'type': 'currency',
        }),
        ('WPF', {
            'label': 'meta:lc_wp_sale_price_dates_from',
            'sync': True,
            'product': True,
            'variation': True,
            'pricing': True,
            'wp': {
                'key': 'lc_wp_sale_price_dates_from',
                'meta': True
            },
            'wp-api': {
                'key': 'lc_wp_sale_price_dates_from',
                'meta': True
            },
        }),
        ('WPT', {
            'label': 'meta:lc_wp_sale_price_dates_to',
            'sync': True,
            'product': True,
            'variation': True,
            'pricing': True,
            'wp': {
                'key': 'lc_wp_sale_price_dates_to',
                'meta': True
            },
            'wp-api': {
                'key': 'lc_wp_sale_price_dates_to',
                'meta': True
            },
        }),
        ('DNR', {
            'label': 'meta:lc_dn_regular_price',
            'sync': True,
            'import': True,
            'product': True,
            'variation': True,
            'pricing': True,
            'wp': {
                'key': 'lc_dn_regular_price',
                'meta': True
            },
            'wp-api': {
                'key': 'lc_dn_regular_price',
                'meta': True
            },
            'static': True,
            'type': 'currency',
        }),
        ('DNS', {
            'label': 'meta:lc_dn_sale_price',
            'sync': True,
            'product': True,
            'variation': True,
            'pricing': True,
            'wp': {
                'key': 'lc_dn_sale_price',
                'meta': True
            },
            'wp-api': {
                'key': 'lc_dn_sale_price',
                'meta': True
            },
            'type': 'currency',
        }),
        ('DNF', {
            'label': 'meta:lc_dn_sale_price_dates_from',
            'sync': True,
            'product': True,
            'variation': True,
            'pricing': True,
            'wp': {
                'key': 'lc_dn_sale_price_dates_from',
                'meta': True
            },
            'wp-api': {
                'key': 'lc_dn_sale_price_dates_from',
                'meta': True
            },
        }),
        ('DNT', {
            'label': 'meta:lc_dn_sale_price_dates_to',
            'sync': True,
            'product': True,
            'variation': True,
            'pricing': True,
            'wp': {
                'key': 'lc_dn_sale_price_dates_to',
                'meta': True
            },
            'wp-api': {
                'key': 'lc_dn_sale_price_dates_to',
                'meta': True
            },
        }),
        ('DPR', {
            'label': 'meta:lc_dp_regular_price',
            'sync': True,
            'import': True,
            'product': True,
            'variation': True,
            'pricing': True,
            'wp': {
                'key': 'lc_dp_regular_price',
                'meta': True
            },
            'wp-api': {
                'key': 'lc_dp_regular_price',
                'meta': True
            },
            'static': True,
            'type': 'currency',
        }),
        ('DPS', {
            'label': 'meta:lc_dp_sale_price',
            'sync': True,
            'product': True,
            'variation': True,
            'pricing': True,
            'wp': {
                'key': 'lc_dp_sale_price',
                'meta': True
            },
            'wp-api': {
                'key': 'lc_dp_sale_price',
                'meta': True
            },
            'type': 'currency',
        }),
        ('DPF', {
            'label': 'meta:lc_dp_sale_price_dates_from',
            'sync': True,
            'product': True,
            'variation': True,
            'pricing': True,
            'wp': {
                'key': 'lc_dp_sale_price_dates_from',
                'meta': True
            },
            'wp-api': {
                'key': 'lc_dp_sale_price_dates_from',
                'meta': True
            },
        }),
        ('DPT', {
            'label': 'meta:lc_dp_sale_price_dates_to',
            'sync': True,
            'product': True,
            'variation': True,
            'pricing': True,
            'wp': {
                'key': 'lc_dp_sale_price_dates_to',
                'meta': True
            },
            'wp-api': {
                'key': 'lc_dp_sale_price_dates_to',
                'meta': True
            },
        }),
        ('CVC', {
            'label': 'meta:commissionable_value',
            'sync': True,
            'import': True,
            'product': True,
            'variation': True,
            'pricing': True,
            'default': 0,
            'wp': {
                'key': 'commissionable_value',
                'meta': True
            },
            'wp-api': {
                'key': 'commissionable_value',
                'meta': True
            },
        }),
        ('weight', {
            'import': True,
            'product': True,
            'variation': True,
            'shipping': True,
            'wp': {
                'key': '_weight',
                'meta': True
            },
            'wp-api': {
                'key': 'weight'
            },
            'sync': True
        }),
        ('length', {
            'import': True,
            'product': True,
            'variation': True,
            'shipping': True,
            'wp': {
                'key': '_length',
                'meta': True
            },
            'sync': True
        }),
        ('width', {
            'import': True,
            'product': True,
            'variation': True,
            'shipping': True,
            'wp': {
                'key': '_width',
                'meta': True
            },
            'sync': True
        }),
        ('height', {
            'import': True,
            'product': True,
            'variation': True,
            'shipping': True,
            'wp': {
                'key': '_height',
                'meta': True
            },
            'sync': True
        }),
        ('stock', {
            'import': True,
            'product': True,
            'variation': True,
            'inventory': True,
            'wp': {
                'key': '_stock',
                'meta': True
            },
            'sync': True,
            'wp-api': {
                'key': 'stock_quantity'
            }
        }),
        ('stock_status', {
            'import': True,
            'product': True,
            'variation': True,
            'inventory': True,
            'wp': {
                'key': '_stock_status',
                'meta': True
            },
            'sync': True
        }),
        ('manage_stock', {
            'product': True,
            'variation': True,
            'inventory': True,
            'wp': {
                'key': '_manage_stock',
                'meta': True
            },
            'wp-api': {
                'key': 'manage_stock'
            },
            'sync': True,
            'default': 'no'
        }),
        ('Images', {
            'import': True,
            'default': ''
        }),
        ('last_import', {
            'label': 'meta:last_import',
            'product': True,
        }),
        ('Updated', {
            'import': True,
            'product': True,
            'wp-api': {
                'key': 'updated_at'
            }
        }),
        ('post_status', {
            'import': True,
            'product': True,
            'variation': True,
            'wp-api': {
                'key': 'status'
            },
            'sync': True,
            'default': 'publish'
        }),
    ])

    def __init__(self, data=None):
        if not data:
            data = self.data
        super(ColDataWoo, self).__init__(data)

    @classmethod
    def get_product_cols(cls):
        return cls.get_export_cols('product')

    @classmethod
    def get_variation_cols(cls):
        return cls.get_export_cols('variation')

    @classmethod
    def get_category_cols(cls):
        return cls.get_export_cols('category')

    @classmethod
    def get_pricing_cols(cls):
        return cls.get_export_cols('pricing')

    @classmethod
    def get_shipping_cols(cls):
        return cls.get_export_cols('shipping')

    @classmethod
    def get_inventory_cols(cls):
        return cls.get_export_cols('inventory')

    @classmethod
    def get_wp_cols(cls):
        return cls.get_export_cols('wp')

    @classmethod
    def get_attribute_cols(cls, attributes, vattributes):
        attribute_cols = OrderedDict()
        all_attrs = SeqUtils.combine_lists(
            attributes.keys(), vattributes.keys())
        for attr in all_attrs:
            attribute_cols['attribute:' + attr] = {
                'product': True,
            }
            if attr in vattributes.keys():
                attribute_cols['attribute_default:' + attr] = {
                    'product': True,
                }
                attribute_cols['attribute_data:' + attr] = {
                    'product': True,
                }
        return attribute_cols

    @classmethod
    def get_attribute_meta_cols(cls, vattributes):
        atttribute_meta_cols = OrderedDict()
        for attr in vattributes.keys():
            atttribute_meta_cols['meta:attribute_' + attr] = {
                'variable': True,
                'tag': attr
            }
        return atttribute_meta_cols


class ColDataUser(ColDataBase):
    # modTimeSuffix = ' Modified'

    modMapping = {
        'Home Address': 'Alt Address',
    }

    @classmethod
    def mod_time_col(cls, col):
        if col in cls.modMapping:
            col = cls.modMapping[col]
        return 'Edited ' + col

    wpdbPKey = 'Wordpress ID'

    data = OrderedDict([
        ('MYOB Card ID', {
            'wp': {
                'meta': True,
                'key': 'myob_card_id'
            },
            'wp-api': {
                'meta': True,
                'key': 'myob_card_id'
            },
            'act': True,
            # 'label':'myob_card_id',
            'import': True,
            'user': True,
            'report': True,
            'sync': 'master_override',
            'warn': True,
            'static': True,
            'basic': True,
        }),
        ('E-mail', {
            'wp': {
                'meta': False,
                'key': 'user_email'
            },
            'wp-api': {
                'meta': False,
                'key': 'email'
            },
            'act': True,
            'import': True,
            'user': True,
            'report': True,
            'sync': True,
            'warn': True,
            'static': True,
            'basic': True,
            'tracked': True,
            'delta': True,
        }),
        ('Wordpress Username', {
            # 'label':'Username',
            'wp': {
                'meta': False,
                'key': 'user_login',
                'final': True
            },
            'wp-api': {
                'meta': False,
                'key': 'username'
            },
            'act': True,
            'user': True,
            'report': True,
            'import': True,
            'sync': 'slave_override',
            'warn': True,
            'static': True,
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
            'wp-api': {
                'key': 'id',
                'meta': False
            },
            'act': False,
            'user': True,
            'report': True,
            'import': True,
            # 'sync':'slave_override',
            'warn': True,
            'static': True,
            'basic': True,
            'default': '',
            # 'tracked':True,
        }),
        ('Role Info', {
            'aliases': [
                'Role',
                'Direct Brand'
            ],
            'sync': True,
            'static': True,
            'basic': True,
            'report': True,
            'delta': True,
            # 'tracked': True,
            'reflective': 'master',
            'user':True,
        }),
        ('Role', {
            'wp': {
                'meta': True,
                'key': 'act_role'
            },
            'wp-api': {
                'meta': True,
                'key': 'act_role'
            },
            # 'label': 'act_role',
            'import': True,
            'act': True,
            # 'user': True,
            # 'report': True,
            # 'sync': True,
            'warn': True,
            'static': True,
            # 'tracked':'future',
        }),
        ('Direct Brand', {
            'import': True,
            'wp': {
                'meta': True,
                'key': 'direct_brand'
            },
            'wp-api': {
                'meta': True,
                'key': 'direct_brand'
            },
            'act': True,
            # 'label':'direct_brand',
            # 'user': True,
            # 'report': True,
            # 'sync': 'master_override',
            'warn': True,
        }),

        ('Name', {
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
            'user': True,
            'sync': True,
            'static': True,
            'basic': True,
            'report': True,
            'tracked': True,
            'invincible': True,
        }),
        ('Contact', {
            'import': True,
            'wp': {
                'meta': False,
                'key': 'display_name'
            },
            'wp-api': {
                'meta': False,
                'key': 'name'
            },
            'act': True,
            'mutable': True,
            'visible': True,
            # 'label':'contact_name',
            # 'warn': True,
            # 'user':True,
            # 'sync':True,
            # "static": True,
            # 'report':True,
            'default':'',
        }),
        ('First Name', {
            'wp': {
                'meta': True,
                'key': 'first_name'
            },
            'wp-api': {
                'meta': False,
                'key': 'first_name'
            },
            'act': True,
            'mutable': True,
            'visible': True,
            # 'label':'first_name',
            'import': True,
            'invincible': 'master',
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
            'wp-api': {
                'meta': False,
                'key': 'last_name'
            },
            'act': True,
            'mutable': True,
            # 'label':'last_name',
            'import': True,
            'visible': True,
            'invincible': 'master',
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
            'wp-api': {
                'meta': True,
                'key': 'middle_name'
            },
            'act': True,
            'import': True,
            'mutable': True,
            'visible': True,
            # 'user': True,
            'default':'',
        }),
        ('Name Suffix', {
            'wp': {
                'meta': True,
                'key': 'name_suffix'
            },
            'wp-api': {
                'meta': True,
                'key': 'name_suffix'
            },
            'act': True,
            'import': True,
            'visible': True,
            # 'user': True,
            'mutable': True,
            'default':'',
        }),
        ('Name Prefix', {
            'wp': {
                'meta': True,
                'key': 'name_prefix'
            },
            'wp-api': {
                'meta': True,
                'key': 'name_prefix'
            },
            'act': True,
            'import': True,
            'visible': True,
            # 'user': True,
            'mutable': True,
            'default':'',
        }),
        ('Memo', {
            'wp': {
                'meta': True,
                'key': 'name_notes'
            },
            'wp-api': {
                'meta': True,
                'key': 'name_notes'
            },
            'act': True,
            'import': True,
            'tracked': True,
        }),
        ('Spouse', {
            'wp': {
                'meta': True,
                'key': 'spouse'
            },
            'wp-api': {
                'meta': True,
                'key': 'spouse'
            },
            'act': True,
            'import': True,
            'tracked': 'future',
            'default':'',
        }),
        ('Salutation', {
            'wp': {
                'meta': True,
                'key': 'nickname'
            },
            'wp-api': {
                'meta': True,
                'key': 'nickname'
            },
            'act': True,
            'import': True,
            'default':'',
        }),

        ('Company', {
            'wp': {
                'meta': True,
                'key': 'billing_company'
            },
            'wp-api': {
                'meta': True,
                'key': 'billing_company'
            },
            'act': True,
            # 'label':'billing_company',
            'import': True,
            'user': True,
            'basic': True,
            'report': True,
            'sync': True,
            'warn': True,
            'static': True,
            # 'visible':True,
            'tracked': True,
        }),


        ('Phone Numbers', {
            'tracked': 'future',
            'aliases': ['Mobile Phone', 'Phone', 'Fax'],
            # 'Mobile Phone Preferred', 'Phone Preferred', ]
            'basic': True,
            'report': True,
        }),

        ('Mobile Phone', {
            'wp': {
                'meta': True,
                'key': 'mobile_number'
            },
            'wp-api': {
                'meta': True,
                'key': 'mobile_number'
            },
            'act': True,
            # 'label':'mobile_number',
            'import': True,
            'user': True,
            'sync': True,
            'warn': True,
            'static': True,
            'invincible':'master',
            # 'visible':True,
            'contact': True,
        }),
        ('Phone', {
            'wp': {
                'meta': True,
                'key': 'billing_phone'
            },
            'wp-api': {
                'meta': True,
                'key': 'billing_phone'
            },
            'act': True,
            # 'label':'billing_phone',
            'import': True,
            'user': True,
            # 'report': True,
            'sync': True,
            'warn': True,
            'static': True,
            'invincible':'master',
            # 'visible':True,
        }),
        ('Fax', {
            'wp': {
                'meta': True,
                'key': 'fax_number'
            },
            'wp-api': {
                'meta': True,
                'key': 'fax_number'
            },
            'act': True,
            # 'label':'fax_number',
            'import': True,
            'user': True,
            'sync': True,
            'contact': True,
            'visible': True,
            'mutable': True,
        }),
        ('Mobile Phone Preferred', {
            'wp': {
                'meta': True,
                'key': 'pref_mob'
            },
            'wp-api': {
                'meta': True,
                'key': 'pref_mob'
            },
            'act': {
                'options':['True', 'False']
            },
            # 'label':'pref_mob',
            'import': True,
            'user': True,
            'sync': True,
            'visible': True,
            'mutable': True,
            'invincible':'master',
        }),
        ('Phone Preferred', {
            'wp': {
                'meta': True,
                'key': 'pref_tel'
            },
            'wp-api': {
                'meta': True,
                'key': 'pref_tel'
            },
            'act': {
                'options':['True', 'False']
            },
            # 'label':'pref_tel',
            'import': True,
            'user': True,
            'sync': True,
            'visible': True,
            'mutable': True,
            'invincible':'master',
        }),
        # TODO: implement pref method
        # ('Pref Method', {
        #     'wp': False,
        #     'wp-api': False,
        #     'import': False,
        #     'sync': ''
        # }),
        ('Address', {
            'act': False,
            'wp': False,
            'report': True,
            'warn': True,
            'static': True,
            'sync': True,
            'aliases': ['Address 1', 'Address 2', 'City', 'Postcode', 'State', 'Country', 'Shire'],
            'basic': True,
            'tracked': True,
        }),
        ('Home Address', {
            'act': False,
            'wp': False,
            'report': True,
            'warn': True,
            'static': True,
            'sync': True,
            'basic': True,
            'aliases': [
                'Home Address 1', 'Home Address 2', 'Home City', 'Home Postcode',
                'Home State', 'Home Country'
            ],
            'tracked': 'future',
        }),
        ('Address 1', {
            'wp': {
                'meta': True,
                'key': 'billing_address_1'
            },
            'wp-api': {
                'meta': True,
                'key': 'billing_address_1'
            },
            'act': True,
            # 'label':'billing_address_1',
            'import': True,
            'user': True,
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
            'wp-api': {
                'meta': True,
                'key': 'billing_address_2'
            },
            'act': True,
            # 'label':'billing_address_2',
            'import': True,
            'user': True,
            # 'sync':True,
            # 'warn': True,
            # 'static':True,
            # 'capitalized':True,
            # 'visible':True,
            'default':'',
        }),
        ('City', {
            'wp': {
                'meta': True,
                'key': 'billing_city'
            },
            'wp-api': {
                'meta': True,
                'key': 'billing_city'
            },
            'act': True,
            # 'label':'billing_city',
            'import': True,
            'user': True,
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
            'wp-api': {
                'meta': True,
                'key': 'billing_postcode'
            },
            'act': True,
            # 'label':'billing_postcode',
            'import': True,
            'user': True,
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
            'wp-api': {
                'meta': True,
                'key': 'billing_state'
            },
            'act': True,
            # 'label':'billing_state',
            'import': True,
            'user': True,
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
            'wp-api': {
                'meta': True,
                'key': 'billing_country'
            },
            'act': True,
            # 'label':'billing_country',
            'import': True,
            'user': True,
            # 'warn':True,
            # 'static':True,
            # 'capitalized':True,
            # 'visible':True,
        }),
        ('Shire', {
            'wp': False,
            'act': True,
            # 'label':'billing_country',
            'import': True,
            'user': True,
            # 'warn':True,
            # 'static':True,
            # 'capitalized':True,
            # 'visible':True,
            'default':'',
        }),
        ('Home Address 1', {
            'wp': {
                'meta': True,
                'key': 'shipping_address_1'
            },
            'wp-api': {
                'meta': True,
                'key': 'shipping_address_1'
            },
            'act': True,
            # 'label':'shipping_address_1',
            'import': True,
            'user': True,
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
            'wp-api': {
                'meta': True,
                'key': 'shipping_address_2'
            },
            'act': True,
            # 'label':'shipping_address_2',
            'import': True,
            'user': True,
            # 'sync':True,
            # 'static':True,
            # 'capitalized':True,
            # 'visible':True,
            'default':'',
        }),
        ('Home City', {
            'wp': {
                'meta': True,
                'key': 'shipping_city'
            },
            'wp-api': {
                'meta': True,
                'key': 'shipping_city'
            },
            'act': True,
            # 'label':'shipping_city',
            'import': True,
            'user': True,
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
            'wp-api': {
                'meta': True,
                'key': 'shipping_postcode'
            },
            'act': True,
            # 'label':'shipping_postcode',
            'import': True,
            'user': True,
            # 'sync':True,
            # 'static':True,
            # 'visible':True,
        }),
        ('Home Country', {
            'wp': {
                'meta': True,
                'key': 'shipping_country'
            },
            'wp-api': {
                'meta': True,
                'key': 'shipping_country'
            },
            'act': True,
            # 'label':'shipping_country',
            'import': True,
            'user': True,
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
            'wp-api': {
                'meta': True,
                'key': 'shipping_state'
            },
            'act': True,
            # 'label':'shipping_state',
            'import': True,
            'user': True,
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
            'wp-api': {
                'meta': True,
                'key': 'myob_customer_card_id'
            },
            'act': True,
            'import': True,
            # 'report':True,
            'user': True,
            'sync': 'master_override',
            'warn': True,
            'default':'',
        }),
        ('Client Grade', {
            'import': True,
            'wp': {
                'meta': True,
                'key': 'client_grade'
            },
            'wp-api': {
                'meta': True,
                'key': 'client_grade'
            },
            'act': True,
            # 'label':'client_grade',
            'user': True,
            # 'report':True,
            'sync': 'master_override',
            'warn': True,
            'visible': True,
        }),
        ('Agent', {
            'wp': {
                'meta': True,
                'key': 'agent'
            },
            'wp-api': {
                'meta': True,
                'key': 'agent'
            },
            'act': True,
            # 'label':'agent',
            'import': 'true',
            'user': True,
            'sync': 'master_override',
            'warn': True,
            'visible': True,
            'default':'',
        }),

        ('ABN', {
            'wp': {
                'meta': True,
                'key': 'abn'
            },
            'wp-api': {
                'meta': True,
                'key': 'abn'
            },
            'act': True,
            # 'label':'abn',
            'import': True,
            'user': True,
            'sync': True,
            'warn': True,
            'visible': True,
            'mutable': True,
        }),
        ('Business Type', {
            'wp': {
                'meta': True,
                'key': 'business_type'
            },
            'wp-api': {
                'meta': True,
                'key': 'business_type'
            },
            'act': True,
            # 'label':'business_type',
            'import': True,
            'user': True,
            'sync': True,
            'invincible':'master',
            'visible': True,
            # 'mutable':True
        }),
        ('Lead Source', {
            'wp': {
                'meta': True,
                'key': 'how_hear_about'
            },
            'wp-api': {
                'meta': True,
                'key': 'how_hear_about'
            },
            'act': True,
            # 'label':'how_hear_about',
            'import': True,
            'user': True,
            'sync': True,
            'invincible': 'master',
            # 'visible':True,
            'default':'',
        }),
        ('Referred By', {
            'wp': {
                'meta': True,
                'key': 'referred_by'
            },
            'wp-api': {
                'meta': True,
                'key': 'referred_by'
            },
            'act': True,
            # 'label':'referred_by',
            'import': True,
            'user': True,
            'sync': True,
        }),
        ('Tans Per Wk', {
            'wp': {
                'meta': True,
                'key': 'tans_per_wk'
            },
            'wp-api': {
                'meta': True,
                'key': 'tans_per_wk'
            },
            'import': True,
            'user': True,
            'sync': True,
            'default': ''
        }),

        # ('E-mails', {
        #     'aliases': ['E-mail', 'Personal E-mail']
        # }),
        ('Personal E-mail', {
            'wp': {
                'meta': True,
                'key': 'personal_email'
            },
            'wp-api': {
                'meta': True,
                'key': 'personal_email'
            },
            'act': True,
            # 'label':'personal_email',
            'import': True,
            'user': True,
            'tracked': 'future',
            'report': True,
        }),
        ('Create Date', {
            'import': True,
            'act': True,
            'wp': False,
            'report': True,
            'basic': True
        }),
        ('Wordpress Start Date', {
            'import': True,
            'wp': {
                'meta': False,
                'key': 'user_registered'
            },
            'wp-api': {
                'meta': False,
                'key': 'user_registered'
            },
            'act': True,
            # 'report': True,
            # 'basic':True
        }),
        ('Edited in Act', {
            'wp': {
                'meta': True,
                'key': 'edited_in_act'
            },
            'wp-api': {
                'meta': True,
                'key': 'edited_in_act'
            },
            'act': True,
            'import': True,
            'report': True,
            'basic': True,
        }),
        ('Edited in Wordpress', {
            'wp': {
                'generated': True,
            },
            'act': True,
            'import': True,
            'report': True,
            'basic': True,
            'default':'',
        }),
        ('Last Sale', {
            'wp': {
                'meta': True,
                'key': 'act_last_sale'
            },
            'wp-api': {
                'meta': True,
                'key': 'act_last_sale'
            },
            'act': True,
            'import': True,
            'basic': True,
            'report': True
        }),

        ('Social Media', {
            'sync': True,
            'aliases': [
                'Facebook Username', 'Twitter Username',
                'GooglePlus Username', 'Instagram Username',
                'Web Site'
            ],
            'tracked': True,
        }),

        ("Facebook Username", {
            'wp': {
                'key': "facebook",
                'meta': True
            },
            'wp-api': {
                'key': "facebook",
                'meta': True
            },
            'mutable': True,
            'visible': True,
            'contact': True,
            'import': True,
            'act': True,
            'default':'',
        }),
        ("Twitter Username", {
            'wp': {
                'key': "twitter",
                'meta': True
            },
            'wp-api': {
                'key': "twitter",
                'meta': True
            },
            'contact': True,
            'mutable': True,
            'visible': True,
            'import': True,
            'act': True,
            'default':'',
        }),
        ("GooglePlus Username", {
            'wp': {
                'key': "gplus",
                'meta': True
            },
            'wp-api': {
                'key': "gplus",
                'meta': True
            },
            'contact': True,
            'mutable': True,
            'visible': True,
            'import': True,
            'act': True,
            'default':'',
        }),
        ("Instagram Username", {
            'wp': {
                'key': "instagram",
                'meta': True
            },
            'wp-api': {
                'key': "instagram",
                'meta': True
            },
            'contact': True,
            'mutable': True,
            'visible': True,
            'import': True,
            'act': True,
            'default':'',
        }),
        ('Web Site', {
            'wp': {
                'meta': False,
                'key': 'user_url'
            },
            'wp-api': {
                'meta': False,
                'key': 'url'
            },
            'act': True,
            'label': 'user_url',
            'import': True,
            'user': True,
            'sync': True,
            'tracked': True,
        }),

        ("Added to mailing list", {
            'wp': {
                'key': 'mailing_list',
                'meta': True,
            },
            'wp-api': {
                'key': 'mailing_list',
                'meta': True,
            },
            'sync': True,
            'import': True,
            'tracked': True,
            'default': '',
        })
        # ('rowcount', {
        #     # 'import':True,
        #     # 'user':True,
        #     'report':True,
        # }),
    ])

    def __init__(self, data=None):
        if not data:
            data = self.data
        super(ColDataUser, self).__init__(data)

    @classmethod
    def get_user_cols(cls):
        return cls.get_export_cols('user')

    @classmethod
    def get_sync_cols(cls):
        return cls.get_export_cols('sync')

    @classmethod
    def get_capital_cols(cls):
        return cls.get_export_cols('capitalized')

    @classmethod
    def get_wp_cols(cls):
        return cls.get_export_cols('wp')

    @classmethod
    def get_act_cols(cls):
        return cls.get_export_cols('act')

    @classmethod
    def get_alias_cols(cls):
        return cls.get_export_cols('aliases')

    @classmethod
    def get_alias_mapping(cls):
        alias_mappings = {}
        for col, data in cls.get_alias_cols().items():
            alias_mappings[col] = data.get('aliases')
        return alias_mappings

    @classmethod
    def get_wp_import_cols(cls):
        cols = []
        for col, data in cls.data.items():
            if data.get('wp') and data.get('import'):
                cols.append(col)
            if data.get('tracked'):
                cols.append(cls.mod_time_col(col))
        return cols

    @classmethod
    def get_wp_import_col_names(cls):
        cols = OrderedDict()
        for col, data in cls.data.items():
            if data.get('wp') and data.get('import'):
                cols[col] = col
            if data.get('tracked'):
                mod_col = cls.mod_time_col(col)
                cols[mod_col] = mod_col
        return cols

    @classmethod
    def get_wpdb_cols(cls, meta=None):
        cols = OrderedDict()
        for col, data in cls.data.items():
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
            assert cls.wpdbPKey in cols.values()
        return cols

    @classmethod
    def get_all_wpdb_cols(cls):
        return SeqUtils.combine_ordered_dicts(
            cls.get_wpdb_cols(True),
            cls.get_wpdb_cols(False)
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
    def get_wp_tracked_cols(cls):
        cols = OrderedDict()
        for col, data in cls.data.items():
            if data.get('tracked'):
                tracking_name = cls.mod_time_col(col)
                for alias in data.get('aliases', []) + [col]:
                    alias_data = cls.data.get(alias, {})
                    if alias_data.get('wp'):
                        this_tracking_name = tracking_name
                        if alias_data.get('tracked'):
                            this_tracking_name = cls.mod_time_col(alias)
                        cols[this_tracking_name] = cols.get(
                            this_tracking_name, []) + [alias]
                        # wp_data = alias_data.get('wp')

                        # if hasattr(wp_data, '__getitem__') and wp_data.get('key'):
                        #     key = wp_data.get('key')
                        #     if key and not key in cols.get(tracking_name, []):
                        #         cols[tracking_name] = cols.get(tracking_name, []) + [key]
        return cols

    get_slave_tracked_cols = get_wp_tracked_cols

    @classmethod
    def get_act_tracked_cols(cls):
        cols = OrderedDict()
        for col, data in cls.data.items():
            if data.get('tracked'):
                tracking_name = cls.mod_time_col(col)
                for alias in data.get('aliases', []) + [col]:
                    alias_data = cls.data.get(alias, {})
                    if alias_data.get('act'):
                        this_tracking_name = tracking_name
                        if alias_data.get('tracked'):
                            this_tracking_name = cls.mod_time_col(alias)
                        cols[this_tracking_name] = cols.get(
                            this_tracking_name, []) + [alias]
        return cols

    get_master_tracked_cols = get_act_tracked_cols

    @classmethod
    def get_act_future_tracked_cols(cls):
        cols = OrderedDict()
        for col, data in cls.data.items():
            if data.get('tracked') and data.get('tracked') == 'future':
                tracking_name = cls.mod_time_col(col)
                for alias in data.get('aliases', []) + [col]:
                    alias_data = cls.data.get(alias, {})
                    if alias_data.get('act'):
                        this_tracking_name = tracking_name
                        if alias_data.get('tracked'):
                            this_tracking_name = cls.mod_time_col(alias)
                        cols[this_tracking_name] = cols.get(
                            this_tracking_name, []) + [alias]
        return cols

    get_master_future_tracked_cols = get_act_future_tracked_cols

    @classmethod
    def get_act_import_cols(cls):
        cols = []
        for col, data in cls.data.items():
            if data.get('act') and data.get('import'):
                cols.append(col)
            if data.get('tracked'):
                cols.append(cls.mod_time_col(col))
        return cols

    @classmethod
    def get_act_import_col_names(cls):
        cols = OrderedDict()
        for col, data in cls.data.items():
            if data.get('act') and data.get('import'):
                cols[col] = col
            if data.get('tracked'):
                mod_col = cls.mod_time_col(col)
                cols[mod_col] = mod_col
        return cols

    @classmethod
    def get_tansync_defaults_recursive(cls, col, export_cols=None, data=None):
        if data is None:
            data = {}
        if export_cols is None:
            export_cols = OrderedDict()

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

        if data.get('visible'):
            new_data['profile_display'] = 1
        if data.get('mutable'):
            new_data['profile_modify'] = 1
        if data.get('contact'):
            new_data['contact_method'] = 1

        if new_data and data.get('wp'):
            wp_data = data['wp']
            if not wp_data.get('meta'):
                new_data['core'] = 1
            if not wp_data.get('generated'):
                assert wp_data.get('key'), "column %s must have key" % col
                key = wp_data['key']
                export_cols[key] = new_data

        if data.get('aliases'):
            for alias in data['aliases']:
                alias_data = cls.data.get(alias, {})
                alias_data['sync'] = data.get('sync')
                export_cols = cls.get_tansync_defaults_recursive(
                    alias, export_cols, alias_data)

        return export_cols

    @classmethod
    def get_tansync_defaults(cls):
        export_cols = OrderedDict()
        for col, data in cls.data.items():
            export_cols = cls.get_tansync_defaults_recursive(
                col, export_cols, data)
        return export_cols
