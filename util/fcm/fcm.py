#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author = 'wyx'
@time = 16/7/30 17:37
@annotation = '' 
"""
from config import FCM_CONFIG
from db import get_connection
from models import android_push
from .baseapi import FCMAPI

#
DEBUG = False


class FCMNotification(FCMAPI):
    async def notify(self,
                     registration_ids=None,
                     message_body=None,
                     message_title=None,
                     data_message=None,
                     low_priority=False,
                     collapse_key=None,
                     delay_while_idle=False,
                     time_to_live=None,
                     topic_name=None,
                     condition=None,
                     click_action=None,
                     tag=None,
                     color=None,
                     message_icon=None,
                     sound=None,
                     body_loc_key=None,
                     body_loc_args=None,
                     title_loc_key=None,
                     title_loc_args=None,
                     restricted_package_name=None):
        if len(registration_ids) > FCM_CONFIG['MAX_REGIDS']:
            payloads = []
            for regids in self.get_regids_chunks(registration_ids):
                payloads.append(self.parse_payload(registration_ids=[regids],
                                                   message_body=message_body,
                                                   message_title=message_title,
                                                   data_message=data_message,
                                                   low_priority=low_priority,
                                                   collapse_key=collapse_key,
                                                   delay_while_idle=delay_while_idle,
                                                   time_to_live=time_to_live,
                                                   topic_name=topic_name,
                                                   condition=condition,
                                                   click_action=click_action,
                                                   tag=tag,
                                                   dry_run=DEBUG,
                                                   color=color,
                                                   message_icon=message_icon,
                                                   sound=sound,
                                                   body_loc_key=body_loc_key,
                                                   body_loc_args=body_loc_args,
                                                   title_loc_key=title_loc_key,
                                                   title_loc_args=title_loc_args,
                                                   restricted_package_name=restricted_package_name
                                                   ))
        else:
            payload = self.parse_payload(registration_ids=[registration_ids],
                                         message_body=message_body,
                                         message_title=message_title,
                                         data_message=data_message,
                                         low_priority=low_priority,
                                         collapse_key=collapse_key,
                                         delay_while_idle=delay_while_idle,
                                         time_to_live=time_to_live,
                                         topic_name=topic_name,
                                         condition=condition,
                                         click_action=click_action,
                                         tag=tag,
                                         dry_run=DEBUG,
                                         color=color,
                                         message_icon=message_icon,
                                         sound=sound,
                                         body_loc_key=body_loc_key,
                                         body_loc_args=body_loc_args,
                                         title_loc_key=title_loc_key,
                                         title_loc_args=title_loc_args,
                                         restricted_package_name=restricted_package_name
                                         )
            payloads = [payload]
        try:
            request_result = await self.send_request(payloads)
            request_result = await parse_result(request_result)
        except Exception as e:
            print(e)
        return request_result


async def parse_result(request_result):
    if request_result.get('invalid_regids', None):
        connection = await get_connection()
        regids = request_result.get('invalid_regids')
        regids = [regid['reg_id'] for regid in regids]
        async with connection.acquire() as conn:
            trans = await conn.begin()
            try:
                failed_items = await conn.execute(android_push.select(android_push.c.reg_id.in_(regids)))
                fail_uids = [item.uid for item in failed_items]
                request_result['fail_uids'] = fail_uids
                await conn.execute(android_push.delete(android_push.c.reg_id.in_(regids)))
            except Exception:
                await trans.rollback()
            await trans.commit()
            return request_result
    return request_result
