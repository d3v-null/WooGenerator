from PIL import Image
from PIL import PngImagePlugin
from utils import sanitationUtils
from pyexiv2.metadata import ImageMetadata
import os
from time import time

class MetaGator(object):

	def __init__(self, path):
		super(MetaGator, self).__init__()
		if not os.path.isfile(path):
			raise Exception("file not found")

		self.path = path
		self.dir, self.fname = os.path.split(path)
		self.name, self.ext = os.path.splitext(self.fname)

	def isJPG(self):
		return self.ext.lower() in ['.jpg', '.jpeg']

	def isPNG(self):
		return self.ext.lower() in ['.png']

	def write_meta(self, title, description):
		title, description = map(sanitationUtils.cleanBackslashString, (title, description))
		# print "title, description: ", title, ', ', description
		if self.isPNG():
			# print "image is PNG"
			try:
				new = Image.open(os.path.join(self.dir, self.fname))
			except Exception as e:
				raise Exception('unable to open image: '+str(e))
			meta = PngImagePlugin.PngInfo()
			meta.add_text("title", title)
			meta.add_text("description", description)
			try:	
				new.save(os.path.join(self.dir, self.fname), pnginfo=meta)
			except Exception as e:
				raise Exception('unable to write image: '+str(e))

		elif self.isJPG():
			# print "image is JPG"
			try:
				
				imgmeta = ImageMetadata(os.path.join(self.dir, self.fname))
				imgmeta.read()
			except IOError:
				raise Exception("file not found")

			for index, value in (
				('Exif.Image.DocumentName', title),
				('Exif.Image.ImageDescription', description), 
				('Iptc.Application2.Headline', title),
				('Iptc.Application2.Caption', description),
			):
				# print " -> imgmeta[%s] : %s" % (index, value)
				if index[:4] == 'Iptc' :		
					# print " --> setting IPTC key", index, "to", value
					imgmeta[index] = [value]
				if index[:4] == 'Exif' :
					# print " --> setting EXIF key", index, "to", value
					imgmeta[index] = value
			imgmeta.write()
		else:
			raise Exception("not an image file: ",self.ext)	


	def read_meta(self):
		title, description = '', ''

		if self.isPNG():	
			oldimg = Image.open(os.path.join(self.dir, self.fname))
			title = oldimg.info.get('title','')
			description = oldimg.info.get('description','')
		elif self.isJPG():
			try:
				imgmeta = ImageMetadata(os.path.join(self.dir, self.fname))
				imgmeta.read()
			except IOError:
				raise Exception("file not found")

			for index, field in (
				('Iptc.Application2.Headline', 'title'),
				('Iptc.Application2.Caption', 'description')
			):
				if(index in imgmeta.iptc_keys):
					value = imgmeta[index].value
					if isinstance(value, list):
						value = value[0]

					if field == 'title': title = value
					if field == 'description': description = value
		else:
			raise Exception("not an image file: ",self.ext)	

		return {'title':title, 'description':description}

if __name__ == '__main__':
	print "JPG test"

	print "Test read meta"

	fname = '/Users/Derwent/Dropbox/technotan/CT-TE.jpg'
	metagator = MetaGator(fname)
	print metagator.read_meta()	

	print "test read and write jpg"

	fname = '/Users/Derwent/Dropbox/technotan/reflattened/EAP-PECPRE.jpg'

	metagator = MetaGator(fname)
	metagator.write_meta(u'TITLE \xa9', time())
	print metagator.read_meta()

	print "test read and write png"

	fname = '/Users/Derwent/Dropbox/technotan/reflattened/STFTO-CAL.png'

	metagator = MetaGator(fname)
	metagator.write_meta(u'TITLE \xa9', time())
	print metagator.read_meta()






