import asyncio
import random
from typing import List, Optional, Dict, Any
import httpx

def _pick(headers_list: Optional[List[str]]) -> Optional[str]:
    if headers_list:
        return random.choice(headers_list)
    return None

def build_headers(user_agents: Optional[List[str]] = None) -> Dict[str, str]:
    ua = _pick(user_agents) or (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    return {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.7",
        "Connection": "keep-alive",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }

def get_proxy(proxies: Optional[List[str]]) -> Optional[str]:
    if proxies:
        return random.choice(proxies)
    return None

def build_client(
    timeout_seconds: int = 20,
    proxies: Optional[List[str]] = None,
    user_agents: Optional[List[str]] = None,
) -> httpx.AsyncClient:
    headers = build_headers(user_agents)
    proxy = get_proxy(proxies)
    timeout = httpx.Timeout(timeout_seconds)
    client = httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=timeout, proxies=proxy)
    return client

async def fetch_text(
    client: httpx.AsyncClient,
    url: str,
    max_retries: int = 3,
    backoff_seconds: float = 1.5,
) -> str:
    last_err: Optional[Exception] = None
    for attempt in range(1, max_retries + 1):
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            # Some ZoomInfo pages require JS/auth; this returns login pages if blocked.
            return resp.text
        except Exception as e:  # noqa: BLE001
            last_err = e
            await asyncio.sleep(backoff_seconds * attempt)
            # rotate UA/proxy slightly between retries
            try:
                client.headers.update(build_headers([client.headers.get("User-Agent", "")]))
            except Exception:
                pass
    if last_err:
        raise last_err
    return ""