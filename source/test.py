class first(object):
    def method(self):
        print "first"

class second(first):
    pass

class third(first):
    a = 1

    def method(self):
        print "third", self.a

class fourth(second, third):
    pass

instance = fourth()
instance.method()