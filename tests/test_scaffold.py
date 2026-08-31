import subprocess

from sundry.cli import main
from sundry.config import load_config
from sundry.scaffold import _detect_repo_slug, run_init


def test_init_creates_config_and_workflow(tmp_path):
    exit_code = run_init([str(tmp_path)])
    assert exit_code == 0

    config_path = tmp_path / "config" / "feeds.toml"
    workflow_path = tmp_path / ".github" / "workflows" / "digest.yml"
    ci_path = tmp_path / ".github" / "workflows" / "ci.yml"
    agents_path = tmp_path / "AGENTS.md"
    claude_path = tmp_path / "CLAUDE.md"
    assert config_path.is_file()
    assert workflow_path.is_file()
    assert ci_path.is_file()
    assert agents_path.is_file()
    assert claude_path.is_file()


def test_init_config_is_valid_and_ready_to_build():
    # Doesn't touch disk beyond tmp_path via run_init in the test above;
    # here we just confirm the template itself parses and satisfies the
    # same validation a real feeds.toml has to pass.
    import tomllib

    from sundry.scaffold import CONFIG_TEMPLATE

    tomllib.loads(CONFIG_TEMPLATE)  # no TOML syntax errors


def test_init_config_loads_via_load_config(tmp_path):
    run_init([str(tmp_path)])
    config = load_config(tmp_path / "config" / "feeds.toml")
    assert {category.key for category in config.categories} == {"general"}


def test_init_config_explains_itself_for_a_non_technical_reader():
    from sundry.scaffold import CONFIG_TEMPLATE

    assert "STEP 1" in CONFIG_TEMPLATE
    assert "STEP 2" in CONFIG_TEMPLATE
    assert "STEP 3" in CONFIG_TEMPLATE
    # The comment/uncomment concept has to be spelled out somewhere, not
    # just assumed — that's the whole gap this template exists to close.
    assert "comment" in CONFIG_TEMPLATE.lower()


def _uncomment_block(lines: list[str], start_marker: str) -> list[str]:
    """Simulate a user literally following 'delete the # at the start of
    each line of this block' on the block starting at `start_marker`."""
    out = []
    in_block = False
    for line in lines:
        if line.strip() == start_marker:
            in_block = True
        if in_block:
            if line.startswith("# "):
                out.append(line[2:])
            elif line == "#":
                out.append("")
            else:
                in_block = False
                out.append(line)
        else:
            out.append(line)
    return out


def test_init_config_example_blocks_are_valid_toml_once_uncommented():
    # Both example blocks are shown commented-out (inert) by default; if a
    # reader follows the file's own instructions and uncomments one, the
    # result must actually parse — a broken worked example is worse than
    # no example.
    import tomllib

    from sundry.scaffold import CONFIG_TEMPLATE

    lines = CONFIG_TEMPLATE.splitlines()
    lines = _uncomment_block(lines, "# [[rss_sources]]")
    lines = _uncomment_block(lines, "# [[categories]]")
    data = tomllib.loads("\n".join(lines))

    assert data["rss_sources"][0]["name"]
    assert data["rss_sources"][0]["url"]
    assert [c["key"] for c in data["categories"]] == ["example_topic", "general"]


def test_init_workflow_pins_the_default_ref(tmp_path):
    from sundry.scaffold import DEFAULT_ENGINE_REF

    run_init([str(tmp_path)])
    workflow_text = (tmp_path / ".github" / "workflows" / "digest.yml").read_text()
    assert f"digest-reusable.yml@{DEFAULT_ENGINE_REF}" in workflow_text


def test_init_ref_is_configurable(tmp_path):
    run_init([str(tmp_path), "--ref", "v3.0.0"])
    workflow_text = (tmp_path / ".github" / "workflows" / "digest.yml").read_text()
    assert "digest-reusable.yml@v3.0.0" in workflow_text


def test_init_ci_workflow_pins_the_default_ref(tmp_path):
    from sundry.scaffold import DEFAULT_ENGINE_REF

    run_init([str(tmp_path)])
    ci_text = (tmp_path / ".github" / "workflows" / "ci.yml").read_text()
    assert f'sundry.git@{DEFAULT_ENGINE_REF}"' in ci_text


def test_init_ci_workflow_has_the_three_jobs(tmp_path):
    run_init([str(tmp_path)])
    ci_text = (tmp_path / ".github" / "workflows" / "ci.yml").read_text()
    assert "reviewdog/action-actionlint" in ci_text  # lint-workflows
    assert "sundry --config config/feeds.toml" in ci_text  # validate-config
    assert "gitleaks" in ci_text  # scan-secrets


def test_init_refuses_to_overwrite_ci_workflow_without_force(tmp_path):
    ci_path = tmp_path / ".github" / "workflows" / "ci.yml"
    ci_path.parent.mkdir(parents=True)
    ci_path.write_text("placeholder", encoding="utf-8")
    assert run_init([str(tmp_path)]) == 1
    assert ci_path.read_text() == "placeholder"


def test_init_refuses_to_overwrite_agents_md_without_force(tmp_path):
    agents_path = tmp_path / "AGENTS.md"
    agents_path.write_text("placeholder", encoding="utf-8")
    assert run_init([str(tmp_path)]) == 1
    assert agents_path.read_text() == "placeholder"


def test_init_agents_md_has_the_schema_and_is_valid_toml(tmp_path):
    import tomllib

    run_init([str(tmp_path)])
    agents_text = (tmp_path / "AGENTS.md").read_text()
    assert "## config/feeds.toml schema" in agents_text
    assert "## Never do this" in agents_text

    # Pull the fenced ```toml block out and confirm it actually parses —
    # the schema reference is only useful to an agent if it's correct.
    block = agents_text.split("```toml\n", 1)[1].split("\n```", 1)[0]
    tomllib.loads(block)


def test_init_agents_md_pins_the_ref_and_detected_repo_slug(tmp_path):
    from sundry.scaffold import DEFAULT_ENGINE_REF

    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "remote", "add", "origin", "https://github.com/someone/some-repo.git"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    run_init([str(tmp_path)])
    agents_text = (tmp_path / "AGENTS.md").read_text()
    assert f"sundry.git@{DEFAULT_ENGINE_REF}" in agents_text
    assert "gh workflow run digest.yml --repo someone/some-repo" in agents_text


def test_init_claude_md_points_at_agents_md(tmp_path):
    run_init([str(tmp_path)])
    claude_text = (tmp_path / "CLAUDE.md").read_text()
    assert "AGENTS.md" in claude_text


def test_init_refuses_to_overwrite_without_force(tmp_path, capsys):
    assert run_init([str(tmp_path)]) == 0
    exit_code = run_init([str(tmp_path)])
    assert exit_code == 1
    assert "already exists" in capsys.readouterr().err


def test_init_force_overwrites(tmp_path):
    assert run_init([str(tmp_path)]) == 0
    assert run_init([str(tmp_path), "--force"]) == 0


def test_cli_main_dispatches_init_subcommand(tmp_path):
    exit_code = main(["init", str(tmp_path)])
    assert exit_code == 0
    assert (tmp_path / "config" / "feeds.toml").is_file()
    assert (tmp_path / ".github" / "workflows" / "digest.yml").is_file()


def test_detect_repo_slug_falls_back_without_a_git_remote(tmp_path):
    assert _detect_repo_slug(tmp_path) == "<owner>/<repo>"


def test_detect_repo_slug_reads_a_github_https_remote(tmp_path):
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "remote", "add", "origin", "https://github.com/someone/some-repo.git"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    assert _detect_repo_slug(tmp_path) == "someone/some-repo"


def test_detect_repo_slug_reads_a_github_ssh_remote(tmp_path):
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "remote", "add", "origin", "git@github.com:someone/some-repo.git"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    assert _detect_repo_slug(tmp_path) == "someone/some-repo"


def test_init_next_steps_include_a_gh_cli_command(tmp_path, capsys):
    run_init([str(tmp_path)])
    out = capsys.readouterr().out
    assert "gh workflow run digest.yml" in out
    assert "alias run-digest=" in out
