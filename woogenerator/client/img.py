from .core import SyncClientWP
import os

class ImgSyncClient(SyncClientWP):
    endpoint_singular = 'media'
    endpoint_plural = 'media'

    def __init__(self, connect_params, **kwargs):
        connect_params['user_auth'] = True
        connect_params['basic_auth'] = True
        connect_params['query_string_auth'] = False
        super(ImgSyncClient, self).__init__(connect_params, **kwargs)

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

    def delete_item(self, img_id):
        return super(ImgSyncClient, self).delete_item(img_id, force=True)
