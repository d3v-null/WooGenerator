class first:
    a = 'first'
    def __init__(self):
        print "first"
        print self.a

class second(first):
    # a = 'second'
    pass

class third:
    a = 'third'
    def __init__(self):
        print "third"
        print self.a

class fourth(second, third):
    # a = 'fourth'
    pass

instance = fourth()
