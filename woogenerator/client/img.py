from __future__ import absolute_import

import os

from ..coldata import ColDataAttachment
from .core import SyncClientWP


class ImgSyncClientWP(SyncClientWP):
    endpoint_singular = 'media'
    endpoint_plural = 'media'
    pagination_limit_key = None
    coldata_class = ColDataAttachment
    primary_key_handle = 'id'


    def __init__(self, connect_params, **kwargs):
        connect_params['user_auth'] = True
        connect_params['basic_auth'] = True
        connect_params['query_string_auth'] = False
        super(ImgSyncClientWP, self).__init__(connect_params, **kwargs)

    def upload_image(self, img_path):
        assert os.path.exists(img_path), "img path should be valid: %s" % img_path
        data = open(img_path, 'rb').read()
        filename = os.path.basename(img_path)
        _, extension = os.path.splitext(filename)
        headers = {
            'cache-control': 'no-cache',
            'content-disposition': 'attachment; filename=%s' % filename,
            'content-type': 'image/%s' % extension
        }
        return self.create_item(data, headers=headers)

    def upload_changes_core(self, pkey, updates_core=None):
        if self.primary_key_handle in updates_core:
            del updates_core[self.primary_key_handle]
        updates_api = self.coldata_class.translate_data_to(updates_core, self.coldata_target_write)
        return self.upload_changes(pkey, updates_api)

    def upload_changes(self, pkey, updates=None):
        file_path = updates.pop('file_path')
        if file_path:
            response = self.upload_image(file_path)
            import pudb; pudb.set_trace()
            # maybe set updates['id'] here?
        return super(ImgSyncClientWP, self).upload_changes(updates)

    def analyse_remote_imgs(self, parser, **kwargs):
        # img_api_iterator = self.get_iterator(self.endpoint_plural)
        # for page in img_api_iterator:
        #     if self.page_nesting:
        #         page = page[self.endpoint_plural]
        #     for page_item in page:
        for page in self.get_page_generator():
            for endpoint_item in page:
                parser.analyse_api_image_raw(endpoint_item)
        if self.DEBUG_API:
            self.register_message("Analysed images:")
            self.register_message(parser.to_str_tree())

    def delete_item(self, img_id):
        return super(ImgSyncClientWP, self).delete_item(img_id, force=True)
