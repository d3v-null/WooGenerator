# -*- coding: utf-8 -
"""
Utility for keeping track of column metadata for translating between databases.
"""

from __future__ import absolute_import

import functools
import itertools
from collections import OrderedDict, Mapping
from copy import copy, deepcopy
from pprint import pformat

import jsonpath_ng
from jsonpath_ng import jsonpath

from .utils import (FileUtils, JSONPathUtils, MimeUtils, PHPUtils,
                    SanitationUtils, SeqUtils, TimeUtils)

# TODO: Replace dicts with `OrderedDict`s
# TODO: Implement indexer property for parser classes
# TODO: rename to hyperdata or something
# TODO: move into own folder

"""
Get rid of stuff like subordinate_override, since it should be able to work both ways.
get rid of attributes like category, product, variation, that's covered by class now.
YAML Import and export of schema
data is not read from file until it is accessed?
"""
"""
API Whisperer
====

Applies a D.R.Y. , object-oriented approach to translating between different
representations data in disparate APIs.

# Use cases
 - You wrote an API pareser that parses data from one api, but need to upgrade
 to a newer API which has a different structure
 - You need to synchronize data between databases using disparate APIs

# ColData Schema
Each ColData class has a schema which specifies how it handles data from different
targets.
schema = {
    ...,
    handle: {            # internal handle for column
        label: ...,      # (optional) external label for reporting column, defaults to handle
        type: ...,       # (optional) internal storage type if not string
        path: ...,
        default: ...,    # (optional) default internal value
        sub_data: ...,   # (optional) see: Sub-Entities section
        <target>: {      # for each target format, see: Target section
            label: ...,  # (optional) external label when reporting data in target format if different from global label
            type: ...,   # (optional) type when expressed in target format if different from global type
            path: ...,   # (optional) location of value in target format, defaults to handle
            edit: False, # (optional) if column is editable in this format, defaults to True
            read: False, # (optional) if column is readable in this format, defaults to True
        }
    },
    ...
]

The translation is only as good as the data you provide it, so write lots of tests
and make sure that your data translates correctly but checking multiple API sources.
The data shcmea is kind of like CSS in that properties are inherited from their parents

# Targets
Targets are different contexts in which the data can be represented.
They can be used to specify the format of data in different APIs, or they can
be the name of an internal format that you want your data in.
The properties of a target can be inherited from a target's ancestors, allowing
a way of specifying multiple similar targets without redundancy.
The default / root target is `core` which represents the data as a mapping from
handles to the core representation of the data

# Sub-Entities
Different APIs can represent the same attribute of an entity with very different
structures.
E.G. 1a: one api might represent metadata as a list of objects:
{
    ...
    'meta': [
        {
            'id': 1,
            'key': 'key1',
            'value': 1
        },
        {
            'id': 2,
            'key', 'key2',
            'value': 2
        }
    ]
    ...
}
E.G. 1b: one api might represent the same entitiy's metadata as a mapping from keys to values
{
    ...
    'meta_data': {
        'key1': '1',
        'key2': '2'
    },
    ....
}

E.G. 2a: one API might represent the images of an entity as a list of objects:
{
    ...
    'categories': [
        {
            'id':0,
            'name': 'Product Category 0'
            'slug': 'product-category-0'
        },
        ...
    ],
    ...
}

E.G. 2b: another API might represent the categories of an entity as a list of category IDs
{
    ...
    'categories': [
        0, ...
    ],
    ...
}

E.G. 2c: another API might represent the categories of an entity as a mapping of
slugs to objects
{
    ...
    'categories': {
        'product-category-0' : {
            'id':0,
            'name': 'Product Category 0'
            'slug': 'product-category-0'
        }
    },
    ...
}

E.G. 2d: Another API might represent the sub-entity in singular form:
{
    ...
    'category': {
        'id':0,
        'name': 'Product Category 0'
        'slug': 'product-category-0'
    }
}

API Whisperer should be structure-agnostic and be able to translate between
these different structures. To allow this, you can set the `sub_data` field to the class
containing the metadata for the sub-entity object, this will recursively perform
the same type-casting and path translation that API Whisperer does for entites,
for that sub-entity and it's sub-entities.
By default, API Whisperer will treat all handles that contain sub-entities as a
singular object, but you can change this behaviour for different targets.
Note: API Whisperer performs path translation and type-casting on sub-entities
before performing path translation and type-casting on entities, which means that
you access the properties of an entity's sub-entities from within the path
specifications in the entity's metadata, even if that sub-entity is originally in
a serialized format. You could even provide your own functions that extract features
from a string like first_name and last_name from a fullname string.

These are the possible structure specifications:

## singluar-value
If the handle value is represented as a singular value from a sub-entity object,
then you can set the `structure` to `('singular-value', 'value')`, where `'value'`
is the handle of the
## singular-object
If the handle value is represented as a singular sub-entity object, then you can
set the structure to `('singular-object', )`
## listed-values
If the handle value is represented as a list of singular values, where the
values are taken from a sub-entity object, you can set the `structure` to
`('listed-values', 'value')`  where `'value'` is the handle of the
data in the list.
## listed-objects
If the handle value is represented in a given target context as a list of
sub-entity objects (e.g. 1a), you can set the `structure` as `('listed-objects', )`.
## mapping-value
If the handle value is represented in a given target context as a mapping from keys
to a singular value where the value is are taken from a sub-entity object (eg. 1b),
then you can set the `structure` as `('mapping-value', ('key', 'value'))` where
`'key'` and '`value`' are the handles of the key and value in the mapping respectively.
## mapping-object
If the handle value is represented in a given target context as a mapping from keys
to singular sub-entity objects (e.g. 2c) then you can set the `structure` as
`('mapping-object', ('key', ))` where `'key'` is the handle of the key in this mapping.
## mapping-list
If the handle value is represented as a mapping from keys to a list of sub-entity
objects then you can set the `structure` to `('mapping-list', ('key', ))` where
`'key'` is the handle of the key in the mapping.
## mapping-dynamic
If the handle value is represented as a mapping from keys to either a list of sub-entity
objects, or a singular sub-entity object depending on how many sub-entity objects
are present, then you can set the `structure` to `('mapping-dynamic', ('key'))` where
`'key'` is the handle of the key in the mapping. (Yes, this actually happens in
wp-api-v1 for post categories `¯\_(ツ)_/¯` )

API Whisperer can convert between singular structures, and it can convert
between listed / mapped structures but does not handle converting between
singular and listed / mapped structures, since this doesn't make sense.

## Force Mapping
When deconstructing a sub-entity handle that has plural data, the default
behaviour is to store the sub-entity as a list of objects, however, if other
handles require access to values from the sub-entity as if the sub-entity
had the structure of a key-value pair, they may require that the sub-entity
be represented as a mapping in the core data structure.
In this case, you can set the `force_mapping` attribute to the handle of the key
which the mapping should be created on in the core structure.
An illustrative example would be wordpress meta. You may have handles that need
to extrace a meta value, and in this case you would want to set `force_mapping`
to `meta_key` so that the `meta_value` can be accessed using the path meta.<meta_key>.meta_value
"""

# TODO: what if translate_data_to checked for writability?

class ColDataLegacy(object):
    """
    Legacy methods for backwards compatiblity, to be deprecated ASAP.
    """
    data = {}
    default_native_target = 'gen-csv'

    @classmethod
    def get_col_data_native(cls, property_=None, target=default_native_target, base_target=default_native_target):
        """
        Return a mapping of the gen path to the handle properties for
        handles where `property_` is not False.
        """
        core_data = cls.data
        if property_:
            core_data = OrderedDict()
            target_properties = cls.get_handles_property_defaults(property_, target)
            for handle, target_property_value in target_properties.items():
                if not target_property_value:
                    continue
                core_data[handle] = cls.data.get(handle)
        return cls.translate_handle_keys(core_data, base_target)

    @classmethod
    def get_col_values_native(
        cls, property_='path',
        target=default_native_target, base_target=default_native_target
    ):
        """
        Return a mapping of the native path to the value of `property_` for
        each handle where such a mapping exists.
        """
        core_data = OrderedDict()
        target_properties = cls.get_handles_property_defaults(property_, target)
        for handle, target_property_value in target_properties.items():
            if not target_property_value:
                continue
            core_data[handle] = target_property_value
        return cls.translate_handle_keys(core_data, base_target)

    @classmethod
    def get_delta_cols_native(cls, target=default_native_target):
        return OrderedDict([
            (col, cls.delta_col(col))
            for col in cls.get_col_data_native('delta', target).keys()
        ])

    @classmethod
    def translate_handle_keys(cls, datum, target):
        """
        Return `datum` with the key handles translated to paths in `target`.
        """
        target_paths = cls.get_handles_property_defaults('path', target)
        translated = OrderedDict()
        for handle, data in datum.items():
            target_path = target_paths.get(handle)
            if not target_path:
                continue
            translated[target_path] = data
        return translated

    @classmethod
    def translate_handle(cls, handle, target):
        """
        Return the `path` associated with `handle` in `target`.
        """
        target_paths = cls.get_handles_property_defaults('path', target)
        return target_paths.get(handle, handle)

    @classmethod
    def translate_handle_seq(cls, handles, target):
        """
        Return the `path`s associated with `handle`s in `target`.
        """
        target_paths = cls.get_handles_property_defaults('path', target)
        response = []
        for handle in handles:
            target_path = target_paths.get(handle, handle)
            response.append(target_path)
        return response

    @classmethod
    def translate_col_seq(cls, cols, target):
        """
        Return the `handle`s associated with the sequence of paths `cols` in `target`.
        """
        cols = deepcopy(cols)
        target_paths = cls.get_handles_property_defaults('path', target)
        for handle, target_path in target_paths.items():
            while True:
                try:
                    path_index = cols.index(target_path)
                except ValueError:
                    break
                cols[path_index] = handle
        return cols

    @classmethod
    def translate_col(cls, col, target):
        """
        Return the `handle` associated with the path `col` in `target`.
        """
        target_paths = cls.get_handles_property_defaults('path', target)
        for handle, target_path in target_paths.items():
            if col == target_path:
                return col

    @classmethod
    def delta_col(cls, col):
        return 'Delta ' + col

    @classmethod
    def name_cols(cls, cols):
        return OrderedDict([
            (col, {}) for col in cols
        ])

    @classmethod
    def get_col_names(cls, cols):
        col_names = OrderedDict()
        for col, data in cols.items():
            label = data.get('label')
            col_names[col] = label if label else col
        return col_names

    @classmethod
    def get_attribute_colnames_native(cls, attributes, vattributes):
        attribute_cols = OrderedDict()
        all_attrs = SeqUtils.combine_lists(
            attributes.keys(), vattributes.keys())
        for attr in all_attrs:
            new_keys = [
                'attribute:' + attr,
                'attribute_data:' + attr
            ]
            if attr in vattributes.keys():
                new_keys.extend([
                    'attribute_default:' + attr,
                ])
            for key in new_keys:
                attribute_cols[key] = key

        return attribute_cols

    @classmethod
    def get_attribute_meta_colnames_native(cls, vattributes):
        atttribute_meta_cols = OrderedDict()
        for attr in vattributes.keys():
            key = 'meta:attribute_' + attr
            atttribute_meta_cols[key] = key
        return atttribute_meta_cols

class ColDataAbstract(ColDataLegacy):
    """
    Store information about how to translate between disparate target schemas.
     - Each target represents a different data format
     - Each handle is a piece of data within that format
     - The properties of a handle show how to coerce data of that handle between formats
    """
    # TODO: make everything OrderedDict

    targets = {
        'api': {
            'wp-api': {
                'wp-api-v1': {
                    'wp-api-v1-edit': {},
                    'wp-api-v1-view': {}
                },
                'wp-api-v2': {
                    'wp-api-v2-edit': {},
                    'wp-api-v2-view': {}
                }
            },
            'wc-api': {
                'wc-legacy-api': {
                    'wc-legacy-api-v1': {
                        'wc-legacy-api-v1-edit': {},
                        'wc-legacy-api-v1-view': {}
                    },
                    'wc-legacy-api-v2': {
                        'wc-legacy-api-v2-edit': {},
                        'wc-legacy-api-v2-view': {},
                    },
                    'wc-legacy-api-v3': {
                        'wc-legacy-api-v3-edit': {},
                        'wc-legacy-api-v3-view': {},
                    },
                },
                'wc-wp-api': {
                    'wc-wp-api-v1': {
                        'wc-wp-api-v1-edit': {},
                        'wc-wp-api-v1-view': {},
                    },
                    'wc-wp-api-v2': {
                        'wc-wp-api-v2-edit': {},
                        'wc-wp-api-v2-view': {},
                    }
                }
            },
            'xero-api': {},
            'infusion-api': {},
        },
        'csv': {
            'gen-csv': {
                'gen-api': {}
            },
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
    }

    handle_cache = OrderedDict()
    handles_cache = OrderedDict()
    structure_morph_cache = OrderedDict()

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
    def find_in(cls, data, property_, ancestors=None, handle=None):
        """
        Prepare a jsonpath finder object for finding the given property of `handles`
        given a list of target ancestors.
        Return a mapping of `handle` to `property_value`
        """
        # Registrar.increment_stack_count('find_in')
        if handle is None:
            handle = '*'
        handles = [handle]
        properties = [property_]
        handle_finder = jsonpath.Fields(*handles)
        finder = handle_finder.child(jsonpath.Fields(*properties))
        if ancestors:
            finder = jsonpath.Union(
                finder,
                handle_finder\
                .child(jsonpath.Fields(*ancestors))\
                .child(jsonpath.Fields(*properties))
            )
        matches = finder.find(data)
        results = OrderedDict()
        for match in matches:
            # print("found match %50s for property %10s, ancestors %50s in %s" % (
            #     match.value,
            #     property_,
            #     str(ancestors)[:50],
            #     str(match.full_path)[:100]
            # ))
            value = match.value
            handle = match.full_path
            while hasattr(handle, 'left'):
                handle = handle.left
            handle = handle.fields[0]
            results[handle] = value
        return results

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
                'sync': True,
                'type': 'string',
                'structure': ('singular-object', ),
                'report' : False,
            }.get(property_)

    @classmethod
    def get_handle_property(cls, handle, property_, target=None):
        """
        Return the value of a handle's property in the context of target. Cache for performace.
        """
        if handle is None or property_ is None:
            return
        cache_key = (cls.__name__, handle, property_, target)
        if cache_key in cls.handle_cache:
            return copy(cls.handle_cache[cache_key])
        target_ancestors = cls.get_target_ancestors(cls.targets, target)
        if target and not target_ancestors:
            raise UserWarning("target %s not recognized:\n%s" % (
                target, pformat(cls.targets)
            ))
        results = cls.find_in(cls.data, property_, target_ancestors, handle)
        if results:
            response = results.items()[-1][1]
        else:
            response = cls.get_property_default(property_, handle)
        cls.handle_cache[cache_key] = response
        return response

    @classmethod
    def get_handles_property(cls, property_, target=None):
        """
        Return a mapping of handles to the value of `property_` wherever it is
        explicitly declared in the context of `target`. Cache for performance.
        """
        cache_key = (cls.__name__, property_, target)
        if cache_key in cls.handles_cache:
            return copy(cls.handles_cache[cache_key])
        target_ancestors = cls.get_target_ancestors(cls.targets, target)
        if target and not target_ancestors:
            raise UserWarning("target %s not recognized:\n%s" % (
                target, pformat(cls.targets)
            ))
        results = cls.find_in(cls.data, property_, target_ancestors, )
        cls.handles_cache[cache_key] = results
        return results

    @classmethod
    def get_handles_property_defaults(cls, property_, target=None):
        """
        Return a mapping of handles to the value of `property_` in the context
        of `target` or the default value if it is not explicitly set.
        """
        handles_property = cls.get_handles_property(property_, target)
        response = OrderedDict()
        for handle, properties in cls.data.items():
            if handle in handles_property:
                handles_property_value = handles_property.get(handle)
            else:
                handles_property_value = cls.get_property_default(property_, handle)
            response[handle] = handles_property_value
        return response

    @classmethod
    def get_handle_in_target(cls, path, target=None):
        if target is None:
            return path
        for handle, path_ in cls.get_target_path_translation(target).items():
            if path_ == path or handle == path:
                return handle

    @classmethod
    def get_property_inclusions(cls, property_, target=None):
        """
        Return a list of handles in which the value of `property_` in the context
        of `target` (or the default value if it is not explicitly set) is trueish.
        """
        response = set()
        if not property_:
            return response
        for handle, value in \
        cls.get_handles_property_defaults(property_, target).items():
            if value:
                response.add(handle)
        return response

    @classmethod
    def get_property_exclusions(cls, property_, target=None):
        """
        Return a list of handles in which the value of `property_` in the context
        of `target` (or the default value if it is not explicitly set) is not trueish.
        Return a list of handles whose value of `property_` in `target` is not True-ish.
        """
        response = set()
        if not property_:
            return response
        for handle, value in \
        cls.get_handles_property_defaults(property_, target).items():
            if not value:
                response.add(handle)
        return response

    @classmethod
    def get_properties_inclusions(cls, properties, target=None):
        """
        Return a list of handles whose value of `property_` in `target` is True-ish.
        """
        inclusions = []
        if not properties:
            return inclusions
        handles_properties = [
            cls.get_handles_property_defaults(property_, target) for property_ in properties
        ]
        for handle in cls.data.keys():
            handles_values = [
                handle_properties.get(handle) \
                for handle_properties in handles_properties
            ]
            if all(handles_values):
                inclusions.append(handle)
        return inclusions

    @classmethod
    def get_properties_exclusions(cls, properties, target=None):
        """
        Return a list of handles whose value of `property_` in `target` is not True-ish.
        """
        exclusions = []
        if not properties:
            return exclusions
        handles_properties = [
            cls.get_handles_property_defaults(property_, target) for property_ in properties
        ]
        for handle in cls.data.keys():
            handles_values = [
                handle_properties.get(handle) \
                for handle_properties in handles_properties
            ]
            if not all(handles_values):
                exclusions.append(handle)
        return exclusions

    @classmethod
    def get_target_path_translation(cls, target, excluding_properties=None):
        """
        Return a mapping of handles to paths in `target` structure.
        Exclude any handles that do not have a truthy value for all excluding properties.
        """
        if excluding_properties == None:
            excluding_properties = []
        if target == None:
            return
        path_translation = cls.get_handles_property_defaults('path', target)
        exclusions = cls.get_properties_exclusions(excluding_properties, target)
        return OrderedDict([
            (handle, path) \
            for handle, path in path_translation.items() \
            if handle not in exclusions
        ])

    @classmethod
    def get_core_path_translation(cls, target, excluding_properties=None):
        """
        Return an identity mapping of handles whose path exists in `target`.
        Exclude any handles that do not have a truthy value for all excluding properties including path.
        """
        if excluding_properties == None:
            excluding_properties = []
        if 'path' not in excluding_properties:
            excluding_properties = excluding_properties + ['path']
        exclusions = cls.get_properties_exclusions(excluding_properties, target)
        path_translation = OrderedDict([
            (handle, handle) \
            for handle in cls.data.keys() \
            if handle not in exclusions
        ])
        return path_translation

    # @classmethod
    # def path_exists(cls, data, path):
    #     """Deprecated, use get_from_path in try/catch block."""
    #     if not path:
    #         return
    #     if re.match(cls.re_simple_path, path):
    #         return path in data
    #     getter = jsonpath_ng.parse(path)
    #     return getter.find(data)

    @classmethod
    def get_from_path(cls, data, path, target=None):
        """
        Get the value at `path` from `data`, assuming structure given by `target`.
        """
        # TODO: get defaults necessary here?
        if not path:
            return
        if data is None:
            return
        if not isinstance(data, Mapping):
            raise IndexError(
                "%s.get_from_path only handles mapping types not %s" % (
                    cls.__name__,
                    data.__class__.__name__
                )
            )
        path_head, path_tail = JSONPathUtils.split_subpath(path)

        # Get subdata value and class from path head
        sub_data_cls = None
        if JSONPathUtils.is_simple_path(path_head):
            sub_data = data[path_head]
        else:
            # It could be a jsonpath expression
            getter = jsonpath_ng.parse(JSONPathUtils.quote_jsonpath(path_head))
            sub_data = getter.find(data)[0].value
        if path_tail:
            handle = cls.get_handle_in_target(path_head, target)
            sub_data_cls = cls.get_handle_property(handle, 'sub_data', target) or cls
            return sub_data_cls.get_from_path(sub_data, path_tail, target)
        return sub_data

    @classmethod
    def update_in_path(cls, data, path, value, target=None):
        if not path:
            return data
        if data is None:
            return data
        if not isinstance(data, Mapping):
            raise IndexError(
                "%s.update_in_path only handles mapping types not %s" % (
                    cls.__name__,
                    data.__class__.__name__
                )
            )
        path_head, path_tail = JSONPathUtils.split_subpath(path)

        if path_tail:
            handle = cls.get_handle_in_target(path_head, target)
            sub_structure = cls.get_handle_property(handle, 'structure', target)
            sub_data_cls = cls.get_handle_property(handle, 'sub_data', target) or cls

            try:
                sub_data = sub_data_cls.get_from_path(data, path_head, target)
            except (IndexError, KeyError) as exc:
                sub_data = {}
                if sub_structure:
                    if sub_structure[0].startswith('listed'):
                        sub_data = []

            tail_value = sub_data_cls.update_in_path(
                sub_data, path_tail, value, target
            )
        else:
            tail_value = value


        if JSONPathUtils.is_simple_path(path_head):
            data[path_head] = tail_value
            return data
        else:
            updater = jsonpath_ng.parse(JSONPathUtils.quote_jsonpath(path_head))
            return JSONPathUtils.blank_update(updater, data, tail_value)


    @classmethod
    def morph_data(cls, data, morph_functions, path_translation, target=None):
        """
        Translate the data using functions preserving paths.
        """
        for handle in morph_functions.keys():
            if handle in path_translation:
                target_path = path_translation.get(handle)
                try:
                    target_value = deepcopy(cls.get_from_path(
                        data, target_path, target
                    ))
                except (IndexError, KeyError):
                    continue
                try:
                    target_value = morph_functions.get(handle)(target_value)
                except (TypeError, ):
                    continue
                data = cls.update_in_path(
                    data, target_path, target_value, target
                )
        return data

    @classmethod
    def translate_paths_from(cls, data, target, translation=None):
        """
        Translate the path structure of data from `target` to core.
        """
        if translation is None:
            translation = cls.get_target_path_translation(target)
        if translation:
            response = OrderedDict()
            for handle, target_path in translation.items():
                if target_path is None:
                    continue
                try:
                    target_value = cls.get_from_path(data, target_path, target)
                    response = cls.update_in_path(
                        response,
                        handle,
                        deepcopy(target_value),
                        target
                    )
                except (IndexError, KeyError):
                    pass
            return response
        return deepcopy(data)

    @classmethod
    def translate_paths_to(cls, data, target, translation=None):
        """
        Translate the path structure of data from core to `target`.
        """
        if translation is None:
            translation = cls.get_target_path_translation(target)
        if translation:
            response = OrderedDict()
            for handle, target_path in translation.items():
                if target_path is None:
                    continue
                try:
                    target_value = cls.get_from_path(data, handle, target)
                    response = cls.update_in_path(
                        response,
                        target_path,
                        deepcopy(target_value),
                        target
                    )
                except (IndexError, KeyError):
                    pass
            return response
        return deepcopy(data)

    @classmethod
    def deconstruct_sub_entity(
        cls, sub_data, target, target_structure=None, forced_mapping_handle=None, excluding_properties=None
    ):
        # TODO: get rid of target_structure and forced_mapping_handle since they can be obained using target
        if target_structure is None:
            target_structure = cls.get_property_default('structure')
        path_translation = cls.get_target_path_translation(target)
        objects = []
        if target_structure[0] == 'singular-object':
            if sub_data:
                return cls.translate_data_from(
                    sub_data,
                    target,
                    excluding_properties=excluding_properties
                )
        elif target_structure[0] == 'singular-value':
            target_value_handle = target_structure[1]
            target_value_path = path_translation.get(target_value_handle, target_value_handle)
            if sub_data:
                return cls.translate_data_from(
                    cls.update_in_path(
                        {},
                        target_value_path,
                        sub_data,
                        target
                    ),
                    target,
                    excluding_properties=excluding_properties
                )
        elif target_structure[0] == 'listed-values':
            target_value_handle = target_structure[1]
            target_value_path = path_translation.get(target_value_handle, target_value_handle)
            objects = [
                cls.translate_data_from(
                    cls.update_in_path(
                        {},
                        target_value_path,
                        sub_value,
                        target
                    ),
                    target,
                    excluding_properties=excluding_properties
                ) for sub_value in sub_data
            ]
        elif target_structure[0] == 'listed-objects':
            objects = [
                cls.translate_data_from(
                    sub_object,
                    target,
                    excluding_properties=excluding_properties
                ) for sub_object in sub_data
            ]
        elif target_structure[0] == 'mapping-value':
            target_key_handle = target_structure[1][0]
            target_key_path = path_translation.get(target_key_handle)
            target_value_handle = target_structure[1][1]
            target_value_path = path_translation.get(target_value_handle, target_value_handle)
            objects = [
                cls.translate_data_from(
                    cls.update_in_path(
                        cls.update_in_path(
                            {},
                            target_key_path,
                            sub_key,
                            target
                        ),
                        target_value_path,
                        sub_value,
                        target
                    ),
                    target,
                    excluding_properties=excluding_properties
                ) for sub_key, sub_value in sub_data.items()
            ]
        elif target_structure[0] == 'mapping-object':
            target_key_handle = target_structure[1][0]
            target_key_path = path_translation.get(target_key_handle)
            objects = [
                cls.translate_data_from(
                    cls.update_in_path(
                        sub_value,
                        target_key_path,
                        sub_key,
                        target
                    ),
                    target,
                    excluding_properties=excluding_properties
                ) for sub_key, sub_value in sub_data.items()
            ]
        if forced_mapping_handle:
            mapping = {}
            for object_ in objects:
                try:
                    mapping_key = cls.get_from_path(object_, forced_mapping_handle, target)
                except (IndexError, KeyError):
                    continue
                mapping[mapping_key] = object_
            return mapping

        return objects

    @classmethod
    def reconstruct_sub_entity(
        cls, sub_data, target, target_structure=None, forced_mapping_handle=None, excluding_properties=None
    ):
        """
        The inverse of deconstruct_sub_entity.
        """
        # TODO: get rid of target_structure and forced_mapping_handle since they can be obained using target
        if target_structure is None:
            target_structure = cls.get_property_default('structure')
        path_translation = cls.get_target_path_translation(target)
        if target_structure[0] == 'singular-object':
             return cls.translate_data_to(
                sub_data,
                target,
                excluding_properties=excluding_properties
            )
        elif target_structure[0] == 'singular-value':
            target_value_handle = target_structure[1]
            target_value_path = path_translation.get(target_value_handle, target_value_handle)
            return cls.get_from_path(
                cls.translate_data_to(
                    sub_data,
                    target,
                    excluding_properties=excluding_properties
                ),
                target_value_path,
                target
            )
        else:
            objects = sub_data
            if forced_mapping_handle:
                assert isinstance(sub_data, dict), \
                "Expected sub_data to be dict, but got %s instead:\n%s" % (
                    type(sub_data),
                    pformat(sub_data)
                )
                objects = []
                for mapping_key, object_ in sub_data.items():
                    object_ = cls.update_in_path(
                        object_,
                        forced_mapping_handle,
                        mapping_key,
                        target
                    )
                    objects.append(object_)
            if target_structure[0] == 'listed-values':
                target_value_handle = target_structure[1]
                target_value_path = path_translation.get(target_value_handle, target_value_handle)
                return [
                    cls.get_from_path(
                        cls.translate_data_to(
                            sub_object,
                            target,
                            excluding_properties=excluding_properties
                        ),
                        target_value_path,
                        target
                    ) for sub_object in objects
                ]
            if target_structure[0] == 'listed-objects':
                return [
                    cls.translate_data_to(
                        sub_object,
                        target,
                        excluding_properties=excluding_properties
                    ) for sub_object in objects
                ]
            if target_structure[0] == 'mapping-value':
                target_key_handle = target_structure[1][0]
                target_key_path = path_translation.get(target_key_handle)
                target_value_handle = target_structure[1][1]
                target_value_path = path_translation.get(target_value_handle, target_value_handle)
                translated_objects = [
                    cls.translate_data_to(
                        sub_object,
                        target,
                        excluding_properties=excluding_properties
                    ) for sub_object in objects
                ]
                return OrderedDict([
                    (
                        cls.get_from_path(translated_object, target_key_path, target),
                        cls.get_from_path(translated_object, target_value_path, target)
                    ) for translated_object in translated_objects
                ])
            return objects


    @classmethod
    def get_structure_morph_functions(cls, target, direction='from', excluding_properties=None):
        cache_key = (cls.__name__, target, direction)
        if cache_key in cls.structure_morph_cache:
            return cls.structure_morph_cache.get(cache_key)
        target_sub_data_classes = cls.get_handles_property('sub_data', target)
        target_structures = cls.get_handles_property('structure', target)
        forced_mappings = cls.get_handles_property('force_mapping')
        morph_functions = OrderedDict()
        morph_function_attribute = {
            'from': 'deconstruct_sub_entity',
            'to': 'reconstruct_sub_entity'
        }[direction]
        for handle in cls.data.keys():
            if handle in target_structures:
                target_structure = target_structures.get(handle)
                if target_structure is None:
                    target_structure = cls.get_property_default('structure')
                assert isinstance(target_structure, tuple), \
                'target_structure for %s in %s should be a tuple not %s -> %s' % (
                    target, handle, type(target_structure), target_structure
                )
                morph_function = None
                target_sub_data_class = target_sub_data_classes.get(handle)
                forced_mapping_handle = forced_mappings.get(handle)
                if target_sub_data_class:
                    morph_function = functools.partial(
                        getattr(target_sub_data_class, morph_function_attribute),
                        target=target,
                        target_structure=target_structure,
                        forced_mapping_handle=forced_mapping_handle,
                        excluding_properties=excluding_properties
                    )
                if morph_function:
                    morph_functions[handle] = morph_function
        cls.structure_morph_cache[cache_key] = morph_functions
        return morph_functions


    @classmethod
    def translate_structure_from(cls, data, target, path_translation=None, excluding_properties=None):
        """
        Translate the Sub-entity structures in data between `target` and core.
        """
        morph_functions = cls.get_structure_morph_functions(target, 'from', excluding_properties)
        return cls.morph_data(data, morph_functions, path_translation, target)

    @classmethod
    def translate_structure_to(cls, data, target, path_translation=None, excluding_properties=None):
        """
        Translate the Sub-entity structures in data between core and `target`.
        """
        morph_functions = cls.get_structure_morph_functions(target, 'to', excluding_properties)
        return cls.morph_data(data, morph_functions, path_translation, target)

    @classmethod
    def get_normalizer(cls, type_):
        """
        Return the function to translate data between `type_` and the core
        representation.
        """
        if type(type_) == type:
            return type_
        if type_ is None:
            return SanitationUtils.identity

        # TODO: consider timezone when normalizing
        return {
            'xml_escaped': SanitationUtils.xml_to_unicode,
            'iso8601_utc': TimeUtils.normalize_iso8601,
            'iso8601_local': TimeUtils.normalize_iso8601_local,
            'iso8601_wp': TimeUtils.normalize_iso8601_wp,
            'iso8601_wp_t': TimeUtils.normalize_iso8601_wp_t,
            'iso8601_wp_t_z': TimeUtils.normalize_iso8601_wp_t_z,
            'iso8601_gdrive': TimeUtils.normalize_iso8601_gdrive,
            'datetime': SanitationUtils.identity,
            'timestamp_utc': TimeUtils.normalize_timestamp_utc,
            'timestamp_local': TimeUtils.normalize_timestamp_local,
            'timestamp_wp': TimeUtils.normalize_timestamp_wp,
            'gmt_timestamp_wp': TimeUtils.normalize_gmt_timestamp_wp,
            'timestamp_gdrive': TimeUtils.normalize_timestamp_gdrive,
            'wp_content_rendered': SanitationUtils.normalize_wp_rendered_content,
            'wp_content_raw': SanitationUtils.normalize_wp_raw_content,
            'yesno': SanitationUtils.yesno2bool,
            'stock_status': SanitationUtils.stock_status2bool,
            'mandatory_int': SanitationUtils.normalize_mandatory_int,
            'optional_int_minus_1': SanitationUtils.normalize_optional_int_minus_1,
            'optional_int_zero': SanitationUtils.normalize_optional_int_zero,
            'optional_int_none': SanitationUtils.normalize_optional_int_none,
            'optional_float_none': SanitationUtils.normalize_optional_float_none,
            'optional_float_zero': SanitationUtils.normalize_optional_float_zero,
            'php_array_associative': PHPUtils.unserialize_mapping,
            'php_array_indexed': PHPUtils.unserialize_list,
            'file_basename': FileUtils.get_path_basename,
            'mime_type': MimeUtils.validate_mime_type,
            'currency': SanitationUtils.similar_currency_comparison,
            'wc_api_default_attribute_list': SanitationUtils.identity,
        }.get(type_, SanitationUtils.coerce_unicode)

    @classmethod
    def get_denormalizer(cls, type_):
        """
        Return the function to translate data between the core representation
        and `type_`
        """
        return {
            'xml_escaped': SanitationUtils.coerce_xml,
            'iso8601_utc': TimeUtils.denormalize_iso8601,
            'iso8601_local': TimeUtils.denormalize_iso8601_local,
            'iso8601_wp': TimeUtils.denormalize_iso8601_wp,
            'iso8601_wp_t': TimeUtils.denormalize_iso8601_wp_t,
            'iso8601_wp_t_z': TimeUtils.denormalize_iso8601_wp_t_z,
            'iso8601_gdrive': TimeUtils.denormalize_iso8601_gdrive,
            'wp_datetime': functools.partial(
                TimeUtils.star_strf_datetime,
                fmt=TimeUtils.wp_datetime_format
            ),
            'yesno': SanitationUtils.bool2yesno,
            'stock_status': SanitationUtils.bool2stock_status,
            'php_array_associative': PHPUtils.serialize_mapping,
            'php_array_indexed': PHPUtils.serialize_list,
            'timestamp_utc': TimeUtils.denormalize_timestamp_utc,
            'timestamp_local': TimeUtils.denormalize_timestamp_local,
            'timestamp_wp': TimeUtils.denormalize_timestamp_wp,
            'gmt_timestamp_wp': TimeUtils.denormalize_gmt_timestamp_wp,
            'timestamp_gdrive': TimeUtils.denormalize_timestamp_gdrive,
            'wp_content_rendered': SanitationUtils.coerce_xml,
            'mime_type': MimeUtils.validate_mime_type,
            'currency': SanitationUtils.similar_currency_comparison,
            'api_currency': SanitationUtils.denormalize_api_currency,
            # 'optional_int_minus_1': SanitationUtils.coerce_unicode,
            # 'optional_int_zero': SanitationUtils.coerce_unicode,
            # 'optional_int_none': SanitationUtils.coerce_unicode,
            # 'optional_float_none': SanitationUtils.coerce_unicode,
            # 'optional_float_zero': SanitationUtils.coerce_unicode,
        }.get(type_, SanitationUtils.identity)

    # @classmethod
    # def translate_type_from(cls, handle, value, target):
    #     """
    #     Perform a single type translation between `target` and core for `value`
    #     """
    #     type_ = cls.get_handles_property('type', target).get('handle')
    #     morph_function = cls.get_normalizer(type_)
    #     return morph_function(value)

    @classmethod
    def translate_types_from(cls, data, target, path_translation=None):
        """
        Perform a translation of types between 'target' and core in the paths
        provided by path_translation, preserving those paths.
        """
        if path_translation is None:
            path_translation = cls.get_core_path_translation(target)
        morph_functions = OrderedDict([
            (handle, cls.get_normalizer(type_)) \
            for handle, type_ \
            in cls.get_handles_property('type', target).items()
        ])
        return cls.morph_data(
            data,
            morph_functions,
            path_translation,
            target
        )

    @classmethod
    def translate_types_to(cls, data, target, path_translation=None):
        """
        Perform a translation of types between core and `target` in the paths
        provided by path_translation, preserving those paths.
        """
        data = deepcopy(data)
        if path_translation is None:
            path_translation = cls.get_core_path_translation(target)
        morph_functions = OrderedDict([
            (handle, cls.get_denormalizer(type_)) \
            for handle, type_ \
            in cls.get_handles_property('type', target).items()
        ])
        return cls.morph_data(
            data,
            morph_functions,
            path_translation,
            target
        )

    # @classmethod
    # def translate_types_from_to(cls, data, target_from, target_to, path_translation=None):
    #     data = cls.translate_types_from(data, target_from, path_translation)
    #     return cls.translate_types_to(data, target_to, path_translation)

    @classmethod
    def translate_data_from(cls, data, target, excluding_properties=None):
        """
        Perform a full translation of paths and types between target and core
        """
        if not data:
            return data
        if not target:
            return data
        if excluding_properties is None:
            excluding_properties = []
        if 'path' not in excluding_properties:
            excluding_properties = ['path'] + excluding_properties

        data = deepcopy(data)
        # split target_path_translation on which handles have sub_data
        target_path_translation = cls.get_target_path_translation(
            target, excluding_properties=excluding_properties
        )
        core_path_translation = cls.get_core_path_translation(
            target, excluding_properties=excluding_properties
        )

        sub_data_handles = cls.get_property_inclusions('sub_data')

        # target paths which have sub_data
        sub_data_target_path_translation = OrderedDict([
            (key, value) for key, value in target_path_translation.items() \
            if key in sub_data_handles
        ])
        # target paths which don't sub_data
        non_sub_data_target_path_translation = OrderedDict([
            (key, value) for key, value in target_path_translation.items() \
            if key not in sub_data_handles
        ])
        # core paths which don't have sub_data
        non_sub_data_core_path_translation = OrderedDict([
            (key, value) for key, value in core_path_translation.items() \
            if key not in sub_data_handles
        ])

        # translate types of handles in target format which have sub_data
        data = cls.translate_types_from(
            data, target, sub_data_target_path_translation
        )
        # translate structure of handles in target format which have a path in target
        data = cls.translate_structure_from(
            data, target, target_path_translation, excluding_properties
        )
        # translate paths of handles into format in the order non_sub_data, sub_data
        ordered_target_path_translation = OrderedDict(
            non_sub_data_target_path_translation.items()
            + sub_data_target_path_translation.items()
        )
        data = cls.translate_paths_from(
            data, target, ordered_target_path_translation
        )
        # translate the rest of the types
        data = cls.translate_types_from(
            data, target, non_sub_data_core_path_translation
        )


        data = OrderedDict([
            (key, value) \
            for key, value in data.items() \
            if key in core_path_translation.values()
        ])

        return data

    @classmethod
    def translate_data_to(cls, data, target, excluding_properties=None):
        """
        Perform a full translation of paths and types between core and target
        """
        if not data:
            return data
        if not target:
            return data
        if excluding_properties is None:
            excluding_properties = []
        if 'path' not in excluding_properties:
            excluding_properties = ['path'] + excluding_properties

        data = deepcopy(data)

        # split target_path_translation on which handles have sub_data
        target_path_translation = cls.get_target_path_translation(
            target, excluding_properties=excluding_properties
        )
        core_path_translation = cls.get_core_path_translation(
            target, excluding_properties=excluding_properties
        )
        # TODO: roll path_translation_(pre|post) into get_path_translation functions

        sub_data_handles = cls.get_property_inclusions('sub_data')
        # target paths which have sub_data
        sub_data_target_path_translation = OrderedDict([
            (key, value) for key, value in target_path_translation.items() \
            if key in sub_data_handles
        ])
        # target paths which don't sub_data
        non_sub_data_target_path_translation = OrderedDict([
            (key, value) for key, value in target_path_translation.items() \
            if key not in sub_data_handles
        ])
        # core paths which don't have sub_data
        non_sub_data_core_path_translation = OrderedDict([
            (key, value) for key, value in core_path_translation.items() \
            if key not in sub_data_handles
        ])

        ordered_target_path_translation = OrderedDict(
            non_sub_data_target_path_translation.items()
            + sub_data_target_path_translation.items()
        )

        # translate types of non-subdata handles in core format
        data = cls.translate_types_to(
            data, target, non_sub_data_core_path_translation
        )
        # Translate all paths
        data = cls.translate_paths_to(
            data, target, ordered_target_path_translation
        )
        # translate subdata structure
        data = cls.translate_structure_to(
            data, target, target_path_translation, excluding_properties
        )
        # translate types of subdata handles in target format
        data = cls.translate_types_to(
            data, target, sub_data_target_path_translation
        )

        allowed_keys = set([
            key.split('.')[0] for key in
            target_path_translation.values()
        ])

        data = OrderedDict([
            (key, value) \
            for key, value in data.items() \
            if key in allowed_keys
        ])

        return data

    @classmethod
    def translate_data_from_to(cls, data, from_target, to_target, excluding_properties=None):
        data = cls.translate_data_from(data, from_target, excluding_properties)
        return cls.translate_data_to(data, to_target, excluding_properties)

    @classmethod
    def translate_data_from_to_simple(cls, data, from_target, to_target, excluding_properties=None):
        """
        Does naiive data translation that doesn't look at sub entities and
        doesn't delete unrecognised keys.
        """
        data = deepcopy(data)
        data = cls.translate_paths_from(
            data, from_target
        )
        data = cls.translate_types_from(
            data, from_target
        )
        data = cls.translate_types_to(
            data, to_target
        )
        data = cls.translate_paths_to(
            data, to_target
        )
        return data

    @classmethod
    def get_sync_handles(cls, main_target=None, subordinate_target=None):
        main_paths = cls.get_handles_property_defaults('path', main_target)
        subordinate_paths =  cls.get_handles_property_defaults('path', subordinate_target)
        main_writes = cls.get_handles_property_defaults('write', main_target)
        subordinate_writes = cls.get_handles_property_defaults('write', subordinate_target)
        sync_handles = OrderedDict()
        for handle in cls.data.keys():
            main_path = main_paths.get(handle)
            main_write = main_writes.get(handle)
            subordinate_path = subordinate_paths.get(handle)
            subordinate_write = subordinate_writes.get(handle)
            if not (main_path and subordinate_path):
                continue
            if not (main_write or subordinate_write):
                continue
            sync_handles[handle] = cls.data[handle]
        return sync_handles

class ColDataSubEntity(ColDataAbstract):
    """
    Metadata for abstract WP sub-entities
    - wp-api-v2: https://developer.wordpress.org/rest-api/reference/posts/
    - wp-api-v1: http://wp-api.org/index-deprecated.html#entities_post
    """
    data = deepcopy(ColDataAbstract.data)

class ColDataSubVariation(ColDataSubEntity):
    """
    Structure of data about a product's variations as they appear on the product.
    Not very well documented, but in wc-wp-api this is just a list of variation ids
    """
    data = deepcopy(ColDataSubEntity.data)
    data = SeqUtils.combine_ordered_dicts(data, {
        'id': {
            'write': False,
            'unique': True,
            'type': 'mandatory_int',
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
            'gen-csv': {
                'type': 'optional_int_none',
                'path': 'ID',
                'read': False,
            },
            'report': True
        },
    })

class CreatedModifiedGmtMixin(object):
    data = {
        'created_gmt': {
            'type': 'datetime',
            'write': False,
            'wp-api': {
                'path': 'date_gmt',
                'type': 'iso8601_utc',
            },
            'wc-wp-api': {
                'path': 'date_created_gmt',
                'type': 'iso8601_utc',
            },
            'wc-wp-api-v1': {
                'path': None,
            },
            'wp-sql': {
                'type': 'wp_datetime',
                'path': 'post_date_gmt'
            },
            'gen-csv': {
                'path': 'created_gmt',
                'read': False,
            },
            'wc-csv': {
                'path': None
            },
        },
        'modified_gmt': {
            'type': 'datetime',
            'write': False,
            'wp-api': {
                'path': 'modified_gmt',
                'type': 'iso8601_utc'
            },
            'wc-wp-api': {
                'path': 'date_modified_gmt',
                'type': 'iso8601_utc',
            },
            'wc-wp-api-v1': {
                'path': None,
            },
            'wp-sql': {
                'path': 'post_modified_gmt',
                'type': 'wp_datetime'
            },
            'gen-csv': {
                'path': 'modified_gmt',
                'type': 'datetime',
                'read': False,
            },
            'xero-api': {
                'path': 'UpdatedDateUTC',
                'type': 'iso8601_utc'
            },
            'wc-csv': {
                'path': None
            },
            'report': True,
        },
    }

class MenuOrderMixin(object):
    data = {
        'menu_order': {
            'type': int,
            'path': None,
            'wp-api': {
                'path': None
            },
            'wc-api': {
                'path': 'menu_order'
            },
            'wp-sql': {
                'path': 'term_meta.order'
            },
            'gen-csv': {
                'path': 'menu_order',
                'write': False,
                'read': False,
            },
            'wc-csv': {
                'path': 'menu_order',
                'write': False,
            }
        },
        'rowcount': {
            'path': None,
            'gen-csv': {
                'path': 'rowcount',
                'read': False,
                'write': False,
            },
            'wc-api': {
                'path': 'rowcount',
                'read': False,
                'write': False,
            }
        },
    }


class ColDataSubAttachment(ColDataSubEntity, CreatedModifiedGmtMixin):
    """
    Metadata for Media sub items; media items that appear within entities in the API
    - wc-wp-api-v2: http://woocommerce.github.io/woocommerce-rest-api-docs/#product-images-properties
    - wc-wp-api-v1: http://woocommerce.github.io/woocommerce-rest-api-docs/wp-api-v1.html#product-image-properties
    - wc-legacy-api-v3: http://woocommerce.github.io/woocommerce-rest-api-docs/v3.html#images-properties
    - wc-legacy-api-v2: http://woocommerce.github.io/woocommerce-rest-api-docs/v2.html#images-properties
    - wc-legacy-api-v1: http://woocommerce.github.io/woocommerce-rest-api-docs/v1.html#products
    """
    data = deepcopy(ColDataSubEntity.data)
    data = SeqUtils.combine_ordered_dicts(data, deepcopy(CreatedModifiedGmtMixin.data))
    data['created_gmt'].update({
        'wc-wp-api-v2-edit': {
            'path': None,
        },
        'sync': False
    })
    data['modified_gmt'].update({
        'wc-wp-api-v2-edit': {
            'path': None,
        },
        'sync': False
    })
    data = SeqUtils.combine_ordered_dicts(data, {
        'id': {
            'write': False,
            'unique': True,
            'type': 'mandatory_int',
            'api': {
                'path': 'id'
            },
            'wp-api-v1': {
                'path': 'ID'
            },
            'wp-sql': {
                'path': 'ID',
            },
            'gen-csv': {
                'type': 'optional_int_none',
            },
            'gen-api': {
                'path': 'ID'
            },
            'report': True
        },
        'title': {
            'type': 'unicode',
            'wc-wp-api':{
                'path': 'name',
                'type': 'wp_content_rendered'
            },
        },
        'source_url': {
            'write': False,
            'type': 'uri',
            'wc-wp-api': {
                'path':'src'
            },
            'gen-csv': {
                'write': True
            }
        },
        'alt_text': {
            'wc-wp-api': {
                'path': 'alt',
            }
        },
        'position': {
            'path': None,
            'wc-api': {
                'path': 'position'
            },
            'gen-csv': {
                'path': 'position'
            }
        },
        # 'file_name': {
        #     'path': None,
        #     'wc-wp-api': {
        #         'path': 'src',
        #         'type': 'file_basename',
        #         'write': False
        #     },
        #     'gen-csv': {
        #         'path': 'file_name',
        #         'read': False
        #     }
        # }
    })

class ColDataSubTermAttachment(ColDataSubAttachment):
    """
    Metadata for Media sub items; media items that appear within terms in the API
    """
    data = deepcopy(ColDataSubAttachment.data)
    del data['position']
    data['title'].update({
        'wc-wp-api': {
            'path': 'title',
            'type': 'wp_content_rendered'
        }
    })

class ColDataSubVarAttachment(ColDataSubAttachment):
    """
    Metadata for Media sub items of varitions.

    AFAIK It's the same as product but just to be safe...
    """
    data = deepcopy(ColDataSubAttachment.data)

class ColDataTermMixin(object):
    data = {
        'term_id': {
            'write': False,
            'unique': True,
            'type': 'mandatory_int',
            'wc-api': {
                'path': 'id'
            },
            'wp-api': {
                'path': 'id'
            },
            'wp-api-v1': {
                'path': 'ID'
            },
            'gen-csv': {
                'path': 'ID',
                'type': 'optional_int_none',
                'write': True,
            },
            'wp-sql': {
                'path': 'terms.term_id'
            },
            'report': True
        },
        'title': {
            'path': None,
            'wp-api-v1': {
                'path': 'name',
                'type': 'wp_content_rendered',
            },
            'wp-sql': {
                'path': 'terms.name',
                'type': 'wp_content_rendered',
            },
            'wc-api':{
                'path': 'name',
                'type': 'wp_content_rendered',
            },
            'gen-api': {
                'path': 'title',
            }
        },
        'slug':{
            'unique': True,
            'path': None,
            'wp-api': {
                'path': 'slug',
            },
            'wp-api-v1': {
                'path': 'name',
            },
            'wc-api': {
                'path': 'slug'
            },
            'wc-legacy-api': {
                'path': 'slug'
            },
            'wp-sql': {
                'path': 'terms.slug'
            },
            'gen-api': {
                'path': 'slug'
            }
        },
        'taxonomy': {
            'path': None,
            'default': 'category',
            'wp-api-v1': {
                'path': 'taxonomy'
            },
            'wp-sql': {
                'path': 'term_taxonomy.taxonomy'
            }
        },
        'count': {
            'type': 'optional_int_none',
            'path': None,
            'write': False,
            'wp-api-v1': {
                'path': 'count'
            },
            'wp-sql': {
                'path': 'term_taxonomy.count'
            }
        },
        'description': {
            'path': None,
            'wp-api-v1': {
                'path': 'description',
                'type': 'wp_content_rendered',
            },
            'wp-sql': {
                'path': 'term_taxonomy.description',
                'type': 'wp_content_rendered',
            },
            'gen-csv': {
                'path': 'descsum'
            },
        },
    }

class ColDataSubTerm(ColDataSubEntity, ColDataTermMixin):
    data = deepcopy(ColDataSubEntity.data)
    data = SeqUtils.combine_ordered_dicts(
        data,
        deepcopy(ColDataTermMixin.data)
    )
    data['term_id'].update({
        'wc-legacy-api': {
            'path': None
        }
    })
    data['slug'].update({
        'wc-legacy-api': {
            'path': None
        }
    })



class ColDataSubCategory(ColDataSubTerm):
    data = deepcopy(ColDataSubTerm.data)
    data = SeqUtils.combine_ordered_dicts(data, {
        'heirarchical_name': {
            'path': None,
            'wc-csv': {
                'path': 'heirarchical_name'
            }
        }
    })

class ColDataSubTag(ColDataSubTerm):
    data = deepcopy(ColDataSubTerm.data)
    data = SeqUtils.combine_ordered_dicts(data, {
    })

class ColDataTerm(ColDataAbstract, ColDataTermMixin):
    data = deepcopy(ColDataSubEntity.data)
    data = SeqUtils.combine_ordered_dicts(
        data,
        ColDataTermMixin.data
    )
    data['title'].update({
        'wp-sql': {
            'path': 'terms.name'
        },
        'csv': {
            'path': 'title'
        },
        'report': True,
    })
    data['slug'].update({
        'wp-sql': {
            'path': 'terms.slug'
        },
        'gen-csv': {
            'path': 'slug'
        },
        'report': True,
    })
    data['taxonomy'].update({
        'wp-sql': {
            'path': 'term_taxonomy.taxonomy'
        }
    })
    data['count'].update({
        'wp-sql': {
            'path': 'term_taxonomy.count'
        }
    })
    data['description'].update({
        'wp-sql': {
            'path': 'term_taxonomy.description'
        },
        'wc-api': {
            'path': 'description'
        },
        'csv': {
            'path': 'descsum'
        },
        'report': True,
    })
    data = SeqUtils.combine_ordered_dicts(data, {
        'term_parent': {
            'path': None,
            'wp-api-v1': {
                'path': 'parent'
            }
        },
        'term_parent_id': {
            'path': None,
            'type': 'optional_int_none',
            'wp-api-v1': {
                'path': 'parent.ID'
            },
            'wp-sql': {
                'path': 'term_taxonomy.parent'
            },
            'wc-api': {
                'path': 'parent'
            },
            'csv': {
                'path': 'parent_id',
                'read': False,
            },
            'report': True
        },
        'term_link': {
            'path': None,
            'wp-api-v1': {
                'path': 'link'
            }
        },
        'term_meta': {
            'path': None,
            'wp-api-v1': {
                'path': 'meta'
            }
        }
    })

class ColDataWcTerm(ColDataTerm):
    data = deepcopy(ColDataTerm.data)
    data['count'].update(
        {
            'wc-api': {
                'path': 'count'
            }
        }
    )
    data = SeqUtils.combine_ordered_dicts(
        data,
        MenuOrderMixin.data
    )
    data['menu_order'].update({
        'wp-sql': {
            'path': 'menu_order'
        }
    })

class ColDataAttributeTerm(ColDataWcTerm):
    """
    Metadata for an attribute term on top of existing data from ColDataWCTerm or ColDataSubTerm.

    e.g.
    GET /wp-json/wc/v2/products/attributes/3/terms
    ```json
    [
    {
        "_links": {
            ...
        },
        "count": 28,
        "description": "",
        "id": 152,
        "menu_order": 0,
        "name": "Mosaic Minerals",
        "slug": "mosaic-minerals"
    },
    ...
    ```

    https://woocommerce.github.io/woocommerce-rest-api-docs/#product-attribute-terms
    """
    data = deepcopy(ColDataWcTerm.data)

class ColDataAttributeTaxonomyMixin(object):
    """
    Mixin for an attribute taxonomy.

    e.g.
    GET /wp-json/wc/v2/products/attributes
    ```json
    [
    {
        "_links": {
            ...
        },
        "has_archives": true,
        "id": 3,
        "name": "brand",
        "order_by": "menu_order",
        "slug": "pa_brand",
        "type": "select"
    },
    ...
    ```
    https://woocommerce.github.io/woocommerce-rest-api-docs/#product-attributes
    """
    data = {
        'attr_id': {
            'wc-wp-api': {
                'path': 'id',
                'type': 'mandatory_int'
            },
            'wp-sql': {
                'path': 'attribute_taxonomies.attribute_id'
            }
        },
        'name': {
            'wp-sql': {
                'path': 'attribute_taxonomies.attribute_name'
            }
        },
        'slug': {
            'wp-sql': {
                'path': 'term_taxonomy.taxonomy'
            },
            'wc-api': {
                'path': None
            }
        },
        'type': {
            'wp-sql': {
                'path': 'attribute_taxonomies.attribute_type'
            }
        },
        'has_archives': {
            'type': bool,
            'wp-sql': {
                'path': 'attribute_taxonomies.attribute_public'
            }
        },
        'order_by': {
            'wp-sql': {
                'path': 'attribute_taxonomies.attribute_orderby'
            }
        }
    }

class ColDataAttributeSummaryMixin(object):
    """
    Mixin for the summary of a product's attribute taxonomy.

    Has fields from attribute taxonomy and term
    """
    data = OrderedDict([
        (key, value) for (key, value) in ColDataAttributeTaxonomyMixin.data.items() \
        if key in ['attr_id', 'name', 'slug']
    ])
    data = SeqUtils.combine_ordered_dicts(data, {
        'options': {
            'path': None,
            'sub_data': ColDataAttributeTerm,
            'structure': ('listed-values', 'title'),
            'wc-api': {
                'path': 'options'
            },
        },
    })

class ColDataAttributeInstanceMixin(object):
    """
    Mixin for the summary of a variations attribute value.

    Has fields from attribute taxonomy and term
    """
    data = deepcopy(OrderedDict([
        (key, value) for (key, value) in ColDataAttributeTaxonomyMixin.data.items() \
        if key in ['attr_id', 'name', 'slug']
    ] + [
        (key, value) for (key, value) in ColDataAttributeTerm.data.items() \
        if key in ['title']
    ]))
    data['title'].update({
        'path': 'option',
        'wc-api': {
            'path': 'option'
        }
    })

class ColDataSubAttribute(ColDataSubEntity, ColDataAttributeSummaryMixin):
    """
    An item in a list of a product's attributes.

    This is a summary of attribute taxonomy and term info.
    https://woocommerce.github.io/woocommerce-rest-api-docs/#product-attributes-properties
    """
    data = deepcopy(ColDataSubEntity.data)
    data = SeqUtils.combine_ordered_dicts(
        data,
        deepcopy(ColDataAttributeSummaryMixin.data)
    )
    data = SeqUtils.combine_ordered_dicts(data, {
        'position': {
            'path': None,
            'wc-api': {
                'path': 'position'
            }
        },
        'visible': {
            'path': None,
            'type': bool,
            'wc-api': {
                'path': 'visible'
            },
            'wp-sql': {
                'path': 'is_visible'
            }
        },
        'variation': {
            'path': None,
            'type': bool,
            'wc-api': {
                'path': 'variation'
            },
            'wp-sql': {
                'path': 'is_variation'
            },
        },
    })

class ColDataSubDefaultAttribute(ColDataSubEntity, ColDataAttributeInstanceMixin):
    """
    An item in a list of a product's default attributes

    https://woocommerce.github.io/woocommerce-rest-api-docs/#product-default-attributes-properties
    """
    data = deepcopy(ColDataSubEntity.data)
    # term_id, title, slug, taxonomy, count, description, term_parent, term_parent_id, term_link, term_meta
    data = SeqUtils.combine_ordered_dicts(
        data,
        deepcopy(ColDataAttributeInstanceMixin.data)
    )
    data = SeqUtils.combine_ordered_dicts(data, {
        'option': {
            'path': None,
            'wc-api': {
                'path': 'option'
            }
        }
    })

class ColDataSubVarAttribute(ColDataSubEntity, ColDataAttributeInstanceMixin):
    """
    Product variation attributes:
    https://woocommerce.github.io/woocommerce-rest-api-docs/#product-variation-attributes-properties

    e.g.
    ```
    ...
    "attributes": [
        {
            "id": 0,
            "name": "size",
            "option": "Large"
        }
    ],
    ...
    ```
    """

    data = deepcopy(ColDataSubEntity.data)
    # term_id, title, slug, taxonomy, count, description
    data = SeqUtils.combine_ordered_dicts(
        data,
        deepcopy(ColDataAttributeInstanceMixin.data)
    )

    data = SeqUtils.combine_ordered_dicts(data, {
    })

class ColDataSubMeta(ColDataSubEntity):
    data = deepcopy(ColDataSubEntity.data)
    data = SeqUtils.combine_ordered_dicts(data, {
        'meta_id': {
            'wc-api': {
                'path': 'id'
            },
        },
        'meta_key': {
            'wc-api': {
                'path': 'key'
            },
            'wp-api': {
                'path': 'key'
            },
            'gen-csv': {
                'path': 'key'
            }
        },
        'meta_value': {
            'wc-api': {
                'path': 'value'
            },
            'wp-api': {
                'path': 'value'
            },
            'gen-csv': {
                'path': 'value'
            }
        }
    })

    @classmethod
    def get_from_path(cls, data, path, target=None):
        if not isinstance(data, list):
            return super(ColDataSubMeta, cls).get_from_path(data, path, target)

        path_head, path_tail = JSONPathUtils.split_subpath(path)
        if not JSONPathUtils.is_simple_path(path_head):
            raise UserWarning(
                "complex jsonpath %s not supported for meta" % path
            )
        # handles_paths = cls.get_handles_property('path', target)
        # This is only called after transform structure, so core path
        handles_paths = cls.get_handles_property('path', None)
        path_key = handles_paths.get('meta_key') or 'meta_key'
        value_key = handles_paths.get('meta_value') or 'meta_value'
        value_index = None
        for index, sub_data in enumerate(data):
            if sub_data.get(path_key) == path_head:
                value_index = index
                break
        if value_index is None:
            raise IndexError("No key %s in data %s" % (
                path_head, data
            ))
        value = data[value_index].get(value_key)
        if path_tail:
            return cls.get_from_path(value, path_tail, target)
        return value


    @classmethod
    def update_in_path(cls, data, path, value, target=None):
        if not isinstance(data, list):
            return super(ColDataSubMeta, cls).update_in_path(data, path, value, target)

        path_head, path_tail = JSONPathUtils.split_subpath(path)

        if not JSONPathUtils.is_simple_path(path_head):
            raise UserWarning(
                "complex jsonpath %s not supported for meta" % path
            )

        if path_tail:
            handle = cls.get_handle_in_target(path_head, target)
            sub_structure = cls.get_handle_property(handle, 'structure', target)
            sub_data_cls = cls.get_handle_property(handle, 'sub_data', target) or cls
            sub_data = sub_data_cls.get_from_path(data, path_head, target)
            tail_value = sub_data_cls.update_in_path(
                sub_data, path_tail, value, target
            )
        else:
            tail_value = value

        # handles_paths = cls.get_handles_property('path', target)
        # This is only called before transform structure, so core path
        handles_paths = cls.get_handles_property('path', None)
        path_key = handles_paths.get('meta_key') or 'meta_key'
        value_key = handles_paths.get('meta_value') or 'meta_value'
        value_index = None
        for index, sub_data in enumerate(data):
            if sub_data.get(path_key) == path_head:
                value_index = index
                break
        if value_index is None:
            value_index = len(data)
            data.append({
                path_key: path_head,
                value_key: tail_value
            })
        else:
            data[value_index][value_key] = tail_value
        return data



class ColDataSubDownload(ColDataSubEntity):
    data = deepcopy(ColDataSubEntity.data)
    data = SeqUtils.combine_ordered_dicts(data, {
        'download_id': {
            'path': None,
            'wc-api': {
                'path': 'id'
            },
        },
        'title': {
            'path': None,
            'wc-api': {
                'path': 'name'
            }
        },
        'file': {
            'path': None,
            'wc-api': {
                'path': 'file'
            }
        }
    })

class ColDataSubUser(ColDataSubEntity):
    data = deepcopy(ColDataSubEntity.data)
    data = SeqUtils.combine_ordered_dicts(data, {
        'user_id': {
            'type': 'optional_int_none',
            'wp-api-v1': {
                'path': 'ID'
            }
        },
        'name': {
            'path': None,
            'wp-api-v1': {
                'path': 'name'
            }
        },
        'slug': {
            'path': None,
            'wp-api-v1': {
                'path': 'slug'
            }
        },
        'url': {
            'path': None,
            'wp-api-v1': {
                'path': 'url'
            }
        },
        'avatar': {
            'path': None,
            'wp-api-v1': {
                'path': 'avatar'
            }
        },
        'meta': {
            'path': None,
            'wp-api-v1': {
                'path': 'meta'
            }
        },
        'first_name': {
            'path': None,
            'wp-api-v1': {
                'path': 'first_name'
            }
        },
        'last_name': {
            'path': None,
            'wp-api-v1': {
                'path': 'last_name'
            }
        },
    })

class ColDataWcProdCategory(ColDataWcTerm):
    data = deepcopy(ColDataWcTerm.data)
    data['count'].update(
        {
            'wp-sql': {
                'path': 'term_meta.product_count_product_cat'
            },
        }
    )
    data['term_parent_id'].update(
        {
            'wc-api': {
                'path': 'parent'
            }
        }
    )
    data['title'].update(
        {
            'gen-api': {
                'path': 'cat_name'
            }
        }
    )
    data = SeqUtils.combine_ordered_dicts(data, {
        'display': {
            'path': None,
            'options': [
                'default', 'products', 'subcategories', 'both'
            ],
            'default': 'default',
            'wc-api': {
                'path': 'display',
            },
            'gen-csv': {
                'path': 'display'
            },
        },
        # 'thumbnail_id': {
        #     'path': None,
        #     'wc-api': {
        #         'path': 'image.id'
        #     },
        #     'wp-sql': {
        #         'path': 'term_meta.thumbnail_id'
        #     }
        # },
        'image': {
            'path': None,
            'sub_data': ColDataSubTermAttachment,
            'wc-api': {
                'path': 'image',
                'structure': ('singular-object', )
            },
            'wp-sql': {
                'path': 'term_meta.thumbnail_id',
                'structure': ('singular-value', 'id')
            },
            'csv': {
                'path': 'Images',
                'structure': ('singular-value', 'file_name')
            },
            'gen-api': {
                'path': 'attachment_object',
                'structure': ('singular-object', )
            },
            'image': True,
        }
    })

class ColDataWpEntity(ColDataAbstract, CreatedModifiedGmtMixin, MenuOrderMixin):
    """
    Metadata for abstract WP objects based off wp post object
    - wp-api-v2: https://developer.wordpress.org/rest-api/reference/posts/
    - wp-api-v2: http://v2.wp-api.org/reference/posts/
    - wp-api-v1: http://wp-api.org/index-deprecated.html#entities_post
    """
    data = deepcopy(ColDataAbstract.data)
    data = SeqUtils.combine_ordered_dicts(data, CreatedModifiedGmtMixin.data)
    data = SeqUtils.combine_ordered_dicts(data, MenuOrderMixin.data)
    data = SeqUtils.combine_ordered_dicts(data, {
        # TODO: rename to post_id?
        'id': {
            'write': False,
            'unique': True,
            'type': 'optional_int_none',
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
            'gen-csv': {
                'path': 'ID',
                'read': False,
                'write': True,
            },
            'wc-csv': {
                'write': False
            },
            'report': True
        },
        'permalink': {
            'write': False,
            'path': None,
            'wp-api': {
                'path': 'link'
            },
            'wc-api': {
                'path': 'permalink'
            },
        },
        'guid': {
            'write': False,
            'path': None,
            'wp-api': {
                'path': 'guid.rendered'
            },
            'wp-sql': {
                'path': 'guid'
            }
        },
        'created_local': {
            'type': 'datetime',
            'write': False,
            'wp-api': {
                'path': 'date',
                'type': 'iso8601_wp_t',
            },
            'wc-wp-api': {
                'path': 'date_created',
                'type': 'iso8601_wp_t',
            },
            'wc-legacy-api': {
                'path': 'created_at',
                'type': 'iso8601_wp_t_z',
            },
            'wp-sql':{
                'path': 'post_date',
                'type': 'wp_datetime',
            },
            'csv': {
                'path': None,
            },
            'xero-api': {
                'path': None
            }
        },
        'modified_local': {
            'type': 'datetime',
            'write': False,
            'wc-wp-api': {
                'path': 'date_modified',
                'type': 'iso8601_wp_t',
            },
            'wc-legacy-api': {
                'path': 'modified_at',
                'type': 'iso8601_wp_t_z',
            },
            'wc-legacy-api-v3': {
                'path': 'updated_at'
            },
            'wp-api': {
                'path': 'modified',
                'type': 'iso8601_wp_t'
            },
            'wp-sql': {
                'path': 'post_modified',
                'type': 'iso8601_wp'
            },
            'csv': {
                'path': None,
            },
            'gen-csv': {
                'path': 'modified_local',
                'read': False,
            },
            'xero-api': {
                'path': None
            },
            'report': True,
        },
        'created_timezone': {
            'path': None,
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
            },
        },
        'modified_timezone': {
            'write': False,
            'path': None,
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
            },
        },
        'slug':{
            'unique': True,
            'path': None,
            'wp-api': {
                'path': 'slug',
                'write': False,
            },
            'wp-api-v1': {
                'path': 'name'
            },
            'wc-api': {
                'path': 'slug',
                'write': False,
            },
            'wc-legacy-api': {
                'path': None
            },
            'wp-sql': {
                'path': 'post_name'
            },
            'gen-csv': {
                'path': 'slug',
                'read': False
            },
        },
        'title': {
            'wp-api':{
                'path': 'title.rendered',
                'type': 'wp_content_rendered'
            },
            'wp-api-v2-edit': {
                'path': 'title.raw',
                'type': 'wp_content_raw'
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
            'gen-csv': {
                'path': 'title',
                'read': False,
            },
            'gen-api': {
                'read': True
            },
            'report': True,
        },
        # 'itemsum': {
        #     'path': None,
        #     'gen-csv': {
        #         'path': 'itemsum',
        #         'read': False,
        #     },
        # },
        'post_status': {
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
            'wc-api': {
                'path': 'status'
            },
            'wp-api': {
                'path': 'status'
            },
            'xero-api': {
                'path': None
            }
        },
        'post_type': {
            'write': False,
            'path': None,
            'default': 'post',
            'wp-sql': {
                'path': 'post_type'
            },
            'wp-api': {
                'path': 'type'
            }
        },
        'post_content': {
            'wc-api': {
                'path': 'description',
                'type': 'wp_content_rendered',
            },
            'wp-api':{
                'path': 'content.rendered',
                'type': 'wp_content_rendered',
                'write': False
            },
            'wp-api-v2-edit': {
                'path': 'content.raw',
                'type': 'wp_content_raw',
                'write': True,
            },
            'wp-api-v1': {
                'path': 'content_raw'
            },
            'wp-sql': {
                'type': None,
                'path': 'post_content'
            },
            'wc-csv': {
                'path': 'post_content'
            },
            'gen-csv': {
                'path': 'descsum',
                'read': False,
            },
            'gen-api': {
                'read': True
            },
            'xero-api': {
                'path': 'Description'
            },
        },
        'post_excerpt': {
            'wc-api': {
                'path': 'short_description',
                'type': 'wp_content_rendered',
            },
            'wp-api': {
                'path': 'excerpt.rendered',
                'type': 'wp_content_rendered'
            },
            'wp-api-v2-edit': {
                'path': 'excerpt.raw',
                'type': 'wp_content_raw'
            },
            'wp-api-v1': {
                'path': 'excerpt_raw'
            },
            'wp-sql': {
                'path': 'post_excerpt'
            },
            'gen-csv': {
                'path': None,
            },
        },
        'mime_type': {
            'write': False,
            'path': None,
            'type': 'mime_type',
            'wc-api': {
                'path': None,
            },
            'wp-sql': {
                'path': 'post_mime_type'
            },
        },
        'parent_id': {
            'type': 'optional_int_none',
            'wp-sql': {
                'path': 'post_parent'
            },
            'wp-api': {
                'path': None,
            },
            'wp-api-v1': {
                'path': 'parent.id'
            },
            'wc-api': {
                'path': 'parent_id'
            },
            'wc-csv': {
                'path': 'post_parent',
                'read': False,
            },
            'gen-csv': {
                'read': False,
            },
            'xero-api': {
                'path': None
            }
        },
        'terms': {
            'path': None,
            'sub_data': ColDataSubTerm,
            'wp-api-v1': {
                'path': 'terms',
                'structure': ('mapping-dynamic', 'taxonomy')
            },
        },
        'meta': {
            'sub_data': ColDataSubMeta,
            # 'force_mapping': 'meta_key',
            'structure': ('listed-objects', ),
            'default': [],
            'sync': False,
            'wp-api': {
                'path': 'meta'
            },
            'wp-api-v1': {
                'path': 'post_meta',
                'structure': ('mapping-value', ('meta_key', 'meta_value'))
            },
            'wc-api': {
                'path': 'meta_data'
            },
            'wc-legacy-api': {
                'path': 'custom_meta'
            },
            'wp-sql':{
                'path': None,
            },
            'wc-csv': {
                'path': None
            },
            'gen-csv': {
                'path': None
            },
            'gen-api': {
                'path': 'meta',
                'structure': ('mapping-value', ('meta_key', 'meta_value')),
                'read': False,
                'default': {}
            },
            'xero-api': {
                'path': None
            }
        },
        'post_categories': {
            'path': None,
            'sub_data': ColDataSubCategory,
            'wc-api': {
                'path': None
            },
            'wc-legacy-api': {
                'path': 'categories',
                'structure': ('listed-values', 'title')
            },
            'wp-api': {
                'path': 'categories',
                'structure': ('listed-values', 'term_id'),
            },
            'wp-api-v1': {
                # note: in wp-api-v1 terms.category is an object if there is
                # one category but a list if there are multiple
                # since the data does not have a consistent format,
                'type': 'wp_api_v1_category',
                'path': None,
            },
            'gen-csv': {
                'path': None,
            },
            'category': True,
        },
        # 'category_ids': {
        #     'path': None,
        #     'wp-api': {
        #         'path': 'categories'
        #     },
        #     'wp-api-v1': {
        #         'path': 'terms.categories'
        #     },
        #     'wc-api': {
        #         'path': 'categories[*].id'
        #     }
        # },
        # 'category_names': {
        #     'path': None,
        #     'wc-api': {
        #         'write': False,
        #         'path': 'categories[*].name'
        #     },
        #     'wc-legacy-api': {
        #         'path': 'categories'
        #     },
        # },
        'tags': {
            'sub_data': ColDataSubTag,
            'path': None,
            'wp-api-v1': {
                'type': 'wp_api_v1_term',
                'path': None,
            },
            'wc-api': {
                'structure': ('listed-objects', )
            },
            'wc-legacy-api': {
                'structure': ('listed-values', 'title')
            },
            'csv': {
                'path': 'tags',
                'type': 'pipe_array'
            },
            'wc-csv': {
                'path': 'tax:product_tag',
            },
            'gen-csv': {
                'read': False,
            }
        },
        'template': {
            'path': None,
            'wp-api': {
                'path': 'template'
            }
        },
    })

class ColDataWpPost(ColDataWpEntity):
    data = deepcopy(ColDataWpEntity.data)
    data = SeqUtils.combine_ordered_dicts(data, {
        'password': {
            'path': None,
            'wp-api': {
                'path': 'password'
            },
            'wp-sql': {
                'path': 'post_password'
            }
        },
        'author': {
            'path': None,
            'sub_data': ColDataSubUser,
            'wp-api': {
                'path': 'author',
                'structure': ('singular-value', 'user_id')
            },
            'wp-api-v1':{
                'path': 'author',
                'structure': ('singular-object', )
            },
            'wp-sql': {
                'path': 'post_author',
                'structure': ('singular-value', 'user_id')
            },
            'gen-csv': {
                'path': 'author_id',
                'structure': ('singular-value', 'user_id')
            },
        },
        # 'author_id': {
        #     'type': int,
        #     'wp-api': {
        #         'path': 'author'
        #     },
        #     'wp-api-v1': {
        #         'path': 'author.ID'
        #     },
        #     'wp-sql': {
        #         'path': 'post_author'
        #     }
        # },
        # TODO: merge with image?
        'featured_media_id': {
            'path': None,
            'type': 'optional_int_zero',
            'wp-api': {
                'path': 'featured_media'
            },
            'wp-api-v1': {
                'path': 'featured_image.ID'
            },
            'wp-sql': {
                'path': 'meta._thumbnail_id'
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
            },
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
        'liveblog_likes': {
            'type': int,
            'path': None,
            'wp-api': {
                'path': 'liveblog_likes'
            }
        }
    })

class ColDataProduct(ColDataWpEntity):
    """
    - wc-wp-api-v2: http://woocommerce.github.io/woocommerce-rest-api-docs/#product-properties
    - wc-wp-api-v1
    - wc-legacy-api: http://woocommerce.github.io/woocommerce-rest-api-docs/v3.html#products
    - wp-api-v2: http://v2.wp-api.org/reference/posts/
    - wp-api-v1: http://wp-api.org/index-deprecated.html#posts
    """

    data = deepcopy(ColDataWpEntity.data)
    del data['post_categories']
    del data['template']
    data['post_type'].update({
        'path': None,
        'default': 'product',
        'wp-api': {
            'path': None,
        }
    })
    data['parent_id'].update({
        'write': False
    })
    data = OrderedDict(data.items() + {
        'product_type': {
            'default': 'simple',
            'wc-api': {
                'path': 'type'
            },
            'wc-csv': {
                'path': 'tax:product_type'
            },
            'gen-csv': {
                'path': 'prod_type',
                'read': False,
            },
            'gen-api': {
                'read': True
            },
            'wp-sql': {
                'path': None,
            },
            'options': [
                'simple',
                'grouped',
                'external',
                'variable',
                # 'composite',
                # 'bundle'
            ],
            'xero-api': {
                'path': None
            }
        },
        'product_categories': {
            'path': None,
            'sub_data': ColDataSubCategory,
            'wc-api': {
                'path': 'categories',
                'structure': ('listed-objects', )
            },
            'wc-legacy-api': {
                'path': 'categories',
                'structure': ('listed-values', 'title')
            },
            'wp-api': {
                'path': None,
            },
            'gen-api': {
                'path': 'category_objects',
                'structure': ('listed-objects', )
            },
            'xero-api': {
                'path': None
            },
            'category': True
        },
        'product_category_list': {
            'path': None,
            # 'sub_data': ColDataSubCategory,
            'wc-csv': {
                'path': 'tax:product_cat',
                'type': 'heirarchical_pipe_array',
                # 'structure': ('listed-values'),
            },
            'gen-csv': {
                'path': 'catsum',
                'read': False,
                'type': 'heirarchical_pipe_array',
                # 'structure': ('listed-values'),
            },
            'category': True,
        },
        'featured': {
            'type': bool,
            'default': False,
            'wp-sql': {
                'path': 'meta._featured',
                'type': 'yesno',
                'default': 'no'
            },
            'csv': {
                'type': 'yesno',
                'default': 'no'
            },
            'gen-csv': {
                'read': False,
            },
            'xero-api': {
                'path': None
            }
        },
        'catalog_visibility': {
            'default': 'visible',
            'options': [
                'visible',
                'catalog',
                'search',
                'hidden'
            ],
            'wp-sql': {
                'path': 'meta._visibility'
            },
            'xero-api': {
                'path': None
            },
            'gen-csv': {
                'read': False,
            }
        },

        'sku': {
            'xero-api': {
                'path': 'Code'
            },
            'wc-csv': {
                'path': 'SKU'
            },
            'gen-csv': {
                'path': 'codesum',
                'read': False,
            },
            'wp-sql': {
                'path': 'meta._sku',
            },
            'report': True,
        },
        'price': {
            'type': 'currency',
            'write': False,
            'api': {
                'type': 'api_currency'
            },
            'wp-sql': {
                'path': 'meta._price',
            },
            'gen-csv': {
                'read': False,
                'path': None,
            },
            'xero-api': {
                'path': None
            }
        },
        'regular_price': {
            'type': 'currency',
            'api': {
                'type': 'api_currency'
            },
            'wp-sql': {
                'path': 'meta._regular_price'
            },
            'gen-csv': {
                'read': False,
            },
            'gen-api': {
                'read': True,
            },
            'xero-api': {
                'path': None
            }
        },
        'sale_price': {
            'type': 'currency',
            'api': {
                'type': 'api_currency'
            },
            'wp-sql': {
                'path': 'meta._sale_price'
            },
            'gen-csv': {
                'read': False,
            },
            'xero-api': {
                'path': None
            },
            'special': True
        },
        'sale_price_dates_from': {
            'type': 'datetime',
            'wc-api': {
                'path': 'date_on_sale_from',
                'type': 'iso8601_wp_t',
            },
            'wc-legacy-api': {
                'read': False,
                'path': 'sale_price_dates_from',
                'type': 'wp_date_local'
            },
            'wp-sql': {
                'path': 'meta._sale_price_dates_from',
                'type': 'timestamp_wp'
            },
            'gen-csv': {
                'read': False,
            },
            'wc-csv': {
                'type': 'iso8601_wp',
            },
            'xero-api': {
                'path': None
            },
            'special': True
        },
        'sale_price_dates_from_gmt': {
            'type': 'datetime',
            'path': None,
            'wc-api': {
                'path': 'date_on_sale_from_gmt',
                'type': 'iso8601_utc'
            },
            'wc-wp-api-v1': {
                'path': None
            },
            'special': True
        },
        'sale_price_dates_to': {
            'type': 'datetime',
            'wc-api': {
                'path': 'date_on_sale_to',
                'type': 'iso8601_wp_t',
            },
            'wc-legacy-api': {
                'read': False,
                'path': 'sale_price_dates_to',
                'type': 'wp_date_local'
            },
            'wp-sql': {
                'path': 'meta._sale_price_dates_to',
                'type': 'timestamp_wp'
            },
            'gen-csv': {
                'read': False
            },
            'wc-csv': {
                'type': 'iso8601_wp',
            },
            'xero-api': {
                'path': None
            },
            'special': True
        },
        'sale_price_dates_to_gmt': {
            'type': 'datetime',
            'path': None,
            'wc-api': {
                'path': 'date_on_sale_to_gmt',
                'type': 'iso8601_utc',
            },
            'wc-wp-api-v1': {
                'path': None
            },
            'special': True
        },
        # 'price_html': {
        #     'write': False,
        #     'path': None,
        #     'wc-api': {
        #         'path': 'price_html'
        #     }
        # },
        'on_sale': {
            'write': False,
            'path': None,
            'type': bool,
            'wc-api': {
                'path': 'on_sale'
            },
            'special': True
        },
        'purchasable': {
            'write': False,
            'path': None,
            'type': bool,
            'wc-api': {
                'path': 'purchasable'
            },
        },
        'total_sales': {
            'write': False,
            'path': None,
            'type': int,
            'wc-api': {
                'path': 'total_sales'
            },
            'wp-sql': {
                'path': 'meta.total_sales'
            },
            'wc-csv': {
                'path': 'meta:total_sales'
            },
        },
        'virtual': {
            'type': bool,
            'wp-sql': {
                'path': 'meta._virtual',
                'type': 'yesno'
            },
            'xero-api': {
                'path': None
            },
            'gen-csv': {
                'read': False,
            }
        },
        'downloadable': {
            'type': bool,
            'wp-sql': {
                'path': 'meta._downloadable',
                'type': 'yesno'
            },
            'xero-api': {
                'path': None
            },
            'gen-csv': {
                'read': False,
            }
        },
        'downloads': {
            'path': None,
            'sub_data': ColDataSubDownload,
            'wc-api': {
                'path': 'downloads',
                'sub_data': 'wc_wp_api_downloads'
            },
            'wp-sql': {
                'path': None
            },
        },
        'download_limit': {
            'type': 'optional_int_minus_1',
            'default': -1,
            'wc-api': {
                'path': 'download_limit',
            },
            'wp-sql': {
                'path': 'meta._download_limit'
            },
            'gen-csv': {
                'read': False,
            },
            'xero-api': {
                'path': None
            }
        },
        'download_expiry': {
            'type': 'optional_int_minus_1',
            'default': -1,
            'wp-sql': {
                'path': 'meta._download_expiry'
            },
            'xero-api': {
                'path': None
            },
            'gen-csv': {
                'read': False,
            },
        },
        'download_type': {
            'path': None,
            'wc-wp-api': {
                'path': 'download_type',
                'default': 'standard'
            }
        },
        'external_url': {
            'wc-legacy-api': {
                'path': 'product_url',
            },
            'wp-sql': {
                'path': 'meta._product_url',
            },
            'xero-api': {
                'path': None
            },
            'gen-csv': {
                'read': False,
            },
            'wc-csv': {
                'path': 'product_url'
            }
        },
        'button_text': {
            'wp-sql': {
                'path': 'meta._button_text'
            },
            'xero-api': {
                'path': None
            },
            'gen-csv': {
                'read': False,
            },
        },
        'tax_status': {
            'default': 'taxable',
            'options': [
                'taxable',
                'shipping',
                'none'
            ],
            'wp-sql': {
                'path': 'meta._tax_status'
            },
            'xero-api': {
                'path': None
            },
            'gen-csv': {
                'read': False,
            },
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
            },
            'gen-csv': {
                'read': False,
            },
        },
        # TODO: sync this later
        # 'manage_stock': {
        #     'type': bool,
        #     # 'default': False,
        #     'wp-sql': {
        #         'path': 'meta._manage_stock',
        #         'type': 'yesno',
        #         'default': 'no'
        #     },
        #     'xero-api': {
        #         'path': 'IsTrackedAsInventory',
        #     },
        #     'gen-csv': {
        #         'read': False,
        #     },
        # },
        'stock_quantity': {
            'type': 'optional_int_none',
            'xero-api': {
                'path': 'QuantityOnHand',
                'type': 'optional_float_none',
            },
            'csv': {
                'path': 'stock',
            },
            'wp-sql': {
                'path': 'meta._stock',
            },
            'gen-csv': {
                'read': False,
            },
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
            },
            'xero-api': {
                'path': None
            },
        },
        'backorders': {
            'options': [
                'no', 'notify', 'yes'
            ],
            'default': 'no',
            'wp-sql': {
                'path': 'meta._backorders'
            },
            'gen-csv': {
                'read': False,
            },
        },
        'backorders_allowed': {
            'type': bool,
            'path': None,
            'write': False,
            'wc-api': {
                'path': 'backorders_allowed'
            },
            'wc-csv': {
                'path': 'backorders',
                'type': 'yesno'
            },
            'gen-csv': {
                'read': False,
            },
        },
        'backordered': {
            'type': bool,
            'path': None,
            'write': False,
            'wc-api': {
                'path': 'backordered'
            },
            'gen-csv': {
                'read': False,
            },
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
            'gen-csv': {
                'read': False,
            },
            'wc-csv': {
                'path': 'meta:_sold_individually',
            },
            'xero-api': {
                'path': None
            },
        },
        'weight': {
            # 'type': 'optional_float_none',
            'wp-sql': {
                'path': 'meta._weight'
            },
            'xero-api': {
                'path': None
            }
        },
        'length': {
            'wc-api': {
                'path': 'dimensions.length'
            },
            'wp-sql': {
                'path': 'meta._length'
            },
            'xero-api': {
                'path': None
            }
        },
        'width': {
            'wc-api': {
                'path': 'dimensions.width'
            },
            'wp-sql': {
                'path': 'meta._width'
            },
            'xero-api': {
                'path': None
            }
        },
        'height': {
            'wc-api': {
                'path': 'dimensions.height'
            },
            'wp-sql': {
                'path': 'meta._height'
            },
            'xero-api': {
                'path': None
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
        # TODO: sync this later
        # 'upsell_ids': {
        #     'default': [],
        #     'wp-sql': {
        #         'path': 'meta._upsell_ids',
        #         'type': 'php_array_indexed',
        #         'default': ''
        #     },
        #     'csv': {
        #         'type': 'pipe_array',
        #         'default': ''
        #     },
        #     'gen-csv': {
        #         'read': False,
        #     },
        #     'xero-api': {
        #         'path': None
        #     }
        # },
        # 'upsell_skus': {
        #     'path': None,
        #     'wp-sql': {
        #         'path': 'meta._upsell_skus',
        #         'type': 'php_array_indexed'
        #     },
        #     'csv': {
        #         'type': 'pipe_array'
        #     },
        #     'xero-api': {
        #         'path': None
        #     }
        # },
        # 'cross_sell_ids': {
        #     'default': [],
        #     'wp-sql': {
        #         'path': 'meta._crosssell_ids',
        #         'type': 'php_array_indexed',
        #         'default': ''
        #     },
        #     'csv': {
        #         'type': 'pipe_array',
        #         'default': ''
        #     },
        #     'gen-csv': {
        #         'read': False,
        #     },
        #     'xero-api': {
        #         'path': None
        #     }
        # },
        # 'crosssell_skus': {
        #     'path': None,
        #     'wp-sql': {
        #         'path': 'meta._crosssell_skus',
        #         'type': 'php_array_indexed'
        #     },
        #     'csv': {
        #         'type': 'pipe_array'
        #     },
        # },
        'purchase_note': {
            'path': None,
            'wc-api': {
                'path': 'purchase_note',
                'type': 'wp_content_rendered'
            },
            'wp-sql': {
                'path': 'meta._purchase_note'
            }
        },
        'attachment_objects': {
            'sub_data': ColDataSubAttachment,
            'wc-api': {
                'path': 'images',
                'structure': ('listed-objects', )
            },
            'csv': {
                'path': 'Images',
                'type': 'pipe_array',
                'structure': ('listed-values', 'file_name')
            },
            'gen-api': {
                'path': 'attachment_objects',
                'type': None,
                'structure': ('listed-objects', )
            },
            'image': True,
        },
        'attributes': {
            'path': None,
            'sub_data': ColDataSubAttribute,
            'wc-api': {
                'path': 'attributes',
                'structure': ('listed-objects', )
            },
            'wp-sql': {
                'path': None,
                # 'path': 'meta._product_attributes',
                # 'type': 'php_array_associative',
                # 'structure': ('mapping-object', ('title', ))
            },
            'gen-api': {
                'path': 'attribute_objects',
                'structure': ('listed-objects', )
            },
            'attribute': True,
        },
        'default_attributes': {
            'path': None,
            'sub_data': ColDataSubDefaultAttribute,
            'wc-api': {
                'path': 'default_attributes',
                'type': 'wc_api_default_attribute_list'
            },
            'wp-sql': {
                'path': None
                # 'path': 'meta._default_attributes',
                # 'type': 'php_array_associative',
                # 'structure': ('listed-objects', )
            },
            'attribute': True,
        },
        'variations': {
            'path': None,
            'sub_data': ColDataSubVariation,
            'wc-wp-api': {
                'path': 'variations',
                'structure': ('listed-values', 'id')
            },
            'wc-legacy-api': {
                'path': 'variations',
                'structure': ('listed-objects', )
            },
            'gen-api': {
                'path': 'variations',
                'structure': ('listed-objects', )
            },
            'variation': True,
        },
        # 'variation_ids': {
        #     'path': None,
        #     'variation': None,
        #     'wc-api': {
        #         'path': 'variations'
        #     }
        # },

    }.items())

class ColDataProductVariation(ColDataProduct):
    """
    Fields that don't need to show up on wc-csv or need to be renamed:
    - catalog_visibility -> transform into visibility:(visible|catalog|search|hidden)
    done:
    - commissionable_value -> meta:commissionable_value
    - external_url -> product_url
    - price (already have regular_price)
    - virtual
    - meta



    TODO:
    what if variation?orderby=title ? since there is no title.
    """

    data = deepcopy(ColDataProduct.data)
    del data['variations']
    del data['product_category_list']
    del data['product_type']
    del data['product_categories']
    del data['title']
    del data['slug']
    del data['attachment_objects']
    del data['catalog_visibility']
    del data['button_text']
    del data['featured']
    del data['sold_individually']
    data['parent_id'].update({
        'write': True,
        'wc-api': {
            'path': None
        }
    })
    data['attributes'].update({
        'sub_data': ColDataSubVarAttribute,
    })

    data = SeqUtils.combine_ordered_dicts(
        data,
        OrderedDict([
            ('parent_sku', {
                'path': None,
                'gen-csv': {
                    'path': 'parent_SKU'
                },
                'wc-csv': {
                    'path': 'parent_sku'
                }
            }),
            ('image', {
                'path': None,
                'sub_data': ColDataSubVarAttachment,
                'wc-api': {
                    'path': 'image',
                    'structure': ('singular-object', )
                },
                'wp-sql': {
                    'path': 'term_meta.thumbnail_id',
                    'structure': ('singular-value', 'id')
                },
                'csv': {
                    'path': 'Images',
                    'structure': ('singular-value', 'file_name')
                },
                'gen-api': {
                    'path': 'attachment_object',
                    'structure': ('singular-object', )
                },
                'image': True,
            })
        ])
    )

class ColDataMeridianEntityMixin(object):
    data = OrderedDict({
        'wootan_danger': {
            'type': 'danger',
            'wc-api': {
                'path': 'meta_data.wootan_danger',
            },
            'wp-sql': {
                'path': 'meta.wootan_danger',
            },
            'wc-csv': {
                'path': 'meta:wootan_danger',
            },
            'gen-csv': {
                'path': 'D',
                'default': ''
            },
            'xero-api': {
                'path': None
            }
        },
        'commissionable_value': {
            'type': float,
            'wc-api': {
                'path': 'meta_data.commissionable_value'
            },
            'wp-sql': {
                'path': 'meta.commissionable_value'
            },
            'gen-csv': {
                'path': 'CVC'
            },
            'wc-csv': {
                'path': 'meta:commissionable_value'
            },
            'default': 0.0,
            'xero-api': {
                'path': None
            }
        },
        'gen_visibility': {
            'path': None,
            'gen-csv': {
                'path': 'VISIBILITY',
                'default': ''
            }
        },
        'is_purchased': {
            'path': None,
            'xero-api': {
                'path': 'isPurchased'
            },
            'gen-csv': {
                'path': 'is_purchased',
                'default': ''
            }
        },
        'is_sold': {
            'path': None,
            'xero-api': {
                'path': 'isSold'
            },
            'gen-csv': {
                'path': 'is_sold',
                'default': ''
            }
        },
        'specials_schedule': {
            'path': None,
            'gen-csv': {
                'path': 'SCHEDULE',
                'default': ''
            },
            'special': True
        },
        'dynamic_product_rulesets': {
            'path': None,
            'gen-csv': {
                'path': 'DYNPROD',
                'default': ''
            },
            'dynamic': True
        },
        'dynamic_category_rulesets': {
            'path': None,
            'gen-csv': {
                'path': 'DYNCAT',
                'default': ''
            },
            'dynamic': True
        },
        'product_attributes': {
            'path': None,
            'gen-csv': {
                'path': 'PA',
                'type': 'json',
                'structure': ('mapping-value', ('title', 'value')),
                'default': ''
            },
            'default': [],
            'attribute': True,
        },
        'variation_attributes': {
            'path': None,
            'gen-csv': {
                'path': 'VA',
                'type': 'json',
                'structure': ('mapping-value', ('title', 'value')),
                'default': ''
            },
            'default': [],
            'attribute': True,
        },
        'extra_categories': {
            'path': None,
            'gen-csv': {
                'path': 'E',
                'default': ''
            },
            'category': True,
        },
        'xero_description': {
            'path': None,
            'gen-csv': {
                'path': 'Xero Description',
                'default': ''
            }
        },
        'raw_description': {
            'path': None,
            'gen-csv': {
                'path': 'HTML Description',
                'write': False
            },
        },
        'xero_id': {
            'path': None,
            'gen-csv': {
                'path': 'item_id',
                'default': '',
                'read': False,
            },
            'xero-api': {
                'path': 'ItemID',
                'write': False,
            },
            'default': ''
        },
        'Updated': {
            'path': None,
            'gen-csv': {
                'path': 'Updated',
                'type': 'yesno'
            },
            'default': ''
        },
        # When Lasercommerce is active, the API reports these values in the admin
        # context, so they will never be properly synced
        'regular_price': {
            'path': None,
            'sync': False,
            'api': {
                'type': 'api_currency'
            },
            'special': True
        },
        'sale_price': {
            'path': None,
            'type': 'currency',
            'api': {
                'type': 'api_currency'
            },
            'sync': False,
            'special': True
        }
    }.items() + [
        (
            'lc_%s_%s' % (tier, field),
            {
                'read': import_,
                'pricing': True,
                'type': root_type,
                'wp-api': {
                    'type': wc_type
                },
                'wc-api': {
                    'type': wc_type
                },
                'wp-sql': {
                    'path': 'meta.lc_%s_%s' % (tier, field),
                    'type': wc_type
                },
                'wc-wp-api': {
                    'path': 'meta_data.lc_%s_%s' % (tier, field),
                },
                'wc-legacy-api': {
                    'path': 'meta.lc_%s_%s' % (tier, field),
                },
                'gen-csv': {
                    'path': ''.join([tier.upper(), field_slug.upper()]),
                    'type': gen_type,
                    'write': False
                },
                'wc-csv': {
                    'path': 'meta:lc_%s_%s' % (tier, field),
                    'type': wc_type
                },
                'xero-api': {
                    'path': None
                },
                'static': static,
                'special': special,
            }
        ) for (tier, (field_slug, field, import_, root_type, wc_type, gen_type, static, special)) in itertools.product(
            ['rn', 'rp', 'wn', 'wp', 'dn', 'dp'],
            [
                ('r', 'regular_price', True, 'currency', 'api_currency', 'currency', True, False),
                ('s', 'sale_price', False, 'currency', 'api_currency', 'currency', False, True),
                ('f', 'sale_price_dates_from', False, 'datetime', 'gmt_timestamp_wp', 'iso8601_gdrive', False, True),
                ('t', 'sale_price_dates_to', False, 'datetime', 'gmt_timestamp_wp', 'iso8601_gdrive', False, True)
                # Note: Wordpress definitely reads time in UTC timestamp.
            ]
        )
    ])
    data['lc_wn_regular_price'].update({
        'xero-api': {
            'path': 'SalesDetails.UnitPrice',
            'static': False,
        },
        'delta': True,
    })


class ColDataProductMeridian(ColDataProduct, ColDataMeridianEntityMixin):
    data = OrderedDict(
        ColDataProduct.data.items()
        + ColDataMeridianEntityMixin.data.items()
    )

class ColDataProductVariationMeridian(ColDataProductVariation, ColDataMeridianEntityMixin):
    data = SeqUtils.combine_ordered_dicts(
        ColDataProductVariation.data,
        ColDataMeridianEntityMixin.data
    )


class ColDataAttachment(ColDataWpEntity):
    """
    Metadata for Media items
    - wp-api-v2: http://v2.wp-api.org/reference/media/
    - wp-api-v1: http://wp-api.org/index-deprecated.html#entities_media
    """
    # TODO: replace rendered with raw?

    # the following wp-api keys exist in post schema but not media schema:
    # - categories
    # - content
    # - excerpt
    # - featured media
    # - format
    # - password
    # - sticky
    # - tags

    data = deepcopy(ColDataWpEntity.data)
    del data['post_categories']
    del data['terms']
    del data['tags']
    del data['modified_timezone']

    data['post_type'].update({
        'default': 'attachment'
    })
    data['post_content'].update({
        'wp-api': {
            'path': 'description.rendered',
            'type': 'wp_content_rendered',
            'write': True
        },
        'wp-api-v1': {
            'path': None
        },
        'wp-api-v2-edit': {
            'path': 'description.raw',
            'type': 'wp_content_raw',
            'write': True
        },
    })
    data['post_excerpt'].update({
        'gen-csv': {
            'path': 'caption'
        },
        'wp-api': {
            'path': 'caption.rendered',
            'type': 'wp_content_rendered'
        },
        'wp-api-v1': {
            'path': None
        },
        'wp-api-v2-edit': {
            'path': 'caption.raw',
            'type': 'wp_content_raw',
            'write': True,
        },
    })
    data['mime_type'].update({
        'wp-api-v1': {
            'path': 'attachment_meta.sizes.thumbnail.mime-type',
            'write': False
        },
    })
    data['menu_order'].update({
        'wp-api-v2': {
            'path': None,
        }
    })
    data = SeqUtils.combine_ordered_dicts(data, {
        # '_caption': {
        #     'path': None,
        #     'wp-api-v1': {
        #         'path': 'caption',
        #         'type': object
        #     }
        # },
        'source_url': {
            'write': False,
            'type': 'uri',
            'wp-api-v1': {
                'path':'source'
            },
            'gen-csv': {
                'write': True
            }
        },
        'alt_text': {
            'wp-api': {
                'read': False,
            },
            'wp-api-v1': {
                'path': None
            }
        },
        'image_meta': {
            'write': False,
            'wp-api': {
                'path': 'media_details'
            },
            'wp-api-v1': {
                'path': 'attachment_meta.image_meta',
                'write': False,
            },
        },
        'width': {
            'write': False,
            'wp-api':{
                'path': 'media_details.width',
            },
            'wp-api-v1':{
                'path': 'attachment_meta.width',
            },
            'report': True,
        },
        'height': {
            'write': False,
            'wp-api':{
                'path': 'media_details.height',
                'write': False,
            },
            'wp-api-v1':{
                'path': 'attachment_meta.height',
            },
            'report': True,
        },
        'file_path': {
            'wp-api': {
                'path': 'media_details.file',
                # 'write': False,
            },
            'wp-api-v1': {
                'path': 'attachment_meta.file',
            },
            'gen-csv': {
                'write': False,
            },
            'report': True,
            # TODO: should this be static? run slow tests.
            # 'static': True,
        },
        'file_name': {
            'path': None,
            'wp-api': {
                'path': 'source_url',
                'type': 'file_basename',
                'write': False,
            },
            'gen-csv': {
                'path': 'file_name',
                'type': 'file_basename'
            }
        },
        'attached_post_id': {
            'wp-api': {
                'path': 'post',
                'write': False,
            }
        }
    })

class ColDataUser(ColDataWpEntity):
    pass

# class ColDataSpecialMixin(object):
#     data = {
#         'start_time': {
#             'path': None
#             'gen-csv': {
#                 'path': 'start_time',
#                 'type': 'iso8601_gdrive'
#             },
#             'gen-api': {
#                 ''
#             }
#         },
#
#     }
#
# class ColDataSpecialGroup(ColDataAbstract):
#     pass
#
# class ColDataSpecialRule(ColDataAbstract):
#     data = {
#
#     }
