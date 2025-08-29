import logging
import shutil
import typing as t
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import RLock
from weakref import WeakValueDictionary

from git_pypi.cmd import Cmd
from git_pypi.exc import BuilderError, CmdError
from git_pypi.git import GitRepository
from git_pypi.types import GitPackageInfo

logger = logging.getLogger(__name__)

CacheKey: t.TypeAlias = str


class PackageCache(t.Protocol):
    def cache(self, package: GitPackageInfo, artifact_file_path: Path) -> Path: ...

    def get(self, package: GitPackageInfo) -> Path | None: ...

    def clear(self): ...


class PackageBuilder:
    def __init__(
        self,
        git_repo: GitRepository,
        package_cache: PackageCache,
        build_command: t.Sequence[str],
        package_artifacts_dir_path: Path | str,
    ) -> None:
        self._build_command = Cmd(*build_command)
        self._package_artifacts_dir_path = Path(package_artifacts_dir_path)

        self._git_repo = git_repo
        self._cache = package_cache
        self._locks = PackageBuildLocks()

    def build(
        self,
        package: GitPackageInfo,
    ) -> Path:
        with self._locks.lock(package):
            if file_path := self._cache.get(package):
                logger.info("Cache hit, skipping build... package=%r", package)
                return file_path

            with (
                TemporaryDirectory() as temp_dir,
                self._git_repo.checkout(package, temp_dir),
            ):
                file_path = self._build(package, Path(temp_dir) / package.path)

        return file_path

    def _build(
        self,
        package: GitPackageInfo,
        package_dir_path: Path | str,
    ) -> Path:
        logger.info("Building... cmd=%r, package=%r", self._build_command, package)

        package_dir_path = Path(package_dir_path)

        try:
            self._build_command.run(cwd=package_dir_path)
        except CmdError as e:
            logger.error("Building... Failed! package=%r", package)
            raise BuilderError(f"Failed to build {package!r}") from e
        else:
            logger.info("Building... OK! package=%r", package)

        artifact_file_path = (
            package_dir_path / self._package_artifacts_dir_path / package.sdist_file_name
        )

        if not artifact_file_path.exists():
            dir_contents = sorted(str(s) for s in artifact_file_path.parent.glob("*"))
            raise BuilderError(
                f"The expected artifact file was not found at '{artifact_file_path}'."
                f" Parent directory contains: {dir_contents}.",
            )

        return self._cache.cache(
            package,
            artifact_file_path,
        )


class PackageBuildLocks:
    def __init__(self) -> None:
        self._lock = RLock()
        self._locks: WeakValueDictionary[str, RLock] = WeakValueDictionary()

    @contextmanager
    def lock(self, package: GitPackageInfo) -> t.Generator[None, None, None]:
        key = package.unique_key

        with self._lock:
            package_lock = self._locks.setdefault(key, RLock())

        with package_lock:
            yield


class LocalFSPackageCache(PackageCache):
    def __init__(self, dir_path: Path):
        self._dir_path = dir_path

    def cache(self, package: GitPackageInfo, artifact_file_path: Path) -> Path:
        """Copy the artifact atomically by first copying it to a temp file and
        then renaming it. Return the cached file path."""
        cached_artifact_file_path = self._get_cache_file_path(package)
        cached_artifact_file_path_tmp = cached_artifact_file_path.with_suffix(".tmp")

        try:
            cached_artifact_file_path.parent.mkdir(exist_ok=True, parents=True)
            shutil.copy(artifact_file_path, cached_artifact_file_path_tmp)
            cached_artifact_file_path_tmp.rename(cached_artifact_file_path)
        except OSError as e:
            raise BuilderError(f"Failed to copy build artifacts of {package}") from e

        return cached_artifact_file_path

    def get(self, package: GitPackageInfo) -> Path | None:
        cached_artifact_file_path = self._get_cache_file_path(package)

        if not cached_artifact_file_path.exists():
            return None

        return cached_artifact_file_path

    def _get_cache_file_path(self, package: GitPackageInfo) -> Path:
        return self._dir_path / package.unique_key

    def clear(self):
        shutil.rmtree(self._dir_path)
