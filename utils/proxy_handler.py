import random
from typing import Optional


class ProxyHandler:
    """Rotates through a list of proxies. Pass an empty list to disable proxying."""

    def __init__(self, proxies: list[str] = None):
        self._proxies = proxies or []
        self._index = 0

    def get_proxy(self) -> Optional[str]:
        if not self._proxies:
            return None
        proxy = self._proxies[self._index % len(self._proxies)]
        self._index += 1
        return proxy

    def get_random_proxy(self) -> Optional[str]:
        if not self._proxies:
            return None
        return random.choice(self._proxies)

    def load_from_file(self, path: str) -> None:
        with open(path) as f:
            self._proxies = [line.strip() for line in f if line.strip()]

    def __len__(self):
        return len(self._proxies)


# Default no-op handler used when no proxies are configured
default_proxy_handler = ProxyHandler()
