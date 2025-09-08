from concurrent.futures import ThreadPoolExecutor
from itertools import chain
from pathlib import Path

from git_pypi.exc import GitPackageIndexError, PackageNotFoundError

from .base import FileName, PackageIndex, ProjectName


class CombinedPackageIndex(PackageIndex):
    """A package index implementation combining several sub-indexes."""

    def __init__(self, indexes: list[PackageIndex]) -> None:
        self._indexes = indexes
        self._thread_pool = ThreadPoolExecutor()

        if not self._indexes:
            raise GitPackageIndexError("At least one package index is required.")

    def list_projects(self) -> list[ProjectName]:
        project_names = self._thread_pool.map(
            lambda idx: idx.list_projects(),
            self._indexes,
        )

        return sorted(set(chain.from_iterable(project_names)))

    def list_packages(self, project_name: ProjectName) -> list[FileName]:
        file_names = self._thread_pool.map(
            lambda idx: idx.list_packages(project_name),
            self._indexes,
        )

        return sorted(set(chain.from_iterable(file_names)))

    def get_package_by_file_name(self, file_name: FileName) -> Path:
        for idx in self._indexes:
            try:
                return idx.get_package_by_file_name(file_name)
            except PackageNotFoundError:
                continue

        raise PackageNotFoundError(file_name)

    def refresh(self) -> None:
        for index in self._indexes:
            index.refresh()

    def close(self) -> None:
        self._thread_pool.shutdown()
