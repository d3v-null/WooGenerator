# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals, print_function

import base64
import cgi
import functools
import json
import numbers
import re
from HTMLParser import HTMLParser
from urlparse import parse_qs, urlparse

import unidecode
from kitchen.text import converters
from six import binary_type, string_types, text_type

DEBUG_UTILS = False


class SanitationUtils(object):
    email_regex = r"[\w.+-]+@[\w-]+\.[\w.-]+"
    regex_url_simple = (r"https?:\/\/(?:www\.)?"
                        r"[-a-zA-Z0-9@:%._\+~#=]{2,256}\."
                        r"[a-z]{2,6}\b(?:[-a-zA-Z0-9@:%_\+.~#?&//=]*)")
    regex_domain_simple = (r"[-a-zA-Z0-9@:%._\+~#=]{2,256}\.[a-z]{2,6}")
    regex_url = (
        r'(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)'
        r'(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+'
        r'(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:\'".,<>?]))')
    regex_wc_link = r"<(?P<url>{0})>; rel=\"(?P<rel>\w+)\"".format(regex_url)
    cell_email_regex = r"^%s$" % email_regex
    myobid_regex = r"C\d+"
    punctuationChars = [
        r'!', r'"', r'\#', r'\$', r'%', r'&', r'\'', r'(', r')', r'\*', r'\+',
        r',', r'\-', r'\.', r'/', r':', r';', r'<', r'=', r'>', r'\?', r'@',
        r'\[', r'\\', r'\]', r'\^', r'_', r'`', r'\{', r'\|', r'\}', r'~'
    ]
    allowedPunctuation = [r'\-', r'\.', r'\'']
    allowedPhonePunctuation = [r'\-', r'\.', r'(', r')', r'\+']
    disallowedPunctuation = list(
        set(punctuationChars) - set(allowedPunctuation))
    whitespaceChars = [r' ', r'\t', r'\r', r'\n', 'r\f']
    # disallowed punctuation and whitespace
    disallowedPunctuationOrSpace = list(
        set(disallowedPunctuation + whitespaceChars))
    # delimeter characters incl whitespace and disallowed punc
    tokenDelimeters = list(
        set([r"\d"] + disallowedPunctuation + whitespaceChars))
    # delimeter characters including all punctuation and whitespace
    tokenPunctuationDelimeters = list(
        set([r"\d"] + punctuationChars + whitespaceChars))
    # delimeter characters excl space
    tokenDelimetersNoSpace = list(
        set(disallowedPunctuation + whitespaceChars + [r"\d"]) - set([' ']))
    punctuationRegex = r"[%s]" % "".join(punctuationChars)
    # delimeter characters incl space and disallowed punc
    delimeterRegex = r"[%s]" % "".join(tokenDelimeters)
    # disallowed punctuation and whitespace
    bad_punc_or_space_regex = r"[%s]" % "".join(disallowedPunctuationOrSpace)
    # disallowed punctuation
    disallowedPunctuationRegex = r"[%s]" % "".join(disallowedPunctuation)
    # not a delimeter (no whitespace or disallowed punc)
    nondelimeterRegex = r"[^%s]" % "".join(tokenDelimeters)
    # not a delimeter or punctuation (no punctuation or whitespace)
    nondelimeterPunctuationRegex = r"[^%s]" % "".join(
        tokenPunctuationDelimeters)
    # not a delimeter except space (no whitespace except space, no disallowed
    # punc)
    nondelimeterOrSpaceRegex = r"[^%s]" % "".join(tokenDelimetersNoSpace)
    disallowedPhoneCharRegex = r"[^%s]" % "".join(allowedPhonePunctuation +
                                                  [r'\d', r' '])
    clearStartRegex = r"(?<!%s)" % nondelimeterRegex
    clearFinishRegex = r"(?!%s)" % nondelimeterRegex
    currency_precision = 2

    @classmethod
    def wrap_clear_regex(cls, regex):
        return cls.clearStartRegex + regex + cls.clearFinishRegex

    @classmethod
    def identify_abbreviation(cls, abbrv_dict, string):
        for abbrv_key, abbrvs in abbrv_dict.items():
            if string in abbrvs + [abbrv_key]:
                return abbrv_key
        return string

    @classmethod
    def identify_abbreviations(cls, abbrv_dict, string):
        matches = re.findall('(' + cls.compile_abbrv_regex(abbrv_dict) + ')',
                             string)

        for candidate in [match for match in filter(None, matches)]:
            identified = cls.identify_abbreviation(abbrv_dict, candidate)
            if identified:
                yield identified

    @classmethod
    def compile_partial_abbrv_regex(cls, abbrv_key, abbrvs):
        return "|".join([abbrv for abbrv in abbrvs + [abbrv_key] if abbrv])

    @classmethod
    def compile_abbrv_regex(cls, abbrv):
        compiled_regex = [
            cls.compile_partial_abbrv_regex(abbrv_key, abbrv_value)
            for abbrv_key, abbrv_value in abbrv.items()
        ]
        return "|".join([compiled for compiled in compiled_regex if compiled])

    @classmethod
    def compose(cls, *functions):
        """
        Compose a list of functions into a single function.
        Stolen from: https://mathieularose.com/function-composition-in-python/
        """

        def compose2(func_f, func_g):
            return lambda x: func_f(func_g(x))

        return functools.reduce(compose2, functions)

    # Functions for dealing with string encodings

    @classmethod
    def identity(cls, thing):
        return thing

    @classmethod
    def assert_ascii(cls, string):
        for index, char in enumerate(string):
            assert ord(char) < 128, "char %s of string %s ... is not ascii" % (
                index, (string[:index - 1]))

    @classmethod
    def unicode_to_utf8(cls, u_str):
        assert isinstance(u_str, text_type),\
            "parameter should be text_type not %s" % type(u_str)
        byte_return = converters.to_bytes(u_str, "utf8")
        assert isinstance(byte_return, binary_type),\
            "something went wrong, should return str not %s" % type(
                byte_return)
        return byte_return

    @classmethod
    def unicode_to_ascii(cls, u_str):
        assert isinstance(u_str, text_type),\
            "parameter should be text_type not %s" % type(u_str)
        byte_return = converters.to_bytes(u_str, "ascii", "backslashreplace")
        assert isinstance(byte_return, binary_type),\
            "something went wrong, should return str not %s" % type(
                byte_return)
        return byte_return

    @classmethod
    def unicode_to_xml(cls, u_str, ascii_only=False):
        assert isinstance(u_str, text_type),\
            "parameter should be text_type not %s" % type(u_str)
        if ascii_only:
            byte_return = converters.unicode_to_xml(u_str, encoding="ascii")
        else:
            byte_return = converters.unicode_to_xml(u_str)
        return byte_return

    @classmethod
    def utf8_to_unicode(cls, utf8_str):
        assert isinstance(utf8_str, binary_type),\
            "parameter should be str not %s" % type(utf8_str)
        byte_return = converters.to_unicode(utf8_str, "utf8")
        assert isinstance(byte_return, text_type),\
            "something went wrong, should return text_type not %s" % type(
                byte_return)
        return byte_return

    @classmethod
    def xml_to_unicode(cls, utf8_str):
        byte_return = converters.xml_to_unicode(utf8_str)
        return byte_return

    @classmethod
    def ascii_to_unicode(cls, ascii_str):
        assert isinstance(ascii_str, binary_type),\
            "parameter should be str not %s" % type(ascii_str)
        # literal_eval("b'{}'".format(ascii_str)).decode('utf-8')
        # unicode_return = converters.to_unicode(ascii_str, "ascii")
        unicode_return = ascii_str.decode('unicode-escape')
        assert isinstance(unicode_return, text_type),\
            "something went wrong, should return text_type not %s" % type(
                unicode_return)
        return unicode_return

    @classmethod
    def coerce_unicode(cls, thing):
        if thing is None:
            unicode_return = u""
        else:
            unicode_return = converters.to_unicode(thing, encoding="utf8")
        assert isinstance(unicode_return, text_type),\
            "something went wrong, should return text_type not %s" % type(
                unicode_return)
        return unicode_return

    @classmethod
    def coerce_bytes(cls, thing):
        byte_return = cls.compose(cls.unicode_to_utf8,
                                  cls.coerce_unicode)(thing)
        assert isinstance(byte_return, binary_type),\
            "something went wrong, should return str not %s" % type(
                byte_return)
        return byte_return

    @classmethod
    def coerce_ascii(cls, thing):
        byte_return = cls.compose(cls.unicode_to_ascii,
                                  cls.coerce_unicode)(thing)
        assert isinstance(byte_return, binary_type),\
            "something went wrong, should return str not %s" % type(
                byte_return)
        return byte_return

    @classmethod
    def coerce_xml(cls, thing):
        byte_return = cls.compose(cls.coerce_unicode, cls.unicode_to_xml,
                                  cls.coerce_unicode)(thing)
        assert isinstance(byte_return, text_type),\
            "something went wrong, should return str not %s" % type(
                byte_return)
        return byte_return

    # @classmethod
    # def coerce_float(cls, thing):
    #     unicode_thing = cls.compose(cls.coerce_unicode)(thing)
    #     try:
    #         float_return = float(unicode_thing)
    #     except ValueError:
    #         float_return = 0.0
    #     assert isinstance(float_return, float),\
    #         "something went wrong, should return str not %s" % type(
    #             float_return)
    #     return float_return
    #
    # @classmethod
    # def coerce_int(cls, thing):
    #     unicode_thing = cls.compose(cls.coerce_unicode)(thing)
    #     try:
    #         int_return = int(unicode_thing)
    #     except ValueError:
    #         int_return = 0
    #     assert isinstance(int_return, int),\
    #         "something went wrong, should return str not %s" % type(
    #             int_return)
    #     return int_return

    @classmethod
    def yesno2bool(cls, string):
        return string.lower().startswith('y')

    @classmethod
    def bool2yesno(cls, bool_):
        return 'yes' if bool_ else 'no'

    @classmethod
    def stock_status2bool(cls, string):
        return string.lower() == 'instock'

    @classmethod
    def bool2stock_status(cls, bool_):
        return 'instock' if bool_ else 'outofstock'

    @classmethod
    def coerce_int(cls, thing, default=None):
        if any([
            thing is None,
            (isinstance(thing, string_types) and not thing)
        ]):
            return default
        return int(thing)

    @classmethod
    def coerce_float(cls, thing, default=None):
        if any([
            thing is None,
            (isinstance(thing, string_types) and not thing)
        ]):
            return default
        return float(thing)

    @classmethod
    def normalize_optional_int_minus_1(cls, thing):
        return cls.coerce_int(thing, -1)

    @classmethod
    def normalize_optional_int_zero(cls, thing):
        return cls.coerce_int(thing, 0)

    @classmethod
    def normalize_optional_int_none(cls, thing):
        return cls.coerce_int(thing)

    @classmethod
    def normalize_mandatory_int(cls, thing):
        if any([thing, isinstance(thing, numbers.Real)]):
            return cls.coerce_int(thing)
        raise UserWarning(
            "Int required, found %s <%s> instead" % (thing, type(thing)))

    @classmethod
    def normalize_optional_float_zero(cls, thing):
        return cls.coerce_float(thing, 0.0)

    @classmethod
    def normalize_optional_float_none(cls, thing):
        return cls.coerce_float(thing)

    @classmethod
    def limit_string(cls, length):
        return lambda x: x[:length]

    @classmethod
    def sanitize_for_table(cls, thing, tablefmt=None):
        if hasattr(thing, '_supports_tablefmt'):
            thing = thing.__unicode__(tablefmt)
        if isinstance(thing, (str, text_type)) and tablefmt == 'simple':
            thing = thing[:64] + '...'
        unicode_return = cls.compose(cls.coerce_unicode, cls.limit_string(50),
                                     cls.escape_newlines,
                                     cls.coerce_unicode)(thing)
        assert isinstance(unicode_return, text_type),\
            "something went wrong, should return text_type not %s" % type(
                unicode_return)
        return unicode_return

    @classmethod
    def sanitize_for_xml(cls, thing):
        unicode_return = cls.compose(cls.coerce_unicode, cls.sanitize_newlines,
                                     cls.unicode_to_xml,
                                     cls.coerce_unicode)(thing)
        assert isinstance(unicode_return, text_type),\
            "something went wrong, should return text_type not %s" % type(
                unicode_return)
        return unicode_return

    @classmethod
    def safe_print(cls, *args):
        print(" ".join([cls.coerce_ascii(arg) for arg in args]))

    @classmethod
    def normalize_val(cls, thing):
        unicode_return = cls.compose(
            cls.coerce_unicode, cls.to_upper, cls.strip_leading_whitespace,
            cls.strip_tailing_whitespace, cls.strip_extra_whitespace,
            cls.coerce_unicode)(thing)
        assert isinstance(unicode_return, text_type),\
            "something went wrong, should return text_type not %s" % type(
                unicode_return)
        return unicode_return

    @classmethod
    def remove_leading_dollar_wspace(cls, string):
        str_out = re.sub(r'^\W*\$', '', string)
        if DEBUG_UTILS:
            print("remove_leading_dollar_wspace", repr(string), repr(str_out))
        return str_out

    @classmethod
    def remove_leading_quote(cls, string):
        str_out = re.sub(r'^\'', '', string)
        if DEBUG_UTILS:
            print("remove_leading_quote", repr(string), repr(str_out))
        return str_out

    @classmethod
    def remove_leading_percent_wspace(cls, string):
        str_out = re.sub(r'%\W*$', '', string)
        if DEBUG_UTILS:
            print("remove_leading_percent_wspace", repr(string), repr(str_out))
        return str_out

    @classmethod
    def remove_lone_dashes(cls, string):
        str_out = re.sub(r'^-$', '', string)
        if DEBUG_UTILS:
            print("remove_lone_dashes", repr(string), repr(str_out))
        return str_out

    @classmethod
    def remove_thousands_separator(cls, string):
        str_out = re.sub(r'(\d+),(\d{3})', r'\g<1>\g<2>', string)
        if DEBUG_UTILS:
            print("remove_thousands_separator", repr(string), repr(str_out))
        return str_out

    @classmethod
    def remove_lone_white_space(cls, string):
        str_out = re.sub(r'^\s*$', '', string)
        if DEBUG_UTILS:
            print("remove_lone_white_space", repr(string), repr(str_out))
        return str_out

    @classmethod
    def remove_null(cls, string):
        str_out = re.sub(r'^NULL$', '', string)
        if DEBUG_UTILS:
            print("remove_null", repr(string), repr(str_out))
        return str_out

    @classmethod
    def strip_leading_whitespace(cls, string):
        if not isinstance(string, string_types):
            return string
        str_out = re.sub(r'^\s*', '', string)
        if DEBUG_UTILS:
            print("strip_leading_whitespace", repr(string), repr(str_out))
        return str_out

    @classmethod
    def strip_leading_newline(cls, string):
        if not isinstance(string, string_types):
            return string
        str_out = re.sub(r'^(\\n|\n)*', '', string)
        if DEBUG_UTILS:
            print("strip_leading_newline", repr(string), repr(str_out))
        return str_out

    @classmethod
    def strip_tailing_whitespace(cls, string):
        if not isinstance(string, string_types):
            return string
        str_out = re.sub(r'\s*$', '', string)
        if DEBUG_UTILS:
            print("strip_tailing_whitespace", repr(string), repr(str_out))
        return str_out

    @classmethod
    def strip_tailing_newline(cls, string):
        if not isinstance(string, string_types):
            return string
        str_out = re.sub(r'(\\n|\n)*$', '', string)
        if DEBUG_UTILS:
            print("strip_tailing_newline", repr(string), repr(str_out))
        return str_out

    @classmethod
    def strip_all_whitespace(cls, string):
        if not isinstance(string, string_types):
            return string
        str_out = re.sub(r'\s', '', string)
        if DEBUG_UTILS:
            print("strip_all_whitespace", repr(string), repr(str_out))
        return str_out

    @classmethod
    def strip_extra_whitespace(cls, string):
        if not isinstance(string, string_types):
            return string
        str_out = re.sub(r'\s{2,}', ' ', string)
        if DEBUG_UTILS:
            print("strip_extra_whitespace", repr(string), repr(str_out))
        return str_out

    @classmethod
    def strip_non_numbers(cls, string):
        if not isinstance(string, string_types):
            return string
        str_out = re.sub(r'[^\d]', '', string)
        if DEBUG_UTILS:
            print("strip_non_numbers", repr(string), repr(str_out))
        return str_out

    @classmethod
    def strip_non_phone_characters(cls, string):
        if not isinstance(string, string_types):
            return string
        str_out = re.sub(cls.disallowedPhoneCharRegex, '', string)
        return str_out

    @classmethod
    def strip_punctuation(cls, string):
        if not isinstance(string, string_types):
            return string
        str_out = re.sub(r'[%s]' % ''.join(cls.punctuationChars), '', string)
        if DEBUG_UTILS:
            print("strip_punctuation", repr(string), repr(str_out))
        return str_out

    @classmethod
    def strip_area_code(cls, string):
        if not isinstance(string, string_types):
            return string
        str_out = re.sub(r'\s*\+\d{2,3}\s*', '', string)
        if DEBUG_UTILS:
            print("strip_area_code", repr(string), repr(str_out))
        return str_out

    @classmethod
    def strip_url_protocol(cls, string):
        if not isinstance(string, string_types):
            return string
        str_out = re.sub(r"^\w+://", "", string)
        if DEBUG_UTILS:
            print("strip_url_protocol", repr(string), repr(str_out))
        return str_out

    @classmethod
    def strip_p_tags(cls, string):
        if not isinstance(string, string_types):
            return string
        str_out = re.sub(r"</?p[^>]*>", "", string)
        return str_out

    @classmethod
    def strip_br_tags(cls, string):
        if not isinstance(string, string_types):
            return string
        str_out = re.sub(r"</?\s*br\s*/?>", "", string)
        return str_out

    @classmethod
    def replace_br_tags(cls, string):
        if not isinstance(string, string_types):
            return string
        str_out = re.sub(r"</?\s*br\s*/?>", "\n", string)
        return str_out

    # @classmethod
    # def strip_url_scheme(cls, url):
    #     str_out = url
    #     result = urlparse(url)
    #     if result:
    #         if result.scheme:
    #             remove_str = '%s:' % result.scheme
    #             if str_out.startswith(remove_str):
    #                 str_out = str_out[len(remove_str):]
    #     if DEBUG_UTILS:
    #         print("strip_url_scheme", repr(url), repr(str_out))
    #     return str_out

    @classmethod
    def strip_url_host(cls, url):
        str_out = url
        result = urlparse(url)
        if result:
            if result.scheme:
                remove_str = '%s:' % result.scheme
                if str_out.startswith(remove_str):
                    str_out = str_out[len(remove_str):]
            if result.netloc:
                remove_str = '//%s' % result.netloc
                if str_out.startswith(remove_str):
                    str_out = str_out[len(remove_str):]

        if DEBUG_UTILS:
            print("strip_url_host", repr(url), repr(str_out))
        return str_out

    @classmethod
    def to_lower(cls, string):
        str_out = string.lower()
        if DEBUG_UTILS:
            print("to_lower", repr(string), repr(str_out))
        return str_out

    @classmethod
    def to_upper(cls, string):
        str_out = string.upper()
        if DEBUG_UTILS:
            print("to_upper", repr(string), repr(str_out))
        return str_out

    @classmethod
    def normalize_unicode(cls, string):
        return unidecode.unidecode(string)
        # return unicodedata.normalize('NFKD', string)

    @classmethod
    def sanitize_newlines(cls, string):
        return re.sub('\n', '</br>', string)

    @classmethod
    def escape_newlines(cls, string):
        return re.sub('\n', r'\\n', string)

    @classmethod
    def compile_regex(cls, subs):
        if subs:
            return re.compile(
                "(%s)" % '|'.join(filter(None, map(re.escape, subs))))
        return None

    @classmethod
    def sanitize_cell(cls, cell):
        return cls.compose(
            cls.remove_leading_dollar_wspace,
            cls.remove_leading_percent_wspace,
            cls.remove_lone_dashes,
            # cls.strip_extra_whitespace,
            # cls.strip_all_whitespace,
            cls.remove_thousands_separator,
            cls.remove_lone_white_space,
            cls.strip_leading_whitespace,
            cls.strip_tailing_whitespace,
            cls.sanitize_newlines,
            cls.strip_tailing_newline,
            cls.strip_leading_newline,
            cls.remove_null,
            cls.coerce_unicode,
        )(cell)

    @classmethod
    def sanitize_special_cell(cls, cell):
        return cls.compose(
            # cls.remove_leading_dollar_wspace,
            # cls.remove_leading_percent_wspace,
            # cls.remove_lone_dashes,
            # cls.strip_extra_whitespace,
            cls.remove_thousands_separator,
            cls.remove_lone_white_space,
            cls.strip_leading_whitespace,
            cls.strip_tailing_whitespace,
            cls.sanitize_newlines,
            cls.strip_tailing_newline,
            cls.strip_leading_newline,
            cls.remove_null,
            cls.coerce_unicode)(cell)

    @classmethod
    def sanitize_class(cls, string):
        return re.sub('[^a-z]', '', string.lower())

    @classmethod
    def slugify(cls, string):
        string = re.sub('[^a-z0-9 _]', '', string.lower())
        return re.sub(' ', '_', string)

    @classmethod
    def similar_comparison(cls, string):
        return cls.compose(cls.to_lower, cls.strip_leading_whitespace,
                           cls.strip_tailing_whitespace, cls.normalize_unicode,
                           cls.coerce_unicode)(string)

    @classmethod
    def similar_no_punc_cmp(cls, string):
        return cls.compose(
            cls.normalize_val,
            cls.strip_punctuation,
        )(string)

    @classmethod
    def similar_phone_comparison(cls, string):
        return cls.compose(
            cls.coerce_unicode, cls.coerce_int, cls.strip_non_numbers,
            cls.strip_area_code, cls.strip_extra_whitespace,
            cls.strip_non_phone_characters, cls.coerce_unicode)(string)

    @classmethod
    def similar_tru_str_comparison(cls, string):
        return cls.compose(cls.truish_string_to_bool,
                           cls.similar_comparison)(string)

    @classmethod
    def similar_url_comparison(cls, string):
        return cls.compose(cls.strip_url_protocol, cls.coerce_unicode)(string)

    @classmethod
    def similar_markup_comparison(cls, string):
        return cls.compose(cls.to_lower, cls.strip_leading_whitespace,
                           cls.strip_tailing_whitespace,
                           cls.strip_extra_whitespace, cls.strip_p_tags,
                           cls.strip_br_tags, cls.coerce_unicode)(string)

    @classmethod
    def similar_currency_comparison(cls, string):
        if string == '':
            return cls.coerce_unicode('')
        return cls.compose(
            cls.round_currency,
            cls.coerce_float,
            cls.remove_leading_dollar_wspace,
            # cls.remove_leading_quote,
            cls.coerce_unicode,
        )(string)

    @classmethod
    def denormalize_api_currency(cls, string):
        return cls.compose(
            cls.coerce_unicode,
            cls.similar_currency_comparison,
        )(string)

    @classmethod
    def make_safe_class(cls, string):
        return cls.compose(cls.strip_all_whitespace,
                           cls.strip_punctuation)(string)

    @classmethod
    def normalize_wp_rendered_content(cls, string):
        return cls.compose(
            # cls.strip_leading_whitespace,
            # cls.strip_tailing_whitespace,
            cls.strip_tailing_newline,
            cls.normalize_unicode,
            cls.xml_to_unicode,
            cls.strip_p_tags,
            cls.replace_br_tags,
            cls.coerce_unicode)(string)

    @classmethod
    def normalize_wp_raw_content(cls, string):
        return cls.compose(
            # cls.strip_leading_whitespace,
            # cls.strip_tailing_whitespace,
            # cls.strip_tailing_newline,
            # cls.xml_to_unicode,
            # cls.strip_p_tags,
            # cls.replace_br_tags,
            cls.coerce_unicode)(string)

    @classmethod
    def shorten(cls, reg, subs, str_in):
        # if(DEBUG_GEN):
        #     print("calling shorten")
        #     print(" | reg:", reg)
        #     print(" | subs:", subs)
        # print(" | str_i: ",str_in)
        if not all([reg, subs, str_in]):
            str_out = str_in
        else:
            str_out = reg.sub(lambda mo: subs[mo.string[mo.start():mo.end()]],
                              str_in)
        # if DEBUG_GEN:
        #     print(" | str_o: ",str_out)
        return str_out

    @classmethod
    def round_currency(cls, price):
        return ("%." + str(cls.currency_precision) + "f") % round(
            price, cls.currency_precision)

    @classmethod
    def html_unescape(cls, string):
        return HTMLParser().unescape(string)

    @classmethod
    def html_escape(cls, string):
        return cgi.escape(string)

    @classmethod
    def html_unescape_recursive(cls, things):
        if isinstance(things, list):
            return [cls.html_unescape_recursive(thing) for thing in things]
        if isinstance(things, (str, text_type)):
            return cls.html_unescape(cls.coerce_unicode(things))
        return things

    @classmethod
    def find_all_images(cls, instring):
        instring = cls.coerce_unicode(instring)
        return re.findall(r'\s*([^.|]*\.[^.|\s]*)(?:\s*|\s*)', instring)

    @classmethod
    def find_all_tokens(cls, instring, delim="|"):
        instring = cls.coerce_unicode(instring)
        escaped_delim = re.escape(delim)
        return re.findall(r'\s*(\b[^\s.%s]+\b)\s*' % escaped_delim, instring)

    @classmethod
    def find_all_dollars(cls, instring):
        instring = cls.coerce_unicode(instring)
        return re.findall(r"\s*\$([\d,]+\.?\d*)", instring)

    @classmethod
    def find_all_percent(cls, instring):
        instring = cls.coerce_unicode(instring)
        return re.findall(r"\s*(\d+\.?\d*)%", instring)

    @classmethod
    def find_all_emails(cls, instring):
        instring = cls.coerce_unicode(instring)
        return re.findall(cls.wrap_clear_regex(cls.email_regex), instring)

    @classmethod
    def find_all_urls(cls, instring):
        instring = cls.coerce_unicode(instring)
        instring = cls.html_unescape(instring)
        return re.findall('(' + cls.regex_url_simple + ')', instring)

    @classmethod
    def find_all_domains(cls, instring):
        instring = cls.coerce_unicode(instring)
        instring = cls.html_unescape(instring)
        return re.findall('(' + cls.regex_domain_simple + ')', instring)

    # @classmethod
    # def findall_wp_links(cls, string):
    #     # TODO: implement
    #     return []

    @classmethod
    def findall_wc_links(cls, string):
        """Finds all wc style link occurences in a given string"""
        matches = []
        lines = string.split(', ')
        print(lines)
        for line in lines:
            print('processing line', line)
            print('attempting match on %s' % cls.regex_wc_link)
            match = re.match(cls.regex_wc_link, line)
            print("match", match)
            if match is None:
                print("match is none")
                continue
            else:
                print("match is none")
            match_dict = match.groupdict()
            if 'url' in match_dict and 'rel' in match_dict:
                matches.append(match_dict)
        print('returning matches', matches)
        return matches

    @classmethod
    def findall_url_params(cls, url):
        result = urlparse(url)
        if result and result.query:
            return parse_qs(result.query)
        return {}

    @classmethod
    def title_splitter(cls, instring):
        assert isinstance(instring, (str, text_type)), \
            "param must be a string not %s" % type(instring)
        if not isinstance(instring, text_type):
            instring = instring.decode('utf-8')
        found = re.findall(r"^\s*(.*?)\s+[^\s\w&\(\)]\s+(.*?)\s*$", instring)
        if found:
            return found[0]
        return instring, ""

    @classmethod
    def string_is_email(cls, email):
        return re.match(cls.email_regex, email)

    @classmethod
    def string_is_myobid(cls, card):
        return re.match(cls.myobid_regex, card)

    @classmethod
    def string_capitalized(cls, string):
        return text_type(string) == text_type(string).upper()

    @classmethod
    def string_contains_numbers(cls, string):
        return bool(re.search(r'\d', string))

    @classmethod
    def string_contains_no_numbers(cls, string):
        return not cls.string_contains_numbers(string)

    @classmethod
    def string_contains_delimeters(cls, string):
        return True if (re.search(cls.delimeterRegex, string)) else False

    @classmethod
    def string_contains_bad_punc(cls, string):
        return True if (re.search(cls.disallowedPunctuationRegex,
                                  string)) else False

    @classmethod
    def string_contains_punctuation(cls, string):
        return True if (re.search(cls.punctuationRegex, string)) else False

    @classmethod
    def truish_string_to_bool(cls, string):
        if not string or 'n' in string or 'false' in string \
                or string == '0' or string == 0:
            if DEBUG_UTILS:
                print("truish_string_to_bool", repr(string), 'FALSE')
            return "FALSE"
        if DEBUG_UTILS:
            print("truish_string_to_bool", repr(string), 'TRUE')
        return "TRUE"

    @classmethod
    def bool_to_truish_string(cls, bool_val):
        if bool_val:
            return "TRUE"
        return "FALSE"

    @classmethod
    def decode_json(cls, json_str, **kwargs):
        assert isinstance(json_str, (str, text_type))
        attrs = json.loads(json_str, **kwargs)
        return attrs

    @classmethod
    def encode_json(cls, obj, **kwargs):
        assert isinstance(obj, (dict, list))
        json_str = json.dumps(obj, **kwargs)
        return json_str

    @classmethod
    def encode_base64(cls, string):
        utf8_str = cls.coerce_bytes(string)
        return base64.standard_b64encode(utf8_str)

    @classmethod
    def decode_base64(cls, b64_str):
        return base64.standard_b64decode(b64_str)
