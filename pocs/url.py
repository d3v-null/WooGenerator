from urlparse import urlparse, parse_qs

result = urlparse("http://www.technotan.com.au/wc-api/v3/products?oauth_consumer_key=ck_e7788208a72367740b4d3108f3f77cffea5e8ac0&oauth_timestamp=1473042659&oauth_nonce=5554867b4fff6f4550ff4650bdc1e77f9fc185c4&oauth_signature_method=HMAC-SHA256&oauth_signature=J7pOhgd/WZ47/jCztAK7dPGJ1tJFG20SlWoqODXdXck=&page=61")
print parse_qs(result.query)
