from pathlib import Path

import pytest

from brain_code.config import Settings
from brain_code.prompts import load_prompt, render


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    project = tmp_path / "project"
    (project / "prompts").mkdir(parents=True)
    (project / "prompts" / "test_static.md").write_text("hello world", encoding="utf-8")
    (project / "prompts" / "test_template.md.tmpl").write_text(
        "name: {{name}}, count: {{count}}",
        encoding="utf-8",
    )
    (project / "prompts" / "test_repeat.md.tmpl").write_text(
        "{{x}} and {{x}} again",
        encoding="utf-8",
    )
    return Settings(
        vault_root=tmp_path / "vault",
        project_root=project,
        api_key=None,
    )


def test_load_prompt_static(settings: Settings):
    assert load_prompt("test_static.md", settings) == "hello world"


def test_render_substitutes_vars(settings: Settings):
    out = render("test_template.md.tmpl", settings, name="khalifah", count="3")
    assert out == "name: khalifah, count: 3"


def test_render_replaces_all_occurrences(settings: Settings):
    out = render("test_repeat.md.tmpl", settings, x="foo")
    assert out == "foo and foo again"


def test_render_unknown_placeholder_left_intact(settings: Settings):
    out = render("test_template.md.tmpl", settings, name="x")
    # {{count}} not provided — should remain as-is
    assert "{{count}}" in out


def test_render_no_vars(settings: Settings):
    out = render("test_static.md", settings)
    assert out == "hello world"


def test_real_prompts_exist():
    """Sanity: the actual prompt files we shipped are loadable."""
    from brain_code.config import load_settings

    s = load_settings()
    for name in [
        "append_system.md",
        "append_user.md.tmpl",
        "synthesize_system.md",
        "synthesize_cached.md.tmpl",
        "synthesize_user.md.tmpl",
    ]:
        content = load_prompt(name, s)
        assert content.strip(), f"{name} is empty"
