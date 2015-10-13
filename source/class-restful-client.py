import requests
import random
import string
import time
from hashlib import sha1
import hmac
import binascii
import re
from urllib import quote, urlencode
import httplib2
from collections import OrderedDict
import json

def key_compare(a, b):
	return cmp(a[0], b[0])

class Restful_Client(object):
	"""docstring for Restful_Client"""
	def __init__(self, endpoint, consumer_key, consumer_secret):
		super(Restful_Client, self).__init__()
		self.consumer_key = consumer_key
		self.consumer_secret = consumer_secret
		self.endpoint = endpoint
		
	def make_request(self, resource, params, method='GET' ):
		oauth_params = {
			'oauth_consumer_key': self.consumer_key,
			'oauth_nonce': self.gen_nonce(),
			'oauth_timestamp': self.gen_timestamp(),
			'oauth_signature_method': 'HMAC-SHA1',
			# 'oauth_version':'1.0'
		}
		oauth_params['oauth_signature'] = self.gen_signature(
			resource,
			OrderedDict( params.items() + oauth_params.items() ),
			method
		)
		params = OrderedDict( params.items() + oauth_params.items() )
		clean_params = self.sort_params(self.normalize_params(params))

		uri = endpoint + resource
		p_string = urlencode(clean_params)

		print 'p string:'
		print '\n'.join(p_string.split('&'))

		return httplib2.Http().request(uri + '?' + p_string)

	def gen_signature(self, resource, params, method):
		base_request_uri = quote(self.endpoint + resource, safe = "")
		clean_params = self.sort_params(
			self.normalize_params(
				self.normalize_params(
					params
				)
			)
		)
		query_string = '%26'.join([
			key + '%3D' + value\
			for key, value in clean_params.iteritems()
		])
		raw_string = '&'.join([method, base_request_uri, query_string]) 
		print "raw string: "
		print '\n'.join(raw_string.split('%26'))
		hashed = hmac.new(self.consumer_secret, raw_string, sha1)
		return binascii.b2a_base64( hashed.digest() )[:-1]

	def normalize_string(self, s):
		return quote(str(s), safe="")

	def normalize_params(self, params):
		return OrderedDict( [
			(self.normalize_string(key), self.normalize_string(value))\
			for key, value \
			in params.iteritems()
		])

	def sort_params(self, params):
		return OrderedDict(sorted(
			params.iteritems(),
			cmp=key_compare
		))

	def gen_timestamp(self):
		return int(time.time())
		# return 1429451603

	def gen_nonce(self):
		return hex(self.gen_timestamp())
		#todo: make this more secure

if __name__ == "__main__":
	store_url = 'http://derwent-mac.ddns.me:8888/wordpress'
	api_base = 'wc-api'
	api_ver = 'v2'
	endpoint = "%s/%s/%s/" % (store_url, api_base, api_ver)

	consumer_key = 'ck_1a7b30cebdb03329517ae0ae23b4a34e'
	consumer_secret = 'cs_79ab1feeed05b6cfff7deaef9c164a6a'

	resource = 'customers'
	parameters = {
		# 'filter[role]':'wholesale',
	# 	'filter[q]':'biotan',
	# 	'fields':'id,title'
	}


	rc = Restful_Client(endpoint, consumer_key, consumer_secret)
	r, c = rc.make_request(resource, parameters, 'GET')
	print r
	print c

