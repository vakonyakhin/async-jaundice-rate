import aiohttp
import asyncio

import pymorphy2

from adapters.inosmi_ru import sanitize
from text_tools import split_by_words, calculate_jaundice_rate


async def fetch(session, url):
    async with session.get(url) as response:
        response.raise_for_status()
        return await response.text()


async def main():
    morph = pymorphy2.MorphAnalyzer()

    url = 'https://inosmi.ru/20251106/evropa-275505851.html'
    async with aiohttp.ClientSession() as session:
        html = await fetch(session, url)
        text = sanitize(html, plaintext=True)
        words = split_by_words(morph, text)
        charged_words = ['есть', 'полный', 'право','россия','запад', 'это']
        rate = calculate_jaundice_rate(words, charged_words)
        print(rate)


asyncio.run(main())
