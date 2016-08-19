#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author = 'wyx'
@time = 16/8/17 17:58
@annotation = '' 
"""
import asyncio

import aiomysql
from aiomysql import DictCursor

__all__ = [
    "db_op", "transaction", "lock_str",
    "MyConnection", "init_pool", "get_conn"
]
query_log = None
query_echo = False  # help you watch the log in console when you debug
pools = {}


def log(msg):
    if query_echo:
        print(msg)
    if query_log is None:
        return
    query_log(msg)


class db_op(object):
    """
    base db option
    """

    @staticmethod
    async def select(conn, sql, params=None, dict_cursor=False):
        log("execute: %s - %r" % (sql, params))

        if dict_cursor:
            cursor = await conn.cursor(DictCursor)
        else:
            cursor = await conn.cursor()
        try:
            if params:
                await cursor.execute(sql, params)
            else:
                await cursor.execute(sql)

            return await cursor.fetchall()
        finally:
            await cursor.close()

    @staticmethod
    async def insert(conn, sql, params=None):
        log("execute: %s - %r" % (sql, params))

        cursor = await conn.cursor()
        try:
            if params:
                await  cursor.execute(sql, params)
            else:
                await cursor.execute(sql)
            return cursor.lastrowid
        finally:
            await cursor.close()

    @staticmethod
    async def execute(conn, sql, params=None):
        log("execute: %s - %r" % (sql, params))

        cursor = await conn.cursor()
        try:
            if params:
                await  cursor.execute(sql, params)
            else:
                await cursor.execute(sql)
        finally:
            await cursor.close()


class lock_str(object):
    """
    Usage:
    It will release the lock finally
    >>>async with lock_str(conn,"lock",timeout) as locked:
    >>>      if not locked:
    >>>         # locked failed do sth
    >>>      do sth
    """

    def __init__(self, connection, key, timeout=0):
        self._conn = connection
        self._key = key
        self._timeout = timeout
        self._locks = []

    def __enter__(self):
        raise RuntimeError(
            'use "async with str_lock(conn,key, timeout) as locked" should be used as context manager expression')

    def __exit__(self, *args):
        pass

    @asyncio.coroutine
    def __aenter__(self):
        locked = yield from self.lock()
        return locked

    @asyncio.coroutine
    def __aexit__(self, exc_type, exc_val, exc_tb):
        yield from self.release()

    async def lock(self):
        locked = await db_op.select(self._conn, "SELECT GET_LOCK(%s, %s)", (self._key, self._timeout))

        if locked[0][0] == 1:
            self._locks.append(self._key)

        return locked

    async def release(self):

        released = await db_op.select(self._conn, "SELECT RELEASE_LOCK(%s)", (self._key,))

        if released[0][0] == 1 and self._key in self._locks:
            self._locks.remove(self._key)

        return released


class transaction(object):
    """
    Usage:
        if "sth" makes any exception occurs, it will roolback
         nothing wrong , it will commit
     >>>async with transaction(conn) as conn:
     >>>    do sth
     >>>

    """

    def __init__(self, connection):
        self._conn = connection
        self._in_trans = False
        self._locks = []

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

    async def begin(self):
        await db_op.execute(self._conn, "BEGIN")
        self._in_trans = True

    async def rollback(self):
        await db_op.execute(self._conn, "ROLLBACK")
        self._in_trans = False

    async def commit(self):
        await db_op.execute(self._conn, "COMMIT")
        self._in_trans = False


class MyConnection(object):
    def __init__(self, minsize=3, maxsize=10, host="localhost", port=3306, db=None,
                 user=None, passwd="", charset="utf8", autocommit=True):
        self._config = {
            "minsize": minsize,
            "maxsize": maxsize,
            "host": host,
            "port": port,
            "db": db,
            "user": user,
            "password": passwd,
            "charset": charset,
            "autocommit": autocommit,
        }

        self._pool = None

    async def connect(self):
        """
        host="localhost", user=None, password="",
        db=None, port=3306,charset='',
        :return:
        """
        log("connect")
        self._pool = await aiomysql.create_pool(**self._config)
        return self._pool


async def get_conn(db_name):
    # TODO:每次都connect会有点奇怪
    return await pools[db_name].connect()


# init before concurrence
def init_pool(db_name, *args, **kwargs):
    pools[db_name] = MyConnection(*args, **kwargs)
