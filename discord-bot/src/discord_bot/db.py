import asyncpg


class Database:
    def __init__(self, url: str):
        self._url = url
        self.pool: asyncpg.Pool | None = None

    async def start(self) -> None:
        self.pool = await asyncpg.create_pool(self._url, min_size=1, max_size=5)

    async def stop(self) -> None:
        if self.pool is not None:
            await self.pool.close()
