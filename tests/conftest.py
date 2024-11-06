import contextlib
import socket
import subprocess
from pathlib import Path

import pytest

TEST_DIR = Path(__file__).parent
REPO_BUNDLE_PATH = TEST_DIR / "test-repo.bundle"


@pytest.fixture(scope="session")
def git_repo_dir_path(tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp("test-repo")
    repo_dir_path = tmp_path / "repo"
    subprocess.run(
        ["git", "clone", str(REPO_BUNDLE_PATH), repo_dir_path],  # noqa: S607
        check=True,
    )
    return repo_dir_path


@pytest.fixture
def random_port():
    with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]
