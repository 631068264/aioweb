#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author = 'wyx'
@time = 16/7/30 11:44
@annotation = '' 
"""
FCM_STATUS_CODE = {
    200: 'Success',
    201: 'Partial success',
    401: 'Unauthorized',
    400: 'JSON parsing error',
    500: 'FCM server is temporarily unavailable',
}


class STATUS(object):
    SUCCESS = 1
    FAIL = 0
