import time
import random
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from config.settings import REQUEST_TIMEOUT, MAX_RETRIES, RATE_LIMIT_DELAY

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
]


def _build_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=MAX_RETRIES,
        backoff_factor=1.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def get(url: str, params: dict = None, headers: dict = None, proxy: str = None) -> requests.Response:
    session = _build_session()
    merged_headers = {"User-Agent": random.choice(USER_AGENTS)}
    if headers:
        merged_headers.update(headers)

    proxies = {"http": proxy, "https": proxy} if proxy else None

    time.sleep(random.uniform(*RATE_LIMIT_DELAY))

    response = session.get(
        url,
        params=params,
        headers=merged_headers,
        proxies=proxies,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response


def post(url: str, data: dict = None, json: dict = None, headers: dict = None, proxy: str = None) -> requests.Response:
    session = _build_session()
    merged_headers = {"User-Agent": random.choice(USER_AGENTS)}
    if headers:
        merged_headers.update(headers)

    proxies = {"http": proxy, "https": proxy} if proxy else None

    time.sleep(random.uniform(*RATE_LIMIT_DELAY))

    response = session.post(
        url,
        data=data,
        json=json,
        headers=merged_headers,
        proxies=proxies,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response
