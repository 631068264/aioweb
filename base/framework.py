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
