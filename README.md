# WooGenerator
Generates WooCommerce friendly CSV files from a Google Drive spreadsheet of products

This is a highly customized project for a very specific job and probably won't be very useful to other people

Install Instructions
====================

Google Drive API
----------------

pip install --upgrade google-api-python-client

refer to these instructions on setting it up:
https://developers.google.com/drive/web/quickstart/python

SSHTunnel
---------

ssh tunnel requres extra dependencies on cygwin. you need to install the mingw toolchain for your system, and openssl-dev

apt-cyg install libffi-devel


Other dependencies
------------------

pip install --upgrade
  bleach
  bzr
  dill
  httplib2
  iptcinfo
  kitchen
  pgi
  phpserialize
  pillow
  piexif
  pygobject3
  pympler
  pymysql
  python-wordpress-xmlrpc
  pyyaml
  sshtunnel
  tabulate
  unicodecsv
  uniqid
  urllib3  
  woocommerce
  wordpress_json
  exitstatus

Cygwin Packages
---------------
apt-cyg install
  cygwin-devel
  exiv2
  gcc-core
  gexiv2
  libboost_python-devel
  libexiv2-devel
  mingw64-i686-binutils
  mingw64-i686-gcc-core
  mingw64-i686-headers
  mingw64-i686-openssl
  mingw64-i686-pkg-config
  mingw64-i686-runtime
  mingw64-i686-windows-default-manifest
  mingw64-i686-winpthreads
  mingw64-i686-zlib
  mingw64-x86_64-binutils
  mingw64-x86_64-exiv2
  mingw64-x86_64-gcc-core
  mingw64-x86_64-headers
  mingw64-x86_64-openssl
  mingw64-x86_64-pkg-config
  mingw64-x86_64-runtime
  mingw64-x86_64-windows-default-manifest
  mingw64-x86_64-winpthreads
  mingw64-x86_64-zlib
  openssh
  openssl
  openssl-devel
  python
  python-cffi
  python-gi
  python-imaging
  python-ply
  python-pycparser
  rsync
  scons
  w32api-headers
  w32api-runtime

 Other Libraries
 ---------------

 Testing
 ----
to test X
```
python test/testX.py
```
