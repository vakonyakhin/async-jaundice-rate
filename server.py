from aiohttp import web, ClientSession
from functools import partial
from anyio import create_task_group

from main import proccess_articles, read_charged_words_from_zip
import pymorphy2


async def handle(request):

    urls_param = request.query.get('urls')
    urls_list = []
    results = []

    session = request.app['client_session']
    morph = request.app['morph']
    charged_words = request.app['charged_words']

    if not urls_param:
        return web.json_response({"error": "Параметр 'urls' обязателен"}, status=400)

    urls_list = [url.strip() for url in urls_param.split(',') if url.strip()]
    if len(urls_list) > 10:
        return web.json_response({"error": "too many urls in request, should be 10 or less"}, status=400)

    process_one_article = partial(
        proccess_articles,
        session, morph,
        charged_words
        )

    async def process_and_collect(url):
        result = await process_one_article(url=url)
        results.append(result)

    async with create_task_group() as tg:
        for url in urls_list:
            tg.start_soon(process_and_collect, url)

    response_data = []
    for url, score, words_count, status, load_time in results:
        response_data.append({
            "url": url,
            "status": status,
            "score": score,
            "words_count": words_count,
            "load_time": f"{load_time:.2f}"
        })

    return web.json_response(response_data)


async def on_startup(app):
    app['client_session'] = ClientSession()
    app['morph'] = pymorphy2.MorphAnalyzer()
    app['charged_words'] = read_charged_words_from_zip()


async def on_cleanup(app):
    await app['client_session'].close()

if __name__ == '__main__':
    app = web.Application()
    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)
    app.add_routes([web.get('/', handle)])
    web.run_app(app)
