#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author = 'wyx'
@time = 16/7/31 21:51
@annotation = '' 
"""
from functools import wraps
from json import JSONDecodeError

import aiohttp
from aiohttp.web_exceptions import HTTPException
from aiohttp.web_reqrep import Response, json_response
from aiohttp_jinja2 import render_template
from attrdict import AttrDict

import config
import logger
from base import cons, util
from base.xform import default_messages, DataChecker
from smartconnect import get_conn

__all__ = [
    "RouteCollector",

    "JsonResponse",
    "TemplateResponse",
    "Redirect",
    "OkResponse",
    "ErrorResponse",

    "general",
    "db_conn",
    "data_check",
]


############################################################
# Route Inspired by the https://github.com/IlyaSemenov/aiohttp_route_decorator
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

    In the template use "url('reverse_route_name')" to get the url
    """

    def __init__(self, path, handler, *, method='GET', methods=None, name=None, **kwargs):
        self.path = path
        self.handler = handler
        self.methods = [method] if methods is None else methods
        self.name = name
        self.kwargs = kwargs

    def add_router(self, router, prefix=''):
        resource = router.add_resource(prefix + self.path, name=self.name)
        for method in self.methods:
            resource.add_route(method, self.handler, **self.kwargs)
        return resource


class RouteCollector(list):
    """
    Usage :
        RouteCollector should have a name
    """

    def __init__(self, name='', *, prefix='', routes=[]):
        if not name:
            raise Exception("RouteCollector should have a name")
        super().__init__(routes)
        self._prefix_path = prefix
        self._prefix_name = name

    def __call__(self, path, *, method='GET', methods=None, name=None, **kwargs):
        self._method_name = name

        def wrapper(handler):
            if self._method_name:
                reverse_route_name = '%s.%s' % (self._prefix_name, self._method_name)
            else:
                reverse_route_name = '%s.%s' % (self._prefix_name, handler.__name__)

            self.append(Route(path, handler, method=method, methods=methods, name=reverse_route_name, **kwargs))
            return handler

        return wrapper

    def add_to_router(self, router, prefix=''):
        for route in self:
            route.add_router(router, prefix=prefix + self._prefix_path)


############################################################
# Response
############################################################
class JsonResponse(Response):
    def __init__(self, **kwargs):
        Response.__init__(self)
        self._json = {} if kwargs is None else kwargs
        self._text = util.safe_json_dumps(self._json)

    def output(self):
        return json_response(text=self._text)


class TemplateResponse(Response):
    def __init__(self, template_name, **context):
        Response.__init__(self)
        self._template_name = template_name
        self._context = context

    def context_update(self, **kwargs):
        self._context.update(kwargs)
        self._request = self._context.pop('request')

    def output(self):
        return render_template(self._template_name, request=self._request,
                               context=self._context)


class Redirect(Response):
    def __init__(self, route_name, query=None, **kwargs):
        Response.__init__(self)
        self._parts = kwargs
        self._route_name = route_name
        self._query = query

    def conext_update(self, **kwargs):
        self._parts.update(kwargs)
        self._request = self._parts.pop('request')

    def output(self):
        path = self._request.app.router[self._route_name].url(
            parts=self._parts, query=self._query)
        return aiohttp.web.HTTPFound(path)


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
# Middleware
############################################################
async def error_middleware(app, handler):
    async def middleware_handler(request):
        try:
            return await handler(request)
        except HTTPException as e:
            if e.status == 404:
                return ErrorResponse('Not Found').output()
            elif e.status == 500:
                import traceback
                err_msg = traceback.format_exc()
                logger.get('web-error').error(err_msg)
                return ErrorResponse(err_msg).output()
        except Exception:
            import traceback
            err_msg = traceback.format_exc()
            print(err_msg)
            logger.get('web-error').error(err_msg)
            return ErrorResponse('System Crash').output()

    return middleware_handler


############################################################
# Decorator
############################################################
def general(desc=None):
    """
    this decorator must the first one that after route one
    :param desc:
    :return:
    """

    def new_deco(old_handler):
        @wraps(old_handler)
        async def new_handler(request, *args, **kwargs):
            print("%s - - %s %s" % (request.transport.get_extra_info('peername')[0], request.method, request.path_qs,))
            resp = await old_handler(request, *args, **kwargs)
            if isinstance(resp, TemplateResponse):
                # add specific context
                resp.context_update(
                    request=request,
                    config=config,
                    cons=cons,
                    util=util,
                )
            elif isinstance(resp, Redirect):
                resp.conext_update(
                    request=request,
                )
            return resp.output()

        return new_handler

    return new_deco


def db_conn(db_name, var_name="db"):
    def new_deco(old_handler):
        @wraps(old_handler)
        async def new_handler(request, *args, **kwargs):
            kwargs[var_name] = await get_conn(db_name)
            return await old_handler(request, *args, **kwargs)

        return new_handler

    return new_deco


def data_check(settings=None, var_name="safe_vars", error_handler=None, is_strict=True, error_var='form_vars'):
    if error_handler is None:
        error_handler = ErrorResponse

    def new_deco(old_handler):
        @wraps(old_handler)
        async def new_handler(request, *args, **kwargs):
            # collect data
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
