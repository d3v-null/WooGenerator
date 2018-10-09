""" Utils for dealing with inheritence in python """


class InheritenceUtils(object):  # pylint: disable=too-few-public-methods
    """ Groups inheritence utils together """
    @classmethod
    def gcs(cls, *instances):
        """
        Taken from
        http://stackoverflow.com/questions/25786566/greatest-common-superclass
        """
        if len(instances) == 0:
            return
        if len(instances) == 1:
            return type(instances[0])
        class_sets = [set([type(instance)]) for instance in instances]
        while not set.intersection(*class_sets):
            set_lengths = [len(class_set) for class_set in class_sets]
            for i, _ in enumerate(class_sets):
                additions = []
                for _class in class_sets[i]:
                    additions.extend(_class.__bases__)
                if additions:
                    class_sets[i].update(set(additions))
            if set_lengths == [len(class_set) for class_set in class_sets]:
                return None
        return list(set.intersection(*class_sets))[0]


def overrides(interface_class):
    """ decorator for specifying where attribute overrides a superclass """
    def overrider(method):
        """ function returned by decorator """
        assert method.__name__ in dir(interface_class)
        return method
    return overrider


def call_bases(bases, func_name, *args, **kwargs):
    for base in bases:
        if hasattr(base, func_name):
            getattr(base, func_name)(*args, **kwargs)


def collect_bases(bases, func_name, collection, *args, **kwargs):
    for base in bases:
        if hasattr(base, func_name):
            collection.update(getattr(base, func_name)(*args, **kwargs))
    return collection
