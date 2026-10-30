"""Polite HTTP for every feed and registry adapter: one place for identification, rate limits and retries.

Rules it enforces:
  - Identify ourselves honestly. SEC requires a contact in the User-Agent; other sites get the same string.
  - Keep each host under its published limit (HOST_INTERVAL), however many callers share it.
  - Retry rate-limit and server errors with growing waits, honouring Retry-After; give up after `tries`.
  - A 404 is an answer ("nothing there"), not an error.
"""

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

# Minimum seconds between requests to one host. Published limits: SEC 10/s, Companies House 600 per
# 5 minutes, recherche-entreprises 7/s, GLEIF 60/minute. Anything else: one request a second.
HOST_INTERVAL = {
    "www.sec.gov": 0.12, "efts.sec.gov": 0.12, "data.sec.gov": 0.12,
    "api.company-information.service.gov.uk": 0.5, "document-api.company-information.service.gov.uk": 0.5,
    "recherche-entreprises.api.gouv.fr": 0.2,
    "api.gleif.org": 1.0,
}
DEFAULT_INTERVAL = 1.0
RETRY_CODES = {429, 500, 502, 503, 504}
_last = {}


def user_agent(require_contact=False):
    """The tracker's User-Agent. SEC refuses anonymous traffic, so EDGAR callers pass require_contact=True."""
    ua = os.environ.get("EDGAR_USER_AGENT", "").strip()
    if require_contact and "@" not in ua:
        raise RuntimeError("Set EDGAR_USER_AGENT to 'Your Name your@email' (SEC requires a contact)")
    return ua or "ai-infrastructure research tracker"


def _throttle(url):
    host = urllib.parse.urlsplit(url).hostname or ""
    wait = HOST_INTERVAL.get(host, DEFAULT_INTERVAL) - (time.monotonic() - _last.get(host, -1e9))
    if wait > 0:
        time.sleep(wait)
    _last[host] = time.monotonic()


def get(url, headers=None, tries=4, timeout=60, max_bytes=None):
    """Return (body bytes, content type), or (None, '') for a 404. max_bytes stops reading early (e.g. to get a title)."""
    hdrs = {"User-Agent": user_agent(), "Accept-Encoding": "identity", **(headers or {})}
    for attempt in range(tries):
        _throttle(url)
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=hdrs), timeout=timeout) as r:
                return (r.read(max_bytes) if max_bytes else r.read()), r.headers.get("Content-Type", "")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None, ""
            if e.code not in RETRY_CODES or attempt == tries - 1:
                raise
            retry_after = e.headers.get("Retry-After", "")
            time.sleep(int(retry_after) if retry_after.isdigit() else 2 ** (attempt + 1))
        except urllib.error.URLError:
            if attempt == tries - 1:
                raise
            time.sleep(2 ** (attempt + 1))


def get_json(url, headers=None, **kw):
    body, _ = get(url, {"Accept": "application/json", **(headers or {})}, **kw)
    return json.loads(body) if body else {}
