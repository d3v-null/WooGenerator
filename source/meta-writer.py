import PIL
from PIL import Image
from PIL import PngImagePlugin
import pyexiv2
import os

class MetaWriter(object):

	"""docstring for MetaWriter"""
	def __init__(self, path):
		super(MetaWriter, self).__init__()
		if not os.path.isfile(path):
			raise Exception("file not found")

		self.dir, self.fname = os.path.split(path)

	def write_meta(self, title, description):
		name, ext = self.split_file(self.fname)
		if(ext in ['png']):
			try:
				new = Image.open(self.fname)
				meta = PngImagePlugin.PngInfo()
				meta.add_text("title", title)
				meta.add_text("description", description)
				new.write(join(self.dir, self.fname), pnginfo=meta)
			except Exception as e:
				raise e

		elif(ext in ['jpeg', 'jpg']):
			try:
				imgmeta = pyexiv2.ImageMetadata(os.path.join(self.dir, self.fname))
				imgmeta.read()
			except IOError:
				raise Exception("file not found")

			for index, value in (
				('Exif.Image.ImageDescription', description), 
				('Iptc.Application2.Headline', [title]),
				('Iptc.Application2.Caption', [description]),
			):
				# print " -> imgmeta[%s] : %s" % (index, value)
				oldvalue = ''
				if index in imgmeta.iptc_keys + imgmeta.exif_keys:		
					mo = re.search("<(?P<index>\S+) \[(?P<type>\S+)\] = (?P<value>.*)>", str(imgmeta[index]))
					if mo:
						oldvalue = mo.groupdict().get('value','')
				if oldvalue != str(value): 
					cm.append("changing imgmeta[%s] from %s to %s" % (index, str(oldvalue)[:20], str(value)[:20]))
					if remeta:
						imgmeta[index] = value
						imgmeta.write()