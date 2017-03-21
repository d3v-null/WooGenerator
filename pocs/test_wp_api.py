# -*- coding: utf-8 -*-

from utils import SanitationUtils

import json
from wordpress_json import WordpressJsonWrapper

wp = WordpressJsonWrapper(
    'http://www.technotea.com.au/wp-json/wp/v2', 'neil', 'Stretch@6164')
# wp = WordpressJsonWrapper('http://minimac.ddns.me:11182/wp-json/wp/v2', 'neil', 'Stretch6164')

headers = {
    "User-Agent": "curl",
    "Content-Type": "text/json",
    # ...
}

# posts = wp.get_posts(post_id=16886, headers=headers)
# print json.dumps(posts)

# posts = wp.get_user(user_id=9)
# print json.dumps(posts)

fields_json = '{"client_grade": "Silver", "myob_customer_card_id": "", "direct_brand": "Pending", "myob_card_id": "C000009", "act_role": "RN", "billing_company": null, "first_name":"asdasdadadaadggg" }'
fields_json_base64 = SanitationUtils.encodeBase64(fields_json)
# fields_json_base64 = "eyJ1c2VyX2xvZ2luIjogImFkbWluIiwgImZpcnN0X25hbWUiOiAibm/wn5GMb2Twn5GMbGUiLCAidXNlcl91cmwiOiAiaHR0cDovL3d3dy5sYXNlcnBoaWxlLmNvbS9hc2QifQ=="

posts = wp.update_user(
    user_id=9, data={'tansync_updated_fields': fields_json_base64})
print json.dumps(posts)

posts = wp.get_user(user_id=9)
print json.dumps(posts)
