""" Utils for dealing with inheritence in python """


class InheritenceUtils(object):  # pylint: disable=too-few-public-methods
    """ Groups inheritence utils together """
    @classmethod
    def gcs(cls, *instances):
        """
        Taken from http://stackoverflow.com/questions/25786566/greatest-common-superclass
        """
        # try:
        if len(instances) > 1:
            class_sets = [set([type(instance)]) for instance in instances]
            while not set.intersection(*class_sets):
                set_lengths = [len(class_set) for class_set in class_sets]
                for i, _ in enumerate(class_sets):
                    additions = []
                    for _class in class_sets[i]:
                        additions.extend(_class.__bases__)
                    # Registrar.register_message("additions: %s" % additions)
                    if additions:
                        class_sets[i].update(set(additions))
                if set_lengths == [len(class_set) for class_set in class_sets]:
                    return None
            return list(set.intersection(*class_sets))[0]
            # classes = [type(x).mro() for x in instances]
            # if classes:
            #     for x in classes.pop():
            #         if x == object:
            #             continue
            #         if all(x in mro for mro in classes):
            #             return x
            # assert False, "no common match found for %s" % str([type(x) for x in instances])
        elif len(instances) == 1:
            return type(instances[0])
        else:
            return None
        # except AssertionError, exc:
        #     Registrar.register_error(exc)
        #     raise exc
        #     return None


def overrides(interface_class):
    """ decorator for specifying where attribute overrides a superclass """
    def overrider(method):
        """ function returned by decorator """
        assert method.__name__ in dir(interface_class)
        return method
    return overrider
