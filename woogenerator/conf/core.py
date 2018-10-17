import os

from .__init__ import MODULE_LOCATION

# Core configuration
CONF_DIR = os.path.join(MODULE_LOCATION, 'conf')
assert os.path.exists(CONF_DIR), "conf dir: %s should exist" % CONF_DIR
DEFAULTS_COMMON_PATH = os.path.join(CONF_DIR, 'defaults_common.yaml')
DEFAULTS_PROD_PATH = os.path.join(CONF_DIR, 'defaults_prod.yaml')
DEFAULTS_USER_PATH = os.path.join(CONF_DIR, 'defaults_user.yaml')

# User controlled configuration
DEFAULT_TESTMODE = True
DEFAULT_LOCAL_WORK_DIR = os.path.expanduser('~/Documents/woogenerator')
DEFAULT_LOCAL_PROD_PATH = 'conf_prod.yaml'
DEFAULT_LOCAL_PROD_TEST_PATH = 'conf_prod_test.yaml'
DEFAULT_LOCAL_USER_PATH = 'conf_user.yaml'
DEFAULT_LOCAL_USER_TEST_PATH = 'conf_user_test.yaml'
DEFAULT_LOCAL_IN_DIR = 'input/'
DEFAULT_LOCAL_OUT_DIR = 'output/'
DEFAULT_LOCAL_LOG_DIR = 'logs/'
DEFAULT_LOCAL_PICKLE_DIR = 'pickles/'
DEFAULT_LOCAL_IMG_RAW_DIR = 'imgs_raw/'
DEFAULT_LOCAL_IMG_CMP_DIR = 'imgs_cmp/'
DEFAULT_MASTER_NAME = 'master'
DEFAULT_SLAVE_NAME = 'slave'
