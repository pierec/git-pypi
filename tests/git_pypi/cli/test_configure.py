from git_pypi.cli.configure import main


def test_generates_an_example_config(tmp_path, snapshot, capsys):
    config_path = tmp_path / "config.toml"
    main(["--config", str(config_path)])

    assert capsys.readouterr() == (
        f"Config file written to {config_path}\n",
        "",
    )
    snapshot.assert_match(config_path.read_text(), "expected_config.toml")


def test_refuses_to_overwrite_the_existing_config(tmp_path, capsys):
    config_path = tmp_path / "config.toml"

    main(["--config", str(config_path)])
    capsys.readouterr()
    main(["--config", str(config_path)])

    assert capsys.readouterr() == (
        f"Config file already exists at {config_path}, aborting\n",
        "",
    )


def test_overwrites_existing_config_if_force_flag_is_set(tmp_path, capsys):
    config_path = tmp_path / "config.toml"

    main(["--config", str(config_path)])
    mtimes = [config_path.stat().st_mtime]
    main(["--config", str(config_path), "--force"])
    mtimes += [config_path.stat().st_mtime]

    assert mtimes[0] < mtimes[1]

    assert capsys.readouterr() == (
        f"Config file written to {config_path}\n"
        f"Config file written to {config_path}\n",
        "",
    )
