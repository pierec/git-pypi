from git_pypi.config import Config
from git_pypi.package_index import (
    CombinedPackageIndex,
    GitPackageIndex,
    create_package_index,
)


def _create_config(config: dict) -> Config:
    return Config.from_dict(config)


def test_creates_a_combined_package_index(
    git_repo_dir_path,
    git_remote_repo_uri,
    git_remote_repo_dir_path,
    vendor_dir_path,
):
    config = _create_config(
        {
            "repositories": {
                "foo": {
                    "type": "git",
                    "dir_path": str(git_repo_dir_path),
                },
                "bar": {
                    "type": "git",
                    "remote_uri": git_remote_repo_uri,
                    "dir_path": str(git_remote_repo_dir_path),
                },
                "zoo": {
                    "type": "package-dir",
                    "dir_path": str(vendor_dir_path),
                },
            }
        }
    )

    package_index = create_package_index(config)

    assert isinstance(package_index, CombinedPackageIndex)
    assert len(package_index._indexes) == 3


def test_creates_a_singular_package_index(git_repo_dir_path):
    config = _create_config(
        {
            "repositories": {
                "foo": {
                    "type": "git",
                    "dir_path": str(git_repo_dir_path),
                },
            }
        }
    )

    package_index = create_package_index(config)

    assert isinstance(package_index, GitPackageIndex)
