"""
Utilities for processing images and image metadata.
"""

from __future__ import absolute_import

import os
import shutil
import traceback


import piexif
from PIL import Image, ImageFile, PngImagePlugin

from .utils import Registrar, SanitationUtils

ImageFile.LOAD_TRUNCATED_IMAGES = True

def get_mime_type(extension):
    if extension.lower() in [
        '.jpg', '.jpeg', '.jfif', '.jpe'
    ]:
        return 'image/jpeg'
    if extension.lower() in [
        '.png', '.x-png'
    ]:
        return 'image/png'
    if extension.lower() in [
        '.jp2', '.jpg2'
    ]:
        return 'image/jp2'

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
        return get_mime_type(self.ext) in ['image/jpeg', 'image/jp2']

    @property
    def is_png(self):
        return get_mime_type(self.ext) in ['image/png']

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
            exif_dict = dict()
            if 'exif' in img.info:
                exif_dict = piexif.load(img.info["exif"])

            if '0th' not in exif_dict:
                exif_dict['0th'] = {}
            exif_dict['0th'][piexif.ImageIFD.DocumentName] = title
            exif_dict['0th'][piexif.ImageIFD.ImageDescription] = description

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

            exif_dict = {}
            if "exif" in img.info:
                exif_dict = piexif.load(img.info["exif"])

            exif_dict_0 = exif_dict.get("0th", {})
            title = exif_dict_0.get(piexif.ImageIFD.DocumentName, '')
            description = exif_dict_0.get(piexif.ImageIFD.ImageDescription, '')
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
            if 'title' not in changed:
                newmeta['title'] = oldmeta['title']
            if 'description' not in changed:
                newmeta['description'] = oldmeta['description']
            self.write_meta(newmeta['title'], newmeta['description'])



def invalid_image(parsers, settings, img_name, error):
    """Register error globally and attribute to image."""
    if settings.require_images:
        Registrar.register_error(error, img_name)
    else:
        Registrar.register_message(error, img_name)
    parsers.master.images[img_name].invalidate(error)

def get_raw_image(settings, img_name):
    """
    Find the path of the image in the raw image dirs.

    Args:
        img_name (str):
            the name of the file to search for

    Returns:
        The path of the image within the raw image dirs

    Raises:
        IOError: file could not be found
    """
    for path in settings.img_raw_dirs:
        if path and img_name in settings.img_raw_dir_contents[path]:
            return os.path.join(path, img_name)
    raise IOError("no image named %s found" % str(img_name))

def remeta_image(settings, parsers, img_data):
    if Registrar.DEBUG_IMG:
        Registrar.register_message("img_data_id: %s" % id(img_data))

    try:
        metagator = MetaGator(get_raw_image(settings, img_data.file_name))
    except Exception as exc:
        invalid_image(
            parsers,
            settings,
            img_data.file_name,
            "error creating metagator: " + str(exc)
        )
        return

    try:
        title, description = img_data.attachments.title, img_data.attachments.description

        metagator.update_meta({
            'title': title,
            'description': description
        })

        img_data[img_data.title_key] = title
        img_data['alt_text'] = title
        img_data['caption'] = description
        img_data['description'] = description
    except Exception as exc:
        invalid_image(
            parsers, settings, img_data.file_name, "error updating meta: " + str(exc)
        )
        Registrar.register_error(traceback.format_exc())
        return
    return img_data

def resize_image(settings, parsers, img_data):
    if Registrar.DEBUG_IMG:
        Registrar.register_message("img_data_id: %s" % id(img_data))

    img_raw_path = get_raw_image(settings, img_data.file_name)
    if not os.path.isfile(img_raw_path):
        invalid_image(
            parsers,
            settings,
            img_data.file_name, "SOURCE FILE NOT FOUND: %s" % img_raw_path
        )
        return

    img_dst_path = os.path.join(settings.img_dst, img_data.file_name)
    if os.path.isfile(img_dst_path):
        img_src_mod = max(
            os.path.getmtime(img_raw_path),
            os.path.getctime(img_raw_path))
        img_dst_mod = os.path.getmtime(img_dst_path)
        # print "image mod (src, dst): ", img_src_mod, imgdstmod
        if img_dst_mod > img_src_mod:
            if Registrar.DEBUG_IMG:
                Registrar.register_message(
                    img_data.file_name, "DESTINATION FILE NEWER: %s" % img_dst_path)
            return

    if Registrar.DEBUG_IMG:
        Registrar.register_message("resizing: %s" % img_data.file_name)

    shutil.copy(img_raw_path, img_dst_path)

    # import pudb; pudb.set_trace()

    img_data[img_data.file_path_key] = img_dst_path

    try:
        title, description = img_data.attachments.title, img_data.attachments.description

        imgmeta = MetaGator(img_dst_path)
        imgmeta.write_meta(title, description)
        if Registrar.DEBUG_IMG:
            Registrar.register_message(
                "old dest img meta: %s" %
                imgmeta.read_meta(), img_data.file_name)

        img_data[img_data.title_key] = title
        img_data['alt_text'] = title
        img_data['caption'] = description
        img_data['description'] = description

        image = Image.open(img_dst_path)
        image.thumbnail(settings.thumbsize)
        image.save(img_dst_path)

        img_data['width'] = settings.thumbsize[0]
        img_data['height'] = settings.thumbsize[1]

        if settings.do_remeta_images:
            imgmeta = MetaGator(img_dst_path)
            imgmeta.write_meta(title, description)
            if Registrar.DEBUG_IMG:
                Registrar.register_message(
                    "new dest img meta: %s" % imgmeta.read_meta(),
                    img_data.file_name
                )
    except IOError as exc:
        invalid_image(
            parsers, settings, img_data.file_name, "could not resize: " + str(exc)
        )
        return

    return img_data

def process_images(settings, parsers):
    """Process the images information in from the parsers."""
    Registrar.register_progress("processing images")

    if Registrar.DEBUG_IMG:
        Registrar.register_message("Looking in dirs: %s" %
                                   settings.img_raw_dirs)

    if not os.path.exists(settings.img_dst):
        os.makedirs(settings.img_dst)

    # list of images in compressed directory
    ls_cmp = os.listdir(settings.img_dst)
    for fname in ls_cmp:
        if fname not in parsers.master.images.keys():
            Registrar.register_warning("DELETING FROM REFLATTENED", fname)
            if settings.do_delete_images:
                os.remove(os.path.join(settings.img_dst, fname))

    # for img_filename, obj_list in parsers.master.images.items():
    for img_data in parsers.master.images.values():
        img_filename = os.path.basename(img_data.file_name)
        if not img_data.attachments.products or img_data.attachments.categories:
            continue
            # we only care about product / category images atm
        if Registrar.DEBUG_IMG:
            if img_data.attachments.categories:
                Registrar.register_message(
                    "Associated Taxos: %s" % str([
                        (taxo.rowcount, taxo.codesum) for taxo in img_data.attachments.categories
                    ]),
                    img_filename
                )

            if img_data.attachments.products:
                Registrar.register_message(
                    "Associated Products: %s" % str([
                        (item.rowcount, item.codesum) for item in img_data.attachments.products
                    ]),
                    img_filename
                )

        # import pudb; pudb.set_trace()

        try:
            img_raw_path = get_raw_image(settings, img_filename)
            img_data[img_data.file_path_key] = img_raw_path
        except IOError as exc:
            invalid_image(
                parsers,
                settings,
                img_filename,
                UserWarning("could not get raw image: %s " % repr(exc))
            )
            continue

        name, ext = os.path.splitext(img_filename)
        if not name:
            invalid_image(
                parsers,
                settings,
                img_filename,
                UserWarning("could not extract name")
            )
            continue

        mime_type = get_mime_type(ext)
        if not mime_type:
            invalid_image(
                parsers,
                settings,
                img_filename,
                UserWarning("invalid image extension")
            )
            continue

        img_data['mime_type'] = mime_type

        # import pudb; pudb.set_trace()

        try:
            title, description = img_data.attachments.title, img_data.attachments.description
        except AttributeError as exc:
            invalid_image(
                parsers,
                settings,
                img_filename,
                "could not get title or description: " + str(exc)
            )
            continue

        if Registrar.DEBUG_IMG:
            Registrar.register_message("title: %s | description: %s" %
                                       (title, description), img_filename)

        # ------
        # REMETA
        # ------

        if settings.do_remeta_images:
            if not remeta_image(settings, parsers, img_data):
                continue

        # ------
        # RESIZE
        # ------

        if settings.do_resize_images:
            if not resize_image(settings, parsers, img_data):
                continue

    return parsers