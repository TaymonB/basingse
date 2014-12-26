import enum
import gzip

import requests
from django.conf import settings

GET, EMPTY_POST = enum.Enum('EmptyRequest', ('get', 'post'))
EMPTY_RESP, OBJECT_RESP, BINARY_RESP = enum.Enum('ResponseType', ('empty', 'properties', 'binary'))

class ElastichostsException(Exception):
    pass

def api_call(resource, data=GET, expected=OBJECT_RESP, gzip_data=True):
    params = {'url': settings.ELASTICHOSTS_API_ENDPOINT + '/'.join(resource),
              'auth': settings.ELASTICHOSTS_API_CREDENTIALS}
    if expected == OBJECT_RESP:
        params['headers'] = {'Accept': 'application/json'}
    if data == GET:
        req = requests.get(**params)
    elif data == EMPTY_POST:
        req = requests.post(**params)
    elif isinstance(data, dict):
        req = requests.post(json=data, **params)
    elif isinstance(data, bytes):
        headers = params.setdefault('headers', {})
        headers['Content-Type'] = 'application/octet-stream'
        if gzip_data:
            headers['Content-Encoding'] = 'gzip'
            data = gzip.compress(data)
        req = requests.post(data=data, **params)
    else:
        raise TypeError('invalid data type')
    try:
        req.raise_for_status()
    except requests.exceptions.HTTPError as req_error:
        if 'X-Elastic-Error' in req.headers:
            eh_error = ElastichostsException(req.text)
            eh_error.elastic_error = req.headers['X-Elastic-Error']
            raise eh_error from req_error
        else:
            raise
    if expected == EMPTY_RESP:
        assert req.status_code == 204
    elif expected == OBJECT_RESP:
        return req.json()
    elif expected == BINARY_RESP:
        return req.content
    else:
        raise ArgumentError('invalid expected')
