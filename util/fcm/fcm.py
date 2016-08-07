#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author = 'wyx'
@time = 16/7/30 17:37
@annotation = '' 
"""
import asyncio

from .baseapi import FCMAPI

# 设置dry_run 调试模式 只是发送到FCM服务器不会发送到设备
DEBUG = False
FCM_LOGGER = None


class FCMNotification(FCMAPI):
    def __init__(self, max_concurrent):
        super(FCMNotification, self).__init__(max_concurrent, FCM_LOGGER)

    async def notify(self,
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
                     color=None,
                     message_icon=None,
                     sound=None,
                     body_loc_key=None,
                     body_loc_args=None,
                     title_loc_key=None,
                     title_loc_args=None,
                     restricted_package_name=None):

        payloads = []
        for regids in self.get_regids_chunks(registration_ids):
            payloads.append(self.parse_payload(task_id=task_id,
                                               registration_ids=regids,
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
        tasks = []
        results = []
        for payload in payloads:
            req_future = asyncio.ensure_future(self.send_request(payload))

            def push_response(fut):
                try:
                    res = fut.result()
                    results.append(res)
                except Exception as e:
                    print(e)
                    for f in tasks:
                        f.cancel()

            req_future.add_done_callback(push_response)
            tasks.append(req_future)
        await asyncio.wait(tasks)
        return True, results
