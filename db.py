#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author = 'wyx'
@time = 16/7/29 11:22
@annotation = '' 
"""
import asyncio

import config
from aiomysql.sa import create_engine


@asyncio.coroutine
def get_conn():
    engine = yield from create_engine(**config.DB_CONFIG)
    return engine
