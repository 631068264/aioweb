#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author = 'wyx'
@time = 16/8/5 11:36
@annotation = '' 
"""
import os
from util.fcm import fcm

project_home = os.path.realpath(__file__)
project_home = os.path.split(project_home)[0]
import sys

sys.path.append(os.path.split(project_home)[0])
sys.path.append(project_home)

import config
from util import logger

# log setting
logger.init_log([(n, os.path.join("logs", p), l)
                 for n, p, l in config.LOG_CONFIG])
if getattr(config, 'fcm_log', None) is not None:
    fcm.FCM_LOGGER = logger.get(config.fcm_log).error
