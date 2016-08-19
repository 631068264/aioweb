#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author = 'wyx'
@time = 16/7/31 18:47
@annotation = '' 
"""
from sys import getsizeof

from base.framework import ErrorResponse, OkResponse, RouteCollector, data_check, general, db_conn
from base.xform import F_int, F_str
from config import FCM_CONFIG
from smartconnect import transaction
from smartsql import QS, F
from smartsql import T
from util.fcm.fcm import FCMNotification

route = RouteCollector('push', prefix='/android_push')
push_service = FCMNotification(max_concurrent=10)


@route('/token', method='POST')
@general()
@db_conn("db_writer")
@data_check({
    'uid': (F_int('用户id') > 0) & 'required' & 'strict',
    'token': F_str('用户token') & 'required' & 'strict',
})
async def token(request, safe_vars, db):
    with await db as conn:
        async with transaction(conn) as conn:
            await QS(conn).table(T.android_push).insert({
                "uid": safe_vars.uid,
                "reg_id": safe_vars.token,
            })

    return OkResponse()


@route('/notify', method='POST')
@general()
@db_conn("db_writer")
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
async def notify(request, safe_vars, db):
    with await db as conn:
        push_item = await QS(conn).table(T.android_push).where(F.uid == safe_vars.uids).select()
        registration_ids = [p.reg_id for p in push_item]

    safe_vars.registration_ids = registration_ids
    safe_vars.pop('uids')

    is_ok, msg = await push_service.notify(**safe_vars)
    if not is_ok:
        return ErrorResponse(**msg)
    return OkResponse(results=msg)
