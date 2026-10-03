"""Keep one report comment per pull request up to date, the way coverage services do."""
from __future__ import annotations

import json
import os
import urllib.request

API = os.environ.get("GITHUB_API_URL", "https://api.github.com")


def _call(method: str, url: str, token: str, body: dict | None = None):
    req = urllib.request.Request(url, method=method, data=json.dumps(body).encode() if body else None,
                                 headers={"Authorization": f"Bearer {token}",
                                          "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read() or "null")


def upsert_comment(repo: str, pr: int, body: str, token: str) -> str:
    """Edit the comment that starts with the body's first line, or post one. Returns its URL."""
    marker = body.splitlines()[0]
    if not marker.startswith("<!--"):
        raise ValueError("the report must start with an HTML comment marker, e.g. <!-- printgate -->")
    page = 1
    while comments := _call("GET", f"{API}/repos/{repo}/issues/{pr}/comments?per_page=100&page={page}",
                            token):
        for c in comments:
            if c["body"].startswith(marker):
                return _call("PATCH", f"{API}/repos/{repo}/issues/comments/{c['id']}", token,
                             {"body": body})["html_url"]
        page += 1
    return _call("POST", f"{API}/repos/{repo}/issues/{pr}/comments", token, {"body": body})["html_url"]
