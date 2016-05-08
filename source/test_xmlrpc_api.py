# -*- coding: utf-8 -*-
from wordpress_xmlrpc import Client
from wordpress_xmlrpc import AuthenticatedMethod
from utils import SanitationUtils
# from wordpress_xmlrpc.methods import posts

class UpdateUser(AuthenticatedMethod):
    method_name = 'tansync.update_user_fields'
    method_args = ('user_id', 'fields_json_base64')

username = 'Neil'
password = 'Stretch6164'
store_url = 'http://minimac.ddns.me:11182/'

# store_url = 'http://technotea.com.au/'
# username = 'Neil'
# password = 'Stretch6164'
xmlrpc_uri = store_url + 'xmlrpc.php'

client = Client(xmlrpc_uri, username, password)
# posts = client.call(posts.GetPosts())
# print posts

# print client.normalize_string(u'no\u2015odle')

fields = {
    'first_name': 'no👌od👌le'.decode('utf8'),
    'user_url': "http://www.laserphile.com/",
    'user_login': "admin"
}
fields_json = SanitationUtils.encodeJSON(fields)
SanitationUtils.safePrint(repr(fields_json))
fields_json_base64 = SanitationUtils.encodeBase64( fields_json )
print fields_json_base64
 # eyJ1c2VyX2xvZ2luIjogImFkbWluIiwgImZpcnN0X25hbWUiOiAibm_wn5GMb2Twn5GMbGUiLCAidXNlcl91cmwiOiAiaHR0cDovL3d3dy5sYXNlcnBoaWxlLmNvbS8ifQ==
test_out = client.call(UpdateUser(1, fields_json_base64))
print test_out