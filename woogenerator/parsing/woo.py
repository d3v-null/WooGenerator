"""
Introduce woo structure to shop classes.
"""
from __future__ import absolute_import

import re
from collections import OrderedDict
from copy import deepcopy
from past.builtins import cmp

from six import integer_types

from ..coldata import (ColDataAttachment, ColDataProductMeridian,
                       ColDataProductVariationMeridian, ColDataWcProdCategory)
from ..utils import (DescriptorUtils, PHPUtils, Registrar, SanitationUtils,
                     SeqUtils, TimeUtils)
from ..utils.inheritence import call_bases, collect_bases
from .abstract import ObjList
from .gen import CsvParseGenTree, ImportGenItem, ImportGenObject, ImportGenTaxo
from .shop import (CsvParseShopMixin, ImportShopAttachmentMixin,
                   ImportShopCategoryMixin, ImportShopMixin,
                   ImportShopProductMixin, ImportShopProductSimpleMixin,
                   ImportShopProductVariableMixin,
                   ImportShopProductVariationMixin, ShopCatList,
                   ShopImgListMixin, ShopMixin, ShopObjList, ShopProdList)
from .special import ImportSpecialGroup
from .tree import CsvParseTreeMixin, ImportTreeItem


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
            SanitationUtils.normalize_val(special)
            for special in self.specials
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


class ImportWooChildMixin(object):
    """
    Base mixin class for woo objects which have parents.
    """
    def to_dict(self):
        response = {}
        if hasattr(self, 'parent'):
            if self.parent and hasattr(self.parent, 'wpid'):
                if self.parent.wpid and int(self.parent.wpid) != -1:
                    response['parent_id'] = self.parent.wpid
        return response


class ImportWooObject(ImportGenObject, ImportShopMixin, ImportWooMixin):
    container = ShopObjList

    def to_dict(self):
        return collect_bases(ImportWooObject.__bases__, 'to_dict', {}, self)

    verify_meta_keys = SeqUtils.combine_lists(
        ImportGenObject.verify_meta_keys,
        ImportWooMixin.verify_meta_keys
    )

    def __init__(self, data, *args, **kwargs):
        if (
            args and hasattr(data, 'get')
            and data.get(self.rowcount_key) is None
            and self.menu_order_key in data
        ):
            data[self.rowcount_key] = data[self.menu_order_key]
        call_bases(
            ImportWooObject.__bases__, '__init__', self, data, *args, **kwargs
        )

    def process_meta(self):
        call_bases(ImportWooObject.__bases__, 'process_meta', self)
        if not isinstance(self.menu_order_key, integer_types):
            self.menu_order = self.rowcount


class ImportWooImg(ImportWooObject, ImportShopAttachmentMixin):
    verify_meta_keys = ImportShopAttachmentMixin.verify_meta_keys
    index = ImportShopAttachmentMixin.index
    is_product = False
    is_category = False

    wpid_key = 'id'
    slug_key = 'slug'
    title_key = 'title'

    def __init__(self, *args, **kwargs):
        call_bases(ImportWooImg.__bases__, '__init__', self, *args, **kwargs)

    @classmethod
    def get_identifier(cls, data):
        return "|".join(SeqUtils.filter_unique_true([
            str(data.get(cls.rowcount_key)),
            cls.get_index(data)
        ]))

    @property
    def identifier(self):
        return self.get_identifier(self)

    def process_meta(self):
        call_bases(ImportWooImg.__bases__, 'process_meta', self)


ImportWooObject.attachment_indexer = ImportWooImg.get_identifier


class WooListMixin(object):
    coldata_class = ColDataProductMeridian
    coldata_cat_class = ColDataWcProdCategory
    coldata_var_class = ColDataProductVariationMeridian
    coldata_img_class = ColDataAttachment
    supported_type = ImportWooObject


class ImportWooItem(ImportWooObject, ImportGenItem):

    verify_meta_keys = SeqUtils.combine_lists(
        ImportWooObject.verify_meta_keys,
        ImportGenItem.verify_meta_keys
    )
    is_item = ImportGenItem.is_item

    def __init__(self, *args, **kwargs):
        # TODO: why arent' bases ImportWooItem.__bases__ ?
        call_bases([ImportWooObject], '__init__', self, *args, **kwargs)


class ImportWooProduct(ImportWooItem, ImportShopProductMixin):
    is_product = ImportShopProductMixin.is_product
    name_delimeter = ' - '

    def __init__(self, data, *args, **kwargs):
        if self.product_type:
            data['prod_type'] = self.product_type
        call_bases(
            ImportWooProduct.__bases__, '__init__', self, data, *args, **kwargs
        )

    def process_meta(self):
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
            self.categories.values()
            + super(ImportWooProduct, self).inheritence_ancestors
        )

    def get_extra_special_category_components(self, specials_name):
        components = {}
        ancestors_self = self.taxo_ancestors + [self]
        fullname_ancestor = None
        code_ancestor = None

        for ancestor in ancestors_self:
            if not fullname_ancestor and ancestor.fullname:
                fullname_ancestor = ancestor
            if not code_ancestor and ancestor.code:
                code_ancestor = ancestor
            if fullname_ancestor and code_ancestor:
                break
        if fullname_ancestor:
            fullname_component = ' '.join([
                fullname_ancestor.fullname, specials_name
            ])
        if code_ancestor:
            code_component = code_ancestor.code
        components[self.fullname_key] = fullname_component
        components[self.code_key] = code_component
        return components

    def to_dict(self):
        response = collect_bases(
            ImportWooProduct.__bases__, 'to_dict', {}, self
        )
        response['category_objects'] = sorted(
            response['category_objects'],
            lambda cat_a, cat_b: cmp(cat_a.wpid, cat_b.wpid)
        )
        return response


class WooProdList(ShopProdList, WooListMixin):
    coldata_class = WooListMixin.coldata_class
    supported_type = ImportWooProduct
    report_cols = coldata_class.get_col_data_native('report')


ImportWooProduct.container = WooProdList


class ImportWooProductSimple(ImportWooProduct, ImportShopProductSimpleMixin):
    product_type = ImportShopProductSimpleMixin.product_type


class ImportWooProductVariable(
        ImportWooProduct, ImportShopProductVariableMixin):
    is_variable = ImportShopProductVariableMixin.is_variable
    product_type = ImportShopProductVariableMixin.product_type
    variation_indexer = ImportWooObject.get_sku
    hidden_keys = SeqUtils.combine_lists(
        ImportWooProduct.hidden_keys,
        ImportShopProductVariableMixin.hidden_keys
    )

    def __init__(self, *args, **kwargs):
        call_bases(
            ImportWooProductVariable.__bases__, '__init__',
            self, *args, **kwargs
        )

    def to_dict(self):
        return collect_bases(
            ImportWooProductVariable.__bases__, 'to_dict', {}, self
        )


class ImportWooProductVariation(
        ImportWooProduct, ImportShopProductVariationMixin, ImportWooChildMixin
):
    is_variation = ImportShopProductVariationMixin.is_variation
    product_type = ImportShopProductVariationMixin.product_type
    variation_indexer = ImportWooObject.get_sku

    verify_meta_keys = SeqUtils.combine_lists(
        ImportWooProduct.verify_meta_keys,
        ImportShopProductVariationMixin.verify_meta_keys
    )
    verify_meta_keys.remove(ImportWooProduct.title_key)
    verify_meta_keys.remove(ImportWooProduct.slug_key)
    verify_meta_keys.remove(ImportWooProduct.namesum_key)

    def to_dict(self):
        return collect_bases(
            ImportWooProductVariation.__bases__, 'to_dict', {}, self
        )


class WooVarList(ShopProdList, WooListMixin):
    supported_type = ImportWooProductVariation
    coldata_class = WooListMixin.coldata_var_class
    report_cols = coldata_class.get_col_data_native('report')


ImportWooProductVariation.container = WooVarList


class ImportWooProductComposite(ImportWooProduct):
    product_type = 'simple'
    # product_type = 'composite'


class ImportWooProductGrouped(ImportWooProduct):
    product_type = 'grouped'


class ImportWooProductBundled(ImportWooProduct):
    product_type = 'simple'
    # product_type = 'bundle'


class ImportWooTaxo(ImportWooObject, ImportGenTaxo):
    # TODO: fix diamond inheritence. inherits from GenObject twice
    namesum_key = ImportGenTaxo.namesum_key
    namesum = DescriptorUtils.safe_key_property(namesum_key)

    verify_meta_keys = SeqUtils.combine_lists(
        ImportWooObject.verify_meta_keys,
        ImportGenTaxo.verify_meta_keys
    )
    is_taxo = ImportGenTaxo.is_taxo

    def __init__(self, *args, **kwargs):
        call_bases([ImportWooObject], '__init__', self, *args, **kwargs)


class ImportWooCategory(
    ImportWooTaxo, ImportShopCategoryMixin, ImportWooChildMixin
):
    is_category = ImportShopCategoryMixin.is_category
    is_product = ImportShopCategoryMixin.is_product
    cat_name = ImportShopCategoryMixin.cat_name

    def __init__(self, *args, **kwargs):
        # TODO why isn't bases just ImportWooCategory.__bases__ ?
        call_bases(
            [ImportWooTaxo, ImportShopCategoryMixin], '__init__',
            self, *args, **kwargs
        )

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
        call_bases(ImportWooCategory.__bases__, 'process_meta', self)
        if not self.title:
            self.title = self.fullname
        if not self.cat_name:
            cat_layers = self.namesum.split(self.name_delimeter)
            self.cat_name = cat_layers[-1]

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

    def to_dict(self):
        return collect_bases(ImportWooCategory.__bases__, 'to_dict', {}, self)


class WooCatList(ShopCatList, WooListMixin):
    coldata_class = WooListMixin.coldata_cat_class
    supported_type = ImportWooCategory
    report_cols = coldata_class.get_col_data_native('report')


ImportWooCategory.container = WooCatList


class WooImgList(ObjList, WooListMixin, ShopImgListMixin):
    coldata_class = WooListMixin.coldata_img_class
    supported_type = ImportWooImg
    report_cols = coldata_class.get_col_data_native('report')


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
    coldata_var_class = ShopMixin.coldata_var_class
    coldata_sub_img_class = ShopMixin.coldata_sub_img_class
    taxo_container = ImportWooCategory
    category_container = ImportWooCategory
    category_indexer = Registrar.get_object_rowcount
    attachment_container = ImportWooImg
    attachment_indexer = attachment_container.get_identifier

    @property
    def cat_search_keys(self):
        return [
            self.category_container.wpid_key,
            self.category_container.slug_key,
            self.category_container.title_key,
            self.category_container.namesum_key,
        ]

    @property
    def img_search_keys(self):
        return [
            self.attachment_container.attachment_id_key,
            # self.attachment_container.slug_key,
            # self.attachment_container.title_key,
            self.attachment_container.file_name_key,
            self.attachment_container.source_url_key
        ]

    @property
    def prod_search_keys(self):
        return [
            self.object_container.wpid_key,
            self.object_container.slug_key,
            self.object_container.title_key
        ]

    def find_category(self, search_data):
        registry = self.taxos
        return self.find_object(search_data, registry, self.cat_search_keys)

    def find_image(self, search_data):
        registry = self.attachments
        return self.find_object(search_data, registry, self.img_search_keys)

    def find_product(self, search_data):
        registry = self.products
        return self.find_object(search_data, registry, self.prod_search_keys)

    @classmethod
    def get_title(cls, object_data):
        assert isinstance(object_data, ImportWooMixin)
        return object_data.title

    def get_defaults(self, **kwargs):
        return {
            self.object_container.wpid_key: '',
            self.object_container.slug_key: '',
            self.object_container.title_key: ''
        }

    @property
    def img_defaults(self):
        if not hasattr(self, '_coldata_img_class_defaults'):
            self._coldata_img_class_defaults = (
                self.coldata_img_class.get_col_values_native('default')
            )
        return deepcopy(self._coldata_img_class_defaults)

    @property
    def cat_defaults(self):
        if not hasattr(self, '_coldata_cat_class_defaults'):
            self._coldata_cat_class_defaults = (
                self.coldata_cat_class.get_col_values_native('default')
            )
        return deepcopy(self._coldata_cat_class_defaults)

    @property
    def var_defaults(self):
        if not hasattr(self, '_coldata_var_class_defaults'):
            self._coldata_var_class_defaults = (
                self.coldata_var_class.get_col_values_native('default')
            )
        return deepcopy(self._coldata_var_class_defaults)

    def process_image(self, img_raw_data, object_data=None, **kwargs):
        img_index = self.attachment_container.get_file_name(img_raw_data)
        if self.DEBUG_IMG:
            if object_data:
                identifier = object_data.identifier
                self.register_message(
                    "%s attached to %s"
                    % (identifier, img_index)
                )
            else:
                self.register_message(
                    "creating image %s" % (img_index)
                )
            self.register_message("PROCESS IMG: %s" % repr(img_raw_data))

        if object_data and getattr(object_data, 'is_taxo'):
            img_raw_data['rowcount'] = -1
        elif not img_raw_data.get('rowcount'):
            img_raw_data['rowcount'] = self.rowcount
            self.rowcount += 1

        img_data = None
        img_index = self.attachment_indexer(img_raw_data)
        if img_index:
            img_data = self.attachments.get(img_index)
        if not img_data:
            img_data = self.find_image(img_raw_data)
        if not img_data and img_raw_data.get('type') == 'sub-image':
            img_data = self.find_image(img_raw_data)
        if not img_data:
            if self.DEBUG_IMG:
                self.register_message("SEARCH IMG NOT FOUND")
            row_data = deepcopy(img_raw_data)
            kwargs['defaults'] = self.img_defaults
            kwargs['row_data'] = row_data
            kwargs['parent'] = self.root_data
            kwargs['container'] = self.attachment_container
            kwargs['rowcount'] = img_raw_data['rowcount']

            try:
                img_data = self.new_object(
                    **kwargs
                )
            except UserWarning as exc:
                warn = UserWarning("could not create image: %s" % exc)
                self.register_error(
                    warn
                )
                if 1 or self.strict:
                    self.raise_exception(warn)
                return

        else:
            if self.DEBUG_IMG:
                self.register_message("FOUND IMG: %s" % repr(img_data))
            # TODO: update found image with img_raw_data
            img_data.update(img_raw_data)
            # TODO: process meta?
            img_data.process_meta()

        self.register_attachment(img_data, object_data)

        return img_data

    def get_empty_category_instance(self, **kwargs):
        if not kwargs.get('container'):
            kwargs['container'] = self.category_container
        if not kwargs.get('row_data'):
            kwargs['row_data'] = {}
        if not kwargs['row_data'].get('type'):
            kwargs['row_data']['type'] = 'category'
        return CsvParseTreeMixin.get_empty_instance(self, **kwargs)

    def get_empty_attachment_instance(self, **kwargs):
        if not kwargs.get('container'):
            kwargs['container'] = self.attachment_container
        if not kwargs.get('row_data'):
            kwargs['row_data'] = {}
        if not kwargs['row_data'].get('type'):
            kwargs['row_data']['type'] = 'image'
        return CsvParseTreeMixin.get_empty_instance(self, **kwargs)

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
    attachment_container = CsvParseWooMixin.attachment_container
    category_indexer = CsvParseWooMixin.category_indexer
    attachment_indexer = CsvParseWooMixin.attachment_indexer
    coldata_class = CsvParseWooMixin.coldata_class
    coldata_cat_class = CsvParseWooMixin.coldata_cat_class
    coldata_img_class = CsvParseWooMixin.coldata_img_class
    coldata_var_class = CsvParseWooMixin.coldata_var_class

    # Whether to calculate the special prices of objects
    do_specials = True
    do_dyns = True
    # This is the name of the parent specials category, e.g. "Specials",
    # Where the children are special categories, e.g. "Product A Specials"
    specials_category_name = None
    # Whether to add products into special categories if they are on special
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
            'M': self.attachment_container,
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
            # (
            #     'Tanning Advantage Application Equipment',
            #     'Equipment > Application Equipment'
            # ),
            # (
            #     'Generic Application Equipment',
            #     'Equipment > Application Equipment'
            # ),
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

        self.cat_mapping = SeqUtils.combine_ordered_dicts(
            kwargs.pop('cat_mapping', {}), extra_cat_maps)
        self.dprc_rules = kwargs.pop('dprc_rules', {})
        self.dprp_rules = kwargs.pop('dprp_rules', {})
        self.special_rules = kwargs.pop('special_rules', {})
        self.current_special_groups = kwargs.pop(
            'current_special_groups', None)
        if kwargs.get('meta_width') is None:
            kwargs['meta_width'] = 2
        if kwargs.get('item_depth') is None:
            kwargs['item_depth'] = 2
        if kwargs.get('taxo_depth') is None:
            kwargs['taxo_depth'] = 2

        super(CsvParseWoo, self).__init__(cols, defaults, **kwargs)

    def clear_transients(self):
        call_bases(CsvParseWoo.__bases__, 'clear_transients', self)
        self.special_items = OrderedDict()
        self.updated_products = OrderedDict()
        self.updated_variations = OrderedDict()
        self.onspecial_products = OrderedDict()
        self.onspecial_variations = OrderedDict()

    def register_object(self, object_data):
        call_bases(CsvParseWoo.__bases__, 'register_object', self, object_data)

    def get_defaults(self, **kwargs):
        return collect_bases(
            CsvParseWoo.__bases__, 'get_defaults', {}, self, **kwargs
        )

    def get_parser_data(self, **kwargs):
        parser_data = kwargs.get('row_data', {})
        return collect_bases(
            CsvParseWoo.__bases__, 'get_parser_data', parser_data,
            self,  **kwargs
        )

    def get_new_obj_container(self, data, *args, **kwargs):
        # TODO: isn't this exactly what gen does?
        container = super(CsvParseWoo, self).get_new_obj_container(
            data, *args, **kwargs
        )

        if (
            issubclass(container, ImportTreeItem)
            and self.schema in data
        ):
            woo_type = data[self.schema]
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
        """
        Associate `object_data` with a particular special rule ID.
        """
        try:
            special = str(special)
            assert isinstance(special, (str, unicode)), \
                'Special must be a string not {}'.format(
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

    def process_attachments(self, object_data):
        img_paths = filter(None, SanitationUtils.find_all_images(
            object_data.get('Images', '')))
        for image in img_paths:
            # TODO: create image object and register if not exist
            img_data = {
                'file_path': image,
                'rowcount': self.rowcount
            }
            self.process_image(img_data, object_data)
        this_attachments = object_data.attachments.values()
        if object_data.is_item:
            ancestors = object_data.item_ancestors
        else:
            ancestors = []
        for ancestor in ancestors:
            ancestor_attachments = ancestor.attachments.values()
            # TODO: create image object and register if not exist
            if len(this_attachments) and not len(ancestor_attachments):
                self.process_image(this_attachments[0], ancestor)
            elif not len(this_attachments) and len(ancestor_attachments):
                self.process_image(ancestor_attachments[0], object_data)

    def process_categories(self, object_data):
        if object_data.is_product:
            for ancestor in object_data.taxo_ancestors:
                if ancestor.name and self.category_indexer(
                        ancestor) not in self.categories:
                    self.register_category(ancestor)
                self.join_category(ancestor, object_data)

        # TODO: update description if category is part of a special

        # TODO: fix this fucking mess
        # TODO: fix for VuTan
        if object_data.get('E'):
            if self.DEBUG_WOO:
                self.register_message("HAS EXTRA LAYERS")
            if object_data.is_product:
                taxo_ancestor_names = [ancestorData.get(
                    'name') for ancestorData in object_data.taxo_ancestors]

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
                    if (
                        re.search(
                            'Bronzing Powder', extra_taxo_name, flags=re.I
                        )
                        or re.search('Foundation', extra_taxo_name, flags=re.I)
                    ):
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
                elif re.search(
                    'Natural Soy Wax Candles', extra_taxo_name, flags=re.I
                ):
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
                elif re.search(
                    'Tanbience Product Packs', extra_taxo_name, flags=re.I
                ):
                    extra_taxo_name = ''

                extra_depth = self.taxo_depth - 1
                extra_rowcount = object_data.rowcount
                extra_stack = self.stack.get_left_slice(extra_depth)
                extra_name = ' '.join(
                    filter(None, [extra_name, extra_taxo_name, extra_suffix]))
                extra_name = SanitationUtils.strip_extra_whitespace(extra_name)
                extra_code = object_data.code
                extra_row = object_data.row

                siblings = extra_stack.get_top().children

                extra_layer = None
                for sibling in siblings:
                    if sibling.name == extra_name:
                        extra_layer = sibling

                if extra_layer:
                    if self.DEBUG_WOO:
                        self.register_message(
                            "found sibling: %s" % extra_layer.identifier)
                    if self.category_indexer(
                            extra_layer) not in self.categories:
                        self.register_category(extra_layer)
                else:
                    if self.DEBUG_WOO:
                        identifier = (
                            extra_layer.identifier if extra_layer else 'None'
                        )
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

                    if self.DEBUG_WOO:
                        self.register_message(
                            "extra_layer name: %s; type: %s" % (
                                str(extra_name), str(type(extra_layer))
                            )
                        )
                    assert issubclass(type(extra_layer), ImportGenTaxo)

                    self.register_category(extra_layer)

                self.join_category(extra_layer, object_data)

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
                    "could not decode attributes: %s | %s" % (attrs, exc),
                    object_data
                )

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
        if self.DEBUG_WOO:
            self.register_message(object_data.index)
        try:
            super(CsvParseWoo, self).process_object(object_data)
        except AssertionError as exc:
            if (
                hasattr(object_data, 'parent')
                and object_data.parent.namesum == self.specials_category_name
            ):
                raise UserWarning(
                    (
                        "Could not add specials category %s.\n%s\n"
                        "Make sure the specials category '%s' exists at the "
                        "bottom of the generator file"
                    ) % (
                        str(object_data),
                        str(exc),
                        object_data.namesum
                    )
                )
            raise UserWarning(
                "could not refresh stack with %s.\n%s" % (
                    str(object_data),
                    str(exc)
                )
            )
        assert issubclass(object_data.__class__, ImportWooObject), \
            "object_data should subclass ImportWooObject not %s" % (
                object_data.__class__.__name__
            )
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
            self.process_attachments(object_data)
            if self.DEBUG_WOO:
                self.register_message("attachments: {}".format(
                    object_data.attachments
                ))
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
                    pricing_rules[PHPUtils.ruleset_uniqid()] = (
                        PHPUtils.unserialize(rule.to_pricing_rule())
                    )

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
                            for member in object_data.members:
                                self.register_join_category(result, member)

        if object_data.is_product:
            categories = object_data.categories.values()
            object_data['catsum'] = '|'.join(SeqUtils.filter_unique_true([
                category.namesum for category in categories
            ]))
            if self.DEBUG_WOO:
                self.register_message("catsum of %s is %s" % (
                    object_data.index, object_data.get('catsum')))

    def post_process_attachments(self, object_data):
        # self.register_message(object_data.index)
        object_data['imgsum'] = '|'.join([
            attachment.file_name
            for attachment in object_data.attachments.values()
        ])

        if (
            self.do_images and object_data.is_product
            and not object_data.is_variation
        ):
            try:
                assert object_data['imgsum'], \
                    "All Products should have attachments"
            except AssertionError as exc:
                self.register_warning(exc, object_data)
                if self.strict:
                    self.raise_exception(exc)

        if self.DEBUG_WOO:
            self.register_message(
                "imgsum of %s is %s" % (
                    object_data.index, object_data.get('imgsum')
                )
            )

    def post_process_attributes(self, object_data):
        # self.register_message(object_data.index)
        # print 'analysing attributes', object_data.get('codesum')
        if not getattr(object_data, 'is_product'):
            return
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
        """
        Determine which special rule IDs apply to this object and
        calculate the discounted prices.
        """
        # self.register_message(object_data.index)

        if not (object_data.is_product or object_data.is_variation):
            return

        if not self.do_specials:
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

            if self.DEBUG_SPECIAL:
                self.register_message("special %s is from %s to %s" % (
                    special, specialfrom, specialto))

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
                        tier_from_key: specialfrom,
                        tier_to_key: specialto,
                    }.items():
                        if self.DEBUG_SPECIAL:
                            self.register_message(
                                "special %s setting object_data[ %s ] to %s " %
                                (special, key, value)
                            )
                        object_data[key] = value

            break  # only applies first special

        for key, value in {
            'sale_price': object_data.get('RNS'),
            'sale_price_dates_from': object_data.get('RNF'),
            'sale_price_dates_to': object_data.get('RNT')
        }.items():
            if value is not None:
                object_data[key] = value

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

    def get_special_category(self, special_components=None):
        """
        Find the special category corresponding to the product type specified
        in `special_components` if it exists, else create it.
        If special_components is None, then find the parent special category.
        """
        # TODO: Generate HTML Descriptions properly
        if not special_components:
            category_fullname = self.specials_category_name
            search_data = {
                self.object_container.title_key: category_fullname
            }
            result = self.find_category(search_data)
            if not result:
                kwargs = OrderedDict()
                search_data[self.schema] = ''
                kwargs['defaults'] = self.cat_defaults
                kwargs['row_data'] = search_data
                kwargs['container'] = self.category_container
                kwargs['parent'] = self.root_data
                kwargs['meta'] = [category_fullname, 'SP']
                result = self.new_object(rowcount=self.rowcount, **kwargs)
                self.process_object(result)
                self.register_object(result)
                self.rowcount += 1
            return result
        else:
            category_fullname = special_components.get(
                self.category_container.fullname_key
            )
            search_data = {
                self.object_container.title_key: category_fullname
            }
            result = self.find_category(search_data)
            if not result:
                kwargs = OrderedDict()
                search_data[self.schema] = ''
                kwargs['defaults'] = self.cat_defaults
                kwargs['row_data'] = search_data
                kwargs['container'] = self.category_container
                kwargs['parent'] = self.get_special_category()
                category_code = special_components.get(
                    self.category_container.code_key
                )
                kwargs['meta'] = [category_fullname, category_code]
                result = self.new_object(rowcount=self.rowcount, **kwargs)
                self.process_object(result)
                self.register_object(result)
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
                        special_category_object = self.get_special_category()
                        if self.DEBUG_SPECIAL:
                            self.register_message(
                                "joining special category: %s" % (
                                    special_category_object.identifier))
                        self.register_join_category(
                            special_category_object, object_data)
                        assert \
                            special_category_object.index \
                            in object_data.categories
                        extra_special_category_object = \
                            self.get_special_category(
                                object_data
                                .get_extra_special_category_components(
                                    self.specials_category_name))
                        if self.DEBUG_SPECIAL:
                            self.register_message(
                                "joining extra special category: %s" % (
                                    extra_special_category_object.identifier))
                        self.register_join_category(
                            extra_special_category_object, object_data)
                        assert \
                            extra_special_category_object.index \
                            in object_data.categories
                        object_data['catsum'] = "|".join(
                            filter(None, [
                                object_data.get('catsum', ""),
                                special_category_object.namesum,
                                extra_special_category_object.namesum
                            ])
                        )
                    if object_data.is_variation:
                        self.register_current_spec_var(object_data)
                    else:
                        self.register_current_spec_prod(object_data)
                    break

    def post_process_shipping(self, object_data):
        if object_data.is_product and not object_data.is_variable:
            for key in ['weight', 'length', 'height', 'width']:
                if not object_data.get(key):
                    exc = UserWarning(
                        "All products must have shipping: %s" % key)
                    self.register_error(exc, object_data)
                    break

    def post_process_pricing(self, object_data):
        for key, value in {
            'regular_price': object_data.get('RNR'),
        }.items():
            if value is not None:
                object_data[key] = value

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
                self.post_process_attachments(object_data)
            self.post_process_attributes(object_data)
            self.post_process_specials(object_data)
            self.post_process_pricing(object_data)
            self.post_process_inventory(object_data)
            self.post_process_updated(object_data)
            self.post_process_visibility(object_data)
            self.post_process_shipping(object_data)
            if self.specials_category_name and self.current_special_groups:
                self.post_process_current_special(object_data)

        return objects


class CsvParseMeridian(CsvParseWoo):
    pass


class CsvParseTT(CsvParseMeridian):

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
            ('TechnoTan Literature', 'Marketing > Literature'),
            ('TechnoTan Signage', 'Marketing > Signage'),
            ('TechnoTan Spray Tanning Packages', 'Packages'),
            ('TechnoTan ', ''),
        ])
        extra_item_subs = OrderedDict()

        extra_cat_maps = OrderedDict([
            ('CTPP', 'CTKPP')
        ])

        cols = SeqUtils.combine_lists(cols, extra_cols)
        defaults = SeqUtils.combine_ordered_dicts(defaults, extra_defaults)
        kwargs['taxo_subs'] = SeqUtils.combine_ordered_dicts(
            kwargs.get('taxo_subs', {}), extra_taxo_subs)
        kwargs['item_subs'] = SeqUtils.combine_ordered_dicts(
            kwargs.get('item_subs', {}), extra_item_subs)
        kwargs['cat_mapping'] = SeqUtils.combine_ordered_dicts(
            kwargs.get('cat_mapping', {}), extra_cat_maps)
        kwargs['schema'] = "TT"
        super(CsvParseTT, self).__init__(cols, defaults, **kwargs)


class CsvParseVT(CsvParseMeridian):

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
            ('VuTan Literature', 'Marketing > Literature'),
            ('VuTan Signage', 'Marketing > Signage'),
            ('VuTan Spray Tanning Packages', 'Packages'),
            ('VuTan ', ''),
        ])
        extra_item_subs = OrderedDict()

        extra_cat_maps = OrderedDict()

        cols = SeqUtils.combine_lists(cols, extra_cols)
        defaults = SeqUtils.combine_ordered_dicts(defaults, extra_defaults)
        kwargs['taxo_subs'] = SeqUtils.combine_ordered_dicts(
            kwargs.get('taxo_subs', {}), extra_taxo_subs)
        kwargs['item_subs'] = SeqUtils.combine_ordered_dicts(
            kwargs.get('item_subs', {}), extra_item_subs)
        kwargs['cat_mapping'] = SeqUtils.combine_ordered_dicts(
            kwargs.get('cat_mapping', {}), extra_cat_maps)
        kwargs['schema'] = "VT"
        super(CsvParseVT, self).__init__(cols, defaults, **kwargs)
