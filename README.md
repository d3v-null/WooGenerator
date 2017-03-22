# WooGenerator

Generates WooCommerce friendly CSV files from a Google Drive spreadsheet of products

***!!! Warning !!!***
I've tried to make this codebase as modular as possible, but in reality there is
so much TechnoTan specific code that it would take quite a bit of modification
to get this to work on another site.

I really suggest not modifying this until you fully understand what's going on.
There is a lot of nasty code in here because it was one of my first major Python
projects.

How it works
====
source/generator.py downloads products from the Google Drive spreadsheet, parses the
products, and creates a csv file that can be imported in to WooCommerce.

The "Meridian Product Heirarchy" spreadsheet is in a custom tree-like format
created specifically for this project. The spreadsheet was designed in a way
that minmized redundancy since the product codes and names for entire categories
were being changed regularly while they were being created. The resulting
format is quite difficult to parse since it is a hybrid of a tree-like structure
and a flat file database that contains all the information for generating product
categories, and variable products / subproducts with different information
pertaining to each different website / database in the single file. This means
that depending on how the sheet is parsed, it can give you information about
products pertaining to MYOB, TechnoTan, VuTan etc. where the same product has
slightly different properties in each database.

Since each database handles products differently, a different class is required
to analyse the spreadsheet for each database. These are as follows:

| Class | Usage |
| --- | --- |
| `myo.CsvParseMyo` | All meridian products for MYOB |
| `woo.CsvParseTT` | All TechnoTan products for WooCommerce |
| `woo.CsvParseVT` | All VuTan products for WooCommerce |



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

make sure you are using python2:

`python -c "import sys; print sys.version"`

Now you can install packages

`sudo -H pip2 install --upgrade $(cat requirements.txt)`

Todo: Are these still dependencies?
```
  pygobject3 \
  iptcinfo \
  bzr \
```

Cygwin Packages
---------------
If you're running cygwin:

```
  apt-cyg install \
    cygwin-devel \
    exiv2 \
    gcc-core \
    gexiv2 \
    libboost_python-devel \
    libexiv2-devel \
    mingw64-i686-binutils \
    mingw64-i686-gcc-core \
    mingw64-i686-headers \
    mingw64-i686-openssl \
    mingw64-i686-pkg-config \
    mingw64-i686-runtime \
    mingw64-i686-windows-default-manifest \
    mingw64-i686-winpthreads \
    mingw64-i686-zlib \
    mingw64-x86_64-binutils \
    mingw64-x86_64-exiv2 \
    mingw64-x86_64-gcc-core \
    mingw64-x86_64-headers \
    mingw64-x86_64-openssl \
    mingw64-x86_64-pkg-config \
    mingw64-x86_64-runtime \
    mingw64-x86_64-windows-default-manifest \
    mingw64-x86_64-winpthreads \
    mingw64-x86_64-zlib \
    openssh \
    openssl \
    openssl-devel \
    python \
    python-cffi \
    python-gi \
    python-imaging \
    python-ply \
    python-pycparser \
    rsync \
    scons \
    w32api-headers \
    w32api-runtime \
```

Other Libraries
---------------

Testing
====
to test X
```
    python -m unittest discover tests
```

Running
====
If you're syncing products:

`python source/generator.py --help`

If you're syncing users:

`python source/merger.py --help`
