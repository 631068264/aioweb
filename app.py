#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author = 'wyx'
@time = 16/7/29 12:08
@annotation = '' 
"""

import views
from aiohttp import web

app = web.Application()
for name in views.__all__:
    module = __import__('views.%s' % name, fromlist=[name])
    module.route.add_to_router(app.router)
web.run_app(app, port=8080, shutdown_timeout=15)
