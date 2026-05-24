from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = PROJECT_ROOT / "app" / "static"


def read_static_file(file_name: str) -> str:
    return (STATIC_DIR / file_name).read_text(encoding="utf-8")


def test_auth_ui_contains_required_forms() -> None:
    html = read_static_file("index.html")

    assert 'id="register-form"' in html
    assert 'id="login-form"' in html
    assert 'id="current-user"' in html
    assert 'id="logout-button"' in html


def test_auth_ui_contains_current_user_in_navbar() -> None:
    html = read_static_file("index.html")

    assert 'id="navbar-current-user"' in html
    assert "Niste prijavljeni" in html


def test_auth_ui_has_no_get_login_form_action() -> None:
    html = read_static_file("index.html")

    assert 'action="/auth/login"' not in html
    assert 'method="get"' not in html.lower()


def test_auth_script_uses_oauth2_form_login() -> None:
    script = read_static_file("script.js")

    assert 'apiFormFetch("/auth/login", body)' in script
    assert '"application/x-www-form-urlencoded"' in script
    assert "URLSearchParams" in script
    assert 'body.set("username"' in script


def test_auth_script_prevents_native_form_submit() -> None:
    script = read_static_file("script.js")

    assert ".preventDefault()" in script
    assert "addEventListener" in script
    assert "submit" in script


def test_auth_script_stores_token_in_local_storage() -> None:
    script = read_static_file("script.js")

    assert "localStorage.setItem(TOKEN_STORAGE_KEY, token)" in script
    assert "localStorage.getItem(TOKEN_STORAGE_KEY)" in script
    assert "localStorage.removeItem(TOKEN_STORAGE_KEY)" in script
    assert 'apiFetch("/auth/me")' in script


def test_auth_script_updates_navbar_user_state() -> None:
    script = read_static_file("script.js")

    assert "navbarCurrentUser" in script
    assert "renderLoggedIn" in script
    assert "renderLoggedOut" in script
    assert "classList.add" in script
    assert "classList.remove" in script


def test_auth_script_does_not_send_password_through_query_string() -> None:
    script = read_static_file("script.js")

    assert "fetch(`/?email" not in script
    assert "window.location" not in script
    assert "URLSearchParams(window.location.search)" not in script


def test_auth_css_contains_navbar_user_pill_styles() -> None:
    css = read_static_file("style.css")

    assert ".user-pill" in css
    assert ".user-pill.logged-in" in css
