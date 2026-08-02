import logging
import pathlib

import aiosqlite
import yoyo

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
_logger = logging.getLogger(__name__)

MIGRATIONS_DIR = pathlib.Path(__file__).parent / "migrations"

class Database:
    def __init__(self, path: pathlib.Path):
        self._path = path
        self._connection: aiosqlite.Connection | None = None

    @property
    def connection(self) -> aiosqlite.Connection:
        if self._connection is None:
            raise RuntimeError("Database has not been connected")
        return self._connection

    async def start(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)

        connection = await aiosqlite.connect(self._path)
        connection.row_factory = aiosqlite.Row

        await connection.execute("PRAGMA journal_mode = WAL")
        await connection.execute("PRAGMA foreign_keys = ON")
        await connection.execute("PRAGMA busy_timeout = 5000")
        await connection.commit()

        self._connection = connection
        self._run_migrations()

    async def stop(self) -> None:
        if self._connection is not None:
            await self._connection.close()
            self._connection = None

    def _run_migrations(self):
        backend = yoyo.get_backend(f"sqlite:///{self._path}")
        migrations = yoyo.read_migrations(str(MIGRATIONS_DIR))

        with backend.lock():
            backend.apply_migrations(backend.to_apply(migrations))

        _logger.info(f"Database schema updated to {migrations[-1].id}")
