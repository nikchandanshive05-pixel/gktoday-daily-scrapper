"""
Resilient network and content extraction utilities.
Bypasses Cloudflare / datacenter blocks via header rotation and Googlebot fallbacks.
"""
import re
import logging
import requests
import feedparser
import trafilatura
from bs4 import BeautifulSoup
from typing import Optional, List, Dict, Any

try:
    from curl_cffi import requests as cureq
    CURL_CFFI_AVAILABLE = True
except ImportError:
    cureq = None
    CURL_CFFI_AVAILABLE = False

logger = logging.getLogger("network")

CHROME_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,mr;q=0.8",
    "Sec-Ch-Ua": '"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Upgrade-Insecure-Requests": "1",
}

GOOGLEBOT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
    "Accept": "*/*",
}


def fetch_html(url: str, timeout: int = 20) -> Optional[str]:
    """
    Fetch raw HTML from a URL with multi-tier bypass:
    1. curl_cffi with Chrome 124 TLS fingerprint impersonation (bypasses Cloudflare JA3/JA4 blocks)
    2. requests with Chrome headers
    3. requests with Googlebot crawler headers
    """
    # 1. Try with curl_cffi TLS impersonation
    if CURL_CFFI_AVAILABLE:
        try:
            resp = cureq.get(
                url,
                impersonate="chrome124",
                timeout=timeout,
                headers={"Accept-Language": "en-US,en;q=0.9,mr;q=0.8"},
            )
            if resp.status_code == 200 and len(resp.text) > 300:
                return resp.text
        except Exception as e:
            logger.debug(f"curl_cffi fetch failed for {url}: {e}")

    # 2. Try with standard requests Chrome Desktop headers
    try:
        resp = requests.get(url, headers=CHROME_HEADERS, timeout=timeout)
        if resp.status_code == 200 and len(resp.text) > 300:
            return resp.text
    except Exception as e:
        logger.debug(f"Chrome UA fetch failed for {url}: {e}")

    # 3. Try with Googlebot crawler headers
    try:
        resp = requests.get(url, headers=GOOGLEBOT_HEADERS, timeout=timeout)
        if resp.status_code == 200 and len(resp.text) > 300:
            return resp.text
        else:
            logger.warning(f"Googlebot UA returned status {resp.status_code} for {url}")
    except Exception as e:
        logger.warning(f"Failed to fetch {url}: {e}")

    return None


def fetch_feed_entries(feed_url: str, timeout: int = 20) -> List[Any]:
    """
    Fetch RSS feed entries using TLS impersonation and browser headers
    to bypass Cloudflare 403 blocks on feedparser's default User-Agent.
    """
    # 1. Try with curl_cffi TLS impersonation
    if CURL_CFFI_AVAILABLE:
        try:
            resp = cureq.get(feed_url, impersonate="chrome124", timeout=timeout)
            if resp.status_code == 200 and resp.content:
                parsed = feedparser.parse(resp.content)
                if parsed.entries:
                    return parsed.entries
        except Exception as e:
            logger.debug(f"curl_cffi feed fetch failed for {feed_url}: {e}")

    # 2. Try with requests Chrome headers
    try:
        resp = requests.get(feed_url, headers=CHROME_HEADERS, timeout=timeout)
        if resp.status_code == 200 and resp.content:
            parsed = feedparser.parse(resp.content)
            if parsed.entries:
                return parsed.entries
    except Exception as e:
        logger.debug(f"Direct feed fetch failed for {feed_url}: {e}")

    # 3. Fallback with Googlebot headers
    try:
        resp = requests.get(feed_url, headers=GOOGLEBOT_HEADERS, timeout=timeout)
        if resp.status_code == 200 and resp.content:
            parsed = feedparser.parse(resp.content)
            if parsed.entries:
                return parsed.entries
    except Exception as e:
        logger.warning(f"Feed fetch failed for {feed_url}: {e}")

    # 4. Standard feedparser fallback
    try:
        parsed = feedparser.parse(feed_url)
        return parsed.entries or []
    except Exception:
        return []


def extract_clean_text(html: str) -> str:
    """
    Extract readable article text from HTML using Trafilatura
    with a robust BeautifulSoup fallback.
    """
    if not html:
        return ""

    # 1. Trafilatura Extraction
    try:
        text = trafilatura.extract(html, include_comments=False, include_tables=True)
        if text and len(text.strip()) > 120:
            return text.strip()
    except Exception as e:
        logger.debug(f"Trafilatura parsing notice: {e}")

    # 2. BeautifulSoup Fallback
    try:
        soup = BeautifulSoup(html, "html.parser")
        for tag in ["script", "style", "nav", "aside", "header", "footer", "form"]:
            for el in soup.find_all(tag):
                el.decompose()

        container = (
            soup.find("article")
            or soup.find("div", class_=re.compile(r"(article-body|entry-content|content-area|story-details|articleBody)"))
            or soup.find("body")
        )
        if container:
            paras = [p.get_text(" ", strip=True) for p in container.find_all(["p", "h3", "h4"])]
            paras = [p for p in paras if len(p) > 30]
            if paras:
                return "\n\n".join(paras)
    except Exception as e:
        logger.warning(f"DOM fallback extraction error: {e}")

    return ""
