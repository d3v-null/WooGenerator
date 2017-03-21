# -*- coding: utf-8 -*-
"""helper classes for parsing files and data."""

import sys
import os
MODULE_PATH = os.path.dirname(__file__)
MODULE_LOCATION = os.path.dirname(MODULE_PATH)
SUPERMODULE_PATH = os.path.dirname(MODULE_LOCATION)
sys.path.insert(0, SUPERMODULE_PATH)
import woogenerator

# sys.path.insert(0, MODULE_PATH)
