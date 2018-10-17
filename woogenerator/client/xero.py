"""Client classes for Xero API."""

from __future__ import absolute_import, print_function, unicode_literals

import os
from builtins import super

from xero import Xero
from xero.auth import PrivateCredentials

from ..utils import Registrar
from .core import SyncClientAbstract


class SyncClientXero(SyncClientAbstract):
    """
    Class for Xero API Clients.
    Todo:
        - Make this work with SyncClientRest
    """

    service_builder = Xero
    service_name = 'XERO'
    endpoint_singular = ''
    mandatory_params = ['api_key', 'rsa_key_file']
    key_translation = {}
    coldata_target = 'xero-api'
    coldata_target_write = 'xero-api'

    def __init__(self, connect_params, **kwargs):
        self.limit = connect_params.get('limit')
        self.offset = connect_params.get('offset', 0)
        self.since = connect_params.get('since')

        for param in self.mandatory_params:
            assert param in connect_params and connect_params[param], \
                "missing mandatory param (%s) from connect parameters: %s" \
                % (param, str(connect_params))

        superconnect_params = {}
        rsa_key_file = connect_params['rsa_key_file']
        rsa_key_file = os.path.expanduser(rsa_key_file)
        with open(rsa_key_file) as keyfile:
            rsa_key = keyfile.read()
            superconnect_params['credentials'] = PrivateCredentials(
                consumer_key=connect_params['api_key'], rsa_key=rsa_key)

        super().__init__(superconnect_params, **kwargs)

    @property
    def endpoint_plural(self):
        return self.endpoint_singular + 's'

    def analyse_remote(self, parser, **kwargs):
        limit = kwargs.get('limit', self.limit)
        since = kwargs.get('since', self.since)
        search = kwargs.get('search')
        # TODO: implement search

        endpoint_obj = getattr(self.service, self.endpoint_plural)
        if since or search:
            filter_params = {}
            if since:
                print("since passed as %s %s" % since, type(since))
                filter_params['since'] = since
            endpoint_items = endpoint_obj.filter(**filter_params)
        else:
            endpoint_items = endpoint_obj.all()

        result_count = 0
        endpoint_items = endpoint_obj.all()
        for endpoint_item in endpoint_items[self.offset:]:
            parser.analyse_api_obj(endpoint_item)
            result_count += 1
            if limit and result_count > limit:
                if Registrar.DEBUG_API:
                    Registrar.register_message('reached limit, exiting')
                return
