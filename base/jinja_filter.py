#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author = 'wyx'
@time = 16/8/8 17:27
@annotation = '' 
"""
import functools


def format_datetime(value, format="%Y-%m-%d %H:%M:%S", default=""):
    if value is None:
        return default
    return value.strftime(format)


# mapping

mapping = {
    'fmt_date': functools.partial(format_datetime, format="%Y-%m-%d"),
}
