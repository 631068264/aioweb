#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author = 'wyx'
@time = 16/7/29 11:08
@annotation = '' 
"""
DB_CONFIG = {
    "host": "127.0.0.1",
    "port": "3306",
    "db": "android_push",
    "user": "root",
    "password": "",
}

FCM_CONFIG = {
    "URL": "https://fcm.googleapis.com/fcm/send",
    "API_KEY": "AIzaSyAk7t-GDiMyUYGC_5oxwoAoVAjSzs_afqc",
    "MAX_REGIDS": 1000,
    "LOW_PRIORITY": 'normal',
    "HIGH_PRIORITY": 'high',
}
