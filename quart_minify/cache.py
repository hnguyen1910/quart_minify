from abc import ABCMeta, abstractmethod

from quart_minify.utils import get_optimized_hashing


class CacheBase(metaclass=ABCMeta):
    def __init__(self, store_key_getter=None):
        self.store_key_getter = store_key_getter

    @abstractmethod
    async def get(self, key):
        pass

    @abstractmethod
    async def set(self, key, value):
        pass

    @abstractmethod
    async def get_or_set(self, key, getter):
        pass

    @abstractmethod
    def clear(self):
        pass


class MemoryCache(CacheBase):
    def __init__(self, store_key_getter=None, limit=0):
        super().__init__(store_key_getter)
        self.limit = limit
        self.hashing = get_optimized_hashing()
        self._cache = {}
        
    async def store(self):
        if self.store_key_getter:
            return self._cache.setdefault(await self.store_key_getter(), {})

        return self._cache

    async def limit_exceeded(self):
        return len(await self.store()) >= self.limit

    async def get(self, key):
        return (await self.store()).get(key)

    async def set(self, key, value):
        if (await self.limit_exceeded()):
            (await self.store()).popitem()

        (await self.store()).update({key: value})

    async def get_or_set(self, key, getter):
        if self.limit == 0:
            return getter()

        hashed_key = self.hashing(key.encode("utf-8")).hexdigest()

        if not (await self.get(hashed_key)):
            await self.set(hashed_key, getter())

        return await self.get(hashed_key)

    def clear(self):
        del self._cache
        self._cache = {}
