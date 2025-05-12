from pathlib import Path

from git_pypi.exc import GitPackageIndexError, PackageNotFoundError

from .base import FileName, PackageIndex, ProjectName


class CombinedPackageIndex(PackageIndex):
    """A package index implementation combining several sub-indexes."""

    def __init__(self, indexes: list[PackageIndex]) -> None:
        self._indexes = indexes

        if not self._indexes:
            raise GitPackageIndexError("At least one package index is required.")

    def list_projects(self) -> list[ProjectName]:
        return sorted(
            {
                project_name
                for idx in self._indexes
                for project_name in idx.list_projects()
            }
        )

    def list_packages(self, project_name: ProjectName) -> list[FileName]:
        return sorted(
            {
                file_name
                for idx in self._indexes
                for file_name in idx.list_packages(project_name)
            }
        )

    def get_package_by_file_name(self, file_name: FileName) -> Path:
        for idx in self._indexes:
            try:
                return idx.get_package_by_file_name(file_name)
            except PackageNotFoundError:
                continue

        raise PackageNotFoundError(file_name)
