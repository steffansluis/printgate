import pytest

from printgate.adapters import github


class FakeAPI:
    def __init__(self, comments):
        self.comments, self.calls = comments, []

    def __call__(self, method, url, token, body=None):
        self.calls.append((method, url, body))
        if method == "GET":
            page = int(url.rsplit("page=", 1)[1])
            return self.comments[(page - 1) * 100:page * 100]
        return {"html_url": f"{method} {url}"}


def test_edits_the_comment_with_the_same_marker(monkeypatch):
    bot = {"type": "Bot"}
    api = FakeAPI([{"id": 1, "body": "unrelated", "user": bot},
                   {"id": 3, "body": "<!-- pg -->\nquoted by a person", "user": {"type": "User"}},
                   {"id": 7, "body": "<!-- pg -->\nold", "user": bot}])
    monkeypatch.setattr(github, "_call", api)
    url = github.upsert_comment("o/r", 3, "<!-- pg -->\nnew", "t")
    assert url.startswith("PATCH") and url.endswith("/issues/comments/7")


def test_posts_when_no_earlier_comment_exists_past_the_first_page(monkeypatch):
    api = FakeAPI([{"id": i, "body": "x"} for i in range(150)])
    monkeypatch.setattr(github, "_call", api)
    assert github.upsert_comment("o/r", 3, "<!-- pg -->\nnew", "t").startswith("POST")
    assert sum(1 for m, *_ in api.calls if m == "GET") == 3


def test_a_report_without_a_marker_is_refused():
    with pytest.raises(ValueError, match="marker"):
        github.upsert_comment("o/r", 3, "no marker", "t")


def test_http_errors_become_readable(monkeypatch):
    import urllib.error
    import urllib.request

    def refuse(*a, **kw):
        raise urllib.error.HTTPError("u", 403, "Forbidden", {}, None)

    monkeypatch.setattr(urllib.request, "urlopen", refuse)
    with pytest.raises(RuntimeError, match="403.*fork"):
        github.upsert_comment("o/r", 3, "<!-- pg -->\nnew", "t")
