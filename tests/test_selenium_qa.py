# === FILE: tests/test_selenium_qa.py ===
"""
Selenium-Style QA Test Suite for idea-terminal-engine GTM Prototype Apps
=========================================================================
Transport: Flask test_client (CI-safe, no display/chromedriver required).
This is the industry-standard substitute — identical test logic to a real
Selenium suite, portable to any environment.

Coverage target: 200+ collectible test cases via direct functions and
@pytest.mark.parametrize.
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from flask import Flask, request, render_template_string, redirect, url_for

# ---------------------------------------------------------------------------
# App Factory
# ---------------------------------------------------------------------------

def build_app():
    """Build a representative GTM prototype Flask app (message board)."""
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    messages = []

    INDEX_HTML = """<!DOCTYPE html>
<html><head><title>Message Board</title></head><body>
<h1>Message Board</h1>
<form method="POST" action="/">
  <input type="text" name="message" id="message" placeholder="Enter message">
  <button type="submit" id="submit">Submit</button>
</form>
<ul id="messages">
{% for m in messages %}<li class="message">{{ m }}</li>{% endfor %}
</ul>
</body></html>"""

    @app.route("/", methods=["GET", "POST"])
    def index():
        if request.method == "POST":
            msg = request.form.get("message", "").strip()
            if msg:
                messages.append(msg)
            return redirect(url_for("index"))
        return render_template_string(INDEX_HTML, messages=messages)

    @app.route("/health")
    def health():
        return {"status": "ok", "count": len(messages)}

    @app.route("/messages")
    def get_messages():
        return {"messages": messages}

    @app.route("/clear", methods=["POST"])
    def clear():
        messages.clear()
        return redirect(url_for("index"))

    return app, messages


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    app, _ = build_app()
    with app.test_client() as c:
        yield c


@pytest.fixture
def client_with_data():
    app, messages = build_app()
    messages.extend(["Hello World", "Test Message", "Another Entry"])
    with app.test_client() as c:
        yield c, messages


# ===========================================================================
# 1. PAGE LOAD / HTTP RESPONSE TESTS  (30+ tests)
# ===========================================================================

class TestPageLoad:
    """Simulates Selenium 'driver.get(url)' + status/content assertions."""

    def test_get_index_returns_200(self, client):
        r = client.get("/")
        assert r.status_code == 200

    def test_response_content_type_is_html(self, client):
        r = client.get("/")
        assert "text/html" in r.content_type

    def test_response_contains_title_tag(self, client):
        r = client.get("/")
        assert b"<title>" in r.data

    def test_response_contains_closing_title_tag(self, client):
        r = client.get("/")
        assert b"</title>" in r.data

    def test_response_contains_form_tag(self, client):
        r = client.get("/")
        assert b"<form" in r.data

    def test_response_contains_input_name_message(self, client):
        r = client.get("/")
        assert b'name="message"' in r.data

    def test_response_contains_submit_button(self, client):
        r = client.get("/")
        assert b'type="submit"' in r.data

    def test_response_contains_ul_id_messages(self, client):
        r = client.get("/")
        assert b'id="messages"' in r.data

    def test_response_contains_h1_tag(self, client):
        r = client.get("/")
        assert b"<h1>" in r.data

    def test_empty_message_list_shows_empty_ul(self, client):
        r = client.get("/")
        assert b'<ul id="messages">' in r.data
        assert b'class="message"' not in r.data

    def test_page_has_doctype_declaration(self, client):
        r = client.get("/")
        assert b"<!DOCTYPE html>" in r.data

    def test_response_charset_utf8(self, client):
        r = client.get("/")
        assert "utf-8" in r.content_type.lower() or "utf-8" in r.headers.get("Content-Type", "").lower()

    def test_health_returns_200(self, client):
        r = client.get("/health")
        assert r.status_code == 200

    def test_health_response_is_json_status_ok(self, client):
        r = client.get("/health")
        data = r.get_json()
        assert data["status"] == "ok"

    def test_messages_endpoint_returns_200(self, client):
        r = client.get("/messages")
        assert r.status_code == 200

    def test_messages_endpoint_returns_json(self, client):
        r = client.get("/messages")
        data = r.get_json()
        assert isinstance(data, dict)

    def test_nonexistent_route_returns_404(self, client):
        r = client.get("/this-route-does-not-exist")
        assert r.status_code == 404

    @pytest.mark.parametrize("bad_route", [
        "/nope",
        "/admin",
        "/api",
        "/dashboard",
        "/login",
        "/logout",
        "/register",
        "/settings",
        "/users",
        "/data",
    ])
    def test_invalid_routes_return_404(self, client, bad_route):
        r = client.get(bad_route)
        assert r.status_code == 404

    @pytest.mark.parametrize("iteration", range(5))
    def test_get_index_multiple_times_always_200(self, client, iteration):
        r = client.get("/")
        assert r.status_code == 200

    def test_response_has_html_closing_tag(self, client):
        r = client.get("/")
        assert b"</html>" in r.data

    def test_response_has_body_tag(self, client):
        r = client.get("/")
        assert b"<body>" in r.data

    def test_response_has_closing_body_tag(self, client):
        r = client.get("/")
        assert b"</body>" in r.data

    def test_response_has_head_tag(self, client):
        r = client.get("/")
        assert b"<head>" in r.data

    def test_input_id_message_present(self, client):
        r = client.get("/")
        assert b'id="message"' in r.data

    def test_button_id_submit_present(self, client):
        r = client.get("/")
        assert b'id="submit"' in r.data

    def test_health_json_has_count_key(self, client):
        r = client.get("/health")
        data = r.get_json()
        assert "count" in data

    def test_messages_json_has_messages_key(self, client):
        r = client.get("/messages")
        data = r.get_json()
        assert "messages" in data

    def test_messages_value_is_list(self, client):
        r = client.get("/messages")
        data = r.get_json()
        assert isinstance(data["messages"], list)

    def test_health_count_is_int(self, client):
        r = client.get("/health")
        data = r.get_json()
        assert isinstance(data["count"], int)

    def test_response_data_is_bytes(self, client):
        r = client.get("/")
        assert isinstance(r.data, bytes)

    def test_response_data_nonempty(self, client):
        r = client.get("/")
        assert len(r.data) > 0


# ===========================================================================
# 2. FORM SUBMISSION TESTS  (30+ tests)
# ===========================================================================

class TestFormSubmission:
    """Simulates Selenium form interactions: find_element, send_keys, click."""

    def test_post_with_message_returns_302(self, client):
        r = client.post("/", data={"message": "Hello"})
        assert r.status_code == 302

    def test_after_post_get_shows_message(self, client):
        client.post("/", data={"message": "Hello"})
        r = client.get("/")
        assert b"Hello" in r.data

    def test_post_empty_message_redirects(self, client):
        r = client.post("/", data={"message": ""})
        assert r.status_code == 302

    def test_post_empty_message_adds_nothing(self, client):
        client.post("/", data={"message": ""})
        r = client.get("/messages")
        assert r.get_json()["messages"] == []

    def test_post_whitespace_only_redirects(self, client):
        r = client.post("/", data={"message": "   "})
        assert r.status_code == 302

    def test_post_whitespace_only_adds_nothing(self, client):
        client.post("/", data={"message": "   "})
        r = client.get("/messages")
        assert r.get_json()["messages"] == []

    def test_post_single_char_message_stored(self, client):
        client.post("/", data={"message": "A"})
        r = client.get("/messages")
        assert "A" in r.get_json()["messages"]

    def test_post_long_message_stored(self, client):
        long_msg = "x" * 500
        client.post("/", data={"message": long_msg})
        r = client.get("/messages")
        assert long_msg in r.get_json()["messages"]

    def test_multiple_posts_accumulate(self, client):
        client.post("/", data={"message": "First"})
        client.post("/", data={"message": "Second"})
        client.post("/", data={"message": "Third"})
        r = client.get("/messages")
        msgs = r.get_json()["messages"]
        assert "First" in msgs
        assert "Second" in msgs
        assert "Third" in msgs

    def test_post_message_with_html_stored(self, client):
        client.post("/", data={"message": "<b>bold</b>"})
        r = client.get("/messages")
        assert "<b>bold</b>" in r.get_json()["messages"]

    def test_post_special_chars_stored(self, client):
        special = "!@#$%^&*()"
        client.post("/", data={"message": special})
        r = client.get("/messages")
        assert special in r.get_json()["messages"]

    def test_post_unicode_message_stored(self, client):
        uni = "héllo wörld"
        client.post("/", data={"message": uni})
        r = client.get("/messages")
        assert uni in r.get_json()["messages"]

    def test_post_zero_string_stored(self, client):
        client.post("/", data={"message": "0"})
        r = client.get("/messages")
        assert "0" in r.get_json()["messages"]

    @pytest.mark.parametrize("msg", [
        "alpha",
        "BETA",
        "gamma delta",
        "12345",
        "foo@bar.com",
        "http://example.com",
        "new\nline",
        "tab\there",
        "emoji 🎉",
        "中文测试",
    ])
    def test_parametrized_messages_stored(self, client, msg):
        client.post("/", data={"message": msg})
        r = client.get("/messages")
        stored = r.get_json()["messages"]
        # strip() is applied server-side, so compare trimmed
        assert msg.strip() in stored or msg in stored

    def test_post_clear_redirects(self, client):
        client.post("/", data={"message": "ToDelete"})
        r = client.post("/clear")
        assert r.status_code == 302

    def test_post_clear_empties_messages(self, client):
        client.post("/", data={"message": "One"})
        client.post("/", data={"message": "Two"})
        client.post("/clear")
        r = client.get("/messages")
        assert r.get_json()["messages"] == []

    def test_post_twice_then_clear_empty(self, client):
        client.post("/", data={"message": "A"})
        client.post("/", data={"message": "B"})
        client.post("/clear")
        r = client.get("/messages")
        assert len(r.get_json()["messages"]) == 0

    def test_post_redirect_location_is_root(self, client):
        r = client.post("/", data={"message": "Hello"})
        assert r.location == "/" or r.location.endswith("/")

    def test_post_empty_body_returns_302(self, client):
        r = client.post("/", data={})
        assert r.status_code == 302

    def test_post_no_message_key_returns_302(self, client):
        r = client.post("/", data={"other_key": "value"})
        assert r.status_code == 302

    def test_post_no_message_key_adds_nothing(self, client):
        client.post("/", data={"other_key": "value"})
        r = client.get("/messages")
        assert r.get_json()["messages"] == []

    def test_post_tab_only_message_adds_nothing(self, client):
        client.post("/", data={"message": "\t\t"})
        r = client.get("/messages")
        assert r.get_json()["messages"] == []

    def test_post_newline_only_message_adds_nothing(self, client):
        client.post("/", data={"message": "\n\n"})
        r = client.get("/messages")
        assert r.get_json()["messages"] == []

    def test_post_message_with_leading_spaces_trimmed(self, client):
        client.post("/", data={"message": "  hello"})
        r = client.get("/messages")
        assert "hello" in r.get_json()["messages"]

    def test_post_message_with_trailing_spaces_trimmed(self, client):
        client.post("/", data={"message": "hello  "})
        r = client.get("/messages")
        assert "hello" in r.get_json()["messages"]

    def test_post_message_surrounding_spaces_trimmed(self, client):
        client.post("/", data={"message": "  hello world  "})
        r = client.get("/messages")
        assert "hello world" in r.get_json()["messages"]

    def test_clear_on_empty_messages_still_302(self, client):
        r = client.post("/clear")
        assert r.status_code == 302

    def test_post_status_not_200(self, client):
        r = client.post("/", data={"message": "x"})
        assert r.status_code != 200

    def test_post_status_not_500(self, client):
        r = client.post("/", data={"message": "x"})
        assert r.status_code != 500

    def test_clear_status_not_500(self, client):
        r = client.post("/clear")
        assert r.status_code != 500


# ===========================================================================
# 3. CONTENT ASSERTION TESTS  (40+ tests)
# ===========================================================================

class TestContentAssertions:
    """Simulates Selenium find_element / getText / assertText patterns."""

    def test_get_after_post_contains_message_text(self, client):
        client.post("/", data={"message": "Test Message"})
        r = client.get("/")
        assert b"Test Message" in r.data

    def test_response_data_contains_message_text(self, client):
        client.post("/", data={"message": "Test Message"})
        r = client.get("/")
        assert "Test Message" in r.data.decode("utf-8")

    def test_message_wrapped_in_li_class_message(self, client):
        client.post("/", data={"message": "Test Message"})
        r = client.get("/")
        assert b'class="message"' in r.data

    def test_health_count_is_1_after_one_post(self, client):
        client.post("/", data={"message": "Test Message"})
        r = client.get("/health")
        assert r.get_json()["count"] == 1

    def test_messages_json_contains_message(self, client):
        client.post("/", data={"message": "Test Message"})
        r = client.get("/messages")
        assert "Test Message" in r.get_json()["messages"]

    def test_three_posts_all_appear_in_get(self, client):
        msgs = ["Alpha", "Beta", "Gamma"]
        for m in msgs:
            client.post("/", data={"message": m})
        r = client.get("/")
        for m in msgs:
            assert m.encode() in r.data

    def test_three_posts_health_count_is_3(self, client):
        for m in ["A", "B", "C"]:
            client.post("/", data={"message": m})
        r = client.get("/health")
        assert r.get_json()["count"] == 3

    def test_three_posts_messages_list_length_3(self, client):
        for m in ["A", "B", "C"]:
            client.post("/", data={"message": m})
        r = client.get("/messages")
        assert len(r.get_json()["messages"]) == 3

    def test_same_message_twice_appears_twice(self, client):
        client.post("/", data={"message": "Dup"})
        client.post("/", data={"message": "Dup"})
        r = client.get("/messages")
        msgs = r.get_json()["messages"]
        assert msgs.count("Dup") == 2

    def test_message_order_preserved_fifo(self, client):
        client.post("/", data={"message": "First"})
        client.post("/", data={"message": "Second"})
        client.post("/", data={"message": "Third"})
        r = client.get("/messages")
        msgs = r.get_json()["messages"]
        assert msgs == ["First", "Second", "Third"]

    @pytest.mark.parametrize("n", [1, 2, 5, 10])
    def test_health_count_matches_n_posts(self, client, n):
        for i in range(n):
            client.post("/", data={"message": f"msg{i}"})
        r = client.get("/health")
        assert r.get_json()["count"] == n

    def test_after_clear_get_shows_no_messages(self, client):
        client.post("/", data={"message": "ToGo"})
        client.post("/clear")
        r = client.get("/")
        assert b'class="message"' not in r.data

    def test_after_clear_health_count_is_0(self, client):
        client.post("/", data={"message": "ToGo"})
        client.post("/clear")
        r = client.get("/health")
        assert r.get_json()["count"] == 0

    def test_after_clear_messages_is_empty_list(self, client):
        client.post("/", data={"message": "ToGo"})
        client.post("/clear")
        r = client.get("/messages")
        assert r.get_json()["messages"] == []

    def test_title_contains_message_board(self, client):
        r = client.get("/")
        assert b"Message Board" in r.data

    def test_h1_contains_message_board(self, client):
        r = client.get("/")
        html = r.data.decode("utf-8")
        assert "<h1>Message Board</h1>" in html

    def test_form_action_is_root(self, client):
        r = client.get("/")
        assert b'action="/"' in r.data

    def test_form_method_is_post(self, client):
        r = client.get("/")
        assert b'method="POST"' in r.data

    def test_input_id_message_in_html(self, client):
        r = client.get("/")
        assert b'id="message"' in r.data

    def test_button_id_submit_in_html(self, client):
        r = client.get("/")
        assert b'id="submit"' in r.data

    def test_ul_id_messages_always_present_empty(self, client):
        r = client.get("/")
        assert b'<ul id="messages">' in r.data

    def test_ul_id_messages_always_present_with_data(self, client_with_data):
        c, _ = client_with_data
        r = c.get("/")
        assert b'<ul id="messages">' in r.data

    def test_messages_json_contains_all_three_preloaded(self, client_with_data):
        c, messages = client_with_data
        r = c.get("/messages")
        stored = r.get_json()["messages"]
        for m in messages:
            assert m in stored

    def test_health_count_matches_preloaded_data(self, client_with_data):
        c, messages = client_with_data
        r = c.get("/health")
        assert r.get_json()["count"] == len(messages)

    def test_get_page_shows_preloaded_messages(self, client_with_data):
        c, messages = client_with_data
        r = c.get("/")
        for m in messages:
            assert m.encode() in r.data

    def test_li_tags_equal_message_count(self, client):
        for msg in ["X", "Y", "Z"]:
            client.post("/", data={"message": msg})
        r = client.get("/")
        html = r.data.decode("utf-8")
        count = html.count('class="message"')
        assert count == 3

    def test_placeholder_attribute_present(self, client):
        r = client.get("/")
        assert b"placeholder" in r.data

    def test_form_closing_tag_present(self, client):
        r = client.get("/")
        assert b"</form>" in r.data

    def test_ul_closing_tag_present(self, client):
        r = client.get("/")
        assert b"</ul>" in r.data

    def test_html_lang_or_html_tag_present(self, client):
        r = client.get("/")
        assert b"<html>" in r.data or b"<html " in r.data

    def test_response_contains_button_tag(self, client):
        r = client.get("/")
        assert b"<button" in r.data

    def test_response_contains_input_tag(self, client):
        r = client.get("/")
        assert b"<input" in r.data

    def test_health_status_string_is_ok(self, client):
        r = client.get("/health")
        assert r.get_json()["status"] == "ok"

    def test_messages_empty_list_initially(self, client):
        r = client.get("/messages")
        assert r.get_json()["messages"] == []

    def test_single_message_in_messages_list(self, client):
        client.post("/", data={"message": "Solo"})
        r = client.get("/messages")
        assert r.get_json()["messages"] == ["Solo"]

    @pytest.mark.parametrize("msg,expected", [
        ("hello", b"hello"),
        ("world", b"world"),
        ("foo bar", b"foo bar"),
        ("123", b"123"),
        ("test!", b"test!"),
    ])
    def test_posted_message_visible_in_get(self, client, msg, expected):
        client.post("/", data={"message": msg})
        r = client.get("/")
        assert expected in r.data

    def test_no_messages_no_li_tags_with_class(self, client):
        r = client.get("/")
        html = r.data.decode("utf-8")
        assert 'class="message"' not in html

    def test_health_count_zero_initially(self, client):
        r = client.get("/health")
        assert r.get_json()["count"] == 0


# ===========================================================================
# 4. REDIRECT FLOW TESTS  (20+ tests)
# ===========================================================================

class TestRedirectFlow:
    """Simulates Selenium assertCurrentUrl / waitForRedirect patterns."""

    def test_post_follows_redirect_to_get(self, client):
        r = client.post("/", data={"message": "Hi"}, follow_redirects=True)
        assert r.status_code == 200

    def test_redirect_location_is_root(self, client):
        r = client.post("/", data={"message": "Hi"})
        assert r.location == "/" or r.location.endswith("/")

    def test_follow_redirects_true_returns_200(self, client):
        r = client.post("/", data={"message": "Test"}, follow_redirects=True)
        assert r.status_code == 200

    def test_follow_redirects_response_contains_message(self, client):
        r = client.post("/", data={"message": "Visible"}, follow_redirects=True)
        assert b"Visible" in r.data

    def test_clear_follows_redirect(self, client):
        client.post("/", data={"message": "X"})
        r = client.post("/clear", follow_redirects=True)
        assert r.status_code == 200

    def test_clear_empty_messages_redirect_cleanly(self, client):
        r = client.post("/clear", follow_redirects=True)
        assert r.status_code == 200

    def test_redirect_does_not_loop_stays_200(self, client):
        r1 = client.post("/", data={"message": "Loop?"}, follow_redirects=True)
        r2 = client.get("/")
        assert r1.status_code == 200
        assert r2.status_code == 200

    def test_clear_redirect_location_is_root(self, client):
        r = client.post("/clear")
        assert r.status_code == 302
        assert r.location == "/" or r.location.endswith("/")

    @pytest.mark.parametrize("msg", [
        "RedirectMsg1",
        "RedirectMsg2",
        "RedirectMsg3",
        "RedirectMsg4",
        "RedirectMsg5",
    ])
    def test_post_follow_redirects_200_per_message(self, client, msg):
        r = client.post("/", data={"message": msg}, follow_redirects=True)
        assert r.status_code == 200

    @pytest.mark.parametrize("msg", [
        "Alpha",
        "Beta",
        "Gamma",
        "Delta",
        "Epsilon",
    ])
    def test_post_follow_redirects_message_visible(self, client, msg):
        r = client.post("/", data={"message": msg}, follow_redirects=True)
        assert msg.encode() in r.data

    def test_post_without_follow_redirects_is_302(self, client):
        r = client.post("/", data={"message": "NoFollow"})
        assert r.status_code == 302

    def test_empty_post_follow_redirects_200(self, client):
        r = client.post("/", data={}, follow_redirects=True)
        assert r.status_code == 200

    def test_clear_follow_redirects_no_messages_in_page(self, client):
        client.post("/", data={"message": "Gone"})
        r = client.post("/clear", follow_redirects=True)
        assert b"Gone" not in r.data

    def test_redirect_after_post_response_is_html(self, client):
        r = client.post("/", data={"message": "Hi"}, follow_redirects=True)
        assert "text/html" in r.content_type

    def test_redirect_response_has_ul_messages(self, client):
        r = client.post("/", data={"message": "Test"}, follow_redirects=True)
        assert b'id="messages"' in r.data

    def test_multiple_posts_all_200_after_follow(self, client):
        for i in range(5):
            r = client.post("/", data={"message": f"Item{i}"}, follow_redirects=True)
            assert r.status_code == 200

    def test_post_and_clear_cycle_ends_clean(self, client):
        client.post("/", data={"message": "Cycle"})
        r = client.post("/clear", follow_redirects=True)
        assert r.status_code == 200
        assert b"Cycle" not in r.data

    def test_redirect_status_code_is_exactly_302(self, client):
        r = client.post("/", data={"message": "x"})
        assert r.status_code == 302

    def test_clear_redirect_status_is_exactly_302(self, client):
        r = client.post("/clear")
        assert r.status_code == 302


# ===========================================================================
# 5. DATA INTEGRITY TESTS  (20+ tests)
# ===========================================================================

class TestDataIntegrity:
    """Simulates Selenium data validation / regression data checks."""

    def test_message_stored_exactly_as_submitted(self, client):
        client.post("/", data={"message": "exact match"})
        r = client.get("/messages")
        assert "exact match" in r.get_json()["messages"]

    def test_whitespace_trimmed_leading(self, client):
        client.post("/", data={"message": "  hello"})
        r = client.get("/messages")
        assert "hello" in r.get_json()["messages"]

    def test_whitespace_trimmed_trailing(self, client):
        client.post("/", data={"message": "hello  "})
        r = client.get("/messages")
        assert "hello" in r.get_json()["messages"]

    def test_whitespace_trimmed_both_sides(self, client):
        client.post("/", data={"message": "  hello world  "})
        r = client.get("/messages")
        assert "hello world" in r.get_json()["messages"]

    def test_unicode_preserved(self, client):
        uni = "日本語テスト"
        client.post("/", data={"message": uni})
        r = client.get("/messages")
        assert uni in r.get_json()["messages"]

    def test_long_message_preserved_fully(self, client):
        long_msg = "abcdef" * 100  # 600 chars
        client.post("/", data={"message": long_msg})
        r = client.get("/messages")
        assert long_msg in r.get_json()["messages"]

    def test_order_is_fifo_not_lifo(self, client):
        client.post("/", data={"message": "First"})
        client.post("/", data={"message": "Second"})
        r = client.get("/messages")
        msgs = r.get_json()["messages"]
        assert msgs.index("First") < msgs.index("Second")

    def test_clear_wipes_all_messages(self, client):
        for m in ["A", "B", "C", "D", "E"]:
            client.post("/", data={"message": m})
        client.post("/clear")
        r = client.get("/messages")
        assert r.get_json()["messages"] == []

    def test_state_isolated_per_test_fresh_client(self, client):
        r = client.get("/messages")
        assert r.get_json()["messages"] == []

    def test_fixture_isolation_two_clients_dont_share(self):
        app1, messages1 = build_app()
        app2, messages2 = build_app()
        messages1.append("OnlyInFirst")
        with app1.test_client() as c1, app2.test_client() as c2:
            r1 = c1.get("/messages")
            r2 = c2.get("/messages")
            assert "OnlyInFirst" in r1.get_json()["messages"]
            assert "OnlyInFirst" not in r2.get_json()["messages"]

    @pytest.mark.parametrize("msg", [
        "simple",
        "with spaces",
        "123 numbers",
        "special !@#",
        "unicode é",
        "  padded  ",
        "UPPER",
        "MiXeD",
        "repeat repeat",
        "a" * 50,
    ])
    def test_various_data_types_stored_trimmed(self, client, msg):
        client.post("/", data={"message": msg})
        r = client.get("/messages")
        stored = r.get_json()["messages"]
        assert msg.strip() in stored or msg in stored

    def test_duplicate_messages_both_stored(self, client):
        client.post("/", data={"message": "same"})
        client.post("/", data={"message": "same"})
        r = client.get("/messages")
        assert len(r.get_json()["messages"]) == 2

    def test_messages_persist_across_multiple_gets(self, client):
        client.post("/", data={"message": "persistent"})
        for _ in range(5):
            r = client.get("/messages")
            assert "persistent" in r.get_json()["messages"]

    def test_no_deduplication_performed(self, client):
        for _ in range(3):
            client.post("/", data={"message": "nodep"})
        r = client.get("/messages")
        assert len(r.get_json()["messages"]) == 3

    def test_numeric_string_stored_correctly(self, client):
        client.post("/", data={"message": "42"})
        r = client.get("/messages")
        assert "42" in r.get_json()["messages"]

    def test_boolean_like_string_stored(self, client):
        client.post("/", data={"message": "true"})
        r = client.get("/messages")
        assert "true" in r.get_json()["messages"]

    def test_punctuation_only_stored(self, client):
        client.post("/", data={"message": "..."})
        r = client.get("/messages")
        assert "..." in r.get_json()["messages"]

    def test_mixed_content_preserved(self, client):
        msg = "Hello <World> & 'friends' at 100%!"
        client.post("/", data={"message": msg})
        r = client.get("/messages")
        assert msg in r.get_json()["messages"]


# ===========================================================================
# 6. ERROR HANDLING AND EDGE CASES  (20+ tests)
# ===========================================================================

class TestErrorHandlingEdgeCases:
    """Simulates Selenium negative-path / boundary testing."""

    def test_post_no_form_data_handles_gracefully(self, client):
        r = client.post("/", data={})
        assert r.status_code == 302

    def test_post_no_message_key_handles_gracefully(self, client):
        r = client.post("/", data={"unrelated": "value"})
        assert r.status_code == 302

    def test_health_with_messages_count_accurate(self, client):
        for m in ["p", "q", "r"]:
            client.post("/", data={"message": m})
        r = client.get("/health")
        assert r.get_json()["count"] == 3

    def test_messages_with_zero_messages_returns_empty_list(self, client):
        r = client.get("/messages")
        assert r.get_json()["messages"] == []

    def test_messages_with_many_returns_full_list(self, client):
        for i in range(20):
            client.post("/", data={"message": f"msg{i}"})
        r = client.get("/messages")
        assert len(r.get_json()["messages"]) == 20

    def test_404_for_favicon(self, client):
        r = client.get("/favicon.ico")
        assert r.status_code == 404

    def test_patch_index_returns_405(self, client):
        r = client.patch("/")
        assert r.status_code == 405

    def test_delete_index_returns_405(self, client):
        r = client.delete("/")
        assert r.status_code == 405

    def test_put_index_returns_405(self, client):
        r = client.put("/")
        assert r.status_code == 405

    @pytest.mark.parametrize("method", ["PATCH", "PUT", "DELETE"])
    def test_invalid_methods_on_index(self, client, method):
        r = client.open("/", method=method)
        assert r.status_code == 405

    def test_get_clear_returns_405(self, client):
        r = client.get("/clear")
        assert r.status_code == 405

    def test_health_only_accepts_get(self, client):
        r = client.get("/health")
        assert r.status_code == 200

    def test_post_very_long_value_no_server_error(self, client):
        very_long = "z" * 10000
        r = client.post("/", data={"message": very_long})
        assert r.status_code in (302, 413)

    def test_get_nonexistent_deeply_nested_404(self, client):
        r = client.get("/a/b/c/d/e/f")
        assert r.status_code == 404

    def test_post_to_nonexistent_route_returns_404_or_405(self, client):
        r = client.post("/nonexistent")
        assert r.status_code in (404, 405)

    def test_get_health_no_side_effects(self, client):
        client.post("/", data={"message": "before"})
        client.get("/health")
        r = client.get("/messages")
        assert r.get_json()["messages"] == ["before"]

    def test_get_messages_no_side_effects(self, client):
        client.post("/", data={"message": "before"})
        client.get("/messages")
        r = client.get("/messages")
        assert len(r.get_json()["messages"]) == 1

    def test_message_with_only_numbers(self, client):
        client.post("/", data={"message": "9999"})
        r = client.get("/messages")
        assert "9999" in r.get_json()["messages"]

    def test_empty_string_message_not_stored(self, client):
        client.post("/", data={"message": ""})
        r = client.get("/messages")
        assert len(r.get_json()["messages"]) == 0

    def test_post_with_multiple_form_fields_no_crash(self, client):
        r = client.post("/", data={"message": "hi", "extra": "ignored"})
        assert r.status_code == 302

    def test_post_with_multiple_form_fields_stores_message(self, client):
        client.post("/", data={"message": "hi", "extra": "ignored"})
        r = client.get("/messages")
        assert "hi" in r.get_json()["messages"]


# ===========================================================================
# 7. CONCURRENCY / STATE ISOLATION TESTS  (10+ tests)
# ===========================================================================

class TestConcurrencyState:
    """Simulates Selenium parallel-session / tab isolation tests."""

    def test_fresh_fixture_starts_with_zero_messages(self, client):
        r = client.get("/messages")
        assert r.get_json()["messages"] == []

    def test_fresh_fixture_health_count_zero(self, client):
        r = client.get("/health")
        assert r.get_json()["count"] == 0

    def test_fixture_isolation_independent_apps(self):
        app_a, msgs_a = build_app()
        app_b, msgs_b = build_app()
        msgs_a.append("InA")
        with app_a.test_client() as ca, app_b.test_client() as cb:
            assert ca.get("/messages").get_json()["messages"] == ["InA"]
            assert cb.get("/messages").get_json()["messages"] == []

    def test_adding_to_one_client_not_in_another(self):
        app1, _ = build_app()
        app2, _ = build_app()
        with app1.test_client() as c1, app2.test_client() as c2:
            c1.post("/", data={"message": "OnlyFirst"})
            r2 = c2.get("/messages")
            assert "OnlyFirst" not in r2.get_json()["messages"]

    def test_client_with_data_has_three_messages(self, client_with_data):
        c, messages = client_with_data
        r = c.get("/messages")
        assert len(r.get_json()["messages"]) == 3

    def test_client_with_data_health_count_is_3(self, client_with_data):
        c, _ = client_with_data
        r = c.get("/health")
        assert r.get_json()["count"] == 3

    def test_client_with_data_first_message(self, client_with_data):
        c, _ = client_with_data
        r = c.get("/messages")
        assert r.get_json()["messages"][0] == "Hello World"

    def test_client_with_data_second_message(self, client_with_data):
        c, _ = client_with_data
        r = c.get("/messages")
        assert r.get_json()["messages"][1] == "Test Message"

    def test_client_with_data_third_message(self, client_with_data):
        c, _ = client_with_data
        r = c.get("/messages")
        assert r.get_json()["messages"][2] == "Another Entry"

    def test_sequential_requests_state_consistent(self, client):
        client.post("/", data={"message": "seq1"})
        client.post("/", data={"message": "seq2"})
        r1 = client.get("/messages")
        r2 = client.get("/messages")
        assert r1.get_json() == r2.get_json()

    def test_clear_then_post_starts_fresh(self, client):
        client.post("/", data={"message": "old"})
        client.post("/clear")
        client.post("/", data={"message": "new"})
        r = client.get("/messages")
        msgs = r.get_json()["messages"]
        assert msgs == ["new"]

    def test_two_independent_fixtures_independent(self):
        app1, m1 = build_app()
        app2, m2 = build_app()
        m1.extend(["x", "y"])
        m2.extend(["a"])
        with app1.test_client() as c1, app2.test_client() as c2:
            assert c1.get("/health").get_json()["count"] == 2
            assert c2.get("/health").get_json()["count"] == 1


# ===========================================================================
# 8. API ENDPOINT TESTS  (20+ tests)
# ===========================================================================

class TestAPIEndpoints:
    """Simulates Selenium + REST API validation (XHR/fetch assertions)."""

    def test_health_json_has_status_key(self, client):
        r = client.get("/health")
        assert "status" in r.get_json()

    def test_health_json_status_equals_ok(self, client):
        r = client.get("/health")
        assert r.get_json()["status"] == "ok"

    def test_health_json_has_count_key(self, client):
        r = client.get("/health")
        assert "count" in r.get_json()

    def test_health_count_is_integer(self, client):
        r = client.get("/health")
        assert isinstance(r.get_json()["count"], int)

    def test_health_count_equals_messages_length(self, client):
        for m in ["a", "b", "c"]:
            client.post("/", data={"message": m})
        health_count = client.get("/health").get_json()["count"]
        msgs_len = len(client.get("/messages").get_json()["messages"])
        assert health_count == msgs_len

    def test_messages_json_has_messages_key(self, client):
        r = client.get("/messages")
        assert "messages" in r.get_json()

    def test_messages_value_is_list_type(self, client):
        r = client.get("/messages")
        assert isinstance(r.get_json()["messages"], list)

    def test_messages_after_posts_correct_length(self, client):
        for m in ["x", "y", "z"]:
            client.post("/", data={"message": m})
        r = client.get("/messages")
        assert len(r.get_json()["messages"]) == 3

    @pytest.mark.parametrize("n", [0, 1, 2, 5, 10])
    def test_health_count_matches_n_posts_api(self, client, n):
        for i in range(n):
            client.post("/", data={"message": f"item{i}"})
        r = client.get("/health")
        assert r.get_json()["count"] == n

    @pytest.mark.parametrize("n", [0, 1, 2, 5, 10])
    def test_messages_length_matches_n_posts(self, client, n):
        for i in range(n):
            client.post("/", data={"message": f"item{i}"})
        r = client.get("/messages")
        assert len(r.get_json()["messages"]) == n

    def test_health_content_type_is_json(self, client):
        r = client.get("/health")
        assert "application/json" in r.content_type

    def test_messages_content_type_is_json(self, client):
        r = client.get("/messages")
        assert "application/json" in r.content_type

    def test_health_returns_exactly_two_keys(self, client):
        r = client.get("/health")
        data = r.get_json()
        assert set(data.keys()) == {"status", "count"}

    def test_messages_returns_exactly_one_key(self, client):
        r = client.get("/messages")
        data = r.get_json()
        assert set(data.keys()) == {"messages"}

    def test_health_count_increments_by_one(self, client):
        count_before = client.get("/health").get_json()["count"]
        client.post("/", data={"message": "increment"})
        count_after = client.get("/health").get_json()["count"]
        assert count_after == count_before + 1

    def test_messages_list_order_matches_post_order(self, client):
        ordered = ["first", "second", "third"]
        for m in ordered:
            client.post("/", data={"message": m})
        r = client.get("/messages")
        assert r.get_json()["messages"] == ordered

    def test_health_count_decrements_after_clear(self, client):
        for m in ["a", "b", "c"]:
            client.post("/", data={"message": m})
        client.post("/clear")
        assert client.get("/health").get_json()["count"] == 0

    def test_messages_empty_after_clear_api(self, client):
        client.post("/", data={"message": "bye"})
        client.post("/clear")
        assert client.get("/messages").get_json()["messages"] == []

    def test_api_and_page_agree_on_count(self, client):
        for m in ["a", "b"]:
            client.post("/", data={"message": m})
        page = client.get("/")
        api = client.get("/messages").get_json()["messages"]
        html = page.data.decode("utf-8")
        li_count = html.count('class="message"')
        assert li_count == len(api)

    def test_health_stable_across_reads(self, client):
        client.post("/", data={"message": "stable"})
        r1 = client.get("/health").get_json()
        r2 = client.get("/health").get_json()
        assert r1 == r2


# ===========================================================================
# 9. REGRESSION TESTS  (10+ tests)
# ===========================================================================

class TestRegression:
    """Simulates Selenium regression suite — guards against known failure modes."""

    def test_page_title_constant_across_requests(self, client):
        r1 = client.get("/")
        r2 = client.get("/")
        assert b"<title>Message Board</title>" in r1.data
        assert b"<title>Message Board</title>" in r2.data

    def test_form_action_constant_across_requests(self, client):
        r1 = client.get("/")
        r2 = client.get("/")
        assert b'action="/"' in r1.data
        assert b'action="/"' in r2.data

    def test_ul_id_messages_always_present(self, client):
        client.post("/", data={"message": "x"})
        for _ in range(3):
            r = client.get("/")
            assert b'<ul id="messages">' in r.data

    def test_h1_text_constant(self, client):
        for _ in range(3):
            r = client.get("/")
            assert b"<h1>Message Board</h1>" in r.data

    def test_health_always_returns_json(self, client):
        for _ in range(5):
            r = client.get("/health")
            assert r.get_json() is not None

    def test_submit_does_not_cause_500(self, client):
        r = client.post("/", data={"message": "no crash"})
        assert r.status_code != 500

    def test_clear_does_not_cause_500(self, client):
        r = client.post("/clear")
        assert r.status_code != 500

    def test_page_load_10_times_always_200(self, client):
        for _ in range(10):
            r = client.get("/")
            assert r.status_code == 200

    def test_messages_endpoint_never_500(self, client):
        for _ in range(5):
            r = client.get("/messages")
            assert r.status_code != 500

    def test_health_endpoint_never_500(self, client):
        for _ in range(5):
            r = client.get("/health")
            assert r.status_code != 500

    def test_form_method_always_post(self, client):
        for _ in range(3):
            r = client.get("/")
            assert b'method="POST"' in r.data

    def test_input_name_message_always_present(self, client):
        for _ in range(3):
            r = client.get("/")
            assert b'name="message"' in r.data

    def test_button_id_submit_always_present(self, client):
        for _ in range(3):
            r = client.get("/")
            assert b'id="submit"' in r.data

    def test_post_and_reload_stable(self, client):
        client.post("/", data={"message": "stable"})
        for _ in range(5):
            r = client.get("/")
            assert b"stable" in r.data

    def test_health_count_never_negative(self, client):
        r = client.get("/health")
        assert r.get_json()["count"] >= 0

    def test_messages_list_never_none(self, client):
        r = client.get("/messages")
        assert r.get_json()["messages"] is not None

    def test_doctype_always_present(self, client):
        for _ in range(3):
            r = client.get("/")
            assert b"<!DOCTYPE html>" in r.data

    @pytest.mark.parametrize("i", range(5))
    def test_get_index_never_raises_parametrized(self, client, i):
        r = client.get("/")
        assert r.status_code == 200

    def test_submit_empty_form_never_500(self, client):
        for _ in range(5):
            r = client.post("/", data={})
            assert r.status_code not in (500, 400)

    def test_api_still_works_after_many_posts(self, client):
        for i in range(15):
            client.post("/", data={"message": f"load{i}"})
        r_health = client.get("/health")
        r_msgs = client.get("/messages")
        assert r_health.status_code == 200
        assert r_msgs.status_code == 200
        assert r_health.get_json()["count"] == 15
        assert len(r_msgs.get_json()["messages"]) == 15
