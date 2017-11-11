"""
Utility for keeping track of column metadata for translating between databases.
"""

from __future__ import absolute_import

import itertools
from collections import OrderedDict
from copy import copy

import jsonpath_ng
from jsonpath_ng import jsonpath

from .utils import JSONPathUtils, Registrar, SeqUtils, SanitationUtils


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
Get rid of stuff like slave_override, since it should be able to work both ways.
get rid of attributes like category, product, variation, that's covered by class now.
"""
"""
YAML Import and export of schema
data is not read from file until it is accessed?
"""

class ColDataAbstract(object):
    """
    Store information about how to translate between disparate target schemas.
     - Each target represents a different data format
     - Each handle is a piece of data within that format
     - The properties of a handle show how to coerce data of that handle between formats
    """

    targets = {
        'api': {
            'wp-api': {
                'wp-api-v1': {},
                'wp-api-v2': {}
            },
            'wc-api': {
                'wc-legacy-api': {
                    'wc-legacy-api-v1': {},
                    'wc-legacy-api-v2': {},
                    'wc-legacy-api-v3': {},
                },
                'wc-wp-api': {
                    'wc-wp-api-v1': {},
                    'wc-wp-api-v2': {}
                }
            },
            'xero-api': {},
            'infusion-api': {},
        },
        'csv': {
            'gen_csv': {},
            'wc-csv': {},
            'act-csv': {},
            'myo-csv': {},
        },
        'sql': {
            'wp-sql': {}
        },
        'report': {
            'report-full': {}
        }
    }
    data = {
        'id': {
            'write': False,
            'unique': True,
            'xero-api': {
                'path': None,
            },
            'wp-api': {
                'path': 'id'
            },
            'wp-api-v1': {
                'path': 'ID'
            },
            'wp-sql': {
                'path': 'ID',
            },
            'act-csv': {
                'path': 'Wordpress ID',
            },
            'report': True
        }
    }

    handle_cache = OrderedDict()
    handles_cache = OrderedDict()

    @classmethod
    def get_target_ancestors(cls, targets=None, target=None):
        """
        Given a target, the the ancestors of that target in the target resolution heirarchy
        """
        ancestors = []
        if (targets and target):
            for this, children in targets.items():
                child_target_ancestors = cls.get_target_ancestors(children, target)
                if this == target or child_target_ancestors:
                    ancestors.append(this)
                if child_target_ancestors:
                    ancestors.extend(child_target_ancestors)
        return ancestors

    @classmethod
    def prepare_finder(cls, properties, ancestors=None, handles=None):
        """
        Prepare a jsonpath finder object for finding the given property of `handles`
        given a list of target ancestors.
        """
        # Registrar.increment_stack_count('prepare_finder')
        if handles is None:
            handles = ['*']
        handle_finder = jsonpath.Fields(*handles)
        finder = handle_finder.child(jsonpath.Fields(*properties))
        if ancestors:
            finder = jsonpath.Union(
                finder,
                handle_finder\
                .child(jsonpath.Fields(*ancestors))\
                .child(jsonpath.Fields(*properties))
            )
        return finder

    @classmethod
    def get_property_default(cls, property_=None, handle=None):
        """
        Return the default value of a handle's property.
        """
        if property_:
            return {
                'path': handle,
                'write': True,
                'read': True,
                'type': 'string'
            }.get(property_)

    @classmethod
    def get_handle_property(cls, handle, property_, target=None):
        """
        Return the value of a handle's property in the context of target. Cache for performace.
        """
        cache_key = (cls.__name__, property_, target)
        if cache_key in cls.handle_cache:
            return copy(cls.handle_cache[cache_key])
        target_ancestors = cls.get_target_ancestors(cls.targets, target)
        finder = cls.prepare_finder([property_], target_ancestors, [handle])
        results = [match.value for match in finder.find(cls.data)]
        if results:
            response = results[-1]
        else:
            response = cls.get_property_default(property_, handle)
        cls.handle_cache[cache_key] = response
        return response

    @classmethod
    def get_handles_property(cls, property_, target=None):
        """
        Return a mapping of handles to the value of property_ wherever it is
        explicitly declared in the context of target. Cache for performance.
        """
        cache_key = (cls.__name__, property_, target)
        if cache_key in cls.handles_cache:
            return copy(cls.handles_cache[cache_key])
        target_ancestors = cls.get_target_ancestors(cls.targets, target)
        finder = cls.prepare_finder([property_], target_ancestors, )
        results = OrderedDict()
        for result in finder.find(cls.data):
            value = result.value
            handle = result.full_path
            while hasattr(handle, 'left'):
                handle = handle.left
            handle = handle.fields[0]
            results[handle] = value
        cls.handles_cache[cache_key] = results
        return results

    @classmethod
    def get_path_translation(cls, from_target, to_target=None):
        """
        Return a list of tuples of path specs for translating between different targets.
        """
        if from_target == to_target:
            return None

        from_paths = cls.get_handles_property('path', from_target)
        to_paths = cls.get_handles_property('path', to_target)
        translation = {}
        for handle in cls.data.keys():
            from_path = from_paths.get(handle, handle)
            to_path = to_paths.get(handle, handle)
            if from_path and to_path:
                translation[from_path] = to_path
        return translation

    @classmethod
    def do_path_translation(cls, data, from_target=None, to_target=None):
        """
        Translate an object with from_target struction into to_target structure.
        Does not translate data formats.
        """
        translation = cls.get_path_translation(from_target, to_target)
        if not translation:
            return data
        new_data = {}
        for from_path, to_path in translation.items():
            getter = jsonpath_ng.parse(from_path)
            results = getter.find(data)
            if not results:
                continue
            result_value = results[0].value

            updater = jsonpath_ng.parse(to_path)
            new_data = JSONPathUtils.blank_update(updater, new_data, result_value)
        return new_data

    @classmethod
    def get_normalizer(cls, type_):
        return {
            'xml_escaped': SanitationUtils.xml_to_unicode
        }.get(type_, SanitationUtils.coerce_unicode)

    @classmethod
    def get_denormalizer(cls, type_):
        return {
            'xml_escaped': SanitationUtils.coerce_xml
        }.get(type_, SanitationUtils.identity)

    @classmethod
    def normalize_data(cls, data, target):
        types = cls.get_handles_property('type', target)
        for handle in cls.data.keys():
            if handle in data and types.get(handle):
                data[handle] = cls.get_normalizer(types[handle])(data[handle])
        return data

    @classmethod
    def denormalize_data(cls, data, target):
        types = cls.get_handles_property('type', target)
        for handle in cls.data.keys():
            if handle in data and types.get(handle):
                data[handle] = cls.get_denormalizer(types[handle])(data[handle])
        return data

    @classmethod
    def translate_data_from(cls, data, target):
        data = cls.do_path_translation(data, target)
        data = cls.normalize_data(data, target)
        return data

    @classmethod
    def translate_data_to(cls, data, target):
        data = cls.denormalize_data(data, target)
        data = cls.do_path_translation(data, None, target)
        return data



    @classmethod
    def get_defaults(cls, target=None):
        return cls.get_handles_property('defaults', target)

    @classmethod
    def get_report_cols(cls, target=None):
        return cls.get_handles_property('report', target)

    @classmethod
    def get_sync_cols(cls, target=None):
        path_cols = cls.get_handles_property('path', target)
        write_cols = cls.get_handles_property('write', target)
        sync_cols = OrderedDict()
        for key in set(path_cols.keys()).union(write_cols.keys()):
            path = path_cols.get(key, None)
            write = write_cols.get(key, None)
            if path is None or write is False:
                continue
            sync_cols[key] = cls.data[key]
        return sync_cols

class ColDataWpEntity(ColDataAbstract):
    """
    Metadata for abstract WP objects
    - wp-api-v2: https://developer.wordpress.org/rest-api/reference/posts/
    - wp-api-v2: http://v2.wp-api.org/reference/posts/
    - wp-api-v1: http://wp-api.org/index-deprecated.html#entities_post
    """
    data = OrderedDict(ColDataAbstract.data.items() + {
        'permalink': {
            'write': False,
            'path': None,
            'wp-api': {
                'path': 'link'
            },
            'wc-api': {
                'path': 'permalink'
            }
        },
        'guid': {
            'write': False,
            'wp-api': {
                'path': 'guid.rendered'
            },
        },
        'created_gmt': {
            'type': 'datetime',
            'write': False,
            'wp-api': {
                'path': 'date_gmt',
                'type': 'iso8601_gmt',
            },
            'wc-wp-api': {
                'path': 'date_created_gmt',
                'type': 'iso8601_gmt',
            },
            'wc-legacy-api': {
                'path': 'created_at',
                'type': 'iso8601_gmt',
            },
            'wp-sql':{
                'type': 'wp_datetime_gmt',
                'path': 'post_date_gmt'
            }
        },
        'created_local': {
            'type': 'datetime',
            'write': False,
            'wp-api': {
                'path': 'date',
                'type': 'iso8601_local',
            },
            'wc-wp-api': {
                'path': 'date_created',
                'type': 'iso8601_local',
            },
            'wc-legacy-api': {
                'path': 'created_at',
                'type': 'iso8601_local',
            },
            'wp-sql':{
                'path': 'post_date',
                'type': 'wp_datetime_local',
            }
        },
        'modified_gmt': {
            'type': 'datetime',
            'write': False,
            'wc-wp-api': {
                'type': 'iso8601_gmt',
                'path': 'date_modified',
            },
            'wc-legacy-api': {
                'path': 'modified_at',
                'type': 'iso8601_gmt',
            },
            'wp-sql': {
                'path': 'post_modified_gmt',
                'type': 'wp_datetime_gmt'
            },
            'report': True,
        },
        'modified_local': {
            'type': 'datetime',
            'write': False,
            'wc-wp-api': {
                'path': 'date_modified',
                'type': 'iso8601_local',
            },
            'wc-legacy-api': {
                'path': 'modified_at',
                'type': 'iso8601_local',
            },
            'wp-sql': {
                'path': 'post_modified',
                'type': 'wp_datetime_local'
            },
            'report': True,
        },
        'created_timezone': {
            'write': False,
            'wp-api': {
                'path': None
            },
            'wp-api-v1': {
                'type': 'olsen_zoneinfo',
                'path': 'date_tz'
            },
            'wc-wp-api': {
                'path': None
            },
            'wc-legacy-api': {
                'path': None
            },
            'wp-sql': {
                'path': None,
            }
        },
        'modified_timezone': {
            'write': False,
            'wp-api': {
                'path': None
            },
            'wp-api-v1': {
                'type': 'olsen_zoneinfo',
                'path': 'modified_tz'
            },
            'wc-wp-api': {
                'path': None
            },
            'wc-legacy-api': {
                'path': None
            },
            'wp-sql': {
                'path': None,
            }
        },
        'slug':{
            'unique': True,
            'wp-api': {
                'path': 'slug'
            },
            'wp-api-v1': {
                'path': 'name'
            },
            'wc-legacy-api': {
                'path': None
            },
            'wp-sql': {
                'path': 'post_name'
            }
        },
        'title': {
            'wp-api':{
                'path': 'title.rendered',
                'type': 'xml_escaped'
            },
            'wp-api-v1': {
                'path': 'title'
            },
            'wc-wp-api': {
                'path': 'name'
            },
            'wp-sql': {
                'path': 'post_title'
            },
            'xero-api': {
                'path': 'Name'
            },
            'wc-csv': {
                'path': 'post_title'
            },
            'report': True,
        },
        'status': {
            'default': 'publish',
            'options': [
                'draft',
                'pending',
                'private',
                'inherit',
            ],
            'wp-sql': {
                'path': 'post_status'
            },
        },
        'type': {
            'write': False,
            'default': 'post',
            'wp-sql': {
                'path': 'post_type'
            },
        },
        'content': {
            'wc-api': {
                'path': 'description'
            },
            'wp-api':{
                'path': 'content.rendered',
                'type': 'wp_content_rendered',
            },
            'wp-api-v1': {
                'path': 'content_raw'
            },
            'xero-api': {
                'key': 'Description'
            },
            'wp-sql': {
                'type': None,
                'path': 'post_content'
            },
            'wc-csv': {
                'path': 'post_content'
            },
            'gen-csv': {
                'path': 'description'
            },
        },
        'excerpt': {
            'wc-api': {
                'path': 'short_description',
                'type': 'wp_content_rendered',
            },
            'wp-api': {
                'path': 'excerpt.rendered',
                'type': 'wp_content_rendered'
            },
            'wp-api-v1': {
                'path': 'excerpt_raw'
            },
            'wp-sql': {
                'type': None,
                'path': 'post_excerpt'
            }
        },
        'menu_order': {
            'wp-api': {
                'path': None
            },
            # 'wp-api-v1': {
            #     'path': 'menu_order'
            # },
            # 'wp-sql': {
            #     'path': 'menu_order'
            # },
            # 'wp-csv': {
            #     'path': 'menu_order'
            # },
            'gen-csv': {
                'path': 'rowcount'
            },
        },
        'mime_type': {
            'write': False,
            'type': 'mime_type',
            'wp-api-v1': {
                'path': 'attachment_meta.sizes.thumbnail.mime-type',
                'write': False
            },
            'wp-sql': {
                'path': 'post_mime_type'
            },
            'report': True,
        },
        'parent_id': {
            'wp-sql': {
                'path': 'post_parent'
            },
            'wc-api': {
                'path': 'parent_id'
            },
            'woo-csv': {
                'path': 'post_parent'
            }
        },
        'terms': {
            'path': None,
            'wp-api-v1': {
                'path': 'terms',
            },
        },
        'meta': {
            'wp-api-v1': {
                'path': 'post_meta'
            },
            'wc-api': {
                'path': 'meta_data',
                'type': 'listed_meta',
            },
            'wc-legacy-api': {
                'path': 'custom_meta'
            },
            'wp-sql':{
                'path': None,
            }
        },
        'categories': {
            'path': None,
            'wc-api': {
                'type': 'wc_wp_api_categories',
                'path': 'categories'
            },
            'wp-api-v1': {
                # note: in wp-api-v1 terms.category is an object if there is
                # one category but a list if there are multiple
                'type': 'wp_api_v1_category',
                'path': 'terms.category'
            },
            'wc-csv': {
                'path': 'tax:product_tag',
                'type': 'heirarchical_pipe_array'
            }
        },
        'category_ids': {
            'path': None,
            'wp-api': {
                'path': 'categories'
            },
            'wp-api-v1': {
                'path': 'terms.categories'
            },
            'wc-api': {
                'path': 'categories[*].id'
            }
        },
        'category_names': {
            'path': None,
            'wc-api': {
                'write': False,
                'path': 'categories[*].name'
            },
            'wc-legacy-api': {
                'path': 'category_names'
            },
        },
        'tags': {
            'path': None,
            'wp-api-v1': {
                # note: in wp-api-v1 terms.category is an object if there is
                # one category but a list if there are multiple
                'type': 'wp_api_v1_term',
                'path': 'terms.category'
            },
            'csv': {
                'path': 'tags',
                'type': 'pipe_array'
            },
            'wc-csv': {
                'path': 'tax:product_tag',
            }
        },

    }.items())

class ColDataWpSubEntity(ColDataAbstract):
    """
    Metadata for abstract WP sub-entities
    - wp-api-v2: https://developer.wordpress.org/rest-api/reference/posts/
    - wp-api-v1: http://wp-api.org/index-deprecated.html#entities_post
    """
    data = OrderedDict(ColDataAbstract.data.items() + {
        'created_gmt': {
            'type': 'iso8601_gmt',
            'wp-api': {
                'path': 'date_gmt'
            },
            'wc-wp-api': {
                'path': 'date_created_gmt'
            },
            'wc-legacy-api': {
                'path': 'created_at'
            },
            'write': False
        },
        'modified_gmt': {
            'type': 'iso8601_gmt',
            'write': False,
            'wc-wp-api': {
                'path': 'date_modified_gmt'
            },
            'wc-legacy-api': {
                'path': 'modified_at'
            }
        },
        'title': {
            'wc-wp-api':{
                'path': 'name',
            },
        },
    }.items())


class ColDataWpPost(ColDataWpEntity):
    data = OrderedDict(ColDataWpEntity.data.items() + {
        'password': {
            'wp-sql': {
                'path': 'post_password'
            }
        },
        'author': {
            'path': None,
            'wp-api-v1':{
                'path': 'author'
            },
        },
        'author_id': {
            'type': int,
            'wp-api': {
                'path': 'author'
            },
            'wp-api-v1': {
                'path': 'author.ID'
            },
            'wp-sql': {
                'path': 'post_author'
            }
        },
        'featured_media': {
            'path': None,
            'wp-api': {
                'path': 'featured_media'
            }
        },
        'comment_status': {
            'options': ['open', 'closed']
        },
        'ping_status': {
            'options': ['open', 'closed']
        },
        'comment_count': {
            'path': None,
            'type': int,
            'wp-sql': {
                'path': 'comment_count'
            }
        },
        'format': {
            'path': None,
            'options': ['standard'],
            'wp-api': {
                'path': 'format'
            }
        },
        'sticky': {
            'path': None,
            'wp-api': {
                'path': 'sticky'
            }
        },
        'template': {
            'path': None,
            'wp-api': {
                'path': 'template'
            }
        },
        'liveblog_likes': {
            'type': int,
            'path': None,
            'wp-api': {
                'path': 'liveblog_likes'
            }
        }
    }.items())

class ColDataProduct(ColDataWpEntity):
    """
    - wc-wp-api-v2: http://woocommerce.github.io/woocommerce-rest-api-docs/#product-properties
    - wc-wp-api-v1
    - wc-legacy-api: http://woocommerce.github.io/woocommerce-rest-api-docs/v3.html#products
    - wp-api-v2: http://v2.wp-api.org/reference/posts/
    - wp-api-v1: http://wp-api.org/index-deprecated.html#posts
    """

    data = OrderedDict(ColDataWpEntity.data.items() + {
        'product_type': {
            'default': 'simple',
            'wc-api': {
                'path': 'type'
            },
            'wc-csv': {
                'path': 'tax:product_type'
            },
            'options': [
                'simple',
                'grouped',
                'external',
                'variable',
                'composite',
                'bundle'
            ]
        },
        'featured': {
            'type': bool,
            'default': False,
            'wp-sql': {
                'path': 'meta._featured',
                'type': 'yesno'
            },
            'csv': {
                'type': 'yesno'
            }
        },
        'catalog_visibility': {
            'default': 'visible',
            'options': [
                'visible',
                'catalog',
                'search',
                'hidden'
            ]
        },
        'sku': {
            'xero-api': {
                'path': 'Code'
            },
            'wc-csv': {
                'path': 'SKU'
            },
            'gen-csv': {
                'path': 'codesum'
            },
            'wp-sql': {
                'path': 'meta._sku',
            },
        },
        'price': {
            'type': 'currency',
            'write': False,
            'wp-sql': {
                'path': 'meta._price',
            }
        },
        'regular_price': {
            'type': 'currency',
            'wp-sql': {
                'path': 'meta._regular_price'
            }
        },
        'sale_price': {
            'type': 'currency',
            'wp-sql': {
                'path': 'meta._sale_price'
            }
        },
        'sale_price_dates_from': {
            'type': 'datetime',
            'wc-api': {
                'path': 'date_on_sale_from',
                'type': 'iso8601_local',
            },
            'wc-legacy-api': {
                'read': False,
                'path': 'sale_price_dates_from',
                'type': 'wp_date_local'
            },
            'wp-sql': {
                'path': 'meta._sale_price_dates_from'
            }
        },
        'sale_price_dates_from_gmt': {
            'type': 'datetime',
            'path': None,
            'wc-api': {
                'path': 'date_on_sale_from',
                'type': 'iso8601_local',
            },
        },
        'sale_price_dates_to': {
            'type': 'datetime',
            'wc-api': {
                'path': 'date_on_sale_to',
                'type': 'iso8601_local',
            },
            'wc-legacy-api': {
                'read': False,
                'path': 'sale_price_dates_to',
                'type': 'wp_date_local'
            },
            'wp-sql': {
                'path': 'meta._sale_price_dates_to'
            }
        },
        'sale_price_dates_to_gmt': {
            'type': 'datetime',
            'path': None,
            'wc-api': {
                'path': 'date_on_sale_to',
                'type': 'iso8601_local',
            },
        },
        'price_html': {
            'write': False,
            'path': None,
            'wc-api': {
                'path': 'price_html'
            }
        },
        'on_sale': {
            'write': False,
            'path': None,
            'type': bool,
            'wc-api': {
                'path': 'on_sale'
            }
        },
        'purchasable': {
            'write': False,
            'path': None,
            'type': bool,
            'wc-api': {
                'path': 'on_sale'
            }
        },
        'total_sales': {
            'write': False,
            'path': None,
            'wc-api': {
                'path': 'on_sale'
            },
            'wp-sql': {
                'path': 'meta.total_sales'
            },
            'woo-csv': {
                'path': 'meta:total_sales'
            }
        },
        'virtual': {
            'type': bool,
            'wp-sql': {
                'path': 'meta._virtual',
                'type': 'yesno'
            }
        },
        'downloadable': {
            'type': bool,
            'wp-sql': {
                'path': 'meta._virtual',
                'type': 'yesno'
            }
        },
        'downloads': {
            'path': None,
            'wc-api': {
                'path': 'downloads'
            },
            'wp-sql': {
                'path': None
            }
        },
        'download_limit': {
            'type': int,
            'wc-api': {
                'path': 'download_limit',
                'default': -1
            },
            'wp-sql': {
                'path': 'meta._download_limit'
            }
        },
        'download_expiry': {
            'wc-api': {
                'default': -1
            },
            'wp-sql': {
                'path': 'meta._download_expiry'
            }
        },
        'external_url': {
            'wc-legacy-api': {
                'path': 'product_url',
            },
            'wp-sql': {
                'path': 'meta._product_url',
            }
        },
        'button_text': {
            'wp-sql': {
                'path': 'meta._button_text'
            }
        },
        'tax_status': {
            'default': 'taxable',
            'options': [
                'taxable',
                'shipping',
                'none'
            ]
        },
        'tax_class': {
            'path': None,
            'wc-api': {
                'path': 'tax_class'
            },
            'wp-sql': {
                'path': 'meta._tax_class'
            },
            'wc-csv': {
                'path': 'tax_class'
            }
        },
        'manage_stock': {
            'type': bool,
            'wp-sql': {
                'path': 'meta._manage_stock',
                'type': 'yesno',
            }
        },
        'stock_quantity': {
            'wc-api': {
                'type': int,
            },
            'xero-api': {
                'path': 'QuantityOnHand',
                'type': float,
            },
            'wc-csv': {
                'path': 'stock',
                'type': int
            },
            'wp-sql': {
                'path': 'meta._stock',
                'type': int
            }
        },
        'in_stock': {
            'type': bool,
            'wc-api': {
                'path': 'in_stock',
                'type': bool
            },
            'wp-sql': {
                'path': 'meta._stock_status',
                'type': 'stock_status'
            },
            'csv': {
                'path': 'stock_status',
                'type': 'stock_status',
            }
        },
        'backorders': {
            'options': [
                'no', 'notify', 'yes'
            ],
            'default': 'no',
            'wp-sql': {
                'path': 'meta._backorders'
            },
        },
        'backorders_allowed': {
            'type': bool,
            'path': None,
            'write': False,
            'wc-api': {
                'path': 'backorders_allowed'
            }
        },
        'backordered': {
            'type': bool,
            'path': None,
            'write': False,
            'wc-api': {
                'path': 'backordered'
            }
        },
        'sold_individually': {
            'type': bool,
            'wp-sql': {
                'path': 'meta._sold_individually',
                'type': 'yesno'
            },
            'csv': {
                'type': 'yesno'
            },
            'woo-csv': {
                'path': 'meta:_sold_individually',
            },
        },
        'weight': {
            'wp-sql': {
                'path': 'meta._weight'
            }
        },
        'length': {
            'wc-api': {
                'path': 'dimensions.length'
            },
            'wp-sql': {
                'path': 'meta._length'
            }
        },
        'width': {
            'wc-api': {
                'path': 'dimensions.width'
            },
            'wp-sql': {
                'path': 'meta._width'
            }
        },
        'height': {
            'wc-api': {
                'path': 'dimensions.height'
            },
            'wp-sql': {
                'path': 'meta._height'
            }
        },
        'shipping_required': {
            'type': bool,
            'path': None,
            'write': False,
            'wc-api': {
                'path': 'shipping_required'
            }
        },
        'shipping_taxable': {
            'type': bool,
            'path': None,
            'write': False,
            'wc-api': {
                'path': 'shipping_taxable'
            }
        },
        'shipping_class': {
            'path': None,
            'wc-api': {
                'path': 'shipping_class'
            },
            'wc-csv': {
                'path': 'tax:product_shipping_class'
            }
        },
        'shipping_class_id': {
            'path': None,
            'write': False,
            'wc-api': {
                'path': 'shipping_class_id'
            },
        },
        'reviews_allowed': {
            'path': None,
            'type': bool,
            'wc-api': {
                'path': 'reviews_allowed'
            }
        },
        'average_rating': {
            'path': None,
            'write': False,
            'wc-api': {
                'path': 'average_rating'
            }
        },
        'rating_count': {
            'path': None,
            'write': None,
            'wc-api': {
                'path': 'rating_count'
            }
        },
        'related_ids': {
            'path': None,
            'write': False,
            'wc-api': {
                'path': 'related_ids'
            }
        },
        'upsell_ids': {
            'wp-sql': {
                'path': 'meta.upsell_ids',
                'type': 'php_array'
            },
            'csv': {
                'type': 'pipe_array'
            }
        },
        'purchase_note': {
            'path': None,
            'wc-api': {
                'path': 'purchase_note'
            },
        },
        'images': {
            'path': None,
            'wc-api': {
                'path': 'images',
                'type': 'wc_api_image_list'
            },
        },
        'attributes': {
            'path': None,
            'wc-api': {
                'path': 'attributes',
                'type': 'wc_api_attribute_list'
            }
        },
        'default_attributes': {
            'path': None,
            'wc-api': {
                'path': 'default_attributes',
                'type': 'wc_api_default_attribute_list'
            }
        },
        'variation_ids': {
            'path': None,
            'variation': None,
            'wc-api': {
                'path': 'variations'
            }
        }

    }.items())

class ColDataProductMeridian(ColDataProduct):
    data = OrderedDict(ColDataProduct.data.items() + {

    }.items() +
    [
        (
            'lc_%s_%s' % (tier, field),
            {
                'import': import_,
                'variation': True,
                'pricing': True,
                'type': type_,
                'wp-sql': {
                    'path': 'meta.lc_%s_%s' % (tier, field),
                },
                'wc-wp-api': {
                    'path': 'meta_data.lc_%s_%s' % (tier, field),
                },
                'wc-legacy-api': {
                    'path': 'custom_meta.lc_%s_%s' % (tier, field),
                },
                'gen-csv': {
                    'path': ''.join([tier.upper(), field_slug.upper()])
                },
                'wc-csv': {
                    'meta:lc_%s_%s' % (tier, field),
                },
                'static': static,
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
    ]
    )


class ColDataMedia(ColDataAbstract):
    """
    Metadata for Media items
    - wp-api-v2: http://v2.wp-api.org/reference/media/
    - wp-api-v1: http://wp-api.org/index-deprecated.html#entities_media
    """
    data = OrderedDict(ColDataWpEntity.data.items() + {
        'source_url': {
            'write': False,
            'type': 'uri',
            'wp-api-v1': {
                'path':'source'
            }
        },
        'alt_text': {
            'wp-api-v1': {
                'path': None
            }
        },
        'caption': {
            'wp-api-v1': {
                'path': None
            },
            'wp-api': {
                'path': 'caption.rendered',
                'type': 'wp_content_rendered'
            }
        },
        'description': {
            'wp-api-v1': {
                'path': None
            },
            'wp-api': {
                'path': 'description.rendered',
                'type': 'wp_content_rendered',
                'write': False
            },
        },
        'image_meta': {
            'write': False,
            'wp-api-v1': {
                'path': 'attachment_meta.image_meta'
            },
            'wp-api': {
                'path': 'attachment_meta.media_details'
            }
        },
        'width': {
            'wp-api-v1':{
                'path': 'attachment_meta.width'
            },
            'wp-api':{
                'path': 'media_details.width'
            },
            'report': True,
        },
        'height': {
            'wp-api-v1':{
                'path': 'attachment_meta.height'
            },
            'wp-api':{
                'path': 'media_details.height'
            },
            'report': True,
        },
        'file_path': {
            'wp-api-v1': {
                'path': 'attachment_meta.file'
            },
            'wp-api': {
                'path': 'media_details.file'
            },
            'report': True
        }
    }.items())

class ColDataSubMedia(ColDataAbstract):
    """
    Metadata for Media sub items; media items that appear within items in the API
    - wc-wp-api-v2: http://woocommerce.github.io/woocommerce-rest-api-docs/#product-images-properties
    - wc-wp-api-v1: http://woocommerce.github.io/woocommerce-rest-api-docs/wp-api-v1.html#product-image-properties
    - wc-legacy-api-v3: http://woocommerce.github.io/woocommerce-rest-api-docs/v3.html#images-properties
    - wc-legacy-api-v2: http://woocommerce.github.io/woocommerce-rest-api-docs/v2.html#images-properties
    - wc-legacy-api-v1: http://woocommerce.github.io/woocommerce-rest-api-docs/v1.html#products
    """
    data = OrderedDict(ColDataWpSubEntity.data.items() + {
        'source_url': {
            'write': False,
            'type': 'uri',
            'wc-wp-api': {
                'path':'src'
            }
        },
        'alt_text': {
            'wc-wp-api': {
                'path': 'alt'
            }
        }
    }.items())

class ColDataBase(object):
    """
    Deprecated style of storing col data
    """
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
    def get_wpapi_cols(cls, api='wc-wp-api'):
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
    def get_wpapi_core_cols(cls, api='wc-wp-api'):
        export_cols = cls.get_export_cols(api)
        api_cols = OrderedDict()
        for col, data in export_cols.items():
            api_data = data.get(api, {})
            if hasattr(api_data, '__getitem__') \
                    and not api_data.get('meta'):
                api_cols[col] = data

        return api_cols

    @classmethod
    def get_wpapi_meta_cols(cls, api='wc-wp-api'):
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
    def get_wpapi_category_cols(cls, api='wc-wp-api'):
        export_cols = cls.get_export_cols(api)
        api_category_cols = OrderedDict()
        for col, data in export_cols.items():
            if data.get('category', ''):
                api_category_cols[col] = data
        return api_category_cols

    @classmethod
    def get_wpapi_import_cols(cls, api='wc-wp-api'):
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
        #     'wc-wp-api': True,
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
            'wc-wp-api': {
                'key': 'id',
                'meta': False,
                'read_only': True
            },
            'wc-legacy-api': {
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
            'wc-wp-api': {
                'key': 'parent'
            },
            'wc-legacy-api': {
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
            'wc-wp-api': {
                'key': 'sku'
            },
            'wc-legacy-api': {
                'key': 'sku'
            },
            'xero-api': {
                'key': 'Code'
            },
        }),
        ('slug', {
            'category': True,
            'wc-wp-api': {
                'key': 'slug',
                'meta': False,
            },
            'wc-legacy-api': {
                'key': 'slug',
                'meta': False,
            },
            'sync': 'slave_override'
        }),
        ('display', {
            'category': True,
            'wc-wp-api': True,
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
            'wc-wp-api': {
                'key': 'title',
                'meta': False
            },
            'wc-legacy-api': {
                'key': 'title',
                'meta': False
            },
            'xero-api': {
                'key': 'Name'
            },
        }),
        ('title', {
            'category': True,
            'wc-wp-api': {
                'key': 'name',
                'meta': False
            },
            'wc-legacy-api': {
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
            'wc-wp-api': {
                'key': 'categories'
            },
            'wc-legacy-api': {
                'key': 'categories'
            },
            # 'sync':'not_variable'
        }),
        # ('catids', {
        # }),
        ('prod_type', {
            'label': 'tax:product_type',
            'product': True,
            'wc-wp-api': {
                'key': 'type'
            },
            'wc-legacy-api': {
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
            'wc-wp-api': {
                'key': 'description',
                'meta': False
            },
            'wc-legacy-api': {
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
            'wc-wp-api': {
                'key': 'menu_order'
            },
            'wc-legacy-api': {
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
            'wc-wp-api': {
                'key': 'wootan_danger',
                'meta': True
            },
            'wc-legacy-api': {
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
            'wc-legacy-api': {
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
            'label': 'meta:active_specials',
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
            'wc-wp-api': {
                'key': 'regular_price',
                'meta': False
            },
            'wc-legacy-api': {
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
            'wc-wp-api': {
                'key': 'sale_price',
                'meta': False
            },
            'wc-legacy-api': {
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
            'wc-wp-api': {
                'key': 'date_on_sale_from_gmt',
                'meta': False
            },
            'wc-legacy-api': {
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
            'wc-wp-api': {
                'key': 'date_on_sale_to_gmt',
                'meta': False
            },
            'wc-legacy-api': {
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
                'wc-wp-api': {
                    'key': 'lc_%s_%s' % (tier, field),
                    'meta': True
                },
                'wc-legacy-api': {
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
            'wc-wp-api': {
                'key': 'commissionable_value',
                'meta': True
            },
            'wc-legacy-api': {
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
            'wc-wp-api': {
                'key': 'weight'
            },
            'wc-legacy-api': {
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
            'wc-wp-api': {
                'key': 'stock_quantity'
            },
            'wc-legacy-api': {
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
            # 'wc-wp-api': {
            #     'key': 'in_stock',
            #     'meta': False
            # },
            # 'wc-legacy-api': {
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
            'wc-wp-api': {
                'key': 'manage_stock'
            },
            'wc-legacy-api': {
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
            'wc-wp-api': {
                'key': 'updated_at'
            },
            'wc-legacy-api': {
                'key': 'updated_at'
            }
        }),
        ('post_status', {
            'import': True,
            'product': True,
            'variation': True,
            'wc-wp-api': {
                'key': 'status'
            },
            'wc-legacy-api': {
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
            'wc-wp-api': None,
            'xero-api': {
                'key': 'isSold'
            },
            'default':'',
        }),
        ('is_purchased', {
            'import': True,
            'product': True,
            'variation': True,
            'wc-wp-api': None,
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
    def get_wp_sql_cols(cls):
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
        ('ACT Role',{
            'wp': {
                'meta': True,
                'key': 'act_role'
            },
            'wp-api': {
                'meta': True,
                'key': 'act_role'
            },
            'wc-api': {
                'meta': True,
                'key': 'act_role'
            },
            'act': {
                'key': 'Role'
            },
            'import': True,
        }),
        ('WP Roles',{
            'wp': {
                'meta': True,
                'key': 'tt6164_capabilities',
            },
            'wp-api': {
                'meta': False,
                'key': 'roles'
            },
            'wc-api': {
                'meta': False,
                'key': 'roles'
            },
            'import': True,
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
        #     },
        #     'wc-api': {
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
    def get_wp_sql_cols(cls):
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
