try:
    import http.client as httplib
except ImportError:
    import httplib

import base64
import decimal
import urllib
try:
    import urllib.parse as urlparse
except ImportError:
    import urlparse

from jsonrpc.json import dumps, loads

USER_AGENT = 'python-jsonrpc/1.1'
HTTP_TIMEOUT = 30


class JSONRPCException(Exception):
    def __init__(self, error):
        super(JSONRPCException, self).__init__()
        self.error = error


class ServiceProxy(object):
    def __init__(self, service_url, name=None, use_decimal=False):
        self._service_url = service_url
        self._name = name
        self._idcnt = 0
        self._use_decimal = use_decimal

        self._url = urlparse.urlparse(service_url)
        if self._url.port is None:
            port = 80
        else:
            port = self._url.port

        if self._url.scheme == 'https':
            self._conn = httplib.HTTPSConnection(self._url.hostname, port,
                                                 None, None,
                                                 False, HTTP_TIMEOUT)
        else:
            self._conn = httplib.HTTPConnection(self._url.hostname, port,
                                                False, HTTP_TIMEOUT)

        self._headers = {
                'Host': self._url.hostname,
                'User-Agent': USER_AGENT,
                'Content-type': 'application/json',
        }

        username = self._url.username
        password = self._url.password
        if username and password:
            authpair = '%s:%s' % (username, password)
            authpair = authpair.encode('utf-8')
            authhdr = 'Basic ' + base64.b64encode(authpair)
            self._headers['Authorization'] = authhdr

    def __getattr__(self, name):
        if self._name is not None:
            name = '%s.%s' % (self._name, name)
        return ServiceProxy(self._service_url, name)

    def __call__(self, *args):
        self._idcnt += 1

        postdata = dumps({
                'id': self._idcnt,
                'version': '1.1',
                'method': self._name,
                'params': args,
        })

        self._conn.request('POST', self._url.path, postdata, self._headers)

        httpresp = self._conn.getresponse()
        if httpresp is None:
            raise JSONRPCException({
                        'code': -342,
                        'message': 'missing HTTP response from the server',
                    })

        resp = httpresp.read().decode('utf-8')
        if self._use_decimal:
            resp = loads(resp, parse_float=decimal.Decimal)
        else:
            resp = loads(resp)

        error = resp.get('error', None)
        if error is not None:
            raise JSONRPCException(error)

        try:
            return resp['result']
        except KeyError:
            raise JSONRPCException({
                        'code': -342,
                        'message': 'missing result in JSON payload',
                    })
