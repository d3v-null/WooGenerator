import logging
import unittest
from collections import OrderedDict
from pprint import pformat, pprint
from unittest import TestCase

import pytest

from context import woogenerator
from woogenerator.coldata import (ColDataAbstract, ColDataAttachment,
                                  ColDataProductMeridian,
                                  ColDataWcProdCategory,
                                  ColDataWpPost, ColDataSubMeta)
from woogenerator.utils import Registrar

from .abstract import AbstractWooGeneratorTestCase


class TestColData(AbstractWooGeneratorTestCase):
    coldata_class = ColDataAbstract

    def setUp(self):
        if self.debug:
            pass
        else:
            logging.basicConfig(level=logging.DEBUG)
            Registrar.DEBUG_ERROR = False
            Registrar.DEBUG_WARN = False
            Registrar.DEBUG_MESSAGE = False

# class TestLegacyAccordanceProd(TestColData):
#     coldata_class = ColDataProductMeridian
#     legacy_coldata_class = ColDataWoo
#
#     def test_legacy_accordance_wpapi_core_cols(self):
#         cols = set(self.coldata_class.get_wpapi_core_cols().keys())
#         legacy_cols = set(self.legacy_coldata_class.get_wpapi_core_cols().keys())
#
#         if self.debug:
#             print('intersect:\n%s' % pformat(cols.intersection(legacy_cols)))
#             print('cols - legacy_cols:\n%s' % pformat(cols.difference(legacy_cols)))
#             print('legacy_cols - cols:\n%s' % pformat(legacy_cols.difference(cols)))
#
#         self.assertTrue(
#             (legacy_cols - set(['itemsum', 'slug'])).issubset(cols),
#         )
#
#     def test_legacy_accordance_report_cols(self):
#         cols = set(self.coldata_class.get_report_cols().keys())
#         legacy_cols = set(self.legacy_coldata_class.get_report_cols().keys())
#
#         if self.debug:
#             print('intersect:\n%s' % pformat(cols.intersection(legacy_cols)))
#             print('cols - legacy_cols:\n%s' % pformat(cols.difference(legacy_cols)))
#             print('legacy_cols - cols:\n%s' % pformat(legacy_cols.difference(cols)))
#
#         self.assertTrue(
#             (legacy_cols - set(['itemsum', 'price', 'sale_price'])).issubset(cols),
#         )
#
#     def test_legacy_accordance_import_cols(self):
#         cols = set(self.coldata_class.get_import_cols())
#         legacy_cols = set(self.legacy_coldata_class.get_import_cols())
#
#         if self.debug:
#             print('intersect:\n%s' % pformat(cols.intersection(legacy_cols)))
#             print('cols - legacy_cols:\n%s' % pformat(cols.difference(legacy_cols)))
#             print('legacy_cols - cols:\n%s' % pformat(legacy_cols.difference(cols)))
#
#         self.assertTrue(
#             (legacy_cols - set(['itemsum', 'price', 'sale_price'])).issubset(cols),
#         )



# class TestLegacyAccordanceCat(TestColData):
#     coldata_class = ColDataWcProdCategory
#     legacy_coldata_class = ColDataWoo
#
#     def test_legacy_accordance_category_cols(self):
#         cols = set(self.coldata_class.get_category_cols().keys())
#         legacy_cols = set(self.legacy_coldata_class.get_category_cols().keys())
#
#         if self.debug:
#             print('intersect:\n%s' % pformat(cols.intersection(legacy_cols)))
#             print('cols - legacy_cols:\n%s' % pformat(cols.difference(legacy_cols)))
#             print('legacy_cols - cols:\n%s' % pformat(legacy_cols.difference(cols)))
#
#         self.assertTrue(
#             (legacy_cols - set(['DYNCAT', 'DYNPROD', 'SCHEDULE'])).issubset(cols),
#         )
#


class TestColDataAbstract(TestColData):
    def test_get_target_ancestors(self):
        self.assertEqual(
            self.coldata_class.get_target_ancestors(
                self.coldata_class.targets,
                'wc-legacy-api-v2'
            ),
            ['api', 'wc-api', 'wc-legacy-api', 'wc-legacy-api-v2']
        )

    # def test_get_property(self):
    #     self.assertEqual(
    #         self.coldata_class.get_handle_property('id', 'path'),
    #         'id'
    #     )
    #     self.assertEqual(
    #         self.coldata_class.get_handle_property('id', 'path', 'xero-api'),
    #         None
    #     )
    #     self.assertEqual(
    #         self.coldata_class.get_handle_property('id', 'path', 'sql'),
    #         'id'
    #     )
    #     self.assertEqual(
    #         self.coldata_class.get_handle_property('id', 'path', 'wp-sql'),
    #         'ID'
    #     )
    #     self.assertEqual(
    #         self.coldata_class.get_handle_property('id', 'path', 'wp-api'),
    #         'id'
    #     )
    #     self.assertEqual(
    #         self.coldata_class.get_handle_property('id', 'write'),
    #         False
    #     )
    #     self.assertEqual(
    #         self.coldata_class.get_handle_property('id', 'write', 'xero-api'),
    #         False
    #     )
    #     self.assertEqual(
    #         self.coldata_class.get_handle_property('id', 'write', 'sql'),
    #         False
    #     )
    #     self.assertEqual(
    #         self.coldata_class.get_handle_property('id', 'write', 'wp-sql'),
    #         False
    #     )
    #     self.assertEqual(
    #         self.coldata_class.get_handle_property('id', 'write', 'wp-api'),
    #         False
    #     )
    #     self.assertEqual(
    #         self.coldata_class.get_handle_property('id', 'write', 'wp-csv'),
    #         False
    #     )


class TestColDataImg(TestColData):
    coldata_class = ColDataAttachment
    debug = False

    def test_get_property(self):
        self.assertEqual(
            self.coldata_class.get_handle_property('source_url', 'path'),
            'source_url'
        )
        self.assertEqual(
            self.coldata_class.get_handle_property(
                'source_url', 'path', 'wp-api-v1'),
            'source'
        )
        self.assertEqual(
            self.coldata_class.get_handle_property(
                'source_url', 'path', 'wp-api-v2'),
            'source_url'
        )

    def test_get_handles(self):
        handles_property_v2 = self.coldata_class.get_handles_property(
            'path', 'wp-api-v2')
        if self.debug:
            print("handles_property_v2: %s" % pformat(handles_property_v2))
        self.assertTrue(
            set(OrderedDict([
                ('post_excerpt', 'caption.rendered'),
                ('title', 'title.rendered'),
                ('image_meta', 'attachment_meta.media_details'),
                ('width', 'media_details.width'),
                ('file_path', 'media_details.file'),
                ('height', 'media_details.height'),
                ('post_content', 'description.rendered')
            ]).keys()).issubset(
                set(handles_property_v2.keys())
            )
        )

    def test_get_target_path_translation(self):
        path_translation = self.coldata_class.get_target_path_translation(
            'wp-api-v2')
        if self.debug:
            print("path_translation: %s" % pformat(path_translation))

        expected_handles = set([
            'alt_text',
            'post_content',
            'created_gmt',
            'created_local',
            'post_excerpt',
            'file_path',
            'guid',
            'height',
            'id',
            'image_meta',
            'meta',
            'mime_type',
            'modified_gmt',
            'modified_local',
            'slug',
            'source_url',
            'post_status',
            'title',
            'post_type',
            'width',
        ])
        actual_handles = set(path_translation.keys())
        if self.debug:
            print("actual handles: %s" % actual_handles)
            print("difference: %s" % expected_handles.symmetric_difference(actual_handles))

        self.assertTrue(
            expected_handles.issubset(actual_handles)
        )

    def test_get_sync_cols(self):
        sync_cols = self.coldata_class.get_sync_handles('wp-api')
        expected_keys = set([
            'meta', 'title', 'post_excerpt', 'file_path'
        ])
        actual_keys = set(sync_cols.keys())
        if self.debug:
            print("sync_cols:\n%s" % pformat(sync_cols.items()))
            print('difference:\n actual - expected:\n%s\n expected - actual:\n%s' % (
                actual_keys.difference(expected_keys),
                expected_keys.difference(actual_keys)
            ))
        self.assertTrue(
            expected_keys.issubset(
                actual_keys
            )
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
           "content" : (
               "<p class=\"attachment\"><a href='http://localhost:18080/wptest/wp-content/uploads/2017/11/Doorway-TechnoTan-Tanning-Tips.jpg'>"
               "<img width=\"300\" height=\"300\" src=\"http://localhost:18080/wptest/wp-content/uploads/2017/11/Doorway-TechnoTan-Tanning-Tips-300x300.jpg\" "
               "class=\"attachment-medium size-medium\" alt=\"alt_text_1983\" srcset="
               "\"http://localhost:18080/wptest/wp-content/uploads/2017/11/Doorway-TechnoTan-Tanning-Tips-300x300.jpg 300w, "
               "http://localhost:18080/wptest/wp-content/uploads/2017/11/Doorway-TechnoTan-Tanning-Tips-150x150.jpg 150w, "
               "http://localhost:18080/wptest/wp-content/uploads/2017/11/Doorway-TechnoTan-Tanning-Tips-768x768.jpg 768w, "
               "http://localhost:18080/wptest/wp-content/uploads/2017/11/Doorway-TechnoTan-Tanning-Tips-1024x1024.jpg 1024w, "
               "http://localhost:18080/wptest/wp-content/uploads/2017/11/Doorway-TechnoTan-Tanning-Tips-180x180.jpg 180w, "
               "http://localhost:18080/wptest/wp-content/uploads/2017/11/Doorway-TechnoTan-Tanning-Tips-600x600.jpg 600w, "
               "http://localhost:18080/wptest/wp-content/uploads/2017/11/Doorway-TechnoTan-Tanning-Tips.jpg 1200w\" "
               "sizes=\"(max-width: 300px) 100vw, 300px\" /></a></p>\n<p>description_1983</p>\n"),
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
              "about" : [{"href" : "http://localhost:18080/wptest/wp-json/wp/v2/types/attachment"}],
              "self" : [{"href" : "http://localhost:18080/wptest/wp-json/wp/v2/media/1983"}],
              "author" : [{"href" : "http://localhost:18080/wptest/wp-json/wp/v2/users/1", "embeddable" : True}],
              "replies" : [{"href" : "http://localhost:18080/wptest/wp-json/wp/v2/comments?post=1983", "embeddable" : True}],
              "collection" : [{"href" : "http://localhost:18080/wptest/wp-json/wp/v2/media"}]
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
              "rendered" : (
                  "<p class=\"attachment\">"
                  "<a href='http://localhost:18080/wptest/wp-content/uploads/2017/11/Doorway-TechnoTan-Tanning-Tips.jpg'>"
                  "<img width=\"300\" height=\"300\" src=\"http://localhost:18080/wptest/wp-content/uploads/2017/11/Doorway-TechnoTan-Tanning-Tips-300x300.jpg\" "
                  "class=\"attachment-medium size-medium\" alt=\"alt_text_1983\" "
                  "srcset=\"http://localhost:18080/wptest/wp-content/uploads/2017/11/Doorway-TechnoTan-Tanning-Tips-300x300.jpg 300w, "
                  "http://localhost:18080/wptest/wp-content/uploads/2017/11/Doorway-TechnoTan-Tanning-Tips-150x150.jpg 150w, "
                  "http://localhost:18080/wptest/wp-content/uploads/2017/11/Doorway-TechnoTan-Tanning-Tips-768x768.jpg 768w, "
                  "http://localhost:18080/wptest/wp-content/uploads/2017/11/Doorway-TechnoTan-Tanning-Tips-1024x1024.jpg 1024w, "
                  "http://localhost:18080/wptest/wp-content/uploads/2017/11/Doorway-TechnoTan-Tanning-Tips-180x180.jpg 180w, "
                  "http://localhost:18080/wptest/wp-content/uploads/2017/11/Doorway-TechnoTan-Tanning-Tips-600x600.jpg 600w, "
                  "http://localhost:18080/wptest/wp-content/uploads/2017/11/Doorway-TechnoTan-Tanning-Tips.jpg 1200w\" "
                  "sizes=\"(max-width: 300px) 100vw, 300px\" /></a></p>\n<p>description_1983</p>\n")
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
        # for key in self.coldata_class.data.keys():
        #     if key not in ['media_details', 'media_type']:
        #         del(self.coldata_class.data[key])
        translated_v2 = self.coldata_class.translate_paths_from(
            api_data_v2, 'wp-api-v2'
        )
        translated_v1 = self.coldata_class.translate_paths_from(
            api_data_v1, 'wp-api-v1'
        )
        key_intersection = set(translated_v1.keys()).intersection(translated_v2.keys()) - set(['image_meta'])
        if self.debug:
            print('translated_v1:\n%s' % pformat(translated_v1))
            print('translated_v2:\n%s' % pformat(translated_v2))
            print('translated_v1_keys:\n%s' % (sorted(translated_v1.keys())))
            print('translated_v2_keys:\n%s' % (sorted(translated_v2.keys())))
            print('key intersection:\n%s' % (sorted(key_intersection)))
        for key in key_intersection:
            self.assertEquals(translated_v1[key], translated_v2[key])

    def test_normalization(self):
        normalized = {
            'title': u'foo > bar'
        }
        denormalized = {
            'title': {
                u'rendered': 'foo &gt; bar'
            }
        }

        self.assertEquals(
            self.coldata_class.translate_data_from(denormalized, 'wp-api'),
            normalized
        )

        self.assertEquals(
            self.coldata_class.translate_data_to(normalized, 'wp-api'),
            denormalized
        )


class TestColDataWpPost(TestColData):
    coldata_class = ColDataWpPost

    def test_get_target_path_translation_post(self):
        path_translation = self.coldata_class.get_target_path_translation(
            'wp-sql')
        if self.debug:
            print("path_translation: %s" % pformat(path_translation))
#
# @pytest.mark.skip
# class testColDataUser(TestColData):
#     coldata_class = ColDataUser
#
#     def setUp(self):
#         super(testColDataUser, self).setUp()
#         self.maxDiff = None
#
#     def test_getImportCols(self):
#         importCols = self.coldata_class.get_import_cols()
#         for key in [
#             'MYOB Card ID',
#             'E-mail',
#             'Wordpress Username',
#             'Wordpress ID',
#             # 'Role',
#             'Contact',
#             'First Name',
#             'Surname',
#             'Middle Name',
#             'Name Suffix',
#             'Name Prefix',
#             'Memo',
#             'Spouse',
#             'Salutation',
#             'Company',
#             'Mobile Phone',
#             'Phone',
#             'Fax',
#             'Address 1',
#             'Address 2',
#             'City',
#             'Postcode',
#             'State',
#             'Country',
#             'Shire',
#             'Home Address 1',
#             'Home Address 2',
#             'Home City', 'Home Postcode', 'Home Country', 'Home State',
#             'MYOB Customer Card ID', 'Client Grade',
#             # 'Direct Brand',
#             'Agent',
#             'Web Site',
#             'ABN',
#             'Business Type',
#             'Lead Source',
#             'Referred By',
#             'Personal E-mail',
#             'Create Date',
#             'Wordpress Start Date',
#             'Edited in Act',
#             'Edited in Wordpress',
#             'Last Sale',
#             'Facebook Username',
#             'Twitter Username',
#             'GooglePlus Username',
#             'Instagram Username',
#             'Added to mailing list',
#             'Tans Per Week'
#         ]:
#             self.assertIn(key, importCols)
#
#     def test_getActTrackedCols(self):
#         actTrackedCols = self.coldata_class.get_act_tracked_cols()
#         self.assertItemsEqual(
#             actTrackedCols,
#             OrderedDict([
#                 ('Edited E-mail', ['E-mail']),
#                 ('Edited Name', ['Name Prefix', 'First Name', 'Middle Name',
#                                  'Surname', 'Name Suffix', 'Salutation', 'Contact']),
#                 ('Edited Memo', ['Memo', 'Memo']),
#                 ('Edited Spouse', ['Spouse', 'Spouse']),
#                 ('Edited Company', ['Company']),
#                 ('Edited Phone Numbers', ['Mobile Phone', 'Phone', 'Fax']),
#                 ('Edited Address', ['Address 1', 'Address 2', 'City', 'Postcode',
#                                     'State', 'Country', 'Shire']),
#                 ('Edited Alt Address', ['Home Address 1', 'Home Address 2', 'Home City',
#                                         'Home Postcode', 'Home State', 'Home Country']),
#                 ('Edited Personal E-mail', ['Personal E-mail']),
#                 ('Edited Web Site', ['Web Site']),
#                 ('Edited Social Media', ['Facebook Username', 'Twitter Username',
#                                          'GooglePlus Username', 'Instagram Username']),
#             ]))
#
#     def test_getDeltaCols(self):
#         DeltaCols = self.coldata_class.get_delta_cols_native()
#         self.assertItemsEqual(DeltaCols, OrderedDict(
#             [
#                 ('E-mail', 'Delta E-mail'),
#                 # ('Role Info', 'Delta Role Info')
#             ]))
#
#     def test_getAllWpDbCols(self):
#         dbCols = self.coldata_class.get_all_wpdb_cols()
#         # print "dbCols %s" % pformat(dbCols.items())
#         for key in [
#             'myob_card_id',
#             # 'act_role',
#             'nickname',
#             'first_name',
#             'last_name',
#             'middle_name',
#             'name_suffix',
#             'name_prefix',
#             'name_notes',
#             'spouse',
#             # 'salutation',
#             'billing_company',
#             'mobile_number',
#             'billing_phone',
#             'fax_number',
#             # 'pref_mob',
#             # 'pref_tel',
#             'billing_address_1',
#             'billing_address_2',
#             'billing_city',
#             'billing_postcode',
#             'billing_state',
#             'billing_country',
#             'shipping_address_1',
#             'shipping_address_2',
#             'shipping_city',
#             'shipping_postcode',
#             'shipping_country',
#             'shipping_state',
#             'myob_customer_card_id',
#             'client_grade',
#             # 'direct_brand',
#             'agent',
#             'abn',
#             'business_type',
#             'how_hear_about',
#             'referred_by',
#             'tans_per_wk',
#             'personal_email',
#             'edited_in_act',
#             'act_last_sale',
#             'facebook',
#             'twitter',
#             'gplus',
#             'instagram',
#             'mailing_list',
#             'user_email',
#             'user_login',
#             'ID',
#             # 'display_name',
#             'user_url',
#             'user_registered',
#             'pref_method',
#         ]:
#             assert key in dbCols.keys()

class TestColDataWcProd(TestColData):
    coldata_class = ColDataProductMeridian

    def test_get_handles_property(self):
        handles_property = self.coldata_class.get_handles_property('path', 'wc-csv')
        if self.debug:
            pprint(handles_property.items())
        self.assertTrue(
            handles_property.get('product_category_list')
        )

    def test_get_handles_property_defaults(self):
        handles_property_defaults = self.coldata_class.get_handles_property_defaults('path', 'wc-csv')
        if self.debug:
            pprint(handles_property_defaults.items())
        self.assertTrue(
            handles_property_defaults.get('product_category_list')
        )

    def test_get_col_values_native(self):
        col_values_native = self.coldata_class.get_col_values_native('path', target='wc-csv')
        if self.debug:
            pprint(col_values_native.items())
        self.assertTrue(
            col_values_native.get('title')
        )

class TestColDataSubMeta(TestColData):
    coldata_class = ColDataSubMeta

    def test_translate_paths_from(self):

        wc_wp_api_v2_data = {
            u'key': u'_upsell_skus', u'id': 26196, u'value': []
        }

        self.assertEquals(
            self.coldata_class.translate_paths_from(wc_wp_api_v2_data, 'wc-wp-api-v2'),
            {u'meta_key': u'_upsell_skus', u'meta_id': 26196, u'meta_value': []}
        )


if __name__ == '__main__':
    unittest.main()

# TODO: Implement these test cases
#
# def testColDataMyo():
#     print "Testing ColDataMyo Class:"
#     coldata_class = ColDataMyo()
#     print coldata_class.get_import_cols()
#     print coldata_class.get_defaults()
#     print coldata_class.get_product_cols()
#
# def testColDataWoo():
#     print "Testing ColDataWoo class:"
#     coldata_class = ColDataWoo()
#     print coldata_class.get_import_cols()
#     print coldata_class.get_defaults()
#     print coldata_class.get_product_cols()
#
# def testColDataUser():
#     print "Testing ColDataUser class:"
#     coldata_class = ColDataUser()
#     # print "importCols", coldata_class.get_import_cols()
#     # print "userCols", coldata_class.get_user_cols().keys()
#     # print "report_cols", coldata_class.get_report_cols().keys()
#     # print "capitalCols", coldata_class.get_capital_cols().keys()
#     # print "sync_cols", coldata_class.get_sync_cols().keys()
#     print "actCols", coldata_class.get_act_cols().keys()
#     # print "wpcols", coldata_class.get_wp_sql_cols().keys()
#     print "get_wp_tracked_cols", coldata_class.get_wp_tracked_cols()
#     print "get_act_tracked_cols", coldata_class.get_act_tracked_cols()
#     print "get_act_future_tracked_cols", coldata_class.get_act_future_tracked_cols()
#
# def testTansyncDefaults():
#     coldata_class = ColDataUser()
#     print '{'
#     for col, data in coldata_class.get_tansync_defaults().items():
#         print '"%s": %s,' % (col, json.dumps(data))
#     print '}'
#
# if __name__ == '__main__':
#     # testColDataMyo()
#     # testColDataWoo()
#     testColDataUser()
#     # testTansyncDefaults()
