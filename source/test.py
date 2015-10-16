class first(object):
    def method(self):
        print "first"

class second(first):
    a = 2
    pass

class third(first):
    a = 3

    def method(self):
        print "third", self.a

class fourth(second, third):
    pass

instance = fourth()
instance.method()

print isinstance(instance, third)