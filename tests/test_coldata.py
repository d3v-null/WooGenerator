from collections import OrderedDict
import unittest
from unittest import TestCase
import logging

from context import woogenerator
from woogenerator.coldata import ColDataUser, ColDataWoo, ColDataAbstract, ColDataMedia
from woogenerator.utils import Registrar
from pprint import pformat


class TestColData(unittest.TestCase):
    col_data_class = ColDataAbstract

    def setUp(self):
        if self.debug:
            pass
        else:
            logging.basicConfig(level=logging.DEBUG)
            Registrar.DEBUG_ERROR = False
            Registrar.DEBUG_WARN = False
            Registrar.DEBUG_MESSAGE = False


class TestColDataAbstract(TestColData):
    def test_get_target_ancestors(self):
        self.assertEqual(
            self.col_data_class.get_target_ancestors(
                self.col_data_class.targets,
                'wc-legacy-api-v2'
            ),
            ['api', 'wc-api', 'wc-legacy-api', 'wc-legacy-api-v2']
        )

    def test_get_property(self):
        self.assertEqual(
            self.col_data_class.get_handle_property('id', 'path'),
            'id'
        )
        self.assertEqual(
            self.col_data_class.get_handle_property('id', 'path', 'xero-api'),
            None
        )
        self.assertEqual(
            self.col_data_class.get_handle_property('id', 'path', 'sql'),
            'id'
        )
        self.assertEqual(
            self.col_data_class.get_handle_property('id', 'path', 'wp-sql'),
            'ID'
        )
        self.assertEqual(
            self.col_data_class.get_handle_property('id', 'path', 'wp-api'),
            'id'
        )
        self.assertEqual(
            self.col_data_class.get_handle_property('id', 'write'),
            False
        )
        self.assertEqual(
            self.col_data_class.get_handle_property('id', 'write', 'xero-api'),
            False
        )
        self.assertEqual(
            self.col_data_class.get_handle_property('id', 'write', 'sql'),
            False
        )
        self.assertEqual(
            self.col_data_class.get_handle_property('id', 'write', 'wp-sql'),
            False
        )
        self.assertEqual(
            self.col_data_class.get_handle_property('id', 'write', 'wp-api'),
            False
        )
        self.assertEqual(
            self.col_data_class.get_handle_property('id', 'write', 'wp-csv'),
            False
        )


class TestColDataImg(TestColData):
    col_data_class = ColDataMedia
    debug = False

    def test_get_property(self):
        self.assertEqual(
            self.col_data_class.get_handle_property('source_url', 'path'),
            'source_url'
        )
        self.assertEqual(
            self.col_data_class.get_handle_property(
                'source_url', 'path', 'wp-api-v1'),
            'source'
        )
        self.assertEqual(
            self.col_data_class.get_handle_property(
                'source_url', 'path', 'wp-api-v2'),
            'source_url'
        )

    def test_get_handles(self):
        handles_property_v2 = self.col_data_class.get_handles_property(
            'path', 'wp-api-v2')
        if self.debug:
            print("handles_property_v2: %s" % pformat(handles_property_v2))
        self.assertEquals(
            handles_property_v2,
            OrderedDict([
                ('caption', 'caption.rendered'),
                ('title', 'title.rendered'),
                ('image_meta', 'attachment_meta.media_details'),
                ('width', 'media_details.width'),
                ('upload_path', 'media_details.file'),
                ('height', 'media_details.height')
            ])
        )

    def test_get_path_translation(self):
        path_translation = self.col_data_class.get_path_translation(
            'wp-api-v2')
        if self.debug:
            print("path_translation: %s" % pformat(path_translation))

        self.assertEquals(
            path_translation,
            {
                'alt_text': 'alt_text',
                 'attachment_meta.media_details': 'image_meta',
                 'caption.rendered': 'caption',
                 'date_gmt': 'date_gmt',
                 'description': 'description',
                 'id': 'id',
                 'media_details.file': 'upload_path',
                 'media_details.height': 'height',
                 'media_details.width': 'width',
                 'mime_type': 'mime_type',
                 'modified_gmt': 'modified_gmt',
                 'slug': 'slug',
                 'source_url': 'source_url',
                 'title.rendered': 'title'
            }
        )

    def test_do_path_translation(self):
        api_data_v1 = {
           "slug" : "doorway-technotan-tanning-tips",
           "modified_tz" : "UTC",
           "source" : "http://localhost:18080/wptest/wp-content/uploads/2017/11/Doorway-TechnoTan-Tanning-Tips.jpg",
           "excerpt" : "<p>caption_1983</p>\n",
           "guid" : "http://localhost:18080/wptest/wp-content/uploads/2017/11/Doorway-TechnoTan-Tanning-Tips.jpg",
           "date" : "2017-11-01T00:08:08",
           "format" : "standard",
           "meta" : {
              "links" : {
                 "collection" : "http://localhost:18080/wptest/wp-json/media",
                 "replies" : "http://localhost:18080/wptest/wp-json/media/1983/comments",
                 "author" : "http://localhost:18080/wptest/wp-json/users/1",
                 "version-history" : "http://localhost:18080/wptest/wp-json/media/1983/revisions",
                 "self" : "http://localhost:18080/wptest/wp-json/media/1983"
              }
           },
           "modified_gmt" : "2017-11-03T06:39:03",
           "sticky" : False,
           "comment_status" : "open",
           "date_gmt" : "2017-11-01T00:08:08",
           "ID" : 1983,
           "ping_status" : "closed",
           "menu_order" : 0,
           "parent" : None,
           "status" : "inherit",
           "content" : "<p class=\"attachment\"><a href='http://localhost:18080/wptest/wp-content/uploads/2017/11/Doorway-TechnoTan-Tanning-Tips.jpg'><img width=\"300\" height=\"300\" src=\"http://localhost:18080/wptest/wp-content/uploads/2017/11/Doorway-TechnoTan-Tanning-Tips-300x300.jpg\" class=\"attachment-medium size-medium\" alt=\"alt_text_1983\" srcset=\"http://localhost:18080/wptest/wp-content/uploads/2017/11/Doorway-TechnoTan-Tanning-Tips-300x300.jpg 300w, http://localhost:18080/wptest/wp-content/uploads/2017/11/Doorway-TechnoTan-Tanning-Tips-150x150.jpg 150w, http://localhost:18080/wptest/wp-content/uploads/2017/11/Doorway-TechnoTan-Tanning-Tips-768x768.jpg 768w, http://localhost:18080/wptest/wp-content/uploads/2017/11/Doorway-TechnoTan-Tanning-Tips-1024x1024.jpg 1024w, http://localhost:18080/wptest/wp-content/uploads/2017/11/Doorway-TechnoTan-Tanning-Tips-180x180.jpg 180w, http://localhost:18080/wptest/wp-content/uploads/2017/11/Doorway-TechnoTan-Tanning-Tips-600x600.jpg 600w, http://localhost:18080/wptest/wp-content/uploads/2017/11/Doorway-TechnoTan-Tanning-Tips.jpg 1200w\" sizes=\"(max-width: 300px) 100vw, 300px\" /></a></p>\n<p>description_1983</p>\n",
           "is_image" : True,
           "author" : {
              "URL" : "",
              "username" : "wptest",
              "nickname" : "wptest",
              "slug" : "wptest",
              "ID" : 1,
              "name" : "wptest",
              "description" : "",
              "registered" : "2017-07-04T11:29:15+00:00",
              "avatar" : "http://1.gravatar.com/avatar/4ebb464288ec15bc8b7bfd41fcd4fd9c?s=96",
              "last_name" : "",
              "first_name" : "",
              "meta" : {
                 "links" : {
                    "archives" : "http://localhost:18080/wptest/wp-json/users/1/posts",
                    "self" : "http://localhost:18080/wptest/wp-json/users/1"
                 }
              }
           },
           "terms" : [],
           "type" : "attachment",
           "modified" : "2017-11-03T06:39:03",
           "attachment_meta" : {
              "image_meta" : {
                 "iso" : "200",
                 "focal_length" : "4.15",
                 "orientation" : "1",
                 "title" : "",
                 "created_timestamp" : "1505479632",
                 "credit" : "",
                 "keywords" : [],
                 "camera" : "iPhone SE",
                 "shutter_speed" : "0.05",
                 "caption" : "",
                 "aperture" : "2.2",
                 "copyright" : ""
              },
              "width" : 1200,
              "height" : 1200,
              "file" : "2017/11/Doorway-TechnoTan-Tanning-Tips.jpg",
              "sizes" : {
                 "thumbnail" : {
                    "width" : 150,
                    "url" : "http://localhost:18080/wptest/wp-content/uploads/2017/11/Doorway-TechnoTan-Tanning-Tips-150x150.jpg",
                    "height" : 150,
                    "file" : "Doorway-TechnoTan-Tanning-Tips-150x150.jpg",
                    "mime-type" : "image/jpeg"
                 },
                 "large" : {
                    "url" : "http://localhost:18080/wptest/wp-content/uploads/2017/11/Doorway-TechnoTan-Tanning-Tips-1024x1024.jpg",
                    "width" : 1024,
                    "height" : 1024,
                    "mime-type" : "image/jpeg",
                    "file" : "Doorway-TechnoTan-Tanning-Tips-1024x1024.jpg"
                 },
                 "shop_single" : {
                    "height" : 600,
                    "mime-type" : "image/jpeg",
                    "file" : "Doorway-TechnoTan-Tanning-Tips-600x600.jpg",
                    "url" : "http://localhost:18080/wptest/wp-content/uploads/2017/11/Doorway-TechnoTan-Tanning-Tips-600x600.jpg",
                    "width" : 600
                 },
                 "shop_catalog" : {
                    "mime-type" : "image/jpeg",
                    "file" : "Doorway-TechnoTan-Tanning-Tips-300x300.jpg",
                    "height" : 300,
                    "width" : 300,
                    "url" : "http://localhost:18080/wptest/wp-content/uploads/2017/11/Doorway-TechnoTan-Tanning-Tips-300x300.jpg"
                 },
                 "medium" : {
                    "height" : 300,
                    "mime-type" : "image/jpeg",
                    "file" : "Doorway-TechnoTan-Tanning-Tips-300x300.jpg",
                    "url" : "http://localhost:18080/wptest/wp-content/uploads/2017/11/Doorway-TechnoTan-Tanning-Tips-300x300.jpg",
                    "width" : 300
                 },
                 "medium_large" : {
                    "width" : 768,
                    "url" : "http://localhost:18080/wptest/wp-content/uploads/2017/11/Doorway-TechnoTan-Tanning-Tips-768x768.jpg",
                    "height" : 768,
                    "mime-type" : "image/jpeg",
                    "file" : "Doorway-TechnoTan-Tanning-Tips-768x768.jpg"
                 },
                 "shop_thumbnail" : {
                    "width" : 180,
                    "url" : "http://localhost:18080/wptest/wp-content/uploads/2017/11/Doorway-TechnoTan-Tanning-Tips-180x180.jpg",
                    "height" : 180,
                    "mime-type" : "image/jpeg",
                    "file" : "Doorway-TechnoTan-Tanning-Tips-180x180.jpg"
                 }
              }
           },
           "title" : "Doorway TechnoTan Tanning Tips",
           "date_tz" : "UTC",
           "link" : "http://localhost:18080/wptest/doorway-technotan-tanning-tips/"
        }
        api_data_v2 = {
           "type" : "attachment",
           "source_url" : "http://localhost:18080/wptest/wp-content/uploads/2017/11/Doorway-TechnoTan-Tanning-Tips.jpg",
           "author" : 1,
           "alt_text" : "alt_text_1983",
           "ping_status" : "closed",
           "post" : None,
           "caption" : {
              "rendered" : "<p>caption_1983</p>\n"
           },
           "_links" : {
              "about" : [
                 {
                    "href" : "http://localhost:18080/wptest/wp-json/wp/v2/types/attachment"
                 }
              ],
              "self" : [
                 {
                    "href" : "http://localhost:18080/wptest/wp-json/wp/v2/media/1983"
                 }
              ],
              "author" : [
                 {
                    "href" : "http://localhost:18080/wptest/wp-json/wp/v2/users/1",
                    "embeddable" : True
                 }
              ],
              "replies" : [
                 {
                    "href" : "http://localhost:18080/wptest/wp-json/wp/v2/comments?post=1983",
                    "embeddable" : True
                 }
              ],
              "collection" : [
                 {
                    "href" : "http://localhost:18080/wptest/wp-json/wp/v2/media"
                 }
              ]
           },
           "status" : "inherit",
           "media_type" : "image",
           "title" : {
              "rendered" : "Doorway TechnoTan Tanning Tips"
           },
           "link" : "http://localhost:18080/wptest/doorway-technotan-tanning-tips/",
           "date_gmt" : "2017-11-01T00:08:08",
           "guid" : {
              "rendered" : "http://localhost:18080/wptest/wp-content/uploads/2017/11/Doorway-TechnoTan-Tanning-Tips.jpg"
           },
           "mime_type" : "image/jpeg",
           "media_details" : {
              "height" : 1200,
              "width" : 1200,
              "image_meta" : {
                 "credit" : "",
                 "aperture" : "2.2",
                 "title" : "",
                 "orientation" : "1",
                 "shutter_speed" : "0.05",
                 "caption" : "",
                 "iso" : "200",
                 "copyright" : "",
                 "keywords" : [],
                 "focal_length" : "4.15",
                 "camera" : "iPhone SE",
                 "created_timestamp" : "1505479632"
              },
              "file" : "2017/11/Doorway-TechnoTan-Tanning-Tips.jpg",
              "sizes" : {
                 "medium_large" : {
                    "source_url" : "http://localhost:18080/wptest/wp-content/uploads/2017/11/Doorway-TechnoTan-Tanning-Tips-768x768.jpg",
                    "mime_type" : "image/jpeg",
                    "file" : "Doorway-TechnoTan-Tanning-Tips-768x768.jpg",
                    "width" : 768,
                    "height" : 768
                 },
                 "thumbnail" : {
                    "file" : "Doorway-TechnoTan-Tanning-Tips-150x150.jpg",
                    "source_url" : "http://localhost:18080/wptest/wp-content/uploads/2017/11/Doorway-TechnoTan-Tanning-Tips-150x150.jpg",
                    "mime_type" : "image/jpeg",
                    "height" : 150,
                    "width" : 150
                 },
                 "large" : {
                    "width" : 1024,
                    "height" : 1024,
                    "mime_type" : "image/jpeg",
                    "source_url" : "http://localhost:18080/wptest/wp-content/uploads/2017/11/Doorway-TechnoTan-Tanning-Tips-1024x1024.jpg",
                    "file" : "Doorway-TechnoTan-Tanning-Tips-1024x1024.jpg"
                 },
                 "full" : {
                    "width" : 1200,
                    "height" : 1200,
                    "mime_type" : "image/jpeg",
                    "source_url" : "http://localhost:18080/wptest/wp-content/uploads/2017/11/Doorway-TechnoTan-Tanning-Tips.jpg",
                    "file" : "Doorway-TechnoTan-Tanning-Tips.jpg"
                 },
                 "shop_single" : {
                    "source_url" : "http://localhost:18080/wptest/wp-content/uploads/2017/11/Doorway-TechnoTan-Tanning-Tips-600x600.jpg",
                    "mime_type" : "image/jpeg",
                    "file" : "Doorway-TechnoTan-Tanning-Tips-600x600.jpg",
                    "width" : 600,
                    "height" : 600
                 },
                 "shop_thumbnail" : {
                    "file" : "Doorway-TechnoTan-Tanning-Tips-180x180.jpg",
                    "source_url" : "http://localhost:18080/wptest/wp-content/uploads/2017/11/Doorway-TechnoTan-Tanning-Tips-180x180.jpg",
                    "mime_type" : "image/jpeg",
                    "height" : 180,
                    "width" : 180
                 },
                 "shop_catalog" : {
                    "file" : "Doorway-TechnoTan-Tanning-Tips-300x300.jpg",
                    "mime_type" : "image/jpeg",
                    "source_url" : "http://localhost:18080/wptest/wp-content/uploads/2017/11/Doorway-TechnoTan-Tanning-Tips-300x300.jpg",
                    "height" : 300,
                    "width" : 300
                 },
                 "medium" : {
                    "file" : "Doorway-TechnoTan-Tanning-Tips-300x300.jpg",
                    "mime_type" : "image/jpeg",
                    "source_url" : "http://localhost:18080/wptest/wp-content/uploads/2017/11/Doorway-TechnoTan-Tanning-Tips-300x300.jpg",
                    "height" : 300,
                    "width" : 300
                 }
              }
           },
           "description" : {
              "rendered" : "<p class=\"attachment\"><a href='http://localhost:18080/wptest/wp-content/uploads/2017/11/Doorway-TechnoTan-Tanning-Tips.jpg'><img width=\"300\" height=\"300\" src=\"http://localhost:18080/wptest/wp-content/uploads/2017/11/Doorway-TechnoTan-Tanning-Tips-300x300.jpg\" class=\"attachment-medium size-medium\" alt=\"alt_text_1983\" srcset=\"http://localhost:18080/wptest/wp-content/uploads/2017/11/Doorway-TechnoTan-Tanning-Tips-300x300.jpg 300w, http://localhost:18080/wptest/wp-content/uploads/2017/11/Doorway-TechnoTan-Tanning-Tips-150x150.jpg 150w, http://localhost:18080/wptest/wp-content/uploads/2017/11/Doorway-TechnoTan-Tanning-Tips-768x768.jpg 768w, http://localhost:18080/wptest/wp-content/uploads/2017/11/Doorway-TechnoTan-Tanning-Tips-1024x1024.jpg 1024w, http://localhost:18080/wptest/wp-content/uploads/2017/11/Doorway-TechnoTan-Tanning-Tips-180x180.jpg 180w, http://localhost:18080/wptest/wp-content/uploads/2017/11/Doorway-TechnoTan-Tanning-Tips-600x600.jpg 600w, http://localhost:18080/wptest/wp-content/uploads/2017/11/Doorway-TechnoTan-Tanning-Tips.jpg 1200w\" sizes=\"(max-width: 300px) 100vw, 300px\" /></a></p>\n<p>description_1983</p>\n"
           },
           "date" : "2017-11-01T00:08:08",
           "template" : "",
           "id" : 1983,
           "meta" : [],
           "modified" : "2017-11-03T06:39:03",
           "slug" : "doorway-technotan-tanning-tips",
           "modified_gmt" : "2017-11-03T06:39:03",
           "comment_status" : "open"
        }
        # for key in self.col_data_class.data.keys():
        #     if key not in ['media_details', 'media_type']:
        #         del(self.col_data_class.data[key])
        translated_v2 = self.col_data_class.do_path_translation(
            api_data_v2, 'wp-api-v2'
        )
        translated_v1 = self.col_data_class.do_path_translation(
            api_data_v1, 'wp-api-v1'
        )
        key_intersection = set(translated_v1.keys()).intersection(translated_v2.keys())
        if self.debug:
            print('translated_v1:\n%s' % pformat(translated_v1))
            print('translated_v2:\n%s' % pformat(translated_v2))
            print('translated_v1_keys:\n%s' % (sorted(translated_v1.keys())))
            print('translated_v2_keys:\n%s' % (sorted(translated_v2.keys())))
            print('key intersection:\n%s' % (sorted(key_intersection)))
        for key in key_intersection:
            self.assertEquals(translated_v1[key], translated_v2[key])

class testColDataUser(TestColData):
    col_data_class = ColDataUser

    def setUp(self):
        super(testColDataUser, self).setUp()
        self.maxDiff = None

    def test_getImportCols(self):
        importCols = self.col_data_class.get_import_cols()
        for key in [
            'MYOB Card ID',
            'E-mail',
            'Wordpress Username',
            'Wordpress ID',
            # 'Role',
            'Contact',
            'First Name',
            'Surname',
            'Middle Name',
            'Name Suffix',
            'Name Prefix',
            'Memo',
            'Spouse',
            'Salutation',
            'Company',
            'Mobile Phone',
            'Phone',
            'Fax',
            'Address 1',
            'Address 2',
            'City',
            'Postcode',
            'State',
            'Country',
            'Shire',
            'Home Address 1',
            'Home Address 2',
            'Home City', 'Home Postcode', 'Home Country', 'Home State',
            'MYOB Customer Card ID', 'Client Grade',
            # 'Direct Brand',
            'Agent',
            'Web Site',
            'ABN',
            'Business Type',
            'Lead Source',
            'Referred By',
            'Personal E-mail',
            'Create Date',
            'Wordpress Start Date',
            'Edited in Act',
            'Edited in Wordpress',
            'Last Sale',
            'Facebook Username',
            'Twitter Username',
            'GooglePlus Username',
            'Instagram Username',
            'Added to mailing list',
            'Tans Per Week'
        ]:
            self.assertIn(key, importCols)

    def test_getActTrackedCols(self):
        actTrackedCols = self.col_data_class.get_act_tracked_cols()
        self.assertItemsEqual(
            actTrackedCols,
            OrderedDict([
                ('Edited E-mail', ['E-mail']),
                ('Edited Name', ['Name Prefix', 'First Name', 'Middle Name',
                                 'Surname', 'Name Suffix', 'Salutation', 'Contact']),
                ('Edited Memo', ['Memo', 'Memo']),
                ('Edited Spouse', ['Spouse', 'Spouse']),
                ('Edited Company', ['Company']),
                ('Edited Phone Numbers', ['Mobile Phone', 'Phone', 'Fax']),
                ('Edited Address', ['Address 1', 'Address 2', 'City', 'Postcode',
                                    'State', 'Country', 'Shire']),
                ('Edited Alt Address', ['Home Address 1', 'Home Address 2', 'Home City',
                                        'Home Postcode', 'Home State', 'Home Country']),
                ('Edited Personal E-mail', ['Personal E-mail']),
                ('Edited Web Site', ['Web Site']),
                ('Edited Social Media', ['Facebook Username', 'Twitter Username',
                                         'GooglePlus Username', 'Instagram Username']),
            ]))

    def test_getDeltaCols(self):
        DeltaCols = self.col_data_class.get_delta_cols()
        self.assertItemsEqual(DeltaCols, OrderedDict(
            [
                ('E-mail', 'Delta E-mail'),
                # ('Role Info', 'Delta Role Info')
            ]))

    def test_getAllWpDbCols(self):
        dbCols = self.col_data_class.get_all_wpdb_cols()
        # print "dbCols %s" % pformat(dbCols.items())
        self.assertItemsEqual(dbCols, OrderedDict([
            ('myob_card_id', 'MYOB Card ID'),
            # ('act_role', 'Role'),
            ('nickname', 'Contact'),
            ('first_name', 'First Name'),
            ('last_name', 'Surname'),
            ('middle_name', 'Middle Name'),
            ('name_suffix', 'Name Suffix'),
            ('name_prefix', 'Name Prefix'),
            ('name_notes', 'Memo'),
            ('spouse', 'Spouse'),
            # ('salutation', 'Salutation'),
            ('billing_company', 'Company'),
            ('mobile_number', 'Mobile Phone'),
            ('billing_phone', 'Phone'),
            ('fax_number', 'Fax'),
            # ('pref_mob', 'Mobile Phone Preferred'),
            # ('pref_tel', 'Phone Preferred'),
            ('billing_address_1', 'Address 1'),
            ('billing_address_2', 'Address 2'),
            ('billing_city', 'City'),
            ('billing_postcode', 'Postcode'),
            ('billing_state', 'State'),
            ('billing_country', 'Country'),
            ('shipping_address_1', 'Home Address 1'),
            ('shipping_address_2', 'Home Address 2'),
            ('shipping_city', 'Home City'),
            ('shipping_postcode', 'Home Postcode'),
            ('shipping_country', 'Home Country'),
            ('shipping_state', 'Home State'),
            ('myob_customer_card_id', 'MYOB Customer Card ID'),
            ('client_grade', 'Client Grade'),
            # ('direct_brand', 'Direct Brand'),
            ('agent', 'Agent'),
            ('abn', 'ABN'),
            ('business_type', 'Business Type'),
            ('how_hear_about', 'Lead Source'),
            ('referred_by', 'Referred By'),
            ('tans_per_wk', 'Tans Per Week'),
            ('personal_email', 'Personal E-mail'),
            ('edited_in_act', 'Edited in Act'),
            ('act_last_sale', 'Last Sale'),
            ('facebook', 'Facebook Username'),
            ('twitter', 'Twitter Username'),
            ('gplus', 'GooglePlus Username'),
            ('instagram', 'Instagram Username'),
            ('mailing_list', 'Added to mailing list'),
            ('user_email', 'E-mail'),
            ('user_login', 'Wordpress Username'),
            ('ID', 'Wordpress ID'),
            # ('display_name', 'Contact'),
            ('user_url', 'Web Site'),
            ('user_registered', 'Wordpress Start Date'),
            ('pref_method', 'Pref Method')
        ]))

    def test_getWPAPICols(self):
        api_cols = ColDataWoo.get_wpapi_cols()
        # print "test_getWPAPICols", api_cols.keys()

    def test_getWPAPIVariableCols(self):
        api_cols = ColDataWoo.get_wpapi_variable_cols()
        # print "test_getWPAPIVariableCols", api_cols.keys()


if __name__ == '__main__':
    unittest.main()

# TODO: Implement these test cases
#
# def testColDataMyo():
#     print "Testing ColDataMyo Class:"
#     col_data = ColDataMyo()
#     print col_data.get_import_cols()
#     print col_data.get_defaults()
#     print col_data.get_product_cols()
#
# def testColDataWoo():
#     print "Testing ColDataWoo class:"
#     col_data = ColDataWoo()
#     print col_data.get_import_cols()
#     print col_data.get_defaults()
#     print col_data.get_product_cols()
#
# def testColDataUser():
#     print "Testing ColDataUser class:"
#     col_data = ColDataUser()
#     # print "importCols", col_data.get_import_cols()
#     # print "userCols", col_data.get_user_cols().keys()
#     # print "report_cols", col_data.get_report_cols().keys()
#     # print "capitalCols", col_data.get_capital_cols().keys()
#     # print "sync_cols", col_data.get_sync_cols().keys()
#     print "actCols", col_data.get_act_cols().keys()
#     # print "wpcols", col_data.get_wp_cols().keys()
#     print "get_wp_tracked_cols", col_data.get_wp_tracked_cols()
#     print "get_act_tracked_cols", col_data.get_act_tracked_cols()
#     print "get_act_future_tracked_cols", col_data.get_act_future_tracked_cols()
#
# def testTansyncDefaults():
#     col_data = ColDataUser()
#     print '{'
#     for col, data in col_data.get_tansync_defaults().items():
#         print '"%s": %s,' % (col, json.dumps(data))
#     print '}'
#
# if __name__ == '__main__':
#     # testColDataMyo()
#     # testColDataWoo()
#     testColDataUser()
#     # testTansyncDefaults()
