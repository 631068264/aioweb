#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author = 'wyx'
@time = 16/8/12 17:19
@annotation = '' 
"""

# from pymysql.connections import dump_packet
import asyncio

import aiomysql
from aiomysql.utils import _ContextManager, PY_35, _PoolAcquireContextManager, _PoolContextManager

query_log = None
echo = False
pools = {}


def transaction(connection):
    return TransactionContextManager(connection)


class TransactionContextManager(_ContextManager):
    if PY_35:
        @asyncio.coroutine
        def __aexit__(self, exc_type, exc_val, exc_tb):
            if exc_type:
                yield from self._obj.rollback()
            elif self._obj._in_trans:
                yield from self._obj.commit()
            self._obj = None


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
        self._in_trans = False
        self._logger = query_log
        self._pool = None
        self._conn = None
        self._locks = []

    def log(self, msg):
        if self._logger is None:
            return
        self._logger(msg)

    async def connect(self):
        """
        host="localhost", user=None, password="",
        db=None, port=3306,charset='',
        :return:
        """
        self.log("connect")
        self._pool = await aiomysql.create_pool(**self._config)
        self._conn = await self._pool.acquire()
        try:
            core = Engine(self._pool)
            return await _PoolContextManager(core)
        finally:
            self._pool.release(self._conn)

    # ############# base db option #############

    async def select(self, sql, params=None, cursor=None):
        self.log("execute: %s - %r" % (sql, params))

        cursor = await self._pool.cursor(cursor)
        if params:
            await  cursor.execute(sql, params)
        await cursor.execute(sql)

        await cursor.close()
        return cursor.fetchall()

    async def insert(self, sql, params=None):
        self.log("execute: %s - %r" % (sql, params))

        cursor = await self._pool.cursor()
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

        cursor = await self._pool.cursor()
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


class Transaction(object):
    def __init__(self, pool, engine):
        self._engine = engine
        self._pool = pool
        self._in_trans = False
        self._logger = query_log
        self._locks = []

    def log(self, msg):
        if self._logger is None:
            return
        self._logger(msg)

    # ############# base db option #############

    async def select(self, sql, params=None, cursor=None):
        self.log("execute: %s - %r" % (sql, params))

        cursor = await self._pool.cursor(cursor)
        if params:
            await  cursor.execute(sql, params)
        await cursor.execute(sql)

        await cursor.close()
        return cursor.fetchall()

    async def insert(self, sql, params=None):
        self.log("execute: %s - %r" % (sql, params))

        cursor = await self._pool.cursor()
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

        cursor = await self._pool.cursor()
        try:
            if params:
                await  cursor.execute(sql, params)
            await cursor.execute(sql)
        finally:
            await cursor.close()

    # ############## transaction #############
    def begin(self):
        coro = self._begin()
        return TransactionContextManager(coro)

    async def _begin(self):
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


class Engine(object):
    def __init__(self, pool):
        self._pool = pool

    def close(self):
        """Close engine.

        Mark all engine connections to be closed on getting back to pool.
        Closed engine doesn't allow to acquire new connections.
        """
        self._pool.close()

    def terminate(self):
        """Terminate engine.

        Terminate engine pool with instantly closing all acquired
        connections also.
        """
        self._pool.terminate()

    @asyncio.coroutine
    def wait_closed(self):
        """Wait for closing all engine's connections."""
        yield from self._pool.wait_closed()

    def acquire(self):
        """Get a connection from pool."""
        coro = self._acquire()
        return _PoolAcquireContextManager(coro, self)

    @asyncio.coroutine
    def _acquire(self):
        raw = yield from self._pool.acquire()
        conn = Transaction(raw, self)
        return conn

    def release(self, conn):
        """Revert back connection to pool."""
        if conn.in_transaction:
            raise Exception("Cannot release a connection with "
                            "not finished transaction")
        raw = conn.connection
        return self._pool.release(raw)

    def __enter__(self):
        raise RuntimeError(
            '"yield from" should be used as context manager expression')

    def __exit__(self, *args):
        # This must exist because __enter__ exists, even though that
        # always raises; that's how the with-statement works.
        pass  # pragma: nocover

    def __iter__(self):
        # This is not a coroutine.  It is meant to enable the idiom:
        #
        #     with (yield from engine) as conn:
        #         <block>
        #
        # as an alternative to:
        #
        #     conn = yield from engine.acquire()
        #     try:
        #         <block>
        #     finally:
        #         engine.release(conn)
        conn = yield from self.acquire()
        return _ConnectionContextManager(self, conn)

    if PY_35:  # pragma: no branch
        @asyncio.coroutine
        def __aenter__(self):
            return self

        @asyncio.coroutine
        def __aexit__(self, exc_type, exc_val, exc_tb):
            self.close()
            yield from self.wait_closed()


class _ConnectionContextManager:
    """Context manager.

    This enables the following idiom for acquiring and releasing a
    connection around a block:

        with (yield from engine) as conn:
            cur = yield from conn.cursor()

    while failing loudly when accidentally using:

        with engine:
            <block>
    """

    __slots__ = ('_engine', '_conn')

    def __init__(self, engine, conn):
        self._engine = engine
        self._conn = conn

    def __enter__(self):
        assert self._conn is not None
        return self._conn

    def __exit__(self, *args):
        try:
            self._engine.release(self._conn)
        finally:
            self._engine = None
            self._conn = None


async def getconn(db_name):
    return await pools[db_name].connect()


# init before concurrence
def init_pool(db_name, *args, **kwargs):
    pools[db_name] = MyConnection(*args, **kwargs)


if __name__ == "__main__":
    pass
