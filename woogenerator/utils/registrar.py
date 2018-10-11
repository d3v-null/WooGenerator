# -*- coding: utf-8 -*-
from __future__ import absolute_import

import base64
import cgi
import functools
import inspect
import itertools
import json
import math
import numbers
import os
import random
import re
import sys
import time
import traceback
import unicodedata
from collections import Counter, OrderedDict
from HTMLParser import HTMLParser
from urlparse import parse_qs, urlparse

import phpserialize
import unicodecsv
import unidecode
from jsonpath_ng import jsonpath
from kitchen.text import converters
from six import binary_type, integer_types, string_types, text_type

from .sanitation import SanitationUtils
from .debug import DebugUtils


class Registrar(object):
    messages = OrderedDict()
    errors = OrderedDict()
    warnings = OrderedDict()
    stack_counts = OrderedDict()
    object_indexer = id
    DEBUG_ERROR = True
    DEBUG_WARN = True
    DEBUG_MESSAGE = False
    DEBUG_PROGRESS = True
    DEBUG_ABSTRACT = False
    DEBUG_ADDRESS = False
    DEBUG_API = False
    DEBUG_CATS = False
    DEBUG_CLIENT = False
    DEBUG_CONTACT = False
    DEBUG_DUPLICATES = False
    DEBUG_GDRIVE = False
    DEBUG_GEN = False
    DEBUG_IMG = False
    DEBUG_MRO = False
    DEBUG_MYO = False
    DEBUG_NAME = False
    DEBUG_PARSER = False
    DEBUG_ROLE = False
    DEBUG_SHOP = False
    DEBUG_SPECIAL = False
    DEBUG_TRACE = False
    DEBUG_TREE = False
    DEBUG_UPDATE = False
    DEBUG_USR = False
    DEBUG_UTILS = False
    DEBUG_VARS = False
    DEBUG_WOO = False
    master_name = None
    slave_name = None
    strict = False

    @classmethod
    def conflict_resolver(cls, *_):
        pass

    def resolve_conflict(self, new, _, index, register_name=''):
        if new:
            pass
        self.register_error(
            "Object [index: %s] already exists in register %s" % (index, register_name))

    @classmethod
    def get_object_rowcount(cls, object_data):
        if 'rowcount' in object_data:
            return object_data['rowcount']
        else:
            raise UserWarning('object does not have rowcount')

    @classmethod
    def get_object_index(cls, object_data):
        if hasattr(object_data, 'index'):
            return object_data.index
        else:
            raise UserWarning(
                '%s object is not indexable: does not have attr "index"' % (
                    type(object_data)
                )
            )

    @classmethod
    def get_object_identifier(cls, object_data):
        if hasattr(object_data, 'identifier'):
            return object_data.identifier
        else:
            raise UserWarning(
                '%s object is not identifiable: does not have attr "identifier"' % (
                    type(object_data)
                )
            )

    @classmethod
    def passive_resolver(cls, *args):
        pass

    @classmethod
    def exception_resolver(cls, new, _, index, register_name=''):
        raise Exception("could not register %s in %s. \nDuplicate index: %s" % (
            str(new), register_name, index))

    @classmethod
    def duplicate_obj_exc_resolver(cls, new, old, index, register_name=''):
        assert hasattr(
            new, 'rowcount'), 'new object type: %s should have a .rowcount attr' % type(new)
        assert hasattr(
            old, 'rowcount'), 'old object type: %s should have a .rowcount attr' % type(old)
        raise Exception(
            ("could not register %s in %s. \n"
             "Duplicate index: %s appears in rowcounts %s and %s"
             ) % (
                str(new), register_name, index, new.rowcount, old.rowcount
            )
        )

    def warning_resolver(self, new, old, index, register_name=''):
        try:
            self.exception_resolver(new, old, index, register_name)
        except Exception as exc:
            self.register_error(exc, new)

    @classmethod
    def string_anything(cls, index, thing, delimeter='|'):
        try:
            index = str(index)
        except:
            index = SanitationUtils.coerce_ascii(index)
        try:
            thing = str(thing)
        except:
            thing = SanitationUtils.coerce_ascii(thing)
        return u"%50s %s %s" % (index, delimeter, thing)

    @classmethod
    def print_anything(cls, index, thing, delimeter):
        print cls.string_anything(index, thing, delimeter)

    @classmethod
    def register_anything(cls, thing, register, indexer=None, resolver=None,
                          singular=True, unique=True, register_name='', container=None):
        if resolver is None:
            resolver = cls.conflict_resolver
        if indexer is None:
            indexer = cls.object_indexer
        if container is None:
            container = list
        index = None
        try:
            if callable(indexer):
                if cls.DEBUG_UTILS:
                    print "INDEXER IS CALLABLE"
                index = indexer(thing)
            else:
                if cls.DEBUG_UTILS:
                    print "INDEXER IS NOT CALLABLE"
                index = indexer
            assert hasattr(index, '__hash__'), "Index must be hashable"
            assert index == index, "index must support eq"
        except AssertionError as exc:
            name = thing.__name__ if hasattr(
                thing, '__name__') else repr(indexer)
            raise Exception("Indexer [%s] produced invalid index: %s | %s" % (
                name, repr(index), str(exc)))
        else:
            # if not register:
            #     register = OrderedDict()
            if singular:
                if index not in register:
                    register[index] = thing
                else:
                    resolver(thing, register[index], index, register_name)
            else:
                if index not in register:
                    register[index] = container()
                if not unique or thing not in register[index]:
                    register[index].append(thing)
        # print "registered", thing

    @classmethod
    def register_error(cls, error, source=None):
        if source:
            try:
                index = source.index
                assert not callable(index)
            except BaseException:
                index = source
        else:
            index = DebugUtils.get_caller_procedures()
        error_string = SanitationUtils.coerce_unicode(error)
        if cls.DEBUG_ERROR:
            Registrar.print_anything(index, "\n\n%s\n\n" % error_string, '!')
        cls.register_anything(
            error_string,
            Registrar.errors,
            index,
            singular=False,
            register_name='errors'
        )

    @classmethod
    def register_warning(cls, message, source=None):
        if source:
            try:
                index = source.index
                assert not callable(index)
            except BaseException:
                index = source
        else:
            index = DebugUtils.get_caller_procedures()
        error_string = SanitationUtils.coerce_unicode(message)
        if cls.DEBUG_WARN:
            Registrar.print_anything(index, "\n\n%s\n\n" % error_string, '|')
        cls.register_anything(
            error_string,
            Registrar.warnings,
            index,
            singular=False,
            register_name='warnings'
        )

    @classmethod
    def register_message(cls, message, source=None):
        if source is None:
            source = DebugUtils.get_caller_procedures()
        if cls.DEBUG_MESSAGE:
            Registrar.print_anything(source, message, '~')
        cls.register_anything(
            message,
            Registrar.messages,
            source,
            singular=False,
            register_name='messages'
        )

    @classmethod
    def register_progress(cls, message):
        if cls.DEBUG_PROGRESS:
            print DebugUtils.hashify(message)

    @classmethod
    def get_message_items(cls, verbosity=0):
        items = cls.errors
        if verbosity > 0:
            items = SeqUtils.combine_ordered_dicts(items, cls.warnings)
        if verbosity > 1:
            items = SeqUtils.combine_ordered_dicts(items, cls.messages)
        return items

    @classmethod
    def print_message_dict(cls, verbosity):
        items = cls.get_message_items(verbosity)
        for key, messages in items.items():
            for message in messages:
                cls.print_anything(key, message, '|')

    @classmethod
    def raise_exception(cls, exc):
        print('full_stack:')
        traceback.print_stack()
        _, _, traceback_ = sys.exc_info()
        traceback.print_exception(type(exc), exc, traceback_)
        if cls.DEBUG_TRACE:
            import pdb; pdb.post_mortem(traceback_)
        else:
            raise exc

    @classmethod
    def increment_stack_count(cls, name=''):
        if not name in cls.stack_counts:
            cls.stack_counts[name] = Counter()
        stack = ' -> '.join([
            line.strip().split('\n')[0] for line in list(reversed(traceback.format_stack()))[3:7]
        ])
        cls.stack_counts[name].update({stack: 1})

    @classmethod
    def display_stack_counts(cls):
        response = ''
        for stack_name, stack_counts in cls.stack_counts.items():
            response += (" -> %s\n" % stack_name)
            for caller, count in sorted(
                stack_counts.items(),
                cmp=(lambda x, y: int(y[1]).__cmp__(int(x[1])))
            ):
                response += ("  -> (%3d) %s\n" % (count, caller))
        return response
