import sys
import time
import math
import threading
import logging

from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport
from ini import *
from cookies import get_cookies, get_cookies_from_client
from retry import retry

logging.basicConfig()
logging.getLogger().setLevel(logging.INFO)
logging.getLogger("gql.transport.requests").setLevel(logging.ERROR)

if REQUESTS_DEBUG:
    try:
        import http.client as http_client
    except ImportError:
        import httplib as http_client
    http_client.HTTPConnection.debuglevel = 1
    requests_log = logging.getLogger("requests.packages.urllib3")
    requests_log.setLevel(logging.DEBUG)
    requests_log.propagate = True
    logging.getLogger("gql.transport.requests").setLevel(logging.DEBUG)

headers = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:98.0) Gecko/20100101 Firefox/98.0',
    'Referer': 'https://www.tokopedia.com/',
    'X-Tkpd-Lite-Service': 'zeus',
    'X-Version': '13ee0e8',
    'content-type': 'application/json',
    'x-device': 'desktop-0.0',
    'X-Source': 'tokopedia-lite',
    'Origin': 'https://www.tokopedia.com',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-site',
    'Pragma': 'no-cache',
    'Cache-Control': 'no-cache',
}
used_cookies = get_cookies(headers)
logging.info('Cookies obtained')
transport = RequestsHTTPTransport(url=BASE_URL, headers=headers, cookies=used_cookies)
transport.cookies = used_cookies
client = Client(transport=transport, fetch_schema_from_transport=False)
query = gql(CATEGORY_REQUEST)
category_query_result = client.execute(query, operation_name="headerMainData", get_execution_result=True)
used_cookies = get_cookies_from_client(client)
categories = category_query_result.data['categoryAllListLite']['categories']
logging.info('Categories obtained')

start = time.time()
counter = 0
THREADS = []


def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


@retry(tries=3, delay=1)
def fetch_product_page(params: dict, client, query):
    try:
        result = client.execute(query, operation_name="SearchProductQuery", variable_values=params)
        return result
    except Exception as e:
        logging.warning(f'Exception occurred: {e}')
        raise


def process_pages(pages: list, cat_id, results, cookies, i):
    # global used_cookies, MAX_CONCURRENCY
    page_chunk_counter = 0
    page_processor_transport = RequestsHTTPTransport(
        url=BASE_URL, headers=headers, cookies=cookies[i], timeout=REQUESTS_TIMEOUT
    )
    page_processor_transport.cookies = cookies[i]
    page_processor_client = Client(
        transport=page_processor_transport, fetch_schema_from_transport=False
    )
    page_processor_query = gql(PRODUCTS_REQUEST)
    for page_processor_page in pages:
        page_processor_params = {
            "params": f"page={page_processor_page}&sc={cat_id}&user_id=0&rows={ROWS_COUNT}&start={(page_processor_page - 1) * ROWS_COUNT}&source=directory&device=desktop&related=true&st=product&safe_search=false",
            # "params":{
            #     "page": page,
            #     "sc": category['id'],
            #     "user_id": 0,
            #     "rows": ROWS_COUNT,
            #     "start": 0,
            #     "source": 'directory',
            #     "device": 'desktop',
            #     "related": True,
            #     "st": 'product',
            #     "safe_search": False,
            # },
            "adParams": ""
        }
        page_processor_products = fetch_product_page(page_processor_params, page_processor_client, page_processor_query)
        page_chunk_counter = page_chunk_counter + len(page_processor_products['CategoryProducts']['data'])
        logging.debug(f'{page_processor_page} page processed')
    cookies[i] = get_cookies_from_client(client)
    client.close_sync()
    results[i] = page_chunk_counter
    logging.info(f'{pages} pages processed, got products: {page_chunk_counter}')


def process_categories(categories: list):
    global counter, end
    for category in categories:
        if 'children' in category:
            process_categories(category['children'])
        else:
            logging.info(f"Starting leave-category {category}")
            page = 1

            params = {
                "params": f"sc={category['id']}&user_id=0&rows={ROWS_COUNT}&start={(page - 1)*ROWS_COUNT+1}&source=directory&device=desktop&related=false&st=product&safe_search=false",
                "adParams": ""
            }
            products = fetch_product_page(params, client, gql(PRODUCTS_REQUEST))
            pages_count = math.ceil(products['CategoryProducts']['count'] / ROWS_COUNT)
            pages_chunks = list(chunks(range(pages_count), PAGES_PER_THREAD))
            bunches = chunks(pages_chunks, MAX_CONCURRENCY)
            should_cancel_current_category = False
            for bunch in bunches:
                threads = [None] * MAX_CONCURRENCY
                results = [None] * MAX_CONCURRENCY
                cookies = [None] * MAX_CONCURRENCY
                for i in range(len(bunch)):
                    threads[i] = threading.Thread(target=process_pages,
                                                  args=(bunch[i], category['id'], results, cookies, i))
                    threads[i].start()
                    # counter = counter + process_pages(pages_list)
                new_product_count = 0
                if len(threads) > 0:
                    for process in threads:
                        process.join()
                    if results is not None:
                        new_product_count = sum(results)
                counter = counter + new_product_count
                if not new_product_count:
                    logging.info(
                        f'No more products were obtained for bunch ({bunch[0]})..({bunch[-1]}), cancelling category fetching')
                    should_cancel_current_category = True
                    break
                logging.info(f'bunch processed, collected {counter} products')
                sys.stderr.flush()
                sys.stdout.flush()
                if counter > NEED_TO_FETCH:
                    logging.info(f"{NEED_TO_FETCH} count achieved, got {counter} elements")
                    end = time.time()
                    logging.info(f'Elapsed{end - start} fetched {counter} products')
                    exit(0)
            if should_cancel_current_category:
                continue


process_categories(categories)

end = time.time()
logging.info(f'Elapsed{end - start} fetched {counter} products')
