from PIL import Image
from PIL import PngImagePlugin
# from pillow import Image
# from pillow import PngImagePlugin
from utils import SanitationUtils, Registrar
# from pyexiv2.metadata import ImageMetadata
import piexif
# import iptcinfo
import os
# from time import time


class MetaGator(Registrar):

    def __init__(self, path):
        super(MetaGator, self).__init__()
        if not os.path.isfile(path):
            raise Exception("file not found: " + path)

        self.path = path
        self.dir, self.fname = os.path.split(path)
        self.name, self.ext = os.path.splitext(self.fname)

    @property
    def isJPG(self):
        return self.ext.lower() in ['.jpg', '.jpeg']

    @property
    def isPNG(self):
        return self.ext.lower() in ['.png']

    def write_meta(self, title, description):
        title, description = map(
            SanitationUtils.coerceAscii, (title, description))
        # print "title, description: ", title, ', ', description
        if self.isPNG:
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

        elif self.isJPG:
            # print "image is JPG"
            fullname = os.path.join(self.dir, self.fname)
            try:
                im = Image.open(fullname)
            except IOError:
                raise Exception("file not found: " + fullname)

            # write exif
            exif_dict = piexif.load(im.info["exif"])

            exif_dict["0th"][piexif.ImageIFD.DocumentName] = title
            exif_dict["0th"][piexif.ImageIFD.ImageDescription] = description

            exif_bytes = piexif.dump(exif_dict)
            im.save(fullname, "jpeg", exif=exif_bytes)

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

        if self.isPNG:
            oldimg = Image.open(os.path.join(self.dir, self.fname))
            title = oldimg.info.get('title', '')
            description = oldimg.info.get('description', '')
        elif self.isJPG:
            fullname = os.path.join(self.dir, self.fname)
            try:
                im = Image.open(fullname)
                # imgmeta = ImageMetadata(os.path.join(self.dir, self.fname))
                # imgmeta.read()
            except IOError:
                raise Exception("file not found")

            exif_dict = piexif.load(im.info["exif"])

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
            map(SanitationUtils.asciiToUnicode, [title, description]))
        return {'title': title, 'description': description}

    def update_meta(self, newmeta):
        oldmeta = self.read_meta()
        newmeta = dict([(key, SanitationUtils.coerceAscii(value))
                        for key, value in newmeta.items()])
        changed = []
        for key in ['title', 'description']:
            if SanitationUtils.similarComparison(oldmeta[key]) != SanitationUtils.similarComparison(newmeta[key]):
                changed += [key]
                if self.DEBUG_IMG:
                    self.registerMessage(
                        u"changing imgmeta[%s] from %s to %s" % (
                            key, repr(oldmeta[key]), repr(newmeta[key])),
                        self.fname
                    )
        if changed:
            self.write_meta(newmeta['title'], newmeta['description'])
