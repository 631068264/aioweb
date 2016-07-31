#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author = 'wyx'
@time = 16/7/31 11:19
@annotation = '' 
"""
import sqlalchemy as sa

metadata = sa.MetaData()

android_push = sa.Table(
    'android_push',
    metadata,
    sa.Column('uid', sa.Integer, primary_key=True),
    sa.Column('reg_id', sa.CHAR(256)),
    sa.Column('name', sa.CHAR(40)),
)

if __name__ == '__main__':
    print(android_push.delete(android_push.c.uid.in_(["Mary", "sdf"])))
    print(android_push.select(android_push.c.uid).where(android_push.c.name.in_(['Mary', 'Susan'])))
    print(android_push.insert({'uid': 12}))
