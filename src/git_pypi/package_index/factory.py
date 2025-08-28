import functools
import typing as t

from git_pypi.builder import LocalFSPackageCache, PackageBuilder, PackageCache
from git_pypi.config import Config, GitRepositoryConfig, PackageDirRepositoryConfig
from git_pypi.git import GitRepository

from .base import PackageIndex
from .combined import CombinedPackageIndex
from .git import GitPackageIndex
from .localfs import LocalFSPackageIndex


def create_package_index(config: Config) -> PackageIndex:
    indexes: list[PackageIndex] = []

    package_cache = create_package_cache(config)

    for repository_config in config.repositories.values():
        indexes.append(_create_package_index(repository_config, package_cache))

    if len(indexes) == 1:
        return indexes[0]
    else:
        return CombinedPackageIndex(indexes)


def create_package_cache(config: Config) -> PackageCache:
    return LocalFSPackageCache(
        dir_path=config.cached_artifacts_dir_path,
    )


@functools.singledispatch
def _create_package_index(
    config: t.Any,
    package_cache: PackageCache,
) -> PackageIndex:
    raise NotImplementedError(type(config))


@_create_package_index.register
def _(
    config: GitRepositoryConfig,
    package_cache: PackageCache,
) -> GitPackageIndex:
    if config.remote_uri:
        git_repo = GitRepository.from_remote(
            dir_path=config.dir_path,
            remote=config.remote_uri,
        )
    else:
        git_repo = GitRepository.from_local_dir(
            dir_path=config.dir_path,
        )

    builder = PackageBuilder(
        git_repo=git_repo,
        package_cache=package_cache,
        build_command=config.build_command,
        package_artifacts_dir_path=config.package_artifacts_dir_path,
        extra_checkout_paths=config.extra_checkout_paths,
    )

    return GitPackageIndex(
        builder=builder,
        git_repo=git_repo,
    )


@_create_package_index.register
def _(
    config: PackageDirRepositoryConfig,
    package_cache: PackageCache,
) -> LocalFSPackageIndex:
    return LocalFSPackageIndex(dir_path=config.dir_path)
