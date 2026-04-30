from datetime import date
from pathlib import Path

import pytest

from brain_code.config import Settings
from brain_code.extractors import movie

OMDB_INCEPTION = {
    "title": "Inception",
    "year": 2010,
    "type": "movie",
    "imdb_id": "tt1375666",
    "imdb_rating": "8.8",
    "runtime": "148 min",
    "poster": "https://example.com/inception.jpg",
    "directors": ["Christopher Nolan"],
    "genres": ["Action", "Adventure", "Sci-Fi"],
    "actors": ["Leonardo DiCaprio", "Joseph Gordon-Levitt", "Elliot Page"],
    "plot": "A thief who steals corporate secrets.",
}

OMDB_SEVERANCE = {
    "title": "Severance",
    "year": 2022,
    "type": "series",
    "imdb_id": "tt11280740",
    "imdb_rating": "8.7",
    "runtime": "60 min",
    "poster": "https://example.com/severance.jpg",
    "directors": ["Ben Stiller"],
    "genres": ["Drama", "Mystery", "Sci-Fi"],
    "actors": ["Adam Scott", "Britt Lower"],
    "plot": "Workers split memories between work and personal life.",
}


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    vault = tmp_path / "vault"
    (vault / "01 Area/Tvs and Movies").mkdir(parents=True)
    return Settings(
        vault_root=vault,
        project_root=tmp_path / "project",
        api_key=None,
    )


def test_ensure_file_creates_movie_with_omdb_metadata(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr("brain_code.extractors.movie.omdb.lookup", lambda *a, **kw: OMDB_INCEPTION)
    was_created, canonical, omdb_data = movie.ensure_file("inception", settings)
    assert was_created is True
    assert canonical == "Inception"
    file_path = settings.vault_root / "01 Area/Tvs and Movies/Inception.md"
    assert file_path.exists()
    content = file_path.read_text(encoding="utf-8")
    assert 'category: "[[Movies]]"' in content
    assert 'imdbId: "tt1375666"' in content
    assert 'scoreImdb: "8.8"' in content
    assert '  - "[[Christopher Nolan]]"' in content
    assert '  - "[[Action]]"' in content
    assert '  - "[[Leonardo DiCaprio]]"' in content
    assert "year: 2010" in content
    assert "  - movies\n  - watched" in content
    assert "# [[Inception]]" in content
    assert "## Watches" in content


def test_ensure_file_uses_canonical_title_from_omdb(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr("brain_code.extractors.movie.omdb.lookup", lambda *a, **kw: OMDB_INCEPTION)
    was_created, canonical, _ = movie.ensure_file("Inseption typo", settings)
    # OMDB normalized to "Inception", file uses canonical
    assert canonical == "Inception"
    assert (settings.vault_root / "01 Area/Tvs and Movies/Inception.md").exists()


def test_ensure_file_creates_tv_show_with_tv_tags(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr("brain_code.extractors.movie.omdb.lookup", lambda *a, **kw: OMDB_SEVERANCE)
    was_created, canonical, _ = movie.ensure_file("Severance", settings, kind_hint="tv")
    assert was_created is True
    file_path = settings.vault_root / "01 Area/Tvs and Movies/Severance.md"
    content = file_path.read_text(encoding="utf-8")
    assert 'category: "[[TV Shows]]"' in content
    assert "  - tv-shows\n  - watched" in content


def test_ensure_file_minimal_stub_when_omdb_unavailable(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr("brain_code.extractors.movie.omdb.lookup", lambda *a, **kw: None)
    was_created, canonical, omdb_data = movie.ensure_file("Some Obscure Movie", settings)
    assert was_created is True
    assert omdb_data is None
    file_path = settings.vault_root / "01 Area/Tvs and Movies/Some Obscure Movie.md"
    content = file_path.read_text(encoding="utf-8")
    assert "# [[Some Obscure Movie]]" in content
    assert "## Watches" in content
    assert "rating:" in content


def test_ensure_file_idempotent(settings: Settings, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("brain_code.extractors.movie.omdb.lookup", lambda *a, **kw: OMDB_INCEPTION)
    movie.ensure_file("Inception", settings)
    was_created, _, _ = movie.ensure_file("Inception", settings)
    assert was_created is False


def test_append_watch_writes_block_and_updates_rating(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr("brain_code.extractors.movie.omdb.lookup", lambda *a, **kw: OMDB_INCEPTION)
    movie.ensure_file("Inception", settings)
    log = {"type": "movie_watched", "entity": "Inception", "kind": "movie", "rating": 9}
    msg = movie.append_watch("Inception", log, settings, date(2026, 4, 30), was_created=True)
    file_path = settings.vault_root / "01 Area/Tvs and Movies/Inception.md"
    content = file_path.read_text(encoding="utf-8")
    assert "### 2026-04-30" in content
    assert "- Rating: 9/10" in content
    # rating field in frontmatter should be updated to 9
    assert "rating: 9" in content
    assert "🆕" in msg


def test_append_watch_tv_with_season(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr("brain_code.extractors.movie.omdb.lookup", lambda *a, **kw: OMDB_SEVERANCE)
    movie.ensure_file("Severance", settings, kind_hint="tv")
    log = {
        "type": "movie_watched",
        "entity": "Severance",
        "kind": "tv",
        "season": 2,
        "episode": 5,
        "notes": "wow that ending",
    }
    msg = movie.append_watch("Severance", log, settings, date(2026, 4, 30), was_created=False)
    file_path = settings.vault_root / "01 Area/Tvs and Movies/Severance.md"
    content = file_path.read_text(encoding="utf-8")
    assert "- Season: 2" in content
    assert "- Episode: 5" in content
    assert "- wow that ending" in content
    assert "show watched" in msg
    assert "🎬" in msg


def test_append_watch_no_rating_no_overall(settings: Settings, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("brain_code.extractors.movie.omdb.lookup", lambda *a, **kw: OMDB_INCEPTION)
    movie.ensure_file("Inception", settings)
    log = {"type": "movie_watched", "entity": "Inception"}
    msg = movie.append_watch("Inception", log, settings, date(2026, 4, 30), was_created=False)
    assert "no rating" in msg
    file_path = settings.vault_root / "01 Area/Tvs and Movies/Inception.md"
    content = file_path.read_text(encoding="utf-8")
    assert "### 2026-04-30" in content
    # rating field should not have been modified
    assert "rating:\n" in content or "rating: \n" in content


def test_append_watch_preserves_existing_watches(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr("brain_code.extractors.movie.omdb.lookup", lambda *a, **kw: OMDB_INCEPTION)
    movie.ensure_file("Inception", settings)
    movie.append_watch(
        "Inception",
        {"type": "movie_watched", "entity": "Inception", "rating": 8},
        settings,
        date(2026, 3, 1),
        was_created=True,
    )
    movie.append_watch(
        "Inception",
        {"type": "movie_watched", "entity": "Inception", "rating": 10},
        settings,
        date(2026, 4, 30),
        was_created=False,
    )
    file_path = settings.vault_root / "01 Area/Tvs and Movies/Inception.md"
    content = file_path.read_text(encoding="utf-8")
    assert "### 2026-03-01" in content
    assert "### 2026-04-30" in content
    # rating field reflects the latest watch
    assert "rating: 10" in content
