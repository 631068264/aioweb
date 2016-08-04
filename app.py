#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author = 'wyx'
@time = 16/7/29 12:08
@annotation = '' 
"""

import os

project_home = os.path.realpath(__file__)
project_home = os.path.split(project_home)[0]
import sys

sys.path.append(os.path.split(project_home)[0])
sys.path.append(project_home)

import views
import config
from aiohttp import web
from util import logger

# log setting
logger.init_log([(n, os.path.join("logs", p), l)
                 for n, p, l in config.LOG_CONFIG])

app = web.Application()
for name in views.__all__:
    module = __import__('views.%s' % name, fromlist=[name])
    module.route.add_to_router(app.router)
app.make_handler(access_log='aiohttp.access')
app.make_handler(access_log='aiohttp.server')
web.run_app(app, port=8080, shutdown_timeout=15)
