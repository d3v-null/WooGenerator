# WooGenerator
Generates WooCommerce friendly CSV files from a Google Drive spreadsheet of products

This is a highly customized project for a very specific job and probably won't be very useful to other people

Install Instructions
====================

Google Drive API
----------------

pip install --upgrade google-api-python-client

https://developers.google.com/drive/web/quickstart/python

SSHTunnel
---------

ssh tunnel requres extra dependencies on cygwin. you need to install the mingw toolchain for your system, and openssl-dev

apt-cyg install libffi-devel


Other dependencies
------------------

pip install --upgrade sshtunnel tabulate dill pyyaml phpserialize uniqid python-wordpress-xmlrpc kitchen unicodecsv pymysql wordpress_json pympler httplib2
