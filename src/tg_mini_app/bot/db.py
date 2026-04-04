from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from tg_mini_app.db.session import create_engine, create_sessionmaker


class Db:
    def __init__(self) -> None:
        engine = create_engine()
        self._session_factory: async_sessionmaker[AsyncSession] = create_sessionmaker(
            engine
        )

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        async with self._session_factory() as s:
            yield s

