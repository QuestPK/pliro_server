import os

from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, AsyncEngine
from sqlalchemy.orm import sessionmaker
from fastapi_limiter import FastAPILimiter
import redis.asyncio as redis
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend

# Async SQLAlchemy Engine
async_engine: AsyncEngine = create_async_engine(
    os.getenv("DATABASE_URL", ""),  # Add a default empty string to prevent None
    echo=True,  # Consider setting this via environment variable
)

# Async Session Maker
AsyncSessionLocal = sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)


# Redis and Rate Limiting
async def init_redis():
    """
    Initialize Redis for caching and rate limiting.

    Returns:
        Redis client for further use if needed.
    """
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        raise ValueError("REDIS_URL environment variable is not set")

    try:
        redis_client = redis.from_url(
            redis_url,
            encoding="utf8",
            decode_responses=True
        )

        # Initialize rate limiting
        await FastAPILimiter.init(redis_client)

        # Initialize caching
        await FastAPICache.init(RedisBackend(redis_client), prefix="fastapi-cache:")

        return redis_client
    except Exception as e:
        print(f"Error initializing Redis: {e}")
        raise


# Dependency for database sessions
async def get_db() -> AsyncSession:
    """
    Dependency to get a database session.

    Yields:
        An async SQLAlchemy session that will be closed after use.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()



async def create_database_if_not_exists(async_engine: AsyncEngine):
    """
    Ensure the database exists before running migrations.
    """
    try:
        async with async_engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        print("Database already exists.")
    except OperationalError:
        async with async_engine.begin() as conn:
            await conn.execute(text("CREATE DATABASE pliro_db"))
        print("Database created successfully.")
