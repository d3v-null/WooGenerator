from __future__ import absolute_import

import os

from ..coldata import ColDataAttachment
from .core import SyncClientWP
from copy import deepcopy
from ..utils import ProgressCounter, SeqUtils, Registrar


class ImgSyncClientWP(SyncClientWP):
    endpoint_singular = 'media'
    endpoint_plural = 'media'
    pagination_limit_key = None
    coldata_class = ColDataAttachment
    primary_key_handle = 'id'
    file_path_handle = 'file_path'

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

    def upload_changes_core(self, pkey=None, updates_core=None):
        """
        If file_path in core changes, upload file and get new pkey before
        uploading changes to that record.
        """
        updates_core = deepcopy(updates_core)
        file_path = updates_core.pop(self.file_path_handle, None)
        if file_path:
            response_raw = self.upload_image(file_path)
            response_api = response_raw.json()
            if self.page_nesting:
                response_api = response_api.get(self.endpoint_singular)
            response_core = self.coldata_class.translate_data_from(
                response_api, self.coldata_target_write
            )
            pkey = response_core.pop(self.primary_key_handle)
        return super(ImgSyncClientWP, self).upload_changes_core(pkey, updates_core)

    def create_item_core(self, core_data):
        """
        If file_path in core changes, upload file and get new pkey before
        uploading changes to that record.
        """
        file_path = core_data.get(self.file_path_handle)
        if file_path:
            return self.upload_changes_core(None, core_data)

    def analyse_remote_imgs(self, parser, **kwargs):
        # img_api_iterator = self.get_iterator(self.endpoint_plural)
        # for page in img_api_iterator:
        #     if self.page_nesting:
        #         page = page[self.endpoint_plural]
        #     for page_item in page:
        skip_unattached_images = kwargs.pop('skip_unattached_images', None)
        if skip_unattached_images:
            attachment_ids = SeqUtils.filter_unique_true([
                attachment.get_attachment_id(attachment) \
                for attachment in parser.attachments.values()
            ])
            progress_counter = ProgressCounter(
                len(attachment_ids), items_plural='images', verb_past='analysed'
            )
            for count, attachment_id in enumerate(attachment_ids):
                if Registrar.DEBUG_PROGRESS:
                    progress_counter.maybe_print_update(count)
                self.analyse_single_reomte_img(
                    parser, attachment_id, **kwargs
                )
        else:
            for page in self.get_page_generator():
                for endpoint_item in page:
                    parser.analyse_api_image_raw(endpoint_item)

    def analyse_single_reomte_img(self, parser, pkey, **kwargs):
        assert pkey, "pkey must be provided to analyse single image"
        endpoint_response = self.get_single_endpoint_item(pkey)
        endpoint_item = endpoint_response.json()
        if self.page_nesting:
            endpoint_item = endpoint_item[self.endpoint_singular]
        parser.analyse_api_image_raw(endpoint_item)

    def delete_item(self, img_id):
        return super(ImgSyncClientWP, self).delete_item(img_id, force=True)
