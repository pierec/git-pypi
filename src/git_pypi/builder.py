import logging
import shutil
import subprocess
import typing as t
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import RLock
from weakref import WeakValueDictionary

import typing_extensions as tt

from .config import DEFAULT_CONFIG, Config
from .exc import BuilderError
from .git import GitRepository
from .types import GitPackageInfo

logger = logging.getLogger(__name__)

CacheKey: t.TypeAlias = str


class PackageCache(t.Protocol):
    def cache(self, package: GitPackageInfo, artifact_file_path: Path) -> Path: ...

    def get(self, package: GitPackageInfo) -> Path | None: ...

    def clear(self): ...


class PackageBuilder:
    def __init__(  # noqa: PLR0913
        self,
        git_repo: GitRepository,
        package_cache: PackageCache,
        build_command: t.Sequence[str],
        package_artifacts_dir_path: Path | str,
        cached_artifacts_dir_path: Path | str,
        extra_checkout_paths: t.Sequence[Path | str] | None = None,
    ) -> None:
        self._build_command = list(build_command)
        self._package_artifacts_dir_path = Path(package_artifacts_dir_path)
        self._cached_artifacts_dir_path = Path(cached_artifacts_dir_path)
        self._extra_checkout_paths = [Path(p) for p in (extra_checkout_paths or [])]

        self._git_repo = git_repo
        self._cache = package_cache
        self._locks = PackageBuildLocks()

    @classmethod
    def from_config(
        cls,
        git_repo: GitRepository,
        config: Config = DEFAULT_CONFIG,
        package_cache: PackageCache | None = None,
    ) -> tt.Self:
        return cls(
            git_repo=git_repo,
            package_cache=package_cache or LocalFSPackageCache.from_config(config),
            build_command=config.build_command,
            package_artifacts_dir_path=config.package_artifacts_dir_path,
            cached_artifacts_dir_path=config.cached_artifacts_dir_path,
            extra_checkout_paths=config.extra_checkout_paths,
        )

    def build(
        self,
        package: GitPackageInfo,
    ) -> Path:
        with self._locks.lock(package):
            if file_path := self._cache.get(package):
                logger.info("Cache hit, skipping build... package=%r", package)
                return file_path

            with TemporaryDirectory() as temp_dir:
                self._git_repo.checkout(package, temp_dir, self._extra_checkout_paths)
                file_path = self._build(package, Path(temp_dir) / package.path)

        return file_path

    def _build(
        self,
        package: GitPackageInfo,
        package_dir_path: Path | str,
    ) -> Path:
        logger.info("Building... cmd=%r, package=%r", self._build_command, package)

        package_dir_path = Path(package_dir_path)

        cp = subprocess.run(  # noqa: S603
            self._build_command,
            cwd=package_dir_path,
            capture_output=True,
            check=False,
        )

        if cp.returncode == 0:
            logger.info("Building... OK! package=%r", package)
        else:
            logger.error("Building... Failed! package=%r", package)
            for line in cp.stdout.splitlines():
                logger.error("OUT> %s", line.decode())
            for line in cp.stderr.splitlines():
                logger.error("ERR> %s", line.decode())
            raise BuilderError(f"Failed to build {package!r}", cp)

        artifact_file_path = (
            package_dir_path / self._package_artifacts_dir_path / package.sdist_file_name
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

    @classmethod
    def from_config(cls, config: Config = DEFAULT_CONFIG) -> tt.Self:
        return cls(dir_path=config.cached_artifacts_dir_path)

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
