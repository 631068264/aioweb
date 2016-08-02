#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author = 'wyx'
@time = 16/7/31 21:51
@annotation = '' 
"""
import json

import cons
from aiohttp.web_reqrep import Response


def OkResponse(data=None, message='', headers=None):
    resp = {
        'status': cons.STATUS.SUCCESS,
        'message': message,
    }
    if data:
        resp.update(data)

    return Response(text=json.dumps(resp), headers=headers,
                    content_type='application/json')


def ErrorResponse(data=None, message='', headers=None):
    resp = {
        'status': cons.STATUS.FAIL,
        'message': message,
    }
    if data:
        resp.update(data)

    return Response(text=json.dumps(resp), headers=headers,
                    content_type='application/json')
