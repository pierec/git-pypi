import logging
from pathlib import Path

from git_pypi.builder import PackageBuilder
from git_pypi.exc import GitError, PackageNotFoundError
from git_pypi.git import GitRepository

from .base import FileName, PackageIndex, ProjectName

logger = logging.getLogger(__name__)


class GitPackageIndex(PackageIndex):
    def __init__(
        self,
        builder: PackageBuilder,
        git_repo: GitRepository,
        skip_fetch: bool,
        fetch_timeout: float | None = None,
    ) -> None:
        self._builder = builder
        self._git_repo = git_repo
        self._skip_fetch = skip_fetch
        self._fetch_timeout = fetch_timeout

    def list_projects(self) -> list[ProjectName]:
        self.refresh()
        return sorted({p.project_name for p in self._git_repo.list_packages()})

    def list_packages(self, project_name: ProjectName) -> list[FileName]:
        self.refresh()
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

    def refresh(self) -> None:
        if self._skip_fetch:
            return

        try:
            self._git_repo.fetch(timeout=self._fetch_timeout)
        except GitError as e:
            logger.warning("Failed to refresh %r: %r", self._git_repo, e)
