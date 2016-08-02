#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author = 'wyx'
@time = 16/7/31 18:47
@annotation = '' 
"""

from aiohttp_route_decorator import RouteCollector
from db import get_connection
from models import android_push
from util.fcm.fcm import FCMNotification
from util.framework import ErrorResponse, OkResponse

route = RouteCollector(prefix='/android_push')
push_service = FCMNotification()


@route('/token', method='POST')
async def token(request):
    resp = await request.json()
    connection = await get_connection()
    async with connection.acquire() as conn:
        trans = await conn.begin()
        try:
            stmt = android_push.insert({'uid': resp['uid'],
                                        'reg_id': resp['token'],
                                        })
            await conn.execute(stmt)
        except Exception as e:
            await trans.rollback()
            return ErrorResponse()
        await trans.commit()

    return OkResponse()


@route('/notify', method='POST')
async def notify(request):
    resp = await request.json()
    uids = resp['uids']
    connection = await get_connection()
    async with connection.acquire() as conn:
        push_item = await conn.execute(android_push.select(android_push.c.uid.in_(uids)))
        registration_ids = [p.reg_id for p in push_item]

    param = {
        'registration_ids': registration_ids,
        'message_body': resp.get('message_body', None),
        'message_title': resp.get('message_title', None),
        'data_message': resp.get('data_message', None),
    }
    is_ok, msg = await push_service.notify(**param)
    if not is_ok:
        return ErrorResponse(message=msg)
    return OkResponse()
