from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = PROJECT_ROOT / "app" / "static"


def read_static_file(filename: str) -> str:
    return (STATIC_DIR / filename).read_text(encoding="utf-8")


def test_index_loads_termini_admin_assets_after_auth_script() -> None:
    html = read_static_file("index.html")

    assert "/static/script.js" in html
    assert "/static/termini_admin.js" in html
    assert "/static/termini_admin.css" in html
    assert html.index("/static/script.js") < html.index("/static/termini_admin.js")


def test_termini_admin_ui_uses_signup_endpoints() -> None:
    script = read_static_file("termini_admin.js")

    assert "safeApiFetch(`/termini/${termId}/prijava`" in script
    assert 'method: "POST"' in script
    assert 'method: "DELETE"' in script
    assert 'safeApiFetch("/me/prijave")' in script


def test_termini_admin_ui_keeps_admin_crud_endpoints() -> None:
    script = read_static_file("termini_admin.js")

    assert 'safeApiFetch("/termini")' in script
    assert 'safeApiFetch("/termini", {' in script
    assert 'method: "PUT"' in script
    assert 'method: "DELETE"' in script
    assert "renderAdminSection" in script


def test_termini_admin_css_contains_signup_classes() -> None:
    css = read_static_file("termini_admin.css")

    assert ".termin-card" in css
    assert ".is-registered" in css
    assert ".my-registrations-box" in css
    assert ".danger-button" in css
