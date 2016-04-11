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
from base64 import b64encode

def key_compare(a, b):
	return cmp(a[0], b[0])

class API_Client(object):
	def __init__(self, endpoint):
		super(API_Client, self).__init__()
		self.endpoint = endpoint

	def make_request(self, resource, params, method='GET' ):
		pass

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

class Basic_Client(API_Client):
	def __init__(self, endpoint, username=None, password=None):
		super(Basic_Client, self).__init__(endpoint)
		self.username = username
		self.password = password
		self.http = httplib2.Http(".cache")
		self.http.add_credentials(self.username, self.password)

	def make_request(self, resource, params, method='GET' ):
		clean_params = self.sort_params(self.normalize_params(params))
		uri = self.endpoint + resource
		p_string = urlencode(clean_params)

		userAndPass = b64encode(b"username:password").decode("ascii")
		headers = { 'Authorization' : 'Basic %s' %  userAndPass }

		uri_params = uri + ('' if not p_string else '?' + p_string )

		print uri_params

		return self.http.request(uri_params, method, headers=headers)

class OAuth_1_Client(API_Client):

	def __init__(self, endpoint, consumer_key=None, consumer_secret=None):
		super(OAuth_1_Client, self).__init__(endpoint)
		self.consumer_key = consumer_key
		self.consumer_secret = consumer_secret
		self.http = httplib2.Http()

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

		uri = self.endpoint + resource
		p_string = urlencode(clean_params)

		print 'p string:'
		print '\n'.join(p_string.split('&'))

		uri_params = uri + ('' if not p_string else '?' + p_string )

		return self.http.request(uri_params, method)

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

	def gen_timestamp(self):
		return int(time.time())
		# return 1429451603

	def gen_nonce(self):
		return hex(self.gen_timestamp())
		#todo: make this more secure

def testWithLocal():
	store_url = 'http://derwent-mac.ddns.me:8888/wordpress'
	api_base = 'wc-api'
	api_ver = 'v2'
	endpoint = "%s/%s/%s/" % (store_url, api_base, api_ver)

	consumer_key = 'ck_1a7b30cebdb03329517ae0ae23b4a34e'
	consumer_secret = 'cs_79ab1feeed05b6cfff7deaef9c164a6a'

	resource = 'customers'
	parameters = {
	}


	rc = OAuth_1_Client(endpoint, consumer_key, consumer_secret)
	r, c = rc.make_request(resource, parameters, 'GET')
	print r
	print c	

def testWithMinimac():
	store_url = 'http://minimac.derwent-asus.ddns.me:11182/'
	api_base = 'wp-json/wp'
	api_ver = 'v2'
	endpoint = "%s/%s/%s/" % (store_url, api_base, api_ver)

	# consumer_key = 'gkPUTHeTta3M'
	# consumer_secret = '77hxCG51gV8nJHRMJqjFgbdQmhkykaZFqtLsyRVcI7EOoprF'

	username = 'Neil'
	password = 'Stretch6164'

	resource = 'posts'
	parameters = {
		# 'first_name':'asd'
	}


	rc = Basic_Client(endpoint, username, password)
	r, c = rc.make_request(resource, parameters, 'GET')
	print r
	print c	

if __name__ == "__main__":
	testWithMinimac()

