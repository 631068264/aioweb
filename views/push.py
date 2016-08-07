#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author = 'wyx'
@time = 16/7/31 18:47
@annotation = '' 
"""
from sys import getsizeof

from base.db import get_connection
from base.framework import ErrorResponse, OkResponse, RouteCollector, data_check
from base.models import android_push
from base.xform import F_int, F_str
from config import FCM_CONFIG
from util.fcm.fcm import FCMNotification

route = RouteCollector(prefix='/android_push')
push_service = FCMNotification(max_concurrent=10)


@route('/token', method='POST')
@data_check({
    'uid': (F_int('用户id') > 0) & 'required' & 'strict',
    'token': F_str('用户token') & 'required' & 'strict',
})
async def token(request, safe_vars):
    connection = await get_connection()
    async with connection.acquire() as conn:
        trans = await conn.begin()
        try:
            stmt = android_push.insert({'uid': safe_vars.uid,
                                        'reg_id': safe_vars.token,
                                        })
            await conn.execute(stmt)
        except Exception as e:
            await trans.rollback()
            return ErrorResponse()
        await trans.commit()

    return OkResponse()


@route('/notify', method='POST')
@data_check({
    'uids': (F_int('用户id') > 0) & 'required' & 'strict' & 'multiple',
    'task_id': F_str('任务id') & 'required' & 'strict',
    'message_body': F_str('message_body') & 'optional' & 'strict' & (
            lambda v: (getsizeof(v) <= FCM_CONFIG['MAX_SIZE_BODY'], v)),
    'message_title': F_str('message_body') & 'optional' & 'strict' & (
            lambda v: (getsizeof(v) <= FCM_CONFIG['MAX_SIZE_BODY'], v)),
    'data_message': F_str('data_message') & 'optional' & 'strict',
    'time_to_live': (FCM_CONFIG['TIME_TO_LIVE'][0] < F_int('time_to_live') < FCM_CONFIG['TIME_TO_LIVE'][
        1]) & 'optional' & 'strict',

})
async def notify(request, safe_vars):
    connection = await get_connection()
    async with connection.acquire() as conn:
        push_item = await conn.execute(android_push.select(android_push.c.uid.in_(safe_vars.uids)))
        registration_ids = [p.reg_id for p in push_item]

    safe_vars.registration_ids = registration_ids
    safe_vars.pop('uids')

    is_ok, msg = await push_service.notify(**safe_vars)
    if not is_ok:
        return ErrorResponse(**msg)
    return OkResponse(results=msg)
