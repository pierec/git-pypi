import cattrs

from git_pypi.config import Config
from git_pypi.package_index import (
    CombinedPackageIndex,
    GitPackageIndex,
    create_package_index,
)


def _create_config(**kwargs) -> Config:
    return cattrs.structure(kwargs, Config)


def test_creates_a_combined_package_index():
    config = _create_config(local_packages_dir_path="foo/bar")

    package_index = create_package_index(config)

    assert isinstance(package_index, CombinedPackageIndex)
    assert len(package_index._indexes) > 1


def test_creates_a_singular_package_index():
    config = _create_config(local_packages_dir_path=None)

    package_index = create_package_index(config)

    assert isinstance(package_index, GitPackageIndex)
