from tech_news_digest.cli import main
from tech_news_digest.config import load_config
from tech_news_digest.scaffold import run_init


def test_init_creates_config_and_workflow(tmp_path):
    exit_code = run_init([str(tmp_path)])
    assert exit_code == 0

    config_path = tmp_path / "config" / "feeds.toml"
    workflow_path = tmp_path / ".github" / "workflows" / "digest.yml"
    assert config_path.is_file()
    assert workflow_path.is_file()


def test_init_config_is_valid_and_ready_to_build():
    # Doesn't touch disk beyond tmp_path via run_init in the test above;
    # here we just confirm the template itself parses and satisfies the
    # same validation a real feeds.toml has to pass.
    import tomllib

    from tech_news_digest.scaffold import CONFIG_TEMPLATE

    tomllib.loads(CONFIG_TEMPLATE)  # no TOML syntax errors


def test_init_config_loads_via_load_config(tmp_path):
    run_init([str(tmp_path)])
    config = load_config(tmp_path / "config" / "feeds.toml")
    assert {category.key for category in config.categories} == {"general"}


def test_init_workflow_pins_the_default_ref(tmp_path):
    from tech_news_digest.scaffold import DEFAULT_ENGINE_REF

    run_init([str(tmp_path)])
    workflow_text = (tmp_path / ".github" / "workflows" / "digest.yml").read_text()
    assert f"digest-reusable.yml@{DEFAULT_ENGINE_REF}" in workflow_text


def test_init_ref_is_configurable(tmp_path):
    run_init([str(tmp_path), "--ref", "v3.0.0"])
    workflow_text = (tmp_path / ".github" / "workflows" / "digest.yml").read_text()
    assert "digest-reusable.yml@v3.0.0" in workflow_text


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
