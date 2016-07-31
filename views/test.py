#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author = 'wyx'
@time = 16/7/31 18:47
@annotation = '' 
"""
import asyncio

from aiohttp import web
from aiohttp_route_decorator import RouteCollector

route = RouteCollector()


# TODO:对外接口
@route('/')
async def index(request):
    body = b'Hello world'
    return web.Response(body='<h1>是打发斯蒂芬, %s!</h1>'.encode('utf-8'))


@route('/{name}')
async def hello(request):
    await asyncio.sleep(0.5)
    h = request.GET["sdf"]
    text = '<h1>是打发斯蒂芬, %s!</h1>' % request.match_info['name']
    return web.Response(text=text)


@route('/post')
async def df(request):
    await asyncio.sleep(0.5)
    # ll = await request.post.get["asdfad"]
    sdf = await request.post()
    sf = sdf.get("asdfad")
    text = '<h1>hello, %s!</h1>' % request.match_info['name']
    return web.Response(body=text.encode('utf-8'))


@route('/jsonpost')
async def jsonpost(request):
    await asyncio.sleep(0.5)
    # ll = await request.post.get["asdfad"]
    sdf = await request.json()
    sdf = sdf["data"]

    return web.json_response({"fadfadf": 1})
