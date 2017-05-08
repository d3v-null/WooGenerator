"""
Utilities for mitigating images metadata.
"""

import os
from PIL import Image, ImageFile, PngImagePlugin

import piexif

from woogenerator.utils import SanitationUtils, Registrar
ImageFile.LOAD_TRUNCATED_IMAGES = True

class MetaGator(Registrar):
    """
    Mitigates image metadata.
    """

    def __init__(self, path):
        super(MetaGator, self).__init__()
        if not os.path.isfile(path):
            raise Exception("file not found: " + path)

        self.path = path
        self.dir, self.fname = os.path.split(path)
        self.name, self.ext = os.path.splitext(self.fname)

    @property
    def is_jpg(self):
        return self.ext.lower() in ['.jpg', '.jpeg']

    @property
    def is_png(self):
        return self.ext.lower() in ['.png']

    def write_meta(self, title, description):
        title, description = map(
            SanitationUtils.coerce_ascii, (title, description))
        # print "title, description: ", title, ', ', description
        if self.is_png:
            # print "image is PNG"
            try:
                new = Image.open(os.path.join(self.dir, self.fname))
            except Exception as exc:
                raise Exception('unable to open image: ' + str(exc))
            meta = PngImagePlugin.PngInfo()
            meta.add_text("title", title)
            meta.add_text("description", description)
            try:
                new.save(os.path.join(self.dir, self.fname), pnginfo=meta)
            except Exception as exc:
                raise Exception('unable to write image: ' + str(exc))

        elif self.is_jpg:
            # print "image is JPG"
            fullname = os.path.join(self.dir, self.fname)
            try:
                img = Image.open(fullname)
            except IOError:
                raise Exception("file not found: " + fullname)

            # write exif
            exif_dict = piexif.load(img.info["exif"])

            exif_dict["0th"][piexif.ImageIFD.DocumentName] = title
            exif_dict["0th"][piexif.ImageIFD.ImageDescription] = description

            exif_bytes = piexif.dump(exif_dict)
            img.save(fullname, "jpeg", exif=exif_bytes)

            # write IPTC

            # for index, value in (
            #     ('Exif.Image.DocumentName', title),
            #     ('Exif.Image.ImageDescription', description),
            #     ('Iptc.Application2.Headline', title),
            #     ('Iptc.Application2.Caption', description),
            # ):
            #     # print " -> imgmeta[%s] : %s" % (index, value)
            #     if index[:4] == 'Iptc' :
            #         # print " --> setting IPTC key", index, "to", value
            #         imgmeta[index] = [value]
            #     if index[:4] == 'Exif' :
            #         # print " --> setting EXIF key", index, "to", value
            #         imgmeta[index] = value
            # imgmeta.write()
        else:
            raise Exception("not an image file: ", self.ext)

    def read_meta(self):
        title, description = u'', u''

        if self.is_png:
            oldimg = Image.open(os.path.join(self.dir, self.fname))
            title = oldimg.info.get('title', '')
            description = oldimg.info.get('description', '')
        elif self.is_jpg:
            fullname = os.path.join(self.dir, self.fname)
            try:
                img = Image.open(fullname)
                # imgmeta = ImageMetadata(os.path.join(self.dir, self.fname))
                # imgmeta.read()
            except IOError:
                raise Exception("file not found")

            exif_dict = piexif.load(img.info["exif"])

            title = exif_dict["0th"].get(piexif.ImageIFD.DocumentName)
            description = exif_dict["0th"].get(
                piexif.ImageIFD.ImageDescription)
            #
            # for index, field in (
            #     ('Iptc.Application2.Headline', 'title'),
            #     ('Iptc.Application2.Caption', 'description')
            # ):
            #     if(index in imgmeta.iptc_keys):
            #         value = imgmeta[index].value
            #         if isinstance(value, list):
            #             value = value[0]
            #
            #         if field == 'title': title = value
            #         if field == 'description': description = value
        else:
            raise Exception("not an image file: ", self.ext)

        title, description = tuple(
            map(SanitationUtils.ascii_to_unicode, [title, description]))
        return {'title': title, 'description': description}

    def update_meta(self, newmeta):
        oldmeta = self.read_meta()
        newmeta = dict([(key, SanitationUtils.coerce_ascii(value))
                        for key, value in newmeta.items()])
        changed = []
        for key in ['title', 'description']:
            if SanitationUtils.similar_comparison(
                    oldmeta[key]) != SanitationUtils.similar_comparison(newmeta[key]):
                changed += [key]
                if self.DEBUG_IMG:
                    self.register_message(
                        u"changing imgmeta[%s] from %s to %s" % (
                            key, repr(oldmeta[key]), repr(newmeta[key])),
                        self.fname
                    )
        if changed:
            self.write_meta(newmeta['title'], newmeta['description'])
