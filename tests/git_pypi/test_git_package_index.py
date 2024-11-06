import logging
import re
import tarfile

import pytest

import git_pypi


def clean_logs(logs: str) -> str:
    logs = re.sub(r"dst_dir='[^']+'", "dst_dir=[...]", logs)
    logs = re.sub(r"make\[\d\]", "make", logs)
    return logs


@pytest.fixture
def config(git_repo_dir_path, tmp_path):
    config = git_pypi.Config(
        repo_dir_path=git_repo_dir_path,
        cached_artifacts_dir_path=tmp_path / "cache",
        fallback_index_url=None,
    )
    return config


@pytest.fixture
def git_package_index(config):
    return git_pypi.GitPackageIndex.from_config(config)


def test_lists_projects(git_package_index):
    projects = git_package_index.list_projects()
    assert projects == [
        "git-pypi-bar",
        "git-pypi-faulty",
        "git-pypi-foo",
        "git-pypi-foobar",
    ]


def test_lists_sdist_packages(git_package_index):
    packages = [
        git_package_index.list_packages(project_name)
        for project_name in [
            "git-pypi-bar",
            "git-pypi-faulty",
            "git-pypi-foo",
            "git-pypi-foobar",
            "foo",
        ]
    ]

    assert packages == [
        [
            "git_pypi_bar-0.1.0.tar.gz",
            "git_pypi_bar-0.2.0.tar.gz",
        ],
        [
            "git_pypi_faulty-9.1.0.tar.gz",
        ],
        [
            "git_pypi_foo-0.1.0.tar.gz",
            "git_pypi_foo-0.1.1.tar.gz",
        ],
        [
            "git_pypi_foobar-0.1.0.tar.gz",
        ],
        [],
    ]


@pytest.mark.parametrize(
    "file_name",
    [
        "git_pypi_foo-0.1.1.tar.gz",
        "git_pypi_bar-0.2.0.tar.gz",
        "git_pypi_foobar-0.1.0.tar.gz",
    ],
)
def test_builds_and_returns_sdist_packages(
    file_name: str,
    git_package_index,
    caplog,
    snapshot,
):
    expected_package_dir = file_name.removesuffix(".tar.gz")
    caplog.set_level(logging.INFO, logger="git_pypi")

    package_path = git_package_index.get_package_by_file_name(file_name)

    with tarfile.open(package_path, "r:gz") as tf:
        pyproject_fh = tf.extractfile(f"{expected_package_dir}/pyproject.toml")
        assert pyproject_fh, "pyproject.toml missing from the archive"
        pyproject = pyproject_fh.read()

    snapshot.assert_match(pyproject, "expected_pyproject.toml")
    snapshot.assert_match(clean_logs(caplog.text), "expected_logs.txt")


def test_raises_package_not_found_on_bad_files(caplog, git_package_index):
    caplog.set_level(logging.INFO, logger="git_pypi")

    with pytest.raises(git_pypi.exc.PackageNotFoundError):
        git_package_index.get_package_by_file_name("foo")

    assert caplog.messages == []


def test_raises_builder_error_if_package_cannot_be_built(
    caplog,
    git_package_index,
    snapshot,
):
    caplog.set_level(logging.INFO, logger="git_pypi")

    with pytest.raises(git_pypi.exc.BuilderError):
        git_package_index.get_package_by_file_name("git_pypi_faulty-9.1.0.tar.gz")

    snapshot.assert_match(clean_logs(caplog.text), "expected_logs.txt")


@pytest.mark.skip("TODO")
def test_packages_are_cached_based_on_git_sha1(): ...
