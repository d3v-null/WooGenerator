#!/usr/bin/env python

import os
import re
from setuptools import setup

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

# Get version from __init__.py file
VERSION = ""
with open("woogenerator/__init__.py", "r") as fd:
    try:
        VERSION = re.search(
            r"^__version__\s*=\s*['\"]([^\"]*)['\"]", fd.read(),
            re.MULTILINE
        )
        VERSION = VERSION.group(1)
    except AttributeError:
        pass

if not VERSION:
    raise RuntimeError("Cannot find version information")

# Get long description
README = open(os.path.join(os.path.dirname(__file__), "README.md")).read()

requirements = [

]

setup(
    name='WooGenerator',
    version=VERSION,
    description='Synchronizes user and product data from disparate APIs',
    long_description=README,
    author='Derwent McElhinney',
    author_email='derwent@laserphile.com',
    url='https://github.com/derwentx/WooGenerator',
    packages=[
        'woogenerator', 'tests'
    ],
    install_requires=[
        'bleach',
        'ConfigArgParse',
        'exitstatus',
        'httplib2',
        'kitchen',
        'npyscreen',
        'paramiko',
        'phpserialize',
        'piexif',
        'PyMySQL',
        'requests',
        'simplejson',
        'sshtunnel',
        'tabulate',
        'unicodecsv',
        'google_api_python_client',
        'PyYAML',
        'wordpress-api',
        'pyxero',
        'bs4',
        'dill',
        'lxml'
    ],
    setup_requires=['pytest-runner'],
    tests_require=[
        'pytest'
    ],
)
