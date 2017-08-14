from bs4 import BeautifulSoup


from wordpress import API
# from woocommerce import API
from pprint import pprint, pformat

def print_response(response):
    """figures out the type of response and attempts to print it """
    try:
        if 'json' in response.headers.get('content-type'):
            print "response json:"
            pprint(response.json())
        else:
            print "response: %s" % BeautifulSoup(response.text, 'lxml').prettify().encode(errors='backslashreplace')
        print "response code: %d" % response.status_code
        print "response headers: %s" % str(response.headers)
        print "request url: %s" % repr(response.request.url)
        print "request body: %s" % repr(response.request.body)
    except Exception as exc:
        print "failed: %s" % repr(exc)
        print "response: %s" % repr(response)

def test_local():
    wcapi = API(
        url='http://localhost:18080/wptest/',
        consumer_key='ck_b13285e31ed659227f2fdc1db856d1d3d0b06c21',
        consumer_secret='cs_3038b86805335faa887c6605364bcd1df9e57254',
        api="wp-json",
        version="wc/v2"
    )
    target_product_id = 22
    # id=22 is variable
    # id=23 is variation of 22

    print "\n\n*******\n* GET *\n*******\n\n"

    response = wcapi.get('products')
    response = wcapi.get('products/%s' % target_product_id)

    # response = wcapi.get('products?page=2')
    # response = wcapi.put('products/99', {'product':{'title':'Woo Single #2a'}} )
    # response = wcapi.put('products/99?id=http%3A%2F%2Fprinter',
    # {'product':{'title':'Woo Single #2a'}} )

    print_response(response)

    print "\n\n*******\n* PUT *\n*******\n\n"

    data = {'product': {'custom_meta': {'attribute_pa_color': 'grey'}}}
    response = wcapi.put('products/%s' % target_product_id, data)
    print_response(response)

def test_technotea():
    wcapi = API(
        url='http://technotea.com.au/',
        consumer_key='ck_204e2f68c5ca4d3be966b7e5da7a48cac1a75104',
        consumer_secret='cs_bcb080a472a2bbded7dc421c63cbe031a91241f5',
        api="wp-json",
        version="wc/v2"
    )

    target_product_id = 24009

    print "\n\n*******\n* GET *\n*******\n\n"

    response = wcapi.get('products/%s?fields=meta' % target_product_id)
    response = wcapi.get('products/categories?filter[q]=solution')
    categories = response.json()
    print "categories: %s" % pformat([(category['id'], category['name']) for
    category in categories])

    # print_response(response)
    print "\n\n*******\n* GET 2 *\n*******\n\n"

    response = wcapi.get('products/%s' % target_product_id)
    product_categories = response.json().get('categories',[])
    print "categories: %s" % pformat(product_categories)
    print "categories: %s" % pformat([(category['id'], category['name']) for
    category in categories])

    print_response(response)

    print "\n\n*******\n* PUT *\n*******\n\n"

    data = {'product':{'custom_meta':{'wootan_danger':'D'}}}
    response = wcapi.put('products/%s' % target_product_id, data)
    print_response(response)

    print "\n\n*******\n* PUT 2 *\n*******\n\n"

    data = {'product':{'categories':[898]}}
    response = wcapi.put('products/%s' % target_product_id, data)

    response = wcapi.get('products/%s?fields=categories' % target_product_id)
    product_categories = response.json().get('product',{}).get('categories',[])
    print "categories: %s" % pformat(product_categories)

def main():
    # test_local()
    test_technotea()

if __name__ == '__main__':
    main()
