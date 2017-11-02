"""
Utility for keeping track of column metadata for translating between databases.
"""

from __future__ import absolute_import

import itertools
from collections import OrderedDict

from .utils import SeqUtils


# TODO:
"""
Proposal: coldata format needs to be unified:
schema = [
    (handle, {          # internal handle for column
        label=...,      # (optional) external label for column, defaults to handle
        type=...,       # (optional) internal storage type if not string
        default=...,    # (optional) default internal value
        target={        # for each target format
            label=...,  # (optional) external label when expressed in target format if different from global label
            type=...,   # (optional) type when expressed in target format if different from global type
            path=...,   # (optional) location of value in target format
            edit=False, # (optional) if column is editable in this format, defaults to True
            read=False, # (optional) if column is readable in this format, defaults to True
        }

    })
]
"""
"""
YAML Import and export of schema
data is not read from file until it is accessed?
"""
"""
Proposal: clearer target names
    wp-api
    wp-api-v1
    wp-api-v2
    wc-legacy-api
    wc-legacy-api-v1
    wc-legacy-api-v2
    wc-legacy-api-v3
    wc-wp-api
    wc-wp-api-v1
    wc-wp-api-v2
    xero-api
"""

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

    @classmethod
    def get_category_cols(cls):
        return cls.get_export_cols('category')

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
        # ('descsum', {
        #     'label': 'Description',
        #     'product': True,
        #     'report': True,
        # }),
        # ('WNR', {
        #     'product': True,
        #     'report': True,
        #     'pricing': True,
        # }),
        # ('RNR', {
        #     'product': True,
        #     'report': True,
        #     'pricing': True,
        # }),
        # ('DNR', {
        #     'product': True,
        #     'report': True,
        #     'pricing': True,
        # }),
        # ('weight', {
        #     'import': True,
        #     'product': True,
        #     'variation': True,
        #     'shipping': True,
        #     'wp': {
        #         'key': '_weight',
        #         'meta': True
        #     },
        #     'wp-api': True,
        #     'sync': True,
        #     'report': True
        # }),
        # ('length', {
        #     'import': True,
        #     'product': True,
        #     'variation': True,
        #     'shipping': True,
        #     'wp': {
        #         'key': '_length',
        #         'meta': True
        #     },
        #     'sync': True,
        #     'report': True
        # }),
        # ('width', {
        #     'import': True,
        #     'product': True,
        #     'variation': True,
        #     'shipping': True,
        #     'wp': {
        #         'key': '_width',
        #         'meta': True
        #     },
        #     'sync': True,
        #     'report': True
        # }),
        # ('height', {
        #     'import': True,
        #     'product': True,
        #     'variation': True,
        #     'shipping': True,
        #     'wp': {
        #         'key': '_height',
        #         'meta': True
        #     },
        #     'sync': True,
        #     'report': True
        # }),
    ])

    @classmethod
    def get_product_cols(cls):
        return cls.get_export_cols('product')

    @classmethod
    def get_pricing_cols(cls):
        return cls.get_export_cols('pricing')

    @classmethod
    def get_shipping_cols(cls):
        return cls.get_export_cols('shipping')

    @classmethod
    def get_inventory_cols(cls):
        return cls.get_export_cols('inventory')


class ColDataCat(ColDataBase):
    data = OrderedDict([
        ('title', {
            'label': 'Category Name',
            'category': True
        }),
        ('taxosum', {
            'label': 'Full Category Name',
            'category': True
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
            'type': 'currency',
        }),
        ('RNR', {
            'label': 'Price Level B, Qty Break 1',
            'import': True,
            'product': True,
            'pricing': True,
            'type': 'currency',
        }),
        ('DNR', {
            'label': 'Price Level C, Qty Break 1',
            'import': True,
            'product': True,
            'pricing': True,
            'type': 'currency',
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

class ColDataXero(ColDataProd):
    data = OrderedDict(ColDataProd.data.items() + [
        ('item_id', {
            'xero-api': {
                'key': 'ItemID'
            },
            # 'report': True,
            'product': True,
            'basic': True,
            'label': 'Xero ItemID',
            # 'sync': 'slave_override',
            'sync': False,
        }),
        ('codesum', {
            'xero-api': {
                'key': 'Code'
            },
            # 'report': True,
            'basic': True,
            'label': 'SKU',
            'product': True,
        }),
        ('Xero Description', {
            'xero-api': {
                'key': 'Description'
            },
            'product': True,
            'default': '',
        }),
        ('itemsum', {
            'xero-api': {
                'key': 'Name'
            },
            'basic': True,
            'label': 'Product Name',
            'report': True,
            'product': True,
            'sync': True,
        }),
        ('is_sold', {
            'xero-api': {
                'key': 'isSold'
            }
        }),
        ('is_purchased', {
            'xero-api': {
                'key': 'isPurchased'
            }
        }),
        ('sales_details', {
            'xero-api': {
                'key': 'SalesDetails'
            },
        }),
        ('WNR', {
            'product': True,
            'report': True,
            'pricing': True,
            'import': True,
            'type': 'currency',
            'xero-api': {
                'key': 'UnitPrice',
                'parent': 'SalesDetails'
            },
            'sync': 'master_override',
            'delta': True,

        }),
        ('stock', {
            'import': True,
            'product': True,
            'variation': True,
            'inventory': True,
            'type': 'float',
            'sync': True,
            'xero-api': {
                'key': 'QuantityOnHand'
            }
        }),
        ('stock_status', {
            'import': True,
            # 'product': True,
            'variation': True,
            'inventory': True,
            'sync': True,
            'xero-api': None,
            # 'delta': True,
        }),
        ('manage_stock', {
            'product': True,
            'variation': True,
            'inventory': True,
            'xero-api': {
                'key': 'IsTrackedAsInventory'
            },
            'sync': True,
            'type': 'bool'
        }),
    ])

    @classmethod
    def unit_price_sales_field(cls, data_target):
        for key, coldata in cls.data.items():
            keydata = ((coldata.get(data_target) or {}).get('key') or {})
            if keydata == 'UnitPrice':
                return key

    def __init__(self, data=None):
        if not data:
            data = self.data
        super(ColDataXero, self).__init__(data)

    @classmethod
    def get_xero_api_cols(cls):
        return cls.get_export_cols('xero-api')

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
                'key': 'id',
                'meta': False,
                'read_only': True
            },
            'wc-api': {
                'key': 'id',
                'meta': False,
                'read_only': True
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
            },
            'wc-api': {
                'key': 'parent'
            }
        }),
        ('codesum', {
            'label': 'SKU',
            'tag': 'SKU',
            'product': True,
            'variation': True,
            'category': False,
            'report': True,
            'sync': True,
            'wp': {
                'key': '_sku',
                'meta': True
            },
            'wp-api': {
                'key': 'sku'
            },
            'wc-api': {
                'key': 'sku'
            },
            'xero-api': {
                'key': 'Code'
            },
        }),
        ('slug', {
            'category': True,
            'wp-api': {
                'key': 'slug',
                'meta': False,
            },
            'wc-api': {
                'key': 'slug',
                'meta': False,
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
            'report': True,
            'sync': 'not_variable',
            'static': True,
            'wp': {
                'key': 'post_title',
                'meta': False
            },
            'wp-api': {
                'key': 'title',
                'meta': False
            },
            'wc-api': {
                'key': 'title',
                'meta': False
            },
            'xero-api': {
                'key': 'Name'
            },
        }),
        ('title', {
            'category': True,
            'wp-api': {
                'key': 'name',
                'meta': False
            },
            'wc-api': {
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
            'category': True
        }),
        ('catlist', {
            'product': True,
            'wp-api': {
                'key': 'categories'
            },
            'wc-api': {
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
            },
            'wc-api': {
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
            'variation': False,
            'sync': 'not_variable',
            'xero-api': {
                'key': 'Description'
            }
        }),
        ('HTML Description', {
            'import': True,
            'category': True,
            'wp-api': {
                'key': 'description',
                'meta': False
            },
            'wc-api': {
                'key': 'description',
                'meta': False
            },
            'sync': True,
            'type': 'html'
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
            'wc-api': {
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
            'wc-api': {
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
            'default': 'visible',
            'wc-api': {
                'key': 'catalog_visibility',
                'meta': False
            }
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
                'key': 'regular_price',
                'meta': False
            },
            'wc-api': {
                'key': '_regular_price',
                'meta': True
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
            'wp-api': {
                'key': 'sale_price',
                'meta': False
            },
            'wc-api': {
                'key': '_sale_price',
                'meta': True
            },
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
                'key': 'date_on_sale_from_gmt',
                'meta': False
            },
            'wc-api': {
                'key': '_sale_price_dates_from',
                'meta': True
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
            'wp-api': {
                'key': 'date_on_sale_to_gmt',
                'meta': False
            },
            'wc-api': {
                'key': '_sale_price_dates_to',
                'meta': True
            },
        }),
    ] +
    [
        (
            ''.join([tier.upper(), field_slug.upper()]),
            {
                'label': 'meta:lc_%s_%s' % (tier, field),
                'sync': True,
                'import': import_,
                'product': True,
                'variation': True,
                'pricing': True,
                'wp': {
                    'key': 'lc_%s_%s' % (tier, field),
                    'meta': True
                },
                'wp-api': {
                    'key': 'lc_%s_%s' % (tier, field),
                    'meta': True
                },
                'wc-api': {
                    'key': 'lc_%s_%s' % (tier, field),
                    'meta': True
                },
                'static': static,
                'type': type_,
            }
        ) for (tier, (field_slug, field, import_, type_, static)) in itertools.product(
            ['rn', 'rp', 'wn', 'wp', 'dn', 'dp'],
            [
                ('r', 'regular_price', True, 'currency', True),
                ('s', 'sale_price', False, 'currency', False),
                ('f', 'sale_price_dates_from', False, 'timestamp', False),
                ('t', 'sale_price_dates_to', False, 'timestamp', False)
            ]
        )
    ] +
    [
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
            'wc-api': {
                'key': 'commissionable_value',
                'meta': True
            },
            'type': 'coefficient'
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
            'wc-api': {
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
            },
            'wc-api': {
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
            # 'wp-api': {
            #     'key': 'in_stock',
            #     'meta': False
            # },
            # 'wc-api': {
            #     'key': 'in_stock',
            #     'meta': False
            # },
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
            'wc-api': {
                'key': 'managing_stock'
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
            },
            'wc-api': {
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
            'wc-api': {
                'key': 'status'
            },
            'sync': True,
            'default': 'publish',
            'invincible': True
        }),
        ('is_sold', {
            'import': True,
            'product': True,
            'variation': True,
            'wp-api': None,
            'xero-api': {
                'key': 'isSold'
            },
            'default':'',
        }),
        ('is_purchased', {
            'import': True,
            'product': True,
            'variation': True,
            'wp-api': None,
            'xero-api': {
                'key': 'isPurchased'
            },
            'default': '',
        }),
    ])


    def __init__(self, data=None):
        if not data:
            data = self.data
        super(ColDataWoo, self).__init__(data)

    @classmethod
    def get_variation_cols(cls):
        return cls.get_export_cols('variation')

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

    master_schema = 'act'

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
            'wc-api': {
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
            'wc-api': {
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
            'wc-api': {
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
            'wc-api': {
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
        # ('Role Info', {
        #     'aliases': [
        #         'Role',
        #         'Direct Brand'
        #     ],
        #     'sync': True,
        #     'static': True,
        #     'basic': True,
        #     'report': True,
        #     'delta': True,
        #     # 'tracked': True,
        #     'reflective': 'master',
        #     'user': True,
        # }),
        # ('Role', {
        #     'wp': {
        #         'meta': True,
        #         'key': 'act_role'
        #     },
        #     'wp-api': {
        #         'meta': True,
        #         'key': 'act_role'
        #     },     'wc-api': {
        #         'meta': True,
        #         'key': 'act_role'
        #     },
        #     # 'label': 'act_role',
        #     'import': True,
        #     'act': True,
        #     # 'user': True,
        #     # 'report': True,
        #     # 'sync': True,
        #     'warn': True,
        #     'static': True,
        #     # 'tracked':'future',
        # }),
        # ('Direct Brand', {
        #     'import': True,
        #     'wp': {
        #         'meta': True,
        #         'key': 'direct_brand'
        #     },
        #     'wp-api': {
        #         'meta': True,
        #         'key': 'direct_brand'
        #     },     'wc-api': {
        #         'meta': True,
        #         'key': 'direct_brand'
        #     },
        #     'act': True,
        #     # 'label':'direct_brand',
        #     # 'user': True,
        #     # 'report': True,
        #     # 'sync': 'master_override',
        #     'warn': True,
        # }),

        ('Name', {
            'aliases': [
                'Contact',
                # 'Display Name',
                'Name Prefix',
                'First Name',
                'Middle Name',
                'Surname',
                'Name Suffix',
                'Memo',
                'Spouse',
                'Salutation',
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
            'act': True,
            'mutable': True,
            'visible': True,
            'default': '',
        }),
        # ('Display Name', {
        #     'import': True,
        #     'act': False
        #     'wp': {
        #         'meta': False,
        #         'key': 'display_name'
        #     },
        #     'wp-api': {
        #         'meta': False,
        #         'key': 'name'
        #     },     'wc-api': {
        #         'meta': False,
        #         'key': 'name'
        #     },
        # })
        ('First Name', {
            'wp': {
                'meta': True,
                'key': 'first_name'
            },
            'wp-api': {
                'meta': False,
                'key': 'first_name'
            },
            'wc-api': {
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
            'wc-api': {
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
            'wc-api': {
                'meta': True,
                'key': 'middle_name'
            },
            'act': True,
            'import': True,
            'mutable': True,
            'visible': True,
            # 'user': True,
            'default': '',
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
            'wc-api': {
                'meta': True,
                'key': 'name_suffix'
            },
            'act': True,
            'import': True,
            'visible': True,
            # 'user': True,
            'mutable': True,
            'default': '',
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
            'wc-api': {
                'meta': True,
                'key': 'name_prefix'
            },
            'act': True,
            'import': True,
            'visible': True,
            # 'user': True,
            'mutable': True,
            'default': '',
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
            'wc-api': {
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
            'wc-api': {
                'meta': True,
                'key': 'spouse'
            },
            'act': True,
            'import': True,
            'tracked': 'future',
            'default': '',
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
            'wc-api': {
                'meta': True,
                'key': 'nickname'
            },
            'act': True,
            'import': True,
            'default': '',
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
            'wc-api': {
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
            'invincible': 'master',
        }),


        ('Phone Numbers', {
            'act': False,
            'wp': False,
            'tracked': 'future',
            'aliases': [
                'Mobile Phone', 'Phone', 'Fax',
                # 'Mobile Phone Preferred', 'Phone Preferred',
                # 'Pref Method'
            ],
            'import': False,
            'basic': True,
            'sync': True,
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
            'wc-api': {
                'meta': True,
                'key': 'mobile_number'
            },
            'act': True,
            # 'label':'mobile_number',
            'import': True,
            'user': True,
            # 'sync': True,
            'warn': True,
            'static': True,
            'invincible': 'master',
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
            'wc-api': {
                'meta': True,
                'key': 'billing_phone'
            },
            'act': True,
            # 'label':'billing_phone',
            'import': True,
            'user': True,
            # 'report': True,
            # 'sync': True,
            'warn': True,
            'static': True,
            'invincible': 'master',
            # 'visible':True,
        }),
        ('Home Phone', {
            'act': True,
            # 'label':'billing_phone',
            'import': True,
            'user': True,
            # 'report': True,
            # 'sync': True,
            'warn': True,
            'static': True,
            'invincible': 'master',
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
            'wc-api': {
                'meta': True,
                'key': 'fax_number'
            },
            'act': True,
            # 'label':'fax_number',
            'import': True,
            'user': True,
            # 'sync': True,
            'contact': True,
            'visible': True,
            'mutable': True,
        }),
        # TODO: implement pref method
        ('Pref Method', {
            'wp': {
                'meta': True,
                'key': 'pref_method',
                'options': ['', 'pref_mob', 'pref_tel', '']
            },
            'wp-api': {
                'meta': True,
                'key': 'pref_method',
                'options': ['', 'pref_mob', 'pref_tel', '']
            },
            'wc-api': {
                'meta': True,
                'key': 'pref_method',
                'options': ['', 'pref_mob', 'pref_tel', '']
            },
            'act': {
                'options': ['E-mail', 'Mobile', 'Phone', 'SMS'],
                'sync':False
            },
            'invincible': 'master',
            'sync': False,
            'import': False,
        }),
        # ('Mobile Phone Preferred', {
        #     'wp': {
        #         'meta': True,
        #         'key': 'pref_mob'
        #     },
        #     'wp-api': {
        #         'meta': True,
        #         'key': 'pref_mob'
        #     },     'wc-api': {
        #         'meta': True,
        #         'key': 'pref_mob'
        #     },
        #     'act': {
        #         'options':['True', 'False']
        #     },
        #     # 'label':'pref_mob',
        #     'import': True,
        #     'user': True,
        #     'sync': True,
        #     'visible': True,
        #     'mutable': True,
        #     'invincible':'master',
        # }),
        # ('Phone Preferred', {
        #     'wp': {
        #         'meta': True,
        #         'key': 'pref_tel'
        #     },
        #     'wp-api': {
        #         'meta': True,
        #         'key': 'pref_tel'
        #     },     'wc-api': {
        #         'meta': True,
        #         'key': 'pref_tel'
        #     },
        #     'act': {
        #         'options':['True', 'False']
        #     },
        #     # 'label':'pref_tel',
        #     'import': True,
        #     'user': True,
        #     'sync': True,
        #     'visible': True,
        #     'mutable': True,
        #     'invincible':'master',
        # }),
        # ('Home Phone Preferred', {
        #     'act': {
        #         'options':['True', 'False']
        #     },
        #     # 'label':'pref_tel',
        #     'import': True,
        #     'user': True,
        #     'sync': True,
        #     'visible': True,
        #     'mutable': True,
        #     'invincible':'master',
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
            'wc-api': {
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
            'wc-api': {
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
            'default': '',
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
            'wc-api': {
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
            'wc-api': {
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
            'wc-api': {
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
            'wc-api': {
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
            'default': '',
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
            'wc-api': {
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
            'wc-api': {
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
            'default': '',
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
            'wc-api': {
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
            'wc-api': {
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
            'wc-api': {
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
            'wc-api': {
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
            'wc-api': {
                'meta': True,
                'key': 'myob_customer_card_id'
            },
            'act': True,
            'import': True,
            # 'report':True,
            'user': True,
            'sync': 'master_override',
            'warn': True,
            'default': '',
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
            'wc-api': {
                'meta': True,
                'key': 'client_grade'
            },
            'act': True,
            # 'label':'client_grade',
            'user': True,
            # 'report':True,
            'sync': 'master_override',
            'invincible': 'master',
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
            'wc-api': {
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
            'default': '',
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
            'wc-api': {
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
            'wc-api': {
                'meta': True,
                'key': 'business_type'
            },
            'act': True,
            # 'label':'business_type',
            'import': True,
            'user': True,
            'sync': True,
            'invincible': 'master',
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
            'wc-api': {
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
            'default': '',
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
            'wc-api': {
                'meta': True,
                'key': 'referred_by'
            },
            'act': True,
            # 'label':'referred_by',
            'import': True,
            'user': True,
            'sync': True,
            'invincible': 'master',
        }),
        ('Tans Per Week', {
            'wp': {
                'meta': True,
                'key': 'tans_per_wk'
            },
            'wp-api': {
                'meta': True,
                'key': 'tans_per_wk'
            },
            'wc-api': {
                'meta': True,
                'key': 'tans_per_wk'
            },
            'act': True,
            'import': True,
            'user': True,
            'sync': True,
            'default': '',
            'invincible': 'master',
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
            'wc-api': {
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
            'wc-api': {
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
            'wc-api': {
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
            'default': '',
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
            'wc-api': {
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
            'wc-api': {
                'key': "facebook",
                'meta': True
            },
            'mutable': True,
            'visible': True,
            'contact': True,
            'import': True,
            'act': True,
            'default': '',
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
            'wc-api': {
                'key': "twitter",
                'meta': True
            },
            'contact': True,
            'mutable': True,
            'visible': True,
            'import': True,
            'act': True,
            'default': '',
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
            'wc-api': {
                'key': "gplus",
                'meta': True
            },
            'contact': True,
            'mutable': True,
            'visible': True,
            'import': True,
            'act': True,
            'default': '',
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
            'wc-api': {
                'key': "instagram",
                'meta': True
            },
            'contact': True,
            'mutable': True,
            'visible': True,
            'import': True,
            'act': True,
            'default': '',
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
            'wc-api': {
                'meta': False,
                'key': 'url'
            },
            'act': True,
            'label': 'user_url',
            'import': True,
            'user': True,
            'sync': True,
            'tracked': True,
            'invincible': 'master',
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
            'wc-api': {
                'key': 'mailing_list',
                'meta': True,
            },
            'sync': True,
            'import': True,
            'tracked': True,
            'default': '',
        }),
        # ('rowcount', {
        #     # 'import':True,
        #     # 'user':True,
        #     'report':True,
        # }),

        # Other random fields that I don't understand
        ("Direct Customer", {
            'act': True,
            'import': True,
        }),
        # ("Mobile Phone Status", {
        #     'act':True,
        #     'import': True,
        # }),
        # ("Home Phone Status", {
        #     'act':True,
        #     'import': True,
        # }),
        # ("Phone Status", {
        #     'act':True,
        #     'import': True,
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
    def get_tracked_cols(cls, schema=None):
        if not schema:
            schema = cls.master_schema
        cols = OrderedDict()
        for col, data in cls.data.items():
            if data.get('tracked'):
                tracking_name = cls.mod_time_col(col)
                for alias in data.get('aliases', []) + [col]:
                    alias_data = cls.data.get(alias, {})
                    if alias_data.get(schema):
                        this_tracking_name = tracking_name
                        if alias_data.get('tracked'):
                            this_tracking_name = cls.mod_time_col(alias)
                        cols[this_tracking_name] = cols.get(
                            this_tracking_name, []) + [alias]
        return cols

    @classmethod
    def get_wp_tracked_cols(cls):
        return cls.get_tracked_cols('wp')

    get_slave_tracked_cols = get_wp_tracked_cols

    @classmethod
    def get_act_tracked_cols(cls):
        return cls.get_tracked_cols('act')

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
