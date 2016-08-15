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
def get_connection():
    engine = yield from create_engine(echo=True, **config.DB_CONFIG)
    return engine
