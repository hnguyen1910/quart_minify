import os
import sys

import pytest
from flask import send_from_directory

from .constants import (
    FALSE_JS,
    FALSE_LESS,
    HTML,
    JS_RAW,
    LESS,
    LESS_RAW,
    MINIFIED_CSS_EDGE_CASES_GO,
    MINIFIED_HTML_CONDITIONAL_COMMENTS,
    MINIFIED_HTML_EMBEDDED_TAGS_GO,
    MINIFIED_HTML_GO,
    MINIFIED_JS,
    MINIFIED_JS_RAW_GO,
)
from .setup import create_app

app, store_minify = create_app(go=True)
is_windows = sys.platform.startswith("win")
skip_reason = "Windows does not support Go parsers"


@pytest.fixture
def client():
    store_minify.cache.clear()
    store_minify.fail_safe = False
    store_minify.cssless = True
    store_minify.js = True
    store_minify.bypass = []
    store_minify.bypass_caching = []
    store_minify.passive = False
    app.config["TESTING"] = True

    files = {
        "./test.js": JS_RAW,
        "./test.less": LESS_RAW,
        "./test.bypass.js": JS_RAW,
    }
    files_items = getattr(files, "iteritems", getattr(files, "items", None))()

    for f, c in files_items:
        with open(f, "w+") as file:
            file.write(c)

    with app.test_client() as client:
        yield client

    for f, c in files_items:
        try:
            os.remove(f)
        except Exception as e:
            pass


def add_url_rule(route, handler):
    added_routes = add_url_rule.__dict__.setdefault("added_routes", set())

    if route not in added_routes:
        with app.app_context():
            app._got_first_request = False
            app.add_url_rule(route, route, handler)
            added_routes.add(route)


@pytest.mark.skipif(is_windows, reason=skip_reason)
def test_go_html_minify(client):
    """testing HTML minify option"""
    resp = client.get("/html")
    assert MINIFIED_HTML_GO == resp.data


@pytest.mark.skipif(is_windows, reason=skip_reason)
def test_html_bypassing(client):
    """testing HTML route bypassing"""
    store_minify.bypass.append("html")
    resp = client.get("/html")
    assert bytes(HTML.encode("utf-8")) == resp.data


@pytest.mark.skipif(is_windows, reason=skip_reason)
def test_javascript_minify(client):
    """testing JavaScript minify option"""
    resp = client.get("/js")
    assert MINIFIED_JS == resp.data


@pytest.mark.skipif(is_windows, reason=skip_reason)
def test_minify_cache(client):
    """testing caching minifed response"""
    store_minify.cache.limit = 10
    client.get("/js")  # hit it twice, to get the cached minified response
    resp = client.get("/js").data

    assert resp == MINIFIED_JS
    assert (
        MINIFIED_JS.decode("utf-8") in store_minify.cache._cache.get("js", {}).values()
    )


@pytest.mark.skipif(is_windows, reason=skip_reason)
def test_fail_safe(client):
    """testing fail safe enabled with false input"""
    store_minify.parser.fail_safe = True
    resp = client.get("/js_false")

    assert bytes(FALSE_JS.encode("utf-8")) == resp.data


@pytest.mark.skipif(is_windows, reason=skip_reason)
def test_fail_safe_false_input(client):
    """testing fail safe disabled with false input"""
    try:
        client.get("/js_false")
    except Exception as e:
        assert "CompilationError" == e.__class__.__name__


@pytest.mark.skipif(is_windows, reason=skip_reason)
def test_caching_limit_only_when_needed(client):
    """test caching limit without any variations"""
    store_minify.cache.limit = 5
    store_minify.js = True
    resp = [client.get("/js").data for i in range(10)]

    assert len(store_minify.cache._cache.get("js", {})) == 1
    for r in resp:
        assert MINIFIED_JS == r


@pytest.mark.skipif(is_windows, reason=skip_reason)
def test_caching_limit_exceeding(client):
    """test caching limit with multiple variations"""
    new_limit = store_minify.cache.limit = 4
    resp = [client.get("/js/{}".format(i)).data for i in range(10)]

    assert len(store_minify.cache._cache.get("js_addition", {})) == new_limit

    for v in store_minify.cache._cache.get("js_addition", {}).values():
        assert bytes(v.encode("utf-8")) in resp


@pytest.mark.skipif(is_windows, reason=skip_reason)
def test_bypass_caching(client):
    """test endpoint bypassed not caching"""
    store_minify.bypass_caching.append("js")
    resp = client.get("/js")
    resp_values = [
        bytes("<script>{}</script>".format(v).encode("utf-8"))
        for v in store_minify.cache._cache.get("js", {}).values()
    ]

    assert MINIFIED_JS == resp.data
    assert resp.data not in resp_values


@pytest.mark.skipif(is_windows, reason=skip_reason)
def test_bypassing_with_regex(client):
    """test endpoint bypassed not minifying and not caching regex"""
    store_minify.bypass.append("css*")
    store_minify.bypass_caching.append("css*")
    store_minify.fail_safe = True
    resp = client.get("/cssless").data.decode("utf-8")
    resp_false = client.get("/cssless_false").data.decode("utf-8")

    assert resp == LESS
    assert resp_false == FALSE_LESS


@pytest.mark.skipif(is_windows, reason=skip_reason)
def test_passive_flag(client):
    """test disabling active minifying"""
    store_minify.passive = True
    resp = client.get("/html").data.decode("utf-8")

    assert resp == HTML


@pytest.mark.skipif(is_windows, reason=skip_reason)
def test_go_html_minify_decorated(client):
    """test minifying html decorator"""
    store_minify.passive = True
    resp = client.get("/html_decorated").data

    assert resp == MINIFIED_HTML_GO


@pytest.mark.skipif(is_windows, reason=skip_reason)
def test_go_html_minify_decorated_cache(client):
    store_minify.passive = True
    client.get("/html_decorated").data
    resp = client.get("/html_decorated").data

    assert resp == MINIFIED_HTML_GO


@pytest.mark.skipif(is_windows, reason=skip_reason)
def test_javascript_minify_decorated(client):
    """test minifying javascript decorator"""
    store_minify.passive = True
    resp = client.get("/js_decorated").data

    assert resp == MINIFIED_JS


@pytest.mark.skipif(is_windows, reason=skip_reason)
def test_minify_css_decorated(client):
    """test minifying css decorator"""
    store_minify.passive = True
    resp = client.get("/css_decorated").data

    assert resp == bytes(f"<style>{MINIFIED_CSS_EDGE_CASES_GO}</style>", "utf-8")


@pytest.mark.skipif(is_windows, reason=skip_reason)
def test_go_minify_static_js_with_add_url_rule(client):
    """test minifying static file js"""
    f = "/test.js"

    add_url_rule(
        f,
        lambda: send_from_directory("../.", f[1:], mimetype="application/javascript"),
    )

    store_minify.static = True
    assert client.get(f).data == MINIFIED_JS_RAW_GO

    store_minify.static = False
    assert client.get(f).data != MINIFIED_JS_RAW_GO

    store_minify.static = True
    store_minify.js = False
    assert client.get(f).data != MINIFIED_JS_RAW_GO


@pytest.mark.skipif(is_windows, reason=skip_reason)
def test_bypass_minify_static_file(client):
    """test bypassing js file minifying"""
    f = "/test.bypass.js"

    add_url_rule(
        f, lambda: send_from_directory("../.", f[1:], mimetype="application/javascript")
    )

    store_minify.static = True
    assert client.get(f).data == MINIFIED_JS_RAW_GO

    store_minify.bypass = ["bypass.*"]
    assert client.get(f).data != MINIFIED_JS_RAW_GO


@pytest.mark.skipif(is_windows, reason=skip_reason)
def test_html_with_embedded_tags(client):
    """test html with embedded js and less tags"""
    assert client.get("/html_embedded").data == MINIFIED_HTML_EMBEDDED_TAGS_GO


@pytest.mark.skipif(is_windows, reason=skip_reason)
def test_unicode_endpoint(client):
    """test endpoint with ascii chars"""
    resp = client.get("/unicode")

    assert resp.status == "200 OK"
    assert resp.data.decode("utf-8") == "–"


@pytest.mark.skipif(is_windows, reason=skip_reason)
def test_go_html_minify_conditional_comments(client):
    """testing go HTML minify with conditional comments"""
    resp = client.get("/conditional-comments")
    assert MINIFIED_HTML_CONDITIONAL_COMMENTS == resp.data
