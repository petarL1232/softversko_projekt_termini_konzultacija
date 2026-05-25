from pathlib import Path

STATIC_DIR = Path(__file__).resolve().parents[1] / "app" / "static"


def read_static_file(name: str) -> str:
    return (STATIC_DIR / name).read_text(encoding="utf-8")


def test_admin_role_management_ui_uses_auth_users_endpoints() -> None:
    script = read_static_file("termini_admin.js")

    assert 'safeApiFetch("/auth/users")' in script
    assert "safeApiFetch(`/auth/users/${userId}/role`, {" in script
    assert 'method: "PATCH"' in script


def test_admin_role_management_ui_contains_required_controls() -> None:
    script = read_static_file("termini_admin.js")

    assert "Upravljanje korisnicima" in script
    assert "student" in script
    assert "professor" in script
    assert "admin" in script
    assert "office_id" in script
    assert "spremiKorisnickuRolu" in script
