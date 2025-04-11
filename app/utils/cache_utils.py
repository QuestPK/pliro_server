from typing import Optional, List
from fastapi_cache import FastAPICache


class CacheManager:

    @staticmethod
    def _get_cache_prefix():
        return "fastapi-cache:"

    @classmethod
    async def get_client(cls):
        return FastAPICache.redis

    @classmethod
    def generate_key(cls, endpoint: str, params: Optional[dict] = None):
        prefix = cls._get_cache_prefix()
        key = f"{prefix}{endpoint}"

        if params:
            query_params = "&".join([f"{k}={v}" for k, v in params.items() if v is not None])
            if query_params:
                key += f"?{query_params}"

        return key

    @classmethod
    async def invalidate_keys(cls, keys: List[str]):
        if not keys:
            return

        try:
            client = await cls.get_client()
            await client.delete(*keys)
        except Exception as e:
            print(f"Error invalidating cache keys: {e}")

    @classmethod
    async def invalidate_by_pattern(cls, pattern: str):
        try:
            client = await cls.get_client()
            prefix = cls._get_cache_prefix()
            full_pattern = f"{prefix}{pattern}"

            keys = await client.keys(full_pattern)
            if keys:
                await client.delete(*keys)
        except Exception as e:
            print(f"Error invalidating cache by pattern: {e}")

    @classmethod
    async def invalidate_endpoint(cls, endpoint: str):
        pattern = f"{endpoint}*"
        await cls.invalidate_by_pattern(pattern)

    @classmethod
    async def set_cache(cls, key: str, value, expire: int = 60):
        try:
            client = await cls.get_client()
            await client.set(key, value, expire=expire)
        except Exception as e:
            print(f"Error setting cache: {e}")

    @classmethod
    async def get_cache(cls, key: str):
        try:
            client = await cls.get_client()
            return await client.get(key)
        except Exception as e:
            print(f"Error getting cache: {e}")
            return None


# STANDARD CACHE UTILITY FUNCTIONS

async def invalidate_standards_list_cache():
    """Invalidate all cached standards list pages."""
    await CacheManager.invalidate_endpoint("list_standards")


async def invalidate_standard_detail_cache(standard_id: int):
    """Invalidate cache for a specific standard detail."""
    key = get_standard_detail_cache_key(standard_id)
    await CacheManager.invalidate_keys([key])


def get_standards_list_cache_key(page: int = 0, page_size: int = 100, approval_status: Optional[str] = None):
    """Generate cache key for standards list endpoint."""
    params = {
        "page": page,
        "pageSize": page_size,
        "approval_status": approval_status
    }
    return CacheManager.generate_key("list_standards", params)


def get_standard_detail_cache_key(standard_id: int):
    """Generate cache key for standard detail endpoint."""
    return CacheManager.generate_key(f"get_standard:{standard_id}")


