from pathlib import Path

STATIC_DIR = Path(__file__).resolve().parents[1] / "app" / "static"


def read_static_file(name: str) -> str:
    return (STATIC_DIR / name).read_text(encoding="utf-8")


def test_office_catalog_endpoint_is_used_for_dropdowns() -> None:
    script = read_static_file("termini_admin.js")

    assert 'safeApiFetch("/catalog/offices")' in script
    assert "renderOfficeOptions" in script
    assert "Odaberi ured/prostoriju" in script


def test_term_cards_show_location_not_raw_office_id_label() -> None:
    script = read_static_file("termini_admin.js")

    assert "Lokacija:" in script
    assert "professorOffice(term.professor_id)" in script
    assert "Ured/prostorija" in script
