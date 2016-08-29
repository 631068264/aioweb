#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author = 'wyx'
@time = 16/7/29 12:08
@annotation = '' 
"""

import os
from base.smartconnect import MysqlConnection

project_home = os.path.realpath(__file__)
project_home = os.path.dirname(project_home)
import sys

sys.path.append(os.path.dirname(project_home))
sys.path.append(project_home)
from base import smartconnect, jinja_filter, logger
from base.framework import error_middleware
import config
from util.fcm import fcm
import aiohttp_jinja2
import views
from aiohttp import web
from jinja2 import FileSystemLoader

# log setting
logger.init_log([(n, os.path.join("logs", p), l)
                 for n, p, l in config.LOG_CONFIG])
if getattr(config, 'fcm_log', None) is not None:
    fcm.FCM_LOGGER = logger.get(config.fcm_log).error

if getattr(config, 'query_log', None) is not None:
    smartconnect.query_log = logger.get(config.query_log).info
if getattr(config, 'query_echo', None) is not None:
    smartconnect.query_echo = config.query_echo

for name, setting in config.db_config.items():
    smartconnect.init_pool(name, setting, MysqlConnection, *config.pool_size)

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
