import typing as t
from pathlib import Path

import typing_extensions as tt

from .builder import PackageBuilder
from .config import DEFAULT_CONFIG, Config
from .exc import PackageNotFoundError
from .git import GitRepository

ProjectName: t.TypeAlias = str
FileName: t.TypeAlias = str


class GitPackageIndex:
    def __init__(
        self,
        builder: PackageBuilder,
        git_repo: GitRepository,
    ) -> None:
        self._builder = builder
        self._git_repo = git_repo

    @classmethod
    def from_config(
        cls,
        config: Config = DEFAULT_CONFIG,
    ) -> tt.Self:
        git_repo = GitRepository.from_config(config=config)
        builder = PackageBuilder.from_config(git_repo=git_repo, config=config)
        return cls(builder, git_repo)

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
