"""Module for namespaces of woogenerator."""

import sys
import os

MODULE_PATH = os.path.dirname(__file__)
MODULE_LOCATION = os.path.dirname(MODULE_PATH)
PACKAGE_LOCATION = os.path.dirname(MODULE_LOCATION)
sys.path.insert(0, PACKAGE_LOCATION)
