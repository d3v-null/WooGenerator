import os
from time import time
from os import sys, path
from unittest import TestCase, main, skip, TestSuite, TextTestRunner

from context import woogenerator
from context import get_testdata, tests_datadir
from woogenerator.metagator import MetaGator

class testMetaGator(TestCase):
    def setUp(self):
        self.work_dir = tests_datadir
        # assert os.path.isdir(self.work_dir)
        self.newmeta = {
            'title': u'TITLE \xa9 \u2014',
            'description': time()
        }


    def test_JPG_Read(self):

        fname = os.path.join(self.work_dir, 'CT-TE.jpg')
        metagator = MetaGator(fname)
        print metagator.read_meta()

    def test_JPG_Write(self):
        fname = os.path.join(self.work_dir, 'EAP-PECPRE.jpg')

        metagator = MetaGator(fname)
        metagator.write_meta(self.newmeta['title'], self.newmeta['description'])
        metagator.update_meta(self.newmeta)
        print metagator.read_meta()

    def test_PNG_Write(self):
        fname = os.path.join(self.work_dir, 'STFTO-CAL.png')

        metagator = MetaGator(fname)
        metagator.write_meta(u'TITLE \xa9 \u2014', time())
        print metagator.read_meta()


if __name__ == '__main__':
    main()
