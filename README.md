# WooGenerator
Generates WooCommerce friendly CSV files from a Google Drive spreadsheet of products

This is a highly customized project for a very specific job and probably won't be very useful to other people

Install Instructions
====================

Google Drive API
----------------

pip install --upgrade google-api-python-client

https://developers.google.com/drive/web/quickstart/python

Other dependencies
------------------

pip install --upgrade tabulate dill


Layout
------
```
  CSVParse_Abstract
   |-CSVParse_Flat
   |  |-CSVParse_USXS
   |  |-CSVParse_SSS
   |  |-CSVParse_Users
   |-CSVParse_Tree
      |-CSVParse_DPR 
      |-CSVParse_Gen
        |-CSVParse_WOO
        |  |-CSVParse_TT
        |  |-CSVParse_VT
        |-CSVParse_MYO
```