from context import TESTS_DATA_DIR, get_testdata, woogenerator

import unittest
# import argparse
import pytest
import logging
from woogenerator.namespace.core import (
    MatchNamespace, ParserNamespace, SettingsNamespaceProto, UpdateNamespace
)
from woogenerator.conf.parser import ArgumentParserCommon, ArgumentParserProd
from woogenerator.utils import Registrar, TimeUtils

def pytest_addoption(parser):
    # parser.addoption("--enable-debug", action="store_true", default=False, help="debug tests")
    parser.addoption("--run-slow", action="store_true", default=False, help="run slow tests")
    parser.addoption("--run-local", action="store_true", default=False, help="run slow tests")

def pytest_collection_modifyitems(config, items):
    if config.getoption("--run-slow"):
        # --runslow given in cli: do not skip slow tests
        return
    skip_slow = pytest.mark.skip(reason="need --runslow option to run")
    skip_local = pytest.mark.skip(reason="need --runlocal option to tun")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip_slow)
    for item in items:
        if "local" in item.keywords:
            item.add_marker(skip_local)

@pytest.fixture(scope="class")
def debug(request):
    response = request.config.getoption("--debug")
    request.cls.debug = response
