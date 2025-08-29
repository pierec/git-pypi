import logging
import re
import tarfile

import pytest

import git_pypi.exc
from git_pypi.config import Config
from git_pypi.package_index.factory import create_package_index
from git_pypi.package_index.git import GitPackageIndex


def clean_logs(logs: str) -> str:
    logs = re.sub(r"dst_dir='[^']+'", "dst_dir=[...]", logs)
    logs = re.sub(r"make\[\d\]", "make", logs)
    return logs


@pytest.fixture(
    params=[
        "git_local_package_index",
        "git_remote_package_index",
    ]
)
def git_package_index(request):
    return request.getfixturevalue(request.param)


@pytest.fixture
def git_local_package_index(
    cache_dir_path,
    git_repo_a_dir_path,
) -> GitPackageIndex:
    config = Config.from_dict(
        {
            "cached-artifacts-dir-path": str(cache_dir_path),
            "repositories": {
                "main": {
                    "type": "git",
                    "dir-path": str(git_repo_a_dir_path),
                }
            },
        }
    )

    package_index = create_package_index(config)
    assert isinstance(package_index, GitPackageIndex)

    return package_index


@pytest.fixture
def git_remote_package_index(
    cache_dir_path,
    git_remote_repo_a_uri,
    git_remote_repo_a_dir_path,
) -> GitPackageIndex:
    config = Config.from_dict(
        {
            "cached-artifacts-dir-path": str(cache_dir_path),
            "repositories": {
                "main": {
                    "type": "git",
                    "remote-uri": git_remote_repo_a_uri,
                    "dir-path": str(git_remote_repo_a_dir_path),
                }
            },
        }
    )

    package_index = create_package_index(config)
    assert isinstance(package_index, GitPackageIndex)

    return package_index


def test_lists_projects(git_package_index):
    projects = git_package_index.list_projects()
    assert projects == [
        "git-pypi-bad-artifact",
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


def test_raises_builder_error_if_artifact_cannot_be_found(
    caplog,
    git_package_index,
    snapshot,
):
    caplog.set_level(logging.INFO, logger="git_pypi")

    with pytest.raises(
        git_pypi.exc.BuilderError,
        match=(
            r"The expected artifact file was not found at '.*/git_pypi_bad_artifact-1\.0\.0\.tar\.gz'\."
            r" Parent directory contains: \['.*/git_pypi_bad_artifact-0\.1\.0\.tar\.gz'\]\."
        ),
    ):
        git_package_index.get_package_by_file_name("git_pypi_bad_artifact-1.0.0.tar.gz")

    snapshot.assert_match(clean_logs(caplog.text), "expected_logs.txt")


@pytest.mark.skip("TODO")
def test_packages_are_cached_based_on_git_sha1(): ...


@pytest.mark.skip("TODO")
def test_switches_checkout_dir_if_repo_exists_with_different_remote(): ...
