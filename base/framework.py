#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author = 'wyx'
@time = 16/7/31 21:51
@annotation = '' 
"""
import json

from aiohttp.web_reqrep import Response
from base import cons
from functools import wraps


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


class OkResponse(Response):
    def __init__(self, **kwargs):
        Response.__init__(self)
        resp = {
            'status': cons.STATUS.SUCCESS,
            'message': '',
        }
        resp.update(kwargs)
        self.text = json.dumps(resp)
        self.content_type = 'application/json'


class ErrorResponse(Response):
    def __init__(self, **kwargs):
        Response.__init__(self)
        resp = {
            'status': cons.STATUS.FAIL,
            'message': '',
        }
        resp.update(kwargs)
        self.text = json.dumps(resp)
        self.content_type = 'application/json'
