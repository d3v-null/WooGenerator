# -*- coding: utf-8 -*-
from __future__ import absolute_import

import inspect
import os


class DebugUtils(object):

    @classmethod
    def get_procedure(cls, level=1):
        try:
            procedure = inspect.stack()[level][3]
            # return procedure
            path = os.path.relpath(os.path.realpath(inspect.stack()[level][1]))
            line = inspect.stack()[level][2]
            baseline = "%s:%s" % (path, line)
            return ".".join([baseline, str(procedure)])
        except BaseException:
            return None

    @classmethod
    def get_caller_procedure(cls, level=0):
        return cls.get_procedure(3 + level)

    @classmethod
    def get_caller_procedures(cls, levels=2):
        procedures = map(cls.get_caller_procedure, range(1, levels + 1))
        return ">".join(reversed(filter(None, procedures)))

    @classmethod
    def hashify(cls, in_str):
        out_str = "\n"
        out_str += "#" * (len(in_str) + 4) + "\n"
        out_str += "# " + in_str + " #\n"
        out_str += "#" * (len(in_str) + 4) + "\n"
        return out_str
