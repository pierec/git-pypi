import pytest

from git_pypi.config import Config
from git_pypi.exc import PackageNotFoundError
from git_pypi.package_index.factory import create_package_index
from git_pypi.package_index.localfs import LocalFSPackageIndex


@pytest.fixture
def localfs_package_index(
    cache_dir_path,
    vendor_dir_path,
) -> LocalFSPackageIndex:
    config = Config.from_dict(
        {
            "cached-artifacts-dir-path": str(cache_dir_path),
            "repositories": {
                "main": {
                    "type": "package-dir",
                    "dir-path": str(vendor_dir_path),
                }
            },
        }
    )

    package_index = create_package_index(config)
    assert isinstance(package_index, LocalFSPackageIndex)

    return package_index


def test_lists_projects(localfs_package_index):
    projects = localfs_package_index.list_projects()
    assert projects == [
        "vendored-a",
        "vendored-b",
    ]


def test_lists_packages(localfs_package_index):
    packages = [
        localfs_package_index.list_packages(project_name)
        for project_name in ["vendored-a", "vendored-b", "unknown"]
    ]

    assert packages == [
        [
            "vendored_a-0.2.19-py3-none-any.whl",
            "vendored_a-0.3.33-py3-none-any.whl",
            "vendored_a-0.4.0.tar.gz",
        ],
        [
            "vendored_b-0.3.33.tar.gz",
        ],
        [],
    ]


def test_returns_package(localfs_package_index, vendor_dir_path):
    package_path = localfs_package_index.get_package_by_file_name(
        "vendored_a-0.3.33-py3-none-any.whl"
    )

    assert package_path == vendor_dir_path / "vendored_a-0.3.33-py3-none-any.whl"


def test_raises_package_not_found_if_matching_file_not_found(localfs_package_index):
    package_file_name = "vendored_a-0.7.77-py3-none-any.whl"
    with pytest.raises(PackageNotFoundError, match=package_file_name):
        localfs_package_index.get_package_by_file_name(package_file_name)
