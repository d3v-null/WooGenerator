import random
import time
from urlparse import parse_qsl, urlparse
from urllib import quote, urlencode
import urllib2
import binascii
import hashlib
import hmac
import webbrowser
import requests
from collections import OrderedDict

WP_CONSUMER_KEY = 'LCLwTOfxoXGh'
WP_CONSUMER_SECRET = 'k7zLzO3mF75Xj65uThpAnNvQHpghp4X1h5N20O8hCbz2kfJq'
WC_CONSUMER_KEY = 'ck_681c2be361e415519dce4b65ee981682cda78bc6'
WC_CONSUMER_SECRET = 'cs_b11f652c39a0afd3752fc7bb0c56d60d58da5877'
CONSUMER_KEY = 'your_app_key'
CONSUMER_SECRET = 'your_app_secret'
CALL_BACK = 'http://127.0.0.1/oauth1_callback'
REQUEST_TOKEN_URL = 'https://bitbucket.org/api/1.0/oauth/request_token'

# REQUEST_TOKEN_URL = 'http://localhost:8888/wordpress/oauth1/request'
# CALL_BACK = 'localhost:8888/wordpress'

q = lambda x: quote(x, safe="~")
get_timestamp = lambda: '1427366369'
# get_timestamp = lambda: int(time.time())
get_nonce = lambda: '27718007815082439851427366369'
# get_nonce = lambda: str(str(random.getrandbits(64)) + str(get_timestamp()))


def get_sign(params, url, http_method, consumer_secret='', oauth_token_secret=""):
    """returns HMAC-SHA1 sign"""
    params.sort()
    normalized_params = urlencode(params)

    hmac_msg = "&".join((http_method, q(url), q(normalized_params)))
    hmac_key = "&".join([consumer_secret, oauth_token_secret])
    sig = hmac.new(hmac_key, hmac_msg, hashlib.sha1)
    sig_b64 = binascii.b2a_base64(sig.digest())[:-1]
    print "params", params
    print "normalized_params", normalized_params
    print "hmac_msg: ", hmac_msg
    print "hmac_key: ", hmac_key
    print "sig_b64: ", sig_b64
    return sig_b64

params_request_token = [
    ('oauth_consumer_key', CONSUMER_KEY),
    ('oauth_nonce', get_nonce()),
    ('oauth_signature_method', "HMAC-SHA1"),
    ('oauth_timestamp', get_timestamp()),
    ('oauth_callback', CALL_BACK),
    ('oauth_version', '1.0'),
]
signature = get_sign(params_request_token,
                     REQUEST_TOKEN_URL, "POST", CONSUMER_SECRET)

quit()

params = [
    ('oauth_consumer_key', WC_CONSUMER_KEY),
    ('oauth_nonce', get_nonce()),
    ('oauth_signature_method', "HMAC-SHA1"),
    ('oauth_timestamp', get_timestamp()),
    ('oauth_callback', CALL_BACK),
    ('oauth_version', '1.0'),
]
# target_url = 'http://localhost:8888/wordpress/wc-api/v3/products/99'
# target_data = '{"product": {"title": "Woo Single #2b"}}'
target_url = 'http://localhost:8888/wordpress/wc-api/v3/products'
target_data = ''
# params.append(('page', '2'))

signature = get_sign(params, target_url, "POST", WC_CONSUMER_SECRET)
params.append(('oauth_signature', signature))
r = requests.post(url=target_url, params=params, data=target_data)

# params = [
#     ('oauth_consumer_key', WP_CONSUMER_KEY),
#     ('oauth_nonce', get_nonce()),
#     ('oauth_signature_method', "HMAC-SHA1"),
#     ('oauth_timestamp', get_timestamp()),
#     ('oauth_callback', CALL_BACK),
#     ('oauth_version', '1.0'),
# ]
# target_url = REQUEST_TOKEN_URL
# signature = get_sign(params, target_url, "POST", WP_CONSUMER_SECRET)
# params.append(('oauth_signature', signature))
#
# r = requests.post(url=target_url, params=params, data='{"product":
# {"title": "Woo Single #2a"}}')

print r.status_code
print r.text
