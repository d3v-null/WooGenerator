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
| `parsing.myo.CsvParseMyo` | All meridian products for MYOB |
| `parsing.woo.CsvParseTT` | All TechnoTan products for WooCommerce |
| `parsing.woo.CsvParseVT` | All VuTan products for WooCommerce |



Install Instructions
====================

Google Drive API
----------------

pip install --upgrade google-api-python-client

refer to these instructions on setting it up:
https://developers.google.com/drive/web/quickstart/python

Store the Google Drive credentials in your product syncing config file, default: `~/woogenerator/conf_prod.yaml` like so:

```
    ...
    gdrive_oauth_client_id: XXXX.apps.googleusercontent.com
    gdrive_oauth_client_secret: YYY
    gdrive_credentials_dir: ~/.credentials
    gdrive_credentials_file: drive-woogenerator.json
```

Store the app config in your config file:

```
    gdrive_scopes: https://spreadsheets.google.com/feeds https://docs.google.com/feeds
    gdrive_client_secret_file: client_secret.json
    gdrive_app_name: Laserphile WooGenerator Drive API
```

Store the File IDs and Sheet IDs of your generator spreadsheet in your config file:

```

```

SSHTunnel
---------

ssh tunnel requres extra dependencies on cygwin. you need to install the mingw toolchain for your system, and openssl-dev

``` shell
apt-cyg install libffi-devel
```

Store your ssh / mysql credentials in your product syncing config file, default: `~/woogenerator/config_prod.yaml` like so:

```
    ...
    ssh-user: XXX
    ssh-pass: XXX
    ssh-host: XXX
    ssh-port: 22
    remote-bind-host: 127.0.0.1
    remote-bind-port: 3306
    db-user: XXX
    db-pass: XXX
    db-name: XXX
    tbl-prefix: XXX

```

Python Version
---

make sure you are using python2:

```bash
python -c "import sys; print sys.version"
# Should be 2.7.X
```

Cygwin Packages
---------------
If you're running cygwin, you may or may not need these:

```
apt-cyg install \
    cygwin-devel \
    cygwin32-w32api-headers \
    exiv2 \
    gcc-core \
    libboost_python-devel \
    libboost-devel \
    libexiv2-devel \
    libffi6 \
    libffi-devel \
    mingw64-i686-boost \
    mingw64-i686-binutils \
    mingw64-i686-gcc-core \
    mingw64-i686-headers \
    mingw64-i686-openssl \
    mingw64-i686-pkg-config \
    mingw64-i686-libffi \
    mingw64-i686-runtime \
    mingw64-i686-windows-default-manifest \
    mingw64-i686-winpthreads \
    mingw64-i686-zlib \
    mingw64-x86_64-boost \
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
    python-crypto \
    python-cffi \
    python-gi \
    python-imaging \
    python-ply \
    python-pycparser \
    python2-cffi \
    python3-cffi \
    rsync \
    scons \
    w32api-headers \
    w32api-runtime \
```

Python packages
---
Now you can install packages

```bash
sudo -H pip2 install --upgrade $(cat requirements.txt)
```

Todo: Are these still dependencies?
```
  pygobject3 \
  iptcinfo \
  bzr \
```

Testing
====
To install testing suite:
```bash
pip install pytest pytest-pudb mock radon mccabe pycodestyle pylama pylint
```
to test all:
```bash
pytest
```

Running
====
If you want to run the gui:

`python woogenerator/gui.py`

If you're syncing products:

`python woogenerator/generator.py --help`

If you're syncing users:

`python woogenerator/merger.py --help`
