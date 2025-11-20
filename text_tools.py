import pymorphy2
import string
import asyncio
from async_timeout import timeout

import pytest


pytest_plugins = ('pytest_asyncio')


def _clean_word(word):
    word = word.replace('«', '').replace('»', '').replace('…', '')
    # FIXME какие еще знаки пунктуации часто встречаются ?
    word = word.strip(string.punctuation)
    return word


async def split_by_words(morph, text):
    """Учитывает знаки пунктуации, регистр и словоформы, выкидывает предлоги."""
    # The timeout is now controlled by the caller.
    words = []
    try:
        async with timeout(3):
            for word in text.split():
                cleaned_word = _clean_word(word)
                normalized_word = morph.parse(cleaned_word)[0].normal_form
                if len(normalized_word) > 2 or normalized_word == 'не':
                    words.append(normalized_word)
                await asyncio.sleep(0)
    except asyncio.exceptions.TimeoutError:
        words = []
        raise asyncio.exceptions.TimeoutError

    return words


@pytest.fixture(scope="module")
# Экземпляры MorphAnalyzer занимают 10-15Мб RAM т.к. загружают в память много данных
# Старайтесь организовать свой код так, чтоб создавать экземпляр MorphAnalyzer заранее и в единственном числе
def morph():
    return pymorphy2.MorphAnalyzer()

@pytest.fixture(scope="module")
def text():
    with open('test.txt', 'r', encoding='utf-8') as file:
        text = file.read()
    return text

@pytest.mark.asyncio
async def test_split_by_words(morph):

    assert await split_by_words(morph, 'Во-первых, он хочет, чтобы') == ['во-первых', 'хотеть', 'чтобы']

    assert await split_by_words(morph, '«Удивительно, но это стало началом!»') == ['удивительно', 'это', 'стать', 'начало']

@pytest.mark.asyncio
async def test_split_by_words_timeout(morph, text):
    words = []
    with pytest.raises(asyncio.TimeoutError):
        await split_by_words(morph, text)

    assert words == []


def calculate_jaundice_rate(article_words, charged_words):
    """Расчитывает желтушность текста, принимает список "заряженных" слов и ищет их внутри article_words."""

    if not article_words:
        return 0.0

    found_charged_words = [word for word in article_words if word in set(charged_words)]

    score = len(found_charged_words) / len(article_words) * 100

    return round(score, 2)


def test_calculate_jaundice_rate():
    assert -0.01 < calculate_jaundice_rate([], []) < 0.01
    assert 33.0 < calculate_jaundice_rate(['все', 'аутсайдер', 'побег'], ['аутсайдер', 'банкротство']) < 34.0
