#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author = 'wyx'
@time = 16/7/31 11:19
@annotation = '' 
"""
import sqlalchemy as sa
from sqlalchemy import select

metadata = sa.MetaData()

android_push = sa.Table(
    'android_push',
    metadata,
    sa.Column('id', sa.INTEGER, primary_key=True),
    sa.Column('uid', sa.INTEGER),
    sa.Column('reg_id', sa.CHAR(256)),
)

if __name__ == '__main__':
    print(android_push.delete(android_push.c.uid.in_(["Mary", "sdf"])))
    print(android_push.insert({'uid': 12}))
    print(android_push.select().group_by(android_push.c.uid))
    print(select([android_push.c.uid]))
