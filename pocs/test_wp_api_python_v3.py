from bs4 import BeautifulSoup


from wordpress import API
# from woocommerce import API
from pprint import pprint, pformat

def print_response(response):
    """figures out the type of response and attempts to print it """
    try:
        if 'json' in response.headers.get('content-type'):
            print "response json:"
            pprint( response.json())
        else:
            print "response: %s" % BeautifulSoup(response.text, 'lxml').prettify().encode(errors='backslashreplace')
        print "response code: %d" % response.status_code
        print "response headers: %s" % str(response.headers)
        print "request url: %s" % repr(response.request.url)
        print "request body: %s" % repr(response.request.body)
    except Exception, e:
        print "failed: %s" % repr(e)
        print "response: %s" % repr(response)

# wcapi = API(
#     url='http://localhost:8888/wordpress/',
#     consumer_key='ck_681c2be361e415519dce4b65ee981682cda78bc6',
#     consumer_secret='cs_b11f652c39a0afd3752fc7bb0c56d60d58da5877',
#     api="wc-api",
#     version="v3"
# )
wcapi = API(
    url='http://technotea.com.au/',
    consumer_key='ck_204e2f68c5ca4d3be966b7e5da7a48cac1a75104',
    consumer_secret='cs_bcb080a472a2bbded7dc421c63cbe031a91241f5',
    api="wc-api",
    version="v3"
)

print "\n\n*******\n* GET *\n*******\n\n"
# response = wcapi.get('products')
# response = wcapi.get('products?page=2')
# response = wcapi.put('products/99', {'product':{'title':'Woo Single #2a'}} )
# response = wcapi.put('products/99?id=http%3A%2F%2Fprinter', {'product':{'title':'Woo Single #2a'}} )

response = wcapi.get('products/categories?filter[q]=solution')
categories = response.json().get('product_categories')
print "categories: %s" % pformat([(category['id'], category['name']) for category in categories])

# print_response(response)
# quit()

response = wcapi.get('products/17834')
product_categories = response.json().get('product',{}).get('categories',[])
print "categories: %s" % pformat(product_categories)
# print "categories: %s" % pformat([(category['id'], category['name']) for category in categories])

print "\n\n*******\n* PUT *\n*******\n\n"

data = {'product':{'categories':[898]}}
response = wcapi.put('products/17834', data)

response = wcapi.get('products/17834?fields=categories')
product_categories = response.json().get('product',{}).get('categories',[])
print "categories: %s" % pformat(product_categories)

#
# quit()

#
# wpapi = API(
#     url='http://localhost:8888/wordpress/',
#     consumer_key='LCLwTOfxoXGh',
#     consumer_secret='k7zLzO3mF75Xj65uThpAnNvQHpghp4X1h5N20O8hCbz2kfJq',
#     api="wp-json",
#     oauth1a_3leg=True,
#     version="wp/v2",
#     wp_user='wordpress',
#     wp_pass='wordpress',
#     callback='http://127.0.0.1:8888/wordpress'
# )

# request_token, request_token_secret = wpapi.oauth.get_request_token()

# print "request_token: %s, request_token_secret: %s" % (request_token, request_token_secret)

# response = wpapi.oauth.get_verifier()

# response = wpapi.oauth.get_access_token()

# response = wpapi.get('/posts')
# response = wpapi.get('/posts?page=1')

# response = wpapi.post('/posts/1', data={'title':"Hello world!!"})



# print wpapi.oauth.authentication
# access_token, access_token_secret = wpapi.oauth.get_request_token()
# print access_token
# print access_token_secret
