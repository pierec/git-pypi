from pathlib import Path

import pytest

import git_pypi
from git_pypi import FileName, ProjectName
from git_pypi.exc import GitPackageIndexError, PackageNotFoundError


class DummyPackageIndex(git_pypi.PackageIndex):
    def __init__(self, contents: dict[ProjectName, list[FileName]]) -> None:
        self._contents = contents

    def list_projects(self) -> list[ProjectName]:
        return sorted(self._contents.keys())

    def list_packages(self, project_name: ProjectName) -> list[FileName]:
        return sorted(self._contents.get(project_name, []))

    def get_package_by_file_name(self, file_name: FileName) -> Path:
        for file_names in self._contents.values():
            if file_name in file_names:
                return Path(file_name)

        raise PackageNotFoundError(file_name)


@pytest.fixture
def combined_package_index():
    return git_pypi.CombinedPackageIndex(
        [
            DummyPackageIndex(
                {
                    ProjectName("git-pypi-foo"): [
                        FileName("git_pypi_foo-0.1.0.tar.gz"),
                        FileName("git_pypi_foo-0.2.0.tar.gz"),
                        FileName("git_pypi_foo-0.3.0.tar.gz"),
                    ],
                    ProjectName("git-pypi-bar"): [
                        FileName("git_pypi_bar-1.1.0.tar.gz"),
                        FileName("git_pypi_bar-1.2.0.tar.gz"),
                        FileName("git_pypi_bar-1.3.0.tar.gz"),
                    ],
                }
            ),
            DummyPackageIndex(
                {
                    ProjectName("git-pypi-foo"): [
                        FileName("git_pypi_foo-0.2.0.tar.gz"),
                        FileName("git_pypi_foo-0.2.1.tar.gz"),
                        FileName("git_pypi_foo-1.3.0.tar.gz"),
                    ],
                    ProjectName("git-pypi-zoo"): [
                        FileName("git_pypi_zoo-8.9.0.tar.gz"),
                        FileName("git_pypi_zoo-7.6.5.tar.gz"),
                    ],
                }
            ),
        ]
    )


def test_cannot_initialized_with_empty_index_list():
    with pytest.raises(
        GitPackageIndexError,
        match=r"At least one package index is required\.",
    ):
        git_pypi.CombinedPackageIndex([])


def test_lists_projects(combined_package_index):
    projects = combined_package_index.list_projects()

    assert projects == [
        "git-pypi-bar",
        "git-pypi-foo",
        "git-pypi-zoo",
    ]


def test_lists_packages(combined_package_index):
    packages = [
        combined_package_index.list_packages(project)
        for project in [
            "git-pypi-foo",
            "git-pypi-bar",
            "git-pypi-zoo",
        ]
    ]

    assert packages == [
        [
            "git_pypi_foo-0.1.0.tar.gz",
            "git_pypi_foo-0.2.0.tar.gz",
            "git_pypi_foo-0.2.1.tar.gz",
            "git_pypi_foo-0.3.0.tar.gz",
            "git_pypi_foo-1.3.0.tar.gz",
        ],
        [
            "git_pypi_bar-1.1.0.tar.gz",
            "git_pypi_bar-1.2.0.tar.gz",
            "git_pypi_bar-1.3.0.tar.gz",
        ],
        [
            "git_pypi_zoo-7.6.5.tar.gz",
            "git_pypi_zoo-8.9.0.tar.gz",
        ],
    ]


@pytest.mark.parametrize(
    "name",
    [
        "git_pypi_foo-0.2.0.tar.gz",
        "git_pypi_bar-1.1.0.tar.gz",
        "git_pypi_zoo-7.6.5.tar.gz",
    ],
)
def test_gets_packages_by_filename(name, *, combined_package_index):
    path = combined_package_index.get_package_by_file_name(name)

    assert str(path) == name


def test_raises_package_not_found_if_matching_file_not_found(combined_package_index):
    package_file_name = "git_pypi_foo-9.9.9.tar.gz"

    with pytest.raises(PackageNotFoundError, match=package_file_name):
        combined_package_index.get_package_by_file_name(package_file_name)
