from git_pypi.config import Config

from .base import PackageIndex
from .combined import CombinedPackageIndex
from .git import GitPackageIndex
from .localfs import LocalFSPackageIndex


def create_package_index(config: Config) -> PackageIndex:
    indexes: list[PackageIndex] = [GitPackageIndex.from_config(config)]

    if config.local_packages_dir_path:
        indexes.append(LocalFSPackageIndex.from_config(config))

    if len(indexes) == 1:
        return indexes[0]
    else:
        return CombinedPackageIndex(indexes)
