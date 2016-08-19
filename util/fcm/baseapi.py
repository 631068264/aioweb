#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author = 'wyx'
@time = 16/7/29 17:19
doc https://firebase.google.com/docs/cloud-messaging/http-server-ref
 https://firebase.google.com/docs/cloud-messaging/concept-options
"""
import asyncio
import json

from aiohttp import ClientSession, errors
from base.cons import FCM_STATUS_CODE
from config import FCM_CONFIG
from db.smartconnect import transaction
from db.smartsql import QS, T, F
from framework import db_conn


class FCMAPI(object):
    CONTENT_TYPE = 'application/json'
    FCM_URL = FCM_CONFIG['URL']
    API_KEY = FCM_CONFIG['API_KEY']

    MAX_REGIDS = FCM_CONFIG['MAX_REGIDS']
    LOW_PRIORITY = FCM_CONFIG['LOW_PRIORITY']
    HIGH_PRIORITY = FCM_CONFIG['HIGH_PRIORITY']

    def __init__(self, max_concurrent=10, fcm_logger=None):
        self.sem = asyncio.Semaphore(value=max_concurrent)
        self.logger = fcm_logger

    def log(self, msg):
        if self.logger is None:
            return
        self.logger(msg)

    def request_headers(self):
        return {
            'Content-Type': self.CONTENT_TYPE,
            'Authorization': 'key=' + self.API_KEY,
        }

    def dump_json(self, data):
        return json.dumps(data, separators=(',', ':'), sort_keys=True)

    def get_regids_chunks(self, regids):
        for i in range(0, len(regids), self.MAX_REGIDS):
            yield regids[i:i + self.MAX_REGIDS]

    def parse_payload(self,
                      task_id,
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
                      dry_run=False,
                      color=None,
                      message_icon=None,
                      sound=None,
                      body_loc_key=None,
                      body_loc_args=None,
                      title_loc_key=None,
                      title_loc_args=None,
                      restricted_package_name=None):

        fcm_payload = {}
        if task_id:
            fcm_payload['task_id'] = task_id
        # 发送对象
        if registration_ids:
            fcm_payload['registration_ids'] = registration_ids
        # 即时发送
        fcm_payload['priority'] = self.LOW_PRIORITY if low_priority else self.HIGH_PRIORITY
        # 折叠
        if collapse_key:
            fcm_payload['collapse_key'] = collapse_key
        # 消息寿命
        if delay_while_idle:
            fcm_payload['delay_while_idle'] = delay_while_idle
        if time_to_live and isinstance(time_to_live, int):
            fcm_payload['time_to_live'] = time_to_live
        # 数据处理
        if data_message and isinstance(data_message, dict):
            fcm_payload['data'] = data_message
        if message_body:
            fcm_payload['notification'] = {
                'body': message_body,
                'title': message_title,
                'icon': message_icon
            }
            if click_action:
                fcm_payload['notification']['click_action'] = click_action
            if color:
                fcm_payload['notification']['color'] = color
            if tag:
                fcm_payload['notification']['tag'] = tag
            if body_loc_key:
                fcm_payload['notification']['body_loc_key'] = body_loc_key
            if body_loc_args:
                fcm_payload['notification']['body_loc_args'] = body_loc_args
            if title_loc_key:
                fcm_payload['notification']['title_loc_key'] = title_loc_key
            if title_loc_args:
                fcm_payload['notification']['title_loc_args'] = title_loc_args
            if sound:
                fcm_payload['notification']['sound'] = sound
        # 主题消息
        if condition:
            fcm_payload['condition'] = condition
        elif topic_name:
            fcm_payload['to'] = '/topic/%s' % topic_name

        if dry_run:
            fcm_payload['dry_run'] = dry_run
        if restricted_package_name:
            fcm_payload['restricted_package_name'] = restricted_package_name

        return self.dump_json(fcm_payload)

    async def send_request(self, payload):
        await self.sem.acquire()
        result = {}
        dump = json.loads(payload)
        task_id = dump['task_id']
        registration_ids = dump['registration_ids']
        try:
            async with ClientSession() as session:
                async with session.post(self.FCM_URL, data=payload, headers=self.request_headers()) as resp:
                    resp_status = resp.status
                    if resp_status == 200:
                        json_body = await resp.json()
                        msg = self.parse_response(json_body, registration_ids)
                        # 处理失败reg_id
                        if isinstance(msg, list):
                            await self.handler_error_regids(msg)
                    elif resp_status == 400:
                        msg = await resp.text()
                        self.log('FCM_Response [task_id=%s]:[ %d ]:%s' % (task_id, resp_status, msg))
                    elif resp_status == 401:
                        msg = FCM_STATUS_CODE[resp_status]
                        self.log('AuthenticationError [task_id=%s]:%s' % (task_id, 'API_KEY_ERROR'))
                    else:
                        msg = await resp.text()
                        self.log('FCM_Response [task_id=%s]:[ %d ]:%s' % (task_id, resp_status, msg))
                        msg = FCM_STATUS_CODE.get(resp_status, FCM_STATUS_CODE[500])

                    result['task_id'] = task_id
                    result['status'] = resp_status
                    result['message'] = FCM_STATUS_CODE[201] if isinstance(msg, list) else msg
            return result
        except errors.ClientOSError as e:
            self.log('[asyncio.errores.ClientOSError] [ task_id=%s ]%s' % (task_id, e.strerror))
            result['task_id'] = task_id
            result['status'] = 500
            result['message'] = e.strerror
            return result
        finally:
            self.sem.release()

    def parse_response(self, response, regids):
        failure = response.get('failure', 0)
        error = ''
        if failure > 0:
            results = response.get('results', [])
            if len(results) == 1:
                # 处理非regid错
                msg = results[0].get('error', '')
                if msg.lower().find('reg') >= 0:
                    error = {
                        'reg_id': regids[0],
                        'reason': msg,
                    }
                    return [error]
                error = msg
            else:
                error = []
                for index, result in enumerate(results):
                    msg = result.get('error', '')
                    if msg and msg.lower().find('reg') >= 0:
                        error.append({
                            'reg_id': regids[index],
                            'reason': msg,
                        })
        if error:
            return error
        return FCM_STATUS_CODE[200]

    @db_conn("db_writer")
    async def handler_error_regids(self, regids, db):
        regids = [reg_id['reg_id'] for reg_id in regids]

        with await db as conn:
            async with transaction(conn) as conn:
                fail_uids = await QS(conn).table(T.android_push).where(F.reg_id == regids).group_by(F.uid).select(F.uid)
                fail_uisds = [uid.uid for uid in fail_uids]
                await QS(conn).table(T.android_push).where(F.reg_id == regids).delete()
