import multiprocessing as mp
import subprocess
import sys
import time
from contextlib import ExitStack

import pytest
import requests

from git_pypi.cli.run import main


@pytest.fixture
def config(tmp_path, random_port):
    return {
        "cache_dir_path": tmp_path / "cache",
        "host": "127.0.0.1",
        "port": random_port,
        "fallback_index_url": "",
    }


@pytest.fixture
def config_file_path(config, tmp_path):
    config = """
    package-artifacts-dir-path = "dist"
    cached-artifacts-dir-path = "{cache_dir_path}"
    build-command = ["make", "build"]
    fallback-index-url = "{fallback_index_url}"

    [server]
    host = "{host}"
    port = {port}
    timeout = 60
    """.format(**config)

    config_file_path = tmp_path / "config.toml"
    config_file_path.write_text(config)

    return config_file_path


@pytest.fixture
def run_main(config, config_file_path, git_repo_dir_path):
    with ExitStack() as es:

        def _wait_for_it(
            process: mp.Process,
            host: str,
            port: int,
            timeout=5,
        ) -> None:
            url = f"http://{host}:{port}/health"
            timeout_at = time.monotonic()
            while time.monotonic() > timeout_at or not process.is_alive():
                try:
                    r = requests.get(url, timeout=0.5)
                except requests.ConnectionError:
                    continue

                if r.status_code == 200:
                    return

            assert process.is_alive(), f"process {process!r} died"

        def _fixture(*args):
            args = ("-c", str(config_file_path), "-r", str(git_repo_dir_path), *args)
            p = mp.Process(target=main, args=(args,))
            p.start()
            es.callback(lambda: p.join(5))
            es.callback(p.kill)

            _wait_for_it(p, config["host"], config["port"])

        yield _fixture


@pytest.fixture
def venv_dir_path(tmp_path):
    venv_dir_path = tmp_path / "venv"
    subprocess.check_call([sys.executable, "-m", "venv", str(venv_dir_path)])
    return venv_dir_path


@pytest.fixture
def run_pip_install(venv_dir_path):
    def _fixture(*args):
        subprocess.check_call(
            [
                str(venv_dir_path / "bin" / "python"),
                "-m",
                "pip",
                "install",
                *args,
            ]
        )

    return _fixture


@pytest.mark.network
class TestWithFallbackIndexURL:
    @pytest.fixture
    def config(self, config):
        config["fallback_index_url"] = "https://pypi.python.org/simple"
        return config

    def test_runs_a_pypi_server(
        self,
        config,
        run_main,
        run_pip_install,
    ):
        run_main()

        index_url = "http://{host}:{port}/simple".format(**config)
        run_pip_install("--no-cache-dir", "--index-url", index_url, "git-pypi-foobar")


def test_returns_200_if_project_found(
    config,
    run_main,
    snapshot,
):
    run_main()

    url = "http://{host}:{port}/simple/git-pypi-bar".format(**config)
    r = requests.get(url, timeout=5)

    assert r.status_code == 200, r.text
    snapshot.assert_match(r.text, "expected.html")


def test_returns_404_if_project_not_found(
    config,
    run_main,
):
    run_main()

    url = "http://{host}:{port}/simple/git-pypi-bogus".format(**config)
    r = requests.get(url, timeout=5)

    assert r.status_code == 404, r.text


def test_returns_404_if_package_not_found(
    config,
    run_main,
):
    run_main()

    url = "http://{host}:{port}/packages/git_pypi_bogus-1.0.0.tar.gz".format(**config)
    r = requests.get(url, timeout=5)

    assert r.status_code == 404, r.text


def test_healthcheck_returns_200(
    config,
    run_main,
):
    run_main()

    url = "http://{host}:{port}/health".format(**config)
    r = requests.get(url, timeout=5)

    assert r.status_code == 200, r.text


def test_clears_cache_on_start_if_cache_clear_flag_is_set(
    config,
    run_main,
):
    cache_dir_path = config["cache_dir_path"]
    cache_dir_path.mkdir(exist_ok=True, parents=True)
    (cache_dir_path / "file-0.test").write_text("")
    (cache_dir_path / "file-1.test").write_text("")

    run_main("--clear-cache")

    assert not cache_dir_path.exists()
