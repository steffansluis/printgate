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
    api = FakeAPI([{"id": 1, "body": "unrelated"}, {"id": 7, "body": "<!-- pg -->\nold"}])
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
