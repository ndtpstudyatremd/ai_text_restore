import asyncio
from aiogram import BaseMiddleware
from aiogram.types import Message

class AlbumMiddleware(BaseMiddleware):
    def __init__(self, latency: float = 0.5):
        self.latency = latency
        self.storage = {}
        super().__init__()

    async def __call__(self, handler, event: Message, data: dict):
        if not event.media_group_id:
            data["album"] = [event]
            return await handler(event, data)

        mid = event.media_group_id
        if mid not in self.storage:
            self.storage[mid] = []
            data["album"] = self.storage[mid]
            self.storage[mid].append(event)
            await asyncio.sleep(self.latency)
            await handler(event, data)
            self.storage.pop(mid, None)
        else:
            self.storage[mid].append(event)
