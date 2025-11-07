import aiohttp
import asyncio

from adapters.inosmi_ru import sanitize


async def fetch(session, url):
    async with session.get(url) as response:
        response.raise_for_status()
        return await response.text()


async def main():
    url = 'https://inosmi.ru/20251106/evropa-275505851.html'
    async with aiohttp.ClientSession() as session:
        html = await fetch(session, url)
        text = sanitize(html, plaintext=False)
        print(text)


asyncio.run(main())
