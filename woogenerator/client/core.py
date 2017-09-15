# -*- coding: utf-8 -*-
"""
Boilerplate for unifying interfaces for disparate API clients.
"""

from __future__ import absolute_import

import codecs
import os
import re
import time
from collections import Iterable
from contextlib import closing
from StringIO import StringIO
from urllib import urlencode
from urlparse import urlparse

import httplib2
import oauth2client
import requests
from apiclient import discovery
from oauth2client import client, tools
from simplejson import JSONDecodeError

from wordpress import API
from wordpress.helpers import UrlUtils

from ..utils import ProgressCounter, Registrar, SanitationUtils


class AbstractServiceInterface(object):
    """Defines the interface to an abstract service"""

    def close(self):
        """ Abstract method for closing the service """

    def connect(self, connect_params):
        """ Abstract method for connecting to the service """
        raise NotImplementedError()

    def put(self, *args, **kwargs):
        """ Abstract method for putting data on the service"""
        raise NotImplementedError()

    def get(self, *args, **kwargs):
        """ Abstract method for getting data from the service"""
        raise NotImplementedError()


class WPAPIService(API, AbstractServiceInterface):
    """ A child of the wordpress API that implements the Service interface """

    def connect(self, connect_params):
        """ Overrides AbstractServiceInterface, connect not used """
        pass


class ClientAbstract(Registrar):
    """ Interface with a service as a client. Boilerplate. """
    service_builder = AbstractServiceInterface

    def __init__(self, connect_params, **kwargs):
        self.connect_params = connect_params
        self.service = None
        self.attempt_connect()

    def __enter__(self):
        return self

    def __exit__(self, exit_type, value, traceback):
        if hasattr(self.service, 'close'):
            self.service.close()

    @property
    def connection_ready(self):
        """ determine if connection is ready for use """
        return self.service

    def assert_connect(self):
        """
        attempt to connect if connection not ready

        Raises:
            AssertionError:
                if connection is not ready after connecting
        """

        if not self.connection_ready:
            self.attempt_connect()
        assert self.connection_ready, "connection must be ready"

    def attempt_connect(self):
        """
        Attempt to connect using instances `connect_params` and `service_builder`
        """
        positional_args = self.connect_params.pop('positional', [])
        service_name = 'UNKN'
        if hasattr(self.service_builder, '__name__'):
            service_name = getattr(self.service_builder, '__name__')
        if self.DEBUG_API:
            self.register_message(
                "building service (%s) with positional: %s and keyword: %s" %
                (str(service_name), str(positional_args),
                 str(self.connect_params)))
        self.service = self.service_builder(*positional_args, **
                                            self.connect_params)


class SyncClientAbstract(ClientAbstract):
    """ Interface with a service as a client to perform syncing. """

    def __init__(self, connect_params, **kwargs):
        super(SyncClientAbstract, self).__init__(connect_params, **kwargs)
        self.limit = kwargs.get('limit')

    def analyse_remote(self, parser, *args, **kwargs):
        """
        Abstract method for analysing remote data using parser
        """
        raise NotImplementedError()

    def upload_changes(self, pkey, updates=None):
        """
        Abstract method for updating data with `changes`
        """
        if updates:
            assert pkey, "must have a valid primary key"
            assert self.connection_ready, "connection should be ready"


class SyncClientNull(SyncClientAbstract):
    """ Designed to act like a client but fails on all actions """

    def __init__(self, *args, **kwargs):
        pass

    def attempt_connect(self):
        pass

    def __exit__(self, exit_type, value, traceback):
        pass

    def upload_changes(self, pkey, updates=None):
        raise UserWarning("Using null client class")


class SyncClientLocal(SyncClientAbstract):
    """ Designed to act like a GDrive client but work on a local file instead """

    def __init__(self, **kwargs):
        self.dialect_suggestion = kwargs.pop('dialect_suggestion', None)
        self.encoding = kwargs.pop('encoding', None)
        super(SyncClientLocal, self).__init__(None, **kwargs)

    def attempt_connect(self):
        pass

    def __exit__(self, exit_type, value, traceback):
        pass

    def analyse_remote(self, parser, **kwargs):
        data_path = kwargs.pop('data_path', None)
        analysis_kwargs = {
            'dialect_suggestion': kwargs.get('dialect_suggestion', self.dialect_suggestion),
            'encoding': kwargs.get('encoding', self.encoding),
            'limit': kwargs.get('limit', self.limit)
        }
        if self.DEBUG_PARSER:
            self.register_message(
                "analysis_kwargs: %s" % analysis_kwargs
            )
        return parser.analyse_file(
            data_path,
            **analysis_kwargs
        )
        # out_encoding='utf8'
        # with codecs.open(out_path, mode='rbU', encoding=out_encoding) as out_file:
        # return parser.analyse_stream(out_file, limit=limit,
        # encoding=out_encoding)


class SyncClientLocalStream(SyncClientLocal):
    """ Designed to act like a GDrive client but work on a local stream instead """

    def analyse_remote(self, parser, byte_file_obj, limit=None, **kwargs):
        return parser.analyse_stream(byte_file_obj, limit=limit)


class SyncClientGDrive(SyncClientAbstract):
    """
    Use google drive apiclient to build an api client
    """
    service_builder = discovery.build

    def __init__(self, gdrive_params, **kwargs):
        for key in [
                'credentials_dir', 'credentials_file', 'client_secret_file',
                'scopes', 'app_name'
        ]:
            assert key in gdrive_params, \
                "key %s should be specified in gdrive_params: %s" % (
                    key,
                    repr(gdrive_params)
                )
        self.skip_download = gdrive_params.pop('skip_download', None)
        self.gdrive_params = gdrive_params
        credentials = self.get_credentials()
        auth_http = credentials.authorize(httplib2.Http())

        superconnect_params = {
            'positional': ['drive', 'v2'],
            'http': auth_http
        }
        super(SyncClientGDrive, self).__init__(superconnect_params, **kwargs)
        self.service = discovery.build(
            *superconnect_params.pop('positional', []), **superconnect_params)

        # pylint: disable=E1101
        self.drive_file = self.service.files().get(
            fileId=self.gdrive_params['gen_fid']).execute()

        self.encoding = kwargs.get('encoding', 'utf8')

    def __exit__(self, exit_type, value, traceback):
        pass

    def attempt_connect(self):
        pass

    def assert_connect(self):
        assert self.connection_ready, "connection must be ready"

    def get_credentials(self):
        """
        Finds credentials in file specified in instances `gdrive_params`
        """
        credential_dir = os.path.expanduser(
            self.gdrive_params['credentials_dir'])
        if not os.path.exists(credential_dir):
            os.makedirs(credential_dir)
        credential_path = os.path.join(credential_dir,
                                       self.gdrive_params['credentials_file'])
        store = oauth2client.file.Storage(credential_path)
        credentials = store.get()
        if not credentials or credentials.invalid:
            flow = client.flow_from_clientsecrets(
                self.gdrive_params['client_secret_file'],
                self.gdrive_params['scopes'])
            flow.user_agent = self.gdrive_params['app_name']
            credentials = tools.run(flow, store)  # pylint: disable=E1101
            self.register_message('Storing credentials to ' + credential_path)
        return credentials

    def download_file_content_csv(self, gid=None):
        """Download current file's content as csv.

        Args:
          gid: GID of file to download

        Returns:
          File's content if successful, None otherwise.
        """
        # print( type(drive_file) )
        # print( drive_file)
        download_url = self.drive_file['exportLinks']['text/csv']
        if gid:
            download_url += "&gid=" + str(gid)
        if download_url:
            resp, content = self.service._http.request(download_url)
            if resp.status == 200:
                self.register_message('Status: %s' % resp)
                if content:
                    return SanitationUtils.coerce_unicode(content)
            else:
                self.register_error('An error occurred: %s' % resp)

    def get_gm_modtime(self, gid=None):
        """ Get modtime of a drive file (individual gid not supported yet) """
        # TODO: individual gid mod times
        return time.strptime(self.drive_file['modifiedDate'],
                             '%Y-%m-%dT%H:%M:%S.%fZ')

    def analyse_remote(self, parser, data_path=None, **kwargs):
        gid = kwargs.pop('gid', None)

        analysis_kwargs = {
            'encoding': kwargs.get('encoding', self.encoding),
            'limit': kwargs.get('limit', self.limit)
        }

        if not self.skip_download:
            if Registrar.DEBUG_GDRIVE:
                message = "Downloading spreadsheet"
                if gid:
                    message += " with gid %s" % gid
                if data_path:
                    message += " to: %s" % data_path
                Registrar.register_message(message)

            content = self.download_file_content_csv(gid)
            if not content:
                return
            if data_path:
                with codecs.open(
                    data_path,
                    encoding=analysis_kwargs['encoding'],
                    mode='w'
                ) as out_file:
                    out_file.write(content)
                parser.analyse_file(
                    data_path, **analysis_kwargs)
            else:
                with closing(StringIO(content)) as content_stream:
                    parser.analyse_stream(
                        content_stream,
                        limit=analysis_kwargs['limit']
                    )

            if Registrar.DEBUG_GDRIVE:
                message = "downloaded contents of spreadsheet"
                if gid:
                    message += ' with gid %s' % gid
                if out_file:
                    message += ' to file %s' % data_path


class SyncClientRest(SyncClientAbstract):
    """
    Client for the REST API
    """

    service_builder = WPAPIService
    version = None
    endpoint_singular = ''
    mandatory_params = ['api_key', 'api_secret', 'url']
    default_version = 'wp/v2'
    default_namespace = 'wp-json'
    page_nesting = True
    search_param = None

    class ApiIterator(Iterable):
        """
        An iterator for traversing items in the API
        """

        def __init__(self, service, endpoint):
            assert isinstance(service, WPAPIService)
            self.service = service
            self.next_endpoint = endpoint
            self.prev_response = None
            self.total_pages = None
            self.total_items = None
            # self.progress_counter = None

            endpoint_queries = UrlUtils.get_query_dict_singular(endpoint)
            # print "endpoint_queries:", endpoint_queries
            self.next_page = None
            if 'page' in endpoint_queries:
                self.next_page = int(endpoint_queries['page'])
            self.limit = 10
            if 'fliter[limit]' in endpoint_queries:
                self.limit = int(endpoint_queries['filter[limit]'])
            # print "slave limit set to to ", self.limit
            self.offset = None
            if 'filter[offset]' in endpoint_queries:
                self.offset = int(endpoint_queries['filter[offset]'])
            # print "slave offset set to to ", self.offset

            # def get_url_param(self, url, param, default=None):
            #     url_params = parse_qs(urlparse(url).query)
            #     return url_params.get(param, [default])[0]

        def process_headers(self, response):
            """
            Process the headers in a response to get info about pagination
            """
            headers = response.headers
            if Registrar.DEBUG_API:
                Registrar.register_message("headers: %s" % str(headers))

            if self.service.namespace == 'wp-json':
                total_pages_key = 'X-WP-TotalPages'
                total_items_key = 'X-WP-Total'
            else:
                total_pages_key = 'X-WC-TotalPages'
                total_items_key = 'X-WC-Total'

            if total_items_key in headers:
                self.total_pages = int(headers.get(total_pages_key, ''))
            if total_pages_key in headers:
                self.total_items = int(headers.get(total_items_key, ''))
            prev_endpoint = self.next_endpoint
            self.next_endpoint = None

            for rel, link in response.links.items():
                if rel == 'next' and link.get('url'):
                    next_response_url = link['url']
                    self.next_page = int(
                        UrlUtils.get_query_singular(next_response_url, 'page'))
                    if not self.next_page:
                        return
                    assert \
                        self.next_page <= self.total_pages, \
                        "next page (%s) should be lte total pages (%s)" \
                        % (str(self.next_page), str(self.total_pages))
                    self.next_endpoint = UrlUtils.set_query_singular(
                        prev_endpoint, 'page', self.next_page)

                    # if Registrar.DEBUG_API:
                    #     Registrar.register_message('next_endpoint: %s' % str(self.next_endpoint))

            if self.next_page:
                self.offset = (self.limit * self.next_page) + 1

        def __iter__(self):
            return self

        def next(self):
            """ Used by Iterable to get next item in the API """
            if Registrar.DEBUG_API:
                Registrar.register_message('start')

            if self.next_endpoint is None:
                if Registrar.DEBUG_API:
                    Registrar.register_message(
                        'stopping due to no next endpoint')
                raise StopIteration()

            # get API response
            try:
                self.prev_response = self.service.get(self.next_endpoint)
            except requests.ReadTimeout as exc:
                # instead of processing this endoint, do the page product by
                # product
                if self.limit > 1:
                    new_limit = 1
                    if Registrar.DEBUG_API:
                        Registrar.register_message('reducing limit in %s' %
                                                   self.next_endpoint)

                    self.next_endpoint = UrlUtils.set_query_singular(
                        self.next_endpoint, 'filter[limit]', new_limit)
                    self.next_endpoint = UrlUtils.del_query_singular(
                        self.next_endpoint, 'page')
                    if self.offset:
                        self.next_endpoint = UrlUtils.set_query_singular(
                            self.next_endpoint, 'filter[offset]', self.offset)

                    self.limit = new_limit

                    # endpoint_queries = parse_qs(urlparse(self.next_endpoint).query)
                    # endpoint_queries = dict([
                    #     (key, value[0]) for key, value in endpoint_queries.items()
                    # ])
                    # endpoint_queries['filter[limit]'] = 1
                    # if self.next_page:
                    #     endpoint_queries['page'] = 10 * self.next_page
                    # print "endpoint_queries: ", endpoint_queries
                    # self.next_endpoint = UrlUtils.substitute_query(
                    #     self.next_endpoint,
                    #     urlencode(endpoint_queries)
                    # )
                    if Registrar.DEBUG_API:
                        Registrar.register_message('new endpoint %s' %
                                                   self.next_endpoint)

                    self.prev_response = self.service.get(self.next_endpoint)

            # handle API errors
            if self.prev_response.status_code in range(400, 500):
                raise requests.ConnectionError('api call failed: %dd with %s' % (
                    self.prev_response.status_code, self.prev_response.text))

            # can still 200 and fail
            try:
                prev_response_json = self.prev_response.json()
            except JSONDecodeError:
                prev_response_json = {}
                exc = requests.ConnectionError(
                    'api call to %s failed: %s' %
                    (self.next_endpoint, self.prev_response.text))
                Registrar.register_error(exc)

            # if Registrar.DEBUG_API:
            #     Registrar.register_message('first api response: %s' % str(prev_response_json))
            if 'errors' in prev_response_json:
                raise requests.ConnectionError('first api call returned errors: %s' %
                                               (prev_response_json['errors']))

            # process API headers
            self.process_headers(self.prev_response)

            return prev_response_json

    @property
    def endpoint_plural(self):
        return "%ss" % self.endpoint_singular

    def __init__(self, connect_params, **kwargs):

        self.limit = connect_params.get('limit')
        self.offset = connect_params.get('offset')
        self.since = kwargs.get('since')

        key_translation = {
            'api_key': 'consumer_key',
            'api_secret': 'consumer_secret'
        }
        for param in self.mandatory_params:
            assert param in connect_params and connect_params[param], \
                "missing mandatory param (%s) from connect parameters: %s" \
                % (param, str(connect_params))

        #
        superconnect_params = {}

        # superconnect_params.update(
        #     timeout=60
        # )

        for key, value in connect_params.items():
            super_key = key
            if key in key_translation:
                super_key = key_translation[key]
            superconnect_params[super_key] = value

        if 'api' not in superconnect_params:
            superconnect_params['api'] = self.default_namespace
        if 'version' not in superconnect_params:
            superconnect_params['version'] = self.default_version
        if superconnect_params['api'] == 'wp-json':
            superconnect_params['oauth1a_3leg'] = True

        super(SyncClientRest, self).__init__(superconnect_params, **kwargs)
        #
        # self.service = WCAPI(
        #     url=connect_params['url'],
        #     consumer_key=connect_params['api_key'],
        #     consumer_secret=connect_params['api_secret'],
        #     timeout=60,
        #     # wp_api=True, # Enable the WP REST API integration
        #     # version="v3", # WooCommerce WP REST API version
        #     # version="wc/v1"
        # )

    #

    # since=None, limit=None, search=None):
    def analyse_remote(self, parser, **kwargs):
        limit = kwargs.get('limit', self.limit)
        since = kwargs.get('since', self.since)
        search = kwargs.get('search')
        if since:
            pass
            # TODO: implement kwargs['since']

        result_count = 0

        # api_iterator = self.ApiIterator(self.service, self.endpoint_plural)
        endpoint_plural = self.endpoint_plural
        if self.search_param and search:
            endpoint_parsed = urlparse(endpoint_plural)
            endpoint_path, endpoint_query = endpoint_parsed.path, endpoint_parsed.query
            additional_query = '%s=%s' % (self.search_param, search)
            if endpoint_query:
                endpoint_query += '&%s' % additional_query
            else:
                endpoint_query = additional_query
            endpoint_plural = "%s?%s" % (endpoint_path, endpoint_query)
            # print "search_param and search exist, new endpoint: %s" % endpoint_plural
            # quit()
        else:
            # print "search_param and search DNE, %s %s" % (self.search_param, search)
            # quit()
            pass

        api_iterator = self.get_iterator(endpoint_plural)
        progress_counter = None
        for page in api_iterator:
            if progress_counter is None:
                total_items = 0
                if api_iterator.total_items is not None:
                    total_items = api_iterator.total_items
                if limit is not None:
                    total_items = min(limit, total_items)
                progress_counter = ProgressCounter(total_items)
            progress_counter.maybe_print_update(result_count)

            # if Registrar.DEBUG_API:
            #     Registrar.register_message('processing page: %s' % str(page))
            page_items = []
            if self.page_nesting and self.endpoint_plural in page:
                page_items = page.get(self.endpoint_plural)
            else:
                page_items = page

            for page_item in page_items:

                parser.analyse_wp_api_obj(page_item)
                result_count += 1
                if limit and result_count > limit:
                    if Registrar.DEBUG_API:
                        Registrar.register_message('reached limit, exiting')
                    return

    def upload_changes(self, pkey, data=None):
        try:
            pkey = int(pkey)
        except ValueError:
            exc = UserWarning("Can't convert pkey %s to int" % pkey)
            Registrar.register_error(exc)
            raise exc
        super(SyncClientRest, self).upload_changes(pkey)
        endpoint_parsed = urlparse(self.endpoint_plural)
        service_endpoint = '%s/%d' % (endpoint_parsed.path, pkey)
        if endpoint_parsed.query:
            service_endpoint += '?%s' % endpoint_parsed.query
        data = dict([(key, value) for key, value in data.items()])
        # print "service version: %s, data:%s" % (self.service.version, data)
        if re.match('wc/v[2-9]', self.service.version):
            data = {self.endpoint_singular: data}
        if Registrar.DEBUG_API:
            Registrar.register_message("updating %s: %s" %
                                       (service_endpoint, data))
        response = self.service.put(service_endpoint, data)
        assert response.status_code not in [400, 401], "API ERROR"
        try:
            assert response.json()
        except BaseException:
            raise UserWarning("json should exist, instead response was %s" %
                              response.text)
        assert not isinstance(
            response.json(),
            int), "could not convert response to json: %s %s" % (
                str(response), str(response.json()))
        assert 'errors' not in response.json(
        ), "response has errors: %s" % str(response.json()['errors'])
        return response

    def get_iterator(self, endpoint=None):
        """
        Gets an iterator to the items in the API
        """
        if not endpoint:
            endpoint = self.endpoint_plural
        endpoint_queries = {}
        if self.limit is not None:
            endpoint_queries['filter[limit]'] = self.limit
        if self.offset is not None:
            endpoint_queries['filter[offset]'] = self.offset
        if endpoint_queries:
            endpoint += "?" + urlencode(endpoint_queries)
        return self.ApiIterator(self.service, endpoint)

    def create_item(self, data):
        """
        Creates an item in the API
        """
        data = dict([(key, value) for key, value in data.items()])
        assert 'name' in data, "name is required to create a category, instead provided with %s" \
            % (str(data))
        if str(data.get('parent')) == str(-1):
            del data['parent']
        service_endpoint = self.endpoint_plural
        endpoint_singular = self.endpoint_singular
        endpoint_singular = re.sub('/', '_', endpoint_singular)
        if not self.service.version.starts_with('wc/v'):
            data = {endpoint_singular: data}
        if Registrar.DEBUG_API:
            Registrar.register_message("creating %s: %s" %
                                       (service_endpoint, data))
        response = self.service.post(service_endpoint, data)
        assert response.status_code not in [400, 401], "API ERROR"
        assert response.json(), "json should exist"
        assert not isinstance(
            response.json(),
            int), "could not convert response to json: %s %s" % (
                str(response), str(response.json()))
        assert 'errors' not in response.json(
        ), "response has errors: %s" % str(response.json()['errors'])
        return response

    # def __exit__(self, exit_type, value, traceback):
    #     pass


class SyncClientWC(SyncClientRest):
    """
    Client for the WC Rest API
    """
    default_version = 'v3'
    default_namespace = 'wc-api'


class SyncClientWP(SyncClientRest):
    """
    Client for the WP REST API
    """
    mandatory_params = [
        'api_key', 'api_secret', 'url', 'wp_user', 'wp_pass', 'callback'
    ]
    page_nesting = False
    search_param = 'search'
