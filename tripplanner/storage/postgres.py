from pathlib import Path

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from tripplanner.config import Settings

SCHEMA_PATH = Path(__file__).with_name("schema.sql")


class PostgresDatabase:
    def __init__(self, settings: Settings) -> None:
        if settings.database_url is None:
            raise ValueError("DATABASE_URL is required for PostgreSQL storage")
        self._pool = AsyncConnectionPool(
            conninfo=settings.database_url.get_secret_value(),
            kwargs={"row_factory": dict_row},
            open=False,
            min_size=1,
            max_size=10,
        )

    async def open(self) -> None:
        await self._pool.open()
        await self._pool.wait()

    async def close(self) -> None:
        await self._pool.close()

    async def health_check(self) -> bool:
        async with self._pool.connection() as connection:
            await connection.execute("SELECT 1")
        return True

    @property
    def pool(self) -> AsyncConnectionPool:
        return self._pool


async def initialize_schema(database: PostgresDatabase) -> None:
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    async with database.pool.connection() as connection:
        async with connection.transaction():
            for statement in schema.split(";"):
                if statement.strip():
                    await connection.execute(statement)
