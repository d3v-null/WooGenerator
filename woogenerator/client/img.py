import os

from .core import SyncClientWP


class ImgSyncClientWP(SyncClientWP):
    endpoint_singular = 'media'
    endpoint_plural = 'media'
    pagination_limit_key = None

    def __init__(self, connect_params, **kwargs):
        connect_params['user_auth'] = True
        connect_params['basic_auth'] = True
        connect_params['query_string_auth'] = False
        super(ImgSyncClientWP, self).__init__(connect_params, **kwargs)

    def upload_image(self, img_path):
        assert os.path.exists(img_path), "img should exist"
        data = open(img_path, 'rb').read()
        filename = os.path.basename(img_path)
        _, extension = os.path.splitext(filename)
        headers = {
            'cache-control': 'no-cache',
            'content-disposition': 'attachment; filename=%s' % filename,
            'content-type': 'image/%s' % extension
        }
        return self.create_item(data, headers=headers)

    def analyse_remote_imgs(self, parser, **kwargs):
        img_api_iterator = self.get_iterator(self.endpoint_plural)
        for page in img_api_iterator:
            if self.page_nesting:
                page = page['media']
            for page_item in page:
                parser.process_api_image(page_item)
        if self.DEBUG_API:
            self.register_message("Analysed images:")
            self.register_message(parser.to_str_tree())

    def delete_item(self, img_id):
        return super(ImgSyncClientWP, self).delete_item(img_id, force=True)
