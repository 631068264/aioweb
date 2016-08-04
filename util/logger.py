#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author = 'wyx'
@time = 16/8/3 22:33
@annotation = '' 
"""
import logging

_log_config = [
    ['', '', 'debug'],
    ['error-log', '', 'debug'],
]


def init_log(log_config=None):
    formater = logging.Formatter('%(name)-12s %(asctime)s %(levelname)-8s %(message)s',
                                 '%a, %d %b %Y %H:%M:%S', )

    if not log_config:
        log_config = _log_config

    for log in log_config:
        logger = logging.getLogger(log[0])
        if log[1]:
            handler = logging.FileHandler(log[1], 'a')
        else:
            import sys
            handler = logging.StreamHandler(sys.stderr)
            logger.propagate = False
        handler.setFormatter(formater)
        logger.addHandler(handler)
        logger.setLevel(getattr(logging, log[2].upper()))


def get(log_name=''):
    return logging.getLogger(log_name)


def error(msg, *args, **kwargs):
    get("cgi-log").error(msg, *args, **kwargs)


def warn(msg, *args, **kwargs):
    get("cgi-log").warn(msg, *args, **kwargs)


def info(msg, *args, **kwargs):
    get("cgi-log").info(msg, *args, **kwargs)


def debug(msg, *args, **kwargs):
    get("cgi-log").debug(msg, *args, **kwargs)
