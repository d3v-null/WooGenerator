# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function
from builtins import super

import itertools
import math
import os
import random
import re
import sys
import time
from collections import OrderedDict

import phpserialize
import unicodecsv
from jsonpath_ng import jsonpath
from six import text_type, string_types

from .sanitation import SanitationUtils

DEFAULT_ENCODING = 'utf8'


class DescriptorUtils(object):
    class DescriptorPropertySafe(property):
        """property which can be safely accessed."""

        pass

    class DescriptorPropertySafeNormalized(property):
        """Normalized property which can be safely accessed."""

        pass

    class DescriptorPropertyKwargAlias(property):
        """Kwarg Alias style property."""

        pass

    @classmethod
    def safe_key_property(cls, key):
        def getter(self):
            return self.get(key)

        def setter(self, value):
            self[key] = value

        return cls.DescriptorPropertySafe(getter, setter)

    @classmethod
    def safe_normalized_key_property(cls, key):
        def getter(self):
            assert key in self.keys(
            ), "{} must be set before get in {}".format(key, repr(type(self)))
            return SanitationUtils.normalize_val(self[key])

        def setter(self, value):
            assert isinstance(
                value,
                string_types), "{} must be set with string not {}".format(
                    key, type(value))
            self[key] = value

        return cls.DescriptorPropertySafeNormalized(getter, setter)

    @classmethod
    def kwarg_alias_property(cls, key, handler):
        def getter(self):
            if self.properties_override:
                retval = handler(self)
            else:
                retval = self.kwargs.get(key)
            # print "getting ", key, "->", retval
            return retval

        def setter(self, value):
            # print "setting ", key, '<-', value
            self.kwargs[key] = value
            self.process_kwargs()

        return cls.DescriptorPropertyKwargAlias(getter, setter)


class SeqUtils(object):
    """
    Utilities for manipulating sequences like lists and dicts
    """

    @classmethod
    def combine_two_lists(cls, list_a, list_b):
        """
        Combine lists a and b uniquely, attempting to preserve order.
        """
        if not list_a:
            return list_b if list_b else []
        if not list_b:
            return list_a
        response = []
        for element in list_a + list_b:
            if element not in response:
                response.append(element)
        return response

    @classmethod
    def subtrace_two_lists(cls, list_a, list_b):
        """
        Return elements in list_a that are not in list_b.
        Attempt to preserve order
        """
        response = []
        for element in list_a:
            if element not in list_b:
                response.append(element)
        return response

    @classmethod
    def combine_lists(cls, *args):
        """
        Combine all argument lists uniquely, attempt to preserve order
        """
        response = []
        for arg in args:
            response = cls.combine_two_lists(response, arg)
        return response

    @classmethod
    def combine_two_ordered_dicts(cls, dict_a, dict_b):
        """
        Combine two ordered dicts, preserving order.

        Combine OrderedDict a with b by starting with A and overwriting with
        items from b.
        """
        if not dict_a:
            return dict_b if dict_b else OrderedDict()
        if not dict_b:
            return dict_a
        response = OrderedDict(dict_a.items())
        response.update(dict_b)
        # for key, value in dict_b.items():
        #     response[key] = value
        return response

    @classmethod
    def combine_ordered_dicts(cls, *args):
        """
        Combine all dict arguments overwriting former with items from latter.
        Attempt to preserve order
        """
        response = OrderedDict()
        for arg in args:
            response = cls.combine_two_ordered_dicts(response, arg)
        return response

    @classmethod
    def filter_unique_true(cls, list_a):
        response = []
        for i in list_a:
            if i and i not in response:
                response.append(i)
        return response

    @classmethod
    def get_all_keys(cls, *args):
        return SeqUtils.filter_unique_true(
            itertools.chain(*(arg.keys()
                              for arg in args if isinstance(arg, dict))))

    @classmethod
    def keys_not_in(cls, dictionary, keys):
        assert isinstance(dictionary, dict)
        return type(dictionary)([(key, value)
                                 for key, value in dictionary.items()
                                 if key not in keys])

    @classmethod
    def check_equal(cls, iterator):
        """
        Check that all items in an iterator are equal.

        Taken from SO answer:
        http://stackoverflow.com/questions/3844801/check-if-all-elements-in-a-list-are-identical
        """

        iterator = iter(iterator)
        try:
            first = next(iterator)
        except StopIteration:
            return True
        return all(first == rest for rest in iterator)


class JSONPathUtils(object):
    re_simple_path = r'^[A-Za-z0-9_-]+$'

    class NonSingularPathError(UserWarning):
        pass

    @classmethod
    def split_subpath(cls, path):
        path_components = path.split('.', 1)
        path_head, path_tail = path_components[0], ''
        if len(path_components) > 1:
            path_tail = path_components[1]
        return path_head, path_tail

    @classmethod
    def is_simple_path(cls, path):
        return re.match(cls.re_simple_path, path)

    @classmethod
    def quote_jsonpath(cls, path):
        if ' ' in path or ':' in path and not re.match(r"^([\"']).*\1$", path):
            return "\"%s\"" % path
        return path

    @classmethod
    def blank_get_field_datum(cls, path, datum, field):
        """
        Emulate jsonpath.Fields.get_field_datum but create the field in path
        if it does not exist.
        """
        try:
            field_value = datum.value[field]
        except (TypeError, KeyError, AttributeError):
            # differs from jsonpath.Fields.get_field_datum here:
            datum.value[field] = {}
            field_value = datum.value[field]
        return jsonpath.DatumInContext(
            value=field_value, path=jsonpath.Fields(field), context=datum)

    @classmethod
    def blank_reified_fields(cls, path, datum):
        """
        Emulate jsonpath.Fields.reified_fields but throw an exception if the
        path is nonsingular.
        """
        if '*' not in path.fields:
            return path.fields
        # differs from jsonpath.Fields.reified_fields here:
        raise cls.NonSingularPathError("'*' in path not supported")

    @classmethod
    def blank_find(cls, path, datum):
        """
        Emulate jsonpath.JSONPath.reified_fields but throw an exception if the
        path is nonsingular.
        """
        if isinstance(path, jsonpath.Child):
            return [
                submatch for subdata in cls.blank_find(path.left, datum)
                for submatch in cls.blank_find(path.right, subdata)
            ]
        if isinstance(path, jsonpath.Fields):
            datum = jsonpath.DatumInContext.wrap(datum)

            return [
                field_datum for field_datum in [
                    cls.blank_get_field_datum(path, datum, field)
                    for field in cls.blank_reified_fields(path, datum)
                ] if field_datum is not None
            ]
        return None

    @classmethod
    def blank_update(cls, path, data, val):
        """
        Emulate JSONPath.update but create a path for the data if it doesn't
        exist and throw an exception if the path is nonsingular.
        Assume path looks somthing like this:
        c -- c -- f
          \- f \- f
        """

        if isinstance(path, jsonpath.Child):
            for datum in cls.blank_find(path.left, data):
                cls.blank_update(path.right, datum.value, val)
            return data
        if isinstance(path, jsonpath.Fields):
            for field in cls.blank_reified_fields(path, data):
                if field in data and hasattr(val, '__call__'):
                    val(data[field], data, field)
                    continue
                data[field] = val
            return data
        if isinstance(path, jsonpath.JSONPath):
            raise cls.NonSingularPathError(
                "path is not made of singular jsonpath objects")
        return None


class ValidationUtils(object):
    @staticmethod
    def is_not_none(arg):
        return arg is not None

    @staticmethod
    def is_contained_in(a_list):
        return lambda v: v in a_list


def uniqid(prefix='', more_entropy=False):
    """uniqid([prefix=''[, more_entropy=False]]) -> str
    Gets a prefixed unique identifier based on the current
    time in microseconds.
    prefix
        Can be useful, for instance, if you generate identifiers
        simultaneously on several hosts that might happen to generate
        the identifier at the same microsecond.
        With an empty prefix, the returned string will be 13 characters
        long. If more_entropy is True, it will be 23 characters.
    more_entropy
        If set to True, uniqid() will add additional entropy (using
        the combined linear congruential generator) at the end of
        the return value, which increases the likelihood that
        the result will be unique.
    Returns the unique identifier, as a string."""
    seed = time.time()
    sec = math.floor(seed)
    usec = math.floor(1000000 * (seed - sec))
    if more_entropy:
        lcg = random.random()
        the_uniqid = "%08x%05x%.8F" % (sec, usec, lcg * 10)
    else:
        the_uniqid = '%8x%05x' % (sec, usec)

    the_uniqid = prefix + the_uniqid
    return the_uniqid


class PHPUtils(object):
    @staticmethod
    def uniqid(prefix="", more_entropy=False):
        # raise DeprecationWarning('uniqid deprecated')
        return uniqid(prefix, more_entropy)

    @staticmethod
    def ruleset_uniqid():
        return PHPUtils.uniqid("set_")

    @staticmethod
    def serialize(thing):
        if thing:
            return phpserialize.dumps(thing)
        return None

    @staticmethod
    def unserialize(string):
        if string:
            return phpserialize.loads(string)
        return None

    @staticmethod
    def serialize_list(list_):
        if list_:
            return phpserialize.dumps(list_)
        return None

    @staticmethod
    def unserialize_list(string):
        if string:
            response = phpserialize.loads(string)
            if response:
                return response.values()
            return []
        return None

    @staticmethod
    def serialize_mapping(list_):
        if list_:
            return phpserialize.dumps(list_)
        return None

    @staticmethod
    def unserialize_mapping(string):
        if string:
            response = phpserialize.loads(string)
            if response:
                return response
            return {}
        return None


class MimeUtils(object):
    mime_data = {

        # Image formats
        'image/jpeg': {
            'extensions': ['.jpg', '.jpeg', '.jfif', '.jpe']
        },
        'image/gif': {
            'extensions': ['gif']
        },
        'image/png': {
            'extensions': ['.png', '.x-png']
        },
        'image/bmp': {
            'extensions': ['bmp']
        },
        'image/tiff': {
            'extensions': ['tif', 'tiff']
        },
        'image/ico': {
            'extensions': ['ico']
        },
        'image/jp2': {
            'extensions': ['.jp2', '.jpg2']
        },

        # Video formats
        'video/x-ms-asf': {
            'extensions': ['asf', 'asx']
        },
        'video/x-ms-wmv': {
            'extensions': ['wmv']
        },
        'video/x-ms-wmx': {
            'extensions': ['wmx']
        },
        'video/x-ms-wm': {
            'extensions': ['wm']
        },
        'video/avi': {
            'extensions': ['avi']
        },
        'video/divx': {
            'extensions': ['divx']
        },
        'video/x-flv': {
            'extensions': ['flv']
        },
        'video/quicktime': {
            'extensions': ['mov', 'qt']
        },
        'video/mpeg': {
            'extensions': ['mpeg', 'mpg', 'mpe']
        },
        'video/mp4': {
            'extensions': ['mp4', 'm4v']
        },
        'video/ogg': {
            'extensions': ['ogv']
        },
        'video/webm': {
            'extensions': ['webm']
        },
        'video/x-matroska': {
            'extensions': ['mkv']
        },

        # Text formats
        'text/plain': {
            'extensions': ['txt', 'asc', 'c', 'cc', 'h']
        },
        'text/csv': {
            'extensions': ['csv']
        },
        'text/tab-separated-values': {
            'extensions': ['tsv']
        },
        'text/calendar': {
            'extensions': ['ics']
        },
        'text/richtext': {
            'extensions': ['rtx']
        },
        'text/css': {
            'extensions': ['css']
        },
        'text/html': {
            'extensions': ['htm', 'html']
        },

        # Audio formats
        'audio/mpeg': {
            'extensions': ['mp3', 'm4a', 'm4b']
        },
        'audio/x-realaudio': {
            'extensions': ['ra', 'ram']
        },
        'audio/wav': {
            'extensions': ['wav']
        },
        'audio/ogg': {
            'extensions': ['ogg', 'oga']
        },
        'audio/midi': {
            'extensions': ['mid', 'midi']
        },
        'audio/x-ms-wma': {
            'extensions': ['wma']
        },
        'audio/x-ms-wax': {
            'extensions': ['wax']
        },
        'audio/x-matroska': {
            'extensions': ['mka']
        },

        # Misc application formats
        'application/rtf': {
            'extensions': ['rtf']
        },
        'application/javascript': {
            'extensions': ['js']
        },
        'application/pdf': {
            'extensions': ['pdf']
        },
        'application/x-shockwave-flash': {
            'extensions': ['swf']
        },
        'application/java': {
            'extensions': ['class']
        },
        'application/x-tar': {
            'extensions': ['tar']
        },
        'application/zip': {
            'extensions': ['zip']
        },
        'application/x-gzip': {
            'extensions': ['gz', 'gzip']
        },
        'application/rar': {
            'extensions': ['rar']
        },
        'application/x-7z-compressed': {
            'extensions': ['7z']
        },
        'application/x-msdownload': {
            'extensions': ['exe']
        },

        # MS Office formats
        'application/msword': {
            'extensions': ['doc']
        },
        'application/vnd.ms-powerpoint': {
            'extensions': ['pot', 'pps', 'ppt']
        },
        'application/vnd.ms-write': {
            'extensions': ['wri']
        },
        'application/vnd.ms-excel': {
            'extensions': ['xla', 'xls', 'xlt', 'xlw']
        },
        'application/vnd.ms-access': {
            'extensions': ['mdb']
        },
        'application/vnd.ms-project': {
            'extensions': ['mpp']
        },
        ('application/vnd.openxmlformats-officedocument.wordprocessingml'
         '.document'): {
            'extensions': ['docx']
        },
        'application/vnd.ms-word.document.macroEnabled.12': {
            'extensions': ['docm']
        },
        ('application/vnd.openxmlformats-officedocument.wordprocessingml'
         '.template'): {
            'extensions': ['dotx']
        },
        'application/vnd.ms-word.template.macroEnabled.12': {
            'extensions': ['dotm']
        },
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': {
            'extensions': ['xlsx']
        },
        'application/vnd.ms-excel.sheet.macroEnabled.12': {
            'extensions': ['xlsm']
        },
        'application/vnd.ms-excel.sheet.binary.macroEnabled.12': {
            'extensions': ['xlsb']
        },
        'application/vnd.openxmlformats-officedocument.spreadsheetml.template':
        {
            'extensions': ['xltx']
        },
        'application/vnd.ms-excel.template.macroEnabled.12': {
            'extensions': ['xltm']
        },
        'application/vnd.ms-excel.addin.macroEnabled.12': {
            'extensions': ['xlam']
        },
        ('application/vnd.openxmlformats-officedocument.presentationml'
         '.presentation'): {
            'extensions': ['pptx']
        },
        'application/vnd.ms-powerpoint.presentation.macroEnabled.12': {
            'extensions': ['pptm']
        },
        ('application/vnd.openxmlformats-officedocument.presentationml'
         '.slideshow'): {
            'extensions': ['ppsx']
        },
        'application/vnd.ms-powerpoint.slideshow.macroEnabled.12': {
            'extensions': ['ppsm']
        },
        ('application/vnd.openxmlformats-officedocument.presentationml'
         '.template'): {
            'extensions': ['potx']
        },
        'application/vnd.ms-powerpoint.template.macroEnabled.12': {
            'extensions': ['potm']
        },
        'application/vnd.ms-powerpoint.addin.macroEnabled.12': {
            'extensions': ['ppam']
        },
        'application/vnd.openxmlformats-officedocument.presentationml.slide': {
            'extensions': ['sldx']
        },
        'application/vnd.ms-powerpoint.slide.macroEnabled.12': {
            'extensions': ['sldm']
        },
        'application/onenote': {
            'extensions': ['onetoc', 'onetoc2', 'onetmp', 'onepkg']
        },

        # OpenOffice formats
        'application/vnd.oasis.opendocument.text': {
            'extensions': ['odt']
        },
        'application/vnd.oasis.opendocument.presentation': {
            'extensions': ['odp']
        },
        'application/vnd.oasis.opendocument.spreadsheet': {
            'extensions': ['ods']
        },
        'application/vnd.oasis.opendocument.graphics': {
            'extensions': ['odg']
        },
        'application/vnd.oasis.opendocument.chart': {
            'extensions': ['odc']
        },
        'application/vnd.oasis.opendocument.database': {
            'extensions': ['odb']
        },
        'application/vnd.oasis.opendocument.formula': {
            'extensions': ['odf']
        },

        # WordPerfect formats
        'application/wordperfect': {
            'extensions': ['wp', 'wpd']
        },

        # iWork formats
        'application/vnd.apple.keynote': {
            'extensions': ['key']
        },
        'application/vnd.apple.numbers': {
            'extensions': ['numbers']
        },
        'application/vnd.apple.pages': {
            'extensions': ['pages']
        },
    }

    @classmethod
    def validate_mime_type(cls, string):
        if not string:
            return None
        if string.lower() in cls.mime_data:
            return string.lower()
        return None

    @classmethod
    def get_ext_mime_type(cls, extension):
        for mime_type, data in cls.mime_data.items():
            extensions = data.get('extensions', [])
            if extension.lower() in extensions:
                return mime_type
        return None


class ProgressCounter(object):
    def __init__(self,
                 total,
                 print_threshold=1,
                 items_plural='items',
                 verb_past='processed'):
        self.total = total
        self.print_threshold = print_threshold
        self.last_print = time.time()
        self.first_print = self.last_print
        self.print_count = 0
        self.current_count = 0
        self.items_plural = items_plural
        self.verb_past = verb_past
        # self.memory_tracker = tracker.SummaryTracker()
        self.maybe_print_update(0, force=True)

    def maybe_print_update(self, count=None, force=False):
        if count is None:
            count = self.current_count
        else:
            self.current_count = count
        now = time.time()
        if force or now - self.last_print > self.print_threshold:
            # self.memory_tracker.print_diff()
            self.last_print = now
            percentage = 0
            if self.total > 0:
                percentage = 100 * count / self.total
            line = "(%3d%%) %10d of %10d %s %s" % (
                percentage, count, self.total, self.items_plural,
                self.verb_past)
            if 1 < percentage < 100:
                time_elapsed = self.last_print - self.first_print
                ratio = (float(self.total) / (count) - 1.0)
                time_remaining = float(time_elapsed) * ratio
                line += " | remaining: %4d seconds, %4d elapsed           " % (
                    int(time_remaining), int(time_elapsed))
            if self.print_count > 0:
                line = "\r%s\r" % line
            sys.stdout.write(line)
            sys.stdout.flush()
            self.print_count += 1
        if count == self.total - 1:
            print("\n")

    def increment_count(self, increment=1):
        self.current_count += increment

class InvisibleProgressCounter(ProgressCounter):
    """
    Fake progress counter that doesn't update anything
    """
    def __init__(self, *args, **kwargs):
        if not args:
            args = [0]
        super().__init__(*args, **kwargs)

    def maybe_print_update(self, *_, **__):
        pass


class UnicodeCsvDialectUtils(object):
    default_dialect = unicodecsv.excel

    class ActOut(unicodecsv.Dialect):
        delimiter = ','
        quoting = unicodecsv.QUOTE_ALL
        doublequote = True
        strict = False
        quotechar = "\""
        escapechar = None
        skipinitialspace = False
        lineterminator = '\r\n'

    class SublimeCsvTable(unicodecsv.Dialect):
        delimiter = ','
        quoting = unicodecsv.QUOTE_MINIMAL
        doublequote = True
        strict = False
        quotechar = "\""
        escapechar = None
        skipinitialspace = True
        lineterminator = '\n'

    @classmethod
    def get_dialect_from_suggestion(cls, suggestion):
        dialect = cls.default_dialect
        if hasattr(cls, suggestion):
            possible_dialect = getattr(cls, suggestion)
            if isinstance(possible_dialect, unicodecsv.Dialect):
                dialect = possible_dialect
        return dialect

    @classmethod
    def dialect_to_str(cls, dialect):
        out = "Dialect: %s" % dialect.__name__
        out += " | DEL: %s" % repr(dialect.delimiter)
        out += " | DBL: %s" % repr(dialect.doublequote)
        out += " | ESC: %s" % repr(dialect.escapechar)
        out += " | QUC: %s" % repr(dialect.quotechar)
        out += " | QUT: %s" % repr(dialect.quoting)
        out += " | SWS: %s" % repr(dialect.skipinitialspace)
        return out

    @classmethod
    def dialect_unicode_to_bytestr(cls, dialect):
        for attr in [
                'delimeter',
                'quotechar',
                'doublequote',
                'escapechar',
                'quotechar',
                'quoting',
        ]:
            if isinstance(getattr(dialect, attr), text_type):
                setattr(dialect, attr,
                        SanitationUtils.coerce_bytes(getattr(dialect, attr)))
        return dialect

    @classmethod
    def get_dialect_from_sample(cls, sample, suggestion):
        byte_sample = SanitationUtils.coerce_bytes(sample)
        csvdialect = unicodecsv.Sniffer().sniff(byte_sample)
        if not csvdialect:
            return cls.get_dialect_from_suggestion(suggestion)
        return csvdialect


class FileUtils(object):
    @classmethod
    def get_path_basename(cls, path):
        """
        Works on URIs too!
        """
        return os.path.basename(path)

    @classmethod
    def get_file_name(cls, path):
        file_name, _ = os.path.splitext(os.path.basename(path))
        return file_name
