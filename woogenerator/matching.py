"""
Utilities for matching lists of parsing.abstract.ImportObjects
"""

from __future__ import absolute_import, print_function

from collections import OrderedDict

from .parsing.abstract import ImportObject, ObjList
from .utils import InheritenceUtils, Registrar, SanitationUtils, SeqUtils

# TODO: convert matching to use core data


class Match(object):
    """A list of main objects and subordinate objects that match in sosme way."""

    def __init__(self, m_objects=None, s_objects=None):
        if m_objects is None:
            m_objects = []
        if s_objects is None:
            s_objects = []
        self._m_objects = filter(None, m_objects) or []
        self._s_objects = filter(None, s_objects) or []
        for _object in self._m_objects + self._s_objects:
            assert isinstance(_object, ImportObject)

    @property
    def m_objects(self):
        """
        return a list of main objects associated with match
        """
        return self._m_objects

    @property
    def m_object(self):
        """
        return the singular main object associated with match

        Raises:
            AssertionError: if m_objects is not singular
        """
        assert self.m_len == 1, \
            ".m_object assumes m_objects unique, instead it is %d long" % len(
                self._m_objects)
        return self._m_objects[0]

    @property
    def s_objects(self):
        """
        return a list of subordinate objects associated with match
        """
        return self._s_objects

    @property
    def s_object(self):
        """
        return the singular subordinate object associated with match

        Raises:
            AssertionError: if s_objects is not singular
        """
        assert self.s_len == 1, \
            ".s_object assumes s_objects unique, instead it is %d long" % len(
                self._s_objects)
        return self._s_objects[0]

    @property
    def s_len(self):
        """
        return the number of subordinate objects in the match
        """
        return len(self._s_objects)

    @property
    def m_len(self):
        """
        return the number of main objects in the match
        """
        return len(self._m_objects)

    @property
    def is_singular(self):
        """
        return true if there is less than one main and subordinate in the match
        """
        return self.m_len <= 1 and self.s_len <= 1

    @property
    def has_no_main(self):
        """
        return true if the match is mainless
        """
        return self.m_len == 0

    @property
    def has_no_subordinate(self):
        """
        return true if the match is subordinateless
        """
        return self.s_len == 0

    @property
    def type(self):
        """
        return the match type of the match
        """
        if self.is_singular:
            if self.has_no_main:
                if not self.has_no_subordinate:
                    return 'mainless'
                return 'empty'
            elif self.has_no_subordinate:
                return 'subordinateless'
            return 'pure'
        return 'duplicate'

    @property
    def gcs(self):
        """
        Return the Greatest Common Subset of classes of the main and subordinate
        objects in the match
        """
        if self.m_len or self.s_len:
            return InheritenceUtils.gcs(*(self.m_objects + self.s_objects))
        return None

    def add_s_object(self, s_object):
        """
        add a subordinate object to the match
        """
        if s_object not in self.s_objects:
            self.s_objects.append(s_object)

    def add_m_object(self, m_object):
        """
        add a main object to the match
        """
        if m_object not in self.m_objects:
            self.m_objects.append(m_object)

    def consume(self, other):
        """
        Consume another match object
        """
        for m_object in other.m_objects:
            self.add_m_object(m_object)

        for s_object in other.s_objects:
            self.add_s_object(s_object)

    def find_key_matches(self, key_fn):
        """
        Split this match into smaller matches based on the results of applying
        key_fn to the objects in this match

        Arguments:
            key_fn (function):
                takes a parsing.abstract.ImportObject and returns a key used
                for mapping

        Returns:
            A dictionary of Match objects sorted by the output of key_fn
        """

        k_matches = {}
        for s_object in self.s_objects:
            value = key_fn(s_object)
            if not value in k_matches.keys():
                k_matches[value] = Match()
            k_matches[value].add_s_object(s_object)
            # for m_object in self.m_objects:
            #     if key_fn(m_object) == value:
            #         kMatches[value].add_m_object(m_object)
        for m_object in self.m_objects:
            value = key_fn(m_object)
            if not value in k_matches.keys():
                k_matches[value] = Match()
            k_matches[value].add_m_object(m_object)
        return k_matches

    @classmethod
    def woo_obj_list_repr(cls, objs):
        """
        Return a representation of objs suitable for woo_obj_list
        """
        length = len(objs)
        return "({0}) [{1:^100s}]".format(
            len(objs),
            ','.join([obj.__repr__()[:200 / length] for obj in objs]))
        # ",".join(map(lambda obj: obj.__repr__()[:200 / length], objs)))

    def __repr__(self):
        return " | ".join([
            self.woo_obj_list_repr(self.m_objects),
            self.woo_obj_list_repr(self.s_objects)
        ])

    @property
    def singular_index(self):
        return " | ".join([str(self.m_object.index), str(self.s_object.index)])

    def containerize(self, print_headings=False):
        """
        Return the objects within the match wrapped in the best possible container
        determined by the container attribute of the gcs of their classes
        """
        assert self.m_len or self.s_len, \
            "match must contain m_objects or s_objects to be containerized"

        obj_container = None

        gcs = self.gcs
        if gcs is not None and hasattr(gcs, 'container'):
            obj_container = gcs.container(
                indexer=(lambda import_object: import_object.identifier))
        else:
            obj_container = ObjList(
                indexer=(lambda import_object: import_object.identifier))

        # TODO: fix for product objects.

        if self.m_objects:
            mobjs = self.m_objects[:]
            if print_headings:
                heading = gcs({}, rowcount='M')
                # heading = ImportObject({}, rowcount='M')
                mobjs = [heading] + mobjs
            for mobj in mobjs:
                obj_container.append(mobj)
        if self.s_objects:
            sobjs = self.s_objects[:]
            if print_headings:
                heading = gcs({}, rowcount='S')
                # heading = ImportObject({}, rowcount='S')
                sobjs = [heading] + sobjs
            for sobj in sobjs:
                # pprint(sobj)
                obj_container.append(sobj)
        return obj_container

    def tabulate(self, cols=None, tablefmt=None, highlight_rules=None):
        """
        Returns a string that contains a representation of the match in the
        table format specified
        """
        out = ""

        obj_container = self.containerize()
        if obj_container:
            try:
                out += obj_container.tabulate(
                    cols=cols,
                    tablefmt=tablefmt,
                    highlight_rules=highlight_rules)
            except TypeError as exc:
                print("obj_container could not tabulate: %s " % type(
                    obj_container))
                raise exc
            except AssertionError as exc:
                print("could not tabulate\nm_objects:%s\ns_objects:%s" % (
                    self.m_objects, self.s_objects))
                raise exc
        else:
            out += 'EMPTY'
        # return SanitationUtils.coerce_unicode(out)
        return out


def find_card_matches(match):
    """
    find within the match, matches on an objects card
    """
    return match.find_key_matches(lambda obj: obj.MYOBID or '')


def find_p_code_matches(match):
    """
    find within the match, matches based on an objects postcode
    """
    return match.find_key_matches(
        lambda obj: obj.get('Postcode') or obj.get('Home Postcode') or '')


class MatchList(list):
    """ A sequence of Match objects indexed by an index_fn"""

    check_indices = True

    def __init__(self, matches=None, index_fn=None):
        super(MatchList, self).__init__()
        if index_fn:
            self._index_fn = index_fn
        else:
            self._index_fn = (lambda import_object: import_object.index)
        self._s_indices = []
        self._m_indices = []
        if matches:
            for match in matches:
                assert isinstance(match, Match)
                self.add_match(match)

    @property
    def s_indices(self):
        """
        Return the list of subordinate indices in all of the matches
        """
        return self._s_indices

    @property
    def m_indices(self):
        """
        Return the list of main indices in all of the matches
        """
        return self._m_indices

    def add_match(self, match):
        """
        Adds a match to the list
        """
        match_s_indices = []
        match_m_indices = []
        for s_object in match.s_objects:
            s_index = self._index_fn(s_object)
            assert \
                s_index not in self.s_indices, \
                ("can't add match s_object %s : s_index %s already in s_indices: %s \n"
                 "%s \n all matches: \n%s ;\n probably ambiguous category names") % \
                (
                    str(s_object), str(s_index), str(self.s_indices), str(
                        match), str('\n'.join(map(str, self)))
                )
            match_s_indices.append(s_index)
        if match_s_indices:
            if self.check_indices:
                assert SeqUtils.check_equal(
                    match_s_indices
                ), "all s_indices should be equal: %s" % match_s_indices
            self.s_indices.append(match_s_indices[0])
        for m_object in match.m_objects:
            # Registrar.register_message('indexing main %s with %s : %s' \
            # % (s_object, repr(self._index_fn), s_index))
            m_index = self._index_fn(m_object)
            assert \
                m_index not in self.m_indices, \
                ("can't add match m_object %s : m_index %s already in m_indices: %s \n"
                 "%s \n all matches: %s") % \
                (
                    str(m_object), str(m_index), str(self.m_indices), str(
                        match), str('\n'.join(map(str, self)))
                )
            match_m_indices.append(m_index)
        if match_m_indices:
            if self.check_indices:
                assert SeqUtils.check_equal(
                    match_m_indices
                ), "all m_indices should be equal: %s" % match_m_indices
            self.m_indices.append(match_m_indices[0])
        self.append(match)

    def add_matches(self, matches):
        """
        Add a sequence of matches to the matches
        """
        for match in matches:
            self.add_match(match)

    def merge(self):
        """
        Combine the matches into a single Match object
        """
        m_objects = []
        s_objects = []
        for match in self:
            for m_obj in match.m_objects:
                m_objects.append(m_obj)
            for s_obj in match.s_objects:
                s_objects.append(s_obj)

        return Match(m_objects, s_objects)

    def tabulate(self, cols=None, tablefmt=None, highlight_rules=None):
        """
        Returns a string that contains a representation of the match in the
        table format specified
        """
        if not self:
            return ""

        prefix, suffix = "", ""
        delimeter = "\n"
        if tablefmt == 'html':
            delimeter = ''
            prefix = '<div class="matchList">'
            suffix = '</div>'
        return prefix + delimeter.join([
            SanitationUtils.coerce_bytes(
                match.tabulate(
                    cols=cols,
                    tablefmt=tablefmt,
                    highlight_rules=highlight_rules))
            for match in self if match
        ]) + suffix


class ConflictingMatchList(MatchList):
    """
    A MatchList that does not checks indices when adding a match
    """
    # TODO: what is this useful for?
    check_indices = False


class AbstractMatcher(Registrar):
    """
    Abstract class that performs matching operations on a given type of ImportObject
    """

    def __init__(self, index_fn=None):
        super(AbstractMatcher, self).__init__()
        if index_fn:
            self.index_fn = index_fn
        else:
            self.index_fn = (lambda import_object: import_object.index)
        self.process_registers = self.process_registers_nonsingular
        # self.retrieveObjects = self.retrieveObjectsNonsingular
        self.m_filter_fn = None
        self.f_filter_fn = None
        self.clear()

    def clear(self):
        """
        Initialize the matcher
        """
        self._matches = {
            'all': MatchList(index_fn=self.index_fn),
            'pure': MatchList(index_fn=self.index_fn),
            'subordinateless': MatchList(index_fn=self.index_fn),
            'mainless': MatchList(index_fn=self.index_fn),
            'duplicate': MatchList(index_fn=self.index_fn)
        }

    @property
    def matches(self):
        """return all match lists."""
        return self._matches['all']

    @property
    def pure_matches(self):
        """return all matches that contain no more than one subordinate or main."""
        return self._matches['pure']

    @property
    def subordinateless_matches(self):
        """return all matches that contain no subordinates."""
        return self._matches['subordinateless']

    @property
    def mainless_matches(self):
        """return all matches that contain no mains."""
        return self._matches['mainless']

    @property
    def duplicate_matches(self):
        """return all matches that contain more than one main or subordinate."""
        return self._matches['duplicate']

    # sa_register is in nonsingular form. regkey => [subordinateObjects]
    def process_registers_nonsingular(self, sa_register, ma_register):
        """
        Groups items in both registers by the result of applying the index function when
        both are nonsingular

        It's messy because we can't assume that our index_fn is the same as the
        index_fn of the register :(

        """
        # TODO: optimize register processing
        ms_indexed = OrderedDict()
        for reg_values in ma_register.values():
            for reg_value in reg_values:
                reg_index = self.index_fn(reg_value)
                if not reg_index in ms_indexed:
                    ms_indexed[reg_index] = ([], [])
                ms_indexed[reg_index][0].append(reg_value)

        for reg_values in sa_register.values():
            for reg_value in reg_values:
                reg_index = self.index_fn(reg_value)
                if not reg_index in ms_indexed:
                    ms_indexed[reg_index] = ([], [])
                ms_indexed[reg_index][1].append(reg_value)

        for ms_values in ms_indexed.values():
            self.process_match(ms_values[0], ms_values[1])

    def process_registers_singular(self, sa_register, ma_register):
        """
        Groups items in both registers by the result of applying the index function when
        both are singular

        again, complicated because can't assume we have the same index_fn as the registers
        """
        # TODO: optimize register processing

        ms_indexed = OrderedDict()
        for reg_value in ma_register.values():
            reg_index = self.index_fn(reg_value)
            if not reg_index in ms_indexed:
                ms_indexed[reg_index] = ([], [])
            ms_indexed[reg_index][0].append(reg_value)

        for reg_value in sa_register.values():
            reg_index = self.index_fn(reg_value)
            if not reg_index in ms_indexed:
                ms_indexed[reg_index] = ([], [])
            ms_indexed[reg_index][1].append(reg_value)

        for ms_values in ms_indexed.values():
            self.process_match(ms_values[0], ms_values[1])

    def process_registers_singular_ns(self, sa_register, ma_register):
        """Main is nonsingular, subordinate is singular."""
        ms_indexed = OrderedDict()
        for reg_values in ma_register.values():
            for reg_value in reg_values:
                reg_index = self.index_fn(reg_value)
                if not reg_index in ms_indexed:
                    ms_indexed[reg_index] = ([], [])
                ms_indexed[reg_index][0].append(reg_value)

        for reg_value in sa_register.values():
            reg_index = self.index_fn(reg_value)
            if not reg_index in ms_indexed:
                ms_indexed[reg_index] = ([], [])
            ms_indexed[reg_index][1].append(reg_value)

        for ms_values in ms_indexed.values():
            self.process_match(ms_values[0], ms_values[1])

    def process_registers_ns_singular(self, sa_register, ma_register):
        """Main is singular, subordinate is nonsingular."""

        ms_indexed = OrderedDict()
        for reg_value in ma_register.values():
            reg_index = self.index_fn(reg_value)
            if not reg_index in ms_indexed:
                ms_indexed[reg_index] = ([], [])
            ms_indexed[reg_index][0].append(reg_value)

        for reg_values in sa_register.values():
            for reg_value in reg_values:
                reg_index = self.index_fn(reg_value)
                if not reg_index in ms_indexed:
                    ms_indexed[reg_index] = ([], [])
                ms_indexed[reg_index][1].append(reg_value)

        for ms_values in ms_indexed.values():
            self.process_match(ms_values[0], ms_values[1])

    @classmethod
    def get_match_type(cls, match):
        """Return the type of a given match."""
        return match.type

    def add_match(self, match, match_type):
        """Add a match to the instances correct match list."""
        self._matches[match_type].add_match(match)
        # try:
        # except Exception as exc:
        # finally:
        # pass
        # self.register_warning( "could not add match to %s matches %s" % (
        #     match_type,
        #     SanitationUtils.coerce_unicode(repr(exc))
        # ))
        # raise exc
        self._matches['all'].add_match(match)
        # try:
        # except Exception as exc:
        # finally:

    # pass
    # self.register_warning( "could not add match to matches %s" % (
    #     SanitationUtils.coerce_unicode(repr(exc))
    # ))

    def m_filter(self, objects):
        """perform the main filter on the objects."""
        if self.m_filter_fn:
            return filter(self.m_filter_fn, objects)
        return objects

    def s_filter(self, objects):
        """perform the subordinate filter on the objects."""
        if self.f_filter_fn:
            return filter(self.f_filter_fn, objects)
        return objects

    def process_match(self, ma_objects, sa_objects):
        """
        Process a list of main and subordinate objects as if they were from a match
        """
        # print "processing match %s | %s" % (repr(ma_objects),
        # repr(sa_objects))
        ma_objects = self.m_filter(ma_objects)
        for ma_object in ma_objects:
            assert \
                issubclass(type(ma_object), ImportObject), \
                "ma_object must subclass ImportObject, not %s \n objects: %s \n self: %s" \
                % (type(ma_object), ma_objects, self.__repr__())
        sa_objects = self.s_filter(sa_objects)
        for sa_object in sa_objects:
            assert \
                issubclass(type(sa_object), ImportObject), \
                "sa_object must subclass ImportObject, not %s \n objects: %s \n self: %s" \
                % (type(sa_object), sa_objects, self.__repr__())
        match = Match(ma_objects, sa_objects)
        match_type = self.get_match_type(match)
        if match_type and match_type != 'empty':
            self.add_match(match, match_type)
            # print "match_type: ", match_type

    def __repr__(self):
        repr_str = ""
        # repr_str += "all matches:\n"
        # for match in self.matches:
        #     repr_str += " -> " + repr(match) + "\n"
        repr_str += "pure matches: (%d) \n" % len(self.pure_matches)
        for match in self.pure_matches:
            repr_str += " -> " + repr(match) + "\n"
        repr_str += "mainless matches: (%d) \n" % len(
            self.mainless_matches)
        for match in self.mainless_matches:
            repr_str += " -> " + repr(match) + "\n"
        repr_str += "subordinateless matches:(%d) \n" % len(self.subordinateless_matches)
        for match in self.subordinateless_matches:
            repr_str += " -> " + repr(match) + "\n"
        repr_str += "duplicate matches:(%d) \n" % len(self.duplicate_matches)
        for match in self.duplicate_matches:
            repr_str += " -> " + repr(match) + "\n"
        return repr_str


class ProductMatcher(AbstractMatcher):
    """
    Matcher class for ImportProducts
    """
    process_registers = AbstractMatcher.process_registers_singular
    # retrieveObjects = AbstractMatcher.retrieveObjectsSingular

    @staticmethod
    def product_index_fn(product_object):
        """the product index function for the class."""
        return product_object.codesum

    def __init__(self):
        super(ProductMatcher, self).__init__(self.product_index_fn)
        self.process_registers = self.process_registers_singular
        # self.retrieveObjects = self.retrieveObjectsSingular


class VariationMatcher(ProductMatcher):
    """
    Matcher class for variations
    """
    pass


class CategoryMatcher(AbstractMatcher):
    """
    Matcher class for categories
    """
    process_registers = AbstractMatcher.process_registers_singular
    # retrieveObjects = AbstractMatcher.retrieveObjectsSingular

    @staticmethod
    def category_index_fn(category_object):
        """Return the name of the category."""
        return category_object.cat_name

    def __init__(self):
        super(CategoryMatcher, self).__init__(self.category_index_fn)
        self.process_registers = self.process_registers_singular
        # self.retrieveObjects = self.retrieveObjectsSingular


class CategoryTitleMatcher(CategoryMatcher):
    @staticmethod
    def category_index_fn(category_object):
        """Return the name of the category."""
        return category_object.title


class ImageMatcher(AbstractMatcher):
    """
    Matches images on normalized filename
    """
    process_registers = AbstractMatcher.process_registers_singular
    # retrieveObjects = AbstractMatcher.retrieveObjectsSingular

    @staticmethod
    def image_index_fn(img_object):
        """Return the basename of the image file."""
        return img_object.normalized_filename

    def __init__(self):
        super(ImageMatcher, self).__init__(self.image_index_fn)
        self.process_registers = self.process_registers_singular
        # self.retrieveObjects = self.retrieveObjectsSingular

    @classmethod
    def find_attachee_sku_matches(cls, match):
        """
        find within the match, matches based on an objects attachee_sku
        """
        return match.find_key_matches(
            lambda obj: SanitationUtils.normalize_val(obj.attachee_skus))

    @classmethod
    def find_file_basename_matches(cls, match):
        """
        find within the match, matches based on an objects file basename
        """
        return match.find_key_matches(
            lambda obj: SanitationUtils.normalize_val(obj.file_basename))

    @classmethod
    def find_norm_title_matches(cls, match):
        """
        find within the match, matches based on an objects normalized_title
        """
        return match.find_key_matches(
            lambda obj: SanitationUtils.normalize_val(obj.norm_title))


class StrictImageMatcher(ImageMatcher):
    @staticmethod
    def image_index_fn(img_object):
        """Return the identifier of the image file."""
        return img_object.identifier


class AttachmentIDMatcher(AbstractMatcher):
    """
    Matches attachments on wordpress ID
    """
    process_registers = AbstractMatcher.process_registers_singular
    # retrieveObjects = AbstractMatcher.retrieveObjectsSingular

    @staticmethod
    def image_index_fn(img_object):
        """Return the basename of the image file."""
        return img_object.wpid

    def __init__(self):
        super(AttachmentIDMatcher, self).__init__(self.image_index_fn)
        self.process_registers = self.process_registers_singular
        # self.retrieveObjects = self.retrieveObjectsSingular


class UsernameMatcher(AbstractMatcher):
    """
    Matcher class for Users, matches on username
    """

    def __init__(self):
        super(UsernameMatcher,
              self).__init__(lambda user_object: user_object.username)


class FilteringMatcher(AbstractMatcher):
    """
    Matching class that only process ImportObjects if their indices are contained
    in a list of allowed indices
    """

    # TODO: holy shit this is inefficient

    def __init__(self, index_fn, s_match_indices=None, m_match_indices=None):
        if not s_match_indices:
            s_match_indices = []
        if not m_match_indices:
            m_match_indices = []
        # print "entering FilteringMatcher __init__"
        super(FilteringMatcher, self).__init__(index_fn)
        self.s_match_indices = s_match_indices
        self.m_match_indices = m_match_indices
        self.m_filter_fn = lambda user_object: user_object.index not in self.m_match_indices
        self.f_filter_fn = lambda user_object: user_object.index not in self.s_match_indices


class CardMatcher(FilteringMatcher):
    """
    A matching class for `parsing.user.UserImportOBject`s that indexes on card
    """

    @staticmethod
    def card_index_fn(user_object):
        """the card index function for the class."""
        assert \
            hasattr(user_object, 'MYOBID'), \
            'must be able to get MYOBID, instead type is %s' % type(
                user_object)
        return user_object.MYOBID

    def __init__(self, s_match_indices=None, m_match_indices=None):
        # if not m_match_indices:
        #     m_match_indices = []
        # if not s_match_indices:
        #     s_match_indices = []
        super(CardMatcher, self).__init__(self.card_index_fn, s_match_indices,
                                          m_match_indices)


class EmailMatcher(FilteringMatcher):
    """
    A matching class for `parsing.user.UserImportOBject`s that indexes on Email
    """

    @staticmethod
    def email_index_fn(user_object):
        """the email index function for the class."""
        assert \
            hasattr(user_object, 'email'), \
            "must be able to get email, instead type is %s" % type(user_object)
        return SanitationUtils.normalize_val(user_object.email)

    def __init__(self, s_match_indices=None, m_match_indices=None):
        # if not s_match_indices:
        #     s_match_indices = []
        # if not m_match_indices:
        #     m_match_indices = []
        super(EmailMatcher, self).__init__(self.email_index_fn,
                                           s_match_indices, m_match_indices)


class NocardEmailMatcher(EmailMatcher):
    """
    A matching class for `parsing.user.UserImportOBject`s that have no card which
    indexes on email
    """

    def __init__(self, s_match_indices=None, m_match_indices=None):
        # if not s_match_indices:
        #     s_match_indices = []
        # if not m_match_indices:
        #     m_match_indices = []
        super(NocardEmailMatcher, self).__init__(s_match_indices,
                                                 m_match_indices)
        self.process_registers = self.process_registers_singular_ns


class AttacheeSkuMatcher(FilteringMatcher):
    @staticmethod
    def attachee_sku_index_fn(attachment_object):
        """gets the sku of the object that the attachment is attached to."""
        assert \
            hasattr(attachment_object, 'attachee_skus'), \
            "must be able to get attachee_skus, instead type is %s" % type(attachment_object)
        return SanitationUtils.normalize_val(attachment_object.attachee_skus)

    def __init__(self, s_match_indices=None, m_match_indices=None):
        # if not s_match_indices:
        #     s_match_indices = []
        # if not m_match_indices:
        #     m_match_indices = []
        super(AttacheeSkuMatcher, self).__init__(
            self.attachee_sku_index_fn, s_match_indices, m_match_indices)
        self.process_registers = self.process_registers_singular


class AttacheeTitleMatcher(FilteringMatcher):
    @staticmethod
    def attachee_title_index_fn(attachment_object):
        """gets the sku of the object that the attachment is attached to."""
        assert \
            hasattr(attachment_object, 'attachee_titles'), \
            "must be able to get attachee_titles, instead type is %s" % type(attachment_object)
        return SanitationUtils.normalize_val(attachment_object.attachee_titles)

    def __init__(self, s_match_indices=None, m_match_indices=None):
        # if not s_match_indices:
        #     s_match_indices = []
        # if not m_match_indices:
        #     m_match_indices = []
        super(AttacheeTitleMatcher, self).__init__(
            self.attachee_title_index_fn, s_match_indices, m_match_indices)
        self.process_registers = self.process_registers_singular
