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
    "MyDBConnection", "transaction", "lock_str",
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


class MyDBConnection(object):
    """
    base db option
    """

    def __init__(self, db):
        self._db = db
        self._locks = []
        self._in_trans = False

    def __deepcopy__(self):
        return self

    async def select(self, sql, params=None, dict_cursor=False):
        async with self._db.acquire() as conn:
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

    async def insert(self, sql, params=None):
        async with self._db.acquire() as conn:
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

    async def execute(self, sql, params=None):
        async with self._db.acquire() as conn:
            log("execute: %s - %r" % (sql, params))

            cursor = await conn.cursor()
            try:
                if params:
                    await  cursor.execute(sql, params)
                else:
                    await cursor.execute(sql)
            finally:
                await cursor.close()


class lock_str(MyDBConnection):
    """
    Usage:
    It will release the lock finally
    >>>async with lock_str(conn,"lock",timeout) as locked:
    >>>      if not locked:
    >>>         # locked failed do sth
    >>>      do sth
    """

    def __init__(self, connection, key, timeout=0):
        MyDBConnection.__init__(self, db=connection)
        self._key = key
        self._timeout = timeout

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
        locked = await self.select("SELECT GET_LOCK(%s, %s)", (self._key, self._timeout))

        if locked[0][0] == 1:
            self._locks.append(self._key)

        return locked

    async def release(self):

        released = await self.select("SELECT RELEASE_LOCK(%s)", (self._key,))

        if released[0][0] == 1 and self._key in self._locks:
            self._locks.remove(self._key)

        return released


class transaction(MyDBConnection):
    """
    Usage:
        if "sth" makes any exception occurs, it will roolback
         nothing wrong , it will commit
     >>>async with transaction(conn) as conn:
     >>>    do sth
     >>>

    """

    def __init__(self, connection):
        MyDBConnection.__init__(self, db=connection)
        # self._conn = connection

    def __enter__(self):
        raise RuntimeError(
            'use "async with transaction(conn) as conn" should be used as context manager expression')

    def __exit__(self, *args):
        pass

    @asyncio.coroutine
    def __aenter__(self):
        yield from self.begin()
        return self._db

    @asyncio.coroutine
    def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_tb:
            yield from self.rollback()
        else:
            yield from self.commit()

    async def begin(self):
        await self.execute("BEGIN")
        self._in_trans = True

    async def rollback(self):
        await self.execute("ROLLBACK")
        self._in_trans = False

    async def commit(self):
        await self.execute("COMMIT")
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


# # ########## local storage ############
#
# try:
#     from thread import get_ident
# except ImportError:
#     from _thread import get_ident
#
#
# class Local(object):
#     def __init__(self):
#         self._storage = {}
#
#     @property
#     def ident(self):
#         return get_ident()
#
#     @property
#     def local_storage(self):
#         return self._storage.setdefault(self.ident, {})
#
#     def __getitem__(self, key):
#         return self.local_storage[key]
#
#     def __setitem__(self, key, value):
#         self.local_storage[key] = value
#
#     def get(self, key, default=None):
#         return self.local_storage.get(key, default)
#
#     def pop(self, key):
#         return self.local_storage.pop(key)
#
#
# class EmptyPoolError(Exception):
#     pass
#
#
# def safe_call(func, *args, **kwargs):
#     try:
#         return func(*args, **kwargs)
#     except:
#         pass
#
#
# def lazy(db_name, local, name):
#     def wrap_func(*args, **kwargs):
#         conn = local.get("conn")
#         if conn is None:
#             conn = get_conn(db_name)
#             if conn is None:
#                 raise EmptyPoolError()
#
#         try:
#             return getattr(conn, name)(*args, **kwargs)
#         finally:
#             if conn.reusable:
#                 safe_call(local.pop, "conn")
#                 del conn
#             else:
#                 local["conn"] = conn
#
#     return wrap_func
#
#
# class ConnectionProxy(object):
#     def __init__(self, db_name):
#         self._db_name = db_name
#         self._local = Local()
#
#     def __getattr__(self, name):
#         return lazy(self._db_name, self._local, name)


async def get_conn(db_name):
    # TODO:每次都connect会有点奇怪
    return await pools[db_name].connect()


# init before concurrence
def init_pool(db_name, *args, **kwargs):
    pools[db_name] = MyConnection(*args, **kwargs)
