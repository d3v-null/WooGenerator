"""
Introduce woo structure to shop classes.
"""
from __future__ import absolute_import

import os
import re
from collections import OrderedDict
from copy import copy, deepcopy
from pprint import pformat

from ..coldata import (ColDataMedia, ColDataProductMeridian, ColDataProductVariationMeridian,
                       ColDataWcProdCategory)
from ..utils import (DescriptorUtils, PHPUtils, Registrar, SanitationUtils,
                     SeqUtils, TimeUtils)
from .abstract import ObjList
from .gen import CsvParseGenTree, ImportGenItem, ImportGenObject, ImportGenTaxo
from .shop import (CsvParseShopMixin, ImportShopCategoryMixin,
                   ImportShopImgMixin, ImportShopMixin, ImportShopProductMixin,
                   ImportShopProductSimpleMixin,
                   ImportShopProductVariableMixin,
                   ImportShopProductVariationMixin, ShopCatList, ShopObjList,
                   ShopProdList, ShopMixin)
from .special import ImportSpecialGroup
from .tree import ImportTreeItem, ImportTreeObject, ItemList, TaxoList

ColDataWcProdCategory



class ImportWooMixin(object):
    """ all things common to Woo import classes """

    wpid_key = 'ID'
    wpid = DescriptorUtils.safe_key_property(wpid_key)
    title_key = 'title'
    title = DescriptorUtils.safe_key_property(title_key)
    slug_key = 'slug'
    slug = DescriptorUtils.safe_key_property(slug_key)
    verify_meta_keys = [
        wpid_key,
        title_key,
        slug_key
    ]

    def __init__(self, *args, **kwargs):
        if self.DEBUG_MRO:
            self.register_message('ImportWooMixin')
        super(ImportWooMixin, self).__init__(*args, **kwargs)
        self.specials = []

    @property
    def is_updated(self):
        return SanitationUtils.normalize_val(self.get('Updated', "")) == 'Y'

    @property
    def splist(self):
        schedule = self.get('SCHEDULE')
        if schedule:
            return filter(None, SanitationUtils.find_all_tokens(schedule))
        else:
            return []

    def has_special(self, special):
        return special in map(SanitationUtils.normalize_val, self.specials)

    def has_special_fuzzy(self, special_search):
        if isinstance(special_search, ImportSpecialGroup):
            special_search = special_search.special_id
        for special_compare in [
                SanitationUtils.normalize_val(special) for special in self.specials
        ]:
            if self.DEBUG_SPECIAL:
                self.register_message(
                    "testing special %s matches special: %s" %
                    (special_compare, special_search))
            if special_search in special_compare:
                return True

    def register_special(self, special):
        if special not in self.specials:
            self.specials.append(special)

class ImportWooObject(ImportGenObject, ImportShopMixin, ImportWooMixin):
    container = ShopObjList
    to_dict = ImportShopMixin.to_dict

    verify_meta_keys = ImportGenObject.verify_meta_keys + ImportWooMixin.verify_meta_keys

    def __init__(self, *args, **kwargs):
        if self.DEBUG_MRO:
            self.register_message('ImportWooObject')
        ImportGenObject.__init__(self, *args, **kwargs)
        ImportShopMixin.__init__(self, *args, **kwargs)
        ImportWooMixin.__init__(self, *args, **kwargs)

class WooListMixin(object):
    coldata_class = ColDataProductMeridian
    coldata_cat_class = ColDataWcProdCategory
    coldata_var_class = ColDataProductVariationMeridian
    coldata_img_class = ColDataMedia
    supported_type = ImportWooObject

class ImportWooItem(ImportWooObject, ImportGenItem):

    verify_meta_keys = SeqUtils.combine_lists(
        ImportWooObject.verify_meta_keys,
        ImportGenItem.verify_meta_keys
    )
    is_item = ImportGenItem.is_item

    def __init__(self, *args, **kwargs):
        if self.DEBUG_MRO:
            self.register_message('ImportWooItem')
        ImportWooObject.__init__(self, *args, **kwargs)
        # ImportGenItem.__init__(self, *args, **kwargs)
    # def __init__(self, *args, **kwargs):
    #     if self.DEBUG_MRO:
    #         self.register_message(' ')
    #     super(ImportWooItem, self).__init__(*args, **kwargs)
    #
    # @property
    # def verify_meta_keys(self):
    #     superverify_meta_keys = super(ImportWooItem, self).verify_meta_keys
    #     # superverify_meta_keys += ImportGenItem.verify_meta_keys
    #     return superverify_meta_keys


class ImportWooProduct(ImportWooItem, ImportShopProductMixin):
    is_product = ImportShopProductMixin.is_product
    name_delimeter = ' - '

    def __init__(self, *args, **kwargs):
        if self.DEBUG_MRO:
            self.register_message('ImportWooProduct')
        if self.product_type:
            args[0]['prod_type'] = self.product_type
        ImportWooItem.__init__(self, *args, **kwargs)
        ImportShopProductMixin.__init__(self, *args, **kwargs)

    def process_meta(self):
        if self.DEBUG_MRO:
            self.register_message('ImportWooProduct')
        super(ImportWooProduct, self).process_meta()

        # process titles
        line1, line2 = SanitationUtils.title_splitter(self.namesum)
        if not line2:
            name_ancestors = self.name_ancestors
            ancestors_self = name_ancestors + [self]
            names = SeqUtils.filter_unique_true(
                map(lambda x: x.name, ancestors_self))
            if names and len(names) < 2:
                line1 = names[0]
                name_delimeter = self.name_delimeter
                line2 = name_delimeter.join(names[1:])

        self['title_1'] = line1
        self['title_2'] = line2

        if not self.title:
            self.title = self.namesum

    @property
    def inheritence_ancestors(self):
        return SeqUtils.filter_unique_true(
            self.categories.values() + super(ImportWooProduct, self).inheritence_ancestors
        )

    @property
    def extra_special_category(self):
        ancestors_self = self.taxo_ancestors + [self]
        names = SeqUtils.filter_unique_true(
            map(lambda x: x.fullname, ancestors_self))
        return "Specials > " + names[0] + " Specials"

class WooProdList(ShopProdList, WooListMixin):
    coldata_class = WooListMixin.coldata_class
    supported_type = ImportWooProduct
    report_cols = coldata_class.get_report_cols_gen()

ImportWooProduct.container = WooProdList

class ImportWooProductSimple(ImportWooProduct, ImportShopProductSimpleMixin):
    product_type = ImportShopProductSimpleMixin.product_type


class ImportWooProductVariable(
        ImportWooProduct, ImportShopProductVariableMixin):
    is_variable = ImportShopProductVariableMixin.is_variable
    product_type = ImportShopProductVariableMixin.product_type

    def __init__(self, *args, **kwargs):
        if self.DEBUG_MRO:
            self.register_message('ImportWooProductVariable')
        ImportWooProduct.__init__(self, *args, **kwargs)
        ImportShopProductVariableMixin.__init__(self, *args, **kwargs)


class ImportWooProductVariation(
        ImportWooProduct, ImportShopProductVariationMixin):
    is_variation = ImportShopProductVariationMixin.is_variation
    product_type = ImportShopProductVariationMixin.product_type

class WooVarList(ShopProdList, WooListMixin):
    supported_type = ImportWooProductVariation
    coldata_class = WooListMixin.coldata_var_class
    report_cols = coldata_class.get_report_cols_gen()

ImportWooProductVariation.container = WooVarList

class ImportWooProductComposite(ImportWooProduct):
    product_type = 'composite'


class ImportWooProductGrouped(ImportWooProduct):
    product_type = 'grouped'


class ImportWooProductBundled(ImportWooProduct):
    product_type = 'bundle'


class ImportWooTaxo(ImportWooObject, ImportGenTaxo):
    namesum_key = ImportGenTaxo.namesum_key
    namesum = DescriptorUtils.safe_key_property(namesum_key)

    verify_meta_keys = SeqUtils.combine_lists(
        ImportWooObject.verify_meta_keys,
        ImportGenTaxo.verify_meta_keys
    )
    is_taxo = ImportGenTaxo.is_taxo

    def __init__(self, *args, **kwargs):
        if self.DEBUG_MRO:
            self.register_message('ImportWooTaxo')
        ImportWooObject.__init__(self, *args, **kwargs)
        # ImportGenTaxo.__init__(self, *args, **kwargs)
    # def __init__(self, *args, **kwargs):
    #     if self.DEBUG_MRO:
    #         self.register_message('ImportWooTaxo')
    #     super(ImportWooTaxo, self).__init__(*args, **kwargs)
    #
    # @property
    # def verify_meta_keys(self):
    #     superverify_meta_keys = super(ImportWooTaxo, self).verify_meta_keys
    #     # superverify_meta_keys += ImportGenTaxo.verify_meta_keys
    #     return superverify_meta_keys

class ImportWooCategory(ImportWooTaxo, ImportShopCategoryMixin):
    is_category = ImportShopCategoryMixin.is_category
    is_product = ImportShopCategoryMixin.is_product

    def __init__(self, *args, **kwargs):
        if self.DEBUG_MRO:
            self.register_message('ImportWooCategory')
        ImportWooTaxo.__init__(self, *args, **kwargs)
        ImportShopCategoryMixin.__init__(self, *args, **kwargs)
        # super(ImportWooCategory, self).__init__(*args, **kwargs)
    # @property
    # def identifier_delimeter(self):
    #     return ImportWooObject.identifier_delimeter(self)

    def find_child_category(self, index):
        for child in self.children:
            if child.is_category:
                if child.index == index:
                    return child
                else:
                    result = child.find_child_category(index)
                    if result:
                        return result
        return None

    def process_meta(self):
        ImportGenTaxo.process_meta(self)
        self.title = self.fullname

    @property
    def cat_name(self):
        cat_layers = self.namesum.split(' > ')
        return cat_layers[-1]

    @property
    def index(self):
        return self.rowcount

    @property
    def identifier(self):
        # identifier = super(ImportWooCategory, self).identifier
        return "|".join([
            self.codesum,
            'r:%s' % str(self.rowcount),
            'w:%s' % str(self.get(self.wpid_key)),
            self.cat_name,
        ])
    #
    # @property
    # def title(self):
    #     return self.cat_name
    #
    # def __getitem__(self, key):
    #     if key == self.title_key:
    #         return self.cat_name
    #     else:
    #         return super(ImportWooCategory, self).__getitem__(key)

class WooCatList(ShopCatList, WooListMixin):
    coldata_class = WooListMixin.coldata_cat_class
    supported_type = ImportWooCategory
    report_cols = coldata_class.get_report_cols_gen()

ImportWooCategory.container = WooCatList

class ImportWooImg(ImportTreeObject, ImportShopImgMixin):
    verify_meta_keys = ImportShopImgMixin.verify_meta_keys
    index = ImportShopImgMixin.index
    is_product = False
    is_category = False

    wpid_key = 'id'
    slug_key = 'slug'
    title_key = 'title'

    def __init__(self, *args, **kwargs):
        ImportTreeObject.__init__(self, *args, **kwargs)
        ImportShopImgMixin.__init__(self, *args, **kwargs)

class WooImgList(ObjList, WooListMixin):
    coldata_class = WooListMixin.coldata_img_class
    supported_type = ImportWooImg
    report_cols = coldata_class.get_report_cols_gen()

ImportWooImg.container = WooImgList

class CsvParseWooMixin(object):
    """ All the stuff that's common to Woo Parser classes """
    object_container = ImportWooObject
    item_container = ImportWooItem
    product_container = ImportWooProduct
    simple_container = ImportWooProductSimple
    variable_container = ImportWooProductVariable
    variation_container = ImportWooProductVariation
    composite_container = ImportWooProductComposite
    grouped_container = ImportWooProductGrouped
    bundled_container = ImportWooProductBundled
    coldata_img_target = 'wp-api'
    # Under woo, all taxos are categories
    coldata_class = ShopMixin.coldata_class
    coldata_cat_class = ShopMixin.coldata_cat_class
    coldata_img_class = ShopMixin.coldata_img_class
    coldata_sub_img_class = ShopMixin.coldata_sub_img_class
    taxo_container = ImportWooCategory
    category_container = ImportWooCategory
    category_indexer = Registrar.get_object_rowcount
    image_container = ImportWooImg

    def find_category(self, search_data):
        search_keys = [
            self.category_container.wpid_key,
            self.category_container.slug_key,
            self.category_container.title_key,
            self.category_container.namesum_key,
        ]
        registry = self.categories
        return self.find_object(search_data, registry, search_keys)

    def find_image(self, search_data):
        registry = self.images
        search_keys = [
            # self.image_container.wpid_key,
            self.image_container.slug_key,
            # self.image_container.title_key,
            self.image_container.file_name_key,
            self.image_container.source_url_key
        ]
        return self.find_object(search_data, registry, search_keys)

    @classmethod
    def get_title(cls, object_data):
        assert isinstance(object_data, ImportWooMixin)
        return object_data.title

    def get_parser_data(self, **kwargs):
        if Registrar.DEBUG_MRO:
            Registrar.register_message(' ')
        defaults = {
            self.object_container.wpid_key: '',
            self.object_container.slug_key: '',
            self.object_container.title_key: ''
        }
        # super_data = super(CsvParseWooMixin, self).get_parser_data(**kwargs)
        # defaults.update(super_data)
        # if self.DEBUG_PARSER:
        # self.register_message("PARSER DATA: %s" % repr(defaults))
        return defaults

    @property
    def img_defaults(self):
        if not hasattr(self, '_coldata_img_class_defaults'):
            self._coldata_img_class_defaults = self.coldata_img_class.get_defaults_gen()
        return deepcopy(self._coldata_img_class_defaults)

    @property
    def cat_defaults(self):
        if not hasattr(self, '_coldata_cat_class_defaults'):
            self._coldata_cat_class_defaults = self.coldata_cat_class.get_defaults_gen()
        return deepcopy(self._coldata_cat_class_defaults)

    def process_image(self, img_raw_data, object_data=None, **kwargs):
        img_filename = self.image_container.get_file_name(img_raw_data)
        if self.DEBUG_IMG:
            if object_data:
                identifier = object_data.identifier
                self.register_message(
                    "%s attached to %s"
                    % (identifier, img_filename)
                )
            else:
                self.register_message(
                    "creating image %s" % (img_filename)
                )
            self.register_message("PROCESS IMG: %s" % repr(img_raw_data))

        img_data = None
        if self.image_container.file_path_key in img_raw_data:
            img_data = self.images.get(img_filename)
        if not img_data:
            img_data = self.find_image(img_raw_data)
        if not img_data:
            if self.DEBUG_IMG:
                self.register_message("SEARCH IMG NOT FOUND")
            row_data = deepcopy(img_raw_data)
            row_data[self.image_container.file_name_key] = img_filename
            kwargs['defaults'] = self.img_defaults
            kwargs['row_data'] = row_data
            kwargs['parent'] = self.root_data
            kwargs['container'] = self.image_container
            try:
                img_data = self.new_object(
                    rowcount=self.rowcount,
                    **kwargs
                )
            except UserWarning as exc:
                warn = UserWarning("could not create image: %s" % exc)
                self.register_error(
                    warn
                )
                if self.strict:
                    self.raise_exception(warn)
            self.register_image(img_data)

        else:
            if self.DEBUG_IMG:
                self.register_message("FOUND IMG: %s" % repr(img_data))

        self.register_attachment(img_data, object_data)

    def get_wpid(self, object_data):
        return object_data.wpid

    def clear_transients(self):
        pass


class CsvParseWoo(CsvParseGenTree, CsvParseShopMixin, CsvParseWooMixin):
    object_container = CsvParseWooMixin.object_container
    item_container = CsvParseWooMixin.item_container
    product_container = CsvParseWooMixin.product_container
    simple_container = CsvParseWooMixin.simple_container
    variable_container = CsvParseWooMixin.variable_container
    variation_container = CsvParseWooMixin.variation_container
    category_container = CsvParseWooMixin.category_container
    composite_container = CsvParseWooMixin.composite_container
    grouped_container = CsvParseWooMixin.grouped_container
    bundled_container = CsvParseWooMixin.bundled_container
    taxo_container = CsvParseWooMixin.taxo_container
    image_container = CsvParseWooMixin.image_container
    category_indexer = CsvParseWooMixin.category_indexer
    coldata_class = CsvParseWooMixin.coldata_class
    coldata_cat_class = CsvParseWooMixin.coldata_cat_class
    coldata_img_class = CsvParseWooMixin.coldata_img_class

    do_specials = True
    do_dyns = True
    specialsCategory = None
    add_special_categories = False

    @property
    def containers(self):
        return {
            'S': self.simple_container,
            'V': self.variable_container,
            'I': self.variation_container,
            'C': self.composite_container,
            'G': self.grouped_container,
            'B': self.bundled_container,
            'M': self.image_container,
        }

    def __init__(self, cols, defaults, **kwargs):
        if self.DEBUG_MRO:
            self.register_message(' ')
        # print ("cat_mapping woo pre: %s" % str(cat_mapping))

        extra_taxo_subs = OrderedDict([
            ('Generic Literature', 'Marketing > Literature'),
            ('Generic Signage', 'Marketing > Signage'),
            ('Generic ', ''),
            ('Shimmerz for Hair', 'Shimmerz for Hair'),
            ('Sqiffy Accessories', 'Sqiffy'),
            ('Sticky Soul Accessories', 'Sticky Soul'),
            ('Tanning Advantage ', ''),
            ('Assorted ', ''),
            ('My Tan Apparel', 'My Tan Dress'),
            # ('Shimmerz for Hair', 'Tanning Accessories > Shimmerz for Hair'),
            # ('Sqiffy Accessories', 'Tanning Accessories > Sqiffy'),
            # ('EzeBreathe', 'Tanning Accessories > EzeBreathe'),
            # ('My Tan', 'Tanning Accessories > My Tan'),
            # ('Tan Sleeper', 'Tanning Accessories > Tan Sleeper'),
            # ('Tanning Advantage Application Equipment', 'Equipment > Application Equipment'),
            # ('Generic Application Equipment', 'Equipment > Application Equipment'),
            # ('Generic Tanning Booths', 'Equipment > Tanning Booths'),
        ])

        extra_item_subs = OrderedDict([
            ('Hot Pink', 'Pink'),
            ('Hot Lips (Red)', 'Red'),
            ('Hot Lips', 'Red'),
            ('Silken Chocolate (Bronze)', 'Bronze'),
            ('Silken Chocolate', 'Bronze'),
            ('Moon Marvel (Silver)', 'Silver'),
            ('Dusty Gold', 'Gold'),

            ('Screen Printed', ''),
            ('Embroidered', ''),
        ])

        if not kwargs.get('schema'):
            kwargs['schema'] = "TT"

        extra_cols = ['PA', 'VA', 'weight', 'length', 'width', 'height',
                      'stock', 'stock_status', 'Images', 'HTML Description',
                      'post_status', kwargs.get('schema')]

        cols = SeqUtils.combine_lists(cols, extra_cols)

        extra_cat_maps = OrderedDict()

        kwargs['taxo_subs'] = SeqUtils.combine_ordered_dicts(
            kwargs.get('taxo_subs', {}), extra_taxo_subs)
        kwargs['item_subs'] = SeqUtils.combine_ordered_dicts(
            kwargs.get('item_subs', {}), extra_item_subs)
        # import_name = kwargs.pop('import_name', time.strftime("%Y-%m-%d %H:%M:%S") )

        self.cat_mapping = SeqUtils.combine_ordered_dicts(
            kwargs.pop('cat_mapping', {}), extra_cat_maps)
        self.dprc_rules = kwargs.pop('dprc_rules', {})
        self.dprp_rules = kwargs.pop('dprp_rules', {})
        self.special_rules = kwargs.pop('special_rules', {})
        self.current_special_groups = kwargs.pop(
            'current_special_groups', None)
        # print "settings current_special_groups: %s" % self.current_special_groups
        # self.specialGroups = kwargs.pop('specialGroups', {})
        if kwargs.get('meta_width') is None:
            kwargs['meta_width'] = 2
        if kwargs.get('item_depth') is None:
            kwargs['item_depth'] = 2
        if kwargs.get('taxo_depth') is None:
            kwargs['taxo_depth'] = 2

        super(CsvParseWoo, self).__init__(cols, defaults, **kwargs)

        # self.category_indexer = self.product_indexer

        # if self.DEBUG_WOO:
        #     self.register_message("cat_mapping woo post: %s" % str(cat_mapping))

        # if self.DEBUG_WOO:
        #     print "WOO initializing: "
        #     print "-> taxo_depth: ", self.taxo_depth
        #     print "-> item_depth: ", self.item_depth
        #     print "-> max_depth: ", self.max_depth
        #     print "-> meta_width: ", self.meta_width

    def clear_transients(self):
        if self.DEBUG_MRO:
            self.register_message(' ')
        CsvParseGenTree.clear_transients(self)
        CsvParseShopMixin.clear_transients(self)
        CsvParseWooMixin.clear_transients(self)
        self.special_items = OrderedDict()
        self.updated_products = OrderedDict()
        self.updated_variations = OrderedDict()
        self.onspecial_products = OrderedDict()
        self.onspecial_variations = OrderedDict()

    def register_object(self, object_data):
        CsvParseGenTree.register_object(self, object_data)
        CsvParseShopMixin.register_object(self, object_data)

    def get_parser_data(self, **kwargs):
        if self.DEBUG_MRO:
            self.register_message(' ')
        super_data = {}
        for base_class in reversed(CsvParseWoo.__bases__):
            if hasattr(base_class, 'get_parser_data'):
                super_data.update(base_class.get_parser_data(self, **kwargs))
        # super_data = CsvParseWooMixin.get_parser_data(self, **kwargs)
        # super_data.update(CsvParseShopMixin.get_parser_data(self, **kwargs))
        # super_data.update(CsvParseGenTree.get_parser_data(self, **kwargs))
        if self.DEBUG_PARSER:
            self.register_message("PARSER DATA: %s" % repr(super_data))
        return super_data

    def get_new_obj_container(self, *args, **kwargs):
        if self.DEBUG_MRO:
            self.register_message(' ')
        container = super(CsvParseWoo, self).get_new_obj_container(
            *args, **kwargs)
        try:
            all_data = args[0]
        except IndexError:
            warn = UserWarning("all_data not specified")
            self.register_error(warn)
            self.raise_exception(warn)

        if issubclass(container, ImportTreeItem) \
                and self.schema in all_data:
            woo_type = all_data[self.schema]
            if woo_type:
                try:
                    container = self.containers[woo_type]
                except IndexError:
                    exc = UserWarning(
                        "Unknown API product type: %s" % woo_type)
                    source = kwargs.get('rowcount')
                    self.register_error(exc, source)
        if self.DEBUG_SHOP:
            self.register_message("container: {}".format(container.__name__))
        return container

    def register_special(self, object_data, special):
        try:
            special = str(special)
            assert isinstance(special, (str, unicode)), 'Special must be a string not {}'.format(
                type(special).__name__)
            assert special is not '', 'Attribute must not be empty'
        except AssertionError as exc:
            self.register_error("could not register special: {}".format(exc))
        self.register_anything(
            object_data,
            self.special_items,
            indexer=special,
            singular=False,
            register_name='specials'
        )
        object_data.register_special(special)

    def register_updated_product(self, object_data):
        assert \
            isinstance(object_data, ImportWooProduct), \
            "object should be ImportWooProduct not %s" % str(type(object_data))
        assert \
            not isinstance(object_data, ImportWooProductVariation), \
            "object should not be ImportWooProductVariation"
        self.register_anything(
            object_data,
            self.updated_products,
            register_name='updated_products',
            singular=True
        )

    def register_updated_variation(self, object_data):
        assert \
            isinstance(object_data, ImportWooProductVariation), \
            "object should be ImportWooProductVariation not %s" % str(
                type(object_data))
        self.register_anything(
            object_data,
            self.updated_variations,
            register_name='updated_variations',
            singular=True
        )

    def register_current_spec_prod(self, object_data):
        assert \
            isinstance(object_data, ImportWooProduct), \
            "object should be ImportWooProduct not %s" % str(type(object_data))
        assert \
            not isinstance(object_data, ImportWooProductVariation), \
            "object should not be ImportWooProductVariation"
        self.register_anything(
            object_data,
            self.onspecial_products,
            register_name='onspecial_products',
            singular=True
        )

    def register_current_spec_var(self, object_data):
        assert \
            isinstance(object_data, ImportWooProductVariation), \
            "object should be ImportWooProductVariation not %s" % str(
                type(object_data))
        self.register_anything(
            object_data,
            self.onspecial_variations,
            register_name='onspecial_variations',
            singular=True
        )

    def process_images(self, object_data):
        img_paths = filter(None, SanitationUtils.find_all_images(
            object_data.get('Images', '')))
        for image in img_paths:
            # TODO: create image object and register if not exist
            img_data = {
                'file_path': image
            }
            self.process_image(img_data, object_data)
        this_images = object_data.images.values()
        if object_data.is_item:
            ancestors = object_data.item_ancestors
        else:
            ancestors = []
        for ancestor in ancestors:
            ancestor_images = ancestor.images.values()
            # TODO: create image object and register if not exist
            if len(this_images) and not len(ancestor_images):
                self.process_image(this_images[0], ancestor)
            elif not len(this_images) and len(ancestor_images):
                self.process_image(ancestor_images[0], object_data)

    def process_categories(self, object_data):
        if object_data.is_product:
            for ancestor in object_data.taxo_ancestors:
                if ancestor.name and self.category_indexer(
                        ancestor) not in self.categories:
                    self.register_category(ancestor)
                self.join_category(ancestor, object_data)

        # TODO: update description if category is part of a special

        # TODO: fix for VuTan
        if object_data.get('E'):
            if self.DEBUG_WOO:
                self.register_message("HAS EXTRA LAYERS")
            if object_data.is_product:
                # self.register_message("ANCESTOR NAMESUM: %s" % \
                #     str(object_data.get_ancestor_key('namesum')))
                # self.register_message("ANCESTOR DESCSUM: %s" % \
                #     str(object_data.get_ancestor_key('descsum')))
                # self.register_message("ANCESTOR CATSUM: %s" % \
                #     str(object_data.get_ancestor_key('catsum')))
                # self.register_message("ANCESTOR ITEMSUM: %s" % \
                #     str(object_data.get_ancestor_key('itemsum')))
                # self.register_message("ANCESTOR TAXOSUM: %s" % \
                #     str(object_data.get_ancestor_key('taxosum')))
                # self.register_message("ANCESTOR NAME: %s" % \
                #     str(object_data.get_ancestor_key('name')))
                taxo_ancestor_names = [ancestorData.get(
                    'name') for ancestorData in object_data.taxo_ancestors]
                # self.register_message("TAXO ANCESTOR NAMES: %s" % str(taxo_ancestor_names))

                # I'm so sorry for this code, it is utter horse shit but it
                # works

                extra_name = object_data.name
                extra_name = re.sub(r' ?\([^\)]*\)', '', extra_name)
                extra_name = re.sub(r'1Litre', '1 Litre', extra_name)
                extra_taxo_name = ''
                if taxo_ancestor_names:
                    if len(taxo_ancestor_names) > 2:
                        extra_taxo_name = taxo_ancestor_names[-2]
                    else:
                        extra_taxo_name = taxo_ancestor_names[0]

                # TODO: This is some janky ass shit that needs to be put in a
                # conf file

                extra_suffix = 'Items'
                if re.search('Sample', extra_name, flags=re.I):
                    extra_suffix = 'Samples'
                    extra_name = re.sub(r' ?Samples?', '',
                                        extra_name, flags=re.I)
                elif re.search('Trial Size', extra_name, flags=re.I):
                    extra_suffix = 'Trial Sizes'
                    extra_name = re.sub(r' ?Trial Sizes?', '',
                                        extra_name, flags=re.I)
                elif re.search('10g', extra_name, flags=re.I):
                    if re.search('Bronzing Powder', extra_taxo_name, flags=re.I) \
                            or re.search('Foundation', extra_taxo_name, flags=re.I):
                        extra_suffix = 'Jars'

                if re.search('Brushes', extra_taxo_name, flags=re.I):
                    extra_suffix = ''
                    if re.search('Concealor', extra_name, flags=re.I):
                        extra_name += 's'
                        extra_taxo_name = ''
                elif re.search('Kits', extra_taxo_name, flags=re.I):
                    extra_suffix = ''
                elif re.search('Tan Care Kits', extra_taxo_name, flags=re.I):
                    extra_suffix = 'Items'
                    extra_taxo_name = ''
                elif re.search('Natural Soy Wax Candles', extra_taxo_name, flags=re.I):
                    extra_suffix = ''
                    extra_taxo_name = ''
                    if not extra_name.endswith('s'):
                        extra_name += 's'
                elif re.search('Shimmerz 4 Hair', extra_taxo_name, flags=re.I):
                    extra_taxo_name = 'Shimmerz'
                    if extra_name.endswith('s'):
                        extra_name = extra_name[:-1]
                    extra_suffix = 'Packs'
                elif re.search('Hair Care', extra_taxo_name, flags=re.I):
                    extra_name = re.sub(' Sachet', '', extra_name, flags=re.I)
                elif re.search('Tanbience Product Packs', extra_taxo_name, flags=re.I):
                    extra_taxo_name = ''

                extra_depth = self.taxo_depth - 1
                extra_rowcount = object_data.rowcount
                extra_stack = self.stack.get_left_slice(extra_depth)
                extra_name = ' '.join(
                    filter(None, [extra_name, extra_taxo_name, extra_suffix]))
                extra_name = SanitationUtils.strip_extra_whitespace(extra_name)
                extra_code = object_data.code
                extra_row = object_data.row

                # print "SKU: %s" % object_data.codesum
                # print "-> EXTRA LAYER NAME: %s" % str(extra_name)
                # print "-> EXTRA STACK: %s" % repr(extra_stack)
                # print "-> EXTRA LAYER CODE: %s" % extra_code
                # print "-> EXTRA ROW: %s" % str(extra_row)

                # extraCodesum = (extra_layer).codesum

                siblings = extra_stack.get_top().children
                # code_ancestors = [ancestor.code for ancestor in extra_stack if ancestor.code ]
                # code_ancestors += [extra_code]
                # extraCodesum = ''.join(code_ancestors)

                # assert issubclass(type(extra_layer), ImportTreeObject), \
                # "needs to subclass ImportTreeObject to do siblings"
                # siblings = getattr(extra_layer, 'siblings')
                # siblings = extra_layer.siblings
                extra_layer = None
                for sibling in siblings:
                    # print "sibling meta: %s" % repr(sibling.meta)
                    if sibling.name == extra_name:
                        extra_layer = sibling
                    # if sibling.codesum == extraCodesum:
                    #     if sibling.rowcount != extra_rowcount:
                    #         extra_layer = sibling
                    #         found_sibling = True
                    #         # if self.DEBUG_WOO: self.register_message("found sibling: %s"% extra_layer.index )
                    #         break

                if extra_layer:
                    if self.DEBUG_WOO:
                        self.register_message(
                            "found sibling: %s" % extra_layer.identifier)
                    if self.category_indexer(
                            extra_layer) not in self.categories:
                        self.register_category(extra_layer)
                else:
                    if self.DEBUG_WOO:
                        identifier = extra_layer.identifier if extra_layer \
                        else 'None'
                        self.register_message(
                            "did not find sibling: %s" % identifier)

                    extra_layer = self.new_object(
                        extra_rowcount,
                        row=extra_row,
                        depth=extra_depth,
                        meta=[
                            extra_name,
                            extra_code
                        ],
                        stack=extra_stack
                    )

                    # assert isinstance(extra_layer, ImportWooCategory )
                    # extra_stack.append(extra_layer)
                    # print "-> EXTRA LAYER ANCESTORS: %s" %
                    # repr(extra_layer.ancestors)
                    if self.DEBUG_WOO:
                        self.register_message("extra_layer name: %s; type: %s" % (
                            str(extra_name), str(type(extra_layer))))
                    assert issubclass(type(extra_layer), ImportGenTaxo)
                    # assert issubclass(type(extra_layer), ImportGenMixin), \
                    #     "needs to subclass ImportGenMixin to do codesum"

                    self.register_category(extra_layer)

                self.join_category(extra_layer, object_data)

                # print "-> FINAL EXTRA LAYER: %s" % repr(extra_layer)

                # self.register_join_category(extra_layer, object_data)

    def process_variation(self, var_data):
        pass

    def process_attributes(self, object_data):
        ancestors = \
            object_data.inheritence_ancestors + \
            [object_data]

        palist = SeqUtils.filter_unique_true(map(
            lambda ancestor: ancestor.get('PA'),
            ancestors
        ))

        if self.DEBUG_WOO:
            self.register_message("palist: %s" % palist)

        for attrs in palist:
            try:
                decoded = SanitationUtils.decode_json(attrs)
                for attr, val in decoded.items():
                    self.register_attribute(object_data, attr, val)
            except Exception as exc:
                self.register_error(
                    "could not decode attributes: %s | %s" % (attrs, exc), object_data)

        if object_data.is_variation:
            parent_data = object_data.parent
            assert parent_data and parent_data.is_variable
            vattrs = SanitationUtils.decode_json(object_data.get('VA'))
            assert vattrs
            for attr, val in vattrs.items():
                self.register_attribute(parent_data, attr, val, True)
                self.register_attribute(object_data, attr, val, True)

    def process_specials(self, object_data):
        for special in object_data.splist:
            self.register_special(object_data, special)

    def process_object(self, object_data):
        if self.DEBUG_MRO:
            self.register_message(' ')
        if self.DEBUG_WOO:
            self.register_message(object_data.index)
        super(CsvParseWoo, self).process_object(object_data)
        assert issubclass(
            object_data.__class__, ImportWooObject), "object_data should subclass ImportWooObject not %s" % object_data.__class__.__name__
        self.process_categories(object_data)
        if object_data.is_product:
            cat_skus = map(
                lambda x: x.codesum,
                object_data.categories.values())
            if self.DEBUG_WOO:
                self.register_message("categories: {}".format(cat_skus))
        if object_data.is_variation:
            self.process_variation(object_data)
            if self.DEBUG_WOO:
                self.register_message("variation of: {}".format(
                    object_data.get('parent_SKU')))
        self.process_attributes(object_data)
        if self.DEBUG_WOO:
            self.register_message(
                "attributes: {}".format(object_data.attributes))
        if self.do_images:
            self.process_images(object_data)
            if self.DEBUG_WOO:
                self.register_message("images: {}".format(object_data.images))
        if self.do_specials:
            self.process_specials(object_data)
            if self.DEBUG_WOO:
                self.register_message(
                    "specials: {}".format(object_data.specials))

    def add_dyn_rules(self, item_data, dyn_type, rule_ids):
        rules = {
            'dprc': self.dprc_rules,
            'dprp': self.dprp_rules
        }[dyn_type]
        dyn_list_index = dyn_type + 'list'
        dyn_id_list_index = dyn_type + 'IDlist'
        if not item_data.get(dyn_list_index):
            item_data[dyn_list_index] = []
        if not item_data.get(dyn_id_list_index):
            item_data[dyn_id_list_index] = []
        for rule_id in rule_ids:
            if rule_id not in item_data[dyn_id_list_index]:
                item_data[dyn_id_list_index] = rule_id
            # print "adding %s to %s" % (rule_id, item_data['codesum'])
            rule = rules.get(rule_id)
            if rule:
                if rule not in item_data[dyn_list_index]:
                    item_data[dyn_list_index].append(rule)
            else:
                self.register_error(
                    'rule should exist: %s' %
                    rule_id, item_data)

    def post_process_dyns(self, object_data):
        # self.register_message(object_data.index)
        if object_data.is_product:
            ancestors = object_data.inheritence_ancestors + [object_data]
            for ancestor in ancestors:
                # print "%16s is a member of %s" % (object_data['codesum'],
                # ancestor['taxosum'])
                dprc_string = ancestor.get('DYNCAT')
                if dprc_string:
                    # print " -> DPRC", dprc_string
                    dprclist = dprc_string.split('|')
                    if self.DEBUG_WOO:
                        self.register_message("found dprclist %s" % (dprclist))
                    self.add_dyn_rules(object_data, 'dprc', dprclist)
                dprp_string = ancestor.get('DYNPROD')
                if dprp_string:
                    # print " -> DPRP", dprp_string
                    dprplist = dprp_string.split('|')
                    if self.DEBUG_WOO:
                        self.register_message("found dprplist %s" % (dprplist))
                    self.add_dyn_rules(object_data, 'dprp', dprplist)

            if object_data.get('dprclist', ''):
                object_data['dprcsum'] = '<br/>'.join(
                    filter(
                        None,
                        map(
                            lambda x: x.to_html(),
                            object_data.get('dprclist', '')
                        )
                    )
                )
                if self.DEBUG_WOO:
                    self.register_message("dprcsum of %s is %s" % (
                        object_data.index, object_data.get('dprcsum')))

            if object_data.get('dprplist', ''):
                object_data['dprpsum'] = '<br/>'.join(
                    filter(
                        None,
                        map(
                            lambda x: x.to_html(),
                            object_data.get('dprplist', '')
                        )
                    )
                )
                if self.DEBUG_WOO:
                    self.register_message("dprpsum of %s is %s" % (
                        object_data.index, object_data.get('dprpsum')))

                pricing_rules = {}
                for rule in object_data.get('dprplist', ''):
                    pricing_rules[PHPUtils.ruleset_uniqid()] = PHPUtils.unserialize(
                        rule.to_pricing_rule())

                object_data['pricing_rules'] = PHPUtils.serialize(
                    pricing_rules)

    def post_process_categories(self, object_data):
        # self.register_message(object_data.index)
        if object_data.is_category:
            # join extra parent categories
            if object_data.get('E'):
                # print object_data
                object_index = self.category_indexer(object_data)
                if object_index in self.cat_mapping.keys():
                    index = self.cat_mapping[object_index]
                    for ancestor in object_data.ancestors:
                        result = ancestor.find_child_category(index)
                        if result:
                            for member in object_data.members.values():
                                self.register_join_category(result, member)

        if object_data.is_product:
            categories = object_data.categories.values()
            object_data['catsum'] = '|'.join(SeqUtils.filter_unique_true(
                map(
                    lambda x: x.namesum,
                    categories
                )
            ))
            if self.DEBUG_WOO:
                self.register_message("catsum of %s is %s" % (
                    object_data.index, object_data.get('catsum')))

    def post_process_images(self, object_data):
        # self.register_message(object_data.index)
        object_data['imgsum'] = '|'.join(object_data.images.keys())

        if self.do_images and object_data.is_product and not object_data.is_variation:
            try:
                assert object_data['imgsum'], "All Products should have images"
            except AssertionError as exc:
                self.register_warning(exc, object_data)
                if self.strict:
                    self.raise_exception(exc)

        if self.DEBUG_WOO:
            self.register_message("imgsum of %s is %s" %
                                  (object_data.index, object_data.get('imgsum')))

    def post_process_attributes(self, object_data):
        # self.register_message(object_data.index)
        # print 'analysing attributes', object_data.get('codesum')

        for attr, data in object_data.attributes.items():

            if not data:
                continue
            values = '|'.join(map(str, data.get('values', [])))
            visible = data.get('visible', 1)
            variation = data.get('variation', 0)
            position = data.get('position', 0)
            default = data.get('default', '')

            if self.DEBUG_WOO:
                self.register_message(OrderedDict([
                    ('attr', attr),
                    ('values', values),
                    ('visible', visible),
                    ('variation', variation),
                    ('default', default)
                ]))

            if object_data.is_product:
                object_data['attribute:' + attr] = values
                object_data['attribute_data:' + attr] = '|'.join(map(str, [
                    position,
                    visible,
                    variation
                ]))
                object_data['attribute_default:' + attr] = default

            if object_data.is_variation:
                if variation:
                    object_data['meta:attribute_' + attr] = values

    def post_process_specials(self, object_data):
        # self.register_message(object_data.index)

        if not (object_data.is_product or object_data.is_variation):
            return

        ancestors = object_data.inheritence_ancestors
        for ancestor in reversed(ancestors):
            ancestor_specials = ancestor.specials
            for special in ancestor_specials:
                object_data.register_special(special)

        specials = object_data.specials
        object_data['spsum'] = '|'.join(specials)
        if self.DEBUG_SPECIAL:
            self.register_message("spsum of %s is %s" % (
                object_data.index, object_data.get('spsum')))

        for special in specials:
            # print "--> all specials: ", self.specials.keys()
            if special not in self.special_rules.keys():
                self.register_error(
                    "special %s does not exist " % special, object_data)
                continue

            if self.DEBUG_SPECIAL:
                self.register_message("special %s exists!" % special)

            if object_data.is_variable:
                # special is calculated for variations but not variables, which
                # is fine
                continue

            specialparams = self.special_rules[special]

            specialfrom = specialparams.start_time
            assert specialfrom, "special should have from: %s" % dict(
                specialparams)
            specialto = specialparams.end_time
            assert specialto, "special should have to: %s" % dict(
                specialparams)

            if not TimeUtils.has_happened_yet(specialto):
                if self.DEBUG_SPECIAL:
                    self.register_message(
                        "special %s is over: %s" % (special, specialto))
                continue

            special_from_string = TimeUtils.wp_time_to_string(
                specialfrom)
            special_to_string = TimeUtils.wp_time_to_string(
                specialto)
            if self.DEBUG_SPECIAL:
                self.register_message("special %s is from %s (%s) to %s (%s)" % (
                    special, specialfrom, special_from_string, specialto, special_to_string))

            for tier in ["RNS", "RPS", "WNS", "WPS", "DNS", "DPS"]:
                discount = specialparams.get(tier)
                if self.DEBUG_SPECIAL:
                    self.register_message(
                        "discount for %s: %s" %
                        (tier, discount))
                if not discount:
                    continue

                special_price = None

                percentages = SanitationUtils.find_all_percent(
                    discount)

                if self.DEBUG_SPECIAL:
                    self.register_message(
                        "percentages found for %s: %s" % (tier, percentages))

                if percentages:
                    coefficient = float(percentages[0]) / 100
                    regular_price_string = object_data.get(
                        tier[:-1] + "R")

                    if regular_price_string:
                        regular_price = float(
                            regular_price_string)
                        special_price = regular_price * coefficient
                else:
                    dollars = SanitationUtils.find_all_dollars(
                        discount)
                    if dollars:
                        dollar = float(
                            self.sanitize_cell(dollars[0]))
                        if dollar:
                            special_price = dollar

                if self.DEBUG_SPECIAL:
                    self.register_message(
                        "special  %s price is %s " % (tier, special_price))

                if special_price:
                    tier_key = tier
                    tier_from_key = tier[:-1] + "F"
                    tier_to_key = tier[:-1] + "T"
                    for key, value in {
                            tier_key: special_price,
                            tier_from_key: TimeUtils.local_to_server_time(specialfrom),
                            tier_to_key: TimeUtils.local_to_server_time(specialto)
                    }.items():
                        if self.DEBUG_SPECIAL:
                            self.register_message(
                                "special %s setting object_data[ %s ] to %s " %
                                (special, key, value)
                            )
                        object_data[key] = value

            break  # only applies first special

        for key, value in {
                'price': object_data.get('RNR'),
                'sale_price': object_data.get('RNS')
        }.items():
            if value is not None:
                object_data[key] = value

        for key, value in {
                'sale_price_dates_from': object_data.get('RNF'),
                'sale_price_dates_to': object_data.get('RNT')
        }.items():
            if value is not None:
                object_data[key] = TimeUtils.wp_time_to_string(
                    TimeUtils.server_to_local_time(value))

    def post_process_updated(self, object_data):
        object_data.inherit_key('Updated')

        if object_data.is_product:
            if object_data.is_updated:
                if isinstance(object_data, ImportShopProductVariationMixin):
                    # if object_data.is_variation:
                    self.register_updated_variation(object_data)
                else:
                    self.register_updated_product(object_data)

    def post_process_inventory(self, object_data):
        object_data.inherit_key('stock_status')

        if object_data.is_item:
            stock = object_data.get('stock')
            if stock or stock is "0":
                object_data['manage_stock'] = 'yes'
                if stock is "0":
                    object_data['stock_status'] = 'outofstock'
            else:
                object_data['manage_stock'] = 'no'

            if object_data.get('stock_status') != 'outofstock':
                object_data['stock_status'] = 'instock'

    def post_process_visibility(self, object_data):
        object_data.inherit_key('VISIBILITY')

        if object_data.is_item:
            visible = object_data.get('VISIBILITY')
            if visible is "hidden":
                object_data['catalog_visibility'] = "hidden"

    def get_special_category(self, name=None):
        # TODO: Generate HTML Descriptions properly
        if not name:
            category_name = self.specialsCategory
            search_data = {
                self.object_container.title_key: category_name
            }
            result = self.find_category(search_data)
            if not result:
                result = self.category_container(
                    {
                        'HTML Description': '',
                        'itemsum': category_name,
                        'ID': None,
                        'title': category_name,
                        'slug': SanitationUtils.slugify(category_name)
                    },
                    parent=self.root_data,
                    meta=[category_name, 'SP'],
                    rowcount=self.rowcount,
                    row=[]
                )
                self.rowcount += 1
            return result
        else:
            category_name = name
            search_data = {
                self.object_container.title_key: category_name
            }
            result = self.find_category(search_data)
            if not result:
                result = self.category_container(
                    {
                        'HTML Description': '',
                        'itemsum': category_name,
                        'ID': None,
                        'title': category_name,
                        'slug': SanitationUtils.slugify(category_name)
                    },
                    parent=self.get_special_category(),
                    meta=[category_name],
                    rowcount=self.rowcount,
                    row=[]
                )
                self.rowcount += 1
            return result

    def post_process_current_special(self, object_data):
        # TODO: actually create special category objects register objects to
        # those categories
        if object_data.is_product and self.current_special_groups:
            for special_group in self.current_special_groups:
                if object_data.has_special_fuzzy(special_group):
                    if self.DEBUG_SPECIAL:
                        self.register_message("%s matches special %s" % (
                            str(object_data), special_group))
                    if self.add_special_categories:
                        object_data['catsum'] = "|".join(
                            filter(None, [
                                object_data.get('catsum', ""),
                                self.specialsCategory,
                                object_data.extra_special_category
                            ])
                        )
                        special_category_object = self.get_special_category()
                        if self.DEBUG_SPECIAL:
                            self.register_message(
                                "joining special category: %s" % special_category_object.identifier)
                        self.register_join_category(
                            special_category_object, object_data)
                        assert special_category_object.index in object_data.categories
                        extra_special_category_object = self.get_special_category(
                            object_data.extra_special_category)
                        if self.DEBUG_SPECIAL:
                            self.register_message(
                                "joining extra special category: %s" % extra_special_category_object.identifier)
                        self.register_join_category(
                            extra_special_category_object, object_data)
                        assert extra_special_category_object.index in object_data.categories
                    if object_data.is_variation:
                        self.register_current_spec_var(object_data)
                    else:
                        self.register_current_spec_prod(object_data)
                    break
            # else:
                # print ("%s does not match special %s | %s"%(str(object_data), self.current_special, str(object_data.splist)))

    def post_process_shipping(self, object_data):
        if object_data.is_product and not object_data.is_variable:
            for key in ['weight', 'length', 'height', 'width']:
                if not object_data.get(key):
                    exc = UserWarning(
                        "All products must have shipping: %s" % key)
                    self.register_error(exc, object_data)
                    break

    def post_process_pricing(self, object_data):
        if object_data.is_product and not object_data.is_variable:
            for key in ['WNR']:
                if not object_data.get(key):
                    exc = UserWarning(
                        "All products must have pricing: %s" % key)
                    self.register_warning(exc, object_data)
                    break

    def analyse_rows(self, unicode_rows, **kwargs):
        objects = super(CsvParseWoo, self).analyse_rows(
            unicode_rows,
            **kwargs
        )

        # post processing

        if self.DEBUG_WOO:
            self.register_message("post_processing %d objects" % len(objects))


        for index, object_data in self.objects.items():
            # print '%s POST' % object_data.get_identifier()
            if self.do_dyns:
                self.post_process_dyns(object_data)
            self.post_process_categories(object_data)
            if self.do_images:
                self.post_process_images(object_data)
            self.post_process_attributes(object_data)
            if self.do_specials:
                self.post_process_specials(object_data)
            self.post_process_inventory(object_data)
            self.post_process_updated(object_data)
            self.post_process_visibility(object_data)
            self.post_process_shipping(object_data)
            if self.specialsCategory and self.current_special_groups:
                self.post_process_current_special(object_data)

        return objects

    def get_categories(self):
        exc = DeprecationWarning(
            "use .categories instead of .get_categories()")
        self.register_error(exc)
        return self.categories
        # return self.flatten(self.categories.values())

    def get_attributes(self):
        exc = DeprecationWarning(
            "use .attributes instead of .get_attributes()")
        self.register_error(exc)
        return self.attributes
        # return self.flatten(self.attributes.values())

    def get_variations(self):
        exc = DeprecationWarning(
            "use .variations instead of .get_variations()")
        self.register_error(exc)
        return self.variations


class CsvParseTT(CsvParseWoo):

    target_schema = "TT"

    def __init__(self, cols=None, defaults=None, **kwargs):
        if cols is None:
            cols = {}
        if defaults is None:
            defaults = {}
        # schema = "TT"

        extra_cols = ['RNRC', 'RPRC', 'WNRC', 'WPRC', 'DNRC', 'DPRC']
        extra_defaults = OrderedDict([])
        extra_taxo_subs = OrderedDict([
            # ('TechnoTan After Care', 'Tan Care > After Care'),
            # ('TechnoTan Pre Tan', 'Tan Care > Pre Tan'),
            # ('TechnoTan Tan Enhancement', 'Tan Care > Tan Enhancement'),
            # ('TechnoTan Hair Care', 'Tan Care > Hair Care'),
            # ('TechnoTan Application Equipment', 'Equipment > Application Equipment'),
            # ('TechnoTan Tanning Booths', 'Equipment > Tanning Booths'),
            ('TechnoTan Literature', 'Marketing > Literature'),
            ('TechnoTan Signage', 'Marketing > Signage'),
            ('TechnoTan Spray Tanning Packages', 'Packages'),
            # ('TechnoTan Solution', 'Solution'),
            # ('TechnoTan After Care', 'After Care'),
            # ('TechnoTan Pre Tan', 'Pre Tan'),
            # ('TechnoTan Tan Enhancement', 'Tan Enhancement'),
            # ('TechnoTan Hair Care', 'Hair Care'),
            # ('TechnoTan Tanning Accessories', 'Tanning Accessories'),
            # ('TechnoTan Technician Accessories', 'Technician Accessories'),
            # ('TechnoTan Application Equipment', 'Application Equipment'),
            # ('TechnoTan Tanning Booths', 'Tanning Booths'),
            # ('TechnoTan Apparel', 'Apparel'),
            ('TechnoTan ', ''),
        ])
        extra_item_subs = OrderedDict()

        extra_cat_maps = OrderedDict([
            ('CTPP', 'CTKPP')
        ])

        # cols = SeqUtils.combine_lists( cols, extra_cols )
        # defaults = SeqUtils.combine_ordered_dicts( defaults, extra_defaults )
        # taxo_subs = SeqUtils.combine_ordered_dicts( taxo_subs, extra_taxo_subs )
        # item_subs = SeqUtils.combine_ordered_dicts( item_subs, extra_item_subs )
        # cat_mapping = SeqUtils.combine_ordered_dicts( cat_mapping, extra_cat_maps )
        #
        #
        # super(CsvParseTT, self).__init__( cols, defaults, schema, import_name,\
        #         taxo_subs, item_subs, taxo_depth, item_depth, meta_width, \
        #         dprc_rules, dprp_rules, specials, cat_mapping)

        #
        cols = SeqUtils.combine_lists(cols, extra_cols)
        defaults = SeqUtils.combine_ordered_dicts(defaults, extra_defaults)
        kwargs['taxo_subs'] = SeqUtils.combine_ordered_dicts(
            kwargs.get('taxo_subs', {}), extra_taxo_subs)
        kwargs['item_subs'] = SeqUtils.combine_ordered_dicts(
            kwargs.get('item_subs', {}), extra_item_subs)
        kwargs['cat_mapping'] = SeqUtils.combine_ordered_dicts(
            kwargs.get('cat_mapping', {}), extra_cat_maps)
        kwargs['schema'] = "TT"
        # import_name = kwargs.pop('import_name', time.strftime("%Y-%m-%d %H:%M:%S") )
        super(CsvParseTT, self).__init__(cols, defaults, **kwargs)

        # if self.DEBUG_WOO:
        #     self.register_message("cat_mapping: %s" % str(cat_mapping))
        # if self.DEBUG_WOO:
        #     print "WOO initializing: "
        #     print "-> taxo_depth: ", self.taxo_depth
        #     print "-> item_depth: ", self.item_depth
        #     print "-> max_depth: ", self.max_depth
        #     print "-> meta_width: ", self.meta_width


class CsvParseVT(CsvParseWoo):

    target_schema = "VT"

    def __init__(self, cols=None, defaults=None, **kwargs):
        if cols is None:
            cols = {}
        if defaults is None:
            defaults = {}

        # schema = "VT"

        extra_cols = ['RNRC', 'RPRC', 'WNRC', 'WPRC', 'DNRC', 'DPRC']
        extra_defaults = OrderedDict([])
        extra_taxo_subs = OrderedDict([
            # ('VuTan After Care', 'Tan Care > After Care'),
            # ('VuTan Pre Tan', 'Tan Care > Pre Tan'),
            # ('VuTan Tan Enhancement', 'Tan Care > Tan Enhancement'),
            # ('VuTan Hair Care', 'Tan Care > Hair Care'),
            # ('VuTan Application Equipment', 'Equipment > Application Equipment'),
            # ('VuTan Tanning Booths', 'Equipment > Tanning Booths'),
            ('VuTan Literature', 'Marketing > Literature'),
            ('VuTan Signage', 'Marketing > Signage'),
            ('VuTan Spray Tanning Packages', 'Packages'),
            # ('VuTan Solution', 'Solution'),
            # ('VuTan After Care', 'After Care'),
            # ('VuTan Pre Tan', 'Pre Tan'),
            # ('VuTan Tan Enhancement', 'Tan Enhancement'),
            # ('VuTan Hair Care', 'Hair Care'),
            # ('VuTan Tanning Accessories', 'Tanning Accessories'),
            # ('VuTan Technician Accessories', 'Technician Accessories'),
            # ('VuTan Application Equipment', 'Application Equipment'),
            # ('VuTan Tanning Booths', 'Tanning Booths'),
            # ('VuTan Apparel', 'Apparel'),
            ('VuTan ', ''),
        ])
        extra_item_subs = OrderedDict()

        extra_cat_maps = OrderedDict()

        # cols = SeqUtils.combine_lists( cols, extra_cols )
        # defaults = SeqUtils.combine_ordered_dicts( defaults, extra_defaults )
        # taxo_subs = SeqUtils.combine_ordered_dicts( taxo_subs, extra_taxo_subs )
        # item_subs = SeqUtils.combine_ordered_dicts( item_subs, extra_item_subs )
        # cat_mapping = SeqUtils.combine_ordered_dicts( cat_mapping, extra_cat_maps )
        #
        # self.register_message("cat_mapping: %s" % str(cat_mapping))
        #
        # super(CsvParseVT, self).__init__( cols, defaults, schema, import_name,\
        #         taxo_subs, item_subs, taxo_depth, item_depth, meta_width, \
        #         dprc_rules, dprp_rules, specials, cat_mapping)
        #

        #
        cols = SeqUtils.combine_lists(cols, extra_cols)
        defaults = SeqUtils.combine_ordered_dicts(defaults, extra_defaults)
        kwargs['taxo_subs'] = SeqUtils.combine_ordered_dicts(
            kwargs.get('taxo_subs', {}), extra_taxo_subs)
        kwargs['item_subs'] = SeqUtils.combine_ordered_dicts(
            kwargs.get('item_subs', {}), extra_item_subs)
        kwargs['cat_mapping'] = SeqUtils.combine_ordered_dicts(
            kwargs.get('cat_mapping', {}), extra_cat_maps)
        kwargs['schema'] = "VT"
        # import_name = kwargs.pop('import_name', time.strftime("%Y-%m-%d %H:%M:%S") )
        super(CsvParseVT, self).__init__(cols, defaults, **kwargs)
