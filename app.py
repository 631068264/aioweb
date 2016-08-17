#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author = 'wyx'
@time = 16/7/29 12:08
@annotation = '' 
"""
import os
from db import smartconnect

project_home = os.path.realpath(__file__)
project_home = os.path.dirname(project_home)
import sys

sys.path.append(os.path.dirname(project_home))
sys.path.append(project_home)

import config
from base import logger
from util.fcm import fcm
import aiohttp_jinja2
import views
from aiohttp import web
from jinja2 import FileSystemLoader
import jinja_filter
from framework import error_middleware

# log setting
logger.init_log([(n, os.path.join("logs", p), l)
                 for n, p, l in config.LOG_CONFIG])
if getattr(config, 'fcm_log', None) is not None:
    fcm.FCM_LOGGER = logger.get(config.fcm_log).error

# TODO:数据库初始化
if getattr(config, 'query_log', None) is not None:
    smartconnect.query_log = logger.get(config.query_log).info

app = web.Application(middlewares=[error_middleware, ])
# import handler
for name in views.__all__:
    module = __import__('views.%s' % name, fromlist=[name])
    module.route.add_to_router(app.router, prefix=config.app_path)

# app-log setting
app.make_handler(access_log='aiohttp.access')

# template setting
env = aiohttp_jinja2.setup(app=app, loader=FileSystemLoader(os.path.join(project_home, 'templates')))
app.router.add_static(config.static_path, os.path.join(project_home, 'static'))
for name, func in jinja_filter.mapping.items():
    env.filters[name] = func

# app run
web.run_app(app, port=8080, shutdown_timeout=15)
