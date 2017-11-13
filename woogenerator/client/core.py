# -*- coding: utf-8 -*-
"""
Boilerplate for unifying interfaces for disparate API clients.
"""

from __future__ import absolute_import

import codecs
import functools
import os
import re
import time
from collections import Iterable, OrderedDict
from contextlib import closing
from copy import copy
from pprint import pformat
from StringIO import StringIO
from urllib import urlencode
from urlparse import urlparse

import cjson
import httplib2
import oauth2client
import paramiko
import pymysql
import requests
from apiclient import discovery
from oauth2client import client, tools
from requests.exceptions import ReadTimeout
from simplejson import JSONDecodeError
from sshtunnel import SSHTunnelForwarder

from wordpress import API
from wordpress.helpers import UrlUtils

from ..coldata import ColDataWpPost
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
    service_name = 'UNKN'

    def __init__(self, connect_params, **kwargs):
        """
         - Connect params passed in to service builder,
         - kwargs used to modify sync client
        """
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
        service_name = self.service_name
        if hasattr(self.service_builder, '__name__'):
            service_name = getattr(self.service_builder, '__name__')
        if self.DEBUG_API:
            self.register_message(
                "building service (%s) with args:\n%s\nand kwargs:\n%s" %
                (str(service_name), pformat(positional_args),
                 pformat(self.connect_params)))
        self.service = self.service_builder(
            *positional_args,
            **self.connect_params
        )

class SyncClientAbstract(ClientAbstract):
    """ Interface with a service as a client to perform syncing. """

    service_name = 'ABSTRACT'

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

    service_name = 'NULL'

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

    service_name = 'LOCAL'

    def __init__(self, **kwargs):
        self.dialect_suggestion = kwargs.pop('dialect_suggestion', None)
        self.encoding = kwargs.pop('encoding', None)
        commect_params = kwargs.pop('connect_params', {})
        connect_params = None
        super(SyncClientLocal, self).__init__(connect_params, **kwargs)

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

    def analyse_remote_categories(self, parser, **kwargs):
        data_path = kwargs.pop('data_path', None)
        # encoding = kwargs.pop('encoding', None)

        with open(data_path, 'rbU') as data_file:
            decoded = SanitationUtils.decode_json(data_file.read())
            if not decoded:
                warn = UserWarning("could not analyse_remote_categories, json not decoded")
                self.register_warning(warn)

            if isinstance(decoded, list):
                parser.process_api_categories(decoded)

    def analyse_remote_imgs(self, parser, **kwargs):
        data_path = kwargs.pop('data_path', None)
        # encoding = kwargs.pop('encoding', None)

        with open(data_path, 'rbU') as data_file:
            decoded = SanitationUtils.decode_json(data_file.read())
            if not decoded:
                warn = UserWarning("could not analyse_remote_imgs, json not decoded")
                self.register_warning(warn)

            if isinstance(decoded, list):
                for decoded_item in decoded:
                    parser.process_api_image(decoded_item)


class SyncClientLocalStream(SyncClientLocal):
    """ Designed to act like a GDrive client but work on a local stream instead """

    def analyse_remote(self, parser, byte_file_obj, limit=None, **kwargs):
        return parser.analyse_stream(byte_file_obj, limit=limit)


class SyncClientGDrive(SyncClientAbstract):
    """
    Use google drive apiclient to build an api client
    """
    service_builder = discovery.build
    service_name = 'GDRIVE'

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

# TODO: probably move REST stuff to rest.py

class SyncClientRest(SyncClientAbstract):
    """ Abstract REST API Client. """

    service_builder = WPAPIService
    service_name = 'REST'
    version = None
    endpoint_singular = ''
    mandatory_params = ['consumer_key', 'consumer_secret', 'url']
    default_version = 'wp/v2'
    default_namespace = 'wp-json'
    meta_get_key = 'meta'
    meta_set_key = 'custom_meta'
    pagination_limit_key = 'filter[limit]'
    pagination_number_key = 'page'
    pagination_offset_key = 'filter[offset]'
    total_pages_key = 'X-WP-TotalPages'
    total_items_key = 'X-WP-Total'
    page_nesting = True
    search_param = None
    meta_listed = False
    readonly_keys = {
        'core': ['id']
    }
    key_translation = {
        # 'api_key': 'consumer_key',
        # 'api_secret': 'consumer_secret'
    }

    class ApiIterator(Iterable):
        """ An iterator for traversing items in the API. """

        def __init__(self, service, endpoint, **kwargs):
            assert isinstance(service, WPAPIService)
            self.service = service
            self.next_endpoint = endpoint
            self.prev_response = None
            self.total_pages = None
            self.total_items = None
            self.pagination_limit_key = kwargs.get('pagination_limit_key')
            self.pagination_number_key = kwargs.get('pagination_number_key')
            self.pagination_offset_key = kwargs.get('pagination_offset_key')
            self.total_pages_key = kwargs.get('total_pages_key')
            self.total_items_key = kwargs.get('total_items_key')

            endpoint_queries = UrlUtils.get_query_dict_singular(endpoint)

            self.next_page = None
            if self.pagination_number_key in endpoint_queries:
                self.next_page = int(endpoint_queries[self.pagination_number_key])
            self.limit = 10
            if self.pagination_limit_key in endpoint_queries:
                self.limit = int(endpoint_queries[self.pagination_limit_key])
            self.offset = None
            if self.pagination_offset_key in endpoint_queries:
                self.offset = int(endpoint_queries[self.pagination_offset_key])

        def process_headers(self, response):
            """
            Process the headers in a response to get info about pagination
            """
            headers = response.headers
            if Registrar.DEBUG_API:
                Registrar.register_message("headers: %s" % str(headers))

            if self.total_pages_key in headers:
                self.total_pages = int(headers.get(self.total_pages_key, ''))
            if self.total_items_key in headers:
                self.total_items = int(headers.get(self.total_items_key, ''))
            prev_endpoint = self.next_endpoint
            self.next_endpoint = None

            for rel, link in response.links.items():
                if rel == 'next' and link.get('url'):
                    next_response_url = link['url']
                    self.next_page = int(
                        UrlUtils.get_query_singular(
                            next_response_url,
                            self.pagination_number_key
                        )
                    )
                    if not self.next_page:
                        return
                    assert \
                        self.next_page <= self.total_pages, \
                        "next page (%s) should be lte total pages (%s)" \
                        % (str(self.next_page), str(self.total_pages))
                    self.next_endpoint = UrlUtils.set_query_singular(
                        prev_endpoint,
                        self.pagination_number_key,
                        self.next_page
                    )

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
            except ReadTimeout as exc:
                # instead of processing this endoint, do the page product by
                # product
                if self.limit > 1:
                    new_limit = 1
                    if Registrar.DEBUG_API:
                        Registrar.register_message('reducing limit in %s' %
                                                   self.next_endpoint)

                    self.next_endpoint = UrlUtils.set_query_singular(
                        self.next_endpoint,
                        self.pagination_limit_key,
                        new_limit
                    )
                    self.next_endpoint = UrlUtils.del_query_singular(
                        self.next_endpoint,
                        self.pagination_number_key
                    )
                    if self.offset:
                        self.next_endpoint = UrlUtils.set_query_singular(
                            self.next_endpoint,
                            self.pagination_offset_key,
                            self.offset
                        )

                    self.limit = new_limit

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

        for param in self.mandatory_params:
            assert param in connect_params and connect_params[param], \
                "missing mandatory param (%s) from connect parameters: %s" \
                % (param, str(connect_params))

        #
        superconnect_params = {}

        for key, value in connect_params.items():
            super_key = key
            if key in self.key_translation:
                super_key = self.key_translation[key]
            superconnect_params[super_key] = value

        if 'api' not in superconnect_params:
            superconnect_params['api'] = self.default_namespace
        if 'version' not in superconnect_params:
            superconnect_params['version'] = self.default_version
        # if superconnect_params['api'] == 'wp-json':
        #     superconnect_params['oauth1a_3leg'] = True

        super(SyncClientRest, self).__init__(superconnect_params, **kwargs)

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

                parser.analyse_api_obj(page_item)
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
        if self.page_nesting:
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
            response.json(), int
        ), "could not convert response to json: %s %s" % (
            str(response), str(response.json())
        )
        assert 'errors' not in response.json(
        ), "response has errors: %s" % str(response.json()['errors'])
        return response

    def get_iterator(self, endpoint=None):
        """
        Gets an iterator to the items in the API
        """
        if not endpoint:
            endpoint = self.endpoint_plural

        endpoint_queries = UrlUtils.get_query_dict_singular(endpoint)
        if self.pagination_limit_key not in endpoint_queries \
        and self.limit is not None:
            endpoint_queries[self.pagination_limit_key] = self.limit

        if self.pagination_offset_key not in endpoint_queries \
        and self.offset is not None:
            endpoint_queries[self.pagination_offset_key] = self.offset
        if endpoint_queries:
            endpoint = UrlUtils.substitute_query(endpoint, urlencode(endpoint_queries))
        return self.ApiIterator(
            self.service,
            endpoint,
            pagination_limit_key=self.pagination_limit_key,
            pagination_number_key=self.pagination_number_key,
            pagination_offset_key=self.pagination_offset_key,
            total_pages_key=self.total_pages_key,
            total_items_key=self.total_items_key,
        )

    def create_item(self, data, **kwargs):
        """
        Creates an item in the API
        """
        if hasattr(data, 'items'):
            data = dict([(key, value) for key, value in data.items()])
        if isinstance(data, dict):
            if str(data.get('parent')) == str(-1):
                del data['parent']
        service_endpoint = self.endpoint_plural
        endpoint_singular = self.endpoint_singular
        endpoint_singular = re.sub('/', '_', endpoint_singular)
        if self.page_nesting:
            data = {endpoint_singular: data}
        if Registrar.DEBUG_API:
            Registrar.register_message("creating %s: %s" % (
                service_endpoint,
                pformat(data)[:1000]
            ))
        response = self.service.post(service_endpoint, data, **kwargs)
        assert response.status_code not in [400, 401], "API ERROR"
        assert response.json(), "json should exist"
        assert not isinstance(
            response.json(),
            int), "could not convert response to json: %s %s" % (
                str(response), str(response.json()))
        assert 'errors' not in response.json(
        ), "response has errors: %s" % str(response.json()['errors'])
        return response

    def delete_item(self, pkey, **kwargs):
        service_endpoint = "%s/%s" % (self.endpoint_plural, pkey)
        force = kwargs.pop('force', False)
        if force:
            service_endpoint += "?force=true"
        if Registrar.DEBUG_API:
            Registrar.register_message("deleting %s" % service_endpoint)
        response = self.service.delete(service_endpoint)
        assert response.status_code not in [400, 401], "API ERROR"
        return response

    def get_first_endpoint_item(self):
        service_endpoint = self.endpoint_plural
        if self.pagination_limit_key:
            service_endpoint += '?%s=1' % self.pagination_limit_key
        items_page = self.get_iterator(service_endpoint).next()
        if self.page_nesting:
            items_page = items_page[self.endpoint_plural]
        return items_page[0]

    @classmethod
    def apply_to_data_item(cls, data, function, wrap_response=None):
        if cls.page_nesting:
            if data:
                endpoint_singular, item = data.items()[0]
            else:
                endpoint_singular = cls.endpoint_singular
                item = {}
            item = function(item)
            if wrap_response:
                return {endpoint_singular: item}
            return item
        else:
            return function(data)

    @classmethod
    def get_item_core(cls, item, key):
        return item.get(key)

    @classmethod
    def get_data_core(cls, data, key):
        return cls.apply_to_data_item(
            data,
            functools.partial(
                cls.get_item_core,
                key=key
            )
        )

    @classmethod
    def get_item_meta(cls, item, key):
        if cls.meta_listed:
            for meta in item[cls.meta_get_key]:
                if meta['key'] == key:
                    return meta['value']
        else:
            return item[cls.meta_get_key].get(key)

    @classmethod
    def get_data_meta(cls, data, key):
        return cls.apply_to_data_item(
            data,
            functools.partial(
                cls.get_item_meta,
                key=key
            )
        )

    @classmethod
    def set_item_core(cls, item, key, value):
        item[key] = value
        return item

    @classmethod
    def set_data_core(cls, data, key, value):
        return cls.apply_to_data_item(
            data,
            functools.partial(
                cls.set_item_core,
                key=key,
                value=value
            ),
            wrap_response=True
        )

    @classmethod
    def set_item_meta(cls, item, meta):
        if cls.meta_listed:
            if not cls.meta_set_key in item:
                item[cls.meta_set_key] = []
            for key, value in meta.items():
                item[cls.meta_set_key].append(
                    {'key':key, 'value':str(value)}
                )
        else:
            if not cls.meta_set_key in item:
                item[cls.meta_set_key] = {}
            for key, value in meta.items():
                item[cls.meta_set_key].update(**{key:value})
        return item

    @classmethod
    def set_data_meta(cls, data, meta):
        return cls.apply_to_data_item(
            data,
            functools.partial(
                cls.set_item_meta,
                meta=meta
            ),
            wrap_response=True
        )

    @classmethod
    def delete_item_meta(cls, item, meta_key):
        return cls.set_item_meta(item, {meta_key:''})

    @classmethod
    def delete_data_meta(cls, data, meta_key):
        return cls.apply_to_data_item(
            data,
            functools.partial(
                cls.set_item_meta,
                meta_key=meta_key
            ),
            wrap_response=True
        )

    @classmethod
    def strip_item_readonly(cls, item):
        readonly_keys = copy(cls.readonly_keys)
        if not readonly_keys:
            return item
        for key in readonly_keys.pop('core', []):
            if key in item:
                del(item[key])
        for key, sub_keys in readonly_keys.items():
            if isinstance(item[key], list):
                new_list = []
                for list_item in item[key]:
                    for sub_key in sub_keys:
                        if sub_key in list_item:
                            del(list_item[sub_key])
                    new_list.append(list_item)
            else:
                for sub_key in sub_keys:
                    if sub_key in item[key]:
                        del(item[key][sub_key])
        return item

    @classmethod
    def strip_data_readonly(cls, data):
        return cls.apply_to_data_item(
            data,
            functools.partial(cls.set_item_meta),
            wrap_response=True
        )

class SyncClientWC(SyncClientRest):
    """
    Client for the WC wp-json Rest API
    https://woocommerce.github.io/woocommerce-rest-api-docs
    """
    default_version = 'wc/v2'
    default_namespace = 'wp-json'
    page_nesting = False
    meta_get_key = 'meta_data'
    meta_set_key = 'meta_data'
    pagination_limit_key = 'per_page'
    pagination_offest_key = 'offset'
    pagination_number_key = 'page'
    search_param = 'name'
    meta_listed = True
    total_pages_key = 'x-wp-totalpages'
    total_items_key = 'x-wp-total'
    readonly_keys = {
        'core': [
            'id', 'permalink', 'date_created', 'date_created_gmt',
             'date_modified', 'date_modified_gmt', 'price', 'price_html',
             'on_sale', 'purchasable', 'total_sales', 'backorders_allowed',
             'backordered', 'shipping_required', 'shipping_taxable',
             'shipping_class_id', 'average_rating', 'rating_count', 'related_ids',
             'variations'
        ],
        'downloads': ['id'],
        'categories': ['name', 'slug'],
        'tags': ['name', 'slug'],
        'images': [
            'date_created', 'date_created_gmt', 'date_modified',
            'date_modified_gmt'
        ],
        meta_set_key: [
            'id'
        ]
    }

class SyncClientWCLegacy(SyncClientRest):
    """
    Client for the Legacy WC Rest API (deprecated since WC3.0)
    https://woocommerce.github.io/woocommerce-rest-api-docs/v3.html
    """
    pagination_limit_key = 'filter[limit]'
    pagination_number_key = 'page'
    pagination_offset_key = 'filter[offset]'
    meta_get_key = 'meta'
    meta_set_key = 'custom_meta'
    default_version = 'v3'
    default_namespace = 'wc-api'
    page_nesting = True
    pagination_limit_key = 'filter[limit]'
    pagination_number_key = 'page'
    pagination_offset_key = 'filter[offset]'
    search_param = 'filter[q]'
    meta_listed = False
    readonly_keys = {
        'core': [
            'id', 'permalink', 'created_at', 'updated_at', 'price', 'price_html',
            'total_sales', 'backorders_allowed', 'taxable', 'backorders_allowed',
            'backordered', 'purchasable', 'visible', 'on_sale',
            'shipping_required', 'shipping_taxable', 'shipping_class_id',
            'average_rating', 'rating_count', 'related_ids', 'featured_src',
            'total_sales', 'parent'
        ],
        'dimensions': ['unit'],
        'images': [
            'created_at', 'updated_at'
        ],
        'downloads': ['id'],
        'categories': ['name', 'slug'],
        'tags': ['name', 'slug'],
        'meta': [
            'id'
        ],
        'variations': [
            'id', 'created_at', 'updated_at', 'permalink', 'price', 'taxable',
            'back-ordered', 'purchasable', 'visible', 'on_sale', 'shipping_class_id'
        ]
    }
    total_pages_key = 'X-WC-TotalPages'
    total_items_key = 'X-WC-Total'




class SyncClientWP(SyncClientRest):
    """
    Client for the WP REST API
    """
    mandatory_params = [
        'consumer_key', 'consumer_secret', 'url', 'wp_user', 'wp_pass', 'callback'
    ]
    page_nesting = False
    search_param = 'search'

class LocalNullTunnel(object):
    """ Pretend to be a SSHTunnelForwarder object for local mocking. """
    def __init__(self, **kwargs):
        self.local_bind_address = (
            kwargs.get('remote_bind_host'), kwargs.get('remote_bind_port')
        )

    def start(self):
        pass

    def close(self):
        pass

class SyncClientSqlWP(SyncClientAbstract):
    service_builder = SSHTunnelForwarder
    coldata_class = ColDataWpPost

    """docstring for UsrSyncClientSqlWP"""

    def __init__(self, connect_params, db_params, **kwargs):
        self.db_params = db_params
        self.tbl_prefix = self.db_params.pop('tbl_prefix', '')
        self.since = kwargs.get('since')
        super(SyncClientSqlWP, self).__init__(connect_params, **kwargs)
        # self.fs_params = fs_params

    def __enter__(self):
        self.service.start()
        return self

    def __exit__(self, exit_type, value, traceback):
        self.service.close()

    def attempt_connect(self):
        if self.connect_params.get('ssh_host'):
            self.service = SSHTunnelForwarder(**self.connect_params)
        else:
            self.service = LocalNullTunnel(**self.connect_params)

    def get_rows(self, _, **kwargs):
        limit = kwargs.get('limit', self.limit)
        filter_pkey = kwargs.get('filter_pkey')

        core_pkey = 'ID'

        self.assert_connect()

        # srv_offset = self.db_params.pop('srv_offset','')
        self.db_params['port'] = self.service.local_bind_address[-1]
        cursor = pymysql.connect(**self.db_params).cursor()

        wp_db_col_paths = self.coldata_class.get_path_translation('wp-sql')

        wp_db_core_cols = OrderedDict()
        wp_db_meta_cols = OrderedDict()

        for handle, db_path in wp_db_col_paths.items():
            if not db_path:
                continue
            path_tokens = db_path.split('.')

            if path_tokens[0] == 'meta':
                if path_tokens[1] != '*':
                    wp_db_meta_cols[path_tokens[1]] = handle
            elif len(path_tokens) == 1:
                wp_db_core_cols[db_path] = handle

        select_clause = ",\n\t\t".join(filter(
            None,
            [
                "core.%s as `%s`" % (key, name)
                for key, name in wp_db_core_cols.items()
            ] + [
                "MAX(CASE WHEN meta.meta_key = '%s' THEN meta.meta_value ELSE \"\" END) as `%s`" % (
                    key, name
                )
                for key, name in wp_db_meta_cols.items()
            ]
        ))

        sql_select = """
    SELECT
        {select_clause}
    FROM
        {tbl_core} core
        LEFT JOIN {tbl_meta} meta
        ON ( meta.`{meta_fkey}` = core.`{core_pkey}`)
    GROUP BY
        core.`{core_pkey}`""".format(
            core_pkey=core_pkey,
            meta_fkey='post_id',
            tbl_core=self.tbl_prefix + 'posts',
            tbl_meta=self.tbl_prefix + 'postmeta',
            select_clause=select_clause,
        )

        if Registrar.DEBUG_API:
            Registrar.register_message('sql_select:\n%s' % sql_select)

        where_clause = ''
        if filter_pkey is not None:
            where_clause = "WHERE filtered.id = {filter_pkey}".format(
                filter_pkey=filter_pkey
            )


        sql_select_filter = """
SELECT *
FROM
(
    {sql_ud}
) filtered
{where_clause}
{limit_clause};"""
        sql_select_filter = sql_select_filter.format(
            sql_ud=sql_select,
            join_type="LEFT",
            where_clause=where_clause,
            limit_clause="LIMIT %d" % limit if limit else ""
        )

        if Registrar.DEBUG_CLIENT:
            Registrar.register_message(sql_select_filter)

        cursor.execute(sql_select_filter)

        headers = [SanitationUtils.coerce_unicode(
            i[0]) for i in cursor.description]

        results = [[SanitationUtils.coerce_unicode(
            cell) for cell in row] for row in cursor]

        return [headers] + results

    def analyse_remote(self, parser, filter_items=None, **kwargs):

        rows = self.get_rows(filter_items, **kwargs)
        # print rows
        if rows:
            # print "there are %d results" % len(results)
            parser.analyse_rows(rows)
