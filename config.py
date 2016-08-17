#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author = 'wyx'
@time = 16/7/29 11:08
@annotation = '' 
"""
DB_CONFIG = {
    'host': '127.0.0.1',
    'port': 3306,
    'db': 'android_push',
    'user': 'root',
    'password': '',
}

FCM_CONFIG = {
    'URL': 'https://fcm.googleapis.com/fcm/send',
    'API_KEY': 'AIzaSyAk7t-GDiMyUYGC_5oxwoAoVAjSzs_afqc',
    'MAX_REGIDS': 1000,
    'LOW_PRIORITY': 'normal',
    'HIGH_PRIORITY': 'high',
    'MAX_SIZE_BODY': 2048,
    'TIME_TO_LIVE': (0, 2419200)
}

fcm_log = 'fcm-log'
query_log = 'query-log'
LOG_CONFIG = [
    ['aiohttp.access', 'access.log', 'debug'],
    ['web-error', 'web-error.log', 'debug'],
    [fcm_log, 'fcm-service.log', 'debug'],
    [query_log, 'query.log', 'debug'],
]

app_path = ''
static_path = '/static'
