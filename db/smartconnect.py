#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author = 'wyx'
@time = 16/8/17 17:58
@annotation = '' 
"""
import asyncio

query_log = None
echo = False


class transaction(object):
    def __init__(self, connection, loop=None):
        self._conn = connection
        self._logger = query_log
        self._loop = loop if loop else asyncio.get_event_loop()
        self._in_trans = False
        self._cursor = None
        self._locks = []

    def log(self, msg):
        if self._logger is None:
            return
        self._logger(msg)

    def __enter__(self):
        raise RuntimeError(
            'use "async with transaction(conn) as conn" should be used as context manager expression')

    def __exit__(self, *args):
        pass

    @asyncio.coroutine
    def __aenter__(self):
        yield from self.begin()
        return self._conn

    @asyncio.coroutine
    def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_tb:
            yield from self.rollback()
        else:
            yield from self.commit()

    # ############# base db option #############

    async def select(self, sql, params=None, cursor=None):
        self.log("execute: %s - %r" % (sql, params))

        cursor = await self._conn.cursor(cursor)
        if params:
            await  cursor.execute(sql, params)
        await cursor.execute(sql)

        await cursor.close()
        return cursor.fetchall()

    async def insert(self, sql, params=None):
        self.log("execute: %s - %r" % (sql, params))

        cursor = await self._conn.cursor()
        try:
            if params:
                await  cursor.execute(sql, params)
            await cursor.execute(sql)
            return cursor.lastrowid
        finally:
            await cursor.close()
            return cursor.lastrowid

    async def execute(self, sql, params=None):
        self.log("execute: %s - %r" % (sql, params))

        cursor = await self._conn.cursor()
        try:
            if params:
                await  cursor.execute(sql, params)
            await cursor.execute(sql)
        finally:
            await cursor.close()

    # ############## transaction #############
    async def begin(self):
        await self.execute("BEGIN")
        self._in_trans = True

    async def rollback(self):
        await self.execute("ROLLBACK")
        self._in_trans = False

    async def commit(self):
        await self.execute("COMMIT")
        self._in_trans = False

    async def lock(self, key, timeout=0):

        # TODO:[0][0]
        locked = await self.select("SELECT GET_LOCK(%s, %s)", (key, timeout))[0][0] == 1

        if locked:
            self._locks.append(key)

        return locked

    async def release(self, key):
        released = await self.select("SELECT RELEASE_LOCK(%s)", (key,))[0][0] == 1

        if released and key in self._locks:
            self._locks.remove(key)

        return released
