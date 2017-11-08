import os
import shutil
import tempfile
import unittest

from context import TESTS_DATA_DIR, woogenerator
from woogenerator.images import MetaGator
from woogenerator.utils import Registrar, TimeUtils


class testMetaGator(unittest.TestCase):
    local_work_dir = TESTS_DATA_DIR

    def setUp(self):
        self.local_work_dir = TESTS_DATA_DIR
        # assert os.path.isdir(self.local_work_dir)
        self.newmeta = {
            'title': u'TITLE \xa9 \u2014',
            'description': unicode(TimeUtils.get_ms_timestamp())
        }

        Registrar.DEBUG_ERROR = False
        Registrar.DEBUG_WARN = False
        Registrar.DEBUG_MESSAGE = False
        Registrar.DEBUG_PROGRESS = False

    def create_temporary_copy(self, path):
        temp_basename = os.path.basename(path)
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, temp_basename)
        shutil.copy2(path, temp_path)
        return temp_path

    def test_JPG_Read(self):

        file_path = os.path.join(self.local_work_dir, 'sample_img.jpg')
        file_path = self.create_temporary_copy(file_path)
        metagator = MetaGator(file_path)
        response = metagator.read_meta()
        self.assertTrue(response)
        self.assertEquals({'title':u'', 'description':u''}, response)

    def test_JPG_Write(self):
        file_path = os.path.join(self.local_work_dir, 'sample_img.jpg')
        file_path = self.create_temporary_copy(file_path)

        metagator = MetaGator(file_path)
        metagator.write_meta(
            self.newmeta['title'],
            self.newmeta['description']
        )
        metagator.update_meta(self.newmeta)
        response = metagator.read_meta()
        self.assertTrue(response)
        self.assertEquals(response, self.newmeta)

    def test_PNG_Write(self):
        file_path = os.path.join(self.local_work_dir, 'sample_img.png')
        file_path = self.create_temporary_copy(file_path)

        metagator = MetaGator(file_path)
        metagator.write_meta(
            self.newmeta['title'],
            self.newmeta['description']
        )
        response = metagator.read_meta()
        self.assertTrue(response)
        self.assertEquals(response, self.newmeta)



if __name__ == '__main__':
    unittest.main()
