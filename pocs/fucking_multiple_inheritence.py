class Mixin_A(object):
    mixin_property = None


class Mixin_B(object):
    mixin_property = True


class A(Mixin_A):
    pass


class B(A, Mixin_B):
    mixin_property = Mixin_B.mixin_property

print "mixin property of A is", repr(A.mixin_property)
a = A()
print "mixin property of a is", repr(a.mixin_property)

print "mixin property of B is", repr(B.mixin_property)
b = B()
print "mixin property of b is", repr(b.mixin_property)

#######

print "real world example"


class ImportShopMixin(object):
    is_variation = None


class ImportShopProductMixin(object):
    pass


class ImportShopProductVariationMixin(object):
    is_variation = True


class ImportWooApiObject(object):
    pass


class ImportWooApiProduct(ImportWooApiObject, ImportShopProductMixin):
    pass


class ImportWooApiProductVariation(
        ImportWooApiProduct, ImportShopProductVariationMixin):
    is_variation = ImportShopProductVariationMixin.is_variation

print "is_variation of ImportWooApiProductVariation", ImportWooApiProductVariation.is_variation
