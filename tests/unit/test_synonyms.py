from app.services.synonyms import (
    find_term_in_text,
    normalize_text,
    build_synonym_lookup,
    create_word_boundary_regex,
)


def test_synonym_matching():
    text = "Proficient in JS, K8s, Postgres, and writing Docker containers."

    matched, term = find_term_in_text("javascript", text)
    assert matched
    assert term.lower() == "js"

    matched, term = find_term_in_text("kubernetes", text)
    assert matched
    assert term.lower() == "k8s"

    matched, term = find_term_in_text("postgresql", text)
    assert matched
    assert term.lower() == "postgres"


def test_word_boundary_safety():
    # 'c' should not match 'cloud' or 'clear'
    text = "We built a cloud architecture for clients."
    matched, _ = find_term_in_text("c", text)
    assert not matched

    # 'go' should not match 'good'
    text = "A good engineer with great communication."
    matched, _ = find_term_in_text("golang", text)
    assert not matched


def test_special_characters_in_tech_names():
    text = "Experienced in C++, C#, and .NET Core applications."

    matched, term = find_term_in_text("c++", text)
    assert matched

    matched, term = find_term_in_text("c#", text)
    assert matched

    matched, term = find_term_in_text(".net", text)
    assert matched


def test_text_normalization():
    raw = "Skills:\n\u2022 Python \u2013 5 years\n\u2022  FastAPI   and   Docker\u00a0\n"
    norm = normalize_text(raw)

    assert "\u2022" not in norm
    assert "\u00a0" not in norm
    assert "fastapi and docker" in norm
    assert "python - 5 years" in norm


def test_custom_synonym_map():
    custom = {"ruby": ["ror", "ruby on rails"]}
    lookup = build_synonym_lookup(custom)

    text = "Experienced building modern RoR applications."
    matched, term = find_term_in_text("ruby", text, synonym_map=lookup)
    assert matched
    assert term.lower() == "ror"
