"""Keep one report comment per pull request up to date, the way coverage services do."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

API = os.environ.get("GITHUB_API_URL", "https://api.github.com")
LIMIT = 65536   # GitHub refuses longer comment bodies


def _call(method: str, url: str, token: str, body: dict | None = None):
    req = urllib.request.Request(url, method=method, data=json.dumps(body).encode() if body else None,
                                 headers={"Authorization": f"Bearer {token}",
                                          "Accept": "application/vnd.github+json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read() or "null")
    except urllib.error.HTTPError as e:
        hint = " (a fork's token is read-only)" if e.code == 403 else ""
        raise RuntimeError(f"GitHub {method} {url} failed: {e.code} {e.reason}{hint}") from e


def upsert_comment(repo: str, pr: int, body: str, token: str) -> str:
    """Edit the bot comment that starts with the body's first line, or post one. Returns its URL.
    Only bot comments are candidates: a person quoting the marker must not get overwritten."""
    marker = body.splitlines()[0]
    if len(body) > LIMIT:
        body = body[:LIMIT - 200] + "\n\n… report truncated; the full one is in the job's artifacts.\n"
    if not marker.startswith("<!--"):
        raise ValueError("the report must start with an HTML comment marker, e.g. <!-- printgate -->")
    page = 1
    while comments := _call("GET", f"{API}/repos/{repo}/issues/{pr}/comments?per_page=100&page={page}",
                            token):
        for c in comments:
            if c["body"].startswith(marker) and c.get("user", {}).get("type") == "Bot":
                return _call("PATCH", f"{API}/repos/{repo}/issues/comments/{c['id']}", token,
                             {"body": body})["html_url"]
        page += 1
    return _call("POST", f"{API}/repos/{repo}/issues/{pr}/comments", token, {"body": body})["html_url"]
