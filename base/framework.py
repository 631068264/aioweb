#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author = 'wyx'
@time = 16/7/31 21:51
@annotation = '' 
"""
from json import JSONDecodeError

from aiohttp.web_reqrep import Response
from attrdict import AttrDict
from base import cons
from base.util import safe_json_dumps
from base.xform import DataChecker, default_messages
from functools import wraps


############################################################
# Route https://github.com/IlyaSemenov/aiohttp_route_decorator
############################################################
class Route:
    """
    Usage:

    route = RouteCollector()

    @route('/foo')
    async def handler(request):
    	return web.Response(body=b'OK')
    ...

    app = Application()
    route.add_to_router(app.router)
    """

    def __init__(self, path, handler, *, method='GET', methods=None, name=None, **kwargs):
        self.path = path
        self.handler = handler
        self.methods = [method] if methods is None else methods
        self.name = name
        self.kwargs = kwargs

    def add_to_router(self, router, prefix=''):
        resource = router.add_resource(prefix + self.path, name=self.name)
        for method in self.methods:
            resource.add_route(method, self.handler, **self.kwargs)
        return resource


class RouteCollector(list):
    def __init__(self, iterable=[], *, prefix='', routes=[]):
        if iterable and routes:
            raise ValueError("RouteCollector accepts either iterable or routes, but not both")
        super().__init__(routes or iterable)
        self.prefix = prefix

    def __call__(self, path, *, method='GET', methods=None, name=None, **kwargs):
        def wrapper(handler):
            self.append(Route(path, handler, method=method, methods=methods, name=name, **kwargs))
            return handler

        return wrapper

    def add_to_router(self, router, prefix=''):
        for route in self:
            route.add_to_router(router, prefix=prefix + self.prefix)


############################################################
# Response
############################################################
class JsonResponse(Response):
    def __init__(self, **kwargs):
        Response.__init__(self)
        self._json = {} if kwargs is None else kwargs
        self.content_type = 'application/json'
        self.text = safe_json_dumps(self._json)


class OkResponse(JsonResponse):
    def __init__(self, **kwargs):
        resp = {
            'status': cons.STATUS.SUCCESS,
            'message': '',
        }
        resp.update(kwargs)
        JsonResponse.__init__(self, **resp)


class ErrorResponse(JsonResponse):
    def __init__(self, message='', **kwargs):
        if isinstance(message, (list, tuple)):
            message = ", ".join(message)
        resp = {
            'status': cons.STATUS.FAIL,
            'message': message,
        }
        resp.update(kwargs)
        JsonResponse.__init__(self, **resp)


############################################################
# Decorator
############################################################
def data_check(settings=None, var_name='safe_vars', error_handler=None, is_strict=True, error_var='form_vars'):
    if error_handler is None:
        error_handler = ErrorResponse

    def new_deco(old_handler):
        @wraps(old_handler)
        async def new_handler(request, *args, **kwargs):
            # Collect data
            is_ok, req_data = await get_request_data(request)
            if not is_ok:
                return error_handler(req_data)
            checker = DataChecker(req_data, settings)

            if not checker.is_valid():
                if is_strict:
                    error_msg = [v for v in checker.err_msg.values() if v is not None]
                    return error_handler(error_msg)
                else:
                    kwargs[error_var] = checker.err_msg
                    return await old_handler(request, *args, **kwargs)
            kwargs[var_name] = AttrDict(checker.valid_data)

            resp = await old_handler(request, *args, **kwargs)

            return resp

        return new_handler

    return new_deco


async def get_request_data(request):
    req_data = {}
    if request.method == 'POST':
        if request.content_type.startswith('application/json'):
            try:
                json_data = await request.json()
                req_data.update(json_data)
            except JSONDecodeError as e:
                return False, default_messages['json']
        else:
            post_data = await request.post()
            req_data.update(post_data)
    elif request.method == 'GET':
        get_data = request.GET
        req_data.update(get_data)

    url_data = request.match_info
    req_data.update(url_data)
    return True, req_data
