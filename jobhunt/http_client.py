import httpx

DEFAULT_TIMEOUT = 30.0
DEFAULT_HEADERS = {"User-Agent": "job-hunt-automation/0.1 (private personal use)"}


def build_client(timeout: float = DEFAULT_TIMEOUT) -> httpx.Client:
    """Create a configured httpx client shared by source adapters."""
    return httpx.Client(timeout=timeout, headers=DEFAULT_HEADERS)
