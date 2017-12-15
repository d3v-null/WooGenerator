 # -*- coding: utf-8 -
"""
Utility for keeping track of column metadata for translating between databases.
"""

from __future__ import absolute_import

import functools
import itertools
import re
from collections import OrderedDict
from copy import copy, deepcopy
from pprint import pformat, pprint

import jsonpath_ng
from jsonpath_ng import jsonpath

from .utils import (FileUtils, JSONPathUtils, MimeUtils, PHPUtils, Registrar,
                    SanitationUtils, SeqUtils, TimeUtils)

# TODO: Replace dicts with `OrderedDict`s
"""
Get rid of stuff like slave_override, since it should be able to work both ways.
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

# DEPRECATE_OLDSTYLE = False
DEPRECATE_OLDSTYLE = True

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
            new_keys = ['attribute:' + attr]
            if attr in vattributes.keys():
                new_keys.extend([
                    'attribute_default:' + attr,
                    'attribute_data:' + attr
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
    re_simple_path = r'^[A-Za-z_]+$'

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
                'type': 'string',
                'structure': ('singular-object', ),
                'report' : False,
            }.get(property_)

    @classmethod
    def get_handle_property(cls, handle, property_, target=None):
        """
        Return the value of a handle's property in the context of target. Cache for performace.
        """
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
    def get_property_exclusions(cls, property_, target=None):
        """
        Return a list of handles whose value of `property_` in `target` is not True-ish.
        """
        exclusions = []
        for handle, value in cls.get_handles_property(property_).items():
            if not value:
                exclusions.append(value)
        return exclusions

    @classmethod
    def get_target_path_translation(cls, target):
        """
        Return a mapping of core paths to paths in `target` structure.
        """
        if target == None:
            return
        return cls.get_handles_property_defaults('path', target)

    @classmethod
    def get_core_path_translation(cls, target):
        """
        Return the indenty translation for core paths in target.
        This does not change paths but excludes paths that do not exist in target.
        """
        exclusions = cls.get_property_exclusions('path', target)
        path_translation = OrderedDict([
            (handle, handle) \
            for handle in cls.data.keys() \
            if handle not in exclusions
        ])
        return path_translation

    # @classmethod
    # def path_exists(cls, data, path):
    #     """ Deprecated, use get_from_path in try/catch block. """
    #     if not path:
    #         return
    #     if re.match(cls.re_simple_path, path):
    #         return path in data
    #     getter = jsonpath_ng.parse(path)
    #     return getter.find(data)

    @classmethod
    def get_from_path(cls, data, path):
        """
        Tries to get the path from data, throws exceptions
        """
        # TODO: get defaults necessary here?
        if not path:
            return
        if data is None:
            return
        if re.match(cls.re_simple_path, path):
            return data[path]
        if ' ' in path:
            path = '"%s"' % path
        getter = jsonpath_ng.parse(path)
        results = getter.find(data)
        return results[0].value

    @classmethod
    def update_in_path(cls, data, path, value):
        if not path:
            return data
        if data is None:
            return data
        if re.match(cls.re_simple_path, path):
            data[path] = value
            return data
        if ' ' in path:
            path = '"%s"' % path
        updater = jsonpath_ng.parse(path)
        return JSONPathUtils.blank_update(updater, data, value)

    @classmethod
    def morph_data(cls, data, morph_functions, path_translation):
        """
        Translate the data using functions preserving paths.
        """
        for handle in cls.data.keys():
            if handle in morph_functions and handle in path_translation:
                target_path = path_translation.get(handle)
                try:
                    target_value = deepcopy(cls.get_from_path(
                        data, target_path
                    ))
                except (IndexError, KeyError):
                    continue
                try:
                    target_value = morph_functions.get(handle)(target_value)
                except (TypeError, ):
                    continue
                data = cls.update_in_path(
                    data, target_path, target_value
                )
        return data

    @classmethod
    def translate_paths_from(cls, data, target):
        """
        Translate the path structure of data from `target` to core.
        """
        translation = cls.get_target_path_translation(target)
        if translation:
            response = OrderedDict()
            for handle, target_path in translation.items():
                if target_path is None:
                    continue
                try:
                    target_value = cls.get_from_path(data, target_path)
                    response = cls.update_in_path(
                        response,
                        handle,
                        deepcopy(target_value)
                    )
                except (IndexError, KeyError):
                    pass
            return response
        return deepcopy(data)

    @classmethod
    def translate_paths_to(cls, data, target):
        """
        Translate the path structure of data from core to `target`.
        """
        translation = cls.get_target_path_translation(target)
        if translation:
            response = OrderedDict()
            for handle, target_path in translation.items():
                if target_path is None:
                    continue
                try:
                    target_value = cls.get_from_path(data, handle)
                    response = cls.update_in_path(
                        response,
                        target_path,
                        deepcopy(target_value)
                    )
                except (IndexError, KeyError):
                    pass
            return response
        return deepcopy(data)

    @classmethod
    def deconstruct_sub_entity(cls, sub_data, target, target_structure=None, forced_mapping_handle=None):
        if target_structure is None:
            target_structure = cls.get_property_default('structure')
        path_translation = cls.get_target_path_translation(target)
        objects = []
        if target_structure[0] == 'singular-object':
            if sub_data:
                return cls.translate_data_from(
                    sub_data,
                    target
                )
        elif target_structure[0] == 'singular-value':
            target_value_handle = target_structure[1]
            target_value_path = path_translation.get(target_value_handle, target_value_handle)
            if sub_data:
                return cls.translate_data_from(
                    cls.update_in_path(
                        {},
                        target_value_path,
                        sub_data
                    ),
                    target
                )
        elif target_structure[0] == 'listed-values':
            target_value_handle = target_structure[1]
            target_value_path = path_translation.get(target_value_handle, target_value_handle)
            objects = [
                cls.translate_data_from(
                    cls.update_in_path(
                        {},
                        target_value_path,
                        sub_value
                    ),
                    target
                ) for sub_value in sub_data
            ]
        elif target_structure[0] == 'listed-objects':
            objects = [
                cls.translate_data_from(
                    sub_object,
                    target
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
                            sub_key
                        ),
                        target_value_path,
                        sub_value
                    ),
                    target
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
                        sub_key
                    ),
                    target
                ) for sub_key, sub_value in sub_data.items()
            ]
        if forced_mapping_handle:
            mapping = {}
            for object_ in objects:
                try:
                    mapping_key = cls.get_from_path(object_, forced_mapping_handle)
                except (IndexError, KeyError):
                    continue
                mapping[mapping_key] = object_
            return mapping

        return objects

    @classmethod
    def reconstruct_sub_entity(cls, sub_data, target, target_structure=None, forced_mapping_handle=None):
        """
        The inverse of deconstruct_sub_entity.
        """
        if target_structure is None:
            target_structure = cls.get_property_default('structure')
        path_translation = cls.get_target_path_translation(target)
        if target_structure[0] == 'singular-object':
             return cls.translate_data_to(
                sub_data,
                target
            )
        elif target_structure[0] == 'singular-value':
            target_value_handle = target_structure[1]
            target_value_path = path_translation.get(target_value_handle, target_value_handle)
            return cls.get_from_path(
                cls.translate_data_to(
                    sub_data,
                    target
                ),
                target_value_path
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
                        mapping_key
                    )
                    objects.append(object_)
            # TODO: finish this
            # if target_structure[0] == 'listed-values':
            #     target_value_handle = target_structure[1]
            #     target_value_path = path_translation.get(target_value_handle, target_value_handle)
            #     return [
            #         cls.get_from_path(
            #             cls.translate_data_to(
            #                 sub_object,
            #                 target
            #             ),
            #             target_value_path
            #         ) for sub_object in objects
            #     ]
            if target_structure[0] == 'listed-objects':
                return [
                    cls.translate_data_to(
                        sub_object,
                        target
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
                        target
                    ) for sub_object in objects
                ]
                return OrderedDict([
                    (
                        cls.get_from_path(translated_object, target_key_path),
                        cls.get_from_path(translated_object, target_value_path)
                    ) for translated_object in translated_objects
                ])
            return objects


    @classmethod
    def get_structure_morph_functions(cls, target, direction='from'):
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
                        forced_mapping_handle=forced_mapping_handle
                    )
                if morph_function:
                    morph_functions[handle] = morph_function
        cls.structure_morph_cache[cache_key] = morph_functions
        return morph_functions


    @classmethod
    def translate_structure_from(cls, data, target, path_translation=None):
        """
        Translate the Sub-entity structures in data between `target` and core.
        """
        morph_functions = cls.get_structure_morph_functions(target, 'from')
        return cls.morph_data(data, morph_functions, path_translation)

    @classmethod
    def translate_structure_to(cls, data, target, path_translation=None):
        """
        Translate the Sub-entity structures in data between core and `target`.
        """
        morph_functions = cls.get_structure_morph_functions(target, 'to')
        return cls.morph_data(data, morph_functions, path_translation)

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
        return {
            'xml_escaped': SanitationUtils.xml_to_unicode,
            'iso8601': functools.partial(
                TimeUtils.star_strp_datetime,
                fmt=TimeUtils.iso8601_datetime_format
            ),
            'wp_datetime': functools.partial(
                TimeUtils.star_strp_datetime,
                fmt=TimeUtils.wp_datetime_format
            ),
            'datetime': SanitationUtils.identity,
            'timestamp': TimeUtils.timestamp2datetime,
            'wp_content_rendered': SanitationUtils.normalize_wp_rendered_content,
            'wp_content_raw': SanitationUtils.normalize_wp_raw_content,
            'yesno': SanitationUtils.yesno2bool,
            'stock_status': SanitationUtils.stock_status2bool,
            'optional_int_minus_1': SanitationUtils.normalize_optional_int_minus_1,
            'optional_int_zero': SanitationUtils.normalize_optional_int_zero,
            'optional_int_none': SanitationUtils.normalize_optional_int_none,
            'php_array_associative': PHPUtils.unserialize_mapping,
            'php_array_indexed': PHPUtils.unserialize_list,
            'file_basename': FileUtils.get_path_basename,
            'mime_type': MimeUtils.validate_mime_type,
            'currency': SanitationUtils.similar_currency_comparison,
        }.get(type_, SanitationUtils.coerce_unicode)

    @classmethod
    def get_denormalizer(cls, type_):
        """
        Return the function to translate data between the core representation
        and `type_`
        """
        return {
            'xml_escaped': SanitationUtils.coerce_xml,
            'iso8601': functools.partial(
                TimeUtils.star_strf_datetime,
                fmt=TimeUtils.iso8601_datetime_format
            ),
            'wp_datetime': functools.partial(
                TimeUtils.star_strf_datetime,
                fmt=TimeUtils.wp_datetime_format
            ),
            'yesno': SanitationUtils.bool2yesno,
            'stock_status': SanitationUtils.bool2stock_status,
            'php_array_associative': PHPUtils.serialize_mapping,
            'php_array_indexed': PHPUtils.serialize_list,
            'timestamp': TimeUtils.datetime2timestamp,
            'mime_type': MimeUtils.validate_mime_type,
            'currency': SanitationUtils.similar_currency_comparison,
        }.get(type_, SanitationUtils.identity)

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
            path_translation
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
            path_translation
        )

    @classmethod
    def translate_data_from(cls, data, target):
        """
        Perform a full translation of paths and types between target and core
        """
        if not data:
            return data
        if not target:
            return data
        data = deepcopy(data)
        # split target_path_translation on which handles have sub_data
        target_path_translation = cls.get_target_path_translation(target)
        core_path_translation = cls.get_core_path_translation(target)
        sub_datum = cls.get_handles_property('sub_data')
        sub_data_handles = set()
        for handle, sub_data in sub_datum.items():
            if sub_data:
                sub_data_handles.add(handle)
        # target paths which have sub_data
        path_translation_pre = OrderedDict()
        # core paths which don't have sub_data
        path_translation_post = OrderedDict()
        for handle in cls.data.keys():
            if handle in sub_data_handles:
                path_translation_pre[handle] = target_path_translation[handle]
            else:
                path_translation_post[handle] = core_path_translation[handle]

        # translate handles in target format which have sub_data
        data = cls.translate_types_from(
            data, target, path_translation_pre
        )

        # translate structure
        data = cls.translate_structure_from(
            data, target, target_path_translation
        )
        data = cls.translate_paths_from(
            data, target
        )
        data = cls.translate_types_from(
            data, target, path_translation_post
        )
        return data

    @classmethod
    def translate_data_to(cls, data, target):
        """
        Perform a full translation of paths and types between core and target
        """
        if not data:
            return data
        if not target:
            return data

        # split target_path_translation on which handles have sub_data
        target_path_translation = cls.get_target_path_translation(target)
        core_path_translation = cls.get_core_path_translation(target)
        sub_datum = cls.get_handles_property('sub_data')
        sub_data_handles = set()
        for handle, sub_data in sub_datum.items():
            if sub_data:
                sub_data_handles.add(handle)
        # core paths which do not have sub data
        path_translation_pre = OrderedDict()
        # target paths which have sub data
        path_translation_post = OrderedDict()
        for handle in cls.data.keys():
            if handle not in sub_data_handles:
                path_translation_pre[handle] = core_path_translation[handle]
            else:
                path_translation_post[handle] = target_path_translation[handle]

        # translate types of non-subdata handles in core format
        data = cls.translate_types_to(
            data, target, path_translation_pre
        )
        # Translate all paths
        data = cls.translate_paths_to(
            data, target
        )
        # translate subdata structure
        data = cls.translate_structure_to(
            data, target, target_path_translation
        )
        # translate types of subdata handles in target format
        data = cls.translate_types_to(
            data, target, path_translation_post
        )

        return data

    @classmethod
    def get_sync_handles(cls, master_target=None, slave_target=None):
        master_paths = cls.get_handles_property_defaults('path', master_target)
        slave_paths =  cls.get_handles_property_defaults('path', slave_target)
        master_writes = cls.get_handles_property_defaults('write', master_target)
        slave_writes = cls.get_handles_property_defaults('write', slave_target)
        sync_handles = OrderedDict()
        for handle in cls.data.keys():
            master_path = master_paths.get(handle)
            master_write = master_writes.get(handle)
            slave_path = slave_paths.get(handle)
            slave_write = slave_writes.get(handle)
            if not (master_path and slave_path):
                continue
            if not (master_write or slave_write):
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
    data = deepcopy(ColDataSubEntity.data)
    data = SeqUtils.combine_ordered_dicts(data, {
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
                'type': 'iso8601',
            },
            'wc-wp-api': {
                'path': 'date_created_gmt',
                'type': 'iso8601',
            },
            'wc-wp-api-v1': {
                'path': None,
            },
            'wp-sql':{
                'type': 'wp_datetime',
                'path': 'post_date_gmt'
            },
            'gen-csv': {
                'path': 'created_gmt',
                'read': False,
            },
        },
        'modified_gmt': {
            'type': 'datetime',
            'write': False,
            'wp-api': {
                'path': 'modified_gmt',
                'type': 'iso8601'
            },
            'wc-wp-api': {
                'path': 'date_modified_gmt',
                'type': 'iso8601',
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
                'type': 'iso8601'
            },
            'report': True,
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
    data = SeqUtils.combine_ordered_dicts(data, {
        'id': {
            'write': False,
            'unique': True,
            'type': 'optional_int_none',
            'api': {
                'path': 'id'
            },
            'wp-api-v1': {
                'path': 'ID'
            },
            'wp-sql': {
                'path': 'ID',
            },
            'gen-api': {
                'path': 'ID'
            },
            'report': True
        },
        'title': {
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
        'file_name': {
            'path': None,
            'wc-wp-api': {
                'path': 'src',
                'type': 'file_basename',
                'write': False
            },
            'gen-csv': {
                'path': 'file_name',
                'read': False
            }
        }
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

class ColDataTermMixin(object):
    data = {
        'term_id': {
            'write': False,
            'unique': True,
            'type': 'optional_int_none',
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
                'write': True,
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
                'path': 'name',
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
                'path': None
            },
            'wp-sql': {
                'path': 'slug'
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
                'path': 'taxonomy'
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
                'path': 'count'
            }
        },
        'description': {
            'path': None,
            'wp-api-v1': {
                'path': 'description',
                'type': 'wp_content_rendered',
            },
            'wp-sql': {
                'path': 'description',
                'type': 'wp_content_rendered',
            },
            'gen-csv': {
                'path': 'descsum'
            },
        },
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
                'path': 'parent'
            }
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

class ColDataSubAttribute(ColDataSubTerm):
    data = deepcopy(ColDataSubTerm.data)
    data['slug'].update({
        'wc-api': {
            'path': None
        }
    })
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
        'options': {
            'path': None,
            'wc-api': {
                'path': 'options'
            }
        },
    })

class ColDataSubDefaultAttribute(ColDataSubTerm):
    data = deepcopy(ColDataSubTerm.data)
    data['slug'].update({
        'wc-api': {
            'path': None
        }
    })
    data = SeqUtils.combine_ordered_dicts(data, {
        'option': {
            'path': None,
            'wc-api': {
                'path': 'option'
            }
        }
    })

class ColDataSubMeta(ColDataSubEntity):
    data = deepcopy(ColDataSubEntity.data)
    data = SeqUtils.combine_ordered_dicts(data, {
        'meta_id': {
            'path': None,
            'wc-api': {
                'path': 'id'
            },
        },
        'meta_key': {
            'path': None,
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
            'path': None,
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
    data['term_parent_id'].update({
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
    data = SeqUtils.combine_ordered_dicts(data, {
        'menu_order': {
            'wc-api': {
                'path': 'menu_order'
            },
            'wp-sql': {
                'path': 'term_meta.order'
            },
            'gen-csv': {
                'path': 'rowcount',
                'write': False,
            }
        }
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
            }
        }
    })

class ColDataWpEntity(ColDataAbstract, CreatedModifiedGmtMixin):
    """
    Metadata for abstract WP objects based off wp post object
    - wp-api-v2: https://developer.wordpress.org/rest-api/reference/posts/
    - wp-api-v2: http://v2.wp-api.org/reference/posts/
    - wp-api-v1: http://wp-api.org/index-deprecated.html#entities_post
    """
    data = deepcopy(ColDataAbstract.data)
    data = SeqUtils.combine_ordered_dicts(data, CreatedModifiedGmtMixin.data)
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
            }
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
                'type': 'iso8601',
            },
            'wc-wp-api': {
                'path': 'date_created',
                'type': 'iso8601',
            },
            'wc-legacy-api': {
                'path': 'created_at',
                'type': 'iso8601',
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
                'type': 'iso8601',
            },
            'wc-legacy-api': {
                'path': 'modified_at',
                'type': 'iso8601',
            },
            'wp-api': {
                'path': 'modified',
                'type': 'iso8601'
            },
            'wp-sql': {
                'path': 'post_modified',
                'type': 'wp_datetime'
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
        'menu_order': {
            'type': int,
            'path': None,
            'wp-api': {
                'path': None
            },
            'wc-api': {
                'path': 'menu_order'
            },
            # 'wp-api-v1': {
            #     'path': 'menu_order'
            # },
            'wp-sql': {
                'path': 'menu_order'
            },
            'gen-csv': {
                'path': 'rowcount',
                'read': False,
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
            'force_mapping': 'meta_key',
            'wp-api': {
                'path': 'meta',
                'structure': ('listed-objects', )
            },
            'wp-api-v1': {
                'path': 'post_meta',
                'structure': ('mapping-value', ('meta_key', 'meta_value'))
            },
            'wc-api': {
                'path': 'meta_data',
                'structure': ('listed-objects', )
            },
            'wc-legacy-api': {
                'path': 'custom_meta',
                'structure': ('listed-objects', )
            },
            'wp-sql':{
                'path': None,
            },
            'gen-csv': {
                'structure': ('mapping-value', ('meta_key', 'meta_value')),
                'read': False,
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
            }
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
            'wp-sql': {
                'path': None,
            },
            'options': [
                'simple',
                'grouped',
                'external',
                'variable',
                'composite',
                'bundle'
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
            }
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
            'wp-sql': {
                'path': 'meta._price',
            },
            'gen-csv': {
                'read': False,
            },
            'xero-api': {
                'path': None
            }
        },
        'regular_price': {
            'type': 'currency',
            'wp-sql': {
                'path': 'meta._regular_price'
            },
            'gen-csv': {
                'read': False,
            },
            'xero-api': {
                'path': None
            }
        },
        'sale_price': {
            'type': 'currency',
            'wp-sql': {
                'path': 'meta._sale_price'
            },
            'gen-csv': {
                'read': False,
            },
            'xero-api': {
                'path': None
            }
        },
        'sale_price_dates_from': {
            'type': 'datetime',
            'wc-api': {
                'path': 'date_on_sale_from',
                'type': 'iso8601',
            },
            'wc-legacy-api': {
                'read': False,
                'path': 'sale_price_dates_from',
                'type': 'wp_date_local'
            },
            'wp-sql': {
                'path': 'meta._sale_price_dates_from',
                'type': 'timestamp'
            },
            'gen-csv': {
                'read': False,
            },
            'xero-api': {
                'path': None
            }
        },
        'sale_price_dates_from_gmt': {
            'type': 'datetime',
            'path': None,
            'wc-api': {
                'path': 'date_on_sale_from_gmt',
                'type': 'iso8601'
            },
            'wc-wp-api-v1': {
                'path': None
            }
        },
        'sale_price_dates_to': {
            'type': 'datetime',
            'wc-api': {
                'path': 'date_on_sale_to',
                'type': 'iso8601',
            },
            'wc-legacy-api': {
                'read': False,
                'path': 'sale_price_dates_to',
                'type': 'wp_date_local'
            },
            'wp-sql': {
                'path': 'meta._sale_price_dates_to',
                'type': 'timestamp'
            },
            'gen-csv': {
                'read': False,
            },
            'xero-api': {
                'path': None
            }
        },
        'sale_price_dates_to_gmt': {
            'type': 'datetime',
            'path': None,
            'wc-api': {
                'path': 'date_on_sale_to_gmt',
                'type': 'iso8601',
            },
            'wc-wp-api-v1': {
                'path': None
            }
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
            'type': 'optional_int',
            'xero-api': {
                'path': 'QuantityOnHand',
                'type': 'optional_float',
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
            }
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
            }
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
            }
        },
        'variations': {
            'path': None,
            'sub_data': ColDataSubVariation,
            'wc-api': {
                'path': 'variations',
                'structure': ('listed-values', 'id')
            }
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
    data = deepcopy(ColDataProduct.data)
    data['title'].update({
        'wc-api': {
            'path': None
        }
    })
    data['parent_id'].update({
        'write': True,
        'wc-api': {
            'path': None
        }
    })
    data['variations'].update({
        'wc-api': {
            'path': None
        }
    })
    data['product_category_list'].update({
        'wc-csv': {
            'path': None
        }
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
            })
        ])
    )

class ColDataMeridianEntityMixin(object):
    data = OrderedDict(ColDataProduct.data.items() + {
        'wootan_danger': {
            'type': 'danger',
            'wc-api': {
                'path': 'meta_data.wootan_danger.meta_value',
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
                'path': 'meta_data.commissionable_value.meta_value'
            },
            'wp-sql': {
                'path': 'meta.commissionable_value'
            },
            'gen-csv': {
                'path': 'CVC'
            },
            'woo-csv': {
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
            }
        },
        'dynamic_product_rulesets': {
            'path': None,
            'gen-csv': {
                'path': 'DYNPROD',
                'default': ''
            }
        },
        'dynamic_category_rulesets': {
            'path': None,
            'gen-csv': {
                'path': 'DYNCAT',
                'default': ''
            }
        },
        'product_attributes': {
            'path': None,
            'gen-csv': {
                'path': 'PA',
                'type': 'json',
                'structure': ('mapping-value', ('title', 'value')),
                'default': ''
            },
            'default': []
        },
        'variation_attributes': {
            'path': None,
            'gen-csv': {
                'path': 'VA',
                'type': 'json',
                'structure': ('mapping-value', ('title', 'value')),
                'default': ''
            },
            'default': []
        },
        'extra_categories': {
            'path': None,
            'gen-csv': {
                'path': 'E',
                'default': ''
            },
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
        }
    }.items() + [
        (
            'lc_%s_%s' % (tier, field),
            {
                'read': import_,
                'variation': True,
                'pricing': True,
                'type': type_,
                'wp-sql': {
                    'path': 'meta.lc_%s_%s.meta_value' % (tier, field),
                },
                'wc-wp-api': {
                    'path': 'meta_data.lc_%s_%s.meta_value' % (tier, field),
                },
                'wc-legacy-api': {
                    'path': 'meta.lc_%s_%s.meta_value' % (tier, field),
                },
                'gen-csv': {
                    'path': ''.join([tier.upper(), field_slug.upper()]),
                    'write': False
                },
                'wc-csv': {
                    'path': 'meta:lc_%s_%s' % (tier, field),
                },
                'xero-api': {
                    'path': None
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
        'source_url': {
            'write': False,
            'type': 'uri',
            'wp-api-v1': {
                'path':'source'
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
        }
    })

class ColDataUser(ColDataWpEntity):
    pass
#
# class ColDataBase(object):
#     """
#     Deprecated style of storing col data
#     """
#     data = OrderedDict()
#     deprecate_oldstyle = DEPRECATE_OLDSTYLE
#
#     def __init__(self, data):
#         super(ColDataBase, self).__init__()
#         assert issubclass(
#             type(data), dict), "Data should be a dictionary subclass"
#         self.data = data
#
#     @classmethod
#     def get_import_cols_native(cls):
#         if cls.deprecate_oldstyle:
#             raise DeprecationWarning("old style coldata class is deprecated")
#         imports = []
#         for col, data in cls.data.items():
#             if data.get('import', False):
#                 imports.append(col)
#         return imports
#
#     @classmethod
#     def get_defaults(cls):
#         if cls.deprecate_oldstyle:
#             raise DeprecationWarning("old style coldata class is deprecated")
#         defaults = {}
#         for col, data in cls.data.items():
#             # Registrar.register_message('col is %s' % col)
#             if 'default' in data:
#                 # Registrar.register_message('has default')
#                 defaults[col] = data.get('default')
#             else:
#                 pass
#                 # Registrar.register_message('does not have default')
#         return defaults
#
#     @classmethod
#     def get_export_cols(cls, schema=None):
#         if cls.deprecate_oldstyle:
#             raise DeprecationWarning("old style coldata class is deprecated")
#         if not schema:
#             return None
#         export_cols = OrderedDict()
#         for col, data in cls.data.items():
#             if data.get(schema, ''):
#                 export_cols[col] = data
#         return export_cols
#
#     @classmethod
#     def get_col_data_native('basic')(cls):
#         return cls.get_export_cols('basic')
#
#     @classmethod
#     def get_delta_cols_native(cls):
#         if cls.deprecate_oldstyle:
#             raise DeprecationWarning("old style coldata class is deprecated")
#         cols = OrderedDict()
#         for col, data in cls.data.items():
#             if data.get('delta'):
#                 cols[col] = cls.delta_col(col)
#         return cols
#
#     @classmethod
#     def get_col_names(cls, cols):
#         if cls.deprecate_oldstyle:
#             raise DeprecationWarning("old style coldata class is deprecated")
#         col_names = OrderedDict()
#         for col, data in cols.items():
#             label = data.get('label', '')
#             col_names[col] = label if label else col
#         return col_names
#
#     @classmethod
#     def name_cols(cls, cols):
#         if cls.deprecate_oldstyle:
#             raise DeprecationWarning("old style coldata class is deprecated")
#         return OrderedDict(
#             [(col, {}) for col in cols]
#         )
#
#     @classmethod
#     def get_report_cols_native(cls):
#         return cls.get_export_cols('report')
#
#     @classmethod
#     def get_wpapi_cols(cls, api='wc-wp-api'):
#         return cls.get_export_cols(api)
#
#     @classmethod
#     def get_wpapi_variable_cols(cls):
#         if cls.deprecate_oldstyle:
#             raise DeprecationWarning("old style coldata class is deprecated")
#         cols = OrderedDict()
#         for col, data in cls.get_wpapi_cols().items():
#             if 'sync' in data:
#                 if data.get('sync') == 'not_variable':
#                     continue
#             cols[col] = data
#         return cols
#
#     @classmethod
#     def get_wpapi_core_cols(cls, api='wc-wp-api'):
#         if cls.deprecate_oldstyle:
#             raise DeprecationWarning("old style coldata class is deprecated")
#         export_cols = cls.get_export_cols(api)
#         api_cols = OrderedDict()
#         for col, data in export_cols.items():
#             api_data = data.get(api, {})
#             if hasattr(api_data, '__getitem__') \
#                     and not api_data.get('meta'):
#                 api_cols[col] = data
#
#         return api_cols
#
#     @classmethod
#     def get_wpapi_meta_cols(cls, api='wc-wp-api'):
#         if cls.deprecate_oldstyle:
#             raise DeprecationWarning("old style coldata class is deprecated")
#         # export_cols = cls.get_export_cols(api)
#         api_cols = OrderedDict()
#         for col, data in cls.data.items():
#             api_data = data.get(api, {})
#             if hasattr(api_data, '__getitem__') \
#                     and api_data.get('meta') is not None:
#                 if api_data.get('meta'):
#                     api_cols[col] = data
#             else:
#                 backup_api_data = data.get('wp', {})
#                 if hasattr(backup_api_data, '__getitem__') \
#                         and backup_api_data.get('meta') is not None:
#                     if backup_api_data.get('meta'):
#                         api_cols[col] = data
#         return api_cols
#
#     @classmethod
#     def get_wpapi_category_cols(cls, api='wc-wp-api'):
#         if cls.deprecate_oldstyle:
#             raise DeprecationWarning("old style coldata class is deprecated")
#         export_cols = cls.get_export_cols(api)
#         api_category_cols = OrderedDict()
#         for col, data in export_cols.items():
#             if data.get('category', ''):
#                 api_category_cols[col] = data
#         return api_category_cols
#
#     @classmethod
#     def get_wpapi_import_cols(cls, api='wc-wp-api'):
#         if cls.deprecate_oldstyle:
#             raise DeprecationWarning("old style coldata class is deprecated")
#         export_cols = cls.get_export_cols('import')
#         api_import_cols = OrderedDict()
#         for col, data in export_cols.items():
#             key = col
#             if api in data and 'key' in data[api]:
#                 key = data[api]['key']
#             api_import_cols[key] = data
#         return api_import_cols
#
#     @classmethod
#     def get_sync_handles(cls):
#         return cls.get_export_cols('sync')
#
#     @classmethod
#     def delta_col(cls, col):
#         return 'Delta ' + col
#
#     @classmethod
#     def get_category_cols(cls):
#         return cls.get_export_cols('category')
#
# # class ColDataProd(ColDataBase):
# #     data = OrderedDict([
# #         ('codesum', {
# #             'label': 'SKU',
# #             'product': True,
# #             'report': True
# #         }),
# #         ('itemsum', {
# #             'label': 'Name',
# #             'product': True,
# #             'report': True
# #         }),
# #         # ('descsum', {
# #         #     'label': 'Description',
# #         #     'product': True,
# #         # }),
# #         # ('WNR', {
# #         #     'product': True,
# #         #     'report': True,
# #         #     'pricing': True,
# #         # }),
# #         # ('RNR', {
# #         #     'product': True,
# #         #     'report': True,
# #         #     'pricing': True,
# #         # }),
# #         # ('DNR', {
# #         #     'product': True,
# #         #     'report': True,
# #         #     'pricing': True,
# #         # }),
# #         # ('weight', {
# #         #     'import': True,
# #         #     'product': True,
# #         #     'variation': True,
# #         #     'shipping': True,
# #         #     'wp': {
# #         #         'key': '_weight',
# #         #         'meta': True
# #         #     },
# #         #     'wc-wp-api': True,
# #         #     'sync': True,
# #         #     'report': True
# #         # }),
# #         # ('length', {
# #         #     'import': True,
# #         #     'product': True,
# #         #     'variation': True,
# #         #     'shipping': True,
# #         #     'wp': {
# #         #         'key': '_length',
# #         #         'meta': True
# #         #     },
# #         #     'sync': True,
# #         #     'report': True
# #         # }),
# #         # ('width', {
# #         #     'import': True,
# #         #     'product': True,
# #         #     'variation': True,
# #         #     'shipping': True,
# #         #     'wp': {
# #         #         'key': '_width',
# #         #         'meta': True
# #         #     },
# #         #     'sync': True,
# #         #     'report': True
# #         # }),
# #         # ('height', {
# #         #     'import': True,
# #         #     'product': True,
# #         #     'variation': True,
# #         #     'shipping': True,
# #         #     'wp': {
# #         #         'key': '_height',
# #         #         'meta': True
# #         #     },
# #         #     'sync': True,
# #         #     'report': True
# #         # }),
# #     ])
# #
# #     @classmethod
# #     def get_product_cols(cls):
# #         return cls.get_export_cols('product')
# #
# #     @classmethod
# #     def get_pricing_cols(cls):
# #         return cls.get_export_cols('pricing')
# #
# #     @classmethod
# #     def get_shipping_cols(cls):
# #         return cls.get_export_cols('shipping')
# #
# #     @classmethod
# #     def get_inventory_cols(cls):
# #         return cls.get_export_cols('inventory')
# #
# #
# # class ColDataCat(ColDataBase):
# #     data = OrderedDict([
# #         ('title', {
# #             'label': 'Category Name',
# #             'category': True
# #         }),
# #         ('taxosum', {
# #             'label': 'Full Category Name',
# #             'category': True
# #         }),
# #     ])
# #
# #
# # class ColDataMyo(ColDataProd):
# #
# #     data = OrderedDict(ColDataProd.data.items() + [
# #         ('codesum', {
# #             'label': 'Item Number',
# #             'product': True,
# #         }),
# #         ('itemsum', {
# #             'label': 'Item Name',
# #             'product': True,
# #             'report': True,
# #         }),
# #         ('WNR', {
# #             'label': 'Selling Price',
# #             'import': True,
# #             'product': True,
# #             'pricing': True,
# #             'type': 'currency',
# #         }),
# #         ('RNR', {
# #             'label': 'Price Level B, Qty Break 1',
# #             'import': True,
# #             'product': True,
# #             'pricing': True,
# #             'type': 'currency',
# #         }),
# #         ('DNR', {
# #             'label': 'Price Level C, Qty Break 1',
# #             'import': True,
# #             'product': True,
# #             'pricing': True,
# #             'type': 'currency',
# #         }),
# #         ('CVC', {
# #             'label': 'Custom Field 1',
# #             'product': True,
# #             'import': True,
# #             'default': 0
# #         }),
# #         ('descsum', {
# #             'label': 'Description',
# #             'product': True,
# #             'report': True,
# #         }),
# #         ('Sell', {
# #             'default': 'S',
# #             'product': True,
# #         }),
# #         ('Tax Code When Sold', {
# #             'default': 'GST',
# #             'product': True,
# #         }),
# #         ('Sell Price Inclusive', {
# #             'default': 'X',
# #             'product': True,
# #         }),
# #         ('Income Acct', {
# #             'default': '41000',
# #             'product': True,
# #         }),
# #         ('Inactive Item', {
# #             'default': 'N',
# #             'product': True,
# #         }),
# #         ('use_desc', {
# #             'label': 'Use Desc. On Sale',
# #             'default': 'X',
# #             'product': True
# #         })
# #     ])
# #
# #     def __init__(self, data=None):
# #         if not data:
# #             data = self.data
# #         super(ColDataMyo, self).__init__(data)
# #
# # class ColDataXero(ColDataProd):
# #     data = OrderedDict(ColDataProd.data.items() + [
# #         ('item_id', {
# #             'xero-api': {
# #                 'key': 'ItemID'
# #             },
# #             # 'report': True,
# #             'product': True,
# #             'basic': True,
# #             'label': 'Xero ItemID',
# #             # 'sync': 'slave_override',
# #             'sync': False,
# #         }),
# #         ('codesum', {
# #             'xero-api': {
# #                 'key': 'Code'
# #             },
# #             # 'report': True,
# #             'basic': True,
# #             'label': 'SKU',
# #             'product': True,
# #         }),
# #         ('Xero Description', {
# #             'xero-api': {
# #                 'key': 'Description'
# #             },
# #             'product': True,
# #             'default': '',
# #         }),
# #         ('itemsum', {
# #             'xero-api': {
# #                 'key': 'Name'
# #             },
# #             'basic': True,
# #             'label': 'Product Name',
# #             'report': True,
# #             'product': True,
# #             'sync': True,
# #         }),
# #         ('is_sold', {
# #             'xero-api': {
# #                 'key': 'isSold'
# #             }
# #         }),
# #         ('is_purchased', {
# #             'xero-api': {
# #                 'key': 'isPurchased'
# #             }
# #         }),
# #         ('sales_details', {
# #             'xero-api': {
# #                 'key': 'SalesDetails'
# #             },
# #         }),
# #         ('WNR', {
# #             'product': True,
# #             'report': True,
# #             'pricing': True,
# #             'import': True,
# #             'type': 'currency',
# #             'xero-api': {
# #                 'key': 'UnitPrice',
# #                 'parent': 'SalesDetails'
# #             },
# #             'sync': 'master_override',
# #             'delta': True,
# #
# #         }),
# #         ('stock', {
# #             'import': True,
# #             'product': True,
# #             'variation': True,
# #             'inventory': True,
# #             'type': 'float',
# #             'sync': True,
# #             'xero-api': {
# #                 'key': 'QuantityOnHand'
# #             }
# #         }),
# #         ('stock_status', {
# #             'import': True,
# #             # 'product': True,
# #             'variation': True,
# #             'inventory': True,
# #             'sync': True,
# #             'xero-api': None,
# #             # 'delta': True,
# #         }),
# #         ('manage_stock', {
# #             'product': True,
# #             'variation': True,
# #             'inventory': True,
# #             'xero-api': {
# #                 'key': 'IsTrackedAsInventory'
# #             },
# #             'sync': True,
# #             'type': 'bool'
# #         }),
# #     ])
# #
# #     @classmethod
# #     def unit_price_sales_field(cls, data_target):
# #         for key, coldata in cls.data.items():
# #             keydata = ((coldata.get(data_target) or {}).get('key') or {})
# #             if keydata == 'UnitPrice':
# #                 return key
# #
# #     def __init__(self, data=None):
# #         if not data:
# #             data = self.data
# #         super(ColDataXero, self).__init__(data)
# #
# #     @classmethod
# #     def get_xero_api_cols(cls):
# #         return cls.get_export_cols('xero-api')
# #
# # class ColDataWoo(ColDataProd):
# #
# #     data = OrderedDict(ColDataProd.data.items() + [
# #         ('ID', {
# #             'category': True,
# #             'product': True,
# #             'wp': {
# #                 'key': 'ID',
# #                 'meta': False
# #             },
# #             'wc-wp-api': {
# #                 'key': 'id',
# #                 'meta': False,
# #                 'read_only': True
# #             },
# #             'wc-legacy-api': {
# #                 'key': 'id',
# #                 'meta': False,
# #                 'read_only': True
# #             },
# #             'report': True,
# #             'sync': 'slave_override',
# #         }),
# #         ('parent_SKU', {
# #             'variation': True,
# #         }),
# #         ('parent_id', {
# #             'category': True,
# #             'wc-wp-api': {
# #                 'key': 'parent'
# #             },
# #             'wc-legacy-api': {
# #                 'key': 'parent'
# #             },
# #             'gen-csv': {
# #                 'read': False,
# #             }
# #         }),
# #         ('codesum', {
# #             'label': 'SKU',
# #             'tag': 'SKU',
# #             'product': True,
# #             'variation': True,
# #             'category': False,
# #             'report': True,
# #             'sync': True,
# #             'wp': {
# #                 'key': '_sku',
# #                 'meta': True
# #             },
# #             'wc-wp-api': {
# #                 'key': 'sku'
# #             },
# #             'wc-legacy-api': {
# #                 'key': 'sku'
# #             },
# #             'xero-api': {
# #                 'key': 'Code'
# #             },
# #         }),
# #         ('slug', {
# #             'category': True,
# #             'product': False,
# #             'wc-wp-api': {
# #                 'key': 'slug',
# #                 'meta': False,
# #             },
# #             'wc-legacy-api': {
# #                 'key': 'slug',
# #                 'meta': False,
# #             },
# #             'sync': 'slave_override'
# #         }),
# #         ('display', {
# #             'category': True,
# #             'wc-wp-api': True,
# #         }),
# #         ('itemsum', {
# #             'tag': 'Title',
# #             'label': 'post_title',
# #             'product': True,
# #             'variation': True,
# #             'report': True,
# #             'sync': 'not_variable',
# #             'static': True,
# #             'wp': {
# #                 'key': 'post_title',
# #                 'meta': False
# #             },
# #             'wc-wp-api': {
# #                 'key': 'title',
# #                 'meta': False
# #             },
# #             'wc-legacy-api': {
# #                 'key': 'title',
# #                 'meta': False
# #             },
# #             'xero-api': {
# #                 'key': 'Name'
# #             },
# #         }),
# #         ('title', {
# #             'category': True,
# #             'wc-wp-api': {
# #                 'key': 'name',
# #                 'meta': False
# #             },
# #             'wc-legacy-api': {
# #                 'key': 'name',
# #                 'meta': False
# #             },
# #             # 'sync':True
# #         }),
# #         ('title_1', {
# #             'label': 'meta:title_1',
# #             'product': True,
# #             'wp': {
# #                 'key': 'title_1',
# #                 'meta': True
# #             }
# #         }),
# #         ('title_2', {
# #             'label': 'meta:title_2',
# #             'product': True,
# #             'wp': {
# #                 'key': 'title_2',
# #                 'meta': True
# #             }
# #         }),
# #         ('taxosum', {
# #             'label': 'category_title',
# #             'category': True
# #         }),
# #         ('catlist', {
# #             'product': True,
# #             'wc-wp-api': {
# #                 'key': 'categories'
# #             },
# #             'wc-legacy-api': {
# #                 'key': 'categories'
# #             },
# #             # 'sync':'not_variable'
# #         }),
# #         # ('catids', {
# #         # }),
# #         ('prod_type', {
# #             'label': 'tax:product_type',
# #             'product': True,
# #             'wc-wp-api': {
# #                 'key': 'type'
# #             },
# #             'wc-legacy-api': {
# #                 'key': 'type'
# #             }
# #         }),
# #         ('catsum', {
# #             'label': 'tax:product_cat',
# #             'product': True,
# #         }),
# #         ('descsum', {
# #             'label': 'post_content',
# #             'tag': 'Description',
# #             'product': True,
# #             'variation': False,
# #             'sync': 'not_variable',
# #             'xero-api': {
# #                 'key': 'Description'
# #             }
# #         }),
# #         ('HTML Description', {
# #             'import': True,
# #             'category': True,
# #             'wc-wp-api': {
# #                 'key': 'description',
# #                 'meta': False
# #             },
# #             'wc-legacy-api': {
# #                 'key': 'description',
# #                 'meta': False
# #             },
# #             'sync': True,
# #             'type': 'html'
# #         }),
# #         ('imgsum', {
# #             'label': 'Images',
# #             'product': True,
# #             'variation': True,
# #             'category': True,
# #         }),
# #         ('rowcount', {
# #             'label': 'menu_order',
# #             'product': True,
# #             'category': True,
# #             'variation': True,
# #             'wc-wp-api': {
# #                 'key': 'menu_order'
# #             },
# #             'wc-legacy-api': {
# #                 'key': 'menu_order'
# #             },
# #             # 'sync':True
# #         }),
# #         ('PA', {
# #             'import': True
# #         }),
# #         ('VA', {
# #             'import': True
# #         }),
# #         ('D', {
# #             'label': 'meta:wootan_danger',
# #             'import': True,
# #             'product': True,
# #             'variation': True,
# #             'shipping': True,
# #             'wc-wp-api': {
# #                 'key': 'wootan_danger',
# #                 'meta': True
# #             },
# #             'wc-legacy-api': {
# #                 'key': 'wootan_danger',
# #                 'meta': True
# #             },
# #             'sync': True
# #         }),
# #         ('E', {
# #             'import': True,
# #         }),
# #         ('DYNCAT', {
# #             'import': True,
# #             'category': True,
# #             'product': True,
# #             'pricing': True,
# #         }),
# #         ('DYNPROD', {
# #             'import': True,
# #             'category': True,
# #             'product': True,
# #             'pricing': True,
# #         }),
# #         ('VISIBILITY', {
# #             'import': True,
# #         }),
# #         ('catalog_visibility', {
# #             'product': True,
# #             'default': 'visible',
# #             'wc-legacy-api': {
# #                 'key': 'catalog_visibility',
# #                 'meta': False
# #             }
# #         }),
# #         ('SCHEDULE', {
# #             'import': True,
# #             'category': True,
# #             'product': True,
# #             'pricing': True,
# #             'default': ''
# #         }),
# #         ('spsum', {
# #             'tag': 'active_specials',
# #             'label': 'meta:active_specials',
# #             'product': True,
# #             'variation': True,
# #             'pricing': True,
# #         }),
# #         ('dprclist', {
# #             'label': 'meta:dynamic_category_rulesets',
# #             # 'pricing': True,
# #             # 'product': True,
# #             # 'category': True
# #         }),
# #         ('dprplist', {
# #             'label': 'meta:dynamic_product_rulesets',
# #             # 'pricing': True,
# #             # 'product': True,
# #             # 'category': True
# #         }),
# #         ('dprcIDlist', {
# #             'label': 'meta:dynamic_category_ruleset_IDs',
# #             'pricing': True,
# #             'product': True,
# #             # 'category': True
# #         }),
# #         ('dprpIDlist', {
# #             'label': 'meta:dynamic_product_ruleset_IDs',
# #             'product': True,
# #             'pricing': True,
# #             # 'category': True
# #         }),
# #         ('dprcsum', {
# #             'label': 'meta:DPRC_Table',
# #             'product': True,
# #             'pricing': True,
# #         }),
# #         ('dprpsum', {
# #             'label': 'meta:DPRP_Table',
# #             'product': True,
# #             'pricing': True,
# #         }),
# #         ('pricing_rules', {
# #             'label': 'meta:_pricing_rules',
# #             'pricing': True,
# #             'wp': {
# #                 'key': 'pricing_rules',
# #                 'meta': False
# #             },
# #             'product': True,
# #         }),
# #         ('price', {
# #             'label': 'regular_price',
# #             'product': True,
# #             'variation': True,
# #             'pricing': True,
# #             'wp': {
# #                 'key': '_regular_price',
# #                 'meta': True
# #             },
# #             'wc-wp-api': {
# #                 'key': 'regular_price',
# #                 'meta': False
# #             },
# #             'wc-legacy-api': {
# #                 'key': '_regular_price',
# #                 'meta': True
# #             },
# #             'report': True,
# #             'static': True,
# #             'type': 'currency',
# #         }),
# #         ('sale_price', {
# #             'label': 'sale_price',
# #             'product': True,
# #             'variation': True,
# #             'pricing': True,
# #             'wp': {
# #                 'key': '_sale_price',
# #                 'meta': True
# #             },
# #             'wc-wp-api': {
# #                 'key': 'sale_price',
# #                 'meta': False
# #             },
# #             'wc-legacy-api': {
# #                 'key': '_sale_price',
# #                 'meta': True
# #             },
# #             'report': True,
# #             'type': 'currency',
# #         }),
# #         ('sale_price_dates_from', {
# #             'label': 'sale_price_dates_from',
# #             'tag': 'sale_from',
# #             'product': True,
# #             'variation': True,
# #             'pricing': True,
# #             'wp': {
# #                 'key': '_sale_price_dates_from',
# #                 'meta': True
# #             },
# #             'wc-wp-api': {
# #                 'key': 'date_on_sale_from_gmt',
# #                 'meta': False
# #             },
# #             'wc-legacy-api': {
# #                 'key': '_sale_price_dates_from',
# #                 'meta': True
# #             },
# #         }),
# #         ('sale_price_dates_to', {
# #             'label': 'sale_price_dates_to',
# #             'tag': 'sale_to',
# #             'product': True,
# #             'variation': True,
# #             'pricing': True,
# #             'wp': {
# #                 'key': '_sale_price_dates_to',
# #                 'meta': True
# #             },
# #             'wc-wp-api': {
# #                 'key': 'date_on_sale_to_gmt',
# #                 'meta': False
# #             },
# #             'wc-legacy-api': {
# #                 'key': '_sale_price_dates_to',
# #                 'meta': True
# #             },
# #         }),
# #     ] +
# #     [
# #         (
# #             ''.join([tier.upper(), field_slug.upper()]),
# #             {
# #                 'label': 'meta:lc_%s_%s' % (tier, field),
# #                 'sync': True,
# #                 'import': import_,
# #                 'product': True,
# #                 'variation': True,
# #                 'pricing': True,
# #                 'wp': {
# #                     'key': 'lc_%s_%s' % (tier, field),
# #                     'meta': True
# #                 },
# #                 'wc-wp-api': {
# #                     'key': 'lc_%s_%s' % (tier, field),
# #                     'meta': True
# #                 },
# #                 'wc-legacy-api': {
# #                     'key': 'lc_%s_%s' % (tier, field),
# #                     'meta': True
# #                 },
# #                 'static': static,
# #                 'type': type_,
# #             }
# #         ) for (tier, (field_slug, field, import_, type_, static)) in itertools.product(
# #             ['rn', 'rp', 'wn', 'wp', 'dn', 'dp'],
# #             [
# #                 ('r', 'regular_price', True, 'currency', True),
# #                 ('s', 'sale_price', False, 'currency', False),
# #                 ('f', 'sale_price_dates_from', False, 'timestamp', False),
# #                 ('t', 'sale_price_dates_to', False, 'timestamp', False)
# #             ]
# #         )
# #     ] +
# #     [
# #         ('CVC', {
# #             'label': 'meta:commissionable_value',
# #             'sync': True,
# #             'import': True,
# #             'product': True,
# #             'variation': True,
# #             'pricing': True,
# #             'default': 0,
# #             'wp': {
# #                 'key': 'commissionable_value',
# #                 'meta': True
# #             },
# #             'wc-wp-api': {
# #                 'key': 'commissionable_value',
# #                 'meta': True
# #             },
# #             'wc-legacy-api': {
# #                 'key': 'commissionable_value',
# #                 'meta': True
# #             },
# #             'type': 'coefficient'
# #         }),
# #         ('weight', {
# #             'import': True,
# #             'product': True,
# #             'variation': True,
# #             'shipping': True,
# #             'wp': {
# #                 'key': '_weight',
# #                 'meta': True
# #             },
# #             'wc-wp-api': {
# #                 'key': 'weight'
# #             },
# #             'wc-legacy-api': {
# #                 'key': 'weight'
# #             },
# #             'sync': True
# #         }),
# #         ('length', {
# #             'import': True,
# #             'product': True,
# #             'variation': True,
# #             'shipping': True,
# #             'wp': {
# #                 'key': '_length',
# #                 'meta': True
# #             },
# #             'sync': True
# #         }),
# #         ('width', {
# #             'import': True,
# #             'product': True,
# #             'variation': True,
# #             'shipping': True,
# #             'wp': {
# #                 'key': '_width',
# #                 'meta': True
# #             },
# #             'sync': True
# #         }),
# #         ('height', {
# #             'import': True,
# #             'product': True,
# #             'variation': True,
# #             'shipping': True,
# #             'wp': {
# #                 'key': '_height',
# #                 'meta': True
# #             },
# #             'sync': True
# #         }),
# #         ('stock', {
# #             'import': True,
# #             'product': True,
# #             'variation': True,
# #             'inventory': True,
# #             'wp': {
# #                 'key': '_stock',
# #                 'meta': True
# #             },
# #             'sync': True,
# #             'wc-wp-api': {
# #                 'key': 'stock_quantity'
# #             },
# #             'wc-legacy-api': {
# #                 'key': 'stock_quantity'
# #             }
# #         }),
# #         ('stock_status', {
# #             'import': True,
# #             'product': True,
# #             'variation': True,
# #             'inventory': True,
# #             'wp': {
# #                 'key': '_stock_status',
# #                 'meta': True
# #             },
# #             # 'wc-wp-api': {
# #             #     'key': 'in_stock',
# #             #     'meta': False
# #             # },
# #             # 'wc-legacy-api': {
# #             #     'key': 'in_stock',
# #             #     'meta': False
# #             # },
# #             'sync': True
# #         }),
# #         ('manage_stock', {
# #             'product': True,
# #             'variation': True,
# #             'inventory': True,
# #             'wp': {
# #                 'key': '_manage_stock',
# #                 'meta': True
# #             },
# #             'wc-wp-api': {
# #                 'key': 'manage_stock'
# #             },
# #             'wc-legacy-api': {
# #                 'key': 'managing_stock'
# #             },
# #             'sync': True,
# #             'default': 'no'
# #         }),
# #         ('Images', {
# #             'import': True,
# #             'default': ''
# #         }),
# #         ('last_import', {
# #             'label': 'meta:last_import',
# #             'product': True,
# #         }),
# #         ('Updated', {
# #             'import': True,
# #             'product': True,
# #             'wc-wp-api': {
# #                 'key': 'updated_at'
# #             },
# #             'wc-legacy-api': {
# #                 'key': 'updated_at'
# #             }
# #         }),
# #         ('post_status', {
# #             'import': True,
# #             'product': True,
# #             'variation': True,
# #             'wc-wp-api': {
# #                 'key': 'status'
# #             },
# #             'wc-legacy-api': {
# #                 'key': 'status'
# #             },
# #             'sync': True,
# #             'default': 'publish',
# #             'invincible': True
# #         }),
# #         ('is_sold', {
# #             'import': True,
# #             'product': True,
# #             'variation': True,
# #             'wc-wp-api': None,
# #             'xero-api': {
# #                 'key': 'isSold'
# #             },
# #             'default':'',
# #         }),
# #         ('is_purchased', {
# #             'import': True,
# #             'product': True,
# #             'variation': True,
# #             'wc-wp-api': None,
# #             'xero-api': {
# #                 'key': 'isPurchased'
# #             },
# #             'default': '',
# #         }),
# #     ])
# #
# #
# #     def __init__(self, data=None):
# #         if not data:
# #             data = self.data
# #         super(ColDataWoo, self).__init__(data)
# #
# #     @classmethod
# #     def get_variation_cols(cls):
# #         return cls.get_export_cols('variation')
# #
# #     @classmethod
# #     def get_wp_sql_cols(cls):
# #         return cls.get_export_cols('wp')
# #
# #     @classmethod
# #     def get_attribute_colnames_native(cls, attributes, vattributes):
# #         attribute_cols = OrderedDict()
# #         all_attrs = SeqUtils.combine_lists(
# #             attributes.keys(), vattributes.keys())
# #         for attr in all_attrs:
# #             attribute_cols['attribute:' + attr] = {
# #                 'product': True,
# #             }
# #             if attr in vattributes.keys():
# #                 attribute_cols['attribute_default:' + attr] = {
# #                     'product': True,
# #                 }
# #                 attribute_cols['attribute_data:' + attr] = {
# #                     'product': True,
# #                 }
# #         return attribute_cols
# #
# #     @classmethod
# #     def get_attribute_meta_colnames_native(cls, vattributes):
# #         atttribute_meta_cols = OrderedDict()
# #         for attr in vattributes.keys():
# #             atttribute_meta_cols['meta:attribute_' + attr] = {
# #                 'variable': True,
# #                 'tag': attr
# #             }
# #         return atttribute_meta_cols
# #
#
# class ColDataUser(ColDataBase):
#     # modTimeSuffix = ' Modified'
#
#     deprecate_oldstyle = False
#
#     master_schema = 'act'
#
#     modMapping = {
#         'Home Address': 'Alt Address',
#     }
#
#     @classmethod
#     def mod_time_col(cls, col):
#         if col in cls.modMapping:
#             col = cls.modMapping[col]
#         return 'Edited ' + col
#
#     wpdbPKey = 'Wordpress ID'
#
#     data = OrderedDict([
#         ('MYOB Card ID', {
#             'wp': {
#                 'meta': True,
#                 'key': 'myob_card_id'
#             },
#             'wp-api': {
#                 'meta': True,
#                 'key': 'myob_card_id'
#             },
#             'wc-api': {
#                 'meta': True,
#                 'key': 'myob_card_id'
#             },
#             'act': True,
#             # 'label':'myob_card_id',
#             'import': True,
#             'user': True,
#             'report': True,
#             'sync': 'master_override',
#             'warn': True,
#             'static': True,
#             'basic': True,
#         }),
#         ('E-mail', {
#             'wp': {
#                 'meta': False,
#                 'key': 'user_email'
#             },
#             'wp-api': {
#                 'meta': False,
#                 'key': 'email'
#             },
#             'wc-api': {
#                 'meta': False,
#                 'key': 'email'
#             },
#             'act': True,
#             'import': True,
#             'user': True,
#             'report': True,
#             'sync': True,
#             'warn': True,
#             'static': True,
#             'basic': True,
#             'tracked': True,
#             'delta': True,
#         }),
#         ('Wordpress Username', {
#             # 'label':'Username',
#             'wp': {
#                 'meta': False,
#                 'key': 'user_login',
#                 'final': True
#             },
#             'wp-api': {
#                 'meta': False,
#                 'key': 'username'
#             },
#             'wc-api': {
#                 'meta': False,
#                 'key': 'username'
#             },
#             'act': True,
#             'user': True,
#             'report': True,
#             'import': True,
#             'sync': 'slave_override',
#             'warn': True,
#             'static': True,
#             # 'tracked':True,
#             # 'basic':True,
#         }),
#         ('Wordpress ID', {
#             # 'label':'Username',
#             'wp': {
#                 'meta': False,
#                 'key': 'ID',
#                 'final': True
#             },
#             'wp-api': {
#                 'key': 'id',
#                 'meta': False
#             },
#             'wc-api': {
#                 'key': 'id',
#                 'meta': False
#             },
#             'act': False,
#             'user': True,
#             'report': True,
#             'import': True,
#             # 'sync':'slave_override',
#             'warn': True,
#             'static': True,
#             'basic': True,
#             'default': '',
#             # 'tracked':True,
#         }),
#         ('ACT Role',{
#             'wp': {
#                 'meta': True,
#                 'key': 'act_role'
#             },
#             'wp-api': {
#                 'meta': True,
#                 'key': 'act_role'
#             },
#             'wc-api': {
#                 'meta': True,
#                 'key': 'act_role'
#             },
#             'act': {
#                 'key': 'Role'
#             },
#             'import': True,
#         }),
#         ('WP Roles',{
#             'wp': {
#                 'meta': True,
#                 'key': 'tt6164_capabilities',
#             },
#             'wp-api': {
#                 'meta': False,
#                 'key': 'roles'
#             },
#             'wc-api': {
#                 'meta': False,
#                 'key': 'roles'
#             },
#             'import': True,
#         }),
#         # ('Role Info', {
#         #     'aliases': [
#         #         'Role',
#         #         'Direct Brand'
#         #     ],
#         #     'sync': True,
#         #     'static': True,
#         #     'basic': True,
#         #     'report': True,
#         #     'delta': True,
#         #     # 'tracked': True,
#         #     'reflective': 'master',
#         #     'user': True,
#         # }),
#         # ('Role', {
#         #     'wp': {
#         #         'meta': True,
#         #         'key': 'act_role'
#         #     },
#         #     'wp-api': {
#         #         'meta': True,
#         #         'key': 'act_role'
#         #     },
#         #     'wc-api': {
#         #         'meta': True,
#         #         'key': 'act_role'
#         #     },
#         #     # 'label': 'act_role',
#         #     'import': True,
#         #     'act': True,
#         #     # 'user': True,
#         #     # 'report': True,
#         #     # 'sync': True,
#         #     'warn': True,
#         #     'static': True,
#         #     # 'tracked':'future',
#         # }),
#         # ('Direct Brand', {
#         #     'import': True,
#         #     'wp': {
#         #         'meta': True,
#         #         'key': 'direct_brand'
#         #     },
#         #     'wp-api': {
#         #         'meta': True,
#         #         'key': 'direct_brand'
#         #     },     'wc-api': {
#         #         'meta': True,
#         #         'key': 'direct_brand'
#         #     },
#         #     'act': True,
#         #     # 'label':'direct_brand',
#         #     # 'user': True,
#         #     # 'report': True,
#         #     # 'sync': 'master_override',
#         #     'warn': True,
#         # }),
#
#         ('Name', {
#             'aliases': [
#                 'Contact',
#                 # 'Display Name',
#                 'Name Prefix',
#                 'First Name',
#                 'Middle Name',
#                 'Surname',
#                 'Name Suffix',
#                 'Memo',
#                 'Spouse',
#                 'Salutation',
#             ],
#             'user': True,
#             'sync': True,
#             'static': True,
#             'basic': True,
#             'report': True,
#             'tracked': True,
#             'invincible': True,
#         }),
#         ('Contact', {
#             'import': True,
#             'act': True,
#             'mutable': True,
#             'visible': True,
#             'default': '',
#         }),
#         # ('Display Name', {
#         #     'import': True,
#         #     'act': False
#         #     'wp': {
#         #         'meta': False,
#         #         'key': 'display_name'
#         #     },
#         #     'wp-api': {
#         #         'meta': False,
#         #         'key': 'name'
#         #     },     'wc-api': {
#         #         'meta': False,
#         #         'key': 'name'
#         #     },
#         # })
#         ('First Name', {
#             'wp': {
#                 'meta': True,
#                 'key': 'first_name'
#             },
#             'wp-api': {
#                 'meta': False,
#                 'key': 'first_name'
#             },
#             'wc-api': {
#                 'meta': False,
#                 'key': 'first_name'
#             },
#             'act': True,
#             'mutable': True,
#             'visible': True,
#             # 'label':'first_name',
#             'import': True,
#             'invincible': 'master',
#             # 'user':True,
#             # 'report': True,
#             # 'sync':True,
#             # 'warn': True,
#             # 'static':True,
#         }),
#         ('Surname', {
#             'wp': {
#                 'meta': True,
#                 'key': 'last_name'
#             },
#             'wp-api': {
#                 'meta': False,
#                 'key': 'last_name'
#             },
#             'wc-api': {
#                 'meta': False,
#                 'key': 'last_name'
#             },
#             'act': True,
#             'mutable': True,
#             # 'label':'last_name',
#             'import': True,
#             'visible': True,
#             'invincible': 'master',
#             # 'user':True,
#             # 'report': True,
#             # 'sync':True,
#             # 'warn': True,
#             # 'static':True,
#         }),
#         ('Middle Name', {
#             'wp': {
#                 'meta': True,
#                 'key': 'middle_name'
#             },
#             'wp-api': {
#                 'meta': True,
#                 'key': 'middle_name'
#             },
#             'wc-api': {
#                 'meta': True,
#                 'key': 'middle_name'
#             },
#             'act': True,
#             'import': True,
#             'mutable': True,
#             'visible': True,
#             # 'user': True,
#             'default': '',
#         }),
#         ('Name Suffix', {
#             'wp': {
#                 'meta': True,
#                 'key': 'name_suffix'
#             },
#             'wp-api': {
#                 'meta': True,
#                 'key': 'name_suffix'
#             },
#             'wc-api': {
#                 'meta': True,
#                 'key': 'name_suffix'
#             },
#             'act': True,
#             'import': True,
#             'visible': True,
#             # 'user': True,
#             'mutable': True,
#             'default': '',
#         }),
#         ('Name Prefix', {
#             'wp': {
#                 'meta': True,
#                 'key': 'name_prefix'
#             },
#             'wp-api': {
#                 'meta': True,
#                 'key': 'name_prefix'
#             },
#             'wc-api': {
#                 'meta': True,
#                 'key': 'name_prefix'
#             },
#             'act': True,
#             'import': True,
#             'visible': True,
#             # 'user': True,
#             'mutable': True,
#             'default': '',
#         }),
#         ('Memo', {
#             'wp': {
#                 'meta': True,
#                 'key': 'name_notes'
#             },
#             'wp-api': {
#                 'meta': True,
#                 'key': 'name_notes'
#             },
#             'wc-api': {
#                 'meta': True,
#                 'key': 'name_notes'
#             },
#             'act': True,
#             'import': True,
#             'tracked': True,
#         }),
#         ('Spouse', {
#             'wp': {
#                 'meta': True,
#                 'key': 'spouse'
#             },
#             'wp-api': {
#                 'meta': True,
#                 'key': 'spouse'
#             },
#             'wc-api': {
#                 'meta': True,
#                 'key': 'spouse'
#             },
#             'act': True,
#             'import': True,
#             'tracked': 'future',
#             'default': '',
#         }),
#         ('Salutation', {
#             'wp': {
#                 'meta': True,
#                 'key': 'nickname'
#             },
#             'wp-api': {
#                 'meta': True,
#                 'key': 'nickname'
#             },
#             'wc-api': {
#                 'meta': True,
#                 'key': 'nickname'
#             },
#             'act': True,
#             'import': True,
#             'default': '',
#         }),
#
#         ('Company', {
#             'wp': {
#                 'meta': True,
#                 'key': 'billing_company'
#             },
#             'wp-api': {
#                 'meta': True,
#                 'key': 'billing_company'
#             },
#             'wc-api': {
#                 'meta': True,
#                 'key': 'billing_company'
#             },
#             'act': True,
#             # 'label':'billing_company',
#             'import': True,
#             'user': True,
#             'basic': True,
#             'report': True,
#             'sync': True,
#             'warn': True,
#             'static': True,
#             # 'visible':True,
#             'tracked': True,
#             'invincible': 'master',
#         }),
#
#
#         ('Phone Numbers', {
#             'act': False,
#             'wp': False,
#             'tracked': 'future',
#             'aliases': [
#                 'Mobile Phone', 'Phone', 'Fax',
#                 # 'Mobile Phone Preferred', 'Phone Preferred',
#                 # 'Pref Method'
#             ],
#             'import': False,
#             'basic': True,
#             'sync': True,
#             'report': True,
#         }),
#
#         ('Mobile Phone', {
#             'wp': {
#                 'meta': True,
#                 'key': 'mobile_number'
#             },
#             'wp-api': {
#                 'meta': True,
#                 'key': 'mobile_number'
#             },
#             'wc-api': {
#                 'meta': True,
#                 'key': 'mobile_number'
#             },
#             'act': True,
#             # 'label':'mobile_number',
#             'import': True,
#             'user': True,
#             # 'sync': True,
#             'warn': True,
#             'static': True,
#             'invincible': 'master',
#             # 'visible':True,
#             'contact': True,
#         }),
#         ('Phone', {
#             'wp': {
#                 'meta': True,
#                 'key': 'billing_phone'
#             },
#             'wp-api': {
#                 'meta': True,
#                 'key': 'billing_phone'
#             },
#             'wc-api': {
#                 'meta': True,
#                 'key': 'billing_phone'
#             },
#             'act': True,
#             # 'label':'billing_phone',
#             'import': True,
#             'user': True,
#             # 'report': True,
#             # 'sync': True,
#             'warn': True,
#             'static': True,
#             'invincible': 'master',
#             # 'visible':True,
#         }),
#         ('Home Phone', {
#             'act': True,
#             # 'label':'billing_phone',
#             'import': True,
#             'user': True,
#             # 'report': True,
#             # 'sync': True,
#             'warn': True,
#             'static': True,
#             'invincible': 'master',
#             # 'visible':True,
#         }),
#         ('Fax', {
#             'wp': {
#                 'meta': True,
#                 'key': 'fax_number'
#             },
#             'wp-api': {
#                 'meta': True,
#                 'key': 'fax_number'
#             },
#             'wc-api': {
#                 'meta': True,
#                 'key': 'fax_number'
#             },
#             'act': True,
#             # 'label':'fax_number',
#             'import': True,
#             'user': True,
#             # 'sync': True,
#             'contact': True,
#             'visible': True,
#             'mutable': True,
#         }),
#         # TODO: implement pref method
#         ('Pref Method', {
#             'wp': {
#                 'meta': True,
#                 'key': 'pref_method',
#                 'options': ['', 'pref_mob', 'pref_tel', '']
#             },
#             'wp-api': {
#                 'meta': True,
#                 'key': 'pref_method',
#                 'options': ['', 'pref_mob', 'pref_tel', '']
#             },
#             'wc-api': {
#                 'meta': True,
#                 'key': 'pref_method',
#                 'options': ['', 'pref_mob', 'pref_tel', '']
#             },
#             'act': {
#                 'options': ['E-mail', 'Mobile', 'Phone', 'SMS'],
#                 'sync':False
#             },
#             'invincible': 'master',
#             'sync': False,
#             'import': False,
#         }),
#         # ('Mobile Phone Preferred', {
#         #     'wp': {
#         #         'meta': True,
#         #         'key': 'pref_mob'
#         #     },
#         #     'wp-api': {
#         #         'meta': True,
#         #         'key': 'pref_mob'
#         #     },     'wc-api': {
#         #         'meta': True,
#         #         'key': 'pref_mob'
#         #     },
#         #     'act': {
#         #         'options':['True', 'False']
#         #     },
#         #     # 'label':'pref_mob',
#         #     'import': True,
#         #     'user': True,
#         #     'sync': True,
#         #     'visible': True,
#         #     'mutable': True,
#         #     'invincible':'master',
#         # }),
#         # ('Phone Preferred', {
#         #     'wp': {
#         #         'meta': True,
#         #         'key': 'pref_tel'
#         #     },
#         #     'wp-api': {
#         #         'meta': True,
#         #         'key': 'pref_tel'
#         #     },     'wc-api': {
#         #         'meta': True,
#         #         'key': 'pref_tel'
#         #     },
#         #     'act': {
#         #         'options':['True', 'False']
#         #     },
#         #     # 'label':'pref_tel',
#         #     'import': True,
#         #     'user': True,
#         #     'sync': True,
#         #     'visible': True,
#         #     'mutable': True,
#         #     'invincible':'master',
#         # }),
#         # ('Home Phone Preferred', {
#         #     'act': {
#         #         'options':['True', 'False']
#         #     },
#         #     # 'label':'pref_tel',
#         #     'import': True,
#         #     'user': True,
#         #     'sync': True,
#         #     'visible': True,
#         #     'mutable': True,
#         #     'invincible':'master',
#         # }),
#
#         ('Address', {
#             'act': False,
#             'wp': False,
#             'report': True,
#             'warn': True,
#             'static': True,
#             'sync': True,
#             'aliases': ['Address 1', 'Address 2', 'City', 'Postcode', 'State', 'Country', 'Shire'],
#             'basic': True,
#             'tracked': True,
#         }),
#         ('Home Address', {
#             'act': False,
#             'wp': False,
#             'report': True,
#             'warn': True,
#             'static': True,
#             'sync': True,
#             'basic': True,
#             'aliases': [
#                 'Home Address 1', 'Home Address 2', 'Home City', 'Home Postcode',
#                 'Home State', 'Home Country'
#             ],
#             'tracked': 'future',
#         }),
#         ('Address 1', {
#             'wp': {
#                 'meta': True,
#                 'key': 'billing_address_1'
#             },
#             'wp-api': {
#                 'meta': True,
#                 'key': 'billing_address_1'
#             },
#             'wc-api': {
#                 'meta': True,
#                 'key': 'billing_address_1'
#             },
#             'act': True,
#             # 'label':'billing_address_1',
#             'import': True,
#             'user': True,
#             # 'sync':True,
#             # 'warn': True,
#             # 'static':True,
#             # 'capitalized':True,
#             # 'visible':True,
#         }),
#         ('Address 2', {
#             'wp': {
#                 'meta': True,
#                 'key': 'billing_address_2'
#             },
#             'wp-api': {
#                 'meta': True,
#                 'key': 'billing_address_2'
#             },
#             'wc-api': {
#                 'meta': True,
#                 'key': 'billing_address_2'
#             },
#             'act': True,
#             # 'label':'billing_address_2',
#             'import': True,
#             'user': True,
#             # 'sync':True,
#             # 'warn': True,
#             # 'static':True,
#             # 'capitalized':True,
#             # 'visible':True,
#             'default': '',
#         }),
#         ('City', {
#             'wp': {
#                 'meta': True,
#                 'key': 'billing_city'
#             },
#             'wp-api': {
#                 'meta': True,
#                 'key': 'billing_city'
#             },
#             'wc-api': {
#                 'meta': True,
#                 'key': 'billing_city'
#             },
#             'act': True,
#             # 'label':'billing_city',
#             'import': True,
#             'user': True,
#             # 'sync':True,
#             # 'warn': True,
#             # 'static':True,
#             # 'report': True,
#             # 'capitalized':True,
#             # 'visible':True,
#         }),
#         ('Postcode', {
#             'wp': {
#                 'meta': True,
#                 'key': 'billing_postcode'
#             },
#             'wp-api': {
#                 'meta': True,
#                 'key': 'billing_postcode'
#             },
#             'wc-api': {
#                 'meta': True,
#                 'key': 'billing_postcode'
#             },
#             'act': True,
#             # 'label':'billing_postcode',
#             'import': True,
#             'user': True,
#             # 'sync':True,
#             # 'warn': True,
#             # 'static':True,
#             # 'visible':True,
#             # 'report': True,
#         }),
#         ('State', {
#             'wp': {
#                 'meta': True,
#                 'key': 'billing_state'
#             },
#             'wp-api': {
#                 'meta': True,
#                 'key': 'billing_state'
#             },
#             'wc-api': {
#                 'meta': True,
#                 'key': 'billing_state'
#             },
#             'act': True,
#             # 'label':'billing_state',
#             'import': True,
#             'user': True,
#             # 'sync':True,
#             # 'warn': True,
#             # 'static':True,
#             # 'report':True,
#             # 'capitalized':True,
#             # 'visible':True,
#         }),
#         ('Country', {
#             'wp': {
#                 'meta': True,
#                 'key': 'billing_country'
#             },
#             'wp-api': {
#                 'meta': True,
#                 'key': 'billing_country'
#             },
#             'wc-api': {
#                 'meta': True,
#                 'key': 'billing_country'
#             },
#             'act': True,
#             # 'label':'billing_country',
#             'import': True,
#             'user': True,
#             # 'warn':True,
#             # 'static':True,
#             # 'capitalized':True,
#             # 'visible':True,
#         }),
#         ('Shire', {
#             'wp': False,
#             'act': True,
#             # 'label':'billing_country',
#             'import': True,
#             'user': True,
#             # 'warn':True,
#             # 'static':True,
#             # 'capitalized':True,
#             # 'visible':True,
#             'default': '',
#         }),
#         ('Home Address 1', {
#             'wp': {
#                 'meta': True,
#                 'key': 'shipping_address_1'
#             },
#             'wp-api': {
#                 'meta': True,
#                 'key': 'shipping_address_1'
#             },
#             'wc-api': {
#                 'meta': True,
#                 'key': 'shipping_address_1'
#             },
#             'act': True,
#             # 'label':'shipping_address_1',
#             'import': True,
#             'user': True,
#             # 'sync':True,
#             # 'static':True,
#             # 'capitalized':True,
#             # 'visible':True,
#         }),
#         ('Home Address 2', {
#             'wp': {
#                 'meta': True,
#                 'key': 'shipping_address_2'
#             },
#             'wp-api': {
#                 'meta': True,
#                 'key': 'shipping_address_2'
#             },
#             'wc-api': {
#                 'meta': True,
#                 'key': 'shipping_address_2'
#             },
#             'act': True,
#             # 'label':'shipping_address_2',
#             'import': True,
#             'user': True,
#             # 'sync':True,
#             # 'static':True,
#             # 'capitalized':True,
#             # 'visible':True,
#             'default': '',
#         }),
#         ('Home City', {
#             'wp': {
#                 'meta': True,
#                 'key': 'shipping_city'
#             },
#             'wp-api': {
#                 'meta': True,
#                 'key': 'shipping_city'
#             },
#             'wc-api': {
#                 'meta': True,
#                 'key': 'shipping_city'
#             },
#             'act': True,
#             # 'label':'shipping_city',
#             'import': True,
#             'user': True,
#             # 'sync':True,
#             # 'static':True,
#             # 'capitalized':True,
#             # 'visible':True,
#         }),
#         ('Home Postcode', {
#             'wp': {
#                 'meta': True,
#                 'key': 'shipping_postcode'
#             },
#             'wp-api': {
#                 'meta': True,
#                 'key': 'shipping_postcode'
#             },
#             'wc-api': {
#                 'meta': True,
#                 'key': 'shipping_postcode'
#             },
#             'act': True,
#             # 'label':'shipping_postcode',
#             'import': True,
#             'user': True,
#             # 'sync':True,
#             # 'static':True,
#             # 'visible':True,
#         }),
#         ('Home Country', {
#             'wp': {
#                 'meta': True,
#                 'key': 'shipping_country'
#             },
#             'wp-api': {
#                 'meta': True,
#                 'key': 'shipping_country'
#             },
#             'wc-api': {
#                 'meta': True,
#                 'key': 'shipping_country'
#             },
#             'act': True,
#             # 'label':'shipping_country',
#             'import': True,
#             'user': True,
#             # 'sync':True,
#             # 'static':True,
#             # 'capitalized':True,
#             # 'visible':True,
#         }),
#         ('Home State', {
#             'wp': {
#                 'meta': True,
#                 'key': 'shipping_state'
#             },
#             'wp-api': {
#                 'meta': True,
#                 'key': 'shipping_state'
#             },
#             'wc-api': {
#                 'meta': True,
#                 'key': 'shipping_state'
#             },
#             'act': True,
#             # 'label':'shipping_state',
#             'import': True,
#             'user': True,
#             # 'sync':True,
#             # 'static':True,
#             # 'capitalized':True,
#             # 'visible':True,
#         }),
#
#
#
#         ('MYOB Customer Card ID', {
#             # 'label':'myob_customer_card_id',
#             'wp': {
#                 'meta': True,
#                 'key': 'myob_customer_card_id'
#             },
#             'wp-api': {
#                 'meta': True,
#                 'key': 'myob_customer_card_id'
#             },
#             'wc-api': {
#                 'meta': True,
#                 'key': 'myob_customer_card_id'
#             },
#             'act': True,
#             'import': True,
#             # 'report':True,
#             'user': True,
#             'sync': 'master_override',
#             'warn': True,
#             'default': '',
#         }),
#         ('Client Grade', {
#             'import': True,
#             'wp': {
#                 'meta': True,
#                 'key': 'client_grade'
#             },
#             'wp-api': {
#                 'meta': True,
#                 'key': 'client_grade'
#             },
#             'wc-api': {
#                 'meta': True,
#                 'key': 'client_grade'
#             },
#             'act': True,
#             # 'label':'client_grade',
#             'user': True,
#             # 'report':True,
#             'sync': 'master_override',
#             'invincible': 'master',
#             'warn': True,
#             'visible': True,
#         }),
#         ('Agent', {
#             'wp': {
#                 'meta': True,
#                 'key': 'agent'
#             },
#             'wp-api': {
#                 'meta': True,
#                 'key': 'agent'
#             },
#             'wc-api': {
#                 'meta': True,
#                 'key': 'agent'
#             },
#             'act': True,
#             # 'label':'agent',
#             'import': 'true',
#             'user': True,
#             'sync': 'master_override',
#             'warn': True,
#             'visible': True,
#             'default': '',
#         }),
#
#         ('ABN', {
#             'wp': {
#                 'meta': True,
#                 'key': 'abn'
#             },
#             'wp-api': {
#                 'meta': True,
#                 'key': 'abn'
#             },
#             'wc-api': {
#                 'meta': True,
#                 'key': 'abn'
#             },
#             'act': True,
#             # 'label':'abn',
#             'import': True,
#             'user': True,
#             'sync': True,
#             'warn': True,
#             'visible': True,
#             'mutable': True,
#         }),
#         ('Business Type', {
#             'wp': {
#                 'meta': True,
#                 'key': 'business_type'
#             },
#             'wp-api': {
#                 'meta': True,
#                 'key': 'business_type'
#             },
#             'wc-api': {
#                 'meta': True,
#                 'key': 'business_type'
#             },
#             'act': True,
#             # 'label':'business_type',
#             'import': True,
#             'user': True,
#             'sync': True,
#             'invincible': 'master',
#             'visible': True,
#             # 'mutable':True
#         }),
#         ('Lead Source', {
#             'wp': {
#                 'meta': True,
#                 'key': 'how_hear_about'
#             },
#             'wp-api': {
#                 'meta': True,
#                 'key': 'how_hear_about'
#             },
#             'wc-api': {
#                 'meta': True,
#                 'key': 'how_hear_about'
#             },
#             'act': True,
#             # 'label':'how_hear_about',
#             'import': True,
#             'user': True,
#             'sync': True,
#             'invincible': 'master',
#             # 'visible':True,
#             'default': '',
#         }),
#         ('Referred By', {
#             'wp': {
#                 'meta': True,
#                 'key': 'referred_by'
#             },
#             'wp-api': {
#                 'meta': True,
#                 'key': 'referred_by'
#             },
#             'wc-api': {
#                 'meta': True,
#                 'key': 'referred_by'
#             },
#             'act': True,
#             # 'label':'referred_by',
#             'import': True,
#             'user': True,
#             'sync': True,
#             'invincible': 'master',
#         }),
#         ('Tans Per Week', {
#             'wp': {
#                 'meta': True,
#                 'key': 'tans_per_wk'
#             },
#             'wp-api': {
#                 'meta': True,
#                 'key': 'tans_per_wk'
#             },
#             'wc-api': {
#                 'meta': True,
#                 'key': 'tans_per_wk'
#             },
#             'act': True,
#             'import': True,
#             'user': True,
#             'sync': True,
#             'default': '',
#             'invincible': 'master',
#         }),
#
#         # ('E-mails', {
#         #     'aliases': ['E-mail', 'Personal E-mail']
#         # }),
#         ('Personal E-mail', {
#             'wp': {
#                 'meta': True,
#                 'key': 'personal_email'
#             },
#             'wp-api': {
#                 'meta': True,
#                 'key': 'personal_email'
#             },
#             'wc-api': {
#                 'meta': True,
#                 'key': 'personal_email'
#             },
#             'act': True,
#             # 'label':'personal_email',
#             'import': True,
#             'user': True,
#             'tracked': 'future',
#             'report': True,
#         }),
#         ('Create Date', {
#             'import': True,
#             'act': True,
#             'wp': False,
#             'report': True,
#             'basic': True
#         }),
#         ('Wordpress Start Date', {
#             'import': True,
#             'wp': {
#                 'meta': False,
#                 'key': 'user_registered'
#             },
#             'wp-api': {
#                 'meta': False,
#                 'key': 'user_registered'
#             },
#             'wc-api': {
#                 'meta': False,
#                 'key': 'user_registered'
#             },
#             'act': True,
#             # 'report': True,
#             # 'basic':True
#         }),
#         ('Edited in Act', {
#             'wp': {
#                 'meta': True,
#                 'key': 'edited_in_act'
#             },
#             'wp-api': {
#                 'meta': True,
#                 'key': 'edited_in_act'
#             },
#             'wc-api': {
#                 'meta': True,
#                 'key': 'edited_in_act'
#             },
#             'act': True,
#             'import': True,
#             'report': True,
#             'basic': True,
#         }),
#         ('Edited in Wordpress', {
#             'wp': {
#                 'generated': True,
#             },
#             'act': True,
#             'import': True,
#             'report': True,
#             'basic': True,
#             'default': '',
#         }),
#         ('Last Sale', {
#             'wp': {
#                 'meta': True,
#                 'key': 'act_last_sale'
#             },
#             'wp-api': {
#                 'meta': True,
#                 'key': 'act_last_sale'
#             },
#             'wc-api': {
#                 'meta': True,
#                 'key': 'act_last_sale'
#             },
#             'act': True,
#             'import': True,
#             'basic': True,
#             'report': True
#         }),
#
#         ('Social Media', {
#             'sync': True,
#             'aliases': [
#                 'Facebook Username', 'Twitter Username',
#                 'GooglePlus Username', 'Instagram Username',
#                 'Web Site'
#             ],
#             'tracked': True,
#         }),
#
#         ("Facebook Username", {
#             'wp': {
#                 'key': "facebook",
#                 'meta': True
#             },
#             'wp-api': {
#                 'key': "facebook",
#                 'meta': True
#             },
#             'wc-api': {
#                 'key': "facebook",
#                 'meta': True
#             },
#             'mutable': True,
#             'visible': True,
#             'contact': True,
#             'import': True,
#             'act': True,
#             'default': '',
#         }),
#         ("Twitter Username", {
#             'wp': {
#                 'key': "twitter",
#                 'meta': True
#             },
#             'wp-api': {
#                 'key': "twitter",
#                 'meta': True
#             },
#             'wc-api': {
#                 'key': "twitter",
#                 'meta': True
#             },
#             'contact': True,
#             'mutable': True,
#             'visible': True,
#             'import': True,
#             'act': True,
#             'default': '',
#         }),
#         ("GooglePlus Username", {
#             'wp': {
#                 'key': "gplus",
#                 'meta': True
#             },
#             'wp-api': {
#                 'key': "gplus",
#                 'meta': True
#             },
#             'wc-api': {
#                 'key': "gplus",
#                 'meta': True
#             },
#             'contact': True,
#             'mutable': True,
#             'visible': True,
#             'import': True,
#             'act': True,
#             'default': '',
#         }),
#         ("Instagram Username", {
#             'wp': {
#                 'key': "instagram",
#                 'meta': True
#             },
#             'wp-api': {
#                 'key': "instagram",
#                 'meta': True
#             },
#             'wc-api': {
#                 'key': "instagram",
#                 'meta': True
#             },
#             'contact': True,
#             'mutable': True,
#             'visible': True,
#             'import': True,
#             'act': True,
#             'default': '',
#         }),
#         ('Web Site', {
#             'wp': {
#                 'meta': False,
#                 'key': 'user_url'
#             },
#             'wp-api': {
#                 'meta': False,
#                 'key': 'url'
#             },
#             'wc-api': {
#                 'meta': False,
#                 'key': 'url'
#             },
#             'act': True,
#             'label': 'user_url',
#             'import': True,
#             'user': True,
#             'sync': True,
#             'tracked': True,
#             'invincible': 'master',
#         }),
#
#         ("Added to mailing list", {
#             'wp': {
#                 'key': 'mailing_list',
#                 'meta': True,
#             },
#             'wp-api': {
#                 'key': 'mailing_list',
#                 'meta': True,
#             },
#             'wc-api': {
#                 'key': 'mailing_list',
#                 'meta': True,
#             },
#             'sync': True,
#             'import': True,
#             'tracked': True,
#             'default': '',
#         }),
#         # ('rowcount', {
#         #     # 'import':True,
#         #     # 'user':True,
#         #     'report':True,
#         # }),
#
#         # Other random fields that I don't understand
#         ("Direct Customer", {
#             'act': True,
#             'import': True,
#         }),
#         # ("Mobile Phone Status", {
#         #     'act':True,
#         #     'import': True,
#         # }),
#         # ("Home Phone Status", {
#         #     'act':True,
#         #     'import': True,
#         # }),
#         # ("Phone Status", {
#         #     'act':True,
#         #     'import': True,
#         # }),
#     ])
#
#     def __init__(self, data=None):
#         if not data:
#             data = self.data
#         super(ColDataUser, self).__init__(data)
#
#     @classmethod
#     def get_user_cols(cls):
#         return cls.get_export_cols('user')
#
#     @classmethod
#     def get_sync_handles(cls):
#         return cls.get_export_cols('sync')
#
#     @classmethod
#     def get_capital_cols(cls):
#         return cls.get_export_cols('capitalized')
#
#     @classmethod
#     def get_wp_sql_cols(cls):
#         return cls.get_export_cols('wp')
#
#     @classmethod
#     def get_act_cols(cls):
#         return cls.get_export_cols('act')
#
#     @classmethod
#     def get_alias_cols(cls):
#         return cls.get_export_cols('aliases')
#
#     @classmethod
#     def get_alias_mapping(cls):
#         alias_mappings = {}
#         for col, data in cls.get_alias_cols().items():
#             alias_mappings[col] = data.get('aliases')
#         return alias_mappings
#
#     @classmethod
#     def get_wp_import_cols(cls):
#         cols = []
#         for col, data in cls.data.items():
#             if data.get('wp') and data.get('import'):
#                 cols.append(col)
#             if data.get('tracked'):
#                 cols.append(cls.mod_time_col(col))
#         return cols
#
#     @classmethod
#     def get_wp_import_col_names(cls):
#         cols = OrderedDict()
#         for col, data in cls.data.items():
#             if data.get('wp') and data.get('import'):
#                 cols[col] = col
#             if data.get('tracked'):
#                 mod_col = cls.mod_time_col(col)
#                 cols[mod_col] = mod_col
#         return cols
#
#     @classmethod
#     def get_wpdb_cols(cls, meta=None):
#         cols = OrderedDict()
#         for col, data in cls.data.items():
#             if data.get('wp'):
#                 wp_data = data['wp']
#                 if hasattr(wp_data, '__getitem__'):
#                     if wp_data.get('generated')\
#                             or (meta and not wp_data.get('meta'))\
#                             or (not meta and wp_data.get('meta')):
#                         continue
#                     if wp_data.get('key'):
#                         key = wp_data['key']
#                         if key:
#                             cols[key] = col
#         if not meta:
#             assert cls.wpdbPKey in cols.values()
#         return cols
#
#     @classmethod
#     def get_all_wpdb_cols(cls):
#         return SeqUtils.combine_ordered_dicts(
#             cls.get_wpdb_cols(True),
#             cls.get_wpdb_cols(False)
#         )
#
#     # @classmethod
#     # def getWPTrackedColsRecursive(self, col, cols = None, data={}):
#     #     if cols is None:
#     #         cols = OrderedDict()
#     #     if data.get('wp'):
#     #         wp_data = data.get('wp')
#     #         if hasattr(wp_data, '__getitem__'):
#     #             if wp_data.get('key'):
#     #                 key = wp_data.get('key')
#     #                 if key:
#     #                     cols[col] = cols.get(col, []) + [key]
#     #     if data.get('tracked'):
#     #         for alias in data.get('aliases', []):
#     #             alias_data = self.data.get(alias, {})
#     #             cols = self.getWPTrackedColsRecursive(alias, cols, alias_data)
#
#     #     return cols
#
#     @classmethod
#     def get_tracked_cols(cls, schema=None):
#         if not schema:
#             schema = cls.master_schema
#         cols = OrderedDict()
#         for col, data in cls.data.items():
#             if data.get('tracked'):
#                 tracking_name = cls.mod_time_col(col)
#                 for alias in data.get('aliases', []) + [col]:
#                     alias_data = cls.data.get(alias, {})
#                     if alias_data.get(schema):
#                         this_tracking_name = tracking_name
#                         if alias_data.get('tracked'):
#                             this_tracking_name = cls.mod_time_col(alias)
#                         cols[this_tracking_name] = cols.get(
#                             this_tracking_name, []) + [alias]
#         return cols
#
#     @classmethod
#     def get_wp_tracked_cols(cls):
#         return cls.get_tracked_cols('wp')
#
#     get_slave_tracked_cols = get_wp_tracked_cols
#
#     @classmethod
#     def get_act_tracked_cols(cls):
#         return cls.get_tracked_cols('act')
#
#     get_master_tracked_cols = get_act_tracked_cols
#
#     @classmethod
#     def get_act_future_tracked_cols(cls):
#         cols = OrderedDict()
#         for col, data in cls.data.items():
#             if data.get('tracked') and data.get('tracked') == 'future':
#                 tracking_name = cls.mod_time_col(col)
#                 for alias in data.get('aliases', []) + [col]:
#                     alias_data = cls.data.get(alias, {})
#                     if alias_data.get('act'):
#                         this_tracking_name = tracking_name
#                         if alias_data.get('tracked'):
#                             this_tracking_name = cls.mod_time_col(alias)
#                         cols[this_tracking_name] = cols.get(
#                             this_tracking_name, []) + [alias]
#         return cols
#
#     get_master_future_tracked_cols = get_act_future_tracked_cols
#
#     @classmethod
#     def get_act_import_cols(cls):
#         cols = []
#         for col, data in cls.data.items():
#             if data.get('act') and data.get('import'):
#                 cols.append(col)
#             if data.get('tracked'):
#                 cols.append(cls.mod_time_col(col))
#         return cols
#
#     @classmethod
#     def get_act_import_col_names(cls):
#         cols = OrderedDict()
#         for col, data in cls.data.items():
#             if data.get('act') and data.get('import'):
#                 cols[col] = col
#             if data.get('tracked'):
#                 mod_col = cls.mod_time_col(col)
#                 cols[mod_col] = mod_col
#         return cols
#
#     @classmethod
#     def get_tansync_defaults_recursive(cls, col, export_cols=None, data=None):
#         if data is None:
#             data = {}
#         if export_cols is None:
#             export_cols = OrderedDict()
#
#         new_data = {}
#         if data.get('sync'):
#             sync_data = data.get('sync')
#             if sync_data == 'master_override':
#                 new_data['sync_ingress'] = 1
#                 new_data['sync_egress'] = 0
#             elif sync_data == 'slave_override':
#                 new_data['sync_ingress'] = 0
#                 new_data['sync_egress'] = 1
#             else:
#                 new_data['sync_egress'] = 1
#                 new_data['sync_ingress'] = 1
#             new_data['sync_label'] = col
# #
# #         if data.get('visible'):
# #             new_data['profile_display'] = 1
# #         if data.get('mutable'):
# #             new_data['profile_modify'] = 1
# #         if data.get('contact'):
# #             new_data['contact_method'] = 1
# #
# #         if new_data and data.get('wp'):
# #             wp_data = data['wp']
# #             if not wp_data.get('meta'):
# #                 new_data['core'] = 1
# #             if not wp_data.get('generated'):
# #                 assert wp_data.get('key'), "column %s must have key" % col
# #                 key = wp_data['key']
# #                 export_cols[key] = new_data
# #
# #         if data.get('aliases'):
# #             for alias in data['aliases']:
# #                 alias_data = cls.data.get(alias, {})
# #                 alias_data['sync'] = data.get('sync')
# #                 export_cols = cls.get_tansync_defaults_recursive(
# #                     alias, export_cols, alias_data)
# #
# #         return export_cols
# #
# #     @classmethod
# #     def get_tansync_defaults(cls):
# #         export_cols = OrderedDict()
# #         for col, data in cls.data.items():
# #             export_cols = cls.get_tansync_defaults_recursive(
# #                 col, export_cols, data)
# #         return export_cols
