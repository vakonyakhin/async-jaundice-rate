import aiohttp
import asyncio
from functools import lru_cache
import time
from enum import Enum
from functools import lru_cache, wraps, partial
import contextlib

import pytest
import pymorphy2
import zipfile
from anyio import create_task_group
from adapters.exceptions import ArticleNotFound
from async_timeout import timeout

from adapters.inosmi_ru import sanitize
from text_tools import split_by_words, calculate_jaundice_rate


pytest_plugins = ('pytest_asyncio')

TEST_ARTICLES = ['https://inosmi.ru/20251106/grem-275508043.html',
                 'https://inosmi.ru/20251107/norvegiya-275513596.html,',
                 'https://inosmi.ru/20251107/mindich-275512408.html',
                 'https://inosmi.ru/20251107/borba-275515286.html',
                 'https://inosmi.ru/20251107/konflikt-275516176.html',
                 'https://inosmi.ru/20251107/kurily-275519675.html',
                 'https://inosmi.ru/20251107/evropa_kitay-275523452.html',
                 'https://inosmi.ru/20251107/germaniya-275518854.html',
                 'https://inosmi.ru/20251107/germaniya-275520710.html',
                 'https://lenta.ru/brief/2021/08/26/afg_terror/'
                 ]


class ProcessingStatus(Enum):
    OK = 'OK'
    FETCH_ERROR = 'FETCH_ERROR'
    PARSING_ERROR = 'PARSING_ERROR'
    TIMEOUT = 'TIMEOUT'


def timer(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = await func(*args, **kwargs)
        end_time = time.perf_counter()
        timer = round(end_time - start_time, 2)
        # for result in results:
        #     print_result(*result)
        print(f'Анализ закончен за {timer} секунд\n')
        return result
    return wrapper


async def fetch(session, url):
    async with session.get(url) as response:
        response.raise_for_status()
        return await response.text()


@lru_cache(maxsize=None)
def read_charged_words_from_zip(zip_filepath='charged_dict.zip', encoding='utf-8'):

    words = set()
    try:
        with zipfile.ZipFile(zip_filepath, 'r') as zip_ref:
            for filename in zip_ref.namelist():
                # Skip directories and hidden files
                if not filename.endswith('/') and not filename.startswith('__'):
                    with zip_ref.open(filename, 'r') as file_in_zip:
                        for line in file_in_zip:
                            words.add(line.decode(encoding).strip())
    except FileNotFoundError:
        print(f"Error: Zip archive '{zip_filepath}' not found.")
    except zipfile.BadZipFile:
        print(f"Error: Zip archive '{zip_filepath}' is corrupted.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    return words


@contextlib.asynccontextmanager
async def timer():
    container = {
        'elapsed_time' : 0.00
    }
    old_time = time.monotonic()
    try:
        yield container
    finally:
        new_time = time.monotonic()
        container['elapsed_time'] = new_time - old_time


def print_result(url, score, words_count, status, load_time):
    print(f'URL: {url}')
    print(f'Статус: {status}')
    print(f'Рейтинг: {score}')
    print(f'Слов в статье: {words_count}')
    print(f'Анализ закончен за {load_time:.2f} секунд\n')


async def proccess_articles(session, morph, charged_words, url):
    score = None
    words_count = None
    elapsed_time = 0.00 
    try:
        async with timeout(3):
            async with timer() as container:
                html = await fetch(session, url)
                text = sanitize(html, plaintext=True)
                words = split_by_words(morph, text)
                words_count = len(words)
                score = calculate_jaundice_rate(words, charged_words)
                status = ProcessingStatus.OK.value
            elapsed_time = container['elapsed_time'] 
    except aiohttp.ClientResponseError:
            status = ProcessingStatus.FETCH_ERROR.value

    except ArticleNotFound:
            status = ProcessingStatus.PARSING_ERROR.value

    except asyncio.exceptions.TimeoutError:
            status = ProcessingStatus.TIMEOUT.value

    return url, score, words_count, status, elapsed_time


@pytest.fixture(scope="module")
def morph():
    return pymorphy2.MorphAnalyzer()


@pytest.fixture(scope="module")
def charged_words():
    return read_charged_words_from_zip()


@pytest.mark.asyncio
@pytest.mark.parametrize("test_url,expected_status,check_score_words", [

    ('https://inosmi.ru/economic/20190629/245384784.html', ProcessingStatus.OK.value, True),

    ('https://inosmi.ru/not-existing-page.html', ProcessingStatus.FETCH_ERROR.value, False),

    ('http://example.com', ProcessingStatus.PARSING_ERROR.value, False),
])
async def test_proccess_articles(morph, charged_words, test_url, expected_status, check_score_words):

    async with aiohttp.ClientSession() as session:
        url, score, words_count, status, elapsed_time = await proccess_articles(session, morph, charged_words, test_url)

        assert status == expected_status
        assert elapsed_time >= 0

        if check_score_words:
            assert score is not None
            assert words_count is not None
        else:
            assert score is None
            assert words_count is None


@pytest.mark.asyncio
async def test_proccess_articles_timeout(morph, charged_words):

    async with aiohttp.ClientSession() as session:
        url, score, words_count, status, elapsed_time = await proccess_articles(session, morph, charged_words, url='https://inosmi.ru/economic/20190629/245384784.html')
        assert status == ProcessingStatus.TIMEOUT.value


async def main():

    morph = pymorphy2.MorphAnalyzer()
    charged_words = read_charged_words_from_zip()

    async with aiohttp.ClientSession() as session:

        process_one_article = partial(proccess_articles, session, morph, charged_words)
        tasks = [process_one_article(url=url) for url in TEST_ARTICLES]
        results = await asyncio.gather(*tasks)

    for result in results:
        print_result(*result)


if __name__ == '__main__':
    asyncio.run(main())
