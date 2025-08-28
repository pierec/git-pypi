import contextlib
import socket
import subprocess
from pathlib import Path

import pytest

TEST_DIR = Path(__file__).parent
REPO_BUNDLE_A_PATH = TEST_DIR / "test-repo-a.bundle"
REPO_BUNDLE_B_PATH = TEST_DIR / "test-repo-b.bundle"


@pytest.fixture(scope="session")
def test_dir_path():
    return TEST_DIR


@pytest.fixture
def cache_dir_path(tmp_path):
    return tmp_path / "cache"


@pytest.fixture
def git_repo_a_dir_path(tmp_path):
    repo_dir_path = tmp_path / "repo-a"
    subprocess.run(
        ["git", "clone", str(REPO_BUNDLE_A_PATH), repo_dir_path],  # noqa: S607
        check=True,
    )
    return repo_dir_path


@pytest.fixture
def git_repo_dir_path(git_repo_a_dir_path):
    return git_repo_a_dir_path


@pytest.fixture
def git_remote_repo_a_uri():
    return str(REPO_BUNDLE_A_PATH)


@pytest.fixture
def git_remote_repo_a_dir_path(tmp_path):
    return tmp_path / "remote-repo-a"


@pytest.fixture
def git_remote_repo_b_uri():
    return str(REPO_BUNDLE_B_PATH)


@pytest.fixture
def git_remote_repo_uri(git_remote_repo_b_uri):
    return git_remote_repo_b_uri


@pytest.fixture
def git_remote_repo_b_dir_path(tmp_path_factory):
    return tmp_path_factory.mktemp("remote-repo-b")


@pytest.fixture
def git_remote_repo_dir_path(git_remote_repo_b_dir_path):
    return git_remote_repo_b_dir_path


@pytest.fixture
def vendor_dir_path(test_dir_path):
    return test_dir_path / "vendor"


@pytest.fixture
def random_port():
    with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]
