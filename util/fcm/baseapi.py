#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author = 'wyx'
@time = 16/7/29 17:19
doc https://firebase.google.com/docs/cloud-messaging/http-server-ref
 https://firebase.google.com/docs/cloud-messaging/concept-options
"""
import json

from aiohttp import ClientSession, errors
from config import FCM_CONFIG
from cons import FCM_STATUS_CODE


class FCMAPI(object):
    CONTENT_TYPE = 'application/json'
    FCM_URL = FCM_CONFIG['URL']
    API_KEY = FCM_CONFIG['API_KEY']

    MAX_REGIDS = FCM_CONFIG['MAX_REGIDS']
    LOW_PRIORITY = FCM_CONFIG['LOW_PRIORITY']
    HIGH_PRIORITY = FCM_CONFIG['HIGH_PRIORITY']

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

    async def send_request(self, payloads):
        results = []
        for payload in payloads:
            result = {}
            try:
                async with ClientSession() as session:
                    async with session.post(self.FCM_URL, data=payload, headers=self.request_headers()) as resp:
                        resp_status = resp.status
                        if resp_status == 200:
                            json_body = await resp.json()
                            msg = self.parse_response(json_body, json.loads(payload)['registration_ids'])
                            if isinstance(msg, list):
                                result['status'] = resp_status
                                result['message'] = FCM_STATUS_CODE[201]
                                result['invalid_regids'] = msg
                                results.append(result)
                                continue
                        elif resp_status == 400:
                            msg = await resp.text()
                        else:
                            msg = FCM_STATUS_CODE.get(resp_status, FCM_STATUS_CODE[500])

                        result['status'] = resp_status
                        result['message'] = msg
                        results.append(result)
            except errors.ClientOSError as e:
                return False, e
        return True, results

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


if __name__ == "__main__":
    def get_regids_chunks(regid):
        for i in range(0, len(regid), 2):
            yield regid[i:i + 2]


    l = [1, 2, 3, 4, 5, 6, 7, 8, 9, 9, ]

    for i in get_regids_chunks(l):
        print(i)
