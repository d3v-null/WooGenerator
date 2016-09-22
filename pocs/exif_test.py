from PIL import Image
import piexif

filename="/Users/Derwent/Desktop/test.jpg"
im = Image.open(filename)
print im.info
print im.info["exif"]
exif_dict = piexif.load(im.info["exif"])
print exif_dict
# process im and exif_dict...
print exif_dict["0th"]
w, h = im.size
print exif_dict["0th"].get(piexif.ImageIFD.DocumentName)
print exif_dict["0th"].get(piexif.ImageIFD.ImageDescription)
exif_dict["0th"][piexif.ImageIFD.DocumentName] = "NAME"
exif_dict["0th"][piexif.ImageIFD.ImageDescription] = "DESC"
exif_bytes = piexif.dump(exif_dict)
im.save(filename, "jpeg", exif=exif_bytes)
