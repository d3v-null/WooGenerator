"""Introduces woo structure to shop classes"""
from collections import OrderedDict
import time
import re

from woogenerator.utils import listUtils, SanitationUtils, TimeUtils, PHPUtils, Registrar, descriptorUtils
from woogenerator.coldata import ColData_Woo
from woogenerator.parsing.abstract import ObjList, CsvParseBase
from woogenerator.parsing.tree import ItemList, TaxoList, ImportTreeObject, ImportTreeItem
from woogenerator.parsing.gen import CSVParse_Gen_Tree, CSVParse_Gen_Mixin
from woogenerator.parsing.gen import ImportGenTaxo, ImportGenObject, ImportGenFlat, ImportGenItem, ImportGenMixin
from woogenerator.parsing.shop import ImportShopMixin, ImportShopProductMixin, ImportShopProductSimpleMixin
from woogenerator.parsing.shop import ImportShopProductVariableMixin, ImportShopProductVariationMixin
from woogenerator.parsing.shop import ImportShopCategoryMixin, CsvParseShopMixin, ShopObjList
from woogenerator.parsing.flat import CSVParse_Flat, ImportFlat
from woogenerator.parsing.special import ImportSpecialGroup


class WooProdList(ItemList):
    report_cols = ColData_Woo.get_product_cols()


class WooCatList(TaxoList):
    report_cols = ColData_Woo.get_category_cols()


class WooVarList(ItemList):
    report_cols = ColData_Woo.get_variation_cols()


class ImportWooMixin(object):
    """ all things common to Woo import classes """

    wpidKey = 'ID'
    wpid = descriptorUtils.safe_key_property(wpidKey)
    titleKey = 'title'
    title = descriptorUtils.safe_key_property(titleKey)
    slugKey = 'slug'
    slug = descriptorUtils.safe_key_property(slugKey)
    verifyMetaKeys = [
        wpidKey,
        titleKey,
        slugKey
    ]

    def __init__(self, *args, **kwargs):
        if self.DEBUG_MRO:
            self.register_message('ImportWooMixin')
        super(ImportWooMixin, self).__init__(*args, **kwargs)
        self.specials = []

    @property
    def isUpdated(self):
        return "Y" == SanitationUtils.normalize_val(self.get('Updated', ""))

    @property
    def splist(self):
        schedule = self.get('SCHEDULE')
        if schedule:
            return filter(None, SanitationUtils.find_all_tokens(schedule))
        else:
            return []

    def has_special(self, special):
        return special in map(SanitationUtils.normalize_val, self.specials)

    def has_special_fuzzy(self, special):
        if isinstance(special, ImportSpecialGroup):
            special = special.ID
        for sp in [
            SanitationUtils.normalize_val(special) for special in self.specials
        ]:
            if special in sp:
                return True

    def register_special(self, special):
        if special not in self.specials:
            self.specials.append(special)

    def get_specials(self):
        exc = DeprecationWarning("use .specials instead of .get_specials()")
        self.register_error(exc)
        return self.specials


class ImportWooObject(ImportGenObject, ImportShopMixin, ImportWooMixin):
    container = ShopObjList

    verifyMetaKeys = ImportGenObject.verifyMetaKeys + ImportWooMixin.verifyMetaKeys

    def __init__(self, *args, **kwargs):
        if self.DEBUG_MRO:
            self.register_message('ImportWooObject')
        ImportGenObject.__init__(self, *args, **kwargs)
        ImportShopMixin.__init__(self, *args, **kwargs)
        ImportWooMixin.__init__(self, *args, **kwargs)
    # def __init__(self, *args, **kwargs):
    #     if self.DEBUG_MRO:
    #         self.register_message(' ')
    #     super(ImportWooObject, self).__init__(*args, **kwargs)
    #
    # @property
    # def verifyMetaKeys(self):
    #     superVerifyMetaKeys = super(ImportWooObject, self).verifyMetaKeys
    #     # superVerifyMetaKeys += ImportShopMixin.verifyMetaKeys
    #     superVerifyMetaKeys += ImportWooMixin.verifyMetaKeys
    #     return superVerifyMetaKeys


class ImportWooItem(ImportWooObject, ImportGenItem):
    verifyMetaKeys = ImportWooObject.verifyMetaKeys + ImportGenItem.verifyMetaKeys

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
    # def verifyMetaKeys(self):
    #     superVerifyMetaKeys = super(ImportWooItem, self).verifyMetaKeys
    #     # superVerifyMetaKeys += ImportGenItem.verifyMetaKeys
    #     return superVerifyMetaKeys


class ImportWooProduct(ImportWooItem, ImportShopProductMixin):
    isProduct = ImportShopProductMixin.isProduct
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
            names = listUtils.filter_unique_true(
                map(lambda x: x.name, ancestors_self))
            if names and len(names) < 2:
                line1 = names[0]
                name_delimeter = self.name_delimeter
                line2 = name_delimeter.join(names[1:])

        self['title_1'] = line1
        self['title_2'] = line2

        if not self.title:
            self.title = self.namesum

    def get_name_delimeter(self):
        exc = DeprecationWarning(
            "use .name_delimeter insetad of .get_name_delimeter()")
        self.register_error(exc)
        return self.name_delimeter

    @property
    def inheritenceAncestors(self):
        return listUtils.filter_unique_true(
            self.categories.values() + super(ImportWooProduct, self).inheritenceAncestors
        )

    def get_inheritance_ancestors(self):
        exc = DeprecationWarning(
            "use .inheritenceAncestors insetad of .get_inheritance_ancestors()")
        self.register_error(exc)
        return self.inheritenceAncestors
        # return listUtils.filter_unique_true(
        #     self.get_categories().values() + \
        #         super(ImportWooProduct, self).get_inheritance_ancestors()
        # )

    @property
    def extraSpecialCategory(self):
        ancestors_self = self.taxoAncestors + [self]
        names = listUtils.filter_unique_true(
            map(lambda x: x.fullname, ancestors_self))
        return "Specials > " + names[0] + " Specials"

    def get_extra_special_category(self):
        exc = DeprecationWarning(
            "use .extraSpecialCategory insetad of .get_extra_special_category()")
        self.register_error(exc)
        return self.extraSpecialCategory
        # ancestors_self = self.getTaxoAncestors() + [self]
        # names = listUtils.filter_unique_true(map(lambda x: x.fullname, ancestors_self))
        # return "Specials > " + names[0] + " Specials"


class ImportWooProductSimple(ImportWooProduct, ImportShopProductSimpleMixin):
    product_type = ImportShopProductSimpleMixin.product_type


class ImportWooProductVariable(
        ImportWooProduct, ImportShopProductVariableMixin):
    isVariable = ImportShopProductVariableMixin.isVariable
    product_type = ImportShopProductVariableMixin.product_type

    def __init__(self, *args, **kwargs):
        if self.DEBUG_MRO:
            self.register_message('ImportWooProductVariable')
        ImportWooProduct.__init__(self, *args, **kwargs)
        ImportShopProductVariableMixin.__init__(self, *args, **kwargs)


class ImportWooProductVariation(
        ImportWooProduct, ImportShopProductVariationMixin):
    isVariation = ImportShopProductVariationMixin.isVariation
    product_type = ImportShopProductVariationMixin.product_type


class ImportWooProductComposite(ImportWooProduct):
    product_type = 'composite'


class ImportWooProductGrouped(ImportWooProduct):
    product_type = 'grouped'


class ImportWooProductBundled(ImportWooProduct):
    product_type = 'bundle'


class ImportWooTaxo(ImportWooObject, ImportGenTaxo):
    verifyMetaKeys = ImportWooObject.verifyMetaKeys + ImportGenTaxo.verifyMetaKeys

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
    # def verifyMetaKeys(self):
    #     superVerifyMetaKeys = super(ImportWooTaxo, self).verifyMetaKeys
    #     # superVerifyMetaKeys += ImportGenTaxo.verifyMetaKeys
    #     return superVerifyMetaKeys


class ImportWooCategory(ImportWooTaxo, ImportShopCategoryMixin):
    isCategory = ImportShopCategoryMixin.isCategory
    isProduct = ImportShopCategoryMixin.isProduct

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
            if child.isCategory:
                if child.index == index:
                    return child
                else:
                    result = child.find_child_category(index)
                    if result:
                        return result
        return None

    @property
    def woo_cat_name(self):
        cat_layers = self.namesum.split(' > ')
        return cat_layers[-1]

    @property
    def index(self):
        return self.rowcount

    @property
    def identifier(self):
        identifier = super(ImportWooCategory, self).identifier
        return "|".join([
            self.codesum,
            'r:%s' % str(self.rowcount),
            'w:%s' % str(self.get(self.wpidKey)),
            self.woo_cat_name,
        ])

    @property
    def title(self):
        return self.woo_cat_name
    #
    # def __getitem__(self, key):
    #     if key == self.titleKey:
    #         return self.woo_cat_name
    #     else:
    #         return super(ImportWooCategory, self).__getitem__(key)


class CsvParseWooMixin(object):
    """ All the stuff that's common to Woo Parser classes """
    objectContainer = ImportWooObject

    def find_category(self, search_data):
        response = None
        matching_category_sets = []
        for search_key in [
            self.objectContainer.wpidKey,
            self.objectContainer.slugKey,
            self.objectContainer.titleKey,
            self.objectContainer.namesumKey,
        ]:
            value = search_data.get(search_key)
            if value:
                if Registrar.DEBUG_API:
                    Registrar.register_message(
                        "checking search key %s" % search_key)
                matching_categories = set()
                for category_key, category in self.categories.items():
                    if category.get(search_key) == value:
                        matching_categories.add(category_key)
                matching_category_sets.append(matching_categories)
        if Registrar.DEBUG_API:
            Registrar.register_message(
                "matching_category_sets: %s" % matching_category_sets)
        if matching_category_sets:
            matches = set.intersection(*matching_category_sets)
            if matches:
                assert len(matches) == 1, "should only have one match: %s " % [
                    self.categories.get(match) for match in matches]
                response = self.categories.get(list(matches)[0])
        return response

    @classmethod
    def get_title(cls, object_data):
        assert isinstance(object_data, ImportWooMixin)
        return object_data.title

    def get_parser_data(self, **kwargs):
        if Registrar.DEBUG_MRO:
            Registrar.register_message(' ')
        defaults = {
            self.objectContainer.wpidKey: '',
            self.objectContainer.slugKey: '',
            self.objectContainer.titleKey: ''
        }
        # super_data = super(CsvParseWooMixin, self).get_parser_data(**kwargs)
        # defaults.update(super_data)
        # if self.DEBUG_PARSER:
        # self.register_message("PARSER DATA: %s" % repr(defaults))
        return defaults

    def get_wpid(self, object_data):
        return object_data.wpid

    def clear_transients(self):
        pass


class CSVParse_Woo(CSVParse_Gen_Tree, CsvParseShopMixin, CsvParseWooMixin):
    objectContainer = ImportWooObject
    itemContainer = ImportWooItem
    productContainer = ImportWooProduct
    taxoContainer = ImportWooCategory
    simpleContainer = ImportWooProductSimple
    variableContainer = ImportWooProductVariable
    variationContainer = ImportWooProductVariation
    categoryContainer = ImportWooCategory
    compositeContainer = ImportWooProductComposite
    groupedContainer = ImportWooProductGrouped
    bundledContainer = ImportWooProductBundled
    category_indexer = Registrar.get_object_rowcount

    do_specials = True
    do_dyns = True
    specialsCategory = None
    add_special_categories = False

    @property
    def containers(self):
        return {
            'S': self.simpleContainer,
            'V': self.variableContainer,
            'I': self.variationContainer,
            'C': self.compositeContainer,
            'G': self.groupedContainer,
            'B': self.bundledContainer,
        }

    def __init__(self, cols, defaults, **kwargs):
        if self.DEBUG_MRO:
            self.register_message(' ')
        # print ("cat_mapping woo pre: %s" % str(cat_mapping))

        extra_cols = ['PA', 'VA', 'weight', 'length', 'width', 'height',
                      'stock', 'stock_status', 'Images', 'HTML Description',
                      'post_status']

        extra_defaults = OrderedDict([
            # ('post_status', 'publish'),
            # ('last_import', import_name),
        ])

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

        extra_item_subs = OrderedDict()

        extra_cat_maps = OrderedDict()

        cols = listUtils.combine_lists(cols, extra_cols)
        defaults = listUtils.combine_ordered_dicts(defaults, extra_defaults)
        kwargs['taxo_subs'] = listUtils.combine_ordered_dicts(
            kwargs.get('taxo_subs', {}), extra_taxo_subs)
        kwargs['item_subs'] = listUtils.combine_ordered_dicts(
            kwargs.get('item_subs', {}), extra_item_subs)
        # import_name = kwargs.pop('import_name', time.strftime("%Y-%m-%d %H:%M:%S") )
        if not kwargs.get('schema'):
            kwargs['schema'] = "TT"
        self.cat_mapping = listUtils.combine_ordered_dicts(
            kwargs.pop('cat_mapping', {}), extra_cat_maps)
        self.dprc_rules = kwargs.pop('dprc_rules', {})
        self.dprpRules = kwargs.pop('dprpRules', {})
        self.specialRules = kwargs.pop('specialRules', {})
        self.current_special_groups = kwargs.pop(
            'current_special_groups', None)
        # self.specialGroups = kwargs.pop('specialGroups', {})
        if not kwargs.get('meta_width'):
            kwargs['meta_width'] = 2
        if not kwargs.get('itemDepth'):
            kwargs['itemDepth'] = 2
        if not kwargs.get('taxoDepth'):
            kwargs['taxoDepth'] = 2

        super(CSVParse_Woo, self).__init__(cols, defaults, **kwargs)

        # self.category_indexer = self.productIndexer

        # if self.DEBUG_WOO:
        #     self.register_message("cat_mapping woo post: %s" % str(cat_mapping))

        # if self.DEBUG_WOO:
        #     print "WOO initializing: "
        #     print "-> taxoDepth: ", self.taxoDepth
        #     print "-> itemDepth: ", self.itemDepth
        #     print "-> maxDepth: ", self.maxDepth
        #     print "-> meta_width: ", self.meta_width

    def clear_transients(self):
        if self.DEBUG_MRO:
            self.register_message(' ')
        CSVParse_Gen_Tree.clear_transients(self)
        CsvParseShopMixin.clear_transients(self)
        CsvParseWooMixin.clear_transients(self)
        self.special_items = OrderedDict()
        self.updated_products = OrderedDict()
        self.updated_variations = OrderedDict()
        self.onspecial_products = OrderedDict()
        self.onspecial_variations = OrderedDict()

    def register_object(self, object_data):
        CSVParse_Gen_Tree.register_object(self, object_data)
        CsvParseShopMixin.register_object(self, object_data)

    def get_parser_data(self, **kwargs):
        if self.DEBUG_MRO:
            self.register_message(' ')
        super_data = {}
        for base_class in reversed(CSVParse_Woo.__bases__):
            if hasattr(base_class, 'get_parser_data'):
                super_data.update(base_class.get_parser_data(self, **kwargs))
        # super_data = CsvParseWooMixin.get_parser_data(self, **kwargs)
        # super_data.update(CsvParseShopMixin.get_parser_data(self, **kwargs))
        # super_data.update(CSVParse_Gen_Tree.get_parser_data(self, **kwargs))
        if self.DEBUG_PARSER:
            self.register_message("PARSER DATA: %s" % repr(super_data))
        return super_data

    def get_new_obj_container(self, *args, **kwargs):
        if self.DEBUG_MRO:
            self.register_message(' ')
        container = super(CSVParse_Woo, self).get_new_obj_container(
            *args, **kwargs)
        try:
            all_data = args[0]
        except IndexError:
            exc = UserWarning("all_data not specified")
            self.register_error(exc)
            raise exc

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
            registerName='specials'
        )
        object_data.register_special(special)

    # def register_product(self, object_data):
    #     assert isinstance(object_data, ImportWooProduct)
    #     if not object_data.isVariation:
    #         super(CSVParse_Woo, self).register_product(object_data)

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
            registerName='updated_products',
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
            registerName='updated_variations',
            singular=True
        )

    def register_current_special_product(self, object_data):
        assert \
            isinstance(object_data, ImportWooProduct), \
            "object should be ImportWooProduct not %s" % str(type(object_data))
        assert \
            not isinstance(object_data, ImportWooProductVariation), \
            "object should not be ImportWooProductVariation"
        self.register_anything(
            object_data,
            self.onspecial_products,
            registerName='onspecial_products',
            singular=True
        )

    def register_current_special_variation(self, object_data):
        assert \
            isinstance(object_data, ImportWooProductVariation), \
            "object should be ImportWooProductVariation not %s" % str(
                type(object_data))
        self.register_anything(
            object_data,
            self.onspecial_variations,
            registerName='onspecial_variations',
            singular=True
        )

    def process_images(self, object_data):
        imglist = filter(None, SanitationUtils.find_all_images(
            object_data.get('Images', '')))
        for image in imglist:
            self.register_image(image, object_data)
        this_images = object_data.images
        if object_data.isItem:
            ancestors = object_data.itemAncestors
        else:
            ancestors = []
        for ancestor in ancestors:
            ancestor_images = ancestor.images
            if len(this_images) and not len(ancestor_images):
                self.register_image(this_images[0], ancestor)
            elif not len(this_images) and len(ancestor_images):
                self.register_image(ancestor_images[0], object_data)

    def process_categories(self, object_data):
        if object_data.isProduct:
            for ancestor in object_data.taxoAncestors:
                if ancestor.name and self.category_indexer(
                        ancestor) not in self.categories:
                    self.register_category(ancestor)
                self.join_category(ancestor, object_data)

        if object_data.get('E'):
            if self.DEBUG_WOO:
                self.register_message("HAS EXTRA LAYERS")
            if object_data.isProduct:
                # self.register_message("ANCESTOR NAMESUM: %s" % str(object_data.get_ancestor_key('namesum')))
                # self.register_message("ANCESTOR DESCSUM: %s" % str(object_data.get_ancestor_key('descsum')))
                # self.register_message("ANCESTOR CATSUM: %s" % str(object_data.get_ancestor_key('catsum')))
                # self.register_message("ANCESTOR ITEMSUM: %s" % str(object_data.get_ancestor_key('itemsum')))
                # self.register_message("ANCESTOR TAXOSUM: %s" % str(object_data.get_ancestor_key('taxosum')))
                # self.register_message("ANCESTOR NAME: %s" % str(object_data.get_ancestor_key('name')))
                taxo_ancestor_names = [ancestorData.get(
                    'name') for ancestorData in object_data.taxoAncestors]
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

                extra_depth = self.taxoDepth - 1
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
                        self.register_message(
                            "did not find sibling: %s" % extra_layer.identifier)

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
            # todo maybe something with extra categories

    def process_variation(self, varData):
        pass

    def process_attributes(self, object_data):
        ancestors = \
            object_data.inheritenceAncestors + \
            [object_data]

        palist = listUtils.filter_unique_true(map(
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

        if object_data.isVariation:
            parent_data = object_data.parent
            assert parent_data and parent_data.isVariable
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
        super(CSVParse_Woo, self).process_object(object_data)
        assert issubclass(
            object_data.__class__, ImportWooObject), "object_data should subclass ImportWooObject not %s" % object_data.__class__.__name__
        self.process_categories(object_data)
        if object_data.isProduct:
            cat_skus = map(
                lambda x: x.codesum,
                object_data.categories.values())
            if self.DEBUG_WOO:
                self.register_message("categories: {}".format(cat_skus))
        if object_data.isVariation:
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

    def add_dyn_rules(self, itemData, dynType, ruleIDs):
        rules = {
            'dprc': self.dprc_rules,
            'dprp': self.dprpRules
        }[dynType]
        dyn_list_index = dynType + 'list'
        dyn_id_list_index = dynType + 'IDlist'
        if not itemData.get(dyn_list_index):
            itemData[dyn_list_index] = []
        if not itemData.get(dyn_id_list_index):
            itemData[dyn_id_list_index] = []
        for rule_id in ruleIDs:
            if rule_id not in itemData[dyn_id_list_index]:
                itemData[dyn_id_list_index] = rule_id
            # print "adding %s to %s" % (rule_id, itemData['codesum'])
            rule = rules.get(rule_id)
            if rule:
                if rule not in itemData[dyn_list_index]:
                    itemData[dyn_list_index].append(rule)
            else:
                self.register_error(
                    'rule should exist: %s' %
                    rule_id, itemData)

    def post_process_dyns(self, object_data):
        # self.register_message(object_data.index)
        if object_data.isProduct:
            ancestors = object_data.inheritenceAncestors + [object_data]
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

            if(object_data.get('dprclist', '')):
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

            if(object_data.get('dprplist', '')):
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
        if object_data.isCategory:
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

        if object_data.isProduct:
            categories = object_data.categories.values()
            object_data['catsum'] = '|'.join(listUtils.filter_unique_true(
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
        object_data['imgsum'] = '|'.join(filter(
            None,
            object_data.images
        ))

        if self.do_images and object_data.isProduct and not object_data.isVariation:
            try:
                assert object_data['imgsum'], "All Products should have images"
            except AssertionError as exc:
                self.register_warning(exc, object_data)

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

            if object_data.isProduct:
                object_data['attribute:' + attr] = values
                object_data['attribute_data:' + attr] = '|'.join(map(str, [
                    position,
                    visible,
                    variation
                ]))
                object_data['attribute_default:' + attr] = default

            if object_data.isVariation:
                if variation:
                    object_data['meta:attribute_' + attr] = values

    def post_process_specials(self, object_data):
        # self.register_message(object_data.index)

        if object_data.isProduct or object_data.isVariation:

            ancestors = object_data.inheritenceAncestors
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
                if special in self.specialRules.keys():
                    if self.DEBUG_SPECIAL:
                        self.register_message("special %s exists!" % special)

                    if not object_data.isVariable:

                        specialparams = self.specialRules[special]

                        specialfrom = specialparams.start_time
                        assert specialfrom, "special should have from: %s" % dict(
                            specialparams)
                        specialto = specialparams.end_time
                        assert specialto, "special should have to: %s" % dict(
                            specialparams)

                        if(not TimeUtils.has_happened_yet(specialto)):
                            if self.DEBUG_SPECIAL:
                                self.register_message(
                                    "special %s is over: %s" % (special, specialto))
                            continue
                        else:
                            special_from_string = TimeUtils.wp_time_to_string(
                                specialfrom)
                            special_to_string = TimeUtils.wp_time_to_string(
                                specialto)
                            if self.DEBUG_SPECIAL:
                                self.register_message("special %s is from %s (%s) to %s (%s)" % (
                                    special, specialfrom, special_from_string, specialto, special_to_string))

                        for tier in ["RNS", "RPS", "WNS", "WPS", "DNS", "DPS"]:
                            discount = specialparams.get(tier)
                            if discount:
                                # print "discount is ", discount
                                special_price = None

                                percentages = SanitationUtils.find_all_percent(
                                    discount)
                                # print "percentages are", percentages
                                if percentages:
                                    coefficient = float(percentages[0]) / 100
                                    regular_price_string = object_data.get(
                                        tier[:-1] + "R")
                                    # print "regular_price_string",
                                    # regular_price_string
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

                                if special_price:
                                    if self.DEBUG_SPECIAL:
                                        self.register_message(
                                            "special %s price is %s " % (special, special_price))
                                    tier_key = tier
                                    tier_from_key = tier[:-1] + "F"
                                    tier_to_key = tier[:-1] + "T"
                                    for key, value in {
                                        tier_key: special_price,
                                        tier_from_key: TimeUtils.localToServerTime(specialfrom),
                                        tier_to_key: TimeUtils.localToServerTime(specialto)
                                    }.items():
                                        if self.DEBUG_SPECIAL:
                                            self.register_message(
                                                "special %s setting object_data[ %s ] to %s " % (special, key, value))
                                        object_data[key] = value
                                    # object_data[tier_key] = special_price
                                    # object_data[tier_from_key] = specialfrom
                                    # object_data[tier_to_key] = specialto
                    break
                    # only applies first special

                else:
                    self.register_error(
                        "special %s does not exist " % special, object_data)

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
            # object_data['price'] = object_data.get('RNR')
            # object_data['sale_price'] = object_data.get('RNS')
            # object_data['sale_price_dates_from'] = object_data.get('RNF')
            # object_data['sale_price_dates_to'] = object_data.get('RNT')

    def post_process_updated(self, object_data):
        object_data.inherit_key('Updated')

        if object_data.isProduct:
            if object_data.isUpdated:
                if isinstance(object_data, ImportShopProductVariationMixin):
                    # if object_data.isVariation:
                    self.register_updated_variation(object_data)
                else:
                    self.register_updated_product(object_data)

    def post_process_inventory(self, object_data):
        object_data.inherit_key('stock_status')

        if object_data.isItem:
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

        if object_data.isItem:
            visible = object_data.get('VISIBILITY')
            if visible is "hidden":
                object_data['catalog_visibility'] = "hidden"

    def get_special_category(self, name=None):
        # TODO: Generate HTML Descriptions properly
        if not name:
            category_name = self.specialsCategory
            search_data = {
                self.objectContainer.titleKey: category_name
            }
            result = self.find_category(search_data)
            if not result:
                result = self.categoryContainer(
                    {
                        'HTML Description': '',
                        'itemsum': category_name,
                        'ID': None,
                        'title': category_name,
                        'slug': SanitationUtils.slugify(category_name)
                    },
                    parent=self.rootData,
                    meta=[category_name, 'SP'],
                    rowcount=self.rowcount,
                    row=[]
                )
                self.rowcount += 1
            return result
        else:
            category_name = name
            search_data = {
                self.objectContainer.titleKey: category_name
            }
            result = self.find_category(search_data)
            if not result:
                result = self.categoryContainer(
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
        if object_data.isProduct and self.current_special_groups:
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
                                object_data.extraSpecialCategory
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
                            object_data.extraSpecialCategory)
                        if self.DEBUG_SPECIAL:
                            self.register_message(
                                "joining extra special category: %s" % extra_special_category_object.identifier)
                        self.register_join_category(
                            extra_special_category_object, object_data)
                        assert extra_special_category_object.index in object_data.categories
                    if object_data.isVariation:
                        self.register_current_special_variation(object_data)
                    else:
                        self.register_current_special_product(object_data)
                    break
            # else:
                # print ("%s does not match special %s | %s"%(str(object_data), self.current_special, str(object_data.splist)))

    def post_process_shipping(self, object_data):
        if object_data.isProduct and not object_data.isVariable:
            for key in ['weight', 'length', 'height', 'width']:
                if not object_data.get(key):
                    exc = UserWarning(
                        "All products must have shipping: %s" % key)
                    self.register_error(exc, object_data)
                    break

    def post_process_pricing(self, object_data):
        if object_data.isProduct and not object_data.isVariable:
            for key in ['WNR']:
                if not object_data.get(key):
                    exc = UserWarning(
                        "All products must have pricing: %s" % key)
                    self.register_warning(exc, object_data)
                    break

    def analyse_file(self, file_name, encoding=None, limit=None):
        objects = super(CSVParse_Woo, self).analyse_file(
            file_name, encoding=encoding, limit=limit)
        # post processing
        # for itemData in self.taxos.values() + self.items.values():
        # print 'POST analysing product', itemData.codesum, itemData.namesum

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
            if self.specialsCategory and self.current_special:
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


class CSVParse_TT(CSVParse_Woo):

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

        # cols = listUtils.combine_lists( cols, extra_cols )
        # defaults = listUtils.combine_ordered_dicts( defaults, extra_defaults )
        # taxo_subs = listUtils.combine_ordered_dicts( taxo_subs, extra_taxo_subs )
        # item_subs = listUtils.combine_ordered_dicts( item_subs, extra_item_subs )
        # cat_mapping = listUtils.combine_ordered_dicts( cat_mapping, extra_cat_maps )
        #
        #
        # super(CSVParse_TT, self).__init__( cols, defaults, schema, import_name,\
        #         taxo_subs, item_subs, taxoDepth, itemDepth, meta_width, \
        #         dprc_rules, dprpRules, specials, cat_mapping)

        #
        cols = listUtils.combine_lists(cols, extra_cols)
        defaults = listUtils.combine_ordered_dicts(defaults, extra_defaults)
        kwargs['taxo_subs'] = listUtils.combine_ordered_dicts(
            kwargs.get('taxo_subs', {}), extra_taxo_subs)
        kwargs['item_subs'] = listUtils.combine_ordered_dicts(
            kwargs.get('item_subs', {}), extra_item_subs)
        kwargs['cat_mapping'] = listUtils.combine_ordered_dicts(
            kwargs.get('cat_mapping', {}), extra_cat_maps)
        kwargs['schema'] = "TT"
        # import_name = kwargs.pop('import_name', time.strftime("%Y-%m-%d %H:%M:%S") )
        super(CSVParse_TT, self).__init__(cols, defaults, **kwargs)

        # if self.DEBUG_WOO:
        #     self.register_message("cat_mapping: %s" % str(cat_mapping))
        # if self.DEBUG_WOO:
        #     print "WOO initializing: "
        #     print "-> taxoDepth: ", self.taxoDepth
        #     print "-> itemDepth: ", self.itemDepth
        #     print "-> maxDepth: ", self.maxDepth
        #     print "-> meta_width: ", self.meta_width


class CSVParse_VT(CSVParse_Woo):

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

        # cols = listUtils.combine_lists( cols, extra_cols )
        # defaults = listUtils.combine_ordered_dicts( defaults, extra_defaults )
        # taxo_subs = listUtils.combine_ordered_dicts( taxo_subs, extra_taxo_subs )
        # item_subs = listUtils.combine_ordered_dicts( item_subs, extra_item_subs )
        # cat_mapping = listUtils.combine_ordered_dicts( cat_mapping, extra_cat_maps )
        #
        # self.register_message("cat_mapping: %s" % str(cat_mapping))
        #
        # super(CSVParse_VT, self).__init__( cols, defaults, schema, import_name,\
        #         taxo_subs, item_subs, taxoDepth, itemDepth, meta_width, \
        #         dprc_rules, dprpRules, specials, cat_mapping)
        #

        #
        cols = listUtils.combine_lists(cols, extra_cols)
        defaults = listUtils.combine_ordered_dicts(defaults, extra_defaults)
        kwargs['taxo_subs'] = listUtils.combine_ordered_dicts(
            kwargs.get('taxo_subs', {}), extra_taxo_subs)
        kwargs['item_subs'] = listUtils.combine_ordered_dicts(
            kwargs.get('item_subs', {}), extra_item_subs)
        kwargs['cat_mapping'] = listUtils.combine_ordered_dicts(
            kwargs.get('cat_mapping', {}), extra_cat_maps)
        kwargs['schema'] = "VT"
        # import_name = kwargs.pop('import_name', time.strftime("%Y-%m-%d %H:%M:%S") )
        super(CSVParse_VT, self).__init__(cols, defaults, **kwargs)
