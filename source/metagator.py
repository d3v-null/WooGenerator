from PIL import Image
from PIL import PngImagePlugin
from pyexiv2.metadata import ImageMetadata
import os
from time import time

class MetaGator(object):

	"""docstring for MetaGator"""
	def __init__(self, path):
		super(MetaGator, self).__init__()
		if not os.path.isfile(path):
			raise Exception("file not found")

		self.dir, self.fname = os.path.split(path)

	def write_meta(self, title, description):
		name, ext = os.path.splitext(self.fname)
		title, description = map(str, (title, description))
		if( ext.lower() in ['.png']):
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

		elif(ext.lower() in ['.jpeg', '.jpg']):
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
					# print " --> setting IPTC key"
					imgmeta[index] = [value]
				if index[:4] == 'Exif' :
					# print " --> setting EXIF key"
					imgmeta[index] = value
			imgmeta.write()
		else:
			raise Exception("not an image file")



	def read_meta(self):
		name, ext = os.path.splitext(self.fname)
		title, description = '', ''

		if(ext.lower() in ['.png']):	
			oldimg = Image.open(os.path.join(self.dir, self.fname))
			title = oldimg.info.get('title','')
			description = oldimg.info.get('description','')
		elif(ext.lower() in ['.jpeg', '.jpg']):
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
			raise Exception("not an image file")	

		return {'title':title, 'description':description}

if __name__ == '__main__':
	print "JPG test"

	fname_src = '/Users/Derwent/Dropbox/technotan/reflattened/EAP-PECPRE.jpg'

	metagator_src = MetaGator(fname_src)
	metagator_src.write_meta('TITLE', time())
	print metagator_src.read_meta()

	fname_src = '/Users/Derwent/Dropbox/technotan/reflattened/STFTO-CAL.png'

	metagator_src = MetaGator(fname_src)
	metagator_src.write_meta('TITLE', time())
	print metagator_src.read_meta()






