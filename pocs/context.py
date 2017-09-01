# -*- coding: utf-8 -*-

import sys
import os
sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..')))
import woogenerator

TESTS_DATA_DIR = os.path.join(
    os.path.abspath(os.path.dirname(os.path.dirname(__file__))),
    'tests',
    'sample_data'
)

def get_testdata(*paths):
    """Return test data"""
    path = os.path.join(TESTS_DATA_DIR, *paths)
    with open(path, 'rb') as f:
        return f.read()
