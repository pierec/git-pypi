from pathlib import Path

from git_pypi.builder import PackageBuilder
from git_pypi.exc import PackageNotFoundError
from git_pypi.git import GitRepository

from .base import FileName, PackageIndex, ProjectName


class GitPackageIndex(PackageIndex):
    def __init__(
        self,
        builder: PackageBuilder,
        git_repo: GitRepository,
    ) -> None:
        self._builder = builder
        self._git_repo = git_repo

    def list_projects(self) -> list[ProjectName]:
        return sorted({p.project_name for p in self._git_repo.list_packages()})

    def list_packages(self, project_name: ProjectName) -> list[FileName]:
        filtered_packages = (
            p.sdist_file_name
            for p in self._git_repo.list_packages()
            if p.project_name == project_name
        )
        return sorted(filtered_packages)

    def get_package_by_file_name(self, file_name: FileName) -> Path:
        filtered_packages = (
            p for p in self._git_repo.list_packages() if p.sdist_file_name == file_name
        )
        package = next(filtered_packages, None)

        if package is None:
            raise PackageNotFoundError(file_name)

        package_file_path = self._builder.build(package)
        return package_file_path
