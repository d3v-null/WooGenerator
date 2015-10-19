from collections import OrderedDict

def combineOrderedDicts(a, b):
    if not a:
        return b if b else OrderedDict()
    if not b: return a
    c = OrderedDict(b.items())
    for key, value in a.items():
        c[key] = value
    return c

a = OrderedDict([
    (1, 'a'),
    (2, 'b')
])

b = OrderedDict([
    (1, 'c'),
])

print a
print b
print combineOrderedDicts(a, b)
print combineOrderedDicts(b, a)