#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author = 'wyx'
@time = 16/8/7 23:06
@annotation = '' 
"""

from base.framework import general, TemplateResponse, RouteCollector

route = RouteCollector('temp')


@route('/a')
@general()
async def a(request):
    return TemplateResponse('a.html', a='hello_w阿斯顿发放orld')


@route('/b/{a}')
@general()
async def b(request):
    return TemplateResponse('c/b.html', a='b')


@route('/r')
@general()
async def r(request):
    pass

# return aiohttp.web.HTTPFound(url('temp.a'))
