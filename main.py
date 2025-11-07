import aiohttp
import asyncio
import aiofiles

import pymorphy2
import zipfile

from adapters.inosmi_ru import sanitize
from text_tools import split_by_words, calculate_jaundice_rate


async def fetch(session, url):
    async with session.get(url) as response:
        response.raise_for_status()
        return await response.text()


def read_charged_words_from_zip(zip_filepath='charged_dict.zip', encoding='utf-8'):

    words = []
    try:
        with zipfile.ZipFile(zip_filepath, 'r') as zip_ref:
            for filename in zip_ref.namelist():
                # Skip directories and hidden files
                if not filename.endswith('/') and not filename.startswith('__'):
                    with zip_ref.open(filename, 'r') as file_in_zip:
                        for line in file_in_zip:
                            words.append(line.decode(encoding).strip())
    except FileNotFoundError:
        print(f"Error: Zip archive '{zip_filepath}' not found.")
    except zipfile.BadZipFile:
        print(f"Error: Zip archive '{zip_filepath}' is corrupted.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    return words


async def main():
    morph = pymorphy2.MorphAnalyzer()
    charged_words = read_charged_words_from_zip()

    url = 'https://inosmi.ru/20251106/evropa-275505851.html'
    async with aiohttp.ClientSession() as session:
        html = await fetch(session, url)
        text = sanitize(html, plaintext=True)
        words = split_by_words(morph, text)
        rate = calculate_jaundice_rate(words, charged_words)
        print(rate)


asyncio.run(main())
