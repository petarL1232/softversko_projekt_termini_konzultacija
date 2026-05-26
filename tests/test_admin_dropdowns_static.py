from pathlib import Path

STATIC_DIR = Path(__file__).resolve().parents[1] / "app" / "static"


def read_static_file(name: str) -> str:
    return (STATIC_DIR / name).read_text(encoding="utf-8")


def test_admin_term_form_uses_professor_and_subject_dropdowns() -> None:
    script = read_static_file("termini_admin.js")

    assert "FZ-14 Admin dropdowns" in script
    assert 'safeApiFetch("/catalog/professors")' in script
    assert 'safeApiFetch("/catalog/subjects")' in script
    assert '<select id="f-prof">' in script
    assert '<select id="f-subj">' in script
    assert "Profesor ID<input" not in script
    assert "Predmet ID<input" not in script


def test_term_cards_show_human_names_instead_of_raw_ids() -> None:
    script = read_static_file("termini_admin.js")

    assert "professorName(term.professor_id)" in script
    assert "subjectName(term.subject_id)" in script
    assert "Pretraga po profesoru ili kolegiju" in script
