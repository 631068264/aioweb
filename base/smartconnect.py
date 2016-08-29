#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author = 'wyx'
@time = 16/8/17 17:58
@annotation = '' 
"""
import asyncio
from datetime import datetime

import aiomysql
import weakref
from aiomysql import DictCursor

__all__ = [
    "MysqlConnection", "transaction", "lock_str",
    "ConnectionProxy", "init_pool", "get_conn"
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


def total_seconds(td):
    return td.days * 60 * 60 * 24 + td.seconds


def active_time(old_handler):
    async def new_handler(self, *args, **kwargs):
        self._last_active_time = datetime.now()
        ret = await old_handler(self, *args, **kwargs)
        self._last_active_time = datetime.now()
        return ret

    return new_handler


def ready(old_handler):
    def new_handler(self, *args, **kwargs):
        if self._conn is None and self.reusable:
            self.connect()
        return old_handler(self, *args, **kwargs)

    return new_handler


class ConnectionPool(object):
    def __init__(self, db_config, conn_cls, minsize=3, maxsize=10, maxidle=60, clean_interval=100):
        self._db_config = db_config
        self._conn_cls = conn_cls
        self._min = minsize
        self._max = maxsize
        self._maxidle = maxidle
        self._clean_interval = clean_interval

        self._pool = []
        self._clean_counter = 0

    @property
    def busy_array(self):
        return sorted(self._pool, key=(lambda v: v.idle))

    @property
    def idle_array(self):
        return sorted(self._pool, key=(lambda v: v.idle), reverse=True)

    @property
    def total(self):
        return len(self._pool)

    @property
    def idle(self):
        counter = 0
        for conn in self._pool:
            if weakref.getweakrefcount(conn) < 1:
                counter += 1
        return counter

    def _clean(self):
        self._clean_counter = 0

        if self.total <= self._min:
            log("clean: pool is not big enough [idle/total/min: %d/%d/%d]" % (self.idle, self.total, self._min))
            return

        if self.idle < 1:
            log("clean: no idle conn found [idle/total/min: %d/%d/%d]" % (self.idle, self.total, self._min))
            return

        total, found = (self.total - self._min), []
        for conn in self.idle_array:
            if conn.idle > self._maxidle:
                found.append(conn)
                if len(found) >= total:
                    break

        if len(found) < 1:
            log("clean: no idle conn found [idle/total/min: %d/%d/%d]" % (self.idle, self.total, self._min))
            return

        # remove which idle > maxidle
        for conn in found:
            self._pool.remove(conn)

        # do close
        for conn in found:
            safe_call(conn.close)

        log("clean: %d conns closed [idle/total/min: %d/%d/%d]" % (len(found), self.idle, self.total, self._min))

    async def get(self):
        # clean if need
        if self._clean_counter >= self._clean_interval:
            self._clean()

        self._clean_counter += 1

        if self.idle > 0:
            for conn in self.busy_array:
                if weakref.getweakrefcount(conn) > 0:
                    continue

                conn = weakref.proxy(conn)
                if not conn.ping():
                    await conn.connect()
                elif not conn.reusable:
                    conn.make_reusable()

                log("get: conn(%d) [idle/total/max: %d/%d/%d]" % (id(conn), self.idle, self.total, self._max))
                return conn
        elif self.total < self._max:
            conn = self._conn_cls(**self._db_config)
            self._pool.append(conn)
            await conn.connect()

            # dig the pool

            log("new: conn(%d) [idle/total/max: %d/%d/%d]" % (id(conn), self.idle, self.total, self._max))
            return conn

        return None


class MysqlConnection(object):
    def __init__(self, host="localhost", port=3306, db=None,
                 user=None, passwd="", charset="utf8"):
        # TODO:修改smartsql  framework
        self._config = {
            "host": host,
            "port": port,
            "db": db,
            "user": user,
            "password": passwd,
            "charset": charset,
            "autocommit": True,
        }

        self._conn = None
        self._locks = []
        self._in_trans = False
        self._last_active_time = None

    def __deepcopy__(self):
        return self

    @property
    def in_trans(self):
        return self._in_trans

    @property
    def has_lock(self):
        return len(self._locks) > 0

    @property
    def reusable(self):
        return not (self.in_trans or self.has_lock)

    @property
    def idle(self):
        if self._last_active_time is None:
            return 0

        nowtime = datetime.now()
        return total_seconds(nowtime - self._last_active_time)

    @active_time
    async def connect(self):
        """
            host="localhost", user=None, password="",
            db=None, port=3306,charset='',
            :return:
            """
        log("connect")
        self._conn = await aiomysql.connect(**self._config)

    def ping(self):
        if self._conn is None:
            return False
        return True

    def close(self):
        log("close")
        if self._conn is None:
            return
        try:
            self._conn.close()
        finally:
            self._conn = None

    def make_reusable(self):
        if self.in_trans:
            self.rollback()

        if self.has_lock:
            for key in self._locks:
                self.release(key)

    @ready
    @active_time
    async def select(self, sql, params=None, dict_cursor=False):
        # async with self._db.acquire() as conn:
        log("execute: %s - %r" % (sql, params))

        if dict_cursor:
            cursor = await self._conn.cursor(DictCursor)
        else:
            cursor = await self._conn.cursor()
        try:
            if params:
                await cursor.execute(sql, params)
            else:
                await cursor.execute(sql)

            return await cursor.fetchall()
        finally:
            await cursor.close()

    @ready
    @active_time
    async def insert(self, sql, params=None):
        # async with self._db.acquire() as conn:
        log("execute: %s - %r" % (sql, params))

        cursor = await self._conn.cursor()
        try:
            if params:
                await  cursor.execute(sql, params)
            else:
                await cursor.execute(sql)
            return cursor.lastrowid
        finally:
            await cursor.close()

    @ready
    @active_time
    async def execute(self, sql, params=None):
        # async with self._db.acquire() as conn:
        log("execute: %s - %r" % (sql, params))

        cursor = await self._conn.cursor()
        try:
            if params:
                await  cursor.execute(sql, params)
            else:
                await cursor.execute(sql)
        finally:
            await cursor.close()

    async def begin(self):
        await self.execute("BEGIN")
        self._in_trans = True

    async def rollback(self):
        await self.execute("ROLLBACK")
        self._in_trans = False

    async def commit(self):
        await self.execute("COMMIT")
        self._in_trans = False

    async def lock(self, key, timeout):
        locked = await self.select("SELECT GET_LOCK(%s, %s)", (key, timeout))

        if locked[0][0] == 1:
            self._locks.append(key)

        return locked

    async def release(self, key):

        released = await self.select("SELECT RELEASE_LOCK(%s)", (key,))

        if released[0][0] == 1 and key in self._locks:
            self._locks.remove(key)

        return released


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
        # TODO:重写方法
        self._conn = connection
        self._key = key
        self._timeout = timeout

    def __enter__(self):
        raise RuntimeError(
            'use "async with str_lock(conn,key, timeout) as locked" should be used as context manager expression')

    def __exit__(self, *args):
        pass

    @asyncio.coroutine
    def __aenter__(self):
        locked = yield from self._conn.lock()
        return locked

    @asyncio.coroutine
    def __aexit__(self, exc_type, exc_val, exc_tb):
        yield from self._conn.release()


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
        # TODO:重写方法
        # MysqlConnection.__init__(self, db=connection)
        self._conn = connection

    def __enter__(self):
        raise RuntimeError(
            'use "async with transaction(conn) as conn" should be used as context manager expression')

    def __exit__(self, *args):
        pass

    @asyncio.coroutine
    def __aenter__(self):
        yield from self._conn.begin()
        return self._conn

    @asyncio.coroutine
    def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_tb:
            yield from self._conn.rollback()
        else:
            yield from self._conn.commit()


# class MyConnection(object):
#     def __init__(self, minsize=3, maxsize=10, host="localhost", port=3306, db=None,
#                  user=None, passwd="", charset="utf8"):
#         self._config = {
#             # "minsize": minsize,
#             # "maxsize": maxsize,
#             "host": host,
#             "port": port,
#             "db": db,
#             "user": user,
#             "password": passwd,
#             "charset": charset,
#         }
#
#         self._conn = None
#
#     def __deepcopy__(self, memo):
#         return self
#
#     async def connect(self):
#         """
#         host="localhost", user=None, password="",
#         db=None, port=3306,charset='',
#         :return:
#         """
#         log("connect")
#         self._conn = await aiomysql.connect(**self._config)
#         self._conn.autocommit(True)
#         return self._conn


# ########## local storage ############

try:
    from thread import get_ident
except ImportError:
    from _thread import get_ident


class Local(object):
    def __init__(self):
        self._storage = {}

    @property
    def ident(self):
        return get_ident()

    @property
    def local_storage(self):
        return self._storage.setdefault(self.ident, {})

    def __getitem__(self, key):
        return self.local_storage[key]

    def __setitem__(self, key, value):
        self.local_storage[key] = value

    def get(self, key, default=None):
        return self.local_storage.get(key, default)

    def pop(self, key):
        return self.local_storage.pop(key)


class EmptyPoolError(Exception):
    pass


def safe_call(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except:
        pass


def lazy(db_name, local, name):
    async def wrap_func(*args, **kwargs):
        conn = local.get("conn")
        if conn is None:
            conn = get_conn(db_name)
            conn = await conn.get()
            if conn is None:
                raise EmptyPoolError()

        try:
            return getattr(conn, name)(*args, **kwargs)
        finally:
            if conn.reusable:
                safe_call(local.pop, "conn")
                del conn
            else:
                local["conn"] = conn

    return wrap_func


class ConnectionProxy(object):
    def __init__(self, db_name):
        self._db_name = db_name
        self._local = Local()

    @asyncio.coroutine
    def __getattr__(self, name):
        result = yield from lazy(self._db_name, self._local, name)
        return result


def get_conn(db_name):
    # TODO:每次都connect会有点奇怪
    return pools[db_name]


# init before concurrence
def init_pool(db_name, *args, **kwargs):
    pools[db_name] = ConnectionPool(*args, **kwargs)
