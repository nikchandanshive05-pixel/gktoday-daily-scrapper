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

SOCIAL_HEADERS = {
    "User-Agent": "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,mr;q=0.8",
}

TWITTER_HEADERS = {
    "User-Agent": "Twitterbot/1.0",
    "Accept": "*/*",
}

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


def fetch_html(url: str, timeout: int = 20) -> Optional[str]:
    """
    Fetch raw HTML from a URL with multi-tier bypass:
    1. Social Crawler UA (facebookexternalhit - whitelisted by Cloudflare news WAFs without PTR lookup)
    2. Twitterbot UA
    3. curl_cffi with Chrome 124 TLS fingerprint impersonation
    4. Chrome Desktop UA
    """
    # 1. Social Crawler UA (Bypasses Cloudflare Datacenter & Reverse-DNS checks)
    try:
        resp = requests.get(url, headers=SOCIAL_HEADERS, timeout=timeout)
        logger.info(f"[DIAG fetch_html] {url} Social UA status: {resp.status_code}, length: {len(resp.content)}")
        if resp.status_code == 200 and len(resp.text) > 300:
            return resp.text
    except Exception as e:
        logger.info(f"[DIAG fetch_html] Social UA error for {url}: {e}")

    # 2. Twitterbot UA
    try:
        resp = requests.get(url, headers=TWITTER_HEADERS, timeout=timeout)
        logger.info(f"[DIAG fetch_html] {url} Twitter UA status: {resp.status_code}, length: {len(resp.content)}")
        if resp.status_code == 200 and len(resp.text) > 300:
            return resp.text
    except Exception as e:
        logger.info(f"[DIAG fetch_html] Twitterbot UA error for {url}: {e}")

    # 3. curl_cffi TLS impersonation
    if CURL_CFFI_AVAILABLE:
        try:
            resp = cureq.get(
                url,
                impersonate="chrome124",
                timeout=timeout,
                headers={"Accept-Language": "en-US,en;q=0.9,mr;q=0.8"},
                verify=False,
            )
            logger.info(f"[DIAG fetch_html] {url} curl_cffi status: {resp.status_code}, length: {len(resp.content)}")
            if resp.status_code == 200 and len(resp.text) > 300:
                return resp.text
        except Exception as e:
            logger.info(f"[DIAG fetch_html] curl_cffi error for {url}: {e}")

    # 4. Chrome Desktop UA fallback
    try:
        resp = requests.get(url, headers=CHROME_HEADERS, timeout=timeout)
        logger.info(f"[DIAG fetch_html] {url} Chrome UA status: {resp.status_code}, length: {len(resp.content)}")
        if resp.status_code == 200 and len(resp.text) > 300:
            return resp.text
    except Exception as e:
        logger.warning(f"Chrome UA fetch failed for {url}: {e}")

    return None


def fetch_feed_entries(feed_url: str, timeout: int = 20) -> List[Any]:
    """
    Fetch RSS feed entries using social crawler bypass and TLS impersonation.
    """
    # 1. Social Crawler UA (Whitelisted on News CDN RSS feeds)
    try:
        resp = requests.get(feed_url, headers=SOCIAL_HEADERS, timeout=timeout)
        logger.info(f"[DIAG feed] {feed_url} Social UA status: {resp.status_code}, length: {len(resp.content)}")
        if resp.status_code == 200 and resp.content:
            parsed = feedparser.parse(resp.content)
            logger.info(f"[DIAG feed] {feed_url} Social UA parsed entries: {len(parsed.entries)}")
            if parsed.entries:
                return parsed.entries
    except Exception as e:
        logger.info(f"[DIAG feed] Social UA error for {feed_url}: {e}")

    # 2. Twitterbot UA
    try:
        resp = requests.get(feed_url, headers=TWITTER_HEADERS, timeout=timeout)
        logger.info(f"[DIAG feed] {feed_url} Twitter UA status: {resp.status_code}, length: {len(resp.content)}")
        if resp.status_code == 200 and resp.content:
            parsed = feedparser.parse(resp.content)
            logger.info(f"[DIAG feed] {feed_url} Twitter UA parsed entries: {len(parsed.entries)}")
            if parsed.entries:
                return parsed.entries
    except Exception as e:
        logger.info(f"[DIAG feed] Twitterbot UA error for {feed_url}: {e}")

    # 3. curl_cffi TLS impersonation
    if CURL_CFFI_AVAILABLE:
        try:
            resp = cureq.get(feed_url, impersonate="chrome124", timeout=timeout, verify=False)
            logger.info(f"[DIAG feed] {feed_url} curl_cffi status: {resp.status_code}, length: {len(resp.content)}")
            if resp.status_code == 200 and resp.content:
                parsed = feedparser.parse(resp.content)
                logger.info(f"[DIAG feed] {feed_url} curl_cffi parsed entries: {len(parsed.entries)}")
                if parsed.entries:
                    return parsed.entries
        except Exception as e:
            logger.info(f"[DIAG feed] curl_cffi error for {feed_url}: {e}")

    # 4. Chrome headers
    try:
        resp = requests.get(feed_url, headers=CHROME_HEADERS, timeout=timeout)
        logger.info(f"[DIAG feed] {feed_url} Chrome UA status: {resp.status_code}, length: {len(resp.content)}")
        if resp.status_code == 200 and resp.content:
            parsed = feedparser.parse(resp.content)
            logger.info(f"[DIAG feed] {feed_url} Chrome UA parsed entries: {len(parsed.entries)}")
            if parsed.entries:
                return parsed.entries
    except Exception as e:
        logger.debug(f"Chrome headers feed fetch failed for {feed_url}: {e}")

    # 5. Standard feedparser fallback
    try:
        parsed = feedparser.parse(feed_url)
        logger.info(f"[DIAG feed] {feed_url} fallback feedparser entries: {len(parsed.entries)}")
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
